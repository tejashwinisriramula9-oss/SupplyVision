"""
SupplyVision – Forecasting & Predictions Endpoints
"""

from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from src.api.dependencies import get_fact_orders
from src.forecasting.demand_forecast import run_forecasting

router = APIRouter()

# Cache last forecast result
_forecast_cache: dict = {}


@router.get("/demand", summary="Demand Forecast (Ensemble)")
async def get_demand_forecast(
    horizon_months: int = Query(6, ge=1, le=24, description="Number of months to forecast"),
    refresh: bool = Query(False, description="Force re-run forecast"),
):
    global _forecast_cache
    cache_key = f"demand_{horizon_months}"

    if not refresh and cache_key in _forecast_cache:
        return JSONResponse(content=_forecast_cache[cache_key])

    orders = get_fact_orders()
    if orders.empty:
        return JSONResponse(content={"error": "No order data available"}, status_code=503)

    results = run_forecasting(orders, horizon_months=horizon_months)

    ensemble = results["ensemble_forecast"].copy()
    ensemble["Month"] = ensemble["Month"].astype(str)

    historical = results["monthly_historical"].copy()
    historical["Month"] = historical["Month"].astype(str)

    response = {
        "historical": historical.to_dict(orient="records"),
        "forecast": ensemble.to_dict(orient="records"),
        "metrics": {
            "linear_regression": results["lr_metrics"],
            "time_series": results["ts_metrics"],
        },
        "horizon_months": horizon_months,
    }
    _forecast_cache[cache_key] = response
    return JSONResponse(content=response)


@router.get("/inventory-requirements", summary="Inventory Requirement Projections")
async def get_inventory_requirements(
    horizon_months: int = Query(6, ge=1, le=12),
    avg_lead_time_days: float = Query(14.0, ge=1.0, le=90.0),
    safety_stock_factor: float = Query(1.5, ge=1.0, le=3.0),
):
    from src.forecasting.demand_forecast import (
        build_monthly_demand, LinearDemandForecaster, project_inventory_requirements
    )

    orders = get_fact_orders()
    if orders.empty:
        return JSONResponse(content={"error": "No order data available"}, status_code=503)

    monthly = build_monthly_demand(orders)
    lr = LinearDemandForecaster(horizon_months=horizon_months)
    lr.fit(monthly)
    forecast = lr.predict()
    inv_req = project_inventory_requirements(forecast, avg_lead_time_days, safety_stock_factor)
    inv_req["Month"] = inv_req["Month"].astype(str)
    inv_req["Reorder_Date"] = inv_req["Reorder_Date"].astype(str)

    return JSONResponse(content=inv_req.to_dict(orient="records"))


@router.get("/models/accuracy", summary="Forecast Model Accuracy Metrics")
async def get_model_accuracy(
    horizon_months: int = Query(6, ge=1, le=24),
):
    orders = get_fact_orders()
    if orders.empty:
        return JSONResponse(content={"error": "No order data available"}, status_code=503)

    results = run_forecasting(orders, horizon_months=horizon_months)
    return JSONResponse(content={
        "linear_regression": results["lr_metrics"],
        "exponential_smoothing": results["ts_metrics"],
    })
