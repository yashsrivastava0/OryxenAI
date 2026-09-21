# Code Generator reliability and portfolio quality: implementation plan

## 1. Purpose and status

This is an implementation handoff for repairing OryxenAI's existing Code
Generator. It covers variable Build Preparation briefs, image acquisition and
rendering, distinctive visual composition, bounded model repair, portable
exports, and the authenticated frontend preview.

**Status: plan delivered; the changes described below have not been implemented
by the author of this plan.** Repository inspection and the generator unit suite
were completed. A fresh live generation campaign, a rendered-portfolio review,
and production deployment were not performed during this investigation.

The inspected unit suite passed using the existing project virtual environment,
the explicit test configuration, and fresh temporary directories. That result
does not establish live generation success: the confirmed cross-stage defects
below are not covered by the existing assertions.

Read `AGENTS.md` and `DECISIONS.md` before implementation. The worktree contains
other contributors' uncommitted generator, frontend, migration, and deployment
changes. Preserve them. Re-read a file and its Git diff immediately before
editing; another contributor changed `AppShell.tsx` during this investigation.

Model names and providers come from `config/models.toml`. Configuration and
verification commands, rather than frozen model names or test counts, remain
the source of truth.

## 2. Outcome required

A successful run must produce a portfolio that:

1. Uses the approved content, route topology, navigation destinations, and
   visual direction from its own immutable Build Preparation brief pair.
2. Works for different professional domains, section names, route counts,
   content lengths, image counts, and supported brief formats.
3. Builds from an exported source directory using its included package manifest
   and real lockfile, without importing anything from the OryxenAI repository.
4. Runs from the built static artifact without calling a model, downloading
   fonts, or fetching image-provider URLs in the visitor's browser.
5. Renders actual local images with appropriate sizes, crops, alt text, and
   loading policy whenever approved image obligations exist.
6. Shows intentional typography, varied composition, and a subject-appropriate
   signature interaction; approved motion has a readable reduced-motion state.
7. Supports direct entry and refresh on every approved route, both in the
   embedded preview and in a separate browser tab.
8. Reaches `ready` only after the exact candidate passes required source,
   build, browser, storage-readback, and preview-promotion checks.
9. Preserves the previous verified preview if regeneration fails.
10. Reports a specific, recoverable failure when an external dependency or
    bounded repair prevents completion. A plausible-looking success flag is
    not a substitute for a working portfolio.

“Different Build Preparation outputs” means different valid content and
supported formats. Malformed JSON indexes, mismatched hashes, unknown versions,
and missing approved sections must produce actionable admission errors.

## 3. Evidence: what is wrong and what is already present

### F01 — An impossible image minimum for small image sets

**Confirmed in source.** In
`src/oryxenai/agents/code_generator/core/image_policy.py`,
`build_image_policy_snapshot()` copies the configured image minimum unchanged
when at least one image slot exists. In `development_planner.py`,
`_validate_v4_image_policy()` requires that many distinct approved slots.

Example: a brief has one approved slot and the configured minimum is two.
No valid planner response can satisfy that contract. More model retries cannot
repair it. Clamp the new run's minimum to its distinct approved slot count.

### F02 — Image requirements change meaning between stages

**Confirmed in source.** The planner counts placed image slots across the
blueprint. `final_source_validation.py::validate_final_source()` counts only
placements on `primary_route_id`. In `design_realization.py`,
`_policy_image_obligations()` returns no policy obligations for other routes.

Example: home contains one approved image and a case-study route contains a
second. Planning satisfies the site minimum, source validation demands both on
home, and the policy-specific browser obligations omit the case-study route.

Fix the shared meaning: the minimum is site-wide; the primary-route requirement
is an additional, separate condition. Derive the same required placements for
source and browser validation.

### F03 — Native preview acceptance can certify broken output

**Confirmed in source.** `config/app.native.toml` enables
`code_generator_verification.preview_first_acceptance`. In
`src/oryxenai/jobs/handlers/code_generator_verification.py`, that branch can
downgrade source/build diagnostics and all runtime findings to advisories. It
can also continue after a runtime-verifier exception with no browser evidence.

This follows the earlier diagnostic policy in D-094. It conflicts with the
current requirement that successful portfolios actually work. Preserve an
explicit unverified candidate for inspection, but require functional checks
before `ready`, active-preview promotion, or success-entitlement consumption.

### F04 — Early frontend refresh requests generation state prematurely

**The call site is confirmed; the precise entitlement failure still needs a
focused reproduction.** `frontend/src/app/AppShell.tsx::refetchCurrentSession`
includes `api.getCodeGenerator(sessionId)` in its initial parallel fetch. A
rejected generation fetch makes the entire connection state `stale`.

The prior session's `ISSUES.md` reports `ENTITLEMENT_BINDING_CONFLICT` during
earlier stages. `CodeGeneratorService.get_state()` calls
`_normal_owner_entitlement()`, whose missing-entitlement branch raises that
error. The report alone does not establish which entitlement condition caused
each browser failure. Reproduce missing versus mismatched bindings separately;
do not suppress all 409 responses.

