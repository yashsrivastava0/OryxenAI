# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-09 20:31 +05:30 — Codex — [a503a4a] — fix(code-generator): enforce reliable generation lifecycle

Implemented the reliability plan through the offline verification boundary:
complete pending source proposals and restricted rejected evidence, durable
serial attempt accounting with stop-on-failure, optional component admission,
hashed image obligations with browser evidence, marker-bound layout recipes,
toolchain preflight, and truthful atomic exports. Added focused regressions,
aligned stale integration fixtures with canonical host identities, and recorded
the adopted contract in `DECISIONS.md` plus R01–R12 dispositions in
`code generator issues.md`. No new live portfolio pipeline call was made in
this implementation commit; the new five-slot campaign starts at 0/5.

Verification: focused reliability/admission/image/export tests pass (24), the
full Code Generator unit suite passes (299), Ruff, mypy, and compileall pass.
The repository-wide baseline still contains unrelated/stale integration and
mock-path failures documented in `code generator issues.md`.

### 2026-09-09 14:40 +05:30 — Codex — [e99ed55] — Code Generator reliability investigation and implementation handoff

Traced the five failed runs, compiled the three current briefs, and replayed the
latest repair offline. Added an evidence-backed implementation plan covering
pending-file retention, durable batch accounting, image/layout quality, truthful
exports and a separately authorized five-run campaign; no new live run or
production-source change was made. Updated `code generator issues.md` and
compacted the oldest detailed history entries per this file's retention policy.

### 2026-09-09 13:45 +05:30 - Codex (GPT-5 / OpenAI) - [29fc598] - fix(code-generator): reconcile stale repair file operations

Closed the fifth live campaign's deterministic `SOURCE_CREATE_EXISTS` repair
failure. Initial generation still enforces exact create/replace state. Repair
validation now reconciles a stale operation tag with the actual owned candidate
tree only after ownership, trusted-file, size, import, and content-policy
checks, so a mixed response can continue across partial/rejected attempts
without widening authority. Applied the same bounded behavior to the
orchestrator's route/integration repairs and the final-repair path, documented
the contract, and added a regression test for existing-plus-missing files.

Verification: all 285 Code Generator unit tests pass; Ruff and mypy pass; the
recorded fifth-run repair response replays offline as one `replace` plus five
`create` operations with no `SOURCE_CREATE_EXISTS`. The five-run live campaign
is closed; no sixth full pipeline call was made.

### 2026-09-09 09:50 +05:30 - Codex (GPT-5 / OpenAI) - [59409b5] - fix(worker): make PowerShell launcher use writable uv cache
Updated `scripts/run-worker.ps1` to run from the repository root, use the
repository-local `uv` cache, create its runtime cache directories, and
propagate launcher failures. This prevents a locked global `uv` cache from
silently leaving Discovery jobs queued without a worker.

### 2026-09-09 03:00 +05:30 - Codex (GPT-5 / OpenAI) - [2f424e5] - fix(code-generator): harden brief-driven generation and previews

Implemented the Code Generator reliability handoff for variable Build Preparation output:

- admitted the canonical and current underscore/legacy brief mirrors through one immutable compiler, including result-only Markdown pairs, while rejecting incomplete or malformed route/section indexes before model calls;
- added exact host-side planner identity/token canonicalization, a configuration-bounded planner retry, and restricted per-attempt diagnostics so `PLANNER_OUTPUT_INVALID` failures are actionable without persisting raw model payloads in receipts;
- added source scans for static, re-export, and literal dynamic npm imports so optional components fall back safely and required unsupported packages fail with a clear dependency issue;
- replaced score-only quality acceptance with one host-owned finding policy: functional/safety/approved-requirement findings block while visual geometry/polish findings remain explicit advisories;
- preserved clean-build candidates as capability-scoped unverified previews, kept separate from active verified promotion, and wired candidate/warning/retry state through the development API and `/app` generation UI;
- made the npm cache warmer install configured pins into a disposable project and prove a real offline `npm ci`, and added the production Docker/Compose/config wiring required for the Azure VM layout.

