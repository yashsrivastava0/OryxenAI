<!--
  Canonical AI Coding Agent Context
  Format: AGENTS.md (Open Agentic Standard - https://agentsmd.io)
  Last Updated: 2026-10-01
  Repository: OryxenAI
  Supported Agents: Claude Code, OpenAI Codex CLI, Google Antigravity, Cursor, GitHub Copilot, Gemini CLI
-->

# OryxenAI — Canonical AI Agent Context

> **Note for AI Coding Assistants (Claude Code, OpenAI Codex CLI, Google Antigravity, Cursor, Copilot, Gemini CLI):**
> Read this document first before inspecting source code or running commands. This file is the single source of truth for repository structure, architectural invariants, security rules, and verification standards.

---

## Agent Fast-Track Cheatsheet

| Domain | Quick Reference & Ground Truth |
| :--- | :--- |
| **Core Architecture** | Two-stage portfolio planning: **Stage 1: Discovery** &rarr; **Stage 2: Content Architect**. The active product and API workflow concludes strictly upon Content Architect plan approval. No automatic stage chaining. |
| **Technology Stack** | Python 3.13 (`uv`), FastAPI, SQLAlchemy Async, PostgreSQL (JSONB state + queue), Preact + TypeScript + Vite frontend. |
| **Queue & Worker** | PostgreSQL-backed durable jobs (`SELECT ... FOR UPDATE SKIP LOCKED`). Zero Redis/Celery. |
| **Model Invocations** | Provider-neutral `ModelClient` configured via `config/models.toml`. Never hardcode provider names or model IDs in business logic. |
| **Configuration** | Secrets strictly in git-ignored `.env`. Non-secret settings in `config/app.toml` and overlays. |
| **Verification Suite** | `uv run ruff check .` &bull; `uv run ruff format --check .` &bull; `uv run mypy src` &bull; `uv run pytest` &bull; `uv run alembic upgrade head` |
| **Branch Safety** | `staging` = routine development &bull; `deployment` = production Azure VM. **Never target or merge to `deployment` without explicit human sign-off in the active session.** |
| **Multi-Agent Rules** | Check `DECISIONS.md` before making architectural choices. Log commit-sized work to `CHANGES.md`. Commit verified units locally by default. |

---

## 1. What OryxenAI Is (and Isn't)

OryxenAI is an authenticated, intelligent portfolio-planning product. It converts raw user intent and background materials into:
1. An approved **Discovery Brief**.
2. An approved **Content Architect Plan**.

The active product and API workflow **ends after content plan approval**. The repository does **not** currently generate, compile, or serve a published portfolio website.

### Deliberately Excluded Behaviors
* **No automatic stage chaining or autonomous supervisor:** Callers and users explicitly trigger each stage via API/UI.
* **No generated-site runtime or browser hosting:** Output is structured planning data, not a deployed frontend portfolio site.
* **No external queue brokers:** No Redis, RabbitMQ, Celery, or Kafka. Background jobs are managed purely via PostgreSQL.
* **No live model calls during standard tests:** Default test runs use deterministic fixtures and mock clients. Live provider calls are strictly opt-in.

---

## 2. Current Implementation Status

### Discovery Stage
* **Status:** Implemented end-to-end.
* **Capabilities:** Intake capture, adaptive interview questions, synthesis of brief, durable worker job execution, session-state persistence (JSONB), and five API endpoints.
* **Boundary:** Stops after explicit brief approval; does not auto-advance to Content Architect.
* **Documentation:** See [`src/oryxenai/agents/discovery/README.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/discovery/README.md).

### Content Architect Stage
* **Status:** Implemented end-to-end.
* **Capabilities:** Consumes approved Discovery dossier, runs as a single durable background job executing 1 to 3 sequential model operations (`plan_content`, optionally `write_pages`, optionally `integrate_content`).
* **Boundary:** Started only through explicit API call; stops upon content plan review and approval.
* **Documentation:** See [`src/oryxenai/agents/content_architect/README.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/content_architect/README.md).

### Authentication, Entitlements & Storage
* Local foundation supporting identity verification, just-in-time account admission, onboarding, owner-scoped session security, admin access, account lifecycle, and worker fencing.
* Normal users are strictly isolated to their own portfolio sessions. Administrative endpoints support archival cleanup.
* Reference: [`src/oryxenai/auth/`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/auth/).

### Product Workspace
* Authenticated Preact/TypeScript/Vite application served via FastAPI.
* Session and run projections expose active workflow fields. Historical runs are retained in PostgreSQL for audit and cleanup.

---

## 3. Config-Driven Policy — Never Hardcode

* **Secrets:** `POSTGRES_PASSWORD`, Supabase keys, R2 keys, and model API keys belong **exclusively** in `.env` (git-ignored). Template with empty placeholders lives in `.env.example`. Never log, return, or commit secrets.
* **Non-Secret Settings:** App name, hosts, ports, pool sizes, and flags live in `config/app.toml` and environment overlays (`config/app.native.toml`, etc.).
* **Model Profiles:** Managed in `config/models.toml`. Provider type, base URL, model name, and credential env-var names are configuration.
* **Database Migrations:** Connection URL is derived dynamically from application settings; never hardcoded in `alembic.ini`.
* **Prose Neutrality:** Never freeze model names, test counts, or static implementation metrics in documentation. Reference configuration, scripts, or test commands instead.

---

## 4. Repository Topology

```text
src/oryxenai/
  main.py                    # FastAPI application factory & lifespan
  core/                      # Settings, logging, lifecycle management
  db/                        # Async SQLAlchemy engine, models, repositories
  jobs/                      # PostgreSQL queue, worker loop, heartbeat
  agents/
    shared/                  # Agent contracts, registry, executor, ModelClient
    discovery/               # Active intake and brief planning stage
    content_architect/       # Active content blueprint stage
  auth/                      # Identity, ownership, entitlements, admin lifecycle
  api/routes/                # Session, stage, and operational endpoints
  web/                       # Product shell and static assets
  storage/                   # Archival cleanup interfaces
frontend/                    # Authenticated Preact/TypeScript/Vite product
config/                      # Committed non-secret TOML configuration
migrations/                  # Alembic schema version history
tests/                       # Unit, API, integration, and worker test suites
scripts/                     # Cross-platform startup and verification tools
docs/                        # Architecture, runbooks, and behavioral specs
```

---

## 5. Database, Worker & Job Semantics

* **Storage Engine:** PostgreSQL with JSONB columns for flexible session state and job payloads.
* **Application DB:** `oryxenai`.
* **Integration Test DB:** `oryxenai_test` (never run integration tests against the application database).
* **Migration Command:** `uv run alembic upgrade head`. Migrations are applied in Docker via a dedicated one-shot service prior to app/worker startup.
* **Job Queue:** Stored in `background_jobs` table. Execution is at-least-once; handlers must remain idempotent.
* **Worker Locking:** Workers claim jobs using `SELECT ... FOR UPDATE SKIP LOCKED`.
* **Fault Tolerance:** Exponential backoff retry with configurable limits; stale leases reclaimed via heartbeat expiration.
* **Optimistic Locking:** Session state updates verify revision counter (`revision`) to guarantee concurrent or late worker results do not overwrite newer user modifications.

---

## 6. End-to-End Request & Data Flow

```text
Browser / Client (Preact UI)
    │
    ▼ (HTTP / REST API)
FastAPI Backend
    │
    ├── 1. Authenticate & authorize owner-scoped session
    ├── 2. Persist intake / responses to PostgreSQL (portfolio_sessions)
    └── 3. Enqueue durable job in PostgreSQL (background_jobs)
            │
            ▼
Durable Background Worker
    │
    ├── 1. Claim job (SELECT ... FOR UPDATE SKIP LOCKED)
    ├── 2. Load session snapshot & invoke ModelClient (config/models.toml)
    ├── 3. Validate structured output envelope
    └── 4. Commit output & state to session (with optimistic revision check)
            │
            ▼
Browser / Client (Preact UI)
    │
    └── Polls / reads updated state -> User reviews, revises, or approves
```

---

## 7. Canonical Commands Reference

### Native Local Launchers
```powershell
# Windows PowerShell
.\scripts\bootstrap.ps1            # Initialize workspace and virtualenv
.\scripts\run-native.ps1 align-db  # Align local PostgreSQL instance
.\scripts\run-native.ps1 migrate   # Apply Alembic migrations
.\scripts\run-native.ps1 dev       # Start API and worker concurrently
.\scripts\run-api.ps1              # Start API only
.\scripts\run-worker.ps1           # Start worker only
.\scripts\check.ps1                # Run full lint + type-check suite
.\scripts\test.ps1                 # Run test suite
.\scripts\doctor.ps1               # Environment sanity check
```

```bash
# Linux / macOS
chmod +x scripts/*.sh
./scripts/run-native.sh align-db
./scripts/run-native.sh migrate
./scripts/run-native.sh dev
```

### Verification & Quality Gate
Every agent must ensure these commands pass before concluding major changes:
```bash
uv run ruff check .               # Lint checks
uv run ruff format --check .      # Code formatting check
uv run mypy src                   # Static typing validation
uv run pytest                     # Full test suite
uv run alembic upgrade head       # Schema validation
```

### Test Directory Layout
```text
tests/unit/          # Pure unit tests (fast, no external services)
tests/api/           # FastAPI HTTP endpoint tests
tests/integration/   # PostgreSQL-backed repository & queue tests (requires oryxenai_test)
tests/worker/        # Worker claiming, concurrency, retry, and shutdown tests
```

---

## 8. Fresh-Machine Setup, Secrets & Branching Policy

### Getting Started on a Fresh Machine
1. Clone repository and inspect this `AGENTS.md` before making changes.
2. Run `.\scripts\bootstrap.ps1` to configure `.workspace/venv`.
3. Copy `.env.example` to `.env`. Populate only the secrets required for your local work. Standard test execution and mock agent runs require no real model API keys. **Never copy secrets across machines.**
4. Apply migrations: `.\scripts\run-native.ps1 migrate`.
5. Verify health: `.\scripts\test.ps1` and `.\scripts\check.ps1`.

### Branch Workflow: `staging` vs `deployment`
* **`staging` Branch (Development):** All routine development occurs here. Push and open PRs freely. GitHub Actions runs continuous integration (lint, type-check, tests, Docker smoke test). Pushes to `staging` never trigger production deployments.
* **`deployment` Branch (Production):** Wired to Azure VM self-hosted runner. Protected by branch rules. Merging to `deployment` automatically redeploys production.
* **Zero Autonomous Deployment Rule:** An AI agent must **never** open a PR targeting `deployment` or merge into `deployment` without explicit, real-time human instruction in the active session.

### Secrets Protection
* Never paste raw secrets into chat sessions, logs, or commit messages.
* `scripts/azure-deploy.sh` contains automated `credential_free_logs()` scans that fail builds if secret patterns appear in logs.
* Never run destructive overwrite commands like `cp .env.example .env` without verified backups.

---

## 9. Multi-Agent Collaboration Protocol

Multiple AI tools (Claude Code, OpenAI Codex, Antigravity, Cursor) collaborate on this codebase. To prevent conflicts and lost work:

1. **Consult Prior Decisions:** Check [`DECISIONS.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/DECISIONS.md) before introducing structural or architectural changes.
2. **Log Units of Work:** Append commit-sized accomplishments to [`CHANGES.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/CHANGES.md) using its template. Do not overwrite or summarize past entries.
3. **Record Architectural Decisions:** Record material architectural decisions or rejected paths in `DECISIONS.md`.
4. **Commit Locally by Default:** Complete, verified units of work must culminate in a task-scoped Git commit:
   - Check `git status --short --branch` and diffs before staging.
   - Stage **only** files owned by the active task. Never execute bulk staging (`git add .` / `git add -A`) in dirty worktrees.
   - Use conventional commit syntax: `feat(scope): ...`, `fix(scope): ...`, `refactor(scope): ...`.
   - Never push, rebase, or rewrite remote history unless explicitly requested by the operator.
5. **Protect Uncommitted Work:** If `git status` reveals unrelated uncommitted modifications from another contributor, flag it immediately rather than writing over them.

---

## 10. Related Documents & Deep References

* [`README.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/README.md) — Human-facing project overview, visual architecture, and quickstart.
* [`docs/architecture.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/architecture.md) — Core architectural rationale ("why", not "what").
* [`docs/frontend-behavior-spec.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/frontend-behavior-spec.md) — Conversational UX contract for Discovery & Content Architect.
* [`CHANGES.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/CHANGES.md) — Append-only chronological change history.
* [`DECISIONS.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/DECISIONS.md) — Architecture decisions and rejected alternatives ledger.
* [`docs/project-status.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/project-status.md) — Release and milestone tracking.
* [`docs/deployment/`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/deployment/) — Deployment architecture, CI/CD runbooks, and issue registry.
* [`src/oryxenai/agents/discovery/README.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/discovery/README.md) — Discovery routes, prompts, and states.
* [`src/oryxenai/agents/content_architect/README.md`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/content_architect/README.md) — Content Architect planning pipeline.
