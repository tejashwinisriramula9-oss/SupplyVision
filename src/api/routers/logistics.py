"""
SupplyVision – Logistics Analytics Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_logistics, get_fact_orders, get_inventory, get_suppliers, get_warehouses
from src.analytics.kpi_engine import KPIEngine

router = APIRouter()


def _engine() -> KPIEngine:
    orders = get_fact_orders()
    return KPIEngine(orders, get_inventory(), get_suppliers(), get_logistics(), get_warehouses(), fact_orders=orders)


@router.get("/kpis", summary="Logistics KPI Cards")
async def get_logistics_kpis():
    return JSONResponse(content=_engine().logistics_kpis().to_dict())


@router.get("/carrier-performance", summary="Carrier Performance Comparison")
async def get_carrier_performance():
    df = _engine().carrier_performance()
    return JSONResponse(content=df.to_dict(orient="records"))


@router.get("/delivery-trend", summary="Monthly Delivery Trend")
async def get_delivery_trend():
    lg = get_logistics()
    if lg.empty:
        return JSONResponse(content=[])
    import pandas as pd
    lg["Ship_Date"] = pd.to_datetime(lg["Ship_Date"])
    trend = (
        lg.resample("ME", on="Ship_Date")
        .agg(
            Total_Shipments=("Shipment_ID", "count"),
            On_Time=("Is_Delayed", lambda x: (x == 0).sum()),
            Delayed=("Is_Delayed", "sum"),
            Avg_Transit=("Transit_Time", "mean"),
            Total_Cost=("Transport_Cost", "sum"),
        )
        .reset_index()
    )
    trend["On_Time_Pct"] = (trend["On_Time"] / trend["Total_Shipments"] * 100).round(2)
    trend["Ship_Date"] = trend["Ship_Date"].astype(str)
    return JSONResponse(content=trend.to_dict(orient="records"))


@router.get("/delay-analysis", summary="Delay Analysis by Carrier and Month")
async def get_delay_analysis():
    lg = get_logistics()
    if lg.empty:
        return JSONResponse(content=[])
    delayed = lg[lg["Is_Delayed"] == 1]
    carrier_delay = (
        delayed.groupby("Carrier")
        .agg(
            Delayed_Count=("Shipment_ID", "count"),
            Avg_Delay_Days=("Delay_Days", "mean"),
            Max_Delay_Days=("Delay_Days", "max"),
            Total_Extra_Cost=("Transport_Cost", "sum"),
        )
        .reset_index()
        .round(2)
        .sort_values("Delayed_Count", ascending=False)
    )
    return JSONResponse(content=carrier_delay.to_dict(orient="records"))


@router.get("/cost-by-carrier", summary="Transport Cost by Carrier")
async def get_cost_by_carrier():
    lg = get_logistics()
    if lg.empty:
        return JSONResponse(content=[])
    grp = (
        lg.groupby("Carrier")
        .agg(
            Total_Cost=("Transport_Cost", "sum"),
            Shipment_Count=("Shipment_ID", "count"),
            Avg_Cost=("Transport_Cost", "mean"),
            Avg_Cost_Per_KG=("Cost_Per_KG", "mean"),
        )
        .reset_index()
        .round(2)
        .sort_values("Total_Cost", ascending=False)
    )
    return JSONResponse(content=grp.to_dict(orient="records"))


@router.get("/shipments", summary="Shipment Records with Filters")
async def get_shipments(
    carrier: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
):
    lg = get_logistics()
    if lg.empty:
        return JSONResponse(content=[])
    if carrier:
        lg = lg[lg["Carrier"].str.lower() == carrier.lower()]
    if status:
        lg = lg[lg["Delivery_Status"].str.lower() == status.lower()]
    if year and "Ship_Year" in lg.columns:
        lg = lg[lg["Ship_Year"] == year]
    cols = ["Shipment_ID", "Order_ID", "Carrier", "Ship_Date", "Delivery_Date",
            "Transit_Time", "Is_Delayed", "Delay_Days", "Transport_Cost",
            "Delivery_Status", "Origin_Country", "Destination_Country"]
    cols = [c for c in cols if c in lg.columns]
    return JSONResponse(content=lg[cols].head(limit).to_dict(orient="records"))
