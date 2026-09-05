# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## HANDOFF — read this first (2026-09-06, early morning, Claude Code session ending)

**Overall status: substantially fixed, not fully fixed.** This session found
and fixed 14 real, distinct bugs today (full list in the table below), every
one confirmed by tracing an actual live run's real failure, not guessed at.
All are committed and pushed to `codex/code-generator-control-room`. Budget
is confirmed fine by the user (real OpenAI balance was $8.51/$10 as of
tonight) — do not self-limit live testing over cost.

**The single biggest finding**: resource acquisition (Pixabay pinned image
URLs going stale between Build Preparation and Code Generator) was silently
failing in the majority of sampled runs all along — this explains most of
the historical "generation looks broken" reports better than any single
generation-side bug did. That is now fixed and confirmed live.

**Where things actually got to tonight**: two consecutive fresh live runs
both reached `generate: succeeded` -> final DOM/runtime verification — the
deepest and most consistent this whole engagement has gone. Neither reached
a clean `ready`/promoted state. Both are exported for direct inspection at:
- `output/code-gen-output/01-56-06-09-2026-0db8503e/` — has a real `dist/`
  build and real `screenshots/`. **Open the screenshots — the portfolio
  genuinely looks good** (real hero photo, clean editorial layout, coherent
  sections, correct responsive reflow). Failed at final verification with
  `DOM_RUNTIME_FAILED` (11 distinct runtime codes, since deduped — see
  table). This is concrete proof "visually looking good" is achievable with
  the current pipeline; the remaining gap is narrower/more technical than it
  looks from a screenshot alone.
- `output/code-gen-output/02-23-06-09-2026-fa31c124/` — reached
  `generate: succeeded` too, but failed before building (`SOURCE_CONTRACT_FAILED`
  — 2 `SOURCE_CONTENT_KEY_MISSING` diagnostics, **not yet investigated at
  all** — see "Not yet fixed" below. This is probably the single best next
  thing to look at; it is a fresh, unexplored finding from tonight, not a
  repeat of anything already fixed.

**Two known environmental gotchas, not code bugs:**
- **System memory is tight** on this machine (often 2-4GB free out of
  15.68GB total — other apps + a peer Codex session share it). Roughly 40%
  of tonight's live attempts got killed by memory pressure mid-`generate`
  (the `npm install`/build/Playwright-verify steps are the heavy part).
  Check free memory first (`Get-CimInstance Win32_OperatingSystem`); if a
  run gets killed, it is almost always **resumable** — check
  `code_generator_runs.status`/`coordinator_stage` for that run_id in
  Postgres, and if it's not yet at a terminal status, re-invoke with
  `scratch/continue_live_generation.py <run_id>` rather than starting over
  (skips the already-completed stages, saving both time and API cost).
- **DB connection — correction (2026-09-06 03:12, added during final
  handoff cleanup): the paragraph below is WRONG about the port, do not
  follow it as originally written.** `config/app.native.toml` is committed
  at port `5432`, not `5545` — checked directly on disk while preparing
  this branch for device handoff. Tonight's actual Postgres data (the run
  rows referenced above) lived at port `5545` only because *this specific
  machine* had a pre-existing local PostgreSQL service already bound to
  `5432` (the "dual PostgreSQL services" conflict), worked around ad hoc via
  an untracked, git-ignored `.workspace/app.runtime-native.toml` that
  nothing in the codebase loads automatically — it was never a supported
  mechanism, just a same-session workaround. **On a new device, none of that
  applies**: that Postgres data is local to this machine and does not
  transfer — the portable evidence is the exported files already committed
  under `output/code-gen-output/` and `output/build-preparation/`. Just use
  `OryxenAI_CONFIG_OVERLAY=config/app.native.toml` normally (plain `5432`);
  if the new machine's own local PostgreSQL is already using `5432`, set
  `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` in `.env` instead of touching the
  TOML — see `.env.example` and README.md's Troubleshooting section, both
  updated with this mechanism during this same cleanup. Original note,
  now superseded, kept for history: "use
  `OryxenAI_CONFIG_OVERLAY=config/app.native.toml` before `uv run python
  ...` — that's the native dev Postgres (port 5545), which is where all of
  tonight's real run data actually lives." The hardcoded `127.0.0.1:5432` in
  old scratch scripts is stale either way; both `scratch/run_live_generation.py`
  and `scratch/continue_live_generation.py` were already fixed tonight to
  just call `get_settings()` plain, which is correct regardless of this port
  correction.
