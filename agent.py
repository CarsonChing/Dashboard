"""
TVM agent: DeepSeek parses the user sentence into structured fields; all math is local.

Sign convention: PV, FV, and PMT are dollar magnitudes (non-negative). Cash direction
is described in the answer text (loan vs savings). The underlying equation uses
PV*(1+r)^n + PMT*factor = FV with PMT as periodic outflow magnitude (positive number
subtracted in the implementation via the standard annuity identity).
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _sn(r: float, n: float) -> float:
    """Future value of $1 per period (ordinary annuity, end of period)."""
    if abs(r) < 1e-15:
        return n
    return ((1 + r) ** n - 1) / r


def _sn_due(r: float, n: float) -> float:
    """FV factor for annuity due: payments at start of each period."""
    return _sn(r, n) * (1 + r)


def _fv_end(pv: float, pmt: float, r: float, n: float) -> float:
    """FV with PMT as a positive periodic payment (reduces balance / builds toward FV)."""
    return pv * (1 + r) ** n - pmt * _sn(r, n)


def _fv_begin(pv: float, pmt: float, r: float, n: float) -> float:
    return pv * (1 + r) ** n - pmt * _sn_due(r, n)


def _bisect_rate(
    pv: float,
    fv: float,
    pmt: float,
    n: float,
    begin: bool,
    lo: float = 1e-9,
    hi: float = 0.5,
) -> float:
    """Solve for per-period r in (lo, hi) such that FV equation holds."""

    def err(r: float) -> float:
        if begin:
            return _fv_begin(pv, pmt, r, n) - fv
        return _fv_end(pv, pmt, r, n) - fv

    e_lo, e_hi = err(lo), err(hi)
    if e_lo * e_hi > 0:
        hi = 2.0
        e_hi = err(hi)
        if e_lo * e_hi > 0:
            raise ValueError("Could not bracket interest rate; check inputs.")

    for _ in range(80):
        mid = (lo + hi) / 2
        e_mid = err(mid)
        if abs(e_mid) < 1e-10:
            return mid
        if e_lo * e_mid <= 0:
            hi, e_hi = mid, e_mid
        else:
            lo, e_lo = mid, e_mid
    return (lo + hi) / 2


def _bisect_n(
    pv: float,
    fv: float,
    pmt: float,
    r: float,
    begin: bool,
    lo: float = 1e-6,
    hi: float = 600.0,
) -> float:
    """Solve for n > 0."""

    def err(n: float) -> float:
        if begin:
            return _fv_begin(pv, pmt, r, n) - fv
        return _fv_end(pv, pmt, r, n) - fv

    e_lo, e_hi = err(lo), err(hi)
    if e_lo * e_hi > 0:
        hi = 1200.0
        e_hi = err(hi)
        if e_lo * e_hi > 0:
            raise ValueError("Could not bracket number of periods; check inputs.")

    for _ in range(80):
        mid = (lo + hi) / 2
        e_mid = err(mid)
        if abs(e_mid) < 1e-9:
            return mid
        if e_lo * e_mid <= 0:
            hi, e_hi = mid, e_mid
        else:
            lo, e_lo = mid, e_mid
    return (lo + hi) / 2


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _call_deepseek(user_text: str, annual_default: float) -> dict[str, Any]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing DEEPSEEK_API_KEY in environment or .env file."
        )

    client = OpenAI(api_key=api_key, base_url=DEFAULT_API_BASE)

    system = (
        "You extract time-value-of-money inputs from the user's message. "
        "Reply with a single JSON object only, no markdown. Schema:\n"
        '{"pv": number or null, "fv": number or null, "pmt": number or null, '
        '"n_periods": number or null, "annual_rate": number or null, '
        '"payments_per_year": number, "solve": "pv"|"fv"|"pmt"|"n"|"rate", '
        '"payment_due": "end"|"begin"}\n'
        "Use non-negative dollar amounts. Exactly one of pv,fv,pmt,n_periods,annual_rate "
        "should be null; set solve to that unknown. "
        f"If the user omits an interest rate and you are NOT solving for the rate, set annual_rate to null "
        f"and we will use default {annual_default:.4f}. If solving for rate, set annual_rate to null. "
        "Infer payments_per_year: 12 for monthly, 4 quarterly, 1 annual."
    )

    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    return _extract_json(content)


def _merge_defaults(
    data: dict[str, Any],
    annual_rate_default: float,
    solve_override: Optional[str],
    payment_due_ui: str,
) -> dict[str, Any]:
    ppy = int(data.get("payments_per_year") or 12)
    if ppy < 1:
        ppy = 12

    solve = str(data.get("solve") or "pmt").lower()
    if solve_override and solve_override != "Auto":
        solve = solve_override.lower()

    due = str(data.get("payment_due") or payment_due_ui or "end").lower()
    if due not in ("begin", "end"):
        due = "end"

    annual = data.get("annual_rate")
    if annual is None and solve != "rate":
        annual = annual_rate_default

    return {
        "pv": data.get("pv"),
        "fv": data.get("fv"),
        "pmt": data.get("pmt"),
        "n_periods": data.get("n_periods"),
        "annual_rate": annual,
        "payments_per_year": ppy,
        "solve": solve,
        "payment_due": due,
    }


def _solve_tvm(m: dict[str, Any]) -> tuple[str, dict[str, float]]:
    pv = m["pv"]
    fv = m["fv"]
    pmt = m["pmt"]
    n = m["n_periods"]
    annual = m["annual_rate"]
    ppy = m["payments_per_year"]
    solve = m["solve"]
    begin = m["payment_due"] == "begin"

    unknowns = sum(
        1
        for x in (pv, fv, pmt, n, annual)
        if x is None
    )
    if unknowns != 1:
        raise ValueError(
            "Expected exactly one unknown among PV, FV, PMT, n, or rate; "
            f"got {unknowns}. Try rephrasing."
        )

    if n is not None and n <= 0:
        raise ValueError("Number of periods must be positive.")
    if annual is not None and annual < 0:
        raise ValueError("Annual rate cannot be negative.")

    def with_r(r_period: float) -> dict[str, float]:
        assert n is not None
        if solve == "pv":
            if begin:
                pv_s = (fv + pmt * _sn_due(r_period, n)) / (1 + r_period) ** n
            else:
                pv_s = (fv + pmt * _sn(r_period, n)) / (1 + r_period) ** n
            return {"pv": pv_s, "fv": fv, "pmt": pmt, "n": n, "annual_rate": annual}
        if solve == "fv":
            if begin:
                fv_s = _fv_begin(pv, pmt, r_period, n)
            else:
                fv_s = _fv_end(pv, pmt, r_period, n)
            return {"pv": pv, "fv": fv_s, "pmt": pmt, "n": n, "annual_rate": annual}
        if solve == "pmt":
            if begin:
                num = pv * (1 + r_period) ** n - fv
                den = _sn_due(r_period, n)
            else:
                num = pv * (1 + r_period) ** n - fv
                den = _sn(r_period, n)
            if abs(den) < 1e-15:
                raise ValueError("Cannot solve payment for these inputs.")
            pmt_s = num / den
            return {"pv": pv, "fv": fv, "pmt": pmt_s, "n": n, "annual_rate": annual}
        raise ValueError(f"Unknown solve target: {solve}")

    if solve == "rate":
        if None in (pv, fv, pmt, n):
            raise ValueError("Solving rate requires PV, FV, PMT, and n all set.")
        r_period = _bisect_rate(float(pv), float(fv), float(pmt), float(n), begin)
        annual_out = r_period * ppy
        summary = (
            f"Implied nominal annual rate: {annual_out * 100:.4f}% "
            f"({ppy} payments per year), per-period r={r_period:.6f}."
        )
        return summary, {
            "pv": float(pv),
            "fv": float(fv),
            "pmt": float(pmt),
            "n_periods": float(n),
            "annual_rate": annual_out,
        }

    if annual is None:
        raise ValueError("Annual interest rate is required for this solve mode.")

    r_period = float(annual) / float(ppy)
    if solve == "n":
        if None in (pv, fv, pmt):
            raise ValueError("Solving n requires PV, FV, and PMT.")
        n_sol = _bisect_n(float(pv), float(fv), float(pmt), r_period, begin)
        summary = (
            f"Number of periods needed: {n_sol:.4f} "
            f"({ppy} periods per year, payment at {'begin' if begin else 'end'})."
        )
        return summary, {
            "pv": float(pv),
            "fv": float(fv),
            "pmt": float(pmt),
            "n_periods": n_sol,
            "annual_rate": float(annual),
        }

    if n is None:
        raise ValueError("Number of periods is required unless solving for n.")

    n = float(n)
    out = with_r(r_period)
    pv_f = float(out["pv"])
    fv_f = float(out["fv"])
    pmt_f = float(out["pmt"])
    mode = "beginning" if begin else "end"

    if solve == "pv":
        summary = (
            f"Present value: ${pv_f:,.2f} "
            f"(FV ${fv_f:,.2f}, payment ${pmt_f:,.2f} each period, "
            f"n={n:.2f}, {mode} of period)."
        )
    elif solve == "fv":
        summary = (
            f"Future value: ${fv_f:,.2f} "
            f"(PV ${pv_f:,.2f}, payment ${pmt_f:,.2f}, n={n:.2f}, {mode})."
        )
    else:
        summary = (
            f"Payment per period: ${pmt_f:,.2f} "
            f"(PV ${pv_f:,.2f}, FV ${fv_f:,.2f}, n={n:.2f}, {mode})."
        )

    return summary, {
        "pv": pv_f,
        "fv": fv_f,
        "pmt": pmt_f,
        "n_periods": n,
        "annual_rate": float(annual),
    }


def run_agent(
    user_text: str,
    annual_rate_default: float,
    solve_override: Optional[str],
    payment_due: str,
) -> str:
    """
    Parse the user sentence via DeepSeek, validate, solve TVM locally, return text.
    solve_override: None or 'Auto' to use model; else 'pv','fv','pmt','n','rate'.
    payment_due: 'end' or 'begin' from UI when model omits it.
    """
    text = (user_text or "").strip()
    if not text:
        return "Please enter a short description of the TVM problem."

    try:
        raw = _call_deepseek(text, annual_rate_default)
        merged = _merge_defaults(
            raw, annual_rate_default, solve_override, payment_due
        )
        summary, _nums = _solve_tvm(merged)
        return summary + "\n\n(Computed locally from parsed inputs; verify for your use case.)"
    except json.JSONDecodeError as exc:
        return f"Could not parse model JSON: {exc}"
    except Exception as exc:
        return f"Error: {exc}"
