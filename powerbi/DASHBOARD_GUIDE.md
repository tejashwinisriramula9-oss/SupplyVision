# SupplyVision – Complete Power BI Dashboard Guide
### For Beginners | Step-by-Step Implementation

---

# PART 1 — BEFORE YOU TOUCH POWER BI
## Understanding What You Are Building

Think of Power BI like building a house.
- Your **CSV files** are the raw materials (bricks, wood)
- **Power Query** is the construction site where you shape those materials
- The **Data Model** is the blueprint showing how rooms connect
- **DAX measures** are the electrical wiring (invisible but makes everything work)
- **Visuals** are the furniture in each room
- **Dashboard pages** are the rooms themselves

You are building 5 rooms (pages) + 1 hidden utility room.

---

# PART 2 — FIRST-TIME SETUP (Do This Before Anything Else)

## Step 1: Open Power BI Desktop

Download from: https://powerbi.microsoft.com/desktop (it is free)

When it opens you will see:
- **Report view** (canvas area — this is where you design)
- **Data view** (shows table contents)
- **Model view** (shows relationships between tables)

---

## Step 2: Apply the SupplyVision Theme FIRST

Do this before loading any data. It sets all colours and fonts globally.

1. Click the **View** tab in the top ribbon
2. Click **Themes** → **Browse for themes**
3. Navigate to: `C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\powerbi\`
4. Select **SupplyVision_Theme.json**
5. Click **Open**

You will see the canvas background change to `#F2F4F7` (light gray).
All new visuals you create will automatically use your brand colours.

---

## Step 3: Set the Canvas Size

Every dashboard page must be 1920 × 1080.

1. Click anywhere on the blank canvas
2. In the right panel, click **Format page** (paint roller icon)
3. Under **Canvas settings**, change Type to **Custom**
4. Set Width: **1920**, Height: **1080**
5. Do this for EVERY page you create

---

## Step 4: Load Your Data

You will load 7 CSV files from `data/processed/`.

1. Click **Home** tab → **Get Data** → **Text/CSV**
2. Navigate to `C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\processed\`
3. Load these files one by one:
   - `fact_orders_clean.csv`
   - `inventory_clean.csv`
   - `suppliers_clean.csv`
   - `customers_clean.csv`
   - `logistics_clean.csv`
   - `warehouses_clean.csv`
4. For each file: click **Transform Data** (not Load directly)

**IMPORTANT:** Never click "Load" directly. Always go through Power Query first.

---

## Step 5: Clean Data in Power Query (Power Query Editor)

When Power Query opens, you need to fix data types.
Power BI sometimes reads numbers as text or dates as text.

For **fact_orders_clean**:
- `Order_Date` → right-click column header → Change Type → Date
- `Revenue`, `COGS`, `Gross_Profit` → Change Type → Decimal Number
- `Quantity`, `Year`, `Month`, `Quarter` → Change Type → Whole Number
- `Discount`, `Gross_Margin_Pct` → Change Type → Decimal Number

For **logistics_clean**:
- `Ship_Date`, `Delivery_Date` → Change Type → Date
- `Transit_Time`, `Delay_Days`, `Is_Delayed` → Change Type → Whole Number
- `Transport_Cost` → Change Type → Decimal Number

For **inventory_clean**:
- `Current_Stock`, `Safety_Stock` → Change Type → Whole Number
- `Unit_Cost`, `Unit_Price`, `Inventory_Value` → Change Type → Decimal Number
- `Last_Updated` → Change Type → Date

For **warehouses_clean**:
- `Capacity`, `Available_Capacity` → Change Type → Whole Number
- `Utilization_Pct` → Change Type → Decimal Number

For **suppliers_clean**:
- `Lead_Time` → Change Type → Whole Number
- `Reliability_Score`, `Supplier_Cost` → Change Type → Decimal Number

Click **Close & Apply** when done.

---

## Step 6: Create the Date Dimension Table

This is the most important step. Without a date table, time intelligence DAX (MoM growth, YoY growth) will NOT work.

1. Click **Home** tab → **Transform Data** → **Enter Data**
   (Actually, use this method instead:)
2. Click **Home** → **Transform Data** to open Power Query
3. Click **New Source** → **Blank Query**
4. Click **Advanced Editor**
5. Delete everything and paste this exact code:

```
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

6. Click **Done**
7. Rename this query to **dim_date** (double-click the query name on the left)
8. Click **Close & Apply**

---

## Step 7: Create the Relationships (Data Model)

This is where you tell Power BI how the tables connect.

1. Click the **Model view** icon (looks like 3 connected shapes on the left sidebar)
2. You will see your tables as boxes. Drag to arrange them neatly.
3. Create these relationships by dragging one column onto another:

| From Table | From Column | To Table | To Column | Type |
|-----------|-------------|----------|-----------|------|
| fact_orders | Order_Date | dim_date | Date | Many → One |
| fact_orders | Product_ID | inventory_clean | Product_ID | Many → One |
| fact_orders | Warehouse_ID | warehouses_clean | Warehouse_ID | Many → One |
| fact_orders | Supplier_ID | suppliers_clean | Supplier_ID | Many → One |
| fact_orders | Customer_ID | customers_clean | Customer_ID | Many → One |
| logistics_clean | Ship_Date | dim_date | Date | Many → One |
| logistics_clean | Supplier_ID | suppliers_clean | Supplier_ID | Many → One |
| inventory_clean | Warehouse_ID | warehouses_clean | Warehouse_ID | Many → One |

**How to create a relationship:**
- Drag `fact_orders[Order_Date]` and drop it onto `dim_date[Date]`
- A line appears between the tables
- Double-click the line to verify: Cardinality should be "Many to one (*:1)"
- Cross filter direction should be "Single" for most relationships

**BEGINNER MISTAKE:** If Power BI shows a yellow warning about relationships, it means you have a circular dependency. Fix it by changing one relationship's cross-filter direction.

---

## Step 8: Create the _Measures Table

Instead of scattering DAX measures inside fact tables, create a clean empty table.

1. Click **Home** → **Enter Data**
2. Create one row with one column called "Placeholder" with value 1
3. Name it **_Measures**
4. Click **Load**
5. Now ALL your DAX measures will live here (organised)

---

## Step 9: Enter All DAX Measures

1. Click on **_Measures** table in the Fields panel (right side)
2. Click **Home** → **New Measure**
3. Type or paste each DAX formula from `powerbi/dax_measures.md`
4. Press Enter after each one

**Enter them in this order** (some measures depend on others):

Group 1 — Basic counts (no dependencies):
- Total Revenue
- Total Orders
- Total Inventory Value
- Current Stock Total
- Safety Stock Total
- Total Transport Cost

Group 2 — Calculated from Group 1:
- Gross Margin %
- Average Order Value
- Cancelled Order %
- Inventory Turnover Ratio
- Fill Rate %
- Stock-Out Rate %
- Overstock Rate %
- Low Stock Alert Count
- On-Time Delivery %
- Delayed Deliveries
- Avg Transit Time
- Avg Delay Days
- Transport Cost per Shipment

Group 3 — Time intelligence (need dim_date):
- Revenue MoM Growth %
- Revenue YoY Growth %
- Days Inventory Outstanding

Group 4 — Supplier measures:
- Supplier Reliability %
- Average Lead Time
- Delivery Reliability %
- Total Supplier Cost
- Excellent Supplier Count
- Poor Supplier Count

Group 5 — Forecasting measures:
- Total Forecast Quantity
- Avg Monthly Forecast
- Peak Forecast Month Quantity
- Total Reorder Quantity Needed

