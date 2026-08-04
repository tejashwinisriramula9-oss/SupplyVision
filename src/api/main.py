"""
SupplyVision – FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.routers import executive, inventory, logistics, suppliers, forecasting
from src.api.dependencies import load_dataframes


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SupplyVision API starting – loading data …")
    load_dataframes()
    logger.success("Data loaded. API ready.")
    yield
    logger.info("SupplyVision API shutting down.")


app = FastAPI(
    title="SupplyVision API",
    description=(
        "Enterprise Supply Chain Analytics & Inventory Intelligence Platform. "
        "Provides KPIs, analytics, and forecasting endpoints for Power BI and web dashboards."
    ),
    version="1.0.0",
    contact={"name": "SupplyVision Team", "email": "analytics@supplyvision.io"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(executive.router,   prefix="/api/v1/executive",   tags=["Executive Overview"])
app.include_router(inventory.router,   prefix="/api/v1/inventory",   tags=["Inventory Intelligence"])
app.include_router(logistics.router,   prefix="/api/v1/logistics",   tags=["Logistics Analytics"])
app.include_router(suppliers.router,   prefix="/api/v1/suppliers",   tags=["Supplier Analytics"])
app.include_router(forecasting.router, prefix="/api/v1/forecasting", tags=["Forecasting & Predictions"])


@app.get("/", tags=["Health"])
async def root():
    from src.api.dependencies import _use_mysql
    source = "MySQL" if _use_mysql() else "Parquet"
    return {
        "application": "SupplyVision",
        "version": "1.0.0",
        "status": "operational",
        "data_source": source,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    from src.api.dependencies import _use_mysql
    from src.db.connection import mysql_available
    if _use_mysql():
        db_ok = mysql_available()
        return JSONResponse({
            "status": "healthy" if db_ok else "degraded",
            "data_source": "MySQL",
            "mysql_connected": db_ok,
        })
    return JSONResponse({"status": "healthy", "data_source": "Parquet"})
