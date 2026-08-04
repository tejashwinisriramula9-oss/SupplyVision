# SupplyVision
### Enterprise Supply Chain Analytics & Inventory Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Power BI](https://img.shields.io/badge/Power%20BI-Dashboard-F2C811?logo=powerbi)](https://powerbi.microsoft.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **SupplyVision** transforms raw supply chain data into actionable business intelligence through
> a full end-to-end analytics platform — Python ETL, MySQL star schema, FastAPI backend,
> predictive demand forecasting, and five interactive Power BI dashboards.

---

## Project Overview

SupplyVision is an enterprise-grade supply chain analytics solution built to monitor, analyse,
and optimise supply chain operations. It processes inventory, supplier, logistics, and order
data to generate actionable insights through interactive Power BI dashboards and machine
learning–based demand forecasting.

**Data Coverage:** Jan 2022 – Dec 2024 (3 years) | **Forecast Horizon:** 6 months forward

---

## Features

| Dashboard | Key Capabilities |
|-----------|-----------------|
| 🏠 **Executive Overview** | Total Revenue, Orders, Inventory Value, On-Time Delivery %, Turnover Ratio, Gross Margin |
| 📦 **Inventory Intelligence** | Stock status, Fill Rate, Overstock/low-stock alerts, Product velocity analysis |
| 🚚 **Logistics Analytics** | Carrier performance, Delay analysis, Transit time trends, Transport cost tracking |
| 🤝 **Supplier Analytics** | Reliability tiers, Lead time analysis, Cost vs reliability scatter, Supplier scorecard |
| 🔮 **Forecasting & Predictions** | 6-month demand forecast, Ensemble model (LR + Exp. Smoothing), Inventory requirements |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Generation | Python 3.11, Faker, NumPy | Synthetic enterprise datasets |
| ETL & Cleaning | Pandas, NumPy | Data transformation, validation |
| Database | MySQL 8.0 (Star Schema) | Persistent storage |
| ORM / Connector | SQLAlchemy, PyMySQL | DB operations |
| Backend API | FastAPI, Uvicorn | REST endpoints for Power BI |
| Forecasting | scikit-learn, statsmodels | Linear Regression + Holt-Winters |
| Dashboards | Power BI Desktop | 5 interactive dashboards |
| DAX / Power Query | DAX Measures, M Language | KPI calculations, ETL in Power BI |
| Reporting | Jinja2, JSON | Automated monthly/quarterly reports |
| Testing | pytest | 42 unit tests |
| Version Control | Git, GitHub | Source control + CI/CD |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              PRESENTATION LAYER                          │
│  Power BI Dashboards  │  Swagger UI  │  Notebooks        │
└────────────────────────┬─────────────────────────────────┘
                         │ REST API (JSON)
┌────────────────────────▼─────────────────────────────────┐
│              API LAYER  (FastAPI + Uvicorn)               │
│  /executive  /inventory  /logistics  /suppliers           │
│  /forecasting                                            │
└────────────────────────┬─────────────────────────────────┘
                         │ KPIEngine + Forecasting
┌────────────────────────▼─────────────────────────────────┐
│              ANALYTICS LAYER                             │
│  KPI Engine  │  Forecasting Module  │  Report Generator  │
└────────────────────────┬─────────────────────────────────┘
                         │ USE_MYSQL=true → MySQL
                         │ USE_MYSQL=false → Parquet
┌────────────────────────▼─────────────────────────────────┐
│              DATA LAYER                                  │
│  MySQL (dim_* + fact_*)  │  Parquet  │  CSV  │  Excel    │
└────────────────────────┬─────────────────────────────────┘
                         │ ETL Pipeline
┌────────────────────────▼─────────────────────────────────┐
│              INGESTION LAYER                             │
│  Raw CSV / Excel  (data/raw/)  ←  Data Generator         │
└──────────────────────────────────────────────────────────┘
```

---

## Database — Star Schema

```
dim_customers
      │
dim_suppliers ──── fact_orders ──── dim_products
                        │                │
                  fact_logistics    fact_inventory
                        │
                   dim_date
