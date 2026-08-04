"""
SupplyVision – ETL: Load to MySQL
Reads processed Parquet files and upserts data into MySQL tables.
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text

load_dotenv()

PROCESSED_DIR = Path("data/processed")

# ─── Connection ──────────────────────────────────────────────────────────────
def get_engine():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "supply_vision")
    user = os.getenv("DB_USER", "sv_user")
    password = os.getenv("DB_PASSWORD", "password")
    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


# ─── Schema creation ─────────────────────────────────────────────────────────
CREATE_STATEMENTS = {
    "dim_warehouses": """
        CREATE TABLE IF NOT EXISTS dim_warehouses (
            Warehouse_ID        VARCHAR(10)  PRIMARY KEY,
            Warehouse_Name      VARCHAR(100),
            Capacity            INT,
            Utilization         FLOAT,
            Available_Capacity  INT,
            Utilization_Pct     FLOAT,
            Utilization_Status  VARCHAR(20),
            Location            VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "dim_suppliers": """
        CREATE TABLE IF NOT EXISTS dim_suppliers (
            Supplier_ID         VARCHAR(10)  PRIMARY KEY,
            Supplier_Name       VARCHAR(150),
            Country             VARCHAR(100),
            Region              VARCHAR(50),
            Lead_Time           INT,
            Reliability_Score   FLOAT,
            Reliability_Tier    VARCHAR(20),
            Lead_Time_Category  VARCHAR(20),
            Supplier_Cost       DECIMAL(14,2),
            Contact_Email       VARCHAR(150),
            Phone               VARCHAR(50)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "dim_products": """
        CREATE TABLE IF NOT EXISTS dim_products (
            Product_ID      VARCHAR(10)  PRIMARY KEY,
            Product_Name    VARCHAR(150),
            Category        VARCHAR(50),
            Safety_Stock    INT,
            Reorder_Point   INT,
            Unit_Cost       DECIMAL(12,2),
            Unit_Price      DECIMAL(12,2),
            Margin_Pct      FLOAT,
            Warehouse_ID    VARCHAR(10),
            Supplier_ID     VARCHAR(10),
            FOREIGN KEY (Warehouse_ID) REFERENCES dim_warehouses(Warehouse_ID),
            FOREIGN KEY (Supplier_ID)  REFERENCES dim_suppliers(Supplier_ID)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "fact_inventory": """
        CREATE TABLE IF NOT EXISTS fact_inventory (
            Product_ID       VARCHAR(10)  PRIMARY KEY,
            Current_Stock    INT,
            Inventory_Value  DECIMAL(14,2),
            Stock_Status     VARCHAR(20),
            Last_Updated     DATE,
            FOREIGN KEY (Product_ID) REFERENCES dim_products(Product_ID)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "fact_orders": """
        CREATE TABLE IF NOT EXISTS fact_orders (
            Order_ID              VARCHAR(12)  PRIMARY KEY,
            Product_ID            VARCHAR(10),
            Customer_ID           VARCHAR(12),
            Order_Date            DATE,
            Year                  INT,
            Month                 INT,
            Quarter               INT,
            YearMonth             VARCHAR(10),
            YearQuarter           VARCHAR(12),
            WeekOfYear            INT,
            DayOfWeek             VARCHAR(12),
            Quantity              INT,
            Unit_Price            DECIMAL(12,2),
            Discount              FLOAT,
            Revenue               DECIMAL(14,2),
            COGS                  DECIMAL(14,2),
            Gross_Profit          DECIMAL(14,2),
            Gross_Margin_Pct      FLOAT,
            Order_Status          VARCHAR(20),
            Sales_Channel         VARCHAR(30),
            Category              VARCHAR(50),
            Warehouse_ID          VARCHAR(10),
            Supplier_ID           VARCHAR(10),
            Shipment_Count        INT,
            Avg_Transit_Time      FLOAT,
            Total_Transport_Cost  DECIMAL(14,2),
            Delayed_Shipments     INT,
            FOREIGN KEY (Product_ID)   REFERENCES dim_products(Product_ID),
            FOREIGN KEY (Warehouse_ID) REFERENCES dim_warehouses(Warehouse_ID),
            FOREIGN KEY (Supplier_ID)  REFERENCES dim_suppliers(Supplier_ID)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    "fact_logistics": """
        CREATE TABLE IF NOT EXISTS fact_logistics (
            Shipment_ID              VARCHAR(12)  PRIMARY KEY,
            Order_ID                 VARCHAR(12),
            Supplier_ID              VARCHAR(10),
            Ship_Date                DATE,
            Delivery_Date            DATE,
            Expected_Transit_Days    INT,
            Transit_Time             INT,
            Delay_Days               INT,
            Is_Delayed               TINYINT(1),
            Transport_Cost           DECIMAL(12,2),
            Cost_Per_KG              DECIMAL(10,2),
            Carrier                  VARCHAR(50),
            Delivery_Status          VARCHAR(20),
            Origin_Country           VARCHAR(100),
            Destination_Country      VARCHAR(100),
            Weight_KG                FLOAT,
            Ship_Year                INT,
            Ship_Month               INT,
            Ship_Quarter             INT,
            Ship_YearMonth           VARCHAR(10),
            FOREIGN KEY (Supplier_ID) REFERENCES dim_suppliers(Supplier_ID)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
}

# Load order matters due to FK constraints
LOAD_ORDER = [
    ("dim_warehouses", "warehouses_clean"),
    ("dim_suppliers",  "suppliers_clean"),
    ("dim_products",   "inventory_clean"),
    ("fact_inventory", "inventory_clean"),
    ("fact_orders",    "fact_orders_clean"),
    ("fact_logistics", "logistics_clean"),
]

# Column mappings where source df columns → table columns differ
COLUMN_MAPS = {
    "dim_products": ["Product_ID", "Product_Name", "Category", "Safety_Stock",
                     "Reorder_Point", "Unit_Cost", "Unit_Price", "Margin_Pct",
                     "Warehouse_ID", "Supplier_ID"],
    "fact_inventory": ["Product_ID", "Current_Stock", "Inventory_Value",
                       "Stock_Status", "Last_Updated"],
}


def create_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
        for table, ddl in CREATE_STATEMENTS.items():
            conn.execute(text(ddl))
            logger.info(f"  Schema ensured: {table}")
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))


def load_table(engine, table_name: str, parquet_name: str) -> None:
    path = PROCESSED_DIR / f"{parquet_name}.parquet"
    if not path.exists():
        logger.warning(f"  File not found, skipping: {path}")
        return

    df = pd.read_parquet(path)

    # Select only columns that belong to the target table
    if table_name in COLUMN_MAPS:
        cols = [c for c in COLUMN_MAPS[table_name] if c in df.columns]
        df = df[cols].drop_duplicates()

    # Convert Period/Timestamp types to str/date
    for col in df.select_dtypes(include=["period[M]", "period"]).columns:
        df[col] = df[col].astype(str)
    for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
        df[col] = df[col].dt.date

    df = df.where(pd.notnull(df), None)

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))

    df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=500)
    logger.success(f"  Loaded {table_name}: {len(df)} rows")


def run_load() -> None:
    logger.info("═══ SupplyVision MySQL Loader Starting ═══")
    engine = get_engine()
    create_schema(engine)

    for table_name, parquet_name in LOAD_ORDER:
        load_table(engine, table_name, parquet_name)

    logger.success("═══ MySQL Load Complete ═══")


if __name__ == "__main__":
    run_load()
