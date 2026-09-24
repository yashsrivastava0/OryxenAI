# OryxenAI development runbook

This is the canonical local startup guide. Choose one of the two supported
modes:

| Mode | FastAPI/UI | Durable worker | PostgreSQL | Best for |
| --- | --- | --- | --- | --- |
| Native | Local `uv` process | Local `uv` process | Local PostgreSQL on `5432` | Fast code changes without image rebuilds |
| Docker | Compose container | Compose container | Compose volume, host port `5544` | Production-like local integration |

Docker is intentionally retained. The native mode does not remove, replace,
or modify the Compose stack.

## What actually runs

FastAPI serves the authenticated product workspace and API. The active
workflow has two explicit stages: Discovery and Content Architect. One
PostgreSQL-backed worker executes their durable jobs. Approval is a separate
user action, and approving the content plan ends the current workflow.

The app and worker are separate processes. PostgreSQL stores sessions, current
state, run snapshots, and durable jobs. Historical output remains stored for
authorized cleanup and audit; current APIs project only supported state.

## One-time setup

Run commands from the repository root. Do not use a personal absolute path
from another machine.

### Required tools

- Python 3.13; the project requires >=3.13,<3.14.
- uv.
- PostgreSQL for native development and database-backed checks.
- Docker Desktop for Compose mode.
- Node.js/npm only when building or checking the product frontend.

The frontend uses the checked-in static bundle when serving the product.
npm dependencies are not needed to start the API or worker.

### Python environment

```powershell
uv python install 3.13
uv sync --frozen
```

Linux/macOS:

```bash
uv python install 3.13
uv sync --frozen
```

Repository scripts use `.workspace/venv` and `.workspace/cache`. Do not commit
those directories.

### Secrets and provider configuration

Create the local secret file only when it does not already exist:

    if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Linux/macOS:

    test -f .env || cp .env.example .env

Never overwrite an existing .env or inspect another device's secrets.
Set the local PostgreSQL password and only the model-provider credentials
needed for a live operation. Model profile names and credential-variable names
come from config/models.toml. The API and worker can start without model
credentials; a requested live call reports a safe configuration error if its
credential is missing.

## Option A — native development, no Docker

PostgreSQL, migrations, FastAPI, and the durable worker run natively. The
helper scripts use config/app.native.toml and the local PostgreSQL default on
127.0.0.1:5432.

### Create the local PostgreSQL role and database

Start the local PostgreSQL service using the operating system service manager.
Then connect as a PostgreSQL administrator:

```powershell
psql -U postgres -h 127.0.0.1 -p 5432
```

Run this once. If the role or database already exists, skip that creation
statement rather than dropping anything:

```sql
CREATE ROLE oryxen LOGIN;
\password oryxen
CREATE DATABASE oryxenai OWNER oryxen;
\q
```

Alternatively, use the repository's interactive alignment command. It reads
the application-role password from `.env`, prompts for the PostgreSQL
administrator password, and does not print either secret or put it in a
command argument:

```powershell
.\scripts\run-native.ps1 align-db
```

```bash
./scripts/run-native.sh align-db
```

Whether aligned manually or through the helper, the role password must match
`POSTGRES_PASSWORD` in `.env`.

Check connectivity:

```powershell
pg_isready -h 127.0.0.1 -p 5432 -U oryxen -d oryxenai
```

```bash
pg_isready -h 127.0.0.1 -p 5432 -U oryxen -d oryxenai
```

If local PostgreSQL listens on another port (common when a pre-existing
system-wide PostgreSQL service already owns `5432`), don't edit the
committed `config/app.native.toml` — add these two lines to your own
`.env` instead (already git-ignored, so the override stays machine-local
and applies automatically to every native script without re-exporting
anything per terminal):

```
DB_HOST_OVERRIDE=127.0.0.1
DB_PORT_OVERRIDE=5545
```

They take priority over the TOML `[database]` block wherever
`settings.database_url` is used. Leave both blank to use the plain default.

### Run native services on Windows

Run migrations once after PostgreSQL is available:

    .\scripts\run-native.ps1 migrate

Open separate PowerShell windows from the repository root:

    .\scripts\run-native.ps1 api
    .\scripts\run-native.ps1 worker

Run diagnostics in another window when needed:

    .\scripts\run-native.ps1 doctor

### Run native services on Linux/macOS

Make the shell helper executable once:

    chmod +x scripts/run-native.sh

Then run migrations and use separate terminals:

    ./scripts/run-native.sh migrate
    ./scripts/run-native.sh api
    ./scripts/run-native.sh worker

Run diagnostics with:

    ./scripts/run-native.sh doctor