Verification: Ruff, mypy, compileall, Docker Compose configuration, and the frontend TypeScript contract pass. The focused Code Generator tests report 63 passes; nine temp-directory tests cannot create pytest's Windows `.lock` file in this environment and are recorded as an environment ACL limitation. Live campaign inputs and outcomes are tracked in `docs/code-generator-live-campaign.md`.

### 2026-09-09 02:44 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [bc7b5a6] - feat(studio): add admin-only pipeline reset

Added an administrator-only pipeline reset capability to allow resetting any active portfolio session completely back to zero (restarting from the Discovery agent) while preserving the administrator's authentication session:
- Added `PipelineResetService.reset_admin_pipeline` in `src/oryxenai/runtime/pipeline_reset.py` to cancel pending jobs with `PIPELINE_RESET`, clean external preview/artifact stores, purge background jobs, agent runs, and code generator execution records, zero `current_state`, reset status to `active`, and record an admin audit log entry.
- Added `POST /api/v1/sessions/{session_id}/reset` in `src/oryxenai/api/routes/sessions.py`, guarded by `require_admin` (returning 403 `ADMIN_REQUIRED` to non-admin users). Registered in authorization route inventory.
- Added `pipeline/reset` action in `frontend/src/app/store.ts` and `api.resetSession` in `frontend/src/data/api-client.ts`.
- Added topbar Reset button with `ADMIN` badge, account menu secondary link, and confirmation dialog modal in `frontend/src/app/AppShell.tsx` and styled in `frontend/src/styles/shell.css`.
- Verified with integration tests in `tests/api/test_admin_pipeline_reset.py`, store unit tests, and production frontend build.



### 2026-09-09 02:28 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [66d8287] - docs(frontend): author comprehensive frontend and agent integration specifications

Created an exhaustive 6-document technical reference suite under `docs/frontend/`
to serve as the unambiguous source of truth for downstream AI coding agents
executing the major frontend revamp:
- `01-architecture-routing-and-auth-runtime.md`: Preact/Vite build boundary,
  FastAPI manifest resolution, Google Supabase auth runtime, /api/v1/me
  entitlement invariants, URL codec, visibility-aware polling, BroadcastChannel
  multi-tab sync, error envelope, and tokens.
- `02-agent-pipeline-and-data-contracts.md`: Authoritative domain schemas,
  state machines, Pydantic models, JSONB storage, and route tables for all 5
  agents (Discovery, Content Architect, Visual Design Director, Build Preparation,
  Code Generator).
- `03-current-frontend-implementation-audit.md`: Line-level audit of all 20+
  components in `frontend/src/components/`, stage views, and data adapters.
- `04-agent-by-agent-deep-dive-and-flaw-analysis.md`: Detailed comparison of
  backend agent outputs vs. current UI presentation, documenting root causes
  of why Build Preparation, Visual Design Director, and Content Architect
  currently appear uncurated or broken (e.g. raw 300KB+ Markdown dumping with
  fenced JSON, loss of structured profiles, and lack of visual design tokens).
- `05-refactor-blueprint-and-component-architecture.md`: Target revamp
  specification with custom hooks decomposition (`useSessionState`,
  `useStagePolling`, etc.), two-column Discovery studio, visual Content
  sitemap, interactive Design moodboard, Build Preparation command center,
  and multi-device Portfolio Theater sandbox.
- `06-api-reference-and-integration-cookbook.md`: Machine-readable route
  catalog, exact JSON payloads, copy-paste recipes, and step-by-step refactoring
  quality checklist.
85 frontend vitest unit tests passing; Vite production build verified clean.


### 2026-09-09 01:20 +05:30 - Codex (GPT-5 / OpenAI) - [78a9c77] - frontend: remove legacy static pipeline shell

Retired the temporary static Discovery/pipeline shell (`index.html`, `app.js`,
and `app.css`) and removed its `/dev` route and `/app` fallback. `/app` now
requires the manifest-selected Preact bundle and reports a clear 503 when it is
not built. The separate Build Preparation diagnostic and Code Generator
development control room remain intact.

### 2026-09-09 00:35 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [f20779f] - code-generator: clarify planner guidance on design-language words vs literal color names

