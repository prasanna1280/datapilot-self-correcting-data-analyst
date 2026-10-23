"""International sample datasets for DataPilot (deterministic, seeded).

Each dataset follows common international conventions:
  - dates in ISO 8601 (YYYY-MM-DD), months as YYYY-MM
  - countries as ISO 3166-1 alpha-2 codes, currencies as ISO 4217 codes in column names
  - snake_case column names, one row per business event, explicit IDs

Each one also has a story built in, so the sample questions have real answers.
Called from scripts/generate_sample_data.py, which also writes data/sample/catalog.json.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pandas as pd

COUNTRIES = {
    "AMER": [("US", "United States", 4.0), ("CA", "Canada", 1.0), ("BR", "Brazil", 1.2), ("MX", "Mexico", 0.8)],
    "EMEA": [("DE", "Germany", 2.0), ("GB", "United Kingdom", 2.0), ("FR", "France", 1.5), ("AE", "United Arab Emirates", 0.6)],
    "APAC": [("IN", "India", 1.8), ("JP", "Japan", 1.6), ("AU", "Australia", 1.0), ("SG", "Singapore", 0.7)],
}


def _pick(rng: random.Random, items, weight_index=-1):
    return rng.choices(items, weights=[i[weight_index] for i in items], k=1)[0]


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(i) for i in range((end - start).days + 1)]


# --------------------------------------------------------------------------- e-commerce
def global_ecommerce_orders(seed: int = 11) -> pd.DataFrame:
    """Jan-Sep 2026 online orders in USD.
    Story: APAC Mobile grows strongly in Q3; Germany Apparel returns spike in August."""
    rng = random.Random(seed)
    catalog = {
        "Electronics": [("ELC-1001", "Wireless Headphones", 129.0), ("ELC-1002", "Smart Speaker", 89.0), ("ELC-1003", "4K Action Camera", 249.0)],
        "Apparel": [("APP-2001", "Running Jacket", 79.0), ("APP-2002", "Merino Sweater", 99.0), ("APP-2003", "Trail Sneakers", 119.0)],
        "Home": [("HOM-3001", "Espresso Machine", 199.0), ("HOM-3002", "Air Purifier", 159.0), ("HOM-3003", "Cookware Set", 139.0)],
        "Beauty": [("BEA-4001", "Vitamin C Serum", 34.0), ("BEA-4002", "Hair Dryer Pro", 89.0)],
    }
    channels = [("Web", 5.0), ("Mobile App", 4.0), ("Marketplace", 2.0)]
    rows = []
    days = _days(date(2026, 1, 1), date(2026, 9, 30))
    n = 0
    while len(rows) < 15_000:
        d = rng.choice(days)
        region = rng.choices(list(COUNTRIES), weights=[4, 3.5, 3], k=1)[0]
        cc, country, _ = _pick(rng, COUNTRIES[region])
        channel = _pick(rng, channels)[0]
        q3 = d.month >= 7
        if region == "APAC" and channel == "Mobile App" and not q3 and rng.random() < 0.45:
            continue  # thin APAC mobile volume before Q3 -> strong Q3 growth
        category = rng.choices(list(catalog), weights=[3, 3, 2, 1.5], k=1)[0]
        sku, name, price = rng.choice(catalog[category])
        units = rng.randint(1, 4)
        disc = rng.choices([0, 0.05, 0.1, 0.15, 0.2], weights=[6, 2, 2, 1, 0.5], k=1)[0]
        ret_p = 0.06
        if cc == "DE" and category == "Apparel" and d.month == 8:
            ret_p = 0.32  # sizing issue on a new supplier batch
        n += 1
        rows.append({
            "order_id": f"ORD-{n:06d}", "order_date": d.isoformat(), "country_code": cc, "country": country,
            "region": region, "channel": channel, "category": category, "sku": sku, "product_name": name,
            "units": units, "unit_price_usd": price, "discount_rate": disc,
            "returned": rng.random() < ret_p,
        })
    df = pd.DataFrame(rows).sort_values(["order_date", "order_id"]).reset_index(drop=True)
    df["order_id"] = [f"ORD-{i + 1:06d}" for i in range(len(df))]
    return df


# --------------------------------------------------------------------------- SaaS
def saas_subscriptions(seed: int = 22) -> pd.DataFrame:
    """Monthly subscription events Jan-Sep 2026 in EUR.
    Story: Pro plan churn in EMEA spikes in May-June 2026 after a price increase."""
    rng = random.Random(seed)
    plans = {"Starter": (29.0, (1, 5)), "Pro": (59.0, (5, 40)), "Enterprise": (49.0, (40, 400))}
    months = [f"2026-{m:02d}" for m in range(1, 10)]
    rows = []
    cid = 0
    active: list[dict] = []
    for i, month in enumerate(months):
        for _ in range(110 if i == 0 else rng.randint(45, 70)):  # new customers
            cid += 1
            region = rng.choices(list(COUNTRIES), weights=[4, 3.5, 2.5], k=1)[0]
            cc = _pick(rng, COUNTRIES[region])[0]
            plan = rng.choices(list(plans), weights=[5, 3.5, 1], k=1)[0]
            seats = rng.randint(*plans[plan][1])
            active.append({"customer_id": f"CUS-{cid:05d}", "region": region, "country_code": cc, "plan": plan,
                           "seats": seats, "start": month})
        still = []
        for c in active:
            price = plans[c["plan"]][0] * (1.15 if c["plan"] == "Pro" and month >= "2026-05" else 1.0)
            mrr = round(c["seats"] * price, 2)
            churn_p = {"Starter": 0.035, "Pro": 0.02, "Enterprise": 0.008}[c["plan"]]
            if c["plan"] == "Pro" and c["region"] == "EMEA" and month in ("2026-05", "2026-06"):
                churn_p = 0.16
            if c["start"] != month and rng.random() < churn_p:
                rows.append({**_sub_row(c, month, mrr), "status": "churned"})
                continue
            if c["start"] != month and rng.random() < 0.03:
                c["seats"] += rng.randint(1, max(2, c["seats"] // 5))
                mrr = round(c["seats"] * price, 2)
                rows.append({**_sub_row(c, month, mrr), "status": "expansion"})
            else:
                rows.append({**_sub_row(c, month, mrr), "status": "new" if c["start"] == month else "active"})
            still.append(c)
        active = still
    return pd.DataFrame(rows)


def _sub_row(c: dict, month: str, mrr: float) -> dict:
    return {"month": month, "customer_id": c["customer_id"], "region": c["region"], "country_code": c["country_code"],
            "plan": c["plan"], "seats": c["seats"], "mrr_eur": mrr}


# --------------------------------------------------------------------------- logistics
def supply_chain_shipments(seed: int = 33) -> pd.DataFrame:
    """Shipments Jan-Sep 2026, costs in USD, weights in kg.
    Story: OceanLink's ocean shipments from CN are badly late in July-August 2026 (port congestion)."""
    rng = random.Random(seed)
    lanes = [("CN", "US", 3), ("CN", "DE", 2.5), ("VN", "US", 1.5), ("IN", "GB", 1.2), ("DE", "US", 1.2),
             ("MX", "US", 1.5), ("JP", "AU", 0.8), ("CN", "AU", 1.0)]
    carriers = {"Ocean": ["OceanLink", "BlueWave Shipping"], "Air": ["SkyFreight", "AeroCargo"], "Road": ["RoadRunner Logistics"]}
    transit = {"Ocean": (24, 38), "Air": (2, 5), "Road": (3, 7)}
    rate = {"Ocean": 0.9, "Air": 5.8, "Road": 1.6}
    rows = []
    days = _days(date(2026, 1, 1), date(2026, 9, 30))
    for i in range(9_000):
        o, dst, _ = _pick(rng, lanes)
        mode = "Road" if (o, dst) == ("MX", "US") else rng.choices(["Ocean", "Air"], weights=[3, 1], k=1)[0]
        carrier = rng.choice(carriers[mode])
        ship = rng.choice(days)
        lo, hi = transit[mode]
        promised_days = hi
        actual = rng.randint(lo, hi + 2)
        if carrier == "OceanLink" and o == "CN" and ship.month in (7, 8):
            actual += rng.randint(6, 16)
        weight = round(rng.uniform(50, 1800) if mode == "Air" else rng.uniform(800, 22000), 1)
        rows.append({
            "shipment_id": f"SHP-{i + 1:06d}", "ship_date": ship.isoformat(),
            "promised_date": (ship + timedelta(promised_days)).isoformat(),
            "delivery_date": (ship + timedelta(actual)).isoformat(),
            "origin_country": o, "destination_country": dst, "mode": mode, "carrier": carrier,
            "weight_kg": weight, "freight_cost_usd": round(weight * rate[mode] * rng.uniform(0.85, 1.2), 2),
        })
    return pd.DataFrame(rows).sort_values("ship_date", kind="stable").reset_index(drop=True)


