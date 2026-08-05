#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export UV_PROJECT_ENVIRONMENT="$REPO_ROOT/.workspace/venv"
export PYTHONPYCACHEPREFIX="$REPO_ROOT/.workspace/cache/python"

mkdir -p "$REPO_ROOT/.workspace/venv"
mkdir -p "$REPO_ROOT/.workspace/cache/python"

uv sync --frozen
