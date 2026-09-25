# Active Agent Workflow and Data Contracts

This document describes the active portfolio workflow and its contracts. Verify implementation details against the source files named below when they change.

## Workflow

The active journey starts with Discovery and proceeds to Content Architect after the user approves the Discovery brief. Both transitions are explicit user actions. Content Architect approval is the terminal state of the current product workflow.

## Discovery

Discovery accepts user intake and supplied reference material, asks adaptive questions, and produces a Markdown brief with a structured profile. The user can answer or skip questions, request the brief early, revise it, and approve it. Approval records an immutable content hash and a session revision.

The agent implementation, schemas, state machine, prompts, and service are in src/oryxenai/agents/discovery/. The API contract is defined by the Discovery routes in src/oryxenai/api/routes/discovery.py.

## Content Architect

Content Architect starts only after Discovery approval. Its input is a compact approved snapshot with the source hash and session revision; raw intake and document text are not passed to this agent. It runs as one durable job and makes up to three sequential model calls: plan_content, optionally write_pages, and optionally integrate_content.

The output contains the site narrative, route plan, page content packs, claim grounding, publication decisions, and review notes. The user can revise the result or approve its public scope. Approval records the content hash used by later application features.

The implementation, schemas, state machine, prompts, validators, and service are in src/oryxenai/agents/content_architect/. Its API contract is defined by src/oryxenai/api/routes/content_architect.py.

## Request and persistence boundaries

The browser calls the API through frontend/src/data/api-client.ts. The product shell restores the session and both stage states through frontend/src/app/AppShell.tsx. Stage adapters validate public envelopes before building view models.

Session state, agent runs, job inputs, outputs, and safe errors are persisted by the existing database and durable job layers. Agent code does not receive database sessions or HTTP requests. Workers reauthorize trusted session ownership before executing portfolio work.

## Operational checks

Use the canonical lint, format, type-check, and test commands in AGENTS.md. Tests exercise the deterministic model client by default; live provider workflows are separate and opt-in unless a user explicitly requests live generation.