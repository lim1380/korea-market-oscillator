#!/usr/bin/env python3
"""Read-only test of V7 formula-reproduction readiness.
Never invent historical scores or publish BUY/SELL without full formulas.
"""
import csv, gzip, json, sys, math, datetime as dt
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'data/v7_legacy_reference.csv.gz'
OUTPUT=ROOT/'data/v7_formula_readiness.json'

REQUIRED_TRANSFORMS={
 'buy_fear_E':'Underlying E fear composition, source normalization, lookback and missing-value rules',
 'buy_trend':'KOSPI trend 0-100 transform and exact lookback/thresholds',
 'buy_rsi_rebound':'RSI window, short bounce rules and conversion to 0-100',
 'sell_trend_break':'Trend-break 0-100 transform and inputs',
 'sell_volatility_rank':'Volatility percentile historical window and warmup',
 'sell_reversal':'Reversal-risk transform and calculation order',
 'trade_state':'5-session evaluation cadence, minimum holding, initial exposure and transition conditions'
}

def main():
 if not LEGACY.exists():raise RuntimeError('V7 legacy reference missing')
 with gzip.open(LEGACY,'rt',encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
 if not rows or len(rows)<2000:raise RuntimeError(f'Legacy V7 row count unexpected: {len(rows)}')
 dates=[r['date'] for r in rows]
 if dates!=sorted(set(dates)):raise RuntimeError('Legacy dates not unique/increasing')
 for r in rows:
  if r['action'] not in ('BUY','SELL','HOLD'):raise RuntimeError('Unknown historical action')
  for k in ('kospi_close','sell_risk_score','integrated_exposure'):
   if not math.isfinite(float(r[k])):raise RuntimeError('Invalid '+k)
 missing=sum(r['buy_score_v6']=='' for r in rows)
 counts=Counter(r['action'] for r in rows)
 current={}
 for name in ('krx_latest','breadth_latest','stage5_latest','stage6_latest'):
  p=ROOT/f'data/{name}.json'
  if not p.exists():raise RuntimeError(f'Missing existing JSON {p.name}')
  current[name]=json.loads(p.read_text(encoding='utf8'))['date']
 if len(set(current.values()))!=1:raise RuntimeError(f'Current JSON dates disagree: {current}')
 # Validate simple published aggregate relationships, but not unknown subscore transforms.
 score_components={'buy':{'fear':.30,'trend':.45,'rsi_bounce':.25,'extreme_fear_bonus_if_E_at_most_15':15},
                   'sell':{'trend_break':.55,'volatility_percentile':.25,'reversal':.20}}
 if abs(sum(score_components['buy'][k] for k in ('fear','trend','rsi_bounce'))-1)>1e-12:raise RuntimeError('Weights invalid')
 if abs(sum(score_components['sell'].values())-1)>1e-12:raise RuntimeError('Weights invalid')
 report={
  'audit':'V7 score formula reproducibility, not signal generation',
  'legacy_rows':len(rows),'legacy_start':dates[0],'legacy_end':dates[-1],
  'stored_signal_counts':dict(counts),'missing_buy_score_rows':missing,
  'live_data_dates':current,'published_weights':score_components,
  'missing_transform_definitions':REQUIRED_TRANSFORMS,
  'score_reproduced':False,'new_signal_calculated':False,
  'status':'BLOCKED_MISSING_ORIGINAL_FORMULAS',
  'next_required':'Provide original V6/V7 calculation source code and corresponding raw features; then replay full historical daily scores and compare dates, scores, positions and trades before enabling signal publication.'
 }
 OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(f'REFERENCE VERIFIED: {len(rows)} days; BUY={counts["BUY"]}, SELL={counts["SELL"]}, HOLD={counts["HOLD"]}; missing buy scores={missing}')
 print('LIVE JSON DATE ALIGNMENT:',current)
 for k,v in REQUIRED_TRANSFORMS.items():print('MISSING FORMULA:',k,'—',v)
 print('STAGE7 FORMULA READINESS AUDIT PASSED; LIVE SIGNAL: BLOCKED (ORIGINAL FORMULAS MISSING)')

if __name__=='__main__':
 try:main()
 except Exception as e:print('STAGE7 FORMULA AUDIT FAILED:',e,file=sys.stderr);sys.exit(1)
