# Code Generator Issues

## 2026-09-10 22:52 +05:30 - Zero images across every observed live run traced to a soft-preference image policy default

User-reported: generated portfolios never show images, including the
campaign's one `ready` result (slot 5, run `ff3398b1`). Root-caused by
tracing the full pipeline for that exact run and two others (slots 3, 4),
all Pack A: Build Preparation's `visual_input.py` correctly researched and
vetted 7 real image candidates per run (real Pixabay photos with license/
attribution/dimensions, `category: "editorial_photo"`); `normalize_
resource_category` in `resource_policy.py` already maps `"editorial_
photo"` to `"image"` correctly; and all 7 slots correctly reached
`execution/contract.json` intact -- confirmed by reading the actual
compiled contract, not inferred. The gap was entirely in host policy:
`image_policy.py`'s `build_image_policy_snapshot()` derived
`minimum_visible_images=0`/`require_primary_route_image=false` from the
configured defaults, so the planner prompt's only instruction was the
soft "prefer a restrained supporting image placement... this preference
is not a release gate" clause -- and the planner model declined every
single one of 21 image opportunities across 3 runs (7 per run x 3 runs),
despite real vetted material being available every time.

Commit `882574e` (D-092) raises `minimum_visible_images` to 2 (matching
the existing `preferred_visible_images=2`, making "preferred" an actual
floor the planner prompt enforces as `PLAN_REQUIRED_IMAGE_PLACEMENT` if
violated) and `require_primary_route_image` to `true`, in both
`settings.py` and `config/app.toml`. The exemption path for packs with
zero approved image slots is untouched and still correctly forces 0/False
regardless. Not yet live-confirmed -- the next live run should verify at
least 2 real images render with valid, non-broken sources.

## 2026-09-10 19:50 +05:30 - Pack A live disposition (slot 5, FINAL) — ready, campaign closed

Run `ff3398b1-86cb-49cd-b12b-5f5857ded187` (Pack A retry, campaign-B slot
5 -- the last slot in the shared 5-run budget) reached **`ready`**: the
first ready result across this entire reliability campaign (campaign A's
5 slots and campaign B's slots 1-4 all failed; 9 live runs total before
this one). All three verification gates passed with zero blocking
diagnostics: `source_contract`, `type_build_artifact`, and `dom_runtime`
(0 blocking, 57 advisory -- e.g. a couple of regions rendering 2 columns
where their contract expects 1, one distinctive-move width ratio outside
its declared range; real, non-fabricated, and worth a future pass, but
correctly non-blocking).

Verified beyond the DB status alone, per this campaign's own discipline:
the promoted preview (`http://127.0.0.1:4174/preview/preview-
3uc4dd7inyzsszvpaakxjgppqyni72d4wckhsmke7zxkkzzn/`) was loaded in an
actual Chrome tab. Every section rendered real, substantive content
(Hero, Positioning, Selected Work with 3 real case studies, Capabilities
across 4 categories, Experience across 3 roles, Credentials with an
honest "pending verification" placeholder rather than fabricated text,
Connect); the 7-link closed navigation is fully functional (clicking
"Capabilities" updated the URL hash and the nav's active state
correctly); zero console errors or exceptions; every real network
request (document, JS bundle, CSS bundle, 3 font files) returned HTTP
200; the route uses no `<img>` elements at all, so "no broken images" is
met trivially (zero visible images is explicitly valid under the
acceptance checklist); `dist/index.html` confirmed present on disk.
Desktop and laptop were checked (mobile is not a release gate, D-088).

This slot needed no new code fix -- it directly confirms slots 1-4's four
fixes (`22db99c`, `d9caf30`, `e7d9284`, `06eb2c0`) together resolve every
real defect this pack previously hit. **Campaign B is now closed (5/5
slots consumed)**; no sixth run or automatic follow-on campaign is
permitted. A future campaign, if authorized, should start with Pack B.

Separately: this slot's live services were killed twice more by host OS
memory pressure from unrelated desktop applications (same pattern as
slot 4 -- not a Code Generator defect). The durable job queue resumed the
in-flight run cleanly both times with no data loss or code change needed.
Browser automation itself also degraded under the same memory pressure
(one Chrome tab became unresponsive to script injection mid-verification;
a fresh tab in the same browser worked immediately) -- also an
environment condition, not a site defect, confirmed by the fresh tab
rendering the exact same page correctly.

## 2026-09-10 18:50 +05:30 - Pack A live disposition (slot 4) and normalizer color-token fix

Run `0b56cda5-59a4-4bd6-b8f0-2fe548d5d0e3` (Pack A retry, campaign-B slot 4)
reached `needs_attention` with `SOURCE_REPAIR_EXHAUSTED` after two genuine
model repair rounds (`call-9019b7189e1c45f45c9a`, `call-9e8186e9a18e22034a9b`).
Accepted checkpoint `e619daae8ee9abe8f777992e7da452f4eedb5ffe22a8b590c8af4fdf1e1a34bd`
(foundation only; the route-batch work unit never reached an accepted
checkpoint). Three final blocking diagnostics, all `SOURCE_CSS_CUSTOM_
PROPERTY_UNBOUND` on `src/routes/home-4ea14058/sections/home-selected-
work-2f0991ad.css`, referencing undefined custom properties
`--color-accent-signal`, `--color-border-subtle`, `--color-ink-secondary`.
Two earlier, transient diagnostics from intermediate repair rounds
(`SOURCE_REPLACE_MISSING`, `SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID`,
both on the hero section) were confirmed already resolved by the model's
own repair output before termination -- inspecting the final pending
candidate (`ledger/pending/route-home-4ea14058-batch-1.json`) showed the
hero CSS correctly matching its distinctive move's exact selector.