Another contributor's current `AppShell.tsx` edit adds initial-stage restoration.
Preserve that independent change while fixing fetch eligibility.

### F05 — Images can be planned without being rendered

**Historical live evidence; reproduce against current code.** The local issue
ledger describes a planned image wrapper without a `LocalImage` child. The
trusted `LocalImage` component already reads local renditions from
`RESOURCE_MANIFEST.image_assets`; it returns `null` when no usable source
exists. Existing resource-binding tests already cover some missing-reference
forms. Extend those checks only where a focused reproduction shows a gap.

A wrapper marker, a successful download, a source comment, or an unused import
is not proof of a visible image. Browser decode and visibility evidence must
remain authoritative.

### F06 — Windows spawn failures need infrastructure recovery

**Historical evidence and existing implementation.** Vite's `spawn EPERM`
condition is already classified by `build_runner.py`. Current uncommitted work
adds process-count and duration context. Do not replace generated source to
repair an operating-system process failure. Preserve this classification and
retest the toolchain before spending generation calls.

### Existing mechanisms to reuse

- Strict Markdown brief ingestion and immutable input envelopes.
- Provider-neutral `ModelClient` profiles.
- Creative direction and typed blueprint planning.
- Deterministic work ownership, layout recipes, and trusted motion primitives.
- Controlled local resource acquisition and dependency admission.
- Source checkpoints, bounded repair, and durable job redelivery.
- Runtime navigation, geometry, image, font, interaction, and motion checks.
- Candidate previews, stable preview promotion, and storage readback.
- The production start/regenerate/retry API and authenticated Generation stage.

Do not rebuild these systems or introduce a second independent generator.

## 4. Architecture: five logical model stages

Retain the current durable job structure. Five logical model stages do not
require five new job types or exactly five HTTP requests to a model provider.
Large portfolios need bounded route batches; claiming a constant five-call
budget for every input would be unrealistic.

| Logical stage | Existing implementation | Responsibility |
| --- | --- | --- |
| 1. Creative direction | `core/creative_operation.py`, `prompts/director.md` | Grounded visual concept, hierarchy, subject-specific signature |
| 2. Blueprint planning | `core/planner_operation.py`, `core/development_planner.py`, `prompts/planner.md` | Exact route/section coverage, tokens, placements, layout and interaction contracts |
| 3. Source construction | `core/generation_orchestrator.py`, `prompts/route_batch.md`, `prompts/route_compose.md` | Complete owned source files in bounded batches |
| 4. Integration and quality review | `core/integration_review_operation.py`, `core/quality_review.py`, integration prompts | Cross-route consistency and evidence-backed findings |
| 5. Targeted repair | `core/final_repair.py`, `core/repair_policy.py`, `prompts/repair_source.md` | Change only implicated owned files using concrete diagnostics |

Deterministic admission runs before stage 1. Acquisition and scaffold
materialization run between planning and source construction. Deterministic
checks run after each relevant source change. Clean build, browser verification,
artifact readback, and atomic promotion finish the workflow.

The existing durable `plan`, `acquire`, `generate`, and `verify` stages remain
the coordinator vocabulary. Existing frontend milestones remain `Plan`,
`Acquire`, `Build`, `Verify`, and `Preview`. Model operations and frontend
milestones are different concepts and must not be conflated.

### Call and retry rules

- Use configured profile names, output ceilings, timeouts, and retry budgets.
- Keep route construction serial until independent concurrency is proven safe.
- Use existing work-graph units rather than one unconstrained call per section.
- Persist the logical call identity, operation, attempt epoch, source checkpoint,
  usage, outcome, and affected owner before progressing to successors.
- Reuse a valid accepted checkpoint after worker redelivery.
- Charge a retry to the existing relevant allowance; worker redelivery must
  not silently reset the generation repair budget.
- A valid `cannot_complete` response ends that repair branch immediately.
- Infrastructure failures do not trigger source-model repair.
- Stop repeated no-progress repairs using the existing diagnostic fingerprints
  and receipt history. Do not increase budgets to hide deterministic defects.

## 5. Implementation order and completion units

Implement in the following order. Each row is a reviewable local commit after
its targeted checks pass. Update `CHANGES.md` for completed units and record real
policy changes in `DECISIONS.md`.

| Task | Depends on | Deliverable |
| --- | --- | --- |
| T01 | None | Isolated baseline and regression fixtures |
| T02 | T01 | Feasible, site-wide image policy with shared placement selection |
| T03 | T02 | Acquisition-to-render image contract and meaningful fallback |
| T04 | T01 | Truthful required verification and preview promotion |
| T05 | T02, T03 | More reliable generation contexts and bounded source repair |
| T06 | T05 | Visual composition and trusted motion acceptance |
| T07 | T04 | Correct session reads, frontend refresh, and preview state |
| T08 | T03, T04 | Portable source/dist exports and direct-route preview |
| T09 | T02–T08 | Variable-input regression and live acceptance campaign |
| T10 | T09 | Documentation, evidence, task-scoped commits, final handoff |

## 6. T01 — Establish an isolated baseline

### Files to inspect

