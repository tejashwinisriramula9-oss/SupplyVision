"""
SupplyVision – Supplier Analytics Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_suppliers, get_logistics, get_fact_orders, get_inventory, get_warehouses
from src.analytics.kpi_engine import KPIEngine

router = APIRouter()


def _engine() -> KPIEngine:
    orders = get_fact_orders()
    return KPIEngine(orders, get_inventory(), get_suppliers(), get_logistics(), get_warehouses(), fact_orders=orders)


@router.get("/kpis", summary="Supplier KPI Cards")
async def get_supplier_kpis():
    return JSONResponse(content=_engine().supplier_kpis().to_dict())


@router.get("/comparison", summary="Full Supplier Comparison Table")
async def get_supplier_comparison():
    df = _engine().supplier_comparison()
    string_cols = df.select_dtypes(include=["category"]).columns
    for col in string_cols:
        df[col] = df[col].astype(str)
    return JSONResponse(content=df.to_dict(orient="records"))


@router.get("/reliability-tiers", summary="Supplier Count by Reliability Tier")
async def get_reliability_tiers():
    sup = get_suppliers()
    if sup.empty:
        return JSONResponse(content=[])
    tiers = sup["Reliability_Tier"].astype(str).value_counts().reset_index()
    tiers.columns = ["Tier", "Count"]
    tiers["Pct"] = (tiers["Count"] / len(sup) * 100).round(2)
    return JSONResponse(content=tiers.to_dict(orient="records"))


@router.get("/lead-time-analysis", summary="Lead Time Distribution")
async def get_lead_time_analysis():
    sup = get_suppliers()
    if sup.empty:
        return JSONResponse(content=[])
    grp = (
        sup.groupby("Lead_Time_Category")
        .agg(Supplier_Count=("Supplier_ID", "count"), Avg_Lead_Time=("Lead_Time", "mean"))
        .reset_index()
        .round(2)
    )
    grp["Lead_Time_Category"] = grp["Lead_Time_Category"].astype(str)
    return JSONResponse(content=grp.to_dict(orient="records"))


@router.get("/cost-analysis", summary="Supplier Cost Analysis")
async def get_cost_analysis():
    sup = get_suppliers()
    if sup.empty:
        return JSONResponse(content=[])
    lg = get_logistics()
    if not lg.empty and "Supplier_ID" in lg.columns:
        cost_lg = (
            lg.groupby("Supplier_ID")["Transport_Cost"]
            .sum()
            .reset_index()
            .rename(columns={"Transport_Cost": "Total_Logistics_Cost"})
        )
        result = sup[["Supplier_ID", "Supplier_Name", "Supplier_Cost", "Region", "Lead_Time"]].merge(
            cost_lg, on="Supplier_ID", how="left"
        ).fillna(0)
        result["Total_Cost"] = result["Supplier_Cost"] + result["Total_Logistics_Cost"]
    else:
        result = sup[["Supplier_ID", "Supplier_Name", "Supplier_Cost", "Region", "Lead_Time"]].copy()
        result["Total_Cost"] = result["Supplier_Cost"]
    result = result.sort_values("Total_Cost", ascending=False).round(2)
    return JSONResponse(content=result.to_dict(orient="records"))


@router.get("/{supplier_id}", summary="Single Supplier Detail")
async def get_supplier_detail(supplier_id: str):
    sup = get_suppliers()
    if sup.empty:
        return JSONResponse(content={}, status_code=404)
    row = sup[sup["Supplier_ID"].str.upper() == supplier_id.upper()]
    if row.empty:
        return JSONResponse(content={"error": f"Supplier '{supplier_id}' not found"}, status_code=404)
    record = row.iloc[0].to_dict()
    for k, v in record.items():
        if hasattr(v, "item"):
            record[k] = v.item()
        elif str(type(v)) == "<class 'pandas._libs.lib.no_default'>":
            record[k] = None
    return JSONResponse(content=record)
