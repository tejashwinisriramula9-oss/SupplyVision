"""
SupplyVision – Inventory Intelligence Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_inventory, get_fact_orders
from src.analytics.kpi_engine import KPIEngine
from src.api.dependencies import get_logistics, get_suppliers, get_warehouses

router = APIRouter()


def _engine() -> KPIEngine:
    orders = get_fact_orders()
    return KPIEngine(orders, get_inventory(), get_suppliers(), get_logistics(), get_warehouses(), fact_orders=orders)


@router.get("/kpis", summary="Inventory KPI Cards")
async def get_inventory_kpis():
    return JSONResponse(content=_engine().inventory_kpis().to_dict())


@router.get("/by-category", summary="Inventory Breakdown by Category")
async def get_by_category():
    df = _engine().inventory_by_category()
    return JSONResponse(content=df.to_dict(orient="records"))


@router.get("/stock-status", summary="Stock Status Distribution")
async def get_stock_status():
    inv = get_inventory()
    if inv.empty:
        return JSONResponse(content=[])
    status_counts = inv["Stock_Status"].value_counts().reset_index()
    status_counts.columns = ["Stock_Status", "Count"]
    status_counts["Pct"] = (status_counts["Count"] / len(inv) * 100).round(2)
    return JSONResponse(content=status_counts.to_dict(orient="records"))


@router.get("/product-velocity", summary="Fast / Slow Moving Products")
async def get_product_velocity(n: int = Query(20, ge=5, le=100)):
    df = _engine().product_velocity(n=n)
    df = df[["Product_ID", "Product_Name", "Category", "Current_Stock",
             "Total_Sold", "Revenue", "Velocity_Score", "Movement_Class"]].copy()
    df["Revenue"] = df["Revenue"].round(2)
    df["Velocity_Score"] = df["Velocity_Score"].round(4)
    df["Movement_Class"] = df["Movement_Class"].astype(str)
    return JSONResponse(content=df.to_dict(orient="records"))


@router.get("/low-stock-alerts", summary="Products Below Safety Stock")
async def get_low_stock_alerts():
    inv = get_inventory()
    if inv.empty:
        return JSONResponse(content=[])
    alerts = inv[inv["Stock_Status"].isin(["Low Stock", "Out of Stock"])].copy()
    alerts = alerts[["Product_ID", "Product_Name", "Category",
                      "Current_Stock", "Safety_Stock", "Stock_Status",
                      "Warehouse_ID", "Inventory_Value"]]
    alerts["Stock_Gap"] = alerts["Safety_Stock"] - alerts["Current_Stock"]
    return JSONResponse(content=alerts.to_dict(orient="records"))


@router.get("/top-value", summary="Top Products by Inventory Value")
async def get_top_by_value(n: int = Query(15, ge=5, le=50)):
    inv = get_inventory()
    if inv.empty:
        return JSONResponse(content=[])
    top = (
        inv.nlargest(n, "Inventory_Value")[
            ["Product_ID", "Product_Name", "Category", "Current_Stock",
             "Unit_Cost", "Inventory_Value", "Stock_Status"]
        ]
    )
    return JSONResponse(content=top.to_dict(orient="records"))


@router.get("/warehouse-distribution", summary="Stock Distribution by Warehouse")
async def get_warehouse_distribution():
    inv = get_inventory()
    wh = get_warehouses()
    if inv.empty:
        return JSONResponse(content=[])
    grp = (
        inv.groupby("Warehouse_ID")
        .agg(Product_Count=("Product_ID", "count"),
             Total_Stock=("Current_Stock", "sum"),
             Total_Value=("Inventory_Value", "sum"))
        .reset_index()
    )
    if not wh.empty:
        grp = grp.merge(wh[["Warehouse_ID", "Warehouse_Name", "Location"]], on="Warehouse_ID", how="left")
    return JSONResponse(content=grp.to_dict(orient="records"))
