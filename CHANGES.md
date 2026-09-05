# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-06 01:19 +05:30 - Codex (GPT-5 / OpenAI) - [68f1cd1] - pipeline: make stalled agent runs observable and recoverable

Added safe job lifecycle metadata, foreground scheduling and lease recovery,
local metadata-only test traces, and deterministic Discovery questions for
substantive long pastes. Identical completed starts now return the stored
result without duplicate job/model work; records D-073.

### 2026-09-06 01:08 +05:30 - Codex (GPT-5 / OpenAI) - [861e981] - discovery: recover stalled jobs and support stop

Added foreground scheduling and stale-lease recovery so Discovery requests
cannot remain behind an abandoned model-generation job, plus durable stop
fencing at the Discovery API, state, run, and worker-result boundaries.

### 2026-09-06 01:06 +05:30 - Codex (GPT-5 / OpenAI) - [cdf7a18] - pipeline: cancellable stage jobs and safe trace export

Added durable cancellation fencing for Content Architect and Visual Design
Director, a reusable first-three-stage job projection, bounded client trace
export/copy support, and regression coverage.

### 2026-09-05 23:08 +05:30 - Codex (GPT-5 / OpenAI) - [963375b] - deployment: record R2 readiness

Recorded the user's report that R2 storage and credentials are already
available, while distinguishing the VM-side configuration still pending and
preserving the rule that no R2 secret values enter chat or source control.

### 2026-09-05 22:53 +05:30 - Codex (GPT-5 / OpenAI) - [caa8f33] - frontend: complete authenticated three-stage handoff

Completed the authenticated Preact product handoff for the first three
explicit stages. Fixed progressive Discovery answer persistence and retry
classification, surfaced stage-start failures, scoped admin session hints,
cleared private drafts/idempotency state on logout, built the frontend bundle
inside Docker, and extended the opt-in live smoke path through Content
Architect and Visual Design Director with explicit approvals.

### 2026-09-05 22:25 +05:30 - Codex (GPT-5 / OpenAI) - [7a0c68f] - deployment: record local environment audit findings

Recorded the redacted local `.env` audit in the live deployment checkpoint:
the file is Git-ignored and populated, but duplicate authorization variables
and one malformed line must be cleaned before a separate production `.env` is
created on the VM. No secret values were displayed or copied.

### 2026-09-05 22:19 +05:30 - Codex (GPT-5 / OpenAI) - [a2a8a60] - deployment: record live Azure VM and SSH checkpoint

Recorded the completed Azure VM provisioning, final networking/NSG settings,
current public/private addresses, cross-device SSH handoff, completed Ubuntu
package preparation, and the remaining Docker/application deployment gates.
Marked the older wizard document as historical so future agents use the live
post-creation checkpoint.

### 2026-09-05 21:15 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [d6cde91] - code-generator: resource acquisition, generation_orchestrator, image_retrieval, jobs/handlers, development_schemas, tests

Root-caused two fresh live-run failures to a genuine resource-acquisition
reliability defect rather than patching symptoms: Build Preparation's
pinned Pixabay candidate URLs can go stale (signed/time-limited) between
pin time and Code Generator's later acquisition, confirmed by directly
re-requesting the exact pinned URLs from a real run against the live
Pixabay API. Acquisition's pinned-candidate path now falls back to one
bounded live search on materialize failure; also stopped requesting
Pixabay's approved-accounts-only `imageURL`/`fullHDURL` fields as defense
in depth. Separately fixed: the mid-generation polish loop no longer
re-attempts an identical structurally-unfixable finding every round
(ledger-confirmed recurrence at round 1 and round 4 of the same run); the
`cannot_complete` log line now surfaces the model's real reason instead of
dropping it; and the planner's CSS-length/token-name validators normalize
common mechanical mistakes instead of only rejecting them, since the
existing corrective-feedback retry had already failed twice on the
identical mistake live. See D-072.

### 2026-09-05 19:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [34c638b] - catch a silent token collision and sharpen two repair diagnostics

