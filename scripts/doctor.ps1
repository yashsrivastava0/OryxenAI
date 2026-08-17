[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$doctorFailed = $false

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

uv run python "$PSScriptRoot\verify_environment.py"
if ($LASTEXITCODE -ne 0) { $doctorFailed = $true }

Write-Host ""

uv run python -c @"
from oryxenai.jobs.worker import Worker; print('Worker module import: OK')
"@
if ($LASTEXITCODE -ne 0) { $doctorFailed = $true }

uv run python -c @"
from oryxenai.db.models.background_job import BackgroundJob; print('Jobs model import: OK')
"@
if ($LASTEXITCODE -ne 0) { $doctorFailed = $true }

$workspaceDir = "$REPO_ROOT\.workspace"
if (Test-Path $workspaceDir) {
    try {
        $testFile = "$workspaceDir\.doctor_test"
        Set-Content -Path $testFile -Value "doctor" -ErrorAction Stop
        Remove-Item -Force $testFile
        Write-Host ".workspace is writable: OK"
    } catch {
        Write-Host ".workspace is writable: NO"
        $doctorFailed = $true
    }
} else {
    Write-Host ".workspace exists: NO"
    $doctorFailed = $true
}

if ($doctorFailed) {
    Write-Error "Doctor found one or more failed environment checks."
    exit 1
}
