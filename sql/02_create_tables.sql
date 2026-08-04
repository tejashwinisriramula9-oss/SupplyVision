-- SupplyVision – DDL: Create All Tables
-- Dimension tables first, then fact tables (FK dependencies)

USE supply_vision;

SET FOREIGN_KEY_CHECKS = 0;

-- ─── Dimension: Warehouses ────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_warehouses;
CREATE TABLE dim_warehouses (
    Warehouse_ID        VARCHAR(10)  NOT NULL,
    Warehouse_Name      VARCHAR(100) NOT NULL,
    Capacity            INT          NOT NULL DEFAULT 0,
    Utilization         FLOAT        NOT NULL DEFAULT 0,
    Available_Capacity  INT          NOT NULL DEFAULT 0,
    Utilization_Pct     FLOAT        NOT NULL DEFAULT 0,
    Utilization_Status  VARCHAR(20),
    Location            VARCHAR(100),
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Warehouse_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Warehouse dimension – capacity and utilization';

-- ─── Dimension: Suppliers ────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_suppliers;
CREATE TABLE dim_suppliers (
    Supplier_ID         VARCHAR(10)  NOT NULL,
    Supplier_Name       VARCHAR(150) NOT NULL,
    Country             VARCHAR(100),
    Region              VARCHAR(50),
    Lead_Time           INT          NOT NULL DEFAULT 14,
    Reliability_Score   FLOAT        NOT NULL DEFAULT 0.75,
    Reliability_Tier    VARCHAR(20),
    Lead_Time_Category  VARCHAR(20),
    Supplier_Cost       DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    Contact_Email       VARCHAR(150),
    Phone               VARCHAR(50),
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Supplier_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Supplier dimension – reliability and cost';

-- ─── Dimension: Products ─────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_products;
CREATE TABLE dim_products (
    Product_ID      VARCHAR(10)  NOT NULL,
    Product_Name    VARCHAR(150) NOT NULL,
    Category        VARCHAR(50)  NOT NULL,
    Safety_Stock    INT          NOT NULL DEFAULT 0,
    Reorder_Point   INT          NOT NULL DEFAULT 0,
    Unit_Cost       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Unit_Price      DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Margin_Pct      FLOAT,
    Warehouse_ID    VARCHAR(10),
    Supplier_ID     VARCHAR(10),
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Product_ID),
    INDEX idx_category (Category),
    INDEX idx_warehouse (Warehouse_ID),
    INDEX idx_supplier  (Supplier_ID),
    CONSTRAINT fk_product_warehouse FOREIGN KEY (Warehouse_ID)
        REFERENCES dim_warehouses(Warehouse_ID) ON DELETE SET NULL,
    CONSTRAINT fk_product_supplier  FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Product/SKU dimension';

-- ─── Fact: Inventory Snapshot ────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_inventory;
CREATE TABLE fact_inventory (
    Product_ID       VARCHAR(10)   NOT NULL,
    Current_Stock    INT           NOT NULL DEFAULT 0,
    Inventory_Value  DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    Stock_Status     VARCHAR(20),
    Last_Updated     DATE,
    snapshot_date    DATE          DEFAULT (CURRENT_DATE),
    PRIMARY KEY (Product_ID),
    CONSTRAINT fk_inv_product FOREIGN KEY (Product_ID)
        REFERENCES dim_products(Product_ID) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Current inventory levels and valuation';

-- ─── Fact: Orders ────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders (
    Order_ID              VARCHAR(12)   NOT NULL,
    Product_ID            VARCHAR(10),
    Customer_ID           VARCHAR(12),
    Order_Date            DATE          NOT NULL,
    Year                  SMALLINT      NOT NULL,
    Month                 TINYINT       NOT NULL,
    Quarter               TINYINT       NOT NULL,
    YearMonth             VARCHAR(10),
    YearQuarter           VARCHAR(12),
    WeekOfYear            TINYINT,
    DayOfWeek             VARCHAR(12),
    Quantity              INT           NOT NULL DEFAULT 1,
    Unit_Price            DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Discount              FLOAT         NOT NULL DEFAULT 0,
    Revenue               DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    COGS                  DECIMAL(14,2),
    Gross_Profit          DECIMAL(14,2),
    Gross_Margin_Pct      FLOAT,
    Order_Status          VARCHAR(20),
    Sales_Channel         VARCHAR(30),
    Category              VARCHAR(50),
    Warehouse_ID          VARCHAR(10),
    Supplier_ID           VARCHAR(10),
    Shipment_Count        INT           DEFAULT 0,
    Avg_Transit_Time      FLOAT,
    Total_Transport_Cost  DECIMAL(14,2),
    Delayed_Shipments     INT           DEFAULT 0,
    PRIMARY KEY (Order_ID),
    INDEX idx_order_date    (Order_Date),
    INDEX idx_order_year    (Year),
    INDEX idx_order_product (Product_ID),
    INDEX idx_order_status  (Order_Status),
    INDEX idx_order_channel (Sales_Channel),
    CONSTRAINT fk_order_product   FOREIGN KEY (Product_ID)
        REFERENCES dim_products(Product_ID) ON DELETE SET NULL,
    CONSTRAINT fk_order_warehouse FOREIGN KEY (Warehouse_ID)
        REFERENCES dim_warehouses(Warehouse_ID) ON DELETE SET NULL,
    CONSTRAINT fk_order_supplier  FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Order transactions fact table';

-- ─── Fact: Logistics / Shipments ─────────────────────────────────────────────
DROP TABLE IF EXISTS fact_logistics;
CREATE TABLE fact_logistics (
    Shipment_ID              VARCHAR(12)   NOT NULL,
    Order_ID                 VARCHAR(12),
    Supplier_ID              VARCHAR(10),
    Ship_Date                DATE          NOT NULL,
    Delivery_Date            DATE,
    Expected_Transit_Days    INT,
    Transit_Time             INT,
    Delay_Days               INT           DEFAULT 0,
    Is_Delayed               TINYINT(1)    DEFAULT 0,
    Transport_Cost           DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    Cost_Per_KG              DECIMAL(10,2),
    Carrier                  VARCHAR(50),
    Delivery_Status          VARCHAR(20),
    Origin_Country           VARCHAR(100),
    Destination_Country      VARCHAR(100),
    Weight_KG                FLOAT,
    Ship_Year                SMALLINT,
    Ship_Month               TINYINT,
    Ship_Quarter             TINYINT,
    Ship_YearMonth           VARCHAR(10),
    PRIMARY KEY (Shipment_ID),
    INDEX idx_ship_date     (Ship_Date),
    INDEX idx_carrier       (Carrier),
    INDEX idx_delayed       (Is_Delayed),
    INDEX idx_ship_supplier (Supplier_ID),
    CONSTRAINT fk_logistics_supplier FOREIGN KEY (Supplier_ID)
        REFERENCES dim_suppliers(Supplier_ID) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Shipment and logistics fact table';

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'All tables created successfully.' AS status;
