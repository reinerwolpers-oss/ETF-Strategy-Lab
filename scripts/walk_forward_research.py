#!/usr/bin/env python3
"""Research-only expanding-window seasonality validation.

Each test year reselects a fixed window using only prior COMPLETED years.
No dependence on the published, holdout-gated candidate selection. No brokers,
no trade simulation or changes to forward paper-portfolio data.
"""
import datetime as dt
import json
import pathlib
import statistics
from seasonal_scan import ROOT, SYMBOLS, DURATIONS, ROUNDTRIP_COST, MIN_TRAIN, load, annual_return

OUTPUT=ROOT/"data"/"walk-forward-research.json"
FIRST_TRAIN_YEAR=2015
FIRST_TEST_YEAR=2021

def choose_window(prices,training_years):
    ranked=[]
    for day in range(0,300,7):
        for duration in DURATIONS:
            returns=[annual_return(prices,y,day,duration) for y in training_years]
            returns=[r for r in returns if r is not None]
            if len(returns)<MIN_TRAIN:
                continue
            worst=min(returns)
            score=statistics.mean(returns)-.25*max(0,-worst)
            ranked.append((score,day,duration,len(returns)))
    if not ranked:
        return None
    return max(ranked)  # Same training-only selection rule as seasonal_scan.py

def window_details(prices,year,day,duration):
    start=dt.date(year,1,1)+dt.timedelta(days=day)
    end=start+dt.timedelta(days=duration)
    if end.year!=year:
        return None
    days=sorted(d for d in prices if start<=d<=end)
    if len(days)<8 or (days[0]-start).days>5 or (end-days[-1]).days>5:
        return None
    return (days[0],days[-1])

def evaluate(prices,qqq,test_year):
    training_years=list(range(FIRST_TRAIN_YEAR,test_year))
    selection=choose_window(prices,training_years)
    if selection is None:
        return None
    score,day,duration,count=selection
    result=annual_return(prices,test_year,day,duration)
    dates=window_details(prices,test_year,day,duration)
    if result is None or dates is None:
        return None
    entry,exit=dates
    # Matched QQQ benchmark over identical date boundaries and common market closes.
    if entry not in qqq or exit not in qqq:
        return None
    comparison=qqq[exit]/qqq[entry]-1
    return {"test_year":test_year,"training_start":FIRST_TRAIN_YEAR,
      "training_end":test_year-1,"training_samples":count,
      "selected_day_offset":day,"selected_holding_calendar_days":duration,
      "entry_date":entry.isoformat(),"exit_date":exit.isoformat(),
      "net_window_return":round(result,6),
      "qqq_same_window_gross_return":round(comparison,6),
      "excess_vs_qqq_gross":round(result-comparison,6)}

def build(series,final_year):
    if final_year<FIRST_TEST_YEAR:
        raise ValueError("No test years")
    if "QQQ" not in series:
        raise ValueError("QQQ benchmark required")
    groups=[]
    for ticker,prices in sorted(series.items()):
        observations=[]
        for year in range(FIRST_TEST_YEAR,final_year+1):
            item=evaluate(prices,series["QQQ"],year)
            if item is not None:
                observations.append(item)
        groups.append({"ticker":ticker,"description":SYMBOLS.get(ticker,ticker),
          "observations":observations,"observed_test_years":len(observations),
          "mean_net_window_return":round(statistics.mean(r["net_window_return"] for r in observations),6) if observations else None,
          "mean_qqq_gross_same_window":round(statistics.mean(r["qqq_same_window_gross_return"] for r in observations),6) if observations else None,
          "positive_year_fraction":round(sum(r["net_window_return"]>0 for r in observations)/len(observations),4) if observations else None})
    return groups

def main():
    final_year=dt.datetime.now(dt.timezone.utc).year-1
    prices={ticker:load(ticker) for ticker in SYMBOLS}
    rows=build(prices,final_year)
    report={"version":1,"mode":"RESEARCH_ONLY","method":"EXPANDING_WINDOW_RESELECTION",
      "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "first_training_year":FIRST_TRAIN_YEAR,"first_test_year":FIRST_TEST_YEAR,
      "last_completed_test_year":final_year,"roundtrip_cost_assumption":ROUNDTRIP_COST,
      "price_source":"Yahoo Finance unofficial adjusted daily closing prices",
      "limitations":"Each test year uses only earlier calendar years for selection, but this analysis was developed after viewing earlier 2022-2025 results: it is NOT a preregistered, untouched independent test. Each window is one hypothetical trade per year, not a portfolio. Strategy cost is a flat 0.4 percentage point; QQQ benchmark uses gross returns and no execution cost. No stop-loss, position sizing, taxes, FX, intraday fills or dividends/corporate-action execution realism. Returns must not be compounded into a trading-performance claim.",
      "rows":rows}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Research only:",[(x["ticker"],x["observed_test_years"]) for x in rows])

if __name__=="__main__":
    main()
