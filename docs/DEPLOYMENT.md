# Deployment: Hostinger VPS + Docker + HTTPS

The VPS already runs **Traefik** (host network, ports 80/443, Let's Encrypt HTTP-01,
automatic HTTP→HTTPS redirect). DataPilot joins it via Docker labels; no nginx/certbot needed.

## 1. DNS (Hostinger hPanel → Domains → prasanna.digital → DNS)
| Type | Name | Value | TTL |
|---|---|---|---|
| A | datapilot | 200.234.47.90 | 300 |

## 2. First deploy
```bash
ssh roaster-vps
git clone https://github.com/prasanna1280/datapilot-self-correcting-data-analyst.git /opt/apps/datapilot
cd /opt/apps/datapilot
cp .env.example .env && nano .env
#   OPENAI_API_KEY=sk-...
#   DOMAIN=datapilot.prasanna.digital
#   SANDBOX_TOKEN=$(openssl rand -hex 24)
#   APP_PASSWORD=<choose one>
#   EXECUTOR_MODE=sandbox
docker compose up -d --build
docker compose ps                                   # app + sandbox: healthy
docker compose exec app python scripts/smoke_test.py
```
Traefik requests the certificate on the first HTTPS hit (DNS must already point at the VPS).

## 3. Update
```bash
cd /opt/apps/datapilot && git pull && docker compose up -d --build
```

## 4. Change secrets from your PC
Edit the local `.env` (git-ignored), then push selected keys to the VPS and restart the app:
```bash
python scripts/push_env.py                  # OPENAI_API_KEY, OPENAI_MODEL, APP_PASSWORD, MAX_MESSAGES, CODE_TIMEOUT_SECONDS
python scripts/push_env.py APP_PASSWORD     # only the password
```
Values go over SSH stdin and are never printed; keys that are empty locally are skipped.

## 5. Operations
| Task | Command |
|---|---|
| Logs | `docker compose logs -f app` / `docker compose logs -f sandbox` |
| Restart | `docker compose restart` |
| Back up DB | `docker compose cp app:/data/db/datapilot.db ./backup.db` |
| Remove the password | blank `APP_PASSWORD` in `.env`, then `docker compose up -d` |
| Verify sandbox has no internet | `docker compose exec sandbox python -c "import urllib.request as u;u.urlopen('https://example.com',timeout=5)"` → must fail |

The app is also bound to `127.0.0.1:8510` on the VPS for local debugging (`ssh -L 8510:localhost:8510 roaster-vps`).
