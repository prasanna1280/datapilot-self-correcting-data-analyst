# Architecture

## Components
| Layer | Folder | Responsibility |
|---|---|---|
| Frontend | `frontend/` | Streamlit pages (Workspace, Sample datasets, Run history, How it works): sign-in, upload, live 6-step tracker, answer, charts, downloads, approve / follow-up |
| Agent engine | `backend/datapilot/` | Builds the AutoGen team, runs it, classifies and persists every message |
| Sandbox | `backend/sandbox/` | Stand-alone HTTP service that executes Python with no secrets and no network |
| Database | `database/` | SQLite: `sessions` (incl. AutoGen team state), `runs`, `messages` |

## Request flow
1. **Upload**: `data_loader.read_upload()` reads CSV/Excel → `stage_dataset()` writes `sessions/<id>/data.csv` → `profile()` builds the column summary.
2. **Ask**: `AnalysisSession.ask()` builds the model client, executor and team, then loads saved team state for follow-ups.
3. **Loop**: `team.run_stream()` yields messages. `select_next_speaker()` routes:
   - `user → Planner → Coder → Executor`
   - Executor error → **Coder** (self-correction); ok → Reviewer
   - Reviewer feedback → **Coder**; `APPROVED` → termination
4. **Termination**: `TextMentionTermination("APPROVED", sources=["Reviewer"]) | FunctionalTermination(reviewer_approved) | MaxMessageTermination(12)`. The functional check also stops on a complete Reviewer answer whose `APPROVED` line was left off.
5. **Persist**: each message → `messages`; result → `runs`; `team.save_state()` → `sessions.team_state`; charts + `analysis.py` snapshot → `outputs/run_N/`.
6. **Human**: the UI shows the answer with Approve / Reject (`runs.human_verdict`). A follow-up question starts a new run on the same team state.

## Execution safety (defence in depth)
1. `CodeExecutorAgent(sources=["Coder"])`: only the Coder's code is executed.
2. `approval_func=safety.approve_code`: AST check that rejects non-whitelisted imports, `exec/eval`, `os.environ`, `subprocess`, file deletion, pickle/SQL, and absolute or `..` paths. A rejection goes back to the Coder like any error.
3. Sandbox container: separate image with only pandas/numpy/matplotlib; **no env secrets**; `internal` Docker network (no internet); read-only root FS; writable only `/data/runtime/sessions` and a 64 MB `/tmp`; `cap_drop: ALL`; `no-new-privileges`; 1 CPU, 1 GB RAM, 128 pids; per-script timeout; child process runs `python -I` with a minimal env; session id and filename validated (no path traversal); shared-token auth.
4. Local dev mode (`EXECUTOR_MODE=local`) uses AutoGen's `LocalCommandLineCodeExecutor` confined to the session folder.

## Access control
When `APP_PASSWORD` is set, `frontend/app.py` shows a sign-in form before any page runs.
- The password is compared with `hmac.compare_digest`.
- On success, a `dp_auth` cookie is set in the browser: `<expiry>.<HMAC-SHA256(APP_PASSWORD, "dp_auth:<expiry>")>`, valid for 7 days (`AUTH_DAYS`), `SameSite=Strict`, `Secure` over HTTPS. The password itself is never stored.
- Streamlit's `session_state` is lost on every page reload, so each new session reads the cookie (`st.context.cookies`) and checks the signature and expiry.
- **Sign out** clears the cookie. Changing `APP_PASSWORD` invalidates every cookie, because the signing key changes.
- The sandbox is not reachable from outside, so it doesn't need this sign-in. It accepts only calls from the app that carry `SANDBOX_TOKEN`.

## Why SelectorGroupChat + selector_func?
RoundRobin speaks in a fixed order, so an Executor error would go to the Reviewer, not the Coder.
A `selector_func` makes the loop deterministic, cheap (no extra LLM call to pick a speaker) and
testable, while the LLM selector stays as a fallback for unexpected states.
