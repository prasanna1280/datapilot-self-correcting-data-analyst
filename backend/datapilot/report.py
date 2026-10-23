"""One-page PDF report: question, approved answer and charts (stretch goal)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

_REPLACEMENTS = {"₹": "Rs ", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-", "…": "..."}


def _latin1(text: str) -> str:
    """Core PDF fonts are latin-1 only; map common unicode and drop the rest."""
    for k, v in _REPLACEMENTS.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf(question: str, answer: str, charts: list[Path], dataset_name: str = "") -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_fill_color(110, 18, 22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(width, 11, _latin1("  DataPilot - Analysis Report"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(90, 90, 90)
    pdf.set_font("Helvetica", "", 8)
    meta = f"Generated {datetime.now():%Y-%m-%d %H:%M}" + (f"  |  Dataset: {dataset_name}" if dataset_name else "")
    pdf.cell(width, 6, _latin1(meta), new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(width, 5, _latin1(f"Question: {question}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for line in answer.strip().splitlines():
        heading = line.strip().isupper() and len(line.strip()) < 40
        pdf.set_font("Helvetica", "B" if heading else "", 9.5 if heading else 9)
        pdf.multi_cell(width, 4.6, _latin1(line) or " ", new_x="LMARGIN", new_y="NEXT")

    images = [c for c in charts if c.exists()][:2]
    if images:
        pdf.ln(2)
        gap = 4
        img_w = (width - gap) / 2 if len(images) == 2 else width * 0.7
        y = pdf.get_y()
        room = pdf.h - pdf.b_margin - y
        for i, img in enumerate(images):
            x = pdf.l_margin + i * (img_w + gap)
            pdf.image(str(img), x=x, y=y, w=img_w, h=min(room, img_w * 0.75), keep_aspect_ratio=True)
    return bytes(pdf.output())
