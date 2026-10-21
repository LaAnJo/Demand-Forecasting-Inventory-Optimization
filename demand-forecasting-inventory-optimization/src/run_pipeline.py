"""Chronological ML validation and interpretable inventory recommendations.
Run from repository root: python -m src.run_pipeline
"""
from pathlib import Path
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from src.business_logic import SERVICE_Z, compute_abc, inventory_policy, forecast_metrics

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'processed'; OUT=ROOT/'outputs'; CHART=ROOT/'charts'; DB=ROOT/'inventory_analytics.sqlite'
LAGS=[1,7,14,28]
FEATURES=['sku_idx','day_of_week','month','day_of_year_sin','day_of_year_cos','lag_1','lag_7','lag_14','lag_28','avg_7','avg_28','std_28']

def date_parts(d):
    return dict(day_of_week=d.dayofweek,month=d.month,day_of_year_sin=np.sin(2*np.pi*d.dayofyear/365.25),day_of_year_cos=np.cos(2*np.pi*d.dayofyear/365.25))

def make_training_features(df, sku_ids):
    z=df[['date','sku','units_sold']].copy().sort_values(['sku','date'])
    z['sku_idx']=z['sku'].map(sku_ids).astype('category')
    z['day_of_week']=z.date.dt.dayofweek
    z['month']=z.date.dt.month
    z['day_of_year_sin']=np.sin(2*np.pi*z.date.dt.dayofyear/365.25)
    z['day_of_year_cos']=np.cos(2*np.pi*z.date.dt.dayofyear/365.25)
    grouped=z.groupby('sku')['units_sold']
    for lag in LAGS:z[f'lag_{lag}']=grouped.shift(lag)
    for window in [7,28]:
        z[f'avg_{window}']=z.groupby('sku')['units_sold'].transform(lambda x: x.shift(1).rolling(window).mean())
    z['std_28']=z.groupby('sku')['units_sold'].transform(lambda x: x.shift(1).rolling(28).std(ddof=0))
    return z.dropna().reset_index(drop=True)

def fit_model(df, sku_ids):
    z=make_training_features(df, sku_ids)
    if len(z)<100:raise ValueError('Not enough observations for 28-day features')
    model=HistGradientBoostingRegressor(max_iter=125,max_leaf_nodes=27,learning_rate=.07,l2_regularization=3.0,
                                         categorical_features=['sku_idx'],random_state=42)
    model.fit(z[FEATURES],z.units_sold)
    return model

def recursive_forecast(history,sku_ids, horizon, model=None):
    """True multi-step forecast. NEVER read actual demand from forecast horizon."""
    if any(v<28 for v in history.groupby('sku').size()):raise ValueError('Each SKU needs >=28 history days')
    prior={sku:history.loc[history.sku==sku].sort_values('date').units_sold.astype(float).tolist() for sku in sku_ids}
    last=history.date.max(); skus=list(sku_ids)
    rows=[]
    for offset in range(1,horizon+1):
        d=last+pd.Timedelta(days=offset); extra=date_parts(d)
        step=[]
        for sku in skus:
            vals=np.asarray(prior[sku],dtype=float)
            rec=dict(sku=sku,date=d,sku_idx=sku_ids[sku],**extra)
            for lag in LAGS:rec[f'lag_{lag}']=float(vals[-lag])
            rec['avg_7']=float(vals[-7:].mean());rec['avg_28']=float(vals[-28:].mean());rec['std_28']=float(vals[-28:].std())
            step.append(rec)
        features=pd.DataFrame(step)
        features['sku_idx']=features.sku_idx.astype('category').cat.set_categories(range(len(sku_ids)))
        if model is None:
            predictions=[np.mean([prior[sku][-lag] for lag in [7,14,21,28]]) for sku in skus]
        else:predictions=model.predict(features[FEATURES]).tolist()
        for sku,val in zip(skus,predictions):
            pred=max(0,float(val));prior[sku].append(pred)
            rows.append(dict(date=d,sku=sku,predicted_units=round(pred,4)))
    return pd.DataFrame(rows)

def evaluate(a,p, method, split):
    z=a[['date','sku','units_sold']].merge(p,on=['date','sku'],validate='one_to_one')
    metrics=forecast_metrics(z.units_sold,z.predicted_units)
    return dict(split=split,model=method,**metrics),z

def save_csv(df,name):df.to_csv(OUT/name,index=False)

def chart_forecast(sales,future):
    hist=sales.groupby('date',as_index=False)['units_sold'].sum().tail(56)
    fc=future.groupby('date',as_index=False)['predicted_units'].sum()
    fig,ax=plt.subplots(figsize=(11,4.5))
    ax.plot(hist.date,hist.units_sold,label='Historical actual units',linewidth=2)
    ax.plot(fc.date,fc.predicted_units,label='Forecast (next 28 days)',linewidth=2)
    ax.axvline(sales.date.max(),linestyle='--',color='gray',alpha=.7)
    ax.set(title='Aggregate demand: historical vs. forward forecast',ylabel='Units / day',xlabel='Date')
    ax.legend(); fig.autofmt_xdate();fig.tight_layout()
    fig.savefig(CHART/'demand_forecast.png',dpi=175);plt.close(fig)