- `tests/conftest.py`
- `config/app.test.toml`
- `scripts/test.ps1`
- `tests/unit/agents/code_generator/`
- `tests/integration/test_code_generator_development_worker.py`
- `tests/integration/test_code_generator_generation_worker.py`
- `tests/integration/test_code_generator_verification_worker.py`
- `tests/api/test_code_generator_development_routes.py`

### Procedure

1. Run `git status --short --branch`, relevant unstaged diffs, and the staged
   diff. Record files already modified or untracked.
2. Explicitly set `OryxenAI_CONFIG_OVERLAY=config/app.test.toml` for tests.
3. Verify the resolved database is `oryxenai_test` before database fixtures run.
   Preserve the existing guard that refuses schema reset elsewhere.
4. Use fresh task-specific temporary/cache directories if Windows denies access
   to a cache created by another process. Do not weaken application checks to
   solve pytest directory permissions.
5. Run generator unit tests and the frontend tests before changing code.
6. Add synthetic, privacy-safe fixture variants for the exact counterexamples
   below. Existing private output can be examined locally, but must not be
   copied into committed fixtures or public evidence.

### Required failing regressions

- One approved image with a configured minimum greater than one.
- Two approved images split across home and a case-study route.
- A primary route with no approved image slots and images on another route.
- A text-only approved brief.
- A broken image, page exception, or empty runtime evidence under native
  preview-first configuration.
- A new session before generation entitlement reservation.
- A mismatched existing generation entitlement that must remain rejected.

Do not turn a real failing regression into an expected failure or skip.

## 7. T02 — Make image policy feasible and consistent

### Edit these existing files

- `core/image_policy.py`
- `core/development_planner.py`
- `core/design_realization.py`
- `core/final_source_validation.py`
- `core/verification_plan.py` if shared selection needs explicit threading
- `tests/unit/agents/code_generator/test_image_evidence_and_layout.py`
- `tests/unit/agents/code_generator/test_development_planner.py`

All `core/` paths in this document are relative to
`src/oryxenai/agents/code_generator/`.

### A. Clamp at creation, not while reading an immutable policy

In `build_image_policy_snapshot()`, after deriving distinct approved slots:

```python
available_count = len(approved_ids)
effective_minimum = min(configured_minimum, available_count)
effective_preferred = min(
    max(configured_preferred, effective_minimum),
    available_count,
)
```

Use those values in the returned `ImagePolicySnapshotV1`. Preserve the zero-slot
exemption and the check that a primary-route requirement is enabled only when
that route has an approved image slot.

Do not mutate a stored policy, blank its hash, or reconstruct it from changed
configuration during resume. New runs receive the corrected policy; old runs
retain their stamped requirements unless explicitly restarted.

### B. Define one placement-selection helper

Add this complete helper to `image_policy.py`, importing `ResourcePlacementV4`
from `development_schemas.py`. It chooses policy obligations; it does not
validate route authority or download resources. Existing blueprint validation
must continue to validate the placement's route and section membership.

```python
def required_image_placements(
    placements: list[ResourcePlacementV4],
    policy: ImagePolicySnapshotV1,
) -> list[ResourcePlacementV4]:
    if policy.text_only_exemption:
        return []

    approved = set(policy.approved_image_slot_ids)
    eligible = [placement for placement in placements if placement.resource_slot_id in approved]
    selected: list[ResourcePlacementV4] = []
    selected_slots: set[str] = set()

    if policy.require_primary_route_image:
        primary = next(
            (placement for placement in eligible if placement.route_id == policy.primary_route_id),
            None,
        )
        if primary is None:
            raise ValueError("IMAGE_POLICY_PRIMARY_PLACEMENT_MISSING")
        selected.append(primary)
        selected_slots.add(primary.resource_slot_id)

    for placement in eligible:
        if len(selected_slots) >= policy.minimum_visible_images:
            break
        if placement.resource_slot_id in selected_slots:
            continue
        selected.append(placement)
        selected_slots.add(placement.resource_slot_id)

    if len(selected_slots) < policy.minimum_visible_images:
        raise ValueError("IMAGE_POLICY_SITE_PLACEMENT_MINIMUM_MISSING")
    return selected
```

The blueprint is immutable after acceptance, so its placement order makes
selection deterministic for one run. This helper deliberately counts distinct
approved slot IDs. Do not claim it guarantees distinct photographic bytes;
that is a separate acquisition-quality observation.

### C. Use the helper everywhere that derives obligations

1. The planner must still validate every declared placement and ensure the
   global count and primary requirement. Convert helper failures to the existing
   safe planner error vocabulary.
2. Replace `_policy_image_obligations()`'s primary-only truncation with shared
   selection across the whole blueprint, followed by filtering for `route_id`.
3. In final source validation, check each selected placement against source for
   its own route and the materialized local asset set.
4. Emit diagnostics on the specific missing placement's route and slot. Avoid
   a generic primary-route error for a missing case-study image.
5. In browser verification, every selected placement must produce an observation
   on its assigned route. Multiple viewports do not count as multiple images.
6. If a required placement is absent or invalid, produce a contract failure;
   never silently return an empty obligation list.
