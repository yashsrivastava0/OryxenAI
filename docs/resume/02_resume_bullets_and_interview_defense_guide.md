# OryxenAI Resume Bullets & Interview Guide

Use only claims supported by the current repository and the candidate's own verified contribution. Avoid invented performance figures, deployment outcomes, or user counts.

## Resume project description

> **OryxenAI | Portfolio Planning Platform** ? Built an authenticated AI planning workflow that turns user intent into an approved Discovery brief and a structured Content Architect plan. Implemented durable PostgreSQL jobs, revision-checked session state, provider-neutral model access, and explicit user approvals between operations.

## Role-focused bullets

### AI systems and model integration

- Implemented bounded Discovery and Content Architect workflows with explicit Pydantic contracts, prompt boundaries, and user approval points.
- Routed model calls through a provider-neutral client and configuration-backed profiles, keeping provider selection and credentials outside agent business logic.
- Passed Content Architect only a compact approved Discovery snapshot, reducing unnecessary exposure of raw intake material.

### Backend and distributed systems

- Built durable PostgreSQL job processing with atomic claims, idempotent handlers, lease renewal, retry limits, and stale-result protection through session revisions.
- Persisted portfolio state and job payloads in PostgreSQL JSONB while retaining database transaction boundaries for state changes and job creation.
- Used explicit ownership and actor snapshots so workers can reauthorize durable work before applying results.

### Security and product architecture

- Added verified identity admission, owner-scoped portfolio access, administrator lifecycle controls, and audited cleanup operations.
- Built an authenticated Preact and TypeScript workspace for intake, review, revision, and approval of planning artifacts.
- Kept secrets in local environment configuration and exposed safe response projections instead of raw credentials or model internals.

## Interview topics

### Why use explicit approval boundaries?

The brief and content plan are meaningful user decisions. Explicit approval keeps the workflow reviewable and makes each transition visible to the user. The API starts each operation separately, so approval cannot silently create another durable job.

### How does durable work remain safe under retries?

The queue provides at-least-once execution, so handlers are idempotent. Claims are transactional, leases support recovery, and session revisions reject results computed against stale state. Trusted ownership snapshots let the worker reauthorize before applying a result.

### How can the model engine be replaced?

The provider-neutral `ModelClient` boundary separates agent contracts from model transport. Provider, endpoint, model, and credential environment-variable name come from `config/models.toml`. A replacement must preserve the structured response contract, prompt separation, configured limits, and safe error handling.

### How is source material protected?

Discovery treats user documents as untrusted input and persists intake in the owned session. After approval, Content Architect receives a compact approved snapshot rather than the original raw documents. Logs and API responses avoid secrets and internal model data.

## Evidence to verify before using a claim

- Check `config/models.toml` for current model profiles.
- Check the active agent directories and route registry for supported operations.
- Use the repository's test and check commands for current verification coverage.
- Describe deployment as implemented only when confirmed by the deployment records and operator acceptance.
