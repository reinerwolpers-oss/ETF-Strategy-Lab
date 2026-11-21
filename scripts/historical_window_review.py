#!/usr/bin/env python3
"""Read-only historical window diagnostics, separate from paper trading.

Fixed calendar windows come from the published scanner. Holdout years were used
to gate candidates, so these are NOT untouched out-of-sample results.
No orders, no writes to paper-portfolio.json, no live broker connectivity.
"""
import datetime as dt
import json
import pathlib
import statistics
from seasonal_scan import ROOT, load, ROUNDTRIP_COST

DEST=ROOT/"data"/"historical-window-review.json"

def window_observation(prices,year,month_day,duration):
    target=dt.date.fromisoformat(f"{year}-{month_day}")
    end=target+dt.timedelta(days=duration)
    if end.year!=year:
        return None
    dates=sorted(day for day in prices if target<=day<=end)
    if len(dates)<8 or (dates[0]-target).days>5 or (end-dates[-1]).days>5:
        return None
    first,last=dates[0],dates[-1]
    gross=prices[last]/prices[first]-1
    return {"entry_date":first.isoformat(),"exit_date":last.isoformat(),
            "gross_return":round(gross,6),"net_window_return":round(gross-ROUNDTRIP_COST,6)}

def main():
    doc=json.loads((ROOT/"data"/"seasonal-signals.json").read_text(encoding="utf-8"))
    if doc.get("version")!=4 or doc.get("currency")!="USD":
        raise ValueError("Unexpected candidate data")
    # Use only completed calendar years from the published research cohorts.
    years=list(doc["training_years"])+list(doc["holdout_years"])
    if not years or max(years)>=dt.datetime.now(dt.timezone.utc).year:
        raise ValueError("Historical years must be complete")
    accepted=[c for c in doc["candidates"] if c["passes_validation"]]
    prices={ticker:load(ticker) for ticker in sorted({c["ticker"] for c in accepted}|{"QQQ"})}
    rows=[]
    for c in accepted:
        observations=[]
        for year in years:
            result=window_observation(prices[c["ticker"]],year,c["entry_month_day"],int(c["holding_calendar_days"]))
            if result is None:continue
            # The benchmark is QQQ buy-and-hold over precisely the same window.
            qqq=prices["QQQ"]
            a=dt.date.fromisoformat(result["entry_date"])
            b=dt.date.fromisoformat(result["exit_date"])
            if a not in qqq or b not in qqq: continue
            benchmark=qqq[b]/qqq[a]-1
            observations.append({"year":year,"cohort":"TRAINING" if year in doc["training_years"] else "HOLDOUT_USED_FOR_GATING",
              **result,"qqq_same_window_return":round(benchmark,6),
              "excess_vs_qqq":round(result["net_window_return"]-benchmark,6)})
        if not observations:continue
        held=[x for x in observations if x["cohort"]=="HOLDOUT_USED_FOR_GATING"]
        rows.append({"ticker":c["ticker"],"description":c["description"],"entry_month_day":c["entry_month_day"],
          "holding_calendar_days":c["holding_calendar_days"],"observations":observations,
          "holdout_sample_count":len(held),
          "holdout_mean_net_return":round(statistics.mean(x["net_window_return"] for x in held),6) if held else None,
          "holdout_mean_qqq_same_window":round(statistics.mean(x["qqq_same_window_return"] for x in held),6) if held else None})
    result={"version":1,"mode":"RESEARCH_ONLY","generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source":"Yahoo Finance unofficial adjusted daily closes; locked calendar windows from data/seasonal-signals.json",
      "training_years":doc["training_years"],"holdout_years":doc["holdout_years"],
      "roundtrip_cost_assumption":ROUNDTRIP_COST,
      "important_limitation":"Holdout years were already used to accept or reject candidates. These results are retrospective diagnostics, NOT a new independent or untouched out-of-sample test. Fixed-window return is NOT full portfolio return and omits stop-loss, capital sizing, FX and taxes. QQQ benchmark is before costs.",
      "rows":rows}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Retrospective only; ETFs:",len(rows),"windows:",sum(len(r["observations"]) for r in rows))

if __name__=="__main__":
    main()
