# OryxenAI

Production-oriented OryxenAI backend and developer testing harness.

> **Discovery is implemented end to end.** It uses the configured OpenCode Go
> adapter when a real run is requested. Later portfolio-generation agents remain
> intentionally out of scope. See [docs/architecture.md](docs/architecture.md)
> for design rationale.

## Current purpose

Prove the end-to-end pipeline works:

```
Application starts → PostgreSQL connects → Discovery intake saved
→ Durable Call A questions → persisted answers → durable Call B brief
→ editable review → explicit immutable approval
```

## Current non-goals

- Portfolio generation, code-generation sandbox, and downstream agent chaining
- Agent chaining, supervisor agent, LangChain/LangGraph, or any agent framework
- Queue/worker (Redis, Celery, Temporal, Kafka)
- Authentication, authorization, billing, Cloudflare, Supabase, GitHub Actions generation
- React frontend, visual editor, SEO, analytics, object storage
- Vector database, embeddings, prompt-management platform, observability SaaS
- Multiple microservices, Kubernetes, Terraform

## Architecture summary

- **Backend:** FastAPI + Pydantic + SQLAlchemy async (asyncpg) + Alembic
- **Database:** PostgreSQL (JSONB for state and payloads)
- **Frontend:** Jinja2 templates + vanilla JS/CSS (no framework, no CDN)
- **Agents:** Ordinary Python protocols + Pydantic models (no agent framework)
- **Model:** Provider-neutral `ModelClient` protocol with OpenCode Go JSON-mode adapter for Discovery
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
│   ├── runtime/                   # state_service, mock_runner
│   ├── api/routes/                # health, agents, sessions, runs, discovery
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
- **PostgreSQL** (provided via Docker Compose, or a local instance on port 5433)

## Environment setup

### Secrets (`.env`)

The root `.env` contains **secrets only** — database password and optional API keys.
Copy `.env.example` and fill in real values:

```powershell
PS C:\Users\yashx\Desktop\OryxenAI> Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD (and optionally API keys)
```

Non-secret configuration (app name, host, port, DB host/port, model profiles) lives in
committed files under `config/`:

- `config/app.toml` — `[app]` and `[database]` settings
- `config/models.toml` — provider-neutral model profiles; Discovery uses OpenCode Go/deepseek-v4-pro

## Windows PowerShell setup

```powershell
PS C:\Users\yashx\Desktop\OryxenAI> uv sync
PS C:\Users\yashx\Desktop\OryxenAI> docker compose up postgres -d
PS C:\Users\yashx\Desktop\OryxenAI> uv run alembic upgrade head
PS C:\Users\yashx\Desktop\OryxenAI> uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000
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
PS C:\Users\yashx\Desktop\OryxenAI> uv sync
PS C:\Users\yashx\Desktop\OryxenAI> docker compose up postgres -d
PS C:\Users\yashx\Desktop\OryxenAI> uv run alembic upgrade head
PS C:\Users\yashx\Desktop\OryxenAI> uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000 --reload
```

## Docker Compose startup

```powershell
PS C:\Users\yashx\Desktop\OryxenAI> docker compose up --build
# App at http://localhost:8000, PostgreSQL on localhost:5433
PS C:\Users\yashx\Desktop\OryxenAI> docker compose down
```

The Docker Compose stack:
- Builds the app image from `Dockerfile` (multi-stage, non-root, no dev deps)
- Starts PostgreSQL 16.4 (Alpine) with a persistent named volume
- App waits for DB health, runs `alembic upgrade head`, then starts Uvicorn (no reload)
- Worker runs as a separate durable PostgreSQL-backed process
- Exposes app on port 8000 and PostgreSQL on port 5433 (host) → 5432 (container)

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
| PUT | `/api/v1/sessions/{id}/discovery/input` | Save Discovery intake/source revision |
| POST | `/api/v1/sessions/{id}/discovery/questions` | Queue Discovery Call A |
| PUT | `/api/v1/sessions/{id}/discovery/answers` | Save typed Discovery answers |
| POST | `/api/v1/sessions/{id}/discovery/brief` | Queue Discovery Call B |
| PATCH | `/api/v1/sessions/{id}/discovery/brief` | Save typed brief edits |
| POST | `/api/v1/sessions/{id}/discovery/approve` | Create immutable approved brief |

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

Discovery additionally stores immutable source revisions in
`discovery_source_documents`. Its API and worker service use optimistic session
revisions so late model results are retained as stale history instead of replacing
newer user work. See `src/oryxenai/agents/discovery/README.md` for the complete flow.

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
- Verify the port: the Docker container maps host **5433** → container **5432**
  (to avoid conflict with a local PostgreSQL on 5432)
- Verify `POSTGRES_PASSWORD` is set in `.env` and matches the Docker container
- Check `config/app.toml` has `port = 5433` for local dev

### Port conflict (8000 or 5433)

- App port 8000: change `APP_PORT` in `config/app.toml` or `--port` flag
- DB port 5433: change the host mapping in `compose.yaml` (e.g. `"5434:5432"`)

### `.env` is accidentally missing

- The app will still start for unit/API tests that don't need PostgreSQL
- Integration tests will be skipped automatically
- For full functionality, copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`

### Model credentials are absent

- The app and worker still start without model credentials
- A real Discovery job fails safely with a controlled configuration error
- Normal tests use the deterministic fake client and require no model credential
- Set the environment variable named by `[profiles.discovery].api_key_env` for real OpenCode Go runs

### Development UI is disabled

- Set `enable_dev_ui = true` in `config/app.toml` `[app]` section

### Docker Desktop + asyncpg + SCRAM-SHA-256

- Docker Compose uses `POSTGRES_HOST_AUTH_METHOD: trust` for local development as
  a workaround for a Docker Desktop + asyncpg + SCRAM-SHA-256 interaction issue
- **Production MUST use `scram-sha-256`**: remove `POSTGRES_HOST_AUTH_METHOD` and
  verify asyncpg auth against your production PostgreSQL
