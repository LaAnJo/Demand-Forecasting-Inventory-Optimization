

-- 1. Fastest-moving high-value SKUs by trailing annual sales.
SELECT p.sku, p.product_name, a.abc_class, a.annual_revenue_gbp, a.annual_units
FROM abc_analysis a JOIN products p USING(sku)
ORDER BY a.annual_revenue_gbp DESC LIMIT 10;

-- 2. Inventory purchase priority list.
SELECT sku, product_name, abc_class, on_hand_units, inventory_position_units,
       reorder_point_units, reorder_quantity_units, stockout_probability,
       ROUND(suggested_purchase_cost_gbp,2) AS planned_spend_gbp
FROM inventory_recommendations
WHERE reorder_flag='REORDER'
ORDER BY stockout_probability DESC, annual_revenue_gbp DESC;

-- 3. Mix of ABC inventory exposure and procurement spend.
SELECT abc_class, COUNT(*) AS skus,
       SUM(CASE WHEN stockout_risk_band='HIGH' THEN 1 ELSE 0 END) AS high_risk_skus,
       ROUND(SUM(suggested_purchase_cost_gbp),2) AS suggested_spend_gbp
FROM inventory_recommendations GROUP BY abc_class ORDER BY abc_class;

-- 4. Month-over-month demand and sales value from historical actuals.
SELECT substr(date,1,7) AS month,
       SUM(units_sold) AS sold_units, ROUND(SUM(revenue_gbp),2) AS revenue_gbp
FROM daily_sales GROUP BY substr(date,1,7) ORDER BY month;

-- 5. Which SKUs were over/under-predicted in TEST?
SELECT sku, ROUND(SUM(predicted_units-units_sold),1) AS unit_bias,
       ROUND(100.0*SUM(ABS(predicted_units-units_sold))/NULLIF(SUM(units_sold),0),1) AS wape_pct
FROM forecast_test GROUP BY sku ORDER BY wape_pct DESC LIMIT 10;
