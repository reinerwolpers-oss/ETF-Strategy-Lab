#!/usr/bin/env python3
"""ETF Strategy Lab 4.6: LOCAL read-only IBKR TWS demo probe.

Connects only to 127.0.0.1:7497, requests server time and contract details
for QQQ and SMH. Never connects to an account service, requests positions,
places/cancels orders, or writes any data to the public GitHub repository.
TWS must have "Read-Only API" enabled; use DEMO session only.
"""
import argparse
import datetime as dt
import json
import pathlib
import threading
import time

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 76
SYMBOLS = ("QQQ", "SMH")
OUTPUT_DIR = pathlib.Path.home() / "IBKR-Test"
OUTPUT_FILE = OUTPUT_DIR / "ibkr-demo-status.json"

def iso_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def safe_status(connected=False, handshake=False, server_time=None, contracts=None, errors=None):
    return {
        "schema": 1, "component": "ETF-Strategy-Lab 4.6",
        "mode": "LOCAL_IBKR_DEMO_READ_ONLY",
        "host": HOST, "port": PORT,
        "connection_established": bool(connected),
        "api_handshake": bool(handshake),
        "server_time_utc": server_time,
        "contract_details": contracts or {},
        "notices": errors or [],
        "checked_at_utc": iso_utc(),
        "broker_orders_enabled": False,
        "account_data_collected": False,
        "published_to_github": False,
    }

def run_probe(timeout):
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
    except ImportError:
        print("FEHLER: ibapi fehlt in dieser Python-Umgebung.")
        return safe_status(errors=["IBAPI_NOT_INSTALLED"])

    class Reader(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.ready = threading.Event()
            self.clock_ready = threading.Event()
            self.contract_ready = {s: threading.Event() for s in SYMBOLS}
            self.server_time = None
            self.contracts = {s: [] for s in SYMBOLS}
            self.notices = []
            self.next_id_seen = False

        def nextValidId(self, orderId):
            # Handshake callback only. Never submit an order.
            self.next_id_seen = True
            self.ready.set()

        def currentTime(self, value):
            self.server_time = dt.datetime.fromtimestamp(
                value, dt.timezone.utc).isoformat()
            self.clock_ready.set()

        def contractDetails(self, reqId, details):
            symbol = {801: "QQQ", 802: "SMH"}.get(reqId)
            if not symbol:
                return
            c = details.contract
            self.contracts[symbol].append({
                "symbol": c.symbol,
                "exchange": c.exchange,
                "primary_exchange": c.primaryExchange,
                "currency": c.currency,
                "con_id": c.conId,
                "long_name": details.longName,
            })

        def contractDetailsEnd(self, reqId):
            symbol = {801: "QQQ", 802: "SMH"}.get(reqId)
            if symbol:
                self.contract_ready[symbol].set()

        def error(self, reqId, errorCode, errorString, *args):
            # 2104/2106/2158 are common connectivity notices.
            self.notices.append({"code": int(errorCode), "request_id": int(reqId)})
            if errorCode not in (2104, 2106, 2158):
                print(f"IBKR Hinweis/Fehler {errorCode} (Anfrage {reqId}).")

        def connectionClosed(self):
            self.notices.append({"code": "CONNECTION_CLOSED"})

    app = Reader()
    print("Verbinde nur lokal mit TWS DEMO 127.0.0.1:7497.")
    print("WICHTIG: Schreibgeschuetzte API in TWS muss aktiv bleiben.")
    try:
        app.connect(HOST, PORT, clientId=CLIENT_ID)
        if not app.isConnected():
            return safe_status(errors=["TCP_CONNECT_FAILED"])
        worker = threading.Thread(target=app.run, daemon=True)
        worker.start()

        if not app.ready.wait(timeout):
            return safe_status(connected=True, errors=["API_HANDSHAKE_TIMEOUT"])
        print("API-Handshake: OK")
        app.reqCurrentTime()
        clock_ok = app.clock_ready.wait(timeout)
        print("Serverzeit:", app.server_time or "nicht erhalten")

        requests = ((801, "QQQ"), (802, "SMH"))
        for req_id, symbol in requests:
            c = Contract()
            c.symbol = symbol
            c.secType = "STK"  # US-listed ETFs are typically represented as STK
            c.exchange = "SMART"
            c.currency = "USD"
            app.reqContractDetails(req_id, c)
        for _, symbol in requests:
            app.contract_ready[symbol].wait(timeout)
            print(symbol, "Kontrakte:", len(app.contracts[symbol]))

        notes=list(app.notices)
        if not clock_ok:
            notes.append({"code":"SERVER_TIME_TIMEOUT"})
        for symbol in SYMBOLS:
            if not app.contract_ready[symbol].is_set():
                notes.append({"code":"CONTRACT_DETAILS_TIMEOUT","symbol":symbol})
        return safe_status(connected=True, handshake=True,
                           server_time=app.server_time, contracts=app.contracts,
                           errors=notes)
    except Exception as exc:
        print("IBKR-Verbindungsfehler:", type(exc).__name__)
        return safe_status(errors=[type(exc).__name__])
    finally:
        try:
            app.disconnect()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="IBKR Demo Read-Only Probe")
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()
    if not 2 <= args.timeout <= 45:
        parser.error("--timeout muss zwischen 2 und 45 Sekunden liegen")
    status = run_probe(args.timeout)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(status, indent=2, ensure_ascii=False)+"\n",
                           encoding="utf-8")
    print("Lokaler Bericht:", OUTPUT_FILE)
    print("HANDSHAKE:", "OK" if status["api_handshake"] else "FEHLGESCHLAGEN")
    print("KEINE Orders, KEINE Kontoabfrage, KEIN GitHub-Upload.")
    return 0 if status["api_handshake"] and status["server_time_utc"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