Group 6 — Status & Dynamic titles:
- Delivery Performance Status
- Selected Year Title
- Dashboard Subtitle

**BEGINNER MISTAKE:** Do not type the measure name twice. The formula bar shows `Measure Name = [formula]`. The name before `=` IS the measure name.


---

# PART 3 — THE 6 DASHBOARD PAGES

## Overview: Why 5 Pages?

| # | Page Name | Audience | Purpose |
|---|-----------|----------|---------|
| 1 | 🏠 Executive Overview | CEO, COO | "Is the business healthy?" |
| 2 | 📦 Inventory Intelligence | Supply Chain Managers | "Do we have the right stock?" |
| 3 | 🚚 Logistics Analytics | Operations Managers | "Are deliveries on time?" |
| 4 | 🤝 Supplier Analytics | Procurement Managers | "Which suppliers are performing?" |
| 5 | 🔮 Forecasting & Predictions | Data Analysts, Planners | "What should we order next month?" |
| 6 | 🔍 Product Detail | Any user (drill-through) | "Deep dive on one product" |
| 2 | 📦 Inventory Intelligence | Supply Chain Managers | "Do we have the right stock?" |
| 3 | 🚚 Logistics Analytics | Operations Managers | "Are deliveries on time?" |
| 4 | 🤝 Supplier Analytics | Procurement Managers | "Which suppliers are performing?" |
| 5 | 🔮 Forecasting & Predictions | Data Analysts, Planners | "What should we order next month?" |
| 6 | 🔍 Product Detail | Any user (drill-through) | "Deep dive on one product" |

Each page answers ONE clear business question. Never mix topics on one page.

---

# PAGE 1: 🏠 EXECUTIVE OVERVIEW

## Business Objective
Give the CEO/COO a 30-second health check of the entire supply chain.
They should be able to answer: "How much did we earn? Are deliveries on time? Is inventory healthy?"

## Target Users
CEO, COO, Operations Director — people who look at this for 2 minutes max.

## Canvas Setup
- Background colour: `#F2F4F7` (already set by theme)
- Add a rectangle shape at the top: Height 80px, full width, colour `#0A2342`
- Inside that rectangle, add a Text Box: "SupplyVision | Executive Overview"
  - Font: Segoe UI Semibold, Size 20, Colour White

---

### LAYOUT — 3 ZONES

```
┌─────────────────────────────────────────────────────────────────────┐
│ ZONE A — HEADER BAR (80px tall, dark blue #0A2342)                  │
│ Title: "SupplyVision | Executive Overview"     [Year slicer] [Qtr]  │
├────────────┬────────────┬────────────┬────────────┬────────┬────────┤
│ ZONE B — KPI CARDS ROW (120px tall, 6 cards side by side)          │
│  Total     │  Total     │ Inventory  │ On-Time    │Turnover│ Gross  │
│  Revenue   │  Orders    │  Value     │ Delivery % │ Ratio  │ Margin │
├────────────┴────────────┴────────────┴────────────┴────────┴────────┤
│ ZONE C — MAIN VISUALS (2 rows × 2 columns)                          │
│                                                                     │
│  [Revenue Trend Line Chart]    [Order Status Donut Chart]           │
│                                                                     │
│  [Revenue by Category Bar]     [Delivery Performance Gauge]         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### ZONE B: THE 6 KPI CARDS

A KPI Card in Power BI is called a **Card visual**. It shows one big number.

#### How to add a Card:
1. In Visualizations panel, click the **Card** icon (looks like a rectangle with a number)
2. Drag your measure to the "Fields" well
3. Resize and position it

#### Card 1: Total Revenue
- Visual: Card
- Measure: `[Total Revenue]`
- Format: Currency, 0 decimal places, prefix $
- Card background: White `#FFFFFF`
- Label text: "Total Revenue"
- Icon: Add a text box with 💰 emoji above it
- Value colour: `#0A2342`
- **Why card?** Revenue is a single key number — no chart needed. Cards are fastest to read.

#### Card 2: Total Orders
- Visual: Card
- Measure: `[Total Orders]`
- Format: Whole number with comma separator
- Label: "Total Orders"
- Icon: 📦

#### Card 3: Total Inventory Value
- Visual: Card
- Measure: `[Total Inventory Value]`
- Format: Currency
- Label: "Inventory Value"
- Icon: 🏭

#### Card 4: On-Time Delivery %
- Visual: Card
- Measure: `[On-Time Delivery %]`
- Format: Decimal, 1 place, suffix %
- Label: "On-Time Delivery"
- Icon: 🚚
- **Conditional formatting:** If value < 85, show value in Red `#C0392B`. If ≥ 85, show Green `#1E8449`.
  - How: Select the card → Format → Callout value → Conditional formatting → Based on rules

#### Card 5: Inventory Turnover Ratio
- Visual: Card
- Measure: `[Inventory Turnover Ratio]`
- Format: Decimal, 2 places, suffix "x"
- Label: "Turnover Ratio"
- Icon: 🔄

#### Card 6: Gross Margin %
- Visual: Card
- Measure: `[Gross Margin %]`
- Format: Decimal, 1 place, suffix %
- Label: "Gross Margin"
- Icon: 💹

**How to add suffix/prefix to a card:**
Select the card → Format panel → Callout value → Display units → None → then in "Value" section look for "Custom label" — type your suffix.

---

### ZONE C: THE 4 MAIN CHARTS

#### Chart 1: Revenue Trend (Line Chart)
- Visual: **Line Chart**
- X-axis: `dim_date[YearMonth]` (or Month Name)
- Y-axis: `[Total Revenue]`
- Secondary line: `[Total Orders]` (optional — on second Y-axis)
- Position: Top-left of Zone C
- Size: About 900px wide × 380px tall
- Line colour: `#2E86C1`
- Why Line Chart? Revenue over time = trend data. Line charts show trends best. A bar chart would work too but becomes cluttered with 36 months of data.

**How to add it:**
1. Click Line Chart icon in Visualizations panel
2. Drag `dim_date[YearMonth]` to X-axis
3. Drag `[Total Revenue]` to Y-axis
4. In Format panel: turn on Data labels → set font size 9
5. Turn on Markers (the dots on the line) → size 4
6. Grid lines colour: `#E8ECF0`

#### Chart 2: Order Status Distribution (Donut Chart)
- Visual: **Donut Chart**
- Legend: `fact_orders[Order_Status]`
- Values: `[Total Orders]`
- Position: Top-right of Zone C
- Why Donut? You want to show parts of a whole (Delivered vs Shipped vs Cancelled etc). Donut = proportion. Never use a pie chart — donuts look more professional and you can put a number in the middle.

**Colour mapping** (set manually in the chart colours):
- Delivered → `#1E8449` (green = good)
- Shipped → `#2E86C1` (blue = in progress)
- Processing → `#F39C12` (amber = pending)
- Cancelled → `#C0392B` (red = bad)
- Returned → `#7F8C8D` (grey = neutral)

**How to set custom colours:**
Format → Data colours → click the colour next to each category → enter hex code

#### Chart 3: Revenue by Category (Horizontal Bar Chart)
- Visual: **Bar Chart** (horizontal, not vertical)
- Y-axis: `inventory_clean[Category]`
- X-axis: `[Total Revenue]`
- Position: Bottom-left of Zone C
- Sort: Descending by Total Revenue (highest category on top)
- Bar colour: `#1A5276` with gradient effect
- Why Horizontal Bar? Categories have long names (Industrial Parts, Raw Materials). Horizontal fits text. Vertical bars would cut off the labels.

**How to sort:**
Click the three dots (...) on the visual → Sort axis → Total Revenue → Sort descending