Root cause, confirmed by reading the exact injected CSS in that pending
candidate: the three broken custom properties come from `d9caf30`'s
"OryxenAI trusted selected-work lifecycle cue" deterministic normalizer
(`normalize_route_batch_selected_work_sources`), which hardcoded assumed
color token names. Color token names are chosen per run by the model's own
creative direction (this run used "ink-strong"/"ink-muted"/"signal"/
"accent"/"border"/"rule"; a different run's fixture used "ink"/"paper") --
never a fixed system contract -- so none of the three hardcoded names
existed in this run's actual `src/design/generated-tokens.css`. Because the
broken CSS lives in normalizer-injected code the model never authored and
is never asked to repair, it persisted unchanged across both repair
rounds while the model successfully fixed its own real mistakes elsewhere
in the same route batch -- confirming this was the sole terminal blocker.

Commit `06eb2c0` adds `_resolve_existing_color_token()`, which scans the
route's actual generated CSS for existing `--color-*` properties and
picks one by semantic keyword (muted/secondary/subtle, border/rule/
outline, signal/accent/primary), omitting the declaration entirely if
nothing resolves rather than emitting an unprovable reference.
Confirmation: re-running the normalizer against this run's real merged
sources and real tokens produced zero undefined custom properties
(previously 3); full `test_source_validation.py` suite (35/35, including
one updated and one new regression test) and the broader `-k
code_generator` selection (362 passed, same 3 pre-existing baseline/
environment failures) both clean. Campaign-B slot 4 consumed; no ready
result. One slot (5) remains in the shared 5-run budget.

Separately, this session's live services (API/worker/preview gateway)
were killed twice by the host OS under memory pressure from unrelated
desktop applications (browser tabs, other AI-tool apps) -- not from these
services themselves, which never appeared among the top memory consumers.
The durable job queue resumed the in-flight run cleanly both times
(current_attempt advanced, generation restarted from the last durable
checkpoint) with no code change needed; this is the job system working as
designed, not a Code Generator defect.

## 2026-09-10 17:28 +05:30 - Pack A live disposition (slot 3) and trusted-motion-pattern validator fix

Run `5cf49daa-7ff5-404c-b884-d17cae272598` (Pack A retry, campaign-B slot 3)
reached `needs_attention` with `SOURCE_CONTRACT_FAILED`: two blocking
diagnostics, `SOURCE_MOTION_BEAT_UNIMPLEMENTED` and
`SOURCE_MOTION_REDUCED_MOTION_MISSING`, both on the hero's
`motion:home:hero-lifecycle-reveal` beat
(`src/routes/home-4ea14058/sections/home-hero-ecdc18c2.tsx`). Accepted
checkpoint `b3d5da49e957053ce94c72daa2d759e7725f9822b6cda1f0503c7ea95057e7a3`.

Root cause, confirmed by running `audit_typescript_source` directly against
the exact rejected checkpoint tree: the model correctly rendered the
trusted `<Reveal data-motion-target="hero-lifecycle">` component per the
beat's `pattern_id: "reveal-fade-rise"` (a catalogue-trusted pattern whose
entire CSS/JS animation lives in `motion.css`/`SharedSystems.tsx`, never in
a section's own owned source). Both `source_validation.py`'s pre-gate and
`normalize_route_batch_motion_sources`'s normalizer already carry this
exact exception (the former's own comment: "confirmed live: a valid
Reveal-based hero was rejected this way") -- but `typescript_ast_audit.py`'s
separate, final V4 motion-beat check never got the same fix, so it
unconditionally demanded transition/animation CSS and a
`prefers-reduced-motion` override in the section's own stylesheet
regardless of `pattern_id`, rejecting an otherwise-correct trusted-pattern
usage at the very last gate.

Commit `e7d9284` mirrors `source_validation.py`'s existing exception into
`typescript_ast_audit.py`: when a beat's `pattern_id` resolves via the
motion pattern catalogue, only require the target marker and the trusted
JSX tag (e.g. `<Reveal>`) to be rendered, skipping the CSS-property/
reduced-motion checks. Confirmation: re-running the validator against the
exact rejected checkpoint went from 2 diagnostics to 0; two new regression
tests (accept with trusted component + no CSS, still-reject when the
component itself is missing); full `typescript_ast_audit.py` suite (9/9)
and the broader `-k code_generator` selection (361 passed, same 3
pre-existing baseline/environment failures) both clean. Campaign-B slot 3
consumed; no ready result. Next: retry Pack A for slot 4 with this fix in
place.

Separately, this session found and worked around a local Windows dev-
environment issue (not a Code Generator defect): `scripts/run-native.ps1
api`'s hardcoded `--reload` makes uvicorn spawn the server as a reload-
supervisor subprocess, which uvicorn's Windows loop factory forces onto
`asyncio.SelectorEventLoop` -- and `SelectorEventLoop` does not support
`asyncio.create_subprocess_exec` on Windows, so every subprocess-based
check (node/npm/typecheck/build/browser launch) failed with a bare
`NotImplementedError` until the API was started without `--reload`. The
worker process is unaffected (it never goes through uvicorn), which is why
prior live slots 1-2 succeeded despite this. No source change was made for
this -- it is a local launch-argument choice, not applicable to the worker
that actually runs generation/build.

## 2026-09-10 15:55 +05:30 - Broken regression test traced to a test-fixture path mismatch; not a live defect

Five folders under `output/code-gen-output/` (`d24c1886`, `66c00daa`,
`b5b906d2`, `dac3c383`, `cd5b9c54`, timestamped 14:37-14:47) looked like new
live-campaign failures but were not: each `portfolio.json` shows
`call_count: 0`, `repair_rounds: 0`, and every `work_unit` still
`"status": "pending"` -- no model call was ever made. They were byproducts of
repeatedly running `tests/integration/test_code_generator_verification_worker.py
::test_verification_builds_and_promotes_a_clean_candidate`, whose fix (route
section ids renamed to route-namespaced `home:hero`/`home:project`) was left
incomplete before a Claude Code -> Codex -> Claude Code handoff.

Root cause: the test hand-wrote its "real" generated route content to
`src/routes/home-4ea140588150/index.tsx`, a path invented for the test with
no relationship to the route's actual (bare) storage key, `home`. The real
scaffold writer (`materialize_trusted_manifests`) and the route registry both
wire the router to `src/routes/home/index.tsx`, which the test never touched
-- so `validate_final_source` correctly inspected an empty placeholder and
raised all five `SOURCE_*_MISSING` diagnostics, deterministically, every
time this test ran. This is a self-contained test-authoring bug in one file,
not a live-pipeline defect -- confirmed by tracing every call site by hand,
not inferred from the error codes alone.

Fix: wrote the test's route content to `src/routes/home/index.tsx` (matching
the actual storage key), wrapped the navigation link in a real `<nav>`
landmark, and added the two closed-navigation-contract anchor links
(`#hero`, `#project`) the admitted "privacy-safe-v3" fixture requires.
The test now passes end to end (build, DOM/runtime verification, screenshot
capture, promotion). The stray output folders were deleted (gitignored,
untracked, test-run artifacts only).

A separate, real bug was found while tracing `d24c1886`'s mislabeled
failure: its real issue code (`PLAN_SECTION_COVERAGE`) never reached
`terminal_failure.code`/`evidence_summary.primary_issue.code` in the
exported `portfolio.json` -- both showed the generic `"needs_attention"`
instead, because `code_generator_verification.py`'s `_execute()` early-failure
branches (raised before a `VerificationProjection` exists) returned no
`"code"` key. Fixed by adding the real issue code to both branches. A new
regression test (`test_verification_surfaces_the_real_issue_code_not_the_
generic_status`) asserts the real code survives into the exported evidence.
See D-090 and D-091 in `DECISIONS.md`. Confirmation: both changed tests plus
the full `tests/integration/test_code_generator_verification_worker.py`
file pass (9/9); `ruff check`/`mypy` clean on both changed files; the
pre-existing DB-connectivity/resource-cleanup flakiness in
`test_code_generator_generation_worker.py` and
`test_portfolio_export.py::test_verification_handler_exports_on_needs_attention`
was independently reproduced on a clean `HEAD` (via `git stash`) and
confirmed unrelated to this change.

## 2026-09-10 14:15 +05:30 - Pack A live quality-review disposition and deterministic selected-work lifecycle cue

Run `f8a3d88c-9546-40fe-ae6b-714e775c4e24` reached `needs_attention` with
`QUALITY_REVIEW_REJECTED_AFTER_REPAIR` during verification. The normal API,
durable jobs, and worker path completed plan, acquisition, generation, and
verification without a worker error. The accepted checkpoint was
`b89f1e433d7e3339831da46c7112c79cdeef57e84a552a938446aaa89ca53c29`.

The integration review's single blocking finding was
`missing-selected-work-lifecycle-cue` at
`src/routes/home-4ea14058/sections/home-selected-work-2f0991ad.tsx:5`: the
selected-work section rendered its intro and three articles but omitted the
blueprint's sparse conceptual lifecycle cue beside those groups. The final
repair receipt hash was
`5ac54cd735290adb8b6582ce6eb44971575c5413cfc563b1fab113f34e02ddfe`; its
ledger file `ledger/repairs/65c8da3a510d5134ac4c6ce25bd6d57e7d833272b9ee3f081e7ba31fa9d4d61c.json`
changed only the hero stylesheet, so the blocking source remained unchanged.

Commit `d9caf30` adds a deterministic, idempotent host normalizer that runs
only for a v4 route batch whose approved blueprint contains a selected-work
section and lifecycle-cue thesis. It materializes a non-evidentiary
`observe`/`shape`/`deliver` marker treatment with scoped CSS, without changing
approved content, image retrieval, or dist/export behavior. Confirmation:
139 targeted tests passed, and the exact saved Pack A tree copied to a
disposable overlay passed `npm run source:audit` and `npm run typecheck` with
exit 0. No ready result or promoted preview was produced by this slot.

## 2026-09-10 14:00 +05:30 - Pack A live disposition and deterministic route-motion normalizer

Run `dd721d1e-cde9-4349-af50-27660ab6d779` reached `needs_attention` with
`SOURCE_REPAIR_EXHAUSTED` during route generation. Its initial route receipt
`e170f1a784920512ef8fdefed1cb3849d28b41bcd9164493c401ad254bb21970` contained
CSS length slips (`fiftych` and `sixtyfivech`), a trusted hero motion selector
that did not match the contract, and a custom selected-work motion beat using
`:has(.work-ready)` without the required guarded opacity/setter evidence. The
accepted checkpoint `0584a38d4ab6058d064e249cfc4c83c44374262cf76099724609cef62aa57442`
was only the pre-route foundation. Repair receipts
`3343dd8d62d5a81a1313bdc8b228211134a772218d0a1ba38a423f44a7a76d72` and
`f51d9622fdb8c79de6895b03a19894999261c0557f8521bde913015eaa5f4b44` show the
model corrected parts of the drift, but the final selected-work guard still
failed validation; the cumulative repair context does not establish that the
CSS length error recurred identically.

Commit `22db99c` adds deterministic host-side route-batch normalization for
spelled CSS lengths, trusted selector anchors, custom-motion guarded fallback
CSS, and exact `data-motion-ready` observer wiring. It does not alter image
retrieval or dist/export behavior. Confirmation: 33 source-validation tests,
the targeted post-fix suites (138 passed), a direct normalized Pack A route
contract check with zero diagnostics, and normalized-overlay typecheck exit 0.
The broader `-k code_generator` run passed 356 tests with four known
baseline/environment failures; no preview or ready result was produced by this
slot.

## 2026-09-10 12:00 +05:30 - Repair-budget default reconciliation

The configured repair policy was described two different ways: `settings.py`
declared 3 rounds per unit, 6 total, and 5 integration-polish rounds, while
`config/app.toml` supplied the effective 2/4/3 values used by live runs. The
five-slot campaign at the top of `docs/code-generator-live-campaign.md` is
the direct evidence that its failures were distinct validator, ownership, and
hidden-content defects rather than a repair that was converging when its
budget expired.

The fix adopts the app configuration as the Pydantic defaults (2/4/3), keeps
the `ge=1, le=6` bound, and leaves `config/app.toml` unchanged. The dead
`repair_depth` field remains in its three verification-handler write sites;
the live bound is `RepairBudget`, so removing an unused compatibility field
before a paid campaign would add risk without changing behavior. No force-
`dist` or image-retrieval change was made.

Offline confirmation: the settings-focused unit tests, mypy, and Ruff lint
passed; the targeted source/audit/repair/contract/export/image suites passed
136 tests. The requested verification-worker file retains one documented
pre-existing `PLAN_SECTION_COVERAGE` fixture failure, and file-level format
checking reports an older unrelated formatting issue at `settings.py:801`.
No live model call was used for this fix.

## 2026-09-10 00:03 +05:30 - Pack A live disposition and typography-token fix

Authorized run `bc4319fb-da84-4c00-88fc-9485a9087d9d` reached
`needs_attention` with terminal code `SOURCE_REPAIR_TOTAL_EXHAUSTED` during
`generating_routes`. Admission, planning, acquisition, foundation generation,
and route batches one and two completed; the accepted checkpoint was
`checkpoint-206348a511a77972369a` with checkpoint hash
`206348a511a77972369a79299c62545d94a5b7ca92e9663091a1a2ac3134572a`, source
manifest `e0536ea55d794f68f5a14437f8f78ac9a8f4dac6a3096152e587915741ccb693`,
59 files, and 1,068,723 bytes. The generation projection persisted seven call
receipts/attempts, four source repair rounds, and budget used four; route batch
three remained pending, so compose, integration review, verification, and
preview promotion did not run.

The root cause was a compiler vocabulary mismatch: the admitted blueprint
contained `type_steps` named `type-body`, `type-label`, `type-heading`, and
`type-display`, which produced `--type-type-*` properties, while the route
response used canonical `--type-heading-*` and `--type-label-*` properties.
Commit `90e8349` normalizes the names in the schema and compiler, protects the
trusted construction path, and updates planner guidance. This is a failed
slot with a targeted fix; the next slot is the live confirmation.

## 2026-09-09 23:39 +05:30 - Pack B live disposition and early disclosure gate

Authorized and recorded run `2f22c091-32e7-47dc-bc99-aef25d4e8058` reached
`needs_attention` with terminal code `INTEGRATION_REVIEW_UNRESOLVED` after
admission, planning, acquisition, and source generation. The accepted source
checkpoint is `checkpoint-45ab339bb9940d8268e6`, with checkpoint hash
`45ab339bb9940d8268e63715b94aba6b88d607ddab30a27497c4a44bf372f5b4`, source
manifest `dcfc97a0dde4af1fbfbd3592c37ea68fe36af77d78bc59fb7058884a095f4186`,
60 files, and 2,173,891 bytes. The generation projection records 14 call
receipts/attempts, three repair rounds, and a repair budget of three; no
verification or preview promotion ran. Final normalized quality contained one
advisory `blueprint-desktop-column-mismatch` and one blocking
`noninformative-disclosure`. The former misread D-076's abstract
`columns_desktop=8` as a literal CSS track requirement. The latter identified
`<Disclosure label="Details"><span aria-hidden="true" /></Disclosure>` in
`home-education-7cdb08f7.tsx` line 12. Commit `9716681` adds the early
host-owned disclosure diagnostic, preserves the advisory grid policy, and
aligns the generation/review prompts. The next authorized slot is the first
live confirmation of this fix.

## 2026-09-09 22:41 +05:30 - Toolchain preflight cleanup disposition

The API-level toolchain proof initially returned a generic blocked response
because Windows denied enumeration of a disposable preflight directory during
best-effort cleanup. `4da1ddb` makes optional tree removal return `False` on
that access error, preserving the actual proof result. After restarting the
API and worker with the required Windows child-process permissions, the API
preflight passed Node, npm, install, TypeScript, Vite build, browser, gateway,
and brief-path checks; no model call was used.

## 2026-09-09 22:22 +05:30 — Pack C live quality-gate disposition

Authorized live run `4dfd10cc-52bd-4fc7-8a6d-96addf47b26e` completed planning,
acquisition, and source generation, then stopped at the bounded integration
review with `INTEGRATION_REVIEW_UNRESOLVED`. The source checkpoint was retained
and the run correctly remained `needs_attention`; verification and preview
promotion did not run.

The provider supplied two subjective findings with codes
`blueprint-distinctive-move-missing` and `typography-role-coverage`. The old
keyword classifier persisted them as blocking because their evidence used
words such as “missing,” even though they described visual polish. The host
policy now maps known functional findings explicitly and keeps subjective
composition, typography, and motion observations advisory (`14bb97c`). The
strict terminal report and historical receipt/read-projection compatibility
fixes are in `c8a66e7` and `80a925c`.

Pack C remains a failed campaign slot, not an accepted portfolio. The exact run,
checkpoint, hashes, usage, and preview outcome are recorded in
`docs/code-generator-live-campaign.md`.

## 2026-09-09 20:31 +05:30 — Reliability plan implementation disposition

Commit `a503a4a` implements the reliability handoff through the offline
verification boundary. The new five-run campaign is recorded separately in
`docs/code-generator-live-campaign.md`; no new full pipeline call was made
before the implementation commit.

| Issue | Disposition | Implementation and verification | New live confirmation |
| --- | --- | --- | --- |
| R01 | fixed/verified offline | `core/generation_orchestrator.py` and `core/source_validation.py` retain complete pending proposals, overlay repairs, and keep rejected bodies restricted; `test_reliability_guards.py` covers sibling retention and integrity. | Pending campaign |
| R02 | fixed/verified offline | Durable attempt records, diagnostic history, and failure merges are persisted before error propagation in `core/generation_orchestrator.py`; accounting regression passes. | Pending campaign |
| R03 | fixed/verified offline | Generation-level counters and per-unit deltas are merged without cloning common prefixes; accounting regression passes. | Pending campaign |
| R04 | fixed/verified offline | `core/parallel_scheduler.py` has an actual serial stop-on-failure path; sibling-start regression passes. | Pending campaign |
| R05 | fixed/verified offline | `core/portfolio_export.py` and the verification failure handler export primary failures, pipeline issues, ledger counts, checkpoints, and safe evidence; report regressions pass. | Pending campaign |
| R06 | fixed/verified offline | Export evidence separates `referenced_in_source` from decoded/visible browser observations and records not-run states; image evidence regressions pass. | Pending campaign |
| R07 | fixed/verified offline | `core/image_policy.py`, planner validation, design realization, final source validation, runtime verification, and candidate identity carry one hashed image policy with distinct route obligations; image policy regressions pass. | Pending campaign |
| R08 | fixed/verified offline | `core/runtime_verifier.py` checks ancestor visibility, clipping/occlusion, lazy-image decode, frame geometry, and scroll restoration; runtime evidence regressions pass. | Pending campaign |
| R09 | fixed/verified offline | `core/layout_recipe_catalogue.py`, token compilation, prompts, and runtime checks share three typed marker-bound recipes; recipe floor regressions pass. | Pending campaign |
| R10 | fixed/verified offline | `core/component_admission.py` and acquisition admission validate exports, local imports, package subpaths, dependencies, CSS, and disposable TypeScript compatibility before optional materialization; admission regressions pass. | Initial/emergent full-pipeline confirmation pending |
| R11 | advisory/upstream | Image provenance and approved-slot policy are preserved in `core/image_policy.py`, acquisition, runtime evidence, and export. Semantic suitability of upstream decorative media remains an evaluator acceptance criterion. | Pending campaign |
| R12 | fixed/verified locally; Linux parity still blocked | `core/toolchain_preflight.py` runs the configured executable through disposable install, TypeScript, build, browser, and gateway checks; Linux/Azure image proof is unavailable in this workspace. | Local preflight passed; Linux unexecuted |

Offline verification for this commit: focused reliability/admission/image/export
tests pass (24 tests), the full Code Generator unit suite passes (299 tests),
Ruff, mypy, and compileall pass. The prior repository-wide run had seven
failures in stale integration fixtures, cross-test database contention, and a
separate Content Architect mock path; those are not represented as a green
repository-wide claim. No live campaign result is yet accepted.

## 2026-09-09 14:40 +05:30 — Repair lifecycle and evidence audit; next implementation plan

Read-only API checks confirmed the five continuation runs remain
`needs_attention`. Fresh compilation accepted all three current underscore-folder
brief pairs. No new full pipeline or portfolio model call was made in this audit.
The owner authorized a separate future campaign of at most five full runs after
implementation, stopping after two accepted cross-pack results.

Detailed handoff: `docs/code-generator-reliability-plan-2026-09-09.md`.
It contains exact saved-call references, issue IDs R01–R12, implementation work
packages, regression scenarios, preview/Linux acceptance and campaign commands.

New confirmed findings beyond the already-committed stale-operation fix:

- R01: `_run_unit` replaces its rejected-file inventory with the latest repair
  response, while `_apply_changes` applies that response over the accepted tree.
  On run `291ed5d7`, one corrected stylesheet therefore lost the other five
  proposed section files. Preserve and validate the merged pending proposal.
- R02/R03: `_run_route_batch_wave` merges receipts only after every scheduled
  batch succeeds; failure loses them from the durable projection. Success merging
  also omits repair totals/strategies. The generation API currently reports zero
  calls/repairs despite saved batch calls. R04 records the scheduler's lack of
  explicit sibling failure cancellation as a required regression scenario.
- R05/R06: the failed export omits route/input/call/image evidence and its report
  ignores terminal issues. The successful-export image summary uses a source
  regex as `rendered` evidence, not browser observations. These require separate
  fixes to accounting, metadata wiring and evidence semantics.
- R07–R12: independently enforce image policy through runtime; test ancestor
  visibility; align exact layout selectors with tested recipes; preflight
  optional component compatibility and platform toolchains. Visual inspection
  found C's decorative craft-table photo poorly matched to its technical work;
  it is an upstream optional pin, not download corruption. Prefer its approved
  abstract illustration and restrained optional-media selection.

Offline evidence: replaying the final `557d90fb` response against its actual
batch tree passes source-policy and route-batch checks with five creates/one
replace; a fresh offline npm install and app/node TypeScript checks also pass.
Overlaying the first one-file repair on the full initial proposal eliminates
the missing-section cascade but still exposes one exact layout-selector
diagnostic. Neither experiment proves route composition, full build, browser
acceptance or promotion. Focused existing regression suites passed after an
approved rerun resolved pytest temporary-directory permissions.

Disposition: investigation/plan complete; R01–R12 are not marked implemented.
Implementation source and prior campaign records are unchanged by this entry.

## 2026-09-09 13:45 +05:30 — Five-run variable-brief campaign and repair-state fix (Codex)

The continuation campaign used the three eligible Build Preparation packs and
stopped at the requested five full-pipeline calls. No sixth call was made.

| Run | Pack | First durable outcome | Root cause / disposition |
| --- | --- | --- | --- |
| `55234cbb-32f3-475f-8716-affce08c8c3f` | Maya (`5f144f04-2789-48c6-9b1c-6bd11c87abdb`) | `needs_attention` during acquire: `DEPENDENCY_INSTALL_FAILED` | Native Windows overlay configured `npm_executable="npm"`, but direct subprocess execution could not start the PowerShell shim. Fixed in `d1c5645` by resolving the executable with `shutil.which()` before launch. |
| `beb5e244-8787-4dcb-8c08-67fac19bcbe5` | Akash (`ba4b986e-7841-4cfb-94a0-d56fbe1b7956`) | `needs_attention` during acquire: offline `npm ci` missing `@emnapi/wasi-threads` and `tslib` | Platform-aware npm lock projection left optional/transitive entries that the warmed Windows cache could not satisfy with `npm ci`. Fixed in `2b2714a` by using offline `npm install --ignore-scripts --prefix` to repair the lock projection, then binding the final lock hash. |
| `e5e32ac3-89d4-48ad-bbaf-4eb5e8927ee6` | Akash | `needs_attention` during plan: `PLAN_CONTENT_KEY_COVERAGE` | The planner omitted the complete content-key list for `home:capabilities` on one retry and omitted image placements on another. Fixed in `97d83dd` by host-canonicalizing known section bindings to the exact content manifest and requiring planner image policy/coverage before acceptance. |
| `e39ee9e6-b71a-430b-bc7a-934046579f27` | Akash | `needs_attention` during generation: `FOUNDATION_SOURCE_CHECK_FAILED` | The admitted `highlighter` component imported unsupported `rough-notation` alongside `motion/react`; the brief declared only the supported `motion` package. Fixed in `59bf982` with an acquisition-time unsupported-import gate that falls back before source enters the generated tree. |
| `291ed5d7-6a7d-44c8-b024-fbb7dbf8c5c8` | Varun (`c0860464-a786-43d8-9c30-d12d7516c4b8`) | `needs_attention` during generation: `SOURCE_REPAIR_EXHAUSTED` | The first route response was rejected for `SOURCE_CSS_INVALID_LENGTH` (`fiftych`). A bounded repair created the missing stylesheet; the next repair returned `create` for that now-existing stylesheet plus `create` for still-missing files. Strict validation rejected the mixed response as `SOURCE_CREATE_EXISTS`, exhausting the repair budget even though ownership and content were bounded. Fixed in `29fc598`: repair validation now reconciles stale `create`/`replace` tags with the actual candidate tree after ownership/trusted-file checks; initial generation remains strict. |

Evidence for the fifth-run diagnosis is retained in
`.workspace/code-generator-generation/291ed5d7-6a7d-44c8-b024-fbb7dbf8c5c8/route-batches/home-4ea14058-batch-1/`:
the `663618e4…`/`c421377e…` contexts show the changing candidate inventory, and
call `557d90fb…` contains the mixed operation response. Offline replay now
normalizes the existing stylesheet to `replace` and the five absent files to
`create`, with no `SOURCE_CREATE_EXISTS` error. The run never reached a
checkpointed route, clean build, preview, or ready state; acquired image
renditions remain in the failed-run export for inspection. Static verification
after the fix: 285 Code Generator unit tests passed, plus Ruff, mypy, and the
focused replay. The live campaign is closed at five full runs.

## 2026-09-09 03:00 +05:30 — Variable Build Preparation reliability pass (Codex) [2f424e5]

This entry records the implementation checkpoint that follows the previous
`PLANNER_OUTPUT_INVALID`/`needs_attention` handoff. The supplied current
Build Preparation mirror has two valid pairs under `output/build_preparation`:

- `5f144f04-2789-48c6-9b1c-6bd11c87abdb` — Maya Bennett; 1 route, 7 sections,
  8 resources, 3 components; content hash
  `a839ee313e9786e3e77d60a4fa6bdce5a1f55dccff5f92349ac46e88419c5210`; visual
  hash `389ce59c85baafce6b734b105bff05bbbb7454d68a6a84f9848429e691cd0427`.
- `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` — Akash Ojha; 1 route, 7 sections,
  8 resources, 3 components; content hash
  `db560919f26b359ce7836c40339c887b3faa001637452c2d672d1193b9155435`; visual
  hash `ff324462dc980bf29deb05bc4533716e55940babb40497170d668d8492f21f74`.

Both compile through the same brief contract. The two empty-title/section
pairs in the mirror are retained as negative validation fixtures only; they
are not eligible live inputs. The older four-route canonical pair remains
available for regression comparison but is not substituted for the owner's two
current inputs.

The implementation now normalizes only exact host-known planner identities and
reserved color aliases, bounds planner retries, writes restricted planner
attempt evidence, detects undeclared supported imports before foundation
typecheck, and applies one host-owned blocking/advisory finding policy. A
clean build with network-safe runtime evidence can produce an unverified
candidate preview; it never replaces the active verified preview. The npm
cache warmer now proves an offline install from a disposable project.

Static verification is complete. The authorized live campaign is deliberately
limited to four full pipeline slots and stops after the first one or two
successful `ready` runs; each reservation, run ID, failure trace, artifact,
preview, and model usage is recorded in
`docs/code-generator-live-campaign.md`. No live outcome is claimed here until
the standard API/worker/preview services are restarted on this commit.

Live slot 1 completed successfully after that restart. Run
`4d009f48-050e-48a7-9611-82f3a5eecd91` used pack A, validated one route and six
work units, produced an accepted 109-file source checkpoint, and reached
`ready` with build hash
`a07ca2b24ed904431d377df474ba8a47a7adfec3b1942bfe8440eabf08622f10`. The
first verification worker was subject to this Windows execution sandbox's
Node child-process restriction (`spawn EPERM` in Vite/esbuild); `npm run check`
passed and an elevated worker rebuilt the identical checkpoint successfully.
The browser smoke gate then passed and promoted the active preview at
`http://127.0.0.1:4174/preview/preview-6esue4fssmj3unpkzxeclt6onwqnxdwazwrdptyikrbtashb/`.
The export is `output/code-gen-output/03-34-09-09-2026-4d009f48` with a real
`dist/` (66 files). Runtime verification retained 43 geometry/visual
observations as advisories and no blocking findings. The verification retry
reused the accepted checkpoint; it was not a second full pipeline slot.

Per the campaign guardrail, the live campaign stopped after this first
successful `ready` result. Pack B remains unrun and available for a future
cross-pack confirmation; no slot 2–4 calls were made.

## 2026-09-09 00:xx +05:30 — Reliability/cost fix pass + new bundle validation + live-test phase, still zero `ready` (Claude Code) [44304ff, 2790e9d, a2ae087, 051afa6, f20779f]

Owner asked for a final pre-Azure pass on Code Generator: tighten the
repair/generation/review loop, investigate a suspected billing/retry-loop
issue, restore a production "Generate & Preview" `/app` stage, prep Azure
Compose/Caddy overlays, and validate + live-test the new Build Preparation
bundle (`20-46-08-09-6b899b90`, "Maya Bennett") before spending more money
on it.

**Fixed, all root-caused from real code/DB evidence, none guessed:**

1. **`FinalRepairError` had no escape hatch for an honest
   `cannot_complete` repair response** — `final_repair.py` raised the same
   generic error for a genuinely declined repair as for any other failure,
   so `_run_bounded_repair` kept retrying to budget exhaustion instead of
   stopping early. Added `FinalRepairDeclined` with a `safe_reason`, and a
   dedup: two identical declines in a row now stop immediately instead of
   burning a third model call. [44304ff]
2. **`RUNTIME_REGION_WIDTH_RATIO` reported one shared defect as N
   unrelated findings** when multiple regions measured the identical
   content width against `main` — added explicit shared-cause correlation
   text to the diagnostic bundle instead of N independently-worded
   findings. [44304ff]
3. **Code Generator's prompt-cache keys were scoped per-generation**
   (`codegen:{generation_id}:{role_profile}`), defeating cross-run reuse of
   the large stable system-prompt/schema prefix — the exact waste pattern
   `docs/research/api-usage-cost-cache-and-multi-provider-remediation-plan.md`
   measured as most of a day's spend. Rekeyed to
   `codegen:{role_profile}:{operation}:{operation_hash[:16]}` in
   `generation_orchestrator.py`, `integration_review_operation.py`, and
   `final_repair.py`. [44304ff]
4. **Round/attempt budgets tightened** (evidence-balanced, not the research
   doc's more aggressive default): `max_repair_rounds_per_unit` 3→2,
   `max_repair_rounds_total` 6→4, `max_integration_polish_rounds` 5→3, plus
   a dedicated `code_generator_max_attempts = 2` job-retry override
   (previously shared the general `max_attempts = 3`). [44304ff]
5. **A pinned component's undeclared npm import was never resolved as a
   dependency** — root cause: the two-Markdown-brief handoff format has no
   field for a pinned component's own npm dependencies at all (confirmed:
   zero `dependencies`/`registry_dependencies`/`resolution_type` mentions
   anywhere in the new bundle's fenced JSON index), so
   `candidate.dependency_metadata` is always empty and
   `Cannot find module 'motion/react'` failed typecheck with nothing to act
   on. Added `detect_supported_import_dependencies()` — a source-scan
   against the configured allowlist only, never an arbitrary install — wired
   into both the actually-exercised `_execute_acquisition` path and the
   emergent `_resolve_requests` path. Live-confirmed: the next run correctly
   triggered dependency resolution for the first time this engagement. [051afa6]
6. **Planner accent/color-token collision, root-caused to the bundle's own
   prose** — the new bundle's visual brief says "one confident technical
   accent," and the model kept naming its literal `colors[*].name` token
   `"accent"`, colliding with the reserved `shadcn_theme_bindings` slot key.
   Added explicit guidance to `planner.md`: design-language words like
   "accent"/"primary action"/"muted background" name a *concept*, not a
   literal token string — pick an unrelated concrete name for the token
   itself. Live-confirmed: planning passed cleanly on the next run. [f20779f]

**Also shipped this pass, not reliability fixes:**

- Restored and adapted a production "Generate & Preview" stage in `/app`
  (merged into one stage, not two), superseding D-063's dev-only boundary —
  new `DECISIONS.md` D-081. [2790e9d]
- Checked in Azure production Compose/Caddy/TOML overlays matching the
  existing runbook exactly, including fixing `preview_base_url` so it no
  longer bakes in `localhost` for a real browser hitting the VM's domain.
  [a2ae087]

**Bundle validation (free, no model calls):** the new bundle
(`20-46-08-09-6b899b90`) was checked directly against
`brief_ingestion.py::compile_briefs()` before any live spend — compiles
cleanly, 4 routes, 22 sections, 23 resources, 13 components, target
`react-vite-v1`, contract hash `05db2d1b…`. Structurally good going in.

**Live-testing phase, in order, real OpenAI calls, all against the new
bundle (`20-46-08-09-6b899b90`) unless noted:**

1. Two consecutive runs failed outright on `OPENAI_API_KEY` auth (401) —
   not a pipeline bug. First was a genuinely invalid/expired key; second
   was the already-running API/worker processes still holding the *old*
   key in memory after the owner rotated it (pydantic-settings reads
   `.env` once at process start). Fixed by restarting both processes clean.
2. `FOUNDATION_SOURCE_CHECK_FAILED` — `Cannot find module 'motion/react'`
   — this is fix #5 above, root-caused and fixed from this exact failure.
3. Two runs hit `PLANNER_OUTPUT_INVALID` on the accent/color-token
   collision (fix #6) — first on `destructive, input`, then specifically on
   `accent`. Fixed by the `planner.md` guidance; the next run's planning
   passed cleanly.
4. One run reached `acquiring` for the first time (dependency-scan fix #5
   correctly triggered) and failed `DEPENDENCY_INSTALL_FAILED` /
   `ENOTCACHED` — the offline npm cache
   (`.workspace/npm-cache`) had never cached `motion`/`framer-motion`/
   `motion-utils`. Not a code bug: a `--package-lock-only` warm attempt was
   insufficient (metadata only, not tarballs); a full `npm install` with
   `npm_config_cache` pointed at the real cache path fixed it, confirmed via
   a clean `npm ci --offline` afterward.
5. **Final run, `fca37030-09bb-43a9-8c42-ff0e9410dd3d`, with every fix
   above in place together for the first time** (accent-collision guidance +
   dependency-scan + warmed cache): `needs_attention` again, but on a
   **brand-new, not-yet-investigated** failure, and earlier than any prior
   step — it failed during **planning itself** (`coordinator_stage: "plan"`),
   before acquire/generate ever started:
   ```
   PLANNER_OUTPUT_INVALID: root: Value error, distinctive move references an unknown region
   ```
   Source: `development_schemas.py:1866` —
   `ExperienceBlueprintV4`'s own cross-reference validator rejects a
   `distinctive_moves` entry whose `region_id` doesn't match any
   `region_id` the same planner response declared in `section_regions`.
   This is the model referencing a region it never declared, in the same
   structured response — a different validator, a different route/root
   cause category from anything fixed tonight. **Not root-caused past the
   validator message itself**: no `planner_receipt`/`plan_summary` was
   persisted for this attempt (the response never validated far enough to
   be stored), so there is no artifact showing which region/route the model
   invented, unlike every other fix tonight which had a real payload to
   inspect. A plausible next step (unverified) is the same style of fix as
   #6 — explicit planner guidance to double-check every `distinctive_move`'s
   `region_id` against its own `section_regions` list before returning — but
   that is a hypothesis, not a confirmed root cause.

**Honest bottom line, unchanged in kind from every prior session:** zero
`ready` outcomes tonight, across every attempt. Every genuinely reproducible
bug found this session (auth/env, missing dependency, accent collision, npm
cache) was root-caused and fixed, and each fix was live-confirmed to clear
its own specific failure on the very next attempt — but the pipeline keeps
surfacing a new, different structural non-determinism each time it clears
the previous one, exactly this project's dominant pattern across its whole
history. The last run of the night got further in *category* (all the way
to a fresh planner-only validation miss, past every previously-fixed gate)
but not further in *pipeline stage* than several earlier runs this
engagement — it failed at planning, before acquire/generate ever ran, so it
produced no export, no `dist/`, nothing new to hand the owner to run
manually. No portfolio from tonight's testing is ready to preview.

## HANDOFF — 2026-09-08 00:xx +05:30 — Claude Code (Sonnet 5 / Anthropic) session ending, full state below

This is a deliberate, complete handoff. This session's own work is finished
and committed; the owner is ending this chat and another agent (possibly a
different model/tool) will pick this up next with no memory of this
conversation. Everything below is what that agent needs, in one place.
Read this whole entry before touching anything.

### Where the branch actually is

Branch `codex/code-generator-control-room`, 28 commits ahead of
`origin/codex/code-generator-control-room`, not pushed. This session's own
commits, oldest to newest:

```
3f5b2aa feat(code-generator): auto-build failed exports, fix two live-confirmed generation defects
06516b1 docs: record auto-build/export-gap fixes
5bef169 fix(code-generator): quote-tolerant motion-selector check, distinctive-move repair guidance for review findings
ac5543e fix(code-generator): explicit CSS longhand guidance for shorthand-vs-longhand distinctive-move findings
dc01c75 docs: record root-cause fixes and 2 more live runs
7f09506 feat(code-generator): unverified candidate preview for needs_attention runs, fix uncommitted export_receipt write
f0760f0 docs: record candidate-preview feature, cost-leak catch, and commit-bug fix   <- HEAD
```

Working tree has pre-existing dirty state that is **not this session's
work** and was deliberately left alone all session (per AGENTS.md's
"treat every pre-existing change as another contributor's" rule) — do not
assume these are yours to commit or discard without checking with the
owner: `PLAN.MD` (modified), `docs/research/doc/api-usage-cost-cache-and-
multi-provider-remediation-plan.md` (deleted) with two new untracked files
in `docs/research/` in its place, `output/code-gen-output/02-23-06-09-2026-
fa31c124/source/package.json` (modified), and a new untracked
`tests/test_gemini_api_keys.py`.

### What is actually proven true right now

- **The code generator has never once reached `ready`** in any live run
  this whole engagement, as far as this session's testing shows. Today
  alone: 6 live runs, 6 `needs_attention` results, each on a genuinely
  different finding. Do not let a clean-looking `dist/` fool you into
  thinking a run "worked" — see the three specific runs below where the
  build was perfect but the pipeline's own review correctly (or
  incorrectly, case by case) rejected it anyway.
- **It has only ever been tested against ONE Build Preparation input**:
  `output/build-preparation/01-31-04-09-94ae4a9c/` ("Arjun Mehta — Senior
  UI/UX Designer", real `content_architect_content_hash`). Every fix made
  this session was diagnosed from that one brief's content and structure.
  There is zero evidence any of it generalizes to a different portfolio.
  `scratch/run_live_generation.py` hardcodes this exact pack id, which is
  why every scratch-driven test this whole engagement used it — that is
  the mechanical reason, not a deliberate choice. Testing genuine
  generalization requires either a different real Build Preparation pack
  (running Discovery → Content Architect → Visual Design Director → Build
  Preparation for new input content first) or the front-end's own pack
  selector once a second real pack exists.
- **The auto-build-on-export capability the owner originally asked for is
  proven working**, confirmed across 3+ independent runs — a
  `needs_attention` export now reliably ships a real `dist/` with an
  honest `build_attempt` status instead of source-only silence.
- **The new "unverified candidate preview" dev-harness feature is proven
  working end to end** — live-verified via real browser interaction, not
  just unit tests, including surviving a full page reload.

### The 6 live runs from today (2026-09-07), in order, with exact findings

1. **`e624bd75`** — `needs_attention` / `SOURCE_REPAIR_EXHAUSTED`. Lost the
   entire route batch (zero sections ever accepted — `repo_dir` held only
   the bare foundation checkpoint). Root cause: a motion-beat check
   required the blueprint's literal double-quoted
   `[data-motion-target="approach-spine"]` verbatim; the model's
   equally-valid single/unquoted form wasn't recognized. **Fixed** in
   `5bef169` (`source_validation.py::_literal_present`). Ran before the
   fix existed; no export exists for this run (also predates the
   generation-stage export-gap fix in `3f5b2aa`).
2. **`c8cd8f1c`** — `needs_attention` / `INTEGRATION_REVIEW_UNRESOLVED`
   after 5 polish rounds. Real defect: a distinctive-move runtime marker
   sat on `.selected-work__index` (nested div) while the actual grid/
   max-width layout lived on the parent `.selected-work`. Repair kept
   failing because the review reported it under its own code
   (`distinctive-move-selector-mismatch`), not the structural code
   `repair_source.md` already had a dedicated bullet for. **Fixed** in
   `5bef169`. This run's export is the first confirmation the auto-build
   fix works (`build_attempt: success`, real `dist/`).
3. **`e7784314`** — `needs_attention` / `INTEGRATION_REVIEW_UNRESOLVED`
   after 5 polish rounds, ran after the `5bef169`/`ac5543e` fixes. Two
   **not-yet-investigated** findings: (a) `blueprint-distinctive-move-
   missing` — the systems/capabilities section's blueprint calls for a
   keyboard-accessible progressive-disclosure control; the model rendered
   a plain static `<ul>` instead, entirely omitted. (b) `resource-frame-
   aspect-mismatch` — the hero atmosphere frame has no explicit
   `aspect-ratio` for a portrait-oriented admitted resource, so the
   required wide framing never actually applies.
4. **`4dbcabae`** — `needs_attention` / `QUALITY_REVIEW_REJECTED_AFTER_
   REPAIR`. The deepest run before today's last one: `generate: succeeded`
   → DOM/runtime verification → one repair round → whole-site re-review
   → rejected on a CSS `gap` shorthand partially overridden by
   `column-gap` alone, leaving `row-gap` correctly cascading but never
   present as a literal property name. **Fixed** in `ac5543e` (this run
   predates that fix).
5. **`5819492d`** — `needs_attention` / `DOM_RUNTIME_FAILED`. Generation
   succeeded, but DOM/runtime checks failed with FIVE diagnostics at once
   (`RUNTIME_DISTINCTIVE_RELATIONSHIP`, `RUNTIME_REGION_COLUMN_COUNT`,
   `RUNTIME_REGION_GAP`, `RUNTIME_REGION_MEASURE`,
   `RUNTIME_REGION_WIDTH_RATIO`), and **the bounded final-repair mechanism
   itself threw `FinalRepairError: The repair operation did not return a
   bounded source correction`, three times in a row** (see
   `src/oryxenai/agents/code_generator/core/final_repair.py:196` and its
   caller `code_generator_verification.py::_run_bounded_repair` around
   line 1533). This is qualitatively different from every other finding
   this engagement — the repair *mechanism itself* is erroring, not just
   producing a wrong fix. **Not investigated.** Highest-priority unknown.
6. **`0ffd6cec`** (triggered from the real front-end, not the scratch
   script) — `needs_attention` at the verify stage. Reached the whole-site
   review with **zero repair rounds needed for the first time all
   session**, then failed final DOM/runtime verification on
   `RUNTIME_REGION_WIDTH_RATIO` — three *different* regions
   (`home:selected-work`, `home:approach`, `home:experience`) all measured
   the **identical 0.877 ratio**, each just outside its own individually
   different allowed range. Three regions landing on the exact same
   number is not three coincidental defects; it strongly smells like one
   shared systemic cause (a page-level container width, most likely) —
   exactly the shape of every other real bug found this engagement.
   **Not investigated. Second-highest-priority unknown, and probably the
   single best next lead** — see `source_validation.py`'s region
   width-ratio measurement code and whatever computes the page's overall
   content-container width for the generated route.

### Two operational bugs found and fixed this session (read before running anything)

1. **Never run `scratch/run_live_generation.py`-style direct handler
   invocation and then start a real worker without cleaning up first.**
   That script calls job handlers directly, bypassing the queue's claim/
   complete mechanism entirely — every job row it touches stays `queued`
   in `background_jobs` forever. Today, 95 such rows had piled up since
   2026-09-05 across this whole engagement. The moment a real worker
   started, it began reprocessing them oldest-first — **real paid OpenAI
   calls against runs that had already concluded days earlier** — with
   any new legitimate run stuck at the back of a 96-job queue. Caught
   within seconds by noticing the worker log showed generation-stage
   operations while the new run was still on `plan`. If you use that
   script again, either avoid starting a real worker afterward, or query
   `background_jobs` for `status IN ('queued','running','retrying')` and
   cancel (`status='cancelled'`, with a reason recorded, never delete)
   every row not belonging to the run you actually care about, *before*
   starting any worker.
2. **`CodeGeneratorDevelopmentRepository.compare_and_swap()` never commits
   internally** (`src/oryxenai/db/repositories/code_generator_development.py`)
   — it executes the UPDATE but the caller must call `await db.commit()`
   inside the same `async with sessionmaker() as db:` block. The first
   version of this session's `export_receipt` write (all three call sites,
   plus a manual verification script) silently didn't persist because of
   this — no exception, no error, just a write that quietly rolled back.
   Caught only by checking the real API response after implementing, not
   by trusting a clean test run. Fixed in `7f09506`. **Whenever you add a
   new `compare_and_swap` call site, verify the write actually persisted
   by reading it back through a fresh query or the real API — never trust
   "no exception was raised."**

### Environment state as this session ends

- **Nothing is currently running.** The API server, worker, and preview
  gateway I started for live browser testing were all auto-killed by the
  harness's low-memory protection near the end of this session — the
  machine has genuine memory pressure from the owner's other apps (3x
  ChatGPT, an IDE, Chrome, Slack), not from anything this session left
  running. To use the dev harness at `http://127.0.0.1:8000/dev/code-
  generator-development`, you need all three running simultaneously:
  `scripts/run-api.ps1` (port 8000), `scripts/run-worker.ps1`, and
  `scripts/run-preview-gateway.ps1` (port 4174 — without it the page
  reports "preview gateway is unreachable" and the new candidate-preview
  route silently has nothing to embed). None of these auto-reload; after
  editing `routes.py` or a job handler, kill and relaunch the affected
  service manually.
- **A real, minor, unfixed bug**: `output/build-preparation/` has 10
  identical-content folders dated 2026-09-07 (`14-21-...` through
  `17-13-...`), all titled generic "Portfolio" with an empty
  `content_architect_content_hash`, timestamped almost exactly when this
  session was navigating the dev-harness front-end. This looks like a
  "local debug mirror" (mentioned in `AGENTS.md`'s Build Preparation
  section) being rewritten on every front-end page load or readiness
  poll, producing junk duplicate folders instead of one real mirror.
  **Not investigated.** Whatever writes these should probably write once
  per actual Build Preparation completion, not once per read. Do not
  mistake these 10 folders for genuine alternate test inputs — they are
  not real portfolios, just an empty placeholder repeated.

### Recommended order of work for whoever picks this up

1. Read this entry fully, then skim `DECISIONS.md` (D-077 onward) and the
   `## Recent changes` head of `CHANGES.md` for the same period, before
   touching code.
2. Investigate finding #6 first (`RUNTIME_REGION_WIDTH_RATIO`, identical
   0.877 across 3 regions) — the "same number in three unrelated places"
   pattern is the strongest actionable lead left, and matches this whole
   engagement's dominant bug class (a systemic measurement/generation
   issue, not independent content noise).
