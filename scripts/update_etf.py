#!/usr/bin/env python3
"""Download validated monthly adjusted ETF prices converted to EUR.

Data source: Yahoo Finance unofficial chart endpoint. Failure never overwrites
previous valid data. This is research data, not a broker quote feed.
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
OUTPUT = ROOT / "data" / "etf-prices.json"
ETFS = {
    "WORLD": "VT",
    "TECH": "QQQ",
    "BONDS": "BND",
    "SEMI": "SMH",
    "FACTOR": "MTUM",
}
FOREX = "EURUSD=X"

def fetch_monthly(ticker, allow_close=False):
    failures = []
    for hostname in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        for attempt in range(3):
            url = (
                f"https://{hostname}/v8/finance/chart/{urllib.parse.quote(ticker)}"
                f"?period1=1356998400&period2={int(time.time())}&interval=1d"
                "&events=div%2Csplits"
            )
            try:
                request = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ETF-Strategy-Lab/3.0)",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(request, timeout=35) as response:
                    payload = json.load(response)
                quote = payload["chart"]["result"][0]
                stamps = quote["timestamp"]
                indicators = quote["indicators"]
                adjusted = indicators.get("adjclose") or []
                prices = adjusted[0].get("adjclose") if adjusted else None
                if not prices and allow_close:
                    prices = indicators["quote"][0].get("close")
                if not prices or len(prices) != len(stamps):
                    raise ValueError("Missing or mismatched adjusted prices")
                monthly = {}
                for stamp, value in zip(stamps, prices):
                    if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                        continue
                    # US market closes occur before midnight UTC.
                    month = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).strftime("%Y-%m")
                    monthly[month] = float(value)
                if len(monthly) < 60:
                    raise ValueError(f"Only {len(monthly)} monthly observations")
                return monthly
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError,
                    IndexError, TypeError, OSError) as error:
                failures.append(f"{hostname} attempt {attempt + 1}: {error}")
                time.sleep(1 + attempt)
    raise RuntimeError(f"Cannot load {ticker}: " + " | ".join(failures))

def main():
    usd_prices = {name: fetch_monthly(ticker) for name, ticker in ETFS.items()}
    eurusd = fetch_monthly(FOREX, allow_close=True)
    shared = sorted(set.intersection(
        *(set(series) for series in [*usd_prices.values(), eurusd])
    ))
    current_month = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    shared = [month for month in shared if month < current_month]
    if len(shared) < 60:
        raise RuntimeError(f"Only {len(shared)} completed shared months")

    for previous, current in zip(shared, shared[1:]):
        py, pm = map(int, previous.split("-"))
        cy, cm = map(int, current.split("-"))
        if (cy - py) * 12 + cm - pm != 1:
            raise RuntimeError(f"Data gap: {previous} to {current}")

    rows = []
    for month in shared:
        fx = eurusd[month]
        if not 0.5 <= fx <= 2.0:
            raise RuntimeError(f"Unreasonable EURUSD exchange rate in {month}: {fx}")
        # Yahoo EURUSD=X = USD per EUR, so divide USD ETF price by EURUSD.
        converted = {name: round(series[month] / fx, 8)
                     for name, series in usd_prices.items()}
        rows.append({"date": month, **converted})

    output = {
        "version": 3,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "currency": "EUR",
        "source": "Yahoo Finance unofficial chart API; ETF adjusted closes; EURUSD=X spot closes",
        "price_frequency": "last available observation of each completed calendar month",
        "symbols": ETFS,
        "fx_symbol": FOREX,
        "fx_conversion": "ETF USD adjusted close divided by EURUSD=X monthly spot rate",
        "rows": rows,
        "disclaimer": "Historical research proxy only. USD and EUR closes may differ in timing.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, OUTPUT)
    print(f"Validated EUR ETF data: {len(rows)} completed months, {shared[0]} through {shared[-1]}")

if __name__ == "__main__":
    main()
