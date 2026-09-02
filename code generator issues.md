# Code Generator Issues

Session log for the live Code Generator reliability campaign on 2026-09-02.

## Test scope

- **Pipeline:** ten fresh production-style starts from the eligible Build Preparation pack `22-51-01-09-1961f2c9`.
- **Configured model:** resolved from `config/models.toml` through the Code Generator role profiles. No model or ceiling changes were made.
- **Environment:** native API, worker, and preview gateway; real provider calls; no fixture or mock substitution.
- **Budget:** all 10 permitted live starts were used.
- **Outcome:** 0/10 reached `ready`; every observed attempt ended in `needs_attention`.

## Run-by-run terminal issues

| Attempt | Run ID | Terminal phase | Issue observed |
|---:|---|---|---|
| 1 | `0ed875da-1b81-41bd-96a3-89842c6dfc13` | Planning | `PLANNER_OUTPUT_INVALID`: `typography_roles.1.body_line_height` was below the schema minimum of `1`. |
| 2 | `8c6bb44e-26c4-451e-9001-d7577a9b05ce`* | Planning | `PLANNER_OUTPUT_INVALID`: `resource_placements.0.sizes` used a value that was not a numeric CSS length. |
| 3 | `001283d3-c86c-46a0-bb80-8ab7308e6f58` | Runtime verification | `DOM_RUNTIME_FAILED`: assertion/overflow/navigation, distinctive-relationship, font-load, motion-state, region geometry, section-order/collision, and touch-target findings. |
| 4 | `5ffdc79c-0ed1-41aa-8781-cd2044b8a335` | Integration review | `INTEGRATION_REVIEW_UNRESOLVED` after the configured polish budget; quality finding `motion-no-fallback-state`. |
| 5 | `dcfd0884-2e08-4fc8-bd85-a35eac24ab23` | Runtime verification | `DOM_RUNTIME_FAILED`: runtime assertion, region-gap, and touch-target findings. |
| 6 | `70ef52d9-392c-4ad6-8ac9-4ec5dd03b91a` | Integration review | `INTEGRATION_REVIEW_UNRESOLVED` after the configured polish budget; quality finding `content-copy-retyped-in-route`. |
| 7 | `74e5ba7e-6a89-49c6-b413-77eeddfa7a76` | Quality review after repair | `QUALITY_REVIEW_REJECTED_AFTER_REPAIR`: route navigation exposed Hero/Project even though the approved public navigation contained only Home. |
| 8 | `64dd8e74-7076-4b10-b285-67bb5520f0a4` | Integration review | `INTEGRATION_REVIEW_UNRESOLVED` after the configured polish budget; quality finding `RESOURCE_RESPONSIVE_ASPECT_RATIO`. |
| 9 | `0a52e3de-7940-4bb8-9fdb-6bb539e286b1` | Integration review | `INTEGRATION_REVIEW_UNRESOLVED` after the configured polish budget; quality findings `V4_MOBILE_REGION_COLUMNS` and `APPROVED_CONTENT_ANTI_PATTERN`. |
| 10 | `7d8e3382-9f0a-4d7b-96ab-7d73fcaa2593` | Source verification | `SOURCE_CONTRACT_FAILED` after the configured repair budget: `SOURCE_MOTION_BEAT_UNIMPLEMENTED` and `SOURCE_MOTION_REDUCED_MOTION_MISSING`. |

\* The second run's identifier was present in the live response/log evidence, but its database/API row was later unavailable. Its planner failure is retained here because it was observed during this session.

## Historical blocker check

The two blockers handed off from the previous live run were explicitly checked in all ten fresh attempts:

- [x] `BLUEPRINT_ANTI_PATTERN_REPEATED_SPLIT` — **0/10 fresh occurrences**.
- [x] `MOTION_TARGET_PROPERTY_MISMATCH` — **0/10 fresh occurrences**.

The pair remains a real historical failure, but this campaign does not support calling it systemic. Several fresh quality reviews explicitly described distinct asymmetric hero/project compositions.

## Detailed issues observed in generated output

### Planner and schema validity

- [x] `PLANNER_OUTPUT_INVALID` for a body line-height token below the finite schema minimum.
- [x] `PLANNER_OUTPUT_INVALID` for an image `sizes` policy that was not expressed as numeric CSS lengths.

### Route ownership, structure, and content contracts

- [x] `SOURCE_ROUTE_BATCH_SECTION_OWNERSHIP_INVALID`.
- [x] `SOURCE_ROUTE_BATCH_H1_OWNERSHIP_INVALID`.
- [x] `SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID` (recurred across multiple attempts).
- [x] `SOURCE_DUPLICATE_PATH` in a repair/generation response.
- [x] `approved-navigation-expanded` and `approved-navigation-contract-mismatch`.
- [x] `section-anchor-target-missing`.
- [x] `content-copy-retyped-in-route`.
- [x] `unapproved-section-copy`.
- [x] `approved-content-antipattern-visible-index` / `APPROVED_CONTENT_ANTI_PATTERN`.
- [x] `invalid-css-math-container`.
- [x] `self-referential-semantic-token`.

### Motion and responsive composition

