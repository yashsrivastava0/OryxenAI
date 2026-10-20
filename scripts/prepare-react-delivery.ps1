[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$taskRepoRoot = Resolve-Path "$PSScriptRoot\.."
Push-Location (Join-Path $taskRepoRoot "react-delivery")
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm ci --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "React delivery dependency installation failed." }
    }
    npm run build:viewer
    if ($LASTEXITCODE -ne 0) { throw "React delivery template build failed." }
} finally { Pop-Location }
Push-Location (Join-Path $taskRepoRoot "plugins/oryxenai-react-handoff")
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm ci --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "MCP importer dependency installation failed." }
    }
    node --test scripts/import-project.test.mjs
    if ($LASTEXITCODE -ne 0) { throw "MCP importer checks failed." }
} finally { Pop-Location }