3. Then finding #5 (`FinalRepairError` — the repair mechanism itself
   erroring) — read `final_repair.py` around its `repair()` method and
   understand exactly what shape of model response it fails to parse into
   "a bounded source correction," since this blocks repair entirely
   rather than just producing a wrong result.
4. Findings #3's two items (missing disclosure control, hero aspect-ratio)
   are real but lower-severity and more contained — reasonable to defer.
5. Before spending more live-test budget: confirm the real OpenAI balance
   with the owner directly (this session's 3 runs with recorded receipts
   alone totaled ~2.72M input / ~137K output tokens; a 4th run had none
   recorded because it failed before any work unit was accepted, meaning
   true spend today is higher than that number).
6. Seriously consider whether testing against a second, genuinely
   different Build Preparation input is worth prioritizing over continuing
   to fix findings from the one input tested so far — single-input testing
   has been this whole engagement's blind spot the entire time, not just
   today.
7. Continue this file's own logging convention: one entry per session/
   investigation, chronological, most-recent on top, commit hash in the
   header, honest about what's proven vs. not.

## 2026-09-07 (evening) — Live dev-harness end-to-end test surfaces a stale-job cost bug and an uncommitted-write bug; adds unverified candidate preview (Claude Code) [7f09506]

Owner asked to switch from the scratch script harness to the real `/dev/
code-generator-development` control room (API + worker + preview gateway,
driven by real browser clicks) so a run could actually be watched and
previewed the way a real user would. Two real bugs found this way that
no amount of code review or unit testing would have caught:

