#!/usr/bin/env python3
"""Publish paper-only trade/risk events to ntfy.

No broker access. A sent-event ledger is persisted in the paper portfolio.
Does not emit daily price checks or reconstructed historical trades.
"""
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
PORTFOLIO=ROOT/"data"/"paper-portfolio.json"
MAX_SENT=2000

def topic_from_secret(raw):
    raw=raw.strip()
    if raw.startswith("https://"):
        url=urllib.parse.urlsplit(raw)
        if url.scheme!="https" or url.hostname!="ntfy.sh" or url.port not in (None,443) or url.username or url.password or url.query or url.fragment:
            raise ValueError("Topic URL must be on https://ntfy.sh")
        raw=url.path.lstrip("/")
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",raw):
        raise ValueError("Invalid ntfy channel format")
    return raw

def message(event):
    kind=event.get("kind")
    if kind in ("PAPER_BUY","PAPER_SELL"):
        verb="Kauf" if kind=="PAPER_BUY" else "Verkauf"
        title=f"ETF Papier-{verb}: {event['ticker']}"
        msg=(f"Nur virtuell: {verb} {event['qty']} Anteile {event['ticker']} "
             f"zum simulierten Kurs {event['price_usd']:.2f} USD. "
             f"Datum {event['date']}. Grund: {event['reason']}. Kein Echtgeld.")
        return title,msg,"default"
    if kind=="PAPER_RISK_STOP":
        return ("ETF Paper Risikostopp",
            f"Nur virtuell: 10%-Depotverlustgrenze erreicht. Neue Testkaeufe gesperrt. "
            f"Datum {event['date']}, Rueckgang {event['drawdown_pct']}%. Keine Brokerorder.",
            "high")
    raise ValueError("Unknown notification event type")

def dispatch(state, topic, send):
    if state.get("mode")!="PAPER_ONLY":
        raise ValueError("Wrong portfolio mode")
    outbox=state.get("notification_outbox",[])
    sent=state.setdefault("notification_sent_ids",[])
    delivered=0
    for event in outbox:
        if event["id"] in sent:continue
        title,body,priority=message(event)
        send(topic,title,body,priority)
        sent.append(event["id"])
        state["notification_sent_ids"]=sent[-MAX_SENT:]
        delivered+=1
        # Persist after EACH successful send, reducing duplication on retry.
        tmp=PORTFOLIO.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        tmp.replace(PORTFOLIO)
    return delivered

def send_ntfy(topic,title,body,priority):
    req=urllib.request.Request("https://ntfy.sh/"+topic,
        data=body.encode("utf-8"),method="POST",
        headers={"Title":title,"Priority":priority,
                 "Tags":"warning" if priority=="high" else "chart_with_upwards_trend"})
    with urllib.request.urlopen(req,timeout=20) as response:
        if not 200<=response.status<300:
            raise RuntimeError("Push was not accepted")

def main():
    if not PORTFOLIO.exists():
        raise SystemExit("Paper portfolio missing.")
    state=json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    pending=[e for e in state.get("notification_outbox",[])
             if e["id"] not in state.get("notification_sent_ids",[])]
    if not pending:
        print("PAPER_PUSH: no new buy/sell/risk events; no push")
        return 0
    raw=os.environ.get("NTFY_TOPIC","")
    if not raw:
        print("PAPER_PUSH: private ETF_NTFY_TOPIC missing, unsent events retained.")
        return 0
    try:
        topic=topic_from_secret(raw)
        count=dispatch(state,topic,send_ntfy)
        print(f"PAPER_PUSH: {count} virtual event(s) accepted by ntfy; phone delivery not confirmed.")
    except (urllib.error.HTTPError,urllib.error.URLError,ValueError,OSError,RuntimeError) as exc:
        print("PAPER_PUSH: delivery failed:",type(exc).__name__)
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
