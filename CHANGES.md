# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-11 03:07 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [c8c9333] - fix(visual-design-director): inline the missing content_ref rule for single-route pages

User-reported: Visual Design Director's `MODEL_OUTPUT_INVALID` ("did not
satisfy the required structure") kept recurring, specifically on this
agent and no other. Live-reproduced end-to-end (Discovery -> Content
Architect -> Visual Design Director, real resume input, real model calls,
bypassing the redacted worker error envelope to read validators.py's raw
errors directly): `establish_visual_language.md`'s `pages_when_included`
path -- mandatory whenever pages_included=true, which the prompt itself
requires for every single-route/simple-hybrid portfolio -- only
cross-referenced `direct_page_experience.md`'s asset `content_ref` rule
("exactly ONE bare section_id, never joined with a separator") instead of
stating it inline. `prompt_builder.py` never actually loads that other
operation's file for this call, so the model never saw the rule and
produced `content_ref: "home:hero; home:positioning"`, which
`validate_final_references` correctly rejects as an unknown content_ref
with no repair path (unlike Content Architect, VDD's `agent.py` has no
corrective re-call on its own final-validation failure). Inlined the rule
into `establish_visual_language.md` and bumped its prompt version;
re-verified live against the same captured Content Architect output that
failed before the fix, twice, both succeeding with single-value
content_ref. The Content-Architect-style repair-call pattern remains a
candidate follow-up if this class of failure recurs for a different field.

### 2026-09-11 02:10 +05:30 - Codex (GPT-6 / OpenAI) - [67d5a75] - fix(agents): restore rich first-four output and bounded Gemini recovery

Updated Discovery, Content Architect, Visual Design Director, and Build Preparation prompts to use ordinary supplied material fully and emit complete adaptive-detail handoffs while preserving explicit restrictions and security guardrails. Routed the first four stages through EXPLABS-first recovery with one same-packet Gemini fallback for provider and structural failures, added route/section/scene completeness gates, and recorded D-093.

### 2026-09-11 00:40 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [no commit; investigation only] - docs(code-generator): close D-090's follow-up, disprove a suspected `_route_source_map` double-hash bug

Live-testing D-092's image-policy fix (run `74c82e9d`, Priya Vasudevan
pack) surfaced what looked like a real instance of D-090's deferred
storage-key risk in `final_source_validation.py::_route_source_map()`. A
fix was written and applied, then traced variable-by-variable against the
real projections and found to be based on a false premise -- the
function's actual input never carries a pre-semantic storage key, so the
original unconditional logic was correct all along and consistent with its
two siblings (`work_graph_compiler.py`, `source_manifest.py`). Reverted;
`final_source_validation.py` matches HEAD exactly, nothing to commit. The
real, confirmed remaining gap is a model-output completeness defect (a
planned image placement whose `<LocalImage>` was never rendered), not a
validator bug. Full trace in `code generator issues.md` and D-090's
follow-up in `DECISIONS.md`.

### 2026-09-10 23:19 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [01e9ed0] - fix(code-generator): name the exact empty field in quality-finding validation errors

Live run `b3e9c620` (Priya Vasudevan pack) failed `GENERATION_OUTPUT_
INVALID` on both attempts of the bounded integration-review schema-
correction retry because `QualityFindingV2`'s validator only named the
rule, not which of its seven required fields was actually blank, leaving
the model nothing concrete to fix. The validator now names the exact empty
field(s); added a regression test.

### 2026-09-10 22:52 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [882574e, 1563282] - fix(code-generator): require at least the preferred image count by default

User-reported: images never appear in generated portfolios. Traced across
3 live runs: Build Preparation researches and vets real image candidates
correctly every time, and they reach execution/contract.json intact --
but with minimum_visible_images=0/require_primary_route_image=false, the
planner had a purely soft "preferred, not a release gate" instruction and
declined all 21 opportunities across those runs. Raised the defaults to
2/true (D-092) so "preferred" becomes an enforced floor; the zero-slot
exemption path is untouched. Not yet live-confirmed.

### 2026-09-10 19:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [11a8fe3] - docs(code-generator): close campaign B with a ready result

Campaign-B slot 5 (Pack A, run ff3398b1), the last slot in the shared
5-run budget, reached `ready` with zero blocking diagnostics across all
three verification gates. Verified beyond DB status: the promoted preview
was loaded in an actual browser, confirming real content in every
section, working navigation, zero console errors, all resources 200, and
`dist/index.html` present. No new code fix was needed -- this confirms
slots 1-4's four fixes (22db99c, d9caf30, e7d9284, 06eb2c0) together.
Campaign B is now closed (5/5 consumed, 1 ready).

### 2026-09-10 18:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [06eb2c0] - fix(code-generator): resolve real color tokens in the selected-work lifecycle normalizer

