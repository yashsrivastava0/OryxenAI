# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-09 23:39 +05:30 - Codex (GPT-6 / OpenAI) - [9716681] - fix(code-generator): catch inert disclosure panels early

The second authorized live campaign run reached source generation and exposed
an inert education `Disclosure` whose panel contained only an aria-hidden
empty span. Added a narrow host-owned source diagnostic so this concrete
functional defect is found during route validation and can be repaired within
the existing bounded budget. Also aligned generation/review prompts with D-076:
`columns_*` are abstract design-grid spans, so the model's desktop-span
observation remains advisory unless an executable recipe or runtime contract is
broken. The full Code Generator unit suite passes (310), mypy passes, and
touched-file Ruff checks pass.

### 2026-09-09 22:41 +05:30 - Codex (GPT-6 / OpenAI) - [4da1ddb] - fix(code-generator): keep toolchain preflight cleanup best effort

Best-effort cleanup now returns a safe incomplete result when Windows denies
directory enumeration, so cleanup cannot discard a valid toolchain proof or
replace it with a generic blocked response. The API-level preflight then passed
Node, npm, install, TypeScript, Vite build, browser, gateway, and brief-path
checks. The full Code Generator unit suite passes (308).

### 2026-09-09 22:24 +05:30 — Codex (GPT-6 / OpenAI) — [14bb97c, c8a66e7, 80a925c] — fix(code-generator): make quality and failure reports truthful

Replaced keyword-based severity inference with explicit host-owned finding
mappings and strict terminal reports, then made historical quality receipts
readable across run, quality, and product projections. Live Pack C reached
source generation and stopped honestly at `INTEGRATION_REVIEW_UNRESOLVED`; its
checkpoint remains retained and no preview was promoted. Verification: full
Code Generator unit suite passes (307), mypy passes, and touched-file
Ruff/format checks pass.

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

## Compacted history

### 2026-09
- 2026-09-09 — [e99ed55] — Investigated five failed Code Generator runs and authored the implementation and five-slot campaign handoff for pending retention, accounting, visual quality, truthful exports, and preflight.
- 2026-09-09 — [29fc598] — Reconciled stale `create`/`replace` repair tags against the owned candidate tree while preserving strict initial-generation semantics and bounded repair authority.
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

## Summary (as of last compaction — 2026-09-09)

- Recent detailed entries retained: 16
- Compacted milestone bullets: 31
- Last updated: 2026-09-09 23:39 +05:30 — Codex
