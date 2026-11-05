#!/usr/bin/env python3
"""V13 Stage 5: KOSPI 125-day distance, VKOSPI, KOSPI200 plain-option volume PCR.

KRX official approved APIs. Zero guessed data. JSON is published only after
validation. `KRX_API_KEY` stays in GitHub Actions Secrets, never in output.
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
INDEX_HISTORY = DATA / 'kospi_index_history.json'
LATEST = DATA / 'stage5_latest.json'
STAGE5_HISTORY = DATA / 'stage5_history.json'
KRX_LATEST = DATA / 'krx_latest.json'
KEY = os.environ.get('KRX_API_KEY', '').strip()
ENDPOINTS = {'kospi': 'idx/kospi_dd_trd', 'volatility': 'idx/drvprod_dd_trd',
             'options': 'drv/opt_bydd_trd'}
KST = dt.timezone(dt.timedelta(hours=9))


def num(value):
    raw = str(value if value is not None else '').strip().replace(',', '').replace('−','-')
    if not raw or raw in ('-', '.'):
        return None
    try:
        x = float(raw)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def norm(value):
    return ''.join(str(value or '').split()).upper()


def request(which, day):
    url = 'https://data-dbg.krx.co.kr/svc/apis/' + ENDPOINTS[which] + '?' + urllib.parse.urlencode({'basDd': day})
    req = urllib.request.Request(url, headers={
        'AUTH_KEY': KEY, 'Accept': 'application/json', 'User-Agent': 'V13-Official-KRX/1.0'})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                obj = json.load(response)
            rows = obj.get('OutBlock_1')
            if not isinstance(rows, list):
                raise RuntimeError(f'{which}: invalid or unauthorized response: {str(obj)[:180]}')
            if rows and any(str(row.get('BAS_DD')) != day for row in rows):
                raise RuntimeError(f'{which}: mismatched BAS_DD for {day}')
            return rows
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'{which} request error {day}: {last_error}')


def exact_index(rows, name):
    matches = [r for r in rows if norm(r.get('IDX_NM')) == norm(name)]
    if len(matches) != 1:
        candidates = [str(r.get('IDX_NM')) for r in rows if ('코스피' in str(r.get('IDX_NM')) or 'KOSPI' in str(r.get('IDX_NM')).upper())]
        raise RuntimeError(f'Index {name}: expected exactly one, got {len(matches)}; available examples: {candidates[:12]}')
    close = num(matches[0].get('CLSPRC_IDX'))
    if close is None or close <= 0:
        raise RuntimeError(f'Index {name}: invalid close')
    return close


def options_pcr(rows):
    """Ordinary KOSPI200 options only; exclude mini, weekly and individual options."""
    seen = set()
    volume = {'CALL': 0, 'PUT': 0}
    contracts = {'CALL': 0, 'PUT': 0}
    for row in rows:
        if norm(row.get('PROD_NM')) != '코스피200옵션':
            continue
        right = str(row.get('RGHT_TP_NM') or '').upper().strip()
        if right not in volume:
            raise RuntimeError(f'Unexpected option right {right!r}')
        code = str(row.get('ISU_CD') or '').strip()
        name = str(row.get('ISU_NM') or '').strip()
        if not name:
            raise RuntimeError('Missing option contract name')
        identity = (right, code, name)
        if identity in seen:
            raise RuntimeError(f'Duplicate option record: {identity!r}')
        seen.add(identity)
        v = num(row.get('ACC_TRDVOL'))
        if v is None or v < 0 or not v.is_integer():
            raise RuntimeError(f'Invalid option volume for {code}')
        volume[right] += int(v)
        contracts[right] += 1
    if not all(contracts.values()) or not all(volume.values()):
        names = sorted(set(str(row.get('PROD_NM')) for row in rows))
        raise RuntimeError(f'No nonzero KOSPI200 standard options CALL and PUT. Products: {names[:18]}')
    return {'pcr_volume': round(volume['PUT']/volume['CALL'], 6),
            'put_volume': volume['PUT'], 'call_volume': volume['CALL'],
            'put_contracts': contracts['PUT'], 'call_contracts': contracts['CALL']}


def load_history():
    if not INDEX_HISTORY.exists():
        return {}
    obj = json.loads(INDEX_HISTORY.read_text(encoding='utf-8'))
    if not isinstance(obj, list):
        raise RuntimeError('KOSPI history must be a JSON list')
    out = {}
    for row in obj:
        if not isinstance(row, dict):
            raise RuntimeError('Bad KOSPI history record')
        day = str(row.get('date', ''))
        close = num(row.get('close'))
        if len(day) != 8 or not day.isdigit() or close is None or close <= 0:
            raise RuntimeError(f'Invalid KOSPI history item: {row}')
        out[day] = close
    return out


def target_date():
    if not KRX_LATEST.exists():
        raise RuntimeError('Missing data/krx_latest.json. Run existing stock market refresh first.')
    day = str(json.loads(KRX_LATEST.read_text(encoding='utf-8')).get('date', ''))
    if len(day) != 8 or not day.isdigit():
        raise RuntimeError('KRX latest date invalid')
    d = dt.datetime.strptime(day, '%Y%m%d').date()
    if (dt.datetime.now(KST).date()-d).days > 7:
        raise RuntimeError(f'KRX latest too old: {day}')
    return d


def fill_index_history(history, target):
    """Bootstrap ~125 valid index closes. Subsequent runs request only missing weekdays."""
    last = max(history) if history else None
    if last and last > target.strftime('%Y%m%d'):
        raise RuntimeError('Stored index date later than target')
    missing = []
    if not history or len([d for d in history if d <= target.strftime('%Y%m%d')]) < 125:
        # Bounded bootstrap, descending from target: ~125 valid trading days,
        # ~175 weekdays maximum to allow Korean public holidays.
        for offset in range(0, 275):
            d = target - dt.timedelta(days=offset)
            if d.weekday() < 5:
                missing.append(d)
                if len(missing) >= 190:
                    break
        if last:
            missing = [d for d in missing if d.strftime('%Y%m%d') not in history]
    else:
        d = dt.datetime.strptime(last, '%Y%m%d').date() + dt.timedelta(days=1)
        while d <= target:
            if d.weekday() < 5:
                missing.append(d)
            d += dt.timedelta(days=1)
    print(f'KOSPI index requests planned: {len(missing)}', flush=True)
    ds_target = target.strftime('%Y%m%d')
    initial_bootstrap = not last or len([d for d in history if d <= target.strftime('%Y%m%d')]) < 125
    for n, day in enumerate(missing, 1):
        if initial_bootstrap and len([d for d in history if d <= target.strftime('%Y%m%d')]) >= 125 and ds_target in history:
            break
        daystr = day.strftime('%Y%m%d')
        rows = request('kospi', daystr)
        if not rows:
            continue  # official empty day = market holiday/no publication
        history[daystr] = exact_index(rows, '코스피')
        if n % 25 == 0:
            print(f'KOSPI historical fetch {n}/{len(missing)}, valid={len(history)}', flush=True)
    return history


def main():
    if not KEY:
        raise RuntimeError('KRX_API_KEY missing from workflow secret')
    target = target_date()
    ds = target.strftime('%Y%m%d')
    history = fill_index_history(load_history(), target)
    sorted_history = sorted((d,v) for d,v in history.items() if d<=ds)
    if len(sorted_history) < 125 or sorted_history[-1][0] != ds:
        raise RuntimeError(f'Need 125 actual KOSPI sessions ending {ds}; have {len(sorted_history)}, last {sorted_history[-1][0] if sorted_history else "none"}')
    latest_125 = sorted_history[-125:]
    # Require 125 actual exchange days, not 125 calendar days.
    sma = sum(v for _,v in latest_125)/125
    close = latest_125[-1][1]
    momentum_pct = round((close/sma-1)*100, 4)
    vkospi = exact_index(request('volatility', ds), '코스피 200 변동성지수')
    opt = options_pcr(request('options', ds))
    record = {
        'date': ds, 'source': 'KRX OPEN API', 'kospi_close': round(close, 4),
        'kospi_sma125': round(sma, 4), 'kospi_sma125_distance_pct': momentum_pct,
        'kospi_valid_sessions': 125, 'vkospi': round(vkospi, 4),
        'vkospi_index_name': '코스피 200 변동성지수',
        'kospi200_pcr_volume': opt['pcr_volume'],
        'put_volume': opt['put_volume'], 'call_volume': opt['call_volume'],
        'put_contracts': opt['put_contracts'], 'call_contracts': opt['call_contracts'],
        'options_product': '코스피200 옵션 (일반 옵션만, 미니/위클리 제외)',
        'signal_status': 'not_calculated',
        'notice': 'These are raw Stage 5 indicators, NOT a completed V13 BUY/SELL score.'
    }
    DATA.mkdir(parents=True, exist_ok=True)
    # Strict validation done: write to temp then replace each target.
    def publish(path, obj):
        tmp = path.with_suffix(path.suffix+'.tmp')
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        tmp.replace(path)
    publish(INDEX_HISTORY, [{'date':d,'close':round(v,4)} for d,v in sorted(history.items())[-350:]])
    old = json.loads(STAGE5_HISTORY.read_text(encoding='utf-8')) if STAGE5_HISTORY.exists() else []
    if not isinstance(old, list):
        raise RuntimeError('stage5_history.json is not a list')
    bydate = {row['date']: row for row in old if isinstance(row,dict) and 'date' in row}
    bydate[ds] = {k:record[k] for k in ('date','kospi_close','kospi_sma125_distance_pct','vkospi','kospi200_pcr_volume')}
    publish(STAGE5_HISTORY, [bydate[d] for d in sorted(bydate)[-500:]])
    publish(LATEST, record)
    print('STAGE5 VERIFIED', ds, 'KOSPI', close, 'SMA125', round(sma,3),
          'VKOSPI', vkospi, 'PCR', opt['pcr_volume'])

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STAGE5 ERROR:', exc, file=sys.stderr)
        sys.exit(1)
