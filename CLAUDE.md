# CLAUDE.md

Guidance for AI coding assistants working in this repo.

- Python 3.12, AutoGen **0.7.x** API (`autogen_agentchat`, `autogen_ext`). Do not use the legacy `pyautogen` 0.2 API.
- Run `python -m pytest` before committing; tests use `ReplayChatCompletionClient`, so no API key is needed.
- Imports are rooted at the repo (`backend.datapilot...`, `database`); `pytest.ini` sets `pythonpath = .`.
- Agent names (`Planner`, `Coder`, `Executor`, `Reviewer`) are referenced by the selector, termination and UI. Rename them everywhere or nowhere.
- If you allow a new library in AI-written code, update `backend/datapilot/safety.py` ALLOWED_IMPORTS **and** `backend/sandbox/requirements.txt`.
- Never put secrets in the sandbox service's environment (`docker-compose.yml` → `sandbox`).
- Sign-in (`frontend/app.py`): `session_state` is lost on page reload, so auth persists in a `dp_auth` cookie signed with HMAC-SHA256 keyed on `APP_PASSWORD` (7 days, `AUTH_DAYS`). Never store the password or anything reversible in the cookie, and keep `sign_in()` running before any page. The browser check is in `docs/TESTING.md` → Sign-in.
- Never commit `.env` or print secret values (`OPENAI_API_KEY`, `APP_PASSWORD`, `SANDBOX_TOKEN`); push them to the VPS with `scripts/push_env.py`.
- Specs live in `PRPs/`; architecture in `docs/ARCHITECTURE.md`.
