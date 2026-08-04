"""
SupplyVision – Executive Overview Endpoints
Serves KPI cards and trend data for the Executive Overview Dashboard.
"""

from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_fact_orders, get_inventory, get_logistics, get_suppliers, get_warehouses
from src.analytics.kpi_engine import KPIEngine

router = APIRouter()


def _engine(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
) -> KPIEngine:
    orders = get_fact_orders()
    inventory = get_inventory()
    suppliers = get_suppliers()
    logistics = get_logistics()
    warehouses = get_warehouses()

    if year and not orders.empty and "Year" in orders.columns:
        orders = orders[orders["Year"] == year]
    if quarter and not orders.empty and "Quarter" in orders.columns:
        orders = orders[orders["Quarter"] == quarter]

    return KPIEngine(orders, inventory, suppliers, logistics, warehouses, fact_orders=orders)


@router.get("/kpis", summary="Executive KPI Cards")
async def get_executive_kpis(
    year: Optional[int] = Query(None, description="Filter by year"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="Filter by quarter (1-4)"),
):
    """Returns all executive-level KPI values."""
    kpis = _engine(year, quarter).executive_kpis().to_dict()
    return JSONResponse(content=kpis)


@router.get("/revenue-trend", summary="Monthly Revenue & Order Trend")
async def get_revenue_trend(
    freq: str = Query("ME", description="Frequency: ME=monthly, QE=quarterly, YE=yearly"),
    year: Optional[int] = Query(None),
):
    engine = _engine(year)
    trend = engine.revenue_trend(freq=freq)
    trend["Order_Date"] = trend["Order_Date"].astype(str)
    return JSONResponse(content=trend.to_dict(orient="records"))


@router.get("/top-products", summary="Top Products by Revenue")
async def get_top_products(
    n: int = Query(10, ge=1, le=50),
    year: Optional[int] = Query(None),
):
    engine = _engine(year)
    df = engine.top_products(n=n)
    return JSONResponse(content=df.to_dict(orient="records"))


@router.get("/delivery-performance", summary="Delivery Performance Summary")
async def get_delivery_performance():
    logistics = get_logistics()
    if logistics.empty:
        return JSONResponse(content={"on_time_pct": 0, "delayed_pct": 0, "total": 0})
    total = len(logistics)
    on_time = int(logistics["Is_Delayed"].eq(0).sum())
    delayed = int(logistics["Is_Delayed"].eq(1).sum())
    return JSONResponse(content={
        "total_shipments": total,
        "on_time": on_time,
        "delayed": delayed,
        "on_time_pct": round(on_time / total * 100, 2),
        "delayed_pct": round(delayed / total * 100, 2),
    })


@router.get("/all-kpis", summary="All KPI Domains")
async def get_all_kpis(
    year: Optional[int] = Query(None),
    quarter: Optional[int] = Query(None, ge=1, le=4),
):
    """Returns KPIs for all 5 dashboard domains in one call."""
    kpis = _engine(year, quarter).all_kpis()
    return JSONResponse(content=kpis)
