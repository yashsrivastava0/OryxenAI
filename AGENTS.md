# OryxenAI — Project Context

This is the canonical, cross-tool context file for OryxenAI. Read this first
— before `README.md`, before exploring the code — regardless of which AI
coding tool or model you are (Claude Code, OpenAI Codex CLI, Google
Antigravity, Cursor, or any other). This file follows the open `AGENTS.md`
standard that Codex CLI, Cursor, GitHub Copilot, and Gemini CLI all read
automatically by this exact filename.

## What OryxenAI is

OryxenAI is a portfolio-planning product. It turns a user's intent into an
approved Discovery brief and an approved Content Architect plan. The active
product and API workflow ends after content approval; the repository does not
currently generate or serve a finished portfolio site.

## Current implementation status

**Discovery** is implemented end to end. It has durable jobs, worker
lifecycle, session-state persistence, five API operations, and an authenticated
product experience. Discovery stops after explicit brief approval. It does not
auto-start another stage. Its intake, answers, and brief are JSONB on session
state; output validation checks the transport envelope while the brief itself
remains free Markdown text. The prompt set has a shared system prompt and two
operation prompts. See src/oryxenai/agents/discovery/README.md for routes
and state transitions.

**Content Architect** is implemented end to end as the second and final
active stage. It consumes only an approved Discovery snapshot, requires
Discovery approval to start, and runs as one durable job. The agent makes one
to three sequential model calls internally (plan_content, optionally
write_pages, optionally integrate_content). It has no chat UI and is
started only through its explicit API. Its output remains reviewable and
requires explicit approval. See
src/oryxenai/agents/content_architect/README.md for routes and state
transitions.

Every model call uses the provider-neutral ModelClient boundary and the
profiles in config/models.toml. Treat that configuration as the source of
truth for provider and model selection; prose may be stale.

**Authentication and ownership** include local foundations for identity
verification, just-in-time account admission, username onboarding,
owner-scoped sessions, administrator access, account lifecycle, durable-work
authorization, and worker fencing. Normal users are restricted to their
entitled portfolio session. Administrative cleanup removes associated stored
artifacts when requested. Check src/oryxenai/auth/ for current enforcement.

**Product UI** is the authenticated Discovery and Content Architect
workspace. Session and run projections expose only the active workflow's
fields. Historical database records and stored output remain available to
authorized cleanup and audit paths; they are not active stages and are not
returned as current product state.

**Deployment** configuration describes the app, PostgreSQL, migrations,
worker, and HTTPS reverse proxy. Repository changes do not deploy themselves.
Check docs/deployment/ for the separately maintained release and acceptance
status; do not infer a live state from local source.

## Deliberately excluded behavior

- No automatic stage chaining or agent supervisor; callers explicitly start
  each active stage.
- No generated-site runtime, public portfolio publishing, or browser preview
  in the active product.
- Normal tests use deterministic fixtures. Live model calls are opt-in except
  when an operator explicitly asks to run the configured model workflow.
- No Redis, Celery, Kafka, or external queue; durable jobs use PostgreSQL.

## Config-driven policy — never hardcode

- **Secrets** (POSTGRES_PASSWORD, provider keys) live only in .env, which
  is git-ignored. .env.example contains empty placeholders. Never log,
  return, or display secrets.
- **Non-secret settings** live in config/app.toml and its environment
  overlays.
- **Model profiles** live in config/models.toml. Provider, base URL, model,
  and credential environment-variable names are configuration, not business
  logic.
- **Migration URL** is resolved from settings, not hardcoded in alembic.ini.
- Never freeze a model name, test count, or implementation snapshot in prose.
  Point to the configuration, test command, or active source directory.

## Repository map

    src/oryxenai/
      main.py                    FastAPI application factory
      core/                      settings, logging, lifecycle
      db/                        async engine, models, repositories
      jobs/                      durable PostgreSQL queue, worker, heartbeat
      agents/shared/             contracts, registry, executor, model client
      agents/discovery/          active intake and brief workflow
      agents/content_architect/  active content planning workflow
      auth/                      identity, ownership, entitlements, admin lifecycle
      api/routes/                active session and stage APIs
      web/                       product shell and static assets
      storage/                   archival cleanup interfaces
    frontend/                    authenticated Preact/TypeScript/Vite product
    config/                      committed non-secret TOML
    migrations/                  Alembic schema history
    tests/                       unit, API, integration, and worker tests
    scripts/                     cross-platform launch and maintenance tools

## Database and migration ownership

- Migrations live under migrations/ and are applied with
  uv run alembic upgrade head.
- The application database is oryxenai; integration tests use the separate
  oryxenai_test database.
