#!/usr/bin/env python3
"""Read-only local IBKR PAPER account summary, no orders or persisted account data.

Requires TWS Paper Trading and Read-Only API on localhost:7497.
Prints only three selected summary values and never prints account identifiers.
"""
import threading

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 80
REQ_ID = 9801
TAGS = ("NetLiquidation", "TotalCashValue", "AvailableFunds")


def main():
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
    except ImportError:
        print("FEHLER: ibapi ist in dieser Python-Umgebung nicht installiert.")
        return 1

    class PaperReader(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.ready = threading.Event()
            self.managed_ready = threading.Event()
            self.summary_ready = threading.Event()
            self.managed = []
            self.summary = {}
            self.messages = []

        def nextValidId(self, orderId):
            # Handshake only, no calls to placeOrder.
            self.ready.set()

        def managedAccounts(self, accountsList):
            self.managed = [s.strip() for s in accountsList.split(",") if s.strip()]
            self.managed_ready.set()

        def accountSummary(self, reqId, account, tag, value, currency):
            # Never output or persist account. Reject unexpected identifiers.
            if reqId != REQ_ID or account not in self.managed or tag not in TAGS:
                return
            if currency == "BASE" or (tag, "BASE") not in self.summary:
                self.summary[(tag, currency)] = value

        def accountSummaryEnd(self, reqId):
            if reqId == REQ_ID:
                self.summary_ready.set()

        def error(self, reqId, errorCode, errorString, *args):
            if errorCode not in (2104, 2106, 2158):
                self.messages.append(str(errorCode))

    app = PaperReader()
    requested = False
    try:
        app.connect(HOST, PORT, clientId=CLIENT_ID)
        if not app.isConnected():
            print("FEHLER: TWS-API nicht erreichbar.")
            return 2
        threading.Thread(target=app.run, daemon=True).start()
        if not app.ready.wait(12):
            print("FEHLER: Kein API-Handshake.")
            return 3
        app.reqManagedAccts()
        if not app.managed_ready.wait(12):
            print("FEHLER: Kontoerkennung fehlgeschlagen.")
            return 4
        if len(app.managed) != 1 or not app.managed[0].startswith("DU"):
            print("STOPP: Keine eindeutig einzelne DU-Paper-Kennung. Keine Kontoabfrage.")
            return 5

        # Account-summary request: data only. Read-Only API must stay enabled.
        app.reqAccountSummary(REQ_ID, "All", ",".join(TAGS))
        requested = True
        if not app.summary_ready.wait(18):
            print("FEHLER: Kontozusammenfassung nicht vollständig empfangen.")
            if app.messages:
                print("IBKR-Fehlercodes:", ", ".join(sorted(set(app.messages))))
            return 6
        print("PAPER-KONTO (DU...): bestaetigt. Kontonummer verdeckt.")
        labels = {
            "NetLiquidation": "Virtueller Netto-Kontowert",
            "TotalCashValue": "Virtueller Kassenbestand",
            "AvailableFunds": "Verfuegbare virtuelle Mittel",
        }
        for tag in TAGS:
            # Prefer aggregate BASE amounts; only show a single alternative
            # currency when no BASE record exists. Never add currencies.
            base = [(currency, value) for (name, currency), value in app.summary.items()
                    if name == tag and currency == "BASE"]
            alternatives = [(currency, value) for (name, currency), value in app.summary.items()
                            if name == tag and currency != "BASE"]
            selected = base[0] if base else (alternatives[0] if len(alternatives) == 1 else None)
            if selected:
                currency, amount = selected
                print(f"{labels[tag]}: {amount} {currency}")
            else:
                print(f"{labels[tag]}: nicht eindeutig verfuegbar")
        print("NUR LESEN. Keine Orders, keine Positionsabfrage, kein Upload zu GitHub.")
        return 0
    except Exception as exc:
        print("FEHLER:", type(exc).__name__)
        return 7
    finally:
        if requested:
            try:
                app.cancelAccountSummary(REQ_ID)
            except Exception:
                pass
        try:
            app.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
