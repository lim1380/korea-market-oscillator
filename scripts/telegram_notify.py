#!/usr/bin/env python3
"""Send a verified V13 daily report using GitHub Actions Secrets.
No token, chat id or API key is written to public files or logs.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
KST = dt.timezone(dt.timedelta(hours=9))


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def fmt_date(value):
    value = str(value or '')
    return f'{value[:4]}-{value[4:6]}-{value[6:8]}' if len(value) == 8 and value.isdigit() else '확인 필요'


def num(value, unit='', precision=2):
    try:
        return f'{float(value):,.{precision}f}{unit}'
    except (TypeError, ValueError):
        return '확인 불가'


def build_message():
    krx = load('krx_latest.json')
    breadth = load('breadth_latest.json')
    stage5 = load('stage5_latest.json')
    stage6 = load('stage6_latest.json')
    model = load('v13_backtested_latest.json')

    dates = {
        'KRX': str(krx.get('date', '')),
        '시장 폭': str(breadth.get('date', '')),
        '변동성': str(stage5.get('date', '')),
        '주식·국채': str(stage6.get('date', '')),
        '전략': str(model.get('market_data_date', '')),
    }
    latest_date = dates['KRX']
    if len(latest_date) != 8 or not latest_date.isdigit():
        raise ValueError('KRX 기준일이 비어 있습니다.')
    mismatches = [k for k, v in dates.items() if v != latest_date]
    if mismatches:
        raise ValueError('기준일 불일치: ' + ', '.join(f'{k}={v}' for k, v in dates.items()))

    today = dt.datetime.now(KST).date()
    session = dt.datetime.strptime(latest_date, '%Y%m%d').date()
    if (today - session).days > 4 or session > today:
        raise ValueError(f'최신 시장 데이터 기준일 검증 실패: {latest_date}')

    exposure = model.get('certified_original_target_exposure_pct')
    certified = model.get('forward_status') == 'CERTIFIED_ORIGINAL_POSITION'
    if certified and isinstance(exposure, (float, int)):
        equity = round(float(exposure))
        position = f'주식 {equity}% / 현금 {100-equity}%'
    else:
        position = '확정 불가 (원본 점수 일부 부족)'

    return '\n'.join([
        '📊 K-MARKET OSCILLATOR V13',
        f'📅 시장 기준일: {fmt_date(latest_date)}',
        f'⏰ 발송 시각: {dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")} KST',
        '',
        f'🎯 전략 목표 비중: {position}',
        f'🔎 전략 상태: {model.get("latest_action_certified") or "판정 보류"}',
        f'⚠️ 매도 위험점수(범위): {num(model.get("last_review_risk_lower"), precision=1)} ~ {num(model.get("last_review_risk_upper"), precision=1)}',
        f'🗓 마지막 전략 평가일: {fmt_date(model.get("last_review_date"))}',
        '',
        f'📈 상승 거래대금 비율: {num(krx.get("advancing_value_ratio_pct"), "%")}',
        f'📊 20일선 상회 종목: {num(breadth.get("breadth", {}).get("20", {}).get("above_pct"), "%")}',
        f'📉 VKOSPI: {num(stage5.get("vkospi"))}',
        '',
        '📱 전체 대시보드:',
        'https://lim1380.github.io/korea-market-oscillator/',
        '',
        '※ 매매 권유 아님. 백테스트 원본 이후 일부 점수는 미산출 상태입니다.',
    ])


def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id:
        raise RuntimeError('텔레그램 Secret 설정이 없습니다.')
    message = build_message()
    body = urllib.parse.urlencode({'chat_id': chat_id, 'text': message, 'disable_web_page_preview': 'true'}).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body, method='POST')
    with urllib.request.urlopen(req, timeout=20) as resp:
        response = json.load(resp)
    if not response.get('ok'):
        raise RuntimeError('텔레그램 발송에 실패했습니다.')
    print('Telegram V13 report delivered; checked market date:', load('krx_latest.json')['date'])


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        print('Telegram notification failed:', type(err).__name__, file=sys.stderr)
        sys.exit(1)
