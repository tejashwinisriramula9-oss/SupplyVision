"""
SupplyVision – MySQL Connection Manager
========================================
Provides a reusable SQLAlchemy engine and a helper that reads a full
MySQL table into a pandas DataFrame.

Password safety:
    The URL is constructed with SQLAlchemy's URL.create() API rather
    than f-string interpolation.  This means passwords containing
    @ ! # % $ & and any other special characters work correctly without
    requiring any manual escaping by the caller.

The engine is a module-level singleton (lru_cache) created once at API
startup and reused for every subsequent request — no per-request
connection overhead.
"""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL   # ← URL.create() for safe construction
from sqlalchemy.exc import OperationalError

load_dotenv()


def _build_url() -> URL:
    """
    Build a SQLAlchemy URL object using URL.create().

    URL.create() internally percent-encodes the password component, so
    characters like  @  !  #  %  $  &  never break the connection string.
    This is the SQLAlchemy-recommended approach and replaces every
    f"mysql+pymysql://{user}:{password}@..." pattern.
    """
    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER",     "sv_user"),
        password=os.getenv("DB_PASSWORD", "SV@SecurePass2024!"),
        host=os.getenv("DB_HOST",         "localhost"),
        port=int(os.getenv("DB_PORT",     "3306")),
        database=os.getenv("DB_NAME",     "supply_vision"),
        query={"charset": "utf8mb4"},
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Return the singleton SQLAlchemy engine.
    Cached after the first call — the same engine object is reused for
    every API request, keeping connection-pool overhead minimal.
    """
    url = _build_url()
    engine = create_engine(
        url,
        pool_pre_ping=True,   # silently reconnect if a stale connection is detected
        pool_recycle=3600,    # replace connections older than 1 hour (avoids MySQL 8h timeout)
        pool_size=5,          # maintain 5 persistent connections
        max_overflow=10,      # allow up to 10 extra burst connections
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        host = os.getenv("DB_HOST", "localhost")
        db   = os.getenv("DB_NAME", "supply_vision")
        logger.success(f"MySQL engine ready: {host}/{db}")
    except OperationalError as exc:
        logger.error(f"MySQL connection failed: {exc}")
        raise
    return engine


def read_table(table: str, where: str | None = None) -> pd.DataFrame:
    """
    Read an entire MySQL table (or a filtered subset) into a DataFrame.

    Args:
        table:  Table name, e.g. 'fact_orders'
        where:  Optional SQL WHERE clause without the WHERE keyword,
                e.g. "Order_Status != 'Cancelled'"

    Returns:
        pandas DataFrame with all columns from the table.

    Example:
        df = read_table("fact_orders", "Year = 2024")
    """
    sql = f"SELECT * FROM `{table}`"
    if where:
        sql += f" WHERE {where}"
    engine = get_engine()
    df = pd.read_sql(sql, engine)
    return df


def mysql_available() -> bool:
    """
    Returns True if the MySQL database is reachable with the current
    .env credentials, False otherwise.  Never raises.
    """
    try:
        get_engine()
        return True
    except Exception:
        return False
