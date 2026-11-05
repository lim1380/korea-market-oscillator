/* Stage 5 independent read-only UI adapter. Zero signal inference. */
(() => {
  'use strict';
  const fetchData = () => fetch('./data/stage5_latest.json?t=' + Date.now(), {cache:'no-store'})
    .then(r => { if (!r.ok) throw new Error('stage5_latest.json HTTP ' + r.status); return r.json(); });
  const exactNum = x => typeof x === 'number' && Number.isFinite(x);
  const datefmt = s => /^\d{8}$/.test(s || '') ? s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6) : '미확인';
  const format = (n, digits) => n.toFixed(digits);
  function setCard(index, subtitle, value, foot) {
    const card = document.getElementById('indicators')?.children[index];
    if (!card) throw new Error('Indicator card layout changed');
    const sub = card.querySelector('.muted');
    const big = card.querySelector('.big');
    const note = card.querySelector('.foot');
    if (sub) sub.textContent = subtitle;
    if (big) big.textContent = value;
    if (note) note.textContent = foot;
  }
  async function init() {
    try {
      const d = await fetchData();
      if (!/^\d{8}$/.test(d.date || '') || !exactNum(d.kospi_close) ||
          !exactNum(d.kospi_sma125) || !exactNum(d.kospi_sma125_distance_pct) ||
          !exactNum(d.vkospi) || !exactNum(d.kospi200_pcr_volume) ||
          d.kospi_valid_sessions !== 125 || d.signal_status !== 'not_calculated') {
        throw new Error('Stage 5 JSON values or date invalid');
      }
      const date = datefmt(d.date);
      // The stage-4 adapter may finish after stage-5. Keep the header dates
      // truthful even if the two independent JSON fetches resolve out of order.
      const datesNode = document.getElementById('dates');
      if (datesNode) {
        const syncDate = () => {
          const old = datesNode.textContent || '';
          const fresh = old.replace(/VKOSPI\/PCR\/KOSPI:\s*(?:\d{4}-\d{2}-\d{2}|과거 자료)/, 'VKOSPI/PCR/KOSPI: ' + date);
          if (fresh !== old) datesNode.textContent = fresh;
          const note = datesNode.nextElementSibling;
          if (note && note.classList.contains('foot') && note.textContent.startsWith('자동 갱신: KRX 시장 폭')) {
            note.textContent = '자동 갱신: KRX 시장 폭·거래대금·KOSPI 모멘텀·VKOSPI·PCR. 메인 신용 스프레드는 기존 자료이며 최종 BUY/SELL은 미계산입니다.';
          }
        };
        syncDate();
        new MutationObserver(syncDate).observe(datesNode, {childList:true, characterData:true, subtree:true});
      }
      const distance = d.kospi_sma125_distance_pct;
      setCard(0, 'KOSPI 종가 / 125거래일 단순이동평균',
        (distance >= 0 ? '+' : '') + format(distance,2) + '%',
        `기준일 ${date} · 종가 ${format(d.kospi_close,2)} · SMA125 ${format(d.kospi_sma125,2)} · 종가/SMA−1`);
      setCard(3, 'VKOSPI · 코스피200 변동성지수', format(d.vkospi,2),
        `KRX 파생상품지수 · ${date} · 최종 매매점수에는 미반영`);
      setCard(4, 'KOSPI200 일반 옵션 거래량 PUT/CALL', format(d.kospi200_pcr_volume,3),
        `기준일 ${date} · PUT ${d.put_volume.toLocaleString('ko-KR')}계약 / CALL ${d.call_volume.toLocaleString('ko-KR')}계약 · 미니·위클리 제외`);
      const lead = document.querySelector('.lead');
      if (lead && !document.getElementById('stage5-status')) {
        const p = document.createElement('p');
        p.id = 'stage5-status';
        p.className = 'foot';
        p.textContent = `KRX 5단계 데이터: KOSPI 125일 모멘텀·VKOSPI·옵션 PCR ${date} 기준 자동 연동. 종합 매수·매도 판정은 아직 미계산.`;
        lead.append(p);
      }
    } catch (error) {
      console.warn('Stage 5 indicators unavailable:', error.message);
      const lead = document.querySelector('.lead');
      if (lead && !document.getElementById('stage5-status')) {
        const p = document.createElement('p');
        p.id = 'stage5-status';
        p.className = 'foot';
        p.style.color = '#f5c34d';
        p.textContent = 'KOSPI 모멘텀·VKOSPI·PCR의 최신 자료는 아직 확인되지 않았습니다. 아래 과거 지표값은 최신값이 아닐 수 있습니다.';
        lead.append(p);
      }
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
