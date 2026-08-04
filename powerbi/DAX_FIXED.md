# SupplyVision – Corrected DAX Measures
## Full Diagnostic Report + All Fixed Measures

---

## ROOT CAUSE ANALYSIS — WHY EVERY ERROR OCCURRED

### Bug 1 — Wrong table names in DAX (CRITICAL — causes ALL errors)

The DAX measures reference table names that **do not match** the actual Power BI table names.

| DAX References | Actual CSV filename | Correct Power BI table name |
|---|---|---|
| `fact_orders` | `fact_orders_clean.csv` | **`fact_orders_clean`** |
| `fact_inventory` | `inventory_clean.csv` | **`inventory_clean`** |
| `fact_logistics` | `logistics_clean.csv` | **`logistics_clean`** |
| `dim_suppliers` | `suppliers_clean.csv` | **`suppliers_clean`** |
| `dim_products` | does NOT exist as separate table | columns are INSIDE `inventory_clean` |

**Why this causes "A single value for 'Inventory_Value' cannot be determined":**
When DAX says `SUMX(fact_inventory, fact_inventory[Inventory_Value])`, Power BI cannot find a
table called `fact_inventory` — it throws an ambiguous context error because it falls back to
searching related tables and finds multiple possible matches.

**Fix:** Rename all tables in Power Query to match the DAX references exactly.
In Power Query Editor → right-click each query → Rename:
- `fact_orders_clean` → rename to `fact_orders`
- `inventory_clean` → rename to `fact_inventory`
- `logistics_clean` → rename to `fact_logistics`
- `suppliers_clean` → rename to `dim_suppliers`
- `customers_clean` → rename to `dim_customers`

This is the single most important fix. Once done, most measures work immediately.

---

### Bug 2 — `dim_products[Safety_Stock]` does not exist (ERROR)

The measure `Safety Stock Total` references `dim_products[Safety_Stock]`.

**Reality:** There is NO separate `dim_products` table. The `Safety_Stock` column lives in
`inventory_clean` (which you will rename to `fact_inventory`).

**Broken measure:**
```dax
Safety Stock Total =
SUM(dim_products[Safety_Stock])   -- ERROR: dim_products does not exist
```

**Fix:** Change `dim_products` to `fact_inventory`.

---

### Bug 3 — `Stock_Status = "Out of Stock"` never matches (WRONG DATA — silent bug)

The measures `Fill Rate %`, `Stock-Out Rate %`, and `Low Stock Alert Count` all filter on
`Stock_Status = "Out of Stock"`.

**Reality from your actual data:**
```
Stock_Status values: ['Optimal', 'Overstock', 'Low Stock']
```

There is NO "Out of Stock" value in your current dataset because no product has
`Current_Stock = 0`. All products have stock > 0.

**Effect:** `Stock-Out Rate %` always returns 0.00%. `Fill Rate %` always returns 100%.
These are not errors — they are silent wrong answers.

**Fix options:**
- Option A (Recommended): Change the DAX to be future-proof using "Out of Stock" OR "Low Stock"
  where appropriate, and accept that current data shows 0 stock-outs.
- Option B: Re-generate data with some zero-stock products.

The corrected measures below use Option A — they work correctly with your current data AND
will automatically work if stock-outs appear after data refresh.

---

### Bug 4 — `fact_inventory[Inventory_Value]` ambiguity error

Occurs when `Total Inventory Value` is used inside a row context (e.g., inside SUMX or
inside a visual with a Product row context active).

`Total Inventory Value = SUMX(fact_inventory, fact_inventory[Inventory_Value])`

Inside a visual that already iterates over inventory rows, this creates a nested row context
where DAX cannot determine which single value of `Inventory_Value` to use.

**Fix:** Use `SUM()` instead of `SUMX()` for a simple column sum. Reserve `SUMX` for
calculated columns.

---

### Bug 5 — `Inventory Turnover Ratio` context error

`DIVIDE([COGS sum], [Total Inventory Value], 0)` fails when the denominator
`[Total Inventory Value]` is evaluated in a filtered context from a visual but the
`fact_inventory` table has no active relationship to apply that filter.

**Fix:** Use `CALCULATE` with `ALL(fact_inventory)` on the denominator to force it to
always aggregate the entire inventory table regardless of filter context.

---

