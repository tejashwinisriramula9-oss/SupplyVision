"""SupplyVision – Automated Audit Script"""
import os, sys, json, importlib
from pathlib import Path

ROOT = Path("C:/Users/CHARAN/OneDrive/Desktop/SupplyVision")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

results = {}

# ── 1. File existence check ──────────────────────────────────────────────────
REQUIRED_FILES = [
    "README.md", "requirements.txt", ".env.example", ".gitignore",
    "pipeline.py", "run_api.py", "setup_mysql.py",
    "src/api/main.py", "src/api/dependencies.py",
    "src/api/routers/executive.py", "src/api/routers/inventory.py",
    "src/api/routers/logistics.py", "src/api/routers/suppliers.py",
    "src/api/routers/forecasting.py",
    "src/analytics/kpi_engine.py",
    "src/forecasting/demand_forecast.py",
    "src/etl/clean_transform.py", "src/etl/data_cleaning.py",
    "src/etl/load_data.py", "src/etl/generate_sql.py",
    "src/data_generation/generate_datasets.py",
    "src/reports/report_generator.py",
    "src/db/connection.py", "src/db/__init__.py",
    "sql/schema.sql", "sql/sample_data.sql",
    "sql/02_create_tables.sql", "sql/03_analytical_views.sql",
    "sql/04_sample_queries.sql",
    "powerbi/dax_measures.md", "powerbi/DAX_FIXED.md",
    "powerbi/DASHBOARD_GUIDE.md", "powerbi/power_query_connections.md",
    "powerbi/SupplyVision_Theme.json", "powerbi/FORECAST_FIX.md",
    "docs/architecture.md", "docs/PROJECT_SUMMARY.md",
    "docs/MYSQL_SETUP_GUIDE.md", "DEPLOYMENT_CHECKLIST.md",
    "tests/test_kpi_engine.py", "tests/test_etl.py",
    "verify_measures.py", "verify_phase1.py",
    "notebooks/01_data_exploration.py", "notebooks/02_forecasting_analysis.py",
    ".github/workflows/ci.yml",
    "data/processed/fact_orders_clean.parquet",
    "data/processed/inventory_clean.parquet",
    "data/processed/suppliers_clean.parquet",
    "data/processed/logistics_clean.parquet",
    "data/processed/warehouses_clean.parquet",
    "data/processed/customers_clean.parquet",
    "data/exports/forecast_ensemble.csv",
    "data/exports/inventory_requirements.csv",
]

missing = [f for f in REQUIRED_FILES if not Path(f).exists()]
present = [f for f in REQUIRED_FILES if Path(f).exists()]
results["files_present"] = len(present)
results["files_missing"] = missing
print(f"\n=== FILE CHECK: {len(present)}/{len(REQUIRED_FILES)} present ===")
if missing:
    for f in missing:
        print(f"  MISSING: {f}")
else:
    print("  All required files present.")

# ── 2. Import checks ──────────────────────────────────────────────────────────
print("\n=== IMPORT CHECK ===")
import_errors = []
modules = [
    "src.api.main", "src.api.dependencies",
    "src.api.routers.executive", "src.api.routers.inventory",
    "src.api.routers.logistics", "src.api.routers.suppliers",
    "src.api.routers.forecasting",
    "src.analytics.kpi_engine",
    "src.forecasting.demand_forecast",
    "src.etl.clean_transform", "src.etl.data_cleaning",
    "src.etl.load_data",
    "src.db.connection",
]
for mod in modules:
    try:
        importlib.import_module(mod)
        print(f"  OK: {mod}")
    except Exception as e:
        import_errors.append((mod, str(e)))
        print(f"  FAIL: {mod} -> {e}")
results["import_errors"] = import_errors

# ── 3. Data file row counts ───────────────────────────────────────────────────
print("\n=== DATA ROW COUNTS ===")
import pandas as pd
data_counts = {}
files_to_count = {
    "fact_orders_clean": "data/processed/fact_orders_clean.parquet",
    "inventory_clean":   "data/processed/inventory_clean.parquet",
    "suppliers_clean":   "data/processed/suppliers_clean.parquet",
    "logistics_clean":   "data/processed/logistics_clean.parquet",
    "warehouses_clean":  "data/processed/warehouses_clean.parquet",
    "customers_clean":   "data/processed/customers_clean.parquet",
}
for name, path in files_to_count.items():
    try:
        df = pd.read_parquet(path)
        data_counts[name] = len(df)
        print(f"  {name}: {len(df):,} rows, {len(df.columns)} cols")
    except Exception as e:
        data_counts[name] = f"ERROR: {e}"
        print(f"  {name}: ERROR - {e}")
