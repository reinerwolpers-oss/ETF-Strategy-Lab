# Read-only IBKR paper account audit, local scheduled task installation.
# This changes ONLY a dedicated Windows task; TWS must remain open.
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'IBKR-Test'
$python = Join-Path $root '.venv\Scripts\python.exe'
$target = Join-Path $root 'ibkr_paper_positions_readonly.py'
$taskName = 'ETF-IBKR-Paper-Positions-Readonly-51'
$url = 'https://raw.githubusercontent.com/reinerwolpers-oss/ETF-Strategy-Lab/main/scripts/ibkr_paper_positions_readonly.py'
if (-not (Test-Path $python)) { throw "Python-Umgebung nicht gefunden: $python" }
if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root | Out-Null }
Invoke-WebRequest -Uri $url -OutFile $target
& $python -m py_compile $target
if ($LASTEXITCODE -ne 0) { throw 'Python-Syntaxpruefung fehlgeschlagen' }
# A separate small launcher writes only on this local Windows machine.
$runner = Join-Path $root 'run_ibkr_paper_positions_51.ps1'
$log = Join-Path $root 'ibkr-paper-positions-51.log'
@'
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'IBKR-Test'
$python = Join-Path $root '.venv\Scripts\python.exe'
$script = Join-Path $root 'ibkr_paper_positions_readonly.py'
$log = Join-Path $root 'ibkr-paper-positions-51.log'
"=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File $log -Append -Encoding utf8
& $python $script 2>&1 | Out-File $log -Append -Encoding utf8
'@ | Set-Content -Path $runner -Encoding UTF8
# Runs only while the user is logged in. No wake trigger.
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $runner + '"')
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '20:35'
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3) -WakeToRun:$false -StartWhenAvailable:$false
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Nur lesende IBKR-Paper-Positionspruefung; keine Brokerorders' -Force | Out-Null
Write-Host "Eingerichtet: $taskName, Montag-Freitag 20:35 Uhr (nur bei laufender TWS und Windows-Anmeldung)." -ForegroundColor Green
Write-Host "Lokale Ausgabe: $log"
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object NextRunTime
