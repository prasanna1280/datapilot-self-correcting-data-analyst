"""DataPilot code sandbox: a tiny HTTP service that runs AI-written Python.

It is deployed as its own container with:
  - no API keys or secrets in its environment,
  - no internet (docker `internal` network),
  - read-only root filesystem; only /workspace/sessions is writable,
  - non-root user, CPU / memory / pids limits (see docker-compose.yml).

POST /execute  {"session_id": "...", "filename": "analysis.py", "code": "...", "timeout": 60}
  -> {"exit_code": 0, "output": "..."}
GET  /health   -> {"ok": true}

Standard library only, so the image stays small.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WORKSPACE = Path(os.environ.get("SANDBOX_WORKSPACE", "/workspace/sessions")).resolve()
TOKEN = os.environ.get("SANDBOX_TOKEN", "")
MAX_TIMEOUT = int(os.environ.get("SANDBOX_MAX_TIMEOUT", "120"))
MAX_CODE_BYTES = 200_000
MAX_OUTPUT_CHARS = 8000

SESSION_RE = re.compile(r"^[a-f0-9]{8,64}$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}\.py$")

# Minimal environment for the child process: nothing secret, matplotlib cache in /tmp.
CHILD_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp",
    "MPLCONFIGDIR": "/tmp/matplotlib",
    "MPLBACKEND": "Agg",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "LANG": "C.UTF-8",
}
if os.name == "nt":  # lets the unit tests run on a Windows dev machine
    CHILD_ENV.update({"SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"), "PATH": os.environ.get("PATH", "")})


def run_code(session_id: str, filename: str, code: str, timeout: int) -> dict:
    if not SESSION_RE.match(session_id):
        return {"exit_code": 1, "output": "invalid session id"}
    if not FILENAME_RE.match(filename):
        return {"exit_code": 1, "output": "invalid filename"}
    work_dir = (WORKSPACE / session_id).resolve()
    if WORKSPACE not in work_dir.parents or not work_dir.is_dir():
        return {"exit_code": 1, "output": "session folder not found"}

    script = work_dir / filename
    script.write_text(code, encoding="utf-8")
    timeout = max(1, min(int(timeout), MAX_TIMEOUT))
    try:
        proc = subprocess.run(
            [sys.executable, "-I", filename],  # -I: isolated mode, ignores PYTHON* env and user site
            cwd=work_dir,
            env=CHILD_ENV,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        output, exit_code = f"Timeout: script exceeded {timeout}s and was stopped.", 124
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[: MAX_OUTPUT_CHARS // 2] + "\n...[truncated]...\n" + output[-MAX_OUTPUT_CHARS // 2 :]
    return {"exit_code": exit_code, "output": output}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            return self._send(404, {"error": "not found"})
        if TOKEN and self.headers.get("X-Sandbox-Token") != TOKEN:
            return self._send(401, {"error": "bad token"})
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_CODE_BYTES:
            return self._send(413, {"error": "payload too large or empty"})
        try:
            req = json.loads(self.rfile.read(length))
            result = run_code(str(req["session_id"]), str(req["filename"]), str(req["code"]), int(req.get("timeout", 60)))
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            return self._send(400, {"error": f"bad request: {e}"})
        self._send(200, result)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("sandbox: " + fmt % args + "\n")


def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("SANDBOX_PORT", "8800"))
    print(f"sandbox listening on :{port}, workspace={WORKSPACE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