1. **Starting a real worker immediately began burning money on stale
   work.** The scratch script (`scratch/run_live_generation.py`) calls
   job handlers directly and never marks the underlying `background_jobs`
   row complete. 95 such rows had piled up since 2026-09-05 across this
   whole engagement. The moment a real worker started, it began
   reprocessing them oldest-first -- real paid OpenAI calls against runs
   that already concluded days ago -- with the new run stuck at the back
   of a 96-job queue. Caught within seconds by noticing the worker log
   showed generation-stage operations when the new run was still on
   `plan`. Stopped the worker, cancelled all 95 stale rows (recorded with
   a reason, not deleted), restarted clean. Not a pipeline defect --
   an operational hazard specific to mixing the scratch harness with a
   real worker, now understood and documented.
2. **The needs_attention preview feature (below) silently didn't
   persist**, caught only by checking the actual API response after
   implementing it, not by trusting a green test run. `compare_and_swap()`
   never commits internally; none of the three `export_receipt`-writing
   call sites (nor a manual verification script) called `db.commit()`
   after it. The write looked like it succeeded and produced no error,
   but silently rolled back. Fixed all three call sites plus the
   verification script; confirmed persistence via a direct API check and
   a full page reload before considering it done.

**Feature added, live-verified end-to-end:** a needs_attention run's own
already-built `dist/` (real since the auto-build fix earlier today) is
now shown in the dev harness's preview panel instead of "Preview
unavailable" -- clearly labeled "Unverified candidate · not promoted"
(amber, distinct from the mint "Verified preview promoted" and the coral
error state) so it can never be mistaken for a passed run. Verified live:
triggered a real run from the UI, watched it progress through every
stage via a Monitor loop, confirmed the candidate route serves real
assets (JS/CSS/fonts/images, all 200), confirmed the embedded preview
bridge handshake completes ("Embedded preview connected."), saw the
actual generated portfolio render inside the frame, and confirmed the
state survives a full page reload -- directly addressing the owner's own
worry that a refresh would lose it.