- Docker runs migrations once in a dedicated service before the app and
  worker start. The app and worker entrypoints do not run migrations.
- Historical run and artifact records are preserved. Current projections
  filter them from active state and run APIs.

## Worker and job semantics

- Jobs are durable PostgreSQL rows in background_jobs.
- Execution is at least once; handlers must be idempotent.
- Claiming uses SELECT … FOR UPDATE SKIP LOCKED.
- Retries use exponential backoff with configurable limits; stale leases are
  recovered through heartbeat expiry.
- Active handlers include the system worker probe, Discovery operations,
  Content Architect builds, and legacy Discovery aliases needed for existing
  queued payloads. The registry is the source of truth for claimable work.
- Start the worker with scripts/run-worker.ps1 or
  uv run python -m oryxenai.jobs.worker.
- Lifecycle: validate settings, heartbeat, poll and claim, execute handlers in
  independent sessions, then shut down gracefully.

## Current request-to-database flow

    Browser → FastAPI
      → authenticate and authorize the portfolio session
      → store intake or answers and enqueue an explicit stage job
      → worker loads the run input, calls the configured model, and applies the
        result with a session revision check
      → browser polls state and lets the user review, revise, and approve
      → approved Content Architect output is the end of the active workflow

The authenticated product bootstrap restores the Supabase session, resolves a
safe local identity, then loads the owner-scoped workspace. Agent code does
not receive database sessions or HTTP requests. Agent input, output, state
snapshots, and safe errors are persisted as JSONB.

## Canonical local commands

    .\scripts\bootstrap.ps1
    .\scripts\run-native.ps1 migrate
    .\scripts\run-native.ps1 dev
    .\scripts\run-api.ps1
    .\scripts\run-worker.ps1
    .\scripts\test.ps1
    .\scripts\check.ps1
    .\scripts\doctor.ps1

## Canonical verification commands

    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src
    uv run pytest
    uv run alembic upgrade head

Database-backed tests require PostgreSQL. Integration tests must use the
dedicated test database and must never drop or reset the application database.

## Where tests belong

All tests live under tests/:

    tests/unit/          pure unit tests, no database
    tests/api/           FastAPI endpoint tests
    tests/integration/   PostgreSQL-backed repository and job tests
    tests/worker/        worker claim, retry, shutdown, and concurrency tests

## Fresh-machine setup and secrets policy

Read this before doing anything on a machine (or for a person) that has
never touched this repo, and before handling any credential on any machine.

### Getting a new machine working

1. Clone the repo and read this file in full before exploring code.
2. Run `.\scripts\bootstrap.ps1` to install dependencies into
   `.workspace/venv`.
3. Copy `.env.example` to `.env` and fill in only the secrets *you* need.
   Most work — the full test suite, running the app/worker locally, and
   Discovery/Content Architect against the
   deterministic mock model client — needs no real model API key at all.
   **Never copy another device's `.env` wholesale**; enter your own values.
4. `.\scripts\run-native.ps1 migrate`, then `.\scripts\run-native.ps1 dev`
   (or the individual `run-api.ps1` / `run-worker.ps1` scripts).
5. Run `.\scripts\test.ps1` and `.\scripts\check.ps1` before your first
   commit to confirm the environment is sound.
6. For anything deployment- or CI-related, read, in this order:
   [`docs/deployment/README.md`](docs/deployment/README.md) →
   [`docs/deployment/ci-cd-runbook.md`](docs/deployment/ci-cd-runbook.md) →
   [`docs/deployment/deployment-issues.md`](docs/deployment/deployment-issues.md).
   The current release and acceptance state are tracked in the deployment
   documents. See "Branch workflow: `staging` vs `deployment`" below before
   opening or merging any PR.

### Branch workflow: `staging` vs `deployment`

Two long-lived branches, two different jobs. Get this wrong and you either
block your own work with unnecessary ceremony, or trigger a live production
deploy nobody asked for.

