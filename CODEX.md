# OryxenAI — Project Context

## What OryxenAI is

OryxenAI is a portfolio-generation platform that transforms a user's intent
into a deployable portfolio site. The system uses a pipeline of specialized
agents (discovery, content architect, visual design director, code generator),
each responsible for one phase of the transformation.

## Current development phase

**Discovery complete through Phase 4 (Final Acceptance).** The platform includes
durable jobs, worker lifecycle, immutable Discovery source snapshots,
persistence, API endpoints, and the vanilla-JS Discovery harness. Discovery
stops after explicit brief approval; later agents remain intentionally out of
scope. All 54 Definition-of-Done criteria from the implementation plan are met.

## What is implemented

- FastAPI application with Jinja2/vanilla-JS developer harness.
- PostgreSQL persistence: JSONB session state, immutable Discovery source
  snapshots, agent-run history, optimistic revisions, and transactional writes.
- Discovery domain schemas, preprocessing, provenance validation, prompts,
  state machine, API, frontend, and durable Call A/Call B worker flow.
- OpenCode Go `ModelClient` adapter using `deepseek-v4-pro` chat/completions
  JSON mode, with deterministic fake-client coverage.
- The remaining agents conform to the shared `Agent` protocol as deterministic
  mocks and are not invoked by Discovery.
- Alembic async migrations.
- Multi-stage Docker image serving API and developer UI.
- Docker Compose topology (app, worker, one-shot migration, postgres).
- Config policy: secrets in `.env`; non-secret config in committed
  `config/app.toml` and `config/models.toml`.

## What is deliberately still mocked or excluded

- Content Architect, Visual Design Director, and Code Generator remain mocks.
- Normal tests use checked-in Discovery fixtures; live OpenCode calls are opt-in.
- No portfolio generation, publishing, web research, or automatic chaining.
- No agent chaining, supervisor, or cross-agent sequencing exists.
- No authentication, billing, Cloudflare, Supabase, R2, or deployment.
- No Redis, Celery, Kafka, or external queue.

## Current request-to-database flow

```
Browser → FastAPI API
  → validate session + agent key
  → executor creates agent_runs row, snapshots state_before
  → Discovery intake creates an immutable source revision
  → API creates an agent_run and enqueues a durable Call A/Call B job
  → worker loads source/run snapshots from DB, calls Discovery, and CAS-applies results
  → browser saves answers/edits and POSTs explicit approval
  → approved brief snapshot is persisted; the flow stops
```

All agent input, output, state snapshots, and errors are stored as JSONB.
Agent code never receives database sessions or HTTP requests.

## Request-to-worker-to-database flow (durable jobs)

```
Browser → FastAPI API
  → enqueue job row in background_jobs (inside API's database tx)
  → return durable job ID
  → worker process claims due rows via FOR UPDATE SKIP LOCKED
  → handler executes in an independent session
  → result or safe error persisted
  → status visible via diagnostics API
```

The API and worker are separate processes. They use the same application
image but never run inside the same container. Migrations run once via a
dedicated one-shot migration service before the app or worker start.

## Repository map

```text
src/oryxenai/
  main.py                    FastAPI application factory
  core/                      settings, logging, lifecycle
  db/                        async engine, session, models, repositories
  jobs/                      durable PostgreSQL job queue, worker, heartbeat
  agents/shared/             contracts, registry, executor, model_client
  agents/{discovery, content_architect, visual_design_director, code_generator}/
  runtime/                   state_service, mock_runner
  api/routes/                health, agents, sessions, runs, system, discovery
  web/                       Jinja2 templates + static assets
config/                      committed non-secret TOML configuration
migrations/                  Alembic (async, settings-driven)
tests/                       unit, api, integration, worker
scripts/                     cross-platform launcher scripts
```

## Sources of configuration

- **Secrets:** `.env` (POSTGRES_PASSWORD, API keys). Never committed.
- **Non-secret app/db/worker:** `config/app.toml` (local). Overlaid by
  `config/app.docker.toml` (Docker) or `config/app.test.toml` (tests).
- **Model profiles:** `config/models.toml` (provider-neutral, Discovery uses
  `opencode_go` / `deepseek-v4-pro`).
- **Migration URL:** resolved from settings, not hardcoded in `alembic.ini`.

## Secret-handling policy

