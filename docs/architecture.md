# OryxenAI architecture

This note explains the boundaries used by the current repository. Read
AGENTS.md for the canonical project context and the active stage READMEs for
their detailed contracts.

The earlier proposal and its rationale are in
[the research and review guide](architecture/README.md),
[system design](architecture/10-proposed-resume-portfolio-system.md), and
[agent contracts](architecture/11-agent-and-artifact-contracts.md).
The stage READMEs describe the running implementation.

## 1. Explicit Python agents

The active workflow has three agents: Explorer, Content Architect, and Code Generator. They are
ordinary Python implementations of shared protocols, not a framework-managed
graph. The shared executor persists runs, dispatches jobs, and applies state
changes; agents receive structured data rather than HTTP or database objects.

## 2. Provider-neutral model boundary

Agents call the ModelClient protocol. config/models.toml provides provider,
model, endpoint, and credential-name routing. This keeps provider changes
outside agent business logic and avoids hardcoded credentials.

## 3. JSONB session state and append-oriented runs

portfolio_sessions.current_state holds current workflow state as JSONB, with
a revision used for optimistic concurrency. agent_runs records inputs,
outputs, state snapshots, safe errors, and timing for traceability. Current
API projections are limited to active schemas.

## 4. Durable PostgreSQL jobs

The API enqueues durable jobs in PostgreSQL. Workers claim due rows with
SELECT FOR UPDATE SKIP LOCKED, renew leases, retry eligible failures, and
apply successful results with revision checks. No external queue is used.

## 5. Authenticated product boundary

Supabase restores the browser identity; the server verifies it before loading
the owner-scoped workspace. Normal users can access only their sessions.
Administrator access and lifecycle actions use explicit authorization and
auditing.

## 6. Explicit workflow and approval

Explorer approval does not automatically start Content Architect. A caller
must make a separate start request. The product's explicit "Approve & generate
my portfolio" action approves the content plan and starts Code Generator.
Explorer's fixed palette choice selects one immutable stylesheet package;
Content Architect carries that selection with the approved content, and Code
Generator generates HTML against that package's markup contract. The workflow
ends with an owner-only verified Studio preview.

## 7. Current product frontend

The authenticated product uses Preact, TypeScript, and Vite and is served by
FastAPI. The browser polls persisted stage/job state. The frontend cannot
authorize actions or decide that work succeeded independently of the server.
