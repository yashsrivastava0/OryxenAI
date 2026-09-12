# Implementation runbook

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

## Change-management requirements

- Use small, reviewable commits.
- Stage only files owned by this remediation.
- Do not reset, amend, rebase, push, or absorb unrelated dirty changes.
- Add one compact change-history entry for the completed commit-sized remediation unit.
- Add a decision entry only for a genuine architectural decision, such as introducing a same-origin media proxy or changing approval semantics.