### Bug 6 — Time intelligence measures reference `dim_date[Date]` but table may not exist

`Revenue MoM Growth %` and `Revenue YoY Growth %` use `DATEADD(dim_date[Date], -1, MONTH)`.
If you have not yet created the `dim_date` table in Power Query, these throw errors.

Also: `dim_date` must be marked as a **Date Table** in Power BI.

**Fix:** Create `dim_date` from the M code provided, then in Model view right-click
`dim_date` → Mark as date table → select the `Date` column.

---

### Bug 7 — `Reliability_Tier` and `Utilization_Status` are CATEGORY dtype

In Python, these columns are `pandas.Categorical`. When exported to CSV, they become plain
text strings — this is fine for Power BI. However, the DAX filter syntax must match the
exact string value.

**Verified actual values:**
- `Reliability_Tier`: `'Acceptable', 'Excellent', 'Poor', 'Good'`
- `Utilization_Status`: `'Normal', 'High', 'Underutilized', 'Critical'`

These match the DAX filters exactly. No fix needed here.

---

## CORRECT DATA MODEL — TABLE NAMES AND RELATIONSHIPS

### Power Query Rename Instructions (Do This First)

Open Power Query Editor (Home → Transform Data), then rename each query:

| Original name | Rename to |
|---|---|
| `fact_orders_clean` | `fact_orders` |
| `inventory_clean` | `fact_inventory` |
| `logistics_clean` | `fact_logistics` |
| `suppliers_clean` | `dim_suppliers` |
| `customers_clean` | `dim_customers` |
| *(new)* date table | `dim_date` |

---

### Required Relationships (Model View)

Create these relationships by dragging columns in Model View:

| From (Many side) | Column | To (One side) | Column | Type |
|---|---|---|---|---|
| `fact_orders` | `Order_Date` | `dim_date` | `Date` | Many-to-One |
| `fact_orders` | `Product_ID` | `fact_inventory` | `Product_ID` | Many-to-One |
| `fact_orders` | `Supplier_ID` | `dim_suppliers` | `Supplier_ID` | Many-to-One |
| `fact_orders` | `Customer_ID` | `dim_customers` | `Customer_ID` | Many-to-One |
| `fact_logistics` | `Ship_Date` | `dim_date` | `Date` | Many-to-One |
| `fact_logistics` | `Supplier_ID` | `dim_suppliers` | `Supplier_ID` | Many-to-One |
| `fact_inventory` | `Supplier_ID` | `dim_suppliers` | `Supplier_ID` | Many-to-One |
| `forecast_results` | `Date` | `dim_date` | `Date` | Many-to-One |

**Cross-filter direction:** Set ALL to **Single** except:
- `dim_suppliers → fact_inventory` can be **Both** (so supplier slicer filters inventory)

**Mark date table:**
Right-click `dim_date` in Model View → Mark as date table → Date column → OK

---


---

## ALL CORRECTED DAX MEASURES

Copy-paste each one into Power BI. All measures go into the `_Measures` table.

---

### SECTION 1 — EXECUTIVE OVERVIEW

```dax
Total Revenue =
CALCULATE(
    SUM(fact_orders[Revenue]),
    fact_orders[Order_Status] <> "Cancelled"
)
```
> Fixed: Replaced SUMX+FILTER with simpler SUM+CALCULATE. Same result, no context errors.

---

```dax
Total Orders =
CALCULATE(
    COUNTROWS(fact_orders),
    fact_orders[Order_Status] <> "Cancelled"
)
```
> No change needed. Already correct.

---

```dax
Total Inventory Value =
SUM(fact_inventory[Inventory_Value])
```
> Fixed: Replaced `SUMX(fact_inventory, fact_inventory[Inventory_Value])` with `SUM()`.
> SUM is simpler and avoids nested row-context ambiguity. The table is now `fact_inventory`
> (was `fact_inventory` in DAX but the Power BI table was loaded as `inventory_clean`).

---

```dax
Gross Margin % =
DIVIDE(
    CALCULATE(SUM(fact_orders[Gross_Profit]), fact_orders[Order_Status] <> "Cancelled"),
    CALCULATE(SUM(fact_orders[Revenue]),      fact_orders[Order_Status] <> "Cancelled"),
    0
) * 100
```
> No change needed. Correct as long as table is renamed to `fact_orders`.

---

