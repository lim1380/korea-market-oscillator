/* V13 stage 4: read independently updated KRX JSONs on the main dashboard.
   Never manufacture a composite BUY/SELL score. No API secrets needed. */
(() => {
  'use strict';
  const src = (p) => fetch('./data/' + p + '?t=' + Date.now(), {cache:'no-store'})
    .then(r => { if (!r.ok) throw Error(`${p}: HTTP ${r.status}`); return r.json(); });
  const datefmt = s => /^\d{8}$/.test(s || '') ? `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}` : (s || '미확인');
  const el = id => document.getElementById(id);
  const fmt = (n, digits=2) => Number.isFinite(Number(n)) ? Number(n).toFixed(digits) : '자료 없음';
  const set = (node, value) => { if(node) node.textContent = value; };
  const applyCard = (i, title, sub, value, note) => {
    const card = el('indicators')?.children[i];
    if(!card) return;
    set(card.querySelector('h3'), title);
    set(card.querySelector('.muted'), sub);
    set(card.querySelector('.big'), value);
    set(card.querySelector('.foot'), note);
  };
  const init = async () => {
    const [breadth, krx, history] = await Promise.allSettled([
      src('breadth_latest.json'), src('krx_latest.json'), src('breadth_history.json')
    ]);
    const b = breadth.status==='fulfilled' ? breadth.value : null;
    const k = krx.status==='fulfilled' ? krx.value : null;
    const historyRows = history.status==='fulfilled' && Array.isArray(history.value) ? history.value : null;
    const badge = document.querySelector('header .tag');
    set(badge, b && k ? 'KRX 시장 폭 자동 연동 · 종합신호 미계산' : '부분 연동 · 종합신호 미계산');
    const dates = el('dates');
    if (dates) {
      // Legacy dates remain explicitly tagged as legacy; do not label VKOSPI/PCR as live.
      const legacy = (typeof DATA !== 'undefined' && DATA.meta) ? DATA.meta : {};
      dates.replaceChildren();
      dates.append(`시장 폭: ${b ? datefmt(b.date) : '수집 확인 필요'} · 거래대금 비율: ${k ? datefmt(k.date) : '수집 확인 필요'} · VKOSPI/PCR/KOSPI: ${legacy.legacy_date || '과거 자료'} · 신용 스프레드: ${legacy.credit_date || '과거 자료'} (메인 화면 기존값)`);
    }
    const note = document.createElement('p');
    note.className = 'foot';
    note.style.marginTop = '7px';
    note.textContent = '자동 갱신: KRX 시장 폭·거래대금만 연결. VKOSPI/PCR/KOSPI 및 메인 신용 스프레드는 과거 데이터이며, 최종 BUY/SELL은 계산하지 않습니다.';
    dates?.after(note);
    if (b && b.breadth) {
      const b20 = b.breadth['20']?.above_pct, b60=b.breadth['60']?.above_pct, b200=b.breadth['200']?.above_pct;
      applyCard(1, '52주 신고가·신저가', '최근 252거래일 종가 기준', `${fmt(b.high_52w_pct)}% / ${fmt(b.low_52w_pct)}%`, `기준일 ${datefmt(b.date)} · 신고가 ${b.high_52w_count}개 / 신저가 ${b.low_52w_count}개 · 종가 기준`);
      applyCard(2, '시장 폭', '20일·60일·200일 이동평균 상회 종목 비율', `${fmt(b20)}% / ${fmt(b60)}% / ${fmt(b200)}%`, `기준일 ${datefmt(b.date)} · 기간별 유효 종목수가 다를 수 있음`);
    }
    if (k && Number.isFinite(Number(k.advancing_value_ratio_pct))) {
      const ratio=Number(k.advancing_value_ratio_pct);
      const buyReason=el('buyreason');
      set(buyReason, `상승 거래대금 비율 ${fmt(ratio)}% (${datefmt(k.date)}) · 50% 초과 필터 ${ratio>50?'충족':'미충족'} · V7 종합점수는 아직 미계산`);
      const cards=document.querySelector('h2.section + .cards');
      if(cards && !el('krx-ratio-main')) {
        const card=document.createElement('div');card.className='card';card.id='krx-ratio-main';
        const h=document.createElement('h3');h.textContent='KRX 상승 거래대금 비율 (자동)';
        const val=document.createElement('div');val.className='big';val.textContent=fmt(ratio)+'%';
        val.style.color=ratio>50?'#43d29e':'#f5c34d';
        const small=document.createElement('div');small.className='foot';small.textContent=`${datefmt(k.date)} · 50% 초과 필터 ${ratio>50?'충족':'미충족'} · 단독 매수 신호 아님`;
        card.append(h,val,small);cards.append(card);
      }
    }
    if(historyRows?.length) {
      const chart=el('breadthChart');
      const draw = n => {
        if(!chart) return;
        const points=historyRows.filter(d => Number.isFinite(Number(d.b20)) && Number.isFinite(Number(d.b60))).slice(-n);
        if(points.length<2) return;
        const NS='http://www.w3.org/2000/svg';
        const mk=(tag,attrs={},content) => {const x=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs)) x.setAttribute(k,String(v));if(content!==undefined)x.textContent=content;return x;};
        chart.replaceChildren();
        chart.append(mk('line',{x1:20,y1:195,x2:500,y2:195,stroke:'#3b4751'}));
        for(const [key,color] of [['b20','#48c99b'],['b60','#e9bf5b']]){
          const coords=points.map((d,i) => [20+i*480/(points.length-1),195-Math.max(0,Math.min(100,Number(d[key])))*1.65]);
          chart.append(mk('path',{d:coords.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' '),stroke:color,'stroke-width':2.4,fill:'none'}));
        }
        chart.append(mk('text',{x:22,y:18,fill:'#a9b7c5','font-size':12},'100%'));
        chart.append(mk('text',{x:22,y:215,fill:'#a9b7c5','font-size':12},datefmt(points[0].date)));
        chart.append(mk('text',{x:385,y:215,fill:'#a9b7c5','font-size':12},datefmt(points.at(-1).date)));
      };
      const selected=el('ranges')?.querySelector('button.active');
      draw(Number(selected?.dataset.n || 260));
      // Installed after original chart listeners: newest history draw wins.
      el('ranges')?.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>draw(Number(button.dataset.n))));
      const legend=chart?.parentElement?.querySelector('.legend');
      set(legend,'녹색: 20일선 · 황색: 60일선 · 자동 수집 데이터');
    }
    if(!b || !k) {
      const p=document.createElement('div');p.className='foot';p.style.color='#f5c34d';
      p.textContent=`자동 수집 파일 확인 필요: ${!b?'시장 폭 ':''}${!k?'거래대금 ':''}. 웹사이트 배포 상태를 확인하세요.`;
      dates?.after(p);
    }
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>init().catch(console.error),{once:true});
  else init().catch(console.error);
})();