#### Chart 4: Monthly On-Time Delivery Trend (Clustered Column Chart)
- Visual: **Clustered Column Chart**
- X-axis: `dim_date[Month Name]`
- Y-axis: `[On-Time Delivery %]`
- Second column: `[Delayed Deliveries]` (on secondary axis)
- Add a constant line at 85% (target line)
- Position: Bottom-right of Zone C
- Why Column? Monthly comparison = column. Bars are for categories. Columns are for time periods when there are fewer time points (12 months vs 36 months).

**How to add a target line:**
Format → Analytics → Constant line → Add → Value: 85 → Label: "Target" → Colour: `#C0392B`

---

### SLICERS FOR PAGE 1

Slicers are dropdown filters. Place them in the top-right corner of the header bar.

#### Slicer 1: Year Filter
- Visual: **Slicer**
- Field: `dim_date[Year]`
- Style: Dropdown (Format → Slicer settings → Style: Dropdown)
- Default selection: 2024
- Width: 120px
- Position: Top-right header area

#### Slicer 2: Quarter Filter
- Visual: **Slicer**
- Field: `dim_date[Quarter]`
- Style: Tile (buttons style)
- Shows: Q1, Q2, Q3, Q4
- Width: 180px

**How to make a Tile/Button slicer:**
After adding slicer → Format → Slicer settings → Options → Style: Tile

---

### INTERACTIONS ON PAGE 1

By default in Power BI, clicking any visual filters all other visuals on the same page.
This is called **cross-filtering** and it is already enabled by default.

**Test it:** Click "Electronics" in the Revenue by Category chart. All other visuals should update to show only Electronics data. This works automatically.

**To control which visuals filter each other:**
Click a visual → go to Format tab → Edit interactions → each other visual shows a filter icon or a highlight icon. Click the "none" icon (circle with line) to disable filtering from that visual.

For Page 1, leave all interactions at default (all visuals filter each other).

---

### DYNAMIC TITLE

Add a Text Box below the header bar:
- Text: click into the text box → type `=` then select `[Dashboard Subtitle]` measure
  - Actually in Power BI, you cannot directly reference measures in text boxes. Instead:
  - Add a **Card visual** with `[Dashboard Subtitle]` measure
  - Remove the card label
  - Set card background to transparent
  - This acts as a dynamic subtitle

---

### BEGINNER MISTAKES TO AVOID — PAGE 1

1. **Do not use a Table visual for KPIs** — tables are for detail data, not summary numbers. Use Cards.
2. **Do not use a Pie Chart** — always use Donut (more professional, can show center label).
3. **Do not put more than 6 KPI cards** — executives want quick answers, not spreadsheets.
4. **Do not forget to sort the bar chart** — unsorted bars look amateur.
5. **Do not use default Power BI blue** — you have a theme, use it. Check that bars are `#2E86C1` not the default light blue.
6. **Do not mix different time granularities on one chart** — if X-axis is months, keep it months throughout.


---

# PAGE 2: 📦 INVENTORY INTELLIGENCE

## Business Objective
Answer: "Do we have the right products in the right quantity? What needs restocking urgently?"

## Target Users
Supply Chain Managers, Warehouse Managers — people who act on stock alerts daily.

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: "Inventory Intelligence"          [Category slicer][WH slicer]│
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ Current  │ Safety   │ Fill     │ Stock-Out│Overstock │  Low Stock   │
│ Stock    │ Stock    │ Rate %   │ Rate %   │ Rate %   │  Alerts      │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┤
│ [Stock Status Donut]  │  [Inventory Value by Category - Bar]         │
│                       │                                              │
│ [Top 15 Products      │  [Fast vs Slow Movers - Scatter]             │
│  by Value - Table]    │                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### KPI CARDS (6 across top)

#### Card 1: Current Stock Total
- Measure: `[Current Stock Total]`
- Format: Whole number with comma
- Label: "Total Units in Stock"
- Icon: 📦

#### Card 2: Safety Stock Total
- Measure: `[Safety Stock Total]`
- Format: Whole number with comma
- Label: "Safety Stock Level"
- Icon: 🛡️

#### Card 3: Fill Rate %
- Measure: `[Fill Rate %]`
- Format: Decimal 1 place, suffix %
- Label: "Fill Rate"
- Conditional formatting: Green if ≥ 90%, Amber if 75–89%, Red if < 75%
- Icon: ✅

#### Card 4: Stock-Out Rate %
- Measure: `[Stock-Out Rate %]`
- Format: Decimal 1 place, suffix %
- Label: "Stock-Out Rate"
- Conditional formatting: Green if < 5%, Amber if 5–10%, Red if > 10%
- Icon: ⚠️
- Note: Lower is better. Red means urgent action needed.

#### Card 5: Overstock Rate %
- Measure: `[Overstock Rate %]`
- Format: Decimal 1 place, suffix %
- Label: "Overstock Rate"
- Icon: 📈

#### Card 6: Low Stock Alert Count
- Measure: `[Low Stock Alert Count]`
- Format: Whole number
- Label: "Restock Alerts"
- Conditional formatting: Red if > 10, Amber if 5–10, Green if < 5
- Icon: 🔴

---

### MAIN CHARTS

#### Chart 1: Stock Status Distribution (Donut)
- Visual: **Donut Chart**
- Legend: `inventory_clean[Stock_Status]`
- Values: count of products (use COUNTROWS implicitly by just dragging the field)
  - Actually drag `inventory_clean[Product_ID]` to Values, then change aggregation to Count
- Colours:
  - Out of Stock → `#C0392B` (red — critical)
  - Low Stock → `#F39C12` (amber — warning)
  - Optimal → `#1E8449` (green — good)
  - Overstock → `#2E86C1` (blue — informational)
- Add centre label showing total SKU count
- Position: Top-left of main area
- Why Donut? Stock status = proportions of categories. Perfect use case for donut.

#### Chart 2: Inventory Value by Category (Horizontal Bar)
- Visual: **Bar Chart** (horizontal)
- Y-axis: `inventory_clean[Category]`
- X-axis: `[Total Inventory Value]`
- Sort: Descending
- Colour: `#1A5276`
- Data labels: ON, format as $K or $M
- Position: Top-right of main area
- Why horizontal bar? Same reason as Page 1 — category names are long.

#### Chart 3: Low Stock Alert Table
- Visual: **Table visual**
- Columns:
  - `inventory_clean[Product_Name]`
  - `inventory_clean[Category]`
  - `inventory_clean[Current_Stock]`
  - `inventory_clean[Safety_Stock]` (renamed "Safety Level")
  - `inventory_clean[Stock_Status]`
  - `warehouses_clean[Warehouse_Name]`
- Filter this table: Add a visual-level filter → `Stock_Status` is "Out of Stock" OR "Low Stock"
- Sort: by `Current_Stock` ascending (most critical = 0 stock at top)
- Why Table? Alert data = you need the exact names and numbers. Charts cannot show individual product names clearly.
- Header colour: `#0A2342` (already set by theme)
- Alternate row colour: `#F2F4F7`
- Position: Bottom-left

**How to add visual-level filter:**
With the Table selected → look at the Filters panel on the right → under "Filters on this visual" → drag `Stock_Status` → select "Out of Stock" and "Low Stock"

#### Chart 4: Product Velocity Scatter Chart
- Visual: **Scatter Chart**
- X-axis: `inventory_clean[Current_Stock]`
- Y-axis: `[Total Revenue]` (or Total Quantity sold — from fact_orders)
- Size: `[Total Orders]`
- Details: `inventory_clean[Product_Name]`
- Colour by: `inventory_clean[Category]`
- Position: Bottom-right
- Why Scatter? Velocity analysis = relationship between 2 variables. High stock + low sales = slow mover. Low stock + high sales = fast mover. A scatter chart shows this relationship visually in one glance.

