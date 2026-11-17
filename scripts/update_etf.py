#!/usr/bin/env python3
"""Fetch and validate historical monthly adjusted closes from Yahoo Finance chart endpoints.
Fails closed: never overwrite an existing price file with mock or partial data.
"""
import datetime as dt
import json
import math
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'etf-prices.json'
SYMBOLS = {'WORLD': 'VT', 'TECH': 'QQQ', 'BONDS': 'BND'}


def fetch_monthly(ticker):
    errs = []
    for host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']:
        url = f'https://{host}/v8/finance/chart/{urllib.parse.quote(ticker)}?period1=1104537600&period2={int(time.time())}&interval=1d&events=div%2Csplits'
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ETFStrategyLab/2.0)', 'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=25) as response:
                    obj = json.load(response)
                record = obj['chart']['result'][0]
                timestamps = record['timestamp']
                indicators = record['indicators']
                adj = indicators.get('adjclose') or []
                values = adj[0].get('adjclose') if adj else None
                if not values:
                    raise ValueError('Adjusted close data missing; refuse to use unadjusted prices')
                months = {}
                for stamp, value in zip(timestamps, values):
                    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                        continue
                    # Yahoo daily exchange timestamps are US market timestamps. Convert to New York date.
                    date = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date()
                    months[date.strftime('%Y-%m')] = float(value)
                if len(months) < 24:
                    raise ValueError(f'Only {len(months)} monthly points')
                return months
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError, OSError) as ex:
                errs.append(f'{host} attempt {attempt+1}: {ex}')
                time.sleep(1.5)
    raise RuntimeError(f'{ticker}: quote retrieval failed: ' + ' / '.join(errs))


def main():
    data = {label: fetch_monthly(symbol) for label, symbol in SYMBOLS.items()}
    common = sorted(set.intersection(*(set(s.keys()) for s in data.values())))
    # A still-running month is removed, so all prices represent completed months.
    current = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m')
    common = [m for m in common if m < current]
    if len(common) < 24:
        raise RuntimeError('Insufficient shared history')
    for a, b in zip(common, common[1:]):
        ay, am = map(int, a.split('-'))
        by, bm = map(int, b.split('-'))
        if (by-ay)*12 + (bm-am) != 1:
            raise RuntimeError(f'Gap in shared months: {a} -> {b}')
    rows = [{'date': m, **{label: round(data[label][m], 8) for label in SYMBOLS}} for m in common]
    result = {
        'version': 2,
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'currency': 'USD',
        'source': 'Yahoo Finance unofficial chart API, dividend/split adjusted close',
        'price_frequency': 'monthly: last available trading day, completed months only',
        'symbols': SYMBOLS,
        'rows': rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(temp, OUT)
    print(f'Updated {OUT}: {len(rows)} observations from {common[0]} to {common[-1]}')


if __name__ == '__main__':
    main()
