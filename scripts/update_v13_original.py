#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exact replay of archived V7 and rigorously bounded V7/V13 forward exposure.

Uses original V7 state transitions. V13 BUY is archived V7 BUY gated by
KOSPI+KOSDAQ advancing traded value > 50%; V7 SELL is unchanged.

Do not fabricate new E scores or the last 30 points of the SELL_REVERSAL
component. For days after the archived V7 history, compute only position
consequences common to ALL possible missing component values (interval proof).
When possible positions diverge, report UNRESOLVED, never a speculative trade.

Requires: pip install numpy pandas
Input files: data/v13_original_reference.csv.gz (archived immutable),
             data/kospi_index_history.json and data/krx_latest.json
Output:     data/v13_backtested_latest.json
"""
from __future__ import annotations
import argparse, datetime as dt, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
REF=DATA/'v13_original_reference.csv.gz'
KOSPI=DATA/'kospi_index_history.json'
KRX=DATA/'krx_latest.json'
OUT=DATA/'v13_backtested_latest.json'
FORWARD=DATA/'v13_kospi_forward_history.json'


def rsi(close,n):
    delta=close.diff()
    up=delta.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    dn=(-delta.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    return (100*up/(up+dn)).replace([np.inf,-np.inf],np.nan).fillna(50)


def score_components(prices):
    p=prices.astype('float64')
    ma20=p.rolling(20).mean();ma60=p.rolling(60).mean();ma200=p.rolling(200).mean()
    trend=(25*(p<ma20).astype(int)+25*(p<ma60).astype(int)+
           20*(p<ma200).astype(int)+15*(ma20<ma20.shift(5)).astype(int)+
           15*(p.pct_change(10)<-0.04).astype(int)).astype(int)
    sigma=p.pct_change().rolling(20,min_periods=20).std().to_numpy()
    # Fidelity: original denominator includes NaNs in the early 252-day window.
    vol=np.full(len(p),50.0)
    for t in range(99,len(p)):
        historical=sigma[max(0,t-251):t+1]
        vol[t]=round(100.0*np.mean(historical<=sigma[t]),2)
    r14=rsi(p,14);r2=rsi(p,2)
    reversal20=20*((p/p.rolling(20).max()-1)<-0.07).astype(int)
    reversal50=50*((r14.shift(5)>68)&(r14<60)).astype(int)
    reversal_known=reversal20+reversal50
    trend_buy=(25*(p>ma20).astype(int)+30*(p>ma60).astype(int)+
               30*(p>ma200).astype(int)+15*(p.pct_change(60)>0).astype(int)).astype(float)
    rebound=(.5*r14+.25*r2+.25*(50+150*p.pct_change(10)).clip(0,100)).clip(0,100)
    lower=.55*trend+.25*vol+.20*reversal_known
    return {'trend_risk':trend,'vol_risk':vol,'reversal_known':reversal_known,
            'reversal20':reversal20,'reversal50':reversal50,
            'risk_lower':lower,'risk_upper':lower+6.0,
            'buy_trend':trend_buy,'buy_rebound':rebound}


def possible_risks(low,high):
    values=[low,high]
    for boundary in (50.,65.):
        if low <= boundary <= high:values.append(boundary)
        if low < boundary:values.append(max(low,boundary-1.e-6))
    return sorted(set(round(float(v),9) for v in values if low-1.e-9<=v<=high+1.e-9))


def next_exposure(previous, risk, buy):
    if risk>=65: return 0.0
    if risk>=50: return min(previous,0.5)
    if buy>=65: return 1.0
    if buy>=40: return 0.5
    return previous


def possibilities(prev,low,high,buybase):
    # E in [0,100], original bonus +15 at E<=15, otherwise 0.
    # Over the full E range, additive E contribution min >4.5, max=30.
    # Using conservative closed bounds cannot falsely assert a unique state.
    possible_buys=[min(100.,buybase+4.5),min(100.,buybase+30.)]
    for cutoff in (40.,65.):
        if possible_buys[0]<=cutoff<=possible_buys[1]:
            possible_buys.extend([cutoff, max(possible_buys[0],cutoff-1e-6)])
    exposures=set()
    for previous in prev:
        for risk in possible_risks(low,high):
            for buy in possible_buys:
                exposures.add(next_exposure(previous,risk,buy))
    return exposures


def replay_original(ref):
    """Exact daily replay to detect changing archive/calculation assumptions."""
    pos=1.0;prev=1.0;predicted=[];actions=[]
    for i,row in ref.iterrows():
        score=row['V6_score'];risk=row['SELL_RISK']
        if i%5==0 and pd.notna(score):
            pos=next_exposure(pos,risk,score)
        action='BUY' if pos>prev else 'SELL' if pos<prev else 'HOLD'
        predicted.append(pos);actions.append(action);prev=pos
    err=sum(abs(a-b)>1e-9 for a,b in zip(predicted,ref.INTEGRATED_EXPOSURE))
    aerr=sum(a!=b for a,b in zip(actions,ref.INTEGRATED_ACTION))
    if err or aerr: raise RuntimeError(f'Original V7 replay mismatch: exposure={err}, actions={aerr}')
    if int(sum(x=='BUY' for x in actions))!=43 or int(sum(x=='SELL' for x in actions))!=43:
        raise RuntimeError('Unexpected archived V7 event counts')
    return {'sessions':len(ref),'exposure_mismatches':err,'action_mismatches':aerr,
            'buy_events':43,'sell_events':43,'status':'EXACT_REPLAY'}


def parse_data():
    ref=pd.read_csv(REF,parse_dates=['date'])
    required={'date','kospi','V6_score','SELL_RISK','SELL_TREND_RISK','SELL_VOL_RISK',
              'SELL_REVERSAL_RISK','INTEGRATED_EXPOSURE','INTEGRATED_ACTION',
              'ALL_advance_value_ratio'}
    if not required.issubset(ref.columns): raise RuntimeError('Missing original V7 reference columns')
    if len(ref)!=2160 or ref.date.duplicated().any() or not ref.date.is_monotonic_increasing:
        raise RuntimeError('V7 reference length/date invalid')
    if ref.date.iloc[0].strftime('%Y%m%d')!='20180102' or ref.date.iloc[-1].strftime('%Y%m%d')!='20261023':
        raise RuntimeError('V7 source reference dates changed')
    rows=json.loads(KOSPI.read_text(encoding='utf-8'))
    if not isinstance(rows,list) or len(rows)<8:raise RuntimeError('Insufficient KOSPI history')
    current=pd.DataFrame(rows)
    if not {'date','close'}.issubset(current.columns):raise RuntimeError('Invalid index history schema')
    current['date']=pd.to_datetime(current.date,format='%Y%m%d',errors='raise')
    current['close']=pd.to_numeric(current.close,errors='raise')
    if current.date.duplicated().any() or not current.date.is_monotonic_increasing or (current.close<=0).any():
        raise RuntimeError('Index history contains missing/duplicate/invalid observations')
    last=ref.date.iloc[-1]
    # Persist our append-only official KOSPI closes beyond the 125-session
    # window retained by the separate stage5 updater. Never silently discard
    # older post-archive sessions once stage5 rolls them out of its JSON.
    stored=[]
    if FORWARD.exists():
        stored=json.loads(FORWARD.read_text(encoding='utf-8'))
        if not isinstance(stored,list):raise RuntimeError('Invalid V13 forward history')
    if stored:
        known=pd.DataFrame(stored)
        known['date']=pd.to_datetime(known.date,format='%Y%m%d',errors='raise')
        known['close']=pd.to_numeric(known.close,errors='raise')
        if known.date.duplicated().any() or not known.date.is_monotonic_increasing:
            raise RuntimeError('Duplicate/out-of-order V13 forward index')
        if (known.date<=last).any():raise RuntimeError('V13 forward index starts before legacy end')
    else:
        known=pd.DataFrame(columns=['date','close'])
    trusted=pd.concat([ref[['date','kospi']].rename(columns={'kospi':'close'}), known],ignore_index=True)
    overlap=current.merge(trusted,on='date',how='inner',suffixes=('_source','_trusted'))
    if len(overlap)<3 or (overlap.close_source-overlap.close_trusted).abs().max()>1.e-5:
        raise RuntimeError('Historical index source not aligned with archived V7/forward prices')
    new_rows=current[current.date>trusted.date.iloc[-1]].copy()
    forward=pd.concat([known,new_rows[['date','close']]],ignore_index=True)
    all_days=pd.concat([ref[['date','kospi']],forward.rename(columns={'close':'kospi'})[['date','kospi']]],ignore_index=True)
    if all_days.date.duplicated().any():raise RuntimeError('Duplicate combined KOSPI date')
    # Reject a missing multi-day segment (including a 2-month workflow outage).
    gaps=all_days.date.diff().dt.days.dropna()
    if (gaps.tail(len(forward)+1)>7).any():raise RuntimeError('Unverified >7-day gap in new KOSPI index history')
    market=json.loads(KRX.read_text(encoding='utf-8'))
    latest=str(market.get('date',''))
    if latest!=all_days.date.iloc[-1].strftime('%Y%m%d'):
        raise RuntimeError('KOSPI and market-traded-value dates disagree')
    ratio=market.get('advancing_value_ratio_pct')
    if not isinstance(ratio,(int,float)) or not np.isfinite(ratio) or ratio<0 or ratio>100:
        raise RuntimeError('Latest traded value ratio invalid')
    return ref,all_days,latest,float(ratio),forward


def main():
    ref,days,latest,ratio,forward=parse_data()
    checked=replay_original(ref)
    s=score_components(days.kospi)
    n=len(ref)
    # Validate original reconstructed components independently, NOT via archived
    # SELL_RISK weighted sum. Reversal unknown 30pt must be exactly 0 or30.
    if not np.array_equal(s['trend_risk'][:n],ref.SELL_TREND_RISK.to_numpy(dtype=int)):
        raise RuntimeError('Historical 55%-weighted trend source does not match V7')
    if not np.array_equal(s['vol_risk'][:n],ref.SELL_VOL_RISK.to_numpy(dtype=float)):
        raise RuntimeError('Historical 25%-weighted volatility percentile does not match V7')
    residual=ref.SELL_REVERSAL_RISK.to_numpy() - s['reversal_known'].iloc[:n].to_numpy()
    if not np.isin(residual,[0,30]).all():
        raise RuntimeError('Historical 20/50-point reversal factors changed')
    # Verify risk exactly follows 55% / 25% / 20% original weighted sum.
    risk=.55*s['trend_risk'][:n].to_numpy()+.25*s['vol_risk'][:n]+.20*ref.SELL_REVERSAL_RISK.to_numpy()
    if np.max(np.abs(risk-ref.SELL_RISK.to_numpy()))>.00501:
        raise RuntimeError('Historical SELL_RISK weighted sum no longer matches archive')
    # Historical archived event dates/labels; V13 BUY is V7 BUY plus observed
    # rising-traded-value ratio >50%; V7 SELL unchanged.
    qualified=(ref.INTEGRATED_ACTION.eq('BUY') & ref.ALL_advance_value_ratio.gt(.5))
    approved=ref.loc[qualified,'date'].dt.strftime('%Y%m%d').tolist()
    last_sell=ref.loc[ref.INTEGRATED_ACTION.eq('SELL'),'date'].iloc[-1].strftime('%Y%m%d')
    last_event_date=ref.loc[ref.INTEGRATED_ACTION.ne('HOLD'),'date'].iloc[-1].strftime('%Y%m%d')
    prev_positions={float(ref.INTEGRATED_EXPOSURE.iloc[-1])}
    trace=[]
    for idx in range(n,len(days)):
        day=days.date.iloc[idx].strftime('%Y%m%d')
        low=float(s['risk_lower'].iloc[idx]);high=float(s['risk_upper'].iloc[idx])
        review=idx%5==0
        if review:
            buybase=float(.45*s['buy_trend'].iloc[idx]+.25*s['buy_rebound'].iloc[idx])
            prev_positions=possibilities(prev_positions,low,high,buybase)
        trace.append({'date':day,'session_index':idx,'review':review,
                      'risk_lower':round(low,4),'risk_upper':round(high,4),
                      'possible_exposure_pct':sorted(round(x*100) for x in prev_positions)})
    last=trace[-1] if trace else None
    certified=bool(last and len(prev_positions)==1)
    status=('CERTIFIED_ORIGINAL_POSITION' if certified else
            'UNRESOLVED_MISSING_V7_FACTORS' if last else 'ARCHIVE_ONLY')
    lastreview=next((x for x in reversed(trace) if x['review']),None)
    last_action='HOLD' if certified and last and not last['review'] else None
    if certified and last and last['review']:
        pos_before=(trace[-2]['possible_exposure_pct'] if len(trace)>=2 else [int(ref.INTEGRATED_EXPOSURE.iloc[-1]*100)])
        if len(pos_before)==1:
            now=last['possible_exposure_pct'][0];prev=pos_before[0]
            last_action='BUY' if now>prev else 'SELL' if now<prev else 'HOLD'
    position_pct=next(iter(prev_positions))*100 if certified else None
    # BUY filter can never create a new entry when risk_lower>=65 on review.
    # We do NOT manufacture a historical backtest hit rate for future bound-only decisions.
    result={'schema_version':'v13-original-archive-bound-v1','model':'Archived V7 exposure/actions + V13 traded-value>50% BUY filter; SELL unchanged',
            'market_data_date':latest,'reference_end':'20261023','reference_start':'20180102',
            'review_cadence_sessions':5,'review_origin':'20180102 (index 0)',
            'archive_validation':checked,
            'historical_v13_qualified_buy_events':int(qualified.sum()),
            'historical_v7_buy_events':43,'historical_v7_sell_events':43,
            'last_archived_v7_event_date':last_event_date,'last_archived_v7_sell_date':last_sell,
            'latest_rising_value_ratio_pct':ratio,
            'latest_buy_filter_pass':ratio>50,'forward_status':status,
            'certified_original_target_exposure_pct':position_pct,
            'possible_original_target_exposure_pct':sorted(round(x*100) for x in prev_positions),
            'latest_action_certified':last_action,
            'last_review_date':lastreview['date'] if lastreview else None,
            'last_review_risk_lower':lastreview['risk_lower'] if lastreview else None,
            'last_review_risk_upper':lastreview['risk_upper'] if lastreview else None,
            'last_market_risk_lower':last['risk_lower'] if last else None,
            'last_market_risk_upper':last['risk_upper'] if last else None,
            'new_sessions_since_archive':len(trace),
            'forward_audit':trace[-15:],
            'buy_score_status':'NOT_CALCULATED — original E includes KOSDAQ/VKOSPI/KTB3 futures historical ranks',
            'reversal_status':'BOUND_ONLY — historical 30pt reversal flag not yet regenerated',
            'v13_buy_status':'BLOCKED_UNLESS_EXACT_V7_BUY_EVENT_CONFIRMED',
            'current_market_position_basis':'Original V7 target equity position is certifiable only if all possible inputs yield the same position.',
            'limitations':'Research backtest is exploratory, not external OOS; 0% means target exposure not a newly generated SELL order. No execution advice.'}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    FORWARD.write_text(json.dumps([{'date':r.date.strftime('%Y%m%d'),'close':float(r.close)} for r in forward.itertuples(index=False)],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V7 ARCHIVE REPLAY EXACT:',len(ref),'sessions, 43 BUY, 43 SELL; V13 historical qualified BUY:',int(qualified.sum()))
    print('V13 FORWARD STATUS:',status,'date',latest,'possible target exposure',result['possible_original_target_exposure_pct'],
          'last review',result['last_review_date'],'risk lower/upper',result['last_review_risk_lower'],result['last_review_risk_upper'])
    print('RESULT:',OUT)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('V13 AUDIT ERROR:',e,file=sys.stderr);sys.exit(1)
