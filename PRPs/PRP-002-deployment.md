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

## Rollback
`git checkout <previous tag> && docker compose up -d --build`. Data volumes are untouched.
