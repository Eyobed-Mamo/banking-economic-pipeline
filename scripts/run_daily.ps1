$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install requirements first. See README.md.' }
$logDir = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ('etl-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
# Start-Process avoids treating Python's normal stderr logging as PowerShell errors.
$errorFile = $logFile + '.stderr'
$process = Start-Process -FilePath $pythonPath -ArgumentList '-m etl.pipeline' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errorFile -Wait -PassThru
if (Test-Path -LiteralPath $errorFile) { Get-Content -LiteralPath $errorFile | Add-Content -LiteralPath $logFile }
exit $process.ExitCode
