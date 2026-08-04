"""
SupplyVision – Realistic Enterprise Dataset Generator
Generates Orders, Inventory, Suppliers, Logistics, and Warehouse data.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
rng = np.random.default_rng(seed=42)
random.seed(42)

# ─── Output directory ────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Constants ───────────────────────────────────────────────────────────────
NUM_PRODUCTS   = 200    # Phase 1: 200+ products
NUM_SUPPLIERS  = 50     # Phase 1: 50+ suppliers
NUM_WAREHOUSES = 10     # Phase 1: 10 warehouses
NUM_CUSTOMERS  = 800
NUM_ORDERS     = 5000   # Phase 1: 1000+ orders (keeping 5000 for richness)
NUM_SHIPMENTS  = 4500   # Phase 1: 500+ shipments
START_DATE = datetime(2022, 1, 1)
END_DATE   = datetime(2024, 12, 31)

CATEGORIES = [
    "Electronics", "Industrial Parts", "Raw Materials",
    "Packaging", "Consumables", "Machinery", "Chemicals", "Textiles",
    "Office Supplies", "Safety Equipment",
]

CARRIERS = ["FedEx", "DHL", "UPS", "Maersk", "DB Schenker", "XPO Logistics",
            "Amazon Logistics", "CEVA Logistics"]

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]

WAREHOUSES = [
    {"Warehouse_ID": f"WH{str(i+1).zfill(2)}", "Warehouse_Name": name, "Location": loc}
    for i, (name, loc) in enumerate([
        ("Chicago Distribution Center", "Chicago, IL"),
        ("Los Angeles Hub",             "Los Angeles, CA"),
        ("Dallas Fulfillment Center",   "Dallas, TX"),
        ("New York East Hub",           "Newark, NJ"),
        ("Miami Gateway",               "Miami, FL"),
        ("Seattle Pacific Hub",         "Seattle, WA"),
        ("Atlanta South Hub",           "Atlanta, GA"),
        ("Denver Mountain Center",      "Denver, CO"),
        ("Phoenix Desert Hub",          "Phoenix, AZ"),
        ("Minneapolis North Center",    "Minneapolis, MN"),
    ])
]


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=int(rng.integers(0, delta.days)))


# ─── 1. Warehouse Table ───────────────────────────────────────────────────────
def generate_warehouses() -> pd.DataFrame:
    rows = []
    for wh in WAREHOUSES:
        capacity = int(rng.integers(5_000, 50_000))
        utilization = round(float(rng.uniform(0.45, 0.95)), 4)
        rows.append({
            "Warehouse_ID": wh["Warehouse_ID"],
            "Warehouse_Name": wh["Warehouse_Name"],
            "Capacity": capacity,
            "Utilization": utilization,
            "Location": wh["Location"],
        })
    return pd.DataFrame(rows)


# ─── 2. Supplier Table ────────────────────────────────────────────────────────
def generate_suppliers() -> pd.DataFrame:
    rows = []
    for i in range(NUM_SUPPLIERS):
        rows.append({
            "Supplier_ID":       f"SUP{str(i+1).zfill(3)}",
            "Supplier_Name":     fake.company(),
            "Country":           fake.country(),
            "Region":            random.choice(REGIONS),
            "Lead_Time":         int(rng.integers(3, 45)),
            "Reliability_Score": round(float(rng.uniform(0.55, 0.99)), 4),
            "Supplier_Cost":     round(float(rng.uniform(5_000, 200_000)), 2),
            "Contact_Email":     fake.company_email(),
            "Phone":             fake.phone_number(),
        })
    return pd.DataFrame(rows)


# ─── 2b. Customer Table ───────────────────────────────────────────────────────
def generate_customers() -> pd.DataFrame:
    rows = []
    for i in range(NUM_CUSTOMERS):
        rows.append({
            "Customer_ID":      f"CUST{str(i+1).zfill(4)}",
            "Customer_Name":    fake.name(),
            "Company":          fake.company(),
            "Email":            fake.email(),
            "Phone":            fake.phone_number(),
            "Country":          fake.country(),
            "Region":           random.choice(REGIONS),
            "Customer_Segment": random.choices(
                ["Enterprise", "Mid-Market", "SMB", "Government"],
                weights=[20, 35, 35, 10]
            )[0],
            "Registration_Date": random_date(datetime(2020, 1, 1), START_DATE).strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


# ─── 3. Inventory / Product Table ────────────────────────────────────────────
def generate_inventory(supplier_ids: list, warehouse_ids: list) -> pd.DataFrame:
    rows = []
    for i in range(NUM_PRODUCTS):
        category = random.choice(CATEGORIES)
        safety_stock = int(rng.integers(50, 500))
        current_stock = int(rng.integers(0, 2000))
        unit_cost = round(float(rng.uniform(5, 2500)), 2)
        rows.append({
            "Product_ID": f"PRD{str(i+1).zfill(4)}",
            "Product_Name": f"{fake.word().capitalize()} {category.split()[0]} {fake.lexify('???').upper()}",
            "Category": category,
            "Current_Stock": current_stock,
            "Safety_Stock": safety_stock,
            "Reorder_Point": safety_stock + int(rng.integers(20, 200)),
            "Unit_Cost": unit_cost,
            "Unit_Price": round(unit_cost * float(rng.uniform(1.2, 3.0)), 2),
            "Warehouse_ID": random.choice(warehouse_ids),
            "Supplier_ID": random.choice(supplier_ids),
            "Last_Updated": random_date(START_DATE, END_DATE).strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


# ─── 4. Orders Table ─────────────────────────────────────────────────────────
def generate_orders(product_ids: list) -> pd.DataFrame:
    rows = []
    for i in range(NUM_ORDERS):
        order_date = random_date(START_DATE, END_DATE)
        quantity = int(rng.integers(1, 200))
        product_id = random.choice(product_ids)
        unit_price = round(float(rng.uniform(10, 5000)), 2)
        discount = round(float(random.choices([0, 0, 0, 0.05, 0.10, 0.15], weights=[50, 15, 10, 10, 10, 5])[0]), 2)
        revenue = round(quantity * unit_price * (1 - discount), 2)
        rows.append({
            "Order_ID": f"ORD{str(i+1).zfill(5)}",
            "Product_ID": product_id,
            "Customer_ID": f"CUST{str(rng.integers(1, NUM_CUSTOMERS+1)).zfill(4)}",
            "Order_Date": order_date.strftime("%Y-%m-%d"),
            "Quantity": quantity,
            "Unit_Price": unit_price,
            "Discount": discount,
            "Revenue": revenue,
            "Order_Status": random.choices(
                ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"],
                weights=[65, 15, 10, 6, 4],
            )[0],
            "Sales_Channel": random.choice(["Online", "Direct Sales", "Partner", "Distribution"]),
        })
    return pd.DataFrame(rows)


# ─── 5. Logistics / Shipment Table ───────────────────────────────────────────
def generate_logistics(order_ids: list, supplier_ids: list) -> pd.DataFrame:
    rows = []
    sampled_orders = random.choices(order_ids, k=NUM_SHIPMENTS)
    for i, order_id in enumerate(sampled_orders):
        ship_date = random_date(START_DATE, END_DATE)
        expected_transit = int(rng.integers(2, 30))
        delta = int(random.choices([-2, -1, 0, 1, 2, 5, 10], weights=[5, 10, 45, 15, 10, 10, 5])[0])
        actual_transit = expected_transit + delta
        actual_transit = max(1, actual_transit)
        delivery_date = ship_date + timedelta(days=actual_transit)
        on_time = delivery_date <= ship_date + timedelta(days=expected_transit)
        rows.append({
            "Shipment_ID": f"SHP{str(i+1).zfill(5)}",
            "Order_ID": order_id,
            "Supplier_ID": random.choice(supplier_ids),
            "Ship_Date": ship_date.strftime("%Y-%m-%d"),
            "Delivery_Date": delivery_date.strftime("%Y-%m-%d"),
            "Expected_Transit_Days": expected_transit,
            "Transit_Time": actual_transit,
            "Transport_Cost": round(float(rng.uniform(50, 5000)), 2),
            "Carrier": random.choice(CARRIERS),
            "Delivery_Status": "On Time" if on_time else "Delayed",
            "Origin_Country": fake.country(),
            "Destination_Country": fake.country(),
            "Weight_KG": round(float(rng.uniform(0.5, 1000)), 2),
        })
    return pd.DataFrame(rows)


# ─── Main ─────────────────────────────────────────────────────────────────────
def generate_all(save_csv: bool = True, save_excel: bool = True) -> dict[str, pd.DataFrame]:
    print("🏭  SupplyVision – Generating enterprise datasets …")

    warehouses_df = generate_warehouses()
    print(f"  ✔  Warehouses  : {len(warehouses_df):>5} rows")

    suppliers_df = generate_suppliers()
    print(f"  ✔  Suppliers   : {len(suppliers_df):>5} rows")

    customers_df = generate_customers()
    print(f"  ✔  Customers   : {len(customers_df):>5} rows")

    inventory_df = generate_inventory(
        supplier_ids=suppliers_df["Supplier_ID"].tolist(),
        warehouse_ids=warehouses_df["Warehouse_ID"].tolist(),
    )
    print(f"  ✔  Inventory   : {len(inventory_df):>5} rows")

    orders_df = generate_orders(product_ids=inventory_df["Product_ID"].tolist())
    print(f"  ✔  Orders      : {len(orders_df):>5} rows")

    logistics_df = generate_logistics(
        order_ids=orders_df["Order_ID"].tolist(),
        supplier_ids=suppliers_df["Supplier_ID"].tolist(),
    )
    print(f"  ✔  Logistics   : {len(logistics_df):>5} rows")

    datasets = {
        "warehouses": warehouses_df,
        "suppliers":  suppliers_df,
        "customers":  customers_df,
        "inventory":  inventory_df,
        "orders":     orders_df,
        "logistics":  logistics_df,
    }

    if save_csv:
        for name, df in datasets.items():
            path = OUTPUT_DIR / f"{name}.csv"
            df.to_csv(path, index=False)
            print(f"  💾  Saved CSV  : {path}")

    if save_excel:
        excel_path = OUTPUT_DIR / "supply_chain_data.xlsx"
        with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
            for name, df in datasets.items():
                df.to_excel(writer, sheet_name=name.capitalize(), index=False)
        print(f"  💾  Saved XLSX : {excel_path}")

    print("✅  Dataset generation complete.\n")
    return datasets


if __name__ == "__main__":
    generate_all()
