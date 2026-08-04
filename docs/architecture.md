# SupplyVision – Architecture & Technical Design

## System Overview

SupplyVision is a full-stack supply chain analytics platform organised into five layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                                │
│   Power BI Dashboards  │  FastAPI Swagger UI  │  Python Notebooks   │
└────────────────────────┬────────────────────────────────────────────┘
                         │  REST API (JSON)
┌────────────────────────▼────────────────────────────────────────────┐
│                    API LAYER  (FastAPI)                              │
│  /executive  /inventory  /logistics  /suppliers  /forecasting        │
└────────────────────────┬────────────────────────────────────────────┘
                         │  KPIEngine calls
┌────────────────────────▼────────────────────────────────────────────┐
│                  ANALYTICS LAYER                                     │
│         KPI Engine  │  Forecasting Module  │  Report Generator       │
└────────────────────────┬────────────────────────────────────────────┘
                         │  Reads parquet / MySQL
┌────────────────────────▼────────────────────────────────────────────┐
│                  DATA LAYER                                          │
│     MySQL (dim_* + fact_*)  │  Parquet  │  CSV  │  Excel             │
└────────────────────────┬────────────────────────────────────────────┘
                         │  ETL pipeline
┌────────────────────────▼────────────────────────────────────────────┐
│                  INGESTION LAYER                                     │
│          Raw CSV / Excel  (data/raw/)  ←  Data Generator             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Model (Star Schema)

```
                      dim_date
                          │
dim_warehouses ────── fact_orders ────── dim_products
                          │                    │
                     fact_logistics       dim_suppliers
                          │
                    fact_inventory
```

### Dimension Tables
| Table           | Description                           | PK          |
|-----------------|---------------------------------------|-------------|
| dim_suppliers   | Supplier reliability and cost data    | Supplier_ID |
| dim_products    | SKU master with pricing and margins   | Product_ID  |
| dim_date        | Date calendar (Power BI calculated)   | Date        |

### Fact Tables
| Table           | Grain                                 | PK          |
|-----------------|---------------------------------------|-------------|
| fact_orders     | One row per order                     | Order_ID    |
| fact_inventory  | One row per product (current snapshot)| Product_ID  |
| fact_logistics  | One row per shipment                  | Shipment_ID |

---

## ETL Pipeline

```
data/raw/                 data/processed/           MySQL
  orders.csv    ─────►    orders_clean.parquet  ──► fact_orders
  inventory.csv ─────►    inventory_clean.parquet ► dim_products
  suppliers.csv ─────►    suppliers_clean.parquet ► dim_suppliers
  logistics.csv ─────►    logistics_clean.parquet ► fact_logistics
  warehouses.csv ────►    warehouses_clean.parquet► dim_warehouses
                          fact_orders_clean.parquet (enriched join)
```

**Cleaning operations applied:**
- Date parsing and validation (drop unparseable rows)
- Negative/zero numeric value handling (clip to 0)
- Discount clamping [0, 1]
- Title-case normalisation on categorical fields
- Derived column computation (Inventory_Value, Delay_Days, Margin_Pct, etc.)
- Stock status classification using `numpy.select`
- Supplier reliability tier assignment via `pd.cut`

---

## Forecasting Models

| Model                   | Library       | Strengths                              |
|-------------------------|---------------|----------------------------------------|
| Linear Regression       | scikit-learn  | Interpretable, fast, good for trend    |
| Exponential Smoothing   | statsmodels   | Handles seasonality and trend          |
| Ensemble (average)      | custom        | Reduces individual model variance      |

**Features used in Linear Regression:**
- Time index (t)
- Lag-1 and Lag-2 demand
- 3-period rolling mean
- Month sine/cosine (seasonal encoding)

**Evaluation metrics:** MAE, RMSE, MAPE, R²

---

## API Endpoints

| Method | Path                                   | Description                      |
|--------|----------------------------------------|----------------------------------|
| GET    | /api/v1/executive/kpis                 | Executive KPI cards              |
| GET    | /api/v1/executive/revenue-trend        | Monthly revenue trend            |
| GET    | /api/v1/executive/top-products         | Top N products by revenue        |
| GET    | /api/v1/executive/all-kpis             | All domains in one call          |
| GET    | /api/v1/inventory/kpis                 | Inventory KPIs                   |
| GET    | /api/v1/inventory/by-category          | Inventory by category            |
| GET    | /api/v1/inventory/stock-status         | Stock status distribution        |
| GET    | /api/v1/inventory/product-velocity     | Fast/slow movers                 |
| GET    | /api/v1/inventory/low-stock-alerts     | Items below safety stock         |
| GET    | /api/v1/logistics/kpis                 | Logistics KPIs                   |
| GET    | /api/v1/logistics/carrier-performance  | Carrier scorecard                |
| GET    | /api/v1/logistics/delivery-trend       | Monthly delivery trend           |
| GET    | /api/v1/suppliers/kpis                 | Supplier KPIs                    |
| GET    | /api/v1/suppliers/comparison           | Full supplier comparison table   |
| GET    | /api/v1/suppliers/{supplier_id}        | Single supplier detail           |
| GET    | /api/v1/forecasting/demand             | 6-month demand forecast          |
| GET    | /api/v1/forecasting/inventory-requirements | Inventory projections        |

---

## Power BI Connection

1. **Get Data** → MySQL Database
2. Host: `localhost:3306`  Database: `supply_vision`
3. Import all `dim_*` and `fact_*` tables
4. In Model view, create relationships:
   - `fact_orders[Product_ID]` → `dim_products[Product_ID]` (many-to-one)
   - `fact_orders[Supplier_ID]` → `dim_suppliers[Supplier_ID]`
   - `fact_inventory[Product_ID]` → `dim_products[Product_ID]`
   - `fact_logistics[Supplier_ID]` → `dim_suppliers[Supplier_ID]`
   - `forecast_results[Date]` → `dim_date[Date]` (many-to-one)
5. Add a Date dimension via Power Query (M code in `powerbi/dax_measures.md`)
6. Create all DAX measures from `powerbi/DAX_FIXED.md`

---

## Security Considerations

- Database credentials are stored in `.env` (never committed to Git)
- API uses CORS – restrict `allow_origins` in production
- MySQL user `sv_user` has privileges only on `supply_vision` database
- Sensitive columns (email, phone) are excluded from API list responses
- Use HTTPS + API key authentication before deploying to production

---

## Scalability Notes

- Parquet format enables column-pruning and faster analytics vs CSV
- MySQL indexes on `Order_Date`, `Year`, `Carrier`, `Is_Delayed` support fast slicing
- FastAPI async handlers allow concurrent dashboard queries
- Batch size in `load_mysql.py` (500 rows) keeps memory usage bounded
- ETL pipeline can be scheduled with `schedule`, Airflow, or cron
