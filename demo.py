import argparse,json
from pathlib import Path
from datetime import datetime
from monitor import evaluate,persist
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',default='data/good.csv')
    p.add_argument('--as-of',default='2026-01-01T12:00:00+00:00')
    args=p.parse_args(); contract=json.loads(Path('contracts/orders.json').read_text())
    report=evaluate(args.input,contract,datetime.fromisoformat(args.as_of))
    Path('results').mkdir(exist_ok=True)
    persist(report,'results/quality.sqlite')
    Path('results/report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2)); raise SystemExit(0 if report['passed'] else 1)
