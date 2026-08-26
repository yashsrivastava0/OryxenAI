[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("align-db", "migrate", "api", "worker", "preview", "dev", "doctor")]
    [string]$Service
)

$ErrorActionPreference = "Stop"

$REPO_ROOT = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $REPO_ROOT

$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:UV_CACHE_DIR = "$REPO_ROOT\.workspace\cache\uv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"
$env:OryxenAI_CONFIG_OVERLAY = "config/app.native.toml"

New-Item -ItemType Directory -Force -Path "$REPO_ROOT\.workspace\cache\python" | Out-Null

switch ($Service) {
    "align-db" {
        uv run python "$PSScriptRoot\align_native_postgres.py"
    }
    "migrate" {
        uv run alembic upgrade head
    }
    "api" {
        $values = @(uv run python -c "from oryxenai.core.settings import get_settings; s=get_settings(); print(s.app.host); print(s.app.port)" | Where-Object { $_ })
        if ($LASTEXITCODE -ne 0 -or $values.Count -lt 2) {
            throw "Could not read the native app host and port from settings."
        }
        uv run uvicorn oryxenai.main:app --host $values[0] --port $values[1] --reload
    }
    "worker" {
        uv run python -m oryxenai.jobs.worker
    }
    "preview" {
        uv run python -m oryxenai.preview.gateway
    }
    "dev" {
        foreach ($childService in @("api", "worker", "preview")) {
            Start-Process powershell.exe `
                -WindowStyle Hidden `
                -WorkingDirectory $REPO_ROOT `
                -ArgumentList @(
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "`"$PSCommandPath`"",
                    $childService
                ) | Out-Null
        }
    }
    "doctor" {
        & "$PSScriptRoot\doctor.ps1"
    }
}
