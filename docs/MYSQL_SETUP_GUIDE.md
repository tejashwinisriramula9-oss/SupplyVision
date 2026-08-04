# SupplyVision – MySQL Setup & Migration Guide
## CSV → MySQL → FastAPI → Power BI

---

## Overview

The upgraded architecture is:

```
data/raw/*.csv
      ↓  python pipeline.py  (generate + clean + ETL)
data/processed/*_clean.parquet
      ↓  python setup_mysql.py  (one-time import)
MySQL supply_vision database
      ↓  FastAPI reads from MySQL (USE_MYSQL=true in .env)
      ↓
Power BI Dashboards (connect to MySQL instead of CSV)
```

---

## PART A — MySQL Installation

### Windows (if MySQL is not installed)

1. Download MySQL Community Server from: https://dev.mysql.com/downloads/mysql/
2. Run the installer, choose "Developer Default"
3. Set a root password — remember it for Step B
4. After install, open **MySQL Workbench** or **MySQL Command Line Client**

### Verify MySQL is running

```bash
mysql -u root -p
# enter your root password
# you should see: mysql>
```

---

## PART B — One-Time Database Setup

### Option 1 — Automated (recommended)

Run the setup script. It creates the database, applies schema, and imports all data:

```bash
# From the project root:
python setup_mysql.py --root-password YOUR_ROOT_PASSWORD
```

This does three things in sequence:
1. Creates `supply_vision` database and `sv_user` account
2. Applies `sql/schema.sql` (all tables, views, stored procedures)
3. Imports all processed CSV/Parquet data into MySQL

Expected output:
```
✔  dim_warehouses:          10 rows
✔  dim_suppliers:           50 rows
✔  dim_customers:          800 rows
✔  dim_products:           200 rows
✔  fact_inventory:         200 rows
✔  fact_orders:          5,000 rows
✔  fact_logistics:       4,500 rows
Import complete: 10,760 rows across 7 tables.
MySQL setup complete. Update .env: USE_MYSQL=true
```

### Option 2 — Manual SQL (if you prefer MySQL Workbench)

```sql
-- Step 1: Run in MySQL Workbench as root
SOURCE C:/Users/CHARAN/OneDrive/Desktop/SupplyVision/sql/schema.sql;

-- Step 2: Import data via Python
-- python setup_mysql.py --skip-create-db --skip-schema
```

---

## PART C — Configure the API to Use MySQL

### 1. Create your `.env` file

```bash
copy .env.example .env
```

Edit `.env` and set:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=supply_vision
DB_USER=sv_user
DB_PASSWORD=SV@SecurePass2024!

USE_MYSQL=true
```

`USE_MYSQL=true` tells the FastAPI backend to read from MySQL on startup.
`USE_MYSQL=false` (default) reads from Parquet files — no MySQL needed.

### 2. Test the connection

```bash
python setup_mysql.py --test-only
```

Expected: `Connection OK — fact_orders has 5,000 rows.`

### 3. Start the API

```bash
python run_api.py
```

Check the startup logs:
```
Loading data from: MySQL
  [MySQL] fact_orders: 5,000 rows
  [MySQL] fact_inventory: 200 rows
  ...
