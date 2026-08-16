# OryxenAI — Project Context

This is the canonical, cross-tool context file for OryxenAI. Read this first
— before `README.md`, before exploring the code — regardless of which AI
coding tool or model you are (Claude Code, OpenAI Codex CLI, Google
Antigravity, Cursor, or any other). This file follows the open `AGENTS.md`
standard that Codex CLI, Cursor, GitHub Copilot, and Gemini CLI all read
automatically by this exact filename.

## What OryxenAI is

OryxenAI is a portfolio-generation platform that transforms a user's intent
into a deployable portfolio site. The system uses a pipeline of specialized
agents (discovery, content architect, visual design director, code generator),
each responsible for one phase of the transformation.

## Current implementation status

**Discovery is implemented end to end**, in its simplified/v2 form. The
platform includes durable jobs, worker lifecycle, session-state persistence,
5 API endpoints, and the vanilla-JS Discovery chat UI. Discovery stops after
explicit brief approval; later agents are invoked only by an explicit,
separate call. Discovery intentionally does NOT include: a separate immutable
source-documents table (raw intake is stored directly as JSONB on the
session state), a repair-prompt loop, a few-shot example library, or a
fact/conflict-graph validation layer — an earlier, more elaborate version had
these and they were deliberately removed as over-engineering (see
`DECISIONS.md` D-002). What remains: a 3-file prompt set (system + two
operation prompts), envelope-only output validation (the brief's Markdown
content itself is intentionally free text, not schema-validated), a 9-status
state machine, idempotency keys, and optimistic concurrency via session
revision.

**Content Architect is also implemented end to end**, as the second stage.
It consumes only a compact APPROVED Discovery snapshot (never the raw
resume/document text), requires Discovery's status to be `approved` before
it will start, and runs as a single durable job (`content_architect.build`)
whose agent makes 1-3 sequential model calls internally (`plan_content`,
then optionally `write_pages`, then optionally `integrate_content`) — an
adaptive bounded workflow, never one call per page/section. It has no chat
UI (no per-stage user interaction is needed) and is never auto-invoked by
Discovery approval; a caller must explicitly `POST .../content-architect/start`.
See `src/oryxenai/agents/content_architect/README.md` for the full route
table and state machine.

**Visual Design Director is also implemented end to end**, as the third
stage. It consumes only a compact APPROVED Content Architect output (never
Discovery's raw resume/document text, never Content Architect's internal
reasoning), requires Content Architect's status to be `approved` before it
will start, and runs as a single durable job
(`visual_design_director.build`) whose agent makes 1-3 sequential model
calls internally (`establish_visual_language`, then optionally
`direct_page_experience`, then optionally `integrate_site_experience`) —
the same adaptive bounded workflow shape as Content Architect. It also
consults a small, checked-in, deterministic local resource catalogue
(`agents/visual_design_director/resources/catalogue.json`) via plain Python
tag-overlap lookup — never a model tool-calling loop — to offer adaptable
design-pattern candidates. It has no chat UI and is never auto-invoked by
Content Architect approval; a caller must explicitly
`POST .../visual-design-director/start`. See
`src/oryxenai/agents/visual_design_director/README.md` for the full route
table and state machine.

**Portfolio Build Preparation is implemented as a hidden pre-code stage.** It
requires approved Content Architect and Visual Design Director state and is
started explicitly with `POST .../build-preparation/start`. A durable
`build_preparation.prepare` job compiles public scope, resolves verified
resources with explicit fallbacks, writes route-scoped build context, creates
one deterministic ZIP, verifies it through configured temporary
S3-compatible object storage (R2 in production), and restores a local debug
mirror when enabled. PostgreSQL stores only the object metadata and hashes;
the staged tree is disposable. The GET endpoint reports staleness when
approved upstream projections or the temporary object changes. See
`src/oryxenai/agents/build_preparation/`.

All model-backed agents call their configured model through the provider-neutral
`ModelClient` boundary — see `config/models.toml` for the live model/provider
per profile; never trust a model name written in prose documentation,
including this one, since it changes independently of any doc.

To verify current status rather than trusting this document: run
`uv run pytest`, and check `src/oryxenai/agents/<name>/` for an `agent.py`
**plus** a `service.py`/`state.py` — an agent directory with only
`schemas.py`, prompts, and samples (no service/state/validators) is still a
deterministic mock, not a live implementation.

## What is deliberately still mocked or excluded

- The registry-compatible Code Generator agent remains a deterministic mock,
  but its feature-gated standalone development workflow now implements Phases
  1-4: v3 admission, planning, controlled acquisition, progressive source
  generation, checkpoints, clean build/runtime verification, finite repair,
  atomic preview promotion, and source/preview API/UI. Production session
  integration remains deferred; see `DECISIONS.md` D-015 and
  `docs/code-generator-architecture/`.
