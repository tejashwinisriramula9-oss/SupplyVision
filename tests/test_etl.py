"""
SupplyVision – Unit Tests: ETL Clean & Transform
"""

import pandas as pd
import pytest

from src.etl.clean_transform import (
    clean_orders,
    clean_inventory,
    clean_suppliers,
    clean_logistics,
    clean_warehouses,
)


@pytest.fixture
def raw_orders() -> pd.DataFrame:
    return pd.DataFrame({
        "Order_ID":    ["ORD001", "ORD002", "ORD003"],
        "Product_ID":  ["PRD001", "PRD002", "PRD003"],
        "Customer_ID": ["CUST001", "CUST001", "CUST002"],
        "Order_Date":  ["2024-01-15", "invalid-date", "2024-03-10"],
        "Quantity":    [10, -5, 20],
        "Unit_Price":  [100.0, 50.0, 200.0],
        "Discount":    [0.0, None, 1.5],  # 1.5 should be clipped to 1.0
        "Revenue":     [1000.0, -250.0, 4000.0],
        "Order_Status": ["delivered", "shipped", "CANCELLED"],
        "Sales_Channel": [" Online ", "direct sales", "Partner"],
    })


@pytest.fixture
def raw_inventory() -> pd.DataFrame:
    return pd.DataFrame({
        "Product_ID":    ["PRD001", "PRD002"],
        "Product_Name":  ["Alpha Widget", "Beta Part"],
        "Category":      ["electronics", "PACKAGING"],
        "Current_Stock": [500, -10],  # Negative should be clipped to 0
        "Safety_Stock":  [100, 50],
        "Reorder_Point": [200, 100],
        "Unit_Cost":     [60.0, 80.0],
        "Unit_Price":    [100.0, 200.0],
        "Warehouse_ID":  ["WH01", "WH02"],
        "Supplier_ID":   ["SUP001", "SUP002"],
        "Last_Updated":  ["2024-01-01", "2024-02-15"],
    })


@pytest.fixture
def raw_suppliers() -> pd.DataFrame:
    return pd.DataFrame({
        "Supplier_ID":       ["SUP001", "SUP002", "SUP003"],
        "Supplier_Name":     ["Acme", "Global", "Express"],
        "Country":           ["USA", "Germany", "Japan"],
        "Region":            ["North America", "Europe", "Asia Pacific"],
        "Lead_Time":         [7, None, 35],  # None should be imputed
        "Reliability_Score": [0.95, 0.70, 1.5],  # 1.5 clipped to 0.99
        "Supplier_Cost":     [50000.0, 120000.0, 80000.0],
    })


@pytest.fixture
def raw_logistics() -> pd.DataFrame:
    return pd.DataFrame({
        "Shipment_ID":           ["SHP001", "SHP002"],
        "Order_ID":              ["ORD001", "ORD002"],
        "Supplier_ID":           ["SUP001", "SUP002"],
        "Ship_Date":             ["2024-01-16", "bad-date"],
        "Delivery_Date":         ["2024-01-20", "2024-02-20"],
        "Expected_Transit_Days": [5, 7],
        "Transit_Time":          [4, 9],
        "Transport_Cost":        [250.0, 800.0],
        "Carrier":               [" fedex ", "DHL"],
        "Delivery_Status":       ["On Time", "Delayed"],
        "Origin_Country":        ["USA", "Germany"],
        "Destination_Country":   ["Canada", "France"],
        "Weight_KG":             [100.0, 200.0],
    })


@pytest.fixture
def raw_warehouses() -> pd.DataFrame:
    return pd.DataFrame({
        "Warehouse_ID":   ["WH01", "WH02"],
        "Warehouse_Name": ["Chicago Hub", "Dallas Center"],
        "Capacity":       [20000, 15000],
        "Utilization":    [0.75, 0.45],
        "Location":       ["Chicago, IL", "Dallas, TX"],
    })


