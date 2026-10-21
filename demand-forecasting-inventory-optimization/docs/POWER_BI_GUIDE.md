# Power BI dashboard: build instructions (approximately 90–120 min)

The `.pbix` report is intentionally **not** fabricated; use these files to create your actual clickable report in Power BI Desktop.

## A. Import CSVs

Open Power BI Desktop → **Home → Get data → Text/CSV**, select:

- `data/processed/daily_sales.csv` → rename table **FactSales**
- `data/processed/product_master.csv` → **DimProduct**
- `outputs/future_forecast.csv` → **FactForecast**
- `outputs/forecast_test.csv` → **FactForecastTest**
- `outputs/abc_analysis.csv` → **ABC**
- `outputs/inventory_recommendations.csv` → **InventoryPlan**
- `outputs/model_comparison.csv` → **ModelResults**

**Power Query:** Change `date` fields to *Date*, unit quantities to whole/decimal as appropriate, selling price/revenue/purchase cost to Decimal Number, and `sku` to Text. Check null keys and duplicates. `InventoryPlan[stockout_probability]` is 0–1 decimal; format it as Percentage in the model.

## B. Relationships (Model view)

Use **DimProduct[sku]** as 1-side, one-to-many, single-direction relationships to the `sku` keys in FactSales, FactForecast, FactForecastTest, InventoryPlan and ABC. Do not directly connect two fact tables. If Power BI shows ambiguity, delete the accidental direct relationships.

Add a Date dimension via Modeling → **New table**:

```DAX
DimDate =
CALENDAR (
    MIN ( FactSales[date] ),
    MAX ( FactForecast[date] )
)
```

Rename its generated `[Date]` column if necessary; connect `DimDate[Date]` to `FactSales[date]`, `FactForecast[date]` and `FactForecastTest[date]`. Mark DimDate as a date table. Date slicers on a future-only period will naturally blank out historical actuals; this is expected, not a broken measure.

## C. Measures (Modeling → New measure)

```DAX
Actual Units = SUM ( FactSales[units_sold] )

Historical Revenue GBP = SUM ( FactSales[revenue_gbp] )

Future Forecast Units = SUM ( FactForecast[predicted_units] )

Test WAPE % =
DIVIDE (
    SUMX (
        FactForecastTest,
        ABS ( FactForecastTest[units_sold] - FactForecastTest[predicted_units] )
    ),
    SUM ( FactForecastTest[units_sold] )
)

Test MAE Units =
AVERAGEX (
    FactForecastTest,
    ABS ( FactForecastTest[units_sold] - FactForecastTest[predicted_units] )
)

High Risk SKU Count =
CALCULATE (
    DISTINCTCOUNT ( InventoryPlan[sku] ),
    InventoryPlan[stockout_risk_band] = "HIGH"
)

Reorder SKU Count =
CALCULATE (
    DISTINCTCOUNT ( InventoryPlan[sku] ),
    InventoryPlan[reorder_flag] = "REORDER"
)

Suggested Purchase Spend GBP =
SUM ( InventoryPlan[suggested_purchase_cost_gbp] )

ABC A Revenue GBP =
CALCULATE ( SUM ( ABC[annual_revenue_gbp] ), ABC[abc_class] = "A" )
```

Format `Test WAPE %` as **Percentage** (WAPE is stored as 0–1 in this DAX measure, not as 0–100). Never relabel WAPE as “forecast accuracy %.”

## D. Page 1 — Executive Overview

**Canvas size:** 16:9. Add a title: *Demand Forecasting & Inventory Optimization — Simulation*.

1. **Five Cards**: Historical Revenue GBP, Future Forecast Units, Test WAPE %, High Risk SKU Count and Suggested Purchase Spend GBP.
2. **Line chart**: X axis `DimDate[Date]`; Y axes Actual Units and Future Forecast Units. Filter to last 56 historical days plus next 28 forecast days, or place separate trend charts to avoid misleading long gaps.
3. **Bar chart**: Axis DimProduct[category], Values Historical Revenue GBP.
4. **Donut / stacked bar**: Axis ABC[abc_class], Values ABC[annual_revenue_gbp]. One-to-many relationships should filter class values consistently.
5. **Slicers**: DimProduct[category], DimProduct[sku]. Note: do not filter the KPI card measures through both ABC and inventory fact without checking cross-filter logic.
6. **Text footer**: “Sales, inventory and lead times are synthetic; risk and purchase recommendations are scenario outputs, not observed results.”

## E. Page 2 — Inventory Action Center

1. **Table** from InventoryPlan with: sku, product_name, abc_class, forecast_next_28d_units, expected_daily_demand, on_hand_units, on_order_units, lead_time_days, safety_stock_units, reorder_point_units, stockout_probability, reorder_quantity_units, suggested_purchase_cost_gbp, reorder_flag.
2. Sort stockout_probability descending. Conditional formatting: red for >=0.7, amber for 0.3–0.7, green for below 0.3.
3. Filters: reorder_flag = REORDER; ABC class slicer; category slicer. Enable a separate full-inventory view by clearing the flag filter.
4. **Scatter chart**: X = InventoryPlan[onhand_days_of_cover], Y = InventoryPlan[stockout_probability], Details = InventoryPlan[sku]; bubble size = annual_revenue_gbp. Check aggregation is *Don't summarize* for numeric one-row-per-SKU columns.
5. **Insight panel**: example “Risk is estimated from normal lead-time demand, assuming fixed lead time and no known inbound delivery schedule.”

## F. Page 3 — Forecast quality (optional but strong for interviews)

1. Line chart Date vs actual (`FactForecastTest[units_sold]`) and predicted (`FactForecastTest[predicted_units]`).
2. SKU slicer.
3. Matrix with SKU and Test WAPE %; optionally bar chart of absolute errors.
4. Small table of ModelResults for validation and test MAE/WAPE. Only the validation rows contain the head-to-head comparison. The test row is *only* the validation-selected winner.

## G. Quality checklist

- Are `sku` fields text throughout?
- Are date fields converted from CSV text to Date?
- Does a SKU slicer affect both actual and forecast charts? (relationship test)
- Does Page 2 clearly distinguish projected reorder quantities from actual historical purchases?
- Do the example KPIs match `outputs/kpi_summary.csv` (allow rounding)?
- Is the source caveat clearly visible?

When complete, save `reports/demand_inventory_dashboard.pbix` and export at least two screenshots to `charts/`. The zipped starter does NOT include this file because it is a genuine Power BI Desktop task.
