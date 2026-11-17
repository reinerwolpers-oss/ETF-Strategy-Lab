#!/usr/bin/env python3
"""Build a public, read-only explanation of the paper bot state.

No network or broker connections. No orders. A missing/stale input is reported
explicitly, not presented as a verified trading signal.
"""
import datetime as dt
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
PORTFOLIO=ROOT/"data"/"paper-portfolio.json"
SEASON=ROOT/"data"/"seasonal-signals.json"
SETTINGS=ROOT/"config"/"paper-settings.json"
OUT=ROOT/"data"/"paper-decisions.json"
SUPPORTED=("VT","QQQ","SMH","MTUM","BND")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def build(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    today=now.date()
    settings=load(SETTINGS)
    portfolio=load(PORTFOLIO)
    season=load(SEASON)
    safe=(settings.get("mode")=="PAPER_ONLY" and
          settings.get("broker_connection") is False and
          settings.get("live_orders") is False and
          portfolio.get("mode")=="PAPER_ONLY")
    if not safe:
        raise RuntimeError("Paper-only safety configuration is invalid")

    last_run=portfolio.get("last_run")
    try:
        last_dt=dt.datetime.fromisoformat(last_run) if last_run else None
        if last_dt and last_dt.tzinfo is None:last_dt=last_dt.replace(tzinfo=dt.timezone.utc)
    except (TypeError,ValueError):
        last_dt=None
    bot_age=(now-last_dt).total_seconds()/3600 if last_dt else None
    bot_fresh=bot_age is not None and -1<=bot_age<=48

    season_at=season.get("generated_at")
    try:
        season_dt=dt.datetime.fromisoformat(season_at)
        if season_dt.tzinfo is None:season_dt=season_dt.replace(tzinfo=dt.timezone.utc)
        season_age=(now-season_dt).total_seconds()/86400
    except (TypeError,ValueError):
        season_age=1e9
    season_fresh=season.get("version")==4 and -1<=season_age<=5
    quotes=portfolio.get("quotes",{})
    candidates={x.get("ticker"):x for x in season.get("candidates",[])
                if x.get("ticker") in SUPPORTED}
    decisions=[]
    for ticker in SUPPORTED:
        candidate=candidates.get(ticker)
        position=portfolio.get("positions",{}).get(ticker)
        quote=quotes.get(ticker,{})
        if not season_fresh:
            reason="Saison-Scanner veraltet oder ungültig"
            action="DATA_BLOCKED"
        elif not settings.get("enabled",False) or not portfolio.get("trading_enabled",False):
            reason="Paper-Not-Stopp aktiviert"
            action="DISABLED"
        elif not bot_fresh:
            reason="Letzter Paper-Bot-Lauf fehlt oder ist veraltet"
            action="STALE_BOT"
        elif position:
            reason="Virtuelle Position offen; Exit und Verlustschwelle werden im Bot geprüft"
            action="HOLD_MONITOR"
        elif portfolio.get("halted"):
            reason="Risikostopp sperrt neue Käufe"
            action="RISK_BLOCKED"
        elif not candidate:
            reason="Kein geprüftes saisonales Modell für diesen ETF"
            action="NO_CANDIDATE"
        elif not candidate.get("passes_validation"):
            reason="Historische Validierungsgrenzen nicht bestanden"
            action="REJECTED"
        else:
            entry=dt.date.fromisoformat(f"{today.year}-{candidate['entry_month_day']}")
            diff=(today-entry).days
            if 0<=diff<=3:
                reason="Saisonfenster erreicht; Ausführung nur bei frischen Schlusskursen und Risikofreigabe"
                action="WINDOW_CHECK"
            elif diff<0:
                reason=f"Geplanter saisonaler Eintritt am {entry.isoformat()}"
                action="WAIT"
            else:
                next_date=dt.date.fromisoformat(f"{today.year+1}-{candidate['entry_month_day']}")
                reason=f"Eintrittsfenster dieses Jahres vorbei; nächste Prüfung {next_date.isoformat()}"
                action="WAIT"
        decisions.append({
            "ticker":ticker,"action":action,"reason":reason,
            "has_position":bool(position),
            "planned_exit_date":position.get("planned_exit_date") if position else None,
            "last_quote_date":quote.get("date"),
            "historical_validation_pass":bool(candidate and candidate.get("passes_validation"))
        })
    result={
        "version":1,"generated_at":now.isoformat(),"mode":"PAPER_ONLY",
        "source":"Read-only explanation based on stored paper and seasonal JSON",
        "last_paper_run":last_run,
        "last_market_day":portfolio.get("last_processed_market_day"),
        "bot_fresh":bot_fresh,"season_fresh":season_fresh,
        "kill_switch_active":not settings.get("enabled",False),
        "portfolio_halted":bool(portfolio.get("halted")),
        "portfolio_halt_reason":portfolio.get("halt_reason"),
        "positions":len(portfolio.get("positions",{})),
        "trades":len(portfolio.get("trades",[])),
        "decisions":decisions,
        "disclaimer":"Explanatory observations only. Not executable signals, broker orders, or live price feed."
    }
    return result

def main():
    report=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(OUT)
    print("Decision report created:",report["generated_at"],"bot_fresh:",report["bot_fresh"])
if __name__=="__main__":
    main()
