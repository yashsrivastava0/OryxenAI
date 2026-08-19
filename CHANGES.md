# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-08-19 15:47 +05:30 - Codex (live provider run) - [3c1ff43] - Harden live Code Generator generation and runtime repair
Added a narrowly scoped JSON-object fallback for provider rejection of strict
dictionary schemas, encoding-safe approved-copy validation, semantic exclusion
of hidden/off-screen controls from geometry checks, and a bounded route CSS
touch-target repair with prompt guidance for future generations. Updated
AGENTS.md so explicit run/generation requests use configured live LLM/API calls
by default. Verified against the selected Build Preparation pack through a live
ready run, passed source/build/DOM/runtime gates, all route/viewports and
reduced-motion/unknown-route journeys, and promoted an atomic preview/export.

### 2026-08-19 13:49 +05:30 - Codex (model/provider omitted) - [8a85438] - Consume nested Build Preparation mirror output
Pointed Code Generator's local mirror configuration at the actual `output/live-build-preparation/build-preparation` pack directory. The requested pack is now discovered and admitted through the normal workflow; a live planner retry remains provider-consent blocked.

### 2026-08-19 13:26 +05:30 - Codex (model/provider omitted) - [6afd672] - Production Code Generator v2 and visual compiler
Connected explicit portfolio-session starts to exact verified Build Preparation artifacts, added structured creative comparison and experience-blueprint calls, compiled deterministic resource bindings and non-overlapping work ownership, and hardened local assets, nested routes, whole-site review, responsive geometry, reduced motion, staleness, and atomic preview retention/promotion. Verified the complete Code Generator Python surface, the clean Vite build/browser promotion path, frontend tests, scoped lint/format/type checks, migration head, scaffold typecheck/build, and offline admission of the selected pack; the broader repository still has unrelated provider-dependent and pre-existing type-check failures.

### 2026-08-18 23:55 +05:30 - Codex (GPT-5 / OpenAI) - [6bdcb13] - Selected verified Build Preparation output for Code Generator
Recorded the live-accepted pack `64801150-cb6d-4052-ae1e-2a30ab55fb20` as the current Code Generator working input, including its ZIP identity, route scope, local image/component/font bindings, projection hashes, R2 handoff distinction, and the static experience-timeline fallback. Marked the older ineligible pack as unusable.

### 2026-08-18 23:43 +05:30 - Codex (GPT-5 / OpenAI) - [da99302] - Build Preparation overview and Code Generator handoff context
Made generated `overview.md` a detailed consumer briefing that documents the pack authority files, local resource flow, route inventory, and handoff review without imposing screen, route, component, card, or layout quotas. Updated the live context prompt and Build Preparation documentation to preserve exact upstream coverage while leaving composition and portfolio information architecture to Code Generator; added regression coverage.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [273799b] - Reliable contextual visual enrichment and Code Generator handoff
Removed role-count truncation and the static provider request quota while retaining per-role retries, rate-limit handling, source validation, image-size limits, and closed-set selection. Added contextual queries, alternate image recovery, complete local component/image provenance bindings, aggregate enrichment admission diagnostics, and Code Generator protection against reacquiring known Build Preparation roles. Focused Build Preparation, Code Generator, and API tests pass; live acceptance repeated the configured model connection failure before provider lookup, so no readiness claim is made.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [cde016e] - Build Preparation live-run boundary fixes
Removed false component-quota execution gaps and reconciled model-selected resource IDs against the live provider closed set, preserving explicit fallbacks and diagnostics. Focused Build Preparation tests pass; the two-run live acceptance exposed the model-boundary defect on run 2, so no third live run was performed.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [42e92ec] - Build Preparation semantic live resource enrichment
Replaced cyclic quota-driven component derivation with semantic typed intents, live provider terms and diagnostics, closed-set alternate source fallback, and complete local Code Generator contracts and run analysis. Normal workflows stay live while offline fixtures are diagnostic-only; provider safety, provenance, hashes, and v3 admission remain fail-closed under D-029/D-030.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [8909c09] - Build Preparation visual resource intent enrichment
Normalized complete, partial, and missing VDD input with hash-stamped presentation assumptions derived from approved Content Architect sections. Added deterministic contextual image/component role compilation, one shared resource context packet, config-driven provider diagnostics, strict local usage contracts, truthful handoff counts/gaps, and frontend role/provider diagnostics. Verified 628 unit tests, 8 Build Preparation API tests, Ruff, compile, and JavaScript checks; the live-provider canary correctly failed closed because external keys were not configured.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [0bd8bb5] - Shared local Pexels/Pixabay image retrieval
Added first-class Pixabay alongside Pexels through one shared image service used by Build Preparation and Code Generator. Structured portfolio-aware intent, bounded provider fallback/dual search, 24-hour filesystem caching, rate-aware retries, deterministic ranking, selected-byte download, decoded-pixel validation, crop/resize/compression, hash deduplication, local provenance metadata, opt-in Unsplash, Docker cache sharing, and focused provider/materialization coverage are now wired without changing component retrieval.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [646a0bb] - Dynamic priority component retrieval
Added a shared deterministic retrieval policy for Build Preparation and Code Generator. Required component roles remain eligible, while optional roles are selected by importance, interaction-role novelty, and route/scene coverage within the per-run maximum; LLMs remain closed-set query/candidate rankers and selected components still fetch real recursive source. See D-030.