**This run's actual pipeline outcome, for the record:** reached the
whole-site review with zero repair rounds needed (a first this session),
then failed final DOM/runtime verification on `RUNTIME_REGION_WIDTH_RATIO`
-- three different regions (`selected-work`, `approach`, `experience`)
all measured the identical 0.877 ratio, each just outside its own
individual allowed range, suggesting one shared systemic cause (likely a
page-level container width) rather than three unrelated defects. Not
investigated this pass -- logged for a future one.

## 2026-09-07 (later) — Root-caused both prior live failures from real DB history, fixed 3 more validator/prompt bugs, live-tested with 2 more fresh runs (Claude Code) [5bef169, ac5543e]

User corrected a run-numbering mix-up: the run they saw succeed and produce
visible output was `c8cd8f1c` (this session's earlier auto-build fix
working); the run they never saw anything for was `e624bd75` (predates that
fix -- the exact run that exposed the gap). Asked for both prior runs'
actual generation failures to be understood deeply (not just described) and
fixed, then re-verified with 2 more live runs before calling anything done.

Investigated using the real DB-persisted history
(`code_generator_events`, `generation_projection`, `integration_review` --
not just the terminal `SafeIssue` text, which is deliberately compact) via
a one-off inspection script. Two root causes found and fixed:

1. **`e624bd75`** exhausted its full 3-round per-unit repair budget on
   `SOURCE_ROUTE_BATCH_MOTION_INVALID` for `motion:home:approach-progress`
   and lost the entire route batch (repo_dir held only the bare foundation
   checkpoint -- confirmed via `repair_rounds: 0`/`repair_budget_used: 0`
   in the persisted projection, meaning the whole batch never got
   checkpointed even once). Root cause: the check required the blueprint's
   literal `[data-motion-target="approach-spine"]` (double-quoted) to
   appear verbatim; `[attr='value']` and `[attr=value]` are equally valid
   CSS, so a model choosing either was indistinguishable from one that
   never wrote the selector, with no way to diagnose why across all 3
   attempts. The codebase already handles this quote-tolerance elsewhere
   (`data-interaction-id`, `aria-label` regexes) -- this check used a naive
   substring test instead. Fixed in `source_validation.py`
   (`_literal_present`, applied to the marker/selector checks and
   `_css_rule_contains`).
2. **`c8cd8f1c`**'s whole-site review correctly caught a real defect
   (distinctive-move marker on `.selected-work__index` while the actual
   grid/max-width lived on the parent `.selected-work`) but 5 polish rounds
   never fixed it. Root cause: the review reports this under its own code
   (`distinctive-move-selector-mismatch`), not the structural
   `SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID` code `repair_source.md`
   already had a dedicated, correct bullet for, so repair fell back to
   generic guidance. Extended that bullet to cover the review's own code.

**Live-tested with the 2 more runs the owner authorized** (`e7784314`,
`4dbcabae`, fresh, canonical brief pack, real OpenAI calls):

- `e7784314`: no recurrence of either fixed defect. Got past generation
  entirely this time (no `SOURCE_REPAIR_EXHAUSTED`), but still hit
  `INTEGRATION_REVIEW_UNRESOLVED` after 5 polish rounds -- on two entirely
  different findings (`blueprint-distinctive-move-missing`: a required
  progressive-disclosure control was never implemented at all;
  `resource-frame-aspect-mismatch`: hero frame missing an explicit
  aspect-ratio for a portrait-oriented resource). Logged, not
  investigated -- confirms every run still tends to surface its own new
  finding rather than converging.
