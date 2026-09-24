# OryxenAI — current project status

**Updated:** 2026-09-24
**Scope:** Current local repository behavior. Deployment state is tracked
separately under docs/deployment/.

## Active product contract

OryxenAI currently supports an explicit two-stage portfolio-planning flow:

1. Discovery gathers intake and answers, produces a brief, and waits for
   explicit approval.
2. Content Architect starts only from the approved brief, produces a content
   plan, and waits for explicit approval.

The active workflow ends when the content plan is approved. The current
product does not create, build, publish, or serve a portfolio site. Approval
never automatically starts another stage.

The stage registry and API router define what is active. Historical source
folders, database records, artifacts, fixtures, and append-only project logs
do not add stages to the current product. Current API projections expose only
supported state. Existing stored output is retained for authorized cleanup
and audit.

## Runtime and data flow

- FastAPI serves the product shell and owner-scoped API.
- PostgreSQL stores portfolio sessions, JSONB stage state, run snapshots,
  durable jobs, model usage, and authorization records.
- A separate worker claims registered jobs with row locking, renews leases,
  and records safe results or errors.
- Discovery and Content Architect call models through the provider-neutral
  ModelClient boundary. config/models.toml is the source of truth for routing.
- Stage starts and approvals are explicit API actions. Workers reauthorize
  durable work before applying portfolio changes.
- Administrative lifecycle and cleanup are audited and resumable.

## Product and API

The authenticated product shell presents the supported planning stages.
Public session and run projections are filtered to their active schemas.
The router exposes health, authentication, session, run, diagnostics, and
supported stage APIs; use the registered route source and each active stage
README as the route contract.

The product does not expose a generated-site preview surface. Do not infer
product capability from historical preview records or old documentation.

## Authentication and ownership

The local implementation includes Supabase identity verification, account
admission, username onboarding, owner-scoped sessions, administrator access,
account lifecycle, entitlement checks, durable-work authorization, and worker
fencing. Production OAuth setup and owner-performed end-to-end acceptance are
separate from local implementation.

See src/oryxenai/auth/ for enforcement and docs/Auth/ for the authentication
design and implementation history.

## Deployment

The local source tree and a live release are separate states. This change has
not deployed anything. Use docs/deployment/deployment-issues.md and the
deployment runbooks for current release, infrastructure, and acceptance
evidence. Do not infer production state from this page or local source.

## Configuration and storage

- Secrets belong only in the ignored .env file; .env.example contains
  placeholders.
- Application settings and model profiles live under config/.
- Alembic owns database schema changes. Apply migrations explicitly before
  starting native services; Compose uses its one-shot migration service.
- Historical records and user outputs are preserved. Account or portfolio
  deletion remains an explicit, audited operation.

## Local commands

Windows PowerShell:

    .\scripts\bootstrap.ps1
    .\scripts\run-native.ps1 align-db
    .\scripts\run-native.ps1 migrate
    .\scripts\run-native.ps1 dev
    .\scripts\doctor.ps1

Docker Compose:

    docker compose up --build -d
    docker compose ps

Canonical quality commands are listed in AGENTS.md. Database-backed tests
require the dedicated test database. No application database reset is part of
normal verification.

## Current source of truth

- AGENTS.md — cross-tool context, workflow contract, repository rules.
- README.md — developer quick start.
- src/oryxenai/agents/discovery/ — Discovery implementation.
- src/oryxenai/agents/content_architect/ — Content Architect implementation.
- src/oryxenai/api/routes/__init__.py — registered API routers.
- src/oryxenai/agents/shared/registry.py — registered agent contracts.
- config/models.toml — configured model profiles and routing.
- docs/deployment/ — release and production acceptance evidence.
- CHANGES.md and DECISIONS.md — append-only historical records; history is
  not a statement of current runtime capability.
