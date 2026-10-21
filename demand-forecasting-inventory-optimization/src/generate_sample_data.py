"""Deterministic fictional retailer (NOT actual company data)."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'processed'

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(42)
    dates=pd.date_range('2024-01-01','2025-12-31',freq='D')
    categories=['Home','Personal Care','Stationery','Electronics','Kitchen']
    products=[]; sales=[]; snapshots=[]
    for i in range(30):
        sku=f'SKU-{i+1:03d}'; category=categories[i%5]
        price=round(float(rng.uniform(8,90)),2)
        cost=round(price*float(rng.uniform(0.48,0.78)),2)
        lead=int(rng.integers(3,19))
        base=float(rng.uniform(3.5,24.0))
        trend=float(rng.uniform(-0.0003,0.0009))
        yearly=float(rng.uniform(.05,.30))
        weekly=float(rng.uniform(.08,.38))
        products.append([sku,f'{category} Product {i+1:02d}',category,price,cost,lead,'SYNTHETIC'])
        prev=[]
        for j,d in enumerate(dates):
            weekday=1 + weekly*(1 if d.dayofweek in [4,5] else (-0.35 if d.dayofweek in [0,1] else 0))
            annual=1+yearly*np.sin(2*np.pi*(j/365.25+ i/12))
            promo=int(rng.random()<0.035)
            lam=max(.01,base*(1+trend*j)*weekday*annual*(1.6 if promo else 1))
            units=int(rng.poisson(lam))
            # occasional spikes and slowdowns
            if rng.random()<0.004:units=int(units*2.2)
            if rng.random()<0.007:units=0
            prev.append(units)
            sales.append([d.strftime('%Y-%m-%d'),sku,units,round(units*price,2),promo,'SYNTHETIC'])
        recent=float(np.mean(prev[-90:]))
        on_hand=int(round(recent*rng.uniform(0.3,18)))
        on_order=int(round(recent*rng.uniform(0,8))) if rng.random()<0.35 else 0
        snapshots.append([sku,on_hand,on_order,0,dates[-1].strftime('%Y-%m-%d'),'SYNTHETIC'])
    pd.DataFrame(products,columns=['sku','product_name','category','unit_price_gbp','unit_cost_gbp','lead_time_days','source']).to_csv(DATA/'product_master.csv',index=False)
    pd.DataFrame(sales,columns=['date','sku','units_sold','revenue_gbp','promotion_flag','source']).to_csv(DATA/'daily_sales.csv',index=False)
    pd.DataFrame(snapshots,columns=['sku','on_hand_units','on_order_units','backorders_units','snapshot_date','source']).to_csv(DATA/'inventory_snapshot.csv',index=False)
    print(f'Generated {len(sales):,} daily observations, {len(products)} simulated SKUs. NOT real sales/inventory data.')

if __name__=='__main__':main()
