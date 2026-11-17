#!/usr/bin/env python3
"""Research-only seasonal ETF scanner. Never places live or simulated broker orders.

Uses Yahoo Finance unofficial adjusted daily close series. Discovers entry
calendar dates and fixed holding periods solely on a training sample; assesses
holdout years independently. Costs are illustrative. Published output must
never be interpreted as a recommendation or predictive return guarantee.
"""
import datetime as dt
import json
import math
import os
import pathlib
import statistics
import time
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DEST=ROOT/"data"/"seasonal-signals.json"
SYMBOLS={"VT":"Weltaktien","QQQ":"Nasdaq-100","SMH":"Halbleiter","MTUM":"Momentum-Faktor","BND":"US-Anleihen"}
DURATIONS=(14,21,28,42,56)
ROUNDTRIP_COST=0.004
MIN_TRAIN=6
MIN_TEST=3

def load(ticker):
    err=None
    for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        url=f"https://{host}/v8/finance/chart/{urllib.parse.quote(ticker)}?period1=1325376000&period2={int(time.time())}&interval=1d&events=div%2Csplits"
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
            with urllib.request.urlopen(request,timeout=35) as f: obj=json.load(f)
            result=obj["chart"]["result"][0]
            values=result["indicators"]["adjclose"][0]["adjclose"]
            stamps=result["timestamp"]
            data={}
            for stamp,value in zip(stamps,values):
                if isinstance(value,(float,int)) and math.isfinite(value) and value>0:
                    date=dt.datetime.fromtimestamp(stamp,dt.timezone.utc).date()
                    data[date]=float(value)
            if len(data)<1600: raise ValueError("Insufficient daily data")
            return data
        except Exception as e:
            err=e
            time.sleep(1)
    raise RuntimeError(f"Unable to fetch {ticker}: {err}")

def annual_return(series,year,start_day,duration):
    entry_target=dt.date(year,1,1)+dt.timedelta(days=start_day)
    exit_target=entry_target+dt.timedelta(days=duration)
    if exit_target.year!=year: return None
    days=sorted(k for k in series if entry_target<=k<=exit_target)
    if len(days)<8 or (days[0]-entry_target).days>5 or (exit_target-days[-1]).days>5:
        return None
    return series[days[-1]]/series[days[0]]-1-ROUNDTRIP_COST

def stats(numbers):
    if not numbers:return None
    return {"years":len(numbers),"mean_net_return":round(statistics.mean(numbers),6),
            "median_net_return":round(statistics.median(numbers),6),
            "win_rate":round(sum(v>0 for v in numbers)/len(numbers),4),
            "worst_net_return":round(min(numbers),6)}

def main():
    today=dt.datetime.now(dt.timezone.utc).date()
    series={s:load(s) for s in SYMBOLS}
    completed_years=range(2015,today.year)
    split=min(2022,today.year-4)
    train_years=[y for y in completed_years if y<split]
    test_years=[y for y in completed_years if y>=split]
    if len(train_years)<MIN_TRAIN or len(test_years)<MIN_TEST:
        raise RuntimeError("Insufficient completed years for independent testing")
    shortlisted=[]
    for ticker,prices in series.items():
        ranked=[]
        for day in range(0,300,7):
            for duration in DURATIONS:
                train=[annual_return(prices,y,day,duration) for y in train_years]
                train=[v for v in train if v is not None]
                if len(train)<MIN_TRAIN:continue
                measures=stats(train)
                score=measures["mean_net_return"]-.25*max(0,-measures["worst_net_return"])
                ranked.append((score,day,duration,measures))
        ranked.sort(reverse=True)
        # One selected candidate per ETF, selected using training years alone.
        if not ranked:continue
        _,day,duration,train_stats=ranked[0]
        test=[annual_return(prices,y,day,duration) for y in test_years]
        test=[v for v in test if v is not None]
        if len(test)<MIN_TEST:continue
        validation=stats(test)
        entry=(dt.date(2025,1,1)+dt.timedelta(days=day)).strftime("%m-%d")
        shortlisted.append({"ticker":ticker,"description":SYMBOLS[ticker],
             "entry_month_day":entry,"holding_calendar_days":duration,
             "training":train_stats,"validation":validation,
             "passes_validation":validation["mean_net_return"]>0 and validation["win_rate"]>=.6
             and validation["worst_net_return"]>-.15})
    shortlisted.sort(key=lambda p:p["validation"]["mean_net_return"],reverse=True)
    signals=[]
    for item in shortlisted:
        if not item["passes_validation"]:continue
        md=item["entry_month_day"]
        for year in (today.year,today.year+1):
            entry=dt.date.fromisoformat(f"{year}-{md}")
            end=entry+dt.timedelta(days=item["holding_calendar_days"])
            if entry-dt.timedelta(days=7)<=today<=end:
                stage="upcoming" if today<entry else "holding_window"
                signals.append({"ticker":item["ticker"],"entry_date":entry.isoformat(),
                 "planned_exit_date":end.isoformat(),"stage":stage,
                 "action":"RESEARCH_ONLY_NO_ORDER"})
    result={"version":4,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "currency":"USD","source":"Yahoo Finance unofficial adjusted daily close",
      "training_years":train_years,"holdout_years":test_years,
      "roundtrip_cost_assumption":ROUNDTRIP_COST,
      "search":"7-day entry grid; 14/21/28/42/56-day holds; one best trained candidate per ETF",
      "disclaimer":"RESEARCH ONLY. No orders. Multiple testing, index membership, price and currency risks apply. Signals not verified trading instructions.",
      "candidates":shortlisted,"seasonal_windows":signals}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    tmp=DEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(tmp,DEST)
    print("Scanned",len(shortlisted),"ETF seasonality candidates;",len(signals),"calendar observation windows")

if __name__=="__main__":
    main()
