"""Session orchestration: stage data, run the team, stream events, persist everything.

One AnalysisSession = one uploaded dataset + one sandbox folder + one AutoGen team
whose state is saved after every run, so follow-up questions continue the same
conversation (even after an app restart).
"""

from __future__ import annotations

import inspect
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import pandas as pd
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseChatMessage
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_core.models import ChatCompletionClient

from database import Database

from . import prompts
from .config import settings
from .data_loader import DATA_FILE_NAME, profile, stage_dataset
from .formatting import detect_currency, reporting_standard
from .executors import make_executor
from .team import APPROVED, CODER, EXECUTOR, PLANNER, REVIEWER, build_team, execution_failed, is_approved, make_model_client

SCRIPT_NAME = "analysis.py"


@dataclass
class AgentEvent:
    seq: int
    source: str
    kind: str  # task | plan | code | exec_ok | exec_error | feedback | approved | other
    content: str
    elapsed_s: float = 0.0


@dataclass
class RunResult:
    run_no: int
    question: str
    status: str  # approved | limit | error
    stop_reason: str | None
    answer: str | None
    n_messages: int
    n_exec_errors: int
    n_feedback: int = 0
    duration_s: float = 0.0
    reproducible: bool | None = None
    charts: list[Path] = field(default_factory=list)
    script: Path | None = None
    events: list[AgentEvent] = field(default_factory=list)


EventCallback = Callable[[AgentEvent], Awaitable[None] | None]


def classify(source: str, text: str) -> str:
    if source == PLANNER:
        return "plan"
    if source == CODER:
        return "code"
    if source == EXECUTOR:
        return "exec_error" if execution_failed(text) else "exec_ok"
    if source == REVIEWER:
        return "approved" if is_approved(text) else "feedback"
    if source == "user":
        return "task"
    return "other"


def strip_approved(text: str) -> str:
    text = text.rstrip()
    return text[: -len(APPROVED)].rstrip() if text.endswith(APPROVED) else text


