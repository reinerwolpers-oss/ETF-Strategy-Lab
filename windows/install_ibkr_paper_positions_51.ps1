# Install read-only IBKR Paper positions Windows task. Local, no broker orders.
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'IBKR-Test'
$python = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$positionScript = Join-Path $root 'ibkr_paper_positions_readonly.py'
$runner = Join-Path $root 'run_ibkr_paper_positions_51.py'
$taskName = 'ETF-IBKR-Paper-Positions-Readonly-51'
$baseUrl = 'https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/scripts/'
if (-not (Test-Path $python)) { throw "Python-Umgebung nicht gefunden: $python" }
if (-not (Test-Path $pythonw)) { throw "Python ohne Konsolenfenster nicht gefunden: $pythonw" }
if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root | Out-Null }
Invoke-WebRequest -Uri ($baseUrl + 'ibkr_paper_positions_readonly.py') -OutFile $positionScript
Invoke-WebRequest -Uri ($baseUrl + 'run_ibkr_paper_positions_51.py') -OutFile $runner
& $python -m py_compile $positionScript $runner
if ($LASTEXITCODE -ne 0) { throw 'Python-Syntaxpruefung fehlgeschlagen' }
# Windows task executes Python directly, no PowerShell script after installation.
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $runner + '"')
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '20:35'
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -WakeToRun:$false -StartWhenAvailable:$false
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Nur lesende IBKR-Paper-Positionspruefung; keine Brokerorders' -Force | Out-Null
Write-Host "Eingerichtet: $taskName, Montag-Freitag 20:35 Uhr (nur bei laufender TWS und Windows-Anmeldung)." -ForegroundColor Green
Write-Host "Lokale Ausgabe: $root\ibkr-paper-positions-51.log"
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object NextRunTime