7. Keep ordinary blueprint resource checks for additional declared images.

### Acceptance cases

| Approved slots and placements | Required result |
| --- | --- |
| No image slots | Zero image floor; text-only exemption |
| One valid home slot, configured floor above one | Effective floor one; one visible home image |
| Home image plus case-study image | Global floor satisfied; both routes checked |
| Images only on case-study routes | No invented home requirement; site floor still enforced |
| Same slot referenced twice | Counts once toward the minimum |
| Correct wrappers without image children | Source or runtime failure |
| Comment mentioning a slot | Does not count as rendered media |
| Required local image missing after acquisition | Explicit resource failure |

## 8. T03 — Close the image acquisition-to-render chain

### Files

- `src/oryxenai/jobs/handlers/code_generator.py`
- `core/resource_adapters.py`
- `core/acquisition_validators.py`
- `core/resource_query.py`
- `core/resource_scout.py`
- `core/source_manifest.py`
- `core/generation_orchestrator.py`
- `scaffolds/react-vite-v1/src/components/generated/SharedSystems.tsx`
- `tests/unit/agents/code_generator/test_resource_binding_validation.py`
- `tests/unit/agents/code_generator/test_image_evidence_and_layout.py`

### Resource resolution algorithm

1. Resolve each planned slot to its approved Build Preparation resource record.
2. Use the approved selected candidate first.
3. Validate provider policy, URL admission, download limit, MIME/type, decoded
   dimensions, and usable bytes using the existing adapters.
4. On an expired or unavailable candidate, try approved alternate candidates
   deterministically within the existing acquisition allowance.
5. If the contract permits a fresh provider search, use the existing approved
   purpose and positive/negative query terms. Restrict selection to vetted
   candidates. Do not choose an unrelated image solely because it downloads.
6. Store local bytes and renditions, then record their hashes, dimensions,
   license/attribution metadata, original slot ID, and materialized paths.
7. A policy-required image cannot silently become an empty frame. Exhaust its
   bounded authorized alternatives, then return a resource-specific failure.
8. An optional slot with an approved omission fallback may be omitted. Collapse
   the unused media region and render an intentional text composition.

Do not add a second image client, a random stock-photo URL, runtime hotlinking,
or a model-generated placeholder standing in for an actual supplied project.

### Source context contract

For each route batch, include the exact materialized asset records belonging to
that unit: slot ID, local rendition paths, dimensions, loading policy, approved
alt policy, placement selector, section ID, and `LocalImage` import path.

The trusted component already supports manifest lookup, so prefer:

```tsx
<LocalImage resourceId="slot-hero" alt="" loading="eager" />
```

This is an example of an approved decorative slot, not a universal resource ID
or alt-text policy. Real generated code must use the unit's supplied slot ID and
its approved alt policy. Do not invent `sources` arrays when manifest lookup
already supplies the correct local renditions.

### Source and browser proof

- Preserve the existing image-binding checks and add focused tests for any
  statically valid generated form that they incorrectly reject.
- Require a real image-producing JSX binding; unused imports and wrappers fail.
- Inspect the final `<img>` after the route mounts and after scrolling lazy
  images into view.
- Await decoding with the configured timeout, then require positive natural
  dimensions and a local current source belonging to the receipt.
- Require a nonzero frame, visible ancestor chain, valid crop, and sufficient
  visibility under the existing design realization thresholds.
- Verify that CSS does not hide images behind clipping, opacity, zero height,
  or an overlay. Preserve existing runtime diagnostics rather than introducing
  duplicate checks with different meanings.

## 9. T04 — Make verified success truthful

### Files

- `src/oryxenai/jobs/handlers/code_generator_verification.py`
- `core/finding_policy.py`
- `core/runtime_verifier.py`
- `core/verification_plan.py`
- `src/oryxenai/preview/promotion.py`
- `config/app.native.toml`
- `tests/unit/agents/code_generator/test_code_generator_verification_handler.py`
- `tests/integration/test_code_generator_verification_worker.py`

### Required policy change

Record a decision superseding D-094 only where it permits unverified functional
success. Diagnostic candidate previews remain useful and should remain available.

Set native verification to the strict acceptance behavior. Also remove or
constrain handler branches that could certify functional failures if a different
overlay enables `preview_first_acceptance`. A configuration toggle must never
make page crashes, broken images, absent evidence, or unsafe navigation verified.

Use `normalize_findings()` and `effective_finding_severity()` as the shared
classification mechanism. The runtime branch should always compute:

```python
runtime_diagnostics = normalize_findings(runtime_diagnostics)
blocking_runtime_diagnostics = [
    diagnostic
    for diagnostic in runtime_diagnostics
    if effective_finding_severity(diagnostic) == "blocking"
]
```

Do not add a broad exception that turns a failed verifier into a passed gate.
`AuthorizationFenceError` must always propagate through existing fences.

### Required blockers

- Invalid or stale approved inputs and checkpoint/hash mismatch.
- Missing required source/content/navigation/image bindings.
- Failed dependency installation, type check, or production build.
- Missing or incomplete build manifest and artifact closure.
- Page exceptions, empty application shell, unresolved routes, broken required
  controls, failed required images/fonts, and forbidden runtime requests.