- `4dbcabae`: **the deepest run this whole engagement has recorded** --
  `generate: succeeded`, DOM/runtime verification, one repair round, and a
  full whole-site re-review, the same milestone as the prior session's best
  run but from completely fresh generation-stage content, confirming the
  quote-tolerance and export fixes hold up. Ended `needs_attention` /
  `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on one narrow, new finding:
  `.approach`'s CSS sets `gap: var(--space-8)` on its base rule and
  overrides only `column-gap` inside a `min-width` media query -- `row-gap`
  cascades in correctly and the layout is functionally right, but the
  literal property name `row-gap` never appears anywhere in the file, and
  a check requiring that exact name can't recognize a shorthand as
  satisfying it. Same naive-text-matching blind-spot pattern as every
  other validator bug this engagement, just for CSS shorthand vs. longhand
  this time. Fixed with route_batch.md (avoid the shorthand-plus-partial-
  override pattern) and repair_source.md (split into explicit longhands
  when a finding names one) guidance.

**Confirmed working across all 3 post-fix exports** (`c8cd8f1c`,
`e7784314`, `4dbcabae`): every one shipped `build_attempt: {"status":
"success"}` with a real `dist/` -- the auto-build-on-export fix is now
solidly proven, not a one-off.

**New, not yet investigated:** `4dbcabae` (a run that went through real
Playwright DOM/runtime verification) has no `verification-screenshots/`
directory in its workspace at all, and the export's `screenshots_path` is
empty. Unclear whether screenshots are only captured on an eventually-
promoted candidate (reasonable) or a genuine regression from D-068's
"screenshot capture on verification" fix -- worth checking before trusting
screenshot evidence on a rejected-after-repair run.

**Honest bottom line, unchanged in kind:** still zero `ready` outcomes
across all 4 live runs this session. What's different this round: one run
(`4dbcabae`) reached the deepest pipeline state on fully fresh content, and
none of the 3 newly-fixed defect classes recurred in the 2 post-fix runs --
but each run keeps surfacing a *different* new finding, which is itself
informative: the whole-site reviewer is thorough enough to be genuinely
hard to fully satisfy within its bounded polish/repair budget, not that
there is one remaining bug to chase down.

## 2026-09-07 — Auto-build on export, two filtered fixes from an external output-analysis doc, live-tested with 2 fresh runs (Claude Code) [3f5b2aa]

User asked for two things: portfolios should auto-build (`npm ci`/`npm run
build`) without manual intervention, and a filtered pass over
`docs/research/code-gen-output-analysis.md` (another AI's analysis of past
generator output) — explicitly not trusted wholesale, only what's still
open and necessary. Cross-referenced its findings against this file and
`DECISIONS.md` D-077: almost everything it raised (fake typecheck,
missing `@types/node`, nav data-target, 44px touch targets, mobile hero
overflow, tablet breakpoints) was already fixed and correctly excluded.
Two items were real and still open, plus a build-automation gap found by
tracing the actual pipeline code:

1. **Auto-build gap on the failure path.** `run_clean_build` (`npm ci` →
   typecheck → `npm run build`) already ran automatically for every
   *promoted* run and its `dist/` was already copied into the export — that
   part of the "auto-build" ask was already done. But `export_failed_run`
   (used for `needs_attention`/`failed` runs) never called it, so a failed
   export always shipped source-only with a blank `not_recorded` report,
   forcing exactly the manual `npm ci`/`npm run build` this session did by
   hand last time just to look at a rejected run. Fixed:
   `export_failed_run` now attempts a best-effort clean build first
   (never fatal to the export) and records a real `build_attempt` status.
2. **A second, bigger instance of the same gap, found live.** The
   generation stage's own `needs_attention` path
   (`generation_orchestrator.py::_fail`) never called `export_failed_run`
   at all — an independent code path from the one already wired in
   `code_generator_verification.py`. Since most runs this engagement has
   ever produced fail *during* generation (repair budget exhausted,
   integration review unresolved) rather than after it, this was the
   majority-case export gap, not an edge case. Fixed the same way.
3. **`blueprint-resource-role-mismatch` repairs were cosmetic, not
   structural** (this is last session's own live rejection, confirmed via
   this session's terminal-failure record: a resource specified as a
   narrow "tactile edge accent" rendered as a square block, and 2 repair
   rounds didn't fix the actual geometry). Added explicit repair guidance
   in `repair_source.md`: drop the square `aspect-ratio`, constrain to a
   narrow width, place as a flex/grid sidebar column — a mechanical target
   instead of a vague verbal description.
4. **Tab/selector content fully unmounted, not just hidden** — a genuinely
   new defect, confirmed by directly reading last session's exported
   source (`home-selected-work-2f0991ad.tsx`): 3 of 4 project detail
   blocks were gated behind `{selectedProject === N && (...)}`, so they
   were never in the DOM at all unless that exact tab was clicked. Not
   previously reported anywhere in this file or PLAN.MD. Added guidance to
   `route_batch.md`: keep every item's content mounted and toggle
   visibility, or derive from a static array — never fully exclude it.

**Live-tested with the 2 fresh full-pipeline runs the owner explicitly
authorized** (real OpenAI calls, canonical brief pack
`01-31-04-09-94ae4a9c`), both started clean (not resumed/retried):

- Run 1 (`e624bd75`): `plan` → `acquire` succeeded, `generate` ended
  `needs_attention` / `SOURCE_REPAIR_EXHAUSTED` on a motion beat
  (`motion:home:approach-progress`, missing `[data-motion-target=
  "approach-spine"]` opacity states) — a different, not-yet-investigated
  motion-authoring defect, unrelated to anything in this session's scope.
  **This run predates fix #2 above** (it's what surfaced the gap) — no
  export exists for it at all, confirming the bug directly: nothing under
  `output/code-gen-output/` for this run id.
- Run 2 (`c8cd8f1c`, after fix #2 landed): `plan` → `acquire` succeeded,
  `generate` ended `needs_attention` / `INTEGRATION_REVIEW_UNRESOLVED`
  after 5 polish rounds (exact finding text not in the safe export, per
  the still-deferred PLAN.MD problem #11/#12 — not pursued further this
  pass). The export this time is real:
  `output/code-gen-output/14-46-07-09-2026-c8cd8f1c/portfolio.json` shows
  `"build_attempt": {"status": "success"}` and a real `dist/` sits next to
  `source/` — the auto-build fix confirmed working end to end on an
  actual failed run. Its `home-selected-work` section also came out
  completely differently this time: a plain always-rendered `<ol>` list
  with all 4 projects' content present unconditionally (no interactive
  tab state at all), and its resource placement is a narrow
  8rem–14rem grid sidebar column, not a square block — neither defect
  class recurred, though with only one data point each this is supporting
  evidence, not proof the prompt changes are what caused it.

**Honest bottom line:** neither run reached `ready`. General pipeline
reliability (a run reaching `ready` without manual intervention) remains
unproven — every fresh run this engagement has recorded has ended in
`needs_attention`, on a different finding each time. What's actually
proven: the auto-build-on-export gap is fixed and directly confirmed live;
the two filtered defect-class fixes did not recur in this session's two
runs (weak but real evidence, not a guarantee). Run 1's `SOURCE_REPAIR_
EXHAUSTED` / motion-beat finding is a new, real, not-yet-investigated
issue for a future pass.

Live-tested the fixes below (this file's next entry down) against the
canonical brief pack (`01-31-04-09-94ae4a9c`). Result: `plan` -> `acquire`
-> `generate: succeeded` -> verification's DOM/runtime checks -> one
bounded repair round -> a full whole-site quality re-review — the deepest
state this engagement has ever recorded, with zero navigation,
content-binding, motion, or touch-target diagnostics anywhere in the run.
Confirmed directly in the real generated output, not just by the run
finishing: `data-navigation-target="home"` present with a resolved
`publicRouteUrl(...)` href; every generated `aspect-ratio` rule paired with
`min-width: 0; max-width: 100%`; breakpoints anchored at exactly
`min-width: 768px`/`1440px` (not an invented round number); `--size-control:
2.75rem` (44px); a `<Reveal>` trusted-pattern beat present with no
hand-authored duplicate animation. Built the candidate locally (`npm ci`,
`npm run build` — both clean) and viewed it in a real browser: clean
editorial typography, working nav, no visible layout breakage at desktop
width.

The run still ended `needs_attention`, not `ready` — its sole blocking
finding was a genuine, correct composition judgment from the whole-site
reviewer (`.selected-work__image { aspect-ratio: 1/1 }` renders as "a
prominent square block" instead of the blueprint's "narrow tactile edge
accent"), unrelated to anything fixed this pass. That is the review stage
working as intended, not a defect.

**Three new findings surfaced, not fixed this pass:**

1. **Hero fallback image was thematically unrelated** (out of this
   session's scope — `resource_scout.py`'s live-search fallback, not
   touched). The pinned hero image candidate 400'd from Pixabay; the live
   fallback search then returned gold Oscar-statue trophies for a "Senior
   UI/UX Designer" portfolio hero. The fallback mechanism worked (no
   empty/broken image), but its search-query relevance is poor. Worth a
   follow-up: either tighten the fallback query construction or fail
   toward a safer neutral placeholder rather than an unrelated top hit.
2. **Offline npm cache didn't have this pass's new dependency** (an
   operational gap this pass's own change created, not a pre-existing
   bug): adding `@types/node` to the scaffold pulled in a new transitive
   `undici-types` package. This project's dependency pipeline is
   deliberately `--offline` against a dedicated cache
   (`.workspace/npm-cache`, config `code_generator_dependencies.
   npm_cache_root` — separate from npm's own default global cache), so the
   very first live run after this pass's scaffold change failed with
   `TOOLCHAIN_INSTALL_FAILED` / `ENOTCACHED` until that cache was warmed
   once (`npm_config_cache=<abs path> npm install` from a repo using the
   updated `package.json`). This is a one-time environment step, not a
   code fix, but it's exactly the kind of gap PLAN.MD's own Step 1 called
   out ("an empty cache must produce a toolchain error before generation
   spends money") — confirmed live: it did produce a clear, correctly
   attributed error, it just needed a human/operator step to resolve, same
   as any other scaffold dependency change would.
3. **A Windows directory-lock footgun for whoever runs this live**, not a
   pipeline bug: manually `cd`-ing a shell into a run's
   `.workspace/code-generator-generation/<run_id>/repo/` directory to
   inspect or test it, then leaving that shell there, blocks a subsequent
   generation attempt's own directory swap (`GENERATION_SWAP_FAILED`,
   "could not be swapped in under filesystem locks") — Windows locks a
   directory against rename/delete while any process has it as its current
   working directory. Fix was simply `cd`-ing back out. Noting this so a
   future session doesn't mistake it for a real concurrency bug.

Two transient, unrelated environment hiccups during this same session,
also not code bugs: an `EPERM` on npm's own temp-directory cleanup
(resolved on retry — a different, one-off Windows file-locking blip, not
the `ENOTCACHED` cache-miss above), and one background process killed by
the OS for low system memory (16GB machine, 3.3GB free at the time, with
several other heavy apps open concurrently — not caused by anything this
session started).

## 2026-09-07 — PLAN.MD implementation pass: scaffold truthfulness + 5 generation-time authoring gaps (Claude Code)

Given the Astra/Codex-authored `PLAN.MD` reliability handoff (commit
`78117e7`), implemented Step 1 in full plus the generation-side authoring
fixes for findings #2, #4, #7, #8, #9, deliberately deferring Step 3
(RegionLayout/ReadableCopy/MediaFrame — the mobile-overflow root cause) and
the distinctive-move schema rework as separate, larger lifts not rushed
into this pass. Full rationale/diff is in commit `78117e7`; short version:

- **Scaffold typecheck was checking nothing** (finding #1): root
  `tsconfig.json` has `files: []` + project references, but the script ran
  bare `tsc --noEmit` against it. Fixed to check both project configs; this
  immediately caught a real latent bug (`ROUTES` array typed as `readonly
  []`/`never` when empty). Added `dev`/`preview`/`check` scripts, `@types/
  node`, and a README — live-verified `npm ci/check/build/dev/preview` all
  work and a deliberate type error fails both typecheck and build.
- **Navigation verification could never pass** (finding #4): Content
  Architect's approved `public_content_manifest.nav` was never threaded
  into generation at all — route_compose.md only ever taught same-page
  section-fragment links. `data-navigation-target` literally never had a
  reason to exist in generated output. Wired the approved nav edges into
  `generation_contract.py` with an explicit `data-navigation-target` +
  `publicRouteUrl(...)` instruction.
- **A correct `.map()`-based content binding was rejected** (finding #9):
  `source_validation.py`'s literal-only regex blocked a statically-known
  `const IDS=[...]; IDS.map(id => contentValue(id))` pattern that
  `scripts/audit-source.mjs`'s real TS-AST checker already resolves
  correctly — the stricter Python pre-gate never let generation reach the
  smarter check. Added a bounded (non-interpreting) fallback for exactly
  this shape.
- **Trusted motion patterns were unsatisfiable** (finding #8, the big one):
  `source_validation.py` demanded `changed_properties`/reduced-motion/
  `setAttribute` literal substrings for every beat, but a `pattern_id`-bound
  beat's entire implementation lives in trusted `motion.css`/
  `SharedSystems.tsx` — files never in a section's own owned source. This
  guaranteed every correctly-implemented trusted-pattern beat failed.
  Gated the whole check behind "no pattern_id"; a trusted beat now only
  needs to prove the component is rendered. Also fixed `reveal-clip-lines`'s
  own catalogue description, which falsely advertised a `load` trigger
  alongside `viewport` when the bound component is IntersectionObserver-only.
- **Distinctive-move ratio direction** (finding #7): `planner.md` told the
  model to pair a region's own ancestor selector as `source_selector`
  against a descendant row as `target_selector` for `width_ratio` — a
  container can never be narrower than its own content, so that pairing
  can only ever measure >= 1.0. Clarified peer-only selectors, ratio
  direction, and that a repeated-row target needs `shared_alignment_axis`,
  not `width_ratio`. Added the same direction reminder to `repair_source.md`.
- Touch target bumped 36px -> 44px per the plan (config, runtime_verifier
  fallback, prompt prose).

`uv run pytest tests/unit/agents/code_generator/`: 260 passed, 1
pre-existing failure (`test_v2_architecture.py`'s
`materialize_acquisition_resources` "path"-key test) confirmed present on
a clean `git stash` tree — unrelated to this pass, not touched.

## 2026-09-06 evening — live re-test surfaces a self-inflicted regression (Claude Code)

First live run after today's 5 fixes (see the section below) reached
`plan` → `acquire` → `generate` all `succeeded` — the deepest and cleanest
this session's fresh run has gotten — then failed final verification with a
**new** error, `QUALITY_REALIZATION_STALE` ("the quality review is for a
different design-realization contract"). Traced immediately: the earlier
resource-fallback fix (`compile_design_realization` now takes optional
`execution`/`resource_ledger` and filters `resource_checks` accordingly) was
wired into `verification_plan.py` and `code_generator_verification.py`'s
final check, but `generation_orchestrator.py::_integration_review` — the
call that actually stamps `quality_review.realization_hash` *during*
generation — was deliberately left on the old unfiltered call (see that
entry's own "left `_integration_review` unwired" note). Any run with at
least one non-required placement lacking a real binding now got two
different hashes for the same route: one stamped at generation time
(unfiltered), one recomputed at verification time (filtered) — a real,
live-confirmed regression from this session's own earlier work, not a
pre-existing bug.

**Fix**: added `projections` as a required parameter to `_integration_review`
and `_rereview_after_repair`, threaded from all 3 real call sites (initial
review, per-round polish-loop review, both post-repair re-review calls) —
confirmed via `mypy` that no other caller was missed. Re-running the same
live pack to confirm `QUALITY_REALIZATION_STALE` is actually gone now, not
just plausible from code reading.

**Lesson for future sessions**: when a fix introduces a new optional
parameter to a function whose result gets hash-compared against a *different
call site* of the same function, grep for every caller before deciding any
one of them is "lower priority to wire up" — a mismatched default among
call sites that must agree is a correctness bug, not a scope-reduction.

## 2026-09-06 evening — second live re-test: a real, severe, fresh crash (Claude Code)

With the staleness fix above landed, a second fresh live run got further
still: `plan` → `acquire` → `generate` succeeded again, and verification got
past the realization-hash check into the actual DOM/runtime browser gate —
then failed with `DOM_RUNTIME_FAILED` (`RUNTIME_ASSERTION_FAILED` — the hero
`[data-content-id="home:hero"]` never appeared within 15s — plus
`RUNTIME_CONSOLE_ERROR`, across all 3 viewports). Final repair tried 3 times
and produced no usable correction each time.

**Root cause, found by reading the persisted `verification_projection`
column directly** (the terminal diagnostic's message was a generic
"blocking console error" with no actual text — see the fix below): the
real browser console error was `Error: Unsafe local route path`, thrown
from the scaffold's `ResourceUrl.ts::publicRouteUrl()`. The hero section
(`home-hero-ecdc18c2.tsx`) called `publicRouteUrl(primaryHref)` where
`primaryHref` resolved to the approved content value `"#selected-work"`
(kind `"internal"` — a same-page anchor to the "selected work" section, not
an actual route path). `publicRouteUrl` requires its input to start with
`/`; a bare `"#..."` fails that check and throws **during the hero's own
render**, crashing the whole page before anything mounts — exactly why the
hero locator timed out and "Page not found" showed up in the screenshot (a
render failure, not a routing miss). This is a genuinely severe, live-
confirmed, fresh bug: it can crash the entire homepage on the single most
common CTA pattern (a "see more" link scrolling to a section on the same
page), and it starves final repair of any real information to act on — see
the diagnostic-message fix below.

**Fixes**: (1) `route_batch.md`/`route_compose.md`: added explicit guidance
that a fragment-only approved href (`#section`, same-page anchor) must
render as a literal string, never wrapped in `publicRouteUrl` — only an
actual route path (starts with `/`) should go through it. (2) Defense in
depth: `ResourceUrl.ts::publicRouteUrl` now passes a `#`-prefixed input
through verbatim (a bare fragment has no path-traversal/origin risk and the
browser resolves it correctly against the current mounted document on its
own) instead of throwing — converts a full-page crash into simply "the link
still works" even if a future generation round makes the same category
mistake. (3) `runtime_verifier.py`: `RUNTIME_CONSOLE_ERROR`/
`RUNTIME_PAGE_ERROR` diagnostic messages now include the actual captured
error text (already collected in `RuntimeEvidence.console_errors`/
`page_errors` but never surfaced past a generic placeholder) instead of a
placeholder — this exact investigation needed a direct DB query to find the
real error; the repair model never had DB access, so it was flying
completely blind on both of tonight's `DOM_RUNTIME_FAILED` attempts before
this fix.