class AnalysisSession:
    def __init__(self, db: Database, session_id: str, dataset_name: str, data_profile: str,
                 team_state: dict | None = None, *, currency: str = "USD", number_style: str = "international",
                 sample_id: str | None = None, rows: int | None = None, cols: int | None = None):
        self.db = db
        self.id = session_id
        self.dataset_name = dataset_name
        self.profile = data_profile
        self.team_state = team_state
        self.currency = currency or "USD"
        self.number_style = number_style or "international"
        self.sample_id = sample_id
        self.rows = rows
        self.cols = cols
        self.work_dir = settings.sessions_dir / session_id

    # ---- construction ---------------------------------------------------
    @classmethod
    def create(cls, db: Database, df: pd.DataFrame, dataset_name: str, *, currency: str | None = None,
               number_style: str = "international", sample_id: str | None = None) -> "AnalysisSession":
        session_id = uuid.uuid4().hex
        work_dir = settings.sessions_dir / session_id
        stage_dataset(df, work_dir)
        data_profile = profile(df)
        currency = currency or detect_currency(df.columns) or "USD"
        db.create_session(session_id, dataset_name, len(df), data_profile, cols=len(df.columns),
                          sample_id=sample_id, currency=currency, number_style=number_style)
        return cls(db, session_id, dataset_name, data_profile, currency=currency, number_style=number_style,
                   sample_id=sample_id, rows=len(df), cols=len(df.columns))

    @classmethod
    def load(cls, db: Database, session_id: str) -> "AnalysisSession | None":
        row = db.get_session(session_id)
        if not row:
            return None
        return cls(db, session_id, row["dataset_name"], row["data_profile"], row["team_state"],
                   currency=row.get("currency"), number_style=row.get("number_style"), sample_id=row.get("sample_id"),
                   rows=row.get("dataset_rows"), cols=row.get("dataset_cols"))

    @property
    def standard(self) -> str:
        return reporting_standard(self.currency, self.number_style)

    # ---- running --------------------------------------------------------
    def _task_text(self, question: str, run_no: int) -> str:
        if run_no == 1 or not self.team_state:
            return prompts.TASK_TEMPLATE.format(question=question, file_name=DATA_FILE_NAME, profile=self.profile,
                                                standard=self.standard)
        return prompts.FOLLOW_UP_TEMPLATE.format(question=question, file_name=DATA_FILE_NAME)

    async def ask(self, question: str, on_event: EventCallback | None = None,
                  model_client: ChatCompletionClient | None = None) -> RunResult:
        run_no = self.db.next_run_no(self.id)
        self.db.start_run(self.id, run_no, question)
        started = time.time()

        own_client = model_client is None
        client = model_client or make_model_client()
        executor = make_executor(self.id, self.work_dir)
        await executor.start()
        team = build_team(client, executor)
        if self.team_state:
            await team.load_state(self.team_state)

        events: list[AgentEvent] = []
        stop_reason: str | None = None
        status = "error"
        try:
            async for item in team.run_stream(task=self._task_text(question, run_no)):
                if isinstance(item, TaskResult):
                    stop_reason = item.stop_reason
                    continue
                if not isinstance(item, BaseChatMessage):
                    continue  # streaming chunks / internal events
                text = item.to_text()
                ev = AgentEvent(len(events) + 1, item.source, classify(item.source, text), text,
                                round(time.time() - started, 1))
                events.append(ev)
                self.db.add_message(self.id, run_no, ev.seq, ev.source, ev.kind, ev.content, ev.elapsed_s)
                if on_event:
                    res = on_event(ev)
                    if inspect.isawaitable(res):
                        await res
            status = "approved" if events and events[-1].kind == "approved" else "limit"
        except Exception as e:  # surface API/network errors to the UI instead of crashing
            stop_reason = f"{type(e).__name__}: {e}"
            raise
        finally:
            self.team_state = await team.save_state()
            self.db.save_team_state(self.id, self.team_state)
            await executor.stop()
            if own_client:
                await client.close()
            answer = strip_approved(events[-1].content) if status == "approved" else None
            n_errors = sum(1 for e in events if e.kind == "exec_error")
            n_feedback = sum(1 for e in events if e.kind == "feedback")
            duration = round(time.time() - started, 1)
            model = settings.model if own_client else "replay"
            self.db.finish_run(self.id, run_no, status=status, stop_reason=stop_reason, answer=answer,
                               n_messages=len(events), n_exec_errors=n_errors, n_feedback=n_feedback,
                               model=model, duration_s=duration)

        charts, script = self._snapshot(run_no, since=started - 1)
        reproducible = None
        if status == "approved" and script:
            reproducible, _ = await self.reproduce(run_no)
        return RunResult(
            run_no=run_no, question=question, status=status, stop_reason=stop_reason, answer=answer,
            n_messages=len(events), n_exec_errors=n_errors, n_feedback=n_feedback, duration_s=duration,
            reproducible=reproducible, charts=charts, script=script, events=events,
        )

    # ---- artifacts ------------------------------------------------------
    def run_dir(self, run_no: int) -> Path:
        return self.work_dir / "outputs" / f"run_{run_no}"

    def _snapshot(self, run_no: int, since: float) -> tuple[list[Path], Path | None]:
        """Copy this run's charts + analysis.py to outputs/run_N so follow-ups don't overwrite them."""
        out = self.run_dir(run_no)
        out.mkdir(parents=True, exist_ok=True)
        for png in self.work_dir.glob("*.png"):
            if png.stat().st_mtime >= since:
                shutil.copy2(png, out / png.name)
        script = self.work_dir / SCRIPT_NAME
        if script.exists() and script.stat().st_mtime >= since:
            shutil.copy2(script, out / SCRIPT_NAME)
        return self.artifacts(run_no)

    def artifacts(self, run_no: int) -> tuple[list[Path], Path | None]:
        out = self.run_dir(run_no)
        charts = sorted(out.glob("*.png"), key=lambda p: p.stat().st_mtime) if out.exists() else []
        script = out / SCRIPT_NAME
        return charts, script if script.exists() else None

    def last_exec_output(self, run_no: int | None = None) -> str | None:
        msgs = [m for m in self.db.get_messages(self.id)
                if m["kind"] == "exec_ok" and (run_no is None or m["run_no"] == run_no)]
        return msgs[-1]["content"] if msgs else None

    async def reproduce(self, run_no: int | None = None) -> tuple[bool, str]:
        """Re-run a run's saved analysis.py in the sandbox and compare with what the Executor printed."""
        if run_no is None:
            runs = self.db.get_runs(self.id)
            run_no = runs[-1]["run_no"] if runs else 1
        _, script = self.artifacts(run_no)
        if script is None:
            return False, "analysis.py not found"
        executor = make_executor(self.id, self.work_dir)
        await executor.start()
        try:
            result = await executor.execute_code_blocks(
                [CodeBlock(code=script.read_text(encoding="utf-8"), language="python")], CancellationToken()
            )
        finally:
            await executor.stop()
        same = _normalise(result.output) == _normalise(self.last_exec_output(run_no) or "")
        self.db.set_reproducible(self.id, run_no, same)
        return same, result.output


def _normalise(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())
