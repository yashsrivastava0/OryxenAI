#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^(align-db|migrate|api|worker|preview|doctor)$ ]]; then
  echo "Usage: $0 {align-db|migrate|api|worker|preview|doctor}" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

export UV_PROJECT_ENVIRONMENT="$REPO_ROOT/.workspace/venv"
export UV_CACHE_DIR="$REPO_ROOT/.workspace/cache/uv"
export PYTHONPYCACHEPREFIX="$REPO_ROOT/.workspace/cache/python"
export OryxenAI_CONFIG_OVERLAY="config/app.native.toml"

mkdir -p "$REPO_ROOT/.workspace/cache/python"

case "$1" in
  align-db)
    exec uv run python scripts/align_native_postgres.py
    ;;
  migrate)
    exec uv run alembic upgrade head
    ;;
  api)
    APP_HOST="$(uv run python -c 'from oryxenai.core.settings import get_settings; print(get_settings().app.host)')"
    APP_PORT="$(uv run python -c 'from oryxenai.core.settings import get_settings; print(get_settings().app.port)')"
    if [[ -z "$APP_HOST" || -z "$APP_PORT" ]]; then
      echo "Could not read the native app host and port from settings." >&2
      exit 1
    fi
    exec uv run uvicorn oryxenai.main:app --host "$APP_HOST" --port "$APP_PORT" --reload
    ;;
  worker)
    exec uv run python -m oryxenai.jobs.worker
    ;;
  preview)
    exec uv run python -m oryxenai.preview.gateway
    ;;
  doctor)
    uv run python scripts/verify_environment.py
    exec uv run python scripts/verify_database.py
    ;;
esac
