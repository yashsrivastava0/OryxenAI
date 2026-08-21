# OryxenAI Architecture — Discovery Phase

> This document explains **why** the current Discovery implementation is designed
> the way it is. It does not describe excluded downstream product stages.
> For **current implementation status** (what's actually built today), see
> [`AGENTS.md`](../AGENTS.md) — this document intentionally stays "why", not
> "what," so it doesn't go stale as implementation status changes.

## 1. Why the system currently uses explicit Python agents

The scaffold uses ordinary Python protocols (`Agent`, `ModelClient`) and small
Pydantic models instead of an agent framework (LangChain, LangGraph, CrewAI,
AutoGen, etc.).

**Rationale:**
- Frameworks impose abstractions (tool calling conventions, message schemas,
  memory stores, supervisor patterns) that are speculative before the actual
  agent behavior is known.
- Explicit agents are easier to test, inspect, and reason about in isolation.
- Each agent owns its directory with its schemas, prompts, and sample
  input/output — making the contract explicit and reviewable.
- A framework can be introduced later **only when** a concrete need is
  demonstrated (e.g. real tool calling, complex routing) without rewriting the
  agent boundaries.

## 2. Why the model boundary is provider-neutral

All model-backed stages use the provider-neutral `ModelClient` contract. Real
operations currently route through the configured Anthropic profile, while
normal tests inject deterministic clients. A central `ModelRouter` resolves a
logical engine to a profile from `config/models.toml`, so changing a provider,
model, or per-engine assignment does not require agent-code changes.

**Rationale:**
- Provider adapters implement the same contract, including the Anthropic
  Messages API adapter and existing OpenAI-compatible adapters. A future
  provider is added at the adapter factory/config boundary, not inside each
  agent.
- The logical route is whatever `[routing.engine_profiles]` assigns in
  `config/models.toml`. The profile controls provider, model, endpoint, key
  name, structured-output capability, thinking strategy, and limits.
- API keys are resolved **indirectly**: a profile declares an `api_key_env`
  name, and the application reads that named secret from `.env` only when a
  real model call is eventually made. Agent code never references
  provider-specific variable names.
- This lets the application and worker start without credentials; only an
  attempted real Discovery operation needs the configured secret.

## 3. Why outputs are stored in JSONB

All agent input, output, state snapshots, model metadata, and error payloads
are stored as PostgreSQL `JSONB` columns.

**Rationale:**
- Agent outputs are structured but evolve rapidly; normalizing every field
  into columns would require a migration per schema change.
- JSONB supports indexing, querying, and schema validation at the application
  layer (Pydantic) without forcing a rigid database schema.
- PostgreSQL JSONB preserves type fidelity (booleans, numbers, nested objects,
  arrays) and supports concurrent reads/writes reliably.
- No SQLite substitution: PostgreSQL JSONB behavior is tested with real
  PostgreSQL (marked `@pytest.mark.integration`).

## 4. Why current state and run history are separate

The system uses a two-level state model:

- **Current aggregate state** (`portfolio_sessions.current_state` JSONB):
  the latest merged state needed by the next agent. Updated transactionally
  with an incrementing `revision` for optimistic concurrency.

- **Immutable run history** (`agent_runs`): every run records input,
  `state_before`, output, `state_after`, status, error, timing, agent
  identity, prompt version, model metadata, and idempotency key. Successful
  runs are never updated.

**Rationale:**
- Separating current state from history means the "what is the current
  situation" query is a single row read, not a replay of all runs.
- Immutable history preserves an audit trail for debugging, retry, and
  future replay features without risking the current state.
- The executor updates both inside one transaction so a successful output and
  the updated session state cannot diverge.

## 5. Why the testing UI is server-rendered

The developer harness is Jinja2 templates + vanilla JS + plain CSS, served by
the same FastAPI application.

**Rationale:**
- The harness verifies **application, database, state, worker, and agent
  boundaries** — it is not the final product UI.
- A server-rendered page with `fetch` calls to the local API is sufficient,
  fast to build, and has zero build pipeline.
- No React, Vite, npm, Tailwind, or CDN dependencies are introduced.
- The final product frontend or generated-portfolio runtime can add a proper
  frontend later without touching this harness.
- The harness escapes all dynamic JSON and never uses `innerHTML` with
  user-provided values.

## 6. Why the app and PostgreSQL are separate containers

Docker Compose runs separate FastAPI, durable worker, one-shot migration, and
PostgreSQL containers.

**Rationale:**
- PostgreSQL has its own lifecycle, persistence, and resource profile; bundling
  it inside the app image would violate the one-process-per-container principle.
- A named volume (`oryxen_pgdata`) persists database data across restarts.
- The migration container applies Alembic migrations before the API and worker;
  the app and worker remain separate processes.
- In production, this topology maps naturally to managed PostgreSQL and a
  containerized app service.

## 7. Why no agent supervisor exists

The system does not include an agent supervisor or cross-agent orchestrator.
Docker runs one Uvicorn process per app container and one worker process per
worker container.

**Rationale:**
- Each container runs a single process: one app (FastAPI + API + UI), one
  worker (background job executor), one migration (one-shot Alembic).
- Docker Compose / Kubernetes already handles restart policies and health
  checks; an in-container supervisor adds complexity without benefit.
- A supervisor will be reconsidered only when a demonstrated need arises
  (e.g. a sidecar process or graceful multi-process shutdown).

## 8. Which boundaries may change later

- **Later agents:** Content Architect and Visual Design Director now
  consume their respective upstream approved output through exactly this
  kind of explicit product decision (each stage requires an explicit
  `/start` call after the previous stage's approval, never auto-chained).
  Code Generator exposes the model-backed structured planner through the agent
  registry, while its standalone harness and explicit production-session API
  share the durable progressive generation and verification core. Production
  start binds one eligible Build Preparation object; no stage auto-chains. See
  `AGENTS.md` and `docs/code-generator-architecture/` for the current boundary.
- **Model client:** Additional providers can implement the same contract; the
  active default and per-engine assignments are configuration decisions.
- **Agent sequencing:** A future task may add cross-agent sequencing or a
  supervisor. The executor currently runs one agent per request; sequencing
  will be an explicit layer above the executor, not embedded in agents.
- **State schema:** The `agents.<key>.{latestRunId, output}` namespacing may
  gain additional fields (e.g. `status`, `timestamp`) as real agents produce
  richer artifacts.
- **Frontend:** The testing harness will be replaced by the real product
  frontend (likely React/Next.js) when the portfolio-generation runtime is
  implemented.
- **Configuration:** Non-secret settings may move from `config/app.toml` to
  command-line flags or a separate deployment_overlay mechanism if deployment
  requirements demand it. `.env` will remain secrets-only.
- **Authentication:** Not present in the scaffold; future auth will add user
  ownership to `portfolio_sessions` and authorization checks to the API.
