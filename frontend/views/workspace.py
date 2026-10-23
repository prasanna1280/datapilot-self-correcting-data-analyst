"""Analysis Workspace: start a session, ask questions, watch the 6 steps live, review outputs."""

from __future__ import annotations

import asyncio

import pandas as pd
import streamlit as st

from backend.datapilot.catalog import get_sample, load_catalog
from backend.datapilot.config import settings
from backend.datapilot.data_loader import ALL_SHEETS, DATA_FILE_NAME, list_sheets, read_upload
from backend.datapilot.formatting import CURRENCIES, NUMBER_STYLES, detect_currency
from backend.datapilot.progress import parse_answer
from backend.datapilot.quality import evaluate
from backend.datapilot.report import build_pdf
from backend.datapilot.runner import AnalysisSession
from frontend import components as ui
from frontend.state import close_session, current_session, get_db, start_from_frame, start_from_sample
from frontend.theme import chip, esc, kv_tiles, page_header


# --------------------------------------------------------------------------- start screen
def render_start() -> None:
    page_header("New analysis", "Choose a dataset, then ask a business question in plain English.", "Workspace")
    st.markdown(ui.steps_overview_html(), unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1], gap="large")

    with left, st.container(border=True):
        st.markdown("#### Sample datasets")
        st.caption("Realistic, international-format datasets with a built-in story to discover.")
        for sample in load_catalog():
            c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
            c1.markdown(
                f"**{esc(sample.title)}**  \n"
                f"<span class='dp-muted'>{esc(sample.domain)} · {esc(sample.currency)} · {esc(sample.file)}</span>",
                unsafe_allow_html=True)
            if c2.button("Open", key=f"start_{sample.id}", width="stretch"):
                start_from_sample(sample)

    with right, st.container(border=True):
        st.markdown("#### Upload your data")
        st.caption(f"CSV or Excel (multi-sheet supported), up to {settings.max_upload_mb} MB. "
                   "Use one row per record and a header row.")
        up = st.file_uploader("Data file", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
        if up is None:
            return
        raw = up.getvalue()
        sheet = None
        if up.name.lower().endswith((".xlsx", ".xls")):
            sheets = list_sheets(raw)
            options = ([ALL_SHEETS] if len(sheets) > 1 else []) + sheets
            sheet = st.selectbox("Worksheet", options,
                                 format_func=lambda s: f"All {len(sheets)} sheets, stacked" if s == ALL_SHEETS else s)
        try:
            df = read_upload(up.name, raw, sheet)
        except ValueError as e:
            st.error(str(e))
            return
        detected = detect_currency(df.columns)
        cur_options = list(CURRENCIES)
        c1, c2 = st.columns(2)
        currency = c1.selectbox("Currency (ISO 4217)", cur_options,
                                index=cur_options.index(detected) if detected in cur_options else 0,
                                format_func=lambda c: f"{c} — {CURRENCIES[c]}",
                                help="Auto-detected from column names like price_usd when possible.")
        style = c2.selectbox("Number format", list(NUMBER_STYLES), format_func=NUMBER_STYLES.get,
                             index=1 if currency == "INR" else 0)
        st.caption(f"Preview: {len(df):,} rows × {len(df.columns)} columns")
        st.dataframe(df.head(5), width="stretch", hide_index=True)
        if st.button("Start analysis session", type="primary", width="stretch"):
            start_from_frame(df, up.name, currency, style)


# --------------------------------------------------------------------------- dataset bar
def render_dataset(session: AnalysisSession) -> pd.DataFrame | None:
    data_file = session.work_dir / DATA_FILE_NAME
    df = pd.read_csv(data_file) if data_file.exists() else None
    sample = get_sample(session.sample_id) if session.sample_id else None
    title = sample.title if sample else session.dataset_name
    page_header(title, sample.description if sample else f"Uploaded file · {session.dataset_name}", "Workspace",
                chip(f"Session {session.id[:8]}", "neutral"))
    if df is not None:
        kv_tiles([
            ("Rows", f"{len(df):,}"), ("Columns", f"{len(df.columns)}"), ("Period", ui.date_range(df)),
            ("Currency", session.currency), ("Number format", "Lakh / crore" if session.number_style == "indian" else "K / M / B"),
            ("Source", session.dataset_name),
        ])
        with st.expander("Data preview & schema"):
            t1, t2, t3 = st.tabs(["Preview (first 200 rows)", "Schema", "Profile sent to the agents"])
            t1.dataframe(df.head(200), width="stretch", height=280, hide_index=True)
            t2.dataframe(ui.schema_frame(df), width="stretch", hide_index=True)
            t3.code(session.profile + "\n\n" + session.standard, language="text")
    return df


# --------------------------------------------------------------------------- one run
def render_run(session: AnalysisSession, run: dict, events: list[dict], *, is_latest: bool) -> str | None:
    """Render a finished run. Returns a follow-up question if the user clicked one."""
    db = get_db()
    charts, script = session.artifacts(run["run_no"])
    clicked = None
    with st.container(border=True):
        ui.run_header(run, settings.max_messages)
        st.markdown(ui.steps_html([e["kind"] for e in events], running=False, run_status=run["status"],
                                  human_verdict=run.get("human_verdict")), unsafe_allow_html=True)
        st.write("")
        m = st.columns(5)
        m[0].metric("Messages", f"{run['n_messages']}/{settings.max_messages}")
        m[1].metric("Code errors fixed", run["n_exec_errors"])
        m[2].metric("Review rounds", run.get("n_feedback") or 0)
        m[3].metric("Duration", f"{run['duration_s']:.0f}s" if run.get("duration_s") else "—")
        m[4].metric("Reproducible", {1: "Yes", 0: "No"}.get(run.get("reproducible"), "—"))

        tabs = st.tabs(["Answer & charts", "Agent conversation", "Code & execution", "Quality gates"])
        with tabs[0]:
            clicked = _answer_tab(session, run, charts, script, is_latest)
        with tabs[1]:
            st.caption("Part A — the full thinking trail: plan, code, errors, fixes, review (shortened). "
                       "Expand any message below for the full content.")
            st.markdown(ui.transcript_html(events), unsafe_allow_html=True)
            st.write("")
            ui.message_details(events)
        with tabs[2]:
            _code_tab(events, script)
        with tabs[3]:
            st.caption("The spec's Done checklist, evaluated on this run's real data.")
            gates = evaluate(run, script=script, executor_mode=settings.executor_mode,
                             max_messages=settings.max_messages)
            st.markdown(ui.gates_html(gates), unsafe_allow_html=True)
            if script and st.button("Re-run analysis.py now", key=f"rep_{run['run_no']}"):
                with st.spinner("Re-executing in the sandbox…"):
                    same, output = asyncio.run(session.reproduce(run["run_no"]))
                (st.success if same else st.error)("Same numbers ✓" if same else "Output differs ✕")
                st.code(output, language="text")
    return clicked


def _answer_tab(session: AnalysisSession, run: dict, charts, script, is_latest: bool) -> str | None:
    db = get_db()
    clicked = None
    if run["status"] == "approved" and run["answer"]:
        files = [c.name for c in charts] + (["analysis.py"] if script else [])
        st.caption("Part B — final answer shown to the user")
        parts = ui.answer_panel(run["answer"], files)
    elif run["status"] == "limit":
        parts = {}
        st.warning(f"The team stopped at the safety limit ({settings.max_messages} messages) before the Reviewer "
                   "approved. The charts and code below are the latest attempt. Ask a narrower follow-up to continue.")
    else:
        parts = {}
        st.error(f"Run failed: {run.get('stop_reason') or 'unknown error'}")

    if charts:
        st.write("")
        cols = st.columns(2)
        for i, png in enumerate(charts):
            with cols[i % 2], st.container(border=True):
                st.image(str(png), width="stretch")
                c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
                c1.caption(f"{png.name} · {ui.file_size(png)}")
                c2.download_button("Download", png.read_bytes(), png.name, "image/png",
                                   key=f"dl_{run['run_no']}_{png.name}", width="stretch")

    st.write("")
    c = st.columns(3)
    key = f"{session.id}_{run['run_no']}"
    if script:
        c[0].download_button("⬇ analysis.py", script.read_bytes(), "analysis.py", "text/x-python",
                             key=f"py_{key}", width="stretch")
    if run["answer"]:
        pdf = build_pdf(run["question"], run["answer"], charts, session.dataset_name,
                        meta={"Run": f"#{run['run_no']}", "Model": run.get("model") or settings.model,
                              "Messages": f"{run['n_messages']}/{settings.max_messages}",
                              "Errors fixed": str(run["n_exec_errors"]), "Session": session.id[:8]})
        c[1].download_button("⬇ PDF report", pdf, f"datapilot_run{run['run_no']}.pdf", "application/pdf",
                             key=f"pdf_{key}", width="stretch")
    next_q = parts.get("SUGGESTED NEXT QUESTION")
    if is_latest and next_q and c[2].button("Ask suggested next question", key=f"next_{key}", width="stretch"):
        clicked = next_q

    if is_latest:
        _human_step(session, run)
    elif run.get("human_verdict"):
        st.caption(f"Human verdict: {run['human_verdict']}")
    return clicked


def _human_step(session: AnalysisSession, run: dict) -> None:
    db = get_db()
    verdict = run.get("human_verdict")
    st.write("")
    with st.container(border=True):
        if verdict == "accepted":
            st.markdown(f"{chip('✓ APPROVED BY YOU', 'ok')} &nbsp; The answer is accepted. "
                        "Ask a follow-up below to continue this session.", unsafe_allow_html=True)
        elif verdict == "rejected":
            st.markdown(f"{chip('✕ REJECTED', 'bad')} &nbsp; Ask a follow-up below explaining what to correct.",
                        unsafe_allow_html=True)
        elif run["status"] in ("approved", "limit"):
            c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="center")
            c1.markdown("**06 · Human approval (User Proxy)**  \nApprove the final answer, or reject it and ask a follow-up.")
            if c2.button("✓ Approve", key=f"ok_{run['run_no']}", type="primary", width="stretch"):
                db.set_human_verdict(session.id, run["run_no"], "accepted")
                st.rerun()
            if c3.button("✕ Reject", key=f"no_{run['run_no']}", width="stretch"):
                db.set_human_verdict(session.id, run["run_no"], "rejected")
                st.rerun()


