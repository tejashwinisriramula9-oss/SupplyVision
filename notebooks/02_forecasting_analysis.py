"""
SupplyVision – Notebook 2: Forecasting Analysis
Visualises demand forecast outputs from the forecasting pipeline.
Run after: python pipeline.py --steps gen etl forecast
"""

# %%
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BRAND_BLUE  = "#0A2342"
ACCENT_BLUE = "#2E86C1"
GREEN       = "#1E8449"
AMBER       = "#F39C12"
EXPORT_DIR  = Path("data/exports")
PROCESSED   = Path("data/processed")

plt.rcParams.update({
    "figure.facecolor": "#F2F4F7",
    "axes.facecolor":   "#FFFFFF",
    "font.family":      "sans-serif",
})


def load_csv(name: str) -> pd.DataFrame:
    p = EXPORT_DIR / f"{name}.csv"
    if not p.exists():
        raise FileNotFoundError(f"Run pipeline.py first – {p} not found.")
    return pd.read_csv(p, parse_dates=["Month"])


# ─── Load data ────────────────────────────────────────────────────────────────
print("Loading forecast data …")

parquet = PROCESSED / "fact_orders_clean.parquet"
csv_path = PROCESSED / "orders_clean.csv"

if parquet.exists():
    orders = pd.read_parquet(parquet)
elif csv_path.exists():
    orders = pd.read_csv(csv_path)
else:
    raise FileNotFoundError("Run pipeline.py first.")

# Build historical monthly demand
from src.forecasting.demand_forecast import build_monthly_demand, run_forecasting

monthly = build_monthly_demand(orders)
results = run_forecasting(orders, horizon_months=6)
lr_fc   = results["lr_forecast"]
ts_fc   = results["ts_forecast"]
ens_fc  = results["ensemble_forecast"]
inv_req = results["inventory_requirements"]

print(f"  Historical periods: {len(monthly)}")
print(f"  Forecast horizon:   {len(ens_fc)} months")
print(f"  LR Metrics: {results['lr_metrics']}")

# %% [markdown]
# ## 1. Demand Forecast – Historical vs Predicted

# %%
fig, ax = plt.subplots(figsize=(15, 6))

# Historical
ax.plot(monthly["Month"], monthly["Total_Quantity"], color=BRAND_BLUE,
        linewidth=2, label="Historical Demand", zorder=3)
ax.fill_between(monthly["Month"], monthly["Total_Quantity"], alpha=0.1, color=BRAND_BLUE)

# Forecasts
if len(lr_fc) > 0:
    ax.plot(lr_fc["Month"], lr_fc["Forecast_Quantity"], "--o", color=ACCENT_BLUE,
            linewidth=2, markersize=6, label="Linear Regression Forecast")

if len(ts_fc) > 0:
    ax.plot(ts_fc["Month"], ts_fc["Forecast_Quantity"], "--s", color=GREEN,
            linewidth=2, markersize=6, label="Exponential Smoothing Forecast")

if len(ens_fc) > 0:
    ax.plot(ens_fc["Month"], ens_fc["Forecast_Quantity"], "-^", color=AMBER,
            linewidth=2.5, markersize=8, label="Ensemble Forecast", zorder=4)

# Divider
if len(monthly) > 0:
    ax.axvline(monthly["Month"].max(), color="#C0392B", linestyle=":", linewidth=1.5, label="Forecast Start")
    ax.axvspan(ens_fc["Month"].min(), ens_fc["Month"].max(), alpha=0.05, color=AMBER)

ax.set_title("SupplyVision – Demand Forecast (6-Month Horizon)", fontsize=16, color=BRAND_BLUE, fontweight="bold")
ax.set_xlabel("Month")
ax.set_ylabel("Total Quantity Demanded")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(framealpha=0.9)
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(EXPORT_DIR / "plot_demand_forecast.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: data/exports/plot_demand_forecast.png")

# %% [markdown]
# ## 2. Inventory Requirements Projection

# %%
if len(inv_req) > 0:
    fig, ax = plt.subplots(figsize=(13, 5))
    x = range(len(inv_req))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], inv_req["Forecast_Quantity"],
                   width, label="Forecast Demand", color=ACCENT_BLUE, alpha=0.9)
    bars2 = ax.bar([i + width/2 for i in x], inv_req["Reorder_Quantity"],
                   width, label="Recommended Order Qty", color=GREEN, alpha=0.9)

    ax.plot(x, inv_req["Safety_Stock_Required"], "r--o", linewidth=2,
            markersize=6, label="Safety Stock Required")

    ax.set_xticks(list(x))
    ax.set_xticklabels([str(m)[:7] for m in inv_req["Month"]], rotation=30, ha="right")
    ax.set_title("Inventory Requirement Projections", fontsize=14, color=BRAND_BLUE, fontweight="bold")
    ax.set_ylabel("Units")
    ax.legend()
    plt.tight_layout()
    plt.savefig(EXPORT_DIR / "plot_inventory_requirements.png", dpi=150, bbox_inches="tight")
    plt.show()

# %% [markdown]
# ## 3. Model Accuracy Comparison

# %%
metrics_data = {
    "Model": ["Linear Regression", "Exp. Smoothing"],
    "MAE":   [results["lr_metrics"].get("MAE", 0), results["ts_metrics"].get("MAE", 0)],
    "RMSE":  [results["lr_metrics"].get("RMSE", 0), results["ts_metrics"].get("RMSE", 0)],
}
m_df = pd.DataFrame(metrics_data).set_index("Model")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Forecast Model Accuracy Comparison", fontsize=14, color=BRAND_BLUE, fontweight="bold")

for ax, col in zip(axes, ["MAE", "RMSE"]):
    bars = ax.bar(m_df.index, m_df[col], color=[ACCENT_BLUE, GREEN], edgecolor="white", width=0.5)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.02,
                f"{bar.get_height():,.1f}", ha="center", va="bottom", color=BRAND_BLUE)
    ax.set_title(col)
    ax.set_ylabel(col)

plt.tight_layout()
plt.savefig(EXPORT_DIR / "plot_model_accuracy.png", dpi=150, bbox_inches="tight")
plt.show()

print(f"\n✅ Forecasting analysis complete.")
print(f"   LR R²:   {results['lr_metrics'].get('R2', 'N/A')}")
print(f"   LR MAPE: {results['lr_metrics'].get('MAPE', 'N/A')}%")
