#!/usr/bin/env python3
"""Read-only daily ETF quote snapshot. Public research data; no broker access."""
import datetime as dt
import json
import pathlib
from scripts.paper_trade import fetch_close, SUPPORTED

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"data"/"daily-etf-quotes.json"

def build(now=None, fetcher=fetch_close):
    now=now or dt.datetime.now(dt.timezone.utc)
    prices={}
    errors={}
    for ticker in sorted(SUPPORTED):
        try:
            day,price=fetcher(ticker)
            if day>now.date() or price<=0:raise ValueError("Unplausible price/date")
            age=(now.date()-day).days
            prices[ticker]={"date":day.isoformat(),"close_usd":round(price,5),
                            "age_calendar_days":age,"status":"RECENT" if age<=3 else "STALE"}
        except Exception as exc:
            # Never persist credentials or raw external responses.
            errors[ticker]=type(exc).__name__
    if errors: overall="PARTIAL"
    elif any(x["status"]=="STALE" for x in prices.values()):overall="STALE"
    else:overall="RECENT"
    return {"version":1,"generated_at":now.isoformat(),"source":"Yahoo Finance unofficial daily close",
            "currency":"USD","quotes":prices,"errors":errors,"status":overall,
            "notice":"Delayed daily close, not real-time and not a broker execution price."}

def main():
    report=build()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(OUTPUT)
    print("Quote snapshot:",report["status"],len(report["quotes"]),"quotes",len(report["errors"]),"errors")
if __name__=="__main__":main()
