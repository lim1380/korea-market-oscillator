#!/usr/bin/env python3
"""Stage 6: KOSPI 20-session price return minus KODEX 국고채3년 ETF
20-session price return. Test-only until the ETF API authorization and
output values are verified; no trading signal is computed. API key never printed.
"""
import datetime as dt
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
KOSPI_HISTORY = DATA / 'kospi_index_history.json'
KRX_LATEST = DATA / 'krx_latest.json'
STAGE6_LATEST = DATA / 'stage6_latest.json'
STAGE6_HISTORY = DATA / 'stage6_history.json'
KEY = os.environ.get('KRX_API_KEY', '').strip()
ETF_API = 'https://data-dbg.krx.co.kr/svc/apis/etp/etf_bydd_trd'
ETF_CODE = '114260'
ETF_NAME = 'KODEX 국고채3년'


def number(value):
    s = str(value if value is not None else '').strip().replace(',', '')
    try:
        x = float(s)
    except ValueError:
        return None
    return x if math.isfinite(x) and x > 0 else None


def index_records():
    if not KOSPI_HISTORY.exists() or not KRX_LATEST.exists():
        raise RuntimeError('First complete Stage 5 and KRX daily refresh; required JSON missing.')
    history = json.loads(KOSPI_HISTORY.read_text(encoding='utf-8'))
    target = str(json.loads(KRX_LATEST.read_text(encoding='utf-8')).get('date', ''))
    if len(target) != 8 or not target.isdigit() or not isinstance(history, list):
        raise RuntimeError('Invalid target date or KOSPI index history')
    dates = {}
    for row in history:
        if not isinstance(row, dict):
            raise RuntimeError('Bad KOSPI history row')
        date = str(row.get('date', ''))
        close = number(row.get('close'))
        if len(date) != 8 or not date.isdigit() or close is None or date in dates:
            raise RuntimeError(f'Invalid or duplicate KOSPI history date: {date}')
        dates[date] = close
    if target not in dates:
        raise RuntimeError(f'KOSPI index history does not contain latest KRX date {target}')
    ordered = [(d, dates[d]) for d in sorted(dates) if d <= target]
    if len(ordered) < 21:
        raise RuntimeError('Need 21 actual KOSPI sessions for a 20-session return')
    latest_date = dt.datetime.strptime(target, '%Y%m%d').date()
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    if (today - latest_date).days > 7 or latest_date > today:
        raise RuntimeError(f'KOSPI latest date outside allowed freshness: {target}')
    return ordered[-21:]


def etf_close_on(day):
    req = urllib.request.Request(ETF_API + '?' + urllib.parse.urlencode({'basDd': day}), headers={
        'AUTH_KEY': KEY, 'Accept': 'application/json', 'User-Agent': 'V13-Stage6-ETF/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                data = json.load(response)
            rows = data.get('OutBlock_1')
            if not isinstance(rows, list):
                raise RuntimeError(f'ETF API did not return OutBlock_1 for {day}: permission or schema error')
            if not rows:
                raise RuntimeError(f'ETF API empty response on KOSPI trading day {day}')
            candidates = []
            for row in rows:
                code = str(row.get('ISU_CD') or '').strip()
                name = ''.join(str(row.get('ISU_NM') or '').upper().split())
                expected = ''.join(ETF_NAME.upper().split())
                # The KRX ETF code can be either a 6-digit ticker or a 12-digit ISIN.
                code_matches = code == ETF_CODE or code == 'KR7' + ETF_CODE + '003' # never rely on this alone
                name_matches = name == expected
                if name_matches and (code_matches or ETF_CODE in code):
                    candidates.append(row)
            if len(candidates) != 1:
                sample = [str(r.get('ISU_NM')) for r in rows if ETF_CODE in str(r.get('ISU_CD') or '') or '국고채3년' in str(r.get('ISU_NM') or '')][:8]
                raise RuntimeError(f'{day}: ETF match expected exactly 1, got {len(candidates)}; candidates={sample}')
            r = candidates[0]
            if str(r.get('BAS_DD')) != day:
                raise RuntimeError(f'ETF date mismatch on {day}')
            close = number(r.get('TDD_CLSPRC'))
            if close is None:
                raise RuntimeError(f'ETF invalid close on {day}')
            return close
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError('Unreachable ETF request state')


def calculate(index, bond_prices):
    if len(index) != 21 or len(bond_prices) != 21:
        raise ValueError('Need exactly 21 aligned trading dates')
    a, b = index[0], index[-1]
    er = (b[1]/a[1]-1)*100
    br = (bond_prices[-1]/bond_prices[0]-1)*100
    return {
        'date': b[0], 'start_date': a[0], 'window': '20 KOSPI sessions (21 aligned closing prices)',
        'equity': 'KOSPI price index', 'equity_return_20d_pct': round(er, 4),
        'bond': ETF_NAME, 'bond_code': ETF_CODE, 'bond_return_20d_pct': round(br, 4),
        'equity_minus_bond_20d_pctpt': round(er-br, 4),
        'start_kospi': a[1], 'end_kospi': b[1],
        'start_bond_etf': bond_prices[0], 'end_bond_etf': bond_prices[-1],
        'source': 'KRX OPEN API daily closes', 'signal_status': 'not_calculated',
        'notice': 'Price-only comparison, not total return. ETF distributions, corporate actions and spread/slippage are not adjusted; not a BUY/SELL signal.'
    }


def main():
    if not KEY:
        raise RuntimeError('KRX_API_KEY missing from GitHub Actions Secrets')
    idx = index_records()
    values = []
    for n, (day, _) in enumerate(idx, 1):
        values.append(etf_close_on(day))
        if n % 7 == 0:
            print(f'ETF verified {n}/21 trading sessions', flush=True)
    result = calculate(idx, values)
    DATA.mkdir(parents=True, exist_ok=True)
    STAGE6_LATEST.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    history = json.loads(STAGE6_HISTORY.read_text(encoding='utf8')) if STAGE6_HISTORY.exists() else []
    if not isinstance(history, list):
        raise RuntimeError('Stage6 history must be a JSON list')
    bydate = {r['date']: r for r in history if isinstance(r, dict) and 'date' in r}
    bydate[result['date']] = {k:result[k] for k in ('date', 'equity_return_20d_pct', 'bond_return_20d_pct', 'equity_minus_bond_20d_pctpt')}
    STAGE6_HISTORY.write_text(json.dumps([bydate[k] for k in sorted(bydate)[-500:]],ensure_ascii=False,indent=2)+'\n', encoding='utf8')
    print('STAGE6 VERIFIED', result['date'], 'equity', result['equity_return_20d_pct'], 'bond',result['bond_return_20d_pct'],'spread',result['equity_minus_bond_20d_pctpt'])


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STAGE6 ERROR:', exc, file=sys.stderr)
        sys.exit(1)
