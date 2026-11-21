#!/usr/bin/env python3
"""Research-only comparison of three cooldowns and the untouched permanent halt.

The 15/30/60 grid was proposed after seeing the 30-day result, so this is
exploratory and must NOT be used to claim independent validation.
"""
import datetime as dt
import json
from seasonal_scan import ROOT, SYMBOLS, load
from historical_portfolio_cooldown import simulate
from historical_portfolio_50 import simulate as baseline_simulate

OUTPUT=ROOT/"data"/"cooldown-duration-comparison.json"
DURATIONS=(15,30,60)

def compact(d,label):
    return {"variant":label,"end_value_usd":d["paper_ending_equity_usd"],
            "total_return":d["paper_total_return"],
            "max_drawdown":d["paper_max_drawdown"],
            "transactions":d["transactions"],
            "risk_pauses":len([e for e in d.get("cooldown_events",[]) if e["event"]=="PAUSE_ENTRIES"]),
            "resumptions":len([e for e in d.get("cooldown_events",[]) if e["event"]=="RESUME_ENTRIES"]),
            "halted_at_end":d["halted_new_entries"],
            "curve":[{"date":x["date"],"equity_usd":x["equity_usd"]} for x in d["curve"]]}
def compare(series, last):
    base=baseline_simulate(series,last=last)
    variants=[compact(base,"Permanent")]
    for days in DURATIONS:
        run=simulate(series,last=last,cooldown_sessions=days)
        if (run["simulation_start"],run["simulation_end"])!=(base["simulation_start"],base["simulation_end"]):
            raise RuntimeError("Inconsistent historical periods")
        variants.append(compact(run,str(days)+" sessions"))
    return {"version":1,"mode":"RESEARCH_ONLY","method":"COOLDOWN_SENSITIVITY_15_30_60",
            "start":base["simulation_start"],"end":base["simulation_end"],
            "start_cash_usd":base["starting_cash_usd"],
            "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
            "variants":variants,
            "limitations":"Exploratory post-hoc selection of 15/30/60 after inspecting 30-day outcomes; not independently validated. One shared price sample and calendar selection rule, adjusted historical closes, synthetic same-close fills, no taxes/FX/actual execution or intraday stops. Paper forward trading untouched."}

def main():
    last=dt.datetime.now(dt.timezone.utc).year-1
    series={s:load(s) for s in SYMBOLS}
    report=compare(series,last)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for row in report["variants"]:
        print(row["variant"],row["end_value_usd"],row["total_return"],row["max_drawdown"],row["transactions"])

if __name__=="__main__":
    main()
