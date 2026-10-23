"""Smoke test for a running deployment (uses whatever EXECUTOR_MODE is configured).

    docker compose exec app python scripts/smoke_test.py                         # scripted model, no API cost
    docker compose exec app python scripts/smoke_test.py --live                  # real model, retail sample
    docker compose exec app python scripts/smoke_test.py --live --sample supply_chain --question 0

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

from backend.datapilot.catalog import get_sample, load_catalog  # noqa: E402
from backend.datapilot.config import settings  # noqa: E402
from backend.datapilot.data_loader import ALL_SHEETS, read_upload  # noqa: E402
from backend.datapilot.runner import AnalysisSession  # noqa: E402
from backend.tests.replay_script import ANSWER, BUGGY, FIXED, PLAN  # noqa: E402
from database import Database  # noqa: E402


async def main(live: bool, sample_id: str, question_idx: int) -> int:
    sample = get_sample(sample_id)
    if sample is None:
        print("unknown sample; choose from:", ", ".join(s.id for s in load_catalog()))
        return 2
    if not live and sample_id != "retail_india":
        print("scripted mode only supports the retail_india sample")
        return 2
    db = Database(settings.db_path)
    df = read_upload(sample.file, sample.path.read_bytes(), ALL_SHEETS)
    session = AnalysisSession.create(db, df, sample.file, currency=sample.currency,
                                     number_style=sample.number_style, sample_id=sample.id)
    question = sample.questions[question_idx]
    client = None if live else ReplayChatCompletionClient([PLAN, BUGGY, FIXED, ANSWER])
    print(f"executor={settings.executor_mode} model={'live ' + settings.model if live else 'replay'} "
          f"sample={sample.id} session={session.id}\nQ: {question}")

    result = await session.ask(question, on_event=lambda e: print(f"  +{e.elapsed_s:>5.1f}s {e.source:<9} {e.kind}"),
                               model_client=client)
    print(f"status={result.status} messages={result.n_messages} self_corrected={result.n_exec_errors} "
          f"review_rounds={result.n_feedback} duration={result.duration_s}s "
          f"charts={[c.name for c in result.charts]} reproducible={result.reproducible}")
    if result.answer:
        print(result.answer)
    ok = result.status == "approved" and bool(result.reproducible) and (live or result.n_exec_errors == 1)
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use the real OpenAI model")
    ap.add_argument("--sample", default="retail_india", help="catalog id of the sample dataset")
    ap.add_argument("--question", type=int, default=0, help="index of the sample question")
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.live, a.sample, a.question)))