```

| Table | Type | Rows | Description |
|-------|------|------|-------------|
| `fact_orders` | Fact | 5,000 | Order transactions with revenue and margin |
| `fact_inventory` | Fact | 200 | Current inventory snapshot per product |
| `fact_logistics` | Fact | 4,500 | Shipments with carrier and delay data |
| `dim_suppliers` | Dimension | 50 | Supplier reliability, lead times, costs |
| `dim_products` | Dimension | 200 | Product SKUs with pricing and categories |
| `dim_customers` | Dimension | 800 | Customer segments and demographics |
| `dim_date` | Dimension | 1,096 | Calendar table for time intelligence |

---

## Power BI Dashboards

### 1. 🏠 Executive Overview
KPI cards for Total Revenue, Total Orders, Gross Margin %, On-Time Delivery %, Inventory Turnover Ratio. Revenue trend line, order status donut, revenue by category bar, delivery trend column chart. Slicers: Year, Quarter.

### 2. 📦 Inventory Intelligence
Current Stock, Safety Stock, Fill Rate %, Stock-Out Rate %, Overstock Rate %, Low Stock Alert Count. Stock status donut, inventory value by category bar, low-stock alert table, product velocity scatter. Slicers: Category, Stock Status. Drill-through to Product Detail page.

### 3. 🚚 Logistics Analytics
On-Time Delivery %, Delayed Deliveries, Avg Transit Time, Avg Delay Days, Total Transport Cost, Delivery Performance Status (text KPI). Carrier performance bar, monthly delivery trend combo chart, delay analysis table, transport cost treemap. Slicers: Year, Carrier.

### 4. 🤝 Supplier Analytics
Supplier Reliability %, Delivery Reliability %, Avg Lead Time, Total Supplier Cost, Excellent/Poor Supplier counts. Reliability tier donut, supplier scorecard table (conditional formatting), lead time category bar, cost vs reliability scatter. Slicers: Region, Reliability Tier.

### 5. 🔮 Forecasting & Predictions
6-month ensemble demand forecast (Jan–Jun 2025). Historical + forecast combo line chart (solid historical / dashed forecast), inventory requirements action table, model accuracy comparison. Bookmarks: All Time / 2024+Forecast / Forecast Only.

---

## DAX KPIs Implemented

| KPI | Formula Approach |
|-----|-----------------|
| Total Revenue | SUM of Revenue excluding Cancelled orders |
| Gross Margin % | Gross Profit ÷ Revenue × 100 |
| Inventory Turnover Ratio | COGS ÷ Total Inventory Value |
| Days Inventory Outstanding | 365 ÷ Inventory Turnover Ratio |
| Fill Rate % | In-stock SKUs ÷ Total SKUs × 100 |
| Stock-Out Rate % | Out-of-stock SKUs ÷ Total SKUs × 100 |
| On-Time Delivery % | Non-delayed shipments ÷ Total shipments × 100 |
| Supplier Reliability % | Avg Reliability Score × 100 |
| Delivery Reliability % | On-time shipments from logistics data × 100 |
| Demand Forecast Accuracy % | 100 − MAPE |
| Average Lead Time | Avg supplier lead time in days |

---

## API Endpoints

```
GET  /                                        Project info + health
GET  /health                                  {"status": "healthy"}

GET  /api/v1/executive/kpis                   Executive KPI cards
GET  /api/v1/executive/revenue-trend          Monthly/quarterly revenue trend
GET  /api/v1/executive/top-products           Top N products by revenue
GET  /api/v1/executive/delivery-performance   On-time vs delayed summary
GET  /api/v1/executive/all-kpis               All 4 KPI domains in one call

GET  /api/v1/inventory/kpis                   Inventory KPI cards
GET  /api/v1/inventory/by-category            Inventory grouped by category
GET  /api/v1/inventory/stock-status           Stock status distribution
GET  /api/v1/inventory/product-velocity       Fast/slow mover analysis
GET  /api/v1/inventory/low-stock-alerts       Products below safety stock
GET  /api/v1/inventory/top-value              Top N by inventory value
GET  /api/v1/inventory/warehouse-distribution Stock per warehouse location

GET  /api/v1/logistics/kpis                   Logistics KPI cards
GET  /api/v1/logistics/carrier-performance    Per-carrier on-time %, cost, transit
GET  /api/v1/logistics/delivery-trend         Monthly shipment/delay trend
GET  /api/v1/logistics/delay-analysis         Delay breakdown by carrier
GET  /api/v1/logistics/cost-by-carrier        Transport cost per carrier
GET  /api/v1/logistics/shipments              Filtered shipment records

GET  /api/v1/suppliers/kpis                   Supplier KPI cards
GET  /api/v1/suppliers/comparison             All suppliers with logistics stats
GET  /api/v1/suppliers/reliability-tiers      Count per reliability tier
GET  /api/v1/suppliers/lead-time-analysis     Lead time category distribution
GET  /api/v1/suppliers/cost-analysis          Supplier + logistics cost total
GET  /api/v1/suppliers/{supplier_id}          Single supplier detail

GET  /api/v1/forecasting/demand               6-month ensemble forecast
GET  /api/v1/forecasting/inventory-requirements  Reorder quantity projections
GET  /api/v1/forecasting/models/accuracy      MAE, RMSE for each model
```

Full interactive docs: `http://localhost:8000/docs`

---

## Forecasting Models

| Model | Library | MAE | Strengths |
|-------|---------|-----|-----------|
| Linear Regression | scikit-learn | ~0 (overfits small dataset) | Interpretable, fast |
| Exponential Smoothing | statsmodels | ~397 | Handles trend + seasonality |
| **Ensemble (avg)** | custom | — | Reduces individual model variance |

Features: time index, lag-1, lag-2, 3-period rolling mean, month sin/cos encoding.

---

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL 8.0+ *(optional — API works from Parquet files)*
- Power BI Desktop *(free from microsoft.com)*
- Git

