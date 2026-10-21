import math
import pytest
from src.business_logic import inventory_policy,compute_abc,forecast_metrics

def test_rop_formula():
    r=inventory_policy(20,5,4,on_hand=80,on_order=0,z=1.64485362695)
    assert r['safety_stock_units']==17
    assert r['reorder_point_units']==97
    assert r['inventory_position_units']==80
    assert r['reorder_quantity_units']>0

def test_abc():
    assert compute_abc([80,15,5])==['A','B','C']

def test_no_zero_demand_crash():
    r=inventory_policy(0,0,4,on_hand=0)
    assert r['reorder_quantity_units']==0
    assert r['stockout_probability']==0

def test_metrics():
    m=forecast_metrics([10,20],[10,22])
    assert math.isclose(m['wape_pct'],100*2/30)
    assert math.isclose(m['mae'],1.0)
