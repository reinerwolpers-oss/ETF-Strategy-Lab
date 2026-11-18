# IBKR-Demo-Datenverbindung 4.6 (lokal, schreibgeschützt)

## Was eingerichtet ist
- `scripts/ibkr_readonly_probe.py`: verbindet ausschließlich `127.0.0.1:7497` (TWS-Demo), fragt IBKR-Serverzeit und Vertragsdetails für QQQ und SMH ab und trennt die Verbindung wieder.
- `tests/test_ibkr_readonly.py`: offline Sicherheitsprüfungen, darunter Verbot von Order-, Konto- und Marktdaten-Abo-API-Aufrufen.
- `.github/workflows/ibkr-readonly-check.yml`: prüft automatisch Syntax, Offline-Tests und den unveränderten `PAPER_ONLY`-Modus. GitHub Actions **kann TWS auf dem privaten Windows-PC nicht erreichen**.
- Der Bot bleibt bei bisherigen externen Tageskursen; es ist **noch keine laufende IBKR-Kursversorgung oder GitHub-Integration** eingerichtet.

## Einmalige Ausführung auf Windows
Voraussetzung: TWS **DEMO SYSTEM**, API für Socketclients an, **Schreibgeschützte API an**, Port 7497, nur lokale Verbindungen. Bereits eingerichtete Python-3.12-Umgebung mit installiertem `ibapi`.

PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\IBKR-Test" | Out-Null
Invoke-WebRequest "https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/scripts/ibkr_readonly_probe.py" -OutFile "$HOME\IBKR-Test\ibkr_readonly_probe.py"
& "$HOME\IBKR-Test\.venv\Scripts\python.exe" "$HOME\IBKR-Test\ibkr_readonly_probe.py"
```

Keine Kennwörter/API-Schlüssel eingeben. Das Ergebnis steht in `$HOME\IBKR-Test\ibkr-demo-status.json`; es enthält nur Status, öffentliche Kontraktdaten und technische Fehlercodes. **Nicht automatisch auf GitHub hochladen**.

Erwartete Konsolenmeldung bei Erfolg: `HANDSHAKE: OK`, `Serverzeit: ...`, `QQQ Kontrakte: ...`, `SMH Kontrakte: ...`.

### Einschränkungen
- TWS-Demo ist kein freigeschaltetes IBKR-Paper-Konto; Demo-Symbole und Marktdaten können eingeschränkt sein.
- Grüne GitHub-Tests beweisen **nur**, dass der Offline-Sicherheitscheck erfolgreich ist. Sie bestätigen keine lokale Brokerverbindung.
- Ein erfolgreicher Handshake beweist noch keine Berechtigung für Echtzeit-Marktdaten.
- Keine Orderübermittlung und kein automatisiertes Live-Trading.
