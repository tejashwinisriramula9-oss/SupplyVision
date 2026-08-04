# SupplyVision – DAX Measures & KPIs
## Power BI Implementation Guide

All measures belong to a dedicated `_Measures` table for clean organisation.
Apply the **Dark Blue / White / Light Gray** theme (hex: #0A2342 / #FFFFFF / #F2F4F7).

---

## 1. Executive Overview Measures

### Total Revenue
```dax
Total Revenue =
CALCULATE(
    SUMX(
        FILTER(fact_orders, fact_orders[Order_Status] <> "Cancelled"),
        fact_orders[Revenue]
    )
)
```

### Total Orders
```dax
Total Orders =
CALCULATE(
    COUNTROWS(fact_orders),
    fact_orders[Order_Status] <> "Cancelled"
)
```

### Total Inventory Value
```dax
Total Inventory Value =
SUMX(fact_inventory, fact_inventory[Inventory_Value])
```

### Gross Margin %
```dax
Gross Margin % =
DIVIDE(
    CALCULATE(SUM(fact_orders[Gross_Profit]), fact_orders[Order_Status] <> "Cancelled"),
    CALCULATE(SUM(fact_orders[Revenue]),      fact_orders[Order_Status] <> "Cancelled"),
    0
) * 100
```

### Average Order Value
```dax
Average Order Value =
DIVIDE([Total Revenue], [Total Orders], 0)
```

### Cancelled Order % 
```dax
Cancelled Order % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_orders), fact_orders[Order_Status] = "Cancelled"),
    COUNTROWS(fact_orders),
    0
) * 100
```

### Revenue MoM Growth %
```dax
Revenue MoM Growth % =
VAR CurrentMonthRev  = [Total Revenue]
VAR PrevMonthRev     = CALCULATE([Total Revenue], DATEADD(dim_date[Date], -1, MONTH))
RETURN
    DIVIDE(CurrentMonthRev - PrevMonthRev, PrevMonthRev, 0) * 100
```

### Revenue YoY Growth %
```dax
Revenue YoY Growth % =
VAR CY = [Total Revenue]
VAR PY = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[Date]))
RETURN DIVIDE(CY - PY, PY, 0) * 100
```

---

## 2. Inventory Intelligence Measures

### Inventory Turnover Ratio
```dax
Inventory Turnover Ratio =
DIVIDE(
    CALCULATE(SUM(fact_orders[COGS]), fact_orders[Order_Status] <> "Cancelled"),
    [Total Inventory Value],
    0
)
```

### Days Inventory Outstanding (DIO)
```dax
Days Inventory Outstanding =
DIVIDE(365, [Inventory Turnover Ratio], 0)
```

### Fill Rate %
```dax
Fill Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_inventory), fact_inventory[Stock_Status] <> "Out of Stock"),
    COUNTROWS(fact_inventory),
    0
) * 100
```

### Stock-Out Rate %
```dax
Stock-Out Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_inventory), fact_inventory[Stock_Status] = "Out of Stock"),
    COUNTROWS(fact_inventory),
    0
) * 100
```

### Overstock Rate %
```dax
Overstock Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_inventory), fact_inventory[Stock_Status] = "Overstock"),
    COUNTROWS(fact_inventory),
    0
) * 100
```

### Current Stock Total
```dax
Current Stock Total =
SUM(fact_inventory[Current_Stock])
```

### Safety Stock Total
```dax
Safety Stock Total =
SUM(dim_products[Safety_Stock])
```

### Low Stock Alert Count
```dax
Low Stock Alert Count =
CALCULATE(
    COUNTROWS(fact_inventory),
    fact_inventory[Stock_Status] IN {"Low Stock", "Out of Stock"}
)
```

---

## 3. Logistics Analytics Measures

### On-Time Delivery %
```dax
On-Time Delivery % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 0),
    COUNTROWS(fact_logistics),
    0
) * 100
```

### Delayed Deliveries Count
```dax
Delayed Deliveries =
CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 1)
```

### Average Transit Time (Days)
```dax
Avg Transit Time =
AVERAGEX(fact_logistics, fact_logistics[Transit_Time])
```

### Average Delay Days
```dax
Avg Delay Days =
CALCULATE(
    AVERAGEX(fact_logistics, fact_logistics[Delay_Days]),
    fact_logistics[Is_Delayed] = 1
)
```

### Total Transport Cost
```dax
Total Transport Cost =
SUM(fact_logistics[Transport_Cost])
```

### Transport Cost per Shipment
```dax
Transport Cost per Shipment =
DIVIDE([Total Transport Cost], COUNTROWS(fact_logistics), 0)
```

### Delivery Performance Status (KPI indicator)
```dax
Delivery Performance Status =
SWITCH(
    TRUE(),
    [On-Time Delivery %] >= 95, "Excellent",
    [On-Time Delivery %] >= 85, "Good",
    [On-Time Delivery %] >= 75, "Acceptable",
    "Poor"
)
```

---

## 4. Supplier Analytics Measures

### Supplier Reliability %
```dax
Supplier Reliability % =
AVERAGEX(dim_suppliers, dim_suppliers[Reliability_Score]) * 100
```

### Average Lead Time (Days)
```dax
Average Lead Time =
AVERAGEX(dim_suppliers, dim_suppliers[Lead_Time])
```

### Delivery Reliability % (from logistics)
```dax
Delivery Reliability % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 0),
    COUNTROWS(fact_logistics),
    0
) * 100
```

### Total Supplier Purchase Cost
```dax
Total Supplier Cost =
SUM(dim_suppliers[Supplier_Cost])
```

### Excellent Supplier Count
```dax
Excellent Supplier Count =
CALCULATE(COUNTROWS(dim_suppliers), dim_suppliers[Reliability_Tier] = "Excellent")
```

### Poor Supplier Count
```dax
Poor Supplier Count =
CALCULATE(COUNTROWS(dim_suppliers), dim_suppliers[Reliability_Tier] = "Poor")
```

---

## 5. Forecasting Measures

### Demand Forecast Accuracy %
```dax
Forecast Accuracy % =
VAR MAPE =
    AVERAGEX(
        forecast_results,
        ABS(forecast_results[Actual] - forecast_results[Forecast])
            / MAX(forecast_results[Actual], 1)
    ) * 100
RETURN MAX(0, 100 - MAPE)
```

---

## 6. Dynamic Titles (for slicers)

### Selected Year Title
```dax
Selected Year Title =
"FY " & SELECTEDVALUE(dim_date[Year], "All Years")
```

### Dashboard Sub-Title
```dax
Dashboard Subtitle =
"Last Updated: " & FORMAT(TODAY(), "DD MMM YYYY")
    & "  |  Period: " & SELECTEDVALUE(dim_date[YearMonth], "All Periods")
```

---

## Power Query (M) – Date Dimension

```m
let
    StartDate   = #date(2022, 1, 1),
    EndDate     = #date(2024, 12, 31),
    DayCount    = Duration.Days(EndDate - StartDate) + 1,
    Source      = List.Dates(StartDate, DayCount, #duration(1,0,0,0)),
    TableFromList = Table.FromList(Source, Splitter.SplitByNothing()),
    DateCol     = Table.RenameColumns(TableFromList, {{"Column1", "Date"}}),
    TypeDate    = Table.TransformColumnTypes(DateCol, {{"Date", type date}}),
    AddYear     = Table.AddColumn(TypeDate,  "Year",    each Date.Year([Date]),    Int64.Type),
    AddMonth    = Table.AddColumn(AddYear,   "Month",   each Date.Month([Date]),   Int64.Type),
    AddDay      = Table.AddColumn(AddMonth,  "Day",     each Date.Day([Date]),     Int64.Type),
    AddQtr      = Table.AddColumn(AddDay,    "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddMonthNm  = Table.AddColumn(AddQtr,    "Month Name", each Date.MonthName([Date]), type text),
    AddDayNm    = Table.AddColumn(AddMonthNm,"Day Name",   each Date.DayOfWeekName([Date]), type text),
    AddYM       = Table.AddColumn(AddDayNm,  "YearMonth",  each Text.From([Year]) & "-" & Text.PadStart(Text.From([Month]),2,"0"), type text),
    AddYQ       = Table.AddColumn(AddYM,     "YearQuarter", each Text.From([Year]) & " " & [Quarter], type text),
    AddWkNum    = Table.AddColumn(AddYQ,     "WeekNumber", each Date.WeekOfYear([Date]), Int64.Type),
    AddIsWkEnd  = Table.AddColumn(AddWkNum,  "IsWeekend",  each Date.DayOfWeek([Date]) >= 5, type logical)
in
    AddIsWkEnd
```

---

## Dashboard Design Specifications

### Color Palette
| Token            | Hex Code  | Usage                          |
|------------------|-----------|--------------------------------|
| Primary Dark     | `#0A2342` | Headers, nav bar, KPI labels   |
| Secondary Blue   | `#1A5276` | Charts, accent elements        |
| Accent Blue      | `#2E86C1` | Active slicers, highlights     |
| Light Gray       | `#F2F4F7` | Card backgrounds, page canvas  |
| White            | `#FFFFFF` | Visual backgrounds             |
| Success Green    | `#1E8449` | Positive KPI indicators        |
| Warning Amber    | `#F39C12` | Threshold alerts               |
| Danger Red       | `#C0392B` | Negative KPIs, stock-out alerts|

### Layout Guidelines
- Canvas size: **1920 × 1080** (16:9 widescreen)
- Page navigator: vertical left panel, 200 px wide
- KPI cards: top row, 6 across, uniform height 120 px
- Main visual area: 2 rows × 2 columns grid below KPI row
- Slicers: Year, Quarter, Category, Supplier in top-right header strip
- Drill-through: right-click any product → Product Detail page
- Bookmarks: Default view / YTD view / Executive Print view
- Tooltips: custom pages showing trend sparkline on hover

### Navigation Pages
1. 🏠 Executive Overview
2. 📦 Inventory Intelligence
3. 🚚 Logistics Analytics
4. 🤝 Supplier Analytics
5. 🔮 Forecasting & Predictions
6. ⚙️ Data Model (hidden – for development)
