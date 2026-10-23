"""How it works: the agents, the loop, the outputs and the standards."""

from __future__ import annotations

import streamlit as st

from backend.datapilot.config import settings
from frontend import components as ui
from frontend.theme import page_header


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table class='dp-table'><tr>{th}</tr>{trs}</table>"


def view() -> None:
    page_header("How DataPilot works", "Ask a business question in plain English. A team of agents plans, writes "
                "Python, runs it, fixes its own errors and returns the answer with charts.", "Guide")

    st.markdown("#### The six steps")
    st.markdown(ui.steps_overview_html(), unsafe_allow_html=True)
    st.caption("Loop: if step 04 returns an error, or step 05 is not satisfied, the conversation goes back to step 03 "
               "automatically. No human is needed to fix code.")

    st.markdown("#### The agent team")
    st.markdown(_table(["Agent", "Job", "AutoGen component"], [
        ["<b>Planner</b>", "Reads the question and the data columns, then writes a short step-by-step analysis plan.", "AssistantAgent"],
        ["<b>Coder</b>", "Writes Python (pandas + matplotlib) for the plan. Rewrites the code when it gets an error.", "AssistantAgent"],
        ["<b>Executor</b>", "Runs the code safely in a sandbox and returns output or errors.", "CodeExecutorAgent + sandbox container"],
        ["<b>Reviewer</b>", "Does the result answer the question? Are numbers sensible? Are charts labelled? Replies APPROVED or sends feedback.", "AssistantAgent"],
        ["<b>User Proxy</b>", "The human. Approves the final answer or asks a follow-up question.", "Approve / Reject buttons · UserProxyAgent (CLI)"],
    ]), unsafe_allow_html=True)

    st.write("")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Outputs explained")
        st.markdown(_table(["Output", "What it means", "Why it matters"], [
            ["<b>Agent conversation</b>", "The full trail: plan, code, errors, fixes, review", "Proves the answer was calculated"],
            ["<b>ERROR then Fixed</b>", "The Coder read the error and repaired its own code", "The agentic loop: no human debugging"],
            ["<b>Reviewer feedback</b>", "A quality check before the user sees anything", "Catches weak charts or wrong answers"],
            ["<b>Final answer</b>", "Plain-English result with exact numbers and the cause", "The owner can act immediately"],
            ["<b>Charts + analysis.py</b>", "Visual proof and re-runnable code", "Anyone can re-run it and get the same numbers"],
        ]), unsafe_allow_html=True)
    with c2:
        st.markdown("#### Standards & safety")
        st.markdown(_table(["Area", "Standard"], [
            ["<b>Dates</b>", "ISO 8601 — YYYY-MM-DD, YYYY-MM, YYYY-Qn"],
            ["<b>Currency</b>", "ISO 4217 code before the amount (USD 1.84M)"],
            ["<b>Numbers</b>", "International K/M/B or Indian lakh/crore, per dataset"],
            ["<b>Charts</b>", "One house style; title, axis labels and units on every chart"],
            ["<b>Limits</b>", f"Stops on APPROVED or after {settings.max_messages} messages; {settings.code_timeout_s}s per script"],
            ["<b>Sandbox</b>", "Separate container: no API keys, no internet, read-only, CPU/RAM capped"],
            ["<b>Code gate</b>", "Static check blocks subprocess, env access, network, files outside the session"],
        ]), unsafe_allow_html=True)

    st.write("")
    st.markdown("#### Tech stack")
    st.markdown(_table(["Part", "Use"], [
        ["<b>AssistantAgent</b>", "Planner, Coder, Reviewer with system messages"],
        ["<b>Code executor</b>", "CodeExecutorAgent with a Docker sandbox (production) or local folder (development)"],
        ["<b>Team</b>", "SelectorGroupChat with a deterministic speaker selector (RoundRobinGroupChat optional)"],
        ["<b>Termination</b>", "TextMentionTermination('APPROVED') | MaxMessageTermination(12)"],
        ["<b>Human-in-the-loop</b>", "Approval step in the UI; UserProxyAgent in the CLI"],
        ["<b>Data</b>", f"pandas, matplotlib · model <code>{settings.model}</code> · SQLite audit trail"],
    ]), unsafe_allow_html=True)
