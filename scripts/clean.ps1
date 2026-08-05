[CmdletBinding()]
param(
    [switch]$Full
)

$REPO_ROOT = Resolve-Path "$PSScriptRoot\.."

$workspace = "$REPO_ROOT\.workspace"
@("$workspace\cache", "$workspace\tmp", "$workspace\reports") | ForEach-Object {
    if (Test-Path $_) { Remove-Item -Recurse -Force $_ }
}

@(".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__") | ForEach-Object {
    $path = "$REPO_ROOT\$_"
    if (Test-Path $path) { Remove-Item -Recurse -Force $path }
}

if ($Full) {
    $venv = "$workspace\venv"
    if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
}
