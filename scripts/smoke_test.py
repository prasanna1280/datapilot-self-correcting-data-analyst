"""Smoke test for a running deployment (uses whatever EXECUTOR_MODE is configured).

    docker compose exec app python scripts/smoke_test.py            # scripted model, no API cost
    docker compose exec app python scripts/smoke_test.py --live     # real OpenAI call

Scripted mode replays: plan -> buggy code (KeyError) -> fixed code -> APPROVED,
so it proves the sandbox, the self-correction loop and reproducibility end to end.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autogen_ext.models.replay import ReplayChatCompletionClient  # noqa: E402

from backend.datapilot.config import settings  # noqa: E402
from backend.datapilot.data_loader import read_upload  # noqa: E402
from backend.datapilot.runner import AnalysisSession  # noqa: E402
from backend.tests.test_team_replay import ANSWER, BUGGY, FIXED, PLAN  # noqa: E402
from database import Database  # noqa: E402

QUESTION = "Which category had the biggest revenue drop in September vs August, and which region caused most of it?"


async def main(live: bool) -> int:
    csv = ROOT / "data" / "sample" / "sales_2026.csv"
    db = Database(settings.db_path)
    session = AnalysisSession.create(db, read_upload(csv.name, csv.read_bytes()), csv.name)
    client = None if live else ReplayChatCompletionClient([PLAN, BUGGY, FIXED, ANSWER])
    print(f"executor={settings.executor_mode} model={'live ' + settings.model if live else 'replay'} session={session.id}")

    result = await session.ask(QUESTION, on_event=lambda e: print(f"  {e.source:<9} {e.kind}"), model_client=client)
    same, _ = await session.reproduce()
    print(f"status={result.status} messages={result.n_messages} self_corrected={result.n_exec_errors} "
          f"charts={[c.name for c in result.charts]} reproducible={same}")
    if result.answer:
        print(result.answer)
    ok = result.status == "approved" and same and (live or result.n_exec_errors == 1)
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use the real OpenAI model")
    sys.exit(asyncio.run(main(ap.parse_args().live)))
