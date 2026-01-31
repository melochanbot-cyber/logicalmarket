#!/usr/bin/env python3
"""Fetch market data from Yahoo Finance and write to data/market.json."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

SYMBOLS = [
    'GC=F',      # Gold
    'SI=F',      # Silver
    'CL=F',      # Crude Oil
    '^GSPC',     # S&P 500
    '^IXIC',     # Nasdaq
    '^DJI',      # Dow Jones
    'BTC-USD',   # Bitcoin
    'ETH-USD',   # Ethereum
    'DX-Y.NYB',  # USD Index
]

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


def fetch_symbol(sym: str) -> dict:
    """Fetch chart data for a single symbol."""
    url = (
        f'https://query1.finance.yahoo.com/v8/finance/chart/'
        f'{urllib.request.quote(sym, safe="")}?range=5d&interval=15m'
    )
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    result = data['chart']['result'][0]
    meta = result['meta']
    closes_raw = result['indicators']['quote'][0].get('close') or []
    closes = [c for c in closes_raw if c is not None]

    price = meta.get('regularMarketPrice') or (closes[-1] if closes else None)
    prev_close = meta.get('chartPreviousClose') or meta.get('previousClose')

    daily_change = (price - prev_close) if price and prev_close else 0
    daily_change_pct = (daily_change / prev_close * 100) if prev_close else 0

    first_close = closes[0] if closes else prev_close
    week_change = (price - first_close) if price and first_close else 0
    week_change_pct = (week_change / first_close * 100) if first_close else 0

    return {
        'price': round(price, 4) if price else None,
        'prevClose': round(prev_close, 4) if prev_close else None,
        'dailyChange': round(daily_change, 4),
        'dailyChangePct': round(daily_change_pct, 2),
        'weekChangePct': round(week_change_pct, 2),
        'sparkData': [round(c, 2) for c in closes[-48:]],
        'high': round(max(closes), 4) if closes else None,
        'low': round(min(closes), 4) if closes else None,
        'marketState': meta.get('marketState', 'CLOSED'),
        'volume': meta.get('regularMarketVolume', 0),
        'currency': meta.get('currency', 'USD'),
    }


def main():
    assets = {}
    success = 0

    for sym in SYMBOLS:
        try:
            assets[sym] = fetch_symbol(sym)
            success += 1
            print(f'  ✓ {sym}: ${assets[sym]["price"]}')
        except Exception as e:
            print(f'  ✗ {sym}: {e}', file=sys.stderr)
            assets[sym] = {'error': True}

    output = {
        'updatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'assets': assets,
    }

    # Ensure data/ directory exists
    os.makedirs('data', exist_ok=True)

    with open('data/market.json', 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f'\nUpdated {success}/{len(SYMBOLS)} assets')

    if success == 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