### 2026-08-18 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [3e2831c] - Cache-free multi-provider component retrieval
Added one shared direct HTTP/API and registry-JSON retrieval boundary for shadcn, Magic UI, Smooth UI, and Cult UI. Discovery is metadata-only; selected components are fetched recursively with strict host/path/dependency validation and provenance, with optional injected MCP transport, no provider-response cache, and 429/timeout/server-error handling. Wired Build Preparation and Code Generator to the four-provider allowlist and added the scaffold `cn()` utility with locked `clsx`/`tailwind-merge` dependencies; see D-029.

### 2026-08-17 22:30 +05:30 - Codex (GPT-5 / OpenAI) - [e3d80c2] - Detached Build Preparation input pickup and monitor readiness
The detached Build Preparation harness now auto-selects the newest matching Content Architect and Visual Design Director output from `Input-Output-Of-Engine`, supports JSON fenced in `.md` outputs, shows the resolved source paths in readiness, and retains configured-path fallback for later integration. Live verification reached packaging and R2 read-back; handoff remained correctly blocked because the approved VDD exposed zero image and component roles.

### 2026-08-17 22:20 +05:30 - Codex (GPT-5 / OpenAI) - [3479c40] - OpenAI provider diagnostics, Build Preparation fixture monitor, Code Generator planner
Preserved OpenAI-only profile selection and made provider connection failures actionable: Build Preparation now reports the endpoint host and retry guidance, while Code Generator distinguishes provider transport/auth/rate/server failures from invalid SitePlan output. Added focused regression coverage; no OpenCode profile is used by the active Build Preparation or planner paths.

### 2026-08-17 22:05 +05:30 — Codex (GPT-5 / OpenAI) — [2edc335] — Real provider-backed visual handoff
Removed generated-local/blank visual fallbacks from Build Preparation, added configured multi-image/component targets with VDD overrides, real Pexels/registry materialization gates, pixel/source quality checks, provider caching/deduplication/rate-limit diagnostics, explicit `VDD_EXECUTION_GAP` slots, Code Generator rejection of unreal visual resources, and truthful fixture counts/status. Offline fixtures are now reviewable but cannot claim a ready handoff without real provider bytes/source; see D-028.

### 2026-08-17 20:34 +05:30 — Codex (GPT-5 / OpenAI) — [7957f7e] — Best-pack readiness UI alignment
Updated the normal developer workspace readiness indicator and troubleshooting copy to use the server-authoritative best Build Preparation pack projection.

