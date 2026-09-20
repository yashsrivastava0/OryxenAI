#!/bin/sh
# Application entrypoint: starts the application server.
# Migrations are run by a separate one-shot service in compose.production.yaml.
set -eu
echo "[entrypoint] Starting..."
exec "$@"