**Not yet confirmed live** — a third live run is the real test of whether
this exact page now renders. `ruff`/`mypy`/full suite (266 passed, same 1
pre-existing failure) are clean for the Python-side change; no Node/Vitest
harness exists in this repo to unit-test the scaffold `.ts` file directly,
so its correctness rests on direct code reading (a simple, low-risk early
return) plus the next live run's actual build+browser result.

## 2026-09-06 evening — third live run: the crash is fixed, exposing a genuinely new frontier (Claude Code)

Confirmed live: the fragment-href fix above worked. A third fresh run
reached `generate: succeeded` again and got past both the hero-render
crash and the realization-hash check into real DOM/runtime layout
diagnostics — the deepest and most informative point this run has ever
reached. Two more real, root-caused bugs found and fixed from this run's
diagnostics (both live-tested with real Playwright browser assertions, not
just code reading):

| Area | Finding | Durable resolution |
|---|---|---|
| Region column-count check treated an abstract design-grid span as a literal CSS track-count requirement | `RUNTIME_REGION_COLUMN_COUNT` demanded `computedColumns === columns_desktop` (e.g. exactly 8 or 12 grid-template-columns tracks). The model's actual CSS for `#design-systems` used a considered, good-looking 2-track asymmetric split (`minmax(0, 1.1fr) minmax(15rem, 0.9fr)`) for a heading+details layout — legitimate design, not a defect. `columns_desktop`/`columns_tablet` have **zero documented semantic anywhere** in this repo (no prompt guidance in any `.md`, no Pydantic `Field(description=...)`, no `DECISIONS.md` entry) — the only textual hint is the schema's own bound (`le=12`), matching the common "12-column design-grid" *planning* convention, not a literal implementation instruction. `RUNTIME_REGION_WIDTH_RATIO` already verifies the real visual-correctness signal (is the region appropriately narrower than main) independently. | Loosened the check to its actual catchable intent: fail only when "is multi-column" (`computedColumns > 1`) disagrees between observed and expected, in either direction — never demanding an exact track count. Proven both ways with real Playwright tests: a legitimate 2-track asymmetric grid against `columns_desktop=8` now passes; a region that collapsed to a single column when multi-column was contracted still correctly fails. |
| Distinctive-move CSS-property check had no way to look at the move's own marked element | `RUNTIME_DISTINCTIVE_PROPERTY` reported `grid-template-columns`/`column-gap` "missing" for `move:home:selected-work:index` on 3 separate journeys, repair failed 3/3 rounds. Traced via the persisted `plan` column: `source_selector` (`[data-region-id="region:home:home:selected-work"]`) measures the *outer section's* width for the move's `width_ratio` relationship — correct, since that section also contains header/label content that shouldn't be forced into the grid. The model reasonably scoped the actual grid CSS to a *nested* element carrying the move's own `runtime_marker` (`data-distinctive="selected-work-index"`, itself planner-assigned, not invented) instead of the outer section — but `DistinctiveMoveRuntimeCheckV1` (the runtime-check schema `compile_design_realization` builds) never carried `runtime_marker` through from the blueprint at all, so the check had no way to find that nested element and could only ever look at `source_selector` itself, which legitimately never had those properties. | Added `runtime_marker: str = ""` to `DistinctiveMoveRuntimeCheckV1`, wired through in `design_realization.py`. The runtime check now looks for `required_css_properties` on the marker-scoped element (`source.matches(marker) ? source : source.querySelector(marker)`) when a marker is set, falling back to `source` itself otherwise (unchanged default, and unchanged when no marker is configured at all). Proven with real Playwright tests: properties on the marked nested element now pass; the same CSS without a marker configured still correctly fails (backward compatible), and a genuinely absent property still fails when the marker path is checked correctly.

271 passed (up from 266), 17 skipped, same 1 pre-existing unrelated
failure. Both fixes have real browser-driven regression tests (not fixture
mocks) proving the exact before/after behavior, in
`test_runtime_verifier_region_and_distinctive_move.py` and
`test_design_realization.py`.

**Not yet fixed, found in the same run** (deprioritized — genuinely deeper,
not a quick fix): `RUNTIME_DISTINCTIVE_RELATIONSHIP` still measured 2.4375
(expected 0.4-0.85) for the same selected-work move — its `source_selector`
is the *outer section* (an ancestor of `target_selector`, the first
project row), and an ancestor's rendered width is essentially always ≥ any
descendant's, so a "source narrower than target" ratio contract for that
specific selector pair looks topologically close to unsatisfiable as
specified. This smells like a **planner-side selector/ratio semantic
mistake** (possibly meant to compare two siblings, e.g. an accent/image
column vs. a text column, not a region vs. one nested project), not a
verification-side bug — fixing it safely needs understanding what the
planner actually intended for `implementation_kind: "asymmetric_width"`
moves, which is a bigger, separate investigation than tonight's scope.
Also unresolved: `move:home:about-connect:close` measuring ratio `0`
(expected 0.3-0.75) — plausibly a disclosure element measured in its
default-collapsed state before any interaction, which may need the move's
ratio checked post-interaction rather than on initial load. Both logged
here rather than guessed at.

## 2026-09-06 evening — fourth live run finds the session's highest-impact bug (Claude Code)

Fourth live run (region/distinctive-move fixes above) got past the crash
again and surfaced `RUNTIME_REGION_WIDTH_RATIO` failing at **exactly
1.000** for nearly every region, on nearly every run tonight and — per a
recheck of every prior run's diagnostics this session — apparently every
run this whole engagement has ever reached this check. Root cause is
unambiguous, standard, well-documented browser behavior, not something
that needed empirical verification: `Element.getBoundingClientRect()`
**always reports the border box**. An auto-width, block-level region (no
explicit `width`) always renders at ~100% of its parent's width regardless
of how much inline padding it carries — CSS padding shrinks the *content*
area, not the element's own rendered footprint. `region.getBoundingClientRect().width / mainRect.width`
can therefore only ever read below 1.0 for a region using an explicit
`max-width`/`width` constraint; the extremely common "full-bleed section,
visual inset via padding" pattern (confirmed in the actual generated CSS:
`.approach { padding: var(--space-24) var(--container-page-padding); }`,
no `max-width` at all) was **structurally guaranteed to fail** this check
regardless of how good the design actually was. The same `rect.width` bug
also fed `RUNTIME_REGION_MEASURE`'s readable-measure estimate, overstating
it by the same padding amount.

**This is very likely the single highest-impact false-positive found this
entire engagement** — it plausibly explains a large fraction of every past
session's "layout looks wrong" `DOM_RUNTIME_FAILED` findings that were
never individually root-caused before now.

