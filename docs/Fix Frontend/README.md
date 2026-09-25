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
13. [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md) — forensic, research-backed handoff for MCQ and free-text Discovery questions.

## Visual references

The [visuals/](visuals/) folder contains generated UI reference images, not production assets. Read [visuals/README.md](visuals/README.md) and [visuals/prompts.md](visuals/prompts.md) alongside the screen specification. The Markdown files remain authoritative for exact copy, data fields, state behavior, accessibility, and responsive constraints.

- [01-shell-overview.png](visuals/01-shell-overview.png)
- [02-discovery-intake.png](visuals/02-discovery-intake.png)
- [03-discovery-review.png](visuals/03-discovery-review.png)
- [04-content-route-review.png](visuals/04-content-route-review.png)
- [12-admin-control-center.png](visuals/12-admin-control-center.png)
- [16-discovery-mcq-question.png](visuals/16-discovery-mcq-question.png)
- [17-discovery-text-question.png](visuals/17-discovery-text-question.png)

The copied current-state screenshots used by the Discovery question research are in [evidence/](evidence/).


## Baseline

The evidence baseline is the evidence-only audit in [../current-frontend-audit/README.md](../current-frontend-audit/README.md). It contains the screenshot set, DOM measurements, issue register, console findings, network findings, responsive observations, and accessibility observations.

## Non-negotiable boundaries

- Keep authentication, ownership, entitlements, server-authoritative approvals, revision checks, idempotency keys, worker fencing, and the current media security policy intact.
- Keep the workflow explicit: approving Discovery makes Content Architect available for a separate start action, and Content Architect approval ends the active workflow.
- Do not expose raw model reasoning, prompts, provider internals, worker payloads, or raw JSON in the normal creator experience.
- Do not loosen the current self-only image/font CSP to load external media.
- Work with the existing Preact, TypeScript, Vite, vanilla CSS, FastAPI, and durable PostgreSQL job architecture.
