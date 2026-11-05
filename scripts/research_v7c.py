#!/usr/bin/env python3
"""V13 7C research-only, transparent *new* candidate model.
Never claim reproduction of V7; does not output any live trading signal.
Inputs are archived KOSPI / VKOSPI, strictly trailing observations.
"""
import csv, gzip, json, math, statistics, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'data/v7c_historical_inputs.csv.gz'
V7=ROOT/'data/v7_legacy_reference.csv.gz'
OUT=ROOT/'audit_output'

def clamp(n):return max(0.,min(100.,n))
def rsi(closes,period=14):
    change=[closes[j]-closes[j-1] for j in range(len(closes)-period,len(closes))]
    u=sum(max(0,x) for x in change);dn=sum(max(0,-x) for x in change)
    return 50 if u==0 and dn==0 else 100 if dn==0 else 100-100/(1+u/dn)
def percentile(values,x):
    return 100*sum(v<=x for v in values)/len(values)

def load():
    with gzip.open(INPUT,'rt',encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f))
    with gzip.open(V7,'rt',encoding='utf-8-sig',newline='') as f: refs=list(csv.DictReader(f))
    if len(raw)<1000:raise ValueError('Insufficient source history')
    prev=''
    for row in raw:
        if row['date']<=prev:raise ValueError('Dates missing order / duplicate')
        prev=row['date']
        for key in ('kospi','vkospi'):
            if not math.isfinite(float(row[key])) or float(row[key])<=0:raise ValueError('Invalid '+key)
    ref={r['date']:r for r in refs}
    for x in raw:
        if x['date'] in ref and abs(float(x['kospi'])-float(ref[x['date']]['kospi_close']))>.05:
            raise ValueError('KOSPI archived comparison mismatch '+x['date'])
    return raw,ref

def calculate(rows):
    closes=[float(x['kospi']) for x in rows];vks=[float(x['vkospi']) for x in rows]
    out=[]
    for i,row in enumerate(rows):
        if i<252:continue
        # Exactly 252 historical observations through signal date, never future samples.
        history=closes[i-251:i+1]; vols=vks[i-251:i+1]
        close=closes[i];v=vols[-1];sma125=statistics.mean(closes[i-124:i+1]); sma20=statistics.mean(closes[i-19:i+1])
        r=rsi(closes[:i+1]); chg5=close/closes[i-5]-1
        # New *candidate* scores, pre-defined heuristic; NOT historical V7 transformations.
        fear=percentile(vols,v)
        trend=clamp(50+500*(close/sma125-1)+250*chg5)
        rebound=clamp(100-r+max(-20,min(20,chg5*1000)))
        buy=round(.30*fear+.45*trend+.25*rebound,4)
        tr_break=clamp(50+500*(sma125/close-1)+300*(sma20/close-1))
        volrisk=percentile(vols,v)
        reversal=clamp((r-50)*2+max(0,-chg5)*500)
        sell=round(.55*tr_break+.25*volrisk+.20*reversal,4)
        entry=(buy>=65 and sell<50)
        exit=(sell>=65)
        out.append({'date':row['date'],'kospi':close,'rsi14':round(r,4),'fear':round(fear,4),'trend':round(trend,4),'rebound':round(rebound,4),'buy_score':buy,'trend_break':round(tr_break,4),'volatility_rank':round(volrisk,4),'reversal':round(reversal,4),'sell_risk_score':sell,'entry_candidate':int(entry),'exit_candidate':int(exit)})
    return out

def choose_events(data,key,min_gap=20):
    out=[];last=-min_gap-1;was=False
    for i,r in enumerate(data):
        today=bool(r[key]);
        if today and not was and i-last>=min_gap:
            out.append(i);last=i
        was=today
    return out

def forward(out,events,side):
    n=win=0;rets=[]
    for i in events:
        if i+21>=len(out):continue
        # Signal after close at t, execution at close t+1, measure price to t+21.
        r=(out[i+21]['kospi']/out[i+1]['kospi']-1)*100
        rets.append(r);n+=1
        if r>0 if side=='buy' else r<0:win+=1
    return {'events_with_complete_forward_window':n,'hit':win,'hit_pct':round(100*win/n,2) if n else None,'mean_20d_pct':round(statistics.mean(rets),3) if rets else None}

def main():
    raw,ref=load();out=calculate(raw)
    if len(out)<1400:raise ValueError('Too little warm data')
    hitref=[r for r in out if r['date'] in ref]
    def compare(key,action):
        pos=[r for r in hitref if r[key]];legacy={d for d,v in ref.items() if v['action']==action}
        return {'candidate_days':len(pos),'v7_event_days':len(legacy),'same_day_overlap':sum(r['date'] in legacy for r in pos),'precision_vs_stored_v7_events_pct':round(100*sum(r['date'] in legacy for r in pos)/len(pos),2) if pos else None}
    report={'model':'V13-7C-RESEARCH-CANDIDATE-NOT-V7','original_v7_reproduced':False,'live_signal_enabled':False,'is_automated_v13':False,'history_start':out[0]['date'],'history_end':out[-1]['date'],'n':len(out),'model_definition':{'fear':'rolling 252-session VKOSPI empirical CDF','trend':'clamp(50+500*(close/SMA125-1)+250*(close/close_5ago-1))','rebound':'clamp(100-RSI14 + clamp(1000*5d_return,-20,20))','buy':'0.30*fear+0.45*trend+0.25*rebound; candidate if >=65 AND sell<50','trend_break':'clamp(50+500*(SMA125/close-1)+300*(SMA20/close-1))','volatility_rank':'rolling 252-session VKOSPI empirical CDF','reversal':'clamp((RSI14-50)*2+max(0,-5d_return)*500)','sell':'0.55*trend_break+0.25*volatility_rank+0.20*reversal; candidate if >=65'},'caveats':['Candidate thresholds uncalibrated; not the V7 score formulas','No historical advancing traded-value 50% filter applied','No stateful trade allocation, transaction costs or slippage','Forward outcomes exploratory/in-sample, including previously explored 2024+','VKOSPI data archived, not independently validated against official revisions']}
    report['v7_comparison']={'buy':compare('entry_candidate','BUY'),'sell':compare('exit_candidate','SELL')}
    report['periods']={}
    for name,fromdate,todate in [('train','2019-01-01','2023-12-31'),('review','2024-01-01','2026-10-23')]:
        subset=[r for r in out if fromdate<=r['date']<=todate]
        report['periods'][name]={side:forward(subset,choose_events(subset,k),side) for side,k in [('buy','entry_candidate'),('sell','exit_candidate')]}
    OUT.mkdir(exist_ok=True)
    with (OUT/'v7c_candidate_daily.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    (OUT/'v7c_research_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('7C RESEARCH CANDIDATE GENERATED',len(out),'sessions',out[0]['date'],out[-1]['date'])
    print('V7 BUY comparison',report['v7_comparison']['buy'])
    print('V7 SELL comparison',report['v7_comparison']['sell'])
    print('TRAIN',report['periods']['train'])
    print('REVIEW',report['periods']['review'])
    print('LIVE SIGNAL: BLOCKED (NEW RESEARCH MODEL, NOT V7 REPRODUCTION)')
if __name__=='__main__':
    try:main()
    except Exception as e:print('STAGE7C ERROR:',e,file=sys.stderr);sys.exit(1)
