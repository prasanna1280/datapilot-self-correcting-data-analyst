"""Session-level helpers shared by the pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from backend.datapilot.catalog import SampleDataset
from backend.datapilot.config import settings
from backend.datapilot.data_loader import ALL_SHEETS, read_upload
from backend.datapilot.runner import AnalysisSession
from database import Database

PAGES: dict[str, object] = {}  # filled by app.py: name -> st.Page


@st.cache_resource
def get_db() -> Database:
    return Database(settings.db_path)


def current_session() -> AnalysisSession | None:
    sid = st.session_state.get("session_id") or st.query_params.get("session")
    if not sid:
        return None
    session = AnalysisSession.load(get_db(), sid)
    if session:
        st.session_state.session_id = sid
    return session


def open_session(session_id: str) -> None:
    st.session_state.session_id = session_id
    st.query_params["session"] = session_id
    if "workspace" in PAGES:
        st.switch_page(PAGES["workspace"])
    st.rerun()


def close_session() -> None:
    st.session_state.pop("session_id", None)
    st.query_params.clear()


def load_sample_frame(sample: SampleDataset) -> pd.DataFrame:
    return read_upload(sample.file, sample.path.read_bytes(), ALL_SHEETS)


def start_from_sample(sample: SampleDataset) -> None:
    session = AnalysisSession.create(get_db(), load_sample_frame(sample), sample.file, currency=sample.currency,
                                     number_style=sample.number_style, sample_id=sample.id)
    open_session(session.id)


def start_from_frame(df: pd.DataFrame, name: str, currency: str | None, number_style: str) -> None:
    session = AnalysisSession.create(get_db(), df, name, currency=currency, number_style=number_style)
    open_session(session.id)
