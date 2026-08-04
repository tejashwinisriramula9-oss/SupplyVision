"""Prints expected DAX measure values for Power BI verification."""
import pandas as pd
from pathlib import Path

p = Path("data/processed")
inv = pd.read_parquet(p / "inventory_clean.parquet")
fo  = pd.read_parquet(p / "fact_orders_clean.parquet")
sup = pd.read_parquet(p / "suppliers_clean.parquet")
lg  = pd.read_parquet(p / "logistics_clean.parquet")
wh  = pd.read_parquet(p / "warehouses_clean.parquet")

print("=" * 60)
print("  EXPECTED MEASURE VALUES — Power BI Verification")
print("=" * 60)

active = fo[fo["Order_Status"] != "Cancelled"]
print(f"\n--- Executive ---")
print(f"Total Revenue:           ${active['Revenue'].sum():>15,.2f}")
print(f"Total Orders:            {len(active):>15,}")
print(f"Gross Profit Total:      ${active['Gross_Profit'].sum():>15,.2f}")
margin = active["Gross_Profit"].sum() / active["Revenue"].sum() * 100
print(f"Gross Margin %:          {margin:>15.2f}%")
avg_ov = active["Revenue"].sum() / len(active)
print(f"Average Order Value:     ${avg_ov:>15,.2f}")
cancelled = fo[fo["Order_Status"] == "Cancelled"]
print(f"Cancelled Order %:       {len(cancelled)/len(fo)*100:>15.2f}%")

print(f"\n--- Inventory ---")
print(f"Total Inventory Value:   ${inv['Inventory_Value'].sum():>15,.2f}")
print(f"Current Stock Total:     {inv['Current_Stock'].sum():>15,}")
print(f"Safety Stock Total:      {inv['Safety_Stock'].sum():>15,}")
low  = inv[inv["Stock_Status"].isin(["Low Stock","Out of Stock"])]
oos  = inv[inv["Stock_Status"] == "Out of Stock"]
over = inv[inv["Stock_Status"] == "Overstock"]
print(f"Low Stock Alert Count:   {len(low):>15,}")
print(f"Stock-Out Rate %:        {len(oos)/len(inv)*100:>15.2f}%")
print(f"Fill Rate %:             {(1 - len(oos)/len(inv))*100:>15.2f}%")
print(f"Overstock Rate %:        {len(over)/len(inv)*100:>15.2f}%")
cogs = active["COGS"].sum()
inv_val = inv["Inventory_Value"].sum()
turnover = cogs / inv_val if inv_val > 0 else 0
print(f"Inventory Turnover Ratio:{turnover:>15.4f}x")
print(f"Days Inventory Outstdg:  {365/turnover if turnover > 0 else 0:>15.1f} days")

print(f"\n--- Logistics ---")
total = len(lg)
on_time = lg["Is_Delayed"].eq(0).sum()
delayed = lg["Is_Delayed"].eq(1).sum()
print(f"Total Shipments:         {total:>15,}")
print(f"On-Time Delivery %:      {on_time/total*100:>15.2f}%")
print(f"Delayed Deliveries:      {delayed:>15,}")
print(f"Avg Transit Time:        {lg['Transit_Time'].mean():>15.2f} days")
only_delayed = lg[lg["Is_Delayed"] == 1]
print(f"Avg Delay Days (delayed):{only_delayed['Delay_Days'].mean():>15.2f} days")
print(f"Total Transport Cost:    ${lg['Transport_Cost'].sum():>15,.2f}")

print(f"\n--- Suppliers ---")
print(f"Total Suppliers:         {len(sup):>15,}")
excellent = sup[sup["Reliability_Tier"] == "Excellent"]
poor = sup[sup["Reliability_Tier"] == "Poor"]
print(f"Excellent Suppliers:     {len(excellent):>15,}")
print(f"Poor Suppliers:          {len(poor):>15,}")
print(f"Supplier Reliability %:  {sup['Reliability_Score'].mean()*100:>15.2f}%")
print(f"Avg Lead Time:           {sup['Lead_Time'].mean():>15.2f} days")
print(f"Total Supplier Cost:     ${sup['Supplier_Cost'].sum():>15,.2f}")

print("\n" + "=" * 60)
print("  Compare these numbers to your Power BI card visuals.")
print("  Matching values = DAX measures are correct.")
print("=" * 60)