Data ready. Source: MySQL
```

Open http://localhost:8000/ — the response now shows `"data_source": "MySQL"`.

---

## PART D — How the FastAPI Code Changed

### Files modified

| File | What changed |
|------|-------------|
| `src/api/dependencies.py` | **Rewrote** — now supports both MySQL and Parquet via `USE_MYSQL` env var |
| `src/api/main.py` | Health endpoint now reports data source |
| `src/db/connection.py` | **New** — SQLAlchemy engine singleton + `read_table()` helper |
| `src/db/__init__.py` | **New** — package init |
| `.env.example` | Added `USE_MYSQL` variable |
| `setup_mysql.py` | **New** — one-time import script |

### Files NOT changed

All 5 routers, the KPI Engine, forecasting, and reporting are **completely unchanged**.
They call `get_fact_orders()`, `get_inventory()`, etc. — those functions are the same,
they just now return data from MySQL instead of Parquet.

### How the data source switch works

```python
# .env
USE_MYSQL=true   → dependencies.py reads from MySQL at API startup
USE_MYSQL=false  → dependencies.py reads from data/processed/*.parquet
```

The data is loaded **once at startup** into an in-memory DataFrame cache.
All API requests read from that cache — no per-request database query.
This keeps response times fast regardless of whether the source is MySQL or Parquet.

---

## PART E — Reconnect Power BI to MySQL

### Current situation
Your Power BI report reads from CSV files in `data/processed/`.

### What you need to do
Connect the same 7 tables from MySQL. Because the **table names and column names are
identical** between MySQL and the CSV files, all visuals, relationships, and DAX
measures continue to work without any changes.

### Step-by-step Power BI reconnection

#### 1. Install the MySQL connector for Power BI

Download from: https://dev.mysql.com/downloads/connector/net/
- Choose "MySQL Connector/NET"
- Install with default settings
- **Restart Power BI Desktop** after installation

#### 2. Open your existing Power BI report

```
File → Open → SupplyVision.pbix
```

#### 3. Change each data source from CSV to MySQL

In Power BI Desktop:

1. **Home → Transform Data** (opens Power Query Editor)

2. For **each of the 7 queries** currently pointing to CSV files:
   - Click the query in the left panel
   - In the **Applied Steps** pane, click the first step: `Source`
   - The formula bar will show something like:
     ```
     = Csv.Document(File.Contents("C:\...\fact_orders_clean.csv"), ...)
     ```
   - Delete this step and replace with the MySQL M code below

#### 4. MySQL M code for each table

Paste these into the **Advanced Editor** for each query (Home → Advanced Editor):

**fact_orders**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM fact_orders"]),
    TypedDate = Table.TransformColumnTypes(Source,
                    {{"Order_Date", type date}})
in
    TypedDate
```

**fact_inventory**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM fact_inventory"])
in
    Source
```

**fact_logistics**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM fact_logistics"]),
    TypedDates = Table.TransformColumnTypes(Source, {
                     {"Ship_Date",     type date},
                     {"Delivery_Date", type date}})
in
    TypedDates
```

**dim_suppliers**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM dim_suppliers"])
in
    Source
```

**dim_customers**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM dim_customers"]),
    TypedDate = Table.TransformColumnTypes(Source,
                    {{"Registration_Date", type date}})
in
    TypedDate
```

**dim_warehouses**
```m
let
    Source = MySQL.Database("localhost", "supply_vision",
                [Query="SELECT * FROM dim_warehouses"])
in
    Source
```

**forecast_results** (stays as CSV — no MySQL table)
```m
-- No change needed for forecast_results.
-- It reads from data/exports/forecast_ensemble.csv as before.
```

#### 5. Enter MySQL credentials when prompted

Power BI will ask for credentials:
- **Authentication type:** Database
- **Username:** sv_user
- **Password:** SV@SecurePass2024!
- Click **Connect**

#### 6. Close & Apply

Click **Close & Apply** in Power Query Editor.
Power BI will reload all data from MySQL.

#### 7. Verify nothing broke

- All visuals should show the same data as before
- All DAX measures should return the same values as `verify_measures.py`
- All relationships should still be active (check Model View)

Run `python verify_measures.py` to get the reference numbers:
```bash
python verify_measures.py
```

Compare those numbers to your Power BI KPI cards. They should match exactly.

---

## PART F — Data Refresh Workflow (after setup)

### When you regenerate data

```bash
# Re-generate + clean + ETL (updates Parquet files)
python pipeline.py --steps gen clean etl

# Re-import into MySQL
python setup_mysql.py --skip-create-db --skip-schema

# In Power BI:
# Home → Refresh
```

### Or as one command

```bash
python pipeline.py --load-db
```

This runs gen → clean → etl → then calls `setup_mysql.py` to reload MySQL.

### Power BI automatic refresh

If you publish to Power BI Service (app.powerbi.com):
1. Go to Dataset Settings → Scheduled Refresh
2. Add your MySQL data source credentials
3. Set refresh frequency (daily, hourly, etc.)

---

## PART G — Fallback to Parquet (if MySQL is down)

If MySQL is unavailable (e.g., on a machine without MySQL installed):

```env
# .env
USE_MYSQL=false
```

The API will silently fall back to reading Parquet files.
No code changes, no restarts — just change the env var and restart.

```bash
python run_api.py
# Startup log will show: "Loading data from: Parquet"
```

This means the project works in two modes:
- **With MySQL:** full enterprise database stack
- **Without MySQL:** lightweight file-based mode (useful for demos, CI/CD)

---

## PART H — MySQL Tables Summary

| MySQL Table | Source CSV | Rows | Primary Key |
|------------|-----------|------|-------------|
| `dim_warehouses` | warehouses_clean | 10 | Warehouse_ID |
| `dim_suppliers` | suppliers_clean | 50 | Supplier_ID |
| `dim_customers` | customers_clean | 800 | Customer_ID |
| `dim_products` | inventory_clean | 200 | Product_ID |
| `fact_inventory` | inventory_clean | 200 | Product_ID |
| `fact_orders` | fact_orders_clean | 5,000 | Order_ID |
| `fact_logistics` | logistics_clean | 4,500 | Shipment_ID |
| **Total** | | **10,760** | |

---

## PART I — Troubleshooting

### "Can't connect to MySQL server"
```bash
# Check MySQL is running:
mysql -u root -p -e "SELECT 1"

# If not running (Windows):
net start MySQL80
```

### "Access denied for user sv_user"
```bash
# Reset password as root:
mysql -u root -p
ALTER USER 'sv_user'@'localhost' IDENTIFIED BY 'SV@SecurePass2024!';
FLUSH PRIVILEGES;
```

### "Table doesn't exist"
```bash
# Re-apply schema:
python setup_mysql.py --skip-create-db --skip-data
```

### "Power BI: MySQL connector not found"
- Download MySQL Connector/NET from mysql.com/downloads
- Restart Power BI Desktop after install

### API shows old Parquet data after MySQL import
- Check `.env` has `USE_MYSQL=true`
- Restart the API server: `python run_api.py`

### Power BI shows blank visuals after switching to MySQL
- Open Power Query Editor → check each query for errors (red !)
- Re-enter MySQL credentials: Home → Data source settings
- Check column names match (they should — MySQL table names = CSV column names)

---

## Quick Reference

```bash
# One-time setup
python setup_mysql.py --root-password YOUR_PASSWORD

# Test connection
python setup_mysql.py --test-only

# Re-import data (after regenerating CSVs)
python setup_mysql.py --skip-create-db --skip-schema

# Run everything including MySQL load
python pipeline.py --load-db

# Start API with MySQL
USE_MYSQL=true in .env, then: python run_api.py

# Start API without MySQL (fallback)
USE_MYSQL=false in .env, then: python run_api.py
```
