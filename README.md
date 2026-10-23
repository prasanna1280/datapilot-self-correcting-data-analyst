# 📊 DataPilot: Self-Correcting Data Analyst

Ask a business question in plain English. A team of **AutoGen** agents plans, writes Python,
runs it in a sandbox, **fixes its own errors**, gets reviewed, and returns the answer with charts.

**Live:** https://datapilot.prasanna.digital · Track 3 Agentic AI · AutoGen · Use case 03

```
01 Ask  ->  02 Plan  ->  03 Code  ->  04 Run  ->  05 Review  ->  06 Answer
                          ^             |            |
                          +---error-----+            |
                          +---feedback---------------+
```

## Features
- **Planner / Coder / Executor / Reviewer** agents plus a human approval step (User Proxy)
- **Self-correction loop**: errors and reviewer feedback go back to the Coder automatically
- **Safety**: stops on `APPROVED` or after **12 messages**. Code runs in an isolated sandbox container with no API keys, no internet, a read-only FS and CPU/RAM limits, after a static safety check
- **Outputs**: written answer, PNG charts, re-runnable `analysis.py`, **one-page PDF report**
- **Follow-up questions** continue the same session (team state persisted in SQLite)
- **CSV and multi-sheet Excel** uploads (pick a sheet, or stack them all)
- `SelectorGroupChat` with deterministic routing (stretch goal); `TEAM_MODE=roundrobin` for the basic version

## Project structure
```
frontend/            Streamlit chat UI (app.py, components.py)
backend/
  datapilot/         Agent engine: config, prompts, team, executors, safety, runner, report, cli
  sandbox/           Isolated code-execution service + Dockerfile
  tests/             pytest suite (replay model: no API key needed)
database/            SQLite schema + data access (sessions, runs, messages)
data/sample/         sales_2026.csv (12,480 rows) + sales_2026.xlsx (4 sheets)
scripts/             generate_sample_data.py, smoke_test.py
PRPs/                Product Requirement Prompts (core + deployment)
docs/                ARCHITECTURE.md, DEPLOYMENT.md, TESTING.md
Dockerfile, docker-compose.yml   app + sandbox containers, Traefik labels
```

## Quick start (local, no Docker)
```bash
python -m venv .venv && .venv\Scripts\activate        # Windows  (source .venv/bin/activate on Linux/Mac)
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env                                  # then set OPENAI_API_KEY
python -m pytest                                        # 30 tests, no API key needed
python scripts/smoke_test.py                            # scripted error -> fix -> APPROVED run
streamlit run frontend/app.py                           # http://localhost:8501
```
CLI with a real `UserProxyAgent`:
```bash
python -m backend.datapilot.cli data/sample/sales_2026.csv "Which category had the biggest revenue drop in September vs August, and which region caused most of it?"
```

## Production (Docker on the VPS)
```bash
cp .env.example .env    # set OPENAI_API_KEY, DOMAIN, SANDBOX_TOKEN, APP_PASSWORD
docker compose up -d --build
docker compose exec app python scripts/smoke_test.py
```
See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Done checklist
| | Requirement | Where |
|---|---|---|
| ✅ | Agents fix a code error on their own | `test_team_replay.py`, `smoke_test.py`, UI **ERROR → FIXED** badges |
| ✅ | Code runs only in the sandbox folder / Docker container | `backend/sandbox`, `safety.py` |
| ✅ | Stops on APPROVED or after 12 messages | `team.make_termination`, `test_stops_after_12_messages_without_approval` |
| ✅ | Re-running analysis.py gives the same numbers | UI *Reproducibility check*, `AnalysisSession.reproduce()` |
| ✅ | Every chart has title, axis labels, units | Coder rules + Reviewer checklist |
| ✅ | Human approval + follow-up in the same session | Approve/Reject buttons, chat follow-ups, CLI `UserProxyAgent` |

## Tech stack
AutoGen 0.7 (`autogen-agentchat`, `autogen-ext[openai]`) · OpenAI `gpt-4.1` · Streamlit · pandas · matplotlib · SQLite · fpdf2 · Docker · Traefik + Let's Encrypt
