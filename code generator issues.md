# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## Current state — 2026-09-05 evening (round 3, resource-acquisition root cause + live-testing iteration)

Two fresh live runs (`b52330f2-…` PLANNER_OUTPUT_INVALID, `93d4d3c4-…`
INTEGRATION_REVIEW_UNRESOLVED after 5 polish rounds) were traced to root
cause using persisted ledger data rather than patched narrowly. The deepest
trace found resource acquisition itself failing in the majority of sampled
runs — see the table below. Five fixes landed (all free/mocked-tested, zero
API cost): Pixabay field fix, bounded pinned-candidate fallback, polish-round
finding dedup, cannot_complete log reason, and planner-output normalization.
Live re-testing after those five landed found two more real bugs (below):
the review/repair layers being blind to non-required resource placements,
and a false-positive selector-matching bug in the distinctive-move CSS
check. No run has yet reached a clean `ready` status; live iteration is
ongoing per the user's explicit "keep going until fixed" instruction.

## Findings and fixes this round

| Area | Finding | Durable resolution |
|---|---|---|
| Resource acquisition failing almost always | Across 14 sampled real-run ledgers, 7 were 100% "fallback" disposition, most others majority-fallback. Traced to `_pixabay_candidate()` preferring `imageURL` (Pixabay serves this only to specially-approved accounts; a normal key gets the field back but every download 400s). | `image_retrieval.py`: drop `imageURL`/`fullHDURL` from the preference chain, use `largeImageURL`/`webformatURL` only. **Correction to the initial hypothesis, found via direct empirical test**: a fresh search's `largeImageURL` already downloads fine (HTTP 200) even before this fix, for this API key — the field wasn't actually absent in practice. The *real* observed failure was the specific **pinned** candidate URLs (Build Preparation's D-060 pins) already using an equivalent shape and still 400ing live, while a brand-new search for the same image succeeds — i.e. **the pinned signed URL had gone stale between pin time and later acquisition**, not a wrong-field bug per se. Fix 1 is still correct defense (never request a gated field), but Fix 2 below is what actually fixes the observed failure. |
| No fallback when a pinned candidate goes stale | `jobs/handlers/code_generator.py`'s pinned-candidate path called `adapter.materialize()` once with no alternative; any failure (expired signed URL, transient error) went straight to `_fallback_receipt()`. | Wrapped the pinned materialize attempt in its own try/except; on failure, falls through to exactly one fresh live search (the existing search-and-select code, unchanged). Bounded: at most one pinned + one live-search attempt, never a loop. 2 new integration tests (fallback succeeds; required-with-no-fallback still hard-fails when both attempts fail). |
| Polish loop re-attempted an identical unfixable finding every round | Ledger inspection of `93d4d3c4-…` showed the same owner returning `cannot_complete` at round 1 (`RESOURCE_BINDING_UNAVAILABLE`) and again at round 4 (`RESOURCE_PLACEMENT_MISSING`, same root cause) — `grouped` findings are rebuilt fresh from the review every round with zero memory of prior rounds. | `generation_orchestrator.py`: added an owner→exhausted-finding-codes map, scoped per run. An owner is skipped for a round only if *every* current blocking code already returned cannot_complete before; a genuinely new code for the same owner still gets its fair attempt. 2 tests (dedup fires; a new code is not suppressed). |
| `cannot_complete` reason silently dropped from logs | The model's `safe_reason` was captured in `GenerationCannotComplete` but the log call only recorded owner/round — diagnosing today's failure required manually grepping workspace ledger files. Also the log message hardcoded the word "cannot_complete" even though the same guard also matches mode `"requests"`. | Log call now includes `result.mode` and, when it's `cannot_complete`, the real `safe_reason`. Confirmed live via test output. |
| Planner CSS-length rejection survived a corrective retry | `run_planner_operation()` already retries once with the validation error appended as feedback — the model still wrote `"sixtyrem"` on both attempts of the same real run. More prompting had already failed; escalated to a host-side fix. | `development_schemas.py`: `_validate_source_sizes()` now normalizes a spelled-out number immediately before a CSS unit (ones/teens/tens/hundred compounds) before the reject-check, instead of only rejecting. A genuinely unparseable word still rejects. Also normalized the 5 duplicated token-name casing validators (lowercase instead of reject) since `planner.md`'s own example anticipates this. |
| Review/repair blind to non-required resources | Live run `ff980629-…`: two image placements both had `required=false` and an honest `generated_local` fallback (system policy already says decorative is fine), yet the whole-site review raised a blocking finding and repair reported `cannot_complete` anyway — `required`/`local_paths` were in context but no prompt told either layer what to do with that fact. | `route_batch.md`, `repair_source.md`, `integration_review.md` all now state the same rule: `required=false` + no local binding is expected input, render a tasteful decorative/generated composition instead, never blocking. |
| Distinctive-move CSS false-positive on ancestor-scoped selectors | Live run `cf762cfb-…`: `SOURCE_REPAIR_EXHAUSTED` after 3 identical repair attempts, all reasonably scoping CSS as `#hero [data-region-id=...]`. Both `source_validation.py::_exact_selector_declarations` and `typescript_ast_audit.py::_selector_targets_contract` required an *exact* selector-string match with zero tolerance for a legitimate ancestor prefix, so genuinely-correct CSS was rejected as "missing" every round. | Both now accept a candidate selector that is the expected selector nested under any ancestor scope, while still rejecting a selector that only coincidentally shares a substring (new negative-case test in each). |

## Investigated, not a bug (by design)

- `style_primitive` fallbacks: `StylePrimitiveAdapter` has no live provider at all by design (offline/fixture only).
- `component_reference_only` fallbacks: an intentional reference-only branch when Build Preparation's suggestion has no local path.

## Deprioritized (thinner evidence, not investigated further)

- `"magicui rejected the component request"` — a second live-provider
  failure pattern for component sourcing. Looks like a genuine live
  rejection, not a field-selection bug like Pixabay. Revisit only if it
  keeps recurring after the fixes above land.

## Pre-existing, confirmed unrelated (out of scope, do not re-diagnose from scratch)

Confirmed via `git stash` that all 5 fail identically with none of this
round's changes applied — do not treat these as regressions from this work:
- `tests/integration/test_code_generator_development_worker.py::test_planner_worker_redelivery_reuses_plan`
- `tests/integration/test_code_generator_generation_worker.py::test_generation_creates_source_checkpoint_and_reuses_it`
- `tests/integration/test_code_generator_generation_worker.py::test_emergent_resource_request_pauses_and_resumes`
- `tests/integration/test_code_generator_verification_worker.py::test_verification_builds_and_promotes_a_clean_candidate` (previously documented `PLAN_SECTION_COVERAGE`-related)
- `tests/unit/agents/code_generator/test_v2_architecture.py::test_emergent_component_source_keeps_its_hash_named_materialization`

## Previous session — 2026-09-05 (D-068)

All 7 Code Generator model profiles remain on direct OpenAI
(`provider = "openai"`, `api_key_env = OPENAI_API_KEY`, model `gpt-5.6-luna`).
ScaleMax remains wired as a config fallback (D-066) if OpenAI credit/rate
issues recur.

D-067's frontier blocker (`QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on run
`6f4cd2e2-…`, a single `missing-section-heading` finding after final-gate
repair) was root-caused to a genuine control-flow gap, not a capability or
budget problem — see D-068. Fixed: `_attempt_repair` now gets exactly one
bounded extra repair+re-review attempt before giving up. **Not yet
confirmed live** — see "Current blocker" below.

