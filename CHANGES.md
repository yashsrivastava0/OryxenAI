# OryxenAI — Change Log

Append-only record of who changed what, where, and why, so any AI tool or
Yash can reconstruct history without re-deriving it from diffs alone.

**Logging policy — log sparingly, this file must stay cheap to maintain:**

- Log **only commit-sized, "major" work**: a finished feature, a real bug
  fix, a refactor, a new file/module, an architecture or schema change —
  roughly what would earn its own git commit message. Do not log every
  individual file save or micro-edit.
- If it's unclear whether something counts as "major," **ask the user
  before adding an entry** rather than guessing — no entry is the safe
  default for anything ambiguous or clearly minor (typo fixes, formatting,
  comment wording).
- One entry per logical unit of work, not one per file touched within it.

Ordering: newest entry first, directly under "## Recent changes" below.
Never delete entries — old entries are compacted (see "Compaction
procedure" near the bottom of this file), never erased.

This file is separate from `DECISIONS.md`. Log *what happened* here; log
*open questions, rejected approaches, and deferred work* there.

## Recent changes

### 2026-08-16 11:51 +05:30 — Codex (GPT-5 / OpenAI) — Code Generator Phases 1-4, Build Preparation, provider configuration, preview workflow, tests
Completed the standalone Code Generator development workflow through admission, planning, controlled acquisition, progressive source generation, verification, finite repair, and preview promotion, while aligning Build Preparation, model/provider configuration, durable jobs, migrations, developer UI, fixtures, and regression coverage with the new contracts. Production session integration and automatic pipeline chaining remain deferred.

### 2026-08-14 13:35 +05:30 — Codex (GPT-5 / OpenAI) — Code Generator core, shared provider, prompts, toolchain, developer UI, fixtures, tests
Refactored the live standalone Code Generator into core/, replaced weak/free-form planning contracts with typed, enforceable design and acceptance contracts, and corrected the provider path so canonical structured input is actually sent separately from trusted prompts. Reworked generation prompts for grounded advanced portfolio implementation, removed scaffold and simulated dependency installs, added real package-manager lockfile policy, readiness reporting, a rich privacy-safe v3 fixture, semantic source evidence checks, and focused regression coverage while preserving the registry mock and standalone Build Preparation boundary.

### 2026-08-14 10:47 +05:30 — OpenCode (GPT-5.6 / OpenCode Go) — Code Generator Phase 4 verification, preview, hardening, and toolchain
Implemented the standalone Phase 4 workflow: clean receipt-bound builds, source/build/DOM-runtime gates, finite diagnostic repair, immutable candidate storage, crash-safe idempotent preview promotion, isolated preview gateway, worker lease fencing, developer route/viewport preview controls, Docker/CI toolchain setup, and verification API/UI coverage. Production session integration and automatic chaining remain deferred.

### 2026-08-14 00:51 +05:30 — OpenCode (GPT-5.6 / OpenCode Go) — Code Generator Phase 3 source generation
Implemented standalone Phase 3 progressive source generation on top of the completed Phase 1/2 workflow: trusted React/Vite/TypeScript scaffold, isolated workspaces, source manifests and policy checks, immutable checkpoints, strict foundation/route/composition/integration operations, emergent receipt-bound acquisition, source/type repair, durable generation job, API, developer UI, migration, and completion-gate tests. Phase 4 verification/preview and production session integration remain deferred.

### 2026-08-13 22:30 +05:30 — Codex (GPT-5 / OpenAI) — Build Preparation pack-v3, standalone Code Generator admission, configuration, fixtures, documentation
Replaced the Code Generator handoff with pack-v3: canonical route storage, hash-covered execution slots, resource ledger/recipes, readiness diagnostics, and strict v3 fixture/upload admission now prevent prose-only or ambiguous resource decisions. Added constrained provider policy/pins and privacy-safe recipe bindings while keeping source generation, main-flow wiring, and emergent acquisition outside this work; see D-018.

### 2026-08-13 20:22 +05:30 — Codex (GPT-5 / OpenAI) — Content Architect, Visual Design Director, Build Preparation, frontend, tests

Defined and enforced a safe public-scope handoff: Content Architect now defaults ordinary supplied portfolio facts to neutral publishable copy while retaining explicit restrictions, rejects incomplete approved routes, and offers an in-context revision action. Visual Design Director receives and emits only CA-approved routes with canonical identity, and Build Preparation tests cover mixed review/public scope plus canonical route metadata; see D-017.

### 2026-08-13 19:41 +05:30 — OpenCode (gpt-5.6-luna / OpenCode Go) — src/oryxenai/agents/build_preparation/service.py

Fixed the session Build Preparation projection so the pack-v2 compiler receives
approved Content Architect claim grounding, story/handoff data, and the
Visual Design Director's shared visual systems. This prevents the durable
session path from failing with `PackContractError` even when the detached
approved-input fixture succeeds.

### 2026-08-13 19:22 +05:30 — OpenCode (glm-5.2) — Content Architect approval guard + Build Preparation route diagnostics

Added a producer-side guard so Content Architect approval refuses to enter APPROVED when no `route_plan` entry is `publication_status="approved"` (state machine `NoPublishableRoutesError`; service 409 `CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES`), preventing the dead Build Preparation pack that previously surfaced as `BUILD_PACK_V2_CONTENT_ROUTES_MISSING`. Split that Build Preparation pack-v2 failure into `BUILD_PACK_V2_CONTENT_ROUTES_EMPTY` vs `BUILD_PACK_V2_CONTENT_ROUTES_NONE_APPROVED` and propagate the dropped route_ids + their statuses into the issue `details`; enriched Stage 0 `scope_compiled` with `dropped_routes` and named the per-route status in exclusion warnings. `route_plan` entries are never mutated, preserving the cross-agent pending-is-gated invariant. See D-016.

### 2026-08-13 16:17 +05:30 — OpenCode (GPT-5.6 / OpenAI) — Code Generator Phase 2 acquisition, migrations, API, frontend, tests

Implemented the standalone Phase 2 resource/dependency acquisition boundary: strict request, candidate, receipt, ledger, delta, adapter, and dependency contracts; safe offline-testable materialization; durable `code_generator.acquire` execution with idempotent redelivery; feature-gated API/UI projections; node_modules lifecycle policy; and Phase 1 completion-gate backfill. Corrected the overlong Phase 1 Alembic revision so the complete migration chain applies to PostgreSQL.

### 2026-08-13 15:10 +05:30 â€” Codex (GPT-5 / OpenAI) â€” Build Preparation pack-v2 contracts, VDD validation, config, tests

Implemented D-013's versioned pack-v2 boundary: deterministic site/visual/provenance projections, hash-covered packaging, exact consumer admission, source-policy safeguards, and diagnostic-only compatibility for incomplete legacy harness inputs.

### 2026-08-13 15:10 +05:30 â€” Codex (GPT-5 / OpenAI) â€” Code Generator Phase 1 standalone planning, persistence, API, developer UI, tests

Implemented the feature-gated fixture/upload admission and durable `code_generator.plan` workflow with independent run/event persistence, strict structured `SitePlan`/`WorkGraph` validation, safe receipts/issues, and a Jinja/vanilla-JS planning page; no source generation, resource acquisition, preview, or session-flow integration was added.

### 2026-08-13 12:35 +05:30 — Codex (model/provider intentionally omitted) — docs/code-generator-architecture/implementation-phases.md, docs/code-generator-architecture/README.md

Added the four-phase, approval-gated Code Generator execution guide: standalone admission/planning and developer UI, controlled acquisition, progressive generation, then verification/repair/preview. The guide keeps Build Preparation integration deferred, defines per-phase completion gates, and includes copy-ready plan and implementation requests.

### 2026-08-13 12:09 +05:30 — Codex (GPT-5 / OpenAI) — AGENTS.md, docs/code-generator-architecture/, docs/architecture.md, docs/build-preparation-agent-proposal.md, DECISIONS.md, CHANGES.md, SUGGESTIONS.md

Superseded the screenshot/vision-review Code Generator draft with D-015's progressive text-only generation pipeline. Added planning-time and emergent image/font/icon/component/style acquisition through trusted provenance and dependency adapters, explicit React/Vite workspace and `node_modules` behavior, three lean source/build/DOM gates, and compiler/runtime-guided finite repair.

### 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI) — docs/code-generator-architecture/, DECISIONS.md, CHANGES.md, SUGGESTIONS.md

Replaced the exploratory Code Generator proposal with a decision-complete v1 handoff covering the narrowly versioned Build Preparation boundary repair, bounded generation and phase-scoped repair, exact verification, and single-current-preview promotion; isolated non-MVP ideas in a deliberately unlinked, non-authoritative holding file. No runtime code or configuration changed.

### 2026-08-13 09:48 +05:30 — Codex (GPT-5 / OpenAI) — docs/code-generator-architecture/

Refined the Code Generator proposal around the ordered product pillars, deterministic orchestration and resource completeness, adaptive model-call and toolchain policy, and the production worker topology. Added a dedicated live-preview and future-deployment design that separates best-effort Build Theater from gated preview promotion while keeping local and cloud preview behavior behind one protocol.

### 2026-08-12 21:43 +05:30 — Codex (GPT-5 / OpenAI) — docs/code-generator-architecture/

Added a research-only Code Generator architecture covering admitted Build Preparation intake, bounded structured model calls, deterministic scaffold/package/resource ownership, durable R2 checkpoints, isolated preview promotion, browser and visual-quality gates, and a privacy-safe golden-reference evaluation corpus. The proposal records contract gaps and owner decisions required before implementation without changing runtime code or `DECISIONS.md`.

### 2026-08-12 20:45 +05:30 — Codex (GPT-5 / OpenAI) — DECISIONS.md, Build Preparation v1 and Code Generator boundary

Recorded D-012: freeze the verified Build Preparation v1 contract, start Code Generator development, and reopen upstream work only for a reproduced admitted-package defect with a clearly identified owner—not for generic downstream visual or implementation quality.

### 2026-08-12 20:36 +05:30 — Codex (GPT-5 / OpenAI) — Build Preparation handoff admission, resource packaging, integrity verification, report.md

Independently audited the four latest build packs and hardened Code Generator admission around upstream approval provenance, public route content, optional image/provider fallback, complete resource planning, registry source/licence/dependency safety, genuine lockfile ownership, ZIP extraction paths, and concurrent fixture diagnostics. Added regression coverage and a production handoff report; the historical packs remain immutable and the repaired offline verification pack correctly blocks until Visual Design Director approval.

### 2026-08-12 16:30 +05:30 — Codex (GPT-5 / OpenAI) — Build Preparation quality handoff, fixture monitor, resource policy

Added a policy-driven editorial-image requirement, deterministic candidate qualification, source/attribution and local-image inspection, and a structured Stage 5 LLM handoff review. Every package now contains `handoff-report.json`; a missing, weak, incompatible, or unmaterialized required resource leaves the durable state at `needs_attention` while retaining the local ZIP/R2 artifact and concise diagnostic issue. The fixture monitor now distinguishes fetched, qualified, selected, and materialized resources, records rejection reasons, and orders materialization before packaging events.

### 2026-08-12 15:42 +05:30 — Codex (GPT-5 / OpenAI) — Build Preparation fixture, artifact packaging, Docker harness
Added a detached, live-progress Build Preparation fixture that writes an India-local, Windows-safe `HH-MM-DD-MM` timestamped build-context folder, ZIP, result, and concise diagnostics before verifying the same immutable ZIP through configured R2 storage. The refreshed fixture UI exposes R2 preflight, stage activity, local download/details actions, and copy-ready issue reports; Docker now mounts the host `output/` folder for direct testing.

### 2026-08-12 — Codex (GPT-5 / OpenAI) — Shared agent-output workspace and live activity log

Reworked the test frontend's right sidebar into a shared Agent workspace for
Discovery, Content Architect, Visual Design Director, and Build Preparation.
Each stage now exposes its persisted full output in a readable preview and a
copy-ready text area with clipboard support. Added a polling-derived activity
timeline for API actions, stage/job transitions, approvals, and errors;
hydration restores the workspace across session refreshes without reading
fixture output files. Updated the frontend behavior spec to document the
copy/export and observability contract.

### 2026-08-12 — Codex — Build Preparation harness input and output readability

Improved the detached Build Preparation harness without changing its two-page
shape. The fixture API and input page now accept optional approved Content
Architect JSON alongside the Visual Design Director input, including file
selection and the same size, JSON, and ambiguous-input safeguards. Blank
Content Architect input remains backward compatible. Debug mirrors now use a
sortable, readable timestamp plus an eight-character run prefix while keeping
the full run ID in the package manifest.

### 2026-08-12 — Claude Code (Claude Sonnet 5 / Anthropic) — Independent verification and fixes for the implemented Build Preparation agent

Codex's Step 0 + Phases 1-3 implementation was independently re-verified
rather than trusted from its own self-report, per the project owner's
explicit request. Three parallel deep-code audits plus direct `pytest`/
`ruff`/`mypy` runs confirmed the core implementation is genuinely solid:
real Pexels/Unsplash/shadcn/MagicUI/Lucide HTTP calls, correct Pexels-
download-vs-Unsplash-hotlink-only licensing split, a real closed-set hard
rejection in `validators.py`, hash-verified ZIP packaging with real
upload *and* read-back verification, no hardcoded secrets/quotas, correct
`AgentKey`/job/API wiring with the CA+VDD approval gate enforced, and
Step 0's cleanup 100% clean (zero dangling imports, grep-confirmed).

Found and fixed:
- The dev test harness (`build-preparation-fixture.js` /
  `build-preparation-progress.js`) rendered only aggregate counts and a
  raw JSON dump — no per-resource listing — defeating its whole purpose
  of catching an empty/broken fetch "at a glance" (the original complaint
  this whole redesign started from). Added a `resources` field to
  `MaterializationResult` (`schemas.py`, populated in `materializer.py`
  from the already-computed per-resource manifest data) and a real
  per-resource list in the progress page (provider, filename/thumbnail,
  `inspection_level`/disposition status).
- `agent.py` (825 lines) mixed real pipeline orchestration with ~190
  lines of offline/fixture-fallback generators. Moved the six `_offline_*`
  functions into `fixture.py` (their natural home and primary caller),
  making `BuildPreparationAgent`'s import of them a local/deferred import
  inside `run_fixture()` to avoid a circular import. Pure move, verified
  by the full test suite before/after (640 passed/1 skipped, unchanged).
- Documented (in `docs/build-preparation-agent-proposal.md` §6) that the
  actual implemented execution order runs Stage 3/4 before materializing,
  not between Stage 2 and 3 as the diagram shows — intentional (route
  briefs are sourced from Stage 3/4 output) but previously undocumented
  against what §16 calls the spec of record.

Verified live, not just via mocked tests: `tests/live/test_build_preparation_live.py`
passed against the real configured OpenAI profile, Pexels/Unsplash keys,
and R2 storage. Went further and constructed a synthetic VDD input with a
genuine photo need to directly prove the original complaint is resolved:
a live run returned 14 real fetched candidates (5 real Pexels photos, 9
real shadcn/MagicUI components), Stage 2's live model correctly rejected
photos that didn't semantically fit a separate abstract-diagram need
(honest fallback, no fabrication), and a second run with a genuinely
photo-appropriate brief resulted in a real Pexels image being selected,
downloaded, Pillow-verified, and written to disk (`inspection_level:
"pixel_inspected"`, confirmed as a real 284KB JPEG on disk).

Left unchanged, per explicit decision: the two-page harness structure
itself (works correctly, not worth the rework), and everything else in
`providers.py`/`packager.py`/`validators.py`/`service.py`/the job/API
wiring — all independently verified correct as implemented.

### 2026-08-11 23:43 +05:30 - Codex (GPT-5 / OpenAI) - Build Preparation Phase 3

Implemented Phase 3 end to end: deterministic build-context manifests and
ZIPs, SHA-256 verification, memory/S3-compatible artifact storage, R2
read-back verification, expiry/staleness metadata, safe local debug mirrors,
public-content filtering, closed-set reconciliation for noisy live context
responses, and durable worker persistence. Updated the two-page harness,
fixtures, documentation, and decision status. Verified offline, PostgreSQL
worker, mocked storage, and opt-in live model/provider/R2 flows; Code Generator
and automatic pipeline chaining remain deferred.

### 2026-08-11 22:30 +05:30 — Codex (GPT-5 / OpenAI) — src/oryxenai/agents/build_preparation, worker, API, harness, tests

Implemented Build Preparation Phase 2 end to end: bounded model stages, provider fallback and closed-set validation, local build-context materialization, durable worker persistence, live/offline harness toggles, and the two-page progress UI; Phase 3 packaging/upload remains deferred. Verified the complete suite, static checks, PostgreSQL worker flow, and an opt-in live model/provider smoke run.

### 2026-08-11 21:35 +05:30 — Codex (OpenAI) — Build Preparation agent, API, worker, harness, tests

Implemented Stage 0 and all Phase 1 scope from `docs/build-preparation-agent-proposal.md`, including the deterministic provider-neutral agent, state/persistence/durable worker flow, approval and staleness-aware API, two-page fixture harness, and retirement of only the specified dead legacy references; Phase 1 makes zero model/provider calls by design and unrelated Visual Design Director, configuration, and settings changes were left untouched. Added unit, API, and PostgreSQL-backed integration coverage; verification completed with 624 passing tests, clean collection, Ruff lint/format, and strict mypy.

### 2026-08-11 — Claude Code (Claude Sonnet 5 / Anthropic) — docs/build-preparation-agent-proposal.md finalized for handoff

Finalized the Build Preparation proposal for handoff to a separate
implementing AI. Evaluated an independent review of the doc
(`prebuild-output/build-preparation-agent-review.md`) point by point rather
than adopting it wholesale: kept 4 narrow correct catches (no hardcoded
provider rate limits, Pexels-vs-Unsplash licensing handling, opaque
resource IDs, an `inspection_level` honesty field) and explicitly rejected
its larger rewrites (ZIP-to-individual-R2-objects, pushing component
fetching onto the still-deferred Code Generator, a new user-media
subsystem, a 3x3 necessity/enforcement matrix, an 11+-input staleness
fingerprint list) as unrequested complexity against the project owner's
own ≤5-user/free-tier brief. Added a temporary local debug-output mirror
(§15) and a standalone, pipeline-detached test harness (§17) so the new
agent can be exercised by hand with a manually-fed Visual Design Director
output before it's wired into the live pipeline. Added a mandatory 3-phase
implementation plan (§16) — skeleton, then providers/LLM stages, then
packaging/retirement — each phase gated on its own plan-implement-verify
cycle, requiring at least one real live model call per LLM stage (not only
mocked tests) before a phase counts as done.

Mid-task, `src/oryxenai/build_preparation/` (the retired module this
proposal supersedes) was deleted from the working tree by the project
owner, which broke the app: `api/dependencies.py`, `api/routes/build_preparation.py`,
`api/routes/__init__.py`, `jobs/handlers/build_preparation.py`, and
`jobs/registry.py` all still imported/registered against the now-gone
package, and `uv run pytest --collect-only` failed with 16 collection
errors across unrelated test suites (Discovery, Content Architect, Visual
Design Director, worker) because they transitively import the broken job
registry. Documented this as a required "Step 0" at the top of §16 with
the exact file list to clean up, since the implementing AI's first
`uv run pytest` would otherwise fail for reasons unrelated to its own
work. No source code was changed by this session — the fix is documented,
not applied; `src/` still needs Step 0 run before anything else builds.

### 2026-08-11 — Claude Code (Claude Sonnet 5 / Anthropic) — docs/build-preparation-agent-proposal.md, docs/portfolio-production-compiler-proposal.md, DECISIONS.md

Authored a replacement architecture proposal for Build Preparation after the
existing `src/oryxenai/build_preparation/` compiler was reported as
producing empty output and not fetching images. Investigation found the
code itself works — the symptom traced to the fixture harness defaulting to
offline/no-provider mode and a sample input with no photo requirement, not
a broken call — but the module was still ~2.2x Visual Design Director's
size for a non-creative stage and lived outside `src/oryxenai/agents/` with
no `AgentKey` entry. The new proposal rebuilds Build Preparation from zero
as agent #4, mirroring the Content Architect/Visual Design Director file
pattern, keeps Render/Supabase/R2, embraces liberal structured model use
(including a new LLM-authored screen-by-screen build brief the old design
never had), adds Unsplash as a Pexels fallback, and replaces the 9-section
bundle with a 5-section one. Marked the prior proposal doc superseded and
recorded the decision as D-011 (D-010 marked superseded-by-D-011). Why:
per the multi-agent collaboration protocol, the architecture decision and
its rationale needed to be durable across tools/sessions before any
implementation work starts. No code was changed; implementation is a
separate, not-yet-started planning pass.

### 2026-08-11 - Codex (GPT-5 / OpenAI) - VDD resource handoff and prompt latency fix

Closed the gap where valid catalogue resources selected inside a page or scene could be missing
from the top-level registry required by Build Preparation. The agent now promotes only shortlist-
validated catalogue IDs, while unknown IDs still fail validation. Tightened the VDD prompts for a
single-route, one-call response with a four-scene budget and compact summaries, and removed a
concrete resource ID from the example so prompts cannot seed a hard-coded candidate.

### 2026-08-11 — Codex (GPT-5 / OpenAI) — build_preparation fixture/compiler/service, VDD fixture, Content Architect prompt, tests

Added narrow one-opening-brace fixture recovery with explicit warnings, route-aware canonical anchor resolution, iconography alias provenance, and a production gate for legacy VDD handoffs missing `content_architect_visual_input_hash`. The fixture now reports that approved media requires no external image and preserves conceptual visuals as custom implementation opportunities.
The VDD final-reference check also keeps the standalone empty-upstream mock harness valid while retaining strict checks for real approved projections.

### 2026-08-11 — Codex (GPT-5 / OpenAI) — Simplified Build Preparation fixture harness

Replaced the temporary Build Preparation showcase page with a compact VDD-input
test harness. Each run now materializes the verified preparation contents under
`output/build-preparation-<UTC timestamp>-<input hash>/` and writes a result
JSON there; no ZIP is written to the local output directory. Production R2
storage and its ZIP contract remain unchanged. Added a safe configurable local
fixture output directory and an explicit empty-input error.

### 2026-08-11 — Codex (GPT-5 / OpenAI) — Visual Design Director boundary hardening

Added a final cross-reference validation pass after VDD's multi-call
reconciliation, so dangling scene content, asset, and resource references are
rejected before review. Expanded VDD approval and Content Architect staleness
fingerprints to include compiler-relevant visual fields and the complete VDD
input projection. Added focused regression coverage and documented the
compiler-facing contract; no VDD files were removed because the package is
fully live and referenced.

### 2026-08-11 — Codex (GPT-5 / OpenAI) — Build Preparation contract hardening

Closed the remaining compiler-contract gaps: canonical public-data pointers and
runtime API declarations, license provenance, a truthful local font catalogue,
bounded image preview renditions, multi-candidate registry selection, and
post-upload/download hash verification. The fixture can display bounded local
previews without persisting image bytes in PostgreSQL or requiring provider
network access during Code Generation.

### 2026-08-10 — Codex (GPT-5 / OpenAI) — Portfolio Production Compiler implementation

Implemented the approved user-visible pre-code compiler boundary. Build
Preparation now carries creative character and visual specifications into a
versioned Blueprint, performs bounded provider-neutral planning/selection,
admits registry source without execution or package installation, creates
responsive local Pexels renditions, ships the React/Vite target manifest and
lockfile, and packages self-describing route/context/resource files into a
hash-verified temporary ZIP. Added coarse persisted progress, explicit
fixture-only reasoning controls, deterministic source-admission and selection
tests, and the structured model profile. The production session path remains
R2-backed; the temporary fixture defaults to deterministic local execution.

### 2026-08-10 — Codex (GPT-5 / OpenAI) — proposed Portfolio Production Compiler architecture

Added, render-verified, and finalized the approved architecture proposal for
replacing fallback-only Build Preparation internals with one user-visible
five-operation production compiler. The final shape uses two normal structured
model calls plus one adaptive cross-route call, hybrid-capable routing,
optional/adaptable statically admitted resources, accurate responsive Pexels
renditions, exact local file/import context, semantic visual specifications, a
dedicated creative-character contract, a self-sufficient atomic R2 ZIP, a
lockfile-backed React target, and a small Render/Supabase/R2 hobby deployment
with later Cloudflare Pages publication. Recorded the not-yet-implemented
decision as D-010.

### 2026-08-10 17:51 +05:30 — Codex (GPT-5 / OpenAI) — build-preparation compiler, resources, fixture, provider config, tests

Bound every route packet to manifest-level resource decisions (requested intent,
local pack path, hash, dependencies, fallback, and custom-implementation
opportunity), added fixed system-font/Lucide context, and made fixture live
resource resolution explicit. Corrected the public shadcn v4 catalog endpoint,
made registry admission skip unsupported candidates, and removed routine
custom-composition noise from warnings so fixture output distinguishes real
provider/approval problems from valid code-generation work.

### 2026-08-10 - Codex (GPT-5 / OpenAI) - build-preparation fixture correctness and bundle download

Fixed VDD-to-Blueprint field mapping, semantic fixture hashing, fallback-resource
deduplication, and truthful memory/R2 metadata. Added a hash-verified streamed
fixture ZIP download endpoint and frontend control so testing never treats an
object key as a local executable path or requires persistent download storage.

### 2026-08-10 - Codex (GPT-5 / OpenAI) - build-preparation fixture and temporary frontend

Added a development-only fixture runner that compiles the checked-in Visual
Design output without touching session state, plus a story-driven
`/build-preparation-fixture` preview that displays the Blueprint, resource
decisions, route packets, warnings, and temporary bundle receipt. Why: isolate
pre-code package debugging from upstream approvals while keeping production
preparation strict and non-publishable fixture output explicit. The preview
also accepts pasted/uploaded VDD JSON, exposes request/error events, and lets
the tester copy or download the exact response.

### 2026-08-10 - Codex (GPT-5) - scripts/docker-entrypoint.sh

Changed the Docker runtime entrypoint to a LF-only POSIX `sh` script. The
slim Python image does not ship Bash, and CRLF in the original shell script
also appended a carriage return to the Alembic `head` argument. Docker Compose
now completes migrations and starts the API and worker successfully.

## Compacted history

### 2026-08

- 2026-08-10 — Codex (GPT-5) — Pexels resolution and preparation harness
- 2026-08-10 — Codex (GPT-5) — config/app.toml, config/app.docker.toml
- 2026-08-09 — Codex (GPT-5) — src/oryxenai/build_preparation/, API, worker, config, tests
- 2026-08-08 19:49 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — src/oryxenai/agents/visual_design_director/, src/oryxenai/db/repositories/visual_design_director.py, src/oryxenai/jobs/handlers/visual_design_director.py, src/oryxenai/api/routes/visual_design_director.py, src/oryxenai/api/dependencies.py, src/oryxenai/api/routes/__init__.py, src/oryxenai/jobs/registry.py, src/oryxenai/agents/shared/{registry,model_client}.py, src/oryxenai/core/settings.py, config/models.toml, config/app.toml, tests/, AGENTS.md, README.md, docs/architecture.md
- 2026-08-08 16:02 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — AGENTS.md, CODEX.md, CLAUDE.md, CHANGES.md, DECISIONS.md, README.md, docs/architecture.md
- 2026-08-08 (retroactive, pre-CHANGES.md history) — unspecified / unspecified — repo-wide

---

## Compaction procedure (read before appending if the file looks long)

**Trigger:** before appending a new entry, if this file is at or over
**500 lines**, compact first, in the same edit, before adding the new entry.
(500 lines keeps the file skimmable in one read — roughly 25-30 entries at
the compact 2-3 lines-plus-header the template above produces — while
giving enough headroom that compaction isn't triggered on every edit.)

**Procedure, run by whichever agent is about to append:**

1. Count entries under `## Recent changes`. Keep the most recent **20**
   entries exactly as-is — do not touch them.
2. For every entry older than the most recent 20, convert it to a single
   archive line using its own header line's date/time and summary:
   `- YYYY-MM-DD HH:MM — <Agent/Tool> (<Model/Provider>) — <area(s)> — <one-line summary>`
   (reuse the entry's existing fields; do not invent new wording).
3. Group archive lines under `## Compacted history`, in a `### YYYY-MM`
   sub-heading matching each entry's month. If a `## Compacted history`
   section and the relevant `### YYYY-MM` sub-heading already exist, append
   to them. If they don't exist yet, create `## Compacted history` once,
   above this "Compaction procedure" section and below `## Recent changes`,
   and add the needed `### YYYY-MM` sub-heading(s) under it.
4. Delete the full (now-archived) entries from `## Recent changes`, leaving
   only the most recent 20.
5. Recompute the `## Summary` block below from the full entry set (recent +
   compacted).
6. Append the new entry at the top of `## Recent changes`, per the template
   below.
7. Do not touch `DECISIONS.md` during this process — it has its own
   lifecycle and is never folded into changelog compaction.

**Entry template** (copy this block verbatim for every new entry, fill in
the fields, insert directly below the `## Recent changes` heading — i.e.
above the current newest entry):

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — <files/areas, comma-separated>
<One or two sentences: what changed and why, combined.>
```

Field notes:

- **Agent/Tool** — the coding tool/CLI in use (e.g. `Claude Code`,
  `Codex CLI`, `Antigravity`, `Cursor`), not a person.
- **Model/Provider** — the actual underlying model and provider (e.g.
  `GPT-5.6 / OpenAI`, `Grok-4 / xAI`, `GLM-4.6 / Zhipu`,
  `Claude Sonnet 5 / Anthropic`) — never omit; this is the field most useful
  for reconstructing "why did this look different" across sessions, and it
  costs almost nothing extra since it rides in the header line.
- **Files/areas** — real paths or directories touched, not vague
  descriptions.
- The body — factual, past tense, what changed and why in one or two
  sentences combined. The header line doubles as the one-line summary used
  during compaction, so write it to stand alone.

---

## Summary (as of last compaction — 2026-08-12)

- Total entries logged: 26 (20 recent, 6 compacted)
- By tool: Codex (20), Claude Code (5), unspecified/retroactive (1)
- By model/provider: GPT-5 / OpenAI (14), GPT-5 (provider unspecified) (4), OpenAI (model unspecified) (1), Claude Sonnet 5 / Anthropic (5), unspecified/retroactive (2)
- Last updated: 2026-08-12 — Codex (GPT-5 / OpenAI)