**The 4 quadrants tell the story:**
- Top-right (high stock, high sales) = Optimal
- Bottom-right (high stock, low sales) = Overstock risk
- Top-left (low stock, high sales) = Reorder urgently
- Bottom-left (low stock, low sales) = Dead stock

---

### SLICERS FOR PAGE 2

#### Slicer 1: Category
- Field: `inventory_clean[Category]`
- Style: Dropdown
- Allows multi-select (default)
- Position: Top header right side

#### Slicer 2: Warehouse
- Field: `warehouses_clean[Warehouse_Name]`
- Style: Dropdown
- Position: Next to Category slicer

#### Slicer 3: Stock Status
- Field: `inventory_clean[Stock_Status]`
- Style: Tile (buttons)
- Shows: All, Optimal, Low Stock, Out of Stock, Overstock
- Position: Below the header, above KPI cards (as a filter strip)

---

### DRILL-THROUGH ON PAGE 2

Add drill-through so users can right-click any product and see its full detail on Page 6 (Product Detail page).

**How to set up drill-through:**
On Page 6 (Product Detail — build this page later):
1. In the Visualizations panel, look for the "Drill through" section
2. Drag `inventory_clean[Product_ID]` into the "Add drill-through fields here" well
3. Power BI automatically adds a Back button on that page

Then on Page 2, right-click any row in the Table visual → Drill through → Product Detail

---

### TOOLTIP ON PAGE 2

Add a tooltip that appears when you hover over a bar in the category chart.
The tooltip shows a mini trend of that category's stock over time.

**How to set up tooltip:**
1. Create a new page — name it "TT_Inventory" (TT = tooltip)
2. In Page information → set Page type to **Tooltip**
3. Add a small Line Chart showing `[Current Stock Total]` by `dim_date[YearMonth]`
4. Filter the page by `inventory_clean[Category]`
5. Go back to Chart 2 (Inventory by Category) → Format → Tooltip → Page → select "TT_Inventory"

Now when you hover over Electronics bar, a mini popup shows the stock trend for Electronics.

---

### BEGINNER MISTAKES TO AVOID — PAGE 2

1. **Do not show ALL 200 products in the table** — always filter to just the alerts (Low Stock + Out of Stock). Showing 200 rows is overwhelming.
2. **Do not forget conditional formatting on the Fill Rate card** — without colour coding, the number has no meaning to a manager.
3. **Do not use a Line Chart for stock status** — stock status is categorical, not time-series. Use donut or bar.
4. **Do not skip the scatter chart** — it is the most analytically valuable visual on this page. Managers use it to make reorder decisions.


---

# PAGE 3: 🚚 LOGISTICS ANALYTICS

## Business Objective
Answer: "Are our shipments arriving on time? Which carriers are underperforming? Where are the delays coming from?"

## Target Users
Operations Managers, Logistics Coordinators

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: "Logistics Analytics"              [Year slicer][Carrier]   │
├────────┬────────┬────────┬────────┬────────┬────────────────────────┤
│On-Time │Delayed │Avg     │Avg     │Total   │ Delivery Status        │
│Delivery│Delivs  │Transit │Delay   │Transport│ (text KPI)            │
│  %     │ Count  │  Days  │  Days  │  Cost  │                        │
├────────┴────────┴────────┴────────┴────────┴────────────────────────┤
│ [Carrier Performance Bar Chart]  │  [Monthly Delivery Trend Line]   │
│                                  │                                  │
│ [Delay Analysis by Carrier]      │  [Transport Cost by Carrier]     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### KPI CARDS

#### Card 1: On-Time Delivery %
- Measure: `[On-Time Delivery %]`
- Conditional: Green ≥ 85, Amber 75–84, Red < 75
- Icon: ✅

#### Card 2: Delayed Deliveries
- Measure: `[Delayed Deliveries]`
- Format: Whole number
- Conditional: Red if > 500
- Icon: ❌

#### Card 3: Avg Transit Time
- Measure: `[Avg Transit Time]`
- Format: Decimal 1 place, suffix " days"
- Icon: ⏱️

#### Card 4: Avg Delay Days
- Measure: `[Avg Delay Days]`
- Format: Decimal 1 place, suffix " days"
- Conditional: Red if > 3
- Icon: ⚠️

#### Card 5: Total Transport Cost
- Measure: `[Total Transport Cost]`
- Format: Currency
- Icon: 💰

#### Card 6: Delivery Performance Status
- Measure: `[Delivery Performance Status]`
- This shows text: "Excellent", "Good", "Acceptable", or "Poor"
- Use a Card visual — it will show the text word
- Conditional formatting: colour the text
  - "Excellent" → `#1E8449`
  - "Good" → `#2E86C1`
  - "Acceptable" → `#F39C12`
  - "Poor" → `#C0392B`
- Icon: 📊

---

### MAIN CHARTS

#### Chart 1: Carrier On-Time Performance (Horizontal Bar)
- Visual: **Bar Chart** (horizontal)
- Y-axis: `logistics_clean[Carrier]`
- X-axis: `[On-Time Delivery %]`
- Sort: Descending (best carrier on top)
- Conditional bar colours:
  - Values ≥ 90: Green
  - 75–89: Amber
  - < 75: Red
- Add a constant line at 85% (the target)
- Data labels: ON, format as percentage
- Position: Top-left
- Why Horizontal Bar? Carrier names (FedEx, DHL, DB Schenker, Amazon Logistics etc) are long. Horizontal fits them. Also performance comparison between discrete categories = bar chart.

**How to add conditional colour bars:**
Format → Data colours → Turn off "Default colour" → Click "fx" (conditional formatting) → Format by: Rules → Add rules for the three ranges

#### Chart 2: Monthly Delivery Trend (Line + Column Combo)
- Visual: **Line and Clustered Column Chart**
- Shared axis: `dim_date[YearMonth]`
- Column values: Total shipments count (drag `logistics_clean[Shipment_ID]`, aggregation = Count)
- Line values: `[On-Time Delivery %]`
- Why Combo? Two different metrics (count + percentage) on one chart. Columns show volume. Line shows performance. A viewer sees at a glance whether high-volume months are also high-delay months.

**How to find this visual:**
In Visualizations panel, look for the chart that shows both bars and a line together. It is called "Line and clustered column chart".

#### Chart 3: Delay Analysis Table
- Visual: **Table**
- Columns:
  - `logistics_clean[Carrier]`
  - Count of Delayed Shipments
  - `[Avg Delay Days]`
  - Max Delay (drag `logistics_clean[Delay_Days]`, aggregation = Max)
  - `[Total Transport Cost]` (cost of delayed shipments)
- Filter: `logistics_clean[Is_Delayed]` = 1 (only show delayed records)
- Sort: By delayed count descending
- Add conditional formatting to Avg Delay Days column
- Position: Bottom-left

#### Chart 4: Transport Cost by Carrier (Treemap)
- Visual: **Treemap**
- Group: `logistics_clean[Carrier]`
- Values: `[Total Transport Cost]`
- Position: Bottom-right
- Why Treemap? You want to show proportional cost contribution — which carrier is eating the most budget. Treemap shows proportional size at a glance. A bar chart would also work but treemap is more visually striking for executives.
- Colours: Use the theme's blue gradient palette (automatic with the theme applied)

---

### SLICERS FOR PAGE 3

