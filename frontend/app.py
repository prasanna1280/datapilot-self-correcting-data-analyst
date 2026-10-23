"""DataPilot - Streamlit chat UI.

Run locally:  streamlit run frontend/app.py
"""

from __future__ import annotations

import asyncio
import hmac
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from backend.datapilot.config import settings  # noqa: E402
from backend.datapilot.data_loader import ALL_SHEETS, list_sheets, read_upload  # noqa: E402
from backend.datapilot.report import build_pdf  # noqa: E402
from backend.datapilot.runner import AnalysisSession  # noqa: E402
from database import Database  # noqa: E402
from frontend.components import CSS, HOW_IT_WORKS, render_answer, render_event, render_trail  # noqa: E402

SAMPLE_CSV = ROOT / "data" / "sample" / "sales_2026.csv"
SAMPLE_QUESTION = ("Which category had the biggest revenue drop in September vs August, "
                   "and which region caused most of it?")

st.set_page_config(page_title="DataPilot - Self-Correcting Data Analyst", page_icon="📊", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def get_db() -> Database:
    return Database(settings.db_path)


def password_gate() -> None:
    """Optional shared password (APP_PASSWORD) so a public URL can't burn the OpenAI budget."""
    if not settings.app_password or st.session_state.get("authed"):
        return
    st.markdown('<div class="dp-hero"><h1>DataPilot</h1><p>Sign in to continue</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Access password", type="password")
        if st.form_submit_button("Enter", type="primary"):
            if hmac.compare_digest(pwd, settings.app_password):
                st.session_state.authed = True
                st.rerun()
            st.error("Wrong password.")
    st.stop()


def current_session(db: Database) -> AnalysisSession | None:
    sid = st.session_state.get("session_id") or st.query_params.get("session")
    if not sid:
        return None
    session = AnalysisSession.load(db, sid)
    if session:
        st.session_state.session_id = sid
    return session


def start_session(db: Database, df: pd.DataFrame, name: str) -> None:
    session = AnalysisSession.create(db, df, name)
    st.session_state.session_id = session.id
    st.session_state.setdefault("my_sessions", []).insert(0, (session.id, name))
    st.query_params["session"] = session.id
    st.rerun()


def sidebar(db: Database) -> None:
    with st.sidebar:
        st.header("📁 Data")
        up = st.file_uploader("Upload sales data", type=["csv", "xlsx", "xls"],
                              help=f"CSV or Excel, up to {settings.max_upload_mb} MB")
        if up is not None:
            raw = up.getvalue()
            sheet = None
            if up.name.lower().endswith((".xlsx", ".xls")):
                sheets = list_sheets(raw)
                options = ([ALL_SHEETS] if len(sheets) > 1 else []) + sheets
                sheet = st.selectbox("Sheet", options,
                                     format_func=lambda s: f"All {len(sheets)} sheets (stacked)" if s == ALL_SHEETS else s)
            if st.button("Start analysis session", type="primary", width="stretch"):
                try:
                    start_session(db, read_upload(up.name, raw, sheet), up.name)
                except ValueError as e:
                    st.error(str(e))
        st.caption("No data handy?")
        if st.button("Use sample: sales_2026.csv (12,480 rows)", width="stretch"):
            start_session(db, pd.read_csv(SAMPLE_CSV), SAMPLE_CSV.name)

        mine = st.session_state.get("my_sessions", [])
        if mine:
            st.header("🕘 This browser")
            for sid, name in mine[:8]:
                if st.button(f"{name} · {sid[:6]}", key=f"open_{sid}", width="stretch"):
                    st.session_state.session_id = sid
                    st.query_params["session"] = sid
                    st.rerun()

        st.divider()
        st.caption(f"Model: `{settings.model}` · Limit: {settings.max_messages} messages/run · "
                   f"Executor: `{settings.executor_mode}` · Code timeout: {settings.code_timeout_s}s")
        if st.button("➕ New session", width="stretch"):
            st.session_state.pop("session_id", None)
            st.query_params.clear()
            st.rerun()


def render_downloads(session: AnalysisSession, run: dict) -> None:
    charts, script = session.artifacts(run["run_no"])
    if charts:
        cols = st.columns(min(len(charts), 2))
        for i, png in enumerate(charts):
            with cols[i % len(cols)]:
                st.image(str(png), caption=png.name, width="stretch")
    key = f"{session.id}_{run['run_no']}"
    c1, c2, c3, c4 = st.columns(4)
    if script:
        c1.download_button("⬇ analysis.py", script.read_bytes(), "analysis.py", "text/x-python", key=f"py_{key}")
    for i, png in enumerate(charts[:2]):
        (c2, c3)[i].download_button(f"⬇ {png.name}", png.read_bytes(), png.name, "image/png", key=f"png_{key}_{i}")
    if run["answer"]:
        pdf = build_pdf(run["question"], run["answer"], charts, session.dataset_name)
        c4.download_button("⬇ PDF report", pdf, f"datapilot_run{run['run_no']}.pdf", "application/pdf", key=f"pdf_{key}")


def render_human_step(db: Database, session: AnalysisSession, run: dict, is_latest: bool) -> None:
    verdict = run.get("human_verdict")
    if verdict == "accepted":
        st.success("✅ You approved this answer.")
    elif verdict == "rejected":
        st.warning("You rejected this answer. Ask a follow-up below to correct it.")
    elif is_latest and run["status"] in ("approved", "limit"):
        st.markdown("**👤 User Proxy — your call:** approve the answer, or ask a follow-up in the chat box.")
        a, b, _ = st.columns([1, 1, 3])
        if a.button("✅ Approve answer", key=f"ok_{run['run_no']}", type="primary"):
            db.set_human_verdict(session.id, run["run_no"], "accepted")
            st.rerun()
        if b.button("✖ Reject", key=f"no_{run['run_no']}"):
            db.set_human_verdict(session.id, run["run_no"], "rejected")
            st.rerun()


def render_history(db: Database, session: AnalysisSession) -> None:
    runs = db.get_runs(session.id)
    messages = db.get_messages(session.id)
    for run in runs:
        with st.chat_message("user", avatar="👤"):
            st.markdown(run["question"])
        with st.chat_message("assistant", avatar="📊"):
            trail = [m for m in messages if m["run_no"] == run["run_no"]]
            label = (f"Agent conversation · {run['n_messages']} messages · "
                     f"{run['n_exec_errors']} self-corrected error(s) · stop: {run['status']}")
            with st.expander(label, expanded=False):
                render_trail(trail)
            if run["status"] == "approved" and run["answer"]:
                render_answer(run["answer"])
            elif run["status"] == "limit":
                st.warning(f"Stopped at the safety limit ({settings.max_messages} messages) before the Reviewer "
                           "approved. Ask a follow-up to refine the question.")
            elif run["status"] == "error":
                st.error(f"Run failed: {run['stop_reason']}")
            render_downloads(session, run)
            render_human_step(db, session, run, is_latest=run is runs[-1])


def run_question(session: AnalysisSession, question: str) -> None:
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="📊"):
        status = st.status("Agents are working… (Planner → Coder → Executor → Reviewer)", expanded=True)
        state = {"prev_error": False}

        def on_event(ev) -> None:
            with status:
                render_event(ev.source, ev.kind, ev.content, after_error=state["prev_error"])
                st.divider()
            state["prev_error"] = ev.kind in ("exec_error", "feedback")
            status.update(label=f"Agents are working… last: {ev.source}")

        try:
            result = asyncio.run(session.ask(question, on_event=on_event))
            status.update(label=f"Done · {result.n_messages} messages · stop: {result.status}",
                          state="complete" if result.status == "approved" else "error", expanded=False)
        except Exception as e:  # API key / network problems
            status.update(label="Run failed", state="error")
            st.error(f"{type(e).__name__}: {e}")
            return
    st.rerun()


def main() -> None:
    password_gate()
    db = get_db()
    sidebar(db)

    st.markdown('<div class="dp-hero"><h1>📊 DataPilot: Self-Correcting Data Analyst</h1>'
                '<p>Ask a business question in plain English. A team of agents plans, writes Python, runs it, '
                'fixes its own errors and returns the answer with charts.</p></div>', unsafe_allow_html=True)

    session = current_session(db)
    if session is None:
        st.markdown(HOW_IT_WORKS, unsafe_allow_html=True)
        st.info("👈 Upload a CSV / Excel file or load the sample dataset to start.")
        return

    data_file = session.work_dir / "data.csv"
    with st.expander(f"Dataset: **{session.dataset_name}** · session `{session.id[:8]}`"):
        if data_file.exists():
            st.dataframe(pd.read_csv(data_file, nrows=200), width="stretch", height=240)
        st.text(session.profile)

    render_history(db, session)

    runs = db.get_runs(session.id)
    if runs and runs[-1]["status"] == "approved":
        with st.expander("🔁 Reproducibility check"):
            st.caption("Re-runs the saved analysis.py in the sandbox and compares the output with the approved run.")
            if st.button("Re-run analysis.py and compare"):
                same, output = asyncio.run(session.reproduce())
                (st.success if same else st.error)("Same numbers ✔" if same else "Output differs ✖")
                st.code(output, language="text")

    question = st.chat_input("Ask a follow-up question…" if runs else "Ask a business question about this data…")
    if not runs and session.dataset_name == SAMPLE_CSV.name:
        if st.button(f"▶ Ask the sample question: {SAMPLE_QUESTION}"):
            question = SAMPLE_QUESTION
    if question:
        if not settings.openai_api_key:
            st.error("OPENAI_API_KEY is not configured on the server.")
            return
        run_question(session, question.strip())


main()