def _code_tab(events: list[dict], script) -> None:
    attempts = []
    code_n = 0
    for e in events:
        if e["kind"] == "code":
            code_n += 1
        elif e["kind"] in ("exec_ok", "exec_error"):
            attempts.append((code_n, e))
    if attempts:
        rows = "".join(
            f"<tr><td><b>Attempt {n}</b></td><td>{chip('OK', 'ok') if e['kind'] == 'exec_ok' else chip('ERROR', 'bad')}</td>"
            f"<td>{esc(ui.one_line(e['kind'], e['content'])[:140])}</td>"
            f"<td>{'+%.0fs' % e['elapsed_s'] if e.get('elapsed_s') is not None else ''}</td></tr>"
            for n, e in attempts
        )
        st.markdown("<table class='dp-table'><tr><th>Execution</th><th>Result</th><th>Output</th><th>Time</th></tr>"
                    f"{rows}</table>", unsafe_allow_html=True)
        st.write("")
    if script:
        st.markdown("**Final `analysis.py`** — re-runnable: anyone can run it next to `data.csv` and get the same numbers.")
        st.code(script.read_text(encoding="utf-8"), language="python", line_numbers=True)
        final = [e for n, e in attempts if e["kind"] == "exec_ok"]
        if final:
            st.markdown("**Final execution output**")
            st.code(final[-1]["content"], language="text")
    else:
        st.info("No script was saved in this run.")