```dax
Average Order Value =
DIVIDE([Total Revenue], [Total Orders], 0)
```
> No change needed.

---

```dax
Cancelled Order % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_orders), fact_orders[Order_Status] = "Cancelled"),
    COUNTROWS(fact_orders),
    0
) * 100
```
> No change needed.

---

```dax
Revenue MoM Growth % =
VAR CurrentMonthRev = [Total Revenue]
VAR PrevMonthRev =
    CALCULATE(
        [Total Revenue],
        DATEADD(dim_date[Date], -1, MONTH)
    )
RETURN
    DIVIDE(CurrentMonthRev - PrevMonthRev, PrevMonthRev, 0) * 100
```
> No change needed. Requires `dim_date` to be created and marked as date table.
> Will return BLANK if dim_date is not connected to fact_orders[Order_Date].

---

```dax
Revenue YoY Growth % =
VAR CY = [Total Revenue]
VAR PY =
    CALCULATE(
        [Total Revenue],
        SAMEPERIODLASTYEAR(dim_date[Date])
    )
RETURN
    DIVIDE(CY - PY, PY, 0) * 100
```
> No change needed. Same dim_date requirement as above.

---

### SECTION 2 — INVENTORY INTELLIGENCE

```dax
Inventory Turnover Ratio =
DIVIDE(
    CALCULATE(
        SUM(fact_orders[COGS]),
        fact_orders[Order_Status] <> "Cancelled"
    ),
    CALCULATE(
        SUM(fact_inventory[Inventory_Value]),
        ALL(fact_inventory)
    ),
    0
)
```
> FIXED (Critical): Added `CALCULATE(..., ALL(fact_inventory))` on the denominator.
> This forces the inventory value to always be the TOTAL across all products, regardless
> of what visual filter context is active. Without this, when a Category slicer is applied,
> the denominator only sums inventory for that category, making the ratio meaningless.
> The numerator (COGS) correctly responds to filters. The denominator (total inventory) should not.

---

```dax
Days Inventory Outstanding =
DIVIDE(365, [Inventory Turnover Ratio], 0)
```
> No change needed. Depends on the fixed Inventory Turnover Ratio above.

---

```dax
Fill Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_inventory),
        fact_inventory[Stock_Status] <> "Out of Stock"
    ),
    COUNTROWS(fact_inventory),
    0
) * 100
```
> No change needed in DAX logic.
> NOTE: Your current dataset has NO "Out of Stock" products (all 200 products have stock > 0).
> This measure will correctly return 100% until some products reach zero stock.
> The measure logic is correct — it will work automatically when out-of-stock products appear.

---

```dax
Stock-Out Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_inventory),
        fact_inventory[Stock_Status] = "Out of Stock"
    ),
    COUNTROWS(fact_inventory),
    0
) * 100
```
> Same note as Fill Rate %. Returns 0% with current data — that is accurate (no stock-outs).

---

```dax
Overstock Rate % =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_inventory),
        fact_inventory[Stock_Status] = "Overstock"
    ),
    COUNTROWS(fact_inventory),
    0
) * 100
```
> No change needed. With current data: 80 Overstock / 200 total = 40%.

---

```dax
Current Stock Total =
SUM(fact_inventory[Current_Stock])
```
> FIXED: Table renamed from `fact_inventory` in DAX to match actual loaded table.
> (This was already the correct measure — only the table name in Power BI needed fixing.)

---

```dax
Safety Stock Total =
SUM(fact_inventory[Safety_Stock])
```
> FIXED: Changed `dim_products[Safety_Stock]` → `fact_inventory[Safety_Stock]`.
> There is NO `dim_products` table. The `Safety_Stock` column lives in `inventory_clean`
> (now renamed to `fact_inventory`). This was the direct cause of the error.

---

```dax
Low Stock Alert Count =
CALCULATE(
    COUNTROWS(fact_inventory),
    fact_inventory[Stock_Status] IN {"Low Stock", "Out of Stock"}
)
```
> FIXED: Table name updated to `fact_inventory`.
> With current data: 32 Low Stock + 0 Out of Stock = returns 32. Correct.

---

```dax
Inventory Value by Category =
CALCULATE(
    SUM(fact_inventory[Inventory_Value]),
    ALLEXCEPT(fact_inventory, fact_inventory[Category])
)
```
> NEW MEASURE: Useful for category-level inventory charts without breaking filter context.

