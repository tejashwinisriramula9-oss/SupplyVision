-- ============================================================
-- SupplyVision – Master Schema
-- Enterprise Supply Chain Analytics & Inventory Intelligence
-- ============================================================
-- Run order: schema.sql → sample_data.sql (or load_data.py)
-- Tested on: MySQL 8.0+
-- ============================================================

-- ─── Database ────────────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS supply_vision
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'sv_user'@'localhost'
    IDENTIFIED BY 'SV@SecurePass2024!';

GRANT ALL PRIVILEGES ON supply_vision.* TO 'sv_user'@'localhost';
FLUSH PRIVILEGES;

USE supply_vision;

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- ─── dim_warehouses ──────────────────────────────────────────
DROP TABLE IF EXISTS dim_warehouses;
CREATE TABLE dim_warehouses (
    Warehouse_ID        VARCHAR(10)   NOT NULL COMMENT 'WH01..WH10',
    Warehouse_Name      VARCHAR(100)  NOT NULL,
    Capacity            INT           NOT NULL DEFAULT 0    COMMENT 'Max pallet capacity',
    Utilization         DECIMAL(5,4)  NOT NULL DEFAULT 0.00 COMMENT 'Fractional 0–1',
    Available_Capacity  INT           NOT NULL DEFAULT 0,
    Utilization_Pct     DECIMAL(6,2)  NOT NULL DEFAULT 0.00,
    Utilization_Status  ENUM('Underutilized','Normal','High','Critical') DEFAULT 'Normal',
    Location            VARCHAR(100),
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Warehouse_ID),
    INDEX idx_wh_status (Utilization_Status)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Warehouse dimension – locations, capacity, utilization';

-- ─── dim_suppliers ───────────────────────────────────────────
DROP TABLE IF EXISTS dim_suppliers;
CREATE TABLE dim_suppliers (
    Supplier_ID         VARCHAR(10)   NOT NULL COMMENT 'SUP001..SUP050',
    Supplier_Name       VARCHAR(150)  NOT NULL,
    Country             VARCHAR(100),
    Region              VARCHAR(50),
    Lead_Time           SMALLINT      NOT NULL DEFAULT 14   COMMENT 'Days',
    Reliability_Score   DECIMAL(5,4)  NOT NULL DEFAULT 0.75 COMMENT '0–1 scale',
    Reliability_Tier    ENUM('Poor','Acceptable','Good','Excellent') DEFAULT 'Good',
    Lead_Time_Category  ENUM('Express','Standard','Extended','Long Lead') DEFAULT 'Standard',
    Supplier_Cost       DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT 'Annual contract cost USD',
    Contact_Email       VARCHAR(150),
    Phone               VARCHAR(50),
    Is_Active           TINYINT(1)    NOT NULL DEFAULT 1,
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Supplier_ID),
    INDEX idx_sup_tier   (Reliability_Tier),
    INDEX idx_sup_region (Region),
    INDEX idx_sup_active (Is_Active)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Supplier dimension – reliability tiers, lead times, costs';

-- ─── dim_customers ───────────────────────────────────────────
DROP TABLE IF EXISTS dim_customers;
CREATE TABLE dim_customers (
    Customer_ID         VARCHAR(12)  NOT NULL COMMENT 'CUST0001..CUST0800',
    Customer_Name       VARCHAR(150),
    Company             VARCHAR(150),
    Email               VARCHAR(150),
    Phone               VARCHAR(50),
    Country             VARCHAR(100),
    Region              VARCHAR(50),
    Customer_Segment    ENUM('Enterprise','Mid-Market','SMB','Government') DEFAULT 'SMB',
    Registration_Date   DATE,
    Is_Active           TINYINT(1)   NOT NULL DEFAULT 1,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Customer_ID),
    INDEX idx_cust_segment (Customer_Segment),
    INDEX idx_cust_region  (Region)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Customer dimension – segments and demographics';