# ─── Orders cleaning ─────────────────────────────────────────────────────────
class TestCleanOrders:
    def test_drops_invalid_dates(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        assert len(cleaned) == 2  # ORD002 has invalid date

    def test_drops_negative_revenue(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        assert (cleaned["Revenue"] > 0).all()

    def test_discount_clipped(self, raw_orders):
        raw_orders.at[2, "Revenue"] = 4000  # ensure it passes revenue check
        cleaned = clean_orders(raw_orders)
        assert (cleaned["Discount"] <= 1.0).all()

    def test_derived_columns_exist(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        for col in ["Year", "Month", "Quarter", "YearMonth", "DayOfWeek"]:
            assert col in cleaned.columns

    def test_order_status_title_case(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        assert all(s == s.title() for s in cleaned["Order_Status"])

    def test_sales_channel_stripped(self, raw_orders):
        cleaned = clean_orders(raw_orders)
        assert all(" " not in s for s in cleaned["Sales_Channel"].str.strip())


# ─── Inventory cleaning ──────────────────────────────────────────────────────
class TestCleanInventory:
    def test_negative_stock_clipped(self, raw_inventory):
        cleaned = clean_inventory(raw_inventory)
        assert (cleaned["Current_Stock"] >= 0).all()

    def test_inventory_value_computed(self, raw_inventory):
        cleaned = clean_inventory(raw_inventory)
        assert "Inventory_Value" in cleaned.columns
        # PRD001: 500 * 60 = 30000
        row = cleaned[cleaned["Product_ID"] == "PRD001"].iloc[0]
        assert abs(row["Inventory_Value"] - 30000.0) < 0.01

    def test_stock_status_categories(self, raw_inventory):
        cleaned = clean_inventory(raw_inventory)
        valid = {"Optimal", "Low Stock", "Out of Stock", "Overstock"}
        assert set(cleaned["Stock_Status"].unique()).issubset(valid)

    def test_category_title_case(self, raw_inventory):
        cleaned = clean_inventory(raw_inventory)
        assert all(s == s.title() for s in cleaned["Category"])


# ─── Supplier cleaning ───────────────────────────────────────────────────────
class TestCleanSuppliers:
    def test_reliability_clipped(self, raw_suppliers):
        cleaned = clean_suppliers(raw_suppliers)
        assert (cleaned["Reliability_Score"] <= 1.0).all()

    def test_lead_time_imputed(self, raw_suppliers):
        cleaned = clean_suppliers(raw_suppliers)
        assert cleaned["Lead_Time"].isna().sum() == 0

    def test_reliability_tier_assigned(self, raw_suppliers):
        cleaned = clean_suppliers(raw_suppliers)
        assert "Reliability_Tier" in cleaned.columns
        assert cleaned["Reliability_Tier"].notna().any()


# ─── Logistics cleaning ──────────────────────────────────────────────────────
class TestCleanLogistics:
    def test_drops_invalid_ship_dates(self, raw_logistics):
        cleaned = clean_logistics(raw_logistics)
        assert len(cleaned) == 1  # SHP002 has bad date

    def test_is_delayed_computed(self, raw_logistics):
        cleaned = clean_logistics(raw_logistics)
        assert "Is_Delayed" in cleaned.columns
        assert cleaned["Is_Delayed"].isin([0, 1]).all()

    def test_carrier_stripped(self, raw_logistics):
        cleaned = clean_logistics(raw_logistics)
        assert "Fedex" in cleaned["Carrier"].values or "FedEx" in cleaned["Carrier"].values

    def test_date_parts_extracted(self, raw_logistics):
        cleaned = clean_logistics(raw_logistics)
        for col in ["Ship_Year", "Ship_Month", "Ship_Quarter"]:
            assert col in cleaned.columns


# ─── Warehouse cleaning ──────────────────────────────────────────────────────
class TestCleanWarehouses:
    def test_utilization_pct_computed(self, raw_warehouses):
        cleaned = clean_warehouses(raw_warehouses)
        assert "Utilization_Pct" in cleaned.columns
        row = cleaned[cleaned["Warehouse_ID"] == "WH01"].iloc[0]
        assert abs(row["Utilization_Pct"] - 75.0) < 0.01

    def test_available_capacity_computed(self, raw_warehouses):
        cleaned = clean_warehouses(raw_warehouses)
        row = cleaned[cleaned["Warehouse_ID"] == "WH01"].iloc[0]
        assert abs(row["Available_Capacity"] - 5000) < 1

    def test_utilization_status_assigned(self, raw_warehouses):
        cleaned = clean_warehouses(raw_warehouses)
        assert "Utilization_Status" in cleaned.columns
