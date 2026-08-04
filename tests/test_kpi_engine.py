"""
SupplyVision – Unit Tests: KPI Engine
Run: pytest tests/ -v
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.kpi_engine import KPIEngine


# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_orders() -> pd.DataFrame:
    return pd.DataFrame({
        "Order_ID":     ["ORD001", "ORD002", "ORD003", "ORD004"],
        "Product_ID":   ["PRD001", "PRD001", "PRD002", "PRD003"],
        "Customer_ID":  ["CUST001", "CUST002", "CUST001", "CUST003"],
        "Order_Date":   pd.to_datetime(["2024-01-15", "2024-02-10", "2024-03-05", "2024-01-20"]),
        "Year":         [2024, 2024, 2024, 2024],
        "Month":        [1, 2, 3, 1],
        "Quarter":      [1, 1, 1, 1],
        "YearMonth":    ["2024-01", "2024-02", "2024-03", "2024-01"],
        "Quantity":     [10, 20, 5, 15],
        "Unit_Price":   [100.0, 150.0, 200.0, 75.0],
        "Discount":     [0.0, 0.05, 0.0, 0.1],
        "Revenue":      [1000.0, 2850.0, 1000.0, 1012.5],
        "COGS":         [600.0, 1500.0, 400.0, 600.0],
        "Gross_Profit": [400.0, 1350.0, 600.0, 412.5],
        "Order_Status": ["Delivered", "Delivered", "Cancelled", "Delivered"],
        "Sales_Channel": ["Online", "Direct Sales", "Online", "Partner"],
        "Category":     ["Electronics", "Electronics", "Packaging", "Raw Materials"],
        "Warehouse_ID": ["WH01", "WH01", "WH02", "WH01"],
        "Supplier_ID":  ["SUP001", "SUP002", "SUP001", "SUP002"],
        "Gross_Margin_Pct": [40.0, 47.4, 60.0, 40.7],
    })


@pytest.fixture
def sample_inventory() -> pd.DataFrame:
    return pd.DataFrame({
        "Product_ID":      ["PRD001", "PRD002", "PRD003"],
        "Product_Name":    ["Widget Alpha", "Widget Beta", "Widget Gamma"],
        "Category":        ["Electronics", "Packaging", "Raw Materials"],
        "Current_Stock":   [500, 0, 1500],
        "Safety_Stock":    [100, 50, 200],
        "Reorder_Point":   [150, 75, 300],
        "Unit_Cost":       [60.0, 80.0, 40.0],
        "Unit_Price":      [100.0, 200.0, 75.0],
        "Inventory_Value": [30000.0, 0.0, 60000.0],
        "Stock_Status":    ["Optimal", "Out of Stock", "Overstock"],
        "Margin_Pct":      [40.0, 60.0, 46.7],
        "Warehouse_ID":    ["WH01", "WH02", "WH01"],
        "Supplier_ID":     ["SUP001", "SUP001", "SUP002"],
    })


@pytest.fixture
def sample_suppliers() -> pd.DataFrame:
    return pd.DataFrame({
        "Supplier_ID":       ["SUP001", "SUP002"],
        "Supplier_Name":     ["Acme Corp", "Global Parts Inc"],
        "Country":           ["USA", "Germany"],
        "Region":            ["North America", "Europe"],
        "Lead_Time":         [7, 21],
        "Reliability_Score": [0.95, 0.70],
        "Reliability_Tier":  ["Excellent", "Acceptable"],
        "Lead_Time_Category": ["Express", "Extended"],
        "Supplier_Cost":     [50000.0, 120000.0],
    })


@pytest.fixture
def sample_logistics() -> pd.DataFrame:
    return pd.DataFrame({
        "Shipment_ID":           ["SHP001", "SHP002", "SHP003", "SHP004"],
        "Order_ID":              ["ORD001", "ORD002", "ORD001", "ORD004"],
        "Supplier_ID":           ["SUP001", "SUP002", "SUP001", "SUP002"],
        "Ship_Date":             pd.to_datetime(["2024-01-16", "2024-02-11", "2024-01-17", "2024-01-21"]),
        "Delivery_Date":         pd.to_datetime(["2024-01-20", "2024-02-20", "2024-01-22", "2024-01-28"]),
        "Expected_Transit_Days": [5, 7, 5, 5],
        "Transit_Time":          [4, 9, 5, 7],
        "Delay_Days":            [0, 2, 0, 2],
        "Is_Delayed":            [0, 1, 0, 1],
        "Transport_Cost":        [250.0, 800.0, 250.0, 400.0],
        "Cost_Per_KG":           [2.5, 4.0, 2.5, 3.2],
        "Carrier":               ["FedEx", "DHL", "FedEx", "UPS"],
        "Delivery_Status":       ["On Time", "Delayed", "On Time", "Delayed"],
        "Ship_Year":             [2024, 2024, 2024, 2024],
        "Ship_Month":            [1, 2, 1, 1],
        "Ship_Quarter":          [1, 1, 1, 1],
        "Ship_YearMonth":        ["2024-01", "2024-02", "2024-01", "2024-01"],
    })


@pytest.fixture
def sample_warehouses() -> pd.DataFrame:
    return pd.DataFrame({
        "Warehouse_ID":       ["WH01", "WH02"],
        "Warehouse_Name":     ["Chicago Hub", "Dallas Center"],
        "Capacity":           [20000, 15000],
        "Utilization":        [0.75, 0.45],
        "Available_Capacity": [5000, 8250],
        "Utilization_Pct":    [75.0, 45.0],
        "Utilization_Status": ["High", "Underutilized"],
        "Location":           ["Chicago, IL", "Dallas, TX"],
    })


@pytest.fixture
def engine(sample_orders, sample_inventory, sample_suppliers, sample_logistics, sample_warehouses):
    return KPIEngine(
        orders=sample_orders,
        inventory=sample_inventory,
        suppliers=sample_suppliers,
        logistics=sample_logistics,
        warehouses=sample_warehouses,
        fact_orders=sample_orders,
    )


# ─── Tests: Executive KPIs ────────────────────────────────────────────────────
class TestExecutiveKPIs:
    def test_total_orders_excludes_cancelled(self, engine):
        kpis = engine.executive_kpis()
        assert kpis.total_orders == 3  # ORD003 is cancelled

    def test_total_revenue_excludes_cancelled(self, engine):
        kpis = engine.executive_kpis()
        # ORD001=1000, ORD002=2850, ORD004=1012.5 = 4862.5
        assert abs(kpis.total_revenue - 4862.5) < 0.01

    def test_total_suppliers(self, engine):
        kpis = engine.executive_kpis()
        assert kpis.total_suppliers == 2

    def test_on_time_delivery_pct(self, engine):
        kpis = engine.executive_kpis()
        # 2 on-time out of 4 = 50%
        assert abs(kpis.on_time_delivery_pct - 50.0) < 0.01

    def test_inventory_turnover_ratio_positive(self, engine):
        kpis = engine.executive_kpis()
        assert kpis.inventory_turnover_ratio > 0

    def test_gross_margin_pct_range(self, engine):
        kpis = engine.executive_kpis()
        assert 0 <= kpis.gross_margin_pct <= 100


# ─── Tests: Inventory KPIs ────────────────────────────────────────────────────
class TestInventoryKPIs:
    def test_stock_out_rate(self, engine):
        kpis = engine.inventory_kpis()
        # 1 out-of-stock out of 3 products = 33.33%
        assert abs(kpis.stock_out_rate - 33.33) < 0.1

    def test_overstock_rate(self, engine):
        kpis = engine.inventory_kpis()
        # 1 overstock = 33.33%
        assert abs(kpis.overstock_rate - 33.33) < 0.1

    def test_inventory_value(self, engine):
        kpis = engine.inventory_kpis()
        assert abs(kpis.inventory_value - 90000.0) < 0.01

    def test_fill_rate(self, engine):
        kpis = engine.inventory_kpis()
        # 2 in-stock / 3 products = 66.67%
        assert abs(kpis.fill_rate_pct - 66.67) < 0.1


# ─── Tests: Logistics KPIs ────────────────────────────────────────────────────
class TestLogisticsKPIs:
    def test_delayed_count(self, engine):
        kpis = engine.logistics_kpis()
        assert kpis.delayed_deliveries == 2

    def test_on_time_count(self, engine):
        kpis = engine.logistics_kpis()
        assert kpis.on_time_count == 2

    def test_total_transport_cost(self, engine):
        kpis = engine.logistics_kpis()
        assert abs(kpis.total_transport_cost - 1700.0) < 0.01

    def test_total_shipments(self, engine):
        kpis = engine.logistics_kpis()
        assert kpis.total_shipments == 4


# ─── Tests: Supplier KPIs ─────────────────────────────────────────────────────
class TestSupplierKPIs:
    def test_avg_reliability_score(self, engine):
        kpis = engine.supplier_kpis()
        expected = (0.95 + 0.70) / 2
        assert abs(kpis.avg_reliability_score - expected) < 0.001

    def test_total_suppliers(self, engine):
        kpis = engine.supplier_kpis()
        assert kpis.total_suppliers == 2

    def test_excellent_suppliers(self, engine):
        kpis = engine.supplier_kpis()
        assert kpis.excellent_suppliers == 1


# ─── Tests: Aggregations ──────────────────────────────────────────────────────
class TestAggregations:
    def test_carrier_performance_columns(self, engine):
        df = engine.carrier_performance()
        assert "Carrier" in df.columns
        assert "On_Time_Rate" in df.columns
        assert "Total_Cost" in df.columns

    def test_inventory_by_category_completeness(self, engine):
        df = engine.inventory_by_category()
        assert len(df) == 3  # Electronics, Packaging, Raw Materials
        assert "Total_Value" in df.columns

    def test_top_products_limit(self, engine):
        df = engine.top_products(n=2)
        assert len(df) <= 2

    def test_all_kpis_domains(self, engine):
        kpis = engine.all_kpis()
        assert set(kpis.keys()) == {"executive", "inventory", "logistics", "suppliers"}

    def test_all_kpis_returns_correct_types(self, engine):
        kpis = engine.all_kpis()
        assert isinstance(kpis["executive"], dict)
        assert isinstance(kpis["inventory"], dict)
        assert isinstance(kpis["logistics"], dict)
        assert isinstance(kpis["suppliers"], dict)
