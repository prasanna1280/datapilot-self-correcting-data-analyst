"""DataPilot - Streamlit entry point (navigation, sign-in, sidebar).

Run locally:  streamlit run frontend/app.py
"""

from __future__ import annotations

import hmac
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from backend.datapilot import __version__  # noqa: E402
from backend.datapilot.config import settings  # noqa: E402
from frontend import state, theme  # noqa: E402
from frontend.views import guide, history, samples, workspace  # noqa: E402

st.set_page_config(page_title="DataPilot · Self-Correcting Data Analyst", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
theme.inject()


def sign_in() -> None:
    """Optional shared password (APP_PASSWORD) so a public URL can't spend the OpenAI budget."""
    if not settings.app_password or st.session_state.get("authed"):
        return
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.write("")
        st.markdown('<div class="dp-brand" style="border:none;justify-content:center;margin-top:8vh">'
                    '<div class="dp-logo">DP</div><div><b>DataPilot</b><span>Self-Correcting Data Analyst</span></div></div>',
                    unsafe_allow_html=True)
        with st.form("login", border=True):
            st.markdown("##### Sign in")
            pwd = st.text_input("Access password", type="password")
            if st.form_submit_button("Continue", type="primary", width="stretch"):
                if hmac.compare_digest(pwd, settings.app_password):
                    st.session_state.authed = True
                    st.rerun()
                st.error("Incorrect password.")
        st.caption("Access is restricted. Contact the owner for a password.")
    st.stop()


def sidebar() -> None:
    st.logo(str(ROOT / "frontend" / "assets" / "logo.svg"), size="large")


def sidebar_footer() -> None:
    with st.sidebar:
        st.divider()
        st.markdown(
            f"<div class='dp-muted' style='font-size:.76rem;line-height:1.7'>"
            f"<b>Model</b> {theme.esc(settings.model)}<br>"
            f"<b>Executor</b> {'Docker sandbox' if settings.executor_mode == 'sandbox' else 'Local sandbox folder'}<br>"
            f"<b>Limits</b> {settings.max_messages} messages · {settings.code_timeout_s}s/script<br>"
            f"<b>Version</b> {__version__}</div>", unsafe_allow_html=True)
        if settings.app_password and st.button("Sign out", width="stretch"):
            st.session_state.clear()
            st.rerun()


sign_in()
sidebar()
pages = {
    "workspace": st.Page(workspace.view, title="Workspace", icon=":material/insights:", url_path="workspace", default=True),
    "samples": st.Page(samples.view, title="Sample datasets", icon=":material/dataset:", url_path="samples"),
    "history": st.Page(history.view, title="Run history", icon=":material/history:", url_path="history"),
    "guide": st.Page(guide.view, title="How it works", icon=":material/menu_book:", url_path="guide"),
}
state.PAGES.update(pages)
nav = st.navigation({"Analysis": [pages["workspace"], pages["samples"]], "Governance": [pages["history"], pages["guide"]]})
nav.run()
sidebar_footer()
