"""Code executors used by the Executor agent.

- local:   AutoGen's LocalCommandLineCodeExecutor, confined to a per-session folder.
           Good for development on your own machine.
- sandbox: SandboxCodeExecutor sends the code to the separate `sandbox` container
           (backend/sandbox/server.py). That container has no API keys, no internet,
           a read-only filesystem except the session folder, and CPU/memory limits.
"""

from __future__ import annotations

import asyncio
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import List

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.code_executors._common import CommandLineCodeResult

from .config import settings

_FILENAME_RE = re.compile(r"^\s*#\s*filename:\s*([A-Za-z0-9_\-]+\.py)\s*$", re.MULTILINE)
MAX_OUTPUT_CHARS = 6000


def filename_for(code: str, default: str = "analysis.py") -> str:
    m = _FILENAME_RE.search("\n".join(code.strip().splitlines()[:3]))
    return m.group(1) if m else default


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... [{len(text) - limit} chars truncated] ...\n{text[-half:]}"


class SandboxCodeExecutor(CodeExecutor):
    """Runs Python code blocks inside the sandbox container over HTTP."""

    def __init__(self, session_id: str, work_dir: Path, base_url: str, token: str = "", timeout: int = 60):
        super().__init__()
        self.session_id = session_id
        self.work_dir = work_dir
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}/execute",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-Sandbox-Token": self.token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout + 15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"exit_code": 1, "output": f"Sandbox rejected the request ({e.code}): {e.read().decode()[:500]}"}
        except (urllib.error.URLError, TimeoutError) as e:
            return {"exit_code": 1, "output": f"Sandbox unavailable: {e}"}

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CommandLineCodeResult:
        outputs: list[str] = []
        exit_code = 0
        code_file = None
        for block in code_blocks:
            if block.language.lower() not in ("python", "py", "python3"):
                outputs.append(f"Unsupported language '{block.language}'. Only python is allowed.")
                exit_code = 1
                break
            code_file = filename_for(block.code)
            result = await asyncio.to_thread(
                self._post,
                {"session_id": self.session_id, "filename": code_file, "code": block.code, "timeout": self.timeout},
            )
            outputs.append(result.get("output", ""))
            exit_code = int(result.get("exit_code", 1))
            if exit_code != 0:
                break
        return CommandLineCodeResult(
            exit_code=exit_code,
            output=truncate("\n".join(outputs)),
            code_file=str(self.work_dir / code_file) if code_file else None,
        )

    async def start(self) -> None:  # stateless HTTP client
        return None

    async def stop(self) -> None:
        return None

    async def restart(self) -> None:
        return None


def make_executor(session_id: str, work_dir: Path) -> CodeExecutor:
    work_dir.mkdir(parents=True, exist_ok=True)
    if settings.executor_mode == "sandbox":
        return SandboxCodeExecutor(
            session_id=session_id,
            work_dir=work_dir,
            base_url=settings.sandbox_url,
            token=settings.sandbox_token,
            timeout=settings.code_timeout_s,
        )
    # cleanup_temp_files=False keeps analysis.py on disk so the user can download and re-run it.
    return LocalCommandLineCodeExecutor(
        work_dir=work_dir, timeout=settings.code_timeout_s, cleanup_temp_files=False
    )