- [x] `motion-no-fallback-state` and `motion-static-fallback`.
- [x] `motion-fallback-hides-divider`.
- [x] `motion-viewport-trigger-unreliable`.
- [x] `SOURCE_ROUTE_BATCH_MOTION_INVALID`.
- [x] `SOURCE_MOTION_BEAT_UNIMPLEMENTED`.
- [x] `SOURCE_MOTION_REDUCED_MOTION_MISSING`.
- [x] `reduced-motion-overrides-mobile-stack`.
- [x] `composition.mobile-stack-missing`.
- [x] `V4_MOBILE_REGION_COLUMNS`.
- [x] `distinctive_move_ratio_below_minimum` and `distinctive-move-mobile-width-ratio`.

### Typography and visual direction realization

- [x] `approved-headline-weight-mismatch`.
- [x] `hero-display-weight-mismatch`.
- [x] `typography-configured-fallback-mismatch`.
- [x] `V4-TYPOGRAPHY-HERO-LOCKUP` and `typography.hero-weight`.
- [x] `DIRECTED_HERO_WEIGHT_NOT_REALIZED`.
- [x] `DIRECTED_PROJECT_WEIGHT_NOT_REALIZED`.

### Resource and image realization

- [x] `resource-visible-ratio-out-of-contract`.
- [x] `hero-image-aspect-mismatch` and `V4-RESOURCE-HERO-ASPECT-RATIO`.
- [x] `project-resource-ratio-not-realized`.
- [x] `resource-aspect-ratio-not-enforced`.
- [x] `responsive-resource-aspect-ratio` and `RESOURCE_RESPONSIVE_ASPECT_RATIO`.

## Runtime verifier findings

Attempt 3 exposed the largest set of runtime findings:

- [x] `RUNTIME_ASSERTION_FAILED`: horizontal overflow and a navigation click timeout.
- [x] `RUNTIME_DISTINCTIVE_RELATIONSHIP`: measured hero/project relationships did not fall within the approved ranges (hero `1.814` vs `0.55–0.85`; project `0` vs `0.2–0.75`).
- [x] `RUNTIME_FONT_LOAD_FAILED`: eight checks failed for configured weights `500` and `700`.
- [x] `RUNTIME_MOTION_STATE_MISMATCH`: hero image clip-path, hero headline transform, and project divider transform/origin did not match the approved motion state.
- [x] `RUNTIME_REGION_COLUMN_COUNT`: the probe reported one rendered column against an approved eight-column contract.
- [x] `RUNTIME_REGION_GAP`: measured `24px` against approved `40px`/`32px` gaps.
- [x] `RUNTIME_REGION_MEASURE`.
- [x] `RUNTIME_SECTION_COLLISION`.
- [x] `RUNTIME_SECTION_ORDER` and `RUNTIME_SECTION_ORDER_INVALID`.
- [x] `RUNTIME_TOUCH_TARGET_TOO_SMALL`.

## Likely verifier or contract mismatches

These are not proven model failures and should be investigated before treating every runtime rejection as a generation defect:

- [x] Section-order and geometry probes query `main [data-content-id]`, which also matches nested headings/content nodes, not only section shells.
- [x] The realization audit uses the same broad `data-content-id` selector, so nested content IDs can create false section-order and collision findings.
- [x] The approved plan can specify eight- or twelve-column regions while generated CSS uses a two-track grid; the contract does not clearly define whether these are logical columns or literal CSS tracks.
- [x] The navigation runtime step expects `[data-navigation-target="home"]`, while generated routes may expose ordinary anchors.
- [x] Font verification calls `document.fonts.check` for each weight without first forcing `document.fonts.load`, which can produce false load failures.
- [x] The runtime relationship thresholds can reject a valid-looking layout when the plan's measurement basis and the verifier's measurement basis differ.

## Environment and observability issues

- [x] Running the generated Node build inside the restricted sandbox produced `spawn EPERM`; running the worker outside the sandbox allowed the same build to pass and continue verification. This was an execution-environment limitation, not a model or source diagnosis.
- [x] The readiness endpoint continued to report `provider_preflight_required` even after `POST /provider-preflight` returned ready. Live starts still succeeded, so this is a readiness-reporting defect/false negative.
- [x] `GET /runs/{id}` intermittently returned HTTP 500 for one run while a direct database read showed the run's terminal state. This weakens API observability and should be separated from worker/model failures.
- [x] The eligible pack has a short expiry window, so stale-pack eligibility must be checked before future campaigns.

## Campaign conclusion and follow-up

- [x] Ten-run limit consumed.
- [x] Historical repeated-split and motion-target pair not reproduced in the ten-run sample.
- [x] No repository source code was changed during this campaign.
- [ ] Align runtime selectors and measurement contracts with section shells, logical columns, navigation targets, and font loading semantics.
- [ ] Harden planner/schema prompting or pre-validation for line-height and image `sizes` values.
- [ ] Improve route ownership, approved-navigation, motion fallback/reduced-motion, responsive resource, and mobile composition guidance.
- [ ] Re-run a bounded confirmation campaign only after the verifier/contract issues are addressed.
