# Code Generator reliability: implementation handoff for Luna

Prepared on 2026-09-09 against implementation revision `e5db08c`.
Status: investigated and planned; the changes below are not implemented by this document.
The newly authorized campaign has **0 of 5 full pipeline runs used**.

## 1. Assignment and stopping rule

Make the existing Code Generator reliably turn different valid Build Preparation
brief pairs into complete, attractive, usable portfolio sites. Work in the
generator, its trusted scaffold, acquisition, repair, verification, and export
paths. Repairing one saved portfolio is evidence gathering, not the product fix.

Implement the work packages below before the first new live run. Then run the
configured real workflow through the normal API, durable queue, worker, and
preview gateway. Reserve at most five new full pipelines, one at a time. Stop
after two accepted portfolios using different packs, or at five attempts.
If the first two pass every acceptance check, stop there. Five is a ceiling,
not a target. Report any unsampled live pack explicitly.

An accepted result means more than `ready`: a clean build, correct approved
content, functioning navigation and interactions, visible relevant imagery when
permitted, satisfactory desktop/mobile screenshots, a working gateway preview,
and truthful reports. A passing TypeScript check alone is insufficient.

Do not promise certainty before an LLM call. The practical replacement for
"100% sure before the next run" is: reproduce the previous defect, implement
the root-cause fix, pass its regression test, pass relevant offline checks, and
record what remains unverified. A limited campaign cannot prove every future
input or every external service will succeed.

Keep models/providers and limits in configuration. Use existing authorized
credentials without printing them. Do not switch provider/model to hide a
generator defect. Do not remove validators, suppress functional failures, create
fake testimonials/results, or substitute mock output for live evaluation.

## 2. Verified baseline and evidence

### 2.1 What actually ran

The current run states were read again through the development API. The five
continuation runs all remain `needs_attention`:

| Run ID | Pack | First failing stage | Evidence and present disposition |
|---|---|---|---|
| `55234cbb-32f3-475f-8716-affce08c8c3f` | A | acquire | Configured native `npm` could not launch. Executable-resolution fix is committed as `d1c5645`. |
| `beb5e244-8787-4dcb-8c08-67fac19bcbe5` | B | acquire | API error is npm `EUSAGE`: lock/package inconsistency, including a missing `@emnapi/wasi-threads` lock entry. This particular failure is not proof of an unavailable tarball. Offline lock projection handling changed in `2b2714a`; clean install must still be proved on each supported platform. |
| `e5e32ac3-89d4-48ad-bbaf-4eb5e8927ee6` | B | plan | `PLAN_CONTENT_KEY_COVERAGE`; planner bookkeeping drift. Host content binding canonicalization and image placement policy are in `97d83dd`. |
| `e39ee9e6-b71a-430b-bc7a-934046579f27` | B | generate/foundation | Optional highlighter source imported unsupported `rough-notation`. Import screening/fallback is in `59bf982`; component interface/type compatibility remains a broader admission concern. |
| `291ed5d7-6a7d-44c8-b024-fbb7dbf8c5c8` | C | generate/route batch | Initial CSS error, partial repair discarded companion file proposals, then stale `create` caused exhaustion. `29fc598` fixes operation tags; proposal retention and batch accounting still need the work below. |

The prior campaign allowed four slots but its ledger records only one reserved
slot: `4d009f48-050e-48a7-9611-82f3a5eecd91`. It reached `ready` after a
verification retry on the same source checkpoint. Two export folders with that
ID are two snapshots of one run. Do not report four actual runs from a four-slot
allowance, or count those exports as separate successful portfolios.

That historical run passed the old build/runtime gates, but its saved blueprint
had no image placements and its desktop screenshot is image-free. The screenshot
also shows an unnecessarily narrow, six-line headline and a mostly unused right
side of the opening. Preserve this as "historical technical success; current
visual acceptance failed."

The older `09adccd5` and `1f310dda` exports are incomplete foundation attempts
associated with the former missing `motion/react` dependency. The older
`fca37030` planner failure referenced an undefined region. Preserve their
regressions; do not reimplement fixes already covered by current source.

### 2.2 Exact newest-run trace

Root:
`.workspace/code-generator-generation/291ed5d7-6a7d-44c8-b024-fbb7dbf8c5c8/`

Within `route-batches/home-4ea14058-batch-1/ledger/`:

1. `calls/24686c46b3f1008d8cef128d86d8358873f72ceecfe759b1beb16785479259c6.json`
   proposes six files: three section TSX modules and three stylesheets.
   Introduction CSS includes `max-width: fiftych`, which is invalid.
2. `contexts/663618e4ab541f318e5467f4b1dbcd09978173a16225c138b8b329eb2a8f3b5e.json`
   correctly contains all six proposed file bodies for repair.
3. `calls/0ac5bd44d7c90f85cb8cd1f05195f10e31020b73acdc9258c2cadeddfde064b3.json`
   returns only the corrected introduction stylesheet. That follows the prompt's
   instruction to make the smallest change, but the host applies it to a tree
   that never received the other five files.
4. `contexts/c421377ede1743b314359dea361359aca2d3af751315e6a564ce68478af1fecb.json`
   now contains only that stylesheet as previous source. Missing section, h1,
   resource, and motion diagnostics follow. Much of this apparent new defect
   set is a consequence of losing the original proposal.