### Verify native startup

These checks do not call a model:

    Invoke-RestMethod http://127.0.0.1:8000/health/live
    Invoke-RestMethod http://127.0.0.1:8000/health/ready
    Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/app
    uv run alembic current

Expected results:

- /health/live reports process liveness.
- /health/ready returns HTTP 200 when PostgreSQL is available.
- /app serves the configured product shell.
- alembic current reports the checked-in database revision.
- The worker remains running without configuration or database errors.

### Native change workflow

- API Python changes reload automatically in the API terminal.
- Worker changes require restarting the worker terminal.
- Prompt/config changes are read by the process executing the next operation;
  restart the worker when in doubt.
- Migration changes require running the native `migrate` command first.
- Ordinary native source edits do not require an image build or Compose restart.
- Stop a process with `Ctrl+C`. Do not start a second worker against the same
  database while diagnosing a slow job.

## Option B — Docker Compose development

Use this mode for the production-like local topology. Compose supplies
PostgreSQL, the migration job, the API, and the durable worker.

### Start the main stack

Create .env only if it is absent, ensure Docker Desktop is running, and run:

    docker info
    docker compose build migrate app worker
    docker compose up -d migrate app worker
    docker compose ps

The migration service must finish successfully before the API and worker
start. PostgreSQL is published on host port 5544; the app is on port 8000.

Verify it:

    Invoke-RestMethod http://127.0.0.1:8000/health/live
    Invoke-RestMethod http://127.0.0.1:8000/health/ready
    Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/app
    docker compose ps

The API and worker must be running, PostgreSQL must be healthy, and the
migration container must have exited successfully. For diagnostics, use
docker compose logs --tail 200 app worker migrate.

Rebuild after Python, prompt, configuration, migration, or dependency changes:

    docker compose build migrate app worker
    docker compose up -d migrate app worker

Changing .env requires recreating affected containers. A plain restart does
not copy source changes into an old image.

### Stop the main stack safely

    docker compose stop app worker postgres
    docker compose ps

docker compose down removes containers but preserves the named volume unless
-v is supplied. Do not use docker compose down -v, DROP DATABASE, or TRUNCATE
during ordinary development; those commands can remove user sessions and
historical work.

## Run the active workflow

1. Start Discovery, provide the requested information, review the brief, and
   approve it.
2. Explicitly start Content Architect from the approved Discovery snapshot.
3. Review, revise if needed, and approve the content plan.

Approval never silently starts another stage. The worker handles each durable
job, and model calls use the configured profile. Local liveness and readiness
checks do not call the model.

## Tests and checks

Fast checks that do not require a running database:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -m "not (integration or strict_integration or worker)"
```

The full suite requires PostgreSQL:

```powershell
uv run pytest
```

Use the native or Docker database consistently for integration and worker
tests. The test overlay targets the dedicated `oryxenai_test` database and
must not point at the application database.

## Troubleshooting

### `connection refused` or `/health/ready` is not ready

- Native: confirm PostgreSQL is running on `127.0.0.1:5432` (or your
  `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` if set — see the native setup
  section above), the `oryxen` role/database exist, and `POSTGRES_PASSWORD`
  matches.
- Docker: confirm `docker compose ps` shows PostgreSQL healthy; the host port
  is `5544`, while containers use internal port `5432`.
- Confirm migrations completed with `uv run alembic current` in native mode or
  `docker compose logs migrate` in Docker mode.

### The frontend loads but an authenticated route fails

Set the Supabase URL and browser-safe publishable key in `.env`, ensure the
configured local origin is registered with the Supabase project, and use the
Google authentication flow. Server-only Supabase credentials must never be
placed in browser code or returned in responses.

### A live agent reports a missing credential

Read the relevant profile’s `api_key_env` in `config/models.toml` and set only
that environment variable in `.env`. Restart the worker after changing
`.env`. Do not replace a requested live run with fixtures.

### The worker does not process jobs

Run exactly one worker against the same database and overlay as the API. Check
the worker terminal, `/health/ready`, and authenticated
`/api/v1/system/status`. A heartbeat proves process activity, not that a
particular agent job succeeded; inspect the job/run state too.

### A Docker change is not visible

Rebuild the affected services. Compose’s application image contains a copy of
the repository and does not automatically see host source changes:

```powershell
docker compose build migrate app worker
docker compose up -d migrate app worker
```

Use native mode when rapid source iteration is the priority.

### Switching between native and Docker shows different data

This is expected. Native PostgreSQL and the Docker named volume are separate
database stores. Do not point two workers at the same database accidentally.
Back up data with `pg_dump` before deliberately moving it between stores.
