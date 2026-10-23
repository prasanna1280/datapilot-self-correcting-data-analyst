"""Copy selected settings from the local .env to the VPS .env, then restart the app.

    python scripts/push_env.py                       # pushes the default keys below
    python scripts/push_env.py APP_PASSWORD          # push only some keys
    python scripts/push_env.py --host roaster-vps --path /opt/apps/datapilot

Values travel over SSH stdin (never on the command line) and are never printed.
Keys that are empty in the local .env are skipped, so a blank local OPENAI_API_KEY
won't wipe the server's key.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEYS = ["OPENAI_API_KEY", "OPENAI_MODEL", "APP_PASSWORD", "MAX_MESSAGES", "CODE_TIMEOUT_SECONDS"]

# Runs on the VPS: merge KEY=VALUE lines from stdin into .env, keep everything else.
REMOTE_MERGE = r"""
import os, sys
updates = dict(l.split("=", 1) for l in sys.stdin.read().splitlines() if "=" in l)
lines = open(".env").read().splitlines() if os.path.exists(".env") else []
out, seen = [], set()
for l in lines:
    k = l.split("=", 1)[0].strip()
    if k in updates:
        out.append(f"{k}={updates[k]}"); seen.add(k)
    else:
        out.append(l)
out += [f"{k}={v}" for k, v in updates.items() if k not in seen]
os.umask(0o077)
open(".env.tmp", "w").write("\n".join(out) + "\n")
os.replace(".env.tmp", ".env")
print("updated:", ", ".join(sorted(updates)))
"""


def read_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.split(" #")[0].strip().strip('"').strip("'")
    return env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*", default=DEFAULT_KEYS)
    ap.add_argument("--host", default="roaster-vps")
    ap.add_argument("--path", default="/opt/apps/datapilot")
    ap.add_argument("--no-restart", action="store_true")
    args = ap.parse_args()

    local = read_env(ROOT / ".env")
    updates = {k: local[k] for k in args.keys if local.get(k)}
    skipped = [k for k in args.keys if not local.get(k)]
    if skipped:
        print("skipped (empty or missing locally):", ", ".join(skipped))
    if not updates:
        print("nothing to push")
        return 1

    payload = "".join(f"{k}={v}\n" for k, v in updates.items())
    restart = "" if args.no_restart else " && docker compose up -d app 2>&1 | tail -1"
    remote = f"cd {args.path} && python3 -c '{REMOTE_MERGE}'{restart}"
    return subprocess.run(["ssh", "-o", "BatchMode=yes", args.host, remote], input=payload, text=True).returncode


if __name__ == "__main__":
    sys.exit(main())