5. `calls/557d90fb956bb6f33894b9fd03d7de170b582cd4bb11abf4d7f160baf73034d3.json`
   reconstructs six files but labels the existing stylesheet `create`.
   The pre-fix validator raises `SOURCE_CREATE_EXISTS`.

Additional offline investigation in this planning pass:

- Replaying the final response against the actual batch tree now normalizes to
  five creates and one replace. Source-policy and route-batch checks pass.
- A fresh offline `npm ci` and both app/node TypeScript checks pass on that
  replay copy. Route composition, whole-site review, clean full build, browser
  verification, and promotion were not replayed; this is not a new success run.
- Overlaying the first one-file repair onto the original six-file proposal
  preserves the sections. It exposes one remaining selector-contract failure:
  CSS styles `#introduction .introduction__inner`, whereas the enforced layout
  selector is `[data-region-id="region:home:home:introduction"]`. This is much
  narrower than the missing-section cascade. Do not claim proposal retention
  alone makes this recorded response fully pass.
- The development generation API still returns no call receipts and zero repair
  rounds for the failed run, despite saved calls in the isolated batch ledgers.
- `output/code-gen-output/13-07-09-09-2026-291ed5d7/generation-report.md`
  has an empty pack reference, no route list, zero call/repair counts, and
  unknown image evidence. It advertises `dist/` although no dist was exported.

Local diagnostic helper, intentionally outside production source:
`.workspace/research/codegen_0909_plan_audit.py`.
Latest replay copies:
`.workspace/research/cg-offline-replay-1cd845295e/`.
These paths are optional local evidence, not prerequisites for CI. Convert the
minimal relevant cases into sanitized fixtures in the implementation.

### 2.3 Confirmed gaps versus risks to test

| ID | Priority | Finding | Source of evidence |
|---|---|---|---|
| R01 | P0 | A small repair loses untouched files from a rejected multi-file proposal. | Saved call/context sequence above; `_run_unit`, `_apply_changes`, `_operation_context`. |
| R02 | P0 | Failed isolated batches lose durable call, diagnostic, and progress projections. | API versus on-disk calls; `_run_route_batch_wave` merges only after `execute_waves` returns successfully. |
| R03 | P0 | Repair totals are cloned per batch and not merged back with the receipts. | Local deep-copy projection; success merge omits `repair_budget_used`, `repair_rounds`, strategies and fingerprint counts. This is a code-confirmed accounting gap; the exact amount of historical overrun is not established. |
| R04 | P0 | A failed task does not explicitly stop all scheduled sibling work. | `execute_waves` schedules an entire ready set with `asyncio.gather`; concurrency=1 is a semaphore, not a sequential stop-on-failure loop. Test cancellation/continuation deterministically. |
| R05 | P0 | Failed-export reports omit primary failures and available generation evidence. | `export_failed_run` supplies only status/reason/issues/build metadata; report ignores `issues` and counts verification findings only. |
| R06 | P1 | Report says an image was rendered based only on a source regex. | `build_image_evidence` scans TS/TSX/CSS; it does not consume browser observations. A source reference is not visible rendering. |
| R07 | P1 | Minimum image policy is checked during planning but not carried as an independently enforced final route minimum. | `image_policy` call sites; final validation requires any materialized placement; runtime checks are compiled from selected/admitted placements. Missing or optional fallback placements can reduce the set checked. |
| R08 | P1 | Image visibility checks miss ancestor opacity and measure only image/nearest-section geometry. | `_assert_design_realization` checks the image's computed style and a section intersection. Add browser counterexamples before changing semantics. |
| R09 | P1 | CSS/property contracts remain easy to contradict despite plausible layouts. | The overlay replay's exact selector error; historical single-child outer-grid hero. |
| R10 | P1 | Optional source admission checks package names, but cannot prove an arbitrary component's exports, peer/API compatibility, aliases, or CSS support. | Current lexical import gate and foundation-wide typecheck boundary. Preserve the existing import fix and extend admission proof. |
| R11 | P1 | Acquired imagery can be valid bytes yet visually unsuitable. | Inspected C's selected-work rendition: craft supplies/flowers. Upstream explicitly pins it as decorative process texture; do not call this a generator download corruption. |
| R12 | P1 | Infrastructure errors have consumed paid planning before toolchain failure. | Runs 1/2 and historical Windows `spawn EPERM`; readiness needs an end-to-end local toolchain smoke check. |

## 3. Inputs and variation matrix

Read both `content_brief.md` and `visual_brief.md` under each directory below.
All three pairs were freshly accepted by `compile_briefs()` in this audit.

| Pack | Directory under `output/build_preparation/` | Variation worth testing |
|---|---|---|
| A / Maya | `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | Seven sections: hero, positioning, selected-work, capabilities, experience, credentials, connect. Historical image-free baseline. |
| B / Akash | `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | Seven sections: introduction, featured-work, engineering-practice, experience, capabilities, education, connect. Different content structure and component choices. |
| C / Varun | `c0860464-a786-43d8-9c30-d12d7516c4b8` | Six sections: introduction, focus-areas, selected-work, experience, education, connect. Route-scoped `home-lifecycle-abstract` with original category `abstract systems illustration`; no source section binding on that slot. |

