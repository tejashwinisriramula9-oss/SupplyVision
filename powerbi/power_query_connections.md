# SupplyVision – Power Query M Code
## All Data Source Connections for Power BI Desktop

---

## Option A: Connect via FastAPI (Recommended – Live Data)

The API server must be running: `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --no-access-log`

### Executive KPIs
```m
let
    Source    = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/executive/kpis")),
    AsRecord  = Source,
    AsTable   = Record.ToTable(AsRecord),
    Renamed   = Table.RenameColumns(AsTable, {{"Name","KPI"},{"Value","Amount"}})
in
    Renamed
```

### All KPIs (single call – all 5 domains)
```m
let
    Source    = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/executive/all-kpis")),
    Exec      = Record.ToTable(Source[executive]),
    Inv       = Record.ToTable(Source[inventory]),
    Log       = Record.ToTable(Source[logistics]),
    Sup       = Record.ToTable(Source[suppliers]),
    Wh        = Record.ToTable(Source[warehouses])
in
    Source
```

### Revenue Trend (Monthly)
```m
let
    Source   = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/executive/revenue-trend")),
    ToTable  = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand   = Table.ExpandRecordColumn(ToTable, "Column1",
                   {"Order_Date","Revenue","Orders","Avg_Order_Value"}),
    DateCol  = Table.TransformColumnTypes(Expand, {{"Order_Date", type date}}),
    NumCols  = Table.TransformColumnTypes(DateCol, {
                   {"Revenue", type number},
                   {"Orders",  Int64.Type},
                   {"Avg_Order_Value", type number}})
in
    NumCols
```

### Top Products
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/executive/top-products?n=20")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Product_ID","Category","Total_Revenue","Total_Quantity","Order_Count"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Total_Revenue",   type number},
                  {"Total_Quantity",  Int64.Type},
                  {"Order_Count",     Int64.Type}})
in
    Types
```

### Inventory KPIs
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/inventory/kpis")),
    ToTable = Record.ToTable(Source),
    Renamed = Table.RenameColumns(ToTable, {{"Name","KPI"},{"Value","Amount"}})
in
    Renamed
```

### Inventory by Category
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/inventory/by-category")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Category","Product_Count","Total_Stock","Total_Value",
                   "Avg_Stock","Stock_Out_Count"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Product_Count",  Int64.Type},
                  {"Total_Stock",    Int64.Type},
                  {"Total_Value",    type number},
                  {"Avg_Stock",      type number},
                  {"Stock_Out_Count",Int64.Type}})
in
    Types
```

### Low Stock Alerts
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/inventory/low-stock-alerts")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Product_ID","Product_Name","Category","Current_Stock",
                   "Safety_Stock","Stock_Status","Warehouse_ID","Inventory_Value","Stock_Gap"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Current_Stock",    Int64.Type},
                  {"Safety_Stock",     Int64.Type},
                  {"Inventory_Value",  type number},
                  {"Stock_Gap",        Int64.Type}})
in
    Types
```

### Product Velocity (Fast/Slow Movers)
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/inventory/product-velocity?n=50")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Product_ID","Product_Name","Category","Current_Stock",
                   "Total_Sold","Revenue","Velocity_Score","Movement_Class"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Current_Stock",  Int64.Type},
                  {"Total_Sold",     type number},
                  {"Revenue",        type number},
                  {"Velocity_Score", type number}})
in
    Types
```

### Logistics KPIs
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/logistics/kpis")),
    ToTable = Record.ToTable(Source),
    Renamed = Table.RenameColumns(ToTable, {{"Name","KPI"},{"Value","Amount"}})
in
    Renamed
```

### Carrier Performance
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/logistics/carrier-performance")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Carrier","Total_Shipments","On_Time_Rate","Avg_Transit_Time",
                   "Total_Cost","Avg_Delay_Days"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Total_Shipments",  Int64.Type},
                  {"On_Time_Rate",     type number},
                  {"Avg_Transit_Time", type number},
                  {"Total_Cost",       type number},
                  {"Avg_Delay_Days",   type number}})
in
    Types
```

### Delivery Trend (Monthly)
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/logistics/delivery-trend")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Ship_Date","Total_Shipments","On_Time","Delayed",
                   "Avg_Transit","Total_Cost","On_Time_Pct"}),
    DateCol = Table.TransformColumnTypes(Expand, {{"Ship_Date", type date}}),
    Types   = Table.TransformColumnTypes(DateCol, {
                  {"Total_Shipments", Int64.Type},
                  {"On_Time",         Int64.Type},
                  {"Delayed",         Int64.Type},
                  {"On_Time_Pct",     type number},
                  {"Total_Cost",      type number}})
in
    Types
```

### Supplier KPIs
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/suppliers/kpis")),
    ToTable = Record.ToTable(Source),
    Renamed = Table.RenameColumns(ToTable, {{"Name","KPI"},{"Value","Amount"}})
in
    Renamed
```

### Supplier Comparison Table
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/suppliers/comparison")),
    ToTable = Table.FromList(Source, Splitter.SplitByNothing()),
    Expand  = Table.ExpandRecordColumn(ToTable, "Column1",
                  {"Supplier_ID","Supplier_Name","Country","Region",
                   "Lead_Time","Reliability_Score","Reliability_Tier",
                   "Supplier_Cost","Shipments","Delivery_Reliability_Pct","Avg_Transit_Time"}),
    Types   = Table.TransformColumnTypes(Expand, {
                  {"Lead_Time",               Int64.Type},
                  {"Reliability_Score",        type number},
                  {"Supplier_Cost",            type number},
                  {"Delivery_Reliability_Pct", type number},
                  {"Avg_Transit_Time",          type number}})
in
    Types
```