**Fix**: both `widthRatio` and `estimatedMeasure` now measure the region's
*content* box (`rect.width` minus its own computed inline padding) instead
of the raw border box. Live-confirmed both ways with a real Playwright
test: a region with no explicit width but 100px inline padding on each
side inside a 1000px `<main>` (visible content 800px, ratio 0.8) failed a
tight 0.75-0.85 contract before the fix (measuring exactly 1.000) and
passes after it. 272 passed (up from 271), 17 skipped, same 1 pre-existing
unrelated failure; `ruff`/`mypy` clean.

**Not investigated this session, logged for later**: `RUNTIME_REGION_GAP`
("gap 32px does not match the approved 24px") — a real, smaller deviation
in the same run, likely a genuine model/token mismatch rather than a check
bug, not yet traced.

## 2026-09-06 evening — fifth live run: width_ratio fix confirmed eliminated; found a bigger architectural tension (Claude Code)

Fifth live run (content-box fix above). **`RUNTIME_REGION_WIDTH_RATIO` is
completely gone from this run's diagnostics** — direct live confirmation
the fix works, not just the isolated Playwright test. Remaining dominant
issue: `RUNTIME_REGION_COLUMN_COUNT` — every region collapsed to 1 column,
but only at the `tablet` interaction id specifically.

Traced to the actual generated CSS: `.approach`'s multi-column grid
collapses via `@media (max-width: 60rem)` (960px) — a **reasonable,
deliberate responsive breakpoint the model chose itself**, not a bug. This
project's `tablet` viewport profile is fixed at exactly 768px
(`config/app.toml`) — well below 960px — so the tablet check always lands
inside the model's own "collapsed" media query. This is not a code defect
to patch; it's a **genuine architectural tension**: `columns_mobile/tablet/
desktop` implicitly assumes the model's CSS breakpoints align with this
project's 3 fixed checked viewport widths, but real responsive design
(correctly, by normal practice) picks its own breakpoint thresholds tuned
to when a specific layout starts looking cramped, which will often not
land exactly at 768px. Whether the fix belongs in the contract (tell the
model explicitly which viewport widths must show which column count),
the check (verify only that *some* breakpoint transition exists, not that
a specific one applies at exactly 768px), or neither, is a real design
decision — logged here rather than guessed at under session-end time
pressure.

**Also observed, not yet investigated**: `RUNTIME_ASSERTION_FAILED` (page
horizontal overflow, desktop), `RUNTIME_TOUCH_TARGET_TOO_SMALL` (tablet nav
link — note the D-072-era deterministic touch-target CSS repair only fires
for legacy V3 source, `final_repair.py::_legacy_deterministic_repair` is
gated `if not is_v4`; V4 source is intentionally "model owned" so this may
be working as designed, not a gap), a distinctive-move ratio mismatch for
a *different* move than previous runs (plans aren't deterministic across
runs), and a navigation-journey timeout waiting for
`[data-navigation-target="home"]`.

## Session summary, 2026-09-06 (Claude Code)

Ten real, confirmed, mostly live-verified bugs fixed in one session,
starting from an externally-authored static-analysis plan whose claims
were verified against actual code (and, in two cases, live behavior)
before acting — never trusted blindly. Full list above, in order found:
comment-stripper regex-literal blindness, final-repair source blindness +
wrong-directory fallback guess, motion transform-matrix substring
comparison, font-load check missing an explicit load, runtime resource
checks blind to acquisition fallback, a self-inflicted realization-hash
regression from that same fix, a fragment-only CTA href crashing the whole
page, region column-count over-strictness, distinctive-move CSS property
blindness to its own runtime marker, and region width/measure using the
wrong CSS box model (border box instead of content box) — likely the
single highest-impact false-positive this whole engagement has produced.

**Net effect, live-confirmed across 5 fresh runs tonight**: the pipeline
went from crashing on render (never reaching real verification) to
reaching final DOM/runtime checks cleanly past both the crash and the
resource/motion/font gates that blocked every previous session. The
current frontier is real, substantive layout/responsive-design questions
(the breakpoint-contract tension above, page overflow, touch targets) —
a categorically different, more advanced class of problem than the
crashes and false-positives fixed tonight. No run reached a clean `ready`/
promoted state this session; that remains the next target.


Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## 2026-09-06 (session continuing from an external plan review, Claude Code)

Started from a reliability-repair plan authored by another model (Astra/Codex,
handed to the user as `PLAN.MD`) that did NOT make live calls or repo changes
— a pure static review. Cross-checked its "confirmed problems" against this
file's own ground truth first: several of its claims line up almost exactly
with the still-open "Not yet fixed" items below (the ~10 undiagnosed
`DOM_RUNTIME_FAILED` codes: font load, resource decode, region geometry,
motion state). Verifying each claim against actual code before acting on it,
fixing confirmed ones surgically (same style as every prior entry in this
file), and deliberately NOT adopting the plan's proposed `ResolvedExecutionContract`
v6 rearchitecture — too large/risky for the current budget and unsupported by
any DECISIONS.md entry; this project's actual history is ~40 targeted
live-bugfix commits, not big-bang rewrites.

| Area | Finding | Durable resolution |
|---|---|---|
| Comment stripper mistook JS regex literals for comments | `source_lexing.py::strip_source_comments` had zero regex-literal awareness. A regex containing an escaped slash (`.replace(/\/+$/, "")`, `/^\/api\//`) produces a bare `//` outside any quote once its own backslashes are consumed, which the scanner treated as a line-comment start — silently truncating the rest of that source line before `source_validation.py`/`typescript_ast_audit.py`/`final_source_validation.py`/`source_generation_adapter.py` (all 4 real call sites) ever see it. Confirmed real via direct code trace, not a live run. | Added a start-of-expression heuristic (same approach real JS lexers use) that recognizes and passes through a regex literal verbatim before the `//`/`/*` comment checks run. Had to special-case `<` as division-context too — an initial version broke `</a> // real comment` (JSX closing-tag slash misread as a regex opener, which then swallowed the real comment). 7 new tests (`test_source_lexing.py`), all existing `typescript_ast_audit` tests still pass. |
| Final repair received no source code for any route/journey-scoped diagnostic | `diagnostics.py::build_bundle`'s `bounded_related_source` (the actual file content shown to the repair model) was only populated from diagnostics carrying an explicit `.file` — but `runtime_verifier.py::_diagnostic()` (every DOM/runtime finding: font load, region geometry, motion state, disclosure/interaction checks, ~30 call sites) never sets `.file`, only `route_id`. This is exactly the diagnostic class behind this file's own "Not yet fixed" `DOM_RUNTIME_FAILED` codes — the repair model was being asked to fix a route it had never been shown. `repair_source.md` itself already says "When rejected file bodies are supplied, return the complete corrected file," confirming source content was always meant to reach the model here. | `build_bundle` now expands the caller's already-scoped `allowed_paths` (concrete files or `<dir>/**` globs) into real on-disk `.tsx`/`.ts`/`.css` content when diagnostics under-supply `.file`, bounded to 12 files / 12000 chars each (same truncation explicit matches already used), and path-escape safe (verified via a `../` test). Separately, `final_repair.py::repair_allowed_paths`'s route-id branch previously fell back to a bare `src/routes/<route_id>/**` (unhashed) directory when the site-contract projection didn't resolve a route's storage key — a real prior export (`output/code-gen-output/18-03-06-09-2026-aff69ea1/source/src/routes/home/`) shows exactly this bare-directory shape existing alongside the real hashed one, consistent with (not conclusively proven as) a repair having once written to the wrong place. Now falls through to the existing generic `src/design/**`/`src/components/shared/**` default instead of fabricating an unhashed path. 5 new tests across `test_diagnostics_bundle.py` (new file) and `test_final_repair.py`. |

Both fixes are free/deterministic (no live model call needed to verify), full
`-k code_generator` suite: 260 passed, 17 skipped, 1 pre-existing unrelated
failure (same one already tracked below), no new regressions. Not yet
confirmed live — next live run should show whether route-scoped
`DOM_RUNTIME_FAILED` findings can now actually get repaired instead of
exhausting the repair budget with zero source visibility.

Two more plan claims checked against actual code, both confirmed real:

| Area | Finding | Durable resolution |
|---|---|---|
| Motion verification compared authored transforms against browser-computed matrix strings | `runtime_verifier.py::_assert_design_realization`'s `matches_after` check was `expected_after in str(after_value)` — a plain substring test. `getComputedStyle` always reports `transform` as a resolved `matrix(...)`/`matrix3d(...)` string, never in the author's own function notation (`translateY(24px)`, `scale(1.05)`) that a motion beat's `after_value` is written in, so a correct, working animation could never satisfy this check — directly the "motion state" code in the still-open list above. **Live-confirmed both ways**: reverting the fix and re-running the new test reproduces `RUNTIME_MOTION_STATE_MISMATCH` on a genuinely correct animation; with the fix, the same case passes and a deliberately wrong expected transform (`translateY(9999px)`) still correctly fails. | For `property_name == "transform"`, normalize the expected value through the browser's own CSS engine (a detached probe element gets `style.transform` set to the expected value, then reads its own `getComputedStyle().transform`) and compare against the observed computed matrix — exact match first, then a per-component numeric fallback (1px tolerance on the 3 translation terms, 0.02 on every other term) for cases where an extra composed transform (e.g. a GPU-acceleration `translateZ(0)`) makes the matrix vs matrix3d string forms differ. 2 new Playwright-driven tests, `test_runtime_verifier_motion.py`. |
| Font verification treated an unrendered-but-declared font weight as broken | Same file, `contract.font_checks` loop: `document.fonts.check(weight, family)` only returns true for a face the browser has actually triggered a load for (rendered text using that exact weight somewhere, or an explicit `.load()`) — a weight declared valid for a role but not the one actually rendered anywhere on the page would always read as "failed to load" even though the face itself is fine. Matches the "font load" code in the still-open list. **Not live-tested**: faithfully reproducing the original failure needs a real custom `@font-face` binary (a system font like Georgia doesn't hit this path — `document.fonts.check()` resolves those immediately with no load to wait on), which felt like too much fixture weight for the signal; verified by code/spec reading instead. | Added `await document.fonts.load(weight, family)` (wrapped in try/catch — a rejection is itself real failure evidence, left for the following `.check()` to report) immediately before the existing `.check()` call. Purely additive: for an already-loaded or already-failing face this is a no-op, so it cannot make the existing check stricter than before, only less prone to this specific false positive. |

**Update, same session, after finding the real join**: the `purpose`-string
join really is unreliable, but `final_source_validation.py:383-410` already
solves exactly this problem for a different check (`SOURCE_EXECUTION_SLOT_UNUSED`)
using a *different*, deterministic mechanism I'd initially missed: for a
`delegated_acquisition` slot, `execution/contract.json`'s
`slots[].resource_slot_id` joins to the resource ledger via a fixed
`f"delegated-{resource_slot_id}"` request-id convention, then
`request_hash` → `active_bindings[].request_id_or_pack_need_id` gives the
real, post-acquisition `local_paths`. The execution slot also carries
`required` directly. Reused this exact pattern (new
`_admitted_resource_slot_ids()` helper in `design_realization.py`, kept
separate from `final_source_validation.py`'s working copy rather than
risking a shared-helper refactor of already-verified logic) to filter
`resource_checks` to placements that are either `required`, or that
actually got a real local file — an optional placement with an honest,
approved fallback (no real binding) is now excluded from the real-image
runtime checks instead of being held to `RUNTIME_RESOURCE_DECODE` etc. A
`required=true` placement with no local file is still always checked
(never exempted, per the plan's own "never excuse an unmet required
behavior" principle). Backward compatible: omitting `execution`/
`resource_ledger` keeps the prior "check everything" behavior. Wired into
the 2 call sites that gate a hard pass/fail (`verification_plan.py`,
`code_generator_verification.py` — both already had `projections` in
scope). Left `generation_orchestrator.py`'s `_integration_review` (mid-
generation whole-site review context, advisory only, not a hard gate)
unwired — it doesn't have `projections` in scope and threading it through
would mean a signature change touching other callers; lower priority since
a wrong value there only skews model-review context, not a pass/fail
verdict. 4 new tests, `test_design_realization.py`.

Both this fix and the motion/font ones above are now included in the 266
passed / 17 skipped / 1 pre-existing-unrelated-failure suite total; `ruff`
and `mypy` clean on every changed file.

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
