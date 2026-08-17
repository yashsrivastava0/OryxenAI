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

    # Offline lockfile creation (npm install --package-lock-only --offline)
    # needs each package's registry metadata, which npm ci never stores.
    # Warm packuments for every scaffold dependency...
    $manifest = Get-Content "$scaffold\package.json" -Raw | ConvertFrom-Json
    foreach ($group in @($manifest.dependencies, $manifest.devDependencies)) {
        if ($null -eq $group) { continue }
        foreach ($property in $group.PSObject.Properties) {
            npm cache add "$($property.Name)@$($property.Value)" --cache $cache
            if ($LASTEXITCODE -ne 0) { throw "npm cache add failed for $($property.Name)." }
        }
    }
    # ...and for admission-bound packages (config/app.toml
    # [code_generator_dependencies.supported_packages]).
    foreach ($package in @("lucide-react@0.500.0", "motion@12.0.0")) {
        npm cache add $package --cache $cache
        if ($LASTEXITCODE -ne 0) { throw "npm cache add failed for $package." }
    }
    Write-Host "Offline npm cache warmed at $cache"
}
finally {
    Pop-Location
}
