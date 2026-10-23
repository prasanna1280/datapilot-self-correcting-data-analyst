"""Run History: every analysis session and its outcome."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.state import get_db, open_session
from frontend.theme import page_header

STATUS = {"approved": "✓ Approved", "limit": "⚠ Stopped at limit", "error": "✕ Failed", "running": "… Running"}


def view() -> None:
    page_header("Run history", "All analysis sessions, newest first. Open one to review or continue it.", "Audit")
    rows = get_db().list_sessions(limit=200)
    if not rows:
        st.info("No sessions yet. Start one from the Workspace or the Sample datasets page.")
        return
    df = pd.DataFrame([{
        "Created (UTC)": r["created_at"], "Dataset": r["dataset_name"], "Rows": r["dataset_rows"],
        "Currency": r.get("currency") or "", "Questions": r["n_runs"], "Approved": r["n_approved"] or 0,
        "Errors self-fixed": r["n_fixes"] or 0, "Last status": STATUS.get(r["last_status"] or "", "—"),
        "First question": r["first_question"] or "—", "Session": r["id"][:8],
    } for r in rows])

    total_runs = int(df["Questions"].sum())
    c = st.columns(4)
    c[0].metric("Sessions", f"{len(df):,}")
    c[1].metric("Questions asked", f"{total_runs:,}")
    c[2].metric("Approved answers", f"{int(df['Approved'].sum()):,}")
    c[3].metric("Code errors self-fixed", f"{int(df['Errors self-fixed'].sum()):,}")
    st.write("")

    event = st.dataframe(df, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row",
                         column_config={"Rows": st.column_config.NumberColumn(format="localized"),
                                        "First question": st.column_config.TextColumn(width="large")})
    selected = event.selection.rows if event and event.selection else []
    if selected:
        r = rows[selected[0]]
        if st.button(f"Open session {r['id'][:8]} · {r['dataset_name']}", type="primary"):
            open_session(r["id"])
    else:
        st.caption("Select a row to open that session.")