#### Slicer 1: Year
- Field: `dim_date[Year]`
- Style: Dropdown

#### Slicer 2: Carrier
- Field: `logistics_clean[Carrier]`
- Style: Dropdown (8 carriers in your data)

#### Slicer 3: Delivery Status
- Field: `logistics_clean[Delivery_Status]`
- Style: Tile
- Shows: All, On Time, Delayed

---

### CROSS-FILTERING ON PAGE 3

This page has excellent cross-filtering behaviour:
- Click "DHL" in the carrier bar chart → the monthly trend line updates to show only DHL performance → the delay table filters to only DHL rows → the treemap highlights DHL
- This happens automatically! No configuration needed.

**One interaction to disable:**
The Transport Cost treemap should NOT filter the On-Time Delivery cards (cost and delays are separate concerns).
- Click the Treemap → Format tab → Edit Interactions
- Click the "None" icon on each KPI card

---

### BEGINNER MISTAKES TO AVOID — PAGE 3

1. **Do not use a Line Chart for carrier comparison** — line charts imply a trend/time sequence. Carriers are categories, not time periods. Use bar chart.
2. **Do not forget the 85% target line** — without it, 82% On-Time looks fine. With it, managers instantly see they are below target.
3. **Do not show all shipment rows in the table** — filter to Delayed only. Showing 4,500 rows is useless.
4. **Do not put both Cost and On-Time % on the same axis** — they have totally different scales (dollars vs percentage). Use a combo chart with secondary axis.


---

# PAGE 4: 🤝 SUPPLIER ANALYTICS

## Business Objective
Answer: "Which suppliers are reliable? Which are risky? Who is causing delays and costing the most?"

## Target Users
Procurement Managers, Supply Chain Directors

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: "Supplier Analytics"            [Region slicer][Tier slicer]│
├────────┬────────┬────────┬────────┬────────┬────────────────────────┤
│Supplier│Avg     │Avg Lead│Total   │Excellent│ Poor                  │
│Reliab% │Delivery│ Time   │Supplier│Suppliers│ Suppliers             │
│        │Reliab% │        │  Cost  │  Count  │  Count                │
├────────┴────────┴────────┴────────┴────────┴────────────────────────┤
│ [Reliability Tier Donut]  │  [Supplier Scorecard Table]             │
│                           │                                         │
│ [Lead Time by Category    │  [Supplier Cost vs Reliability Scatter] │
│   Horizontal Bar]         │                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### KPI CARDS

#### Card 1: Supplier Reliability %
- Measure: `[Supplier Reliability %]`
- Format: Decimal 1, suffix %
- Conditional: Green ≥ 85, Amber 70–84, Red < 70
- Icon: ⭐

#### Card 2: Delivery Reliability %
- Measure: `[Delivery Reliability %]`
- Format: Decimal 1, suffix %
- Note: This is different from Supplier Reliability %. Delivery Reliability comes from actual logistics data. Supplier Reliability comes from the supplier's score field.
- Icon: 🚛

#### Card 3: Average Lead Time
- Measure: `[Average Lead Time]`
- Format: Decimal 1, suffix " days"
- Conditional: Green ≤ 14, Amber 15–21, Red > 21
- Icon: 📅

#### Card 4: Total Supplier Cost
- Measure: `[Total Supplier Cost]`
- Format: Currency, 0 decimal
- Icon: 💰

#### Card 5: Excellent Supplier Count
- Measure: `[Excellent Supplier Count]`
- Format: Whole number
- Background: Subtle green tint on the card
- Icon: 🟢

#### Card 6: Poor Supplier Count
- Measure: `[Poor Supplier Count]`
- Format: Whole number
- Background: Subtle red tint if > 0
- Conditional: Red if > 0, Green if = 0
- Icon: 🔴

---

### MAIN CHARTS

#### Chart 1: Reliability Tier Breakdown (Donut)
- Visual: **Donut Chart**
- Legend: `suppliers_clean[Reliability_Tier]`
- Values: Count of Supplier_ID
- Colours:
  - Excellent → `#1E8449`
  - Good → `#2E86C1`
  - Acceptable → `#F39C12`
  - Poor → `#C0392B`
- Position: Top-left
- Why Donut? Shows composition — what percentage of your 50 suppliers are in each tier. Critical management insight in one visual.

#### Chart 2: Supplier Scorecard (Table)
- Visual: **Table**
- Columns:
  - `suppliers_clean[Supplier_Name]`
  - `suppliers_clean[Region]`
  - `suppliers_clean[Reliability_Score]` (format as % with 1 decimal)
  - `suppliers_clean[Lead_Time]` (suffix " days")
  - `[Delivery Reliability %]` (from logistics — this requires a relationship)
  - `suppliers_clean[Supplier_Cost]` (format as currency)
  - `suppliers_clean[Reliability_Tier]`
- Sort: By Reliability_Score descending
- Apply conditional formatting to Reliability_Score:
  - Format → Cell elements → Conditional formatting → Background colour
  - Green for high scores, red for low
- Position: Top-right (larger, takes more space)
- Why Table? Procurement managers need to see each supplier by name and compare side by side. No chart can show individual supplier names + multiple metrics simultaneously.

#### Chart 3: Lead Time by Lead Time Category (Bar)
- Visual: **Bar Chart** (horizontal)
- Y-axis: `suppliers_clean[Lead_Time_Category]`
  (Express, Standard, Extended, Long Lead)
- X-axis: Count of suppliers in each category
- Colour: `#2E86C1`
- Sort: By Lead Time (Express first, Long Lead last)
- Data labels: On
- Position: Bottom-left
- Why Bar? Categorical distribution — how many suppliers fall in each lead time bucket. Simple and clear.

#### Chart 4: Cost vs Reliability Scatter (Scatter Plot)
- Visual: **Scatter Chart**
- X-axis: `suppliers_clean[Supplier_Cost]`
- Y-axis: `suppliers_clean[Reliability_Score]`
- Size: `suppliers_clean[Lead_Time]` (bigger bubble = longer lead time)
- Details: `suppliers_clean[Supplier_Name]` (shows name on hover)
- Colour by: `suppliers_clean[Reliability_Tier]`
- Position: Bottom-right
- Why Scatter? This chart answers: "Are we paying more for reliable suppliers?" If expensive suppliers are also reliable (top-right quadrant), spending is justified. If you find expensive AND unreliable suppliers (bottom-right), that requires immediate action.

**Quadrant interpretation:**
- Top-right = High cost, High reliability → Premium suppliers, justified
- Top-left = Low cost, High reliability → Best value suppliers
- Bottom-right = High cost, Low reliability → Needs urgent review
- Bottom-left = Low cost, Low reliability → Risk suppliers

---

### SLICERS FOR PAGE 4

#### Slicer 1: Region
- Field: `suppliers_clean[Region]`
- Style: Dropdown (North America, Europe, Asia Pacific, etc.)

#### Slicer 2: Reliability Tier
- Field: `suppliers_clean[Reliability_Tier]`
- Style: Tile (buttons showing Poor / Acceptable / Good / Excellent)

#### Slicer 3: Lead Time Category
- Field: `suppliers_clean[Lead_Time_Category]`
- Style: Dropdown

---

### DRILL-DOWN ON PAGE 4

Add drill-down to the Reliability Tier Donut:

1. With the donut selected, click the **drill mode** icon (the forked arrow) in the visual header
2. Now clicking a tier (e.g., "Poor") will show only Poor suppliers inside the donut
3. To come back, click the up arrow in the visual header

---

### BEGINNER MISTAKES TO AVOID — PAGE 4

