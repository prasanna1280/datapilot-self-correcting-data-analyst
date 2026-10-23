# PRP-002 — Deployment: Docker on Hostinger VPS behind HTTPS

| Field | Value |
|---|---|
| Depends on | PRP-001 |
| Target | Hostinger VPS (Ubuntu 24.04, Docker 29, Compose v5) |
| Edge | Existing Traefik (host network, Let's Encrypt HTTP-01) |
| Status | ✅ Implemented |

## Goal
Run DataPilot at `https://<subdomain>` with a valid TLS certificate, auto-restart,
persistent sessions, and AI-written code isolated from secrets and the internet.

## Architecture
```
Internet --443--> Traefik (host network, TLS via Let's Encrypt)
                     |
                     v  datapilot_default network
               datapilot-app  (Streamlit + AutoGen, has OPENAI_API_KEY)
                     |  HTTP + shared token, sandbox_net (internal: no internet)
                     v
               datapilot-sandbox (python + pandas/matplotlib only; no secrets,
                                  read-only FS, cap_drop ALL, 1 CPU / 1 GB / 128 pids)
     shared volume `runtime` -> /data/runtime/sessions/<id>  (data.csv, analysis.py, *.png)
     app-only volume `db`    -> /data/db/datapilot.db        (SQLite)
```

## Access control
A public URL must not spend the OpenAI budget, so `APP_PASSWORD` gates the whole app.
- **Requirement:** after signing in, users stay signed in across page refreshes and deep links for 7 days. Streamlit's `session_state` alone is lost on every reload.
- **Design:** a `dp_auth` cookie `<expiry>.<HMAC-SHA256(APP_PASSWORD, "dp_auth:<expiry>")>` with `SameSite=Strict`, plus `Secure` over HTTPS. It never contains the password.
- **Sign out** clears the cookie; rotating `APP_PASSWORD` (`scripts/push_env.py APP_PASSWORD`) invalidates all cookies.
- Details: `docs/ARCHITECTURE.md` → Access control.

## Steps
1. DNS: `A` record `<subdomain>` → VPS IP (Traefik needs it for the HTTP-01 challenge).
2. `git clone` the repo to `/opt/apps/datapilot`.
3. Create `.env` from `.env.example` (`OPENAI_API_KEY`, `DOMAIN`, random `SANDBOX_TOKEN`, optional `APP_PASSWORD`).
4. `docker compose up -d --build`.
5. Validate: `docker compose ps` (both healthy), `docker compose exec app python scripts/smoke_test.py`, `curl -I https://<domain>`.

## Validation
- Both containers `healthy`; restart policy `unless-stopped`.
- Smoke test prints `SMOKE TEST PASSED` with `executor=sandbox`.
- `docker compose exec sandbox python -c "import urllib.request;urllib.request.urlopen('https://api.openai.com')"` **fails** (no internet from the sandbox).
- `https://<domain>` serves a valid Let's Encrypt certificate; `http://` redirects to `https://`.
- Sign-in: refreshing and opening `/history` stay signed in; **Sign out** + refresh shows the form again (`docs/TESTING.md` → Sign-in). Passed on 23 Oct 2026.

## Rollback
`git checkout <previous tag> && docker compose up -d --build`. Data volumes are untouched.
