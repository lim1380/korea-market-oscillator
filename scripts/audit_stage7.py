#!/usr/bin/env python3
"""Read-only stage 7 audit. V7 stored scores are NOT a score generation engine.
Checks archived V7 results, cross-references KRX KOSPI observations, never sends trade signals.
"""
import csv
import gzip
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'data'/'v7_legacy_reference.csv.gz'
INDEX=ROOT/'data'/'kospi_index_history.json'
STAGE5=ROOT/'data'/'stage5_latest.json'
STAGE6=ROOT/'data'/'stage6_latest.json'


def load():
    if not REF.is_file():raise RuntimeError(f'Missing {REF.relative_to(ROOT)}')
    with gzip.open(REF,'rt',encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    if not rows:raise RuntimeError('V7 source records empty')
    dates=[]
    for r in rows:
        d=r['date']
        datetime.strptime(d,'%Y-%m-%d')
        dates.append(d)
        if r['action'] not in ('BUY','SELL','HOLD'):
            raise RuntimeError(f'Invalid V7 event on {d}')
        for key in ('kospi_close','sell_risk_score','integrated_exposure'):
            x=float(r[key]);
            if not math.isfinite(x):raise RuntimeError(f'Invalid {key} on {d}')
        for key in ('buy_score_v6','sell_risk_score'):
            if r[key] and not 0<=float(r[key])<=100:
                raise RuntimeError(f'{key} outside 0..100 on {d}')
        if float(r['integrated_exposure']) not in (0,0.5,1):
            raise RuntimeError(f'Exposure invalid on {d}')
    if dates!=sorted(set(dates)):
        raise RuntimeError('V7 duplicate or unordered dates')
    return rows


def main():
    rows=load()
    actions=Counter(r['action'] for r in rows)
    missing=sum(not r['buy_score_v6'] for r in rows)
    historical={r['date'].replace('-',''):float(r['kospi_close']) for r in rows}
    print(f'V7 HISTORY VALID: {len(rows)} rows from {rows[0]["date"]} to {rows[-1]["date"]}')
    print(f'V7 events (stored labels, NOT regenerated): BUY={actions["BUY"]} SELL={actions["SELL"]} HOLD={actions["HOLD"]}')
    print(f'V7 missing V6 scores: {missing}')
    if not INDEX.exists():raise RuntimeError('Stage 5 KOSPI history JSON missing')
    records=json.loads(INDEX.read_text(encoding='utf-8'))
    if not isinstance(records,list):raise RuntimeError('Stage 5 KOSPI history not list')
    actual={str(r['date']):float(r['close']) for r in records}
    overlap=sorted(set(actual)&set(historical))
    if len(overlap)<50:raise RuntimeError(f'Not enough KOSPI overlapping trading days: {len(overlap)}')
    diff=[(day,historical[day],actual[day],abs(historical[day]-actual[day])) for day in overlap]
    largest=sorted(diff,key=lambda x:x[3],reverse=True)[:5]
    print(f'KOSPI CLOSE AUDIT: {len(overlap)} overlapping days, max absolute difference={largest[0][3]:.4f}')
    for d,h,a,e in largest:print(f'  {d}: archived={h:.4f}, KRX={a:.4f}, abs_difference={e:.4f}')
    if any(x[3]>0.05 for x in diff):
        raise RuntimeError('V7 vs KRX KOSPI price mismatch >0.05 index points; investigate reference before scoring')
    for p in (STAGE5,STAGE6):
        if not p.exists():raise RuntimeError(f'Missing {p.name}')
    a=json.loads(STAGE5.read_text(encoding='utf-8'))
    b=json.loads(STAGE6.read_text(encoding='utf-8'))
    if a['date']!=b['date']:raise RuntimeError('Stage5/Stage6 dates differ')
    print('Current Stage5/6 agreed date:',a['date'])
    print('Critical: V7 saved scores end on',rows[-1]['date'], '; today score is NOT available from this archive.')
    print('Required before live signal: exact V6 fear/trend/RSI transform and V7 trend-break/volatility-percentile/reversal formulas, stateful 5-day trade logic, and walk-forward verification.')
    print('STAGE7 REFERENCE AUDIT PASSED; SIGNAL STATUS: NOT_CALCULATED')

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('STAGE7 AUDIT FAILED:',e,file=sys.stderr)
        sys.exit(1)
