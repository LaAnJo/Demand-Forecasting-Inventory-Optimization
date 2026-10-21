# Business and modeling logic — why each step exists

## 1. What operations teams need

A useful forecast is not the end product. The output should tell an inventory planner **how many units to buy and which products need attention**. A product can have strong sales but enough inventory, and a low-value product can be at high risk of stocking out. This project separates forecasts (predictions) from operational decisions (policy assumptions).

## 2. What the data means

- Each `daily_sales` row is one SKU on one date. `units_sold` is observed sales, not necessarily uncensored customer demand.
- Synthetic sample: 30 SKUs × 731 days = 21,930 SKU-days; generated with seasonality, trend, noise and unmodeled promotions.
- A true retail company would have stockout logs, supplier service histories, order minimum quantities, supply capacity, calendar of store closures, and promotion plans. These are absent.
- Zero-sale days are genuine in the synthetic sample. In transactional datasets, zero recorded sales could instead indicate closures/stockouts and must be investigated.
- Revenue is `units_sold × unit_price`; currency **GBP (£)**.

## 3. Feature leakage and forecast horizon

If you model demand for December 15, `rolling_7` must summarize December 8–14, **not include December 15**. We compute `shift(1).rolling(7)` and use prior sales only. Do not randomly split time-series rows. The test period is an honest future horizon: first select the model on the earlier validation window, retrain without test dates, and evaluate once on the final holdout.

A one-step model used to forecast 28 days could cheat by incorporating actual future observations into lag features. Here, `recursive_forecast()` extends sales history with yesterday's **predicted** sales at each horizon step. This accumulates forecast error as a real long-horizon forecast does. The 4-week seasonal baseline follows the same no-peeking principle.

## 4. Forecast metrics and interpretation

- **MAE**: mean absolute unit error per SKU-day (units).
- **RMSE**: square root of mean squared unit error; penalizes larger misses.
- **WAPE**: `100 × sum(abs(actual - predicted)) / sum(abs(actual))`, computed on all SKU-day rows. May exceed 100%; unreliable with tiny actual total. *Lower is better.*
- **Bias %**: `100 × sum(predicted - actual)/sum(abs(actual))`; positive = overforecasting.
- **Model selection**: compare validation WAPE for simple baseline vs gradient boosting; do not pick winners based on test score. Reporting test WAPE **does not mean “we improved business by X%.”**

## 5. ABC prioritization

Rank each SKU by trailing 365-day **sales revenue**. Compute running contribution to total revenue. Start each SKU in A while the *preceding* cumulative share is below 80%; B until the preceding cumulative share reaches 95%; C after that. A does NOT mean 80% of SKUs; typically a small share of items contributes a large share of revenue, though the exact mix varies. Our classes apply only to included SKUs.

Decisions: check A SKUs frequently, use suitable service targets and avoid stockouts; for C SKUs, weigh holding and ordering costs. Class alone should **not** decide safety stock in a production policy.

## 6. Safety stock, reorder point and order quantity

Assumptions: expected daily demand `d`, standard deviation of daily demand `σ_d`, fixed supplier lead time `L`, 95% one-sided cycle-service proxy `z=1.64485` and weekly review interval `R=7` days. With independent daily demand and constant lead time:

- Safety stock (`SS`) = `ceil(z × σ_d × sqrt(L))`.
- Expected lead-time demand = `d × L`.
- Reorder point (`ROP`) = `ceil(d × L + SS)`.
- Inventory position = `on_hand + on_order − backorders`.
- If inventory position <= ROP, order enough to bring it to `ceil(d × (L + R) + SS)`; otherwise recommend 0.

**Worked example**: `d=20 units/day`, `σ_d=5`, `L=4 days`, `on_hand=80`, `on_order=0`, `R=7`. `SS=ceil(1.64485×5×sqrt(4))=17`, `ROP=ceil(80+17)=97`, target `ceil(20×11+17)=237`, reorder quantity `237−80=157` units. Before approving an actual order, check MOQ, packs, expiry, capacity, budget and lead-time uncertainty.

**Caveat:** This combines a reorder-point trigger with an order-up-to review horizon as a simple teaching approximation. A formal periodic-review policy typically sizes safety stock for `L+R`, not just `L`; this demo intentionally keeps the simple 95% lead-time safety-stock expression. Adapt the policy to your organization's ordering cadence before use.

## 7. Modeled stockout probability

Let lead-time demand approximately follow `Normal(d×L, σ_d×sqrt(L))`; the probability of exhausting **on-hand** stock before delivery is `P(Demand_L > on_hand)`. High `>=70%`, medium `30–70%`, low `<30%`. This is **modeled risk**, not observed stockout frequency. Inbound orders count toward *inventory position* for the order trigger but are excluded from immediate on-hand risk because their promised arrival dates are unknown.

## 8. Why a machine-learning model can lose

Tree models may not outperform simple baselines for sparse, intermittent or highly seasonal products. That is why validation selects whichever has lower WAPE. We do not tune by peeking into the held-out test set. Future enhancements: rolling-origin cross-validation, per-SKU model selection, Croston/TSB for intermittent demand, explicit promotions known ahead, calibration of lead-time demand quantiles, costs and fill-rate simulations.

## 9. Business value without inflated claims

You *can* say the model identifies **17 simulated SKU replenishment actions** and compare forecast error to baseline. You *cannot* say it reduced stockouts by 20%, lowered carrying costs, or generated savings without before/after evidence or a validated counterfactual simulation with assumptions clearly stated.
