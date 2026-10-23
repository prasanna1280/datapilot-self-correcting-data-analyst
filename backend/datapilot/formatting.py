"""Reporting standards: currency (ISO 4217), number style and dates (ISO 8601).

The standard is chosen per session (auto-detected from column names, overridable in
the UI) and injected into the task, so the Coder prints and labels numbers the same way.
"""

from __future__ import annotations

import re
from typing import Iterable

CURRENCIES = {
    "USD": "US dollar", "EUR": "Euro", "GBP": "Pound sterling", "INR": "Indian rupee",
    "JPY": "Japanese yen", "AUD": "Australian dollar", "SGD": "Singapore dollar", "AED": "UAE dirham",
}
NUMBER_STYLES = {
    "international": "International — K / M / B (e.g. USD 1.84M)",
    "indian": "Indian — lakh / crore (e.g. INR 18.4 L)",
}
_CURRENCY_RE = re.compile(r"(?:^|_)(usd|eur|gbp|inr|jpy|aud|sgd|aed)(?:$|_)", re.IGNORECASE)


def detect_currency(columns: Iterable[str]) -> str | None:
    """Find an ISO 4217 code in column names like `unit_price_usd` or `mrr_eur`."""
    for col in columns:
        m = _CURRENCY_RE.search(str(col))
        if m:
            return m.group(1).upper()
    return None


def reporting_standard(currency: str, number_style: str) -> str:
    """Text block appended to the task so every agent formats numbers the same way."""
    if number_style == "indian":
        money = (f"Money in {currency} using Indian units: 1 lakh (L) = 100,000 and 1 crore (Cr) = 10,000,000. "
                 f'Write amounts like "{currency} 18.4 L" or "{currency} 2.1 Cr"; chart axes in "{currency} lakh".')
    else:
        money = (f"Money in {currency} (ISO 4217 code before the number) with international units: "
                 f'K = thousand, M = million, B = billion. Write amounts like "{currency} 1.84M" or "{currency} 912.5K"; '
                 f'chart axes like "Net revenue ({currency} M)".')
    return "\n".join([
        "REPORTING STANDARD (follow exactly):",
        f"- {money}",
        "- Other numbers: comma thousands separator, point as decimal mark (12,480; 3.5). Percentages with one decimal and a % sign (28.8%). Percentage-point changes as 'pp'.",
        "- Dates in ISO 8601: YYYY-MM-DD for days, YYYY-MM for months, YYYY-Qn for quarters.",
        "- Units in every label (kg, days, seats, %, currency code).",
    ])


def money(value: float, currency: str = "USD", number_style: str = "international") -> str:
    """Format a number for UI tiles following the same standard."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if number_style == "indian":
        if v >= 1e7:
            return f"{sign}{currency} {v / 1e7:,.2f} Cr"
        if v >= 1e5:
            return f"{sign}{currency} {v / 1e5:,.1f} L"
        return f"{sign}{currency} {v:,.0f}"
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= div:
            return f"{sign}{currency} {v / div:,.2f}{suffix}"
    return f"{sign}{currency} {v:,.0f}"