- **Cost accounting**: `config/models.toml`'s pricing rates are an internal
  "configured credits" unit, not 1:1 with real USD (confirmed off by ~24x
  tonight) — never compute a dollar figure from them. If real spend needs
  checking, ask the user to look at their actual provider billing page.

**Branch handoff housekeeping (done 2026-09-06 03:12, separate from the
code-generator fixes above):** `output/` was trimmed to just the one
Build Preparation pack and the two Code Generator runs referenced above
(everything else predated tonight or was a minor early-stage export);
`.gitignore` was fixed so those specific kept paths are actually tracked
(git won't re-include a file under an already-excluded directory without
an explicit ancestor-negation chain); README.md's stale "Code Generator
out of scope" banner and non-goals were corrected and now point here
first; and the `.env.example`/README.md/`docs/run/run.md` port-conflict
docs were fixed (see the DB-connection correction above). All committed
and pushed to `codex/code-generator-control-room`. This paragraph and the
correction above are the only edits to this file from that pass — nothing
about the code-generator investigation itself changed.

**Suggested next steps, roughly in priority order:**
1. Investigate `fa31c124`'s `SOURCE_CONTENT_KEY_MISSING` (fresh, unexplored).
2. Run one more fresh live attempt against the same eligible pack
   (`output/build-preparation/01-31-04-09-94ae4a9c/`, or check
   `output/build-preparation/` for whichever pack is currently eligible) to
   see whether tonight's accumulated fixes (dedup, `Reveal` marker
   forwarding, easing normalization) let a run reach final verification
   cleanly, or whether `DOM_RUNTIME_FAILED` recurs with a smaller, deduped
   bundle that repair can actually resolve now.
3. If `DOM_RUNTIME_FAILED` recurs, the other ~10 distinct runtime codes
   from `0db8503e` (font load, resource decode, region geometry, motion
   state, distinctive-move relationship/selector) have not been
   individually root-caused yet — same methodology as everything in the
   table below: read the actual ledger/ workspace data for the failing run
   before guessing, most bugs tonight were subtler than the terminal
   error message alone suggested.
4. The missing keyboard-accessible disclosure component finding (run
   `15debdae-…`) is also still open, lower priority than #1-3 since it's
   only been seen once.

Every fix below also has a runnable regression test — `uv run pytest -k
code_generator` should stay green (261 passing, 5 confirmed-pre-existing-
unrelated failures, see the dedicated section below) after any further
change.

## Current state — 2026-09-05 evening (round 3, resource-acquisition root cause + live-testing iteration)