1. **Do not confuse Supplier Reliability % and Delivery Reliability %** — they come from different sources. `Supplier Reliability %` averages the `Reliability_Score` column from the suppliers table (the score the supplier was given). `Delivery Reliability %` is calculated from actual logistics shipment data. Both are important.
2. **Do not skip the scatter chart** — it is the highest-value visual for procurement decisions.
3. **Do not sort the scorecard table alphabetically** — sort by reliability score. Worst performers should be visible immediately.
4. **Do not make the Supplier Name column too narrow** — supplier names are long (generated by Faker). Widen the column.


---

# PAGE 5: 🔮 FORECASTING & PREDICTIONS

## Business Objective
Answer: "What will demand look like in the next 6 months? How much should we order?"

## Target Users
Data Analysts, Demand Planners, Supply Chain Directors

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: "Forecasting & Predictions"         [Model selector]        │
├──────────────────────┬──────────────────────┬────────────┬──────────┤
│ Forecast Horizon     │ Last Historical Month│ LR MAE     │ LR MAPE  │
│ (6 Months)           │ (Dec 2024)           │            │          │
├──────────────────────┴──────────────────────┴────────────┴──────────┤
│                                                                     │
│  [Historical + Forecast Line Chart — MAIN VISUAL, full width]       │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ [Inventory Requirements Table]   │  [Model Accuracy Bar Chart]      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### LOADING FORECAST DATA

Your forecast data is already generated at:
`C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\exports\forecast_ensemble.csv`
`C:\Users\CHARAN\OneDrive\Desktop\SupplyVision\data\exports\inventory_requirements.csv`

Load these into Power BI:
1. Home → Get Data → Text/CSV
2. Load `forecast_ensemble.csv` — rename to **forecast_data** in Power Query
3. Load `inventory_requirements.csv` — rename to **inventory_requirements**

**Fix data types in Power Query:**
- forecast_data: `Month` → Date, `Forecast_Quantity` → Decimal Number
- inventory_requirements: `Month` → Date, all quantity columns → Decimal Number, `Reorder_Date` → Date

**No relationship needed for forecast tables** — they are standalone. The line chart uses Month on X-axis directly.

---

### COMBINING HISTORICAL + FORECAST DATA

You need one chart showing both historical demand AND the forecast together.
The trick is to use TWO lines on the same chart.

You already have:
- Historical monthly data in `fact_orders` (aggregated by Order_Date)
- Forecast data in `forecast_data` (Month column)

**Approach:**
1. Add a Line Chart visual
2. Shared X-axis: Use a calculated column approach — both tables have a Month/Date column
3. First Y-axis line: Historical — drag `[Total Revenue]` or create measure `Total Quantity Sold = SUM(fact_orders[Quantity])`
4. Second Y-axis line: Forecast — drag `forecast_data[Forecast_Quantity]`
5. The chart will show historical up to Dec 2024, then the forecast continues beyond

**Visually separate them:**
- Historical line: Solid, `#2E86C1`, thickness 3px
- Forecast line: Dashed, `#F39C12`, thickness 2px

**How to make a dashed line:**
Click the line on the chart → Format → Lines → Style → Dashed

**Add a vertical reference line at Dec 2024:**
Format → Analytics → Constant line → Value: the date where forecast starts → Label "Forecast Start" → Dashed, `#C0392B`

---

### KPI CARDS FOR PAGE 5

#### Card 1: Forecast Horizon
- Visual: Card
- Create a simple measure: `Forecast Horizon = "6 Months (Jan–Jun 2025)"`
- This is a text card showing the forecast period
- Icon: 📅

#### Card 2: Peak Forecast Month
- Create a measure:
  ```dax
  Peak Forecast Month =
  MAXX(forecast_data, forecast_data[Forecast_Quantity])
  ```
- Shows the highest forecasted demand value
- Icon: 📈

#### Card 3: Avg Monthly Forecast
- Create a measure:
  ```dax
  Avg Monthly Forecast =
  AVERAGE(forecast_data[Forecast_Quantity])
  ```
- Icon: 📊

#### Card 4: Total Reorder Quantity Needed
- Create a measure:
  ```dax
  Total Reorder Needed =
  SUM(inventory_requirements[Reorder_Quantity])
  ```
- Icon: 🔄

---

### MAIN CHARTS

#### Chart 1: Historical + Forecast Line (MAIN — Full Width)
- Described above in the setup section
- Make this LARGE — it should take up the full width of the page
- Height: about 400px, Width: full 1780px
- This is the hero visual of this page

#### Chart 2: Inventory Requirements Table
- Visual: **Table**
- Source: `inventory_requirements` table
- Columns:
  - Month
  - Forecast_Quantity (rename to "Predicted Demand")
  - Safety_Stock_Required
  - Reorder_Quantity (rename to "Recommended Order")
  - Reorder_Date (rename to "Order By Date")
- Sort: By Month ascending (closest month first)
- This table is the ACTION table — it tells operations what to order and when
- Why Table? This is action data. The planner needs the exact numbers to raise purchase orders.

#### Chart 3: Model Comparison Bar Chart
- Visual: **Clustered Bar Chart**
- Y-axis: Model names ("Linear Regression", "Exp. Smoothing")
- X-axis: MAE values (create a static table in Power BI: Enter Data → Model, MAE, RMSE)

**How to add model accuracy manually:**
After running `python pipeline.py`, check `data/exports/` — the pipeline prints metrics.
Create a manual table:
1. Home → Enter Data
2. Columns: Model | MAE | RMSE
3. Row 1: Linear Regression | [value from pipeline output] | [value]
4. Row 2: Exp. Smoothing | [value] | [value]
5. Name this table: **model_accuracy**

Then use this table in the bar chart.

---

### SLICERS FOR PAGE 5

#### Slicer 1: Forecast Model Selector
- Visual: **Slicer**
- Create a simple table (Enter Data) with values: "Ensemble", "Linear Regression", "Exp. Smoothing"
- Field: Model_Name column
- Style: Tile
- Note: This slicer is decorative/informational for now — full model switching requires API integration

---

### BOOKMARKS ON PAGE 5

Bookmarks save the current state of the page (which slicers are selected, which visuals are visible).

Create 3 bookmarks for this page:

**Bookmark 1: Full Historical View**
- All slicers cleared
- Shows all 36 months of history + 6-month forecast
- Name: "All Time"

**Bookmark 2: 2024 + Forecast**
- Year slicer set to 2024
- Shows only 2024 history + forecast
- Name: "2024 + Forecast"

**Bookmark 3: Forecast Only**
- Hide the historical line (click the line → Format → Lines → toggle off the historical series)
- Name: "Forecast Only"

**How to create a bookmark:**
View tab → Bookmarks pane → Add → rename it

**How to link buttons to bookmarks:**
Insert → Buttons → Blank button → Format → Action → Type: Bookmark → select your bookmark
Place 3 buttons labeled "All Time | 2024+Forecast | Forecast Only" in a row

---

### BEGINNER MISTAKES TO AVOID — PAGE 5

1. **Do not use a Bar Chart for time series forecast** — bar charts imply independent categories. A line chart shows continuity over time, which is what a forecast is.
2. **Do not forget to make the forecast line dashed** — solid line = historical data, dashed line = future prediction. This is industry standard.
3. **Do not skip the Reorder Date column** — "when to order" is more actionable than "how much to order". Both are needed.
4. **Do not put the model accuracy numbers in the forecast chart** — separate them into their own card or table. Mixing model metrics with the forecast line confuses viewers.


---

# PAGE 6: 🔍 PRODUCT DETAIL (Drill-Through Page)

