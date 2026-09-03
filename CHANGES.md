# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-03 11:35 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [13cc78b] - stop Build Preparation packs from expiring in practice

D-009's 3-day TTL existed to bound storage cost/cleanup for packs that embedded real image/font/component bytes -- D-060 made packs compact references instead (measured 68KB, down from 1.1MB), so the original rationale is now largely moot, and the TTL had repeatedly forced regenerating a pack mid-session purely to keep testing. Raised `bundle_ttl_days` from 3 to 36500 (100 years) in `config/app.toml` and its Pydantic default -- all existing enforcement (`PACK_EXPIRED`, `BUILD_PREPARATION_ARTIFACT_EXPIRED`, the packs-listing eligibility computation) is unchanged code; only the configured horizon moved. Recorded D-061 as a partial revision of D-009. 925 unit tests pass; ruff/mypy clean.

### 2026-09-03 11:15 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [6bd8a2d] - land deferred resources at their planned pack path

A resumed live run reached generate and hit `FOUNDATION_SOURCE_CHECK_FAILED` -- a third real bug from this same D-060 pass, and a genuine gap in Track 1 itself. `write_generated_tokens` compiles `generated-tokens.css`'s `@font-face` rules directly from `plan.execution_bindings.local_paths`, correctly assuming a `resources/...` path already sits under `public/resources/pack/...` because Build Preparation shipped the bytes and `materialize_pack_resources()` copied them there verbatim -- but `materialize_acquisition_resources()` (which places bytes Code Generator itself fetches) always wrote to a hash-named `acquired` destination that nothing upstream ever referenced, so a deferred font's compiled CSS pointed at a path that didn't exist. Added `_intended_pack_paths_by_candidate()` (looks up a receipt's matching `deferred_materialized` slot by `(provider, candidate id)`) and `_matching_intended_path()` (pairs a materialized file to its one intended path, or by filename-suffix for a multi-file resource like a font's four weights); a resource with no matching slot (genuine emergent/delegated discovery) keeps the prior hash-named fallback, unchanged. Updated both call sites (initial generation, repair-round restore) to pass the execution contract through. 3 new tests; 925 unit tests and 12 integration tests pass; ruff/mypy clean.

### 2026-09-03 03:20 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [c3597d5] - fetch real bytes for deferred resources, not metadata

First live end-to-end test of Track 1 (D-060) against a genuinely fresh deferred_materialized pack surfaced two real bugs, neither reachable by unit tests: (1) `execution.py`'s `_local_paths()` listed a resource's bare directory alongside its file paths, then sorted the result — since a directory always lexically sorts before its own children, the model's font-file reference (correctly copied from the first `local_paths` entry) got the directory instead of a `.woff2` file, tripping the WOFF/WOFF2 validator. Fixed by filtering out any path that's a strict parent of another path in the same set. (2) The deferred reference only carried `source_reference` (a human-readable page/registry URL) but `ImageAdapter`/`FontAdapter`'s generic fetch path downloads `canonical_source` directly as file bytes, and `ComponentSourceAdapter` only takes its registry-aware path when specific metadata is present — acquisition was trying to download a Pexels *page*, a Fontsource *API* response, and treating a component registry's raw JSON as source text (failing the remote-code safety check on the JSON's own `$schema` URL). Added `ResolvedResource.direct_source_url`/`direct_source_urls`, populated from the exact URLs Build Preparation's own download already verified, and wired into `_build_deferred_requests`'s candidate construction. Verified directly: all 8 deferred resources (6 Pexels photos, 1 MagicUI component, 1 Fontsource font) now materialize real bytes matching the pre-D-060 pack's file counts/sizes. 922 unit tests pass; ruff/mypy clean.

### 2026-09-03 03:15 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [b132a9a] - reconcile Build Preparation pack contract docs

`README.md`/`generation-pipeline.md` now describe `deferred_materialized` as a normal, concrete resolution alongside local files/package bindings/recipes, not an emergent-acquisition edge case. Fixed `generation-pipeline.md`'s "representative layout" referencing two files that don't exist in real output (`resources/plan.json`, `provenance/sources.json`) and added `execution/contract.json`, which was missing entirely despite being central to admission. `selected-build-preparation-output.md` documents one specific checked-in fixture that predates D-060 (genuinely `local_materialized`) — added a scoping note rather than rewriting its accurate description of that pack's real committed content.

### 2026-09-03 03:00 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [7fb421f] - remove confirmed duplication in the handoff report

Stopped writing `handoff-analysis.json` (confirmed byte-for-byte duplicate of `handoff-report.json`'s own `run_analysis` field) and dropped the `analysis_path`/`analysis_hash` fields it was the only writer of. Trimmed `run_analysis` itself to drop four keys (`candidate_qualifications`, `materialized_resources`, `role_failures`, `code_generator_eligible`) that duplicated `HandoffQualityReport`'s own top-level fields verbatim, keeping the genuinely unique diagnostic content. Fixed a real doubly-nested `usage_contract.provider_receipt.provider_receipt` bug across the image, image-alternate, and component-alternate materialization paths — one code path unwrapped `retrieval_metadata.get("provider_receipt", {})` correctly, three others assigned the whole `retrieval_metadata` dict instead. Investigated the `execution_gaps` field looking populated in one file and empty in a sibling — confirmed intentional (an existing comment already explains Code Generator's admission check requires the report's top-level list filtered to blocking gaps only), left unchanged. 104 Build Preparation unit tests pass (1 updated); 920 unit tests and 15 related integration tests pass; ruff/mypy clean.

### 2026-09-03 02:35 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [1c175c6] - fetch bytes for deferred_materialized slots in Code Generator

Added `_build_deferred_requests` in `code_generator.py`: translates each `deferred_materialized` execution slot into a `ResourceRequest` paired with a fully-specified `ResourceCandidate` built directly from Build Preparation's pinned decision — no query to guess, no candidates to rank. `_execute_acquisition`'s main loop now skips `search()`/policy filtering/selection entirely for a request with a pinned candidate and calls `adapter.materialize()` directly, reusing the same adapters already live and tested for gap-slots. New `tests/unit/jobs/handlers/` directory (matches the project's own unit-test convention for pure, DB-free logic) covers request shape, category mapping, dependency metadata, and slot filtering. 920 unit tests, 12 code_generator integration tests, 1 worker test pass; mypy clean across all 216 source files. This completes the Track 1 core mechanism from D-060 — Build Preparation decides, Code Generator fetches.

### 2026-09-03 02:05 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [a476452] - defer image/font/component bytes to Code Generator

`_materialize_image_candidate`, the Fontsource block, and `_materialize_component_candidate` now emit `disposition="deferred_materialized"` and skip persisting bytes/source text into the pack, instead of writing them plus a redundant sidecar JSON their own prior comment already said the planner never reads — all the real download/inspect/dedupe/policy verification work is unchanged. Updated every disposition-aware handoff-eligibility and reporting check (`quality.py`, `fixture_runs.py`) to recognize the new value so a deferred decision counts as resolved. Dropped `_materialize_component_candidate`'s now-unused `root`/`files` parameters. 104 Build Preparation unit tests pass (3 updated for the new behavior); 917 unit tests and related API tests pass repo-wide.

### 2026-09-03 01:40 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [8c7e994] - add deferred_materialized resolution type

Root-caused why 10/10 fresh live Code Generator runs (Codex/Luna campaign, `efca5de`) all still failed after the two historical blockers stopped recurring: none trace to Build Preparation's pack being too complex for the planner (it only ever reads 6 narrow files, never `handoff-report.json`/`handoff-analysis.json`), but the pack genuinely is bloated (confirmed byte-for-byte duplicate file, arrays written 3-4 times). Starting a revamp where Build Preparation keeps 100% of the resource decision authority but stops embedding bytes: added `deferred_materialized` as a sixth `resolution_type` alongside `local_materialized`/`target_package_binding`/`local_recipe`/`delegated_acquisition`/`execution_gap`, wired through both admission gates, the ledger/execution-contract policy flags, and the handoff-eligibility usable-disposition checks. Purely additive so far — nothing yet produces this type. Recorded as a partial revision of D-018 (decide-what stays upstream; decide-when-to-fetch-bytes moves downstream to Code Generator's existing, already-live acquisition adapters). 306 existing Build Preparation/Code Generator unit tests still pass; ruff/mypy clean.

### 2026-09-03 00:22 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [e78e70b] - elevate Studio UI/UX into an Editorial Architectural Atelier
Elevated the OryxenAI Studio user experience from a generic basic form into an interactive, tactile Editorial Architectural Atelier (rejecting generic AI slop, rainbow gradient blurs, and fake chatbot tickers): added ArchitecturalCanvas rendering a fullscreen HTML5 drafting grid with cursor-proximity spring deflection, precision crosshairs, and live coordinate telemetry (paused when hidden, prefers-reduced-motion compatible); added ArchetypeSelector with 4 distinct technical persona cards (Systems Architect, Creative Technologist, Founding Product Lead, Research Engineer) pre-seeding authentic structured intake prompts, plus quick prompt starter chips; added live narrative telemetry bar calculating word/character metrics and density progression in real time; added PipelineStagePreview showcase detailing the 5 transformations (Discovery, Content, Design, Prepare, Code Gen); updated StartSurface with time-adaptive greetings and live status beacons; and refined shell.css with frosted glassmorphic card elevations, sticky studio topbar with workspace telemetry, and magnetic tactile button physics. Verified with 133 Vitest tests across 16 test suites, production Vite build, and live browser verification with subagent on /app.
Fixed infinite reload loop and missing authentication configuration when accessing /app in detached development mode: branched product_shell.html scripts block on pipeline_mode to load pipeline-bootstrap.mjs during detached runs; updated pipeline-bootstrap.mjs and app-auth-bootstrap.mjs to dynamically load the Preact product entry and hand in a default developer identity without Supabase OAuth; and added preserveEntrySignatures: "exports-only" to frontend/vite.config.ts so Rollup retains the entry module's {boot, stop, restart} exports instead of tree-shaking the studio UI. Verified in-browser with subagent confirming full Editorial Swiss studio header, intake textarea, and start button render without reload loops. All 133 frontend tests and web route tests pass.

### 2026-09-02 23:28 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [9b5ea36] - implement Frontend Phase 5 hardening and production cutover
Implemented Phase 5 hardening and cutover for the authenticated /app portfolio studio per docs/Frontend/05 (§12-15, §18-19): safe storage wrapper with in-memory fallback for private browsing, quota limits, and restricted webviews; ErrorBoundary component with honest Editorial Swiss recovery card; SafeMarkdown parser enhancements for blockquotes and fenced code blocks; AppShell concurrency refactor executing all 6 stage projections in parallel via Promise.allSettled; automatic downstream unlocking on terminal poller completion; mutation in-flight tracking and double-submission protection across all stages; locked-stage URL normalization via replaceState; full responsive layout system covering Mobile (< 600px, 100dvh, >= 44px touch targets), Tablet (600-899px), Laptop (900-1279px), and Wide Desktop (>= 1280px); @media (forced-colors: active) high contrast mode; @media print artifact export stylesheet; high contrast :focus-visible indicators; and cutover to canonical Preact studio by default (enable_product_preact_shell = true) while preserving /dev developer diagnostic harnesses. Verified with 133 passing Vitest tests across 16 test suites, production Vite build (11.84 kB JS / 29.08 kB CSS, well within §14 budgets), 18 passing Python tests, ruff, and mypy (0 issues in 216 files).
Implemented the verified Preview surface per docs/Frontend/05 (§6.6, §8.10, §19 Phase 4): pure Preview adapter with receipt validation (strict scheme/host/traversal checks, route derivation from promoted contract, selected route fallback, and previous-preview retention during active or failed runs); pure PreviewSurface presentation component and connected usePreviewController hook; exact-origin postMessage handshake using preview-bridge-v1 protocol (handling preview:init, preview:ready, and preview:route); container-sizing hardening with zero-CLS box reservation before load and fixed-size wrapper transform: scale() letterbox (never resizing iframe outside 1440x900, 768x1024, 390x844 verified profiles or fit); toolbar containing route selector, 4 viewports, scale indicator, refresh, and open in new tab; cold-start overlay adapting copy after 2 seconds and 8-second failure/timeout recovery without discarding receipt or mutating generation state; empty absent state; full AppShell integration and URL search params sync. Verified with 111 Vitest unit/component tests across 11 suites, FastAPI web route tests, and production Vite bundle within budget (11.62 kB JS / 24.75 kB CSS).

### 2026-09-02 22:47 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [f9e8eef] - implement Frontend Phase 3 build preparation and code generator integration
Implemented full Phase 3 product frontend integration: volatile Build Preparation adapter mapping runtime substages to four semantic user milestones ("Checking approved plan", "Resolving portfolio materials", "Compiling build context", "Packaging and verifying handoff"), staleness detection and handoff eligibility; durable Code Generator session adapter mapping six lifecycle milestones (queue, plan, acquire, generate, verify, promote), active preview preservation, and server-fenced retry rules; pure functional PreparationStage and GenerationStage surfaces; reusable ProgressSurface with honest milestone checklist, neutral elapsed timer, and leave-safe reassurance (no fake percentages, ETAs, or token streams); session-scoped idempotency key management; full AppShell polling coordination for active preparation/generation durable jobs; and unified styles. Verified with 92 Vitest tests, FastAPI web route tests, and clean production Vite bundle (11.62 kB JS / 20.08 kB CSS).

### 2026-09-02 22:30 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [47a57b0] - implement Frontend Phase 2 app shell, discovery, content, and design
Implements Phase 2 studio capabilities: portfolio start/resume, multi-stage JourneyRail navigation with live stage status, cross-tab invalidation via BroadcastChannel, tab-visibility polling coordination, interactive Discovery conversation surface (handling text, single_select, multi_select, boolean question types, and draft preservation), pure Content Architect adapter with route plan/content pack review, pure Visual Design Director adapter with visual language/page direction review, bounded safe Preact Markdown renderer with section headings index, revision composers, explicit handoff panels between stages with zero auto-chaining, honest attention/recovery panels, and Editorial Swiss design system styling. Verified with 54 unit and component Vitest tests, 47 node auth tests, 4 FastAPI web route tests, typecheck, and Vite production bundle measurements (4.81 kB JS / 3.73 kB CSS gzip). Recorded D-059 for single root .env configuration.

### 2026-09-02 21:39 +05:30 - Codex (GPT-5 / OpenAI) - [efca5de] - record live Code Generator issue campaign
Documented the ten permitted live Code Generator starts against the eligible Build Preparation pack, including each terminal failure, all observed planner/source/runtime/integration diagnostics, environment and observability limitations, and the two historical blockers. Neither historical blocker recurred in the ten-run sample; no source code or model/repair ceilings were changed.

### 2026-09-02 16:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [20f72e2] - retry within budget on rejected source validation too
A third fresh live run got cleanly through planning, generation, and integration, then hit `SOURCE_CONTRACT_FAILED` with `repair_rounds` still 0. `final_repair.py` now catches `SourceValidationError` in the same retry loop. Updated D-058 and added a regression test.

### 2026-09-02 16:35 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [3099e1c] - deduplicate font-face rules shared across typography roles
A second fresh live run hit duplicate `@font-face` blocks in `generated-tokens.css`. Now tracks emitted tuples and skips repeats. Regression test added.

### 2026-09-02 16:20 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [eaa7390] - allow negative shadow offset and spread tokens
Added `SignedLengthTokenV4` (finite-only) for offset_x/offset_y/spread; blur keeps strict non-negative type. Unit test added.

### 2026-09-02 16:05 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [7292f2c] - persist true repair-round count when a round is consumed but fails
Persisted `repair_rounds` updated to `budget.total_used` on every consumed round including failed ones.

### 2026-09-02 15:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [d3cc095] - retry final repair within budget after cannot_complete
`_attempt_repair` now loops on `FinalRepairError` until `RepairBudget.can_attempt` is exhausted. Recorded D-058.

### 2026-09-02 15:41 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [082d179] - add SPA fallback redirects to the react-vite-v1 scaffold
Added static `public/_redirects` file so every generated build serves `index.html` for deep-linked or refreshed routes on Netlify/Cloudflare Pages.

### 2026-09-02 15:33 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [375aae3] - thread image alt-text and placement into usage_contract
Extended materialized-image `usage_contract` with `alt_text`, `focal_point`, `placement`, and `decorative`. Verified with 14 unit tests.

---

## Compacted history

### 2026-09
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [280982e, ae17373] - Frontend research package and implementation blueprint (authenticated journey, information architecture, route/API/adapter/component contracts, Preview UX, visual system, performance/rollout budgets).
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [e8c6b55, 749022f, d971764, 08633e6, 97cdada, dfce00f, c0c1f67, a622d7d, 5f4be9a, b760acb] - Hardened Code Generator V4 admission, distinctive move floors, structural sameness detection, shadcn Tailwind v4 theme bridge, and retired legacy resource filenames.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [1cf313f] - Final verification repair usage is bounded by diagnostic group with a shared run-wide ceiling and fail-closed V4 repair responses.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [234a05d] - Restored dedicated Code Generator role profile bindings while keeping routing provider-neutral and configuration-owned.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [aecfe40] - Aligned V4 selector evidence and responsive image-size contracts with executable source validation.
- 2026-09-01 - Codex (GPT-5 / OpenAI) - [d41eba1, b780266] - Hardened Code Generator generation, source evidence, repair, and polish contracts; fixed native PostgreSQL role alignment.

### 2026-08
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [557201b] - Live runs confirmed the accepted-mode fix and exposed a separate rejected-candidate persistence gap for later diagnosis.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [557201b] - Root-caused retry-time accepted results to an overloaded repair operation and forbade accepted mode throughout the shared model-result boundary.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [no code change] - Established that the accepted-mode failure occurred on a diagnostic retry with prior content rather than on the first generation call.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [d36c053] - Regenerated an eligible Build Preparation pack, raised the rich-content generation context ceiling, and recorded remaining fixture-path/provider constraints.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [664d88e] - Planner prompt now states the lowercase semantic token-name grammar required by the V4 schema, preventing avoidable `PLANNER_OUTPUT_INVALID` results from numeric-only token names.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [2a4a345] - Added a diagnostic backstop for any accepted-result envelope that bypasses its forbidden validation context, preserving a loud failure instead of silently accepting bad source.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [c354841] - Schema-context validation rejects accepted results when a generation call is marked forbidden, allowing the bounded correction retry to surface the precise issue.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [5a89eb0] - Fresh-generation prompts stopped listing accepted as a valid result; integration/repair retained prior-content semantics and regression coverage.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [510d8d1] - Documented accepted-result semantics and corrected the integration prompt's empty-change contract while fresh-generation operations reject acceptance.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [86824a7] - Font bindings now preserve per-file weights and token compilation avoids double prefixes; prompts document the group-prefix convention.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [8f50f4b] - Quality-review rejection is persisted with its real diagnostics instead of being discarded during repair failure.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [eef4c7d] - Test overlay now points at reachable PostgreSQL and marks the previously skipped integration files; it also documented a separate legacy foundation-profile regression.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5dc23b2] - V4 route composition audit now honors planner-owned paths and section ownership, while invalid repair responses stay out of the cache.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [65801b7] - Source audit preserves planner route storage keys instead of deriving a second path identity.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [17fd5e3] - Standalone UI exposes verification retry after a failed job returns the run to source-ready.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f20f5c5] - Terminal verification and new source generation clear stale job bindings so same-run retry remains available.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5e3ea5c] - Host-only source normalization rebinds quality receipts to the updated checkpoint hash before verification.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [a63162d] - Successful owner-scoped integration polish is persisted as the resumable source checkpoint.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [4c8f361] - Stated the v4 repair envelope invariant explicitly (exact signatures, coverage arrays) so valid corrections stop being rejected for missing transport metadata.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [1b447a4] - Preserved the v4 schema discriminator through repair-context compaction so returned coverage is interpreted through the correct envelope.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f72ab5e] - Trimmed repair context to route/contract/diagnostic essentials to fix a GENERATION_CONTEXT_LIMIT failure from supplying complete owned files.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [bf0e076] - Repair context now falls back to authoritative current file contents when no rejected candidate tree exists, fixing a repair-context authority gap.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f536178] - Canonicalized the reviewer's "-composer" owner alias to the real "-compose" work unit ID, fail-closed for unknown owners.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [bb9454e] - Made the source audit trace content IDs consumed through a .map() callback, instead of failing to prove their contentValue() calls.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [93771b9] - Made the source audit resolve the @/ SharedSystems alias and array-held content IDs statically instead of rejecting both valid forms.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0b46913] - Made the source audit scaffold part of the trusted shell files restored on workspace open, so it can't silently regress to an older version.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [20ea8b8] - Scoped composer contexts to their exact owned paths only, fixing a second GENERATION_CONTEXT_LIMIT from a stale full-src-inventory filter.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0a6dcfe] - Enforced one literal section anchor/DOM id per owned TSX file for split route batches, and widened the V4 audit to count rendered section modules.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0431996] - Cleared stale rejected-attempt diagnostics on same-run resume so retries validate against the restored source tree instead of replaying pre-repair audit findings.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [ffac6f6] - Bounded resumed source-generation context to owned-file inventory to stay under the 120k-character ceiling during repair.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [958b27a] - Added a worker-thread Popen fallback for Windows batch toolchain launches when async launch modes fail.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [27b9679] - Retried denied Windows process-group launches without the optional new-process-group flag.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [90f2a82] - Routed allowlisted .cmd/.bat toolchain commands through the Windows command interpreter to fix [WinError 5] Access is denied.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [253b1fa] - Preserved the OS-level error in toolchain start-failure diagnostics so a native launch failure is observable.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [414b0c7] - Enforced route-scoped (not shortened) DOM anchor IDs at route-batch checkpoint time, reopening stale checkpoints on violation.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [ab3672f] - Validated route-batch named local imports/re-exports against target-module exports before checkpoint, reopening stale invalid batches.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [8ee6947, 4bd5d7b] - Bounded retry diagnostics to the active work unit so unrelated composer history stopped crowding out the context ceiling (4bd5d7b's own entry was written then deleted as a near-duplicate of this one without swapping in its real hash; folded in here instead of left orphaned).
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [eb55728] - Gave route batches an exact trusted-module import map and bounded resolver before checkpointing, with same-run reopening of stale batches.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d620d1f] - Removed batch-owned content IDs/facts/route bindings from V4 composer context, and added a same-run resume path for terminal queued/checkpointed runs.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [c0b4087] - Gave same-run generation retries fresh durable job identities (keyed by run revision) so a terminal retry always gets a worker job.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [772bef1] - Aligned V4 composer content contract so composers reserve content-key coverage for section-owning route batches, not themselves.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [70b024d] - Fixed the detached generator shell to import the main Code Generator module at its computed asset version, preventing stale cached controls.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5edcb30] - Trimmed composer context (dropped duplicate generated-content interface) to resolve GENERATION_CONTEXT_LIMIT, and added same-run "Resume generation" in the standalone frontend.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [e12d787] - Deferred the whole-site route audit out of the route-batch phase so batch diagnostics stop targeting the still-scaffold route shell.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d5247dd] - Made V4 resource coverage reporting require the complete work-unit slot assignment, not just used slots.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [169ea5f] - Exposed a bounded generated-content.ts interface excerpt to route-batch context instead of omitting it entirely.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [fb1c209] - Required every V4 typography binding to declare an explicit body/display role instead of silently defaulting to body.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [cbe4491] - Bounded Code Generator operation context to the active work unit's plans/projections/APIs/dependencies to fix a ~245k-character context overflow.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d1a229d] - Made source/toolchain checks phase-aware so the whole-site AST audit defers until route composition/final integration.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [8c07530] - Fixed JSX-element AST field reads in the source audit and made V4 typography custom-property emission collision-safe.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [caead48] - Made optional dependency installation transactional (disposable sibling workspace) so a rejected fallback package can't poison the toolchain check.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [d4fe70f] - Added a deterministic route/section identity manifest and host-side identity validation so V4 planning can't invent or reuse region ownership IDs.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [1e3610e] - Fixed the native dev launcher's UV cache path and PowerShell path-quoting for repository paths containing spaces.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [78ee3ea] - Removed the unreachable Code Generator foundation model profile/routing/prompt (confirmed dead; foundation stays a deterministic compiler boundary) and corrected architecture docs.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [e945f54] - Made the preview gateway part of the default Docker stack with a real async health probe, and set strict public-readback only on the hosted overlay (D-054).
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [b92a86c] - Root-caused and fixed the stuck detached run: API/worker were split across a stray port-5545 Postgres and the canonical 5432 instance; stopped the stray process, abandoned the orphaned run, and fixed a WorkGraph compiler bug that collapsed unique V4 section owner IDs into one.
- 2026-08-26 - Claude Code (Claude Sonnet 5 / Anthropic) - [b4f7daa] - Fixed advance_after() building a real (version-0) authorization context for detached runs, which silently blocked every auto-chained stage advance.
- 2026-08-26 - Claude Code (Claude Sonnet 5 / Anthropic) - [9b2d28f] - Relaxed the V4 font-role file-set check to a subset match instead of requiring exact equality.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [e5d55f9] - Classified local PostgreSQL credential failures as an actionable 503 and added secret redaction across detached diagnostics.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [8a918f3] - Allowed both native dev ports in the local origin allowlist to fix ORIGIN_NOT_ALLOWED on an alternate port.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [7c44add] - Added the no-auth standalone Code Generator control room (Build Preparation mirror bootstrap, Luna routing, inspector UI) with safe export receipts/generation-report.md.
- 2026-08-26 - Codex (model/provider omitted) - [9b39fe3] - Replaced generic repeated resource searches with profession-aware image/component roles and added provider/rate-limit guards.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [5d6886a] - Added Anthropic-specific credit-exhaustion error markers, which previously fell through to a generic provider-error bucket.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [8e93fc2] - Fixed role_for()'s fallback wrongly promoting unrecognized sections to the required "selected-work" role; added a genuine low-stakes fallback.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [2f9403b] - Added per-provider rate-limit backoff to the component-registry fetch path, matching the existing image-fetch cross-query memory.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [2a6fb12, 60a41a3] - Added ID-stability guidance to the VDD full-pages reconciliation prompt (was inventing composite content_ref IDs) and fixed the worker never calling configure_logging().
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [ed9de3b] - Gave component materialization the same alternate-candidate retry loop as images, removed ~190 lines of dead code, and enriched execution-gap messages.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [40d0477] - Added a detached-auth router for the standalone Code Generator dev harness, selected when auth.pipeline_mode == "detached" (D-053).
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [53cd913] - Fixed /dev hardcoding pipeline_mode="attached" instead of following config, and stopped the frontend collapsing session-create failures into a generic message.
- 2026-08-25 - Codex (model/provider omitted) - [87cad46] - Extended detached mode through Build Preparation fixture/progress APIs and redirected detached /sign-in to /app (D-052).
- 2026-08-25 - Codex (model/provider omitted) - [b70dde2] - Fixed the detached Build Preparation frontend/CLI exposing the internal build_preparation engine route as a selectable profile.
- 2026-08-25 - Codex (model/provider omitted) - [c9f0a95] - Hardened the native live Build Preparation path (Luna output-shape recovery, fixture stamping, image-candidate retries); verified a live pack ZIP end to end.
- 2026-08-25 - Codex (model/provider omitted) - [62166f3] - Converted deterministic output-contract failures into bounded, privacy-safe retries across Discovery/CA/VDD.
- 2026-08-25 - Codex (model/provider omitted) - [5f272b3] - Shortened the Build Preparation checkpoint revision ID to fit Alembic's version column and hardened the native doctor's schema check.
- 2026-08-25 - Codex (model/provider omitted) - [9055cc3] - Aligned test-profile timeouts across every bounded model workflow and added detached-only authorization inventory coverage for the model-profile preflight API.
- 2026-08-25 - Codex (model/provider omitted) - [c19e4a1] - Detached-only safe profile listing/preflight, sticky four-stage model selection, live Build Preparation progress, and native PostgreSQL/auth/migration diagnostics.
- 2026-08-25 - Codex (model/provider omitted) - [5b5df50] - Unified retry/timeout decisions, redacted per-operation receipts/live progress, and source/profile/candidate-bound Build Preparation stage checkpoints (D-051).
- 2026-08-25 - Codex (model/provider omitted) - [2614bde] - Centralized provider-neutral model runtime (profile routing, capability validation, preflight caching); removed live mock fallback.
- 2026-08-25 - Codex (GPT-5 / OpenAI) - [15cf585] - Config-driven detached development mode for Discovery-through-Build-Preparation, with session classification, no-store behavior, and a Restart Pipeline action.
- 2026-08-25 - Codex - [540d33a] - Canonical native/Docker dual-mode development runbook and the isolated Docker Code Generator overlay.
- 2026-08-24 - Codex (GPT-5 / OpenAI) - [a39bd7e] - Reduced Anthropic interactive latency for the first three agents (lower budgets/effort, safe JSON control-character recovery).
- 2026-08-24 - Codex (GPT-5 / OpenAI) - [563b2a6] - Forced Google account selection after sign-out via `prompt=select_account`.
- 2026-08-24 - Codex (Claude Sonnet 5 / Anthropic) - [3b3ed9f, 456db9c] - Routed all four model-backed agents through Anthropic Claude Sonnet 5; a live Build Preparation pack materialized and correctly landed `needs_attention` on two real VDD execution gaps.
- 2026-08-24 - Codex (GPT-5.6 Luna / OpenAI) - [9b95baf, bf8f63d] - Routed all four model-backed agents through a direct OpenAI Luna profile; live calls reached OpenAI but stopped at `credit_balance_exhausted` before any pack materialized.
- 2026-08-24 - Codex (model/provider omitted) - [e70b6ab, dddc1ba] - Open Google registration admission mode (open/allowlist, D-048) and matching auth-handoff documentation.
- 2026-08-24 - Codex (model/provider omitted) - [449b379, c5b5821] - Authentication redirect-flicker fix and final Supabase/PKCE/Admin-API readiness hardening ahead of owner browser acceptance.
- 2026-08-24 - Codex (model/provider omitted) - [b17227c] - Phase 4 administrator lifecycle, audit, and resumable deletion/reset.
- 2026-08-24 - Codex (model/provider omitted) - [90d5dfe] - Phase 3 portfolio entitlements, durable owner/actor snapshots, and worker fencing.
- 2026-08-24 - Codex (model/provider omitted) - [d288077, 48e5f6c] - Phase 2 session ownership/API authorization (D-045) and the Phase 1 Supabase Google-only auth foundation.
- 2026-08-23 - Codex - [c9ad71d, 0f9bc0d, a03ba6f] - Authentication research, prerequisite verification, provider selection, and minimum-route implementation handoff.
- 2026-08-23 - Codex - [5ca0b85] - Code Generator V4 source realization, quality/runtime contracts, preview hardening, and stable retry semantics.
- 2026-08-21 - Codex - [3437075, 26890c5] - V4 quality/read-back promotion gates, provider contracts, runtime verification, and preview reliability.
- 2026-08-21 - Codex - [5fcbdd4, 1b37748, 0b7a806, 7eac824] - Provider-neutral routing, standalone runbook, hosted preview architecture, generation, verification, and atomic promotion.
- 2026-08-21 - Codex (GPT-5 / OpenAI) - [0240f57] - Lightweight LLM observability research and metadata-only tracing recommendation.
- 2026-08-21 - Codex (GPT-5 / OpenAI) - [b6a2be5] - First-three-agent Docker startup recovery runbook and verified frontend/API/worker state.
- 2026-08-21 - Codex (live provider run) - [0e965fd] - Code Generator provider contract, planner admission, and Docker workspace portability.
- 2026-08-20 - Codex - [f726d03] - Native Claude Sonnet 5 Code Generator provider adapter and structured-output handling.
- 2026-08-20 - Codex (live Docker run) - [3ced105] - Standalone Code Generator Docker runtime recovery and live provider attempt.
- 2026-08-20 - Codex (live Docker run) - [8cdbfb8] - Docker route-generation workspace, dependency, and typecheck reliability fixes.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [6e2c072] - TypeScript source-contract audit and exact browser/runtime verification.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [e8d6ec1] - Build Preparation pack-v4 delegated acquisition and deterministic resource handling.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [86b3e8d] - Design-neutral Code Generator V3 generation, typed experience tokens, trusted shared systems, route-batch ownership, isolated scheduling, and source regressions.
- 2026-08-20 - Codex (GPT-5) - [0c4901f] - Fenced stage attempts, immutable workflow artifacts, trace metadata, retry classification, worker readiness, and content-addressed artifact repositories.
- 2026-08-19 - Codex (live provider run) - [8259231] - Grounded Build Preparation to Code Generator execution, exact-pack survival, verified preview promotion, and persistent local export.
- 2026-08-19 - Codex (live provider run) - [a01c030] - Docker fixture execution repair, read-only CA/VDD inputs, deterministic need IDs, package retention, and verified R2 read-back.
- 2026-08-19 - Codex (live provider run) - [33b7113] - Build Preparation execution runbook with verified links, secret names, detached/live commands, and handoff diagnostics.
- 2026-08-19 - Codex (live provider run) - [237e0ed] - Build Preparation response-schema alignment, normalization, live packaging, and R2 read-back diagnostics.
- 2026-08-19 - Codex (model/provider omitted) - [45eafdc] - Reusable Discovery/Content/Visual Docker runbook, migration repair, provider checks, startup, and verification steps.
- 2026-08-19 - Codex (live provider run) - [3c1ff43] - Code Generator provider fallback, source validation, responsive repair, runtime gates, and atomic preview/export.
- 2026-08-19 - Codex (model/provider omitted) - [8a85438] - Nested Build Preparation mirror discovery and exact-pack admission, with provider-consent retry remaining.
- 2026-08-19 - Codex (model/provider omitted) - [6afd672] - Production Code Generator v2, visual compiler, deterministic resources, workflow verification, and preview retention/promotion.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [6bdcb13] - Selected verified Build Preparation output and recorded pack identity, scope, bindings, hashes, and handoff distinction.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [da99302] - Build Preparation overview, authority files, resource flow, route inventory, handoff review, and regression coverage.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [273799b] - Contextual visual enrichment, alternate recovery, provenance bindings, aggregate diagnostics, and downstream reacquisition guards.
- 2026-08-13 - Codex (model/provider omitted) - [4c4f51d] - Four-phase Code Generator execution guide covering admission, planning, acquisition, generation, verification, repair, and preview.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [4c4f51d] - D-015 progressive text-only generation pipeline, trusted acquisition, workspace isolation, gates, and repair guidance.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [958b4d8] - Code Generator v1 architecture handoff, Build Preparation boundary repair, bounded generation, exact verification, and preview promotion.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [958b4d8] - Code Generator proposal refinement covering product pillars, deterministic orchestration, provider policy, workers, and preview promotion.
- 2026-08-18 — Codex (GPT-5 / OpenAI) — [cde016e, 42e92ec, 8909c09, 0bd8bb5, 646a0bb, 3e2831c] — Build Preparation boundary/semantic enrichment, local image retrieval, deterministic component-priority selection, and cache-free multi-provider component retrieval.
- 2026-08-17 — Codex / OpenCode — [e3d80c2, 3479c40, 2edc335, 7957f7e, 2903bd2] — Detached input pickup, provider diagnostics, real visual handoff, best-pack readiness, resource coordination, and preview-gateway hardening.
- 2026-08-17 — Codex (GPT-5 / OpenAI) — [fffd253, 9ed8fe4, d23bc09, e35dd62, 91aa906] — Code Generator workspace UI, checkpoint recovery, cross-agent Git policy, canonical core ownership, source contracts, and DOM/runtime/export verification.
- 2026-08-16–14 — Codex / OpenCode — [5bf4b5f, c091282] — Standalone Code Generator phases 1–4, provider/toolchain integration, progressive generation, clean builds, verification, repair, and atomic preview promotion.
- 2026-08-13 — Codex / OpenCode — [4c4f51d, d0a6b1d] — Pack-v3/v2 contracts, Code Generator admission/acquisition/planning, public-scope handoff guards, and the initial architecture/runbook documentation.
- 2026-08-12 — Codex (GPT-5 / OpenAI) — [0174a5b, 7c4580f] — Code Generator architecture research, Build Preparation admission & quality handoff, shared agent workspace UI.
- 2026-08-11 — Codex / Claude Code — [ea2267f, 39d16cf] — Build Preparation agent rebuild as Agent #4 (D-011), Phases 1–3 implementation (manifests, R2 storage, worker persistence, provider fallbacks).
- 2026-08-10 — Codex (GPT-5 / OpenAI) — [d4a4556] — Initial Portfolio Production Compiler implementation, Pexels integration, and fixture preview (D-010).
- 2026-08-08–09 — Codex / Claude Code — [bdc8822..a75810a] — Initial Discovery, Content Architect, and Visual Design Director agents, durable PostgreSQL worker queue, and core platform scaffolding.

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

## Summary (as of last compaction — 2026-09-03)

- Recent detailed entries retained: 20
- Compacted milestone bullets: 135
- Last updated: 2026-09-03 — Claude Code (Sonnet 5 / Anthropic)
