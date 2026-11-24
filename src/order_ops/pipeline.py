"""Deterministic CSV -> validated SQLite warehouse -> dashboard artifacts."""
import argparse, csv, hashlib, json, random, sqlite3
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS=['order_id','ordered_at','customer_id','region','category','quantity','unit_price','discount_pct','status']
REGIONS={'Cairo','Alexandria','Giza','Fayoum'}
CATEGORIES={'Electronics','Home','Books','Clothing'}
STATUSES={'delivered','cancelled','returned','pending'}

def generate(path, count=2400):
    rng=random.Random(42); rows=[]
    for i in range(count):
        rows.append(dict(zip(FIELDS,[f'ORD-{i+1:05}',str(date(2026,1,1)+timedelta(days=rng.randrange(300))),f'C-{rng.randrange(1,401):04}',rng.choice(sorted(REGIONS)),rng.choice(sorted(CATEGORIES)),rng.randrange(1,6),f'{rng.randrange(1000,90000)/100:.2f}',rng.choice([0,0,5,10,15]),rng.choices(['delivered','cancelled','returned','pending'],[78,8,9,5])[0]])))
    rows += [rows[0].copy(),dict(rows[1],quantity='-2'),dict(rows[2],order_id='BAD-1',unit_price='NaN'),dict(rows[3],order_id='BAD-2',ordered_at='2026-02-30'),dict(rows[4],order_id='BAD-3',region='Unknown')]
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    return len(rows)

def validate(row):
    if not row['order_id'].strip() or not row['customer_id'].strip(): raise ValueError('missing_identifier')
    try: date.fromisoformat(row['ordered_at'])
    except ValueError: raise ValueError('invalid_date')
    if row['region'] not in REGIONS: raise ValueError('unknown_region')
    if row['category'] not in CATEGORIES: raise ValueError('unknown_category')
    if row['status'] not in STATUSES: raise ValueError('unknown_status')
    try:
        q=int(row['quantity']); price=Decimal(row['unit_price']); discount=Decimal(row['discount_pct'])
        if q<1 or q>1000: raise ValueError('invalid_quantity')
        if not price.is_finite() or price<=0 or price>1000000 or price.as_tuple().exponent < -2: raise ValueError('invalid_price')
        if not discount.is_finite() or discount<0 or discount>100: raise ValueError('invalid_discount')
        cents=int((price*q*(100-discount)).quantize(Decimal('1')))
    except (InvalidOperation,OverflowError): raise ValueError('invalid_number')
    return (row['order_id'],row['ordered_at'],row['customer_id'],row['region'],row['category'],q,int(price*100),str(discount),row['status'],cents)

SCHEMA="""
CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY, ordered_at TEXT NOT NULL,customer_id TEXT NOT NULL, region TEXT NOT NULL,category TEXT NOT NULL,quantity INTEGER CHECK(quantity>0),unit_cents INTEGER CHECK(unit_cents>0),discount_pct TEXT,status TEXT,net_cents INTEGER CHECK(net_cents>=0));
CREATE TABLE IF NOT EXISTS runs(source_sha256 TEXT PRIMARY KEY,input_rows INTEGER,accepted_rows INTEGER,rejected_rows INTEGER);
CREATE VIEW IF NOT EXISTS monthly_revenue AS
WITH m AS (SELECT substr(ordered_at,1,7) month, SUM(CASE WHEN status='delivered' THEN net_cents ELSE 0 END)/100.0 revenue FROM orders GROUP BY 1)
SELECT month,revenue,LAG(revenue) OVER(ORDER BY month) previous_revenue FROM m;
"""

def run(source, database, output):
    source=Path(source); output=Path(output);output.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest(); accepted=[]; rejected=[]; seen=set()
    with source.open(newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS: raise ValueError('CSV columns do not match contract')
        for line,row in enumerate(reader,2):
            try:
                item=validate(row)
                if item[0] in seen: raise ValueError('duplicate_order_id')
                seen.add(item[0]);accepted.append(item)
            except (ValueError,TypeError,KeyError) as exc: rejected.append({'line':line,'reason':str(exc),'row':row})
    # Each source is a complete snapshot, not an append. Atomic replacement prevents partial refreshes.
    with sqlite3.connect(database) as db:
        db.executescript(SCHEMA)
        with db:
            db.execute('DELETE FROM orders')
            db.executemany('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?)',accepted)
            db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?)',(digest,len(accepted)+len(rejected),len(accepted),len(rejected)))
        db.row_factory=sqlite3.Row
        data=[dict(r) for r in db.execute('SELECT order_id,ordered_at,customer_id,region,category,status,net_cents FROM orders ORDER BY ordered_at,order_id')]
        monthly=[dict(r) for r in db.execute('SELECT * FROM monthly_revenue ORDER BY month')]
    report={'source_sha256':digest,'currency':'EGP','dataset':'Synthetic demo, not a real business','input_rows':len(accepted)+len(rejected),'accepted_rows':len(accepted),'rejected_rows':len(rejected),'rejection_reasons':dict(Counter(r['reason'] for r in rejected)),'monthly':monthly}
    (output/'quality.json').write_text(json.dumps(report,indent=2))
    (output/'quarantine.json').write_text(json.dumps(rejected,indent=2))
    (output/'data.json').write_text(json.dumps({'quality':report,'orders':data}))
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--generate',action='store_true');ap.add_argument('--source',default='data/orders.csv');ap.add_argument('--database',default='warehouse.sqlite');ap.add_argument('--output',default='site');a=ap.parse_args()
    if a.generate: generate(a.source)
    print(json.dumps(run(a.source,a.database,a.output),indent=2))
if __name__=='__main__': main()