### 2026-08-17 20:31 +05:30 — Codex (GPT-5 / OpenAI) — [2903bd2] — Build Preparation resources, Code Generator coordination, verifier hardening
Unified pack-v3 route/execution admission across producer and consumer, added Fontsource/font and registry-aware component materialization with provenance, structured Build Preparation context/receipts, live Code Generator resource adapters, deterministic best-pack selection, durable server-side stage advancement, and the frontend’s truthful one-click flow. Hardened preview-gateway diagnostics, source/build gate reuse, infrastructure fail-closed behavior, migration state, and doctor exit reporting; verified 751 tests plus frontend checks, with only the external-provider verification canary remaining environment-dependent.

### 2026-08-17 17:09 +05:30 — Codex (GPT-5 / OpenAI) — [fffd253] — Code Generator workspace UI, pack admission, trusted shell, tests
Implemented the compact one-click portfolio workspace with semantic durable progress, newest eligible Build Preparation selection, route/viewport preview controls, and an advanced/debug disclosure. Added full v3 pack eligibility validation, truthful readiness blockers, deterministic no-write integration, scaffold reassertion for immutable preview shell files, and focused frontend/API/unit regression coverage.

### 2026-08-17 17:12 +05:30 — Codex (GPT-5 / OpenAI) — [9ed8fe4] — Code Generator checkpoint resume hardening
Reasserted the immutable scaffold shell after accepted-checkpoint restore, closing the stale-runtime path found during live verification and preserving the trusted preview router across resumed generation.

### 2026-08-17 15:46 +05:30 — Codex (GPT-5 / OpenAI) — [d23bc09] — AGENTS.md, DECISIONS.md, CHANGES.md
Established a cross-agent Git policy requiring every verified commit-sized task to end in a reviewed, task-scoped local commit while preserving unrelated dirty work and keeping pushes explicit. Added staging, verification, commit-message, overlap, and post-commit evidence rules; see D-027.

### 2026-08-17 15:19 +05:30 — Codex (GPT-5 / OpenAI) — [e35dd62] — src/oryxenai/agents/code_generator/, tests/, architecture documentation
Removed the duplicate Code Generator compatibility namespace, migrated internal tests to the canonical `core.*` implementations, and documented the registry planner/core ownership boundary. Deleted all package-root wildcard adapters and the unused generation-schema facade without changing runtime behavior; see D-026.

### 2026-08-17 13:29 +05:30 — Codex (GPT-5 / OpenAI) — [91aa906] — Build Preparation visual handoff, Code Generator source contract, preview/runtime smoke, timestamp export
Made required visual slots concrete by materializing deterministic local image/component assets, copied component source into an importable generated path, and rejected comment/manifest-only resource markers. Fixed nested preview asset bases, protected the trusted shell/design entrypoint, reduced the default browser pass to route/asset smoke, and changed exports to timezone-aware `HH-mm-DD-MM-YYYY` folders with collision-safe metadata; see D-025.

### 2026-08-17 11:20 +05:30 — Codex (GPT-5 / OpenAI) — [91aa906] — Code Generator DOM verification, Windows safety, contract prompts, portfolio export
Completed the standalone Code Generator live path from the Build Preparation v3 pack through a `ready` run, promoted preview, and run-scoped source/dist/metadata export. Added the normative generation contract and prompt alignment, Windows-safe filesystem retries, literal interaction/content anchors, offline approved-link assertions, and receipt-bound export metadata; production session integration remains deferred; see D-024.

### 2026-08-16 11:51 +05:30 — Codex (GPT-5 / OpenAI) — [5bf4b5f] — Code Generator Phases 1-4, Build Preparation, provider configuration, preview workflow, tests
Completed the standalone Code Generator development workflow through admission, planning, controlled acquisition, progressive source generation, verification, finite repair, and preview promotion, while aligning Build Preparation, model/provider configuration, durable jobs, migrations, developer UI, fixtures, and regression coverage with the new contracts. Production session integration and automatic pipeline chaining remain deferred.