results["data_counts"] = data_counts

# ── 4. KPI engine verification ────────────────────────────────────────────────
print("\n=== KPI ENGINE CHECK ===")
try:
    from src.analytics.kpi_engine import KPIEngine
    fo  = pd.read_parquet("data/processed/fact_orders_clean.parquet")
    inv = pd.read_parquet("data/processed/inventory_clean.parquet")
    sup = pd.read_parquet("data/processed/suppliers_clean.parquet")
    lg  = pd.read_parquet("data/processed/logistics_clean.parquet")
    wh  = pd.read_parquet("data/processed/warehouses_clean.parquet")
    engine = KPIEngine(fo, inv, sup, lg, wh, fact_orders=fo)
    kpis = engine.all_kpis()
    exec_kpis = kpis["executive"]
    print(f"  Total Revenue:        ${exec_kpis['total_revenue']:,.2f}")
    print(f"  Total Orders:         {exec_kpis['total_orders']:,}")
    print(f"  Gross Margin %:       {exec_kpis['gross_margin_pct']:.2f}%")
    print(f"  On-Time Delivery %:   {kpis['logistics']['on_time_delivery_pct']:.2f}%")
    print(f"  Inv Turnover Ratio:   {exec_kpis['inventory_turnover_ratio']:.4f}x")
    print(f"  KPI domains returned: {list(kpis.keys())}")
    results["kpi_check"] = "PASS"
except Exception as e:
    results["kpi_check"] = f"FAIL: {e}"
    print(f"  KPI check FAILED: {e}")

# ── 5. Forecasting check ──────────────────────────────────────────────────────
print("\n=== FORECASTING CHECK ===")
try:
    fc = pd.read_csv("data/exports/forecast_ensemble.csv")
    ir = pd.read_csv("data/exports/inventory_requirements.csv")
    print(f"  forecast_ensemble.csv: {len(fc)} rows, cols: {list(fc.columns)}")
    print(f"  inventory_requirements.csv: {len(ir)} rows, cols: {list(ir.columns)}")
    results["forecast_check"] = "PASS"
except Exception as e:
    results["forecast_check"] = f"FAIL: {e}"
    print(f"  Forecasting FAILED: {e}")

# ── 6. API startup simulation ────────────────────────────────────────────────
print("\n=== API STARTUP SIMULATION (USE_MYSQL=false) ===")
try:
    os.environ["USE_MYSQL"] = "false"
    from src.api.dependencies import load_dataframes, get_fact_orders, get_inventory
    load_dataframes()
    fo_api = get_fact_orders()
    inv_api = get_inventory()
    print(f"  get_fact_orders(): {len(fo_api):,} rows")
    print(f"  get_inventory():   {len(inv_api):,} rows")
    results["api_startup"] = "PASS"
except Exception as e:
    results["api_startup"] = f"FAIL: {e}"
    print(f"  API startup FAILED: {e}")

# ── 7. URL safety check ───────────────────────────────────────────────────────
print("\n=== URL SAFETY CHECK ===")
unsafe = []
for fp in ["setup_mysql.py", "src/db/connection.py", "src/api/dependencies.py"]:
    content = Path(fp).read_text(encoding="utf-8")
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if "mysql+pymysql://" in s and (s.startswith('f"') or s.startswith("f'") or (" + " in s and "password" in s)):
            unsafe.append(f"{fp}:{i}: {s[:80]}")
if unsafe:
    for u in unsafe:
        print(f"  UNSAFE: {u}")
else:
    print("  All connection strings use URL.create() — safe for special chars.")
results["url_safety"] = "PASS" if not unsafe else f"FAIL: {unsafe}"

