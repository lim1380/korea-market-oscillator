#!/usr/bin/env python3
"""Safely check KRX service permissions without printing the API key or affecting daily refresh."""
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get('KRX_API_KEY', '').strip()
SERVICES = {
    'KOSPI 시리즈 일별시세정보': 'idx/kospi_dd_trd',
    '파생상품지수 시세정보 (VKOSPI 확인용)': 'idx/drvprod_dd_trd',
    '옵션 일별매매정보 (PCR 확인용)': 'drv/opt_bydd_trd',
}

def query(service, day):
    url = 'https://data-dbg.krx.co.kr/svc/apis/' + service + '?' + urllib.parse.urlencode({'basDd': day})
    req = urllib.request.Request(url, headers={'AUTH_KEY': KEY, 'Accept': 'application/json', 'User-Agent': 'V13-API-Check/1.0'})
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.load(resp)
    rows = result.get('OutBlock_1')
    if not isinstance(rows, list):
        raise ValueError('응답 필드 오류 또는 API 서비스 미승인')
    return rows

def main():
    if not KEY:
        raise SystemExit('KRX_API_KEY GitHub Secret을 찾을 수 없습니다.')
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    # Probe several recent weekdays in case of weekends, holidays or delayed feeds.
    days = [(today - dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(1, 9) if (today - dt.timedelta(days=i)).weekday() < 5]
    failed = []
    for label, path in SERVICES.items():
        tested = False
        for day in days:
            try:
                rows = query(path, day)
                if not rows:
                    continue
                fields = sorted(rows[0].keys())
                print(f'[OK] {label} | {day} | {len(rows)}건')
                print('     응답 필드:', ', '.join(fields))
                if path == 'idx/drvprod_dd_trd':
                    names = sorted({str(x.get('IDX_NM', '')).strip() for x in rows})
                    print('     지수명 예시:', ', '.join(names[:35]))
                    print('     VKOSPI 명칭 후보:', ', '.join(x for x in names if '변동성' in x or 'VKOSPI' in x.upper()) or '(결과에 없음 — 별도 확인 필요)')
                if path == 'drv/opt_bydd_trd':
                    names = sorted({str(x.get('PROD_NM', '')).strip() for x in rows})
                    rights = sorted({str(x.get('RGHT_TP_NM', '')).strip() for x in rows})
                    print('     상품명 예시:', ', '.join(names[:25]))
                    print('     콜풋 구분:', ', '.join(rights))
                tested = True
                break
            except urllib.error.HTTPError as exc:
                print(f'[ERROR] {label} | HTTP {exc.code} — 승인/인증/요청 방식 확인 필요')
                tested = True
                failed.append(label)
                break
            except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
                print(f'[ERROR] {label} | {type(exc).__name__}: {str(exc)[:120]}')
                tested = True
                failed.append(label)
                break
        if not tested:
            print(f'[NO DATA] {label} | 최근 영업일 응답이 비어 있습니다')
            failed.append(label)
    if failed:
        print('\n추가 확인 필요:', ', '.join(failed))
        raise SystemExit(1)
    print('\n세 종류의 KRX 데이터 API 응답 확인 완료. 계산식 및 종목/지수명 검증은 다음 단계입니다.')

if __name__ == '__main__':
    main()
