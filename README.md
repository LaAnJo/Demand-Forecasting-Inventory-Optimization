# Demand Forecasting & Inventory Optimization

**Python · SQL (SQLite) · Power BI · Advanced Excel · Machine Learning**

An end-to-end, interview-ready **demonstration** of demand forecasting and inventory planning for 30 SKUs. The included starter dataset is **100% synthetic** (2024-01-01 through 2025-12-31): no real business customers, supplier lead times, inventory balances, outcomes or savings. The script can be adapted to real UCI transaction data with inventory assumptions explicitly labeled.

## Business question

> Given daily historical product sales, which items will we need over the next 28 days, which ones generate most of our sales value, and which products should be reordered to reduce forecasted stockout exposure?

**Decisions supported**: SKU demand projection, ABC category, inventory days of cover, reorder flag, reorder quantity and an approximate probability of exhausting on-hand stock before lead-time demand arrives.

## Repository contents

```text
demand-forecasting-inventory-optimization/
├── src/
│   ├── generate_sample_data.py  # regenerate sample inputs (seed 42)
│   ├── run_pipeline.py          # leakage-safe ML evaluation + inventory outputs
│   ├── import_uci.py            # optional real transactions, synthetic inventory
│   └── business_logic.py       # ABC, safety stock, ROP, WAPE
├── data/processed/
│   ├── daily_sales.csv          # 21,930 rows of fictional daily SKU demand
│   ├── product_master.csv       # price, cost, lead time
│   └── inventory_snapshot.csv   # on-hand and on-order balances
├── outputs/                    # forecasts, evaluation, ABC, inventory actions
├── charts/                     # 2 Python visuals
├── reports/                    # editable formula-driven Excel planner
├── sql/01_analytics.sql        # 5 analytical SQL queries
├── docs/POWER_BI_GUIDE.md      # relationship diagram, visuals and DAX
├── docs/BUSINESS_LOGIC.md      # methods, interpretation, assumptions, caveats
├── docs/INTERVIEW_NOTES.md     # portfolio pitch and Q&A
├── tests/test_business_logic.py
├── inventory_analytics.sqlite # local SQLite output
└── requirements.txt
```

## First run — Windows PowerShell

Requires Python 3.10+, VS Code (optional), Power BI Desktop for the visualization step, and Excel to inspect the planner.

```powershell
cd demand-forecasting-inventory-optimization
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.run_pipeline
python -m pytest -q
```

The repository includes sample inputs and computed outputs, so running the pipeline refreshes the results. To **generate a fresh but identical** fictional dataset: `python -m src.generate_sample_data` followed by `python -m src.run_pipeline`. The seed is 42.

Mac/Linux: `python3 -m venv .venv && source .venv/bin/activate` and then the same remaining commands. If the activation policy blocks PowerShell activation, use `.\.venv\Scripts\python.exe -m src.run_pipeline` directly without activation.

### datasets and how to use them

| File | Description | Power BI visual |
|---|---|---|
| `outputs/kpi_summary.csv` | Dataset status, test WAPE, suggested purchase spending | KPI overview |
| `outputs/model_comparison.csv` | Two validation models + selected test model | Model comparison |
| `outputs/forecast_test.csv` | Held-out actuals vs predictions | Error tracking |
| `outputs/future_forecast.csv` | Daily SKU predictions for next 28 days | Demand by date/SKU |
| `outputs/abc_analysis.csv` | Revenue ranking and ABC class | Pareto / category split |
| `outputs/inventory_recommendations.csv` | Calculated safety stock, ROP, stockout risk, reorder qty | Action table |
| `data/processed/daily_sales.csv` | Source daily historical sales | Trend / volume / revenue |

## Data model

- **FactDailySales**: one row per `date` × `sku`, with units, revenue, and a promotion flag (not used in modeling).
- **DimProduct**: one row per SKU with product name, category and unit selling price/cost.
- **FactForecast**: one row per future `date` × `sku`; historical observations are not used for these future predictions.
- **InventoryPlan**: one row per SKU for a single inventory snapshot; reorder recommendations are simulated decisions, **not purchase orders**.
- **FactForecastTest**: one row per held-out `date` × `sku`, with actual and predicted units.

## End-to-end analytical method

1. **Business framing**: forecast SKU-level daily units and prioritize replenishment, not merely predict revenue.
2. **Quality checks**: check missing keys, duplicates, negative sales, date continuity and complete SKU-date grid. Transaction returns must be handled before aggregation.
3. **Feature engineering**: day of week, month, cyclical day of year, lags 1/7/14/28, rolling means 7/28, 28-day rolling SD. Every rolling value is `shift(1)` to avoid using the day's answer as an input.
4. **Split by time**: initial training through 2025-11-05; validation 2025-11-06 to 2025-12-03; test 2025-12-04 to 2025-12-31. **No shuffle.**
5. **Baseline**: average of the same weekday in the past four weeks; recursively extend predictions across the future.
6. **Machine learning**: pooled histogram gradient boosting with SKU treated as a categorical feature; recursive 28-day out-of-sample prediction. For each future step, later lags use previous **predictions**, not unseen future actuals.
7. **Select on validation WAPE**; retrain the winner on train+validation, then evaluate *once* on untouched test dates. Refit winner on all historical sales for the next 28-day forecast.
8. **ABC**: rank all included SKUs by trailing-365-day sales revenue; assign A through 80% cumulative value, B through 95%, C the remainder. Boundary SKUs stay in the class they entered (classes can slightly exceed 80/95%).
9. **Safety stock**: use a 95% one-sided z-score, historical 90-day daily standard deviation and **fixed** assumed supplier lead time. Reorder point = lead-time forecast demand + safety stock.
10. **Inventory actions**: use stock position (`on_hand + on_order - backorders`) for reorder decisions. If at/below ROP, recommend ordering up to the lead-time plus 7-day review horizon, including safety stock.
11. **Risk ranking**: approximate probability of lead-time demand exceeding **on-hand** inventory under a normal distribution. It does not account for actual inbound shipment timing, stockouts that censor sales, lead-time variability, promotions, capacity, MOQ or ordering cost.
12. **Decision layer**: produce SQLite tables and Excel formulas, then build the recommended Power BI report.

## Results (included reproducible SYNTHETIC run)

- 30 items, 21,930 product-day observations (731 days).
- 28-day held-out test WAPE **21.53%** for the validation-selected gradient boosting method.
- 17 simulated SKUs triggered a reorder; 13 have high modeled stockout probability (> or equal to 70%).
- These numbers are not real operational improvements, measured service levels or financial savings.