## Business Objective
Deep dive into a single product. Accessed by right-clicking any product on Pages 2, 3, or 4 and selecting "Drill through → Product Detail".

## This page is NOT in the navigation bar — it is hidden and only accessible via drill-through.

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ [← Back Button]   Product Detail: {Product_Name}                    │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ Current  │ Safety   │Inventory │  Total   │ Total    │  Stock       │
│ Stock    │ Stock    │  Value   │  Orders  │ Revenue  │  Status      │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┤
│ [Order Trend Line for this product]  │ [Category comparison bar]    │
│                                      │                              │
│ [Supplier info card]                 │ [Logistics table for orders] │
└─────────────────────────────────────────────────────────────────────┘
```

## How to Set Up Drill-Through

1. Create a new page, name it **Product Detail**
2. In the Visualizations panel → Drill through section → drag `inventory_clean[Product_ID]` to the drill-through field
3. Power BI automatically adds a **Back button** on this page

## What to Add on this Page

All visuals automatically filter to the drilled-through product.

- Card: Current Stock
- Card: Safety Stock
- Card: Inventory Value
- Card: Total Revenue (from fact_orders filtered to this product)
- Card: Total Orders
- Card: Stock Status
- Line Chart: `[Total Revenue]` by `dim_date[YearMonth]` (this product's order trend)
- Table: Supplier info (Supplier Name, Lead Time, Reliability Score)
- Table: Recent shipments from logistics_clean filtered to orders for this product

---

# PART 4 — NAVIGATION SYSTEM

## Building the Left Navigation Panel

Every professional Power BI dashboard has a navigation bar so users can jump between pages.

### Step 1: Create the Navigation Panel Background

On EVERY page:
1. Insert → Shapes → Rectangle
2. Size: 200px wide × 1080px tall
3. Position: X=0, Y=0 (left edge)
4. Fill colour: `#0A2342` (dark navy)
5. No border

### Step 2: Add Navigation Buttons

On each page, add 5 navigation buttons:

1. Insert → Buttons → Blank
2. For each button:
   - Size: 180px wide × 60px tall
   - Background: `#0A2342` (same as panel, invisible border)
   - Hover background: `#1A5276` (slightly lighter navy)
   - Text: the page name with emoji
   - Font: Segoe UI, 12px, White

3. Format → Action:
   - Type: Page navigation
   - Destination: Select the page name

4. Highlight the CURRENT page button:
   - On Page 1, make the "Executive Overview" button background `#2E86C1`
   - On Page 2, make the "Inventory Intelligence" button `#2E86C1`
   - etc.

**Button positions on the left panel (Y coordinates):**
- Logo / Title text: Y=20
- Page 1 button: Y=120
- Page 2 button: Y=195
- Page 3 button: Y=270
- Page 4 button: Y=345
- Page 5 button: Y=420

### Step 3: Add the Logo

1. Insert → Image
2. You can use a simple text box saying "SV" styled nicely, or create a PNG logo
3. Place at the top of the nav panel

### Step 4: Group Navigation Elements

Select all nav panel elements → right-click → Group → name it "NavPanel"
Now you can copy-paste this group to every page and it stays aligned.

**How to copy to other pages:**
Right-click the group → Copy → go to next page → Paste → verify position is X=0, Y=0

---

# PART 5 — COMPLETE CROSS-FILTERING & INTERACTIONS MAP

## Which visuals filter which (by page)

### Page 1 (Executive Overview)
- Revenue Trend Line ↔ Order Status Donut ↔ Revenue by Category bar ↔ Delivery chart
- All visuals cross-filter each other (default)
- Exception: Year and Quarter slicers filter ALL visuals on the page

### Page 2 (Inventory Intelligence)
- Stock Status Donut → filters Table (shows only that status)
- Category Bar → filters all other visuals
- Exception: Scatter chart should NOT filter the KPI cards (disable this)
  - Click Scatter → Edit Interactions → click None on each Card

### Page 3 (Logistics)
- Carrier Bar → filters Monthly Trend + Delay Table + Treemap
- Monthly Trend → filters Carrier bar (shows which carrier was busy that month)
- Exception: Cost Treemap should NOT filter On-Time Delivery KPI cards

### Page 4 (Suppliers)
- Reliability Tier Donut → filters Scorecard Table + Scatter
- Scorecard Table row click → filters all other visuals
- Scatter click → highlights in Scorecard Table

---

# PART 6 — FORMATTING RULES (The Details That Make It Professional)

## Consistency Rules
Apply these to EVERY visual on EVERY page:

1. **Background:** White `#FFFFFF` for all visual containers
2. **Border:** Rounded corners, 8px radius, colour `#E8ECF0`
3. **Drop shadow:** ON for all cards and charts
4. **Title:** Every visual must have a title
   - Font: Segoe UI Semibold, 14px, `#0A2342`
   - Title background: White
5. **Font size:** All axis labels = 11px, all data labels = 10px

## How to Apply These Settings Fast

After formatting one visual exactly right:
1. Right-click the visual → Copy
2. Paste it where needed
3. OR: Right-click → Copy format → click another visual → right-click → Paste format

This pastes the formatting without the data. Huge time-saver.

## Number Formatting Rules

| Number Type | Format |
|-------------|--------|
| Revenue / Cost | $1,234,567 (0 decimal, $ prefix, comma) |
| Percentage | 87.5% (1 decimal, % suffix) |
| Days | 14.3 days (1 decimal, "days" suffix) |
| Stock count | 1,234 (whole number, comma) |
| Ratio | 3.45x (2 decimal, "x" suffix) |

**How to set number format on a card:**
Select card → Format → Callout value → Display units: None → Value decimal places: 1

**How to add suffix:**
Format → Callout value → Custom format → type `0.0"%"` for percentage or `0.0" days"` for days

---

# PART 7 — COMPLETE BUILD ROADMAP

## Phase 1: Setup (Day 1 — 2-3 hours)

**Step 1.1:** Install Power BI Desktop (15 min)
**Step 1.2:** Apply SupplyVision_Theme.json (5 min)
**Step 1.3:** Load all 7 CSV files through Power Query (30 min)
**Step 1.4:** Fix all data types in Power Query (20 min)
**Step 1.5:** Create dim_date using the M code (15 min)
**Step 1.6:** Load forecast_ensemble.csv and inventory_requirements.csv (10 min)
**Step 1.7:** Build all relationships in Model view (20 min)
**Step 1.8:** Create _Measures table (5 min)
**Step 1.9:** Enter ALL DAX measures (45 min — copy-paste from dax_measures.md)
**Step 1.10:** Test 5 measures to verify they return numbers (10 min)

✅ Checkpoint: All measures showing correct values in the Data pane

---

## Phase 2: Build Page 1 — Executive Overview (Day 1 — 2 hours)

**Step 2.1:** Create new page, set canvas 1920×1080 (5 min)
**Step 2.2:** Add header bar rectangle + title text (10 min)
**Step 2.3:** Add Year and Quarter slicers (10 min)
**Step 2.4:** Add all 6 KPI Cards (30 min)
**Step 2.5:** Add Revenue Trend Line Chart (20 min)
**Step 2.6:** Add Order Status Donut with custom colours (15 min)
**Step 2.7:** Add Revenue by Category horizontal bar (15 min)
**Step 2.8:** Add Delivery Trend column chart with target line (15 min)
**Step 2.9:** Test cross-filtering by clicking each visual (5 min)
**Step 2.10:** Apply conditional formatting to On-Time Delivery card (5 min)

✅ Checkpoint: Page 1 looks like a professional executive dashboard

---

