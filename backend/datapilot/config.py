"""Runtime settings, read once from environment variables (and an optional .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader so local runs work without extra dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))

    # Safety limits from the spec: stop on APPROVED or after 12 messages.
    max_messages: int = field(default_factory=lambda: _int("MAX_MESSAGES", 12))
    code_timeout_s: int = field(default_factory=lambda: _int("CODE_TIMEOUT_SECONDS", 60))

    # "local"  -> run code in a per-session folder on this machine (dev only)
    # "sandbox" -> send code to the isolated sandbox container (production)
    executor_mode: str = field(default_factory=lambda: os.environ.get("EXECUTOR_MODE", "local").lower())
    sandbox_url: str = field(default_factory=lambda: os.environ.get("SANDBOX_URL", "http://sandbox:8800"))
    sandbox_token: str = field(default_factory=lambda: os.environ.get("SANDBOX_TOKEN", ""))

    runtime_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("RUNTIME_DIR", ROOT_DIR / "data" / "runtime")).resolve()
    )
    db_path: Path = field(
        default_factory=lambda: Path(os.environ.get("DB_PATH", ROOT_DIR / "data" / "datapilot.db")).resolve()
    )
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 50))
    app_password: str = field(default_factory=lambda: os.environ.get("APP_PASSWORD", ""))

    @property
    def sessions_dir(self) -> Path:
        return self.runtime_dir / "sessions"


settings = Settings()
