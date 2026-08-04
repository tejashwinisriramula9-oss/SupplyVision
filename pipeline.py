"""
SupplyVision – Master Pipeline Runner
Orchestrates the full end-to-end data pipeline:
  1.  Generate synthetic enterprise datasets  (gen)
  2a. Clean & Transform – data_cleaning.py   (clean)
  2b. ETL – clean_transform.py               (etl)
  3.  Load to MySQL – load_data.py           (db)
  4.  Generate sample_data.sql               (sql)
  5.  Run forecasting models                 (forecast)
  6.  Generate business reports              (reports)

Usage:
    python pipeline.py                              # default: gen clean etl forecast reports
    python pipeline.py --steps gen clean etl        # specific steps
    python pipeline.py --load-db                    # include MySQL load
    python pipeline.py --steps gen clean etl sql    # also emit sample_data.sql
    python pipeline.py --year 2024                  # report year override
"""

import argparse
import sys
import time
from pathlib import Path

from loguru import logger

# ─── Logger setup ─────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/pipeline.log", level="DEBUG", rotation="10 MB", retention="30 days")

STEP_ALL = ["gen", "clean", "etl", "db", "sql", "forecast", "reports"]


def step_generate():
    logger.info("━━━ STEP 1: Data Generation ━━━")
    from src.data_generation.generate_datasets import generate_all
    generate_all()


def step_clean():
    logger.info("━━━ STEP 2a: Data Cleaning (data_cleaning.py) ━━━")
    from src.etl.data_cleaning import run_cleaning
    run_cleaning()


def step_etl():
    logger.info("━━━ STEP 2b: ETL – Clean & Transform ━━━")
    from src.etl.clean_transform import run_etl
    run_etl()


def step_load_db():
    logger.info("━━━ STEP 3: Load to MySQL (setup_mysql.py) ━━━")
    from setup_mysql import get_sv_engine, apply_schema, load_all_tables
    import argparse
    engine = get_sv_engine()
    apply_schema(engine)
    results = load_all_tables(engine)
    total = sum(results.values())
    logger.success(f"MySQL load complete: {total:,} rows across {len(results)} tables.")


def step_generate_sql():
    logger.info("━━━ STEP 4: Generate sample_data.sql ━━━")
    from src.etl.generate_sql import generate_sample_sql
    path = generate_sample_sql()
    logger.success(f"sample_data.sql written: {path}")


def step_forecast(year: int = 2024):
    logger.info("━━━ STEP 5: Demand Forecasting ━━━")
    import pandas as pd
    from pathlib import Path
    from src.forecasting.demand_forecast import run_forecasting

    processed = Path("data/processed")
    parquet = processed / "fact_orders_clean.parquet"
    csv = processed / "orders_clean.csv"

    if parquet.exists():
        orders = pd.read_parquet(parquet)
    elif csv.exists():
        orders = pd.read_csv(csv)
    else:
        logger.warning("No order data found – skipping forecast step.")
        return

    results = run_forecasting(orders, horizon_months=6)
    logger.success(f"Forecast complete. LR Metrics: {results['lr_metrics']}")


def step_reports(year: int = 2024):
    logger.info("━━━ STEP 6: Report Generation ━━━")
    from src.reports.report_generator import run_reports
    run_reports()


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="SupplyVision – End-to-End Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=STEP_ALL,
        default=["gen", "clean", "etl", "forecast", "reports"],
        help="Pipeline steps to execute (default: gen clean etl forecast reports)",
    )
    parser.add_argument("--load-db", action="store_true", help="Include MySQL load step")
    parser.add_argument("--gen-sql",  action="store_true", help="Generate sample_data.sql")
    parser.add_argument("--year", type=int, default=2024, help="Reporting year (default: 2024)")
    args = parser.parse_args()

    steps = list(args.steps)
    if args.load_db and "db"  not in steps:
        steps.append("db")
    if args.gen_sql and "sql" not in steps:
        steps.append("sql")

    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║     SupplyVision – Data Pipeline         ║")
    logger.info("╚══════════════════════════════════════════╝")
    logger.info(f"Steps: {steps}  |  Year: {args.year}")

    start = time.time()
    errors = []

    step_map = {
        "gen":      step_generate,
        "clean":    step_clean,
        "etl":      step_etl,
        "db":       step_load_db,
        "sql":      step_generate_sql,
        "forecast": lambda: step_forecast(args.year),
        "reports":  lambda: step_reports(args.year),
    }

    for step in steps:
        try:
            step_map[step]()
        except Exception as exc:
            logger.error(f"Step '{step}' failed: {exc}")
            errors.append((step, str(exc)))

    elapsed = time.time() - start
    logger.info("─" * 50)

    if errors:
        for step, msg in errors:
            logger.error(f"  ✗ {step}: {msg}")
        logger.warning(f"Pipeline finished with {len(errors)} error(s) in {elapsed:.1f}s")
        sys.exit(1)
    else:
        logger.success(f"✅ Pipeline complete in {elapsed:.1f}s – all {len(steps)} steps passed.")


if __name__ == "__main__":
    main()
