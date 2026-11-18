#!/usr/bin/env python3
"""ETF Strategy Lab 4.8 - local, read-only historical price monitor.

Requires TWS DEMO on localhost:7497 with Read-Only API enabled.
Creates ONLY local summary JSON, HTML and append-only log. It NEVER places
orders, reads accounts, sends network requests except via the local IBKR
demo and the public GitHub daily quote snapshot, or pushes files to GitHub.
"""
import datetime as dt
import html
import json
import pathlib
import sys
import traceback

try:
    from .ibkr_historical_compare import run_probe
except ImportError:
    from ibkr_historical_compare import run_probe

OUT = pathlib.Path.home() / "IBKR-Test"
SUMMARY = OUT / "ibkr-monitor-status.json"
REPORT = OUT / "ibkr-monitor-report.html"
LOG = OUT / "ibkr-monitor.log"
DIFFERENCE_WARNING_PCT = 1.0
MAX_SOURCE_AGE_CALENDAR_DAYS = 5


def evaluate(data, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    statuses={}
    alarms=[]
    if not data.get("handshake"):
        alarms.append("API_HANDSHAKE_FAILED")
    if data.get("status") != "BARS_RECEIVED":
        alarms.append("HISTORICAL_DATA_INCOMPLETE")
    for ticker in ("QQQ","SMH"):
        row=data.get("instruments",{}).get(ticker,{})
        checks=[]
        latest=row.get("last_ibkr_bar")
        if not latest:
            checks.append("NO_IBKR_BAR")
        else:
            try:
                lastdate=dt.date.fromisoformat(latest["date"])
                age=(now.date()-lastdate).days
                if age < 0 or age > MAX_SOURCE_AGE_CALENDAR_DAYS:
                    checks.append("IBKR_DATA_STALE")
            except (ValueError,KeyError,TypeError):
                checks.append("BAD_IBKR_DATE")
        refdate=row.get("reference_date")
        if refdate:
            try:
                age=(now.date()-dt.date.fromisoformat(refdate)).days
                if age < 0 or age > MAX_SOURCE_AGE_CALENDAR_DAYS:
                    checks.append("REFERENCE_DATA_STALE")
            except (ValueError,TypeError):
                checks.append("BAD_REFERENCE_DATE")
        else:
            checks.append("REFERENCE_NOT_AVAILABLE")
        same=row.get("same_date_comparison")
        if not same:
            checks.append("NO_SAME_DATE_COMPARISON")
        else:
            difference=same.get("difference_pct")
            if not isinstance(difference,(int,float)):
                checks.append("BAD_PRICE_DIFFERENCE")
            elif abs(difference) >= DIFFERENCE_WARNING_PCT:
                checks.append("PRICE_DIVERGENCE_GE_1_PERCENT")
        statuses[ticker]={"checks":checks,"last_bar":latest,"comparison":same,
                          "reference_date":refdate,"bars_received":row.get("bars_received",0)}
        alarms.extend(ticker+":"+flag for flag in checks)
    return {"schema":1,"version":"4.8","mode":"LOCAL_IBKR_DEMO_READ_ONLY",
            "generated_at_utc":now.isoformat(),"ibkr_status":data.get("status","UNKNOWN"),
            "handshake":bool(data.get("handshake")),"prices":statuses,
            "warnings":alarms,"health":"OK" if not alarms else "ATTENTION",
            "threshold_difference_pct":DIFFERENCE_WARNING_PCT,
            "max_source_age_calendar_days":MAX_SOURCE_AGE_CALENDAR_DAYS,
            "source_details":"IBKR TRADES RTH unadjusted versus public provider daily close",
            "paper_portfolio_changed":False,"broker_orders_sent":False,
            "github_upload":False}


def create_html(summary):
    def escape(value):
        return html.escape(str(value if value is not None else "-"),quote=True)
    rows=[]
    for ticker,item in summary["prices"].items():
        bar=item.get("last_bar") or {}
        comp=item.get("comparison") or {}
        issues=", ".join(item["checks"]) or "OK"
        rows.append("<tr><td>"+escape(ticker)+"</td><td>"+escape(bar.get("date"))+
                    "</td><td>"+escape(bar.get("close_usd"))+"</td><td>"+
                    escape(item.get("reference_date"))+"</td><td>"+
                    escape(comp.get("difference_pct"))+"</td><td>"+escape(issues)+"</td></tr>")
    warnings="<p>"+escape(", ".join(summary["warnings"]) or "Keine")+"</p>"
    return """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IBKR Demo-Monitor 4.8</title><style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1080px;margin:32px auto;
padding:0 20px;background:#101827;color:#eff5ff}h1{font-size:28px}
.card{background:#1d2b41;border:1px solid #344962;border-radius:14px;padding:20px;margin:15px 0}
table{width:100%;border-collapse:collapse;min-width:650px}td,th{text-align:left;padding:12px;
border-bottom:1px solid #465470}.scroll{overflow:auto}small{color:#bbcee0}
</style></head><body><h1>IBKR Demo-Kursmonitor 4.8</h1>
<div class="card"><strong>Status: """+escape(summary["health"])+"""</strong><p>Letzte Prüfung: """+escape(summary["generated_at_utc"])+"""</p>
<p>API-Handshake: """+escape(summary["handshake"])+""" · Historie: """+escape(summary["ibkr_status"])+"""</p></div>
<div class="card"><h2>QQQ &amp; SMH</h2><div class="scroll"><table>
<thead><tr><th>ETF</th><th>IBKR Datum</th><th>IBKR USD</th><th>Referenzdatum</th>
<th>Abweichung %</th><th>Prüfung</th></tr></thead><tbody>"""+ "".join(rows)+"""</tbody></table></div></div>
<div class="card"><h2>Hinweise</h2>"""+warnings+"""<small>Warnung ab 1 % Abweichung; Datenalter > 5 Kalendertage.
Verglichen werden nur Kurse vom selben Börsentag. Unterschiedliche Datenaufbereitung
kann Kursdifferenzen verursachen. Demo-Daten können fehlen oder verzögert sein.</small></div>
<div class="card"><strong>Nur lokal · keine Kontodaten · keine Orders · kein GitHub-Upload</strong>
<p>Dies ist keine Live-Handelsfreigabe und keine Prüfung von ETF-Strategieerträgen.</p></div>
</body></html>"""


def append_log(message):
    OUT.mkdir(parents=True,exist_ok=True)
    with LOG.open("a",encoding="utf-8") as file:
        file.write(dt.datetime.now(dt.timezone.utc).isoformat()+" "+message+"\n")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        data=run_probe(20)
        report=evaluate(data)
        SUMMARY.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        REPORT.write_text(create_html(report),encoding="utf-8")
        append_log(report["health"]+" "+", ".join(report["warnings"]))
        print("Monitor 4.8:",report["health"])
        print("Bericht:",REPORT)
        print("JSON:",SUMMARY)
        for ticker,details in report["prices"].items():
            print(ticker,details["checks"] or "OK")
        print("KEINE Orders, KEIN GitHub-Upload.")
        return 0 if report["health"]=="OK" else 2
    except Exception as exc:
        # Scheduled pythonw sessions have no terminal: always keep a local log.
        append_log("MONITOR_FAILURE "+type(exc).__name__)
        print("Monitor fehlgeschlagen:",type(exc).__name__)
        return 1


if __name__=="__main__":
    sys.exit(main())