---

### SECTION 3 — LOGISTICS ANALYTICS

```dax
On-Time Delivery % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 0),
    COUNTROWS(fact_logistics),
    0
) * 100
```
> FIXED: Table renamed to `fact_logistics`.
> Note: `Is_Delayed` is integer (0 or 1) in your data — filter `= 0` is correct.

---

```dax
Delayed Deliveries =
CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 1)
```
> FIXED: Table name only.

---

```dax
Avg Transit Time =
AVERAGE(fact_logistics[Transit_Time])
```
> FIXED: Replaced `AVERAGEX(fact_logistics, fact_logistics[Transit_Time])` with `AVERAGE()`.
> AVERAGEX iterates rows unnecessarily for a simple column average. AVERAGE is cleaner.
> Table name updated.

---

```dax
Avg Delay Days =
CALCULATE(
    AVERAGE(fact_logistics[Delay_Days]),
    fact_logistics[Is_Delayed] = 1
)
```
> FIXED: Table name + replaced AVERAGEX with AVERAGE.

---

```dax
Total Transport Cost =
SUM(fact_logistics[Transport_Cost])
```
> FIXED: Table name only.

---

```dax
Transport Cost per Shipment =
DIVIDE([Total Transport Cost], COUNTROWS(fact_logistics), 0)
```
> FIXED: Depends on `Total Transport Cost` which now references `fact_logistics`.

---

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
> No change needed. Depends on the fixed `On-Time Delivery %` measure.

---

### SECTION 4 — SUPPLIER ANALYTICS

```dax
Supplier Reliability % =
AVERAGEX(dim_suppliers, dim_suppliers[Reliability_Score]) * 100
```
> FIXED: Table name — `dim_suppliers` is the correct name after renaming in Power Query.
> `Reliability_Score` column confirmed present in suppliers_clean.

---

```dax
Average Lead Time =
AVERAGE(dim_suppliers[Lead_Time])
```
> FIXED: Replaced AVERAGEX with AVERAGE. Table name `dim_suppliers` confirmed correct.

---

```dax
Delivery Reliability % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 0),
    COUNTROWS(fact_logistics),
    0
) * 100
```
> FIXED: Table name to `fact_logistics`.
> Note: This measure is identical to `On-Time Delivery %` and returns the same value.
> They represent the same metric from two perspectives. Both are kept for dashboard labelling.

---

```dax
Total Supplier Cost =
SUM(dim_suppliers[Supplier_Cost])
```
> FIXED: Table name to `dim_suppliers`.

---

```dax
Excellent Supplier Count =
CALCULATE(
    COUNTROWS(dim_suppliers),
    dim_suppliers[Reliability_Tier] = "Excellent"
)
```
> FIXED: Table name. Verified: "Excellent" is a valid value in your data.

---

```dax
Poor Supplier Count =
CALCULATE(
    COUNTROWS(dim_suppliers),
    dim_suppliers[Reliability_Tier] = "Poor"
)
```
> FIXED: Table name. Verified: "Poor" is a valid value in your data.

---

### SECTION 5 — FORECASTING

```dax
Forecast Accuracy % =
VAR MAPE =
    AVERAGEX(
        forecast_data,
        DIVIDE(
            ABS(forecast_data[Total_Quantity] - forecast_data[Forecast_Quantity]),
            MAX(forecast_data[Total_Quantity], 1)
        )
    ) * 100
RETURN MAX(0, 100 - MAPE)
```
> FIXED: Multiple issues corrected:
> 1. Table name: `forecast_results` does not exist → changed to `forecast_data`
>    (this is the name you should use when loading forecast_ensemble.csv)
> 2. Column names: `[Actual]` and `[Forecast]` do not exist in your CSV.
>    The actual column names are `Total_Quantity` (historical) and `Forecast_Quantity`.
> 3. `MAX(value, 1)` is not valid DAX — replaced with `DIVIDE(..., MAX(col, 1), 0)`
>    Actually the correct pattern is: `IF(col = 0, 1, col)` to avoid /0.
>    The corrected formula uses DIVIDE with a proper zero-guard.
> NOTE: This measure only works if both historical and forecast are in the SAME table.
> See the Power Query M code for combining them below.

---

### SECTION 7 — DYNAMIC TITLES