Campaign-B live slot 4 (Pack A) exhausted its repair budget on three
SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND diagnostics, all from d9caf30's
deterministic lifecycle-cue normalizer hardcoding assumed color token
names (`--color-ink-secondary`/`--color-border-subtle`/`--color-accent-
signal`) that don't exist in this run's actual generated tokens -- color
names are chosen per run by the model, never fixed. Added
`_resolve_existing_color_token()` to look up real tokens by semantic
keyword instead, degrading gracefully when none resolve. Verified 3 → 0
undefined references against the exact rejected run. Slot 4 consumed, no
ready result; 1 slot remains.

### 2026-09-10 17:28 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [e7d9284] - fix(code-generator): recognize trusted motion patterns in the final source audit

Campaign-B live slot 3 (Pack A) rejected a correct, trusted `<Reveal>`-based
hero motion beat because `typescript_ast_audit.py`'s final V4 motion-beat
check, unlike `source_validation.py`'s pre-gate and the route-motion
normalizer, had no exception for catalogue `pattern_id` beats and demanded
CSS/reduced-motion evidence that legitimately lives in `SharedSystems.tsx`/
`motion.css` instead. Mirrored the existing exception; verified 2 → 0
diagnostics against the exact rejected checkpoint. Slot 3 consumed, no
ready result; retrying Pack A for slot 4.

### 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [6c22712] - fix(code-generator): repair the verification regression test's route-path mismatch

Traced five stray `output/code-gen-output/` folders (zero model calls each,
per `portfolio.json`) to one broken integration test,
`test_verification_builds_and_promotes_a_clean_candidate`, left incomplete
across a Claude Code -> Codex -> Claude Code handoff. Root cause: the test
hand-wrote its "real" route content to an invented path
(`src/routes/home-4ea140588150/`) unrelated to the route's actual bare
storage key (`home`), so the router-wired placeholder the scaffold writer
creates was validated instead. Fixed the path, added a real `<nav>` landmark,
and added the closed-navigation-contract anchors the admitted fixture
requires; the test now passes end to end (build, DOM/runtime verification,
screenshot capture, promotion). See D-090.

### 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [fd9669d] - fix(code-generator): surface the real issue code in terminal-failure/export evidence

`code_generator_verification.py`'s `_execute()` early-failure branches
(raised before a `VerificationProjection` exists) returned no `"code"` key,
so a real issue code (observed live as `PLAN_SECTION_COVERAGE`) was masked
as the generic `"needs_attention"` status in exported `portfolio.json`
evidence. Added the real code to both branches; new regression test asserts
it survives into `terminal_failure.code`/`evidence_summary.primary_issue.code`.
See D-091.

### 2026-09-10 14:43 +05:30 - Codex (configured runtime) - [d9caf30] - fix(code-generator): materialize selected-work lifecycle cue

After live Pack A slot 2 reached verification but was rejected for the
blueprint-required selected-work lifecycle cue, added an idempotent host-side
materializer for the sparse `observe`/`shape`/`deliver` treatment. It is scoped
to the admitted v4 lifecycle thesis and leaves approved content, images, and
dist/export behavior unchanged. The targeted suites passed 139 tests and the
exact saved slot-2 tree passed source audit and typecheck in a disposable
overlay.

### 2026-09-10 14:00 +05:30 - Codex (configured runtime) - [22db99c] - fix(code-generator): normalize route motion contract drift

After live Pack A exposed deterministic CSS-length and route-motion contract
drift, added host-side normalization for spelled CSS lengths, trusted selector
anchors, custom-motion guard/fallback CSS, and exact observer wiring. The
targeted suites and direct Pack A route-contract replay passed; the bounded
campaign records the live failure separately.

### 2026-09-10 12:00 +05:30 - Codex (configured runtime) - [68e1693] - fix(code-generator): reconcile repair-budget defaults

Aligned the Code Generator Pydantic repair defaults with the effective
`config/app.toml` policy (2 per unit, 4 total, 3 integration-polish rounds)
and documented D-089's deliberate retention of the unused `repair_depth`
field. The change keeps repair bounded based on the evidence from the prior
five-slot campaign rather than raising limits for distinct root-causable
defects.

## Compacted history

