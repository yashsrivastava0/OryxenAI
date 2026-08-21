# OryxenAI

Production-oriented OryxenAI backend and developer testing harness.

> **Discovery, Content Architect, Visual Design Director, and the hidden
> Portfolio Build Preparation stage are implemented end to end.** Code
> Generator remains intentionally out of scope for now. See
> [docs/architecture.md](docs/architecture.md) for design
> rationale and [docs/frontend-behavior-spec.md](docs/frontend-behavior-spec.md)
> for the chat/UX contract.

> **AI agents working on this repo:** start with
> [`AGENTS.md`](AGENTS.md), not this file — it's the canonical, current
> project context. See also [`CHANGES.md`](CHANGES.md) (change history) and
> [`DECISIONS.md`](DECISIONS.md) (decisions and open issues).

## Current purpose

Prove the staged pipeline works:

```
Application starts → PostgreSQL connects → approved Discovery/Content/Visual
snapshots → explicit Build Preparation start → durable immutable preparation
pack in temporary object storage
```

## Current non-goals

- Portfolio generation, code-generation sandbox, and downstream agent chaining
- Agent chaining, supervisor agent, LangChain/LangGraph, or any agent framework
- Queue/worker (Redis, Celery, Temporal, Kafka)
- Authentication, authorization, billing, Supabase, GitHub Actions generation,
  or published-portfolio hosting
- React frontend, visual editor, SEO, analytics, and published-portfolio hosting
- Vector database, embeddings, prompt-management platform, observability SaaS
- Multiple microservices, Kubernetes, Terraform

## Architecture summary

- **Backend:** FastAPI + Pydantic + SQLAlchemy async (asyncpg) + Alembic
- **Database:** PostgreSQL (JSONB for state and payloads)
- **Preparation artifacts:** private S3-compatible object storage (Cloudflare
  R2 by default); PostgreSQL stores metadata and hashes only
- **Frontend:** Jinja2 templates + vanilla JS/CSS (no framework, no CDN)
- **Agents:** Ordinary Python protocols + Pydantic models (no agent framework)
- **Model:** Provider-neutral `ModelClient` protocol with config-driven Anthropic Messages API defaults and extensible provider adapters
- **Config:** Secrets in `.env`; non-secret config in committed `config/app.toml` + `config/models.toml`
- **Docker:** One app image (API + testing UI) + one PostgreSQL container

## Folder structure

```
OryxenAI/
├── src/oryxenai/
│   ├── main.py                    # FastAPI app factory + middleware
│   ├── core/                      # settings, logging, lifecycle
│   ├── db/                        # models, repositories, async session
│   ├── agents/shared/             # contracts, registry, executor, model_client
│   ├── agents/{discovery,content_architect,visual_design_director,code_generator}/
│   │   ├── agent.py  schemas.py  README.md
│   │   ├── prompts/{system.md,prepare_questions.md,build_brief.md,repair_output.md}
│   │   └── samples/{input.json,output.json}
│   ├── agents/build_preparation/  # Stage 0 through Phase 3 preparation agent
│   ├── runtime/                   # state_service, mock_runner
│   ├── api/routes/                # health, agents, sessions, runs, discovery, content-architect, visual-design-director
│   └── web/                       # templates, static (css/js)
├── config/                        # committed non-secret TOML config
├── migrations/                    # Alembic
├── tests/                         # unit, api, integration, fixtures
├── docs/architecture.md
├── scripts/                       # docker-entrypoint.sh, verify_environment.py
├── .github/workflows/ci.yml
├── Dockerfile, compose.yaml, alembic.ini, pyproject.toml, uv.lock
└── README.md
```

## Prerequisites

- **Python 3.13** (pinned via `requires-python = ">=3.13,<3.14"`)
- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **Docker Desktop** (for Docker Compose startup; requires WSL2 on Windows)
- **PostgreSQL** (provided via Docker Compose, or a local instance on the port
  configured in `config/app.toml` `[database] port`, default `5544`)

## Environment setup

### Secrets (`.env`)

The root `.env` contains **secrets only** — database password and optional API keys.
Copy `.env.example` and fill in real values:

```powershell
PS > Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD (and optionally API keys)
```

Non-secret configuration (app name, host, port, DB host/port, model profiles) lives in
committed files under `config/`:

- `config/app.toml` — `[app]` and `[database]` settings
- `config/models.toml` — provider-neutral model profiles and logical engine
  routing; active engines currently use the configured Anthropic profile
  (see `[routing.engine_profiles]` and `[profiles.*]`)

## Windows PowerShell setup

