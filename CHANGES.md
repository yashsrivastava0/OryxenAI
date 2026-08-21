# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-08-21 - Codex (GPT-5 / OpenAI) - [b6a2be5] - First-three-agent startup recovery runbook
Updated `docs/run/run.md` with the current migration head, Docker engine and
stale-worker recovery, the guarded empty-database migration replay, and the
verified API/worker/frontend startup state. The instructions preserve the
PostgreSQL volume and unrelated dirty worktree changes.

### 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI) — [1b37748] — docs/run/run.md, standalone Code Generator Docker runbook
Documented the isolated Code Generator development workflow: local Docker
overlay and database setup, API/worker/preview-gateway startup, shared
workspace debugging, readiness checks, UI/API usage, output locations, and
safe shutdown/troubleshooting.

### 2026-08-21 — Codex (GPT-5 / OpenAI) — [0b7a806] — Backend-only Docker, hosted shared previews, and source-linked Code Generator debugging
Implemented D-039: generated portfolios remain portable Vite/React source plus verified `dist/` with Docker artifacts excluded from exports; hosted previews use configurable S3-compatible immutable storage and conditional promotion pointers; local development keeps filesystem storage; readiness fails closed when preview storage is unavailable; and the developer UI/API can open bounded accepted-source slices from file/line diagnostics. Added the free-host deployment contract covering Render-like ephemeral filesystems, worker limitations, managed PostgreSQL, private object storage, and the shared preview gateway.

### 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI) — [7eac824] — Code Generator generation, source/runtime verification, build isolation, preview promotion
Hardened the provider-to-preview path with config-compatible structured output, bounded semantic/schema retries, source-only route workspaces, serialized package installs, deterministic route/content/interaction normalization, pack-resource materialization, writable browser/runtime environments, stale-artifact rejection, and diagnostic candidate-gateway failures (D-038). Verified two live generations from pack `20-35-19-08-6d3c4909` reached `ready` with all source/build/DOM gates passing and stable previews returning HTTP 200.

### 2026-08-21 - Codex (live provider run) - [0e965fd] - Code Generator provider contract, planner admission, Docker workspace portability
Added config-driven Anthropic wire capabilities, no-context provider preflight, safe provider diagnostics, typed-mapping schema fallback, bounded planner validation retry, exact pack selection receipts, frontend preflight/error states, and Docker runtime repository-root fallback. The live exact-pack run now passes provider preflight, planning, and acquisition; the remaining route-builder attempt is still provider-backed and bounded by the existing durable job policy.

### 2026-08-20 - Codex - [f726d03] - Add Claude Sonnet 5 Code Generator provider
Added an optional native Anthropic Messages API adapter with schema-guided
structured output, extended-thinking budgets, usage normalization, provider
retry/error handling, and lazy `ANTHROPIC_API_KEY` resolution. Only the Code
Generator profiles now target `claude-sonnet-5`; all upstream agents retain
their existing providers.

### 2026-08-20 - Codex (live Docker run) - [3ced105] - Restore standalone Code Generator Docker runtime
Accepted the configured system Chromium executable in standalone readiness,
finalized completed durable stage attempts before advancing, and added focused
coverage. The existing standalone stack reached live route generation from an
eligible Build Preparation pack; the provider then failed closed with
`insufficient_quota`.

### 2026-08-20 - Codex (live Docker run) - [8cdbfb8] - Complete Docker route generation
Fixed the Docker generation path so npm's disposable `node_modules/.bin`
symlinks do not fail workspace safety checks, route-batch waves retain their
already-satisfied foundation dependency, and isolated route workspaces retain
the receipt-bound toolchain for real typechecks. Focused Code Generator tests
and Ruff passed; the live run remains provider-backed and fail-closed.

### 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [6e2c072] - TypeScript source audit and exact runtime verification
Added the V3 source-contract audit for local imports/exports, route landmarks,
section and interaction ownership, trusted SharedSystems, forbidden network
code, and executable resource usage. Strengthened browser verification with
exact route/section/interaction outcomes, mounted-route handling, accessibility
state, local-resource, and non-empty evidence checks.

### 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [e8d6ec1] - Build Preparation pack-v4 delegated acquisition
Added explicit opt-in pack-v4 delegation after upstream resource attempts,
closed provider/candidate policy, strict v3/v4 reader compatibility, and
deterministic delegated image/font/component requests using the existing local
retrieval and provenance boundary.

### 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [86b3e8d] - Design-neutral Code Generator V3 generation
Added typed ExperienceBlueprintV3 tokens, trusted behavioral SharedSystems,
deterministic token/content compilation, route-batch ownership, isolated
parallel scheduling, and prompt/source regressions that remove generic
scaffold styling and duplicate shell ownership.

### 2026-08-20 00:00 +05:30 - Codex (GPT-5) - [0c4901f] - Add fenced stage attempts and immutable workflow artifacts
Added the Code Generator reliability spine: normalized stage-attempt rows and
partial active-attempt fencing, trace/contract metadata on runs and events,
safe retry/input/repair classification, worker release/readiness metadata,
content-addressed local and R2-compatible workflow artifact repositories, and
phase-level regression coverage. Existing v3 development/session behavior stays
compatible while later stages adopt the normalized coordinator.

### 2026-08-19 21:23 +05:30 - Codex (live provider run) - [8259231] - Grounded Build Preparation to Code Generator execution
Hardened live Build Preparation context normalization, duplicate-resource fallback, and Code Generator repository-root path resolution so the exact eligible pack survives admission, acquisition, generation, and verification from any Windows launch directory. The live run promoted a verified single-route portfolio preview and persistent local export; focused tests passed.

### 2026-08-19 17:42 +05:30 - Codex (live provider run) - [a01c030] - Harden Build Preparation live fixture execution
Fixed the Docker provider-cache permission failure, mounted attached CA/VDD
inputs read-only for the Compose frontend, reconciled malformed Stage 2 need
IDs to the deterministic Stage 0 set, and retained packages when the advisory
Stage 5 model review receives a provider rejection. Focused tests passed, and
the final live frontend run reached packaging plus verified R2 read-back;
handoff remained correctly blocked by four deterministic resource/VDD issues.

### 2026-08-19 17:03 +05:30 - Codex (live provider run) - [33b7113] - Document Build Preparation execution
Added the requested `docs/run/run.md` runbook with verified frontend links,
config-driven secret names, production and detached live-run commands, the
`handoff_eligible` gate, and the Docker/network/schema/resource issues found
during the live Build Preparation run.

### 2026-08-19 16:53 +05:30 - Codex (live provider run) - [237e0ed] - Align Build Preparation live response schemas
Accepted responsive/reduced-motion query fields and the complete Stage 3/4
context envelope emitted by the configured live model, then normalized the
context metadata before downstream validation. Focused Build Preparation tests
passed, and the approved production session completed live model/provider
execution through packaging and verified R2 read-back; handoff remained blocked
by an unresolved approved component role and duplicate decorative image bytes.

### 2026-08-19 16:40 +05:30 - Codex (model/provider omitted) - [45eafdc] - doc/run/run.md
Added the reusable Docker runbook for Discovery, Content Architect, and Visual
Design Director, including the observed migration failures, non-destructive
database repair, live-provider configuration check, startup commands, and
verification steps.

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

## Summary (as of last compaction — 2026-08-21)

- Recent detailed entries retained: 24
- Compacted milestone bullets: 9
- Last updated: 2026-08-21 — Codex (GPT-5 / OpenAI)
