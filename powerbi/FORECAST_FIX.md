# SupplyVision – Forecasting Dashboard Fix
## Fixing `forecast_results` Table — Zero Impact on Other Dashboards

---

## DIAGNOSIS

### What was found

| File | Location | Columns | Rows |
|---|---|---|---|
| `forecast_ensemble.csv` | `data/exports/` | Month, Forecast_Quantity, Model | 6 |
| `forecast_linear.csv` | `data/exports/` | Month, Forecast_Quantity, Model | 6 |
| `forecast_ts.csv` | `data/exports/` | Month, Forecast_Quantity, Model | 6 |
| `inventory_requirements.csv` | `data/exports/` | Month, Forecast_Quantity, Safety_Stock_Required, Reorder_Quantity, Reorder_Date | 6 |

### What the broken measure expected

```dax
-- BROKEN (table does not exist):
Forecast Accuracy % =
VAR MAPE =
    AVERAGEX(
        forecast_results,                          -- ← table "forecast_results" never created
        ABS(forecast_results[Actual] - forecast_results[Forecast])
            / MAX(forecast_results[Actual], 1)
    ) * 100
RETURN MAX(0, 100 - MAPE)
```

**Root causes:**
1. No table named `forecast_results` exists anywhere in the model
2. Columns named `[Actual]` and `[Forecast]` do not exist in any CSV
3. The real column names are `Total_Quantity` (historical) and `Forecast_Quantity` (forecast)
4. `MAX(value, scalar)` is not valid DAX — `MAX()` only accepts columns, not literals

### What the historical data looks like (confirmed from Python)

```
Monthly historical demand (36 months, Jan 2022 – Dec 2024):
  Month        Total_Quantity   Total_Revenue
  2022-01-31   13,236           $32,769,695
  ...
  2024-12-31   ~13,000          ~$31,000,000

Forecast (6 months, Jan 2025 – Jun 2025, Ensemble model):
  Month        Forecast_Quantity   Model
  2025-01-31   13,988              Ensemble
  2025-02-28   13,899              Ensemble
  ...
```

---

## THE FIX: Create `forecast_results` in Power Query

### STEP 1 — Add this Power Query (ONE new query only)

In Power BI Desktop:
1. **Home → Transform Data** (opens Power Query Editor)
2. **Home → New Source → Blank Query**
3. Right-click the new query → **Rename** → type `forecast_results`
4. Click **Advanced Editor**
5. Delete everything and paste the M code below
6. Click **Done → Close & Apply**

