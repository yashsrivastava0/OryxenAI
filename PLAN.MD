# Build Preparation Revamp: Decide Upstream, Materialize Downstream

## Who you are and what this is

You are picking up an architectural change to OryxenAI's Build Preparation
and Code Generator agents, approved after a live-evidence investigation.
Read this file fully before doing anything — it supersedes all prior
versions of this file. Focus is split but ordered: **primarily Build
Preparation's output contract, with the Code Generator changes needed to
consume it; a secondary track of already root-caused Code Generator bugs
runs alongside.** This is a live, multi-session handoff, not a one-shot task
— do solid, verified work and stop at a genuine stopping point.

**The three goals, unchanged throughout this whole project:** (1) Code
Generator completes a real generation without error, (2) the generated
portfolio has zero build/runtime/console errors, (3) the output looks
genuinely modern and distinctive — never generic "AI template" output.

## What has already been done — do not redo this

Run `git log --oneline -20` on `codex/code-generator-control-room` and read
`CHANGES.md`'s newest entries first. Two prior live-evidence rounds already
happened:

1. **7 bugs fixed via live runs** (commits `375aae3` through `20f72e2`) —
   image usage-contract plumbing, a `_redirects` file for static-host
   deep-linking, a repair-budget short-circuit on a model's honest
   `cannot_complete`, its `repair_rounds` undercount follow-up, a
   `ShadowTokenV4` sign-constraint bug, a duplicate-`@font-face` compiler
   bug, and a `SourceValidationError` retry-loop gap.
2. **A 10-run live campaign** (Codex/Luna, 2026-09-02, documented in full at
   repo-root `code generator issues.md`, commit `efca5de` — read it) found
   0/10 runs reached `ready`. The historical blocker pair from round 1
   (`BLUEPRINT_ANTI_PATTERN_REPEATED_SPLIT` + `MOTION_TARGET_PROPERTY_MISMATCH`)
   did **not** recur (0/10) — confirmed one-off, not systemic, drop it. All
   10 runs failed on a long tail of *other* issues instead.

**A third round (this session) root-caused those 10 failures against real
code**, not just the report's own text, and found:

- Code Generator's planner (`development_planner.py:34-70`,
  `build_planner_context`) reads only 6 narrow, schema-validated files. It
  never reads `handoff-report.json` or `handoff-analysis.json` — so a
  "pack too complex for the planner" theory is **not** what's failing these
  10 runs; the bloat never reaches the model.
- Every one of the 10 failures traces to a specific, already-found bug —
  see Track 2 below for exact file:line references. Don't re-diagnose these
  from scratch; go read the code at the given locations and fix.
- The pack **is** genuinely bloated in confirmed, measurable ways (a 129KB
  file that's a byte-for-byte duplicate of data already in a sibling file,
  arrays written 3-4 times, two architecture docs disagreeing about what
  files even exist). This is real, and Track 1 below fixes it — just don't
  mistake it for the cause of the 10 current failures.
- Code Generator **already has** a complete, live, real resource-acquisition
  subsystem (`resource_adapters.py`, shared provider clients for
  Pexels/Pixabay/Unsplash/Fontsource/Lucide/shadcn/magicui/smoothui/cultui)
  — it just only fires today for the rare slots Build Preparation leaves
  as an explicit gap. Track 1 widens this into the normal path; nothing
  needs to be invented from scratch.

## Track 1 — Build Preparation / Code Generator handoff revamp (primary)

**The decision:** Build Preparation keeps 100% of the resource *decision*
authority (search, rank, license/policy check, pick exactly one winning
candidate — its real, hard, valuable work). What moves downstream is only
*fetching the bytes*. Instead of downloading and embedding image/font/
component bytes, Build Preparation emits a compact, fully-pinned reference
to the resource it already decided on (provider, candidate id, license/
attribution, and every `usage_contract` field the planner needs — alt text,
focal point, placement, aspect ratio, dependency list). Code Generator's
existing acquisition adapters — already live for gap-slots today — fetch
that one already-decided resource's bytes at generation time. No
search/selection happens on Code Generator's side for these slots; the
decision was already made. This is a real, partial revision of decision
D-018 (which rejected "arbitrary web/URL fetches by Code Generator") — the
distinction that makes it not a violation: D-018 protected against Code
Generator ever *inventing or guessing* a resource decision, and this design
still guarantees that; only *when the bytes get fetched* changes. Log this
distinction explicitly as its own new decision entry (current highest is
D-059 as of this writing — verify by reading `DECISIONS.md` yourself before
assigning a number, other contributors add entries concurrently), not a
silent rewrite of D-018.

