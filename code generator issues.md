# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## Current state — 2026-09-05 (D-068)

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

## Current blocker

- Not a code failure — a resource one. Two live end-to-end attempts against
  the eligible pack (`output/build-preparation/01-31-04-09-94ae4a9c/`) this
  session: the first reached `generate` and stopped at the *new*
  `INTEGRATION_POLISH_INCOMPLETE` gap above (now fixed, not re-tested); a
  second and a resume-of-that-run attempt were both killed by real system
  memory pressure (~1.5GB free of 15.7GB on this machine) before reaching
  `verify_and_preview` — not a logic bug. Fix A's exact retry path
  (`QUALITY_REVIEW_REJECTED_AFTER_REPAIR` → one bounded extra attempt) was
  therefore **not directly witnessed live this session**; it is proven only
  by `test_attempt_repair_retries_once_after_quality_rejection_then_accepts`
  and `test_attempt_repair_gives_up_after_one_quality_rejection_retry`
  (`tests/integration/test_code_generator_verification_worker.py`).
- The original historical blocker run (`6f4cd2e2-…`) cannot be cheaply
  resumed to test this fix directly: its `generation_projection.quality_review`
  was already overwritten by the rejected repair attempt itself (by design —
  a rejected repair must never become the accepted checkpoint), so a
  verify-only resume immediately hits `QUALITY_SOURCE_STALE` before any
  model call. A fresh full run is required to exercise Fix A live.

## Remaining external blocker

- None from the provider/rate-limit/schema-compliance class.
- System memory pressure on the development machine blocked completing a
  live run past `generate` this session — retry once more memory is free.

## Next verification target

- Re-run a fresh full attempt (plan → acquire → generate → verify) against
  the same eligible pack once system memory pressure eases. Confirm:
  (a) `INTEGRATION_POLISH_INCOMPLETE`'s fix actually lets a `cannot_complete`
  owner get skipped without killing the run; (b) a `QUALITY_REVIEW_REJECTED_AFTER_REPAIR`
  case (if one recurs) actually gets the one bounded extra retry and either
  resolves or cleanly terminates after exactly that; (c) inspect the
  captured `verification-screenshots/` for real visual confirmation the
  output looks like an advanced, animated, image-rich portfolio — the
  actual test of "visually looking good," not just green checks.