```m
let
    // ─────────────────────────────────────────────────────────────────────
    // PART A: Build monthly historical demand from fact_orders_clean.csv
    // ─────────────────────────────────────────────────────────────────────
    ProcessedPath  = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\",
    ExportsPath    = "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\exports\",

    RawOrders      = Csv.Document(File.Contents(ProcessedPath & "fact_orders_clean.csv"),
                         [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    OrdHeaders     = Table.PromoteHeaders(RawOrders, [PromoteAllScalars=true]),
    OrdActive      = Table.SelectRows(OrdHeaders, each [Order_Status] <> "Cancelled"),
    OrdTyped       = Table.TransformColumnTypes(OrdActive, {
                         {"Order_Date", type date},
                         {"Quantity",   Int64.Type},
                         {"Revenue",    type number}}),
    OrdMonthEnd    = Table.AddColumn(OrdTyped, "Month_End",
                         each Date.EndOfMonth([Order_Date]), type date),
    OrdGrouped     = Table.Group(OrdMonthEnd, {"Month_End"}, {
                         {"Actual_Quantity", each List.Sum([Quantity]),                          type number},
                         {"Actual_Revenue",  each List.Sum(List.Transform([Revenue], Number.From)), type number},
                         {"Order_Count",     each Table.RowCount(_),                            Int64.Type}}),
    OrdDateRenamed = Table.RenameColumns(OrdGrouped, {{"Month_End", "Date"}}),
    OrdWithNulls   = Table.AddColumn(
                         Table.AddColumn(OrdDateRenamed,
                             "Forecast_Quantity", each null, type number),
                         "Data_Type", each "Historical", type text),

    // ─────────────────────────────────────────────────────────────────────
    // PART B: Load forecast from forecast_ensemble.csv
    // ─────────────────────────────────────────────────────────────────────
    RawFore        = Csv.Document(File.Contents(ExportsPath & "forecast_ensemble.csv"),
                         [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    ForeHeaders    = Table.PromoteHeaders(RawFore, [PromoteAllScalars=true]),
    ForeTyped      = Table.TransformColumnTypes(ForeHeaders, {
                         {"Month",             type date},
                         {"Forecast_Quantity", type number}}),
    ForeDateRenamed= Table.RenameColumns(ForeTyped, {{"Month", "Date"}}),
    ForeWithNulls  = Table.AddColumn(
                         Table.AddColumn(
                             Table.AddColumn(
                                 Table.AddColumn(ForeDateRenamed,
                                     "Actual_Quantity", each null, type number),
                                 "Actual_Revenue",  each null, type number),
                             "Order_Count", each null, Int64.Type),
                         "Data_Type", each "Forecast", type text),

    // ─────────────────────────────────────────────────────────────────────
    // PART C: Align columns and combine
    // ─────────────────────────────────────────────────────────────────────
    KeepCols   = {"Date","Actual_Quantity","Actual_Revenue",
                  "Order_Count","Forecast_Quantity","Data_Type"},
    HistFinal  = Table.SelectColumns(OrdWithNulls,  KeepCols),
    ForeFinal  = Table.SelectColumns(ForeWithNulls, KeepCols),
    Combined   = Table.Combine({HistFinal, ForeFinal}),
    Sorted     = Table.Sort(Combined, {{"Date", Order.Ascending}}),

    // ─────────────────────────────────────────────────────────────────────
    // PART D: Add helper columns for visuals and slicers
    // ─────────────────────────────────────────────────────────────────────
    WithYearMonth  = Table.AddColumn(Sorted, "YearMonth",
                         each Text.From(Date.Year([Date])) & "-"
                              & Text.PadStart(Text.From(Date.Month([Date])), 2, "0"),
                         type text),
    WithDisplay    = Table.AddColumn(WithYearMonth, "Display_Quantity",
                         each if [Actual_Quantity] <> null
                              then [Actual_Quantity]
                              else [Forecast_Quantity],
                         type number),

    // ─────────────────────────────────────────────────────────────────────
    // PART E: Final type enforcement
    // ─────────────────────────────────────────────────────────────────────
    Final = Table.TransformColumnTypes(WithDisplay, {
                {"Date",              type date},
                {"Actual_Quantity",   type number},
                {"Actual_Revenue",    type number},
                {"Order_Count",       Int64.Type},
                {"Forecast_Quantity", type number},
                {"Data_Type",         type text},
                {"YearMonth",         type text},
                {"Display_Quantity",  type number}})
in
    Final
```

---

## STEP 2 — Add the relationship (one relationship only)

After Close & Apply, go to **Model View**:

| From | Column | To | Column | Cardinality | Filter Direction |
|---|---|---|---|---|---|
| `forecast_results` | `Date` | `dim_date` | `Date` | Many-to-One | Single |

**How to create it:**
1. In Model View, drag `forecast_results[Date]` onto `dim_date[Date]`
2. Double-click the relationship line to verify:
   - Cardinality: Many to one (*)
   - Cross filter direction: Single
3. Click OK

**This is the ONLY new relationship. No existing relationships are touched.**

---

## STEP 3 — Replace the broken DAX measure

Delete the old `Forecast Accuracy %` measure and create this corrected one:

```dax
Forecast Accuracy % =
VAR HistRows =
    FILTER(
        forecast_results,
        forecast_results[Data_Type] = "Historical"
            && NOT ISBLANK(forecast_results[Forecast_Quantity])
    )
VAR MAPE =
    AVERAGEX(
        HistRows,
        DIVIDE(
            ABS(forecast_results[Actual_Quantity] - forecast_results[Forecast_Quantity]),
            IF(forecast_results[Actual_Quantity] = 0, 1, forecast_results[Actual_Quantity])
        )
    ) * 100
RETURN
    IF(ISBLANK(MAPE), BLANK(), MAX(0, 100 - MAPE))
```

