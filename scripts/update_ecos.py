#!/usr/bin/env python3
"""Fetch verified ECOS interest-rate series into public web-safe JSON.

Only public figures are written. API key must come from ECOS_API_KEY env.
This is an ECOS-only first stage, not a full V13 trade signal.
"""
import datetime as dt
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'ecos_latest.json'
KEY = os.environ.get('ECOS_API_KEY', '').strip()
TABLE = '817Y002'
SERIES = {'government_3y': ('010200000', '국고채(3년)'), 'corporate_aa_minus_3y': ('010310000', '회사채(3년, AA-, 민평)')}


def request(code, start, end):
    url = ('https://ecos.bok.or.kr/api/StatisticSearch/'
           + urllib.parse.quote(KEY, safe='') + '/json/kr/1/1000/'
           + TABLE + '/D/' + start + '/' + end + '/' + code)
    req = urllib.request.Request(url, headers={'User-Agent':'V13-Market-Dashboard/1.0'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        obj = json.load(resp)
    if 'RESULT' in obj:
        raise RuntimeError(str(obj['RESULT']))
    result = obj.get('StatisticSearch')
    if not result:
        raise RuntimeError('ECOS API response missing StatisticSearch')
    if int(result.get('list_total_count', 0)) > 1000:
        raise RuntimeError('More than 1000 observations: pagination required; refusing partial data')
    return result.get('row') or []


def parse(rows, label):
    values={}
    for r in rows:
        name=str(r.get('ITEM_NAME1') or '')
        # Exact substring verification to prevent silently using another instrument.
        if label.replace(' ', '') not in name.replace(' ', ''):
            raise RuntimeError(f'Unexpected ECOS item name for {label}: {name}')
        d=str(r.get('TIME',''))
        v=str(r.get('DATA_VALUE','')).strip().replace(',','')
        if len(d)==8 and d.isdigit() and v not in {'','-','.'}:
            values[d]=float(v)
    return values


def main():
    if not KEY:
        raise RuntimeError('ECOS_API_KEY is missing (GitHub Actions Secrets)')
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    start=(now-dt.timedelta(days=450)).strftime('%Y%m%d')
    end=now.strftime('%Y%m%d')
    vals={}
    for kind,(code,label) in SERIES.items():
        rows=request(code,start,end)
        vals[kind]=parse(rows,label)
    common=sorted(set(vals['government_3y']) & set(vals['corporate_aa_minus_3y']))
    if len(common)<200:
        raise RuntimeError(f'Insufficient overlapping history: {len(common)} records')
    latest=common[-1]
    age=(now-dt.datetime.strptime(latest,'%Y%m%d').date()).days
    if age>7:
        raise RuntimeError(f'ECOS latest observation stale ({latest}, {age} calendar days)')
    spreads=[round((vals['corporate_aa_minus_3y'][d]-vals['government_3y'][d])*100,4) for d in common]
    median=statistics.median(spreads[:-1][-252:]) if len(spreads)>252 else None
    change5=round(spreads[-1]-spreads[-6],4)
    warning=(median is not None and spreads[-1]>median and change5>0)
    result={
      'source':'Bank of Korea ECOS', 'stat_code':TABLE,
      'data_date':f'{latest[:4]}-{latest[4:6]}-{latest[6:]}',
      'updated_at_kst':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds'),
      'government_3y_pct':vals['government_3y'][latest],
      'corporate_aa_minus_3y_pct':vals['corporate_aa_minus_3y'][latest],
      'credit_spread_bp':round(spreads[-1],2),
      'credit_spread_change_5d_bp':round(change5,2),
      'credit_spread_prior_252d_median_bp':round(median,2) if median is not None else None,
      'credit_risk_warning':bool(warning),
      'signal_status':'not_calculated',
      'notice':'ECOS-only: BUY/SELL not calculated without full V13 data/engine.'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ECOS data date:', result['data_date'],'spread:', result['credit_spread_bp'],'bp')

if __name__=='__main__':
    try:
        main()
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr)
        sys.exit(1)
