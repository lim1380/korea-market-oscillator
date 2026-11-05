/* V13 visual dashboard only. Reads the existing published JSONs; does not alter
   V7/V13 backtest, signals, collected history, workflows or API secrets. */
(() => {
  'use strict';
  const ROOT = 'v13-modern';
  const css = `
:root{color-scheme:dark}html,body{background:#0b1017!important}body>header,body>main{display:none!important}
#${ROOT}{--bg:#0b1017;--pane:#161f2b;--pane2:#1d2936;--border:#2c3948;--text:#edf5ff;--muted:#9cb0c4;--mint:#44d2aa;--amber:#ffcb69;--coral:#fb777c;--blue:#82b6ff;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;min-height:100vh}
#${ROOT} *{box-sizing:border-box}#${ROOT} .wrap{max-width:1240px;padding:0 25px;margin:auto}#${ROOT} .top{border-bottom:1px solid #253240;background:linear-gradient(90deg,#101c2a,#10151d)}
#${ROOT} .topin{display:flex;align-items:center;justify-content:space-between;gap:15px;min-height:88px}#${ROOT} .brand{font-size:20px;font-weight:850;letter-spacing:-.8px}#${ROOT} .brand strong{color:var(--amber)}#${ROOT} .sub{font-size:12px;color:var(--muted);margin-top:3px}#${ROOT} .topright{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
#${ROOT} .chip{border:1px solid var(--border);border-radius:99px;padding:6px 11px;font-size:12px;color:#c7d6e6;background:#182532}#${ROOT} button,#${ROOT} .act{border:1px solid #455b70;color:#eaf4ff;background:#223246;border-radius:9px;padding:9px 13px;font:inherit;font-size:12px;cursor:pointer;text-decoration:none;display:inline-flex;gap:7px;align-items:center}#${ROOT} button:hover,#${ROOT} .act:hover{background:#31465d}#${ROOT} .act.primary{background:#276450;border-color:#3c8d74;color:#effffb}
#${ROOT} .content{padding-top:26px;padding-bottom:60px}#${ROOT} .eyebrow{color:#a0b6ca;font-size:12px;font-weight:750;letter-spacing:1.2px;text-transform:uppercase}#${ROOT} .hero{border:1px solid #385263;background:radial-gradient(80% 200% at 90% -30%,#245061 0%,transparent 60%),linear-gradient(135deg,#1b2b37,#17202c 72%);border-radius:20px;padding:26px 30px;box-shadow:0 16px 50px #02070b45;display:grid;grid-template-columns:minmax(0,1.3fr) minmax(240px,.7fr);gap:25px;align-items:center}
#${ROOT} .hero h1{font-size:clamp(26px,3.1vw,42px);line-height:1.25;letter-spacing:-1.5px;margin:13px 0 12px}#${ROOT} .hero h1.caution{color:var(--coral)}#${ROOT} .hero h1.ok{color:var(--mint)}#${ROOT} .hero p{font-size:14px;line-height:1.75;color:#bdcddd;margin:0;max-width:650px}#${ROOT} .bigpos{border-left:1px solid #405364;padding:5px 0 5px 27px}#${ROOT} .bigpos .num{font-size:clamp(38px,5.2vw,60px);font-weight:850;letter-spacing:-2px;line-height:1.15}#${ROOT} .bigpos .lbl{font-size:13px;color:#a4b9cc;margin-top:8px}
#${ROOT} .barpos{display:flex;width:100%;height:9px;overflow:hidden;border-radius:99px;background:#394754;margin-top:18px}#${ROOT} .barpos .equity{background:#4ad1a5;height:100%}
#${ROOT} .grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:16px}#${ROOT} .mini{background:var(--pane);border:1px solid var(--border);border-radius:14px;padding:18px 20px;min-height:130px}#${ROOT} .mini .label{font-size:13px;color:#c4d0dd;font-weight:650}#${ROOT} .mini .number{font-size:28px;font-weight:850;margin:9px 0 5px;letter-spacing:-.7px}#${ROOT} .mini .desc{color:var(--muted);font-size:12px;line-height:1.6}#${ROOT} .danger{color:var(--coral)!important}#${ROOT} .good{color:var(--mint)!important}#${ROOT} .warn{color:var(--amber)!important}
#${ROOT} .sectionhead{display:flex;align-items:end;justify-content:space-between;gap:14px;margin:34px 0 15px}#${ROOT} .sectionhead h2{font-size:21px;line-height:1.2;margin:0;letter-spacing:-.5px}#${ROOT} .sectionhead p{font-size:12px;color:var(--muted);margin:5px 0 0}#${ROOT} .seven{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}#${ROOT} .metric{background:var(--pane);border:1px solid var(--border);border-radius:15px;padding:20px;min-width:0}#${ROOT} .metric-top{display:flex;justify-content:space-between;align-items:start;gap:12px}#${ROOT} .metric-name{font-weight:730;font-size:15px}#${ROOT} .metric-desc{font-size:12px;color:var(--muted);margin-top:5px}#${ROOT} .metric-value{font-weight:820;font-size:28px;letter-spacing:-.7px;margin:14px 0 1px}#${ROOT} .metric-unit{font-size:13px;color:var(--muted);font-weight:550;margin-left:3px}#${ROOT} .metric-state{font-size:12px;display:inline-flex;align-items:center;gap:4px;border:1px solid var(--border);border-radius:99px;padding:5px 10px;white-space:nowrap;background:#253343}#${ROOT} .meter{height:10px;background:linear-gradient(90deg,#e76676 0%,#e6a34e 27%,#7e8f9e 50%,#52ac93 75%,#28c3a3 100%);border-radius:99px;margin:19px 0 9px;position:relative}#${ROOT} .meter.risk{background:linear-gradient(90deg,#39c5a3 0%,#75a4a3 35%,#e0bd5c 65%,#ed6873 100%)}#${ROOT} .meter .dot{position:absolute;left:var(--x);top:50%;width:15px;height:20px;border:3px solid #ffffff;border-radius:7px;transform:translate(-50%,-50%);background:#111b26;box-shadow:0 0 0 2px #121b23}#${ROOT} .scale{display:flex;justify-content:space-between;font-size:11px;color:#889daf}#${ROOT} .metric-note{font-size:12px;color:#b5c7d7;margin:14px 0 0;line-height:1.55}#${ROOT} .metric-note strong{color:#ebf5ff}#${ROOT} .metric-footer{font-size:11px;color:#7e94a8;margin-top:11px}
#${ROOT} .signalbox{display:flex;align-items:center;justify-content:space-between;gap:15px;border:1px solid #3b4b5b;background:#14212c;border-radius:13px;margin-top:14px;padding:15px 18px}#${ROOT} .signalbox .label{font-size:13px;color:#b6cddd}#${ROOT} .signalbox strong{font-size:15px}#${ROOT} .signalbox small{display:block;color:#91a8b9;margin-top:4px;font-size:11px}#${ROOT} .charts{display:grid;grid-template-columns:1fr 1fr;gap:14px}#${ROOT} .chartbox{background:var(--pane);border:1px solid var(--border);border-radius:15px;padding:18px;min-width:0}#${ROOT} .chartbox h3{margin:0 0 13px;font-size:14px}#${ROOT} .chartbox svg{width:100%;height:220px;display:block;background:#111a25;border-radius:10px}#${ROOT} .chartbox .legend{font-size:12px;color:#a5bacd;margin-top:11px}#${ROOT} .legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
#${ROOT} details{border:1px solid var(--border);border-radius:13px;background:#161e29;margin-top:10px;overflow:hidden}#${ROOT} summary{cursor:pointer;padding:16px 18px;font-size:14px;font-weight:740}#${ROOT} summary::marker{color:#9eb1c2}#${ROOT} .detailcontent{border-top:1px solid var(--border);padding:15px 19px;font-size:13px;color:#b6c7d7;line-height:1.85}#${ROOT} .detailcontent p{margin:6px 0 12px}#${ROOT} .detailcontent b{color:#ebf5ff}#${ROOT} .footer{margin-top:25px;font-size:11px;color:#8096aa;line-height:1.7}#${ROOT} .err{color:#ffb19b}
@media(max-width:800px){#${ROOT} .hero{grid-template-columns:1fr}#${ROOT} .bigpos{border-left:0;border-top:1px solid #405364;padding:20px 0 0}#${ROOT} .seven,#${ROOT} .charts{grid-template-columns:1fr}#${ROOT} .topin{align-items:flex-start;flex-direction:column;padding-top:16px;padding-bottom:16px}#${ROOT} .topright{width:100%}}@media(max-width:600px){#${ROOT} .wrap{padding-left:15px;padding-right:15px}#${ROOT} .hero{padding:22px 20px}#${ROOT} .grid3{grid-template-columns:1fr;gap:9px}#${ROOT} .mini{min-height:0;padding:15px 17px}#${ROOT} .mini .number{font-size:26px}#${ROOT} .seven{gap:10px}#${ROOT} .metric{padding:17px}#${ROOT} .metric-value{font-size:26px}#${ROOT} .sectionhead h2{font-size:19px}#${ROOT} .signalbox{display:block}#${ROOT} .signalbox>div:last-child{margin-top:10px}}
`;
  const style = document.createElement('style'); style.id = 'v13-modern-styles'; style.textContent = css; document.head.appendChild(style);
  const fmt = (n, digits=1) => typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('ko-KR', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
  const safeDate = s => /^\d{8}$/.test(String(s || '')) ? `${s.slice(0,4)}.${s.slice(4,6)}.${s.slice(6,8)}` : '확인 필요';
  const freshDate = s => {if(!/^\d{8}$/.test(String(s||'')))return false;const t=Date.parse(s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8)+'T00:00:00+09:00');return Number.isFinite(t) && Date.now()-t<8*86400000 && Date.now()-t> -86400000;};
  const clamp = (n,min,max) => Math.max(min,Math.min(max,n));
  const nval = v => (typeof v === 'number' && Number.isFinite(v) ? v : null);
  const src = name => fetch('./data/'+name+'?u='+Date.now(), {cache:'no-store'}).then(r=>{if(!r.ok)throw Error(name+' HTTP '+r.status);return r.json()});
  const $ = id => document.getElementById(id);
  const node = (tag,cls,text) => {const el=document.createElement(tag);if(cls)el.className=cls;if(text!=null)el.textContent=text;return el;};
  const el = (tag,props={},...children)=>{const x=document.createElement(tag);for(const [k,v] of Object.entries(props)){if(k==='class')x.className=v;else if(k==='text')x.textContent=v;else if(k==='html')x.innerHTML=v;else x.setAttribute(k,v);}for(const c of children){if(c)x.append(c);}return x;};
  function meter(value, low, high, reverse, labels) {
    const pct = nval(value)===null?50:clamp((value-low)/(high-low)*100,1,99);
    const m=el('div',{class:'meter'+(reverse?' risk':'')});m.style.setProperty('--x',pct+'%');m.append(el('span',{class:'dot','aria-hidden':'true'}));
    const scale=el('div',{class:'scale'},node('span','',labels[0]),node('span','',labels[1]));
    return [m,scale];
  }
  const formatPercent=(x,d=1) => nval(x)===null?'—':(x>0?'+':'')+fmt(x,d)+'%';
  function metricCard(cfg){
    const card=node('article','metric');
    const head=node('div','metric-top');
    const left=node('div');left.append(node('div','metric-name',cfg.title),node('div','metric-desc',cfg.subtitle));
    const state=node('span','metric-state '+(cfg.color||''),cfg.state);head.append(left,state);card.append(head);
    const value=node('div','metric-value',cfg.value);value.classList.add(cfg.color||'');card.append(value);
    const [bar,scale]=meter(cfg.raw,cfg.min,cfg.max,cfg.risk,cfg.ends);card.append(bar,scale);
    card.append(node('p','metric-note',cfg.note));card.append(node('div','metric-footer',cfg.footer));return card;
  }
  function drawLine(svg,data,series,unit=''){
    const NS='http://www.w3.org/2000/svg';
    const make=(name,attributes={},txt)=>{const x=document.createElementNS(NS,name);for(const [k,v] of Object.entries(attributes))x.setAttribute(k,String(v));if(txt!==undefined)x.textContent=txt;return x;};
    svg.replaceChildren();svg.setAttribute('viewBox','0 0 520 220');svg.setAttribute('preserveAspectRatio','none');
    const valid=data.filter(x=>series.every(s=>nval(x[s.key])!==null));
    if(valid.length<3){svg.append(make('text',{x:160,y:112,fill:'#9fb0c4','font-size':14},'시계열 데이터 부족'));return;}
    const vals=valid.flatMap(d=>series.map(s=>d[s.key]));let lo=Math.min(...vals),hi=Math.max(...vals);if(hi-lo<.0001){lo-=1;hi+=1;}
    const pad=(hi-lo)*.1;lo-=pad;hi+=pad;
    const y=v=>181-(v-lo)/(hi-lo)*141;
    for(let i=0;i<4;i++){const yy=41+i*(140/3);svg.append(make('line',{x1:40,y1:yy,x2:500,y2:yy,stroke:'#26394a','stroke-width':1}));}
    for(const s of series){const d=valid.map((x,i)=>(i?'L':'M')+(40+i*460/(valid.length-1)).toFixed(2)+','+y(x[s.key]).toFixed(2)).join(' ');
      svg.append(make('path',{d,stroke:s.color,fill:'none','stroke-width':2.6,'stroke-linejoin':'round','stroke-linecap':'round'}));}
    svg.append(make('text',{x:12,y:18,fill:'#9db0c2','font-size':12},fmt(hi,unit==='bp'?1:0)+unit));
    svg.append(make('text',{x:12,y:214,fill:'#91a7ba','font-size':11},safeDate(valid[0].date?.replaceAll('-',''))));
    svg.append(make('text',{x:395,y:214,fill:'#91a7ba','font-size':11},safeDate(valid.at(-1).date?.replaceAll('-',''))));
  }
  const timeNorm = d => String(d||'').replaceAll('-','');
  const olderHistory = () => { try{return typeof DATA !== 'undefined' && Array.isArray(DATA.history) ? DATA.history : [];}catch(e){return [];} };
  function setText(id,value){const e=$(id);if(e)e.textContent=value;}
  function showRender(p){
    const root=$(ROOT);if(!root)return;
    const {krx:k,breadth:b,stage5:s5,stage6:s6,backtest:bt,breadthHistory:bh}=p;
    const primaryDate=k?.date||s5?.date||bt?.market_data_date||'';
    const dated=[k?.date,b?.date,s5?.date,s6?.date].filter(Boolean);
    const aligned=dated.length===4 && dated.every(d=>d===dated[0]);
    const current=aligned && freshDate(dated[0]);
    const history=olderHistory();
    const meta=(()=>{try{return typeof DATA!=='undefined' ? DATA.meta||{}:{};}catch(e){return {};}})();
    const credit=nval(meta.credit_bp);
    const exposure=bt?.forward_status==='CERTIFIED_ORIGINAL_POSITION' && nval(bt.certified_original_target_exposure_pct)!==null && bt.market_data_date===primaryDate && bt.archive_validation?.status==='EXACT_REPLAY' && bt.archive_validation?.exposure_mismatches===0 ? bt.certified_original_target_exposure_pct:null;
    const validPosition=current && exposure!==null && exposure>=0 && exposure<=100;
    const fdate=safeDate(primaryDate);
    const buyPass=k && nval(k.advancing_value_ratio_pct)!==null ? k.advancing_value_ratio_pct>50:null;
    const riskLow=nval(bt?.last_review_risk_lower);
    const riskHigh=nval(bt?.last_review_risk_upper);
    const heroTitle=!aligned?'수집 날짜 확인 필요':!current?'데이터 갱신 필요':validPosition?(exposure===0?'현금 100% 유지':`주식 ${fmt(exposure,0)}% 유지`):'원본 매매 판단 보류';
    const rootWrap=root.querySelector('.content');
    setText('v13-data-date',fdate+' 기준');
    setText('v13-headline',heroTitle);
    $('v13-headline')?.classList.toggle('caution',validPosition&&exposure===0);
    $('v13-headline')?.classList.toggle('ok',validPosition&&exposure>=50);
    setText('v13-hero-desc',!aligned?'KRX 지표의 기준일이 같지 않아 판단을 보류합니다.':!current?'마지막 수집일이 오래됐습니다. 새로운 수집 실행 후 확인하세요.':validPosition?
      ('기존 V7 전략의 목표 주식 비중을 재현한 결과입니다. '+(bt.latest_action_certified==='HOLD'?'새 매도 주문이 아니라 기존 포지션 유지입니다.':'기존 포지션 상태를 확인했습니다.')+' 신규 BUY 생성은 전체 원천점수가 확보될 때까지 보류합니다.'):
      '원본 V7의 최신 목표 비중을 확정할 수 없어 매매 판단을 보류합니다. 임의로 BUY/SELL을 생성하지 않습니다.');
    setText('v13-pos-number',validPosition?fmt(exposure,0)+'%':'—');
    setText('v13-pos-label',validPosition?'목표 주식 비중 · 현금 '+fmt(100-exposure,0)+'%':'목표 주식 비중 · 확인 필요');
    $('v13-position-bar').style.width=(validPosition?exposure:0)+'%';
    setText('v13-mini-buy',!aligned?'기준일 불일치':buyPass===false?'미충족':buyPass===true?'필터 충족':'확인 필요');
    setText('v13-mini-buy-desc',buyPass===null?'데이터 없음':'상승 거래대금 '+fmt(k.advancing_value_ratio_pct,2)+'% · 기준 50% 초과');
    setText('v13-mini-risk',riskLow!==null&&riskHigh!==null ? fmt(riskLow,1)+'–'+fmt(riskHigh,1)+'점':'—');
    setText('v13-mini-risk-desc',riskLow!==null?'직전 정기 평가 위험점수 범위 · 65점 이상이면 비중 0%':'위험점수 계산 확인 필요');
    setText('v13-mini-review',bt?.last_review_date?safeDate(bt.last_review_date):'확인 필요');
    setText('v13-mini-review-desc','V7 원본 규칙 · 5거래일마다 재평가');
    setText('v13-v7-event',`원본 V7: 과거 ${bt?.archive_validation?.sessions||'—'}거래일 재현 / BUY ${bt?.archive_validation?.buy_events??'—'}회 · SELL ${bt?.archive_validation?.sell_events??'—'}회`);
    setText('v13-signal-sub',aligned&&validPosition ? '위 목표 비중은 검증 가능한 포지션입니다. 신규 매매 신호와 구분합니다.' : '현재 날짜의 V7 점수를 완전히 계산할 수 없어 신규 매매 신호는 보류합니다.');
    const metrics=$('v13-metrics');metrics.replaceChildren();
    const b20=nval(b?.breadth?.['20']?.above_pct),b60=nval(b?.breadth?.['60']?.above_pct),b200=nval(b?.breadth?.['200']?.above_pct);
    const hi=nval(b?.high_52w_pct),lo=nval(b?.low_52w_pct);
    const dist=nval(s5?.kospi_sma125_distance_pct), vix=nval(s5?.vkospi), pcr=nval(s5?.kospi200_pcr_volume), rel=nval(s6?.equity_minus_bond_20d_pctpt);
    const creditDate=meta.credit_date || '';
    const configs=[
      {title:'시장 모멘텀',subtitle:'KOSPI · 125일선 이격도',value:formatPercent(dist,2),raw:dist,min:-30,max:30,state:dist===null?'자료 없음':dist<0?'추세 약세':'추세 강세',color:dist===null?'':dist<0?'danger':'good',ends:['125일선 크게 하회','125일선 크게 상회'],note:'0%가 125일 이동평균선입니다. '+(dist===null?'자료 확인 필요':dist<0?'현재 지수는 이동평균선 아래에 있습니다.':'현재 지수는 이동평균선 위에 있습니다.'),footer:`기준일 ${fdate} · 막대 -30%~+30%는 비교용 눈금`},
      {title:'52주 신고가·신저가',subtitle:'최근 252거래일 종가 기준',value:hi!==null&&lo!==null?fmt(hi,2)+'% / '+fmt(lo,2)+'%':'—',raw:hi!==null&&lo!==null?hi-lo:null,min:-10,max:10,state:hi===null||lo===null?'자료 없음':hi<lo?'신저가 우세':'신고가 우세',color:hi===null||lo===null?'':hi<lo?'danger':'good',ends:['신저가 우세','신고가 우세'],note:hi===null||lo===null?'자료 확인 필요':`신고가 ${fmt(hi,2)}% / 신저가 ${fmt(lo,2)}% · 순차이 ${fmt(hi-lo,2)}%p`,footer:`기준일 ${fdate} · 막대는 (신고가%-신저가%) -10~+10%p`},
      {title:'시장 폭',subtitle:'이동평균선 상회 종목 비율',value:b20!==null?fmt(b20,1)+'%':'—',raw:b20,min:0,max:100,state:b20===null?'자료 없음':b20<30?'광범위한 약세':b20>70?'광범위한 강세':'중립 범위',color:b20===null?'':b20<30?'danger':b20>70?'good':'warn',ends:['0% · 하회 종목 다수','100% · 상회 종목 다수'],note:b20===null?'자료 확인 필요':`20일 ${fmt(b20,1)}% · 60일 ${fmt(b60,1)}% · 200일 ${fmt(b200,1)}%`,footer:`기준일 ${fdate} · 20일선 상회 비율을 막대로 표시`},
      {title:'시장 변동성',subtitle:'VKOSPI · 코스피200 변동성지수',value:fmt(vix,2),raw:vix,min:10,max:70,risk:true,state:vix===null?'자료 없음':vix>=35?'고변동성':vix>=25?'변동성 경계':'상대적 안정',color:vix===null?'':vix>=35?'danger':vix>=25?'warn':'good',ends:['변동성 낮음','변동성 높음'],note:vix===null?'자료 확인 필요':'값이 클수록 옵션시장이 예상하는 변동성이 큽니다. 매수·매도 점수 자체는 아닙니다.',footer:`기준일 ${fdate} · 10~70 눈금은 시각화용`},
      {title:'풋/콜 거래량 비율',subtitle:'KOSPI200 일반 옵션 PUT / CALL',value:fmt(pcr,3),raw:pcr,min:0.3,max:1.5,risk:true,state:pcr===null?'자료 없음':pcr<.7?'콜 거래량 우세':pcr>1?'풋 거래량 우세':'혼재',color:pcr===null?'':pcr<.7?'warn':pcr>1?'warn':'',ends:['콜 거래량 우세','풋 거래량 우세'],note:'비율이 높을수록 풋 거래량이 상대적으로 많습니다. 단독으로 공포·탐욕을 단정하지 않습니다.',footer:`기준일 ${fdate} · 0.3~1.5 눈금은 시각화용`},
      {title:'주식·국채 상대수익률',subtitle:'최근 20거래일 · KOSPI − 국채 ETF',value:rel!==null?(rel>0?'+':'')+fmt(rel,2)+'%p':'—',raw:rel,min:-30,max:30,state:rel===null?'자료 없음':rel<0?'주식 상대 약세':'주식 상대 강세',color:rel===null?'':rel<0?'danger':'good',ends:['주식 상대 약세','주식 상대 강세'],note:'주식과 국채 ETF의 가격 수익률 차이입니다. 분배금·총수익은 포함되지 않습니다.',footer:`기준일 ${fdate} · -30~+30%p 눈금은 시각화용`},
      {title:'신용 스프레드',subtitle:'AA- 회사채 3년 − 국고채 3년',value:credit!==null?fmt(credit,1)+'bp':'—',raw:credit,min:0,max:150,risk:true,state:credit===null?'자료 없음':'신용위험 수준 참고',color:credit===null?'':'warn',ends:['스프레드 좁음','스프레드 넓음'],note:'값이 높을수록 기업 자금조달의 상대적 위험 프리미엄이 큽니다. 절대 수준만으로 경고를 확정하지 않습니다.',footer:`기준일 ${creditDate.replaceAll('-','.')} · 0~150bp 시각화용 눈금`},
    ];
    configs.forEach(c=>metrics.append(metricCard(c)));
    const bdata=Array.isArray(bh)?bh.filter(x=>x&&nval(x.b20)!==null&&nval(x.b60)!==null).slice(-130):[];
    drawLine($('v13-chart-breadth'),bdata,[{key:'b20',color:'#4bd8ae'},{key:'b60',color:'#f4c76a'}],'%');
    const cdata=history.filter(x=>nval(x['신용스프레드_bp'])!==null).slice(-260).map(x=>({date:x.date,spread:x['신용스프레드_bp']}));
    drawLine($('v13-chart-credit'),cdata,[{key:'spread',color:'#87b9ff'}],'bp');
    setText('v13-credit-dated','신용 스프레드 최신 기준일 '+(creditDate||'확인 필요')+' · 주식 데이터와 별도 수집');
    setText('v13-source-info','종가 기준 '+fdate+' · V7 원본 연구자료는 2026.10.23까지 · 정기평가일 '+safeDate(bt?.last_review_date));
  }
  function initialize(){
    const root=el('div',{id:ROOT});
    root.innerHTML=`
      <div class="top"><div class="wrap topin"><div><div class="brand">K-MARKET <strong>OSCILLATOR V13</strong></div><div class="sub">백테스트 원본 전략 · 한국시장 리스크 대시보드</div></div><div class="topright"><span class="chip" id="v13-data-date">데이터 확인 중</span><a class="act primary" href="https://github.com/lim1380/korea-market-oscillator/actions/workflows/refresh.yml" target="_blank" rel="noopener noreferrer">↻ 새 데이터 수집</a><button id="v13-reload" type="button">⟳ 화면 새로고침</button></div></div></div>
      <div class="wrap content">
        <section class="hero"><div><div class="eyebrow">TODAY'S POSITION · 원본 V7 전략</div><h1 id="v13-headline">데이터 확인 중</h1><p id="v13-hero-desc">검증된 원본 매매 상태를 불러오고 있습니다.</p></div><div class="bigpos"><div class="eyebrow">TARGET EQUITY EXPOSURE</div><div class="num" id="v13-pos-number">—</div><div class="lbl" id="v13-pos-label">주식 목표 비중 확인 중</div><div class="barpos"><div class="equity" id="v13-position-bar" style="width:0%"></div></div></div></section>
        <div class="grid3"><div class="mini"><div class="label">① V13 매수 필터</div><div class="number" id="v13-mini-buy">—</div><div class="desc" id="v13-mini-buy-desc">상승 거래대금 50% 초과</div></div><div class="mini"><div class="label">② 원본 V7 매도 위험</div><div class="number" id="v13-mini-risk">—</div><div class="desc" id="v13-mini-risk-desc">정기 평가 위험점수</div></div><div class="mini"><div class="label">③ 마지막 정기 평가</div><div class="number" id="v13-mini-review">—</div><div class="desc" id="v13-mini-review-desc">5거래일마다 재평가</div></div></div>
        <div class="signalbox"><div><div class="label">원본 매매 로직 검증 상태</div><strong id="v13-v7-event">과거 기록 대조 중...</strong><small id="v13-signal-sub">현재 매수·매도 결과를 검증 중입니다.</small></div><span class="chip">새로운 임의 신호 없음</span></div>
        <div class="sectionhead"><div><h2>공포·탐욕 구성지표 7개</h2><p>원점수의 방향과 의미를 막대로 표시합니다. 가짜 종합점수나 백분위는 사용하지 않습니다.</p></div><span class="chip">시장 데이터</span></div>
        <section id="v13-metrics" class="seven" aria-label="시장 지표"></section>
        <div class="sectionhead"><div><h2>시장 흐름</h2><p>당일 숫자뿐 아니라 최근 방향도 함께 확인</p></div></div>
        <div class="charts"><div class="chartbox"><h3>20일·60일 이동평균 상회 종목 비율</h3><svg id="v13-chart-breadth" role="img" aria-label="20일 및 60일 이동평균 상회 종목 비율 추세"></svg><div class="legend"><span class="dot" style="background:#4bd8ae"></span>20일선 <span style="display:inline-block;width:15px"></span><span class="dot" style="background:#f4c76a"></span>60일선</div></div><div class="chartbox"><h3>신용 스프레드 추이</h3><svg id="v13-chart-credit" role="img" aria-label="신용 스프레드 추세"></svg><div class="legend" id="v13-credit-dated">신용 데이터 기준일 확인 중</div></div></div>
        <div class="sectionhead"><div><h2>궁금할 때만 자세히 보기</h2><p>매매 규칙과 데이터 해석은 아래에서 확인할 수 있습니다.</p></div></div>
        <details><summary>매수·매도 규칙과 백테스트 기준</summary><div class="detailcontent"><p><b>매수:</b> 과거 검증한 V7 BUY 신호와 상승 거래대금 비율 50% 초과가 모두 확인될 때만 V13 매수 후보입니다.</p><p><b>매도:</b> V7 위험점수·주식 비중 상태 전환 규칙을 그대로 유지합니다. 신용 스프레드는 경고용으로만 사용합니다.</p><p><b>백테스트:</b> V7 과거 2,160거래일의 기록은 재현했지만 신규 거래일의 원본 구성점수가 모두 재계산되는 것은 아닙니다. 과거 연구 결과를 새 신호의 확률처럼 사용하지 않습니다.</p></div></details>
        <details><summary>지표별 색상과 게이지 읽는 방법</summary><div class="detailcontent"><p>게이지의 <b>흰색 위치 표시</b>는 실제 숫자를 미리 정한 눈금에 배치한 것입니다. 빨강·노랑·초록은 쉬운 방향 해석용이며, 과거 상대 백분위나 최종 매매 신호가 아닙니다.</p><p>시장의 125일선, 신고가·신저가, 이동평균선 상회 비율, VKOSPI, PCR, 주식·국채 상대수익률, 신용 스프레드 등 7개를 각각 구분해 볼 수 있습니다.</p><p>VKOSPI와 옵션 PCR은 시장상황에 따라 역방향 해석이 가능한 참고지표입니다. 신용 스프레드는 날짜가 별도로 표시됩니다.</p></div></details>
        <details><summary>데이터 출처 · 갱신 방법 · 한계</summary><div class="detailcontent"><p><b>자동 갱신:</b> 한국시간 평일 18시 30분 GitHub Actions 예약 실행. 시작 지연이나 원천 데이터 지연이 있을 수 있습니다.</p><p><b>수동 갱신:</b> 위 ‘새 데이터 수집’으로 GitHub Actions를 열어 Run workflow를 클릭하고, 실행 완료 후 ‘화면 새로고침’을 누르세요.</p><p><b>출처:</b> KRX 공개 API, ECOS 및 기존 백테스트 보관자료. 현재 시장 지표와 과거 전략 자료의 기간은 다릅니다.</p><p>이 화면은 검증 가능한 원본 목표 비중만 표시합니다. 미계산 BUY/SELL을 임의로 만들어 표시하지 않습니다.</p></div></details>
        <div class="footer" id="v13-source-info">원본 데이터 확인 중...</div>
      </div>`;
    document.body.insertBefore(root,document.body.firstChild);
    $('v13-reload').addEventListener('click',()=>{const u=new URL(location.href);u.searchParams.set('reload',Date.now());location.assign(u.href)});
    Promise.allSettled(['krx_latest.json','breadth_latest.json','stage5_latest.json','stage6_latest.json','v13_backtested_latest.json','breadth_history.json'].map(src))
     .then(res=>{const names=['krx','breadth','stage5','stage6','backtest','breadthHistory'];const p={};res.forEach((r,i)=>{p[names[i]]=r.status==='fulfilled'?r.value:null;});showRender(p);})
     .catch(err=>{setText('v13-headline','데이터 확인 필요');setText('v13-hero-desc',err.message||'자료 수집 결과를 확인할 수 없습니다.');});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();
