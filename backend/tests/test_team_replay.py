"""End-to-end team runs with a scripted (replay) model - no API key, real code execution.

Proves the agentic loop: a buggy script fails in the Executor, the Coder sees the
error and rewrites it, the Reviewer approves, and re-running analysis.py gives the
same numbers. Also proves the 12-message safety limit and follow-up continuity.
"""

import pytest
from autogen_ext.models.replay import ReplayChatCompletionClient

from backend.datapilot.report import build_pdf
from backend.datapilot.runner import AnalysisSession

PLAN = "1) revenue = units * unit_price * (1 - discount)\n2) Group by month + category\n3) Find biggest drop\n4) Split by region"

BUGGY = '''```python
# filename: analysis.py
import pandas as pd
df = pd.read_csv("data.csv")
print(df.groupby("category")["revenue"].sum())
```'''

FIXED = '''Fixed: revenue column is now created before grouping.
```python
# filename: analysis.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data.csv", parse_dates=["order_date"])
df["revenue"] = df["units"] * df["unit_price"] * (1 - df["discount"])
df["month"] = df["order_date"].dt.strftime("%Y-%m")
m = df[df["month"].isin(["2026-08", "2026-09"])]
by_cat = m.pivot_table(index="category", columns="month", values="revenue", aggfunc="sum")
by_cat["drop"] = by_cat["2026-08"] - by_cat["2026-09"]
top = by_cat["drop"].idxmax()
print(f"Biggest drop: {top} Aug {by_cat.loc[top, '2026-08']/1e5:.1f} L, Sep {by_cat.loc[top, '2026-09']/1e5:.1f} L")
reg = m[m["category"] == top].pivot_table(index="region", columns="month", values="revenue", aggfunc="sum")
reg["drop"] = reg["2026-08"] - reg["2026-09"]
print(f"Top region: {reg['drop'].idxmax()} {reg['drop'].max()/1e5:.1f} L")
ax = (by_cat["drop"] / 1e5).plot(kind="bar", title="Revenue drop Sep vs Aug by category")
ax.set_xlabel("Category"); ax.set_ylabel("Revenue drop (Rs lakh)")
plt.tight_layout(); plt.savefig("category_trend.png"); plt.close()
print("SAVED: category_trend.png")
```'''

ANSWER = "ANSWER\nElectronics had the biggest drop.\n\nWHERE IT CAME FROM\nSouth region.\n\nFILES\ncategory_trend.png | analysis.py\n\nSUGGESTED NEXT QUESTION\nDid discounts change?\n\nAPPROVED"


@pytest.mark.asyncio
async def test_self_correction_loop_end_to_end(db, sales_df):
    session = AnalysisSession.create(db, sales_df, "sales_2026.csv")
    client = ReplayChatCompletionClient([PLAN, BUGGY, FIXED, ANSWER])
    seen = []

    result = await session.ask("Which category dropped most in Sep vs Aug?", on_event=seen.append, model_client=client)

    kinds = [e.kind for e in result.events]
    assert kinds == ["task", "plan", "code", "exec_error", "code", "exec_ok", "approved"]
    assert "KeyError" in result.events[3].content            # the error the Coder had to fix
    assert "Biggest drop: Electronics" in result.events[5].content
    assert result.status == "approved" and result.n_exec_errors == 1
    assert result.answer.startswith("ANSWER") and "APPROVED" not in result.answer
    assert [c.name for c in result.charts] == ["category_trend.png"]
    assert result.script and result.script.parent.name == "run_1"
    assert len(seen) == 7

    # Everything is persisted.
    run = db.get_runs(session.id)[0]
    assert run["status"] == "approved" and run["n_exec_errors"] == 1
    assert len(db.get_messages(session.id)) == 7

    # Re-running the saved analysis.py gives exactly the same numbers.
    same, output = await session.reproduce()
    assert same, output

    pdf = build_pdf("q", result.answer, result.charts, "sales_2026.csv")
    assert pdf[:4] == b"%PDF"

    # Follow-up continues the same session/team state (reloaded from the DB).
    reloaded = AnalysisSession.load(db, session.id)
    assert reloaded.team_state is not None
    follow = await reloaded.ask("Did discounts change?", model_client=ReplayChatCompletionClient([PLAN, FIXED, ANSWER]))
    assert follow.run_no == 2 and follow.status == "approved"
    assert follow.events[0].content.startswith("Follow-up question")


@pytest.mark.asyncio
async def test_stops_after_12_messages_without_approval(db, sales_df):
    session = AnalysisSession.create(db, sales_df.head(50), "small.csv")
    feedback = "FEEDBACK: add axis labels"
    client = ReplayChatCompletionClient([PLAN] + [FIXED, feedback] * 6)

    result = await session.ask("q", model_client=client)

    assert result.n_messages == 12
    assert result.status == "limit" and result.answer is None
    assert "Maximum number of messages 12 reached" in (result.stop_reason or "")
