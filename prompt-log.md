# Streamlit dashboard development for AI agent
_Exported on 4/17/2026 at 23:23:21 GMT+8 from Cursor (3.1.15)_

---

**User**

Objective
Create a simple Streamlit dashboard that provides a user interface for inter-
acting with an AI agent.
Learning Outcomes
By completing this assignment, you will:
• Build a basic Streamlit application
• Create interactive UI elements
• Connect UI to agent functionality
• Handle user input and display results
Requirements
0. App Scope (Required)
Your submission must include a runnable Streamlit app (app.py) that: - Starts
with streamlit run app.py - Accepts user input from the UI - Calls your local
agent.py module - Displays agent output in the dashboard
The agent can be adapted from Sentinel work, a prior mini-assignment, or
implemented new for this assignment.
1. Dashboard Layout (30%)
Create a Streamlit app with:
• Page title and description
• Sidebar for configuration
• Main area for content
• Clean, organized layout
2. User Input (30%)
Implement input handling:
• Text input for user queries
• Configuration options (e.g., dropdown, slider)
• Submit button
• Input validation
3. Agent Integration (30%)
Connect to an agent:
• Call agent with user input
• Display loading indicator during processing
• Show agent response
• Handle errors gracefully
4. User Experience (10%)
Add UX features:
• Clear feedback messages
• Appropriate use of Streamlit components
• Responsive design

I'm designing a demo, criteria listed above. You should write 3 files:
1. app.py — Your Streamlit application (~100-150 lines)
2. agent.py — Simple local agent module that app.py calls
3. requirements.txt — Dependencies

# Make codes as simple as possible, but fulfill all requirements.
# The agent should be a TVM calculator, that can read read user input (a short sentence describing the situation)

---

**Cursor**

Exploring the workspace and drafting a plan for the Streamlit TVM dashboard that meets the assignment criteria.



Workspace is empty — greenfield. Planning a minimal TVM “agent” that parses short natural-language queries and a Streamlit shell that satisfies every rubric item.



---

**User**

read deepseek api from .env, add a gitignore for pycache, env and dsstore

---

**Cursor**

Updating the plan to load the DeepSeek API from `.env` and add a `.gitignore`. Locating and reading the plan file.



Updating the plan document to integrate DeepSeek (loaded from `.env`) and add `.gitignore` entries.



Fixing the architecture diagram (remove confusing self-loop) and aligning the `agent.py` implementation outline with the DeepSeek flow.



Here is what was **added to the plan** ([`streamlit_tvm_dashboard_878bad99.plan.md`](/Users/carsonching/.cursor/plans/streamlit_tvm_dashboard_878bad99.plan.md)):

### DeepSeek + `.env`
- Load secrets with **`python-dotenv`** (`load_dotenv()` in `agent.py`).
- Documented env vars: **`DEEPSEEK_API_KEY`** (required), optional **`DEEPSEEK_API_BASE`** and **`DEEPSEEK_MODEL`**.
- **Flow:** DeepSeek returns **strict JSON** (TVM fields + what to solve for); **all math stays local** after validation so results stay deterministic and safe.
- **Dependencies:** `streamlit`, `python-dotenv`, plus **`openai`** (OpenAI-compatible client) *or* **`httpx`** — plan says to pick one.

### `.gitignore`
- New deliverable: **[`.gitignore`](.gitignore)** with at least **`__pycache__/`**, **`.env`**, **`.DS_Store`**; optional extras (`venv/`, etc.) noted as optional.

### Todos
- New first todo **`add-gitignore`**; **`add-agent`** and **`add-reqs`** updated to match DeepSeek + dotenv.

When you want this implemented in the repo, say **execute the plan** or **implement it** and we can add the files under your Dashboard folder.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing the dashboard: starting with `.gitignore`, then `agent.py`, `app.py`, and `requirements.txt`.



Fixing agent logic: correcting merge behavior when solving for rate, and restructuring TVM solving so `solve == "n"` doesn't require `n` to be set.



Fixing TVM sign convention (payments reduce future value) and correcting `_merge_defaults` so we don't overwrite a null `annual_rate` when solving for `rate`.



Here’s what was implemented:

### Files

1. **[`.gitignore`](/Users/carsonching/Documents/Courses/IIMT 3688/Assignments/Dashboard/.gitignore)** — Ignores `__pycache__/`, `*.py[cod]`, `.env`, `.DS_Store`, and `venv`/`.venv/`.

2. **[`agent.py`](/Users/carsonching/Documents/Courses/IIMT 3688/Assignments/Dashboard/agent.py)** — Loads `.env` via `python-dotenv`, reads `DEEPSEEK_API_KEY` (optional `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL`), calls DeepSeek with the **OpenAI-compatible** client, expects **strict JSON** (`pv`, `fv`, `pmt`, `n_periods`, `annual_rate`, `payments_per_year`, `solve`, `payment_due`). **Does not** use the model for arithmetic: it validates inputs, then solves **locally** with end/begin annuity formulas; **rate** and **n** use bisection when needed. **Rate solve:** `annual_rate` stays `None` in merge (default rate is not applied when `solve == "rate"`).

3. **[`app.py`](/Users/carsonching/Documents/Courses/IIMT 3688/Assignments/Dashboard/app.py)** (~92 lines) — `st.set_page_config`, title/description, **sidebar**: solve target (`Auto` / `pv` / `fv` / `pmt` / `n` / `rate`), **slider** for default annual %, **select** for payment timing; **main**: `text_area`, **Submit**, empty-input **warning**, **`st.spinner`**, **`st.success`** / **`st.error`**, expander + caption.

4. **[`requirements.txt`](/Users/carsonching/Documents/Courses/IIMT 3688/Assignments/Dashboard/requirements.txt)** — `streamlit`, `python-dotenv`, `openai` (pinned ranges as in the file).

### Run

Create `.env` in the project folder:

`DEEPSEEK_API_KEY=your_key_here`

Then:

`pip install -r requirements.txt`  
`streamlit run app.py`

A quick local check without a key returns: `Error: Missing DEEPSEEK_API_KEY in environment or .env file.` (handled in the UI as an error.)

All related todos are **completed**.

---

**User**

now write a README.md — Brief documentation (1 page max):
• Short system overview (problem, workflow, key components)
• How to run the app
• Features implemented
• Design decisions

---

**Cursor**


Reviewing the project files to ensure the README matches the implementation.




Added [README.md](README.md) in your Dashboard folder. It stays within about one printed page and covers:

- **Overview** — Plain-language TVM problem, flow from UI → `run_agent` → DeepSeek JSON → local solve → UI, plus a small component table.
- **How to run** — `pip install -r requirements.txt`, `.env` with `DEEPSEEK_API_KEY`, optional env vars, `streamlit run app.py`.
- **Features** — Layout, sidebar controls, validation, spinner, success/error handling, expander/captions.
- **Design decisions** — Parse-only LLM, single unknown, default rate vs rate-solve, sign convention, minimal dependencies.

The plan file was not modified.

