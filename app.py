import streamlit as st

from agent import run_agent

st.set_page_config(
    page_title="TVM Agent Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("TVM Agent Dashboard")
st.markdown(
    "Describe a **time-value-of-money** situation in one short sentence. "
    "The agent uses DeepSeek to read your scenario, then **solves the math locally**. "
    "Payments are treated as **positive dollar amounts** moving toward the stated FV "
    "(e.g. loan payoff or savings goal)."
)

with st.sidebar:
    st.header("Configuration")
    solve_choice = st.selectbox(
        "Solve for",
        ("Auto", "pv", "fv", "pmt", "n", "rate"),
        help="Auto lets the model pick the unknown; override for demos.",
    )
    default_annual_pct = st.slider(
        "Default annual rate if omitted (%)",
        min_value=0.0,
        max_value=25.0,
        value=6.0,
        step=0.25,
    )
    payment_timing = st.selectbox(
        "Payment timing (if not in prompt)",
        ("end", "begin"),
        format_func=lambda x: "End of period" if x == "end" else "Beginning of period",
    )
    st.caption(
        "Set `DEEPSEEK_API_KEY` in a `.env` file. Optional: `DEEPSEEK_API_BASE`, "
        "`DEEPSEEK_MODEL`."
    )

st.subheader("Your scenario")
query = st.text_area(
    "Describe the problem",
    height=120,
    placeholder=(
        "Example: I borrow $200,000 at 5.5% annual, monthly payments for 30 years; "
        "what is my payment? FV is zero."
    ),
)

submitted = st.button("Submit", type="primary")

if submitted:
    if not query or not query.strip():
        st.warning("Enter a short description before submitting.")
    else:
        override = None if solve_choice == "Auto" else solve_choice
        rate_decimal = default_annual_pct / 100.0
        with st.spinner("Calling agent (DeepSeek + local TVM)…"):
            result = run_agent(
                query.strip(),
                rate_decimal,
                override,
                payment_timing,
            )

        err = (
            result.startswith("Error:")
            or result.startswith("Could not parse")
            or "Missing DEEPSEEK_API_KEY" in result
        )
        if err:
            st.error(result)
        elif result.startswith("Please enter"):
            st.warning(result)
        else:
            st.success(result)

with st.expander("How to write prompts"):
    st.markdown(
        """
- Mention **PV** (loan or deposit), **payment**, **interest rate**, **term**, and **FV** (often **0** for a paid-off loan).
- Say whether payments are **monthly** / **annual** so periods are inferred.
- The model returns structured fields; the app **recomputes** amounts with formulas (not the LLM).
        """
    )

st.caption(
    "Assignment demo: Streamlit UI · sidebar controls · validation · loading state · errors shown inline."
)