## Phase 3: Build Page 2 — Inventory (Day 2 — 2 hours)

**Step 3.1:** Duplicate Page 1 (right-click page tab → Duplicate)
**Step 3.2:** Delete all visuals except nav panel and header
**Step 3.3:** Update header text to "Inventory Intelligence"
**Step 3.4:** Add 6 KPI cards with conditional formatting (30 min)
**Step 3.5:** Add Stock Status Donut with custom colours (15 min)
**Step 3.6:** Add Inventory by Category bar chart (15 min)
**Step 3.7:** Add Low Stock Alert table with visual-level filter (20 min)
**Step 3.8:** Add Product Velocity scatter chart (15 min)
**Step 3.9:** Add Category and Warehouse slicers (10 min)
**Step 3.10:** Set up drill-through target (Page 6) (10 min)

✅ Checkpoint: Low stock alerts are visible, conditional formatting works

---

## Phase 4: Build Page 3 — Logistics (Day 2 — 1.5 hours)

**Step 4.1:** Duplicate previous page, clear visuals
**Step 4.2:** Update header, add Year and Carrier slicers (10 min)
**Step 4.3:** Add 6 KPI cards (25 min)
**Step 4.4:** Add Carrier Performance horizontal bar with target line (20 min)
**Step 4.5:** Add Monthly Delivery Trend combo chart (15 min)
**Step 4.6:** Add Delay Analysis table (filtered to delayed only) (15 min)
**Step 4.7:** Add Transport Cost treemap (10 min)
**Step 4.8:** Disable treemap → card interactions (5 min)

✅ Checkpoint: Clicking a carrier filters everything on the page

---

## Phase 5: Build Page 4 — Suppliers (Day 3 — 1.5 hours)

**Step 5.1:** Duplicate, clear visuals, update header (10 min)
**Step 5.2:** Add 6 KPI cards (25 min)
**Step 5.3:** Add Reliability Tier donut (15 min)
**Step 5.4:** Add Supplier Scorecard table with conditional formatting (25 min)
**Step 5.5:** Add Lead Time category bar (10 min)
**Step 5.6:** Add Cost vs Reliability scatter (15 min)
**Step 5.7:** Add Region and Tier slicers (10 min)

✅ Checkpoint: Scatter chart shows supplier names on hover

---

## Phase 6: Build Page 5 — Forecasting (Day 3 — 2 hours)

**Step 6.1:** Duplicate, clear visuals, update header (10 min)
**Step 6.2:** Load forecast CSV files (already done in Phase 1)
**Step 6.3:** Add 4 KPI cards (20 min)
**Step 6.4:** Add Historical + Forecast combo line chart (30 min)
**Step 6.5:** Make forecast line dashed, historical solid (10 min)
**Step 6.6:** Add vertical reference line at forecast start (5 min)
**Step 6.7:** Add Inventory Requirements table (20 min)
**Step 6.8:** Create model_accuracy Enter Data table (10 min)
**Step 6.9:** Add Model Comparison bar chart (10 min)
**Step 6.10:** Add 3 bookmarks + bookmark buttons (15 min)

✅ Checkpoint: Historical ends at Dec 2024, forecast dashes continue to Jun 2025

---

## Phase 7: Build Page 6 — Product Detail Drill-Through (Day 4 — 1 hour)

**Step 7.1:** Create new page named "Product Detail"
**Step 7.2:** Set drill-through field to Product_ID
**Step 7.3:** Add 6 KPI cards (all filtered to drilled product)
**Step 7.4:** Add Order trend line chart
**Step 7.5:** Add Supplier info card
**Step 7.6:** Add logistics table
**Step 7.7:** Style the Back button (already auto-added)
**Step 7.8:** Test: Go to Page 2, right-click a product → Drill through → Product Detail

✅ Checkpoint: Drill-through works, Back button returns to Page 2

---

## Phase 8: Navigation System (Day 4 — 1 hour)

**Step 8.1:** Build navigation panel on Page 1 (rectangle + 5 buttons)
**Step 8.2:** Set button actions to page navigation
**Step 8.3:** Style active page button differently (`#2E86C1` vs `#0A2342`)
**Step 8.4:** Group nav elements
**Step 8.5:** Copy-paste nav group to all 5 main pages
**Step 8.6:** Update active button highlight on each page
**Step 8.7:** Test all navigation buttons

✅ Checkpoint: Clicking any nav button takes you to that page

---

## Phase 9: Polish & QA (Day 4 — 1 hour)

**Step 9.1:** Check all titles are correct on all pages
**Step 9.2:** Verify all numbers match (cross-check Revenue card vs line chart total)
**Step 9.3:** Verify all slicers sync within their page
**Step 9.4:** Verify drill-through and back button work
**Step 9.5:** Check all charts are sorted correctly
**Step 9.6:** Make sure conditional formatting is on all KPI cards
**Step 9.7:** Save the file as `SupplyVision.pbix`
**Step 9.8:** Export Page 1 as PDF for executive sharing
  - File → Export → Export to PDF

✅ Final Checkpoint: The dashboard is complete, professional, and fully interactive

---

## Phase 10: Optional Enhancements (Future)

- Connect to MySQL live database instead of CSV files
- Add Power BI service publish for web sharing
- Set up scheduled refresh (requires Power BI Pro license)
- Add Q&A visual for natural language queries
- Add Decomposition Tree for root cause analysis
- Publish to Power BI report server for enterprise sharing

---

# PART 8 — QUICK REFERENCE

## Most Common Beginner Power BI Actions

| Task | How to do it |
|------|-------------|
| Add a visual | Click the visual icon in Visualizations panel |
| Resize a visual | Drag the handles on the corners/edges |
| Move a visual | Drag from the centre |
| Delete a visual | Select it → press Delete key |
| Copy a visual | Ctrl+C → Ctrl+V |
| Copy formatting | Right-click → Copy → right-click another → Paste special → Formatting only |
| Sort a chart | Click ... on visual → Sort axis → choose field → Ascending/Descending |
| Add a filter | Drag field to Filters panel on the right |
| Rename a measure | Double-click measure name in Fields panel → edit |
| Undo | Ctrl+Z |
| Save | Ctrl+S |
| Preview / Read mode | Press F5 or click View → Reading view |

## Your Colour Reference Card

| Use | Hex | When |
|-----|-----|------|
| Primary background | `#0A2342` | Nav bar, headers, table headers |
| Chart primary | `#2E86C1` | Main bar/line charts |
| Chart secondary | `#1A5276` | Secondary bars, background bars |
| Page background | `#F2F4F7` | Canvas background |
| Visual background | `#FFFFFF` | Inside cards and charts |
| Good / positive | `#1E8449` | Green: on-time, in-stock, excellent |
| Warning | `#F39C12` | Amber: low stock, acceptable |
| Critical / bad | `#C0392B` | Red: out of stock, delayed, poor |
| Neutral | `#7F8C8D` | Grey: supporting info |

## File Locations

| File | Path |
|------|------|
| Theme JSON | `powerbi\SupplyVision_Theme.json` |
| DAX Measures | `powerbi\dax_measures.md` |
| Processed CSVs | `data\processed\*_clean.csv` |
| Forecast CSV | `data\exports\forecast_ensemble.csv` |
| Inventory Req | `data\exports\inventory_requirements.csv` |
| This guide | `powerbi\DASHBOARD_GUIDE.md` |
| Save .pbix here | `powerbi\SupplyVision.pbix` |

---

*End of SupplyVision Power BI Dashboard Guide*
*Estimated total build time: 12–16 hours for a beginner*
*Result: A professional enterprise-grade 5-page BI dashboard*
