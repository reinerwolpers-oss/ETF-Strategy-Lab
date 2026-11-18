# ETF-Saison-Bot 4.7: IBKR-Demo-Kursvergleich

Die GitHub-Dateien sind eingerichtet. **Der lokale Abruf historischer Kurse muss noch auf dem Windows-PC gestartet werden.**

## Sicherheit
- TWS **DEMO SYSTEM**, Socket-API auf `127.0.0.1:7497` und **Schreibgeschützte API** aktiviert.
- Je eine historische Tageskursabfrage für **QQQ** und **SMH**, Rückblick 1 Monat, Handelsdaten `TRADES`, reguläre US-Handelszeiten.
- Öffentlicher GitHub-Tageskurs-Snapshot wird nur zum Vergleich heruntergeladen.
- Ergebnis ausschließlich lokal unter `$HOME\IBKR-Test\ibkr-history-comparison.json`.
- Keine Orders, keine Konten oder Positionen, kein automatischer GitHub-Upload, keine Änderung des virtuellen 500-USD-Depots.
- Kein automatischer Hintergrunddienst und keine laufende IBKR-Kursversorgung des Bots.
- Nicht verfügbare Demo-Daten werden als nicht verfügbar ausgewiesen, niemals erfunden.

## Auf dem Windows-PC starten

TWS muss geöffnet bleiben. Die separate Python-3.12-Umgebung mit `ibapi` ist bereits eingerichtet.

Beide PowerShell-Zeilen ausführen:

```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/scripts/ibkr_historical_compare.py" -OutFile "$HOME\IBKR-Test\ibkr_historical_compare.py"
& "$HOME\IBKR-Test\.venv\Scripts\python.exe" "$HOME\IBKR-Test\ibkr_historical_compare.py"
```

## Auswertung
- `IBKR-Handshake: OK`: technische API-Verbindung erfolgreich.
- `QQQ Tagesbalken: N` und `SMH Tagesbalken: N`: tatsächlich erhaltene Tagesbalken.
- `Status: BARS_RECEIVED`: beide Instrumente lieferten historische Balken.
- `NO_HISTORICAL_BARS`, `PARTIAL_OR_UNAVAILABLE` oder `PARTIAL_TIMEOUT`: keine vollständige Datenbasis; Demo-Berechtigungen können eingeschränkt sein.
- Ein Vergleich wird **nur bei identischem Handelstag** durchgeführt. Andere Datenquellen, Handelszeiten und Kursbereinigung können Unterschiede erzeugen.
- Der Report bleibt auf deinem PC. Das öffentliche GitHub-Dashboard kann diese lokale Datei nicht unmittelbar abrufen.