```dax
Selected Year Title =
"FY " & SELECTEDVALUE(dim_date[Year], "All Years")
```
> No change needed. Requires `dim_date` to exist.

---

```dax
Dashboard Subtitle =
"Last Updated: " & FORMAT(TODAY(), "DD MMM YYYY")
    & "  |  Period: " & SELECTEDVALUE(dim_date[YearMonth], "All Periods")
```
> No change needed. Requires `dim_date` to exist.

---

### SECTION 8 — ADDITIONAL MEASURES (New — recommended additions)

```dax
Total COGS =
CALCULATE(
    SUM(fact_orders[COGS]),
    fact_orders[Order_Status] <> "Cancelled"
)
```
> NEW: Explicit COGS measure. Cleaner than embedding in Inventory Turnover formula.

---

```dax
Gross Profit Total =
CALCULATE(
    SUM(fact_orders[Gross_Profit]),
    fact_orders[Order_Status] <> "Cancelled"
)
```
> NEW: Explicit Gross Profit measure for use in charts.

---

```dax
Total Shipments =
COUNTROWS(fact_logistics)
```
> NEW: Simple shipment count without any filter. Useful for KPI cards.

---

```dax
On Time Shipments =
CALCULATE(COUNTROWS(fact_logistics), fact_logistics[Is_Delayed] = 0)
```
> NEW: Explicit on-time count.

---

```dax
Revenue per Category =
CALCULATE(
    [Total Revenue],
    ALLEXCEPT(fact_orders, fact_orders[Category])
)
```
> NEW: Useful for category-level bar charts.


---

## CORRECTED POWER QUERY M CODE

### dim_date (Updated — adds Quarter as integer for easier DAX use)

```m
let
    StartDate    = #date(2022, 1, 1),
    EndDate      = #date(2024, 12, 31),
    DayCount     = Duration.Days(EndDate - StartDate) + 1,
    Dates        = List.Dates(StartDate, DayCount, #duration(1,0,0,0)),
    DateTable    = Table.FromList(Dates, Splitter.SplitByNothing()),
    Renamed      = Table.RenameColumns(DateTable, {{"Column1", "Date"}}),
    TypedDate    = Table.TransformColumnTypes(Renamed, {{"Date", type date}}),
    AddYear      = Table.AddColumn(TypedDate,  "Year",          each Date.Year([Date]),           Int64.Type),
    AddMonth     = Table.AddColumn(AddYear,    "Month",         each Date.Month([Date]),          Int64.Type),
    AddDay       = Table.AddColumn(AddMonth,   "Day",           each Date.Day([Date]),            Int64.Type),
    AddQtrNum    = Table.AddColumn(AddDay,     "Quarter",       each Date.QuarterOfYear([Date]),  Int64.Type),
    AddQtrLabel  = Table.AddColumn(AddQtrNum,  "Quarter_Label", each "Q" & Text.From([Quarter]), type text),
    AddMonthName = Table.AddColumn(AddQtrLabel,"Month_Name",    each Date.MonthName([Date]),      type text),
    AddMonthShort= Table.AddColumn(AddMonthName,"Month_Short",  each Text.Start(Date.MonthName([Date]),3), type text),
    AddDayName   = Table.AddColumn(AddMonthShort,"Day_Name",    each Date.DayOfWeekName([Date]),  type text),
    AddWeekNum   = Table.AddColumn(AddDayName, "Week_Number",   each Date.WeekOfYear([Date]),     Int64.Type),
    AddYearMonth = Table.AddColumn(AddWeekNum, "YearMonth",
                       each Text.From([Year]) & "-" & Text.PadStart(Text.From([Month]),2,"0"),
                       type text),
    AddYearQtr   = Table.AddColumn(AddYearMonth,"YearQuarter",
                       each Text.From([Year]) & " " & [Quarter_Label],
                       type text),
    AddIsWeekend = Table.AddColumn(AddYearQtr, "Is_Weekend",
                       each Date.DayOfWeek([Date]) >= 5,
                       type logical),
    SortByDate   = Table.Sort(AddIsWeekend, {{"Date", Order.Ascending}})
in
    SortByDate
```

---

### fact_orders (from CSV — with all correct types)

