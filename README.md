# OryxenAI

OryxenAI is a portfolio-planning product with two active, explicit stages:
Discovery and Content Architect. The active workflow ends after the user
approves the content plan. The product does not currently create or serve a
finished portfolio site.

> AI coding tools should read AGENTS.md first. It is the canonical current
> project context. See docs/project-status.md for release and acceptance
> status, CHANGES.md for append-only change history, and DECISIONS.md for
> recorded architectural decisions.

## Current purpose

Capture a user's intent, produce a reviewed Discovery brief, then produce a
reviewed Content Architect plan. Starting either stage is an explicit API
action; approval does not automatically start another stage.

## Architecture summary

- Backend: FastAPI, Pydantic, SQLAlchemy async, and Alembic.
- Database: PostgreSQL, with JSONB for session state and job payloads.
- Product frontend: Preact, TypeScript, and Vite, served by FastAPI.
- Durable work: PostgreSQL-backed jobs executed by a separate worker.
- Model access: provider-neutral ModelClient with profiles in
  config/models.toml.
- Configuration: secrets in .env; non-secret settings in config/.
- Docker: app, migration, worker, PostgreSQL, and HTTPS reverse proxy.

## Repository map

    src/oryxenai/
      main.py
      agents/discovery/
      agents/content_architect/
      agents/shared/
      api/routes/
      auth/
      db/
      jobs/
      web/
    frontend/
    config/
    migrations/
    scripts/
    tests/
    docs/

## Prerequisites

- Python 3.13 and uv.
- PostgreSQL for native development and database-backed tests.
- Docker Desktop for Compose mode.
- Node.js/npm only when building or checking the product frontend.

For startup, credentials, and troubleshooting, use the development runbook at
docs/run/run.md. The remaining setup sections here are a quick reference.

## Environment setup

### Secrets (`.env`)

The root `.env` contains **secrets only** — database password and optional API keys.
Create it from `.env.example` only if it does not already exist, then fill in
the values needed on this machine:

```powershell
PS > if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env: set POSTGRES_PASSWORD (and optionally API keys)
```

Non-secret configuration (app name, host, port, DB host/port, model profiles) lives in
committed files under `config/`:

- `config/app.toml` — `[app]` and `[database]` settings
- `config/models.toml` — provider-neutral model profiles and logical engine
  routing (see `[routing.engine_profiles]` and `[profiles.*]`)

## Windows PowerShell setup

    uv python install 3.13
    uv sync --frozen
    .\scripts\run-native.ps1 align-db
    .\scripts\run-native.ps1 migrate
    .\scripts\run-native.ps1 dev

The native development command starts the API and worker. Open
http://127.0.0.1:8000/app and follow the configured authentication mode.
For separate terminals, run run-native.ps1 api and run-native.ps1 worker.

## Linux/macOS setup

    uv python install 3.13
    uv sync --frozen
    chmod +x scripts/run-native.sh
    ./scripts/run-native.sh align-db
    ./scripts/run-native.sh migrate
    ./scripts/run-native.sh dev

The native development command starts the API and worker. Open
http://127.0.0.1:8000/app and follow the configured authentication mode.
For separate terminals, run run-native.sh api and run-native.sh worker.

## Direct local startup

Use scripts/run-native.ps1 or scripts/run-native.sh so the API and worker
load the same configuration overlay. The full PostgreSQL setup and service
details are in docs/run/run.md.

## Docker Compose startup

    docker compose up --build -d
    docker compose ps

The stack starts PostgreSQL, runs migrations once, then starts the API and
durable worker. The app is available on port 8000; PostgreSQL is published
on host port 5544. See docs/run/run.md for configuration and safe shutdown.
## Migration commands

```powershell
# Apply migrations
uv run alembic upgrade head

# Create a new migration (after modifying models)
uv run alembic revision --autogenerate -m "Description"

# Downgrade one revision
uv run alembic downgrade -1

# Inspect current revision
uv run alembic current

# Inspect migration history
uv run alembic history --verbose
```

## Test commands

```powershell
# All tests (requires PostgreSQL for integration tests)
uv run pytest

# Unit tests only (fast, no DB)
uv run pytest tests/unit

# API tests
uv run pytest tests/api

# Integration tests (require PostgreSQL)
uv run pytest tests/integration

# Verbose
uv run pytest -v
```

## Lint, format, and type-check commands

```powershell
uv run ruff check .           # lint
uv run ruff check --fix .     # lint + autofix
uv run ruff format .           # format
uv run ruff format --check .  # format check (CI)
uv run mypy src                # type check
```

## Product and API routes

The product workspace is served at http://127.0.0.1:8000/app after sign-in
when authentication is enabled. The API schema is available at /docs in
development.

