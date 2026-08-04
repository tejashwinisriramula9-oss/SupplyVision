"""
SupplyVision – Phase 1: data_cleaning.py
==========================================
Standalone enterprise-grade data cleaning module.

Responsibilities:
  - Load raw Excel / CSV files
  - Apply domain-specific cleaning rules per table
  - Detect and handle duplicates
  - Impute or flag missing values with audit trail
  - Standardise date formats to ISO-8601 (YYYY-MM-DD)
  - Validate business rules (price > cost, stock ≥ 0, etc.)
  - Emit a cleaning quality report
  - Save cleaned output to data/processed/

Usage:
    python src/etl/data_cleaning.py
    python src/etl/data_cleaning.py --table orders
    python src/etl/data_cleaning.py --report-only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

Path("logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/data_cleaning.log", level="DEBUG", rotation="5 MB")

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ─── Cleaning Report ──────────────────────────────────────────────────────────
@dataclass
class TableCleanReport:
    table: str
    rows_in:          int = 0
    rows_out:         int = 0
    duplicates_dropped: int = 0
    nulls_filled:     int = 0
    invalid_dropped:  int = 0
    business_rule_fixes: int = 0
    derived_cols_added: list[str] = field(default_factory=list)
    warnings:         list[str] = field(default_factory=list)

    @property
    def rows_dropped(self) -> int:
        return self.rows_in - self.rows_out

    def summary(self) -> str:
        return (
            f"[{self.table}] IN={self.rows_in:,}  OUT={self.rows_out:,}  "
            f"dupes={self.duplicates_dropped}  nulls_filled={self.nulls_filled}  "
            f"invalid_dropped={self.invalid_dropped}  biz_fixes={self.business_rule_fixes}"
        )


# ─── Loaders ─────────────────────────────────────────────────────────────────
def load_raw(name: str) -> pd.DataFrame:
    csv = RAW_DIR / f"{name}.csv"
    if csv.exists():
        df = pd.read_csv(csv, low_memory=False)
        logger.info(f"  Loaded {name}.csv: {len(df):,} rows")
        return df
    xlsx = RAW_DIR / "supply_chain_data.xlsx"
    if xlsx.exists():
        df = pd.read_excel(xlsx, sheet_name=name.capitalize())
        logger.info(f"  Loaded Excel/{name.capitalize()}: {len(df):,} rows")
        return df
    raise FileNotFoundError(
        f"No raw data for '{name}'. Run: python pipeline.py --steps gen"
    )


def save_cleaned(df: pd.DataFrame, name: str) -> None:
    df.to_csv(PROCESSED_DIR / f"{name}_clean.csv", index=False)
    df.to_parquet(PROCESSED_DIR / f"{name}_clean.parquet", index=False)
    logger.success(f"  Saved {name}_clean: {len(df):,} rows → {PROCESSED_DIR}")


# ─── Shared helpers ───────────────────────────────────────────────────────────
def _drop_full_duplicates(df: pd.DataFrame, report: TableCleanReport) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    report.duplicates_dropped += dropped
    if dropped:
        report.warnings.append(f"Dropped {dropped} fully duplicate rows")
    return df


def _drop_pk_duplicates(df: pd.DataFrame, pk: str, report: TableCleanReport) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=[pk], keep="first")
    dropped = before - len(df)
    report.duplicates_dropped += dropped
    if dropped:
        report.warnings.append(f"Dropped {dropped} PK duplicates on {pk}")
    return df


def _coerce_numeric(df: pd.DataFrame, cols: list[str], report: TableCleanReport,
                    fill: float | None = None) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            continue
        before_nulls = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if fill is not None:
            filled = df[col].isna().sum()
            df[col] = df[col].fillna(fill)
            report.nulls_filled += max(0, filled - before_nulls)
    return df


def _standardise_dates(df: pd.DataFrame, cols: list[str], report: TableCleanReport) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            continue
        before = df[col].isna().sum()
        df[col] = pd.to_datetime(df[col], errors="coerce")
        after = df[col].isna().sum()
        new_nulls = after - before
        if new_nulls > 0:
            report.warnings.append(f"{col}: {new_nulls} unparseable dates set to NaT")
    return df


def _title_case(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.strip().str.title()
    return df


# ─── Table cleaners ───────────────────────────────────────────────────────────
def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="orders", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Order_ID", report)

    # ── Dates ────────────────────────────────────────────────────────────────
    df = _standardise_dates(df, ["Order_Date"], report)
    invalid_date = df["Order_Date"].isna().sum()
    df = df.dropna(subset=["Order_Date"])
    report.invalid_dropped += invalid_date

    # ── Numerics ─────────────────────────────────────────────────────────────
    df = _coerce_numeric(df, ["Quantity", "Unit_Price", "Revenue", "Discount"], report)
    df["Discount"] = df["Discount"].fillna(0).clip(0, 1)

    # Business rules: no negative/zero revenue, no zero quantity
    bad_rev = (df["Revenue"] <= 0).sum()
    bad_qty = (df["Quantity"] <= 0).sum()
    df = df[(df["Revenue"] > 0) & (df["Quantity"] > 0)]
    report.invalid_dropped += bad_rev + bad_qty
    if bad_rev:
        report.warnings.append(f"Dropped {bad_rev} rows with Revenue ≤ 0")
    if bad_qty:
        report.warnings.append(f"Dropped {bad_qty} rows with Quantity ≤ 0")

    # ── String normalisation ──────────────────────────────────────────────────
    df = _title_case(df, ["Order_Status", "Sales_Channel"])

    # ── Derived columns ───────────────────────────────────────────────────────
    df["Year"]       = df["Order_Date"].dt.year
    df["Month"]      = df["Order_Date"].dt.month
    df["Quarter"]    = df["Order_Date"].dt.quarter
    df["YearMonth"]  = df["Order_Date"].dt.to_period("M").astype(str)
    df["YearQuarter"]= df["Year"].astype(str) + " Q" + df["Quarter"].astype(str)
    df["WeekOfYear"] = df["Order_Date"].dt.isocalendar().week.astype(int)
    df["DayOfWeek"]  = df["Order_Date"].dt.day_name()
    report.derived_cols_added = ["Year", "Month", "Quarter", "YearMonth",
                                  "YearQuarter", "WeekOfYear", "DayOfWeek"]

    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


def clean_inventory(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="inventory", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Product_ID", report)

    df = _coerce_numeric(df, ["Current_Stock", "Safety_Stock", "Reorder_Point",
                               "Unit_Cost", "Unit_Price"], report, fill=0)

    # Business rules
    neg_stock = (df["Current_Stock"] < 0).sum()
    df["Current_Stock"] = df["Current_Stock"].clip(lower=0)
    if neg_stock:
        report.business_rule_fixes += neg_stock
        report.warnings.append(f"Clipped {neg_stock} negative Current_Stock values to 0")

    neg_cost = (df["Unit_Cost"] <= 0).sum()
    df["Unit_Cost"]  = df["Unit_Cost"].clip(lower=0.01)
    df["Unit_Price"] = df["Unit_Price"].clip(lower=0.01)
    if neg_cost:
        report.business_rule_fixes += neg_cost

    # Price must be ≥ cost (enforce with a floor)
    price_lt_cost = (df["Unit_Price"] < df["Unit_Cost"]).sum()
    df.loc[df["Unit_Price"] < df["Unit_Cost"], "Unit_Price"] = (
        df.loc[df["Unit_Price"] < df["Unit_Cost"], "Unit_Cost"] * 1.20
    )
    if price_lt_cost:
        report.business_rule_fixes += price_lt_cost
        report.warnings.append(f"Fixed {price_lt_cost} rows where Unit_Price < Unit_Cost (set to cost×1.2)")

    # Derived
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
    df = _standardise_dates(df, ["Last_Updated"], report)
    df = _title_case(df, ["Category"])

    report.derived_cols_added = ["Inventory_Value", "Stock_Status", "Margin_Pct"]
    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


def clean_suppliers(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="suppliers", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Supplier_ID", report)

    # Lead time: impute with median
    lt_nulls = df["Lead_Time"].isna().sum()
    median_lt = df["Lead_Time"].median()
    df["Lead_Time"] = pd.to_numeric(df["Lead_Time"], errors="coerce").fillna(median_lt)
    report.nulls_filled += lt_nulls

    # Reliability: clip to [0, 1]
    df["Reliability_Score"] = (
        pd.to_numeric(df["Reliability_Score"], errors="coerce").fillna(0.75).clip(0, 1)
    )
    df["Supplier_Cost"] = pd.to_numeric(df["Supplier_Cost"], errors="coerce").fillna(0)

    # Email normalisation
    if "Contact_Email" in df.columns:
        df["Contact_Email"] = df["Contact_Email"].str.lower().str.strip()

    # Derived tiers
    df["Reliability_Tier"] = pd.cut(
        df["Reliability_Score"],
        bins=[0, 0.65, 0.80, 0.90, 1.0],
        labels=["Poor", "Acceptable", "Good", "Excellent"],
    ).astype(str)
    df["Lead_Time_Category"] = pd.cut(
        df["Lead_Time"],
        bins=[0, 7, 14, 30, 999],
        labels=["Express", "Standard", "Extended", "Long Lead"],
    ).astype(str)

    report.derived_cols_added = ["Reliability_Tier", "Lead_Time_Category"]
    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


def clean_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="customers", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Customer_ID", report)

    # Normalise email
    if "Email" in df.columns:
        df["Email"] = df["Email"].str.lower().str.strip()

    # Standardise dates
    df = _standardise_dates(df, ["Registration_Date"], report)

    # Enforce known segment values
    valid_segments = {"Enterprise", "Mid-Market", "SMB", "Government"}
    bad_seg = ~df["Customer_Segment"].isin(valid_segments)
    if bad_seg.sum():
        df.loc[bad_seg, "Customer_Segment"] = "SMB"
        report.business_rule_fixes += int(bad_seg.sum())
        report.warnings.append(f"Replaced {bad_seg.sum()} unknown Customer_Segment values with 'SMB'")

    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


def clean_logistics(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="logistics", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Shipment_ID", report)

    df = _standardise_dates(df, ["Ship_Date", "Delivery_Date"], report)
    bad_dates = df["Ship_Date"].isna().sum()
    df = df.dropna(subset=["Ship_Date", "Delivery_Date"])
    report.invalid_dropped += bad_dates

    # Delivery must be after or same as ship date
    bad_delivery = (df["Delivery_Date"] < df["Ship_Date"]).sum()
    df = df[df["Delivery_Date"] >= df["Ship_Date"]]
    if bad_delivery:
        report.invalid_dropped += bad_delivery
        report.warnings.append(f"Dropped {bad_delivery} rows where Delivery_Date < Ship_Date")

    df = _coerce_numeric(df, ["Transit_Time", "Transport_Cost", "Weight_KG",
                               "Expected_Transit_Days"], report)
    median_tt = df["Transit_Time"].median()
    df["Transit_Time"] = df["Transit_Time"].fillna(median_tt).clip(lower=1)
    df["Transport_Cost"] = df["Transport_Cost"].fillna(0)
    df["Weight_KG"] = df["Weight_KG"].fillna(1)

    # Derived
    df["Delay_Days"] = (
        (df["Delivery_Date"] - df["Ship_Date"]).dt.days - df["Expected_Transit_Days"]
    ).clip(lower=0)
    df["Is_Delayed"] = (
        df["Delivery_Date"] > df["Ship_Date"] + pd.to_timedelta(df["Expected_Transit_Days"], unit="D")
    ).astype(int)
    df["Cost_Per_KG"] = (df["Transport_Cost"] / df["Weight_KG"].replace(0, np.nan)).round(2)
    df["Ship_Year"]     = df["Ship_Date"].dt.year
    df["Ship_Month"]    = df["Ship_Date"].dt.month
    df["Ship_Quarter"]  = df["Ship_Date"].dt.quarter
    df["Ship_YearMonth"]= df["Ship_Date"].dt.to_period("M").astype(str)
    df = _title_case(df, ["Carrier", "Delivery_Status"])

    report.derived_cols_added = ["Delay_Days", "Is_Delayed", "Cost_Per_KG",
                                   "Ship_Year", "Ship_Month", "Ship_Quarter", "Ship_YearMonth"]
    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


def clean_warehouses(df: pd.DataFrame) -> tuple[pd.DataFrame, TableCleanReport]:
    report = TableCleanReport(table="warehouses", rows_in=len(df))

    df = _drop_full_duplicates(df, report)
    df = _drop_pk_duplicates(df, "Warehouse_ID", report)

    df = _coerce_numeric(df, ["Capacity", "Utilization"], report)
    df["Capacity"]    = df["Capacity"].fillna(10_000).clip(lower=1)
    df["Utilization"] = df["Utilization"].fillna(0.70).clip(0, 1)

    df["Available_Capacity"] = (df["Capacity"] * (1 - df["Utilization"])).round(0).astype(int)
    df["Utilization_Pct"]    = (df["Utilization"] * 100).round(2)
    df["Utilization_Status"] = pd.cut(
        df["Utilization"],
        bins=[0, 0.5, 0.7, 0.9, 1.0],
        labels=["Underutilized", "Normal", "High", "Critical"],
    ).astype(str)

    report.derived_cols_added = ["Available_Capacity", "Utilization_Pct", "Utilization_Status"]
    report.rows_out = len(df)
    logger.success(report.summary())
    return df, report


# ─── Enriched fact_orders ─────────────────────────────────────────────────────
def build_fact_orders(
    orders: pd.DataFrame,
    inventory: pd.DataFrame,
    logistics: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("Building fact_orders (enriched join) …")
    product_cols = inventory[["Product_ID", "Category", "Unit_Cost",
                               "Warehouse_ID", "Supplier_ID"]].drop_duplicates("Product_ID")
    fact = orders.merge(product_cols, on="Product_ID", how="left",
                        suffixes=("", "_prod"))

    # Prefer original Category if present
    if "Category_prod" in fact.columns:
        fact["Category"] = fact["Category"].combine_first(fact.pop("Category_prod"))
    else:
        fact.rename(columns={"Category_prod": "Category"}, errors="ignore", inplace=True)

    logistics_agg = (
        logistics.groupby("Order_ID")
        .agg(
            Shipment_Count     = ("Shipment_ID",   "count"),
            Avg_Transit_Time   = ("Transit_Time",   "mean"),
            Total_Transport_Cost = ("Transport_Cost", "sum"),
            Delayed_Shipments  = ("Is_Delayed",     "sum"),
        )
        .reset_index()
    )
    fact = fact.merge(logistics_agg, on="Order_ID", how="left")
    fact["Shipment_Count"]    = fact["Shipment_Count"].fillna(0).astype(int)
    fact["Delayed_Shipments"] = fact["Delayed_Shipments"].fillna(0).astype(int)

    fact["COGS"]             = (fact["Quantity"] * fact["Unit_Cost"]).round(2)
    fact["Gross_Profit"]     = (fact["Revenue"] - fact["COGS"]).round(2)
    fact["Gross_Margin_Pct"] = (
        (fact["Gross_Profit"] / fact["Revenue"].replace(0, np.nan)) * 100
    ).round(2)

    logger.success(f"fact_orders built: {len(fact):,} rows")
    return fact


# ─── Quality Report ───────────────────────────────────────────────────────────
def print_quality_report(reports: dict[str, TableCleanReport]) -> None:
    print("\n" + "═" * 70)
    print("  SupplyVision – Data Quality Report")
    print("═" * 70)
    total_in = total_out = 0
    for name, r in reports.items():
        total_in  += r.rows_in
        total_out += r.rows_out
        status = "✅" if r.rows_dropped == 0 else "⚠️ "
        print(f"\n  {status} {name.upper()}")
        print(f"     Rows in / out : {r.rows_in:>6,} / {r.rows_out:>6,}  (dropped {r.rows_dropped:,})")
        print(f"     Duplicates    : {r.duplicates_dropped}")
        print(f"     Nulls filled  : {r.nulls_filled}")
        print(f"     Biz-rule fixes: {r.business_rule_fixes}")
        if r.derived_cols_added:
            print(f"     Derived cols  : {', '.join(r.derived_cols_added)}")
        for w in r.warnings:
            print(f"     ⚠  {w}")
    print(f"\n  Total: {total_in:,} rows in → {total_out:,} rows out")
    print("═" * 70 + "\n")


def save_quality_report(reports: dict[str, TableCleanReport]) -> None:
    out = {name: asdict(r) for name, r in reports.items()}
    path = Path("data/exports/data_quality_report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, default=str))
    logger.info(f"Quality report saved: {path}")


# ─── Main ─────────────────────────────────────────────────────────────────────
CLEANERS = {
    "orders":     clean_orders,
    "inventory":  clean_inventory,
    "suppliers":  clean_suppliers,
    "customers":  clean_customers,
    "logistics":  clean_logistics,
    "warehouses": clean_warehouses,
}


def run_cleaning(
    only_table: str | None = None,
    report_only: bool = False,
) -> dict[str, TableCleanReport]:
    logger.info("═══ SupplyVision data_cleaning.py Starting ═══")

    tables = [only_table] if only_table else list(CLEANERS.keys())
    cleaned: dict[str, pd.DataFrame] = {}
    quality_reports: dict[str, TableCleanReport] = {}

    for name in tables:
        try:
            raw = load_raw(name)
        except FileNotFoundError as exc:
            logger.warning(f"Skipping {name}: {exc}")
            continue

        df_clean, rpt = CLEANERS[name](raw)
        quality_reports[name] = rpt
        cleaned[name] = df_clean

    # Build enriched fact table if all three sources are available
    if not only_table and all(k in cleaned for k in ["orders", "inventory", "logistics"]):
        fact = build_fact_orders(cleaned["orders"], cleaned["inventory"], cleaned["logistics"])
        cleaned["fact_orders"] = fact

    if not report_only:
        for name, df in cleaned.items():
            save_cleaned(df, name)

    print_quality_report(quality_reports)
    save_quality_report(quality_reports)

    logger.success("═══ Cleaning complete ═══")
    return quality_reports


def main():
    parser = argparse.ArgumentParser(description="SupplyVision – Data Cleaning")
    parser.add_argument("--table",       default=None,
                        help="Clean a single table (orders/inventory/suppliers/etc.)")
    parser.add_argument("--report-only", action="store_true",
                        help="Run cleaning but do NOT save outputs")
    args = parser.parse_args()
    run_cleaning(only_table=args.table, report_only=args.report_only)


if __name__ == "__main__":
    main()
