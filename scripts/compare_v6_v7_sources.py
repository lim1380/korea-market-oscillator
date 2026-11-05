#!/usr/bin/env python3
"""V13 stage 7B — compare archived V7 score with V6 A-F source scores.
Research audit only. Does NOT reconstruct historical scores or generate BUY/SELL.
"""
import csv,gzip,json,math,statistics,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
V7=ROOT/"data"/"v7_legacy_reference.csv.gz"
V6=ROOT/"data"/"v6_source_scores.csv.gz"
OUT=ROOT/"audit_output"
NAMES=("A_주가_VKOSPI_점수","B_거래량PCR_국채포함_점수",
       "C_미결제PCR_국채포함_점수","D_혼합PCR_국채포함_점수",
       "E_국채포함_PCR제외_점수","F_혼합PCR_국채제외_점수")

def read(path):
    if not path.is_file():raise RuntimeError(f"Missing source: {path}")
    with gzip.open(path,"rt",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def number(s):
    if s is None or str(s).strip()=="":
        return None
    x=float(s)
    if not math.isfinite(x):raise ValueError("Non-finite source score")
    return x
def pearson(pairs):
    if len(pairs)<3:return None
    x=[a for a,b in pairs];y=[b for a,b in pairs]
    mx=statistics.mean(x);my=statistics.mean(y)
    vx=sum((a-mx)**2 for a in x);vy=sum((b-my)**2 for b in y)
    if not vx or not vy:return None
    return sum((a-mx)*(b-my) for a,b in pairs)/math.sqrt(vx*vy)
def main():
    v7=read(V7);v6=read(V6)
    a={r["date"]:r for r in v7}; b={r["date"]:r for r in v6}
    if len(a)!=len(v7) or len(b)!=len(v6):raise RuntimeError("Duplicate dates")
    days=sorted(set(a)&set(b))
    if len(days)<1500:raise RuntimeError(f"Too few aligned sessions: {len(days)}")
    price_err=max(abs(number(a[d]["kospi_close"])-number(b[d]["kospi"])) for d in days)
    if price_err>0.05:raise RuntimeError(f"KOSPI source mismatch: {price_err}")
    report={"source":"V7 stored archive vs original V6 A-F score columns",
            "overlap_days":len(days),"v7_buy_missing":sum(not a[d]["buy_score_v6"] for d in days),
            "kospi_max_absolute_difference":price_err,"candidate_models":{},
            "live_signal":"BLOCKED — original V6/V7 transform formulas not yet available"}
    OUT.mkdir(exist_ok=True)
    with (OUT/"comparison.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["date","v7_buy_score"]+[n+"_source" for n in NAMES])
        for d in days:
            w.writerow([d,a[d]["buy_score_v6"]]+[b[d].get(n,"") for n in NAMES])
    for n in NAMES:
        pairs=[]
        for d in days:
            x=number(a[d]["buy_score_v6"]);y=number(b[d].get(n))
            if x is not None and y is not None:pairs.append((x,y))
        dif=[abs(x-y) for x,y in pairs]
        stat={"n":len(pairs),"pearson_r":round(pearson(pairs),6) if pairs else None,
              "mae_points":round(statistics.mean(dif),6) if dif else None,
              "exact_matches_tolerance_0_001":sum(x<.001 for x in dif)}
        report["candidate_models"][n]=stat
        print(f'{n}: n={stat["n"]}, r={stat["pearson_r"]}, MAE={stat["mae_points"]}, exact={stat["exact_matches_tolerance_0_001"]}')
    e=report["candidate_models"]["E_국채포함_PCR제외_점수"]
    assert e["n"]==1784 and e["exact_matches_tolerance_0_001"]==0, "Source schema or results changed; investigate"
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STAGE7B SOURCE SCORE COMPARISON PASSED; ORIGINAL V7 SIGNAL: NOT REPRODUCED")
if __name__=="__main__":
    try: main()
    except Exception as ex:
        print("STAGE7B ERROR:",ex,file=sys.stderr)
        sys.exit(1)