- Missing configured route/journey evidence or a verifier that did not run.
- Required content hidden in reduced-motion mode.
- Failed authorization, stale owner/run binding, storage readback, or promotion.

### Advisory findings

Keep subjective composition, spacing, crop preference within an allowed range,
and polish suggestions advisory unless they violate a concrete approved
functional/design contract. Preserve the existing explicit finding policy; do
not use arbitrary keywords such as “premium” to turn taste into a release gate.

### Evidence and promotion algorithm

1. Bind source checkpoint and candidate identity.
2. Run final source checks against effective projections and the stored policy.
3. Produce a fresh clean build and its content hash.
4. Start a candidate server for that exact artifact.
5. Execute every required journey at the configured release viewports, including
   reduced-motion journeys.
6. Compare actual journey IDs with required journey IDs. A configured check ID
   copied into a report is not proof of execution.
7. Persist browser evidence and diagnostics bound to candidate/build hashes.
8. If required checks fail, enter bounded repair or `needs_attention`.
9. An independently safe but unverified build may receive `candidate_preview`;
   it must not become `active_preview` or consume success entitlement.
10. Upload, read back, and hash-check the accepted immutable artifact.
11. Recheck owner authorization and source currency before atomic promotion.
12. Mark `ready` and finalize success only for that verified promoted artifact.

### Required regression tests

Parameterize native preview-first enabled/disabled. Under both configurations,
assert no promotion for page error, required image failure, no evidence,
missing journey, type-check failure, stale source, and authorization rejection.
Assert that a purely advisory visual observation does not prevent success.
Assert that a failed regeneration retains the prior verified pointer.

## 10. T05 — Make smaller-model generation easier to satisfy

### Files

- `core/generation_prompt_builder.py`
- `core/generation_contract.py`
- `core/generation_orchestrator.py`
- `core/content_compiler.py`
- `core/work_graph_compiler.py`
- `core/source_generation_adapter.py`
- `core/diagnostics.py`
- `core/final_repair.py`
- `prompts/system.md`, `prompts/route_batch.md`, `prompts/route_compose.md`
- `prompts/integrate.md`, `prompts/integration_review.md`, `prompts/repair_source.md`

### Input packet for each owned work unit

Provide only authoritative, relevant context:

1. Operation, work-unit ID, exact owned file paths, and allowed operation types.
2. Current immutable input, plan, resource-ledger, and checkpoint hashes.
3. Route ID/path and section IDs in approved order.
4. Complete approved public content for those sections and its stable content IDs.
5. Actual available shared-component imports and prop signatures.
6. Exact generated design-token names and trusted CSS/motion APIs.
7. Local resources and selected image obligations for the unit.
8. Required section, region, interaction, motion, and resource markers.
9. Existing contents of editable files when repairing.
10. Concrete diagnostics with file, route, owner, expected, and observed values.
11. Output/schema ceiling and the meaning of `changes`, `requests`, and
    `cannot_complete` for that operation.

Do not tell a model to infer project-relative imports, invent unavailable
component props, recompute semantic storage keys, or recreate package files.
The compiler already owns those facts.

### Output acceptance

- Parse the strict response envelope before touching candidate source.
- Check path ownership and trusted-file boundaries first.
- Reject empty/truncated file bodies and unsupported imports.
- Apply complete files transactionally inside the candidate workspace.
- Keep deterministic operation reconciliation limited to the existing repair
  semantics; initial generation must not overwrite unrelated files.
- Type-check the affected candidate and validate its section/content/resources.
- Persist a checkpoint only after the unit's required checks pass.
- Persist failure diagnostics before considering the next serial unit.

### Repair loop

1. Classify the failure as upstream, infrastructure, or generated source.
2. For source failures, identify the owner and smallest complete affected file
   set. Include related interfaces needed to make a valid repair.
3. Build the existing `DiagnosticBundle` from actual source and receipt data.
4. Give the model the required outcome, not an instruction to bypass the test.
5. Consume the existing per-unit and total repair allowance.
6. Validate and apply the response through the same ownership boundary.
7. Re-run affected checks and invalidate dependent quality/runtime evidence.
8. A new accepted checkpoint requires a new clean build before promotion.
9. Stop on no-progress fingerprints, explicit decline, or exhausted allowance.

Prompts must state that missing text cannot be fabricated, a broken image
cannot be fixed by hiding it, and a failed interaction cannot be fixed by
removing its required marker. Repair the behavior while preserving approved
content and public actions.

Bump the relevant prompt-version entry when changing a trusted prompt. Use the
existing receipt/hash mechanism so old prompt evidence is not reused as if it
came from the new contract.

## 11. T06 — Make visual quality intentional and executable

### Files

- `prompts/director.md`
- `prompts/planner.md`
- `core/layout_recipe_catalogue.py`
- `core/motion_pattern_catalogue.py`
- `core/token_compiler.py`
- `scaffolds/react-vite-v1/src/components/generated/SharedSystems.tsx`
- `scaffolds/react-vite-v1/src/design/motion.css`
- `tests/unit/agents/code_generator/test_runtime_verifier_motion.py`
- `tests/unit/agents/code_generator/test_runtime_verifier_region_and_distinctive_move.py`

