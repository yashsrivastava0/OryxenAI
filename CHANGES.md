# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-08-24 - Codex (model/provider omitted) - [16e3e94] - Make GitHub CI database and Docker smoke setup self-contained
Configured the CI PostgreSQL port override to match the GitHub service
container, upgraded the workflow actions to Node 24-compatible releases,
disabled the failing optional uv cache, and added disposable, post-secret-scan
environment placeholders for the Docker smoke test. Production credentials and
local `.env` files remain outside version control.

### 2026-08-24 18:36 +05:30 - Codex (model/provider omitted) - [e70b6ab] - Align auth handoff documentation with public admission
Updated the Auth README, owner deployment checklist, and implementation handoff
so future agents use the new open/allowlist admission mode rather than the
obsolete allowlist-only policy. Google OAuth Testing/publishing remains a
separate provider-side deployment gate.

### 2026-08-24 18:30 +05:30 - Codex (model/provider omitted) - [dddc1ba] - Open Google registration and browser auth hardening
Added explicit `open`/`allowlist` admission modes, with the product and Docker
deployment admitting verified Google users until the server-side 15-user cap.
Updated the auth UI copy and route metadata, added no-token HTML assertions and
security headers, and documented the remaining Google OAuth Testing/publishing
owner gate (D-048). Supabase PKCE browser sessions remain managed by the pinned
client; tokens are not rendered in HTML, URLs, logs, or API responses.

### 2026-08-24 17:44 +05:30 - Codex (model/provider omitted) - [449b379] - Authentication redirect flicker fix
Loaded the pinned Supabase browser client before every product/development auth
bootstrap, removed auth-only CSS from the product workspace, preserved valid
sessions when workspace code fails, and added callback/script-order regression
coverage. This removes the false configuration error and `/app` to `/sign-in`
redirect loop while keeping new-user onboarding and returning-user routing
deterministic.

### 2026-08-24 17:11 +05:30 - Codex (model/provider omitted) - [c5b5821] - Final authentication readiness hardening
Corrected modern Supabase secret-key Admin API headers, browser token refresh,
canonical PKCE routing, terminal local sign-out, retryable administrator
operation UX, external-call transaction boundaries, schema-aware readiness,
and cross-platform Docker startup. Safely migrated the verified-empty local
application schema to Alembic head and left the API, worker, and PostgreSQL
stack healthy for owner Google-browser acceptance.

### 2026-08-24 - Codex (model/provider omitted) - [b17227c] - Phase 4 administrator lifecycle and acceptance
Implemented the linear Phase 4 migration, safe admin operations/audit ledger,
Supabase Admin API adapter, resumable user/project cleanup, identity/project
tombstones, entitlement reset, promotion/demotion safety, deletion worker
fences, Code Generator admin commands, functional masked admin console, and
deterministic verification/reporting. Local authentication and authorization
are complete through Phase 4; owner browser acceptance and production
deployment remain separate gates.

### 2026-08-24 13:07 +05:30 - Codex (model/provider omitted) - [90d5dfe] - Phase 3 portfolio entitlements and worker fencing
Implemented migration 0016 with one normal-user portfolio, generation-variant, and verified-success entitlement; trusted durable owner/actor snapshots; global model-generation admission; redacted provider-credit failures; worker reauthorization; verified preview finalization; and server-enforced post-success read-only behavior. Updated the authenticated product shell and Phase 3 documentation/tests. Administrator lifecycle, destructive reset/delete, live multi-account acceptance, and deployment remain Phase 4.

### 2026-08-24 02:09 +05:30 - Codex (model/provider omitted) - [d288077] - Phase 2 portfolio ownership and API authorization
Implemented migration 0015 with fail-closed legacy quarantine, owner-scoped session aggregates, centralized owner/admin route dependencies, protected development surfaces, bearer-authenticated product/developer boot, and regression coverage. Recorded D-045; entitlement, worker fencing, administrator lifecycle, and deployment remain Phases 3 and 4.