| Method | Path | Description |
|--------|------|-------------|
| GET | /health/live | Process liveness |
| GET | /health/ready | Dependency readiness |
| GET | /api/v1/me | Resolve the authenticated local identity |
| PUT | /api/v1/me/username | Claim the onboarding username |
| GET | /api/v1/agents | List active registered agents |
| POST | /api/v1/sessions | Create an owned portfolio session |
| GET | /api/v1/sessions | List owned sessions |
| GET | /api/v1/sessions/{id} | Get session and projected current state |
| GET | /api/v1/sessions/{id}/runs | List active-workflow runs |
| POST | /api/v1/sessions/{id}/runs/mock | Run an administrator-only development mock |
| GET | /api/v1/sessions/{id}/discovery | Read Discovery state |
| POST | /api/v1/sessions/{id}/discovery/start | Store intake and enqueue Discovery |
| PUT | /api/v1/sessions/{id}/discovery/answers | Save answers and continue Discovery |
| POST | /api/v1/sessions/{id}/discovery/revise | Revise the Discovery brief |
| POST | /api/v1/sessions/{id}/discovery/approve | Approve the Discovery brief |
| GET | /api/v1/sessions/{id}/content-architect | Read Content Architect state |
| POST | /api/v1/sessions/{id}/content-architect/start | Start from approved Discovery |
| POST | /api/v1/sessions/{id}/content-architect/revise | Revise the content plan |
| POST | /api/v1/sessions/{id}/content-architect/approve | Approve the content plan |

Errors use a structured envelope containing a stable code, safe message, and
request ID. The route implementations and stage READMEs are the source of
truth when this table drifts.
## How mock agent runs work

1. The API validates the session and agent key.
2. The executor checks for an idempotent existing run (if a key was supplied).
3. A new `agent_runs` row is created with `state_before` (the session's current state).
4. The deterministic mock agent loads its checked-in `samples/output.json`, validates
   it against its response schema, and returns an `AgentResult`.
5. The output is merged into the session's `current_state` under
   `agents.<key>.{latestRunId, output}`.
6. The session's `revision` is incremented (optimistic update).
7. The run is marked `succeeded` with `output_payload` and `state_after`.
8. On any failure, the run is marked `failed` with a safe structured `error_payload`;
   the session state is not changed.

## How agent outputs and state are stored

- **Current aggregate state:** `portfolio_sessions.current_state` (JSONB) — the merged
  session state; Content Architect consumes only the approved Discovery snapshot.
- **Immutable run history:** `agent_runs` (append-oriented) — each run records input,
  `state_before`, output, `state_after`, status, error, timing, agent identity, and
  idempotency key.
- **Transaction:** The executor updates both tables inside a single transaction so a
  successful output and the updated session state cannot diverge.

Discovery stores its intake, answers, memory, and brief directly as JSONB on
`portfolio_sessions.current_state["discovery"]`. Its API and worker service use
optimistic session revisions so late model results are retained as stale history
instead of replacing newer user work. See `src/oryxenai/agents/discovery/README.md`
for the complete flow.

## How to add a future agent

1. Add a new member to `AgentKey` in `src/oryxenai/agents/shared/contracts.py`.
2. Create a directory under `src/oryxenai/agents/<new_agent>/` with:
   - `__init__.py`, `agent.py`, `schemas.py`, `README.md`
   - `prompts/system.md`, `prompts/task.md`
   - `samples/input.json`, `samples/output.json`
3. Implement `agent.py` conforming to the `Agent` protocol: `async def run(context) -> AgentResult`.
4. Register the agent in `default_registry()` in `src/oryxenai/agents/shared/registry.py`.
5. **Do not place test files inside the agent directory.** All tests live under `tests/`.

## Troubleshooting

### Database connection refused

- Verify PostgreSQL is running: `docker compose ps`
- Verify the port: the Docker container maps host **5544** → container **5432**
  (a non-default host port, to avoid conflicts with other local/Docker
  Postgres instances — see `compose.yaml`)
- Verify `POSTGRES_PASSWORD` is set in `.env` and matches the Docker container
- Check `config/app.toml` `[database] port` matches `compose.yaml`'s host port

### Port conflict (8000 or 5544)

- App port 8000: change `APP_PORT` in `config/app.toml` or `--port` flag
- DB port 5544: pick another free host port and update it in both
  `compose.yaml` (`ports:`) and `config/app.toml` (`[database] port`) —
  they must match

### Native mode: PostgreSQL port `5432` is already taken

This happens when another local PostgreSQL install (not this project's) is
already listening on `5432` — common on Windows when a system-wide
PostgreSQL service auto-starts. **Don't edit the committed
`config/app.native.toml`** (that changes the default for every native
developer). Instead, add these two lines to your own `.env` (already
git-ignored, so this stays machine-local):

```
DB_HOST_OVERRIDE=127.0.0.1
DB_PORT_OVERRIDE=5545
```

Set `DB_PORT_OVERRIDE` to whatever free port your own local PostgreSQL
instance actually listens on. These two settings take priority over
`config/app.native.toml`'s `[database]` block for every native script
(`align-db`, `migrate`, `api`, `worker`, `dev`) — no script or TOML edit
needed. Leave both blank/unset to use the plain default (`5432`).

### `.env` is accidentally missing

- The app will still start for unit/API tests that don't need PostgreSQL
- Integration tests will be skipped automatically
- For full functionality, copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`

### Model credentials are absent

- The app and worker still start without model credentials
- A real Discovery job fails safely with a controlled configuration error
- Normal tests use the deterministic fake client and require no model credential
- Set the environment variable named by the active profile's `api_key_env` for
  real model runs. The committed default is Anthropic; change routing/profile
  configuration to add or assign another provider without changing agents.

### Development UI is disabled

- Set `enable_dev_ui = true` in `config/app.toml` `[app]` section

### Postgres host port already in use

- The committed default host port (`compose.yaml` + `config/app.toml`
  `[database] port`) may collide with another project's Postgres container
  on a shared dev machine. Pick a free host port, update both files to
  match (container-internal port stays `5432`), and re-run
  `docker compose up postgres -d`.
