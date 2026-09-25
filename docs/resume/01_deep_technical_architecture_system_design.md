# OryxenAI: Technical Architecture & System Design

This overview describes the active portfolio-planning product. It accepts a user's intent, produces an approved Discovery brief, and then produces an approved Content Architect plan. Those planning artifacts are the product output.

## Product workflow

1. **Discovery** gathers the user's goals and source material, asks focused questions, and builds a reviewable brief. The user approves the brief explicitly.
2. **Content Architect** consumes only the approved Discovery snapshot, plans the portfolio structure and copy, and saves a reviewable output. The user approves that output explicitly.
3. Each operation is started by an explicit caller. Approval does not start another operation automatically.

Agent state is persisted on the owned portfolio session. A revision check prevents stale worker results from replacing newer user state. Agent implementations do not receive HTTP requests or database sessions.

## Durable work and state

Background work is stored in PostgreSQL. Workers claim due jobs with `FOR UPDATE SKIP LOCKED`, execute idempotent handlers, renew leases, and retry according to configured limits. Job creation and session changes use database transactions; stale results are rejected through session revisions and source snapshots.

Session state and job inputs/outputs use JSONB. Approved Discovery data is a compact, hash-stamped snapshot. Content Architect reads that approved snapshot instead of the raw resume or document text.

## Model boundary

Agents call models through the provider-neutral `ModelClient` interface. Profiles in `config/models.toml` provide provider, endpoint, model, and credential-environment-name settings. Agent business logic does not select a provider or embed credentials.

Discovery uses separate trusted system and operation prompts, sends user material as untrusted input, and validates the response envelope while allowing the brief body to remain Markdown. Content Architect uses a bounded sequence of planning calls and validates the structured response contracts at the boundary.

## Authentication and ownership

The API verifies Supabase-issued identity tokens, admits users through local account policy, and exposes owner-scoped portfolio sessions. Administrator operations are audited and use explicit lifecycle services. Durable work carries trusted owner and actor snapshots; workers reauthorize those snapshots before applying results.

Secrets remain in `.env`; non-secret application settings and model profiles remain in committed configuration. API responses and logs use safe projections rather than credential values or raw model internals.

## Product frontend and operations

The authenticated Preact and TypeScript workspace supports Discovery and Content Architect review. FastAPI serves the product API; a separate worker runs durable jobs. Compose starts PostgreSQL, applies migrations in a dedicated service, and then starts the API and worker.

Use repository commands and current configuration as the source of truth for setup and verification. Do not infer provider choices, release state, or test coverage from this overview.
