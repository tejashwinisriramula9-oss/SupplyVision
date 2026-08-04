"""
SupplyVision – Phase 1: load_data.py
=====================================
Enterprise ETL loader — reads processed CSV/Parquet files
and loads them into MySQL using the schema defined in schema.sql.

Features:
  - Auto-creates schema if not exists
  - FK-safe load order
  - Truncate-and-reload strategy (idempotent)
  - Per-table column mapping
  - Batch inserts (configurable chunk size)
  - Row-count verification after each load
  - Full audit logging to logs/load_data.log

Usage:
    python src/etl/load_data.py
    python src/etl/load_data.py --env .env.production
    python src/etl/load_data.py --skip-schema   # skip DDL, load data only
    python src/etl/load_data.py --table fact_orders  # load single table
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# ─── Logging ─────────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/load_data.log", level="DEBUG", rotation="10 MB", retention="30 days",
           format="{time} | {level} | {message}")

PROCESSED_DIR = Path("data/processed")
SQL_DIR       = Path("sql")

# ─── FK-safe load order ───────────────────────────────────────────────────────
# (table_name, parquet_stem)
LOAD_ORDER: list[tuple[str, str]] = [
    ("dim_warehouses", "warehouses_clean"),
    ("dim_suppliers",  "suppliers_clean"),
    ("dim_customers",  "customers_clean"),
    ("dim_products",   "inventory_clean"),
    ("fact_inventory", "inventory_clean"),
    ("fact_orders",    "fact_orders_clean"),
    ("fact_logistics", "logistics_clean"),
]

# Columns to select from each source DataFrame (avoids loading extra computed cols)
COLUMN_MAPS: dict[str, list[str]] = {
    "dim_warehouses": [
        "Warehouse_ID", "Warehouse_Name", "Capacity", "Utilization",
        "Available_Capacity", "Utilization_Pct", "Utilization_Status", "Location",
    ],
    "dim_suppliers": [
        "Supplier_ID", "Supplier_Name", "Country", "Region",
        "Lead_Time", "Reliability_Score", "Reliability_Tier", "Lead_Time_Category",
        "Supplier_Cost", "Contact_Email", "Phone",
    ],
    "dim_customers": [
        "Customer_ID", "Customer_Name", "Company", "Email", "Phone",
        "Country", "Region", "Customer_Segment", "Registration_Date",
    ],
    "dim_products": [
        "Product_ID", "Product_Name", "Category",
        "Safety_Stock", "Reorder_Point", "Unit_Cost", "Unit_Price",
        "Warehouse_ID", "Supplier_ID",
    ],
    "fact_inventory": [
        "Product_ID", "Current_Stock", "Inventory_Value", "Stock_Status", "Last_Updated",
    ],
    "fact_orders": [
        "Order_ID", "Product_ID", "Customer_ID", "Order_Date",
        "Year", "Month", "Quarter", "YearMonth", "YearQuarter",
        "WeekOfYear", "DayOfWeek", "Quantity", "Unit_Price", "Discount",
        "Revenue", "COGS", "Gross_Profit", "Gross_Margin_Pct",
        "Order_Status", "Sales_Channel", "Category",
        "Warehouse_ID", "Supplier_ID",
        "Shipment_Count", "Avg_Transit_Time", "Total_Transport_Cost", "Delayed_Shipments",
    ],
    "fact_logistics": [
        "Shipment_ID", "Order_ID", "Supplier_ID",
        "Ship_Date", "Delivery_Date", "Expected_Transit_Days", "Transit_Time",
        "Delay_Days", "Is_Delayed", "Transport_Cost", "Cost_Per_KG",
        "Carrier", "Delivery_Status", "Origin_Country", "Destination_Country",
        "Weight_KG", "Ship_Year", "Ship_Month", "Ship_Quarter", "Ship_YearMonth",
    ],
}


# ─── DB connection ────────────────────────────────────────────────────────────
def get_engine(env_file: str = ".env"):
    load_dotenv(env_file)
    host     = os.getenv("DB_HOST",     "localhost")
    port     = os.getenv("DB_PORT",     "3306")
    db       = os.getenv("DB_NAME",     "supply_vision")
    user     = os.getenv("DB_USER",     "sv_user")
    password = os.getenv("DB_PASSWORD", "SV@SecurePass2024!")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"
    try:
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.success(f"Connected to MySQL: {host}:{port}/{db}")
        return engine
    except OperationalError as exc:
        logger.error(f"Cannot connect to MySQL: {exc}")
        raise


# ─── Schema setup ─────────────────────────────────────────────────────────────
def apply_schema(engine) -> None:
    """Execute schema.sql (idempotent CREATE IF NOT EXISTS + views + procs)."""
    schema_file = SQL_DIR / "schema.sql"
    if not schema_file.exists():
        logger.warning(f"schema.sql not found at {schema_file} – skipping DDL.")
        return

    sql_text = schema_file.read_text(encoding="utf-8")
    # Split on DELIMITER-bounded blocks and plain semicolons
    statements = _split_sql(sql_text)

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            try:
                conn.execute(text(stmt))
            except SQLAlchemyError as exc:
                logger.warning(f"DDL warning (non-fatal): {exc}")
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    logger.success("Schema applied.")


def _split_sql(sql: str) -> list[str]:
    """Naively split SQL ignoring DELIMITER blocks (handled by stored proc multi-line)."""
    import re
    # Remove DELIMITER blocks entirely – they don't work via SQLAlchemy text()
    sql = re.sub(r"DELIMITER\s*\$\$.*?DELIMITER\s*;", "", sql, flags=re.DOTALL)
    return [s.strip() for s in sql.split(";") if s.strip()]


# ─── Data loading ─────────────────────────────────────────────────────────────
def _load_parquet(stem: str) -> pd.DataFrame:
    parquet = PROCESSED_DIR / f"{stem}.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    csv = PROCESSED_DIR / f"{stem}.csv"
    if csv.exists():
        return pd.read_csv(csv, low_memory=False)
    raise FileNotFoundError(
        f"Cannot find {parquet} or {csv}. Run: python pipeline.py --steps gen etl"
    )


def _prep_df(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Select required columns, coerce types, replace NaN with None."""
    cols = COLUMN_MAPS.get(table_name, list(df.columns))
    available = [c for c in cols if c in df.columns]
    df = df[available].copy().drop_duplicates()

    # Convert Period columns to str
    for col in df.select_dtypes(include="period").columns:
        df[col] = df[col].astype(str)

    # Convert datetime to date where needed
    date_cols = [c for c in df.columns if "Date" in c or "date" in c]
    for col in date_cols:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.date

    # Convert categoricals to str
    for col in df.select_dtypes(include="category").columns:
        df[col] = df[col].astype(str)

    df = df.where(pd.notnull(df), None)
    return df


