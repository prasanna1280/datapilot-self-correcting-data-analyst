# PRP-001 — DataPilot core: self-correcting agent team

> **PRP** = Product Requirement Prompt: what to build, why it matters, the context an
> implementer (human or AI) needs, and how we know it is done.

| Field | Value |
|---|---|
| Track | 3, Agentic AI · AutoGen · Use case 03 |
| Level | Intermediate |
| Interface | Streamlit chat |
| Core skill | Agent loops + code execution |
| Status | ✅ Implemented (v1.0.0) |

## 1. Goal
A retail business owner uploads a year of sales data and asks, in plain English,
*"Which category dropped the most last month, and which region caused it?"*
A team of agents **plans → writes Python → runs it → fixes its own errors → reviews**
and returns a short answer, PNG charts and a re-runnable `analysis.py`.

## 2. Why (the real problem)
- Owners, sales managers and ops heads cannot write Python/SQL and wait days for an analyst.
- Normal chatbots **guess** numbers. DataPilot **calculates** them by running real code, and checks its own work.
- **Agentic, not a fixed pipeline:** the path is decided at run time. If code fails, the Coder
  sees the error and rewrites it. If the Reviewer is not satisfied, work goes back. The loop
  runs until the goal is met or a limit is reached.

## 3. What to build
| Agent | AutoGen class | Job |
|---|---|---|
| Planner | `AssistantAgent` | Reads question + data columns, writes a short step-by-step plan |
| Coder | `AssistantAgent` | Writes Python (pandas + matplotlib); rewrites it on error/feedback |
| Executor | `CodeExecutorAgent` | Runs code in a sandbox (Docker container or local folder), returns output/errors |
| Reviewer | `AssistantAgent` | Answers the question? Sensible numbers? Labelled charts? → `APPROVED` or feedback |
| User Proxy | `UserProxyAgent` (CLI) / approval buttons (web) | The human approves the answer or asks a follow-up |

**Team:** `SelectorGroupChat` with a deterministic `selector_func` (stretch goal). `TEAM_MODE=roundrobin` switches to `RoundRobinGroupChat`.
**Termination:** `TextMentionTermination("APPROVED", sources=["Reviewer"]) | MaxMessageTermination(12)`.

### Routing (selector_func)
```
user/follow-up -> Planner -> Coder -> Executor --error--> Coder
                                              --ok-----> Reviewer --feedback--> Coder
                                                                  --APPROVED--> stop -> human
```

## 4. Context for the implementer
- AutoGen **0.7.x** (`autogen-agentchat`, `autogen-ext[openai]`); model via `OpenAIChatCompletionClient` (default `gpt-4o-mini`, `temperature=0`).
- Uploaded data is staged as `data.csv` in a per-session folder `data/runtime/sessions/<uuid>/`; all code runs with that folder as cwd.
- Coder must emit **one** ```python block starting with `# filename: analysis.py`, so the executor saves it under that name.
- Executor reads code only from `Coder` messages (`sources=["Coder"]`), and an `approval_func` static safety gate rejects imports outside pandas/numpy/matplotlib/stdlib-math, `os.environ`, `subprocess`, `exec`, absolute or `..` paths.
- Team state is saved with `team.save_state()` into SQLite after each run, so follow-up questions resume the same conversation (even after a restart).
- Money: Indian format, `Rs`, lakh (L) = 1e5, crore (Cr) = 1e7.

## 5. Sample
Input: `data/sample/sales_2026.csv` (12,480 rows; `order_date,region,category,product,units,unit_price,discount`).
Question: *Which category had the biggest revenue drop in September vs August, and which region caused most of it?*
Expected shape of the answer:
```
ANSWER
Electronics had the biggest drop: revenue fell from Rs 52.6 L in August to Rs 35.9 L in September (down 31.8%).
WHERE IT CAME FROM
South region caused Rs 9.1 L of the Rs 16.8 L drop (54%). Earbuds X2 and Smartwatch Lite explain most of it.
FILES
category_trend.png | region_breakdown.png | analysis.py
SUGGESTED NEXT QUESTION
Did discounts on Earbuds X2 change between August and September?
```

## 6. Done checklist (validation)
| # | Requirement | How it is verified |
|---|---|---|
| 1 | At least one run shows the agents fixing a code error on their own | `backend/tests/test_team_replay.py::test_self_correction_loop_end_to_end`, `scripts/smoke_test.py`; the UI badges the error and the **FIXED** code |
| 2 | Code runs only inside the sandbox folder or Docker container | `sandbox` container (no secrets, internal network, read-only FS); `test_sandbox.py`, `test_safety.py` |
| 3 | Run stops on APPROVED or after 12 messages, never loops forever | `test_stops_after_12_messages_without_approval` |
| 4 | Running the saved analysis.py again gives exactly the same numbers | `AnalysisSession.reproduce()`; UI "Reproducibility check"; asserted in the tests |
| 5 | Every chart has a title, axis labels and units | Coder prompt rule + Reviewer checklist item 3 |
| 6 | Human approval works, and a follow-up continues the same session | Approve/Reject buttons + follow-up chat; CLI `UserProxyAgent`; follow-up asserted in the replay test |

## 7. Stretch goals
- [x] `SelectorGroupChat` so the next speaker is picked at run time
- [x] Excel files with multiple sheets (pick one, or stack all with a `sheet` column)
- [x] Export answer + charts as a one-page PDF report