### 2026-08-14 13:35 +05:30 — Codex (GPT-5 / OpenAI) — [c091282] — Code Generator core, shared provider, prompts, toolchain, developer UI, fixtures, tests
Refactored the live standalone Code Generator into core/, replaced weak/free-form planning contracts with typed, enforceable design and acceptance contracts, and corrected the provider path so canonical structured input is actually sent separately from trusted prompts. Reworked generation prompts for grounded advanced portfolio implementation, removed scaffold and simulated dependency installs, added real package-manager lockfile policy, readiness reporting, a rich privacy-safe v3 fixture, semantic source evidence checks, and focused regression coverage while preserving the registry mock and standalone Build Preparation boundary.

### 2026-08-14 10:47 +05:30 — OpenCode (GPT-5.6 / OpenCode Go) — [c091282] — Code Generator Phase 4 verification, preview, hardening, and toolchain
Implemented the standalone Phase 4 workflow: clean receipt-bound builds, source/build/DOM-runtime gates, finite diagnostic repair, immutable candidate storage, crash-safe idempotent preview promotion, isolated preview gateway, worker lease fencing, developer route/viewport preview controls, Docker/CI toolchain setup, and verification API/UI coverage. Production session integration and automatic chaining remain deferred.

### 2026-08-14 00:51 +05:30 — OpenCode (GPT-5.6 / OpenCode Go) — [c091282] — Code Generator Phase 3 source generation
Implemented standalone Phase 3 progressive source generation on top of the completed Phase 1/2 workflow: trusted React/Vite/TypeScript scaffold, isolated workspaces, source manifests and policy checks, immutable checkpoints, strict foundation/route/composition/integration operations, emergent receipt-bound acquisition, source/type repair, durable generation job, API, developer UI, migration, and completion-gate tests. Phase 4 verification/preview and production session integration remain deferred.

### 2026-08-13 22:30 +05:30 — Codex (GPT-5 / OpenAI) — [4c4f51d] — Build Preparation pack-v3, standalone Code Generator admission, configuration, fixtures, documentation
Replaced the Code Generator handoff with pack-v3: canonical route storage, hash-covered execution slots, resource ledger/recipes, readiness diagnostics, and strict v3 fixture/upload admission now prevent prose-only or ambiguous resource decisions. Added constrained provider policy/pins and privacy-safe recipe bindings while keeping source generation, main-flow wiring, and emergent acquisition outside this work; see D-018.

### 2026-08-13 20:22 +05:30 — Codex (GPT-5 / OpenAI) — [d0a6b1d] — Content Architect, Visual Design Director, Build Preparation, frontend, tests
Defined and enforced a safe public-scope handoff: Content Architect now defaults ordinary supplied portfolio facts to neutral publishable copy while retaining explicit restrictions, rejects incomplete approved routes, and offers an in-context revision action. Visual Design Director receives and emits only CA-approved routes with canonical identity, and Build Preparation tests cover mixed review/public scope plus canonical route metadata; see D-017.

### 2026-08-13 19:41 +05:30 — OpenCode (gpt-5.6-luna / OpenCode Go) — [d0a6b1d] — src/oryxenai/agents/build_preparation/service.py
Fixed the session Build Preparation projection so the pack-v2 compiler receives approved Content Architect claim grounding, story/handoff data, and the Visual Design Director's shared visual systems. This prevents the durable session path from failing with `PackContractError` even when the detached approved-input fixture succeeds.