### Demand Forecast
```m
let
    Source  = Json.Document(Web.Contents("http://127.0.0.1:8000/api/v1/forecasting/demand?horizon_months=6")),
    Hist    = Table.FromList(Source[historical], Splitter.SplitByNothing()),
    HistExp = Table.ExpandRecordColumn(Hist, "Column1",
                  {"Month","Total_Quantity","Total_Revenue","Month_Num"}),
    Fore    = Table.FromList(Source[forecast], Splitter.SplitByNothing()),
    ForeExp = Table.ExpandRecordColumn(Fore, "Column1",
                  {"Month","Forecast_Quantity","Model"}),
    HistTag = Table.AddColumn(HistExp, "Type", each "Historical"),
    ForeTag = Table.AddColumn(ForeExp, "Type", each "Forecast"),
    Combined = Table.Combine({
        Table.RenameColumns(HistTag, {{"Total_Quantity","Quantity"}}),
        Table.RenameColumns(ForeTag, {{"Forecast_Quantity","Quantity"}})
    }),
    DateCol = Table.TransformColumnTypes(Combined, {{"Month", type date}})
in
    DateCol
```

---

## Option B: Connect via CSV Files (Offline / No API needed)

In Power BI: **Home → Get Data → Text/CSV**

| Query Name | File Path |
|---|---|
| fact_orders | `data/processed/fact_orders_clean.csv` |
| inventory | `data/processed/inventory_clean.csv` |
| suppliers | `data/processed/suppliers_clean.csv` |
| logistics | `data/processed/logistics_clean.csv` |
| warehouses | `data/processed/warehouses_clean.csv` |
| customers | `data/processed/customers_clean.csv` |
| forecast | `data/exports/forecast_ensemble.csv` |

### CSV Base Path helper (edit once, used everywhere)
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\"
in
    BasePath
```

### fact_orders from CSV
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "fact_orders_clean.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Order_Date",    type date},
                   {"Revenue",       type number},
                   {"COGS",          type number},
                   {"Gross_Profit",  type number},
                   {"Quantity",      Int64.Type},
                   {"Year",          Int64.Type},
                   {"Month",         Int64.Type},
                   {"Quarter",       Int64.Type}})
in
    Types
```

### inventory from CSV
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "inventory_clean.csv"),
                   [Delimiter=",", Encoding=65001]),
    Headers  = Table.PromoteHeaders(Source),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Current_Stock",   Int64.Type},
                   {"Safety_Stock",    Int64.Type},
                   {"Reorder_Point",   Int64.Type},
                   {"Unit_Cost",       type number},
                   {"Unit_Price",      type number},
                   {"Inventory_Value", type number},
                   {"Margin_Pct",      type number}})
in
    Types
```

### suppliers from CSV
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "suppliers_clean.csv"),
                   [Delimiter=",", Encoding=65001]),
    Headers  = Table.PromoteHeaders(Source),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Lead_Time",        Int64.Type},
                   {"Reliability_Score",type number},
                   {"Supplier_Cost",    type number}})
in
    Types
```

### logistics from CSV
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "logistics_clean.csv"),
                   [Delimiter=",", Encoding=65001]),
    Headers  = Table.PromoteHeaders(Source),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Ship_Date",      type date},
                   {"Delivery_Date",  type date},
                   {"Transit_Time",   Int64.Type},
                   {"Delay_Days",     Int64.Type},
                   {"Is_Delayed",     Int64.Type},
                   {"Transport_Cost", type number},
                   {"Cost_Per_KG",    type number}})
in
    Types
```

### warehouses from CSV
```m
let
    BasePath = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    Source   = Csv.Document(File.Contents(BasePath & "warehouses_clean.csv"),
                   [Delimiter=",", Encoding=65001]),
    Headers  = Table.PromoteHeaders(Source),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Capacity",           Int64.Type},
                   {"Utilization_Pct",    type number},
                   {"Available_Capacity", Int64.Type}})
in
    Types
```

### dim_date (Generated Calendar Table)
```m
let
    StartDate    = #date(2022, 1, 1),
    EndDate      = #date(2024, 12, 31),
    DayCount     = Duration.Days(EndDate - StartDate) + 1,
    Dates        = List.Dates(StartDate, DayCount, #duration(1,0,0,0)),
    DateTable    = Table.FromList(Dates, Splitter.SplitByNothing()),
    Renamed      = Table.RenameColumns(DateTable, {{"Column1","Date"}}),
    TypedDate    = Table.TransformColumnTypes(Renamed, {{"Date", type date}}),
    AddYear      = Table.AddColumn(TypedDate,  "Year",          each Date.Year([Date]),           Int64.Type),
    AddMonth     = Table.AddColumn(AddYear,    "Month",         each Date.Month([Date]),          Int64.Type),
    AddDay       = Table.AddColumn(AddMonth,   "Day",           each Date.Day([Date]),            Int64.Type),
    AddQtr       = Table.AddColumn(AddDay,     "Quarter",       each Date.QuarterOfYear([Date]),  Int64.Type),
    AddQtrStr    = Table.AddColumn(AddQtr,     "Quarter_Label", each "Q" & Text.From([Quarter]),  type text),
    AddMonthName = Table.AddColumn(AddQtrStr,  "Month_Name",    each Date.MonthName([Date]),      type text),
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
    AddFiscalQtr = Table.AddColumn(AddIsWeekend,"Fiscal_Year",
                       each if [Month] >= 10 then [Year] + 1 else [Year],
                       Int64.Type)
in
    AddFiscalQtr
```
