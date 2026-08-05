[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

uv run ruff check
uv run ruff format --check
uv run mypy src
