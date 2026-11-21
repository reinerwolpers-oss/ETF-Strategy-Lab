#!/usr/bin/env python3
"""Local read-only positions summary for one verified IBKR DU paper account.

No live/paper orders; no account ID, prices, quantities, balances or positions
are uploaded, persisted, logged or sent over the network except to local TWS.
"""
import threading

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 81

def masked_symbol(value):
    # Limited output; never display account identifiers or sensitive contract text.
    return (value or "?").upper()[:20]

def main():
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
    except ImportError:
        print("FEHLER: ibapi fehlt.")
        return 1

    class Reader(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)
            self.handshake = threading.Event()
            self.accounts_ready = threading.Event()
            self.positions_ready = threading.Event()
            self.accounts = []
            self.positions = []
            self.codes = []

        def nextValidId(self, orderId):
            self.handshake.set()

        def managedAccounts(self, accountsList):
            self.accounts = [x.strip() for x in accountsList.split(",") if x.strip()]
            self.accounts_ready.set()

        def position(self, account, contract, position, avgCost):
            if account not in self.accounts or not account.startswith("DU"):
                return
            self.positions.append((masked_symbol(contract.symbol), str(position),
                                   str(contract.currency or ""), str(contract.secType or "")))

        def positionEnd(self):
            self.positions_ready.set()

        def error(self, reqId, errorCode, errorString, *args):
            if errorCode not in (2104, 2106, 2158):
                self.codes.append(int(errorCode))

    app = Reader()
    requested = False
    try:
        app.connect(HOST, PORT, clientId=CLIENT_ID)
        if not app.isConnected():
            print("FEHLER: TWS Paper API auf Port 7497 nicht erreichbar.")
            return 2
        threading.Thread(target=app.run, daemon=True).start()
        if not app.handshake.wait(12):
            print("FEHLER: Kein API-Handshake.")
            return 3
        app.reqManagedAccts()
        if not app.accounts_ready.wait(12):
            print("FEHLER: Kontoidentifikation nicht moeglich.")
            return 4
        if len(app.accounts) != 1 or not app.accounts[0].startswith("DU"):
            print("STOPP: Nicht genau ein bestaetigtes DU-Paper-Konto. Keine Positionsabfrage.")
            return 5
        app.reqPositions()
        requested = True
        if not app.positions_ready.wait(20):
            print("FEHLER: Positionsabfrage nicht vollstaendig. Fehlercodes:", sorted(set(app.codes)))
            return 6
        print("IBKR-PAPER-KONTO: bestaetigt; Kontonummer verborgen")
        if not app.positions:
            print("Offene Positionen: 0")
        else:
            print("Offene Positionen:", len(app.positions))
            for symbol, qty, currency, kind in sorted(app.positions):
                print("ETF/Wertpapier:", symbol, "| Typ:", kind, "| Stueck:", qty, "| Waehrung:", currency)
        print("NUR LESEN: Keine Orders, kein GitHub-Upload und keine Kontonummer gespeichert.")
        return 0
    except Exception as exc:
        print("FEHLER:", type(exc).__name__)
        return 7
    finally:
        if requested:
            try:
                app.cancelPositions()
            except Exception:
                pass
        try:
            app.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    raise SystemExit(main())
