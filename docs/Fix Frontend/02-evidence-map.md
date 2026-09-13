# Evidence map: FE-001 through FE-020

All references below point to the evidence-only audit in `../current-frontend-audit/`. The audit's [README](../current-frontend-audit/README.md), [issue register](../current-frontend-audit/03-issue-register.md), [measurements](../current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json), [console log](../current-frontend-audit/evidence/console/console_logs.txt), and [network findings](../current-frontend-audit/evidence/network/network_findings.txt) are the baseline.

| ID | Stage | Evidence | Confirmed cause | Remediation target |
|---|---|---|---|---|
| FE-001 | Generation | [generation-02-progress.png](../current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png); console/network evidence; measurements | Failed job is not reflected in the session view; adapter cannot identify the active job | Active-job projection, terminal reconciliation, adapter attention mapping, polling stop, valid retry/recovery |
| FE-002 | Content | [content-01-result-top.png](../current-frontend-audit/evidence/screenshots/content/content-01-result-top.png) | Header metadata competes with oversized H1 in a two-column header | Single-flow header with status/context below the title |
| FE-003 | Design | [design-02-result-top.png](../current-frontend-audit/evidence/screenshots/design/design-02-result-top.png) | Same header collision pattern as Content | Same single-flow header contract |
| FE-004 | Content | [content-02-result-mid.png](../current-frontend-audit/evidence/screenshots/content/content-02-result-mid.png); [content-03-actions.png](../current-frontend-audit/evidence/screenshots/content/content-03-actions.png) | All prose and sections expand linearly; action is last | Route map, tabs, selected-route sections, collapsible secondary detail, ActionDock |
| FE-005 | Discovery | [discovery-04-brief-top.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-04-brief-top.png); [discovery-05-approval-bottom.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-05-approval-bottom.png) | Full brief is mounted before decision action | Summary-first review and sticky approval dock |
| FE-006 | Design | [design-03-scenes.png](../current-frontend-audit/evidence/screenshots/design/design-03-scenes.png); [design-04-actions.png](../current-frontend-audit/evidence/screenshots/design/design-04-actions.png) | Storyboard is collapsed and action is at document end | Visible storyboard with route/scene navigation and sticky dock |
| FE-007 | Content | [content-02-result-mid.png](../current-frontend-audit/evidence/screenshots/content/content-02-result-mid.png) | Nested grid leaves a narrow body column | Remove inner TOC/rail width reservation; use readable single-column body |
| FE-008 | Preparation | [preparation-04-actions.png](../current-frontend-audit/evidence/screenshots/preparation/preparation-04-actions.png); [network_findings.txt](../current-frontend-audit/evidence/network/network_findings.txt) | External preview URLs blocked by self-only CSP | Metadata evidence tile and safe source link; no cross-origin `<img>` |
| FE-009 | Global | [discovery-03-question-active.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png) | Raw JSON utility is permanently visible in primary layout | Closed developer-only Output Inspector |
| FE-010 | Generation | [generation-01-start.png](../current-frontend-audit/evidence/screenshots/generation/generation-01-start.png) | Generation arrival does not present a usable start action | Available state with explicit Generate button; lock state names prerequisite and destination |
| FE-011 | Content | [content-02-result-mid.png](../current-frontend-audit/evidence/screenshots/content/content-02-result-mid.png) | Same source text mapped to heading and body | Adapter-level duplicate suppression and field-role rendering |
| FE-012 | Discovery | [discovery-04-brief-top.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-04-brief-top.png) | Display scale and header width force six-line title | Bounded stage title, balanced wrapping, no metadata collision |
| FE-013 | Discovery | [discovery-05-approval-bottom.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-05-approval-bottom.png) | Button lives in a narrow action cell | ActionDock with non-wrapping label on desktop and intentional full-width mobile layout |
| FE-014 | Design | [design-04-actions.png](../current-frontend-audit/evidence/screenshots/design/design-04-actions.png) | Same narrow action-cell failure | Shared ActionDock contract |
| FE-015 | Design | [design-03-scenes.png](../current-frontend-audit/evidence/screenshots/design/design-03-scenes.png) | Scene and candidate content hidden behind collapsed details | Storyboard is primary; details are secondary |
| FE-016 | Preparation | [preparation-02-result-top.png](../current-frontend-audit/evidence/screenshots/preparation/preparation-02-result-top.png) | Metrics duplicated between rail and center | One readiness context strip and one evidence summary |
| FE-017 | Global | [discovery-01-empty.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-01-empty.png); measurements | Shell padding/decorations create overflow before input | Viewport-safe shell with bounded surface and no decorative overflow |
| FE-018 | Discovery | [discovery-03-question-active.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png) | Global stepper competes with active question | Compact navigator with visible active state and sufficient stacking order |
| FE-019 | Generation | [generation-02-progress.png](../current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png) | Raw coordinator label leaks into user copy | Human-readable milestone copy and consistent spacing |
| FE-020 | Global/Generation | [generation-02-progress.png](../current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png); output rail observation | Output rail selection falls back to stale earlier output | Inspector selection keyed by active stage and cleared safely when unavailable |

