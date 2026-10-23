"""One-page PDF report: question, approved answer, run metadata and charts (stretch goal)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from .progress import parse_answer

_REPLACEMENTS = {"₹": "INR ", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-", "…": "...",
                 "→": "->", "€": "EUR ", "£": "GBP ", "×": "x"}
BRAND = (122, 31, 43)
INK = (15, 23, 42)
MUTED = (100, 116, 139)
RULE = (226, 232, 240)


def _latin1(text: str) -> str:
    """Core PDF fonts are latin-1 only; map common unicode and drop the rest."""
    for k, v in _REPLACEMENTS.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    footer_text = ""

    def footer(self) -> None:
        self.set_y(-11)
        self.set_draw_color(*RULE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 6, _latin1(self.footer_text), align="L")
        self.cell(0, 6, f"Page {self.page_no()}", align="R")


def build_pdf(question: str, answer: str, charts: list[Path], dataset_name: str = "",
              meta: dict[str, str] | None = None) -> bytes:
    pdf = _Report(orientation="P", unit="mm", format="A4")
    pdf.set_margins(14, 12, 14)
    pdf.set_auto_page_break(auto=True, margin=14)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.footer_text = f"DataPilot - Self-Correcting Data Analyst  |  Generated {generated}  |  Numbers computed by code, reviewed by agents"
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    # Header band
    pdf.set_fill_color(*BRAND)
    pdf.rect(0, 0, pdf.w, 22, style="F")
    pdf.set_xy(pdf.l_margin, 6)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(width * 0.7, 7, "DataPilot  |  Analysis Report")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(width * 0.3, 7, _latin1(generated), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(width, 5, _latin1(f"Dataset: {dataset_name}" if dataset_name else ""), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(27)

    # Question
    pdf.set_text_color(*MUTED)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.cell(width, 4, "BUSINESS QUESTION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(width, 5.4, _latin1(question), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Metadata strip
    if meta:
        items = list(meta.items())[:6]
        col_w = width / len(items)
        y = pdf.get_y()
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(*RULE)
        pdf.rect(pdf.l_margin, y, width, 11, style="DF")
        for i, (k, v) in enumerate(items):
            pdf.set_xy(pdf.l_margin + i * col_w + 2.5, y + 1.6)
            pdf.set_font("Helvetica", "B", 6.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(col_w - 3, 3.2, _latin1(k.upper()))
            pdf.set_xy(pdf.l_margin + i * col_w + 2.5, y + 5.2)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*INK)
            pdf.cell(col_w - 3, 4, _latin1(v))
        pdf.set_y(y + 14)

    # Answer sections
    parts = parse_answer(answer)
    for key, label in (("ANSWER", "Answer"), ("WHERE IT CAME FROM", "Where it came from"),
                       ("SUGGESTED NEXT QUESTION", "Suggested next question")):
        if not parts.get(key):
            continue
        pdf.set_text_color(*BRAND)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(width, 4.5, label.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        pdf.set_font("Helvetica", "B" if key == "ANSWER" else "", 10 if key == "ANSWER" else 9.2)
        pdf.multi_cell(width, 4.8, _latin1(parts[key]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Charts (two side by side, scaled to fit the page)
    images = [c for c in charts if c.exists()][:2]
    if images:
        pdf.set_text_color(*BRAND)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(width, 4.5, "CHARTS", new_x="LMARGIN", new_y="NEXT")
        gap = 4
        img_w = (width - gap) / 2 if len(images) == 2 else width * 0.75
        y = pdf.get_y() + 1
        room = pdf.h - pdf.b_margin - y - 6
        h = min(room, img_w * 0.62)
        for i, img in enumerate(images):
            x = pdf.l_margin + i * (img_w + gap)
            pdf.set_draw_color(*RULE)
            pdf.rect(x, y, img_w, h)
            pdf.image(str(img), x=x + 1, y=y + 1, w=img_w - 2, h=h - 2, keep_aspect_ratio=True)
            pdf.set_xy(x, y + h + 0.5)
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(img_w, 3.5, _latin1(img.name))
    return bytes(pdf.output())
