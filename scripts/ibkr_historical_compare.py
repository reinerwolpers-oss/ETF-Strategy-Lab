#!/usr/bin/env python3
"""ETF Strategy Lab 4.7: one-shot LOCAL IBKR demo historical bar comparison.

Read-only: localhost TWS API, 2 historical data requests, and a read-only
download of the public reference snapshot. Does not request account data,
submit/cancel orders, write into the GitHub repo, or alter paper trading.
"""
import datetime as dt
import json
import math
import pathlib
import threading
import urllib.error
import urllib.request

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 77
SYMBOLS = ("QQQ", "SMH")
REFERENCE_URL = ("https://raw.githubusercontent.com/reinerwolpers-oss/"
                 "ETF-Strategy-Lab/main/data/daily-etf-quotes.json")
OUTPUT_DIR = pathlib.Path.home() / "IBKR-Test"
OUTPUT_FILE = OUTPUT_DIR / "ibkr-history-comparison.json"
INFO_CODES = {2104, 2106, 2158}
TERMINAL_CODES = {162, 165, 200, 321, 354, 366, 420, 10167, 10168}

def reference_quotes(url=REFERENCE_URL):
    """Read-only public reference; never upload local IBKR data."""
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "ETF-Strategy-Lab-Local-Compare/4.7"}),
            timeout=10,
        ) as response:
            data=json.load(response)
        if data.get("version")!=1 or data.get("currency")!="USD":
            raise ValueError("Unexpected reference format")
        return {s:data.get("quotes",{}).get(s,{}) for s in SYMBOLS}, None
    except (OSError,ValueError,KeyError,TypeError,urllib.error.URLError):
        return {}, "REFERENCE_NOT_AVAILABLE"

def compare(symbol, bars, reference):
    rows={x["date"]:x for x in bars}
    ref=reference.get(symbol,{})
    day=ref.get("date")
    close=ref.get("close_usd")
    result={"ticker":symbol,"bars_received":len(rows),
            "last_ibkr_bar":rows[max(rows)] if rows else None,
            "reference_date":day if isinstance(day,str) else None,
            "reference_close_usd":close if isinstance(close,(int,float)) else None,
            "same_date_comparison":None}
    if day in rows and isinstance(close,(int,float)) and math.isfinite(close) and close>0:
        ibkr=rows[day]["close_usd"]
        result["same_date_comparison"]={
            "date":day,"ibkr_close_usd":ibkr,"reference_close_usd":close,
            "difference_usd":round(ibkr-close,5),
            "difference_pct":round(100*(ibkr/close-1),4),
            "interpretation":"UNADJUSTED_TRADES_VS_OTHER_PROVIDER_MAY_DIFFER"
        }
    return result