Expected contract hashes:

- A: `d3858b6133cc66bda14222ac7009530cf13c1990687a3a5b63f7b7ebd15b4ab9`
- B: `bf27265ec7e4c27b9151e881b02b516916608f472508bd9eb835055bf1076215`
- C: `bf077c5a360964138755be1d11b5acf64b828fa777ce4a142954ab808b261128`

Recompute and record hashes if inputs change; never silently treat a changed
brief as the same fixture. Keep the Markdown pair immutable during a run.

The hyphenated `output/build-preparation/` currently contains an older valid
four-route pack `20-46-08-09-6b899b90` and two empty-index negative examples
`02-31-09-09-292e7fab`, `02-31-09-09-4115324a`. Use the former offline to test
multi-route behavior and the latter to prove rejection before a model call.
Do not confuse folder spelling with eligibility or rewrite invalid source
briefs to make the paid campaign pass.

The three current packs are all single-route examples. Passing them does not
establish multi-route reliability. Add offline cases for renamed routes and
sections, reordered sections, long content, Unicode, empty optional lists,
absent optional media, extra supported sections, and route-scoped media.
Supported contract variation must work; corrupted hashes, unknown contract
versions, unsafe URLs, and unresolvable IDs should fail clearly at admission.

## 4. Strategy and boundaries

Keep the durable coordinator and React/Vite pipeline. Reduce the number of
mechanical details the model must invent. Host code owns identities, paths,
content binding lists, toolchain, image resolution, basic responsive layout
rules, attempt accounting, and release decisions. The model chooses the
composition and writes approved-content section implementations using tested
building blocks.

Use a small layout recipe catalogue, building on `RouteShell`, `LocalImage`,
`Reveal`, and `Disclosure`. A framework rewrite or a full second portfolio
renderer would introduce too much untested code. A universal page template that
ignores approved content/design is also inappropriate. The bounded fallback
should simplify a failing section to an approved, tested recipe while retaining
its content and required interactions.

Review D-064, D-065, D-068, D-077, D-083 and D-084 before implementation.
D-077 deliberately deferred broader layout components. The owner now authorizes
necessary templates and simplification; record the narrowly adopted recipe
decision and serial accounting contract in `DECISIONS.md` when implementing.
Do not mark this planning document as an implemented architectural decision.

Do not start by increasing repair limits. Preserve finite configured budgets,
make their counting correct, and eliminate deterministic reasons for wasting
them. A full pipeline includes multiple role/model calls; five pipelines does
not mean five individual completions. Record both quantities separately.

## 5. Ordered implementation work packages

Paths below starting with `core/` are relative to
`src/oryxenai/agents/code_generator/`. The same base applies to `prompts/`
and `scaffolds/`. Paths starting with `jobs/` or `agents/shared/` are relative
to `src/oryxenai/`. Tests and scripts are relative to the repository root.
New files are explicitly identified.

### WP1 — Reproducible regression baseline and preflight

Files: `core/brief_ingestion.py`, `core/development_input.py`,
`core/check_runner.py`, `core/dependency_manager.py`, `core/process_runner.py`,
`scripts/warm-npm-cache.ps1`, `scripts/warm-npm-cache.sh`, readiness service.

1. Inspect Git status, unstaged/staged diffs, current decisions and campaign
   ledger. Preserve contributor changes. In this audit `PLAN.MD`, input
   documents, deleted documentation, an old export, and untracked research/tools
   were already dirty. Never stage the whole tree.
2. Create minimal sanitized fixtures for R01/R02/R05 and the three input
   variations. Do not commit private prompt dumps, signed media URLs, caches or
   complete personal briefs simply to get reproducibility.
3. Add a generator preflight that uses the same effective settings/executable
   resolution as the worker. Report safe facts: Node/npm versions, platform,
   scaffold hash, dependency pins hash, writable workspace/cache, resolved
   browser availability, and reachable gateway. Never serialize all settings.
4. In a new disposable workspace, prove install, TypeScript, Vite build, and
   local browser launch against a small valid scaffold fixture. This happens
   before planning a paid portfolio. A metadata-only npm warm is insufficient.
5. Test the real dependency manager starting from the scaffold lock, then
   adding the approved dependency sets used by A/B/C. Proving the warmer's
   all-packages-at-once lock does not prove every acquisition sequence.
6. After the dependency manager's permitted lock preparation, perform a fresh
   offline `npm ci` using the resulting manifest/lock. Check the final lock
   hash matches the receipt. Keep strict `npm ci` for final verification.
7. Run equivalent proof inside the Linux image intended for the Azure VM.
   Windows-native cache/install success is not Linux proof. Record unexecuted
   Linux tests honestly if that runtime is unavailable.
8. If the cache lacks approved dependencies, run the trusted cache warmer once,
   then retry the offline proof. Never let generated code request unrestricted
   package installation. Treat subprocess permissions, disk, browser, and cache
   failures as environment issues; do not send them to a source-repair LLM.

Acceptance: A/B/C compile, malformed pairs fail before ModelClient, and the
actual platform can install/build/launch without a portfolio model call.

### WP2 — Preserve complete proposals through bounded repair (R01)