- **`staging`** — day-to-day development. Branch off it (or off `deployment`
  if you're starting genuinely new work), commit, push, open PRs, merge into
  `staging` freely. GitHub Actions still runs the full quality gate (lint,
  type-check, tests, Docker smoke test) on every push/PR here — that's your
  verification — but pushing to `staging` **can never trigger a live
  deploy**, by construction: `.github/workflows/ci.yml`'s `deploy` job only
  fires when `github.ref == 'refs/heads/deployment'`. No amount of pushing
  to `staging` touches the Azure VM.
- **`deployment`** — production. This is the *only* branch wired to the
  Azure VM's self-hosted runner; merging into it is what goes live. It has
  branch-protection rules (`deployment-ci-gate`) blocking direct pushes from
  anyone, including the repo owner — the only way in is a PR.
- **Promotion from `staging` to `deployment` is a separate, explicit,
  human-initiated step, every single time.** An AI agent must never open a
  PR targeting `deployment`, and must never merge one, unless the operator
  has said so *in that session* — "push this," "deploy this," "promote to
  production," or equivalent. A previous session's approval, a standing
  habit, or "it's probably fine since the last one worked" do not count.
  When that instruction comes: open a PR from `staging` (or the exact commit
  the operator names) into `deployment`, wait for the quality gate to go
  green, then merge with `gh pr merge --merge` (never `--squash`/`--rebase`
  — see `docs/deployment/ci-cd-runbook.md`). That merge is what triggers the
  live redeploy; there is no separate "now actually deploy" step after it.
- If you're not sure whether the operator's instruction counts as that
  explicit go-ahead, ask — don't guess in the direction of deploying.

### Secrets: what's a secret, where it lives, what to never do

- `.env` (and any `.env.*` variant) is git-ignored everywhere in this repo
  — confirmed via `.gitignore`. `.env.example` documents every expected
  name with an empty placeholder, never a working value. This is the only
  place real secrets belong locally: `POSTGRES_PASSWORD`,
  `SUPABASE_SECRET_KEY`, `R2_SECRET_ACCESS_KEY`, model-provider API keys.
- The Azure VM's production `.env` is a separate, VM-local file created
  interactively by `./scripts/azure-deploy.sh setup`/`configure`. No GitHub
  Secret holds it, and the CI `deploy` job never touches it directly —
  only through the script, which reads it locally on the VM.
- CI's own Docker smoke test uses a disposable throwaway `.env` built from
  `.env.example` plus synthetic placeholder values (fake admin emails, a
  fake Supabase URL) — never real secrets — and deletes it at the end of
  every run regardless of outcome.
- **This repository is public.** Never paste a real secret value into an
  AI chat, a commit, a log line, or anything a CI job might print.
  `scripts/azure-deploy.sh`'s `credential_free_logs()` enforces this
  automatically on every deploy: it scans Compose logs for every
  configured secret before a release is considered live and blocks the
  deploy if it finds one, printing only a container name, value length,
  and SHA-256 hash for diagnosis — never the value itself. Preserve that
  property in any future change to that function.
- **Never** run `cp .env.example .env` (or anything else that overwrites
  `.env`) without backing up the existing file first and verifying the
  backup with a checksum — a working `.env` holds live secrets that cannot
  be reconstructed from the repo if lost.
- An AI agent should never read, SSH to fetch, or attempt to reconstruct
  the VM's real `.env` contents. If a deploy fails with `Missing .env; run
  setup first.`, that means the operator needs to run `setup`/`configure`
  themselves (both prompt interactively for secrets) — an agent should
  stop and say so, not try to work around it.

### What an AI agent should always ask the operator before doing

- Opening a PR that targets `deployment`, or merging one — **every single
  time**, no exceptions for routine-looking changes. See "Branch workflow"
  above. Day-to-day work belongs on `staging`, which needs no such
  permission.
- Rotating, entering, or changing any secret, on any machine.
- SSHing into the Azure VM for anything beyond read-only diagnostics
  (`status`, `logs`, `doctor`) already run through the documented script.
- Widening what a CI job or deploy script is allowed to print, touch, or
  expose publicly.
- Anything `docs/deployment/deployment-issues.md`'s own operating rules or
  `DECISIONS.md` mark as requiring explicit operator sign-off.

## Multi-agent collaboration protocol

Multiple AI tools, models, and devices work on this repo. To keep them
consistent:

1. **Check `DECISIONS.md` first** before making an architectural choice that
   might already have been decided or explicitly rejected.
2. **Log commit-sized work to `CHANGES.md`.** After finishing a real unit of
   work (a feature, a fix, a refactor, an architecture/schema change) —
   roughly what would earn its own git commit message — append one compact
   entry per `CHANGES.md`'s own template (append-only; AI agents must never
   auto-compact `CHANGES.md`). Do
   not log every individual file save. If it's unclear whether something
   counts as "major" enough to log, **ask the user** rather than guessing.
   For deployment/CI-pipeline work specifically (the Azure VM, GitHub
   Actions, Docker Compose, the `deployment` branch's required checks),
   also update
   [`docs/deployment/deployment-issues.md`](docs/deployment/deployment-issues.md)
   after every session — **on both success and failure** — following its
   compact schema and strict < 400 lines context budget (convert resolved
   blockers to the compacted ledger upon success; never write narrative essays).
   That file's high-density diagnostic detail (exact errors, root causes,
   fixes, commit SHAs) belongs there, not in `CHANGES.md`; `CHANGES.md` still
   gets its own short summary entry for the commit-sized outcome.
3. **Log real decisions to `DECISIONS.md`**, not routine implementation
   choices — same rule: ask if unsure.
4. **Never hardcode** a model name, provider, API key env-var value, test
   count, or "currently implemented" snapshot anywhere — follow the
   config-driven policy above.
5. **Commit completed major work locally by default.** A finished, verified
   unit that qualifies for `CHANGES.md` must end with a task-scoped Git commit;
   the agent does not wait for a separate “commit this” request. Use a concise
   conventional subject such as `feat(scope): outcome`, `fix(scope): outcome`,
   or `refactor(scope): outcome`, and report the resulting commit hash.
   - At the start and again before staging, inspect `git status --short
     --branch`, the relevant `git diff`, and the staged diff. Treat every
     pre-existing tracked or untracked change as another contributor's work.
   - Stage only files or exact hunks owned by the completed task. Never use
     `git add .` or `git add -A` in a dirty multi-agent worktree unless the user
     explicitly requests one complete-state commit. Never include `.env`,
     secrets, caches, `node_modules`, build output, or unreviewed tool files.
   - Before committing, run the task's verification, `git diff --cached
     --check`, and review `git diff --cached --stat` plus the complete staged
     patch. If an already-dirty file cannot be separated safely, do not absorb
     another contributor's edits: commit the isolatable work and report the
     exact overlapping files as the blocker for the remainder.
   - A local commit is not a push. Never push, amend, rebase, reset, or rewrite
     history unless the user explicitly requests it. After committing, show
     `git log -1 --oneline` and the remaining `git status --short` so unfinished
     or unrelated work stays visible.
6. **Minimize how long real work sits uncommitted.** A local commit costs
   nothing and is the only real protection against losing work to an
   accidental delete, overwrite, or filesystem operation outside git — git
   history survives all of those; an unprotected working tree does not (this
   rule exists because exactly that happened: a day of uncommitted work was
   briefly exposed to total loss by a Windows Explorer delete before it was
   recovered via `git restore` plus a Recycle Bin restore — see `CHANGES.md`,
   2026-09-04).
   - At the start of a session, if `git status` shows non-trivial
     pre-existing uncommitted changes unrelated to the current task, flag it
     to the user rather than silently building more work on top of an
     unprotected worktree.
   - Commit locally at natural checkpoints — end of a work session, after a
     meaningful chunk of work, or before any bulk filesystem operation
     (drag-drop, `rm -rf`, antivirus quarantine, a large refactor) — even if
     the change doesn't yet meet the `CHANGES.md` "major work" bar. Rule 2's
     `CHANGES.md`/`DECISIONS.md` logging stays reserved for commit-sized
     units; the local commit itself should happen more often than that.
   - Push to the remote regularly too, not just commit locally — a local
     commit protects against working-tree loss but not against losing the
     whole machine or disk. Don't let a branch drift many commits ahead of
     `origin` for extended periods; ask the user before pushing if it's
     unclear whether they want that branch published yet. This "push
     regularly" guidance is about `staging`/feature branches, which is safe
     and expected — it never overrides "Branch workflow: `staging` vs
     `deployment`" above, which still requires explicit per-instance
     permission for anything touching `deployment`.

## Related documents

- [`README.md`](README.md) — human-facing developer setup and usage.
- [`docs/architecture.md`](docs/architecture.md) — architectural rationale
  ("why", not "what").
- [`docs/frontend-behavior-spec.md`](docs/frontend-behavior-spec.md) — the
  conversational/UX contract for the Discovery/Content Architect chat flow.
- [`CHANGES.md`](CHANGES.md) — change history (who/what/where/when/why).
- [`docs/project-status.md`](docs/project-status.md) — current implemented,
  pending, Azure, and next-step handoff.
- [`docs/deployment/README.md`](docs/deployment/README.md) — deployment index
  and one-VM operational path.
- [`docs/deployment/deployment-issues.md`](docs/deployment/deployment-issues.md)
  — timestamped log of every CI/CD and Docker Compose bug found and fixed
  (or still open); update it after every deployment/CI session per the
  multi-agent collaboration protocol below.
- [`DECISIONS.md`](DECISIONS.md) — decisions, rejected alternatives, and
  open/deferred items.
- [`CODEX.md`](CODEX.md) and [`CLAUDE.md`](CLAUDE.md) — short redirects to
  this file for tools/habits that look for those names specifically.