def chart_abc(abc):
    v=abc.sort_values('annual_revenue_gbp',ascending=False).reset_index(drop=True)
    v['cum_pct']=v.annual_revenue_gbp.cumsum()/v.annual_revenue_gbp.sum()*100
    fig,ax=plt.subplots(figsize=(10,4.5))
    ax.bar(range(len(v)),v.annual_revenue_gbp,color='#3b82f6',alpha=.65,label='SKU revenue')
    ax2=ax.twinx();ax2.plot(range(len(v)),v.cum_pct,color='#c2410c',linewidth=2,label='Cumulative %')
    ax2.axhline(80,linestyle='--',color='#a16207');ax2.axhline(95,linestyle='--',color='#a16207')
    ax2.set_ylim(0,107);ax.set(ylabel='Revenue (£)',xlabel='Products ranked by annual revenue',title='ABC / Pareto classification');ax2.set_ylabel('Cumulative revenue (%)')
    fig.tight_layout();fig.savefig(CHART/'abc_pareto.png',dpi=175);plt.close(fig)

def main():
    for f in ['daily_sales.csv','product_master.csv','inventory_snapshot.csv']:
        if not (DATA/f).exists():raise FileNotFoundError(f'Missing {f}. First: python -m src.generate_sample_data')
    OUT.mkdir(parents=True,exist_ok=True);CHART.mkdir(parents=True,exist_ok=True)
    sales=pd.read_csv(DATA/'daily_sales.csv',parse_dates=['date']).sort_values(['date','sku'])
    products=pd.read_csv(DATA/'product_master.csv');inv=pd.read_csv(DATA/'inventory_snapshot.csv')
    required={'date','sku','units_sold','revenue_gbp'}
    assert required.issubset(sales.columns)
    assert (sales.units_sold>=0).all() and sales[['date','sku']].duplicated().sum()==0
    assert not sales[['date','sku','units_sold']].isna().any().any()
    skus=sorted(sales.sku.unique());sku_ids={sku:i for i,sku in enumerate(skus)}
    assert len(sales)==len(skus)*sales.date.nunique(),'Needs a complete daily series for every SKU'
    assert sales.date.nunique()>=120,'Need at least 120 days'
    final_date=sales.date.max()
    test_start=final_date-pd.Timedelta(days=27)
    val_start=test_start-pd.Timedelta(days=28)
    train=sales[sales.date<val_start].copy()
    train_val=sales[sales.date<test_start].copy()
    val_actual=sales[(sales.date>=val_start)&(sales.date<test_start)].copy()
    test_actual=sales[sales.date>=test_start].copy()
    print(f'Train through {train.date.max():%Y-%m-%d}; validate {val_start:%Y-%m-%d} to {test_start-pd.Timedelta(days=1):%Y-%m-%d}; test {test_start:%Y-%m-%d} to {final_date:%Y-%m-%d}')
    val_ml=recursive_forecast(train,sku_ids,28,fit_model(train,sku_ids))
    val_seasonal=recursive_forecast(train,sku_ids,28)
    metric_ml,val_detail_ml=evaluate(val_actual,val_ml,'Gradient Boosting','validation')
    metric_seasonal,val_detail_baseline=evaluate(val_actual,val_seasonal,'Seasonal 4-week average','validation')
    winner='Gradient Boosting' if metric_ml['wape_pct']<metric_seasonal['wape_pct'] else 'Seasonal 4-week average'
    model_test=fit_model(train_val,sku_ids) if winner=='Gradient Boosting' else None
    test_pred=recursive_forecast(train_val,sku_ids,28,model_test)
    metric_test,test_detail=evaluate(test_actual,test_pred,winner,'test')
    eval_df=pd.DataFrame([metric_ml,metric_seasonal,metric_test]).round(4)
    save_csv(eval_df,'model_comparison.csv')
    save_csv(val_detail_ml.assign(model='Gradient Boosting'),'forecast_validation_ml.csv')
    save_csv(val_detail_baseline.assign(model='Seasonal 4-week average'),'forecast_validation_baseline.csv')
    save_csv(test_detail.assign(model=winner),'forecast_test.csv')
    forward_model=fit_model(sales,sku_ids) if winner=='Gradient Boosting' else None
    future=recursive_forecast(sales,sku_ids,28,forward_model)
    save_csv(future,'future_forecast.csv')
    trailing=sales[sales.date>=final_date-pd.Timedelta(days=364)]
    abc=trailing.groupby('sku',as_index=False).agg(annual_revenue_gbp=('revenue_gbp','sum'),annual_units=('units_sold','sum'))
    abc=abc.sort_values('annual_revenue_gbp',ascending=False).reset_index(drop=True)
    abc['abc_class']=compute_abc(abc.annual_revenue_gbp.values)
    abc['revenue_share_pct']=(100*abc.annual_revenue_gbp/abc.annual_revenue_gbp.sum()).round(2)
    abc['cumulative_revenue_pct']=abc.revenue_share_pct.cumsum().round(2)
    abc=abc.merge(products[['sku','product_name','category']],on='sku',validate='one_to_one')
    save_csv(abc,'abc_analysis.csv')
    recent=sales[sales.date>=final_date-pd.Timedelta(days=89)].groupby('sku').units_sold.agg(daily_std_units=lambda x: x.std(ddof=0),historical_daily_demand='mean').reset_index()
    proj=future.groupby('sku',as_index=False).predicted_units.sum().rename(columns={'predicted_units':'forecast_next_28d_units'})
    planner=products.merge(inv,on='sku',validate='one_to_one',suffixes=('','_inventory')).merge(abc[['sku','annual_revenue_gbp','abc_class']],on='sku').merge(recent,on='sku').merge(proj,on='sku')
    planner['expected_daily_demand']=planner.forecast_next_28d_units/28
    policies=[inventory_policy(float(x.expected_daily_demand),float(x.daily_std_units),int(x.lead_time_days),int(x.on_hand_units),int(x.on_order_units),int(x.backorders_units)) for x in planner.itertuples()]
    policy_frame=pd.DataFrame(policies)
    planner=pd.concat([planner.reset_index(drop=True),policy_frame],axis=1)
    planner['onhand_days_of_cover']=np.where(planner.expected_daily_demand>0,planner.on_hand_units/planner.expected_daily_demand,np.nan)
    planner['suggested_purchase_cost_gbp']=(planner.reorder_quantity_units*planner.unit_cost_gbp).round(2)
    planner['source_note']='Actual sales if imported; inventory/lead times simulated if using UCI adapter' if (sales.source!='SYNTHETIC').any() else 'ALL INPUT DATA SYNTHETIC'
    planner=planner.sort_values(['stockout_probability','annual_revenue_gbp'],ascending=[False,False]).reset_index(drop=True)
    planner=planner.round({'forecast_next_28d_units':2,'expected_daily_demand':3,'daily_std_units':3,'stockout_probability':4,'onhand_days_of_cover':1,'historical_daily_demand':2})
    save_csv(planner,'inventory_recommendations.csv')
    kpi=pd.DataFrame([dict(as_of_date=str(final_date.date()),dataset_source='SYNTHETIC' if (sales.source=='SYNTHETIC').all() else 'UCI REAL TRANSACTIONS + SIMULATED INVENTORY',
                           sku_count=len(skus),annual_revenue_gbp=round(float(abc.annual_revenue_gbp.sum()),2),
                           forecast_next_28d_units=round(float(future.predicted_units.sum()),1),
                           test_wape_pct=round(metric_test['wape_pct'],2),test_mae_units=round(metric_test['mae'],2),
                           selected_model=winner,high_risk_skus=int((planner.stockout_risk_band=='HIGH').sum()),
                           skus_needing_reorder=int((planner.reorder_flag=='REORDER').sum()),
                           suggested_purchase_cost_gbp=round(float(planner.suggested_purchase_cost_gbp.sum()),2))])
    save_csv(kpi,'kpi_summary.csv')
    with sqlite3.connect(DB) as conn:
        for df,tbl in [(sales,'daily_sales'),(products,'products'),(inv,'inventory_snapshot'),(abc,'abc_analysis'),(planner,'inventory_recommendations'),(future,'future_forecast'),(test_detail,'forecast_test'),(eval_df,'model_comparison')]:
            d=df.copy()
            for c in d.columns:
                if pd.api.types.is_datetime64_any_dtype(d[c]):d[c]=d[c].dt.strftime('%Y-%m-%d')
            d.to_sql(tbl,conn,if_exists='replace',index=False)
        conn.executescript("""CREATE INDEX IF NOT EXISTS idx_sales_sku_date ON daily_sales(sku,date);
             CREATE INDEX IF NOT EXISTS idx_forecast_sku_date ON future_forecast(sku,date);
             CREATE VIEW IF NOT EXISTS inventory_actions AS SELECT sku,product_name,abc_class,on_hand_units,
                 reorder_point_units,reorder_quantity_units,stockout_risk_band,suggested_purchase_cost_gbp
                 FROM inventory_recommendations WHERE reorder_flag='REORDER';""")
    chart_forecast(sales,future);chart_abc(abc)
    print('Model comparison:')
    print(eval_df.to_string(index=False));print('Selected via VALIDATION WAPE:',winner)
    print('Reorder SKUs:',kpi.iloc[0]['skus_needing_reorder'],'High-risk SKUs:',kpi.iloc[0]['high_risk_skus'])
    print('Generated outputs/, charts/, inventory_analytics.sqlite')

if __name__=='__main__':main()