# --------------------------------------------------------------------------- HR (multi-sheet)
def hr_workforce(seed: int = 44) -> dict[str, pd.DataFrame]:
    """Workforce register split into one sheet per region, salaries in USD.
    Story: APAC Engineering attrition is far above other teams in 2026."""
    rng = random.Random(seed)
    depts = [("Engineering", 4), ("Sales", 2.5), ("Customer Success", 1.5), ("Finance", 0.8), ("Marketing", 1.0), ("People", 0.6)]
    levels = [("L1 Associate", 3, 52_000), ("L2 Professional", 3.5, 74_000), ("L3 Senior", 2.5, 98_000),
              ("L4 Lead", 1.2, 128_000), ("L5 Director", 0.4, 175_000)]
    region_pay = {"AMER": 1.0, "EMEA": 0.9, "APAC": 0.62}
    reasons = ["Better offer", "Relocation", "Career change", "Compensation", "Manager", "Retirement"]
    sheets = {}
    eid = 0
    for region, sheet in (("AMER", "Americas"), ("EMEA", "EMEA"), ("APAC", "APAC")):
        rows = []
        for _ in range({"AMER": 1100, "EMEA": 900, "APAC": 1000}[region]):
            eid += 1
            dept = _pick(rng, depts)[0]
            level, _, base = _pick(rng, levels, 1)
            hire = date(2016, 1, 1) + timedelta(rng.randint(0, 3800))
            exit_p = 0.09
            if region == "APAC" and dept == "Engineering":
                exit_p = 0.27
            exit_date, reason = "", ""
            if hire < date(2026, 1, 1) and rng.random() < exit_p:
                exit_date = (date(2026, 1, 1) + timedelta(rng.randint(0, 272))).isoformat()
                reason = "Better offer" if exit_p > 0.2 and rng.random() < 0.6 else rng.choice(reasons)
            rows.append({
                "employee_id": f"EMP-{eid:05d}", "country_code": _pick(rng, COUNTRIES[region])[0], "region": region,
                "department": dept, "job_level": level, "hire_date": hire.isoformat(), "exit_date": exit_date,
                "exit_reason": reason, "annual_salary_usd": round(base * region_pay[region] * rng.uniform(0.85, 1.2), -2),
                "performance_rating": rng.choices([1, 2, 3, 4, 5], weights=[0.5, 1.5, 5, 2.5, 0.8], k=1)[0],
            })
        sheets[sheet] = pd.DataFrame(rows)
    return sheets