# ── 8. Requirements check ─────────────────────────────────────────────────────
print("\n=== REQUIREMENTS CHECK ===")
try:
    reqs = Path("requirements.txt").read_text()
    important = ["fastapi", "uvicorn", "pandas", "sqlalchemy", "pymysql",
                 "scikit-learn", "statsmodels", "loguru", "python-dotenv"]
    for pkg in important:
        found = pkg.lower() in reqs.lower()
        status = "OK" if found else "MISSING"
        print(f"  {status}: {pkg}")
    results["requirements_check"] = "PASS"
except Exception as e:
    results["requirements_check"] = f"FAIL: {e}"

# ── 9. .env.example check ────────────────────────────────────────────────────
print("\n=== .ENV.EXAMPLE CHECK ===")
try:
    env_content = Path(".env.example").read_text()
    env_keys = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
                "USE_MYSQL", "API_HOST", "API_PORT"]
    for key in env_keys:
        status = "OK" if key in env_content else "MISSING"
        print(f"  {status}: {key}")
    results["env_check"] = "PASS"
except Exception as e:
    results["env_check"] = f"FAIL: {e}"

# ── 10. GitHub readiness ─────────────────────────────────────────────────────
print("\n=== GITHUB READINESS ===")
git_checks = {
    ".gitignore":              Path(".gitignore").exists(),
    "README.md":               Path("README.md").exists(),
    ".github/workflows/ci.yml":Path(".github/workflows/ci.yml").exists(),
    ".env not committed":      not Path(".env").exists(),
    "LICENSE":                 Path("LICENSE").exists(),
}
for check, passed in git_checks.items():
    print(f"  {'OK' if passed else 'MISSING'}: {check}")
results["github_checks"] = git_checks

# ── 11. Power BI files ───────────────────────────────────────────────────────
print("\n=== POWER BI FILES ===")
pbix = Path("powerbi/SupplyVision.pbix")
theme = Path("powerbi/SupplyVision_Theme.json")
dax   = Path("powerbi/dax_measures.md")
guide = Path("powerbi/DASHBOARD_GUIDE.md")
print(f"  SupplyVision.pbix:       {'EXISTS' if pbix.exists() else 'MISSING (not built yet)'}")
print(f"  SupplyVision_Theme.json: {'EXISTS' if theme.exists() else 'MISSING'}")
print(f"  dax_measures.md:         {'EXISTS' if dax.exists() else 'MISSING'} ({dax.stat().st_size//1024}KB)" if dax.exists() else "  dax_measures.md:         MISSING")
print(f"  DASHBOARD_GUIDE.md:      {'EXISTS' if guide.exists() else 'MISSING'} ({guide.stat().st_size//1024}KB)" if guide.exists() else "  DASHBOARD_GUIDE.md:      MISSING")
results["pbix_exists"] = pbix.exists()

# ── 12. Warehouse references (should all be gone) ────────────────────────────
print("\n=== WAREHOUSE REFERENCE SCAN ===")
warehouse_terms = ["Warehouse Analytics", "warehouse_kpis", "/api/v1/warehouses"]
files_to_scan = [
    "src/api/main.py", "src/api/dependencies.py",
    "src/analytics/kpi_engine.py", "README.md",
    "docs/PROJECT_SUMMARY.md",
]
wh_hits = []
for fp in files_to_scan:
    content = Path(fp).read_text(encoding="utf-8", errors="ignore")
    for term in warehouse_terms:
        if term in content:
            wh_hits.append(f"{fp}: contains '{term}'")
if wh_hits:
    for h in wh_hits:
        print(f"  FOUND: {h}")
else:
    print("  Clean — no warehouse analytics references in core files.")
results["warehouse_clean"] = len(wh_hits) == 0

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("AUDIT SUMMARY")
print("="*60)
print(f"Files present:     {results['files_present']}/{len(REQUIRED_FILES)}")
print(f"Import errors:     {len(results['import_errors'])}")
print(f"KPI engine:        {results['kpi_check']}")
print(f"Forecasting:       {results['forecast_check']}")
print(f"API startup:       {results['api_startup']}")
print(f"URL safety:        {results['url_safety']}")
print(f"Warehouse clean:   {results['warehouse_clean']}")
print(f"PBIX file exists:  {results['pbix_exists']}")
