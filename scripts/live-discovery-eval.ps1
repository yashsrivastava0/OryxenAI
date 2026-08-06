# Live Discovery provider evaluation runner (Section 27 / 7.3).
#
# Opt-in: requires a valid OPENCODE_GO_API_KEY in .env and RUN_LIVE_DISCOVERY=1.
# Runs a bounded synthetic corpus against the real endpoint for both the
# thinking-disabled and thinking-enabled profiles, and writes sanitized
# summaries to reports/live-discovery/.
#
# Usage: powershell -File scripts/live-discovery-eval.ps1

$ErrorActionPreference = "Stop"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $REPO_ROOT

$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:RUN_LIVE_DISCOVERY = "1"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\pyc"

uv run python -m oryxenai.live_eval "$@"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Live Discovery evaluation failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Output "Live Discovery evaluation complete."
