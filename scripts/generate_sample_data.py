"""Generate the demo dataset: data/sample/sales_2026.csv (+ a multi-sheet .xlsx).

One year of retail orders (Oct 2025 - Sep 2026), ~12,480 rows, matching the
spec columns: order_date,region,category,product,units,unit_price,discount.

A story is baked in so the sample question has a real answer: Electronics
revenue drops sharply in September 2026 vs August, mostly in the South region,
driven by "Earbuds X2" and "Smartwatch Lite".

Run:  python scripts/generate_sample_data.py
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 2026
TARGET_ROWS = 12_480
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"

REGIONS = {"North": 1.0, "South": 1.15, "East": 0.85, "West": 0.95}

# category -> [(product, unit_price_in_rupees, popularity_weight)]
CATALOG = {
    "Electronics": [
        ("Earbuds X2", 1999, 3.0),
        ("Smartwatch Lite", 3499, 2.0),
        ("Power Bank 20K", 1499, 2.0),
        ("BT Speaker Mini", 2499, 1.5),
        ("USB-C Charger 65W", 1299, 1.5),
    ],
    "Grocery": [
        ("Millet Mix 1kg", 249, 3.0),
        ("Basmati Rice 5kg", 699, 2.5),
        ("Cold Pressed Oil 1L", 389, 2.0),
        ("Masala Tea 500g", 299, 2.0),
    ],
    "Fashion": [
        ("Cotton Kurta", 899, 2.5),
        ("Denim Jeans", 1499, 2.0),
        ("Running Shoes", 2799, 1.5),
    ],
    "Home & Kitchen": [
        ("Steel Bottle 1L", 549, 2.5),
        ("Non-stick Pan", 1199, 1.5),
        ("Mixer Grinder", 3299, 1.0),
    ],
    "Beauty": [
        ("Aloe Face Wash", 199, 3.0),
        ("Sunscreen SPF50", 449, 2.0),
        ("Hair Serum", 599, 1.5),
    ],
}

UNITS_RANGE = {
    "Electronics": (3, 18),
    "Grocery": (10, 60),
    "Fashion": (2, 15),
    "Home & Kitchen": (2, 14),
    "Beauty": (5, 40),
}

# Festive-season lift (Oct/Nov) and a mild summer dip.
MONTH_FACTOR = {10: 1.25, 11: 1.3, 12: 1.1, 1: 0.95, 2: 0.9, 3: 1.0,
                4: 0.95, 5: 0.9, 6: 0.92, 7: 1.0, 8: 1.05, 9: 1.0}


def _weighted(rng: random.Random, items: dict[str, float] | list[tuple]) -> object:
    if isinstance(items, dict):
        keys, weights = list(items), list(items.values())
    else:
        keys, weights = [i[0] for i in items], [i[-1] for i in items]
    return rng.choices(keys, weights=weights, k=1)[0]


def _september_shock(d: date, region: str, product: str) -> tuple[float, float]:
    """Return (keep_probability, extra_discount) for the Sep-2026 Electronics drop."""
    if not (d.year == 2026 and d.month == 9):
        return 1.0, 0.0
    if region == "South" and product in ("Earbuds X2", "Smartwatch Lite"):
        return 0.12, 0.10   # stock-out + heavy discounting in the South
    if region == "South" and product in ("Power Bank 20K", "BT Speaker Mini"):
        return 0.80, 0.0
    if product in ("Earbuds X2", "Smartwatch Lite"):
        return 0.90, 0.0
    return 1.0, 0.0


def generate(rows: int = TARGET_ROWS, seed: int = SEED) -> pd.DataFrame:
    rng = random.Random(seed)
    start, end = date(2025, 10, 1), date(2026, 9, 30)
    days = (end - start).days + 1
    day_weights = [MONTH_FACTOR[(start + timedelta(i)).month] for i in range(days)]

    records: list[dict] = []
    while len(records) < rows:
        d = start + timedelta(days=rng.choices(range(days), weights=day_weights, k=1)[0])
        region = _weighted(rng, REGIONS)
        category = rng.choices(list(CATALOG), weights=[1.4, 1.6, 1.0, 0.9, 1.1], k=1)[0]
        product, price, _ = rng.choices(CATALOG[category], weights=[p[2] for p in CATALOG[category]], k=1)[0]

        keep, extra_disc = _september_shock(d, region, product)
        if rng.random() > keep:
            continue

        lo, hi = UNITS_RANGE[category]
        units = rng.randint(lo, hi)
        discount = rng.choices([0.0, 0.05, 0.10, 0.15, 0.20], weights=[5, 2, 2, 1, 0.5], k=1)[0]
        discount = round(min(discount + extra_disc, 0.35), 2)
        records.append({
            "order_date": d.isoformat(),
            "region": region,
            "category": category,
            "product": product,
            "units": units,
            "unit_price": price,
            "discount": discount,
        })

    df = pd.DataFrame(records).sort_values(["order_date", "region", "product"], kind="stable")
    return df.reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate()
    csv_path = OUT_DIR / "sales_2026.csv"
    df.to_csv(csv_path, index=False)

    # Multi-sheet Excel (one sheet per quarter) to demo the Excel stretch goal.
    xlsx_path = OUT_DIR / "sales_2026.xlsx"
    q = pd.to_datetime(df["order_date"]).dt.to_period("Q").astype(str)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xw:
        for quarter in sorted(q.unique()):
            df[q == quarter].to_excel(xw, sheet_name=quarter, index=False)

    print(f"wrote {len(df):,} rows -> {csv_path}")
    print(f"wrote {q.nunique()} sheets -> {xlsx_path}")


if __name__ == "__main__":
    main()
