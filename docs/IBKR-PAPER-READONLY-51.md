# IBKR Paper-Konto: automatische lokale Nur-Lese-Prüfung 5.1

Der IBKR Paper-Modus wurde in TWS über ein einzelnes DU-Konto und eine erfolgreiche
schreibgeschützte Kontoabfrage bestätigt. **Das ist keine Freigabe für Orders.**

## Was automatisch läuft
- Separater Windows-Task `ETF-IBKR-Paper-Positions-Readonly-51`, werktags um 20:35 Ortszeit.
- Fragt nur bei lokal gestarteter und angemeldeter TWS auf `127.0.0.1:7497` an.
- Verlangt genau **eine** `DU`-Kontokennung, druckt jedoch niemals die Kontonummer.
- Liest die Positionen und schreibt eine ausschließlich **lokale** Protokolldatei
  `%USERPROFILE%\IBKR-Test\ibkr-paper-positions-51.log`.
- Keine Orders, keine Positionsänderung, kein Upload zu GitHub. Kontowerte werden
  nicht mit dem separaten 500-$-Forschungsdepot verrechnet.

## Einmalige Installation auf deinem Windows-PC
TWS im **Paper-Trading-Modus** geöffnet lassen, mit aktiviertem
`Schreibgeschützte API`, Port 7497. In PowerShell:

```powershell
$url = "https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/windows/install_ibkr_paper_positions_51.ps1"
Invoke-WebRequest -Uri $url -OutFile "$HOME\IBKR-Test\install_ibkr_paper_positions_51.ps1"
& "$HOME\IBKR-Test\install_ibkr_paper_positions_51.ps1"
```

Wenn die lokale Windows-Ausführungsrichtlinie das Skript blockiert, bitte nicht
pauschal die systemweiten Sicherheitsregeln ändern. Das Skript kann vor
Ausführung in einem Editor geprüft und gemäß der lokalen Richtlinie gestartet
werden.

## Test und Überprüfung

```powershell
Start-ScheduledTask -TaskName "ETF-IBKR-Paper-Positions-Readonly-51"
Get-ScheduledTaskInfo -TaskName "ETF-IBKR-Paper-Positions-Readonly-51" | Select-Object LastRunTime,LastTaskResult,NextRunTime
Get-Content "$HOME\IBKR-Test\ibkr-paper-positions-51.log" -Tail 15
```

Der Task läuft **nicht**, wenn der PC aus ist, im Standby schläft, Windows
abgemeldet ist oder TWS nicht angemeldet ist.

## Vorbereitung von Paper-Orders, ausdrücklich noch NICHT aktiviert

Für spätere autorisierte Testorders müsste eine separate Testumgebung mit
nachweislichem DU-Konto, harten Stückzahl- und Kapitalgrenzen, gesperrten
Live-Accounts, expliziter Freigabe und eindeutigem Not-Stopp gebaut und
abgenommen werden. Das bestehende 500-$-GitHub-Paper-Depot und die Vorwärts-
validierung bleiben unverändert. Die TWS-Option `Schreibgeschützte API`
bleibt eingeschaltet. Es wurde kein Programm zum Platzieren von Orders
installiert oder aktiviert.