Files: `core/generation_orchestrator.py`, `core/source_validation.py`,
`core/generation_contract.py`, `prompts/repair_source.md`.
Tests: existing `test_generation_contracts.py`, `test_phase2_design_neutral.py`,
plus new `tests/unit/agents/code_generator/test_repair_candidate_lifecycle.py`.

1. Introduce a per-unit pending proposal, separate from the accepted checkpoint:
   base checkpoint hash, canonical owned paths, latest complete file bodies,
   pending exported signatures, current diagnostic bundle, and attempt identity.
   Use existing restricted ledger persistence; no new service is needed.
2. Validate each response envelope/path/ownership/byte limit before retaining
   file bodies. Invalid source may remain restricted repair evidence, but it
   must never become an accepted checkpoint or executable trusted code.
3. On an initial six-file proposal, retain all six even if one CSS file fails.
   On a one-file repair response, overlay that complete corrected body onto the
   pending proposal. Absence from a repair response means unchanged pending
   source, not deletion. A declared delete must not be inferred.
4. Reconstruct a disposable candidate from the last accepted base plus the
   merged pending files. Run content/import/path validation, TypeScript, and
   the unit contract against that complete candidate.
5. Keep D-084: initial creation is strict; stale create/replace tags may be
   normalized only in the already-authorized repair envelope. Do not broaden
   path ownership or permit trusted-file mutation.
6. Swap into the accepted repository and create a checkpoint only after unit
   validation passes. Keep candidate errors/files available for the next repair
   without overwriting the last accepted tree. Reuse existing swap/rollback
   primitives and validated paths; never reset the user's repository.
7. Refresh `previous_attempt_files` from the entire pending proposal, not just
   the most recent repair response. Keep a complete owned-file inventory even
   when source bodies need context limits. If an indispensable file would be
   dropped, shrink the unit or return an explicit context-size condition;
   silently omitting it recreates this bug.
8. Include expected, present, pending, missing and changed paths in repair
   context. Tell the model that it may return only changed complete files and
   that the host preserves other pending files. Keep exact content/marker and
   export contracts visible. Validate combined export signatures against the
   resulting candidate rather than requiring unrelated files to be reemitted.
9. Replace stale active diagnostics after revalidation; preserve historical
   diagnostics in the attempt ledger. Fingerprints should include owner/path
   where available so equal messages in different files do not hide each other.
10. Persist the pending proposal/checkpoint binding so a worker restart either
    resumes the same unit safely or discards a stale proposal explicitly.
    A redelivery must not reset consumed repair counts.

Regression sequence: initial six files with one bad CSS length → one-file fix
→ all six still present → a remaining selector error names the actual file
→ next bounded fix → one accepted checkpoint. Also test an unsafe file hidden
among five valid ones, invalid repaired content, missing files, duplicate paths,
restart, and swap failure. No source becomes accepted merely because it exists.

### WP3 — Serial stop-on-failure execution and durable accounting (R02–R04)

Files: `core/generation_orchestrator.py`, `core/parallel_scheduler.py`,
`core/development_schemas.py`, generation projection repository/handler code,
`core/repair_policy.py`, and current worker retry helpers.
Tests: new `tests/unit/agents/code_generator/test_generation_attempt_accounting.py`
and relevant worker/integration tests.

1. Implement a real sequential path when configured `route_concurrency=1`.
   Await batch 1, persist its outcome, then decide whether to start batch 2.
   Do not enqueue all sibling coroutines behind a semaphore.
2. Keep isolated candidate directories if needed, but use one authoritative
   generation-level attempt/budget record. Persist a reserved repair attempt
   before its ModelClient call; record its result, exception or cancellation
   before propagating failure. Use durable attempt IDs for deduplication.
3. In `finally`/error handling, merge or append new receipts, diagnostics,
   per-unit status and counters even when a batch fails. Use deltas or unique
   attempt records; summing whole cloned projections would double-count the
   common prefix. Export only safe summaries, not raw contexts.
4. Persist completed unit checkpoints independently. A later failed batch must
   not erase a previously verified batch. On retry, resume those checkpoints
   only when source, input, policy, prompt and toolchain identities match.
5. Correct success-path merging too: persist unit repair/request state,
   generation repair totals, strategies, and recurrence counts. The current
   merge loses these even if all batches return successfully.
6. Do not expose the known-unsafe concurrent path as an alternative. For this
   repair release, constrain active portfolio generation to serial batches
   through configuration validation. If retaining concurrency>1, it must first
   pass centralized reservation, sibling cancellation/draining, no-orphan-call,
   and failure-accounting tests; this is unnecessary for the requested campaign.
7. Trace planner retry, transport retry, durable job retry, source repair,
   integration polish, and final repair separately. Preserve legitimate
   recovery, but never let a generic worker retry restart an exhausted semantic
   repair loop. Separate safe retryable environment/provider errors from
   deterministic contract/source exhaustion.

Acceptance: failing batch 1 produces nonzero accurate call/repair counts in the
API; batch 2 is not started in serial mode; total budgets survive redelivery;
success/failure receipts persist exactly once; last accepted preview stays intact.

### WP4 — Optional components cannot break the trusted foundation (R10)

Files: `jobs/handlers/code_generator.py` acquisition path,
`core/generation_orchestrator.py::_resolve_requests`,
`core/dependency_manager.py`, `agents/shared/component_retrieval.py`,
`core/resource_adapters.py`, and scaffold shared primitives.

