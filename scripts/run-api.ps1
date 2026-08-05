[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."
$env:UV_PROJECT_ENVIRONMENT = "$REPO_ROOT\.workspace\venv"
$env:PYTHONPYCACHEPREFIX = "$REPO_ROOT\.workspace\cache\python"

$vals = uv run python -c "from oryxenai.core.settings import get_settings; s=get_settings(); print(s.app.host); print(s.app.port)"
$hostAddr, $port = $vals -split "\s+" | Where-Object { $_ }

uv run uvicorn oryxenai.main:app --host $hostAddr --port $port