### 2026-09
- 2026-09-10 — [39076d0] — Refreshed stale image pins by stable asset ID and hardened dist exports against partial/retry failures on Windows.
- 2026-09-10 — [7a01ee9, 3f07609, f1e74d3, 40434cf, ed21a6a, c3fabdc, 5eca499] — Closed desktop generation reliability gaps (preview/export, source/interaction ownership, contract ordering, static content-map, conditional-motion audit) from the five-run campaign.
- 2026-09-10 — [90e8349] — Fixed fluid type-step token double-prefixing (`--type-type-heading-*` -> `--type-heading-*`) at the schema/compiler boundary.
- 2026-09-09 — [9716681] — Caught inert disclosure panels (aria-hidden empty content) as a host-owned source diagnostic; aligned `columns_*` review guidance with D-076.
- 2026-09-09 — [4da1ddb] — Made toolchain preflight cleanup best-effort so a Windows enumeration denial can't discard a valid toolchain proof.
- 2026-09-09 — [14bb97c, c8a66e7, 80a925c] — Replaced keyword-based severity inference with explicit host-owned quality findings; Pack C stopped honestly at `INTEGRATION_REVIEW_UNRESOLVED`.
- 2026-09-09 — [a503a4a] — Implemented the Code Generator reliability plan: pending-proposal completion, serial attempt accounting, hashed image obligations, marker-bound layout recipes, toolchain preflight, truthful atomic exports (D-0XX, R01-R12 in `code generator issues.md`).
- 2026-09-09 — [66d8287] — Authored a 6-document frontend/agent integration reference suite under `docs/frontend/` for the major frontend revamp.
- 2026-09-09 — [59409b5] — Fixed `run-worker.ps1` to use a writable repo-local `uv` cache instead of a lockable global one.
- 2026-09-09 — [2f424e5] — Hardened brief-driven Code Generator: brief-mirror admission, planner retry/canonicalization, npm import scanning, host-owned quality findings, unverified-preview candidates, npm cache warmer, Azure VM Docker wiring.
- 2026-09-09 — [78a9c77] — Retired the temporary static Discovery/pipeline shell; `/app` now requires the manifest-selected Preact bundle.
- 2026-09-09 — [bc7b5a6] — Added an administrator-only pipeline reset capability (full session reset back to Discovery, admin-audited).
- 2026-09-09 — [f20779f] — Clarified planner guidance distinguishing a brief's design-language words from literal `colors[*].name` tokens after a live naming collision.
- 2026-09-09 — [051afa6] — Added undeclared-npm-import detection via source scan for pinned/deferred components, closing the empty-`dependency_metadata` gap.
- 2026-09-08 — [a2ae087] — Checked in Azure production Compose/Caddy/TOML deployment overlays matching the VM runbook.
- 2026-09-08 — [2790e9d] — Released the authenticated Generate & Preview stage with the promoted-preview iframe bridge and Build Preparation gate (D-081); detailed history remains in Git.
- 2026-09-09 — [e99ed55] — Investigated five failed Code Generator runs and authored the implementation and five-slot campaign handoff for pending retention, accounting, visual quality, truthful exports, and preflight.
- 2026-09-09 — [29fc598] — Reconciled stale `create`/`replace` repair tags against the owned candidate tree while preserving strict initial-generation semantics and bounded repair authority.
- 2026-09-08 — [44304ff] — Added honest repair-decline handling, shared-cause runtime correlation, stable prompt-cache keys, tighter observed repair ceilings, and a dedicated Code Generator job-attempt policy.
- 2026-09-08 — [ddc2e77, 3a6cf25, b07582d, 7f2fbd0, 9d256f3, d6b6777, bb7078b, 5731cf5, 78eacc7] — Completed Build Preparation/frontend handoffs, safe output copy and cache behavior, provider-neutral routing, scoped telemetry, and false-identity/preflight handling; detailed history remains in Git.
- 2026-09-07 — [7f09506, 5bef169, ac5543e, 3f5b2aa, 78117e7] — Added candidate previews, corrected live repair and export behavior, and closed scaffold/toolchain and generation-time authoring gaps.
- 2026-09-06 — [446d4c7, 87f97f4, 7578b9a, f7546d4, 6707cce, 5768ce7, 618a038, fa9be97, f208540, ebfbc94, cdf8952, 1956d58, 7c94916, 83179f3, ae89b61, 68f1cd1, 861e981, cdf7a18] — Fixed Code Generator/runtime issues, delivered frontend studio/auth/output work, and hardened agent job lifecycle and cancellation.
- 2026-09-05 — [903477a, a2a8a60, 963375b, 7a0c68f, caa8f33, 34c638b, d6cde91, 8a2066a, 5b86779, aedf96c, 0ce8ecd, 9fabd58] — Completed deployment/auth foundations, provider budgets/caching, resource and repair fixes, motion patterns, and canonical output cleanup.

---

## Compaction Procedure & Template (for AI Agents)

**Trigger:** If `CHANGES.md` reaches or exceeds **250 lines**, compact older entries before appending new work.

**Procedure:**
1. Keep the most recent **15–20** entries intact under `## Recent changes`.
2. Move older entries into consolidated single-line milestone bullets under `## Compacted history -> ### YYYY-MM`.
3. Recompute the `## Summary` block below.

**Entry Template (Copy verbatim for new entries, insert directly below `## Recent changes`):**

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — [<commit-sha>] — <files/areas, comma-separated>
<One or two sentences: what changed, why, and related ADR references (e.g. D-0XX).>
```

---

## Summary (as of last compaction — 2026-09-11)

- Recent detailed entries retained: 13
- Compacted milestone bullets: 23
- Last updated: 2026-09-11 03:07 +05:30 — Claude Code (Sonnet 5 / Anthropic)
