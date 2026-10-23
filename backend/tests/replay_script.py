"""Scripted model replies: plan -> buggy code (KeyError) -> fixed code -> APPROVED.

Shared by the tests and scripts/smoke_test.py (no pytest dependency).
"""

PLAN = "1) revenue = units * unit_price * (1 - discount)\n2) Group by month + category\n3) Find biggest drop\n4) Split by region"

BUGGY = '''```python
# filename: analysis.py
import pandas as pd
df = pd.read_csv("data.csv")
print(df.groupby("category")["revenue"].sum())
```'''

FIXED = '''Fixed: revenue column is now created before grouping.
```python
# filename: analysis.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data.csv", parse_dates=["order_date"])
df["revenue"] = df["units"] * df["unit_price"] * (1 - df["discount"])
df["month"] = df["order_date"].dt.strftime("%Y-%m")
m = df[df["month"].isin(["2026-08", "2026-09"])]
by_cat = m.pivot_table(index="category", columns="month", values="revenue", aggfunc="sum")
by_cat["drop"] = by_cat["2026-08"] - by_cat["2026-09"]
top = by_cat["drop"].idxmax()
print(f"Biggest drop: {top} Aug {by_cat.loc[top, '2026-08']/1e5:.1f} L, Sep {by_cat.loc[top, '2026-09']/1e5:.1f} L")
reg = m[m["category"] == top].pivot_table(index="region", columns="month", values="revenue", aggfunc="sum")
reg["drop"] = reg["2026-08"] - reg["2026-09"]
print(f"Top region: {reg['drop'].idxmax()} {reg['drop'].max()/1e5:.1f} L")
ax = (by_cat["drop"] / 1e5).plot(kind="bar", title="Revenue drop Sep vs Aug by category")
ax.set_xlabel("Category"); ax.set_ylabel("Revenue drop (Rs lakh)")
plt.tight_layout(); plt.savefig("category_trend.png"); plt.close()
print("SAVED: category_trend.png")
```'''

ANSWER = "ANSWER\nElectronics had the biggest drop.\n\nWHERE IT CAME FROM\nSouth region.\n\nFILES\ncategory_trend.png | analysis.py\n\nSUGGESTED NEXT QUESTION\nDid discounts change?\n\nAPPROVED"
