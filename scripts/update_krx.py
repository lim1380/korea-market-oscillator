#!/usr/bin/env python3
"""KRX approved official OpenAPI, daily stock market breadth (no trades or invented signals)."""
import datetime as dt, json, os, sys, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEY=os.environ.get('KRX_API_KEY','').strip()
OUT=ROOT/'data'/'krx_latest.json'
HIST=ROOT/'data'/'krx_history.json'
API={'KOSPI':'https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd',
     'KOSDAQ':'https://data-dbg.krx.co.kr/svc/apis/sto/ksq_bydd_trd'}

def fetch(market,date):
    url=API[market]+'?'+urllib.parse.urlencode({'basDd':date})
    request=urllib.request.Request(url,headers={'AUTH_KEY':KEY,'Accept':'application/json','User-Agent':'V13-indicator-dashboard/1.0'})
    with urllib.request.urlopen(request,timeout=50) as r:
        obj=json.loads(r.read())
    if 'OutBlock_1' not in obj or not isinstance(obj['OutBlock_1'],list):
        raise RuntimeError(f'{market}: KRX approval/API/response error: {str(obj)[:250]}')
    rows=obj['OutBlock_1']
    if len(rows)<500: raise RuntimeError(f'{market}: insufficient stock rows {len(rows)}; refusing partial data')
    return rows

def number(v):
    x=str(v or '').replace(',','').replace('−','-').strip()
    return float(x) if x and x not in ('-','.') else None

def calc(day,stocks):
    up=down=0
    nup=ndown=nflat=0
    invalid=0
    for r in stocks:
        close=number(r.get('TDD_CLSPRC'))
        change=number(r.get('CMPPREVDD_PRC'))
        val=number(r.get('ACC_TRDVAL'))
        if close is None or change is None or val is None or close<=0 or val<0:
            invalid+=1;continue
        if change>0: up+=val;nup+=1
        elif change<0: down+=val;ndown+=1
        else:nflat+=1
    if nup+ndown<500 or (up+down)<=0:raise RuntimeError('Invalid/incomplete trading data')
    return {'date':day,'market':'KOSPI+KOSDAQ','tracked_stocks':len(stocks),'valid_stocks':nup+ndown+nflat,
       'excluded_rows':invalid,'advancing_stocks':nup,'declining_stocks':ndown,'unchanged_stocks':nflat,
       'advancing_value_krw':int(up),'declining_value_krw':int(down),
       'advancing_value_ratio_pct':round(100*up/(up+down),2),
       'signal':'not_calculated','reason':'V13 buy and sell scores require full tested V7 engine, market indices, and derivatives data',
       'not_available':['20/60/200-day breadth','52-week highs/lows','V13 BUY/SELL']}

def main():
    if not KEY:raise RuntimeError('KRX_API_KEY is missing. Get KRX key and approval for KOSPI & KOSDAQ daily-trade APIs.')
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    result=None
    for delta in range(0,8):
        d=(now-dt.timedelta(days=delta)).strftime('%Y%m%d')
        try:
            a=fetch('KOSPI',d);b=fetch('KOSDAQ',d)
            if all(r.get('BAS_DD')==d for r in a+b):
                result=calc(d,a+b);break
        except Exception as e:
            if 'approval/API/response' in str(e) or isinstance(e,urllib.error.HTTPError):raise
            print(f'Skip {d}: {e}')
    if not result: raise RuntimeError('No complete recent day found; refusing to publish stale prices')
    if (now-dt.datetime.strptime(result['date'],'%Y%m%d').date()).days>4:
        raise RuntimeError('Last KRX trading date is more than four calendar days old')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    old=[]
    if HIST.exists():
        try:old=json.loads(HIST.read_text(encoding='utf8'))
        except ValueError:raise RuntimeError('History JSON malformed')
    bydate={x['date']:x for x in old if isinstance(x,dict) and 'date' in x}
    bydate[result['date']]={k:result[k] for k in ('date','advancing_value_ratio_pct','advancing_stocks','declining_stocks','valid_stocks')}
    HIST.write_text(json.dumps(sorted(bydate.values(),key=lambda x:x['date'])[-500:],ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('KRX verified',result['date'],result['valid_stocks'],'stocks; advance value %',result['advancing_value_ratio_pct'])
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
