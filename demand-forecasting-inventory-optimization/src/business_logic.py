"""Pure functions for inventory policies and forecast accuracy."""
import math
from statistics import NormalDist
import numpy as np

SERVICE_Z = 1.6448536269514722  # standard normal: 95% one-sided cycle service

def forecast_metrics(actual, predicted):
    a = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if a.shape != p.shape or a.size == 0:
        raise ValueError('actual and predicted must be same non-empty shape')
    e = p-a
    denom = np.abs(a).sum()
    return {
        'mae': float(np.abs(e).mean()),
        'rmse': float(np.sqrt(np.mean(e**2))),
        'wape_pct': float(100*np.abs(e).sum()/denom) if denom > 0 else float('nan'),
        'bias_pct': float(100*e.sum()/denom) if denom > 0 else float('nan'),
    }

def compute_abc(revenues):
    """Return ABC classes in ORIGINAL input order. A/B/C by share before SKU."""
    r = np.asarray(revenues,dtype=float)
    if r.ndim != 1 or len(r)==0 or np.any(r<0):
        raise ValueError('nonempty nonnegative revenue vector required')
    order = np.argsort(-r, kind='stable')
    total = r.sum()
    ans = ['C']*len(r)
    before = 0.0
    for idx in order:
        share_before = before/total if total>0 else 1.0
        ans[int(idx)] = 'A' if share_before < 0.8 else ('B' if share_before < 0.95 else 'C')
        before += r[idx]
    return ans

def inventory_policy(mean_demand, daily_std, lead_time_days, on_hand, on_order=0, backorders=0, review_period_days=7, z=SERVICE_Z):
    """Approximate periodic-review policy; lead time fixed and independent daily demand."""
    if min(mean_demand,daily_std,lead_time_days,on_hand,on_order,backorders,review_period_days) < 0:
        raise ValueError('nonnegative inventory inputs required')
    sigma_l = daily_std * math.sqrt(lead_time_days)
    lead_time_mean = mean_demand * lead_time_days
    safety_stock = math.ceil(z * sigma_l)
    reorder_point = math.ceil(lead_time_mean + safety_stock)
    position = int(on_hand+on_order-backorders)
    target_stock = math.ceil(mean_demand*(lead_time_days+review_period_days)+safety_stock)
    order_quantity = max(0, target_stock-position) if position<=reorder_point else 0
    if sigma_l == 0:
        risk = 1.0 if on_hand < lead_time_mean else 0.0
    else:
        risk = NormalDist(mu=lead_time_mean,sigma=sigma_l).cdf(on_hand)
        risk = 1-risk
    return dict(safety_stock_units=safety_stock,reorder_point_units=reorder_point,
                inventory_position_units=position,target_stock_units=target_stock,
                reorder_quantity_units=order_quantity,stockout_probability=float(risk),
                stockout_risk_band='HIGH' if risk>=0.7 else ('MEDIUM' if risk>=0.3 else 'LOW'),
                reorder_flag='REORDER' if position<=reorder_point else 'OK')