Steps, in order:

1. **Pin the reference schema.** Add a new `resolution_type` (e.g.
   `deferred_materialized`) distinct from the existing `delegated_acquisition`
   — the existing type still implies Code Generator may need to *choose*
   among candidates; this new one carries an exact, already-chosen
   candidate with zero ambiguity. Don't blur the two. Apply consistently
   across images, fonts, components, and icons.
2. **Build Preparation stops materializing bytes by default.**
   `src/oryxenai/agents/build_preparation/materializer.py` —
   `_materialize_image_candidate` (~491-678), `_materialize_component_candidate`
   (~314-403), font/icon blocks (~1389-1443/1572-1579). Keep all
   search/rank/license/policy logic; replace the download-and-write step
   with emitting the pinned reference. Keep a cheap existence check (HEAD
   request, not a full download) so a decision is never handed off
   already-dead.
3. **Code Generator accepts and fetches pinned references.**
   `development_input.py` (~807-822, 956-968) currently hard-rejects any
   photo/component that isn't already a materialized local file
   (`PACK_RESOURCE_NOT_REAL` / `PACK_VISUAL_RECIPE_FORBIDDEN`) — extend it
   to accept the new resolution type. `code_generator.py`
   (`_execution_resolved_slot_ids` ~1272-1281, `_build_delegated_requests`
   ~1437-1515) — for the new pinned case, call the adapter's
   `materialize()` directly (skip `search()`/selection, there's no
   ambiguity to resolve). Verify rate-limit handling scales when this is
   most/all resources, not a rare few. Reuse as-is, no changes needed:
   `resource_adapters.py`, `acquisition_validators.py`,
   `shared/image_retrieval.py`, `shared/component_retrieval.py`.
