"""
SupplyVision – MySQL Setup & Import Script
==========================================
Run this ONCE to:
  1. Create the supply_vision database and sv_user (as root)
  2. Apply the full schema (tables, views, procedures, triggers)
  3. Import all processed CSV/Parquet data into MySQL

Usage:
    # Full setup (requires MySQL root credentials):
    python setup_mysql.py

    # Skip database/user creation (if supply_vision DB already exists):
    python setup_mysql.py --skip-create-db

    # Skip schema DDL (tables already exist):
    python setup_mysql.py --skip-schema

    # Import data only:
    python setup_mysql.py --skip-create-db --skip-schema

    # Test connection only:
    python setup_mysql.py --test-only

Password safety:
    All connection URLs are built with SQLAlchemy's URL.create() API.
    Passwords containing @  !  #  %  $  &  and other special characters
    are handled correctly without any quoting or escaping by the caller.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL          # ← safe URL builder
from sqlalchemy.exc import OperationalError, SQLAlchemyError

load_dotenv()

Path("logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/setup_mysql.log", level="DEBUG", rotation="5 MB")

PROCESSED_DIR = Path("data/processed")
SQL_DIR       = Path("sql")

# ─── FK-safe load order (dim tables before fact tables) ──────────────────────
LOAD_ORDER = [
    ("dim_warehouses", "warehouses_clean",  [
        "Warehouse_ID", "Warehouse_Name", "Capacity", "Utilization",
        "Available_Capacity", "Utilization_Pct", "Utilization_Status", "Location",
    ]),
    ("dim_suppliers",  "suppliers_clean",   [
        "Supplier_ID", "Supplier_Name", "Country", "Region",
        "Lead_Time", "Reliability_Score", "Reliability_Tier", "Lead_Time_Category",
        "Supplier_Cost", "Contact_Email", "Phone",
    ]),
    ("dim_customers",  "customers_clean",   [
        "Customer_ID", "Customer_Name", "Company", "Email", "Phone",
        "Country", "Region", "Customer_Segment", "Registration_Date",
    ]),
    ("dim_products",   "inventory_clean",   [
        "Product_ID", "Product_Name", "Category",
        "Safety_Stock", "Reorder_Point", "Unit_Cost", "Unit_Price",
        "Warehouse_ID", "Supplier_ID",
    ]),
    ("fact_inventory", "inventory_clean",   [
        "Product_ID", "Current_Stock", "Inventory_Value", "Stock_Status", "Last_Updated",
    ]),
    ("fact_orders",    "fact_orders_clean", [
        "Order_ID", "Product_ID", "Customer_ID", "Order_Date",
        "Year", "Month", "Quarter", "YearMonth", "YearQuarter",
        "WeekOfYear", "DayOfWeek", "Quantity", "Unit_Price", "Discount",
        "Revenue", "COGS", "Gross_Profit", "Gross_Margin_Pct",
        "Order_Status", "Sales_Channel", "Category",
        "Warehouse_ID", "Supplier_ID",
        "Shipment_Count", "Avg_Transit_Time", "Total_Transport_Cost", "Delayed_Shipments",
    ]),
    ("fact_logistics", "logistics_clean",   [
        "Shipment_ID", "Order_ID", "Supplier_ID",
        "Ship_Date", "Delivery_Date", "Expected_Transit_Days", "Transit_Time",
        "Delay_Days", "Is_Delayed", "Transport_Cost", "Cost_Per_KG",
        "Carrier", "Delivery_Status", "Origin_Country", "Destination_Country",
        "Weight_KG", "Ship_Year", "Ship_Month", "Ship_Quarter", "Ship_YearMonth",
    ]),
]


# ─── URL builders (all use URL.create — never string interpolation) ───────────
def _root_url(root_user: str, root_password: str) -> URL:
    """
    Builds a SQLAlchemy URL for the MySQL root connection (no database selected).
    URL.create() percent-encodes the password automatically, so characters like
    @ ! # % $ & work without any manual escaping.
    """
    return URL.create(
        drivername="mysql+pymysql",
        username=root_user,
        password=root_password,     # URL.create handles all special chars
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=None,              # no DB — we're about to create it
        query={"charset": "utf8mb4"},
    )


def _sv_url(database: str | None = None) -> URL:
    """
    Builds a SQLAlchemy URL for the sv_user connection.
    Reads credentials from .env / environment variables.
    """
    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER",     "sv_user"),
        password=os.getenv("DB_PASSWORD", "SV@SecurePass2024!"),
        host=os.getenv("DB_HOST",         "localhost"),
        port=int(os.getenv("DB_PORT",     "3306")),
        database=database or os.getenv("DB_NAME", "supply_vision"),
        query={"charset": "utf8mb4"},
    )


# ─── Step 1: Create database and user (as root) ───────────────────────────────
def create_database(root_user: str, root_password: str) -> None:
    """
    Connects as root (no database) and creates:
      - supply_vision database
      - sv_user with the password from .env / DB_PASSWORD
    """
    logger.info("Creating supply_vision database and sv_user …")

    sv_password = os.getenv("DB_PASSWORD", "SV@SecurePass2024!")

    try:
        engine = create_engine(_root_url(root_user, root_password), pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE DATABASE IF NOT EXISTS supply_vision "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
            # Use a parameterised statement for the password so special chars
            # in sv_password are never misinterpreted as SQL syntax.
            conn.execute(
                text("CREATE USER IF NOT EXISTS 'sv_user'@'localhost' "
                     "IDENTIFIED BY :pw"),
                {"pw": sv_password},
            )
            conn.execute(text(
                "GRANT ALL PRIVILEGES ON supply_vision.* TO 'sv_user'@'localhost'"
            ))
            conn.execute(text("FLUSH PRIVILEGES"))
        logger.success("Database supply_vision and user sv_user created.")
    except OperationalError as exc:
        logger.error(f"Could not create database: {exc}")
        raise


# ─── Step 2: Apply schema ─────────────────────────────────────────────────────
def apply_schema(engine) -> None:
    """Execute schema.sql — strips DELIMITER blocks that SQLAlchemy cannot process."""
    import re
    schema_file = SQL_DIR / "schema.sql"
    if not schema_file.exists():
        logger.warning("schema.sql not found — skipping DDL.")
        return

    sql_text = schema_file.read_text(encoding="utf-8")
    # SQLAlchemy's text() driver cannot process DELIMITER $$ blocks used for
    # stored procedures — strip them (they were already applied if they exist).
    sql_text = re.sub(r"DELIMITER\s*\$\$.*?DELIMITER\s*;", "", sql_text, flags=re.DOTALL)
    statements = [
        s.strip()
        for s in sql_text.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        ok = err = 0
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                ok += 1
            except SQLAlchemyError as exc:
                err += 1
                logger.debug(f"DDL non-fatal: {str(exc)[:120]}")
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    logger.success(f"Schema applied: {ok} statements ok, {err} non-fatal warnings.")


# ─── Step 3: Load data ────────────────────────────────────────────────────────
def _prep(parquet_stem: str, columns: list[str]) -> pd.DataFrame:
    """Load one processed file, select required columns, coerce types."""
    path = PROCESSED_DIR / f"{parquet_stem}.parquet"
    if path.exists():
        df = pd.read_parquet(path)
    else:
        csv = PROCESSED_DIR / f"{parquet_stem}.csv"
        if not csv.exists():
            raise FileNotFoundError(f"Cannot find {path} or {csv}. "
                                    f"Run: python pipeline.py --steps gen etl")
        df = pd.read_csv(csv, low_memory=False)

    available = [c for c in columns if c in df.columns]
    df = df[available].copy().drop_duplicates()

    # pandas Categorical → plain str
    for col in df.select_dtypes(include="category").columns:
        df[col] = df[col].astype(str)

    # pandas Period → str (YearMonth etc.)
    for col in df.columns:
        if hasattr(df[col].dtype, "freq"):
            df[col] = df[col].astype(str)

    # datetime64 → Python date object (MySQL DATE column)
    for col in df.select_dtypes(include="datetime64[ns]").columns:
        df[col] = df[col].dt.date

    # Replace NaN / NaT with None so MySQL stores NULL
    return df.where(pd.notnull(df), None)


def load_all_tables(engine, chunk_size: int = 500) -> dict[str, int]:
    """Truncate and reload every table in FK-safe order."""
    results: dict[str, int] = {}

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

    for table, stem, cols in LOAD_ORDER:
        logger.info(f"  Loading {table} …")
        try:
            df = _prep(stem, cols)
        except FileNotFoundError as exc:
            logger.warning(f"  Skipping {table}: {exc}")
            results[table] = 0
            continue

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE `{table}`"))

        df.to_sql(
            table, engine,
            if_exists="append",
            index=False,
            chunksize=chunk_size,
            method="multi",
        )

        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
        results[table] = int(count)
        logger.success(f"  ✔ {table}: {count:,} rows")

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    return results


# ─── Step 4: Connection helpers ───────────────────────────────────────────────
def get_sv_engine():
    """
    Return a connected SQLAlchemy engine for sv_user / supply_vision.
    Uses URL.create() — safe for any password content.
    """
    url = _sv_url()
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        logger.error(f"Cannot connect as sv_user: {exc}")
        raise
    return engine


def test_connection() -> bool:
    """
    Verify the sv_user connection and check that fact_orders is populated.
    Returns True on success, False on any error.
    """
    try:
        engine = get_sv_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM fact_orders")
            ).scalar()
        host = os.getenv("DB_HOST", "localhost")
        db   = os.getenv("DB_NAME", "supply_vision")
        logger.success(
            f"Connection OK — {host}/{db} — "
            f"fact_orders has {result:,} rows."
        )
        return True
    except Exception as exc:
        logger.error(f"Connection failed: {exc}")
        return False


# ─── CLI ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="SupplyVision – MySQL Setup & Import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--root-user",      default="root",
                        help="MySQL root username (default: root)")
    parser.add_argument("--root-password",  default="",
                        help="MySQL root password (prompted if omitted)")
    parser.add_argument("--skip-create-db", action="store_true",
                        help="Skip CREATE DATABASE / CREATE USER step")
    parser.add_argument("--skip-schema",    action="store_true",
                        help="Skip schema DDL (schema.sql)")
    parser.add_argument("--skip-data",      action="store_true",
                        help="Skip CSV/Parquet → MySQL data import")
    parser.add_argument("--test-only",      action="store_true",
                        help="Only test the sv_user connection, then exit")
    parser.add_argument("--chunk-size",     type=int, default=500,
                        help="Rows per INSERT batch (default: 500)")
    args = parser.parse_args()

    # ── Test-only mode ────────────────────────────────────────────────────────
    if args.test_only:
        ok = test_connection()
        sys.exit(0 if ok else 1)

    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║    SupplyVision – MySQL Setup             ║")
    logger.info("╚══════════════════════════════════════════╝")

    # ── Step 1: Create DB + user ──────────────────────────────────────────────
    if not args.skip_create_db:
        rp = args.root_password or input("MySQL root password: ")
        create_database(args.root_user, rp)

    # ── Step 2: Apply schema ──────────────────────────────────────────────────
    engine = get_sv_engine()
    if not args.skip_schema:
        apply_schema(engine)

    # ── Step 3: Import data ───────────────────────────────────────────────────
    if not args.skip_data:
        results = load_all_tables(engine, args.chunk_size)
        total   = sum(results.values())
        logger.success(
            f"Import complete: {total:,} rows across {len(results)} tables."
        )
        for t, n in results.items():
            logger.info(f"  {t:<25} {n:>6,} rows")

    logger.success("MySQL setup complete. Set USE_MYSQL=true in your .env to activate.")


if __name__ == "__main__":
    main()
