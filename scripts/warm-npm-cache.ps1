[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

# One-time trusted setup: populate the offline npm cache the Code Generator's
# offline installs read from. Generation itself never touches the network.
$scaffold = "$REPO_ROOT\src\oryxenai\agents\code_generator\scaffolds\react-vite-v1"
$cache = "$REPO_ROOT\.workspace\npm-cache"
New-Item -ItemType Directory -Force -Path $cache | Out-Null

Push-Location $scaffold
try {
    npm ci --cache $cache --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed while warming the offline cache." }
    Write-Host "Offline npm cache warmed at $cache"
}
finally {
    Pop-Location
}
