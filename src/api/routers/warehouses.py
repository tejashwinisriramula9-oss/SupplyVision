"""
SupplyVision – Warehouse Analytics Endpoints
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.dependencies import get_warehouses, get_inventory
from src.analytics.kpi_engine import KPIEngine
from src.api.dependencies import get_fact_orders, get_suppliers, get_logistics

router = APIRouter()


def _engine() -> KPIEngine:
    orders = get_fact_orders()
    return KPIEngine(orders, get_inventory(), get_suppliers(), get_logistics(), get_warehouses(), fact_orders=orders)


@router.get("/kpis", summary="Warehouse Utilization KPIs")
async def get_warehouse_kpis():
    return JSONResponse(content=_engine().warehouse_kpis())


@router.get("/utilization", summary="Per-Warehouse Utilization Detail")
async def get_utilization():
    wh = get_warehouses()
    if wh.empty:
        return JSONResponse(content=[])
    cols = ["Warehouse_ID", "Warehouse_Name", "Location", "Capacity",
            "Utilization_Pct", "Available_Capacity", "Utilization_Status"]
    cols = [c for c in cols if c in wh.columns]
    result = wh[cols].copy()
    result["Utilization_Status"] = result["Utilization_Status"].astype(str)
    return JSONResponse(content=result.to_dict(orient="records"))


@router.get("/inventory-by-warehouse", summary="Inventory Summary per Warehouse")
async def get_inventory_by_warehouse():
    return JSONResponse(content=_engine().inventory_by_category().to_dict(orient="records"))
