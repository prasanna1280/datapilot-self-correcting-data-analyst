"""Rendering helpers for the Streamlit UI."""

from __future__ import annotations

import html

import streamlit as st

AGENTS = {
    "user": ("👤", "You"),
    "Planner": ("🧭", "Planner"),
    "Coder": ("💻", "Coder"),
    "Executor": ("⚙️", "Executor"),
    "Reviewer": ("🔎", "Reviewer"),
}
BADGES = {
    "exec_error": ("ERROR", "#b42318", "#fee4e2"),
    "exec_ok": ("OK", "#067647", "#dcfae6"),
    "feedback": ("FEEDBACK", "#b54708", "#fef0c7"),
    "approved": ("APPROVED", "#067647", "#dcfae6"),
    "fix": ("FIXED", "#175cd3", "#d1e9ff"),
}

CSS = """
<style>
:root { --dp-maroon: #6e1216; --dp-rose: #fbeff0; }
.dp-hero { background: var(--dp-maroon); color: #fff; padding: 18px 22px; border-radius: 10px; margin-bottom: 14px; }
.dp-hero h1 { color: #fff; font-size: 1.6rem; margin: 0; padding: 0; }
.dp-hero p { margin: 4px 0 0; opacity: .9; font-size: .95rem; }
.dp-badge { display: inline-block; font-size: .7rem; font-weight: 700; padding: 1px 8px; border-radius: 999px; margin-left: 6px; letter-spacing: .03em; }
.dp-agent { font-weight: 700; }
.dp-answer { border-left: 5px solid var(--dp-maroon); background: var(--dp-rose); padding: 14px 18px; border-radius: 6px; white-space: pre-wrap; font-size: .95rem; color: #1d1d1d; }
.dp-steps { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0 10px; }
.dp-step { flex: 1 1 90px; border: 1px solid #e8c9cc; background: var(--dp-rose); border-radius: 6px; padding: 6px 8px; font-size: .75rem; color: #3b0d10; }
.dp-step b { display: block; color: var(--dp-maroon); }
</style>
"""

HOW_IT_WORKS = """
<div class="dp-steps">
  <div class="dp-step"><b>01 Ask</b>Upload a CSV and type a question</div>
  <div class="dp-step"><b>02 Plan</b>Planner writes the analysis steps</div>
  <div class="dp-step"><b>03 Code</b>Coder writes Python</div>
  <div class="dp-step"><b>04 Run</b>Executor runs it in the sandbox</div>
  <div class="dp-step"><b>05 Review</b>Reviewer approves or sends it back</div>
  <div class="dp-step"><b>06 Answer</b>You approve or ask a follow-up</div>
</div>
"""


def badge(kind: str) -> str:
    if kind not in BADGES:
        return ""
    text, fg, bg = BADGES[kind]
    return f'<span class="dp-badge" style="color:{fg};background:{bg}">{text}</span>'


def render_event(source: str, kind: str, content: str, *, after_error: bool = False) -> None:
    """One agent message inside the conversation trail."""
    icon, label = AGENTS.get(source, ("•", source))
    shown_kind = "fix" if kind == "code" and after_error else kind
    st.markdown(f'{icon} <span class="dp-agent">{label}</span>{badge(shown_kind)}', unsafe_allow_html=True)

    if kind == "task":
        first_line = content.splitlines()[0] if content else ""
        st.caption(first_line)
        with st.popover("Full task sent to the team"):
            st.text(content)
    elif kind in ("exec_ok", "exec_error"):
        st.code(content.strip() or "(no output)", language="text")
    elif kind == "code":
        st.markdown(content)
    else:
        st.markdown(content.replace("APPROVED", "**APPROVED**") if kind == "approved" else content)


def render_trail(events: list[dict]) -> None:
    prev_error = False
    for ev in events:
        render_event(ev["source"], ev["kind"], ev["content"], after_error=prev_error)
        prev_error = ev["kind"] in ("exec_error", "feedback")
        st.divider()


def render_answer(answer: str) -> None:
    st.markdown(f'<div class="dp-answer">{html.escape(answer)}</div>', unsafe_allow_html=True)
