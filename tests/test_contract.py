from contextlib import closing
import json,tempfile,sqlite3,unittest
from pathlib import Path
from datetime import datetime
from monitor import evaluate,persist
class ContractTests(unittest.TestCase):
    def setUp(self):
        self.contract=json.loads(Path('contracts/orders.json').read_text())
        self.now=datetime.fromisoformat('2026-01-01T12:00:00+00:00')
    def test_good_data_passes(self): self.assertTrue(evaluate('data/good.csv',self.contract,self.now)['passed'])
    def test_bad_data_detects_multiple_failures(self):
        r=evaluate('data/bad.csv',self.contract,self.now)
        bad={x['check'] for x in r['checks'] if not x['passed']}
        self.assertEqual(bad,{'unique:order_id','range:amount','allowed:status','freshness'})
    def test_freshness_uses_all_rows(self):
        r=evaluate('data/bad.csv',self.contract,self.now)
        self.assertFalse(next(x for x in r['checks'] if x['check']=='freshness')['passed'])
    def test_missing_schema_and_empty_file_fail(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'empty.csv'; p.write_text('amount,status\n')
            self.assertFalse(evaluate(p,self.contract,self.now)['passed'])
    def test_history_persisted(self):
        with tempfile.TemporaryDirectory() as t:
            db=Path(t)/'history.sqlite'; r=evaluate('data/good.csv',self.contract,self.now)
            persist(r,db); persist(r,db)
            with closing(sqlite3.connect(db)) as c: self.assertEqual(c.execute('select count(*) from quality_runs').fetchone()[0],2)
