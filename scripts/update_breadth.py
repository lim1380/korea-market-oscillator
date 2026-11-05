#!/usr/bin/env python3
"""V13 market breadth: rolling 285 KRX trading days, no third-party packages.
Bootstrap: data/krx_stock_rolling.csv.gz (2017-2026 archived stock closes).
Daily: KRX official daily trade API with KRX_API_KEY secret.
Outputs: data/breadth_latest.json, data/breadth_history.json.
Do not interpret any single breadth filter as a full BUY/SELL signal.
"""
import csv, datetime as dt, gzip, io, json, math, os, sys, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLLING = ROOT / 'data' / 'krx_stock_rolling.csv.gz'
LATEST = ROOT / 'data' / 'breadth_latest.json'
HISTORY = ROOT / 'data' / 'breadth_history.json'
KEY = os.environ.get('KRX_API_KEY','').strip()
API = {'KOSPI':'https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd',
       'KOSDAQ':'https://data-dbg.krx.co.kr/svc/apis/sto/ksq_bydd_trd'}
WINDOW = 285  # Enough observations for previous 252 and 200 trading-day averages
MIN_DAYS = {20:20, 60:60, 200:200}


def read_prices():
    if not ROLLING.exists():
        raise RuntimeError('Missing data/krx_stock_rolling.csv.gz. Upload seed first.')
    by_day=defaultdict(dict)
    with gzip.open(ROLLING, 'rt', encoding='utf-8', newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames != ['date','market','code','close']:
            raise RuntimeError(f'Rolling CSV schema mismatch: {reader.fieldnames}')
        for r in reader:
            day=r['date'];code=r['market']+':'+r['code']
            try: close=float(r['close'])
            except ValueError: continue
            if not (close>0 and math.isfinite(close)): continue
            if code in by_day[day]:
                raise RuntimeError(f'Duplicate stock {day} {code}')
            by_day[day][code]=close
    if len(by_day)<260: raise RuntimeError(f'Insufficient price history: {len(by_day)} dates')
    return dict(sorted(by_day.items()))


def fetch(market, day):
    url=API[market]+'?'+urllib.parse.urlencode({'basDd':day})
    request=urllib.request.Request(url, headers={'AUTH_KEY':KEY,'Accept':'application/json',
                                                  'User-Agent':'V13-Market-Breadth/1.0'})
    with urllib.request.urlopen(request,timeout=50) as response:
        data=json.load(response)
    rows=data.get('OutBlock_1')
    if isinstance(rows,list) and len(rows)==0:
        raise RuntimeError(f'NO_TRADING_DAY: {market} {day}')
    if not isinstance(rows,list) or len(rows)<500:
        raise RuntimeError(f'{market} invalid/unauthorized response for {day}: {str(data)[:180]}')
    if any(r.get('BAS_DD')!=day for r in rows): raise RuntimeError(f'{market} date mismatch {day}')
    out={}
    for r in rows:
        code=str(r.get('ISU_SRT_CD') or r.get('ISU_CD') or '').strip()
        raw=str(r.get('TDD_CLSPRC') or '').replace(',','').strip()
        try: close=float(raw)
        except ValueError: continue
        if len(code)!=6 or not code.isdigit() or close<=0 or not math.isfinite(close): continue
        if code in out: raise RuntimeError(f'{market}: duplicate code {code}')
        out[code]=close
    if len(out)<500: raise RuntimeError(f'{market}: insufficient valid stock prices {len(out)}')
    return {market+':'+code:price for code,price in out.items()}


def fetch_days_since(last_day):
    """Fetch every calendar date after stored latest, never silently skip an intermediate session."""
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    past=dt.datetime.strptime(last_day,'%Y%m%d').date()
    if past>now: raise RuntimeError('Stored latest date is in the future')
    if (now-past).days>30:
        raise RuntimeError('More than 30 calendar days missing; backfill audit required')
    collected={}
    for offset in range(1,(now-past).days+1):
        day=past+dt.timedelta(days=offset)
        if day.weekday()>=5: continue
        ds=day.strftime('%Y%m%d')
        try:
            a=fetch('KOSPI',ds)
            b=fetch('KOSDAQ',ds)
            collected[ds]={**a,**b}
            print('KRX day verified:',ds,'valid prices:',len(collected[ds]))
        except RuntimeError as e:
            # A no-data response is normal for an exchange holiday or data not yet published.
            if str(e).startswith('NO_TRADING_DAY:'):
                print('No KRX market data for',ds,'(holiday or not published yet)')
            else: raise
    return collected


def calc(by_day, idx):
    dates=list(by_day)
    day=dates[idx]
    if idx<252: raise RuntimeError('Need prior 252 trading days for 52-week comparison')
    prevdates=dates[max(0,idx-252):idx]
    today=by_day[day]
    counts={w:0 for w in MIN_DAYS}
    eligible={w:0 for w in MIN_DAYS}
    high=low=hl_eligible=0
    # Construct per-stock preceding values, using only dates BEFORE target date.
    prev=defaultdict(list)
    for d in prevdates:
        for code,close in by_day[d].items():
            prev[code].append(close)
    for code,close in today.items():
        series=prev.get(code,[])
        for w in MIN_DAYS:
            # In the last w market sessions, stock must have a valid close on EVERY session.
            taildates=dates[idx-w:idx]
            vals=[by_day[d].get(code) for d in taildates]
            if len(vals)!=w or any(v is None for v in vals):continue
            eligible[w]+=1
            # SMA includes current day's close, per charting convention.
            sma=(sum(vals[1:])+close)/w
            if close>sma:counts[w]+=1
        # New 52w highs/lows use 252-day prior close range; only fully observed histories.
        if len(series)==252:
            hl_eligible+=1
            if close>max(series): high+=1
            if close<min(series): low+=1
    if len(today)<1000 or eligible[200]<800 or hl_eligible<800:
        raise RuntimeError(f'Invalid market coverage {day}: today={len(today)} above200={eligible[200]} 52w={hl_eligible}')
    result={'date':day,'observed_stocks':len(today),'method':'KOSPI+KOSDAQ ordinary KRX issue codes; close>SMA with current close included; prior 252 sessions for 52w close high/low; requires valid close on every relevant session',
            'breadth':{},'high_52w_count':high,'low_52w_count':low,
            'high_52w_pct':round(high/hl_eligible*100,2),'low_52w_pct':round(low/hl_eligible*100,2),
            'high_52w_minus_low_52w_pct':round((high-low)/hl_eligible*100,2),
            'eligible_52w_stocks':hl_eligible,
            'signal_status':'not_calculated',
            'notice':'These are market breadth indicators, not the complete V13 BUY/SELL engine.'}
    for w in MIN_DAYS:
        result['breadth'][str(w)]={'above_count':counts[w], 'eligible_count':eligible[w], 'above_pct':round(counts[w]/eligible[w]*100,2) if eligible[w] else None}
    return result


def save_rolling(by_day):
    dates=sorted(by_day)[-WINDOW:]
    # Deterministic gzip: mtime is not necessary for signal reproducibility.
    with gzip.open(ROLLING,'wt',encoding='utf-8',newline='',compresslevel=6) as f:
        w=csv.writer(f);w.writerow(['date','market','code','close'])
        for d in dates:
            for key,price in sorted(by_day[d].items()):
                m,code=key.split(':',1)
                w.writerow([d,m,code,format(price,'.10g')])


def main():
    if not KEY: raise RuntimeError('KRX_API_KEY secret missing')
    data=read_prices()
    before=max(data)
    additions=fetch_days_since(before)
    # Insert only fully verified paired-market KRX trading days.
    for d,prices in sorted(additions.items()):
        data[d]=prices
    target=max(data)
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    if (today-dt.datetime.strptime(target,'%Y%m%d').date()).days>7:
        raise RuntimeError(f'Latest KRX stock data too old: {target}')
    result=calc(data,list(data).index(target))
    LATEST.parent.mkdir(parents=True,exist_ok=True)
    LATEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    records=[]
    if HISTORY.exists():
        records=json.loads(HISTORY.read_text(encoding='utf-8'))
    dedup={x['date']:x for x in records if isinstance(x,dict) and 'date' in x}
    dedup[target]={'date':target,'b20':result['breadth']['20']['above_pct'],'b60':result['breadth']['60']['above_pct'],
                   'b200':result['breadth']['200']['above_pct'],'high52':result['high_52w_pct'],'low52':result['low_52w_pct']}
    HISTORY.write_text(json.dumps([dedup[d] for d in sorted(dedup)[-500:]],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save_rolling(data)
    print('BREADTH VERIFIED',target, result['breadth'],'52w high',result['high_52w_count'],'low',result['low_52w_count'])

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('ERROR:',e,file=sys.stderr)
        sys.exit(1)
