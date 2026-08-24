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

The main frontend is served by FastAPI. There is no separate frontend dev
server for the Discovery or authenticated product workspace.

The application process serves:

- `/` — Google/Supabase authentication shell
- `/app` — authenticated product workspace
- `/dev` — developer workspace when enabled
- `/dev/build-preparation-fixture` — detached Build Preparation UI
- `/dev/code-generator-development` — standalone Code Generator UI
- `/health/live` and `/health/ready` — process and database checks
- `/api/v1/*` — session, stage, job, and diagnostic APIs

One separate durable worker is required for queued Discovery, Content
Architect, Visual Design Director, Build Preparation, and Code Generator jobs.
The agents are not separate operating-system services; they are registered
handlers executed by PostgreSQL-backed jobs.

The preview gateway is optional for the main Discovery → Build Preparation
flow. Start it for the standalone Code Generator workflow.

## One-time setup

Run commands from the repository root. Do not use a personal absolute path
from another machine.

### Required tools

- Python `3.13` — the project requires `>=3.13,<3.14`.
- `uv`.
- PostgreSQL, with `psql` available on `PATH` for native mode.
- Docker Desktop only when using Docker mode.
- Node.js/npm when running Code Generator generation and verification.
- Chromium or the browser required by the configured verification profile for
  Code Generator verification.

The main FastAPI frontend uses checked-in static assets. npm dependencies are
not required merely to start the frontend or worker.

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

Create the local secret file once:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Linux/macOS:

```bash
test -f .env || cp .env.example .env
${EDITOR:-vi} .env
```

At minimum, set `POSTGRES_PASSWORD` to the password of the local `oryxen`
database role in native mode. Docker uses the same value to initialize its
PostgreSQL container.

Model profiles name their credential environment variables through
`api_key_env` in `config/models.toml`. Do not hardcode provider, model, or key
names in scripts or documentation. Inspect the configured names safely:

```powershell
Select-String -Path config/models.toml -Pattern 'api_key_env'
```

```bash
rg 'api_key_env' config/models.toml
```

Set the corresponding values in `.env` before starting a real model-backed
stage. The application and worker can boot without model credentials, but a
requested live operation fails clearly when its configured key is missing.

`.env.example` also documents optional credentials for Supabase, image
retrieval, and temporary artifact storage. Only fill credentials for the
workflow being run. Never print, commit, or paste secret values into this
runbook or terminal output.

## Option A — native development, no Docker

This is the fast iteration path. PostgreSQL, migrations, FastAPI, the worker,
and the optional preview gateway run natively. The helper scripts select
`config/app.native.toml`, which uses `127.0.0.1:5432` and enables developer
surfaces.

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

The password entered by `\password` must match `POSTGRES_PASSWORD` in `.env`.
Do not put the password in a command-line argument.

Check connectivity:

```powershell
pg_isready -h 127.0.0.1 -p 5432 -U oryxen -d oryxenai
```

```bash
pg_isready -h 127.0.0.1 -p 5432 -U oryxen -d oryxenai
```

If local PostgreSQL uses another port, change the native overlay or set the
same `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` values in every native terminal.

### Run native services on Windows

Run migrations once after PostgreSQL is available:

```powershell
.\scripts\run-native.ps1 migrate
```

Open separate PowerShell windows from the repository root:

```powershell
# Window 1 — FastAPI, frontend, and API; reloads Python changes.
.\scripts\run-native.ps1 api

# Window 2 — durable PostgreSQL worker; keep exactly one worker on this DB.
.\scripts\run-native.ps1 worker

# Window 3 — optional Code Generator preview gateway.
.\scripts\run-native.ps1 preview
```

Run diagnostics in another window when needed:

```powershell
.\scripts\run-native.ps1 doctor
```

### Run native services on Linux/macOS

Make the shell helper executable once:

```bash
chmod +x scripts/run-native.sh
```

Then run migrations and use separate terminals:

```bash
./scripts/run-native.sh migrate
./scripts/run-native.sh api
./scripts/run-native.sh worker
./scripts/run-native.sh preview
```

The preview command is optional. Run diagnostics with:

```bash
./scripts/run-native.sh doctor
```

### Verify native startup

These checks do not make a model call:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/
uv run alembic current
```

Expected results:

- `/health/live` returns `{"status":"alive"}`.
- `/health/ready` returns HTTP `200` with database `up`.
- `/` returns the authentication shell.
- `alembic current` reports the checked-in head without a hardcoded revision
  number in this document.
- The worker terminal continues without a database or configuration exception.

After authenticating as an administrator, `/dev` and developer APIs can be
used. Authenticated `/api/v1/system/status` reports the migration revision and
worker heartbeat. `/api/v1/agents` lists registered agent keys for an
onboarded user.

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
PostgreSQL, the migration job, FastAPI/UI, and the durable worker.

### Start the main stack

Create `.env`, ensure Docker Desktop is running, and run:

```powershell
docker info
docker compose build migrate app worker
docker compose up -d migrate app worker
docker compose ps
```

The migration service must complete successfully before the API and worker
start. The normal topology is:

```text
postgres (host 5544) → migrate → app (host 8000) + worker
```

Verify it:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/
docker compose ps
```

