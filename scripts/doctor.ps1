[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

uv run python "$PSScriptRoot\verify_environment.py"

Write-Host ""

uv run python -c @"
from oryxenai.jobs.worker import Worker; print('Worker module import: OK')
"@

uv run python -c @"
from oryxenai.db.models.background_job import BackgroundJob; print('Jobs model import: OK')
"@

$workspaceDir = "$REPO_ROOT\.workspace"
if (Test-Path $workspaceDir) {
    try {
        $testFile = "$workspaceDir\.doctor_test"
        Set-Content -Path $testFile -Value "doctor" -ErrorAction Stop
        Remove-Item -Force $testFile
        Write-Host ".workspace is writable: OK"
    } catch {
        Write-Host ".workspace is writable: NO"
    }
} else {
    Write-Host ".workspace exists: NO"
}