Live-confirmed a reproducible planner failure specific to one pack's own
visual brief: prose describing "one confident technical accent" pulled the
model toward literally naming a raw color token "accent" too, colliding
with the reserved `shadcn_theme_bindings` slot key (D-071's existing
collision validator). Two independent full runs (6 total planner attempts
across the existing 3-attempt budget) both still failed on this exact
category despite the corrective retry already naming the collision — real
model pressure from the brief's own wording, not noise. Added guidance that
a brief's design-language words ("an accent color," "the primary action")
name a concept, not the literal `colors[*].name` string. Live-verified: the
next run's planning stage passed cleanly. Prompt-only; no code/test/worker
changes needed.

### 2026-09-09 00:20 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [051afa6] - code-generator: detect a pinned component's undeclared npm imports via source scan

Live-confirmed root cause of "Cannot find module 'motion/react'" at
foundation typecheck: the two-Markdown-brief handoff format has no field
for a pinned/deferred component's own npm dependencies, so
`dependency_metadata` stays empty end to end and the package is never
requested — confirmed via direct DB inspection of the persisted dependency
ledger (`receipts: []`), not guessed. The existing auto-resolution logic in
both acquisition call sites was already correct; it simply had nothing to
resolve. Added `detect_supported_import_dependencies()`
(`dependency_manager.py`): scans a fetched component's actual source text
for bare-specifier imports, matching only against the already-configured
`supported_packages` allowlist, so an unvetted package can never be
silently installed. Live-verified across three more runs: the fix correctly
triggered dependency resolution for the first time, surfaced an unrelated
one-time offline-npm-cache miss (same category as the earlier undici-types
gap, not a code defect — fixed by warming `.workspace/npm-cache` with a
real network install), and a further run cleared acquisition cleanly. New
unit coverage for the scan helper. 267 passed (2 new), same 1 pre-existing
unrelated failure. mypy/ruff clean.

### 2026-09-08 23:40 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [a2ae087] - deploy: check in Azure production Compose/Caddy/TOML overlays

Added `config/app.production.toml`, `compose.production.yaml`, and a repo-root
`Caddyfile` matching `docs/deployment/02-azure-vm-runbook.md`'s sections 5/6/8
content exactly (every field verified against the current Settings model
first), so the operator clones and edits placeholders on the VM instead of
hand-authoring multi-line files over SSH. Caddy stays a native VM service per
the existing runbook design, not a Docker container. Also fixed the runbook's
own text to point at these checked-in files.

### 2026-09-08 23:20 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [2790e9d] - app: release Generate & Preview stage, superseding D-063's boundary

Added a fifth `/app` stage (D-081) that starts the previously-unexposed
production Code Generator session API and embeds its promoted preview,
gated on Build Preparation completion. Recovered and adapted a near-complete
prior implementation from history (`f9e8eef`/`9c27a69`, removed at `389fa28`)
to the current `ActivePreview`/`CodeGeneratorSessionStatus` field names.
Generate and Preview are one merged stage; the rail's decorative
permanently-locked "Preview" tile is removed. The preview panel (route
selector, mobile/tablet/desktop/fit viewports, refresh, open-in-new-tab,
sandboxed iframe) reuses the exact `postMessage` bridge already live-verified
in the developer harness. `product-boundary.test.ts` now requires
`/code-generator` instead of forbidding it.

### 2026-09-08 23:00 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [44304ff] - code-generator: honor honest repair declines, reuse stable cache keys, tighten repair budgets

