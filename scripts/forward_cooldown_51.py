#!/usr/bin/env python3
"""Frozen forward-only 30-session paper research, independent of original paper state.

Uses public completed US daily closes and synthetic accounting only.
No broker connectivity, no backfill, no alerts, no live orders.
"""
import datetime as dt
import json
import math
import os
from paper_trade import ROOT, fetch_close, require_same_completed_market_close, us_market_date

CONFIG=ROOT/"config"/"forward-cooldown-51.json"
STATE=ROOT/"data"/"forward-cooldown-51.json"

def get_config():
    c=json.loads(CONFIG.read_text(encoding="utf-8"))
    if c.get("mode")!="PAPER_ONLY" or c.get("broker_connection") is not False or c.get("live_orders") is not False:
        raise ValueError("Unsafe configuration: fail closed")
    if c.get("variant")!="FROZEN_30_SESSION_COOLDOWN" or c.get("cooldown_sessions")!=30:
        raise ValueError("Expected frozen 30-session policy")
    if {x["ticker"] for x in c["frozen_windows"]}!={"QQQ","SMH"}:
        raise ValueError("Unexpected ETF universe")
    return c

def init_state(cfg):
    return {"schema":1,"mode":"PAPER_ONLY","variant":cfg["variant"],"starting_cash":500.0,
        "cash":500.0,"positions":{},"trades":[],"equity_history":[],
        "peak_equity":500.0,"risk_epoch_peak":500.0,"global_peak":500.0,
        "cooldown_remaining":0,"cooldown_events":[],"processed_sessions":0,
        "last_processed_market_day":None,"last_run":None,"last_error":None}