### 2026-08-13 19:22 +05:30 — OpenCode (glm-5.2) — [d0a6b1d] — Content Architect approval guard + Build Preparation route diagnostics
Added a producer-side guard so Content Architect approval refuses to enter APPROVED when no `route_plan` entry is `publication_status="approved"` (state machine `NoPublishableRoutesError`; service 409 `CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES`), preventing the dead Build Preparation pack that previously surfaced as `BUILD_PACK_V2_CONTENT_ROUTES_MISSING`. Split that Build Preparation pack-v2 failure into `BUILD_PACK_V2_CONTENT_ROUTES_EMPTY` vs `BUILD_PACK_V2_CONTENT_ROUTES_NONE_APPROVED` and propagate the dropped route_ids + their statuses into the issue `details`; enriched Stage 0 `scope_compiled` with `dropped_routes` and named the per-route status in exclusion warnings. `route_plan` entries are never mutated, preserving the cross-agent pending-is-gated invariant. See D-016.

### 2026-08-13 16:17 +05:30 — OpenCode (GPT-5.6 / OpenAI) — [4c4f51d] — Code Generator Phase 2 acquisition, migrations, API, frontend, tests
Implemented the standalone Phase 2 resource/dependency acquisition boundary: strict request, candidate, receipt, ledger, delta, adapter, and dependency contracts; safe offline-testable materialization; durable `code_generator.acquire` execution with idempotent redelivery; feature-gated API/UI projections; node_modules lifecycle policy; and Phase 1 completion-gate backfill. Corrected the overlong Phase 1 Alembic revision so the complete migration chain applies to PostgreSQL.

### 2026-08-13 15:10 +05:30 — Codex (GPT-5 / OpenAI) — [4c4f51d] — Build Preparation pack-v2 contracts, VDD validation, config, tests
Implemented D-013's versioned pack-v2 boundary: deterministic site/visual/provenance projections, hash-covered packaging, exact consumer admission, source-policy safeguards, and diagnostic-only compatibility for incomplete legacy harness inputs.

### 2026-08-13 15:10 +05:30 — Codex (GPT-5 / OpenAI) — [4c4f51d] — Code Generator Phase 1 standalone planning, persistence, API, developer UI, tests
Implemented the feature-gated fixture/upload admission and durable `code_generator.plan` workflow with independent run/event persistence, strict structured `SitePlan`/`WorkGraph` validation, safe receipts/issues, and a Jinja/vanilla-JS planning page; no source generation, resource acquisition, preview, or session-flow integration was added.

### 2026-08-13 12:35 +05:30 — Codex (model/provider omitted) — [4c4f51d] — docs/code-generator-architecture/
Added the four-phase, approval-gated Code Generator execution guide: standalone admission/planning and developer UI, controlled acquisition, progressive generation, then verification/repair/preview.

### 2026-08-13 12:09 +05:30 — Codex (GPT-5 / OpenAI) — [4c4f51d] — AGENTS.md, docs/code-generator-architecture/, DECISIONS.md, CHANGES.md
Superseded the screenshot/vision-review Code Generator draft with D-015's progressive text-only generation pipeline. Added planning-time and emergent resource acquisition through trusted adapters, React/Vite workspace isolation, three lean gates, and compiler/runtime-guided finite repair.

### 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI) — [958b4d8] — docs/code-generator-architecture/, DECISIONS.md, CHANGES.md
Replaced the exploratory Code Generator proposal with a decision-complete v1 handoff covering Build Preparation boundary repair, bounded generation, exact verification, and single-current-preview promotion.

### 2026-08-13 09:48 +05:30 — Codex (GPT-5 / OpenAI) — [958b4d8] — docs/code-generator-architecture/
Refined the Code Generator proposal around ordered product pillars, deterministic orchestration, adaptive model policy, worker topology, and isolated live preview promotion.

---

## Compacted history

### 2026-08
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

## Summary (as of last compaction — 2026-08-17)

- Total major milestones logged: 23 (19 recent detailed, 4 compacted eras)
- By tool: Codex (18), OpenCode (4), Claude Code (1)
- By model/provider: GPT-5 / OpenAI (17), GPT-5.6 / OpenCode Go / OpenAI (3), glm-5.2 (1), mixed/unspecified (2)
- Last updated: 2026-08-17 — Codex (GPT-5 / OpenAI) & Antigravity (Gemini 3.7 Flash)