Two fresh live runs (`b52330f2-…` PLANNER_OUTPUT_INVALID, `93d4d3c4-…`
INTEGRATION_REVIEW_UNRESOLVED after 5 polish rounds) were traced to root
cause using persisted ledger data rather than patched narrowly. The deepest
trace found resource acquisition itself failing in the majority of sampled
runs — see the table below. Five fixes landed (all free/mocked-tested, zero
API cost): Pixabay field fix, bounded pinned-candidate fallback, polish-round
finding dedup, cannot_complete log reason, and planner-output normalization.
Live re-testing after those five landed found four more real bugs (below):
the review/repair layers being blind to non-required resource placements, a
false-positive selector-matching bug in the distinctive-move CSS check, a
planner retry-count fix, and a duplicate-file-path canonicalization fix.
Run `15debdae-…` (2026-09-05 ~19:35) got the furthest of any run this round
— past every one of those blockers, through all 5 whole-site polish rounds
— and landed on 2 real remaining findings: a `Reveal`/marker DOM-node
mismatch (fixed, see table) and a missing keyboard-accessible disclosure
component (not yet fixed — see below). No run has yet reached a clean
`ready` status; live iteration is ongoing per the user's explicit "keep
going until fixed" instruction.

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
| Planner collision retry not always landing in 2 attempts | Live-observed 3 separate times (`accent`/`accent` twice, `muted`+`secondary` once) — the shadcn-collision validator (D-071) correctly rejects, but a single corrective retry doesn't always fix it even with the exact colliding tokens named. | `planner_operation.py`: widened the bounded retry from 2 to 3 attempts (all 4 `attempt ==`/`range(2)` sites updated consistently). Still finite; only costs a cheap planner-stage call. 2 new tests prove the 3rd attempt fires and that it still raises correctly once exhausted. |
| Duplicate file path exhausting the repair budget | Live run `b980b20e-…`: one response listed the same CSS file twice with two nearly-identical bodies (one rule split into two declarations, merged into one in the other) — the model revising its own answer within one response, not a real conflict. 3 repair attempts couldn't resolve it (`SOURCE_REPAIR_EXHAUSTED`). | `generation_orchestrator.py::_validate_v4_generation_coverage` now silently keeps the *last* entry per path (same "last key wins" semantics as JSON) instead of raising `SOURCE_DUPLICATE_PATH`. A response that never repeats a path is unaffected. |
| Repair given wrong import-path depth for section files | Live run `040380f5-…`: 3 section files all repaired with `../../../../` (4 levels) to `SharedSystems`/`generated-content`, which overshoots `src/` entirely. `route_batch.md` (initial generation) already correctly states section files need 3 levels and warns against 4; `repair_source.md` had no depth guidance for section files at all — its only nearby example was for the *route composer* (`index.tsx`, correctly 2 levels), which likely bled into confusing the repair model. | `repair_source.md`'s `SOURCE_LOCAL_IMPORT_MISSING` guidance now states both depths explicitly (3 for a section file, 2 for the route composer), mirroring `route_batch.md`'s own wording. |
| `Reveal`/marker DOM-node mismatch | Live run `15debdae-…` (furthest run yet — past every other blocker, through all 5 polish rounds): a blocking finding reported a motion CSS selector combining `data-resource-marker` and `data-motion-ready` on one element that could never match. `Reveal` (added earlier this engagement) sets `data-motion-ready` on its own wrapper `<div>`; a marker placed on `children` instead lands on a different DOM node. `Reveal`/`StaggerGroup` had no way to accept an extra attribute onto their own wrapper at all. | `SharedSystems.tsx`: both now forward a typed `...rest` onto the wrapper element, so `<Reveal data-resource-marker="...">` puts both attributes on the same node. `route_batch.md`/`repair_source.md` both state this explicitly, plus the descendant-selector alternative for when the two attributes genuinely belong on different elements. Verified: scaffold `npm run typecheck` and `npm run build` both clean. |
| Motion easing rejected on all 3 planner attempts | Live run: "motion beats require a validated CSS easing value" for 2 beats, all 3 attempts. Traced to this project's own `planner.md` prose ("easeOutCubic-family", "easeOutExpo-family" — a style family, not a literal value) reading close enough to valid CSS that the model copied it directly into `easing`. | Fixed both ends: `planner.md` now explicitly requires a schema-valid easing keyword regardless of `pattern_id` and suggests `ease-out` as a safe default; `development_schemas.py` also gets a host-side `_normalize_easing()` mapping common spelled-together words to their valid keyword before the reject-check, on both `MotionTokenV4` and `MotionBeatV4`. |
| Identical runtime diagnostic repeated across viewports | Live run `0db8503e-…` — **furthest run this entire engagement**: `generate` fully succeeded, reached final verification, produced real screenshots of an actually good-looking site (see screenshots dir), but failed with 11 distinct `DOM_RUNTIME_FAILED` codes, one (`RUNTIME_TOUCH_TARGET_TOO_SMALL`) repeated 6 times with the identical fingerprint — the same one real small nav link, caught once per viewport/journey. Final repair failed to produce any correction across all 3 attempts against this bloated bundle. | `runtime_verifier.py::verify()` now dedupes by `Diagnostic.fingerprint` (already keys on code+journey_id+route_id+message) before returning. New Playwright-driven test proves 2 same-journey-id viewports hitting one real failure collapse to 1 diagnostic. **Not yet re-tested live** — next live run should confirm whether the smaller bundle actually lets repair succeed. |
| `output/code-gen-output/` only preserved successful runs | Explicit user request: a failed/incomplete run's generated source (and any build/screenshots) was silently discarded — only a promoted `ready` run ever got exported, so there was no way to inspect what a failed attempt had actually produced. | Added `export_failed_run()` to `portfolio_export.py` (needs only a run id + whatever the workspace has on disk, no promotion-only state) and wired it into the two failure choke-points: `code_generator.py`'s shared `_needs_attention()` (plan/acquire/generate failures) and `CodeGeneratorVerificationHandler.execute()` (verification failures). Both are try/except-wrapped, advisory only. 4 new tests. Confirmed live for both `0db8503e` and `fa31c124` (manually re-exported the latter since its own run process had the pre-fix code already loaded in memory — expected, not a bug). |