1. Preserve exact execution-slot/category matching and the current supported/
   unsupported bare-import gate. Do not install `rough-notation` just because
   a fetched optional source imports it.
2. Before an optional fetched module enters the generated tree, validate its
   intended path, local imports/aliases, expected exports, dependency receipts,
   CSS expectations, and TypeScript compatibility in a disposable admission
   candidate using the admitted scaffold. Attribute errors to that component.
3. If optional component admission fails, keep the raw source as reference-only
   evidence and use its declared local fallback. Prefer existing native/React
   primitives: `Disclosure` or `<details>` for work detail, ordinary semantic
   lists for capability grouping, and an ordered list for a timeline. Implement
   required interactions rather than pretending a list is a functioning tab UI.
4. Remove rejected executable source and stale dependency/usage obligations from
   the candidate through controlled materialization. Record fallback disposition
   and reason against the same slot; keep approved slot/route/section identity.
5. A required component with no conforming fallback must fail at acquisition
   with its exact compatibility reason. It must not surface as a mysterious
   deterministic foundation failure after planning additional source work.
6. Exercise both initial and emergent acquisition paths in regression tests.
   Tests cover unsupported subpaths, scoped packages, relative imports, missing
   exports and incompatible prop types, plus a known compatible admitted module.

Acceptance: the highlighter reproduction gets a usable permitted fallback;
optional downloaded code cannot cause an otherwise valid foundation to fail.

### WP5 — Finish host-owned plan bookkeeping and image obligations (R07)

Files: `core/planner_operation.py`, `core/development_planner.py`,
`core/blueprint_compiler.py`, `core/development_schemas.py`,
`core/generation_contract.py`, `core/design_realization.py`,
`core/final_source_validation.py`, settings and identity/hash compilation.

1. Preserve existing exact canonicalization of route/section identities, content
   keys, reserved colors, typography and distinctive-move selectors. Add tests
   that exercise every A/B/C section name; do not hardcode `home:hero`.
2. Treat host-known identities and coverage arrays as compiler data. Do not
   make a model invent missing IDs or reorder approved content. Reject truly
   unknown/ambiguous scope with expected/observed IDs and a bounded retry.
3. Snapshot the effective image policy into the run's admitted/compiled evidence
   and carry it to source validation, runtime verification and export. Include
   its version/hash in the candidate/verification identity. Worker settings
   changing midway must not silently change an existing run's obligations.
4. Separate a slot's optional-resource fallback permission from the portfolio's
   minimum visible-image requirement. For the supplied packs, require at least
   one visible approved image on the primary route; prefer a second only when
   contextually useful. An abstract raster illustration is an image; a hidden
   `<img>`, empty frame, icon, or source comment does not satisfy the requirement.
5. Require independent final evidence that enough qualifying placements were
   materialized and visibly used on the required route. Count defined unique
   placements/slots consistently; do not satisfy a minimum by duplicate tiny
   copies or by an image on a different route.
6. If the primary selected optional image fails acquisition, choose another
   already-approved compatible slot within its allowed route/section scope and
   record a bounded host plan delta. Rerun plan/resource checks. If no approved
   image can satisfy the obligation, report that resource failure explicitly.
   Do not manufacture portfolio facts or silently claim imagery success.
7. Keep text-only/prohibited-imagery inputs supported. Mark the image policy
   exemption explicitly when no approved media is permitted, and validate the
   site under that declared policy. The current three packs do permit images.
8. For C's route-scoped abstract slot, preserve acquisition scope separately from
   the planner's presentation assignment to `home:introduction`. Join by exact
   slot ID when building reports; an empty source `section_ids` is not proof
   the image was placed nowhere.

Tests: empty placement array, failed primary image plus successful image on
another route, all optional downloads failing, permitted replacement, unknown
section, text-only exemption, duplicate placements, and policy change on resume.

### WP6 — Tested layout recipes and focused prompt changes (R09/R11)

Files: scaffold `src/components/generated/SharedSystems.tsx` and trusted CSS,
new `core/layout_recipe_catalogue.py`, existing token/workspace compilers,
`core/generation_contract.py`, `prompts/planner.md`, `prompts/route_batch.md`,
`prompts/route_compose.md`, `prompts/repair_source.md`, source/AST validators.

The redesign audit supports better typography, real layout ownership and
contextual imagery. It does not authorize inventing content, switching the
approved palette, adding stock avatars, or fetching runtime placeholder photos.

1. Add only three tested composition recipes initially: text-with-supporting-media,
   work-detail-list, and timeline/list. Use current framework/dependencies.
   They are content-shape recipes, not profession/person-specific templates.
2. Keep literal route/section/region markers in generated route source where
   existing audits require them. Have the compiler emit CSS for the canonical
   `[data-region-id="..."]` that actually owns the recipe's direct children.
   Avoid a new wrapper that hides those markers from static validation.
3. The split recipe needs two actual grid children on wide screens, a single
   column on small screens, `minmax(0, ...)` tracks, child `min-width: 0`, and
   bounded image frames. It must not put a two-column grid on a section that
   contains only one full-content wrapper.
4. Use existing admitted tokens for typography/palette/gaps. Give body copy a
   readable measure without imposing that narrow measure on the entire hero.
   Use bounded responsive heading sizes and wrapping; judge real long copy at
   small laptop width. Do not enforce an arbitrary universal line count.
