# Implementation file map

This is the routing sheet for the implementing AI. It identifies where each screen concern currently lives and what the remediation should change or leave alone. It is not permission to rewrite the architecture.

## Global creator shell

| Concern | Current source | Required work |
|---|---|---|
| App composition, stage selection, topbar, account menu | `frontend/src/app/AppShell.tsx` | remove creator-topbar destructive admin reset; keep quiet admin link; preserve auth/session and explicit stage commands; compose shared navigator, context, dock, inspector |
| Session/request store | `frontend/src/app/store.ts` | preserve revision, ownership, read-only, and announcement behavior; add only view-model state needed by the documented UI |
| Frontend adapters | `frontend/src/data/adapters/` | keep pure; normalize states and active job from server data; preserve raw agent-owned output separately; suppress duplicate display values |
| Shared layout tokens/styles | `frontend/src/styles/shell.css`; shared product tokens/motion are served from `src/oryxenai/auth/static/tokens.css` and `src/oryxenai/auth/static/motion.css` | replace rail-heavy layout with bounded canvas, reserved dock, contained tabs, focus/reduced-motion rules; do not invent a new framework |
| Existing output rail | `frontend/src/app/AppShell.tsx` and related output components | move to closed developer-only `OutputInspector`; active selection follows current stage and never falls back to stale Discovery output |

## Stage screens

| Screen | Current source | Required representation |
|---|---|---|
| Discovery intake/questioning/review | `frontend/src/stages/discovery/DiscoveryStage.tsx` | labeled intake/answer composer, one question at a time, concise review summary, profile facts, brief reader, revision composer, visible destination-specific approval |
| Content review | `frontend/src/stages/content/ContentStage.tsx` | narrative thesis, route map, contained route tabs, one expanded route, non-duplicated section cards, revision/approval dock |

## Existing reusable components to audit

Before adding a new shared abstraction, inspect these existing components and tests:

- `frontend/src/components/WorkspaceCanvas.tsx`;
- `frontend/src/components/ContentPackExplorer.tsx`;
- `frontend/src/data/activity-copy.ts`;
- `frontend/src/stages/stages.test.ts`;
- adapter-specific tests under `frontend/src/data/adapters/`.

The target abstractions are documented in [06-component-and-view-model-contracts.md](06-component-and-view-model-contracts.md): `StageNavigator`, `StageContextStrip`, `ArtifactReview`, `ActionDock`, `OutputInspector`, `ProgressSurface`, `AttentionPanel`, and `InputComposer`.

## Discovery question routing addendum

| Concern | Current source | Required work |
|---|---|---|
| Question rendering and submit timing | `frontend/src/components/ConversationSurface.tsx` | keep one question visible; make single-select and multi-select selection local; submit only from explicit `Next question`; retain text drafts and save errors |
| Discovery callbacks and stage transitions | `frontend/src/stages/discovery/DiscoveryStage.tsx` | preserve existing callback/API semantics; distinguish answer save from worker/stage transitions |
| Question view model | `frontend/src/data/adapters/discovery.ts` | keep `DiscoveryQuestionVM` authoritative; do not invent option descriptions or limits; normalize unknown data safely |
| Question styling and geometry | `frontend/src/styles/shell.css` | add explicit selectors for question header, fieldset, option tiles, textarea, action area, focus, error, and mobile stacking |
| Question tests | `frontend/src/data/adapters/discovery.test.ts`, `frontend/src/stages/stages.test.ts`, and fixture-backed browser tests under the existing frontend test location | cover selection timing, native semantics, retained values after failure, status announcements, and target viewport geometry |

Read [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md) before making visual or interaction decisions. The two new images are visual references only; backend state and the existing authenticated API boundary remain authoritative.

## Admin surface

| Concern | Current source | Required work |
|---|---|---|
| Admin route | `src/oryxenai/auth/web.py` (`GET /admin`) | preserve route and no-store/auth headers |
| Admin HTML shell | `src/oryxenai/auth/templates/auth_shell.html` | preserve IDs/hooks; keep admin page separate from creator stages; ensure labels and dialog semantics remain intact |
| Admin controller | `src/oryxenai/auth/static/auth-admin.mjs` | preserve safe fetch, tab/cursor loading, live messages, typed confirmation, and idempotency-key behavior; add only bounded UI improvements |
| Admin styling | `src/oryxenai/auth/static/auth.css` | keep the cream/ink/cobalt family; verify mobile summary, tabs, row actions, dialog, focus, and reduced motion |
| Admin API | `src/oryxenai/auth/admin/api.py`, `src/oryxenai/auth/admin/service.py` | do not move authorization into the browser; consume the existing safe response projections |
| Admin tests | `tests/` admin/auth test files and browser boundary tests | cover role gating, self/last-admin protections, idempotency, tab data, confirmation mismatch, session expiry, and responsive DOM behavior where available |

## Evidence routing

Use [02-evidence-map.md](02-evidence-map.md) to connect each change to FE-001–FE-020. For the admin reset relocation, use the non-numbered audit observations in:

- `docs/current-frontend-audit/06-agent-state-and-action-audit.md`;
- `docs/current-frontend-audit/09-accessibility-interaction-findings.md`;
- `docs/current-frontend-audit/10-journey-and-information-architecture-findings.md`.

The image set in `visuals/` is a visual direction aid. The screenshots in `docs/current-frontend-audit/evidence/screenshots/` are the forensic baseline. Never mark an evidence row passed from a mockup alone.

## Implementation order by page

1. Establish the server projection and pure adapter behavior.
2. Replace the `/app` shell and action placement.
3. Wire the Discovery composer and destination-specific handoff labels.
4. Keep Content Architect approval terminal and preserve its explicit start boundary from Discovery.
5. Move raw output into the inspector and verify the active stage selection.
6. Audit `/admin` separately; remove only the creator-topbar reset affordance and preserve the admin console's server contract.
7. Add fixture browser coverage, then run the authenticated Discovery and Content Architect journey.