## Not yet fixed (found, not yet acted on)

- **`SOURCE_CONTENT_KEY_MISSING` on 2 content keys** — run `fa31c124-…` (2026-09-06 ~02:15, exported at `output/code-gen-output/02-23-06-09-2026-fa31c124/`, source only, no build): `generate` fully succeeded, but final verification failed with `SOURCE_CONTRACT_FAILED` — two approved content keys (`content:home:home:hero:primary-cta-kind-dd5e7a62` and `...primary-cta-label-7207f029`) are "not referenced by executable route source." **Not yet investigated at all** — this is the single most promising next lead, since it's a fresh, unexplored finding from a run that got as far as any run tonight. Start by reading `output/code-gen-output/02-23-06-09-2026-fa31c124/source/src/routes/home-4ea14058/index.tsx` (or the equivalent path in `.workspace/code-generator-generation/fa31c124-99f6-410a-adeb-651261d88114/repo/` if the workspace still exists) to see what the primary-CTA rendering actually looks like, and compare against how `contentValue(...)` calls are supposed to reference these two specific keys elsewhere in the codebase's own conventions (see `source_validation.py`'s near-miss-detection work from earlier tonight for the sibling `SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING` diagnostic, which may share a root cause).
- **Missing keyboard-accessible disclosure component** — run `15debdae-…`: the systems section rendered a static `<ul>` instead of the assigned capability-grouping progressive-disclosure behavior (no `aria-expanded`/`aria-controls`, no keyboard-operable trigger), despite the selected creative direction calling for it. Not yet investigated — next thing to check if this recurs.
- **The other ~10 distinct `DOM_RUNTIME_FAILED` codes from run `0db8503e-…`** (font load, resource decode, region geometry, motion state, distinctive-move relationship/selector) — the dedup fix above removes redundant copies of the *same* issue but not the underlying distinct issues themselves. Not yet individually investigated; next live run will show whether the smaller, deduped bundle lets final repair actually resolve them, or whether each needs its own root-cause trace.

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

Superseded by "HANDOFF — read this first" at the top of this file (that
target was fully met — resource dispositions did flip to majority-admitted,
no finding was re-attempted after the dedup fix, and captured screenshots
did confirm real images rendering). See the top section for what to do next.
