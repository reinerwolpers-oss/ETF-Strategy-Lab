# ETF-Saison-Bot 4.8 · Automatischer lokaler IBKR-Demo-Kursmonitor

Version 4.8 ist im GitHub-Repository vorbereitet. **Der Windows-Task kann nicht von GitHub aus auf deinem privaten PC registriert werden.** Dafür ist der einmalige untenstehende PowerShell-Befehl auf deinem Windows-PC nötig.

## Funktion
- Nutzt deine laufende **TWS-Demo**, `127.0.0.1:7497`, mit aktivierter **Schreibgeschützter API**.
- Fragt historische QQQ- und SMH-Tagesbalken über `reqHistoricalData` ab (TRADES, 1 day, RTH, letzter Monat).
- Lädt einen öffentlich zugänglichen GitHub-Kurs-Snapshot nur zum Vergleich herunter, ohne hochzuladen.
- Vergleicht ausschließlich Kurse vom **gleichen Handelstag**.
- Markiert Kursabweichungen **ab 1 %**, fehlende Vergleichstage und Datensätze, die **mehr als fünf Kalendertage** alt sind. Feiertage und Zeitzonen können zusätzliche Hinweise auslösen.
- Schreibt `ibkr-monitor-status.json`, `ibkr-monitor-report.html` und `ibkr-monitor.log` in dein lokales `IBKR-Test`-Verzeichnis.
- Legt einen Windows-Task an, der **Montag bis Freitag 20:30 Uhr lokale Windows-Zeit** prüft, **nur während du bei Windows angemeldet bist**. Verwendet `pythonw.exe`, daher kein aufpoppendes CMD-Fenster.
- Hat **keine Order-, Konto- oder Positionsabfragen**, keine GitHub-Daten-Uploads und keine automatische IBKR-Kursübernahme in den Paper-Bot.
- Wenn TWS nicht läuft oder Demo keinen Zugriff erlaubt, wird ein Hinweis im lokalen Bericht/Log erzeugt; es gibt keine Ersatz- oder erfundenen Kurse.
- Warnungen stehen **im lokalen Bericht und Log**, nicht als iPhone-ntfy-Push. Die bestehende ntfy-Benachrichtigung des unabhängigen Paper-Bots bleibt unverändert.

Hinweis: Um 20:30 Uhr ist der US-Börsentag oft noch nicht abgeschlossen. Der Vergleich verwendet nur bereits vorliegende Tagesbalken und darf nicht als endgültiger Schlusskurs des laufenden US-Handelstags interpretiert werden. Die TWS-Demo muss angemeldet und erreichbar sein; der Zeitplan weckt den PC nicht auf.

## Bereits installierten Zeitplan ändern

```powershell
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "20:30"
Set-ScheduledTask -TaskName "ETF-IBKR-Demo-Readonly-Monitor-48" -Trigger $trigger
Get-ScheduledTaskInfo -TaskName "ETF-IBKR-Demo-Readonly-Monitor-48" | Select-Object NextRunTime
```

## Einmalig auf Windows installieren

TWS im **DEMO SYSTEM** offen lassen und in TWS `Global Configuration → API → Settings` verifizieren: **Socket-Clients an**, **Schreibgeschützte API an**, nur lokale Verbindungen, Port `7497`.

Diese Befehle in PowerShell eingeben:

```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/windows/install_ibkr_monitor_48.ps1" -OutFile "$HOME\IBKR-Test\install_ibkr_monitor_48.ps1"
& "$HOME\IBKR-Test\install_ibkr_monitor_48.ps1"
```

Das Skript lädt zwei Python-Dateien von diesem Repository herunter, prüft Python 3.12 mit `ibapi` und registriert den geplanten Task `ETF-IBKR-Demo-Readonly-Monitor-48` im eigenen Windows-Konto. Vor dem Ausführen kann der Quelltext im GitHub-Repository geprüft werden.

## Sofortiger Funktionstest

```powershell
& "$HOME\IBKR-Test\.venv\Scripts\python.exe" "$HOME\IBKR-Test\ibkr_local_monitor.py"
Invoke-Item "$HOME\IBKR-Test\ibkr-monitor-report.html"
```

Für Details: `Get-Content "$HOME\IBKR-Test\ibkr-monitor.log" -Tail 15`

## Task kontrollieren oder entfernen

```powershell
Get-ScheduledTask -TaskName "ETF-IBKR-Demo-Readonly-Monitor-48"
```

Bei Bedarf wieder entfernen:

```powershell
Unregister-ScheduledTask -TaskName "ETF-IBKR-Demo-Readonly-Monitor-48" -Confirm:$false
```

Die Datei `config/paper-settings.json` bleibt `PAPER_ONLY` mit `broker_connection=false`, `live_orders=false`. GitHub Actions prüft nur Quellcode und Offline-Sicherheitstests; es kann den lokalen TWS-Datenabruf nicht bestätigen.
