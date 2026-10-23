"""SQLite persistence: sessions, runs (one per question) and the full agent conversation."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- sessions -------------------------------------------------------
    def create_session(self, session_id: str, dataset_name: str, rows: int, profile: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO sessions (id, dataset_name, dataset_rows, data_profile) VALUES (?, ?, ?, ?)",
                (session_id, dataset_name, rows, profile),
            )

    def save_team_state(self, session_id: str, state: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute("UPDATE sessions SET team_state = ? WHERE id = ?", (json.dumps(state, default=str), session_id))

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        out = dict(row)
        out["team_state"] = json.loads(out["team_state"]) if out["team_state"] else None
        return out

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT s.id, s.created_at, s.dataset_name, COUNT(r.id) AS n_runs,
                          (SELECT question FROM runs WHERE session_id = s.id ORDER BY run_no LIMIT 1) AS first_question
                   FROM sessions s LEFT JOIN runs r ON r.session_id = s.id
                   GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- runs -----------------------------------------------------------
    def next_run_no(self, session_id: str) -> int:
        with self._conn() as c:
            (n,) = c.execute("SELECT COALESCE(MAX(run_no), 0) FROM runs WHERE session_id = ?", (session_id,)).fetchone()
        return n + 1

    def start_run(self, session_id: str, run_no: int, question: str) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO runs (session_id, run_no, question) VALUES (?, ?, ?)", (session_id, run_no, question))

    def finish_run(self, session_id: str, run_no: int, *, status: str, stop_reason: str | None,
                   answer: str | None, n_messages: int, n_exec_errors: int) -> None:
        with self._conn() as c:
            c.execute(
                """UPDATE runs SET finished_at = datetime('now'), status = ?, stop_reason = ?, answer = ?,
                          n_messages = ?, n_exec_errors = ? WHERE session_id = ? AND run_no = ?""",
                (status, stop_reason, answer, n_messages, n_exec_errors, session_id, run_no),
            )

    def set_human_verdict(self, session_id: str, run_no: int, verdict: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE runs SET human_verdict = ? WHERE session_id = ? AND run_no = ?",
                      (verdict, session_id, run_no))

    def get_runs(self, session_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM runs WHERE session_id = ? ORDER BY run_no", (session_id,)).fetchall()
        return [dict(r) for r in rows]

    # ---- messages -------------------------------------------------------
    def add_message(self, session_id: str, run_no: int, seq: int, source: str, kind: str, content: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO messages (session_id, run_no, seq, source, kind, content) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, run_no, seq, source, kind, content),
            )

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT run_no, seq, source, kind, content FROM messages WHERE session_id = ? ORDER BY run_no, seq",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]