4. **Delete the confirmed duplication** (independent of steps 1-3, can
   happen anytime): stop writing `handoff-analysis.json`
   (`materializer.py:1780-1786`, confirmed byte-for-byte duplicate of
   `handoff-report.json`'s `run_analysis` field); stop triple/quadruple-
   writing the qualifications and materialized-resources arrays across
   `handoff-report.json`/`handoff-analysis.json`/`resources/manifest.json`/
   `resources/projection.json`; fix the doubly-nested
   `provider_receipt.provider_receipt` key; fix the `execution_gaps`
   inconsistency (populated in `execution/contract.json`, empty `[]` in the
   sibling `handoff-report.json` field for the same fact).
5. **Reconcile the architecture docs** — `docs/code-generator-architecture/
   README.md`, `generation-pipeline.md`, `selected-build-preparation-output.md`
   currently name three different, disagreeing file lists for the same
   pack (`generation-pipeline.md` even references files that don't exist,
   `resources/plan.json`/`provenance/sources.json`). Make them agree, and
   reflect the new reference shape.
6. **Investigate the empty creative-intent fields** — `must_preserve`,
   `must_not_fabricate`, `navigation_direction`, `shared_visual_systems`,
   `interaction_system`, `compiler_handoff` are empty in the real committed
   pack (`design/visual-direction.json`). Root-cause whether this is a
   Visual Design Director prompt gap, a Build Preparation passthrough bug,
   or legitimately optional before editing anything on spec.
7. **Live-verify.** Native stack only (`.\scripts\run-native.ps1 dev`), real
   `gpt-5.6-luna` calls, no mocks. Check pack eligibility first
   (`GET /api/v1/development/code-generator/build-preparation-packs`, packs
   expire ~3 days). Confirm the new pack is measurably smaller and the
   duplication is actually gone. Run Code Generator against it end-to-end;
   confirm admission accepts the new resolution type and bytes actually get
   fetched at the right time. On any failure, read the worker process's
   own stdout for the real traceback — every bug found across all three
   rounds of this project was only visible there, never in the API
   response alone.

## Track 2 — Concrete Code Generator bugs, already root-caused

Independent of Track 1, needed regardless for pillars 1/2. Each has a
confirmed file:line cause from this session's own code reading — go verify
and fix, don't re-diagnose from scratch:

1. `TypographyBindingV4.body_line_height` (`development_schemas.py:1011-1027`)
   applies the same `ge=1` floor to both `body` and `display` roles, but
   tight display/headline line-heights below 1.0 are normal, desirable
   editorial typography. Needs a role-aware bound.
2. `_CSS_MEDIA_DIMENSION_RE` (`development_schemas.py:799-819`) truncates at
   the first whitespace, so a spec-correct `calc()` expression with
   required internal spaces (e.g. `calc(40rem + 2px)`) gets misparsed and
   rejected as invalid CSS when it isn't.
3. Unscoped `data-content-id` runtime selectors
   (`runtime_verifier.py:376-382, 815-818, 943-947`) conflate the one
   section-level anchor the static contract enforces with different,
   nested per-copy content-key markers (`SectionRegionV4.content_ids`) that
   share the same attribute name. Needs a distinct attribute name for the
   nested markers, or runtime queries scoped to known section-shell
   elements only.
4. Column-count check (`runtime_verifier.py:968-974`) does literal
   `grid-template-columns` track counting against a model-chosen "columns"
   number `planner.md:41` never defines as "must be literal CSS grid
   tracks" — legitimate non-grid or responsive implementations fail by
   construction. Pick deliberately: tighten the contract's stated meaning
   (lower risk, less layout freedom) vs. loosen the check (harder, keeps
   pillar-3 creative freedom) — weigh against pillar 3, don't default
   silently.
5. Navigation selector (`verification_plan.py:164-183`,
   `runtime_verifier.py:657-666`) requires `[data-navigation-target="..."]`
   — confirmed via repo-wide grep that no prompt or generation-contract
   code ever tells the model to emit this attribute
   (`generation_contract.py:266` always assigns `data-interaction-id`
   instead). Prefer fixing the verifier to resolve navigation via the
   interaction's existing `data-interaction-id` + route-target matching,
   over adding new required markup surface.
6. Font-load check (`runtime_verifier.py:1072-1093`) calls
   `document.fonts.check()` with no preceding `await document.fonts.ready`
   — a known race. Secondary: the display-role font selector is hardcoded
   to `h1, h2, h3` (`design_realization.py:111-120`) with no way for the
   model to say which element actually carries display treatment.
7. After 1-6 land, use live runs (not blind prompt edits) to see how many
   remaining quality-review findings (content copy retyped, distinctive-
   move ratios, typography weight not realized, resource aspect ratio not
   enforced) persist — several may be downstream noise from the same
   selector/timing bugs rather than independent generation defects.

**Do not re-fix these 8 pre-existing, unrelated test failures** (confirmed
present in old commits, verified via stash-isolation to have nothing to do
with any prior fix): `test_session_service.py` (2 tests,
`creative_direction["variant_receipt"]` is `None`), test-order pollution
across `test_materializer.py`/`test_component_retrieval.py`/`test_providers.py`
(6 tests, shared rate-limit/cache state bleeds across test files run
together), and `test_settings_worker.py`/`test_settings.py` (pool_size
config vs. test mismatch).

## Ground rules (unchanged for this entire project)

- OpenAI `gpt-5.6-luna` only, via `OPENAI_API_KEY`. Never another model or
  provider, never change this.
- Never change the numeric ceilings `max_repair_rounds_per_unit=3`,
  `max_repair_rounds_total=6`, `max_integration_polish_rounds=3`.
- No Docker, anywhere, ever, for this work.
- No vision-model or screenshot-based quality gates in the automated
  pipeline, ever — rejected repeatedly and explicitly (D-015, D-032, D-034,
  D-036). A one-time manual Chrome-browser look at a finished run is a
  different, acceptable thing.
- Never silently substitute a different resource than what was decided —
  when a pinned reference fails to fetch at generation time, surface a
  specific diagnostic; don't silently swap in a different image/component
  (this reintroduces exactly the "stock substitution for evidence" risk
  D-018 was written to prevent).
- Bounded effort: if the same class of failure recurs after 2 focused
  attempts, stop and report exactly what was tried and seen.
- One commit per fix, immediately followed by a separate `docs(changes)`
  commit matching `CHANGES.md`'s template. Check `DECISIONS.md`'s actual
  current highest `D-0XX` by reading the file directly — its compacted
  summary footer is stale and undercounts. Identify yourself accurately in
  commits/changelog/decisions — don't claim to be a different tool/model
  than you actually are.
- Never `git push --force`, amend, rebase, or `reset --hard` on existing
  history. Never `git add -A`/`git add .` — this tree has multiple other
  contributors' concurrent changes (a frontend/auth workstream currently
  touches many files); stage only the exact files your fix touches. Run
  `git status`/`git diff` before assuming a file's state.
- Never touch `.env` directly, `test_anthropic_key.py`, or
  `test_openai_key.py`.
- This file (`PLAN.MD`) is the real cross-tool, cross-session handoff
  document — keep it current and **commit it** after any substantive edit;
  it was previously found sitting uncommitted for several sessions with its
  real content only in the working tree, one `git checkout` away from being
  silently replaced by a stale, unrelated document still sitting at HEAD.
