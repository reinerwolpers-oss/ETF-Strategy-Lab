#!/usr/bin/env python3
"""ETF Strategy Lab paper simulator. No broker libraries, credentials or order APIs.

IMPORTANT: Fills are indicative daily closing-price estimates, not executable
orders. All funds/prices are USD. Closed-candle data may be delayed.
"""
import datetime as dt
import json
import math
import os
import pathlib
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=pathlib.Path(__file__).resolve().parents[1]
STATE=ROOT/"data"/"paper-portfolio.json"
SIGNALS=ROOT/"data"/"seasonal-signals.json"
START_CASH=500.0
CONFIG=ROOT/"config"/"paper-settings.json"
MAX_HISTORY=1500
MAX_TRADES=1000
MAX_POSITION_FRACTION=0.20
# Fractional shares are a virtual modeling choice, NOT a guarantee of IBKR execution.
FRACTIONAL_SHARE_STEP=0.001
MAX_INVESTED_FRACTION=0.60
STOP_LOSS_FRACTION=0.08
MAX_DRAWDOWN_FRACTION=0.10
FEE_PER_FILL=1.0
SLIPPAGE_FRACTION=0.001
SUPPORTED={"VT","QQQ","SMH","MTUM","BND"}

MARKET_TZ=ZoneInfo("America/New_York")

def us_market_date(now):
    """Date of the US trading session, avoiding UTC-midnight rollover."""
    if now.tzinfo is None:
        raise ValueError("now must have a timezone")
    return now.astimezone(MARKET_TZ).date()

def require_same_completed_market_close(market,now):
    """Fail closed on mixed, missing or earlier dates. No synthetic forward-fills."""
    expected=us_market_date(now)
    dates={ticker:day for ticker,(day,price) in market.items()}
    if not dates or any(day!=expected for day in dates.values()):
        raise RuntimeError("A required ETF has no completed US market close for "+expected.isoformat()+". No virtual orders processed.")
    return expected


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def fetch_close(ticker):
    err=None
    for hostname in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        url=(f"https://{hostname}/v8/finance/chart/{urllib.parse.quote(ticker)}"
             f"?range=14d&interval=1d")
        try:
            request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
            with urllib.request.urlopen(request,timeout=25) as resp:
                result=json.load(resp)["chart"]["result"][0]
            values=result["indicators"]["quote"][0]["close"]
            items=[]
            for stamp,price in zip(result["timestamp"],values):
                if isinstance(price,(float,int)) and math.isfinite(price) and price>0:
                    day=dt.datetime.fromtimestamp(stamp,dt.timezone.utc).date()
                    items.append((day,float(price)))
            if not items: raise RuntimeError("No closes")
            return max(items)
        except Exception as exc:
            err=exc
            time.sleep(1)
    raise RuntimeError(f"No trusted price for {ticker}: {err}")

def paper_settings():
    cfg=load_json(CONFIG)
    if cfg.get("mode")!="PAPER_ONLY" or type(cfg.get("enabled")) is not bool:
        raise RuntimeError("Paper configuration invalid: fail closed")
    return cfg

def record_error(message):
    # The repository workflow may not persist errors unless it commits state.
    # Never mutate positions after a failed market-data check.
    print("PAPER ERROR:",message)

def new_state():
    return {"schema":1,"mode":"PAPER_ONLY","trading_enabled":True,"starting_cash":START_CASH,
            "cash":START_CASH,"positions":{},"trades":[],"equity_history":[],
            "peak_equity":START_CASH,"halted":False,"halt_reason":None,
            "last_run":None,"last_error":None,"notification_outbox":[],"notification_sent_ids":[]}

def save(state):
    STATE.parent.mkdir(parents=True,exist_ok=True)
    tmp=STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(tmp,STATE)

def add_notification(state, event):
    """Append a deterministic one-time paper event to a bounded outbox."""
    if state.get("mode")!="PAPER_ONLY":
        raise RuntimeError("Notifications allowed only in paper mode")
    event_id=event["id"]
    outbox=state.setdefault("notification_outbox",[])
    sent=state.setdefault("notification_sent_ids",[])
    if event_id not in sent and not any(e["id"]==event_id for e in outbox):
        outbox.append(event)
    state["notification_outbox"]=outbox[-200:]