5. Model-selected recipe parameters must be typed and bounded. Reuse existing
   region/placement fields where possible. If a recipe selector field is needed,
   make it an additive versioned enum with a deterministic legacy default;
   update model schema, compiler, generation contract, prompt hash and tests.
6. Render image paths only through `LocalImage` and the trusted manifest. Pair
   it with a known-size frame so a valid image has nonzero visible area. Use
   eager loading for an opening image and lazy loading for supporting images.
7. Keep motion progressive: approved content is mounted in normal document
   flow; motion failure or reduced-motion preference must not hide it. Reuse
   `Reveal`/`StaggerGroup`; do not generate a second competing animation on the
   same property. No required project description available only on hover.
8. Prefer approved neutral/abstract imagery over an unrelated photo. C already
   has a suitable abstract network illustration. Its craft-table image is an
   optional upstream pin described as process texture: omit it or keep it truly
   subdued if useful, rather than displaying it as dominant project evidence.
   Preserve provenance; do not label decorative stock imagery a project screenshot.
9. Update planner/builder/repair prompts together: distinguish literal
   requirements from optional style preferences; give one complete compatible
   example per recipe; supply exact content accessors, owned paths, layout
   selectors, image bindings and existing-file state. Remove contradictions and
   duplicate wording only after mapping each enforced rule to its source.
10. For a repeated cosmetic/layout failure, permit one bounded simplification to
    a tested recipe within the existing repair budget. Keep all approved copy,
    links and required interactions. Run the same validators afterward. Do not
    accept a fallback solely because it is a template or because a model says so.

Acceptance: a synthetic long-content sample and A/B/C-shaped fixtures render
without empty columns, missing images, clipped copy or hidden work details at
390×844, 768×1024, 1280×800 and 1440×900. The approved visual direction remains
recognizable. Capture both initial-viewport and full-page images for inspection.

### WP7 — Browser evidence and release policy agree (R06–R09)

Files: `core/runtime_verifier.py`, `core/design_realization.py`,
`core/finding_policy.py`, `core/final_source_validation.py`,
`core/integration_review_operation.py`, verification handler and runtime tests.

1. Keep functional blockers: build/type errors, exceptions, broken routes/links,
   missing approved content, inaccessible required controls, failed required
   media, unsafe networking, and meaningful horizontal overflow.
2. Keep subjective spacing/ratio/composition observations advisory unless a
   specific approved requirement is violated. Do not reintroduce a cosmetic
   repair loop or turn every layout observation into `needs_attention`.
3. Audit the current keyword-based severity classifier. Use an explicit mapping
   for known deterministic codes; model findings should carry evidence and
   requirement references. A phrase such as "missing visual balance" must not
   become a functional blocker just because its code contains `missing`.
   Unknown unclassified findings remain visible and conservatively handled.
4. Verify each obligated image in the real browser: load/decode within a bounded
   timeout, `currentSrc` belongs to admitted local media, positive natural
   dimensions, visible painted area, applicable alt policy, and usable frame.
   Inspect opacity/visibility on ancestors and clipping/occlusion as needed;
   checking only the `<img>` style is insufficient. Add counterexample fixtures
   for ancestor `opacity:0`, zero-sized frame and an entirely clipped image.
5. Scroll lazy supporting images into view before checking them; preserve/reset
   scroll position for screenshots and subsequent journeys. Waiting for decode
   should be bounded for eager images too. Verify initial hero separately.
6. Keep intrinsic image ratio and rendered frame/crop ratio separate. The current
   check measures natural dimensions. Do not reject legitimate `object-fit`
   presentation for violating a constraint that actually describes the frame.
   Name both observations in evidence and test a valid cropped image.
7. Persist safe per-image observations: slot, route, section, viewport, decoded,
   visible, local path, measured frame and reason. Use these observations in
   reports. Source reference detection may remain a preliminary check but must
   be named `referenced_in_source`, never proof of visible rendering.
8. Test correct exact-selector recipes positively and actually missing layout
   properties negatively. Fix compiler/prompt agreement; do not globally disable
   marker or layout ownership validation to admit class-based CSS.
9. Preserve verified and unverified candidate preview separation and success
   entitlement guards. A prior active preview must not make a failed new run
   appear successful. A candidate preview must be labelled as such.

Acceptance: an image-free recreation of the historical `ready` source cannot
pass the new image-required campaign; a clean functioning portfolio with only
spacing advisories can pass; hidden/broken media and real functional errors fail.

### WP8 — Truthful, useful reports for every terminal path (R05/R06)

Files: `core/portfolio_export.py`, `core/generation_orchestrator.py::_fail`,
`jobs/handlers/code_generator.py::_needs_attention`,
`jobs/handlers/code_generator_verification.py::_export_portfolio` and failure
path, plus `tests/unit/agents/code_generator/test_portfolio_export.py`.

1. Extract a shared safe evidence-summary builder used for successful and failed
   exports. Callers pass the run/plan/projection/verification facts they possess.
   Do not let `export_failed_run` synthesize blank metadata when records exist.
2. Report run status, failing stage, first actionable issue, terminal wrapper
   error, input hashes/reference, last accepted checkpoint, candidate status,
   actual build outcome, routes, attempt/repair counts and evidence completeness.