### Design contract

The director/planner must translate the approved visual direction into:

- A concept tied to the actual profession and strongest evidence.
- Named, concrete color roles, readable contrast, and consistent token usage.
- A display/body type relationship, useful scale, and bounded line measures.
- Route and section composition that varies with the narrative.
- One coherent signature moment, with supporting effects used selectively.
- Image placement/crop choices tied to available local assets.
- Explicit behavior at the existing release viewports and smaller widths.
- A reduced-motion version with all content and controls still available.

Do not introduce a shared hardcoded palette or hero layout for all portfolios.
The frontend-design skill informs these checks: grounded identity, disciplined
surrounding composition, and concept-supporting motion.

### Trusted effects first

Use the existing catalogue for reveals and other supported primitives. If a
brief calls for an effect not supported by a trusted primitive, add a small,
tested primitive only when the effect improves that concept. Do not install a
new animation framework just to satisfy the phrase “advanced effects.”

For any new scroll/pointer/sticky effect:

1. Content starts visible and usable before enhancement initializes.
2. Observer, listener, timer, and animation-frame cleanup runs on unmount.
3. Reduced motion disables displacement/pinning that could hide content.
4. Keyboard users have an equivalent action to pointer-only interaction.
5. Touch or coarse-pointer contexts retain the useful static state.
6. A JavaScript error in decoration must not crash the route.
7. Verification exercises start, changed, and reduced-motion states.

Keep geometry checks consistent with real CSS semantics. Preserve the existing
content-box width fix and abstract-grid interpretation; do not reintroduce
exact-column-count failures already rejected by D-076/D-088.

### Human visual acceptance

Inspect actual screenshots and rendered routes for at least two substantially
different inputs. Confirm readable hero hierarchy, meaningful image placement,
consistent typography, no accidental empty tracks, no repeated generic cards
for every section, and a working signature moment. Record concrete observations.

Screenshot review is acceptance evidence for this engineering campaign. Do not
quietly introduce a production vision-model approval loop; that would be a
separate architecture and cost decision.

## 12. T07 — Repair frontend and session integration

### Files

- `frontend/src/app/AppShell.tsx`
- `frontend/src/app/AppShell.test.ts`
- `frontend/src/data/api-client.ts`
- `frontend/src/data/adapters/generation.ts`
- `frontend/src/data/adapters/generation.test.ts`
- `frontend/src/stages/generation/GenerationStage.tsx`
- `src/oryxenai/agents/code_generator/service.py`
- `src/oryxenai/agents/code_generator/session_schemas.py`
- `tests/unit/agents/code_generator/test_session_service.py`

### A. Separate not-started from inconsistent authorization state

Reproduce `get_state()` for these situations before modifying authorization:

| Session condition | Expected read behavior |
| --- | --- |
| Owned session, no generation run or preview, reservation not yet created | Safe not-started/locked projection |
| Correct reservation and current run | Current generation state |
| Reservation points to another run/session | Binding conflict |
| Session exposes a run without required trusted binding | Binding conflict |
| Other user's session | Access denied |
| Administrator acting through the supported admin boundary | Existing explicit admin semantics |

If absence of an entitlement before generation is the reproduced cause, make
that read explicitly optional only for an empty generation state. Continue
loading and checking any existing entitlement even when the JSON projection
claims no current run. Otherwise a corrupted state could bypass the mismatch
check. Do not weaken start/retry/regenerate ownership or entitlement guards.

### B. Fetch generation only when relevant

In `refetchCurrentSession()`:

1. Fetch session and upstream states using the existing independent requests.
2. Derive preparation readiness from the returned server state.
3. Detect an existing generation binding/preview from the authoritative session
   or a previously confirmed generation state for that same session.
4. Fetch generation when preparation is ready or an existing generation state
   needs restoration. A stale upstream edit must not hide a prior preview.
5. Otherwise use the explicit not-started projection for the locked stage.
6. Calculate connection freshness from requests actually required and attempted.
7. Do not treat access-denied, server errors, and arbitrary 409s as success.
8. Guard results by session identity so a slow response from a previous session
   cannot replace the newly selected session's state.

Preserve the in-progress initial-stage restoration work and its tests.

### C. Truthful preview state

- `active_preview` is verified only after backend promotion.
- `candidate_preview` is visibly unverified even if its iframe loads.
- A failed new run may display the prior verified preview with its proper label.
- A fresh failed run without either artifact shows diagnostics and retry.
- `preview_pending` stays working; it is not the same as `ready`.
- Use backend retry availability, job IDs, milestone, and error codes.
- Do not fabricate portfolio profession/summary defaults for unknown payloads.
- The proposed time estimate must be labeled according to its evidence. A
  configured timeout is an upper budget, not an observed expected duration.
  Preserve other contributors' timing data while correcting misleading copy if
  its focused test reproduces that problem.

### D. Embedded preview behavior

- Build iframe URLs with the existing mounted-route convention, not ad hoc
  concatenation that drops the capability or preview prefix.