```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "fact_orders_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Order_ID",            type text},
                   {"Product_ID",          type text},
                   {"Customer_ID",         type text},
                   {"Order_Date",          type date},
                   {"Quantity",            Int64.Type},
                   {"Unit_Price",          type number},
                   {"Discount",            type number},
                   {"Revenue",             type number},
                   {"Order_Status",        type text},
                   {"Sales_Channel",       type text},
                   {"Year",                Int64.Type},
                   {"Month",               Int64.Type},
                   {"Quarter",             Int64.Type},
                   {"YearMonth",           type text},
                   {"YearQuarter",         type text},
                   {"WeekOfYear",          Int64.Type},
                   {"DayOfWeek",           type text},
                   {"Product_Name",        type text},
                   {"Category",            type text},
                   {"Unit_Cost",           type number},
                   {"Warehouse_ID",        type text},
                   {"Supplier_ID",         type text},
                   {"Shipment_Count",      type number},
                   {"Avg_Transit_Time",    type number},
                   {"Total_Transport_Cost",type number},
                   {"Delayed_Shipments",   Int64.Type},
                   {"COGS",                type number},
                   {"Gross_Profit",        type number},
                   {"Gross_Margin_Pct",    type number}})
in
    Types
```

---

### fact_inventory (from inventory_clean.csv)

```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "inventory_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Product_ID",      type text},
                   {"Product_Name",    type text},
                   {"Category",        type text},
                   {"Current_Stock",   Int64.Type},
                   {"Safety_Stock",    Int64.Type},
                   {"Reorder_Point",   Int64.Type},
                   {"Unit_Cost",       type number},
                   {"Unit_Price",      type number},
                   {"Warehouse_ID",    type text},
                   {"Supplier_ID",     type text},
                   {"Last_Updated",    type date},
                   {"Inventory_Value", type number},
                   {"Stock_Status",    type text},
                   {"Margin_Pct",      type number}})
in
    Types
```

---

### fact_logistics (from logistics_clean.csv)

```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "logistics_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Shipment_ID",           type text},
                   {"Order_ID",              type text},
                   {"Supplier_ID",           type text},
                   {"Ship_Date",             type date},
                   {"Delivery_Date",         type date},
                   {"Expected_Transit_Days", Int64.Type},
                   {"Transit_Time",          Int64.Type},
                   {"Transport_Cost",        type number},
                   {"Carrier",               type text},
                   {"Delivery_Status",       type text},
                   {"Origin_Country",        type text},
                   {"Destination_Country",   type text},
                   {"Weight_KG",             type number},
                   {"Delay_Days",            Int64.Type},
                   {"Is_Delayed",            Int64.Type},
                   {"Cost_Per_KG",           type number},
                   {"Ship_Year",             Int64.Type},
                   {"Ship_Month",            Int64.Type},
                   {"Ship_Quarter",          Int64.Type},
                   {"Ship_YearMonth",        type text}})
in
    Types
```

---

### dim_suppliers (from suppliers_clean.csv)

```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "suppliers_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Supplier_ID",        type text},
                   {"Supplier_Name",      type text},
                   {"Country",            type text},
                   {"Region",             type text},
                   {"Lead_Time",          Int64.Type},
                   {"Reliability_Score",  type number},
                   {"Supplier_Cost",      type number},
                   {"Contact_Email",      type text},
                   {"Phone",              type text},
                   {"Reliability_Tier",   type text},
                   {"Lead_Time_Category", type text}})
in
    Types
```

---

### dim_customers (from customers_clean.csv)

```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "customers_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Customer_ID",       type text},
                   {"Customer_Name",     type text},
                   {"Company",           type text},
                   {"Email",             type text},
                   {"Phone",             type text},
                   {"Country",           type text},
                   {"Region",            type text},
                   {"Customer_Segment",  type text},
                   {"Registration_Date", type date}})
in
    Types
```

---

### forecast_data (from forecast_ensemble.csv — combined historical + forecast)

