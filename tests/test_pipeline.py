import csv,json,sqlite3
import pytest
from order_ops.pipeline import generate,run,validate,FIELDS

@pytest.fixture
def env(tmp_path):
    source=tmp_path/'orders.csv';generate(source,100)
    return source,tmp_path/'db.sqlite',tmp_path/'out'

def test_reconciliation(env):
    r=run(*env)
    assert (r['input_rows'],r['accepted_rows'],r['rejected_rows'])==(105,100,5)
    assert r['rejection_reasons']=={'duplicate_order_id':1,'invalid_quantity':1,'invalid_price':1,'invalid_date':1,'unknown_region':1}

def test_idempotent(env):
    one=run(*env);data=(env[2]/'data.json').read_bytes();two=run(*env)
    assert one==two and data==(env[2]/'data.json').read_bytes()
    with sqlite3.connect(env[1]) as db: assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==100

def test_accounting(env):
    run(*env)
    with sqlite3.connect(env[1]) as db:
        cents=db.execute("SELECT SUM(net_cents) FROM orders WHERE status='delivered'").fetchone()[0]
        monthly=db.execute('SELECT SUM(revenue) FROM monthly_revenue').fetchone()[0]
    assert monthly==pytest.approx(cents/100)

def test_contract_does_not_replace_good_snapshot(env):
    run(*env); env[0].write_text('wrong,header\n1,2\n')
    with pytest.raises(ValueError):run(*env)
    with sqlite3.connect(env[1]) as db:assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==100

def base():return dict(zip(FIELDS,['O1','2026-01-01','C1','Cairo','Books','3','12.75','10','delivered']))

def test_money_rounding(): assert validate(base())[-1]==3442

@pytest.mark.parametrize('field,value',[('quantity','0'),('quantity','x'),('unit_price','Infinity'),('unit_price','1.001'),('discount_pct','101'),('discount_pct','NaN'),('status','oops'),('customer_id',''),('ordered_at','yesterday'),('category','Other')])
def test_validation(field,value):
    row=base();row[field]=value
    with pytest.raises(ValueError):validate(row)

def test_cancelled_not_revenue(env):
    run(*env)
    data=json.loads((env[2]/'data.json').read_text())
    assert sum(x['revenue'] for x in data['quality']['monthly'])==pytest.approx(sum(x['net_cents']/100 for x in data['orders'] if x['status']=='delivered'))
