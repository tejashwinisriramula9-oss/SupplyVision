from pathlib import Path
terms = [
    'Warehouse Analytics', 'Warehouse Utilization', 'Warehouse Utilisation',
    'warehouse_kpis', 'dim_warehouses', 'vw_warehouse', 'Critical Warehouses',
    'Available Capacity', 'Total Capacity', 'Warehouse Dashboard',
]
files = [
    'docs/PROJECT_SUMMARY.md',
    'powerbi/dax_measures.md',
    'powerbi/DAX_FIXED.md',
    'powerbi/DASHBOARD_GUIDE.md',
    'powerbi/power_query_connections.md',
    'sql/04_sample_queries.sql',
    'verify_measures.py',
    'src/analytics/kpi_engine.py',
]
for fp in files:
    p = Path(fp)
    if not p.exists():
        print(f'MISSING  : {fp}')
        continue
    content = p.read_text(encoding='utf-8', errors='ignore')
    hits = [t for t in terms if t in content]
    status = 'NEEDS EDIT' if hits else 'CLEAN     '
    print(f'{status}: {fp}')
    for h in hits:
        print(f'           - {h}')