3. Include generation/acquisition/planning issues as well as verification
   findings. An absent verification receipt means `not_run` when the stage was
   never reached, or `unknown` when evidence is missing, never zero defects.
4. Distinguish `planned`, `materialized`, `referenced_in_source`,
   `decoded_in_browser`, and `visible_in_browser`. Use null/not-run states for
   browser evidence when verification never executed. Do not infer it from files.
5. Advertise `dist/` only when present and produced from the reported source
   identity. Include a preview URL only with its real verification status.
   Do not call a failed scaffold export a complete portfolio.
6. For early failures with no source, write a metadata-only diagnostic export or
   equivalent downloadable safe failure receipt. A source/dist directory is not
   required to explain a failed plan/acquisition.
7. For failed batch groups, expose accepted source separately from restricted
   rejected candidates. Preserve candidate artifact references for developers;
   do not mix unaccepted batch source into a purported runnable export.
8. Make export writes atomic and collision-safe. Preserve existing exports
   rather than deleting an earlier same-minute snapshot before the new one is
   complete. Use unique attempt/snapshot suffixes; report export failures as
   advisory without losing the terminal generation diagnosis.
9. Test ready, early planner failure, acquisition failure, failed route batch,
   buildable unverified candidate, unsuccessful build, missing runtime receipt,
   and nonzero failed-attempt accounting. Assert report text and JSON agree.

### WP9 — Offline completion checks and Linux/preview parity

1. Run focused regressions after each work package, then Code Generator unit,
   API, integration and worker tests that exercise changed boundaries. Use the
   dedicated test database; never reset application data to make tests pass.
2. Keep a small deterministic no-model replay that executes the orchestrator's
   real validation/repair path with scripted model responses. At least one case
   must run initial rejection → minimal repair → unit acceptance → composition
   → build/runtime checks. Isolated validator tests do not cover lifecycle bugs.
3. Replay the recorded latest response and the minimal R01 sequence against
   current validators. Synthetic fixtures should cover varied content shapes,
   missing optional resources and the multi-route contract independently.
4. Check lint, formatting and types on changed code. Run frontend checks only
   if the API projection/UI adapter changed. Do not absorb unrelated failures
   or contributor edits into this task.
5. Exercise generated sites through the real preview gateway under a capability
   prefix, with deep-route refresh, local image/font URLs, mobile navigation and
   the preview bridge. A root-only local static server is not equivalent proof.
6. Validate `compose.production.yaml`, configured app/preview origins,
   persistent workspace/cache/artifact access and gateway readback.
   Replace placeholder hosts only with actual deployment configuration supplied
   by the owner. Local validation is not an Azure deployment claim.
7. Resolve child-process permission failures as environment blockers and rerun
   the same offline checks under approved permissions. Do not weaken source
   checks or spend another planner run to diagnose `spawn EPERM`.

Useful existing commands from repository root:

```powershell
uv run pytest -q tests/unit/agents/code_generator
uv run mypy src
uv run ruff check src/oryxenai/agents/code_generator tests/unit/agents/code_generator
uv run ruff format --check src/oryxenai/agents/code_generator tests/unit/agents/code_generator
docker compose -f compose.production.yaml config --quiet
```

For this planning audit, focused generation-contract, dependency, export and V4
tests passed after a Windows temporary-directory permission error was resolved
by an approved rerun using a fresh in-workspace pytest directory. That is baseline
evidence, not proof that the planned changes exist or that full generation passes.

## 6. New five-run campaign: exact operating procedure

### Before reserving slot 1

- Complete WP1–WP9 and commit verified changes. Record HEAD, input hashes,
  policy/scaffold/prompt identity and effective nonsecret settings.
- Inspect current jobs and worker processes before starting services. Do not
  start an extra worker or indiscriminately kill Python/Node processes. Do not
  resume old failed pipelines or cancel other users' jobs as incidental cleanup.
- Create a new dated section in `docs/code-generator-live-campaign.md`, retaining
  both older campaigns unchanged. State maximum 5, used 0, accepted 0.
- Verify provider readiness and local infrastructure. Provider preflight sends
  no portfolio content and must not start a full generator pipeline.

### Run order and failure handling

| New slot | Choice and condition |
|---|---|
| 1 | C, because it reproduces the latest repair sequence and tests the route-scoped illustration. |
| 2 | B if slot 1 passed; if slot 1 failed, first diagnose/fix/replay that issue and choose the pack that exercises the fix. |
| 3 | A if it remains unsampled and fewer than two accepted cross-pack results exist; otherwise choose the unresolved failure case. |
| 4 | Only after diagnosing and fixing the previous failure, with a recorded reason this run adds evidence. |
| 5 | Final slot under the same rule. Stop afterward regardless of outcome. |

For each run:

1. Reserve the slot in the ledger before POST. Record pack hash, code revision,
   idempotency key and start time. Capture returned run ID immediately.
2. Start exactly one full pipeline. Poll its state and paginated events to a
   terminal state. Do not run all three example inputs concurrently.
3. On failure, read the earliest causal event, persisted source proposal,
   actual candidate inventory, dependency/resource receipts, diagnostics and
   later wrapper errors. Distinguish source defect, validator error, missing
   evidence, bad upstream media, and environment/provider failure.
