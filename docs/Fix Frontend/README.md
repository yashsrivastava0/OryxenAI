# OryxenAI Frontend Remediation Research Pack

This folder is the implementation handoff for the OryxenAI frontend remediation. It turns the current browser audit, source inspection, runtime findings, and visual direction into an evidence-linked specification for the implementing AI.

## Read in this order

1. [00-research-notes.md](00-research-notes.md) — product posture and external research.
2. [01-forensic-root-causes.md](01-forensic-root-causes.md) — the ten systemic causes behind FE-001 through FE-020.
3. [02-evidence-map.md](02-evidence-map.md) — issue-by-issue evidence links and remediation targets.
4. [03-runtime-state-and-api-contract.md](03-runtime-state-and-api-contract.md) — state, polling, job, failure, and approval rules.
5. [04-shell-information-architecture.md](04-shell-information-architecture.md) — replacement shell and information architecture.
6. [05-screen-by-screen-specification.md](05-screen-by-screen-specification.md) — stage-by-stage screen behavior.
7. [06-component-and-view-model-contracts.md](06-component-and-view-model-contracts.md) — shared components and adapter contracts.
8. [07-responsive-accessibility-and-error-states.md](07-responsive-accessibility-and-error-states.md) — responsive and inclusive behavior.
9. [08-acceptance-matrix.md](08-acceptance-matrix.md) — measurable acceptance criteria.
10. [09-implementation-runbook.md](09-implementation-runbook.md) — ordered implementation and verification sequence.
11. [10-admin-console-specification.md](10-admin-console-specification.md) — administrator-only screen, controls, confirmations, and safety boundary.
12. [11-implementation-file-map.md](11-implementation-file-map.md) — screen-to-source map and implementation checklist for the next AI.

## Visual references

The [visuals/](visuals/) folder contains generated UI reference images, not production assets. Read [visuals/README.md](visuals/README.md) and [visuals/prompts.md](visuals/prompts.md) alongside the screen specification. The Markdown files remain authoritative for exact copy, data fields, state behavior, accessibility, and responsive constraints.

- [01-shell-overview.png](visuals/01-shell-overview.png)
- [02-discovery-intake.png](visuals/02-discovery-intake.png)
- [03-discovery-review.png](visuals/03-discovery-review.png)
- [04-content-route-review.png](visuals/04-content-route-review.png)
- [05-design-storyboard.png](visuals/05-design-storyboard.png)
- [06-preparation-ready.png](visuals/06-preparation-ready.png)
- [07-generation-available.png](visuals/07-generation-available.png)
- [08-generation-working.png](visuals/08-generation-working.png)
- [09-generation-attention.png](visuals/09-generation-attention.png)
- [10-mobile-review.png](visuals/10-mobile-review.png)
- [11-output-inspector.png](visuals/11-output-inspector.png)
- [12-admin-control-center.png](visuals/12-admin-control-center.png)

## Baseline

The evidence baseline is the evidence-only audit in [../current-frontend-audit/README.md](../current-frontend-audit/README.md). It contains the screenshot set, DOM measurements, issue register, console findings, network findings, responsive observations, and accessibility observations.

The audit tested the real FastAPI, worker, preview gateway, PostgreSQL, and authenticated product flow. It reached the Code Generator planning failure and recorded the resulting frontend freeze. The repository does not contain browser recordings; where a recording would normally be cited, the screenshot, measurement, or runtime evidence is called out explicitly.

## Non-negotiable boundaries

- Keep authentication, ownership, entitlements, server-authoritative approvals, revision checks, idempotency keys, worker fencing, and preview isolation intact.
- Do not introduce automatic stage chaining. A combined `Approve & continue` button remains one explicit user command that performs guarded server operations.
- Do not expose raw model reasoning, prompts, provider internals, worker payloads, or raw JSON in the normal creator experience.
- Do not loosen the current self-only image/font CSP to make external previews work.
- Do not fabricate Visual Design Director hex colors, palette tokens, font names, or specimens. The stage emits design intent and scene direction, not literal token values; this follows DECISIONS.md D-095.
- Work with the existing Preact, TypeScript, Vite, vanilla CSS, FastAPI, and durable PostgreSQL job architecture.
