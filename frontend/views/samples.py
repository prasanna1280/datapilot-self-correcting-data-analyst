"""Sample Datasets gallery."""

from __future__ import annotations

import streamlit as st

from backend.datapilot.catalog import load_catalog
from backend.datapilot.data_loader import list_sheets
from frontend import components as ui
from frontend.state import load_sample_frame, start_from_sample
from frontend.theme import chip, esc, page_header

MIME = {".csv": "text/csv", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


@st.cache_data(show_spinner=False)
def _stats(sample_id: str) -> dict:
    sample = next(s for s in load_catalog() if s.id == sample_id)
    df = load_sample_frame(sample)
    sheets = list_sheets(sample.path.read_bytes()) if sample.file.endswith(".xlsx") else []
    return {"rows": len(df), "cols": len(df.columns), "period": ui.date_range(df), "sheets": sheets,
            "columns": ", ".join(map(str, df.columns)), "head": df.head(8)}


def view() -> None:
    page_header("Sample datasets", "International-standard demo data: ISO 8601 dates, ISO 3166 country codes, "
                "ISO 4217 currencies, snake_case columns, one row per business event.", "Library")
    catalog = load_catalog()
    if not catalog:
        st.warning("No catalog found. Run `python scripts/generate_sample_data.py`.")
        return
    cols = st.columns(2, gap="medium")
    for i, sample in enumerate(catalog):
        stats = _stats(sample.id)
        with cols[i % 2], st.container(border=True):
            fmt = "Lakh / crore" if sample.number_style == "indian" else "K / M / B"
            meta = [chip(sample.domain, "brand"), chip(sample.currency, "neutral"), chip(fmt, "neutral"),
                    chip(f"{stats['rows']:,} rows × {stats['cols']} cols", "neutral")]
            if stats["sheets"]:
                meta.append(chip(f"{len(stats['sheets'])} sheets: {', '.join(stats['sheets'])}", "info"))
            questions = "".join(f"<li>{esc(q)}</li>" for q in sample.questions)
            st.markdown(
                f'<div class="dp-ds"><h4>{esc(sample.title)}</h4><div class="dp-muted">{esc(sample.description)}</div>'
                f'<div class="meta">{"".join(meta)}</div>'
                f'<div class="dp-muted"><b>Period:</b> {esc(stats["period"])} &nbsp;·&nbsp; <b>File:</b> '
                f'<code>{esc(sample.file)}</code></div>'
                f'<div class="dp-muted" style="margin-top:8px"><b>Try asking</b></div><ul>{questions}</ul></div>',
                unsafe_allow_html=True)
            with st.expander("Columns & preview"):
                st.caption(stats["columns"])
                st.dataframe(stats["head"], width="stretch", hide_index=True)
            c1, c2 = st.columns(2)
            if c1.button("Analyse in workspace", key=f"open_{sample.id}", type="primary", width="stretch"):
                start_from_sample(sample)
            c2.download_button("Download file", sample.path.read_bytes(), sample.file,
                               MIME.get(sample.path.suffix, "application/octet-stream"),
                               key=f"dl_{sample.id}", width="stretch")