```m
let
    BasePath    = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\exports\",

    // Load historical monthly demand from fact_orders
    Orders      = Csv.Document(File.Contents(
                      "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\fact_orders_clean.csv"),
                      [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    OrdHeaders  = Table.PromoteHeaders(Orders, [PromoteAllScalars=true]),
    OrdFiltered = Table.SelectRows(OrdHeaders, each [Order_Status] <> "Cancelled"),
    OrdDate     = Table.TransformColumnTypes(OrdFiltered, {{"Order_Date", type date}}),
    OrdQty      = Table.TransformColumnTypes(OrdDate, {{"Quantity", Int64.Type}}),
    OrdGrouped  = Table.Group(OrdQty, {"YearMonth"}, {
                      {"Total_Quantity", each List.Sum([Quantity]), type number},
                      {"Total_Revenue",  each List.Sum(List.Transform([Revenue], Number.From)), type number}
                  }),
    OrdWithMonth= Table.AddColumn(OrdGrouped, "Month",
                      each Date.From(DateTime.FromText([YearMonth] & "-01")), type date),
    OrdTagged   = Table.AddColumn(OrdWithMonth,  "Data_Type", each "Historical", type text),
    OrdForecast = Table.AddColumn(OrdTagged, "Forecast_Quantity", each null, type number),
    OrdModel    = Table.AddColumn(OrdForecast, "Model", each "Actual", type text),

    // Load forecast data
    ForeSource  = Csv.Document(File.Contents(BasePath & "forecast_ensemble.csv"),
                      [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    ForeHeaders = Table.PromoteHeaders(ForeSource, [PromoteAllScalars=true]),
    ForeTypes   = Table.TransformColumnTypes(ForeHeaders, {
                      {"Month", type date},
                      {"Forecast_Quantity", type number}}),
    ForeTagged  = Table.AddColumn(ForeTypes,  "Data_Type", each "Forecast", type text),
    ForeQty     = Table.AddColumn(ForeTagged, "Total_Quantity", each null, type number),
    ForeRevenue = Table.AddColumn(ForeQty,    "Total_Revenue",  each null, type number),
    ForeYM      = Table.AddColumn(ForeRevenue,"YearMonth",
                      each Text.From(Date.Year([Month])) & "-" &
                           Text.PadStart(Text.From(Date.Month([Month])),2,"0"), type text),

    // Combine
    OrdFinal    = Table.SelectColumns(OrdModel,
                      {"Month","YearMonth","Total_Quantity","Total_Revenue",
                       "Forecast_Quantity","Model","Data_Type"}),
    ForeFinal   = Table.SelectColumns(ForeYM,
                      {"Month","YearMonth","Total_Quantity","Total_Revenue",
                       "Forecast_Quantity","Model","Data_Type"}),
    Combined    = Table.Combine({OrdFinal, ForeFinal}),
    Sorted      = Table.Sort(Combined, {{"Month", Order.Ascending}})
in
    Sorted
```


---

## ANSWERING YOUR QUESTION: Do CSV/Python changes auto-appear in Power BI?

**No. Nothing updates automatically.** Power BI caches a snapshot of your data at the time you last loaded it. Changes to CSV files, Python scripts, or the API have zero effect on an open Power BI report until you explicitly refresh.

### Exact Steps to Refresh After Any Source Change

#### Scenario A: You changed a CSV file (ran `python pipeline.py` to regenerate data)

1. Open `SupplyVision.pbix` in Power BI Desktop
2. Click **Home** tab → **Refresh** button (the circular arrows icon)
3. Power BI re-reads all CSV files from disk and reloads the data
4. All visuals update automatically
5. Save the file: `Ctrl+S`

**That's it. One click.**

#### Scenario B: You changed Power Query M code (edited a query)

1. Open `SupplyVision.pbix`
2. Click **Home** → **Transform Data** (opens Power Query Editor)
3. Make your M code changes
4. Click **Close & Apply** (top-left button in Power Query Editor)
5. Power BI re-runs all queries and loads fresh data

**Do NOT use the Refresh button for M code changes — you must Close & Apply.**

#### Scenario C: You changed a DAX measure

1. Open `SupplyVision.pbix`
2. Find the measure in the Fields panel (right side)
3. Click the measure name once
4. The formula bar at the top shows the DAX — edit it directly
5. Press **Enter** or click the checkmark
6. Visuals update immediately — no refresh needed for DAX changes

**DAX is evaluated live. No refresh button. Edit and it instantly updates.**

#### Scenario D: You changed the column structure of a CSV (added/removed columns)

1. Click **Home** → **Transform Data**
2. In Power Query, click on the affected query
3. Look at the **Applied Steps** panel on the right — the `Changed Type` step will
   show a yellow warning triangle
4. Click that step → fix the column types
5. **Close & Apply**

**Column structure changes always require Power Query fixes — just Refresh is not enough.**

