[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $REPO_ROOT

$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:UV_CACHE_DIR = "$REPO_ROOT\.workspace\cache\uv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

New-Item -ItemType Directory -Force -Path "$REPO_ROOT\.workspace\cache\uv" | Out-Null
New-Item -ItemType Directory -Force -Path "$REPO_ROOT\.workspace\cache\python" | Out-Null

uv run python -m oryxenai.jobs.worker
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