- Preserve the origin/source/version checks in the preview bridge.
- Keep the sandbox and CSP restrictions; do not relax them to fix loading.
- Show a useful load failure with retry/open actions if the bridge never becomes
  ready. Do not show indefinite loading after a known terminal failure.
- Route switching, iframe reload, and opening the same route in a new tab must
  all serve the same promoted artifact.

## 13. T08 — Make exports easy to run

### Files

- `core/portfolio_export.py`
- `core/build_runner.py`
- `core/dependency_manager.py`
- `scaffolds/react-vite-v1/package.json`
- `scaffolds/react-vite-v1/package-lock.json`
- `scaffolds/react-vite-v1/README.md`
- `scaffolds/react-vite-v1/src/app/ResourceUrl.ts`
- `scaffolds/react-vite-v1/src/app/AppRouter.tsx`
- `src/oryxenai/preview/gateway.py`
- `scripts/preview-codegen-export.py`
- `tests/unit/agents/code_generator/test_portfolio_export.py`

### Export contract

Retain source, built `dist`, truthful metadata, and the existing generation
report. Include concise run instructions that match actual package scripts.

Source instructions must cover a normal package-manager install from the real
lockfile and the existing build/preview scripts. Confirm the required Node
version against the committed toolchain before documenting it; do not guess a
version. The source must not require application API keys or the application
database just to display the portfolio.

For an already built export, retain the repository's static viewer command:

```powershell
uv run python scripts/preview-codegen-export.py output/code-gen-output/<export-folder>/dist
```

The bracketed directory is an operator-supplied path, not generated source code.
Document that SPA navigation needs an HTTP server with route fallback; opening
`index.html` directly via `file://` is not the supported execution method.

### Verification

1. Export the accepted source and the exact verified artifact.
2. Copy that source to a fresh temporary directory without `node_modules`.
3. Install using the exported lockfile, type-check, and build.
4. Serve the exported `dist` at a root URL and the application preview prefix.
5. Open and refresh every approved route, including a nested case-study route.
6. Confirm actual JS/CSS/image/font assets load at both mounts.
7. Confirm missing asset requests receive 404 rather than HTML route fallback.
8. Check the artifact remains usable with external network requests blocked.
9. Confirm source/metadata contain no local absolute paths or credentials.

Keep toolchain errors distinct from invalid generated code. A Windows spawn
failure goes to preflight/retry guidance, not a model request to rewrite CSS.

## 14. T09 — Variable-brief regression and live acceptance matrix

### Structural cases

| Case | Why it matters | Expected evidence |
| --- | --- | --- |
| Single route, sparse text, no images | No invented sections/assets | Valid readable text-first portfolio |
| Single route, exactly one image | Impossible-floor regression | One real visible local image |
| Single route, multiple images | Ordinary visual portfolio | Policy images decoded and visible |
| Multiple routes with images distributed across them | Scope consistency | Same selected obligations at plan/source/runtime |
| Shared section names on different routes | Identity isolation | Correct per-route semantic owners |
| Long titles and dense content | Layout resilience | No lost/clipped required text |
| Renamed routes and nonstandard section IDs | No home/hero-only assumptions | Exact approved coverage and navigation |
| Nested route and deep-link refresh | Portable routing | 200 page response and valid local assets |
| Expired primary image URL with an approved alternate | Acquisition recovery | Alternate receipt and actual rendered image |
| Optional unavailable resource with omission fallback | Honest degradation | No broken slot or empty image frame |
| Required image unavailable | Truthful failure | Specific error; no verified success |
| Current raw and supported namespaced brief formats | Compatibility | Stable admitted projections |
| Unknown version, modified index/hash, duplicate IDs | Admission integrity | Rejected before model calls |
| Browser crash, missing journey, image decode failure | Promotion integrity | Candidate/attention; no active promotion |
| Worker redelivery during a route batch | Durability and cost | Checkpoint reuse without duplicate logical work |
| Failed regeneration after earlier success | User continuity | Previous verified preview retained |

Use existing checked-in fixtures for deterministic tests. Build fixture variants
with the real producer or a test helper that recalculates valid indexes/hashes.
Do not disable admission checks to get synthetic data through.

### Live campaign

1. Finish deterministic fixes and targeted checks before starting paid runs.
2. Enumerate local Build Preparation outputs through the existing
   `DevelopmentInputAdapter`/development service, and admit each candidate.
3. Choose at least two existing valid outputs with different content hashes,
   content structures, resource placement patterns, and professional domains.
   Prefer including a genuinely multi-route case. Record only safe structural
   metadata in the committed campaign report.
4. Run provider and disposable toolchain preflights with configured profiles.
5. Use normal durable service/API entrypoints and a worker with the matching
   release capability. Do not invoke handlers manually while leaving their
   jobs queued for another worker to claim.
6. Track full-generation attempts separately from model operations, repair
   calls, provider transport retries, and verification-only retries.
7. Bound the campaign to five new full-generation attempts initially. This is
   an engineering test ceiling, not a promise of five provider calls per run.
   If the ceiling is reached, report the remaining failure precisely; do not
   label it successful or continue spending without a new explicit budget.
