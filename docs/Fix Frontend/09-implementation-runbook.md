# Implementation runbook

Before changing code, read [11-implementation-file-map.md](11-implementation-file-map.md) and [10-admin-console-specification.md](10-admin-console-specification.md). The file map is a routing aid; the backend and existing tests remain authoritative.

## Phase 1: establish the safe state contract

1. Inspect the current dirty worktree and preserve unrelated contributor changes.
2. Add Code Generator active-job and retry-eligibility projection.
3. Reconcile terminal handler/timeout failures into a safe run attention state when no retry remains.
4. Correct the frontend adapter to select the active job by job ID.
5. Add adapter and worker/API regression tests for failed planning, timeout exhaustion, cancellation, and retry eligibility.

Exit condition: the audit's failed Code Generator job stops polling, displays attention, preserves prior preview data, and exposes only a server-valid recovery action.

## Phase 2: replace the shell geometry

1. Remove the permanent three-column composition from the product surface.
2. Introduce the compact StageNavigator, StageContextStrip, single stage canvas, ActionDock, and closed OutputInspector.
3. Keep the existing boot/auth seam, URL stage selection, error boundary, connection notices, and account behavior.
4. Reduce title scale, remove absolute badge placement, and constrain prose width.
5. Make the ActionDock sticky with reserved layout space at desktop, tablet, and mobile widths.

Exit condition: no title collisions, no permanent empty-screen scrollbar, no narrow body column, and no action four-line wrap in all target viewports.

## Phase 3: rebuild stage representations

1. Discovery: summary-first review, profile facts, brief reader, and action dock.
2. Content: route map, route tabs, selected-route section cards, deduplicated copy, and secondary details.
3. Design: thesis, intent cards, route selector, visible storyboard, and asset treatments without fabricated tokens.
4. Preparation: readiness summary, metadata evidence cards, brief readers, and CSP-safe fallback tiles.
5. Generation: available start state, semantic progress, attention recovery, and preview theater.

Exit condition: every stage presents its native artifact before secondary prose or developer data.

### Discovery question execution detail

Before moving to the later stage representations:

1. Preserve `DiscoveryQuestionVM` and the existing answer endpoint.
2. Refactor `ConversationSurface` so single-select selection is local and explicit `Next question` performs submission.
3. Render single-select/boolean as native radio groups and multi-select as native checkbox groups inside full-row selectable tiles.
4. Keep the existing text draft persistence, but give the textarea a visible label, bounded copy, and an action that remains above the fold.
5. Add explicit question selectors to the frontend stylesheet; do not rely on browser-native button/checkbox presentation.
6. Replace the broad active-card live region with a transition-only status element and preserve focus across polling.
7. Add fixture-backed browser scenarios for selection timing, retained values after failure, keyboard operation, and the four viewport sizes.
8. Compare the implementation against [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md), [16-discovery-mcq-question.png](visuals/16-discovery-mcq-question.png), and [17-discovery-text-question.png](visuals/17-discovery-text-question.png). Treat the Markdown behavior contract as authoritative when a mockup is ambiguous.

## Phase 4: responsive and accessibility hardening

1. Validate desktop, short laptop, tablet, and mobile compositions.
2. Contain route-tab overflow and remove page-level horizontal scrolling.
3. Add focus management for inspector/drawers and preserve focus during polling.
4. Reduce live-region scope to meaningful status changes.
5. Verify reduced motion, contrast, labels, and keyboard actions.

Exit condition: all responsive and accessibility checks in `08-acceptance-matrix.md` pass.

## Phase 5: evidence-driven verification

1. Run the existing frontend and backend test suites.
2. Run fixture-backed browser tests with the target viewport matrix.
3. Repeat the authenticated journey using privacy-safe audit data.
4. Recheck console/network output for blocked media, uncaught errors, and repeated polling after terminal state.
5. Update the evidence matrix only with observed results; do not claim a screenshot or measurement was validated without running it.

6. Validate the separate administrator shell: remove the creator-topbar reset affordance, preserve the account-menu Administration link, and verify `/admin` actions against the existing server-authorized routes and confirmation contract.

## Change-management requirements

- Use small, reviewable commits.
- Stage only files owned by this remediation.
- Do not reset, amend, rebase, push, or absorb unrelated dirty changes.
- Add one compact change-history entry for the completed commit-sized remediation unit.
- Add a decision entry only for a genuine architectural decision, such as introducing a same-origin media proxy or changing approval semantics.

## Further enhancements after the remediation

These are intentionally deferred and must not expand the current remediation without a new scope decision:

- add product analytics only after the state and privacy contract is stable;
- add richer preview comparison and shareable review links only as separately scoped work;
- add server-backed filtering and search to Users, Projects, and Audit without changing authorization boundaries;
- add operation detail drawers that expose safe state history rather than raw worker payloads;
- add bulk actions only after a separate idempotency and confirmation review;
- add a small health-summary link to diagnostics only if it remains safe and role-gated.