Live testing of D-068's fixes across 6 fresh live runs surfaced three more real bugs, each found only by actually completing a run. (1) The model transcribes an opaque hash-like content-key suffix with a one-character typo and repeats the identical typo across every repair round; `SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING` now searches for a same-prefix near-miss call already in the source and names it directly, giving the repair model something concrete to fix instead of guessing. (2) `SOURCE_BLUEPRINT_MOVE_MARKER_ONLY` had a generic message, unlike its mid-generation sibling which already names the exact selector/properties — the final-repair model reported `cannot_complete` on it 3 rounds running; now states the same concrete facts. (3) A genuine silent-corruption bug: a raw color token and a shadcn theme binding slot sharing the same literal name (both commonly "accent") compile to the identical `--color-accent` CSS custom property; the alias silently overwrites the real color with no error anywhere, surfacing only as an opaque whole-site review finding after a full generation pass that otherwise scored 4/4/4/4/4. Added the same collision check at both the schema level (`DesignTokenSystemV4`'s validator, catching it the instant the planner responds — confirmed live) and the token compiler (defense-in-depth for any blueprint reaching compilation via `model_copy`, which doesn't re-validate), plus `planner.md` guidance since the model repeated the identical collision on the very next live attempt even after the validator started rejecting it. Also confirmed live: D-068's `cannot_complete` polish-loop resilience fix fired multiple times across several runs without crashing, correctly falling through to the pre-existing bounded `INTEGRATION_REVIEW_UNRESOLVED` terminal state. Verified: 232 code_generator unit tests (2 new), ruff/mypy clean. Live-verified over 6 real runs (~$0.3-1.0 this batch, ~$0.4-1.2 combined with D-068's runs, well within the $5 session budget); one run reached final review with all 5 scores at 4 and exactly one blocking finding — the closest yet, not a clean pass. Full end-to-end success (a promoted preview) was not reached this session; remaining variance is concentrated in whole-site resource-placement rendering and generic model non-determinism on already-prompted-against rules, not in control-flow/validation gaps. Records D-071.

### 2026-09-05 16:40 +05:30 - Codex (GPT-5 / OpenAI) - [8a2066a] - enforce a pre-call ceiling for explicitly capped live runs

Added a provider-neutral `BudgetedModelClient` that serializes structured calls, reserves a conservative prompt plus maximum completion charge before transmission, releases unused reservation only after valid usage telemetry, and consumes the reservation on failures or unknown usage. Added focused tests for refusal-before-call, temporary output caps, profile restoration, and failure consumption. The authorized resume validation run completed Discovery at `0.256180` recorded configured credits, but Content Architect returned `MODEL_EMPTY_OUTPUT`; because an earlier interrupted attempt had no usage receipt, no later stage was retried against the hard ceiling. Records D-070.

### 2026-09-05 15:23 +05:30 - Codex (GPT-5 / OpenAI) - [5b86779] - add scoped long-lived model-result caching and cache receipts

Added owner/session-scoped PostgreSQL caching for validated structured results across Discovery, Content Architect, Visual Design Director, and Build Preparation, with a six-month TTL, single-flight leases, provider prompt-cache hints, usage/character/cost telemetry, and redacted local exports. Added truthful cached-response notices to both frontend control surfaces; records D-069. Live execution of the supplied resume remains pending explicit authorization to send the document to the configured external provider.

### 2026-09-05 14:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [aedf96c] - close two repair control-flow gaps, complete caching, add motion catalogue

Root-caused D-067's frontier blocker (`QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on a single easily-fixable finding) to a genuine control-flow gap, not a capability/budget problem: `_attempt_repair`'s post-repair whole-site re-review rejection raised terminally from *outside* its own bounded retry loop, discarding 5 of 6 available repair rounds. Added exactly one bounded extra repair+re-review attempt (never open-ended); refactored into `_run_bounded_repair`/`_rereview_after_repair`/`_diagnostics_from_quality_findings` helpers, 2 new + 1 unchanged regression test prove the exact bound. Live testing surfaced the identical class of gap one stage earlier: `_review_and_polish`'s owner-scoped repair call killed the whole run outright on a `cannot_complete` response with zero retry, even though the outer polish-round loop (5 rounds, D-067) exists precisely to give a different round another try — fixed the same way (skip that owner for the round, let the bounded loop continue), with a matching regression test. Completed prefix-caching coverage for the whole-site integration review — the single most expensive, most-repeated call in the pipeline (up to 8x/run, up to ~600,000 chars) had zero `request_context` support, unlike 4 of the other 5 call sites — with a careful `INTEGRATION_REVIEW_KEY_ORDER` (source_manifest/round last, since they change every round) plus a stable per-run `prompt_cache_key`; confirmed live via non-zero `cached_prompt_tokens`. Added a deterministic motion-pattern catalogue (`core/motion_pattern_catalogue.py`, 3 patterns: reveal-fade-rise, reveal-clip-lines, stagger-group) and an optional `MotionBeatV4.pattern_id`, extending the codebase's existing image/font/component catalogue-and-select precedent to motion — confirmed live, the planner set `pattern_id` on a real beat on its first attempt; required fixing a load-bearing prompt contradiction (`route_batch.md`/`route_compose.md` explicitly forbade the `.reveal`/`.stagger` class names this introduces). Added advisory screenshot capture to DOM/runtime verification (zero extra cost, the browser context is already open) since the pipeline had never once captured visual evidence of a generated portfolio, and captured raw model `usage` at 3 previously-discarding call sites (director, redirect-director, final-repair), with a `RepairReceipt` hash-exclusion-set fix so existing persisted receipts don't break on load. Also fixed, as a safety measure: `tests/integration/test_build_preparation_worker.py`'s one worker test built no mock model client and was silently spending real provider budget on every plain `pytest` run — gated behind the project's own existing `RUN_LIVE_*` opt-in convention (`tests/live/`). Verified: 231 code_generator unit tests, 10/14 code_generator integration tests (4 pre-existing `PLAN_SECTION_COVERAGE` failures confirmed unrelated via `git stash` on unmodified HEAD, not touched this session), ruff/mypy clean. Live-verified over 2 real runs against the eligible pack (~$0.06-$0.21 total at published Luna rates); a third and fourth attempt were killed by real system memory pressure before reaching final verification, so the first fix's exact retry firing was not directly witnessed live this session, though its regression tests prove the bound precisely. Records D-068; `code generator issues.md` rewritten with the current state and next verification target.

---

## Compacted history

### 2026-09
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [0ce8ecd] - Added the canonical first-deployment path (one Azure Linux VM, Docker Compose, Supabase auth, Cloudflare R2, Caddy HTTPS) with a production-overlay runbook; no application code changed.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [903477a] - Added a browser-agent handoff for resuming Azure deployment after a lost portal session, with exact VM wizard values and billable-action pause points.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [e1173df] - Recorded the live Azure VM wizard checkpoint (resource group created, wizard paused at Networking) as the canonical deployment-status handoff.
- 2026-09-05 - Antigravity (Gemini 3.8 Flash / Google) - [9fabd58] - Consolidated all agent outputs under a single canonical `output/` directory, removing deprecated prebuild-output and 54 empty/corrupted Build Preparation runs.
- 2026-09-04 - Claude Code (Sonnet 5 / Anthropic) - [112d1a6] - Added commit-cadence policy to the multi-agent protocol after a near-loss incident.
- 2026-09-04 - Claude Code (Sonnet 5 / Anthropic) - [6ab319a, 5d8a93b, 6cec47b] - Synced Build Preparation/Code Generator docs with the Markdown-brief pipeline, persisted active session client-side, and fixed OpenAI key diagnostic reporting.
- 2026-09-04 - Codex (GPT-5 / OpenAI) - [5b84673, 871f960] - Hardened migrated Code Generator generation after the Build Preparation brief-contract migration.
- 2026-09-04 - Codex (GPT-5 / OpenAI) - [1f0ed68] - Migrated Code Generator to consume Build Preparation's Markdown brief contracts directly.
- 2026-09-04 - Codex (GPT-5 / OpenAI) - [389fa28] - Shipped the authenticated three-agent editorial studio.
- 2026-09-04 - Antigravity (Gemini 3.8 Flash / Google) - [1627f5d] - Fixed four live-observed Build Preparation brief/image-retrieval defects and optimized model prompt packet size; verified live end to end.
- 2026-09-04 - Antigravity (Gemini 2.5 Pro / Google) - [a8ad4e7] - Pruned 11 hallucination-prone AI skills; rebuilt Build Preparation into a 1-model-call zero-byte-download pipeline producing two Markdown briefs directly on session state (D-062), superseding a dozen prior pack-era decisions.
- 2026-09-03 - Antigravity (Gemini 3.8 Flash / Google) - [222419a] - Documented a 5-user zero-cost 24-month deployment runway using the GitHub Student Developer Pack.
- 2026-09-03 - Antigravity (Gemini 2.5 Pro / Google) - [28b8b1c] - Delivered a zero-scroll studio command center, fixed an engine-polling invocation bug, and added live progress monitors.
- 2026-09-03 - Antigravity (Gemini 2.5 Pro / Google) - [2cc2cb9] - Redesigned the studio hero into an agency-grade dark atelier aesthetic and inverted the user intake journey.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [c461b49] - Raised the generated-source size ceiling from 8MB to 32MB after direct reproduction showed legitimate responsive-rendition bloat, not a bug.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [5b4a33c] - Removed duplicate deferred-image renditions that caused source bloat and exceeded the 8MB generation ceiling.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [13cc78b] - Extended Build Preparation pack retention to a long horizon after compacting reference-only packs; recorded D-061.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [6bd8a2d] - Aligned deferred-resource materialization with planned pack paths, preserving emergent-resource fallback behavior.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [c3597d5] - Fixed deferred resource byte acquisition for files, fonts, and registry components after live Track 1 failures.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [b132a9a] - Reconciled Build Preparation pack contract docs with the `deferred_materialized` resolution type and fixed nonexistent-file references.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [7fb421f] - Removed confirmed duplication in the handoff report and fixed a doubly-nested `provider_receipt` bug across three materialization paths.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [1c175c6] - Code Generator fetches bytes directly for `deferred_materialized` slots via pinned candidates, completing D-060 Track 1's core mechanism.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [a476452] - Image/font/component materialization defers bytes to Code Generator instead of embedding them in the pack.
- 2026-09-03 - Claude Code (Sonnet 5 / Anthropic) - [8c7e994] - Root-caused a 10/10 live Code Generator failure campaign to genuine pack bloat (not planner complexity, which only reads 6 files) and added `deferred_materialized` as a sixth resolution type, additive only.
- 2026-09-02 - Antigravity (Gemini 2.5 Pro / Google) - [9b5ea36] - Frontend Phase 5 hardening/cutover: safe storage, ErrorBoundary, verified Preview surface with postMessage handshake, responsive layout system, canonical Preact shell default.
- 2026-09-02 - Antigravity (Gemini 2.5 Pro / Google) - [f9e8eef] - Frontend Phase 3: Build Preparation/Code Generator progress adapters mapping runtime substages to honest semantic milestones, no fake percentages/ETAs.
- 2026-09-02 - Antigravity (Gemini 2.5 Pro / Google) - [47a57b0] - Frontend Phase 2: app shell, Discovery conversation surface, Content Architect/Visual Design Director review adapters, Editorial Swiss styling (D-059).
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [efca5de] - Documented a ten-run live Code Generator campaign against the eligible Build Preparation pack; neither historical blocker recurred, no code changed.
- 2026-09-02 - Claude Code (Sonnet 5 / Anthropic) - [20f72e2, 3099e1c, eaa7390, 7292f2c, d3cc095] - Four live-run bugfixes in one afternoon: retry on rejected source validation, dedupe font-face rules, allow negative shadow tokens, persist true repair-round counts, retry final repair within budget (D-058).
- 2026-09-03 - Antigravity (Gemini 2.5 Pro / Google) - [e78e70b] - Elevated the Studio UI/UX into an Editorial Architectural Atelier (ArchitecturalCanvas drafting-grid interaction, persona-based intake, live telemetry) and fixed a detached-mode /app infinite reload loop.
- 2026-09-02 - Claude Code (Sonnet 5 / Anthropic) - [082d179, 375aae3] - Added SPA fallback redirects to the react-vite-v1 scaffold and threaded image alt-text/focal-point/placement into usage_contract (the first two of the seven pre-D-060 live-run fixes).
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [280982e, ae17373] - Frontend research package and implementation blueprint (authenticated journey, information architecture, route/API/adapter/component contracts, Preview UX, visual system, performance/rollout budgets).
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [e8c6b55, 749022f, d971764, 08633e6, 97cdada, dfce00f, c0c1f67, a622d7d, 5f4be9a, b760acb] - Hardened Code Generator V4 admission, distinctive move floors, structural sameness detection, shadcn Tailwind v4 theme bridge, and retired legacy resource filenames.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [1cf313f] - Final verification repair usage is bounded by diagnostic group with a shared run-wide ceiling and fail-closed V4 repair responses.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [234a05d] - Restored dedicated Code Generator role profile bindings while keeping routing provider-neutral and configuration-owned.
- 2026-09-02 - Codex (GPT-5 / OpenAI) - [aecfe40] - Aligned V4 selector evidence and responsive image-size contracts with executable source validation.
- 2026-09-01 - Codex (GPT-5 / OpenAI) - [d41eba1, b780266] - Hardened Code Generator generation, source evidence, repair, and polish contracts; fixed native PostgreSQL role alignment.

### 2026-08
- 2026-08-28 - Claude Code - [557201b, 2a4a345, c354841, 5a89eb0] - Root-caused accepted-mode retry failures, made fresh-generation envelopes reject acceptance, and kept invalid results out of the cache.
- 2026-08-28 - Claude Code - [664d88e, 86824a7, 8f50f4b] - Tightened V4 token/font contracts and preserved real quality-review diagnostics through bounded repair.
- 2026-08-28 - Codex - [5dc23b2, 65801b7, 4c8f361, 1b447a4] - Preserved planner-owned route identities and exact repair-envelope discriminators across V4 audit and repair paths.
- 2026-08-28 - Codex - [17fd5e3, f20f5c5, a63162d] - Added standalone verification retry/resume and persisted successful integration-polish checkpoints.
- 2026-08-28 - Codex - [f72ab5e, bf0e076, cbe4491, 20ea8b8] - Bounded repair/composer context to active ownership and authoritative files, resolving repeated context-limit failures.
- 2026-08-28 - Codex - [bb9454e, 93771b9, 0b46913, eb55728] - Hardened static source-audit resolution, trusted import maps, route anchors, and stale-checkpoint reopening.
- 2026-08-28 - Codex - [958b27a, 27b9679, 90f2a82, 253b1fa] - Added Windows toolchain launch fallbacks and preserved native start-failure diagnostics.
- 2026-08-27 - Codex - [caead48, d4fe70f, 1e3610e] - Made optional dependency installation transactional, route identity deterministic, and native launcher paths reliable.
- 2026-08-27 - Codex - [78ee3ea, e945f54, b92a86c] - Removed dead Code Generator foundation routing, added the default preview gateway health path, and repaired a detached-run PostgreSQL/work-graph mismatch.
- 2026-08-26 - Claude Code / Codex - [b4f7daa, 9b2d28f, e5d55f9, 8a918f3] - Fixed detached authorization advancement, V4 font-role matching, actionable database diagnostics, and alternate native-origin admission.
- 2026-08-26 - Codex - [7c44add, 9b39fe3] - Added the detached Code Generator control room, safe generation receipts, profession-aware resources, and provider/rate-limit guards.
- 2026-08-25 - Claude Code - [5d6886a, 2f9403b, ed9de3b] - Added provider-specific credit/rate handling and bounded alternate-candidate acquisition for components.
- 2026-08-25 - Codex - [40d0477, 53cd913, 87cad46, b70dde2] - Completed detached auth/build-preparation routing and made its frontend follow configured pipeline mode.
- 2026-08-25 - Codex - [c9f0a95, 62166f3, 5f272b3] - Hardened live Build Preparation recovery, bounded deterministic-contract retries, and migration/fixture diagnostics.
- 2026-08-25 - Codex - [9055cc3, c19e4a1, 5b5df50, 2614bde] - Centralized provider-neutral model runtime, profile preflight, retry/timeout policy, redacted receipts, and source-bound stage checkpoints.
- 2026-08-25 - Codex - [15cf585, 540d33a] - Added config-driven detached development mode and the canonical native/Docker development runbook.
- 2026-08-24 - Codex - [a39bd7e, 563b2a6] - Reduced first-three-agent latency on the configured provider and forced account selection after Google sign-out.
- 2026-08-24 - Codex - [3b3ed9f, 456db9c, 9b95baf, bf8f63d] - Routed live four-agent profiles through configured providers and recorded both a materialized Build Preparation result and a credit-exhaustion stop.
- 2026-08-24 - Codex - [e70b6ab, dddc1ba, 449b379, c5b5821] - Opened Google registration admission and hardened Supabase/PKCE redirect and admin-API readiness.
- 2026-08-24 - Codex - [b17227c, 90d5dfe, d288077, 48e5f6c] - Implemented authentication Phases 1–4: administrator lifecycle, entitlements/fencing, session ownership, and the Google-only foundation.
- 2026-08-23 - Codex - [c9ad71d, 0f9bc0d, a03ba6f, 5ca0b85] - Delivered authentication research/handoff and Code Generator V4 source, runtime, preview, and retry foundations.
- 2026-08-21 - Codex - [3437075, 26890c5, 5fcbdd4, 1b37748, 0b7a806, 7eac824] - Added V4 quality/read-back gates, provider contracts, standalone/hosted architecture, runtime verification, and atomic promotion.
- 2026-08-21 - Codex - [0240f57, b6a2be5, 0e965fd] - Documented metadata-only observability, first-three-agent startup recovery, and the Code Generator provider contract.
- 2026-08-20 - Codex - [f726d03, 3ced105, 8cdbfb8, 6e2c072] - Added the native provider adapter and repaired Docker workspace, route-generation, TypeScript, and browser/runtime verification paths.
- 2026-08-20 - Codex - [e8d6ec1, 86b3e8d] - Added delegated Build Preparation acquisition and the design-neutral V3 Code Generator with typed tokens, trusted systems, and route ownership.
- 2026-08-19 - Codex - [8259231, a01c030, 33b7113, 237e0ed] - Verified live Build Preparation/Code Generator handoffs, fixture execution, response schemas, R2 read-back, and preview/export recovery.
- 2026-08-19 - Codex - [45eafdc, 3c1ff43, 8a85438, 6afd672] - Added reusable agent runbooks and production Code Generator v2 with provider fallback, source validation, responsive repair, and atomic preview.
- 2026-08-18 - Codex - [6bdcb13, da99302, 273799b] - Established the verified Build Preparation pack identity, authority files, resource flow, contextual enrichment, provenance, and reacquisition guards.
- 2026-08-13–14 - Codex - [4c4f51d, d0a6b1d, 958b4d8] - Defined Pack-v3/v2 and Code Generator admission, progressive generation, workspace isolation, verification, repair, and preview architecture.
- 2026-08-12 - Codex - [0174a5b, 7c4580f] - Added Code Generator architecture research, Build Preparation admission/quality handoff, and the shared agent workspace UI.
- 2026-08-11 - Codex / Claude Code - [ea2267f, 39d16cf] - Rebuilt Build Preparation as Agent #4 with manifests, R2 storage, worker persistence, and provider fallbacks.
- 2026-08-10 - Codex - [d4a4556] - Added the initial Portfolio Production Compiler, Pexels integration, and fixture preview.
- 2026-08-08–09 - Codex / Claude Code - [bdc8822..a75810a] - Added the initial Discovery, Content Architect, and Visual Design Director agents, durable PostgreSQL queue, and core platform scaffolding.
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

## Summary (as of last compaction — 2026-09-06)

- Recent detailed entries retained: 12
- Compacted milestone bullets: 70
- Last updated: 2026-09-06 01:19 +05:30 — Codex (GPT-5 / OpenAI)