- Normal tests use checked-in fixtures; live model calls are opt-in.
- No portfolio generation, publishing, web research, or automatic chaining
  between agents.
- No agent supervisor or cross-agent sequencing exists — every stage is
  started by an explicit caller.
- No authentication, billing, Supabase, or published-portfolio deployment
  automation. Cloudflare R2 is used only for temporary Build Preparation
  packs.
- No Redis, Celery, Kafka, or external queue.

## Config-driven policy — never hardcode

- **Secrets** (`POSTGRES_PASSWORD`, API keys) live only in `.env`, which is
  git-ignored. `.env.example` documents variable names with empty/fake
  values. Secrets are never logged, never returned in API responses, and
  never displayed by the doctor command.
- **Non-secret app/db/worker settings** live in `config/app.toml` (local),
  overlaid by `config/app.docker.toml` (Docker) or `config/app.test.toml`
  (tests).
- **Model profiles** live in `config/models.toml` — provider-neutral,
  per-agent (`[profiles.discovery]`, `[profiles.content_architect]`, ...).
  API keys are resolved indirectly via an `api_key_env` name, never
  referenced by literal value or provider name in agent code or business
  logic. Changing provider/base_url/model/api_key_env must never require an
  agent-code change.
- **Migration URL** is resolved from settings, not hardcoded in
  `alembic.ini`.
- **This same discipline extends to documentation itself**: never freeze a
  model name, a test count, or a "currently implemented" snapshot in prose.
  Point at the source of truth instead — `config/models.toml` for models,
  `uv run pytest` for test coverage, the relevant `src/oryxenai/agents/*/`
  directory for implementation status.

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
  api/routes/                health, agents, sessions, runs, system, discovery, content-architect, visual-design-director
  web/                       Jinja2 templates + static assets
config/                      committed non-secret TOML configuration
migrations/                  Alembic (async, settings-driven)
tests/                       unit, api, integration, worker
scripts/                     cross-platform launcher scripts
```

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
- Claiming uses `SELECT … FOR UPDATE SKIP LOCKED`. Two workers never own the
  same job concurrently.
- Retries use exponential backoff with configurable delay and max attempts.
- Stale running jobs are recovered via lease/heartbeat expiry.
- Registered handlers: `system.worker_probe` (diagnostic, never calls an
  agent or model), `discovery.understand_and_question`, `discovery.build_or_revise_brief`,
  `content_architect.build`, `visual_design_director.build`,
  `build_preparation.prepare`, plus two
  legacy Discovery aliases (`discovery.prepare_questions`,
  `discovery.build_brief`) kept only so any in-flight pre-rename job payload
  still executes.
- The worker is started via `scripts/run-worker.ps1` (or
  `uv run python -m oryxenai.jobs.worker`).
- Worker lifecycle: startup validation → heartbeat loop → poll/claim →
  independent handler sessions → graceful SIGINT/SIGTERM shutdown.

## Current request-to-database flow

```
Browser → FastAPI API
  → validate session + agent key
  → executor creates agent_runs row, snapshots state_before
  → API stores intake/answers directly on session state (JSONB)
  → API creates an agent_run and enqueues a durable job
  → worker loads the run's input payload from DB, calls the agent, and CAS-applies results
  → browser polls state, saves answers/edits, and POSTs explicit approval
  → approved snapshot is persisted; the flow stops until the next stage is explicitly started
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

- **Domain:** envelope schemas, envelope-only validators, 9-status state
  machine (`agents/discovery/schemas.py`, `validators.py`, `state.py`). The
  brief's Markdown content is intentionally NOT business-validated — only
  the transport envelope (mode, assistant_message, question/brief shape) is.
- **Prompts:** 3 files — `prompts/system.md` (trusted, shared by both
  operations), `prompts/understand_and_question.md`,
  `prompts/build_or_revise_brief.md`. No repair-prompt loop and no few-shot
  example library — the prompts themselves carry inline BAD/GOOD
  contrastive examples instead.
- **Model adapter:** OpenAI-compatible `chat/completions` JSON-object mode
  (`agents/shared/providers/`), sending the trusted system prompt and the
  untrusted user/document data as separate `system`/`user` chat messages.
  Tests and the dev-harness mock-run endpoint use `MockModelClient`
  (`shared/model_client.py`) — no separate fake-client module.
- **Durable worker:** both operations run through the persisted job queue,
  each with stale-result detection and CAS revision checks.
- **Persistence:** Discovery intake/answers/memory/brief live directly as
  JSONB under `portfolio_sessions.current_state["discovery"]` (no separate
  source-documents table), plus idempotent job keys and approved brief
  snapshots (hash-stamped on approval).
- **API:** 5 REST endpoints — GET state, POST start, PUT answers, POST
  revise (natural-language brief revision), POST approve. See
  `agents/discovery/README.md` for the authoritative route table.
