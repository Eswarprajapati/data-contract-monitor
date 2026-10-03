from contextlib import closing
"""Configurable CSV data contracts with persisted quality results."""
import csv,json,sqlite3,math
from pathlib import Path
from datetime import datetime,timezone

def evaluate(file,contract,now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('now must be timezone aware')
    with Path(file).open(newline='') as f:
        reader=csv.DictReader(f); columns=reader.fieldnames or []; rows=list(reader)
    findings=[]
    def check(name,passed,details): findings.append({'check':name,'passed':bool(passed),'details':details})
    missing=sorted(set(contract['required_columns'])-set(columns))
    check('schema',not missing,{'missing_columns':missing})
    check('minimum_rows',len(rows)>=contract.get('minimum_rows',1),{'row_count':len(rows)})
    for field in contract.get('not_null',[]):
        count=sum(not (row.get(field) or '').strip() for row in rows)
        check('not_null:'+field,count==0,{'invalid_rows':count})
    for field in contract.get('unique',[]):
        values=[row.get(field) for row in rows if row.get(field)]
        count=len(values)-len(set(values))
        check('unique:'+field,count==0,{'duplicate_count':count})
    for field,bounds in contract.get('numeric_ranges',{}).items():
        count=0
        for row in rows:
            try:
                v=float(row.get(field,''))
                if not math.isfinite(v) or not bounds[0]<=v<=bounds[1]: count+=1
            except (ValueError,TypeError): count+=1
        check('range:'+field,count==0,{'invalid_rows':count})
    for field,allowed in contract.get('allowed_values',{}).items():
        count=sum(row.get(field) not in allowed for row in rows)
        check('allowed:'+field,count==0,{'invalid_rows':count})
    fresh=contract.get('freshness')
    if fresh:
        ages=[]; invalid=0
        for row in rows:
            try:
                t=datetime.fromisoformat(row.get(fresh['column'],'').replace('Z','+00:00'))
                if t.tzinfo is None: raise ValueError('Missing timezone')
                age=(now-t).total_seconds()
                if age<0: invalid+=1
                ages.append(age)
            except (ValueError,TypeError): invalid+=1
        oldest=max(ages) if ages else None
        check('freshness',invalid==0 and oldest is not None and oldest<=fresh['max_age_seconds'],
              {'oldest_age_seconds':oldest,'invalid_timestamps':invalid})
    return {'dataset':contract['dataset'],'source':Path(file).name,'checked_at':now.isoformat(),
            'passed':all(x['passed'] for x in findings),'checks':findings}

def persist(report,database):
    with closing(sqlite3.connect(database)) as c, c:
        c.execute('CREATE TABLE IF NOT EXISTS quality_runs(id INTEGER PRIMARY KEY, dataset TEXT,checked_at TEXT,passed INTEGER,report_json TEXT)')
        c.execute('INSERT INTO quality_runs(dataset,checked_at,passed,report_json) VALUES (?,?,?,?)',
                  [report['dataset'],report['checked_at'],int(report['passed']),json.dumps(report)])
