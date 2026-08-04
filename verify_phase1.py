"""Phase 1 verification script."""
import pandas as pd
from pathlib import Path

p = Path("data/processed")
files = [
    "warehouses_clean", "suppliers_clean", "customers_clean",
    "inventory_clean", "orders_clean", "logistics_clean", "fact_orders_clean",
]

print("Phase 1 – Processed file row counts:")
print("-" * 55)
for f in files:
    pq = p / f"{f}.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        print(f"  {f:<30} {len(df):>6,} rows  |  {len(df.columns)} cols")

print()
print("SQL outputs:")
print("-" * 55)
for f in ["schema.sql", "sample_data.sql", "01_create_database.sql",
          "02_create_tables.sql", "03_analytical_views.sql", "04_sample_queries.sql"]:
    fp = Path("sql") / f
    if fp.exists():
        sz = fp.stat().st_size
        print(f"  {f:<30} {sz/1024:>8.1f} KB")

print()
print("Raw CSV files (data/raw/):")
print("-" * 55)
raw = Path("data/raw")
for f in sorted(raw.glob("*.csv")):
    df = pd.read_csv(f)
    print(f"  {f.name:<30} {len(df):>6,} rows")

print()
print("Phase 1 requirements check:")
print("-" * 55)
specs = {
    "orders_clean.parquet":     ("Orders >= 1,000",      1000),
    "inventory_clean.parquet":  ("Products >= 200",        200),
    "suppliers_clean.parquet":  ("Suppliers >= 50",         50),
    "logistics_clean.parquet":  ("Shipments >= 500",       500),
    "warehouses_clean.parquet": ("Warehouses >= 10",        10),
    "customers_clean.parquet":  ("Customers >= 500",       500),
}
all_pass = True
for fn, (label, minimum) in specs.items():
    fp = p / fn
    if fp.exists():
        n = len(pd.read_parquet(fp))
        status = "PASS" if n >= minimum else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {status}  {label:<30}  actual={n:,}")
    else:
        print(f"  MISS  {label}")
        all_pass = False

print()
print("schema.sql generated:", (Path("sql") / "schema.sql").exists())
print("sample_data.sql generated:", (Path("sql") / "sample_data.sql").exists())
print("data_quality_report.json:", (Path("data/exports") / "data_quality_report.json").exists())
print()
print("All Phase 1 requirements met:", all_pass)
