"""Inspect all forecast-related files for Power BI fix."""
import pandas as pd
from pathlib import Path

exports   = Path("data/exports")
processed = Path("data/processed")

print("=== FILES IN data/exports/ ===")
for f in sorted(exports.glob("*.csv")):
    df = pd.read_csv(f)
    print(f"\n{f.name}  ({len(df)} rows):")
    for col in df.columns:
        sample = str(df[col].iloc[0]) if len(df) > 0 else "empty"
        print(f"  {col:<35} dtype={str(df[col].dtype):<15} sample={sample[:45]}")

print()
print("=== fact_orders_clean — date range + key columns ===")
fo = pd.read_parquet(processed / "fact_orders_clean.parquet")
status_cancel = fo["Order_Status"] == "Cancelled"
print(f"Order_Date range : {fo['Order_Date'].min()} → {fo['Order_Date'].max()}")
print(f"Total rows       : {len(fo)}")
print(f"Cancelled rows   : {status_cancel.sum()}")
print(f"Active rows      : {(~status_cancel).sum()}")
print(f"COGS nulls       : {fo['COGS'].isna().sum()}")
print(f"YearMonth sample : {fo['YearMonth'].iloc[0]}")

# Build the monthly aggregation that matches what the Python forecasting pipeline built
active = fo[~status_cancel].copy()
active["Order_Date"] = pd.to_datetime(active["Order_Date"])
monthly = (
    active.resample("ME", on="Order_Date")
    .agg(Total_Quantity=("Quantity", "sum"), Total_Revenue=("Revenue", "sum"))
    .reset_index()
    .rename(columns={"Order_Date": "Month"})
)
print()
print("=== HISTORICAL MONTHLY DEMAND (first 5 rows) ===")
print(monthly.head().to_string())
print(f"Total months: {len(monthly)}")
