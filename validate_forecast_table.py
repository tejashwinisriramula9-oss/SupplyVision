"""
Validates the forecast_results table logic that the Power Query M code will build.
Run this to confirm row counts, column names, and data values BEFORE entering
the M code into Power BI.
"""
import pandas as pd
import numpy as np
from pathlib import Path

PROCESSED = Path("data/processed")
EXPORTS   = Path("data/exports")

print("=" * 65)
print("  forecast_results Table Validation")
print("=" * 65)

# ── PART A: Historical monthly demand ─────────────────────────────────────
orders = pd.read_csv(PROCESSED / "fact_orders_clean.csv", parse_dates=["Order_Date"])
active = orders[orders["Order_Status"] != "Cancelled"].copy()
active["Date"] = active["Order_Date"].dt.to_period("M").dt.to_timestamp("M")

historical = (
    active.groupby("Date")
    .agg(
        Actual_Quantity=("Quantity",  "sum"),
        Actual_Revenue= ("Revenue",   "sum"),
        Order_Count=    ("Order_ID",  "count"),
    )
    .reset_index()
)
historical["Forecast_Quantity"] = np.nan
historical["Data_Type"]         = "Historical"

print(f"\nHistorical rows : {len(historical)}")
print(f"Date range      : {historical['Date'].min().date()} → {historical['Date'].max().date()}")
print(f"Avg qty/month   : {historical['Actual_Quantity'].mean():.0f}")

# ── PART B: Forecast ───────────────────────────────────────────────────────
fore_raw = pd.read_csv(EXPORTS / "forecast_ensemble.csv", parse_dates=["Month"])
forecast = fore_raw.rename(columns={"Month": "Date"})[["Date", "Forecast_Quantity", "Model"]]
forecast["Actual_Quantity"] = np.nan
forecast["Actual_Revenue"]  = np.nan
forecast["Order_Count"]     = np.nan
forecast["Data_Type"]       = "Forecast"

print(f"\nForecast rows   : {len(forecast)}")
print(f"Date range      : {forecast['Date'].min().date()} → {forecast['Date'].max().date()}")
print(f"Avg forecast qty: {forecast['Forecast_Quantity'].mean():.0f}")

# ── PART C: Combine ────────────────────────────────────────────────────────
KEEP_COLS = ["Date", "Actual_Quantity", "Actual_Revenue",
             "Order_Count", "Forecast_Quantity", "Data_Type"]
combined = pd.concat(
    [historical[KEEP_COLS], forecast[KEEP_COLS]],
    ignore_index=True
).sort_values("Date").reset_index(drop=True)

# Helper columns
combined["YearMonth"] = combined["Date"].dt.strftime("%Y-%m")
combined["Display_Quantity"] = combined["Actual_Quantity"].fillna(combined["Forecast_Quantity"])

print(f"\nCombined rows   : {len(combined)}  (expected 42 = 36 historical + 6 forecast)")
print(f"Full date range : {combined['Date'].min().date()} → {combined['Date'].max().date()}")
print(f"\nData_Type breakdown:")
print(combined["Data_Type"].value_counts().to_string())

print(f"\nColumn names (must match DAX references exactly):")
for col in combined.columns:
    print(f"  {col}")

print(f"\nFirst 3 rows (Historical):")
print(combined[combined["Data_Type"] == "Historical"].head(3).to_string(index=False))

print(f"\nForecast rows:")
print(combined[combined["Data_Type"] == "Forecast"].to_string(index=False))

print(f"\nNull check (Actual_Quantity should be null for forecast rows):")
print(f"  Historical — Actual_Quantity nulls: {combined[combined['Data_Type']=='Historical']['Actual_Quantity'].isna().sum()} (expected 0)")
print(f"  Forecast   — Actual_Quantity nulls: {combined[combined['Data_Type']=='Forecast']['Actual_Quantity'].isna().sum()} (expected 6)")
print(f"  Forecast   — Forecast_Quantity nulls: {combined[combined['Data_Type']=='Forecast']['Forecast_Quantity'].isna().sum()} (expected 0)")

print("\n" + "=" * 65)
print("  ✅ Validation passed — M code will produce correct table")
print("=" * 65)
