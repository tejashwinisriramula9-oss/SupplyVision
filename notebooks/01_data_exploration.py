"""
SupplyVision – Notebook 1: Data Exploration
Run with Jupyter: jupyter notebook notebooks/01_data_exploration.py
Or as a plain Python script: python notebooks/01_data_exploration.py
"""

# %% [markdown]
# # SupplyVision – Data Exploration
# Interactive exploration of the supply chain datasets.

# %%
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── Style ─────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#F2F4F7",
    "axes.facecolor":   "#FFFFFF",
    "axes.edgecolor":   "#0A2342",
    "axes.labelcolor":  "#0A2342",
    "text.color":       "#0A2342",
    "xtick.color":      "#1A5276",
    "ytick.color":      "#1A5276",
    "font.family":      "sans-serif",
})
BRAND_BLUE  = "#0A2342"
ACCENT_BLUE = "#2E86C1"
LIGHT_GRAY  = "#F2F4F7"

PROCESSED = Path("data/processed")

# ── Load data ─────────────────────────────────────────────────────────────────
def load(name: str) -> pd.DataFrame:
    p = PROCESSED / f"{name}_clean.parquet"
    if p.exists():
        return pd.read_parquet(p)
    c = PROCESSED / f"{name}_clean.csv"
    if c.exists():
        return pd.read_csv(c, parse_dates=True)
    raise FileNotFoundError(f"Run pipeline.py first – {name} not found.")

print("Loading datasets …")
orders     = load("orders")
inventory  = load("inventory")
suppliers  = load("suppliers")
logistics  = load("logistics")
warehouses = load("warehouses")

try:
    fact_orders = load("fact_orders")
except FileNotFoundError:
    fact_orders = orders

print(f"  Orders:     {len(orders):>6,} rows")
print(f"  Inventory:  {len(inventory):>6,} rows")
print(f"  Suppliers:  {len(suppliers):>6,} rows")
print(f"  Logistics:  {len(logistics):>6,} rows")
print(f"  Warehouses: {len(warehouses):>6,} rows")

# %% [markdown]
# ## 1. Revenue Trend

# %%
active = fact_orders[fact_orders["Order_Status"] != "Cancelled"].copy()
active["Order_Date"] = pd.to_datetime(active["Order_Date"])
monthly = active.resample("ME", on="Order_Date").agg(Revenue=("Revenue","sum"), Orders=("Order_ID","count")).reset_index()

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.suptitle("SupplyVision – Revenue & Order Volume Trend", fontsize=16, color=BRAND_BLUE, fontweight="bold")

axes[0].fill_between(monthly["Order_Date"], monthly["Revenue"], alpha=0.3, color=ACCENT_BLUE)
axes[0].plot(monthly["Order_Date"], monthly["Revenue"], color=ACCENT_BLUE, linewidth=2)
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
axes[0].set_ylabel("Monthly Revenue")

axes[1].bar(monthly["Order_Date"], monthly["Orders"], color=BRAND_BLUE, width=20, alpha=0.8)
axes[1].set_ylabel("Order Count")
axes[1].set_xlabel("Month")

plt.tight_layout()
plt.savefig("data/exports/plot_revenue_trend.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: data/exports/plot_revenue_trend.png")

# %% [markdown]
# ## 2. Inventory Status Distribution

# %%
status_counts = inventory["Stock_Status"].value_counts()
colors = {"Out of Stock": "#C0392B", "Low Stock": "#F39C12", "Optimal": "#1E8449", "Overstock": "#2E86C1"}
bar_colors = [colors.get(s, "#7F8C8D") for s in status_counts.index]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(status_counts.index, status_counts.values, color=bar_colors, edgecolor="white", linewidth=1.5)
for bar in bars:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{bar.get_height():,}", ha="center", va="bottom", fontsize=11, color=BRAND_BLUE)
ax.set_title("Inventory Stock Status Distribution", fontsize=14, color=BRAND_BLUE, fontweight="bold")
ax.set_xlabel("Stock Status")
ax.set_ylabel("Product Count")
plt.tight_layout()
plt.savefig("data/exports/plot_inventory_status.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 3. Carrier On-Time Delivery Performance

# %%
carrier_perf = (
    logistics.groupby("Carrier")
    .agg(Total=("Shipment_ID","count"), OnTime=("Is_Delayed", lambda x: (x==0).sum()))
    .reset_index()
)
carrier_perf["OnTime_Pct"] = carrier_perf["OnTime"] / carrier_perf["Total"] * 100
carrier_perf = carrier_perf.sort_values("OnTime_Pct", ascending=True)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(carrier_perf["Carrier"], carrier_perf["OnTime_Pct"], color=ACCENT_BLUE, edgecolor="white")
for bar, val in zip(bars, carrier_perf["OnTime_Pct"]):
    ax.text(bar.get_width() - 1, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}%", ha="right", va="center", color="white", fontweight="bold")
ax.axvline(85, color="#C0392B", linestyle="--", linewidth=1.5, label="85% Target")
ax.set_xlim(0, 100)
ax.set_title("On-Time Delivery % by Carrier", fontsize=14, color=BRAND_BLUE, fontweight="bold")
ax.set_xlabel("On-Time Delivery %")
ax.legend()
plt.tight_layout()
plt.savefig("data/exports/plot_carrier_performance.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 4. Supplier Reliability Distribution

# %%
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(suppliers["Reliability_Score"] * 100, bins=20, color=ACCENT_BLUE,
        edgecolor="white", linewidth=0.8, alpha=0.85)
ax.axvline(80, color="#C0392B", linestyle="--", linewidth=1.5, label="80% Threshold")
ax.axvline(suppliers["Reliability_Score"].mean() * 100, color="#F39C12",
           linestyle="-", linewidth=2, label=f"Mean {suppliers['Reliability_Score'].mean()*100:.1f}%")
ax.set_title("Supplier Reliability Score Distribution", fontsize=14, color=BRAND_BLUE, fontweight="bold")
ax.set_xlabel("Reliability Score (%)")
ax.set_ylabel("Supplier Count")
ax.legend()
plt.tight_layout()
plt.savefig("data/exports/plot_supplier_reliability.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 5. Revenue by Category

# %%
cat_rev = (
    fact_orders[fact_orders["Order_Status"] != "Cancelled"]
    .groupby("Category")["Revenue"]
    .sum()
    .sort_values(ascending=False)
)
blues = plt.cm.Blues(np.linspace(0.4, 0.9, len(cat_rev)))

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(cat_rev.index, cat_rev.values, color=blues, edgecolor="white")
for bar in bars:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1e4,
            f"${bar.get_height()/1e6:.1f}M", ha="center", va="bottom", fontsize=9, color=BRAND_BLUE)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
ax.set_title("Total Revenue by Product Category", fontsize=14, color=BRAND_BLUE, fontweight="bold")
ax.set_xlabel("Category")
ax.set_ylabel("Revenue")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig("data/exports/plot_revenue_by_category.png", dpi=150, bbox_inches="tight")
plt.show()

print("\n✅ Exploration complete. Charts saved to data/exports/")