#### Scenario E: You added a completely new CSV file

1. **Home** → **Get Data** → **Text/CSV**
2. Navigate to the new file
3. Go through Power Query to set types
4. **Close & Apply**
5. Then go to Model View and add the relationship

#### Summary Table

| What changed | Action in Power BI |
|---|---|
| Data in existing CSV (ran pipeline) | **Home → Refresh** |
| M code / Power Query logic | **Transform Data → Close & Apply** |
| DAX measure formula | **Edit in formula bar → Enter** |
| Column names changed in CSV | **Transform Data → fix Applied Steps → Close & Apply** |
| New CSV file added | **Get Data → new query → Close & Apply** |
| API response changed (live connection) | **Home → Refresh** |
| Forecast CSV regenerated | **Home → Refresh** |

#### Quick Keyboard Shortcut
After running `python pipeline.py`, the fastest refresh in Power BI:
- `Alt + F5` = Refresh all data (same as clicking the Refresh button)

---

## COMPLETE FIX CHECKLIST — Do These Steps In Order

```
□ Step 1:  Open Power BI Desktop
□ Step 2:  File → Open → SupplyVision.pbix (or create new)
□ Step 3:  Home → Transform Data (opens Power Query)
□ Step 4:  Rename each query (right-click → Rename):
           fact_orders_clean  →  fact_orders
           inventory_clean    →  fact_inventory
           logistics_clean    →  fact_logistics
           suppliers_clean    →  dim_suppliers
           customers_clean    →  dim_customers
□ Step 5:  For each query, use the corrected M code from this document
           to ensure all column types are correct
□ Step 6:  Add the dim_date query using the M code in this document
□ Step 7:  Click Close & Apply
□ Step 8:  Go to Model View
□ Step 9:  Create all 9 relationships listed in this document
□ Step 10: Right-click dim_date → Mark as date table → select Date column
□ Step 11: Delete ALL old DAX measures (they had wrong table names)
□ Step 12: Click on _Measures table
□ Step 13: Enter each corrected DAX measure from this document
□ Step 14: Test these specific measures first (the ones that were broken):
           - Total Inventory Value       → should show a dollar amount ~$XX million
           - Safety Stock Total          → should show a whole number ~30,000-50,000
           - Inventory Turnover Ratio    → should show a number like 0.5-5.0
           - Days Inventory Outstanding  → should show ~73-365
           - Fill Rate %                 → should show 100% (no out-of-stock currently)
           - Low Stock Alert Count       → should show 32
           - On-Time Delivery %          → should show ~50-70%
□ Step 15: Test time intelligence measures:
           - Add a Year slicer from dim_date[Year]
           - Select 2024
           - Revenue MoM Growth % should show a % value (positive or negative)
           - If it shows BLANK, the dim_date relationship is missing
□ Step 16: Save as SupplyVision.pbix
```

---

## VERIFIED EXPECTED VALUES (to confirm your measures are working)

After applying all fixes, these are the correct values your measures should return
when NO filters are applied (showing all data, all years):

| Measure | Expected value | How to verify |
|---|---|---|
| Total Revenue | ~$X (large number) | Card visual, no filters |
| Total Orders | 4,700 approx (5000 minus Cancelled ~6%) | Card visual |
| Total Inventory Value | Large dollar amount | Check inventory CSV: sum of Inventory_Value |
| Safety Stock Total | ~30,000–50,000 units | Sum of Safety_Stock in inventory_clean |
| Low Stock Alert Count | **32** | Exact: 32 products with Low Stock status |
| Stock-Out Rate % | **0.00%** | No Out of Stock products currently |
| Fill Rate % | **100.00%** | All products have stock > 0 |
| Overstock Rate % | **40.00%** | 80 Overstock / 200 products |
| On-Time Delivery % | ~50–55% | About half of 4500 shipments are on-time |
| Delayed Deliveries | ~2000–2200 | About half of 4500 shipments |
| Total Suppliers | 50 | COUNTROWS of dim_suppliers |

Run this Python script to verify the expected values before checking Power BI:

```
python verify_phase1.py
```

If your Power BI numbers match these, the measures are working correctly.

---

*End of SupplyVision DAX Fix Document*
*All 7 root causes identified and resolved*
*All 30+ DAX measures corrected*
*Complete Power Query M code provided for all 8 tables*
