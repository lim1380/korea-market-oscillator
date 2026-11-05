/* Archived V7/V13 strategy adapter. Uses data/v13_backtested_latest.json
 * generated only after 2160/2160 exact historical replay. The new-day output
 * can certify an exposure if it is invariant under MISSING future E and 30pt
 * reversal factor; otherwise it must say unavailable. No heuristic substitutes.
 */
(() => {
  'use strict';
  const node = id => document.getElementById(id);
  const num = value => typeof value === 'number' && Number.isFinite(value);
  const date = d => /^\d{8}$/.test(d||'') ? d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6) : '확인 필요';
  const safe = text => String(text||'');
  // The previously installed 5-heuristic badge is NOT the backtested model.
  // Hide it consistently, including if its independent fetch returns later.
  const css=document.createElement('style');
  css.textContent='#v13-market-status{display:none!important}';
  document.head.append(css);
  function card(title,headline,details,footer,color) {
    let panel=node('v13-original-status');
    if(!panel) {
      panel=document.createElement('section');panel.id='v13-original-status';panel.className='card';
      panel.style.cssText='margin:14px 0;border:1px solid #4d796d';
      const h2=[...document.querySelectorAll('h2.section')].find(x=>x.textContent.includes('공포·탐욕'));
      if(h2)h2.before(panel);else document.querySelector('main')?.prepend(panel);
    }
    panel.replaceChildren();
    const h=document.createElement('h3');h.textContent=title;
    const big=document.createElement('div');big.className='big';big.textContent=headline;big.style.color=color;
    const text=document.createElement('p');text.className='rule';text.textContent=details;
    const foot=document.createElement('p');foot.className='foot';foot.textContent=footer;
    panel.append(h,big,text,foot);
  }
  function setVerdict(which,headline,reason,color) {
    const cards=document.querySelector('h2.section + .cards');
    const cardNode=cards?.children[which];
    if(!cardNode)return;
    const big=cardNode.querySelector('.big');
    const detail=cardNode.querySelector('.rule');
    if(big){big.textContent=headline;big.style.color=color;}
    if(detail)detail.textContent=reason;
  }
  async function load(path) {
    const response=await fetch('./data/'+path+'?ts='+Date.now(),{cache:'no-store'});
    if(!response.ok)throw Error(path+' HTTP '+response.status);
    return response.json();
  }
  async function main() {
    try {
      const [model,krx] = await Promise.all([
        load('v13_backtested_latest.json'),load('krx_latest.json')]);
      if(model.schema_version!=='v13-original-archive-bound-v1' ||
         model.archive_validation?.status!=='EXACT_REPLAY' ||
         model.archive_validation?.sessions!==2160 ||
         model.archive_validation?.action_mismatches!==0 ||
         model.archive_validation?.exposure_mismatches!==0 ||
         model.market_data_date!==krx.date)
        throw Error('원본 검증 또는 최신 시장 날짜가 일치하지 않습니다');
      const day=model.market_data_date, parsed=Date.parse(date(day)+'T12:00:00+09:00');
      if(!Number.isFinite(parsed)||Date.now()-parsed>7*86400000||parsed>Date.now()+86400000)
        throw Error('마지막 매매모델 평가일이 오래되었거나 미래입니다');
      const ratio=model.latest_rising_value_ratio_pct;
      if(!num(ratio)||!num(krx.advancing_value_ratio_pct)||Math.abs(ratio-krx.advancing_value_ratio_pct)>0.01)
        throw Error('상승 거래대금 자료가 일치하지 않습니다');
      const archive='과거 V7 2,160거래일 주식비중·매수·매도 기록 100% 재현';
      const historical='V13 조건: V7 BUY + 상승 거래대금 50% 초과, V7 SELL은 원본 그대로';
      if(model.forward_status==='CERTIFIED_ORIGINAL_POSITION' &&
         num(model.certified_original_target_exposure_pct)) {
        const pct=model.certified_original_target_exposure_pct;
        const proof=num(model.last_review_risk_lower) ?
          `최근 정기평가 ${date(model.last_review_date)} · 매도 위험점수 가능한 범위 ${model.last_review_risk_lower.toFixed(2)}~${model.last_review_risk_upper.toFixed(2)}점`:
          '정기평가 위험점수 점검';
        if(pct===0) {
          const decision='원본 전략: 현금 100% 유지';
          card('V7 원본 백테스트 규칙 · V13 선정 필터',decision,
            `${proof}. 위험점수 하한이 65점 이상이면 원본 규칙상 주식 목표비중은 0%입니다. 현재 BUY 신호가 아니라 기존 포지션 유지입니다.`,
            `${archive} · ${historical} · 최종 기준일 ${date(day)} · 마지막 V7 SELL ${date(model.last_archived_v7_sell_date)}`,
            '#ff7880');
          setVerdict(0,'매수 신호 없음',
            `백테스트된 V7 매수 신호를 현재 새로 확정한 것은 아닙니다. 마지막 검증 비중이 0%이며, 상승 거래대금 비율 ${ratio.toFixed(2)}% (${ratio>50?'필터 충족':'필터 미충족'})입니다.`,
            '#f5c34d');
          setVerdict(1,'현금 100% 유지',
            `V7 종합 매도위험 최소 ${model.last_review_risk_lower.toFixed(2)}점 ≥65점 (${date(model.last_review_date)} 정기평가). 마지막 실제 SELL 기록 ${date(model.last_archived_v7_sell_date)}. ${date(day)}에 새 매도 명령이 발생했다는 뜻은 아닙니다.`,
            '#ff7880');
        } else {
          card('V7 원본 백테스트 규칙 · V13 선정 필터',
            `검증 가능한 V7 목표 주식비중 ${pct.toFixed(0)}%`,
            `과거 상태 전환 규칙에 따라 목표 비중을 확인했습니다. 단, 최신 V7 BUY 점수를 원본 E 입력으로 새로 계산한 것은 아니므로 V13 신규 BUY 여부를 별도 확정하지 않습니다.`,
            `${archive} · ${historical} · 최종 기준일 ${date(day)}`,
            '#43d29e');
          setVerdict(0,'신규 매수 신호 검증 필요',
            `현재 V7 목표 주식비중 ${pct.toFixed(0)}%는 확인되지만 최신 E 점수가 없어 V13 BUY 조건 전체를 판정하지 않습니다.`, '#f5c34d');
          setVerdict(1,`V7 목표 주식비중 ${pct.toFixed(0)}%`,
            `원본 매도 위험 하한/상한을 사용해 가능한 비중을 검사했습니다. ${proof}.`, '#43d29e');
        }
      } else {
        const options=Array.isArray(model.possible_original_target_exposure_pct)?
          model.possible_original_target_exposure_pct.join(' / ')+'%':'확인 필요';
        card('V7 원본 백테스트 규칙 · 신호 미확정','정확한 최신 판단 보류',
          `원본 입력 중 E 공포점수 또는 매도 반전 점수 30점의 계산이 남았습니다. 가능한 목표 비중 ${options}. 임의의 신호를 생성하지 않습니다.`,
          `${archive} · ${historical} · 최종 기준일 ${date(day)}`,
          '#f5c34d');
        setVerdict(0,'판정 보류','현재 V7 BUY 점수의 실제 새 계산이 없으므로 확정할 수 없습니다.', '#f5c34d');
        setVerdict(1,'판정 보류','현재 V7 목표 비중이 모든 가능한 원본 입력에서 일치하지 않습니다.', '#f5c34d');
      }
      const lead=document.querySelector('.lead');
      if(lead && !node('v13-original-lead')) {
        const info=document.createElement('p');info.id='v13-original-lead';info.className='foot';
        info.style.color='#43d29e';
        info.textContent='[원본 전략 점검] '+archive+ ' · '+ date(day)+
           ' 기준 가능한 포지션을 별도 검증합니다. 위의 기존 안내 중 종합점수 미계산 표시는 원본 E 점수의 실시간 전체 재현이 아직 없다는 뜻입니다.';
        lead.append(info);
      }
    }catch(e) {
      console.warn('V13 archived strategy unavailable:',e);
      card('V7 원본 백테스트 규칙 · 모델 검증 필요',
        '자료 불일치 · 매매 판단 보류',safe(e.message)+
        '. 이전 시장의 신호를 최신 결과처럼 재사용하지 않습니다.',
        '해당 화면은 원본 V7/V13 백테스트 모델과 다른 5조건 시장위험 점검으로 대체하지 않습니다.',
        '#f5c34d');
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',main,{once:true});
  else main();
})();
