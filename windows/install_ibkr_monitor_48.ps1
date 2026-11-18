# ETF Strategy Lab 4.8 - Windows scheduled DEMO history monitor installer.
# Run once in your normal (non-admin) PowerShell session.
# Only local read-only API requests. NEVER any orders.
$ErrorActionPreference = "Stop"
$folder = Join-Path $HOME "IBKR-Test"
$python = Join-Path $folder ".venv\Scripts\python.exe"
$pythonw = Join-Path $folder ".venv\Scripts\pythonw.exe"
$taskName = "ETF-IBKR-Demo-Readonly-Monitor-48"

if (-not (Test-Path $python)) {
    throw "Python-3.12-Testumgebung fehlt: $python"
}
if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe fehlt: $pythonw"
}
# Confirm that the user's ibapi import works before installing the task.
& $python -c "from ibapi.client import EClient; from ibapi.wrapper import EWrapper"
if ($LASTEXITCODE -ne 0) { throw "IBKR Python API nicht korrekt installiert." }

New-Item -ItemType Directory -Force $folder | Out-Null
$base = "https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/scripts/"
foreach ($file in @("ibkr_historical_compare.py", "ibkr_local_monitor.py")) {
    Invoke-WebRequest ($base + $file) -OutFile (Join-Path $folder $file)
}
& $python -m py_compile (Join-Path $folder "ibkr_historical_compare.py") (Join-Path $folder "ibkr_local_monitor.py")
if ($LASTEXITCODE -ne 0) { throw "Syntaxprüfung fehlgeschlagen." }

# Task Scheduler supports direct pythonw execution: no CMD/PowerShell popup.
# TWS must ALREADY be running as Demo on the same logged-in user desktop.
$script = Join-Path $folder "ibkr_local_monitor.py"
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $script + '"') -WorkingDirectory $folder
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "23:45"
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Local IBKR TWS DEMO, read-only QQQ/SMH history check; no trades" -Force | Out-Null
Write-Host "ETF 4.8: Task registriert: $taskName" -ForegroundColor Green
Write-Host "Zeit: Montag-Freitag 23:45 lokale Windows-Zeit, nur wenn der Benutzer angemeldet ist."
Write-Host "TWS-Demo muss geöffnet und schreibgeschützt sein."
Write-Host "Lokaler Bericht: $folder\ibkr-monitor-report.html"
Write-Host "Lokales Protokoll: $folder\ibkr-monitor.log"
Write-Host "Für einen einmaligen Test bei geöffneter TWS-Demo ausführen:"
Write-Host '& "$HOME\IBKR-Test\.venv\Scripts\python.exe" "$HOME\IBKR-Test\ibkr_local_monitor.py"'
Write-Host "Kein GitHub-Upload, keine Brokerorders, kein Eingriff in das virtuelle Depot."