-- ─── dim_products ────────────────────────────────────────────
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    Product_ID      VARCHAR(10)   NOT NULL COMMENT 'PRD0001..PRD0200',
    Product_Name    VARCHAR(150)  NOT NULL,
    Category        VARCHAR(50)   NOT NULL,
    Sub_Category    VARCHAR(50),
    SKU             VARCHAR(30)   GENERATED ALWAYS AS (Product_ID) STORED,
    Safety_Stock    INT           NOT NULL DEFAULT 0  COMMENT 'Min stock before reorder alert',
    Reorder_Point   INT           NOT NULL DEFAULT 0  COMMENT 'Trigger reorder at this level',
    Min_Order_Qty   INT           NOT NULL DEFAULT 1,
    Unit_Cost       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Unit_Price      DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Margin_Pct      DECIMAL(6,2)
                    GENERATED ALWAYS AS (
                        ROUND((Unit_Price - Unit_Cost) / Unit_Price * 100, 2)
                    ) STORED COMMENT 'Computed gross margin %',
    Warehouse_ID    VARCHAR(10),
    Supplier_ID     VARCHAR(10),
    Is_Active       TINYINT(1)    NOT NULL DEFAULT 1,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Product_ID),
    INDEX idx_prod_category  (Category),
    INDEX idx_prod_warehouse (Warehouse_ID),
    INDEX idx_prod_supplier  (Supplier_ID),
    INDEX idx_prod_active    (Is_Active),
    CONSTRAINT fk_product_warehouse FOREIGN KEY (Warehouse_ID)
        REFERENCES dim_warehouses(Warehouse_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_product_supplier  FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_product_price CHECK (Unit_Price >= Unit_Cost),
    CONSTRAINT chk_safety_stock  CHECK (Safety_Stock >= 0),
    CONSTRAINT chk_reorder_point CHECK (Reorder_Point >= Safety_Stock)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Product/SKU dimension with computed margin and FK constraints';

-- ============================================================
-- FACT TABLES
-- ============================================================

-- ─── fact_inventory ──────────────────────────────────────────
DROP TABLE IF EXISTS fact_inventory;
CREATE TABLE fact_inventory (
    Product_ID       VARCHAR(10)   NOT NULL,
    Current_Stock    INT           NOT NULL DEFAULT 0  COMMENT 'Units on hand',
    Inventory_Value  DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT 'Current_Stock × Unit_Cost',
    Stock_Status     ENUM('Out of Stock','Low Stock','Optimal','Overstock') DEFAULT 'Optimal',
    Last_Updated     DATE,
    Snapshot_Date    DATE          NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (Product_ID),
    INDEX idx_inv_status   (Stock_Status),
    INDEX idx_inv_snapshot (Snapshot_Date),
    CONSTRAINT fk_inv_product FOREIGN KEY (Product_ID)
        REFERENCES dim_products(Product_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Current inventory snapshot – stock levels and valuation';

-- ─── fact_orders ─────────────────────────────────────────────
DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    Order_ID              VARCHAR(12)   NOT NULL COMMENT 'ORD00001..ORD05000',
    Product_ID            VARCHAR(10),
    Customer_ID           VARCHAR(12),
    Order_Date            DATE          NOT NULL,
    Year                  SMALLINT      NOT NULL,
    Month                 TINYINT       NOT NULL  CHECK (Month BETWEEN 1 AND 12),
    Quarter               TINYINT       NOT NULL  CHECK (Quarter BETWEEN 1 AND 4),
    YearMonth             VARCHAR(10)             COMMENT 'YYYY-MM',
    YearQuarter           VARCHAR(12)             COMMENT 'YYYY QN',
    WeekOfYear            TINYINT,
    DayOfWeek             VARCHAR(12),
    Quantity              INT           NOT NULL DEFAULT 1 CHECK (Quantity > 0),
    Unit_Price            DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Discount              DECIMAL(5,4)  NOT NULL DEFAULT 0.00 CHECK (Discount BETWEEN 0 AND 1),
    Revenue               DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    COGS                  DECIMAL(16,2)           COMMENT 'Quantity × Unit_Cost',
    Gross_Profit          DECIMAL(16,2)           COMMENT 'Revenue − COGS',
    Gross_Margin_Pct      DECIMAL(6,2),
    Order_Status          ENUM('Delivered','Shipped','Processing','Cancelled','Returned')
                              DEFAULT 'Processing',
    Sales_Channel         ENUM('Online','Direct Sales','Partner','Distribution')
                              DEFAULT 'Online',
    Category              VARCHAR(50),
    Warehouse_ID          VARCHAR(10),
    Supplier_ID           VARCHAR(10),
    Shipment_Count        TINYINT       DEFAULT 0,
    Avg_Transit_Time      DECIMAL(6,2),
    Total_Transport_Cost  DECIMAL(14,2),
    Delayed_Shipments     TINYINT       DEFAULT 0,
    PRIMARY KEY (Order_ID),
    INDEX idx_ord_date      (Order_Date),
    INDEX idx_ord_year      (Year),
    INDEX idx_ord_yearmonth (YearMonth),
    INDEX idx_ord_product   (Product_ID),
    INDEX idx_ord_customer  (Customer_ID),
    INDEX idx_ord_status    (Order_Status),
    INDEX idx_ord_channel   (Sales_Channel),
    INDEX idx_ord_category  (Category),
    CONSTRAINT fk_order_product   FOREIGN KEY (Product_ID)
        REFERENCES dim_products(Product_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_order_customer  FOREIGN KEY (Customer_ID)
        REFERENCES dim_customers(Customer_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_order_warehouse FOREIGN KEY (Warehouse_ID)
        REFERENCES dim_warehouses(Warehouse_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_order_supplier  FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Order transactions fact – revenue, margins, and logistics linkage';

-- ─── fact_logistics ──────────────────────────────────────────
DROP TABLE IF EXISTS fact_logistics;
CREATE TABLE fact_logistics (
    Shipment_ID              VARCHAR(12)   NOT NULL COMMENT 'SHP00001..SHP04500',
    Order_ID                 VARCHAR(12),
    Supplier_ID              VARCHAR(10),
    Ship_Date                DATE          NOT NULL,
    Delivery_Date            DATE,
    Expected_Transit_Days    SMALLINT,
    Transit_Time             SMALLINT      CHECK (Transit_Time > 0),
    Delay_Days               SMALLINT      DEFAULT 0 CHECK (Delay_Days >= 0),
    Is_Delayed               TINYINT(1)    DEFAULT 0,
    Transport_Cost           DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Cost_Per_KG              DECIMAL(10,2),
    Carrier                  VARCHAR(60),
    Delivery_Status          ENUM('On Time','Delayed','Lost','Returned') DEFAULT 'On Time',
    Origin_Country           VARCHAR(100),
    Destination_Country      VARCHAR(100),
    Weight_KG                DECIMAL(10,3),
    Ship_Year                SMALLINT,
    Ship_Month               TINYINT,
    Ship_Quarter             TINYINT,
    Ship_YearMonth           VARCHAR(10),
    PRIMARY KEY (Shipment_ID),
    INDEX idx_ship_date      (Ship_Date),
    INDEX idx_ship_carrier   (Carrier),
    INDEX idx_ship_delayed   (Is_Delayed),
    INDEX idx_ship_year      (Ship_Year),
    INDEX idx_ship_supplier  (Supplier_ID),
    INDEX idx_ship_order     (Order_ID),
    CONSTRAINT fk_logistics_supplier FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Shipment fact – transit times, delays, carrier performance';

-- ============================================================
-- AUDIT / HISTORY TABLE
-- ============================================================
DROP TABLE IF EXISTS audit_inventory_history;
CREATE TABLE audit_inventory_history (
    History_ID      INT           NOT NULL AUTO_INCREMENT,
    Product_ID      VARCHAR(10)   NOT NULL,
    Change_Date     DATE          NOT NULL,
    Old_Stock       INT,
    New_Stock       INT,
    Change_Reason   VARCHAR(100)  COMMENT 'Restock / Sale / Adjustment',
    Changed_By      VARCHAR(50)   DEFAULT 'SYSTEM',
    PRIMARY KEY (History_ID),
    INDEX idx_audit_product (Product_ID),
    INDEX idx_audit_date    (Change_Date)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COMMENT='Inventory change audit trail';

-- ============================================================
-- TRIGGER: auto-log inventory changes
-- ============================================================
DROP TRIGGER IF EXISTS trg_inventory_after_update;

DELIMITER $$
CREATE TRIGGER trg_inventory_after_update
    AFTER UPDATE ON fact_inventory
    FOR EACH ROW
BEGIN
    IF OLD.Current_Stock <> NEW.Current_Stock THEN
        INSERT INTO audit_inventory_history
            (Product_ID, Change_Date, Old_Stock, New_Stock, Change_Reason)
        VALUES
            (NEW.Product_ID, CURRENT_DATE, OLD.Current_Stock,
             NEW.Current_Stock, 'System Update');
    END IF;
END$$
DELIMITER ;

-- ============================================================
-- VIEWS
-- ============================================================

-- Executive summary view
CREATE OR REPLACE VIEW vw_executive_summary AS
SELECT
    o.Year,
    o.Quarter,
    o.YearMonth,
    COUNT(o.Order_ID)                                           AS Total_Orders,
    SUM(o.Revenue)                                              AS Total_Revenue,
    SUM(o.COGS)                                                 AS Total_COGS,
    SUM(o.Gross_Profit)                                         AS Total_Gross_Profit,
    ROUND(SUM(o.Gross_Profit)/NULLIF(SUM(o.Revenue),0)*100, 2) AS Gross_Margin_Pct,
    COUNT(DISTINCT o.Customer_ID)                               AS Unique_Customers,
    COUNT(DISTINCT o.Product_ID)                                AS Unique_Products,
    ROUND(SUM(o.Revenue)/NULLIF(COUNT(o.Order_ID),0), 2)       AS Avg_Order_Value
FROM fact_orders o
WHERE o.Order_Status != 'Cancelled'
GROUP BY o.Year, o.Quarter, o.YearMonth;

-- Inventory intelligence view
CREATE OR REPLACE VIEW vw_inventory_intelligence AS
SELECT
    p.Product_ID, p.Product_Name, p.Category, p.Sub_Category,
    p.Unit_Cost, p.Unit_Price, p.Margin_Pct,
    p.Supplier_ID, p.Warehouse_ID,
    i.Current_Stock, p.Safety_Stock, p.Reorder_Point,
    i.Inventory_Value, i.Stock_Status, i.Last_Updated,
    w.Warehouse_Name, w.Location AS Warehouse_Location,
    s.Supplier_Name, s.Lead_Time, s.Reliability_Score, s.Reliability_Tier
FROM dim_products p
LEFT JOIN fact_inventory  i ON p.Product_ID  = i.Product_ID
LEFT JOIN dim_warehouses  w ON p.Warehouse_ID = w.Warehouse_ID
LEFT JOIN dim_suppliers   s ON p.Supplier_ID  = s.Supplier_ID;

-- Logistics performance view
CREATE OR REPLACE VIEW vw_logistics_performance AS
SELECT
    l.Shipment_ID, l.Order_ID, l.Carrier,
    l.Ship_Date, l.Delivery_Date, l.Transit_Time,
    l.Expected_Transit_Days, l.Delay_Days, l.Is_Delayed,
    l.Transport_Cost, l.Cost_Per_KG, l.Delivery_Status,
    l.Ship_Year, l.Ship_Month, l.Ship_Quarter, l.Ship_YearMonth,
    s.Supplier_Name, s.Country AS Supplier_Country, s.Region AS Supplier_Region,
    o.Revenue AS Order_Revenue, o.Category
FROM fact_logistics l
LEFT JOIN dim_suppliers s ON l.Supplier_ID = s.Supplier_ID
LEFT JOIN fact_orders   o ON l.Order_ID    = o.Order_ID;

-- Supplier scorecard view
CREATE OR REPLACE VIEW vw_supplier_scorecard AS
SELECT
    s.Supplier_ID, s.Supplier_Name, s.Country, s.Region,
    s.Lead_Time, s.Reliability_Score, s.Reliability_Tier,
    s.Lead_Time_Category, s.Supplier_Cost,
    COUNT(l.Shipment_ID)                        AS Total_Shipments,
    SUM(l.Is_Delayed)                           AS Delayed_Shipments,
    ROUND((1-AVG(l.Is_Delayed))*100, 2)         AS Delivery_Reliability_Pct,
    ROUND(AVG(l.Transit_Time), 2)               AS Avg_Transit_Time,
    ROUND(SUM(l.Transport_Cost), 2)             AS Total_Logistics_Cost,
    COUNT(DISTINCT p.Product_ID)                AS Products_Supplied
FROM dim_suppliers s
LEFT JOIN fact_logistics l ON s.Supplier_ID = l.Supplier_ID
LEFT JOIN dim_products   p ON s.Supplier_ID = p.Supplier_ID
GROUP BY s.Supplier_ID, s.Supplier_Name, s.Country, s.Region,
         s.Lead_Time, s.Reliability_Score, s.Reliability_Tier,
         s.Lead_Time_Category, s.Supplier_Cost;

-- Warehouse utilization view
CREATE OR REPLACE VIEW vw_warehouse_utilization AS
SELECT
    w.Warehouse_ID, w.Warehouse_Name, w.Location,
    w.Capacity, w.Utilization_Pct, w.Available_Capacity, w.Utilization_Status,
    COUNT(p.Product_ID)    AS Product_Count,
    SUM(i.Current_Stock)   AS Total_Stock,
    SUM(i.Inventory_Value) AS Total_Inventory_Value,
    COUNT(CASE WHEN i.Stock_Status='Out of Stock' THEN 1 END) AS Stock_Out_Products,
    COUNT(CASE WHEN i.Stock_Status='Overstock'    THEN 1 END) AS Overstock_Products
FROM dim_warehouses w
LEFT JOIN dim_products   p ON w.Warehouse_ID = p.Warehouse_ID
LEFT JOIN fact_inventory i ON p.Product_ID   = i.Product_ID
GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Location,
         w.Capacity, w.Utilization_Pct, w.Available_Capacity, w.Utilization_Status;

-- Customer order summary view
CREATE OR REPLACE VIEW vw_customer_summary AS
SELECT
    c.Customer_ID, c.Customer_Name, c.Company,
    c.Customer_Segment, c.Country, c.Region,
    COUNT(o.Order_ID)                         AS Total_Orders,
    ROUND(SUM(o.Revenue), 2)                  AS Lifetime_Revenue,
    ROUND(AVG(o.Revenue), 2)                  AS Avg_Order_Value,
    MIN(o.Order_Date)                         AS First_Order_Date,
    MAX(o.Order_Date)                         AS Last_Order_Date
FROM dim_customers c
LEFT JOIN fact_orders o ON c.Customer_ID = o.Customer_ID
                       AND o.Order_Status != 'Cancelled'
GROUP BY c.Customer_ID, c.Customer_Name, c.Company,
         c.Customer_Segment, c.Country, c.Region;

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

DROP PROCEDURE IF EXISTS sp_monthly_kpi_snapshot;
DELIMITER $$
CREATE PROCEDURE sp_monthly_kpi_snapshot(IN p_year INT, IN p_month INT)
BEGIN
    SELECT
        p_year AS Report_Year, p_month AS Report_Month,
        COUNT(Order_ID)                                          AS Total_Orders,
        ROUND(SUM(Revenue), 2)                                   AS Total_Revenue,
        ROUND(SUM(Gross_Profit), 2)                              AS Gross_Profit,
        ROUND(SUM(Gross_Profit)/NULLIF(SUM(Revenue),0)*100, 2)  AS Gross_Margin_Pct,
        ROUND(AVG(Revenue), 2)                                   AS Avg_Order_Value,
        COUNT(DISTINCT Customer_ID)                              AS Unique_Customers
    FROM fact_orders
    WHERE Year = p_year AND Month = p_month AND Order_Status != 'Cancelled';
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_inventory_turnover;
DELIMITER $$
CREATE PROCEDURE sp_inventory_turnover(IN p_year INT)
BEGIN
    DECLARE total_cogs    DECIMAL(18,2);
    DECLARE total_inv_val DECIMAL(18,2);

    SELECT COALESCE(SUM(COGS), 0)          INTO total_cogs
    FROM fact_orders
    WHERE Year = p_year AND Order_Status != 'Cancelled';

    SELECT COALESCE(SUM(Inventory_Value), 1) INTO total_inv_val
    FROM fact_inventory;

    SELECT
        p_year                                          AS Year,
        ROUND(total_cogs, 2)                           AS Annual_COGS,
        ROUND(total_inv_val, 2)                        AS Inventory_Value,
        ROUND(total_cogs / total_inv_val, 4)           AS Inventory_Turnover_Ratio,
        ROUND(365 / (total_cogs / total_inv_val), 1)   AS Days_Inventory_Outstanding;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_supplier_performance;
DELIMITER $$
CREATE PROCEDURE sp_supplier_performance(IN p_supplier_id VARCHAR(10))
BEGIN
    SELECT
        s.Supplier_ID, s.Supplier_Name, s.Reliability_Score, s.Lead_Time,
        COUNT(l.Shipment_ID)                     AS Total_Shipments,
        SUM(l.Is_Delayed)                        AS Delayed_Count,
        ROUND((1-AVG(l.Is_Delayed))*100, 2)      AS On_Time_Pct,
        ROUND(AVG(l.Transit_Time), 1)            AS Avg_Transit_Days,
        ROUND(SUM(l.Transport_Cost), 2)          AS Total_Spend
    FROM dim_suppliers s
    LEFT JOIN fact_logistics l ON s.Supplier_ID = l.Supplier_ID
    WHERE s.Supplier_ID = p_supplier_id
    GROUP BY s.Supplier_ID, s.Supplier_Name, s.Reliability_Score, s.Lead_Time;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_reorder_alerts;
DELIMITER $$
CREATE PROCEDURE sp_reorder_alerts()
BEGIN
    SELECT
        p.Product_ID, p.Product_Name, p.Category,
        i.Current_Stock, p.Safety_Stock, p.Reorder_Point,
        i.Stock_Status,
        p.Supplier_ID, s.Supplier_Name, s.Lead_Time,
        w.Warehouse_Name
    FROM fact_inventory i
    JOIN dim_products   p ON i.Product_ID  = p.Product_ID
    JOIN dim_suppliers  s ON p.Supplier_ID = s.Supplier_ID
    JOIN dim_warehouses w ON p.Warehouse_ID = w.Warehouse_ID
    WHERE i.Stock_Status IN ('Out of Stock','Low Stock')
    ORDER BY i.Current_Stock ASC;
END$$
DELIMITER ;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'SupplyVision schema created successfully.' AS status;
