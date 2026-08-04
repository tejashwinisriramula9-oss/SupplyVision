"""
SupplyVision – ETL: Clean & Transform
Reads raw CSV/Excel data, applies enterprise-grade cleaning rules,
adds computed columns, and outputs processed Parquet + CSV files.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _load(name: str) -> pd.DataFrame:
    csv_path = RAW_DIR / f"{name}.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    xlsx_path = RAW_DIR / "supply_chain_data.xlsx"
    if xlsx_path.exists():
        return pd.read_excel(xlsx_path, sheet_name=name.capitalize())
    raise FileNotFoundError(
        f"Cannot find data for '{name}'. "
        f"Expected {csv_path} or {xlsx_path}. Run python pipeline.py --steps gen first."
    )


def _save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(PROCESSED_DIR / f"{name}_clean.csv", index=False)
    df.to_parquet(PROCESSED_DIR / f"{name}_clean.parquet", index=False)
    logger.info(f"Saved {name}: {len(df)} rows → {PROCESSED_DIR}")


# ─── Table-specific cleaners ─────────────────────────────────────────────────
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning Orders …")
    df = df.copy()

    # Parse dates
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df.dropna(subset=["Order_Date"], inplace=True)

    # Numeric coercion
    for col in ["Quantity", "Unit_Price", "Revenue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with negative revenue or zero quantity
    df = df[(df["Revenue"] > 0) & (df["Quantity"] > 0)]

    # Fill missing discount
    df["Discount"] = df["Discount"].fillna(0).clip(0, 1)

    # Derived columns
    df["Year"] = df["Order_Date"].dt.year
    df["Month"] = df["Order_Date"].dt.month
    df["Quarter"] = df["Order_Date"].dt.quarter
    df["YearMonth"] = df["Order_Date"].dt.to_period("M").astype(str)
    df["YearQuarter"] = df["Year"].astype(str) + " Q" + df["Quarter"].astype(str)
    df["WeekOfYear"] = df["Order_Date"].dt.isocalendar().week.astype(int)
    df["DayOfWeek"] = df["Order_Date"].dt.day_name()

    # Categorical
    df["Order_Status"] = df["Order_Status"].str.strip().str.title()
    df["Sales_Channel"] = df["Sales_Channel"].str.strip().str.title()

    logger.success(f"Orders cleaned: {len(df)} rows")
    return df


def clean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning Inventory …")
    df = df.copy()

    for col in ["Current_Stock", "Safety_Stock", "Reorder_Point", "Unit_Cost", "Unit_Price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Current_Stock"] = df["Current_Stock"].clip(lower=0)
    df["Unit_Cost"] = df["Unit_Cost"].clip(lower=0.01)
    df["Unit_Price"] = df["Unit_Price"].clip(lower=0.01)

    # Derived columns
    df["Inventory_Value"] = (df["Current_Stock"] * df["Unit_Cost"]).round(2)
    df["Stock_Status"] = np.select(
        [
            df["Current_Stock"] == 0,
            df["Current_Stock"] < df["Safety_Stock"],
            df["Current_Stock"] > df["Reorder_Point"] * 3,
        ],
        ["Out of Stock", "Low Stock", "Overstock"],
        default="Optimal",
    )
    df["Margin_Pct"] = ((df["Unit_Price"] - df["Unit_Cost"]) / df["Unit_Price"] * 100).round(2)
    df["Category"] = df["Category"].str.strip().str.title()
    df["Last_Updated"] = pd.to_datetime(df["Last_Updated"], errors="coerce")

    logger.success(f"Inventory cleaned: {len(df)} rows")
    return df


def clean_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning Suppliers …")
    df = df.copy()

    df["Lead_Time"] = pd.to_numeric(df["Lead_Time"], errors="coerce").fillna(df["Lead_Time"].median())
    df["Reliability_Score"] = pd.to_numeric(df["Reliability_Score"], errors="coerce").fillna(0.75).clip(0, 1)
    df["Supplier_Cost"] = pd.to_numeric(df["Supplier_Cost"], errors="coerce").fillna(0)

    # Tier classification
    df["Reliability_Tier"] = pd.cut(
        df["Reliability_Score"],
        bins=[0, 0.65, 0.80, 0.90, 1.0],
        labels=["Poor", "Acceptable", "Good", "Excellent"],
    )
    df["Lead_Time_Category"] = pd.cut(
        df["Lead_Time"],
        bins=[0, 7, 14, 30, 999],
        labels=["Express", "Standard", "Extended", "Long Lead"],
    )

    logger.success(f"Suppliers cleaned: {len(df)} rows")
    return df


def clean_logistics(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning Logistics …")
    df = df.copy()

    df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], errors="coerce")
    df["Delivery_Date"] = pd.to_datetime(df["Delivery_Date"], errors="coerce")
    df.dropna(subset=["Ship_Date", "Delivery_Date"], inplace=True)

    df["Transit_Time"] = pd.to_numeric(df["Transit_Time"], errors="coerce").fillna(
        df["Transit_Time"].median()
    ).clip(lower=1)
    df["Transport_Cost"] = pd.to_numeric(df["Transport_Cost"], errors="coerce").fillna(0)
    df["Weight_KG"] = pd.to_numeric(df["Weight_KG"], errors="coerce").fillna(1)

    # Derived
    df["Delay_Days"] = (df["Delivery_Date"] - df["Ship_Date"]).dt.days - df["Expected_Transit_Days"]
    df["Delay_Days"] = df["Delay_Days"].clip(lower=0)
    df["Is_Delayed"] = (df["Delivery_Date"] > df["Ship_Date"] + pd.to_timedelta(df["Expected_Transit_Days"], unit="D")).astype(int)
    df["Cost_Per_KG"] = (df["Transport_Cost"] / df["Weight_KG"].replace(0, np.nan)).round(2)
    df["Ship_Year"] = df["Ship_Date"].dt.year
    df["Ship_Month"] = df["Ship_Date"].dt.month
    df["Ship_Quarter"] = df["Ship_Date"].dt.quarter
    df["Ship_YearMonth"] = df["Ship_Date"].dt.to_period("M").astype(str)
    df["Carrier"] = df["Carrier"].str.strip().str.title()

    logger.success(f"Logistics cleaned: {len(df)} rows")
    return df


def clean_warehouses(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Cleaning Warehouses …")
    df = df.copy()

    df["Capacity"] = pd.to_numeric(df["Capacity"], errors="coerce").fillna(10000)
    df["Utilization"] = pd.to_numeric(df["Utilization"], errors="coerce").fillna(0.7).clip(0, 1)

    df["Available_Capacity"] = (df["Capacity"] * (1 - df["Utilization"])).round(0).astype(int)
    df["Utilization_Pct"] = (df["Utilization"] * 100).round(2)
    df["Utilization_Status"] = pd.cut(
        df["Utilization"],
        bins=[0, 0.5, 0.7, 0.9, 1.0],
        labels=["Underutilized", "Normal", "High", "Critical"],
    )

    logger.success(f"Warehouses cleaned: {len(df)} rows")
    return df


# ─── Merged / Enriched fact tables ────────────────────────────────────────────
def build_fact_orders(
    orders: pd.DataFrame,
    inventory: pd.DataFrame,
    logistics: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building fact_orders …")
    product_cols = inventory[["Product_ID", "Product_Name", "Category", "Unit_Cost", "Warehouse_ID", "Supplier_ID"]]
    fact = orders.merge(product_cols, on="Product_ID", how="left")

    logistics_agg = (
        logistics.groupby("Order_ID")
        .agg(
            Shipment_Count=("Shipment_ID", "count"),
            Avg_Transit_Time=("Transit_Time", "mean"),
            Total_Transport_Cost=("Transport_Cost", "sum"),
            Delayed_Shipments=("Is_Delayed", "sum"),
        )
        .reset_index()
    )
    fact = fact.merge(logistics_agg, on="Order_ID", how="left")
    fact["Delayed_Shipments"] = fact["Delayed_Shipments"].fillna(0).astype(int)
    fact["COGS"] = (fact["Quantity"] * fact["Unit_Cost"]).round(2)
    fact["Gross_Profit"] = (fact["Revenue"] - fact["COGS"]).round(2)
    fact["Gross_Margin_Pct"] = ((fact["Gross_Profit"] / fact["Revenue"].replace(0, np.nan)) * 100).round(2)

    logger.success(f"fact_orders built: {len(fact)} rows")
    return fact


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_etl() -> dict[str, pd.DataFrame]:
    logger.info("═══ SupplyVision ETL Pipeline Starting ═══")

    raw = {name: _load(name) for name in ["orders", "inventory", "suppliers", "logistics", "warehouses"]}

    # customers CSV is optional (only present after Phase 1 data gen)
    try:
        raw["customers"] = _load("customers")
    except FileNotFoundError:
        logger.warning("customers.csv not found – skipping customers table.")

    cleaned = {
        "orders":     clean_orders(raw["orders"]),
        "inventory":  clean_inventory(raw["inventory"]),
        "suppliers":  clean_suppliers(raw["suppliers"]),
        "logistics":  clean_logistics(raw["logistics"]),
        "warehouses": clean_warehouses(raw["warehouses"]),
    }

    if "customers" in raw:
        cleaned["customers"] = _clean_customers(raw["customers"])

    fact_orders = build_fact_orders(cleaned["orders"], cleaned["inventory"], cleaned["logistics"])
    cleaned["fact_orders"] = fact_orders

    for name, df in cleaned.items():
        _save(df, name)

    logger.success("═══ ETL Pipeline Complete ═══")
    return cleaned


def _clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Lightweight customer cleaner used by clean_transform pipeline."""
    logger.info("Cleaning Customers …")
    df = df.copy()
    if "Email" in df.columns:
        df["Email"] = df["Email"].str.lower().str.strip()
    if "Registration_Date" in df.columns:
        df["Registration_Date"] = pd.to_datetime(df["Registration_Date"], errors="coerce")
    df = df.drop_duplicates(subset=["Customer_ID"])
    logger.success(f"Customers cleaned: {len(df)} rows")
    return df


if __name__ == "__main__":
    run_etl()
