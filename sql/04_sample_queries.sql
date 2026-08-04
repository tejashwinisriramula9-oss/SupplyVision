-- SupplyVision – Sample Analytical Queries
-- Use these in Power BI DirectQuery or for ad-hoc analysis

USE supply_vision;

-- ══════════════════════════════════════════════════════════════════════════════
-- EXECUTIVE OVERVIEW
-- ══════════════════════════════════════════════════════════════════════════════

-- 1. Total Revenue, Orders, Margin by Year
SELECT
    Year,
    COUNT(Order_ID)                                              AS Total_Orders,
    ROUND(SUM(Revenue), 2)                                       AS Total_Revenue,
    ROUND(SUM(COGS), 2)                                          AS Total_COGS,
    ROUND(SUM(Gross_Profit), 2)                                  AS Gross_Profit,
    ROUND(SUM(Gross_Profit) / NULLIF(SUM(Revenue),0) * 100, 2)  AS Gross_Margin_Pct
FROM fact_orders
WHERE Order_Status != 'Cancelled'
GROUP BY Year
ORDER BY Year;

-- 2. Monthly Revenue Trend
SELECT
    YearMonth,
    ROUND(SUM(Revenue), 2)   AS Monthly_Revenue,
    COUNT(Order_ID)           AS Monthly_Orders,
    ROUND(AVG(Revenue), 2)   AS Avg_Order_Value
FROM fact_orders
WHERE Order_Status != 'Cancelled'
GROUP BY YearMonth
ORDER BY YearMonth;

-- 3. Revenue by Sales Channel
SELECT
    Sales_Channel,
    COUNT(Order_ID)          AS Orders,
    ROUND(SUM(Revenue), 2)  AS Revenue,
    ROUND(AVG(Revenue), 2)  AS Avg_Order_Value
FROM fact_orders
WHERE Order_Status != 'Cancelled'
GROUP BY Sales_Channel
ORDER BY Revenue DESC;

-- ══════════════════════════════════════════════════════════════════════════════
-- INVENTORY INTELLIGENCE
-- ══════════════════════════════════════════════════════════════════════════════

-- 4. Inventory Value by Category
SELECT
    p.Category,
    COUNT(p.Product_ID)           AS Product_Count,
    SUM(i.Current_Stock)          AS Total_Stock,
    ROUND(SUM(i.Inventory_Value), 2) AS Inventory_Value
FROM dim_products p
JOIN fact_inventory i ON p.Product_ID = i.Product_ID
GROUP BY p.Category
ORDER BY Inventory_Value DESC;

-- 5. Stock-Out and Low Stock Alert
SELECT
    p.Product_ID,
    p.Product_Name,
    p.Category,
    i.Current_Stock,
    p.Safety_Stock,
    i.Stock_Status,
    ROUND(i.Inventory_Value, 2) AS Inventory_Value
FROM fact_inventory i
JOIN dim_products  p ON i.Product_ID  = p.Product_ID
WHERE i.Stock_Status IN ('Out of Stock', 'Low Stock')
ORDER BY i.Stock_Status, i.Current_Stock;

-- 6. Top 10 Products by Revenue (orders joined)
SELECT
    o.Product_ID,
    p.Product_Name,
    p.Category,
    ROUND(SUM(o.Revenue), 2)  AS Total_Revenue,
    SUM(o.Quantity)            AS Total_Sold
FROM fact_orders  o
JOIN dim_products p ON o.Product_ID = p.Product_ID
WHERE o.Order_Status != 'Cancelled'
GROUP BY o.Product_ID, p.Product_Name, p.Category
ORDER BY Total_Revenue DESC
LIMIT 10;

-- ══════════════════════════════════════════════════════════════════════════════
-- LOGISTICS ANALYTICS
-- ══════════════════════════════════════════════════════════════════════════════

-- 7. On-Time Delivery by Carrier
SELECT
    Carrier,
    COUNT(Shipment_ID)                                    AS Total_Shipments,
    SUM(Is_Delayed)                                       AS Delayed,
    ROUND((1 - AVG(Is_Delayed)) * 100, 2)                AS On_Time_Pct,
    ROUND(AVG(Transit_Time), 2)                           AS Avg_Transit_Days,
    ROUND(SUM(Transport_Cost), 2)                         AS Total_Cost
FROM fact_logistics
GROUP BY Carrier
ORDER BY On_Time_Pct DESC;

-- 8. Monthly Delay Trend
SELECT
    Ship_YearMonth,
    COUNT(Shipment_ID)                         AS Total_Shipments,
    SUM(Is_Delayed)                            AS Delayed_Shipments,
    ROUND(AVG(Delay_Days), 2)                  AS Avg_Delay_Days,
    ROUND(SUM(Transport_Cost), 2)              AS Total_Cost
FROM fact_logistics
GROUP BY Ship_YearMonth
ORDER BY Ship_YearMonth;

-- ══════════════════════════════════════════════════════════════════════════════
-- SUPPLIER ANALYTICS
-- ══════════════════════════════════════════════════════════════════════════════

-- 9. Full Supplier Scorecard
SELECT * FROM vw_supplier_scorecard
ORDER BY Delivery_Reliability_Pct DESC;

-- 10. Suppliers by Reliability Tier
SELECT
    Reliability_Tier,
    COUNT(Supplier_ID)            AS Supplier_Count,
    ROUND(AVG(Reliability_Score), 4) AS Avg_Score,
    ROUND(AVG(Lead_Time), 1)     AS Avg_Lead_Time,
    ROUND(SUM(Supplier_Cost), 2) AS Total_Cost
FROM dim_suppliers
GROUP BY Reliability_Tier
ORDER BY Avg_Score DESC;

-- ══════════════════════════════════════════════════════════════════════════════
-- KPI CALCULATIONS
-- ══════════════════════════════════════════════════════════════════════════════

-- 11. Inventory Turnover Ratio (2024)
CALL sp_inventory_turnover(2024);

-- 12. Monthly KPI Snapshot (March 2024)
CALL sp_monthly_kpi_snapshot(2024, 3);

-- 13. Fill Rate % (products with stock > 0 / total products)
SELECT
    COUNT(*)                                                    AS Total_Products,
    SUM(CASE WHEN Current_Stock > 0 THEN 1 ELSE 0 END)        AS In_Stock,
    ROUND(SUM(CASE WHEN Current_Stock > 0 THEN 1 ELSE 0 END)
          / COUNT(*) * 100, 2)                                  AS Fill_Rate_Pct
FROM fact_inventory;
