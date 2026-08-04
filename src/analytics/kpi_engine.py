"""
SupplyVision – KPI Engine
Calculates all enterprise KPIs from cleaned DataFrames.
Returns structured dictionaries suitable for API responses and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np
import pandas as pd


# ─── Data class for typed KPI results ────────────────────────────────────────
@dataclass
class ExecutiveKPIs:
    total_revenue: float = 0.0
    total_orders: int = 0
    total_inventory_value: float = 0.0
    on_time_delivery_pct: float = 0.0
    inventory_turnover_ratio: float = 0.0
    total_suppliers: int = 0
    avg_order_value: float = 0.0
    total_gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    cancelled_order_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InventoryKPIs:
    current_stock_total: int = 0
    safety_stock_total: int = 0
    inventory_value: float = 0.0
    stock_out_rate: float = 0.0
    overstock_rate: float = 0.0
    low_stock_count: int = 0
    fill_rate_pct: float = 0.0
    avg_margin_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LogisticsKPIs:
    avg_delivery_time: float = 0.0
    delayed_deliveries: int = 0
    on_time_delivery_pct: float = 0.0
    total_transport_cost: float = 0.0
    avg_delay_days: float = 0.0
    total_shipments: int = 0
    on_time_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SupplierKPIs:
    avg_reliability_score: float = 0.0
    avg_lead_time: float = 0.0
    total_supplier_cost: float = 0.0
    excellent_suppliers: int = 0
    poor_suppliers: int = 0
    total_suppliers: int = 0
    delivery_reliability_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── KPI Calculations ─────────────────────────────────────────────────────────
class KPIEngine:
    """
    Accepts cleaned DataFrames and exposes calculate_* methods
    for each dashboard domain.
    """

    def __init__(
        self,
        orders: pd.DataFrame,
        inventory: pd.DataFrame,
        suppliers: pd.DataFrame,
        logistics: pd.DataFrame,
        warehouses: pd.DataFrame,
        fact_orders: pd.DataFrame | None = None,
    ):
        self.orders = orders
        self.inventory = inventory
        self.suppliers = suppliers
        self.logistics = logistics
        self.warehouses = warehouses
        self.fact_orders = fact_orders if fact_orders is not None else orders

    # ── Executive KPIs ────────────────────────────────────────────────────────
    def executive_kpis(self) -> ExecutiveKPIs:
        o = self.fact_orders
        active = o[o["Order_Status"] != "Cancelled"]

        total_revenue = float(active["Revenue"].sum())
        total_orders = int(len(active))
        total_inventory_value = float(self.inventory["Inventory_Value"].sum())

        # On-Time Delivery %
        if len(self.logistics) > 0:
            otd = self.logistics["Is_Delayed"].eq(0).sum() / len(self.logistics) * 100
        else:
            otd = 0.0

        # Inventory Turnover = COGS / Avg Inventory Value
        cogs = float(active["COGS"].sum()) if "COGS" in active.columns else total_revenue * 0.65
        avg_inv = max(total_inventory_value, 1)
        inv_turnover = round(cogs / avg_inv, 2)

        avg_order_value = round(total_revenue / max(total_orders, 1), 2)
        gross_profit = float(active["Gross_Profit"].sum()) if "Gross_Profit" in active.columns else 0.0
        gross_margin = round(gross_profit / max(total_revenue, 1) * 100, 2)
        cancelled_pct = round(o[o["Order_Status"] == "Cancelled"].shape[0] / max(len(o), 1) * 100, 2)

        return ExecutiveKPIs(
            total_revenue=round(total_revenue, 2),
            total_orders=total_orders,
            total_inventory_value=round(total_inventory_value, 2),
            on_time_delivery_pct=round(otd, 2),
            inventory_turnover_ratio=inv_turnover,
            total_suppliers=len(self.suppliers),
            avg_order_value=avg_order_value,
            total_gross_profit=round(gross_profit, 2),
            gross_margin_pct=gross_margin,
            cancelled_order_pct=cancelled_pct,
        )

    # ── Inventory KPIs ────────────────────────────────────────────────────────
    def inventory_kpis(self) -> InventoryKPIs:
        inv = self.inventory
        total = len(inv)

        stock_out = inv[inv["Stock_Status"] == "Out of Stock"]
        overstock = inv[inv["Stock_Status"] == "Overstock"]
        low_stock = inv[inv["Stock_Status"] == "Low Stock"]

        fill_rate = (1 - len(stock_out) / max(total, 1)) * 100

        return InventoryKPIs(
            current_stock_total=int(inv["Current_Stock"].sum()),
            safety_stock_total=int(inv["Safety_Stock"].sum()),
            inventory_value=round(float(inv["Inventory_Value"].sum()), 2),
            stock_out_rate=round(len(stock_out) / max(total, 1) * 100, 2),
            overstock_rate=round(len(overstock) / max(total, 1) * 100, 2),
            low_stock_count=int(len(low_stock)),
            fill_rate_pct=round(fill_rate, 2),
            avg_margin_pct=round(float(inv["Margin_Pct"].mean()), 2),
        )

    # ── Logistics KPIs ────────────────────────────────────────────────────────
    def logistics_kpis(self) -> LogisticsKPIs:
        lg = self.logistics
        if len(lg) == 0:
            return LogisticsKPIs()

        delayed = lg[lg["Is_Delayed"] == 1]
        on_time = lg[lg["Is_Delayed"] == 0]

        return LogisticsKPIs(
            avg_delivery_time=round(float(lg["Transit_Time"].mean()), 2),
            delayed_deliveries=int(len(delayed)),
            on_time_delivery_pct=round(len(on_time) / len(lg) * 100, 2),
            total_transport_cost=round(float(lg["Transport_Cost"].sum()), 2),
            avg_delay_days=round(float(delayed["Delay_Days"].mean()) if len(delayed) > 0 else 0.0, 2),
            total_shipments=int(len(lg)),
            on_time_count=int(len(on_time)),
        )

    # ── Supplier KPIs ─────────────────────────────────────────────────────────
    def supplier_kpis(self) -> SupplierKPIs:
        sup = self.suppliers

        # Delivery reliability from logistics
        if len(self.logistics) > 0 and "Supplier_ID" in self.logistics.columns:
            sup_lg = self.logistics.groupby("Supplier_ID")["Is_Delayed"].mean().reset_index()
            sup_lg["Delivery_Reliability"] = 1 - sup_lg["Is_Delayed"]
            avg_del_rel = round(float(sup_lg["Delivery_Reliability"].mean()) * 100, 2)
        else:
            avg_del_rel = round(float(sup["Reliability_Score"].mean()) * 100, 2)

        excellent = sup[sup["Reliability_Tier"] == "Excellent"].shape[0]
        poor = sup[sup["Reliability_Tier"] == "Poor"].shape[0]

        return SupplierKPIs(
            avg_reliability_score=round(float(sup["Reliability_Score"].mean()), 4),
            avg_lead_time=round(float(sup["Lead_Time"].mean()), 2),
            total_supplier_cost=round(float(sup["Supplier_Cost"].sum()), 2),
            excellent_suppliers=int(excellent),
            poor_suppliers=int(poor),
            total_suppliers=int(len(sup)),
            delivery_reliability_pct=avg_del_rel,
        )

    # ── All KPIs as dict ─────────────────────────────────────────────────────
    def all_kpis(self) -> dict[str, Any]:
        return {
            "executive": self.executive_kpis().to_dict(),
            "inventory": self.inventory_kpis().to_dict(),
            "logistics": self.logistics_kpis().to_dict(),
            "suppliers": self.supplier_kpis().to_dict(),
        }

    # ── Revenue Trend ─────────────────────────────────────────────────────────
    def revenue_trend(self, freq: str = "M") -> pd.DataFrame:
        o = self.fact_orders[self.fact_orders["Order_Status"] != "Cancelled"].copy()
        o["Order_Date"] = pd.to_datetime(o["Order_Date"])
        trend = (
            o.resample(freq, on="Order_Date")
            .agg(
                Revenue=("Revenue", "sum"),
                Orders=("Order_ID", "count"),
                Avg_Order_Value=("Revenue", "mean"),
            )
            .reset_index()
        )
        trend["Revenue"] = trend["Revenue"].round(2)
        trend["Avg_Order_Value"] = trend["Avg_Order_Value"].round(2)
        return trend

    # ── Top N products by revenue ─────────────────────────────────────────────
    def top_products(self, n: int = 10) -> pd.DataFrame:
        o = self.fact_orders[self.fact_orders["Order_Status"] != "Cancelled"]
        grp = (
            o.groupby(["Product_ID", "Category"])
            .agg(
                Total_Revenue=("Revenue", "sum"),
                Total_Quantity=("Quantity", "sum"),
                Order_Count=("Order_ID", "count"),
            )
            .reset_index()
            .sort_values("Total_Revenue", ascending=False)
            .head(n)
        )
        grp["Total_Revenue"] = grp["Total_Revenue"].round(2)
        return grp

    # ── Carrier performance ───────────────────────────────────────────────────
    def carrier_performance(self) -> pd.DataFrame:
        lg = self.logistics
        return (
            lg.groupby("Carrier")
            .agg(
                Total_Shipments=("Shipment_ID", "count"),
                On_Time_Rate=("Is_Delayed", lambda x: (1 - x.mean()) * 100),
                Avg_Transit_Time=("Transit_Time", "mean"),
                Total_Cost=("Transport_Cost", "sum"),
                Avg_Delay_Days=("Delay_Days", "mean"),
            )
            .reset_index()
            .round(2)
            .sort_values("On_Time_Rate", ascending=False)
        )

    # ── Supplier comparison ───────────────────────────────────────────────────
    def supplier_comparison(self) -> pd.DataFrame:
        sup = self.suppliers.copy()
        if "Supplier_ID" in self.logistics.columns and len(self.logistics) > 0:
            lg_sup = (
                self.logistics.groupby("Supplier_ID")
                .agg(
                    Shipments=("Shipment_ID", "count"),
                    Delivery_Reliability_Pct=("Is_Delayed", lambda x: (1 - x.mean()) * 100),
                    Avg_Transit_Time=("Transit_Time", "mean"),
                )
                .reset_index()
            )
            sup = sup.merge(lg_sup, on="Supplier_ID", how="left")
        return sup.round(2)

    # ── Inventory by category ─────────────────────────────────────────────────
    def inventory_by_category(self) -> pd.DataFrame:
        return (
            self.inventory.groupby("Category")
            .agg(
                Product_Count=("Product_ID", "count"),
                Total_Stock=("Current_Stock", "sum"),
                Total_Value=("Inventory_Value", "sum"),
                Avg_Stock=("Current_Stock", "mean"),
                Stock_Out_Count=("Stock_Status", lambda x: (x == "Out of Stock").sum()),
            )
            .reset_index()
            .round(2)
            .sort_values("Total_Value", ascending=False)
        )

    # ── Slow/Fast movers ─────────────────────────────────────────────────────
    def product_velocity(self, n: int = 20) -> pd.DataFrame:
        o = self.fact_orders[self.fact_orders["Order_Status"] == "Delivered"]
        qty = (
            o.groupby("Product_ID")
            .agg(Total_Sold=("Quantity", "sum"), Revenue=("Revenue", "sum"))
            .reset_index()
        )
        inv = self.inventory[["Product_ID", "Product_Name", "Category", "Current_Stock"]]
        merged = inv.merge(qty, on="Product_ID", how="left").fillna(0)
        merged["Velocity_Score"] = merged["Total_Sold"] / (merged["Current_Stock"].replace(0, 1))
        merged["Movement_Class"] = pd.cut(
            merged["Velocity_Score"],
            bins=[-np.inf, 0.1, 1.0, 5.0, np.inf],
            labels=["Dead Stock", "Slow Moving", "Normal", "Fast Moving"],
        )
        return merged.sort_values("Velocity_Score", ascending=False)

    # ── All KPIs as dict ─────────────────────────────────────────────────────
    def all_kpis(self) -> dict[str, Any]:
        return {
            "executive": self.executive_kpis().to_dict(),
            "inventory": self.inventory_kpis().to_dict(),
            "logistics": self.logistics_kpis().to_dict(),
            "suppliers": self.supplier_kpis().to_dict(),
        }
