[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

uv run ruff check
uv run ruff format --check
uv run mypy src

$FRONTEND_ROOT = Join-Path $REPO_ROOT "frontend"
Push-Location $FRONTEND_ROOT
try {
    npm run typecheck
    npm test
    npm run build
} finally {
    Pop-Location
}
