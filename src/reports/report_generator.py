"""
SupplyVision – Report Generator
Produces Monthly, Quarterly, KPI, and Executive Summary reports.
Outputs: structured CSV exports + HTML/PDF reports.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

REPORT_DIR = Path("reports")
TEMPLATES_DIR = Path("src/reports/templates")
EXPORT_DIR = Path("data/exports")


# ─── Utility ──────────────────────────────────────────────────────────────────
def fmt_currency(value: float) -> str:
    return f"${value:,.2f}"


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def fmt_int(value: int) -> str:
    return f"{value:,}"


# ─── Report Data Builders ─────────────────────────────────────────────────────
class ReportBuilder:
    def __init__(
        self,
        orders: pd.DataFrame,
        inventory: pd.DataFrame,
        suppliers: pd.DataFrame,
        logistics: pd.DataFrame,
        warehouses: pd.DataFrame,
        fact_orders: pd.DataFrame | None = None,
    ):
        from src.analytics.kpi_engine import KPIEngine

        self.fact_orders = fact_orders if fact_orders is not None else orders
        self.engine = KPIEngine(
            orders, inventory, suppliers, logistics, warehouses,
            fact_orders=self.fact_orders,
        )
        self.orders = orders
        self.inventory = inventory
        self.suppliers = suppliers
        self.logistics = logistics
        self.warehouses = warehouses

    # ── Monthly Report ────────────────────────────────────────────────────────
    def monthly_report(self, year: int, month: int) -> dict[str, Any]:
        logger.info(f"Building monthly report: {year}-{month:02d}")
        fo = self.fact_orders
        if "Year" in fo.columns and "Month" in fo.columns:
            period_orders = fo[(fo["Year"] == year) & (fo["Month"] == month)]
        else:
            period_orders = fo

        revenue = float(period_orders[period_orders.get("Order_Status", pd.Series()) != "Cancelled"]["Revenue"].sum()) if len(period_orders) > 0 else 0.0
        total_orders = len(period_orders)

        lg_month = self.logistics
        if "Ship_Year" in lg_month.columns and "Ship_Month" in lg_month.columns:
            lg_month = lg_month[(lg_month["Ship_Year"] == year) & (lg_month["Ship_Month"] == month)]

        otd = (lg_month["Is_Delayed"].eq(0).mean() * 100) if len(lg_month) > 0 else 0.0

        report = {
            "report_type": "Monthly",
            "period": f"{year}-{month:02d}",
            "generated_at": datetime.now().isoformat(),
            "kpis": {
                "revenue": fmt_currency(revenue),
                "total_orders": fmt_int(total_orders),
                "on_time_delivery_pct": fmt_pct(otd),
                "inventory_value": fmt_currency(float(self.inventory["Inventory_Value"].sum()) if "Inventory_Value" in self.inventory.columns and len(self.inventory) > 0 else 0.0),
            },
            "top_products": self.engine.top_products(5).to_dict(orient="records"),
            "carrier_performance": self.engine.carrier_performance().head(5).to_dict(orient="records"),
            "inventory_alerts": len(self.inventory[self.inventory["Stock_Status"].isin(["Out of Stock", "Low Stock"])]),
        }
        return report

    # ── Quarterly Report ──────────────────────────────────────────────────────
    def quarterly_report(self, year: int, quarter: int) -> dict[str, Any]:
        logger.info(f"Building quarterly report: {year} Q{quarter}")
        fo = self.fact_orders
        if "Year" in fo.columns and "Quarter" in fo.columns:
            period = fo[(fo["Year"] == year) & (fo["Quarter"] == quarter)]
        else:
            period = fo

        active = period[period.get("Order_Status", pd.Series("")) != "Cancelled"] if len(period) > 0 else period

        gross_profit = float(active["Gross_Profit"].sum()) if "Gross_Profit" in active.columns and len(active) > 0 else 0.0
        revenue = float(active["Revenue"].sum()) if len(active) > 0 else 0.0
        margin = round(gross_profit / max(revenue, 1) * 100, 2)

        return {
            "report_type": "Quarterly",
            "period": f"{year} Q{quarter}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "revenue": fmt_currency(revenue),
                "gross_profit": fmt_currency(gross_profit),
                "gross_margin_pct": fmt_pct(margin),
                "total_orders": fmt_int(len(active)),
                "new_suppliers": fmt_int(len(self.suppliers)),
            },
            "inventory_kpis": self.engine.inventory_kpis().to_dict(),
            "logistics_kpis": self.engine.logistics_kpis().to_dict(),
            "supplier_kpis": self.engine.supplier_kpis().to_dict(),
            "top_products": self.engine.top_products(10).to_dict(orient="records"),
            "category_breakdown": self.engine.inventory_by_category().to_dict(orient="records"),
        }

    # ── KPI Report ────────────────────────────────────────────────────────────
    def kpi_report(self) -> dict[str, Any]:
        logger.info("Building KPI report")
        all_kpis = self.engine.all_kpis()
        return {
            "report_type": "KPI Summary",
            "generated_at": datetime.now().isoformat(),
            "executive_kpis": all_kpis["executive"],
            "inventory_kpis": all_kpis["inventory"],
            "logistics_kpis": all_kpis["logistics"],
            "supplier_kpis":  all_kpis["suppliers"],
        }

    # ── Executive Summary Report ──────────────────────────────────────────────
    def executive_summary(self, year: int | None = None) -> dict[str, Any]:
        logger.info(f"Building executive summary: year={year or 'all'}")
        fo = self.fact_orders
        if year and "Year" in fo.columns:
            fo = fo[fo["Year"] == year]

        kpis = self.engine.executive_kpis()
        inv_kpis = self.engine.inventory_kpis()
        log_kpis = self.engine.logistics_kpis()
        sup_kpis = self.engine.supplier_kpis()

        trend = self.engine.revenue_trend("QE")
        trend["Order_Date"] = trend["Order_Date"].astype(str)

        recommendations = self._generate_recommendations(kpis, inv_kpis, log_kpis, sup_kpis)

        return {
            "report_type": "Executive Summary",
            "period": str(year) if year else "All Time",
            "generated_at": datetime.now().isoformat(),
            "headline_kpis": {
                "Total Revenue": fmt_currency(kpis.total_revenue),
                "Total Orders": fmt_int(kpis.total_orders),
                "Inventory Value": fmt_currency(kpis.total_inventory_value),
                "On-Time Delivery": fmt_pct(kpis.on_time_delivery_pct),
                "Inventory Turnover": f"{kpis.inventory_turnover_ratio}x",
                "Gross Margin": fmt_pct(kpis.gross_margin_pct),
            },
            "operational_kpis": {
                "Fill Rate": fmt_pct(inv_kpis.fill_rate_pct),
                "Stock-Out Rate": fmt_pct(inv_kpis.stock_out_rate),
                "Avg Delivery Time": f"{log_kpis.avg_delivery_time:.1f} days",
                "Delayed Deliveries": fmt_int(log_kpis.delayed_deliveries),
                "Avg Supplier Lead Time": f"{sup_kpis.avg_lead_time:.1f} days",
                "Supplier Reliability": fmt_pct(sup_kpis.delivery_reliability_pct),
            },
            "revenue_trend": trend.to_dict(orient="records"),
            "top_products": self.engine.top_products(5).to_dict(orient="records"),
            "recommendations": recommendations,
        }

    # ── AI-style Business Recommendations ────────────────────────────────────
    def _generate_recommendations(self, kpis, inv_kpis, log_kpis, sup_kpis) -> list[str]:
        recs = []

        if inv_kpis.stock_out_rate > 10:
            recs.append(
                f"⚠️ Stock-out rate is {inv_kpis.stock_out_rate:.1f}%. "
                "Review reorder points for high-velocity SKUs and tighten safety stock policies."
            )
        if inv_kpis.overstock_rate > 20:
            recs.append(
                f"📦 Overstock rate is {inv_kpis.overstock_rate:.1f}%. "
                "Consider clearance promotions or supplier return agreements to free capital."
            )
        if log_kpis.on_time_delivery_pct < 85:
            recs.append(
                f"🚚 On-time delivery is {log_kpis.on_time_delivery_pct:.1f}% (below 85% target). "
                "Evaluate carrier contracts and consider adding backup carriers for high-risk routes."
            )
        if sup_kpis.poor_suppliers > 0:
            recs.append(
                f"🔴 {sup_kpis.poor_suppliers} supplier(s) rated Poor. "
                "Initiate supplier improvement plans or qualify alternative vendors."
            )
        if kpis.inventory_turnover_ratio < 3:
            recs.append(
                f"🔄 Inventory turnover is {kpis.inventory_turnover_ratio}x (low). "
                "Reduce safety stock buffers for slow-moving categories or negotiate JIT delivery."
            )
        if kpis.gross_margin_pct < 20:
            recs.append(
                f"💹 Gross margin is {kpis.gross_margin_pct:.1f}%. "
                "Review pricing strategy and negotiate better supplier unit costs."
            )
        if sup_kpis.avg_lead_time > 21:
            recs.append(
                f"⏱ Average supplier lead time is {sup_kpis.avg_lead_time:.0f} days. "
                "Explore regional suppliers or consignment stock to reduce lead-time risk."
            )
        if not recs:
            recs.append("✅ All key metrics are within acceptable thresholds. Continue monitoring.")

        return recs

    # ── Export All Reports ────────────────────────────────────────────────────
    def export_all(self, year: int = 2024) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        (REPORT_DIR / "monthly").mkdir(exist_ok=True)
        (REPORT_DIR / "quarterly").mkdir(exist_ok=True)
        (REPORT_DIR / "executive").mkdir(exist_ok=True)

        # Monthly reports
        for month in range(1, 13):
            data = self.monthly_report(year, month)
            _save_json(data, REPORT_DIR / "monthly" / f"monthly_{year}_{month:02d}.json")

        # Quarterly reports
        for quarter in range(1, 5):
            data = self.quarterly_report(year, quarter)
            _save_json(data, REPORT_DIR / "quarterly" / f"quarterly_{year}_Q{quarter}.json")

        # KPI + Executive
        _save_json(self.kpi_report(), REPORT_DIR / "executive" / f"kpi_report_{year}.json")
        _save_json(self.executive_summary(year), REPORT_DIR / "executive" / f"executive_summary_{year}.json")

        logger.success(f"All reports exported for {year}")


def _save_json(data: dict, path: Path) -> None:
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"  Saved: {path}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_reports() -> None:
    from pathlib import Path
    import pandas as pd

    processed = Path("data/processed")

    def load(name: str) -> pd.DataFrame:
        p = processed / f"{name}_clean.parquet"
        if p.exists():
            return pd.read_parquet(p)
        c = processed / f"{name}_clean.csv"
        if c.exists():
            return pd.read_csv(c)
        return pd.DataFrame()

    builder = ReportBuilder(
        orders=load("orders"),
        inventory=load("inventory"),
        suppliers=load("suppliers"),
        logistics=load("logistics"),
        warehouses=load("warehouses"),
        fact_orders=load("fact_orders"),
    )
    builder.export_all(year=2024)


if __name__ == "__main__":
    run_reports()