- `.env` is git-ignored and contains only genuine credential values.
- `.env.example` documents variable names with empty/fake values.
- Non-secret configuration never appears in `.env`.
- API keys are resolved indirectly via `config/models.toml` (never
  referenced by agent code or by name in business logic).
- Secrets are never logged, never returned in API responses, and never
  displayed by the doctor command.

## Database and migration ownership

- Migrations live under `migrations/` and are applied by `alembic upgrade head`.
- The application database is `oryxenai`. The test database is `oryxenai_test`.
- In Docker, a one-shot `migrate` service runs migrations once before the
  `app` and `worker` start. Neither the app nor the worker entrypoint runs
  `alembic upgrade head` itself.
- For local development, migrations are run explicitly:
  `uv run alembic upgrade head`.
- Integration tests use a dedicated test database and never drop or reset
  the application database.

## Worker and job semantics

- Jobs are durable PostgreSQL rows in `background_jobs`.
- At-least-once execution. Idempotent handlers are expected.
- Claiming uses `SELECT … FOR UPDATE SKIP LOCKED`. Two workers never own
  the same job concurrently.
- Retries use exponential backoff with configurable delay and max attempts.
- Stale running jobs are recovered via lease/heartbeat expiry.
- Registered handlers: `system.worker_probe` (diagnostic) and `discovery`
  (Call A and Call B). The probe handler is deterministic and never calls an
  agent or model.
- The worker is started via `scripts/run-worker.ps1` (or `uv run python -m oryxenai.jobs.worker`).
- Worker lifecycle: startup validation → heartbeat loop → poll/claim →
  independent handler sessions → graceful SIGINT/SIGTERM shutdown.

## Canonical local commands

```powershell
.\scripts\bootstrap.ps1   # install dependencies into .workspace/venv
.\scripts\run-api.ps1      # start the FastAPI server
.\scripts\run-worker.ps1   # start the background worker
.\scripts\test.ps1         # run the test suite
.\scripts\check.ps1        # lint, format-check, type-check
.\scripts\doctor.ps1       # environment diagnostics
.\scripts\clean.ps1        # remove generated files (preserves .workspace/venv)
```

## Canonical verification commands

```powershell
uv run ruff check .                    # lint
uv run ruff format --check .           # format check
uv run mypy src                        # type check
uv run pytest                          # tests (integration requires PostgreSQL)
alembic upgrade head                   # migrate
```

## Where tests belong

All test files live under `tests/`:

```text
tests/unit/          pure unit tests, no database
tests/api/           FastAPI endpoint tests (may need test DB for system routes)
tests/integration/   PostgreSQL-backed repository and job tests
tests/worker/        worker claim, retry, shutdown, and concurrency tests
```

No test files exist inside any agent directory or under `src/`.

## Discovery Agent — implementation summary

The Discovery Agent is implemented end-to-end with the following architecture:

- **Domain:** schemas, preprocessing, provenance validation, state machine
  (`agents/discovery/schemas.py`, `validators.py`, `state.py`)
- **Prompts:** templated system + task prompts (`agents/discovery/prompts/`)
- **Model adapter:** OpenCode Go `deepseek-v4-pro` chat/completions JSON mode,
  with deterministic fake-client for tests (`providers/opencode_go.py`,
  `fake_client.py`)
- **Durable worker:** Call A (questions) and Call B (brief) run through the
  persisted job queue, each with stale-result detection and CAS revision checks
- **Persistence:** immutable `discovery_source_documents` table, Discovery
  aggregate state under `portfolio_sessions.current_state["discovery"]`,
  idempotent job keys, and approved brief snapshots
- **API:** 7 REST endpoints (GET state, PUT input, POST questions, PUT answers,
  POST brief, PATCH brief, POST approve)
- **Frontend:** Jinja2 + vanilla-JS intake → one-at-a-time questions →
  brief review/edit → approval flow, with refresh-safe session storage
- **Tests:** unit (schemas, state, prompts, preprocessing, validators, fake
  client, adapter, worker handler), API, integration (persistence, worker),
  6 evaluation fixtures

## What to implement next

- **Refine and evaluate the Discovery Agent** using real but privacy-safe
  examples.
- **Do not proceed to Content Architect automatically.** Later agents
  (Content Architect, Visual Design Director, Code Generator) remain
  deterministic mocks and are never invoked by Discovery approval.