## Related cross-cutting observation without a new FE ID

The audit also recorded an administrator-safety problem that is intentionally kept separate from the FE-001–FE-020 register: an admin-only `Reset Pipeline` control was visible in the ordinary creator topbar. The exact audit evidence is [06-agent-state-and-action-audit.md](../current-frontend-audit/06-agent-state-and-action-audit.md), [09-accessibility-interaction-findings.md](../current-frontend-audit/09-accessibility-interaction-findings.md), and [10-journey-and-information-architecture-findings.md](../current-frontend-audit/10-journey-and-information-architecture-findings.md). The remediation target is `frontend/src/app/AppShell.tsx`: keep the quiet account-menu link to `/admin`, remove the destructive topbar control, and preserve the server-authorized administrator confirmation flow documented in [10-admin-console-specification.md](10-admin-console-specification.md).

## Evidence interpretation rules

- Screenshot evidence describes the observed runtime, even when an uncommitted change appears to address part of it.
- A source-level change is not accepted until the corresponding browser geometry/state scenario passes.
- The audit contains no recording files; this is an evidence gap, not evidence that the behavior did not occur.
- The current audit's exact issue language and measurements remain authoritative where this pack summarizes them.

## Discovery question evidence addendum

The following supplied screenshots are copied unchanged into this pack as current-state evidence:

| Evidence | What it proves | Target |
|---|---|---|
| [discovery-question-current-01.png](evidence/discovery-question-current-01.png) | Long prompt, inline checkbox controls, weak grouping, large unused lower viewport, and an open administrator popover covering creator content | [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md), [16-discovery-mcq-question.png](visuals/16-discovery-mcq-question.png) |
| [discovery-question-current-02.png](evidence/discovery-question-current-02.png) | Same Discovery multi-select question state reproduced in a second capture; confirms the issue is not a single-frame rendering accident | [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md), [16-discovery-mcq-question.png](visuals/16-discovery-mcq-question.png) |

The canonical repository screenshot [discovery-03-question-active.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png) remains the audit source for FE-009 and FE-018. FE-017 remains measured by [scroll_and_layout_metrics.json](../current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json). The cross-cutting administrator-menu finding remains documented in [06-agent-state-and-action-audit.md](../current-frontend-audit/06-agent-state-and-action-audit.md) and [10-journey-and-information-architecture-findings.md](../current-frontend-audit/10-journey-and-information-architecture-findings.md).

The supplied screenshots are not production assets and must not be copied into the creator UI. They are evidence of the previous state only.

### Explicit issue and safety routing

| Finding | Exact evidence | Implementation target |
|---|---|---|
| FE-009 — permanent developer utility rail | [discovery-03-question-active.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png), [FE-009 issue record](../current-frontend-audit/03-issue-register.md#fe-009-developer-handoff-utility-dominates-primary-right-column) | Remove the permanent raw-JSON rail from the creator question surface; use the closed-by-default developer-only Output Inspector. |
| FE-017 — initial empty-screen scrollbar | [scroll_and_layout_metrics.json](../current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json), [FE-017 issue record](../current-frontend-audit/03-issue-register.md#fe-017-vertical-scrollbar-present-on-empty-intake-screen) | Contain shell height, remove decorative overflow, reserve only the action space needed by the question, and verify all four target viewports. |
| FE-018 — obscured/washout stepper | [discovery-03-question-active.png](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png), [FE-018 issue record](../current-frontend-audit/03-issue-register.md#fe-018-stepper-navigation-obscured-behind-question-card) | Keep the compact stage navigator above the question canvas with stable contrast and no overlap or z-index competition. |
| Administrator-menu obstruction / destructive reset exposure | [discovery-question-current-01.png](evidence/discovery-question-current-01.png), [discovery-question-current-02.png](evidence/discovery-question-current-02.png), [administrator action audit](../current-frontend-audit/06-agent-state-and-action-audit.md#b-reset-pipeline-dangerous-action-top-navigation-bar), [journey/IA finding](../current-frontend-audit/10-journey-and-information-architecture-findings.md#4-problem-family-d-developer-tooling-dominates-user-workspace) | Keep the creator account menu closed by default, remove destructive reset from creator navigation, and route authorized administration to the separate `/admin` surface. |