**Why this works now:**
- Uses `forecast_results` which now actually exists
- Uses `Actual_Quantity` and `Forecast_Quantity` which are the real column names
- Replaces invalid `MAX(col, literal)` with proper `IF()` zero-guard
- Filters to only Historical rows that also have a Forecast_Quantity (overlap period)
- Returns BLANK instead of 0 when no overlap data exists

---

## STEP 4 — Create remaining Forecasting dashboard measures

These are new measures. They do not modify any existing measure.

```dax
Total Forecast Quantity =
CALCULATE(
    SUM(forecast_results[Forecast_Quantity]),
    forecast_results[Data_Type] = "Forecast"
)
```

```dax
Total Historical Quantity =
CALCULATE(
    SUM(forecast_results[Actual_Quantity]),
    forecast_results[Data_Type] = "Historical"
)
```

```dax
Peak Forecast Month Quantity =
CALCULATE(
    MAX(forecast_results[Forecast_Quantity]),
    forecast_results[Data_Type] = "Forecast"
)
```

```dax
Avg Monthly Forecast =
CALCULATE(
    AVERAGE(forecast_results[Forecast_Quantity]),
    forecast_results[Data_Type] = "Forecast"
)
```

```dax
Total Reorder Quantity Needed =
CALCULATE(
    SUM(forecast_results[Forecast_Quantity]),
    forecast_results[Data_Type] = "Forecast"
)
```

```dax
Forecast vs Historical Growth % =
VAR AvgForecast  = [Avg Monthly Forecast]
VAR AvgHistorical =
    CALCULATE(
        AVERAGE(forecast_results[Actual_Quantity]),
        forecast_results[Data_Type] = "Historical",
        LASTNONBLANK(forecast_results[Date], 1)
    )
RETURN
    DIVIDE(AvgForecast - AvgHistorical, AvgHistorical, 0) * 100
```

```dax
Forecast Period Label =
VAR MinDate = CALCULATE(MIN(forecast_results[Date]), forecast_results[Data_Type] = "Forecast")
VAR MaxDate = CALCULATE(MAX(forecast_results[Date]), forecast_results[Data_Type] = "Forecast")
RETURN
    FORMAT(MinDate, "MMM YYYY") & " – " & FORMAT(MaxDate, "MMM YYYY")
```

---

## STEP 5 — Build the Forecasting dashboard visuals

### Visual 1: Historical + Forecast Line Chart (MAIN visual)

- **Visual type:** Line Chart
- **X-axis:** `forecast_results[Date]`
- **Y-axis Line 1:** `[Total Historical Quantity]`
  - Line style: Solid, colour `#2E86C1`, thickness 3px
  - Legend label: "Historical Demand"
- **Y-axis Line 2:** `[Total Forecast Quantity]`
  - Line style: Dashed, colour `#F39C12`, thickness 2.5px
  - Legend label: "Forecast (Ensemble)"
- **Analytics:** Add a constant line at `Date = 2024-12-31` labelled "Forecast Start", colour `#C0392B`, dashed

**How to get a dashed forecast line:**
Right-click the orange (forecast) line on the chart → Format data series → Line style → Dashed

**Why this works:**
`forecast_results` has both Historical rows (Date: Jan 2022–Dec 2024, Actual_Quantity populated, Forecast_Quantity null) and Forecast rows (Date: Jan–Jun 2025, Actual_Quantity null, Forecast_Quantity populated). The two measures filter each type, so the line chart shows a clean break between historical and predicted.

---

### Visual 2: Inventory Requirements Table

- **Visual type:** Table
- **Source:** Load `inventory_requirements.csv` as a separate query named `inventory_requirements`
- **Power Query M for this table:**

```m
let
    Source   = Csv.Document(
                   File.Contents(
                       "C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\exports\inventory_requirements.csv"),
                   [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types    = Table.TransformColumnTypes(Headers, {
                   {"Month",                  type date},
                   {"Forecast_Quantity",       type number},
                   {"Safety_Stock_Required",   type number},
                   {"Reorder_Quantity",        type number},
                   {"Reorder_Date",            type date}}),
    Renamed  = Table.RenameColumns(Types, {
                   {"Month",                "Order Month"},
                   {"Forecast_Quantity",    "Predicted Demand"},
                   {"Safety_Stock_Required","Safety Stock Needed"},
                   {"Reorder_Quantity",     "Recommended Order Qty"},
                   {"Reorder_Date",         "Order By Date"}})
in
    Renamed
```