Root-caused and fixed two open reliability bugs from the prior session's
handoff: `FinalRepairError` had no escape hatch for a V4 plan's honest
`cannot_complete` result, so the caller blindly retried an already-declined
diagnostic bundle to budget exhaustion; now a distinct `FinalRepairDeclined`
is retried once and stopped on a second identical decline.
`RUNTIME_REGION_WIDTH_RATIO` findings sharing the same measured content width
now get an explicit shared-cause note instead of looking like N independent
defects. Separately, fixed all three Code Generator prompt-cache keys (they
were scoped to `generation_id`/`identity_hash`, defeating reuse of the large
stable system-prompt prefix across runs — the same pattern the cost
research doc measured as ~73% of a day's spend), tightened repair-round
ceilings to match this project's own observed 1-2-round real-fix depth, and
gave Code Generator jobs their own `code_generator_max_attempts` config
instead of sharing the more permissive general worker default.

### 2026-09-08 20:55 +05:30 - Codex (GPT-5 / OpenAI) - [d6b6777] - build-preparation: fix false identity rejection and safe preflight errors

Build Preparation now takes the approved owner identity from the Content
Architect public manifest/visual handoff before inspecting factual evidence,
so repeated employer or organization names cannot be mistaken for the
portfolio owner. The strict visual-identity guard remains in place for real
cross-person mismatches. Preflight validation failures are translated into a
safe, attributable 409 response instead of an unhandled generic 500, with
regression coverage for both the false-positive and error-sanitization paths.

### 2026-09-08 17:51 +05:30 - Codex (GPT-5 / OpenAI) - [bb7078b] - app: harden Design-to-Prepare handoff

Applied the same stale-projection protection to the explicit Visual Design →
Build Preparation handoff. If the browser still has a fail-closed `locked`
projection while upstream approval is already durable, the handoff now starts
the preparation job instead of opening a permanently locked screen. The
frontend boundary regression check covers this path.

### 2026-09-08 17:28 +05:30 - Codex (GPT-5 / OpenAI) - [5731cf5] - app: repair stale Discovery-to-Content handoff

Fixed the `/app` Continue to Content handoff when the browser still holds
Content Architect's fail-closed `locked` projection from before Discovery was
approved. The explicit handoff now starts Content for both stale `locked` and
fresh `available` projections, and the frontend boundary test protects the
regression path. Verified with the complete frontend typecheck, Vitest suite,
and production build.

### 2026-09-08 16:05 +05:30 - Codex (GPT-5 / OpenAI) - [78eacc7] - telemetry: align Experiential management observations

Aligned the Experiential usage reconciler with the documented management API
host and its organization-scoped usage contract. The reconciler now derives
the management host from the configured inference URL, reads non-secret key
metadata and effective key limits without guessing identifiers, and only calls
usage rollups when an optional EXPLABS_ORG_ID environment value is
configured. This removes recurring invalid telemetry probes while preserving
local attempt telemetry and provider-observed data when the account scope is
available. Added bounded unit coverage for URL derivation and key-ID safety.


## Compacted history

### 2026-09
- 2026-09-08 - Codex - [ddc2e77] - Integrated approved Build Preparation into /app with safe output copying and provider attempt/usage safeguards; detailed history retained in Git.
- 2026-09-08 - Codex - [3a6cf25] - Added per-boot legacy frontend cache busting so updated output controls appear after refresh.
- 2026-09-08 - Codex - [b07582d] - Added per-agent safe JSON copy controls and clipboard fallback states.
- 2026-09-08 - Codex (GPT-5 / OpenAI) - [7f2fbd0] - Fixed repeated manual Discovery retries colliding with durable idempotency constraints, and kept job-attempt tracing internal to adapter.
- 2026-09-08 - Codex (GPT-5 / OpenAI) - [9d256f3] - Implemented provider-neutral Experiential/Gemini routing, quota ledger, bounded recovery, and usage telemetry; records D-078.
- 2026-09-07 - Claude Code (Sonnet 5 / Anthropic) - [7f09506] - Added unverified candidate preview for needs_attention runs in dev harness; cancelled 95 stale queued jobs and fixed uncommitted export_receipt writes.
- 2026-09-07 - Claude Code (Sonnet 5 / Anthropic) - [5bef169, ac5543e] - Root-caused live repair failures in DB history; fixed quote-tolerant attribute selector checks and distinctive-move review code mapping.
- 2026-09-07 - Claude Code (Sonnet 5 / Anthropic) - [3f5b2aa] - Added clean auto-build on failed exports, wired export into generation failure path, and added geometry repair guidance.
- 2026-09-07 - Claude Code (Sonnet 5 / Anthropic) - [78117e7] - Implemented truthful scaffold toolchain and 5 generation-time authoring fixes (cross-route nav edges, aspect-ratio pairing, 44px touch targets).
- 2026-09-06 - Claude Code (Sonnet 5 / Anthropic) - [446d4c7, 87f97f4, 7578b9a, f7546d4, 6707cce] - Fixed 10 Code Generator bugs across 5 live runs including content-box measurement for width-ratio checks and comment stripper regex.
- 2026-09-06 - Antigravity (Gemini 3.8 Flash / Google) - [5768ce7] - Revamped /app Discovery workspace into an Editorial Swiss living draft studio with 6-stage drafting rail and progressive disclosure.
- 2026-09-06 - Antigravity (Gemini 3.8 Flash / Google) - [618a038] - Added official OryxenAI 3-layer logo to sign-in, fixed back-button CTA stuck state, and added drafting grid and traveling sweep motion.
- 2026-09-06 - Antigravity (Gemini 3.8 Flash / Google) - [fa9be97] - Redesigned Screen 1 (/sign-in) with 44/56 two-column Editorial Swiss studio layout, Google OAuth above the fold, and 5-card showcase carousel.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [f208540, ebfbc94] - Documented frontend context/output ledger, copy-controls requirements, and replacement runbook pack for redesign agents.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [cdf8952] - Fixed a Content approval 409 on pending-claim routes, bounded a one-click Discovery-to-Content handoff, and added safe copy-ready JSON to review surfaces; records D-075.
- 2026-09-06 - Claude Code (Sonnet 5 / Anthropic) - [1956d58] - Curated kept `output/` artifacts, fixed a `.gitignore` nested-negation bug, corrected stale README claims, and documented `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE`.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [7c94916] - Fixed Discovery's frontend to send correct answer action modes instead of presentation kinds, restoring authenticated answer submission.
- 2026-09-06 - Claude Code (Sonnet 5 / Anthropic) - [83179f3 and 8 prior commits] - Closed 8 more live-tested Code Generator bugs beyond D-072 and added failed-run export (`export_failed_run`); records D-074.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [ae89b61] - Fixed stale shared-execution-lane blocking that stalled Discovery behind old Code Generator leases.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [68f1cd1, 861e981] - Added safe job lifecycle metadata, foreground scheduling, and stale-lease recovery for Discovery, plus durable stop fencing; records D-073.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [cdf7a18] - Added durable cancellation fencing for Content Architect/Visual Design Director, a reusable three-stage job projection, and bounded trace export/copy support.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [903477a, a2a8a60, 963375b, 7a0c68f] - Completed Azure VM provisioning, networking, SSH handoffs, and R2 credentials readiness checkpoints.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [caa8f33] - Completed the authenticated three-stage Preact product handoff (Discovery/Content Architect/Visual Design Director) with retry/session fixes.
- 2026-09-05 - Claude Code (Sonnet 5 / Anthropic) - [34c638b, d6cde91] - Fixed `--color-accent` token collision, bounded live-search fallback for expired pinned Pixabay URLs, enriched repair diagnostics; records D-071, D-072.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [8a2066a] - Added provider-neutral `BudgetedModelClient` to reserve prompt/completion charges before transmission and stop at a session cost cap; records D-070.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [5b86779] - Added session-scoped PostgreSQL caching for validated structured model results across Discovery/Content Architect/Visual Design Director/Build Preparation; records D-069.
- 2026-09-05 - Claude Code (Sonnet 5 / Anthropic) - [aedf96c] - Closed repair control-flow gaps, added review prompt prefix-caching, introduced the deterministic motion pattern catalogue; records D-068.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [0ce8ecd] - Added canonical first-deployment path (Azure Linux VM, Docker Compose, Supabase auth, Cloudflare R2, Caddy HTTPS) with a production-overlay runbook.
- 2026-09-05 - Antigravity (Gemini 3.8 Flash / Google) - [9fabd58] - Consolidated all agent outputs under single canonical `output/` directory, purging obsolete prebuild artifacts.

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

## Summary (as of last compaction — 2026-09-09)

- Recent detailed entries retained: 17
- Compacted milestone bullets: 29
- Last updated: 2026-09-09 14:40 +05:30 — Codex
