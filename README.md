# TVM Agent Dashboard

## System overview

**Problem.** Time-value-of-money (TVM) questions are often phrased in plain language (“loan amount, rate, term—what’s the payment?”). Turning that into reliable numbers requires both **interpretation** and **correct formulas**.

**Workflow.** The user describes a scenario in a short sentence in the Streamlit UI. **`app.py`** collects the query and sidebar settings, then calls **`run_agent`** in **`agent.py`**. The agent sends the text to the **DeepSeek** API (OpenAI-compatible) and asks for **structured JSON** (PV, FV, PMT, periods, annual rate, what to solve for, payment timing). **No dollar amounts are taken from the model’s arithmetic**—only parsed fields. The agent **validates** inputs and **computes** the unknown with local TVM math (closed forms where possible; bisection for rate or number of periods when needed). The result is shown back in the dashboard with loading and error feedback.

**Key components**

| Component | Role |
|-----------|------|
| `app.py` | Streamlit layout, sidebar controls, input validation, spinner, success/error display |
| `agent.py` | Load `.env`, DeepSeek chat completion, JSON extraction, local TVM solver, `run_agent()` |
| `requirements.txt` | `streamlit`, `python-dotenv`, `openai` |
| `.env` (local, not committed) | `DEEPSEEK_API_KEY`; optional `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL` |

## How to run

1. **Python 3.10+** recommended.

2. Create a **virtual environment** (optional but avoids global package clashes), then install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. In the project directory, create a **`.env`** file:

   ```env
   DEEPSEEK_API_KEY=your_key_here
   ```

   Optional: `DEEPSEEK_API_BASE` (default `https://api.deepseek.com/v1`), `DEEPSEEK_MODEL` (default `deepseek-chat`).

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the URL shown in the terminal (usually `http://localhost:8501`), enter a scenario, adjust sidebar options if needed, and click **Submit**.

## Features implemented

- **Page layout:** Title, description, wide layout, sidebar for configuration, main area for the query and results.
- **Inputs:** Multi-line scenario text, **Submit** button, **sidebar** selectbox for “solve for” (Auto or `pv` / `fv` / `pmt` / `n` / `rate`), **slider** for default annual rate when the prompt omits a rate, **select** for payment timing (end vs beginning of period) when not specified in text.
- **Validation:** Empty or whitespace-only input shows a **warning** and does not call the agent.
- **Agent integration:** `st.spinner` while the agent runs; **success** for a normal numeric answer; **error** for missing API key, bad JSON, or solver/validation failures.
- **UX:** Expander with prompt tips, captions for env vars and assumptions; consistent feedback for errors vs success.

## Design decisions

- **LLM for parsing only.** DeepSeek maps language to fields; **all TVM results are computed in Python** so answers stay auditable and deterministic (given parsed inputs).
- **Single unknown.** The model is instructed to leave exactly one of PV, FV, PMT, `n`, or annual rate as unknown; the solver rejects ambiguous or inconsistent cases with a clear message.
- **Default rate from the UI** applies when the model omits a rate **unless** the target unknown is **rate** (so rate-solving is not overwritten by the slider).
- **Sign convention.** PV, FV, and PMT are treated as **non-negative dollar amounts**; the implementation uses the standard future-value identity with **positive** periodic payments reducing balance toward the stated FV (e.g. loan paid to zero).
- **Dependencies.** Minimal stack: Streamlit for UI, `python-dotenv` for secrets, OpenAI SDK pointed at DeepSeek’s base URL—no NumPy required for TVM.