def load_table(
    engine,
    table_name: str,
    parquet_stem: str,
    chunk_size: int = 500,
) -> int:
    logger.info(f"  Loading {table_name} ← {parquet_stem} …")
    try:
        df = _load_parquet(parquet_stem)
    except FileNotFoundError as exc:
        logger.warning(f"  Skipping {table_name}: {exc}")
        return 0

    df = _prep_df(df, table_name)

    with engine.begin() as conn:
        conn.execute(text(f"SET FOREIGN_KEY_CHECKS=0"))
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))

    df.to_sql(
        table_name, engine,
        if_exists="append",
        index=False,
        chunksize=chunk_size,
        method="multi",
    )

    # Verify row count
    with engine.connect() as conn:
        db_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

    if db_count == len(df):
        logger.success(f"  ✔  {table_name}: {db_count:,} rows loaded.")
    else:
        logger.warning(f"  ⚠  {table_name}: expected {len(df):,}, got {db_count:,}.")

    return int(db_count)


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_load(
    env_file: str = ".env",
    skip_schema: bool = False,
    only_table: str | None = None,
    chunk_size: int = 500,
) -> dict[str, int]:
    logger.info("═══ SupplyVision load_data.py Starting ═══")

    engine = get_engine(env_file)

    if not skip_schema:
        logger.info("Applying schema …")
        apply_schema(engine)

    results: dict[str, int] = {}
    order = [(t, p) for t, p in LOAD_ORDER if only_table is None or t == only_table]

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    for table_name, parquet_stem in order:
        results[table_name] = load_table(engine, table_name, parquet_stem, chunk_size)

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    total = sum(results.values())
    logger.success(f"═══ Load complete: {total:,} total rows across {len(results)} tables ═══")
    return results


def main():
    parser = argparse.ArgumentParser(description="SupplyVision – MySQL Data Loader")
    parser.add_argument("--env",         default=".env",    help="Path to .env file")
    parser.add_argument("--skip-schema", action="store_true", help="Skip DDL step")
    parser.add_argument("--table",       default=None,      help="Load a single table only")
    parser.add_argument("--chunk-size",  type=int, default=500)
    args = parser.parse_args()

    run_load(
        env_file=args.env,
        skip_schema=args.skip_schema,
        only_table=args.table,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
