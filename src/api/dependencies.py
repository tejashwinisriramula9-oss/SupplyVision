"""
SupplyVision – API Shared Dependencies
=======================================
Data source strategy (controlled by .env USE_MYSQL):

  USE_MYSQL=true   → reads every table from MySQL at startup
  USE_MYSQL=false  → reads Parquet files from data/processed/ (original behaviour)

All downstream routers call the same get_*() accessors regardless of source,
so zero router code changes are required.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

PROCESSED_DIR = Path("data/processed")

# ─── Module-level DataFrame cache ────────────────────────────────────────────
_frames: dict[str, pd.DataFrame] = {}

# ─── MySQL table → internal frame name mapping ────────────────────────────────
# key   = internal cache key (used by get_*() functions)
# value = MySQL table name
_MYSQL_TABLE_MAP: dict[str, str] = {
    "orders":     "fact_orders",
    "inventory":  "fact_inventory",
    "suppliers":  "dim_suppliers",
    "logistics":  "fact_logistics",
    "warehouses": "dim_warehouses",
    "customers":  "dim_customers",
    "fact_orders":"fact_orders",    # alias — same table, richer join column set
}

# ─── Parquet file stem → internal frame name mapping ────────────────────────
_PARQUET_MAP: dict[str, str] = {
    "orders":     "orders_clean",
    "inventory":  "inventory_clean",
    "suppliers":  "suppliers_clean",
    "logistics":  "logistics_clean",
    "warehouses": "warehouses_clean",
    "customers":  "customers_clean",
    "fact_orders":"fact_orders_clean",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _use_mysql() -> bool:
    return os.getenv("USE_MYSQL", "false").lower() in ("true", "1", "yes")


def _load_from_mysql(name: str) -> Optional[pd.DataFrame]:
    """Load one table from MySQL into a DataFrame."""
    from src.db.connection import read_table, get_engine
    table = _MYSQL_TABLE_MAP.get(name)
    if not table:
        logger.warning(f"No MySQL table mapping for: {name}")
        return None
    try:
        df = read_table(table)
        logger.info(f"  [MySQL] {table}: {len(df):,} rows")
        return df
    except Exception as exc:
        logger.error(f"  [MySQL] Failed to load {table}: {exc}")
        return None


def _load_from_parquet(name: str) -> Optional[pd.DataFrame]:
    """Load one table from processed Parquet/CSV files."""
    stem = _PARQUET_MAP.get(name, f"{name}_clean")
    path = PROCESSED_DIR / f"{stem}.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        logger.info(f"  [Parquet] {stem}: {len(df):,} rows")
        return df
    csv_path = PROCESSED_DIR / f"{stem}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, low_memory=False)
        logger.info(f"  [CSV] {stem}: {len(df):,} rows")
        return df
    logger.warning(f"  Data file not found: {stem}")
    return None


# ─── Startup loader ───────────────────────────────────────────────────────────
def load_dataframes() -> None:
    """
    Called once at API startup.
    Populates _frames from MySQL (if USE_MYSQL=true) or Parquet files.
    All get_*() accessors read from this cache — zero per-request I/O.
    """
    source = "MySQL" if _use_mysql() else "Parquet"
    logger.info(f"Loading data from: {source}")

    names = ["orders", "inventory", "suppliers", "logistics",
             "warehouses", "customers", "fact_orders"]

    for name in names:
        if _use_mysql():
            df = _load_from_mysql(name)
        else:
            df = _load_from_parquet(name)

        if df is not None and not df.empty:
            _frames[name] = df
        else:
            _frames[name] = pd.DataFrame()
            logger.warning(f"  Empty DataFrame for: {name}")

    # Post-load type normalisation for MySQL results
    # (MySQL returns dates as date objects; some DAX-facing columns need strings)
    if _use_mysql():
        _normalise_mysql_types()

    logger.success(f"Data ready. Source: {source}  |  "
                   f"Frames: {[k for k,v in _frames.items() if not v.empty]}")


def _normalise_mysql_types() -> None:
    """
    Ensures DataFrame dtypes match what routers and KPIEngine expect,
    regardless of whether data came from MySQL or Parquet.
    """
    # fact_orders: ensure Order_Date is datetime64 and date-part columns are int
    fo = _frames.get("fact_orders", pd.DataFrame())
    if not fo.empty:
        if "Order_Date" in fo.columns:
            fo["Order_Date"] = pd.to_datetime(fo["Order_Date"], errors="coerce")
        for col in ["Year", "Month", "Quarter", "WeekOfYear",
                    "Quantity", "Delayed_Shipments", "Shipment_Count"]:
            if col in fo.columns:
                fo[col] = pd.to_numeric(fo[col], errors="coerce").fillna(0).astype(int)
        _frames["fact_orders"] = fo

    # logistics: ensure Ship_Date / Delivery_Date are datetime64, Is_Delayed is int
    lg = _frames.get("logistics", pd.DataFrame())
    if not lg.empty:
        for col in ["Ship_Date", "Delivery_Date"]:
            if col in lg.columns:
                lg[col] = pd.to_datetime(lg[col], errors="coerce")
        if "Is_Delayed" in lg.columns:
            lg["Is_Delayed"] = pd.to_numeric(lg["Is_Delayed"], errors="coerce").fillna(0).astype(int)
        _frames["logistics"] = lg

    # inventory: Reliability_Tier / Utilization_Status may be bytes in MySQL
    sup = _frames.get("suppliers", pd.DataFrame())
    if not sup.empty and "Reliability_Tier" in sup.columns:
        sup["Reliability_Tier"] = sup["Reliability_Tier"].astype(str)
        _frames["suppliers"] = sup

    wh = _frames.get("warehouses", pd.DataFrame())
    if not wh.empty and "Utilization_Status" in wh.columns:
        wh["Utilization_Status"] = wh["Utilization_Status"].astype(str)
        _frames["warehouses"] = wh

    # Mirror fact_orders → orders cache key (some routers use get_orders())
    if not _frames["fact_orders"].empty:
        _frames["orders"] = _frames["fact_orders"]


# ─── Public accessors (unchanged API contract) ───────────────────────────────
def get_orders() -> pd.DataFrame:
    return _frames.get("orders", pd.DataFrame())


def get_inventory() -> pd.DataFrame:
    return _frames.get("inventory", pd.DataFrame())


def get_suppliers() -> pd.DataFrame:
    return _frames.get("suppliers", pd.DataFrame())


def get_logistics() -> pd.DataFrame:
    return _frames.get("logistics", pd.DataFrame())


def get_warehouses() -> pd.DataFrame:
    return _frames.get("warehouses", pd.DataFrame())


def get_customers() -> pd.DataFrame:
    return _frames.get("customers", pd.DataFrame())


def get_fact_orders() -> pd.DataFrame:
    fo = _frames.get("fact_orders", pd.DataFrame())
    if fo.empty:
        return _frames.get("orders", pd.DataFrame())
    return fo
