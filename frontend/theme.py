"""Design system: tokens + global CSS for the Streamlit app.

Neutral enterprise palette (slate) with the DataPilot brand accent from the spec (maroon).
Status colours are reserved for state (success / warning / danger / info) and always come
with an icon + label, never colour alone.
"""

from __future__ import annotations

import html

import streamlit as st

TOKENS = {
    "brand": "#7A1F2B", "brand_soft": "#F8EDEE", "brand_ink": "#5C1520",
    "ink": "#0F172A", "ink_2": "#334155", "muted": "#64748B", "border": "#E2E8F0", "border_2": "#CBD5E1",
    "canvas": "#F5F6F8", "surface": "#FFFFFF", "terminal": "#0F1720",
    "success": "#067647", "success_bg": "#ECFDF3", "warning": "#B54708", "warning_bg": "#FFFAEB",
    "danger": "#B42318", "danger_bg": "#FEF3F2", "info": "#175CD3", "info_bg": "#EFF8FF",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
  --brand:#7A1F2B; --brand-soft:#F8EDEE; --brand-ink:#5C1520;
  --ink:#0F172A; --ink-2:#334155; --muted:#64748B; --border:#E2E8F0; --border-2:#CBD5E1;
  --canvas:#F5F6F8; --surface:#FFFFFF; --terminal:#0F1720;
  --ok:#067647; --ok-bg:#ECFDF3; --warn:#B54708; --warn-bg:#FFFAEB; --bad:#B42318; --bad-bg:#FEF3F2;
  --info:#175CD3; --info-bg:#EFF8FF;
  --radius:10px; --shadow:0 1px 2px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.04);
}
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
code, pre, .dp-term { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace !important; }
.stApp { background: var(--canvas); }
.block-container { padding-top: 1.4rem; padding-bottom: 6rem; max-width: 1280px; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.01em; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: var(--radius); }
div[data-testid="stExpander"] details { border-radius: var(--radius); border-color: var(--border); background: var(--surface); }
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { padding: 8px 14px; font-weight: 500; }
div[data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 14px; box-shadow: var(--shadow); }
div[data-testid="stMetricLabel"] p { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }
div[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 600; color: var(--ink); }

/* ---------- page header ---------- */
.dp-page { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; margin: 0 0 14px; }
.dp-page h1 { font-size: 1.45rem; font-weight: 700; margin: 0; padding: 0; }
.dp-page .sub { color: var(--muted); font-size: .9rem; margin-top: 2px; }
.dp-crumb { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }

/* ---------- brand block (sidebar) ---------- */
.dp-brand { display:flex; gap:10px; align-items:center; padding: 4px 2px 12px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.dp-logo { width:36px; height:36px; border-radius:9px; background: var(--brand); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.95rem; }
.dp-brand b { display:block; color: var(--ink); font-size: .98rem; }
.dp-brand span { color: var(--muted); font-size: .74rem; }

/* ---------- chips / badges ---------- */
.dp-chip { display:inline-flex; align-items:center; gap:5px; font-size:.72rem; font-weight:600; padding:2px 9px; border-radius:999px; border:1px solid transparent; white-space:nowrap; letter-spacing:.02em; }
.dp-chip.ok { color:var(--ok); background:var(--ok-bg); border-color:#ABEFC6; }
.dp-chip.warn { color:var(--warn); background:var(--warn-bg); border-color:#FEDF89; }
.dp-chip.bad { color:var(--bad); background:var(--bad-bg); border-color:#FECDCA; }
.dp-chip.info { color:var(--info); background:var(--info-bg); border-color:#B2DDFF; }
.dp-chip.neutral { color:var(--ink-2); background:#F1F5F9; border-color: var(--border); }
.dp-chip.brand { color:var(--brand); background:var(--brand-soft); border-color:#EBC8CC; }

/* ---------- cards ---------- */
.dp-card { background: var(--surface); border:1px solid var(--border); border-radius: var(--radius); padding: 16px 18px; box-shadow: var(--shadow); }
.dp-card h4 { margin: 0 0 4px; font-size: 1rem; }
.dp-muted { color: var(--muted); font-size: .85rem; }
.dp-kv { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.dp-kv div { background: var(--surface); border:1px solid var(--border); border-radius: var(--radius); padding: 10px 14px; box-shadow: var(--shadow); }
.dp-kv small { display:block; color: var(--muted); font-size:.7rem; font-weight:600; text-transform:uppercase; letter-spacing:.05em; }
.dp-kv b { display:block; color: var(--ink); font-size: 1rem; font-weight:600; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* ---------- 6-step pipeline ---------- */
.dp-steps { display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 8px; margin: 6px 0 4px; }
.dp-step { position:relative; background: var(--surface); border:1px solid var(--border); border-radius: var(--radius); padding: 10px 12px 11px; min-height: 96px; }
.dp-step .n { font-size:.7rem; font-weight:700; color: var(--muted); letter-spacing:.06em; }
.dp-step .t { font-size:.95rem; font-weight:700; color: var(--ink); margin-top:1px; }
.dp-step .c { font-size:.72rem; color: var(--muted); line-height:1.3; margin-top:2px; }
.dp-step .s { margin-top:7px; font-size:.72rem; font-weight:600; display:flex; align-items:center; gap:5px; }
.dp-step .dot { width:8px; height:8px; border-radius:50%; background: var(--border-2); flex: none; }
.dp-step.done { border-color:#ABEFC6; } .dp-step.done .s { color: var(--ok); } .dp-step.done .dot { background: var(--ok); }
.dp-step.active { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(122,31,43,.10); } .dp-step.active .s { color: var(--brand); }
.dp-step.active .dot { background: var(--brand); animation: dp-pulse 1.1s ease-in-out infinite; }
.dp-step.retry { border-color:#FEDF89; background: #FFFDF5; } .dp-step.retry .s { color: var(--warn); } .dp-step.retry .dot { background: var(--warn); }
.dp-step.error { border-color:#FECDCA; background:#FFFBFA; } .dp-step.error .s { color: var(--bad); } .dp-step.error .dot { background: var(--bad); }
.dp-step.waiting { border-color:#B2DDFF; } .dp-step.waiting .s { color: var(--info); } .dp-step.waiting .dot { background: var(--info); }
.dp-step.pending .s { color: var(--muted); }
.dp-step:not(:last-child)::after { content:'›'; position:absolute; right:-9px; top: 36px; color: var(--border-2); font-weight:700; font-size: 1.1rem; z-index: 2; }
@keyframes dp-pulse { 0%,100% { opacity: 1; transform: scale(1);} 50% { opacity: .35; transform: scale(.75);} }
.dp-loop { font-size:.75rem; color: var(--muted); margin: 2px 2px 0; }
@media (max-width: 900px) { .dp-steps { grid-template-columns: repeat(3, minmax(0,1fr)); } .dp-step::after { display:none; } }

/* ---------- terminal transcript (Part A) ---------- */
.dp-term { background: var(--terminal); color:#D7DEE7; border-radius: var(--radius); padding: 14px 16px; font-size: .8rem; line-height: 1.65; overflow-x:auto; }
.dp-term .row { display:grid; grid-template-columns: 78px 14px 1fr 54px; gap: 4px; }
.dp-term .who { font-weight:600; } .dp-term .sep { color:#5B6B7C; }
.dp-term .t { color:#5B6B7C; text-align:right; font-size:.72rem; }
.dp-term .Planner { color:#7CC4FF; } .dp-term .Coder { color:#C7A6FF; } .dp-term .Executor { color:#FFD27A; }
.dp-term .Reviewer { color:#7EE2B8; } .dp-term .user { color:#E5E7EB; }
.dp-term .err { color:#FF8A80; font-weight:600; } .dp-term .ok { color:#7EE2B8; font-weight:600; } .dp-term .appr { color:#7EE2B8; font-weight:700; }
.dp-term .fb { color:#FFD27A; }
.dp-term .cursor { display:inline-block; width:7px; height:14px; background:#D7DEE7; vertical-align:-2px; animation: dp-pulse 1s steps(2) infinite; }

/* ---------- final answer (Part B) ---------- */
.dp-answer { background: var(--surface); border:1px solid var(--border); border-left: 4px solid var(--brand); border-radius: var(--radius); padding: 16px 20px; box-shadow: var(--shadow); }
.dp-answer .lbl { font-size:.7rem; font-weight:700; letter-spacing:.08em; color: var(--brand); text-transform: uppercase; margin: 12px 0 4px; }
.dp-answer .lbl:first-child { margin-top: 0; }
.dp-answer .headline { font-size: 1.05rem; font-weight: 600; color: var(--ink); line-height: 1.5; }
.dp-answer .body { color: var(--ink-2); font-size: .93rem; line-height: 1.6; white-space: pre-wrap; }
.dp-files { display:flex; flex-wrap:wrap; gap:6px; }
.dp-file { font-family:'JetBrains Mono', monospace; font-size:.75rem; background:#F1F5F9; border:1px solid var(--border); border-radius:6px; padding:2px 8px; color: var(--ink-2); }

/* ---------- quality gates ---------- */
.dp-gates { display:flex; flex-direction:column; gap: 6px; }
.dp-gate { display:grid; grid-template-columns: 26px 1fr auto; align-items:center; gap: 10px; background: var(--surface); border:1px solid var(--border); border-radius: 8px; padding: 9px 12px; }
.dp-gate .ic { width:22px; height:22px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:.8rem; font-weight:700; }
.dp-gate.pass .ic { background: var(--ok-bg); color: var(--ok); } .dp-gate.fail .ic { background: var(--bad-bg); color: var(--bad); }
.dp-gate.info .ic { background: var(--info-bg); color: var(--info); } .dp-gate.pending .ic { background:#F1F5F9; color: var(--muted); }
.dp-gate b { color: var(--ink); font-size: .88rem; font-weight:600; } .dp-gate span { color: var(--muted); font-size:.8rem; }

/* ---------- run header ---------- */
.dp-run { display:flex; justify-content:space-between; align-items:flex-start; gap: 12px; }
.dp-run .q { font-size: 1.05rem; font-weight: 600; color: var(--ink); line-height: 1.4; }
.dp-run .meta { color: var(--muted); font-size: .8rem; margin-top: 3px; }
.dp-runno { font-size:.72rem; font-weight:700; color: var(--brand); letter-spacing:.06em; text-transform: uppercase; }

/* ---------- dataset gallery ---------- */
.dp-ds h4 { margin: 6px 0 2px; font-size: 1.02rem; }
.dp-ds .meta { display:flex; flex-wrap:wrap; gap: 6px; margin: 8px 0 6px; }
.dp-ds ul { margin: 6px 0 0 1rem; padding: 0; color: var(--ink-2); font-size: .84rem; }
.dp-ds li { margin-bottom: 3px; }

/* ---------- tables ---------- */
.dp-table { width:100%; border-collapse: separate; border-spacing: 0; background: var(--surface); border:1px solid var(--border); border-radius: var(--radius); overflow:hidden; font-size:.86rem; }
.dp-table th { background:#F8FAFC; color: var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; text-align:left; padding: 9px 12px; border-bottom:1px solid var(--border); }
.dp-table td { padding: 9px 12px; border-bottom:1px solid var(--border); color: var(--ink-2); vertical-align: top; }
.dp-table tr:last-child td { border-bottom: none; }
.dp-table td b { color: var(--ink); }

/* buttons */
.stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 500; }
.stButton > button[kind="primary"] { background: var(--brand); border-color: var(--brand); }
.stButton > button[kind="primary"]:hover { background: var(--brand-ink); border-color: var(--brand-ink); }
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text: object) -> str:
    return html.escape(str(text))


def chip(text: str, tone: str = "neutral") -> str:
    return f'<span class="dp-chip {tone}">{esc(text)}</span>'


def page_header(title: str, subtitle: str = "", crumb: str = "", right_html: str = "") -> None:
    crumb_html = f'<div class="dp-crumb">{esc(crumb)}</div>' if crumb else ""
    sub = f'<div class="sub">{esc(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="dp-page"><div>{crumb_html}<h1>{esc(title)}</h1>{sub}</div><div>{right_html}</div></div>',
                unsafe_allow_html=True)


def kv_tiles(items: list[tuple[str, str]]) -> None:
    cells = "".join(f"<div><small>{esc(k)}</small><b title=\"{esc(v)}\">{esc(v)}</b></div>" for k, v in items)
    st.markdown(f'<div class="dp-kv">{cells}</div>', unsafe_allow_html=True)


STATUS_CHIP = {
    "approved": ("APPROVED", "ok"), "limit": ("STOPPED AT LIMIT", "warn"), "error": ("FAILED", "bad"),
    "running": ("RUNNING", "brand"),
}