### Setup

```bash
git clone https://github.com/your-username/supplyvision.git
cd supplyvision

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MySQL credentials (optional)
```

### Run the Data Pipeline

```bash
# Generate data → Clean → ETL → Forecast → Reports  (no MySQL needed)
python pipeline.py

# Also load into MySQL
python pipeline.py --load-db

# Specific steps only
python pipeline.py --steps gen etl forecast
```

### Start the API Server

```bash
python run_api.py
# → http://localhost:8000/docs
```

### Run Tests

```bash
pytest tests/ -v
# 42 tests, all passing
```

---

## Project Structure

```
SupplyVision/
├── data/
│   ├── raw/                    # Generated CSV + multi-sheet Excel
│   ├── processed/              # Cleaned Parquet + CSV (ETL output)
│   └── exports/                # Forecast outputs, quality report, charts
├── src/
│   ├── data_generation/        # Synthetic enterprise dataset generator
│   ├── etl/                    # clean_transform, data_cleaning, load_data
│   ├── analytics/              # KPIEngine — all business metrics
│   ├── forecasting/            # Linear Regression + Exp. Smoothing
│   ├── api/                    # FastAPI app + 5 domain routers
│   └── reports/                # Monthly / Quarterly / Executive reports
├── sql/
│   ├── schema.sql              # Master DDL + views + stored procs
│   ├── sample_data.sql         # 2.2 MB INSERT file (all tables)
│   ├── 02_create_tables.sql
│   ├── 03_analytical_views.sql
│   └── 04_sample_queries.sql
├── powerbi/
│   ├── SupplyVision_Theme.json # Brand colour theme
│   ├── dax_measures.md         # All corrected DAX measures
│   ├── DAX_FIXED.md            # Diagnostic + fix guide
│   ├── FORECAST_FIX.md         # Forecasting table fix
│   ├── DASHBOARD_GUIDE.md      # Beginner build guide
│   └── power_query_connections.md
├── notebooks/
│   ├── 01_data_exploration.py  # EDA + matplotlib charts
│   └── 02_forecasting_analysis.py
├── reports/                    # JSON reports (monthly/quarterly/executive)
├── tests/                      # 42 pytest unit tests
├── docs/
│   ├── architecture.md
│   └── PROJECT_SUMMARY.md      # Full AI handoff document
├── pipeline.py                 # Master pipeline runner
├── run_api.py                  # API server launcher
├── verify_measures.py          # Verifies expected KPI values
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## MySQL Setup

```bash
# One-time setup (creates DB, applies schema, imports all data):
python setup_mysql.py --root-password YOUR_MYSQL_ROOT_PASSWORD

# Test connection:
python setup_mysql.py --test-only

# Enable MySQL mode in the API:
# Edit .env → USE_MYSQL=true
```

See `docs/MYSQL_SETUP_GUIDE.md` for the complete step-by-step guide including
Power BI reconnection instructions.

```sql
-- Or manually in MySQL Workbench:
SOURCE sql/schema.sql;
-- Then run: python setup_mysql.py --skip-create-db --skip-schema
```

---

## Deployment

### Backend (FastAPI)

```bash
# Development
python run_api.py

# Production (Render / Railway / VPS)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Environment Variables

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=supply_vision
DB_USER=sv_user
DB_PASSWORD=your_password
API_HOST=0.0.0.0
API_PORT=8000
```

### Render Deployment

1. Push to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render dashboard

### Power BI Service Publishing

1. Open `SupplyVision.pbix` in Power BI Desktop
2. Home → Publish → select your workspace
3. In Power BI Service: set scheduled refresh if connected to live data source

---

## Screenshots

> *Dashboard screenshots to be added after Power BI build is complete.*

| Dashboard | Preview |
|-----------|---------|
| Executive Overview | `docs/screenshots/executive.png` |
| Inventory Intelligence | `docs/screenshots/inventory.png` |
| Logistics Analytics | `docs/screenshots/logistics.png` |
| Supplier Analytics | `docs/screenshots/suppliers.png` |
| Forecasting | `docs/screenshots/forecasting.png` |

---

## Future Enhancements

- [ ] JWT authentication for API endpoints
- [ ] Real-time data ingestion via webhooks
- [ ] Product-level forecasting (per-SKU demand)
- [ ] Automated PDF report generation (weasyprint templates)
- [ ] Power BI Row-Level Security (RLS) per user role
- [ ] Docker containerisation for one-command deployment
- [ ] Apache Airflow for scheduled ETL pipeline
- [ ] Azure Synapse / Snowflake integration for large-scale data

---

## Suitable For

- **Data Analyst Portfolio** — end-to-end Python data pipeline + SQL + Power BI
- **Business Intelligence Analyst** — Power BI + DAX + star schema design
- **Supply Chain Analytics** — domain-specific KPIs and ensemble forecasting
- **College / University Project** — enterprise-level architecture and implementation

---

## License

MIT License — see [LICENSE](LICENSE) for details.