def run_probe(timeout=20):
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
    except ImportError:
        return {"result":"IBAPI_NOT_INSTALLED","instruments":{}}

    reqids={901:"QQQ",902:"SMH"}
    class Reader(EWrapper,EClient):
        def __init__(self):
            EClient.__init__(self,self)
            self.ready=threading.Event()
            self.done={ticker:threading.Event() for ticker in SYMBOLS}
            self.bars={ticker:[] for ticker in SYMBOLS}
            self.issues=[]
            self.terminal=set()

        def nextValidId(self,orderId):
            self.ready.set()

        def historicalData(self,reqId,bar):
            ticker=reqids.get(reqId)
            if not ticker:return
            date=str(bar.date).strip()
            try:
                parsed=dt.datetime.strptime(date[:8],"%Y%m%d").date().isoformat()
                close=float(bar.close)
            except (ValueError,TypeError):
                return
            if math.isfinite(close) and close>0:
                self.bars[ticker].append({"date":parsed,"close_usd":round(close,5)})

        def historicalDataEnd(self,reqId,start,end):
            ticker=reqids.get(reqId)
            if ticker:self.done[ticker].set()

        def error(self,reqId,errorCode,errorString,*args):
            try: code=int(errorCode)
            except (ValueError,TypeError):return
            if code not in INFO_CODES:
                issue={"code":code,"request_id":int(reqId)}
                # Avoid writing account identifiers, detailed gateway text, or secrets.
                self.issues.append(issue)
            if reqId in reqids and code in TERMINAL_CODES:
                self.terminal.add(reqId)
                self.done[reqids[reqId]].set()

    app=Reader()
    result={"schema":1,"component":"ETF-Strategy-Lab 4.7",
            "mode":"LOCAL_IBKR_DEMO_READ_ONLY",
            "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "host":HOST,"port":PORT,"ibkr_source":"TRADES daily bars, RTH=1, 1 M",
            "connection_established":False,"handshake":False,
            "orders_sent":False,"account_data_requested":False,
            "auto_published":False,"instruments":{},"notices":[]}
    try:
        app.connect(HOST,PORT,clientId=CLIENT_ID)
        if not app.isConnected():
            result["status"]="TCP_CONNECTION_FAILED"
            return result
        result["connection_established"]=True
        threading.Thread(target=app.run,daemon=True).start()
        if not app.ready.wait(timeout):
            result["status"]="HANDSHAKE_TIMEOUT"
            return result
        result["handshake"]=True
        print("IBKR-Handshake: OK")
        # Only two historical requests, with a pacing pause, no subscriptions.
        for reqid,ticker in reqids.items():
            contract=Contract()
            contract.symbol=ticker
            contract.secType="STK"
            contract.exchange="SMART"
            contract.currency="USD"
            app.reqHistoricalData(reqid,contract,"","1 M","1 day",
                                  "TRADES",1,1,False,[])
            finished=app.done[ticker].wait(timeout)
            print(ticker,"Tagesbalken:",len(app.bars[ticker]),
                  "Abfrage beendet:",finished)
            if not finished:
                app.cancelHistoricalData(reqid)
        references,ref_error=reference_quotes()
        if ref_error:result["reference_warning"]=ref_error
        result["reference_source"]="PUBLIC_GITHUB_DELAYED_DAILY_QUOTES"
        result["instruments"]={
            ticker:compare(ticker,app.bars[ticker],references)
            for ticker in SYMBOLS}
        result["notices"]=app.issues
        if not all(app.done[s].is_set() for s in SYMBOLS):
            result["status"]="PARTIAL_TIMEOUT"
        elif any(k in app.terminal for k in reqids):
            result["status"]="PARTIAL_OR_UNAVAILABLE"
        elif not all(app.bars[s] for s in SYMBOLS):
            result["status"]="NO_HISTORICAL_BARS"
        else:
            result["status"]="BARS_RECEIVED"
        return result
    except Exception as exc:
        result["status"]="LOCAL_PROBE_FAILED"
        result["failure_type"]=type(exc).__name__
        return result
    finally:
        if app.isConnected():app.disconnect()

def main():
    import argparse
    parser=argparse.ArgumentParser(description="Local IBKR demo historical ETF comparison; no orders.")
    parser.add_argument("--timeout",type=int,default=20)
    args=parser.parse_args()
    if args.timeout<5 or args.timeout>60:
        parser.error("--timeout must be between 5 and 60")
    report=run_probe(args.timeout)
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",
                           encoding="utf-8")
    print("Status:",report.get("status",report.get("result")))
    for ticker,item in report.get("instruments",{}).items():
        same=item.get("same_date_comparison")
        print(ticker,"letzter IBKR-Schlusskurs:",item.get("last_ibkr_bar"),
              "Vergleich am gleichen Tag:",same or "nicht moeglich")
    print("Lokaler Bericht:",OUTPUT_FILE)
    print("KEINE Orders. KEIN Broker-Depotzugriff. KEIN GitHub-Upload.")
    return 0 if report.get("status")=="BARS_RECEIVED" else 1

if __name__=="__main__":
    raise SystemExit(main())
