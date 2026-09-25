# Active Model Call Boundaries & Engine Replacement Notes

This document describes the model-facing contracts used by the active portfolio-planning workflow. The authoritative provider and model settings are in `config/models.toml`; this document intentionally does not freeze provider names, model names, prices, or limits.

## Active operations

| Operation | Input boundary | Output boundary |
| --- | --- | --- |
| Discovery | User intent, answers, and source material are passed as untrusted input alongside trusted system and operation prompts. | A validated response envelope containing a question or a Markdown brief. The user must approve the brief. |
| Content Architect | A compact snapshot of the approved Discovery brief. Raw intake documents are not forwarded. | A validated structured content plan. The user must approve the plan. |

Content Architect runs as one durable job and makes a bounded sequence of internal model calls for planning, optional page copy, and optional integration. A caller explicitly starts each operation. Approval does not automatically enqueue more work.

## Replacement boundary

Model transport is isolated behind the shared `ModelClient` contract. Agent code consumes profile settings and typed request/response envelopes; it must not select a provider directly or embed API credentials. Profile configuration resolves credentials indirectly from environment-variable names.

A compatible replacement should preserve:

- trusted instructions separated from user-supplied content;
- structured response handling and the existing validation boundary;
- configured timeout, token, retry, and provider limits;
- safe error projections without returning credentials or raw internal reasoning;
- deterministic fixtures for ordinary tests, with live calls only through the configured opt-in path.

## State and privacy boundaries

Discovery persists intake and answers on the owned session and stores an approved brief snapshot for subsequent use. Content Architect receives only the approved snapshot and writes its output through the same revision-checked session workflow. The database-backed queue stores durable job payloads; worker authorization is checked before results are applied.

## Sources of truth

- `config/models.toml` for model profiles and logical routing;
- `src/oryxenai/agents/shared/` for the model-client boundary;
- `src/oryxenai/agents/discovery/` and `src/oryxenai/agents/content_architect/` for active contracts;
- the API and worker registries for currently callable operations.