# --------------------------------------------------------------------------- live run
def run_live(session: AnalysisSession, question: str) -> None:
    with st.container(border=True):
        ui.run_header({"run_no": get_db().next_run_no(session.id), "question": question, "status": "running",
                       "n_messages": 0, "model": settings.model}, settings.max_messages)
        tracker = st.empty()
        st.caption("Live agent conversation")
        term = st.empty()
        details = st.container()
        events: list[dict] = []

        def paint() -> None:
            tracker.markdown(ui.steps_html([e["kind"] for e in events], running=True), unsafe_allow_html=True)
            term.markdown(ui.transcript_html(events, running=True), unsafe_allow_html=True)

        def on_event(ev) -> None:
            events.append({"source": ev.source, "kind": ev.kind, "content": ev.content, "elapsed_s": ev.elapsed_s})
            paint()
            with details:
                ui.message_detail(events[-1])

        paint()
        try:
            asyncio.run(session.ask(question, on_event=on_event))
        except Exception as e:  # API key / network problems
            st.error(f"{type(e).__name__}: {e}")
            return
    st.rerun()


# --------------------------------------------------------------------------- page
def view() -> None:
    session = current_session()
    if session is None:
        render_start()
        return

    db = get_db()
    render_dataset(session)
    runs = db.get_runs(session.id)
    messages = db.get_messages(session.id)
    st.write("")

    pending = st.session_state.pop("pending_question", None)
    for run in runs:
        trail = [m for m in messages if m["run_no"] == run["run_no"]]
        clicked = render_run(session, run, trail, is_latest=run is runs[-1])
        pending = pending or clicked

    # Suggested questions (sample catalog for a fresh session).
    sample = get_sample(session.sample_id) if session.sample_id else None
    if not runs and not pending:
        with st.container(border=True):
            st.markdown("**Ask a business question**")
            st.caption("Type your own question below, or start with one of these:")
            for i, q in enumerate(sample.questions if sample else [
                "Summarise the key trends in this data with one chart.",
                "Which segment changed the most between the last two months, and why?",
            ]):
                if st.button(q, key=f"sq_{i}", width="stretch"):
                    pending = q

    question = st.chat_input("Ask a follow-up question…" if runs else "Ask a business question about this data…")
    question = (question or pending or "").strip()
    if question:
        if runs:
            last = runs[-1]
            if not last.get("human_verdict"):
                db.set_human_verdict(session.id, last["run_no"], "follow_up")
        if not settings.openai_api_key:
            st.error("OPENAI_API_KEY is not configured on the server.")
            return
        run_live(session, question)

    with st.sidebar:
        st.divider()
        if st.button("＋ New analysis", width="stretch"):
            close_session()
            st.rerun()