def trade(state,day,ticker,side,quantity,quote,reason):
    assert quantity>0 and side in ("BUY","SELL")
    # Model pessimistic slippage plus a fixed fee; only synthetic fills.
    fill=quote*(1+SLIPPAGE_FRACTION if side=="BUY" else 1-SLIPPAGE_FRACTION)
    amount=round(fill*quantity,8)
    if side=="BUY":
        if state["cash"]<amount+FEE_PER_FILL-1e-6:return False
        state["cash"]-=amount+FEE_PER_FILL
        state["positions"][ticker]={"qty":quantity,"entry_price":fill,
            "entry_date":day.isoformat(),"peak_price":fill}
    else:
        if ticker not in state["positions"]:return False
        state["cash"]+=amount-FEE_PER_FILL
        del state["positions"][ticker]
    new_trade={"date":day.isoformat(),"ticker":ticker,
        "side":side,"qty":quantity,"estimated_price_usd":round(fill,5),
        "estimated_notional_usd":round(amount,4),"fee_usd":FEE_PER_FILL,
        "reason":reason,"execution":"SYNTHETIC_DAILY_CLOSE_NOT_BROKER_ORDER"}
    state["trades"].append(new_trade)
    add_notification(state,{"id":f"paper:{day.isoformat()}:{ticker}:{side}",
        "kind":"PAPER_"+side,"date":day.isoformat(),"ticker":ticker,
        "qty":quantity,"price_usd":round(fill,5),"reason":reason})
    return True

