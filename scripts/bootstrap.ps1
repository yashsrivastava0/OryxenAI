[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."

$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

New-Item -ItemType Directory -Force -Path "$REPO_ROOT\.workspace\venv" | Out-Null
New-Item -ItemType Directory -Force -Path "$REPO_ROOT\.workspace\cache\python" | Out-Null

uv sync --frozen
