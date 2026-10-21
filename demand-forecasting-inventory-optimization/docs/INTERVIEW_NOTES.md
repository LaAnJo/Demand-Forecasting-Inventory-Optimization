# 90-second walkthrough and common questions

**Problem:** I modeled daily demand by SKU and translated a 28-day forecast into practical inventory decisions: ABC importance, safety stock, reorder point and purchasing priority.

**Data:** The bundled first version uses a two-year **synthetic** retailer. I explicitly distinguish historical sales from simulated inventory and do not assert observed operational savings. I also included an optional real-data importer using UCI Online Retail sales; its inventory policies remain assumption-based.

**Modeling:** I used an honest date split, a four-week seasonal baseline and a pooled histogram gradient boosting regressor. Lagged features were shifted to prevent leakage. Each forecast day recursively consumes previous predictions, not actual future demand. I selected the winner on validation WAPE, tested once on an untouched horizon, then refit for 28 future days.

**Decision layer:** Revenue-based ABC flags important SKUs. I combine average forward demand and historical demand variability with assumed supplier lead time to calculate safety stock and reorder triggers. SQL and Power BI help expose which products warrant planner attention. Excel allows lead-time and service assumptions to be changed interactively.

**Limits:** Real results require stockout histories, true inventory positions and actual supplier lead-time observations. Demand variability may not be normally distributed; service level and safety stock are only approximate. I've avoided claiming any actual cost reduction.

## Interview Q&A

**Q: Why time-based validation?** A: Random splitting puts observations from the future into model training, producing unrealistically optimistic accuracy and potentially leaking rolling features.

**Q: What is WAPE?** A: Absolute errors summed over SKU-days divided by all actual units, multiplied by 100. It is interpretable as error relative to sales volume; lower is better, and it can exceed 100%.

**Q: Why not claim 95% of orders fill?** A: A z-score in a fixed-lead-time normal model roughly targets a single-cycle stockout probability, not the fill rate. Fill rate requires demand units short, not just likelihood of any shortage.

**Q: What's the difference between on-hand and inventory position?** A: On-hand is physically available; inventory position adds outstanding receipts and subtracts backorders. Unknown shipment arrival dates make immediate stockout risk harder to quantify.

**Q: What if an item sells only every few weeks?** A: Evaluate intermittent-demand baselines such as Croston or TSB and rethink WAPE on tiny denominators; don't assume one pooled ML model is universally best.

**Q: How would you improve the project?** A: Replace synthetic stock records with ERP transactions; ingest actual supplier lead-time distributions, backorders, MOQ, known promotions; use rolling-origin backtests and a cost/service-level inventory simulation.