4. Add a minimal failing regression or offline replay, implement the root fix,
   verify it and commit before the next reservation. Compare recurrence by
   failure cause + file/owner + checkpoint, not just `needs_attention`.
5. If a run is `ready`, inspect desktop and mobile screenshots and exercise its
   visible controls/media. Save exact preview URL, export, build/checkpoint
   hashes, blocking/advisory findings and image observations. A visually empty
   result consumes a slot but does not count as an accepted portfolio.
6. Prefer two accepted results from different packs on the final implementation
   revision. If code changes after the first success, revalidate its saved source
   under the final checks without new LLM calls; report this limitation clearly.
7. Every restarted planner/source pipeline consumes a new slot. A verification-
   only retry reusing the same accepted source is not a new full pipeline, but
   record it and any final-repair model calls. Never use retries to disguise a
   sixth source-generation attempt.
8. Stop at two accepted cross-pack results or five reservations. If slot 5
   fails, diagnose and implement a bounded justified fix if possible, run its
   offline checks, and finish with an honest unresolved live-validation handoff.
   Do not make a sixth full pipeline call under this authorization.

### Commands for the implementing agent

Use the existing service launcher only after checking whether those services
already run. It starts API, worker and preview processes.

```powershell
Set-Location -LiteralPath 'C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI'
.\scripts\run-native.ps1 dev
```

In a PowerShell shell, choose one pack per reserved slot. These requests start
real work; they are for the implementation campaign, not the planning audit.

```powershell
$cgBase = 'http://127.0.0.1:8000/api/v1/development/code-generator'
Invoke-RestMethod -Method Get -Uri "$cgBase/readiness"
Invoke-RestMethod -Method Get -Uri "$cgBase/build-preparation-packs"
Invoke-RestMethod -Method Post -Uri "$cgBase/provider-preflight"

$cgPack = 'c0860464-a786-43d8-9c30-d12d7516c4b8'
$cgKey = [guid]::NewGuid().ToString()
$cgRun = Invoke-RestMethod -Method Post `
  -Uri "$cgBase/runs/from-build-preparation" `
  -Headers @{ 'Idempotency-Key' = $cgKey } `
  -ContentType 'application/json' `
  -Body (@{ brief_set = $cgPack } | ConvertTo-Json)
$cgRunId = $cgRun.run_id
$cgRun | ConvertTo-Json -Depth 8

Invoke-RestMethod "$cgBase/runs/$cgRunId" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$cgBase/runs/$cgRunId/events?limit=200" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$cgBase/runs/$cgRunId/generation" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$cgBase/runs/$cgRunId/verification" | ConvertTo-Json -Depth 12
Invoke-RestMethod "$cgBase/runs/$cgRunId/preview" | ConvertTo-Json -Depth 8
```

Use the event endpoint's returned cursor/`after` contract to fetch subsequent
pages; the first 200 events may be incomplete. Inspect routes for exact response
shape before scripting unattended polling. If attached auth is enabled, use an
existing authorized admin session/Bearer header; never disable product auth.
If POST times out after possible acceptance, reconcile using the same idempotency
key and existing run before creating another reservation.

From a completed export, npm must run inside its `source/` subdirectory or with
an explicit `--prefix` pointing there. Do not run npm from the export parent or
the user's home directory. The exported `dist/` must be from its reported source.

## 7. Deliverables and final handoff

The implementation is complete only when it supplies:

1. Generator/scaffold fixes with task-scoped commits and meaningful regressions.
2. Issue entries for R01–R12 classified as fixed, verified, advisory, deferred,
   or still blocked, with source locations, tests and live confirmation status.
3. Truthful successful/failed export reports backed by durable attempt and
   browser evidence; no fabricated zero counts or nonexistent dist claims.
4. A campaign ledger with every reserved slot, pack/code/input identities,
   terminal result, first cause, fix commit, calls/repairs and preview/export.
5. Accepted screenshots and preview links for successful packs, or an explicit
   statement that no result met acceptance. List the untested packs/platforms.
6. Updated `CHANGES.md`, its required compaction check, architectural decisions
   actually adopted, and a concise next-agent handoff. Commit only owned work;
   do not push, reset or sweep unrelated changes into the commit.

Suggested commit units: candidate lifecycle; serial accounting; component
admission; image obligation/evidence; layout recipes/prompts; truthful exports;
offline and preview acceptance; live failure fixes as individually verified.

## 8. Primary references checked for this plan

- npm documents that `npm ci` rejects a mismatched lock and does not update it.
  This supports separating acquisition lock preparation from the clean-install
  proof. [npm ci documentation](https://docs.npmjs.com/cli/v11/commands/npm-ci/)
- Playwright's visibility/actionability definitions do not establish that an
  image is meaningfully painted; use explicit media observations and screenshots.
  [Playwright actionability](https://playwright.dev/python/docs/actionability)
- Vite's public base-path behavior matters to nested preview URLs; test the
  repository's resource/router helpers under its actual gateway prefix.
  [Vite base configuration](https://vite.dev/config/shared-options.html#base)

Local evidence: `code generator issues.md`, `docs/code-generator-live-campaign.md`,
the specific run directories above, current handler/core source, historical
desktop/mobile screenshots, and fresh read-only API projections.