8. Persist a report per attempt: input hashes, run ID, pipeline/release identity,
   stages reached, call usage, first blocking diagnostic, repair attempts,
   artifact hashes, image observations, and preview status.
9. Reproduce each new failure locally from retained evidence, fix its actual
   cause, and resume only where the immutable contract allows it.
10. Inspect both an embedded preview and its direct URL in a real browser.
11. Review screenshots from the successful different inputs for visual quality.
12. Repeat on the intended Linux/Chromium runtime before claiming deployment
    readiness. Windows acceptance alone is not Azure acceptance.

Do not globally cancel background jobs, reset application data, or overwrite
other contributors' outputs to prepare the campaign.

## 15. Verification commands

Run commands from the repository root unless otherwise stated.

```powershell
$env:OryxenAI_CONFIG_OVERLAY = "config/app.test.toml"
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit/agents/code_generator
uv run pytest tests/integration/test_code_generator_development_worker.py
uv run pytest tests/integration/test_code_generator_generation_worker.py
uv run pytest tests/integration/test_code_generator_verification_worker.py
uv run pytest tests/api/test_code_generator_development_routes.py
npm --prefix frontend run test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Then run the complete backend suite with the same isolated test configuration
before release. If integration tests skip because PostgreSQL is unavailable,
record them as unverified, not passed. If the UV cache is inaccessible, use the
existing project virtual environment directly or a task-specific configured
cache. Do not reinstall arbitrary dependency versions to work around permissions.

In a dirty worktree, distinguish pre-existing unrelated lint/test failures from
regressions introduced by this implementation. Do not silently “fix everything”
outside the task or include unrelated work in the commit.

## 16. Compatibility and rollout

1. Keep the existing brief envelope, supported format dispatch, and production
   session endpoints unless a focused failure demonstrates a required change.
2. The image-policy fix can use the existing fields and policy hash. Do not add
   a database column merely to express site-wide selection.
3. Read older run records. Do not silently reinterpret their stored policy or
   mark past preview-first success as newly verified.
4. Bump prompt versions for changed generation guidance and the worker release
   identity when admission/execution compatibility requires it.
5. Use the existing queue release fence. Do not let a stale worker claim a job
   whose contract it cannot execute.
6. Quiesce relevant work before a release that changes verification semantics.
   Finish or explicitly retry affected runs through the supported service path.
7. Record the D-094 acceptance-policy change with its concrete tradeoff: an
   unverified candidate remains visible, but success now requires evidence.
8. Reconcile task-owned changes, run checks, and select an exact local commit.
   Pushing and production deployment are separate from this repair plan.

## 17. Instructions for the smaller model implementing each task

Use this sequence for every task:

1. Read this task's section and the listed current files completely enough to
   understand their call sites; inspect the relevant Git diff.
2. State the exact invariant being fixed in the task notes.
3. Write or identify a focused regression demonstrating the broken behavior.
4. Make the smallest coherent change at the authoritative boundary.
5. Update every consumer of the changed semantic contract in the same unit.
6. Reuse existing types, diagnostic codes, helpers, receipts, and settings.
7. Do not invent a field, endpoint, prop, or enum; inspect its declaration first.
8. When a needed helper is new, define its complete input/output contract and
   ensure all callers pass the same representation.
9. Run the focused test, then affected tests and required static checks.
10. Inspect the diff for policy weakening, lost content, unauthorized path edits,
    changed source hashes, accidentally exposed credentials, and unrelated work.
11. Record the implementation and verification evidence without claiming live
    acceptance from fixture tests.
12. Stage only task-owned files/hunks, review the complete staged patch, run
    `git diff --cached --check`, and create the required local commit.

Do not change tests to bless broken runtime behavior. Do not add arbitrary
“make it work” replacements for a missing required image, content section, or
interaction. Deterministic helpers are appropriate for known IDs, paths,
resource selection, trusted rendering primitives, and contract calculation;
they must not fabricate a person's portfolio facts.

## 18. Definition of done

The repair is complete only when all of the following are evidenced:

- Feasible image floors and the same site-wide obligations at planning,
  source validation, and runtime verification.
- Missing/failed required images cannot become verified success.
- Different valid brief structures pass the regression matrix.
- At least two structurally different real Build Preparation outputs produce
  fresh live portfolios that pass strict required verification.
- Rendered pages show intentional visual direction and functioning motion,
  with reduced-motion readability.
- Embedded and direct preview routes work for the promoted artifact.
- Exported source builds independently and exported `dist` serves its routes.
- Genuine authorization conflicts still fail closed.
- A failed regeneration preserves the previous verified preview.
- Model attempts and repairs remain bounded, persisted, and resumable.
- Relevant tests/static checks pass; unavailable checks are reported explicitly.
- Task-owned work, decisions, and verification evidence are committed locally.

The final implementation handoff must report what changed, which inputs were
exercised, what browser/build evidence exists, any unresolved limitation, the
local commit hashes, and the remaining unrelated worktree changes. Until these
criteria are met, describe the result as partial implementation or an unresolved
failure rather than a fully fixed generator.
