[CmdletBinding()]
param(
    [string]$Suite = "all"
)

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

switch ($Suite) {
    "integration" {
        $env:OryxenAI_CONFIG_OVERLAY = "config/app.test.toml"
        $pytestArgs = @("-m", "integration or strict_integration or worker")
    }
    "worker" {
        $env:OryxenAI_CONFIG_OVERLAY = "config/app.test.toml"
        $pytestArgs = @("-m", "worker")
    }
    "unit" {
        $pytestArgs = @("-m", "not (integration or strict_integration or worker)")
    }
    default {
        $pytestArgs = @()
    }
}

if ($env:PYTEST_PROFILE) { $pytestArgs += "--profile" }

if ($Suite -ne "worker") { & "$PSScriptRoot\prepare-react-delivery.ps1" }

uv run pytest @pytestArgs @args
