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
    # Build a disposable manifest that contains the scaffold plus every
    # configured, pinned package. A real install (not package-lock-only)
    # hydrates tarballs and transitive/platform dependencies into the cache.
    $manifest = Get-Content "$scaffold\package.json" -Raw | ConvertFrom-Json
    $warm = "$REPO_ROOT\.workspace\npm-cache-warm"
    if (Test-Path -LiteralPath $warm) {
        Remove-Item -LiteralPath $warm -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $warm | Out-Null
    Copy-Item -LiteralPath "$scaffold\package.json" -Destination "$warm\package.json"
    Copy-Item -LiteralPath "$scaffold\package-lock.json" -Destination "$warm\package-lock.json"

    # Keep package names/versions in TOML rather than copying a stale list into
    # an operational script. Add them to devDependencies so the generated
    # lockfile records the exact package graph without changing the scaffold.
    if ($null -eq $manifest.devDependencies) {
        $manifest | Add-Member -MemberType NoteProperty -Name devDependencies -Value ([pscustomobject]@{})
    }
    $configuredPackage = $null
    foreach ($line in Get-Content "$REPO_ROOT\config\app.toml") {
        if ($line -match '^\[code_generator_dependencies\.supported_packages\.([^\]]+)\]') {
            $configuredPackage = $Matches[1].Trim('"')
            continue
        }
        if ($null -ne $configuredPackage -and $line -match '^version_pin\s*=\s*"([^"]+)"') {
            $manifest.devDependencies | Add-Member -MemberType NoteProperty -Name $configuredPackage -Value $Matches[1] -Force
            $configuredPackage = $null
        }
    }
    $manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath "$warm\package.json" -Encoding utf8
    Push-Location $warm
    try {
        npm install --cache $cache --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "npm install failed while warming the offline cache." }
    }
    finally {
        Pop-Location
    }

    # A cache warm is useful only if a fresh workspace can consume it.  Keep
    # this proof separate from the warm install's node_modules tree.
    $proof = "$REPO_ROOT\.workspace\npm-cache-offline-proof"
    if (Test-Path -LiteralPath $proof) {
        Remove-Item -LiteralPath $proof -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $proof | Out-Null
    Copy-Item -LiteralPath "$warm\package.json" -Destination "$proof\package.json"
    Copy-Item -LiteralPath "$warm\package-lock.json" -Destination "$proof\package-lock.json"
    Push-Location $proof
    try {
        npm ci --cache $cache --ignore-scripts --offline --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "offline npm ci proof failed after warming the cache." }
    }
    finally {
        Pop-Location
        Remove-Item -LiteralPath $proof -Recurse -Force
        Remove-Item -LiteralPath $warm -Recurse -Force
    }
    Write-Host "Offline npm cache warmed at $cache"
}
finally {
    Pop-Location
}