### 2026-08-24 00:00 +05:30 - Codex (model/provider omitted) - [48e5f6c] - Supabase Auth Phase 1 foundation
Implemented Google-only Supabase PKCE sessions, asymmetric JWT/JWKS verification, allowlisted just-in-time admission, two bootstrap admins outside the 15-user capacity, username onboarding, direct auth routes, a self-hosted browser controller, migration 0014, and focused coverage; Phases 2-4 and production cloud setup remain deferred.

### 2026-08-23 21:19 +05:30 - Codex (model/provider omitted) - [c9ad71d] - Auth prerequisite and minimum-route handoff
Recorded the privately configured separate normal test identity, zero-warning
strict prerequisite result, documentation-only phase boundary, and deterministic
first-visit/callback/refresh/deployment route controller. No auth runtime,
migration, dependency, table, secret, or cloud resource was added.

### 2026-08-23 20:56 +05:30 - Codex (model/provider omitted) - [0f9bc0d] - Supabase Auth setup and implementation handoff
Accepted Supabase Google-only identity with FastAPI/PostgreSQL authorization
(D-043), replaced the Clerk-first research, recorded the sanitized development
setup, and added a repository-grounded implementation plan plus redaction-safe
offline/online prerequisite verifier. Provider checks passed; runtime auth is
not implemented, and one separate normal-user test identity remains pending.

### 2026-08-23 19:37 +05:30 - Codex (model/provider omitted) - [5ca0b85] - Code Generator V4 realization, verification, and preview hardening
Activated the V4 source-realization, quality, runtime, and preview contracts,
added the scaffold source audit and integration-review regression coverage, and
recorded stable retry versus explicit new-variant semantics (D-042). Refreshed
the checked-in portfolio input examples and removed obsolete generated/session
artifacts; repository and clean scaffold verification passed.

### 2026-08-23 14:03 +05:30 — Codex (model/provider omitted) — [a03ba6f] — Authentication research
Added a source-grounded `docs/Auth/` research and handoff set covering provider
selection, Google/username flow, ownership and one-success quota semantics,
admin authority, security, deployment responsibilities, and edge cases. This
research adds no runtime auth or accepted architecture decision.

### 2026-08-21 22:20 +05:30 - Codex (GPT-5 / OpenAI) - [3437075] - V4 promotion quality/read-back gate
Required an accepted v4 quality receipt before final verification can promote,
verified the candidate index before changing the active pointer, and upgraded
new portfolio exports to additive metadata schema v2 while retaining v1 reader
compatibility.

### 2026-08-21 22:00 +05:30 - Codex (GPT-5 / OpenAI) - [26890c5] - Code Generator V4 reliability and preview quality contracts
Added provider-compatible v4 creative/blueprint/search/source/quality DTOs,
typed token compilation, semantic route ownership, measurable design
realization, exact bounded provider-query receipts, v4 development quality
review parity, hash-bound quality API/reporting, and `preview_pending`
publication retention. Fixed preview CSP origin allowlists, gateway-specific
health checks, index caching, storage read-back, and pack-v4 mirror admission;
added focused v4 and gateway coverage while preserving v3 compatibility.

### 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI) — [5fcbdd4] — Anthropic model routing, adapter hardening, profile API/UI
Implemented D-040: all active engines now resolve through the shared
`ModelRouter` and provider-neutral client factory to Anthropic Claude Sonnet 5
using the credential named by the active profile. Added adaptive-thinking/
native-schema capability configuration, prompt caching, safe selectable-profile metadata, live
fail-closed behavior, and regression coverage; Batch API submission remains
deferred for a future asynchronous workload.

### 2026-08-21 - Codex (GPT-5 / OpenAI) - [0240f57] - Lightweight LLM observability research
Recorded a research-only recommendation for simple cost and tracing visibility:
Langfuse first, Phoenix as a local alternative, and one metadata-only
integration point at the shared `ModelClient` boundary. No runtime code,
dependency, dashboard, or architecture decision was added.

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

---

## Compacted history

### 2026-08
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

## Summary (as of last compaction — 2026-08-24)

- Recent detailed entries retained: 20
- Compacted milestone bullets: 26
- Last updated: 2026-08-24 — Codex (model/provider omitted)
