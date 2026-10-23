"""Reusable UI building blocks (render-only; no business logic)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from backend.datapilot.progress import one_line, parse_answer, step_states
from backend.datapilot.quality import Gate
from frontend.theme import STATUS_CHIP, chip, esc

AGENT_ROLE = {
    "user": "Task", "Planner": "Planner", "Coder": "Coder", "Executor": "Executor", "Reviewer": "Reviewer",
}
KIND_LABEL = {
    "task": ("Task", "neutral"), "plan": ("Plan", "info"), "code": ("Code", "brand"), "exec_ok": ("OK", "ok"),
    "exec_error": ("ERROR", "bad"), "feedback": ("Feedback", "warn"), "approved": ("APPROVED", "ok"),
}


# --------------------------------------------------------------------------- pipeline
def steps_html(kinds: list[str], *, running: bool, run_status: str | None = None,
               human_verdict: str | None = None) -> str:
    icon = {"done": "✓", "error": "✕", "retry": "↻", "waiting": "…", "active": "", "pending": ""}
    cells = []
    for s in step_states(kinds, running=running, run_status=run_status, human_verdict=human_verdict):
        detail = s.detail or ("Waiting" if s.state == "pending" else "")
        cells.append(
            f'<div class="dp-step {s.state}"><div class="n">{s.num}</div><div class="t">{esc(s.name)}</div>'
            f'<div class="c">{esc(s.caption)}</div>'
            f'<div class="s"><span class="dot"></span>{esc(icon.get(s.state, ""))} {esc(detail)}</div></div>'
        )
    loop = ('<div class="dp-loop">Loop: if step 04 returns an error, or step 05 is not satisfied, the conversation goes '
            'back to step 03 automatically. No human is needed to fix code.</div>')
    return f'<div class="dp-steps">{"".join(cells)}</div>{loop}'


def steps_overview_html() -> str:
    """The six steps with their job descriptions, no run state (start screen / guide)."""
    from backend.datapilot.progress import STEPS

    cells = "".join(
        f'<div class="dp-step"><div class="n">{n}</div><div class="t">{esc(name)}</div><div class="c">{esc(cap)}</div></div>'
        for n, name, cap in STEPS
    )
    return f'<div class="dp-steps">{cells}</div>'


# --------------------------------------------------------------------------- Part A
def transcript_html(events: list[dict], *, running: bool = False) -> str:
    rows = []
    for ev in events:
        src, kind = ev["source"], ev["kind"]
        line = esc(one_line(kind, ev["content"]))
        if kind == "exec_error":
            line = line.replace("ERROR", '<span class="err">ERROR</span>', 1)
        elif kind == "exec_ok":
            line = line.replace("OK.", '<span class="ok">OK.</span>', 1)
        elif kind == "approved":
            line = '<span class="appr">APPROVED</span>'
        elif kind == "feedback":
            line = f'<span class="fb">{line}</span>'
        t = ev.get("elapsed_s")
        rows.append(
            f'<div class="row"><span class="who {esc(src)}">{esc(AGENT_ROLE.get(src, src))}</span>'
            f'<span class="sep">:</span><span>{line}</span><span class="t">{f"+{t:.0f}s" if t is not None else ""}</span></div>'
        )
    if running:
        rows.append('<div class="row"><span></span><span></span><span><span class="cursor"></span></span><span></span></div>')
    return f'<div class="dp-term">{"".join(rows) or "Waiting for the first agent…"}</div>'


def message_detail(ev: dict, attempt: int | None = None) -> None:
    """Full content of one agent message, rendered by type."""
    kind, content = ev["kind"], ev["content"]
    label, tone = KIND_LABEL.get(kind, (kind, "neutral"))
    role = AGENT_ROLE.get(ev["source"], ev["source"])
    title = (role if role == label else f"{role} · {label}") + (f" · attempt {attempt}" if attempt else "")
    t = ev.get("elapsed_s")
    with st.expander(f"{title}" + (f"  (+{t:.0f}s)" if t is not None else ""), expanded=False):
        if kind == "code":
            prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()
            if prose:
                st.markdown(prose)
            m = re.search(r"```(?:python|py)?\n(.*?)```", content, flags=re.DOTALL)
            st.code(m.group(1) if m else content, language="python", line_numbers=True)
        elif kind in ("exec_ok", "exec_error"):
            st.code(content.strip() or "(no output)", language="text")
        elif kind == "task":
            st.text(content)
        else:
            st.markdown(content.replace("APPROVED", "**APPROVED**"))


def message_details(events: list[dict]) -> None:
    code_n = 0
    for ev in events:
        if ev["kind"] == "code":
            code_n += 1
        message_detail(ev, attempt=code_n if ev["kind"] in ("code", "exec_ok", "exec_error") and code_n else None)


# --------------------------------------------------------------------------- Part B
def answer_panel(answer: str, files: list[str]) -> dict[str, str]:
    parts = parse_answer(answer)
    blocks = [f'<div class="lbl">Answer</div><div class="headline">{esc(parts.get("ANSWER", ""))}</div>']
    if parts.get("WHERE IT CAME FROM"):
        blocks.append(f'<div class="lbl">Where it came from</div><div class="body">{esc(parts["WHERE IT CAME FROM"])}</div>')
    if files:
        chips = "".join(f'<span class="dp-file">{esc(f)}</span>' for f in files)
        blocks.append(f'<div class="lbl">Files</div><div class="dp-files">{chips}</div>')
    if parts.get("SUGGESTED NEXT QUESTION"):
        blocks.append(f'<div class="lbl">Suggested next question</div><div class="body">{esc(parts["SUGGESTED NEXT QUESTION"])}</div>')
    st.markdown(f'<div class="dp-answer">{"".join(blocks)}</div>', unsafe_allow_html=True)
    return parts


def gates_html(gates: list[Gate]) -> str:
    icon = {"pass": "✓", "fail": "✕", "info": "i", "pending": "–"}
    tone = {"pass": ("PASS", "ok"), "fail": ("FAIL", "bad"), "info": ("N/A", "info"), "pending": ("PENDING", "neutral")}
    rows = "".join(
        f'<div class="dp-gate {g.status}"><div class="ic">{icon[g.status]}</div>'
        f'<div><b>{esc(g.label)}</b><br><span>{esc(g.evidence)}</span></div>{chip(*tone[g.status])}</div>'
        for g in gates
    )
    return f'<div class="dp-gates">{rows}</div>'


def run_header(run: dict, max_messages: int) -> None:
    label, tone = STATUS_CHIP.get(run.get("status") or "running", ("—", "neutral"))
    meta = [f"{run.get('n_messages') or 0}/{max_messages} messages"]
    if run.get("duration_s"):
        meta.append(f"{run['duration_s']:.0f}s")
    if run.get("model"):
        meta.append(run["model"])
    if run.get("started_at"):
        meta.append(f"{run['started_at']} UTC")
    st.markdown(
        f'<div class="dp-run"><div><div class="dp-runno">Run #{run["run_no"]}</div>'
        f'<div class="q">{esc(run["question"])}</div><div class="meta">{esc(" · ".join(meta))}</div></div>'
        f'<div>{chip(label, tone)}</div></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- data
def schema_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append({
            "Column": col, "Type": str(s.dtype), "Non-null": f"{s.notna().mean():.1%}",
            "Distinct": f"{s.nunique(dropna=True):,}", "Example": str(s.dropna().iloc[0]) if s.notna().any() else "",
        })
    return pd.DataFrame(rows)


def date_range(df: pd.DataFrame) -> str:
    for col in df.columns:
        if "date" in col.lower() or col.lower() in ("month", "period"):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.9:
                return f"{parsed.min():%Y-%m} → {parsed.max():%Y-%m}"
    return "—"


def file_size(path: Path) -> str:
    n = path.stat().st_size
    return f"{n / 1024:,.1f} KB" if n < 1024 ** 2 else f"{n / 1024 ** 2:,.2f} MB"