def main():
    now=dt.datetime.now(dt.timezone.utc)
    today=us_market_date(now)
    settings=paper_settings()
    state=load_json(STATE) if STATE.exists() else new_state()
    if state.get("mode")!="PAPER_ONLY":raise RuntimeError("Fail closed: invalid trading mode")
    if state.get("starting_cash")!=START_CASH:raise RuntimeError("Unexpected capital configuration")
    if not settings["enabled"] or not state.get("trading_enabled",False):
        state["last_run"]=now.isoformat()
        state["last_error"]="Paper execution disabled by safety switch"
        save(state)
        print("Paper execution disabled; no fills")
        return

    # Validate all persisted positions BEFORE accessing external quotes.
    for ticker,position in state["positions"].items():
        if ticker not in SUPPORTED or not math.isfinite(float(position["qty"])) or float(position["qty"])<=0:
            raise RuntimeError("Invalid paper position: fail closed")
    document=load_json(SIGNALS)
    if document.get("version")!=4 or not document.get("candidates"):
        raise RuntimeError("Valid seasonal candidates not available")
    stamp=dt.datetime.fromisoformat(document["generated_at"])
    if (now-stamp).total_seconds()>5*86400 or stamp>now+dt.timedelta(minutes=5):
        raise RuntimeError("Seasonal candidate file older than 5 days; fail closed")

    candidates={x["ticker"]:x for x in document["candidates"]
                if x.get("passes_validation") and x["ticker"] in SUPPORTED}
    tickers=set(state["positions"])|set(candidates)
    market={ticker:fetch_close(ticker) for ticker in tickers}
    # Never execute on missing/old closes or partial market data.
    today=require_same_completed_market_close(market,now)
    fresh={ticker:(day==today) for ticker,(day,price) in market.items()}
    # Avoid accidentally processing the same closing candle twice.
    last=state.get("last_processed_market_day")
    if last and today.isoformat()<=last:
        print("No new trading day",today)
        return

    equity=state["cash"]+sum(
        p["qty"]*market[t][1] for t,p in state["positions"].items())
    state["peak_equity"]=max(state["peak_equity"],equity)
    drawdown=equity/state["peak_equity"]-1
    if drawdown<=-MAX_DRAWDOWN_FRACTION and not state.get("halted",False):
        state["halted"]=True
        state["halt_reason"]="Portfolio drawdown breached 10%; buy orders permanently blocked"
        add_notification(state,{"id":"paper:riskstop:drawdown10",
            "kind":"PAPER_RISK_STOP","date":today.isoformat(),
            "reason":state["halt_reason"],"drawdown_pct":round(drawdown*100,2)})

    # Manage exits first. Missing fresh prices never trigger fake fills.
    for ticker,position in list(state["positions"].items()):
        day,price=market[ticker]
        if not fresh[ticker]:continue
        position["peak_price"]=max(position.get("peak_price",position["entry_price"]),price)
        # Lock the exit date at entry. Do not let a later scanner change it.
        if position.get("planned_exit_date"):
            seasonal_exit=dt.date.fromisoformat(position["planned_exit_date"])
        elif ticker in candidates:
            entry=dt.date.fromisoformat(position["entry_date"])
            seasonal_exit=entry+dt.timedelta(days=int(candidates[ticker]["holding_calendar_days"]))
            position["planned_exit_date"]=seasonal_exit.isoformat()
        else:
            # Legacy position with no scheduled exit: prioritize closure.
            seasonal_exit=today
        reason=None
        if price<=position["entry_price"]*(1-STOP_LOSS_FRACTION):
            reason="8% stop-loss threshold at daily close"
        elif today>=seasonal_exit:
            reason="Seasonal holding period ended"
        if reason:trade(state,today,ticker,"SELL",position["qty"],price,reason)

    # Do not enter a window late. 0-3 calendar days permits weekends.
    if not state["halted"]:
        for ticker,candidate in sorted(candidates.items()):
            if ticker in state["positions"] or not fresh[ticker]:continue
            entry=dt.date.fromisoformat(f"{today.year}-{candidate['entry_month_day']}")
            if not 0<=(today-entry).days<=3:continue
            # A fixed calendar date is not a forward-looking return signal.
            price=market[ticker][1]
            equity=state["cash"]+sum(p["qty"]*market[t][1] for t,p in state["positions"].items())
            invested=sum(p["qty"]*market[t][1] for t,p in state["positions"].items())
            budget=min(equity*MAX_POSITION_FRACTION,
                       max(0,equity*MAX_INVESTED_FRACTION-invested),
                       state["cash"]-FEE_PER_FILL)
            unit_cost=price*(1+SLIPPAGE_FRACTION)
            qty=math.floor(max(0,budget)/unit_cost/FRACTIONAL_SHARE_STEP)*FRACTIONAL_SHARE_STEP
            qty=round(qty,3)
            if qty>0 and trade(state,today,ticker,"BUY",qty,price,
                            "Passed historic holdout; scheduled calendar window"):
                planned=today+dt.timedelta(days=int(candidate["holding_calendar_days"]))
                state["positions"][ticker]["planned_exit_date"]=planned.isoformat()
                state["positions"][ticker]["season_entry_month_day"]=candidate["entry_month_day"]

    # Fractional shares are synthetic accounting units, not broker fills.
    equity=state["cash"]+sum(p["qty"]*market[t][1] for t,p in state["positions"].items())
    state["peak_equity"]=max(state["peak_equity"],equity)
    invested=sum(p["qty"]*market[t][1] for t,p in state["positions"].items())
    state["equity_history"].append({"date":today.isoformat(),
        "equity_usd":round(equity,2),"cash_usd":round(state["cash"],2),
        "invested_usd":round(invested,2),
        "drawdown_pct":round(100*(equity/state["peak_equity"]-1),3),
        "positions":len(state["positions"]),"quotes_fresh":all(fresh.values()),
        "benchmark_qqq_close_usd":round(market["QQQ"][1],5) if "QQQ" in market else None})
    state["quotes"]={t:{"date":day.isoformat(),"close_usd":round(price,5)}
                     for t,(day,price) in market.items()}
    state["equity_history"]=state["equity_history"][-MAX_HISTORY:]
    state["trades"]=state["trades"][-MAX_TRADES:]
    state["last_processed_market_day"]=today.isoformat()
    state["last_run"]=now.isoformat()
    state["last_error"]=None
    save(state)
    print("PAPER ONLY",today,"equity USD",round(equity,2),
          "positions",len(state["positions"]),"trades",len(state["trades"]),
          "halted",state["halted"])


if __name__=="__main__":
    main()