```powershell
PS > uv sync
PS > docker compose up postgres -d
PS > uv run alembic upgrade head
PS > uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the developer testing harness.

## Linux/macOS setup

```bash
uv sync
docker compose up postgres -d
uv run alembic upgrade head
uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000
```

## uv commands

```powershell
uv sync                    # create/refresh venv from lockfile
uv sync --frozen           # strict: fail if lockfile is stale
uv add <package>           # add a production dependency
uv add --group dev <pkg>   # add a dev dependency
uv run <command>           # run a command in the project venv
uv lock --check             # verify lockfile is up to date
```

## Direct local startup

```powershell
PS > uv sync
PS > docker compose up postgres -d
PS > uv run alembic upgrade head
PS > uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000 --reload
```

## Docker Compose startup

```powershell
# Main workflow: PostgreSQL, migrations, FastAPI/UI, and durable worker.
PS > docker compose up --build
# App at http://localhost:8000, PostgreSQL on localhost:5544
PS > docker compose down
```

The Docker Compose stack:
- Builds the app image from `Dockerfile` (multi-stage, non-root, no dev deps)
- Starts PostgreSQL 16.4 (Alpine) with a persistent named volume
- App waits for DB health, runs `alembic upgrade head`, then starts Uvicorn (no reload)
- Worker runs as a separate durable PostgreSQL-backed process
- Exposes app on port 8000 and PostgreSQL on port 5544 (host) → 5432 (container)

Build Preparation validation is deliberately a separate run and is not
started by the main stack:

```powershell
# Offline/deterministic validation using the checked-in VDD fixture.
PS > docker compose --profile build-validation run --rm build-validation

# Optional live model/provider validation; requires the relevant .env keys
# and configured temporary artifact storage credentials.
PS > docker compose --profile build-validation run --rm build-validation --live-model --live-providers
```

The validation service exits after one detached Stage 0 → Phase 3 run. It does
not start the API, worker, migrations, or a portfolio session. For a local
non-Docker run, use the same entry point:

```powershell
PS > uv run python -m oryxenai.agents.build_preparation.cli
PS > uv run python -m oryxenai.agents.build_preparation.cli --live-model --live-providers
```

The two-page browser harness remains available from the main app at
`/build-preparation-fixture` and `/build-preparation-fixture/progress`.

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

## API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/live` | Process liveness (no DB dependency) |
| GET | `/health/ready` | Dependency readiness (checks PostgreSQL) |
| GET | `/api/v1/agents` | List registered mock agents |
| POST | `/api/v1/sessions` | Create a portfolio test session |
| GET | `/api/v1/sessions` | List recent sessions |
| GET | `/api/v1/sessions/{id}` | Get one session and its current state |
| GET | `/api/v1/sessions/{id}/runs` | Run history for a session |
| POST | `/api/v1/sessions/{id}/runs/mock` | Execute a deterministic mock run |
| GET | `/api/v1/sessions/{id}/discovery` | Get user-safe Discovery state |
| POST | `/api/v1/sessions/{id}/discovery/start` | Store intake, queue Discovery Call A |
| PUT | `/api/v1/sessions/{id}/discovery/answers` | Save answers; `complete: true` queues Call B |
| POST | `/api/v1/sessions/{id}/discovery/revise` | Natural-language brief revision (re-runs Call B) |
| POST | `/api/v1/sessions/{id}/discovery/approve` | Create immutable approved brief |
| GET | `/api/v1/sessions/{id}/content-architect` | Get Content Architect state |
| POST | `/api/v1/sessions/{id}/content-architect/start` | Snapshot approved Discovery, queue build (requires Discovery approved) |
| POST | `/api/v1/sessions/{id}/content-architect/revise` | Natural-language content revision (re-runs build) |
| POST | `/api/v1/sessions/{id}/content-architect/approve` | Approve the reviewed content |
| GET | `/api/v1/sessions/{id}/visual-design-director` | Get Visual Design Director state |
| POST | `/api/v1/sessions/{id}/visual-design-director/start` | Snapshot approved Content Architect output, queue build (requires Content Architect approved) |
| POST | `/api/v1/sessions/{id}/visual-design-director/revise` | Natural-language visual-direction revision (re-runs build) |
| POST | `/api/v1/sessions/{id}/visual-design-director/approve` | Approve the reviewed visual direction |

All errors return a structured envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "requestId": "correlation-id"
  }
}
```

## Developer harness URL

`http://127.0.0.1:8000` (or `http://localhost:8000` in Docker)

The harness allows you to:
1. Check liveness and DB readiness
2. Create test sessions and view recent ones
3. Select a session and complete the Discovery intake
4. Answer questions, review the brief, and click NEXT to approve
5. Inspect stored output, state, jobs, and run history

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
  state needed by the next agent.
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
