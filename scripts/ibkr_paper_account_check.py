#!/usr/bin/env python3
"""Local-only read-only identification of TWS-managed paper account(s).

Only prints masked account identifiers and count; never writes account IDs,
sends orders, requests balances, or uploads data.
"""
import threading
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

HOST="127.0.0.1"
PORT=7497
CLIENT_ID=79

class AccountChecker(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self,self)
        self.ready=threading.Event()
        self.accounts_received=threading.Event()
        self.accounts=[]
        self.errors=[]
    def nextValidId(self,orderId):
        self.ready.set()
    def managedAccounts(self,accountsList):
        self.accounts=[x.strip() for x in accountsList.split(",") if x.strip()]
        self.accounts_received.set()
    def error(self,reqId,errorCode,errorString,*args):
        if errorCode not in (2104,2106,2158):
            self.errors.append(int(errorCode))

def main():
    app=AccountChecker()
    try:
        app.connect(HOST,PORT,clientId=CLIENT_ID)
        if not app.isConnected():
            print("FEHLER: API-Port nicht erreichbar.")
            return 1
        threading.Thread(target=app.run,daemon=True).start()
        if not app.ready.wait(12):
            print("FEHLER: API-Handshake Timeout")
            return 2
        app.reqManagedAccts()
        if not app.accounts_received.wait(12):
            print("FEHLER: Keine Kontoliste erhalten, Codes:",app.errors)
            return 3
        print("API-Handshake: OK")
        print("Anzahl zugeordneter Konten:",len(app.accounts))
        for acct in app.accounts:
            kind="PAPER-KONTO (DU...)" if acct.startswith("DU") else "NICHT ALS PAPER ERKANNT"
            print("Konto:",kind,"| ID: [VERDECKT]")
        if not app.accounts:
            print("FEHLER: Keine verwalteten Konten gemeldet.")
            return 4
        if any(not account.startswith("DU") for account in app.accounts):
            print("STOPP: Ein Konto ist kein eindeutig erkennbares DU-Paper-Konto.")
            return 5
        print("SICHERHEIT: Nur Konto-Kennung erkannt; keine Guthaben, Positionen oder Orders angefragt.")
        return 0
    finally:
        app.disconnect()

if __name__=="__main__":
    raise SystemExit(main())