## Findings and fixes this session (D-068)

| Area | Finding | Durable resolution |
|---|---|---|
| `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` had no retry | `_attempt_repair`'s post-repair whole-site re-review rejection raised terminally from *outside* its own bounded retry loop, so it could never consume another round of the existing 6-total/3-per-unit budget — the one observed case had used only 1 of 6. | Refactored into `_run_bounded_repair`/`_rereview_after_repair`/`_diagnostics_from_quality_findings` helpers (`jobs/handlers/code_generator_verification.py`); one bounded extra repair+re-review attempt, never a third re-review regardless of remaining budget. 2 new regression tests prove the exact bound. |
| `INTEGRATION_POLISH_INCOMPLETE` had no retry either | Live-discovered this session: the *mid-generation* whole-site polish loop's owner-scoped repair call (`_review_and_polish`) raised and killed the whole run the moment a repair attempt reported `cannot_complete`, even on the first attempt, even though the outer polish-round loop (5 rounds, D-067) exists precisely to give a different round another try. | Now logs a warning and `break`s (skipping that owner for the round) instead of raising; the pre-existing bounded polish-round loop keeps trying or converges to the pre-existing `INTEGRATION_REVIEW_UNRESOLVED` terminal state. 1 new regression test. |
| Whole-site review had zero prefix-caching | The single most expensive, most-repeated call in the pipeline (up to 8x/run, up to ~600,000 chars) had no `request_context` at all, unlike 4 of the other 5 call sites. | Added `INTEGRATION_REVIEW_KEY_ORDER` + a stable `prompt_cache_key`, ordering run-invariant content before the two always-changing scalars (`round`, `source_manifest`) and the large `assembled_source` dict. **Confirmed live**: non-zero `cached_prompt_tokens` in persisted usage on the second live call onward. |
| Motion was 100% free-form | Scaffold's `motion.css` was empty (reduced-motion safety net only); every beat's animation was invented from scratch, the one remaining unconstrained surface versus the deterministic catalogue-and-select pattern already used for images/fonts/components. | Added `core/motion_pattern_catalogue.py` (3 patterns) + optional `MotionBeatV4.pattern_id`; `generation_contract.py` instructs route_batch/route_compose to apply a named trusted `SharedSystems.tsx` component when set. **Confirmed live**: the planner set `pattern_id` on a real beat on the first live attempt. Required a companion fix — `route_batch.md`/`route_compose.md` previously explicitly forbade the `.reveal`/`.stagger` class names this introduces. |
| No visual evidence anywhere | DOM/runtime verification never captured a screenshot; zero pixel-level evidence of a generated portfolio existed anywhere in this pipeline. | Added advisory screenshot capture to `runtime_verifier.py` (zero extra cost — the browser context is already open) plus export/report wiring. |
| A Build Preparation test silently spent real budget | `tests/integration/test_build_preparation_worker.py`'s worker test built no mock model client, unlike every other test in the suite — a plain `pytest` run made a real live call every time. | Gated behind `@pytest.mark.live` + `RUN_LIVE_BUILD_PREPARATION=1`, matching this project's own existing live-test convention (`tests/live/`). |

(Memory-pressure blocker from this earlier session is resolved — two fresh
live runs this round reached `generate`/`verify` normally. Superseded by the
"Next verification target" below.)

## Next verification target

- Re-run a fresh full attempt (plan → acquire → generate → verify) against
  the same eligible pack with this round's fixes applied. Confirm:
  (a) resource dispositions are majority `admitted`, not majority `fallback`;
  (b) no identical blocking finding gets re-attempted across non-adjacent
  polish rounds; (c) inspect captured `verification-screenshots/` for real
  visual confirmation of images actually rendering, not decorative-only
  sections — the concrete test of "visually looking good."
