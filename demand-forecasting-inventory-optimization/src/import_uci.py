"""OPTIONAL: prepare real transaction-demand history from UCI Online Retail .xlsx.
Download the CC-BY-4.0 source from https://archive.ics.uci.edu/dataset/352/online-retail
Then: python -m src.import_uci --input path/to/'Online Retail.xlsx'
This replaces the bundled synthetic sales AND simulates inventory (not present in UCI).
Run: python -m src.run_pipeline
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

DATA=Path(__file__).resolve().parents[1]/'data'/'processed'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path,help='Path to downloaded Online Retail.xlsx (22.6 MB)')
    parser.add_argument('--max-skus',type=int,default=30)
    args=parser.parse_args()
    raw=pd.read_excel(args.input,engine='openpyxl',dtype={'StockCode':str,'InvoiceNo':str})
    n_raw=len(raw)
    raw['InvoiceDate']=pd.to_datetime(raw['InvoiceDate'],errors='coerce')
    raw['Quantity']=pd.to_numeric(raw['Quantity'],errors='coerce')
    raw['UnitPrice']=pd.to_numeric(raw['UnitPrice'],errors='coerce')
    raw=raw.dropna(subset=['InvoiceDate','StockCode','Quantity','UnitPrice'])
    raw=raw[(raw.Quantity>0)&(raw.UnitPrice>0)]
    raw=raw[~raw.InvoiceNo.str.upper().str.startswith('C',na=False)]
    raw=raw[raw.StockCode.str.fullmatch(r'[0-9A-Z]{5,6}',na=False)]
    raw['date']=raw.InvoiceDate.dt.normalize()
    raw['revenue_gbp']=raw.Quantity*raw.UnitPrice
    last=raw.date.max()
    # Top SKUs with actual movement late in the observation window.
    recent=raw[raw.date>=last-pd.Timedelta(days=90)]
    candidates=recent.groupby('StockCode').agg(n_days=('date','nunique'),recent_revenue=('revenue_gbp','sum'))
    good=candidates[candidates.n_days>=12].sort_values('recent_revenue',ascending=False).head(args.max_skus).index
    raw=raw[raw.StockCode.isin(good)].copy()
    if raw.StockCode.nunique()<5:raise ValueError('Not enough high-frequency products after cleaning')
    # Missing transaction days are zero recorded sales, NOT proof of zero underlying demand.
    start=last-pd.Timedelta(days=364)
    dates=pd.date_range(start,last,freq='D')
    grid=pd.MultiIndex.from_product([dates,sorted(good)],names=['date','sku']).to_frame(index=False)
    daily=raw[(raw.date>=start)&(raw.date<=last)].groupby(['date','StockCode'],as_index=False).agg(units_sold=('Quantity','sum'),revenue_gbp=('revenue_gbp','sum'))
    daily=daily.rename(columns={'StockCode':'sku'})
    daily=grid.merge(daily,on=['date','sku'],how='left')
    daily[['units_sold','revenue_gbp']]=daily[['units_sold','revenue_gbp']].fillna(0)
    daily['units_sold']=daily.units_sold.astype(int)
    daily['revenue_gbp']=daily.revenue_gbp.round(2)
    daily['promotion_flag']=0  # unknown; not inferred
    daily['source']='UCI_REAL_SALES'
    rng=np.random.default_rng(42)
    master=[];snap=[]
    for sku in sorted(good):
        x=raw[raw.StockCode==sku]
        description=x.Description.dropna().astype(str).mode()
        name=description.iloc[0][:75] if len(description) else f'StockCode {sku}'
        price=float(x.UnitPrice.median())
        # UCI has no product category/cost/lead-time/on-hand fields.
        lead=int(rng.integers(3,19)); cost=round(price*.65,2)
        master.append([sku,name,'Uncategorized (UCI)',round(price,2),cost,lead,'UCI_SALES + ASSUMED_COST_LEAD'])
        avg=float(daily.loc[daily.sku==sku].tail(90).units_sold.mean())
        on_hand=round(avg*float(rng.uniform(2,18)))
        on_order=round(avg*float(rng.uniform(0,8))) if rng.random()<.35 else 0
        snap.append([sku,int(on_hand),int(on_order),0,last.strftime('%Y-%m-%d'),'SIMULATED_INVENTORY'])
    DATA.mkdir(parents=True,exist_ok=True)
    daily.to_csv(DATA/'daily_sales.csv',index=False)
    pd.DataFrame(master,columns=['sku','product_name','category','unit_price_gbp','unit_cost_gbp','lead_time_days','source']).to_csv(DATA/'product_master.csv',index=False)
    pd.DataFrame(snap,columns=['sku','on_hand_units','on_order_units','backorders_units','snapshot_date','source']).to_csv(DATA/'inventory_snapshot.csv',index=False)
    print(f'Imported {len(raw):,}/{n_raw:,} filtered real transaction rows; {len(good)} SKUs, {len(dates)} days.')
    print('Inventory balances, cost and lead time are FICTIONAL ASSUMPTIONS; no realized savings can be inferred.')

if __name__=='__main__':main()