The app and worker containers must be running, PostgreSQL must be healthy,
and the migration container must have exited successfully. Use
`docker compose logs --tail 200 app worker migrate` for diagnostics.

The application image contains a copy of the repository. Rebuild after
Python, prompt, configuration, migration, or dependency changes:

```powershell
docker compose build migrate app worker
docker compose up -d migrate app worker
```

Changing `.env` also requires recreating affected containers so the new
environment is loaded. A plain restart does not copy changed source files into
an old image.

### Stop the main stack safely

```powershell
docker compose stop app worker postgres
docker compose ps
```

`docker compose down` removes containers but preserves the named volume unless
`-v` is supplied. Do not use `docker compose down -v`, `DROP DATABASE`, or
`TRUNCATE` during ordinary development; those commands can remove sessions,
jobs, and generated-work evidence.

### Docker Build Preparation validation

The detached validation service is not part of the default stack:

```powershell
# Deterministic fixture validation.
docker compose --profile build-validation run --rm build-validation

# Explicit live model/provider validation.
docker compose --profile build-validation run --rm build-validation --live-model --live-providers
```

The live form requires configured model, image-provider, and temporary
artifact credentials. It must fail visibly when a requested provider is not
available; it must not silently substitute fixture output.

## Running the agent pipeline

Use the authenticated product workspace at `http://127.0.0.1:8000/` and follow
the explicit stage order:

1. Complete Discovery and approve its brief.
2. Explicitly start Content Architect and approve its output.
3. Explicitly start Visual Design Director and approve its output.
4. Explicitly start Build Preparation and wait for its durable job.
5. Start Code Generator only when the Build Preparation handoff is eligible.

Approval does not automatically start the next stage. Each stage uses the
shared API/worker and the configured model profile. Startup checks do not call
the model; live calls happen only after the user starts a live operation.

For a detached Build Preparation run, use:

- `http://127.0.0.1:8000/dev/build-preparation-fixture`
- `http://127.0.0.1:8000/dev/build-preparation-fixture/progress`

The fixture page is diagnostic/development-only. Use the production session
route when testing the approved session pipeline.

## Standalone Code Generator development

### Native Code Generator

The native overlay enables the developer UI and uses local filesystem preview
storage. Start the native API, worker, and preview gateway, then open:

```text
http://127.0.0.1:8000/dev/code-generator-development
```

Before generating, check the page readiness result and run its provider
preflight. A real run also needs configured Code Generator credentials,
Node/npm, a valid Build Preparation pack or privacy-safe fixture, and the
configured browser.

### Isolated Docker Code Generator

The standalone Docker workflow uses a separate database and Compose project.
The checked-in overlay is `config/app.docker.codegen-run.toml`.

```powershell
$Project = "oryxenai-codegen"
$Overlay = "config/app.docker.codegen-run.toml"
$Workspace = (Resolve-Path (New-Item -ItemType Directory -Force .workspace)).Path

docker compose -p $Project --profile codegen build migrate app worker preview-gateway
docker compose -p $Project up -d postgres

$ready = $false
while (-not $ready) {
    docker compose -p $Project exec -T postgres pg_isready -U oryxen -d oryxenai *> $null
    $ready = $LASTEXITCODE -eq 0
    if (-not $ready) { Start-Sleep -Seconds 2 }
}

$dbExists = docker compose -p $Project exec -T postgres psql -U oryxen -d oryxenai -Atc `
    "SELECT 1 FROM pg_database WHERE datname = 'oryxenai_codegen_run';"
if (($dbExists | Out-String).Trim() -ne "1") {
    docker compose -p $Project exec -T postgres psql -U oryxen -d oryxenai -c `
        "CREATE DATABASE oryxenai_codegen_run;"
}

docker compose -p $Project run --rm --no-deps `
    -e OryxenAI_CONFIG_OVERLAY=$Overlay migrate

docker compose -p $Project run --rm -d --no-deps -p 8001:8000 `
    -v "${Workspace}:/app/.workspace" `
    -v "${PWD}/output:/app/output" `
    -e OryxenAI_CONFIG_OVERLAY=$Overlay `
    app uvicorn oryxenai.main:app --host 0.0.0.0 --port 8000

docker compose -p $Project run --rm -d --no-deps `
    -v "${Workspace}:/app/.workspace" `
    -e OryxenAI_CONFIG_OVERLAY=$Overlay `
    worker python -m oryxenai.jobs.worker

docker compose -p $Project --profile codegen run --rm -d --no-deps -p 4174:4174 `
    -v "${Workspace}:/app/.workspace" `
    -e OryxenAI_CONFIG_OVERLAY=$Overlay `
    preview-gateway python -m oryxenai.preview.gateway

docker compose -p $Project ps
```

Open `http://127.0.0.1:8001/dev/code-generator-development`. Generated sites
are exported under `output/code-gen-output`; preview objects are stored in
`.workspace/code-generator-preview`. Stop the isolated containers without
deleting evidence:

```powershell
docker compose -p $Project rm -f -s app worker preview-gateway
docker compose -p $Project stop postgres
```

Do not use `down -v` unless intentionally resetting this separate Code
Generator database and its volumes.

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

- Native: confirm PostgreSQL is running on `127.0.0.1:5432`, the `oryxen`
  role/database exist, and `POSTGRES_PASSWORD` matches.
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