- **Frontend:** Jinja2 + vanilla-JS chat composer → adaptive one-at-a-time
  questions → brief review/edit/revise → approval flow, with refresh-safe
  state recovery and a collapsed developer-tools panel for diagnostics. See
  `docs/frontend-behavior-spec.md` for the full conversational/UX contract.
- **Tests:** unit (schemas, state machine, prompt builder, validators,
  adapter, service), API (HTTP flow, route contract), integration
  (persistence, worker) — run `uv run pytest -k discovery` for current
  coverage rather than trusting a frozen number here.

## Visual Design Director Agent — implementation summary

The Visual Design Director Agent is implemented end-to-end, mirroring
Content Architect's architecture one stage down the pipeline:

- **Domain:** envelope schemas, envelope-only validators, 5-status state
  machine (`agents/visual_design_director/schemas.py`, `validators.py`,
  `state.py`). Structured fields (route_id echoes, scene_id, asset_id,
  resource_id) carry stable IDs for downstream compilation; free-dict
  fields (`visual_language`, `shared_visual_systems`, `motion_system`,
  `compiler_handoff`, ...) stay unvalidated prose — the same structured-vs-
  free split Content Architect's own schema already uses.
- **Prompts:** 4 files — `prompts/system.md` (trusted, shared by all three
  operations), `prompts/establish_visual_language.md`,
  `prompts/direct_page_experience.md`, `prompts/integrate_site_experience.md`.
- **Resource catalogue:** `resource_catalogue.py::find_candidates` is a
  deterministic, in-process, tag-overlap lookup over a small checked-in
  fixture (`resources/catalogue.json`) — computed once per run in plain
  Python before any model call, never a model tool-calling loop. A
  `resource_id` the model references must have been in the shortlist
  actually given to that call; enforced structurally in `validators.py`.
- **Model adapter:** same OpenAI-compatible `chat/completions` JSON-object
  mode as Discovery/Content Architect, own `[profiles.visual_design_director]`
  entry in `config/models.toml`.
- **Durable worker:** runs through the persisted job queue
  (`visual_design_director.build`), with stale-result detection (against
  Content Architect's own approved content hash) and CAS revision checks.
- **Persistence:** direction output lives directly as JSONB under
  `portfolio_sessions.current_state["visual_design_director"]` (no
  dedicated table — same JSONB-on-session-state precedent as Discovery and
  Content Architect), plus idempotent job keys and approved direction
  snapshots (hash-stamped on approval).
- **API:** 4 REST endpoints — GET state, POST start, POST revise
  (natural-language direction revision), POST approve. See
  `agents/visual_design_director/README.md` for the authoritative route
  table.
- **Tests:** unit (schemas, state machine, prompt builder, resource
  catalogue, validators, agent workflow orchestration, service helpers),
  API (HTTP flow, route contract), integration (persistence, worker,
  staleness) — run `uv run pytest -k visual_design_director` for current
  coverage rather than trusting a frozen number here.

## What to implement next

- **Refine and evaluate the Discovery, Content Architect, and Visual Design
  Director agents** using real but privacy-safe examples.
- **Code Generator production integration remains unimplemented** — the
  standalone Phases 1-4 workflow is under
  `docs/code-generator-architecture/`, and Build Preparation does not
  auto-chain into it.

## Multi-agent collaboration protocol

Multiple AI tools, models, and devices work on this repo. To keep them
consistent:

1. **Check `DECISIONS.md` first** before making an architectural choice that
   might already have been decided or explicitly rejected.
2. **Log commit-sized work to `CHANGES.md`.** After finishing a real unit of
   work (a feature, a fix, a refactor, an architecture/schema change) —
   roughly what would earn its own git commit message — append one compact
   entry per `CHANGES.md`'s own template, and run its compaction check. Do
   not log every individual file save. If it's unclear whether something
   counts as "major" enough to log, **ask the user** rather than guessing.
3. **Log real decisions to `DECISIONS.md`**, not routine implementation
   choices — same rule: ask if unsure.
4. **Never hardcode** a model name, provider, API key env-var value, test
   count, or "currently implemented" snapshot anywhere — follow the
   config-driven policy above.

## Related documents

- [`README.md`](README.md) — human-facing developer setup and usage.
- [`docs/architecture.md`](docs/architecture.md) — architectural rationale
  ("why", not "what").
- [`docs/frontend-behavior-spec.md`](docs/frontend-behavior-spec.md) — the
  conversational/UX contract for the Discovery/Content Architect chat flow.
- [`CHANGES.md`](CHANGES.md) — change history (who/what/where/when/why).
- [`DECISIONS.md`](DECISIONS.md) — decisions, rejected alternatives, and
  open/deferred items.
- [`CODEX.md`](CODEX.md) and [`CLAUDE.md`](CLAUDE.md) — short redirects to
  this file for tools/habits that look for those names specifically.
