"""Terminal version of DataPilot with a real AutoGen UserProxyAgent as the human.

    python -m backend.datapilot.cli data/sample/sales_2026.csv \
        "Which category had the biggest revenue drop in September vs August, and which region caused most of it?"

After the Reviewer says APPROVED, the UserProxyAgent asks you to approve the
answer or type a follow-up question, which continues the same session.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken

from database import Database

from .config import settings
from .data_loader import ALL_SHEETS, read_upload
from .runner import AgentEvent, AnalysisSession

APPROVE_WORDS = {"approve", "approved", "yes", "y", "ok", ""}
EXIT_WORDS = {"exit", "quit", "q"}


def _print_event(ev: AgentEvent) -> None:
    label = {"exec_error": "ERROR", "exec_ok": "OK"}.get(ev.kind, "")
    body = ev.content if len(ev.content) < 1500 else ev.content[:1500] + " ..."
    print(f"\n--- {ev.source} {label} ".ljust(60, "-") + f"\n{body}")


async def main_async(data_path: Path, question: str, sheet: str | None) -> None:
    db = Database(settings.db_path)
    df = read_upload(data_path.name, data_path.read_bytes(), sheet or ALL_SHEETS)
    session = AnalysisSession.create(db, df, data_path.name)
    print(f"Session {session.id} | sandbox folder: {session.work_dir}")

    human = UserProxyAgent("User", description="The human who approves the final answer or asks a follow-up.")
    while True:
        result = await session.ask(question, on_event=_print_event)
        print(f"\n=== stopped: {result.stop_reason} | messages: {result.n_messages} "
              f"| self-corrected errors: {result.n_exec_errors}")
        print("Files:", ", ".join(p.name for p in result.charts), "|", result.script)

        prompt = (result.answer or "The team hit the message limit without approval.") + \
            "\n\nType 'approve' to accept, a follow-up question to continue, or 'exit':"
        reply = await human.on_messages([TextMessage(content=prompt, source="Reviewer")], CancellationToken())
        text = reply.chat_message.to_text().strip()
        if text.lower() in APPROVE_WORDS:
            db.set_human_verdict(session.id, result.run_no, "accepted")
            print("Approved. Bye!")
            return
        if text.lower() in EXIT_WORDS:
            db.set_human_verdict(session.id, result.run_no, "rejected")
            return
        db.set_human_verdict(session.id, result.run_no, "follow_up")
        question = text


def main() -> None:
    p = argparse.ArgumentParser(description="DataPilot CLI")
    p.add_argument("data", type=Path, help="CSV or Excel file")
    p.add_argument("question", help="Business question in plain English")
    p.add_argument("--sheet", help="Excel sheet name (default: all sheets stacked)")
    args = p.parse_args()
    asyncio.run(main_async(args.data, args.question, args.sheet))


if __name__ == "__main__":
    main()
