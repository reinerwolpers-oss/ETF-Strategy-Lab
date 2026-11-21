#!/usr/bin/env python3
"""Standalone retrospective 500 USD portfolio simulation. Research only.

Re-selects each ETF's seasonality from PRIOR completed years. Synthetic
same-day close fills overstate executability; no brokers or paper-state writes.
"""
import datetime as dt
import json
import math
from seasonal_scan import ROOT, SYMBOLS, load
from walk_forward_research import choose_window, FIRST_TEST_YEAR, FIRST_TRAIN_YEAR
from paper_trade import (START_CASH, MAX_POSITION_FRACTION, MAX_INVESTED_FRACTION,
                         STOP_LOSS_FRACTION, MAX_DRAWDOWN_FRACTION, FEE_PER_FILL,
                         SLIPPAGE_FRACTION, FRACTIONAL_SHARE_STEP)

DEST=ROOT/"data"/"historical-portfolio-50.json"

def simulate(series, first=FIRST_TEST_YEAR, last=2025):
    if "QQQ" not in series or first>last:
        raise ValueError("QQQ and valid year range required")
    symbols=sorted(SYMBOLS)
    if any(s not in series for s in symbols):
        raise ValueError("Complete universe required")
    cash=START_CASH
    peak=START_CASH
    positions={}
    trades=[]
    curve=[]
    halted=False
    selected={}
    skipped_days=0
    # Common trading dates: never use a forward-filled or invented closing price.
    dates=sorted(set.intersection(*(set(series[s]) for s in symbols)))
    dates=[d for d in dates if first<=d.year<=last]
    if not dates:
        raise ValueError("No common dated market observations")
    baseline=series["QQQ"][dates[0]]
    for date in dates:
        if date.year not in selected:
            prior=list(range(FIRST_TRAIN_YEAR,date.year))
            selected[date.year]={}
            for s in symbols:
                candidate=choose_window(series[s],prior)
                if candidate:
                    _,offset,duration,count=candidate
                    selected[date.year][s]={"entry_target":dt.date(date.year,1,1)+dt.timedelta(days=offset),
                                           "duration":duration,"training_samples":count}
        market={s:series[s][date] for s in symbols}
        def equity():
            return cash+sum(p["qty"]*market[s] for s,p in positions.items())
        def fill(s,side,qty,reason):
            nonlocal cash
            rate=market[s]*(1+SLIPPAGE_FRACTION if side=="BUY" else 1-SLIPPAGE_FRACTION)
            amount=qty*rate
            if side=="BUY":
                if cash+1e-8<amount+FEE_PER_FILL:
                    return False
                cash-=amount+FEE_PER_FILL
            else:
                cash+=amount-FEE_PER_FILL
            trades.append({"date":date.isoformat(),"ticker":s,"side":side,"qty":round(qty,3),
                           "price_usd":round(rate,5),"fee_usd":FEE_PER_FILL,"reason":reason})
            return True
        # Drawdown guard is checked on available daily-close marks before new entries.
        peak=max(peak,equity())
        if equity()/peak-1<=-MAX_DRAWDOWN_FRACTION:
            halted=True
        for s,p in list(positions.items()):
            px=market[s]
            if px<=p["entry_price"]*(1-STOP_LOSS_FRACTION):
                reason="Stop threshold at daily close"
            elif date>=p["exit_target"]:
                reason="Seasonal holding period ended"
            else:
                continue
            if fill(s,"SELL",p["qty"],reason):
                del positions[s]
        if not halted:
            for s,c in sorted(selected[date.year].items()):
                if s in positions:
                    continue
                age=(date-c["entry_target"]).days
                if age<0 or age>3:
                    continue
                value=equity()
                invested=sum(p["qty"]*market[t] for t,p in positions.items())
                budget=min(value*MAX_POSITION_FRACTION,
                           max(0,value*MAX_INVESTED_FRACTION-invested),
                           cash-FEE_PER_FILL)
                qty=round(math.floor(max(0,budget)/market[s]/(1+SLIPPAGE_FRACTION)/FRACTIONAL_SHARE_STEP)*FRACTIONAL_SHARE_STEP,3)
                if qty<=0:
                    continue
                entry=market[s]*(1+SLIPPAGE_FRACTION)
                if fill(s,"BUY",qty,"Prior-year-trained seasonal calendar window"):
                    positions[s]={"qty":qty,"entry_price":entry,
                                  "exit_target":date+dt.timedelta(days=c["duration"])}
        value=equity()
        peak=max(peak,value)
        if value/peak-1<=-MAX_DRAWDOWN_FRACTION:
            halted=True
        benchmark=START_CASH*market["QQQ"]/baseline
        curve.append({"date":date.isoformat(),"equity_usd":round(value,2),
                      "qqq_buy_hold_usd":round(benchmark,2),
                      "drawdown_pct":round(100*(value/peak-1),3),
                      "cash_usd":round(cash,2),"positions":len(positions)})
    def maximum_drawdown(values):
        top=values[0]
        worst=0.
        for v in values:
            top=max(top,v)
            worst=min(worst,v/top-1)
        return worst
    ending=curve[-1]
    return {"starting_cash_usd":START_CASH,
            "simulation_start":curve[0]["date"],"simulation_end":curve[-1]["date"],
            "paper_ending_equity_usd":ending["equity_usd"],
            "qqq_ending_equity_usd":ending["qqq_buy_hold_usd"],
            "paper_total_return":round(ending["equity_usd"]/START_CASH-1,6),
            "qqq_total_return":round(ending["qqq_buy_hold_usd"]/START_CASH-1,6),
            "paper_max_drawdown":round(maximum_drawdown([START_CASH]+[p["equity_usd"] for p in curve]),6),
            "qqq_max_drawdown":round(maximum_drawdown([START_CASH]+[p["qqq_buy_hold_usd"] for p in curve]),6),
            "halted_new_entries":halted,"transactions":len(trades),
            "open_positions_at_end":{s:{"quantity":p["qty"],"planned_exit_date":p["exit_target"].isoformat()} for s,p in positions.items()},
            "selections":{str(y):{s:{"entry_target":v["entry_target"].isoformat(),"holding_days":v["duration"],"training_samples":v["training_samples"]} for s,v in row.items()} for y,row in selected.items()},
            "trades":trades,"curve":curve}

def main():
    today=dt.datetime.now(dt.timezone.utc).date()
    last=today.year-1
    market={s:load(s) for s in SYMBOLS}
    result=simulate(market,last=last)
    result.update({"version":1,"mode":"RESEARCH_ONLY","method":"PRIOR_YEAR_TRAINED_HISTORICAL_PORTFOLIO",
       "generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
       "data_source":"Yahoo Finance unofficial adjusted close proxies",
       "limitations":"Retrospective research, built after reviewing earlier results; no untouched independent test. Every selection uses prior completed calendar years only, but synthetic execution at the same daily close after seeing it is not executable in reality. Historical adjusted prices differ from raw tradeable fills. Cash held in USD, no FX, tax, cash interest or real dividend handling. Missing cross-ETF trading dates are excluded; intraday stop losses, order spreads and gaps are not modeled. Benchmark QQQ is a hypothetical cost-free buy and hold. Open positions are marked to market at final date; no forced liquidation."})
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Historical research only",result["simulation_start"],result["simulation_end"],"equity",result["paper_ending_equity_usd"],"trades",result["transactions"])

if __name__=="__main__":
    main()