def apply_day(state,cfg,day,market):
    """Mutate isolated paper state once per new US closing day; no external effects."""
    if state.get("mode")!="PAPER_ONLY" or state.get("variant")!=cfg["variant"]:
        raise ValueError("Invalid saved state")
    if state.get("starting_cash")!=500.0:
        raise ValueError("Invalid initial capital")
    if day<dt.date.fromisoformat(cfg["start_date"]):
        raise ValueError("Cannot backfill earlier than frozen start")
    previous=state.get("last_processed_market_day")
    if previous and day.isoformat()<=previous:
        return False
    symbols={x["ticker"] for x in cfg["frozen_windows"]}
    if set(market)!=symbols or any(not math.isfinite(market[s]) or market[s]<=0 for s in symbols):
        raise ValueError("Incomplete or invalid market data")
    risk=cfg["risk"]
    cash=float(state["cash"])
    positions=state["positions"]
    for sym,p in positions.items():
        if sym not in symbols or p["qty"]<=0 or not math.isfinite(p["qty"]):
            raise ValueError("Invalid open paper position")

    def equity():
        return cash+sum(p["qty"]*market[s] for s,p in positions.items())

    def synthetic_trade(sym,side,qty,reason):
        nonlocal cash
        fill=market[sym]*(1+risk["slippage_fraction"] if side=="BUY" else 1-risk["slippage_fraction"])
        amount=qty*fill
        fee=risk["fee_per_trade_usd"]
        if side=="BUY":
            if cash+1e-8<amount+fee:return False
            cash-=amount+fee
        else:
            cash+=amount-fee
        state["trades"].append({"date":day.isoformat(),"ticker":sym,"side":side,
            "qty":round(qty,3),"price_usd":round(fill,5),"fee_usd":fee,
            "reason":reason,"execution":"SYNTHETIC_DAILY_CLOSE_NO_BROKER"})
        return fill

    # Count only freshly processed, verified market sessions, never wall-clock days.
    previous_cooldown=int(state.get("cooldown_remaining",0))
    if previous_cooldown>0:
        state["cooldown_remaining"]=previous_cooldown-1
        if state["cooldown_remaining"]==0:
            state["risk_epoch_peak"]=equity()
            state["cooldown_events"].append({"date":day.isoformat(),"event":"RESUME_ENTRIES"})

    state["risk_epoch_peak"]=max(float(state["risk_epoch_peak"]),equity())
    if state["cooldown_remaining"]==0 and equity()/state["risk_epoch_peak"]-1<=-risk["portfolio_drawdown_trigger_fraction"]:
        state["cooldown_remaining"]=cfg["cooldown_sessions"]
        state["cooldown_events"].append({"date":day.isoformat(),"event":"PAUSE_ENTRIES","sessions":cfg["cooldown_sessions"]})

    for sym,p in list(positions.items()):
        reason=None
        if market[sym]<=p["entry_price"]*(1-risk["stop_loss_fraction"]):
            reason="8% close-based stop"
        elif day>=dt.date.fromisoformat(p["planned_exit_date"]):
            reason="Frozen seasonal exit"
        if reason and synthetic_trade(sym,"SELL",p["qty"],reason) is not False:
            del positions[sym]

    if state["cooldown_remaining"]==0:
        for w in sorted(cfg["frozen_windows"],key=lambda x:x["ticker"]):
            sym=w["ticker"]
            if sym in positions:continue
            target=dt.date.fromisoformat(f"{day.year}-{w['entry_month_day']}")
            if not 0<=(day-target).days<=3:continue
            invested=sum(p["qty"]*market[s] for s,p in positions.items())
            value=equity()
            budget=min(value*risk["max_position_fraction"],
                       max(0,value*risk["max_invested_fraction"]-invested),
                       cash-risk["fee_per_trade_usd"])
            step=risk["fractional_share_step"]
            unit=market[sym]*(1+risk["slippage_fraction"])
            qty=round(math.floor(max(0,budget)/unit/step)*step,3)
            if qty<=0:continue
            fill=synthetic_trade(sym,"BUY",qty,"Frozen prospective seasonal window")
            if fill is not False:
                positions[sym]={"qty":qty,"entry_price":fill,
                    "entry_date":day.isoformat(),
                    "planned_exit_date":(day+dt.timedelta(days=w["holding_calendar_days"])).isoformat()}

    value=equity()
    state["risk_epoch_peak"]=max(float(state["risk_epoch_peak"]),value)
    state["global_peak"]=max(float(state["global_peak"]),value)
    if state["cooldown_remaining"]==0 and value/state["risk_epoch_peak"]-1<=-risk["portfolio_drawdown_trigger_fraction"]:
        state["cooldown_remaining"]=cfg["cooldown_sessions"]
        state["cooldown_events"].append({"date":day.isoformat(),"event":"PAUSE_ENTRIES","sessions":cfg["cooldown_sessions"]})

    state["cash"]=round(cash,8)
    state["processed_sessions"]=int(state["processed_sessions"])+1
    state["last_processed_market_day"]=day.isoformat()
    state["equity_history"].append({"date":day.isoformat(),"equity_usd":round(value,2),
        "cash_usd":round(cash,2),"positions":len(positions),
        "drawdown_pct":round(100*(value/state["global_peak"]-1),3),
        "cooldown_remaining":state["cooldown_remaining"],
        "benchmark_qqq_close_usd":round(market["QQQ"],5)})
    state["equity_history"]=state["equity_history"][-1500:]
    state["trades"]=state["trades"][-1000:]
    return True

def main():
    cfg=get_config()
    now=dt.datetime.now(dt.timezone.utc)
    session=us_market_date(now)
    if session<dt.date.fromisoformat(cfg["start_date"]):
        print("Frozen forward variant not started:",session)
        return
    state=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else init_state(cfg)
    if state.get("last_processed_market_day") and state["last_processed_market_day"]>=session.isoformat():
        print("Already processed US market session",session)
        return
    market={x["ticker"]:fetch_close(x["ticker"]) for x in cfg["frozen_windows"]}
    require_same_completed_market_close(market,now)
    prices={s:quote for s,(day,quote) in market.items()}
    if not apply_day(state,cfg,session,prices):
        return
    state["last_run"]=now.isoformat()
    STATE.parent.mkdir(parents=True,exist_ok=True)
    temp=STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(temp,STATE)
    print("FROZEN PAPER ONLY",session,"equity",state["equity_history"][-1]["equity_usd"],
          "trades",len(state["trades"]),"cooldown_remaining",state["cooldown_remaining"])

if __name__=="__main__":
    main()