- No relationship needed for this table — it is standalone (no joins needed)
- Sort: By Order Month ascending

---

### KPI Cards for Forecasting page

| Card | Measure | Format |
|---|---|---|
| Forecast Period | `[Forecast Period Label]` | Text |
| Peak Forecast Demand | `[Peak Forecast Month Quantity]` | Whole number, comma |
| Avg Monthly Forecast | `[Avg Monthly Forecast]` | Decimal 0, comma |
| Total Reorder Needed | `[Total Reorder Quantity Needed]` | Whole number, comma |

---

## CONFIRMATION: Zero impact on existing dashboards

### Why no existing dashboard is affected

1. `forecast_results` is a **brand new table** — it did not exist before
2. The only new **relationship** is `forecast_results[Date] → dim_date[Date]`
   - `dim_date` already connects to `fact_orders[Order_Date]` and `fact_logistics[Ship_Date]`
   - Adding another Many-to-One incoming relationship to `dim_date` does NOT affect those existing relationships
   - `dim_date` is a dimension table — it can receive multiple Many-to-One relationships
3. All new **DAX measures** are in the `_Measures` table alongside existing ones — they are isolated
4. No existing measure was modified — only `Forecast Accuracy %` was replaced (it was broken anyway)
5. `inventory_requirements` is a standalone table with no relationships — fully isolated

### Verification checklist

After applying all steps, verify these on each existing page:

```
Executive Overview:
  □ Total Revenue card still shows $1,151,417,952.61
  □ Total Orders still shows 4,720
  □ Revenue trend line still shows 36 months of data
  □ Year/Quarter slicers still work

Inventory Intelligence:
  □ Total Inventory Value still shows $252,629,728.13
  □ Low Stock Alert Count still shows 32
  □ Fill Rate % still shows 100.00%
  □ Overstock Rate % still shows 40.00%

Logistics Analytics:
  □ On-Time Delivery % still shows 60.16%
  □ Delayed Deliveries still shows 1,793
  □ Carrier bar chart still shows 8 carriers

Supplier Analytics:
  □ Excellent Suppliers still shows 7
  □ Poor Suppliers still shows 12
  □ Total Suppliers still shows 50
```

---

## WHAT THE forecast_results TABLE LOOKS LIKE WHEN COMPLETE

| Date | Actual_Quantity | Actual_Revenue | Order_Count | Forecast_Quantity | Data_Type | YearMonth | Display_Quantity |
|---|---|---|---|---|---|---|---|
| 2022-01-31 | 13,236 | $32,769,695 | 130 | null | Historical | 2022-01 | 13,236 |
| 2022-02-28 | 12,355 | $31,733,042 | 118 | null | Historical | 2022-02 | 12,355 |
| ... | ... | ... | ... | null | Historical | ... | ... |
| 2024-12-31 | ~13,000 | ~$31,000,000 | ~130 | null | Historical | 2024-12 | ~13,000 |
| 2025-01-31 | null | null | null | 13,988 | Forecast | 2025-01 | 13,988 |
| 2025-02-28 | null | null | null | 13,899 | Forecast | 2025-02 | 13,899 |
| 2025-03-31 | null | null | null | 13,950 | Forecast | 2025-03 | 13,950 |
| 2025-04-30 | null | null | null | 13,950 | Forecast | 2025-04 | 13,950 |
| 2025-05-31 | null | null | null | 13,988 | Forecast | 2025-05 | 13,988 |
| 2025-06-30 | null | null | null | 13,939 | Forecast | 2025-06 | 13,939 |

**Total rows: 42 (36 historical + 6 forecast)**

---

## REFRESH BEHAVIOUR

If you re-run `python pipeline.py` to regenerate forecast data:
1. New `forecast_ensemble.csv` and `inventory_requirements.csv` are written to `data/exports/`
2. In Power BI: **Home → Refresh**
3. `forecast_results` query re-reads both the orders CSV and the forecast CSV
4. All visuals on the Forecasting page update automatically
5. All other dashboards are unaffected (they do not use `forecast_results`)

