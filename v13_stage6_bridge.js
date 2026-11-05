/* V13 stage 6: render verified KOSPI vs bond ETF relative return. */
(() => {
  'use strict';
  const fmtDate = s => /^\d{8}$/.test(s || '')
    ? `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}` : '날짜 확인 필요';
  const numeric = v => typeof v === 'number' && Number.isFinite(v);
  async function start() {
    const statusId = 'stage6-status';
    const statusNode = () => {
      let p = document.getElementById(statusId);
      if (!p) {
        p = document.createElement('p');
        p.id = statusId;
        p.className = 'foot';
        document.querySelector('.lead')?.append(p);
      }
      return p;
    };
    try {
      const response = await fetch('./data/stage6_latest.json?ts=' + Date.now(), {cache:'no-store'});
      if (!response.ok) throw new Error(`stage6_latest.json HTTP ${response.status}`);
      const d = await response.json();
      const valid = /^\d{8}$/.test(d.date || '') &&
        numeric(d.equity_return_20d_pct) && numeric(d.bond_return_20d_pct) &&
        numeric(d.equity_minus_bond_20d_pctpt) &&
        d.bond_code === '114260' && d.signal_status === 'not_calculated';
      if (!valid) throw new Error('6단계 JSON 값 또는 기준일 검증 실패');
      if (Math.abs((d.equity_return_20d_pct - d.bond_return_20d_pct) -
          d.equity_minus_bond_20d_pctpt) > 0.001) {
        throw new Error('6단계 상대수익률 계산값 불일치');
      }
      // 5단계 지표와 거래일 일치를 확인하여 혼합 날짜를 숨김
      const stage5Response = await fetch('./data/stage5_latest.json?ts=' + Date.now(), {cache:'no-store'});
      if (!stage5Response.ok) throw new Error('5단계 기준일을 확인할 수 없음');
      const stage5 = await stage5Response.json();
      if (d.date !== stage5.date) throw new Error(`5·6단계 기준일 불일치: ${stage5.date} / ${d.date}`);
      const card = document.getElementById('indicators')?.children[5];
      if (!card) throw new Error('메인 화면 상대수익률 카드가 없음');
      const value = `${d.equity_minus_bond_20d_pctpt > 0 ? '+' : ''}${d.equity_minus_bond_20d_pctpt.toFixed(2)}%p`;
      card.querySelector('.muted').textContent = 'KOSPI 20거래일 가격수익률 − KODEX 국고채3년 ETF 20거래일 가격수익률';
      card.querySelector('.big').textContent = value;
      card.querySelector('.foot').textContent =
        `기준일 ${fmtDate(d.date)} · KOSPI ${d.equity_return_20d_pct.toFixed(2)}% · 국채 ETF ${d.bond_return_20d_pct.toFixed(2)}% · 분배금 미반영`;
      const p = statusNode();
      if (p) p.textContent = `6단계 상대수익률 ${fmtDate(d.date)} 자동 연동 · ${value} · 종합 매수·매도 신호는 미계산`;
    } catch(err) {
      console.warn('Stage 6 indicator unavailable:', err.message);
      const p = statusNode();
      if (p) {
        p.style.color = '#f5c34d';
        p.textContent = `6단계 상대수익률 자동 연동 확인 필요: ${err.message}. 값은 임의로 표시하지 않습니다.`;
      }
    }
  }
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
