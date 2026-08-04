-- SupplyVision – Analytical Views & Stored Procedures
-- Pre-built queries for Power BI and BI reporting tools

USE supply_vision;

-- ─── View: Executive Dashboard ───────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_executive_summary AS
SELECT
    o.Year,
    o.Quarter,
    o.YearMonth,
    COUNT(o.Order_ID)                                        AS Total_Orders,
    SUM(o.Revenue)                                           AS Total_Revenue,
    SUM(o.COGS)                                              AS Total_COGS,
    SUM(o.Gross_Profit)                                      AS Total_Gross_Profit,
    ROUND(SUM(o.Gross_Profit) / NULLIF(SUM(o.Revenue),0)*100, 2) AS Gross_Margin_Pct,
    COUNT(DISTINCT o.Customer_ID)                            AS Unique_Customers,
    COUNT(DISTINCT o.Product_ID)                             AS Unique_Products,
    ROUND(SUM(o.Revenue) / NULLIF(COUNT(o.Order_ID),0), 2)  AS Avg_Order_Value
FROM fact_orders o
WHERE o.Order_Status != 'Cancelled'
GROUP BY o.Year, o.Quarter, o.YearMonth;

-- ─── View: Inventory Intelligence ────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_inventory_intelligence AS
SELECT
    p.Product_ID,
    p.Product_Name,
    p.Category,
    p.Unit_Cost,
    p.Unit_Price,
    p.Margin_Pct,
    p.Supplier_ID,
    p.Warehouse_ID,
    i.Current_Stock,
    p.Safety_Stock,
    p.Reorder_Point,
    i.Inventory_Value,
    i.Stock_Status,
    w.Warehouse_Name,
    w.Location       AS Warehouse_Location,
    s.Supplier_Name,
    s.Lead_Time,
    s.Reliability_Score
FROM dim_products p
LEFT JOIN fact_inventory   i ON p.Product_ID   = i.Product_ID
LEFT JOIN dim_warehouses   w ON p.Warehouse_ID  = w.Warehouse_ID
LEFT JOIN dim_suppliers    s ON p.Supplier_ID   = s.Supplier_ID;

-- ─── View: Logistics Performance ─────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_logistics_performance AS
SELECT
    l.Shipment_ID,
    l.Order_ID,
    l.Carrier,
    l.Ship_Date,
    l.Delivery_Date,
    l.Transit_Time,
    l.Expected_Transit_Days,
    l.Delay_Days,
    l.Is_Delayed,
    l.Transport_Cost,
    l.Cost_Per_KG,
    l.Delivery_Status,
    l.Ship_Year,
    l.Ship_Month,
    l.Ship_Quarter,
    l.Ship_YearMonth,
    s.Supplier_Name,
    s.Country          AS Supplier_Country,
    s.Region           AS Supplier_Region,
    o.Revenue          AS Order_Revenue,
    o.Category
FROM fact_logistics l
LEFT JOIN dim_suppliers s ON l.Supplier_ID = s.Supplier_ID
LEFT JOIN fact_orders   o ON l.Order_ID    = o.Order_ID;

-- ─── View: Supplier Scorecard ─────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_supplier_scorecard AS
SELECT
    s.Supplier_ID,
    s.Supplier_Name,
    s.Country,
    s.Region,
    s.Lead_Time,
    s.Reliability_Score,
    s.Reliability_Tier,
    s.Lead_Time_Category,
    s.Supplier_Cost,
    COUNT(l.Shipment_ID)                                                    AS Total_Shipments,
    SUM(l.Is_Delayed)                                                       AS Delayed_Shipments,
    ROUND((1 - AVG(l.Is_Delayed)) * 100, 2)                                AS Delivery_Reliability_Pct,
    ROUND(AVG(l.Transit_Time), 2)                                           AS Avg_Transit_Time,
    ROUND(SUM(l.Transport_Cost), 2)                                         AS Total_Logistics_Cost,
    COUNT(DISTINCT p.Product_ID)                                            AS Products_Supplied
FROM dim_suppliers s
LEFT JOIN fact_logistics l ON s.Supplier_ID = l.Supplier_ID
LEFT JOIN dim_products   p ON s.Supplier_ID = p.Supplier_ID
GROUP BY s.Supplier_ID, s.Supplier_Name, s.Country, s.Region,
         s.Lead_Time, s.Reliability_Score, s.Reliability_Tier,
         s.Lead_Time_Category, s.Supplier_Cost;

-- ─── View: Warehouse Utilization ─────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_warehouse_utilization AS
SELECT
    w.Warehouse_ID,
    w.Warehouse_Name,
    w.Location,
    w.Capacity,
    w.Utilization_Pct,
    w.Available_Capacity,
    w.Utilization_Status,
    COUNT(p.Product_ID)        AS Product_Count,
    SUM(i.Current_Stock)       AS Total_Stock,
    SUM(i.Inventory_Value)     AS Total_Inventory_Value,
    COUNT(CASE WHEN i.Stock_Status = 'Out of Stock' THEN 1 END) AS Stock_Out_Products,
    COUNT(CASE WHEN i.Stock_Status = 'Overstock'    THEN 1 END) AS Overstock_Products
FROM dim_warehouses w
LEFT JOIN dim_products  p ON w.Warehouse_ID = p.Warehouse_ID
LEFT JOIN fact_inventory i ON p.Product_ID  = i.Product_ID
GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Location,
         w.Capacity, w.Utilization_Pct, w.Available_Capacity, w.Utilization_Status;

-- ─── Stored Procedure: Monthly KPI Snapshot ──────────────────────────────────
DROP PROCEDURE IF EXISTS sp_monthly_kpi_snapshot;

DELIMITER $$
CREATE PROCEDURE sp_monthly_kpi_snapshot(IN p_year INT, IN p_month INT)
BEGIN
    SELECT
        p_year  AS Report_Year,
        p_month AS Report_Month,
        COUNT(Order_ID)                                          AS Total_Orders,
        ROUND(SUM(Revenue), 2)                                   AS Total_Revenue,
        ROUND(SUM(Gross_Profit), 2)                              AS Gross_Profit,
        ROUND(SUM(Gross_Profit)/NULLIF(SUM(Revenue),0)*100, 2)  AS Gross_Margin_Pct,
        ROUND(AVG(Revenue), 2)                                   AS Avg_Order_Value
    FROM fact_orders
    WHERE Year = p_year AND Month = p_month AND Order_Status != 'Cancelled';
END$$
DELIMITER ;

-- ─── Stored Procedure: Inventory Turnover ─────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_inventory_turnover;

DELIMITER $$
CREATE PROCEDURE sp_inventory_turnover(IN p_year INT)
BEGIN
    DECLARE total_cogs     DECIMAL(18,2);
    DECLARE total_inv_val  DECIMAL(18,2);

    SELECT COALESCE(SUM(COGS), 0) INTO total_cogs
    FROM fact_orders
    WHERE Year = p_year AND Order_Status != 'Cancelled';

    SELECT COALESCE(SUM(Inventory_Value), 1) INTO total_inv_val
    FROM fact_inventory;

    SELECT
        p_year                              AS Year,
        ROUND(total_cogs, 2)               AS Annual_COGS,
        ROUND(total_inv_val, 2)            AS Inventory_Value,
        ROUND(total_cogs / total_inv_val, 4) AS Inventory_Turnover_Ratio,
        ROUND(365 / (total_cogs / total_inv_val), 1) AS Days_Inventory_Outstanding;
END$$
DELIMITER ;

SELECT 'Analytical views and procedures created successfully.' AS status;
