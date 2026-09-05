# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-05 - Codex (GPT-5 / OpenAI) - [e1173df] - record Azure VM wizard checkpoint

Added `docs/deployment/04-current-azure-deployment-status.md` as the canonical
handoff for the live Azure setup. It records that only `oryxenai-demo-rg` is
created, the VM wizard is paused at Networking, all confirmed VM/disk/SSH
choices, the exact intended NSG and resource names, pending Supabase/R2/DNS/
Docker work, secret rules, cost controls, acceptance criteria, and the next
portal action. Linked the checkpoint from the deployment README; no Azure
resources or application code were changed.

### 2026-09-05 19:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [34c638b] - catch a silent token collision and sharpen two repair diagnostics

Live testing of D-068's fixes across 6 fresh live runs surfaced three more real bugs, each found only by actually completing a run. (1) The model transcribes an opaque hash-like content-key suffix with a one-character typo and repeats the identical typo across every repair round; `SOURCE_ROUTE_BATCH_CONTENT_KEY_MISSING` now searches for a same-prefix near-miss call already in the source and names it directly, giving the repair model something concrete to fix instead of guessing. (2) `SOURCE_BLUEPRINT_MOVE_MARKER_ONLY` had a generic message, unlike its mid-generation sibling which already names the exact selector/properties — the final-repair model reported `cannot_complete` on it 3 rounds running; now states the same concrete facts. (3) A genuine silent-corruption bug: a raw color token and a shadcn theme binding slot sharing the same literal name (both commonly "accent") compile to the identical `--color-accent` CSS custom property; the alias silently overwrites the real color with no error anywhere, surfacing only as an opaque whole-site review finding after a full generation pass that otherwise scored 4/4/4/4/4. Added the same collision check at both the schema level (`DesignTokenSystemV4`'s validator, catching it the instant the planner responds — confirmed live) and the token compiler (defense-in-depth for any blueprint reaching compilation via `model_copy`, which doesn't re-validate), plus `planner.md` guidance since the model repeated the identical collision on the very next live attempt even after the validator started rejecting it. Also confirmed live: D-068's `cannot_complete` polish-loop resilience fix fired multiple times across several runs without crashing, correctly falling through to the pre-existing bounded `INTEGRATION_REVIEW_UNRESOLVED` terminal state. Verified: 232 code_generator unit tests (2 new), ruff/mypy clean. Live-verified over 6 real runs (~$0.3-1.0 this batch, ~$0.4-1.2 combined with D-068's runs, well within the $5 session budget); one run reached final review with all 5 scores at 4 and exactly one blocking finding — the closest yet, not a clean pass. Full end-to-end success (a promoted preview) was not reached this session; remaining variance is concentrated in whole-site resource-placement rendering and generic model non-determinism on already-prompted-against rules, not in control-flow/validation gaps. Records D-071.

### 2026-09-05 16:40 +05:30 - Codex (GPT-5 / OpenAI) - [8a2066a] - enforce a pre-call ceiling for explicitly capped live runs

Added a provider-neutral `BudgetedModelClient` that serializes structured calls, reserves a conservative prompt plus maximum completion charge before transmission, releases unused reservation only after valid usage telemetry, and consumes the reservation on failures or unknown usage. Added focused tests for refusal-before-call, temporary output caps, profile restoration, and failure consumption. The authorized resume validation run completed Discovery at `0.256180` recorded configured credits, but Content Architect returned `MODEL_EMPTY_OUTPUT`; because an earlier interrupted attempt had no usage receipt, no later stage was retried against the hard ceiling. Records D-070.

### 2026-09-05 15:23 +05:30 - Codex (GPT-5 / OpenAI) - [5b86779] - add scoped long-lived model-result caching and cache receipts

Added owner/session-scoped PostgreSQL caching for validated structured results across Discovery, Content Architect, Visual Design Director, and Build Preparation, with a six-month TTL, single-flight leases, provider prompt-cache hints, usage/character/cost telemetry, and redacted local exports. Added truthful cached-response notices to both frontend control surfaces; records D-069. Live execution of the supplied resume remains pending explicit authorization to send the document to the configured external provider.

### 2026-09-05 14:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [aedf96c] - close two repair control-flow gaps, complete caching, add motion catalogue

Root-caused D-067's frontier blocker (`QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on a single easily-fixable finding) to a genuine control-flow gap, not a capability/budget problem: `_attempt_repair`'s post-repair whole-site re-review rejection raised terminally from *outside* its own bounded retry loop, discarding 5 of 6 available repair rounds. Added exactly one bounded extra repair+re-review attempt (never open-ended); refactored into `_run_bounded_repair`/`_rereview_after_repair`/`_diagnostics_from_quality_findings` helpers, 2 new + 1 unchanged regression test prove the exact bound. Live testing surfaced the identical class of gap one stage earlier: `_review_and_polish`'s owner-scoped repair call killed the whole run outright on a `cannot_complete` response with zero retry, even though the outer polish-round loop (5 rounds, D-067) exists precisely to give a different round another try — fixed the same way (skip that owner for the round, let the bounded loop continue), with a matching regression test. Completed prefix-caching coverage for the whole-site integration review — the single most expensive, most-repeated call in the pipeline (up to 8x/run, up to ~600,000 chars) had zero `request_context` support, unlike 4 of the other 5 call sites — with a careful `INTEGRATION_REVIEW_KEY_ORDER` (source_manifest/round last, since they change every round) plus a stable per-run `prompt_cache_key`; confirmed live via non-zero `cached_prompt_tokens`. Added a deterministic motion-pattern catalogue (`core/motion_pattern_catalogue.py`, 3 patterns: reveal-fade-rise, reveal-clip-lines, stagger-group) and an optional `MotionBeatV4.pattern_id`, extending the codebase's existing image/font/component catalogue-and-select precedent to motion — confirmed live, the planner set `pattern_id` on a real beat on its first attempt; required fixing a load-bearing prompt contradiction (`route_batch.md`/`route_compose.md` explicitly forbade the `.reveal`/`.stagger` class names this introduces). Added advisory screenshot capture to DOM/runtime verification (zero extra cost, the browser context is already open) since the pipeline had never once captured visual evidence of a generated portfolio, and captured raw model `usage` at 3 previously-discarding call sites (director, redirect-director, final-repair), with a `RepairReceipt` hash-exclusion-set fix so existing persisted receipts don't break on load. Also fixed, as a safety measure: `tests/integration/test_build_preparation_worker.py`'s one worker test built no mock model client and was silently spending real provider budget on every plain `pytest` run — gated behind the project's own existing `RUN_LIVE_*` opt-in convention (`tests/live/`). Verified: 231 code_generator unit tests, 10/14 code_generator integration tests (4 pre-existing `PLAN_SECTION_COVERAGE` failures confirmed unrelated via `git stash` on unmodified HEAD, not touched this session), ruff/mypy clean. Live-verified over 2 real runs against the eligible pack (~$0.06-$0.21 total at published Luna rates); a third and fourth attempt were killed by real system memory pressure before reaching final verification, so the first fix's exact retry firing was not directly witnessed live this session, though its regression tests prove the bound precisely. Records D-068; `code generator issues.md` rewritten with the current state and next verification target.

### 2026-09-05 - Codex (GPT-5 / OpenAI) - [0ce8ecd] - add simple Azure deployment documentation

Added the canonical first-deployment path for the two-user demo: one Azure
Linux VM running the existing Docker Compose API, PostgreSQL, worker, and
preview gateway; Supabase Google authentication; Cloudflare R2; and Caddy
HTTPS. Added current provider research, a production-overlay runbook,
end-to-end agent-to-preview acceptance checks, recovery commands, and cost
notes. Marked the older Render topology in the auth operations document as
historical. No application source or pre-existing Code Generator changes were
included.

### 2026-09-05 01:10 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [9fabd58] - consolidate agent outputs and eliminate prebuild-output legacy locations

Cleaned up repository structure and unified all agent outputs under a single canonical `output/` directory:
(1) Removed deprecated `prebuild-output/` directory, including git-removal of legacy August zip packs (`15-36-25-08-8acdcb12` and `22-51-01-09-1961f2c9`), unadopted proposal document, and admission scratch files.
(2) Cleaned `output/build-preparation/` by removing 54 empty/corrupted/ineligible runs while strictly preserving the 2 verified eligible packs (`01-31-04-09-94ae4a9c` benchmark and `01-28-04-09-fb8c6001`).
(3) Pruned `output/code-gen-output/` to retain the 3 newest full generation runs, and deleted obsolete empty staging directories (`output/build-preparation-staging`, `output/test-build-preparation`, `output/live-build-preparation`).
(4) Removed stray `src/oryxenai/output/` directory and unreferenced `VDD-NEW-OUTPUT.MD`, root `.pytest-tmp*`, and scattered `.uv-cache*` directories.
(5) Updated `config/app.docker.codegen-run.toml` and `docs/run/run.md` to reference `output/build-preparation`, added `output/README.md`, and refined `.gitignore` to cleanly ignore ephemeral runs under `output/*` while tracking `output/README.md`.
Verified with ruff and test suites across build preparation and development input discovery.

### 2026-09-04 23:45 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [112d1a6] - add commit-cadence policy to the multi-agent protocol

Added rule 6 to `AGENTS.md`'s multi-agent collaboration protocol: commit locally at natural checkpoints (session end, meaningful chunk of work, before any bulk filesystem operation) regardless of whether the change meets the `CHANGES.md` "major work" bar, flag pre-existing uncommitted changes at session start instead of silently building on top of them, and push regularly so a branch doesn't drift far ahead of `origin`. Directly motivated by the incident in the entry immediately below: a local commit is the only real protection against losing work to something outside git (an accidental delete, a filesystem tool, antivirus quarantine), since git history survives all of those and an unprotected working tree does not.

### 2026-09-04 23:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [6ab319a, 5d8a93b, 6cec47b] - sync docs, persist active session client-side, fix diagnostic reporting

Recovered from an accidental local mass-deletion of `src/`, `tests/`, `scripts/`, and `prebuild-output/` (Windows Explorer delete, not a git operation) via `git restore` plus the user's own Recycle Bin restore; verified via `git diff`, Python `py_compile`, and TypeScript `tsc --noEmit` that nothing was lost or corrupted before committing anything. Then committed the real uncommitted work that had accumulated: (1) `docs(agents)` [6ab319a] synced `AGENTS.md`/`DECISIONS.md` with the already-shipped Markdown-brief handoff and ScaleMax routing work (D-064 through D-066), compacting superseded entries; (2) `feat(frontend)` [5d8a93b] made `AppShell` restore the active session id from `sessionStorage` on load instead of only trusting the server-provided id (survives a refresh), redesigned `StartSurface`'s hero/method-banner layout, and fixed the discovery adapter to report `available` instead of a stuck `working` state when a session has zero questions yet; (3) `chore` [6cec47b] fixed `test_openai_key.py` always printing success even when every model call hit `insufficient_quota`. Pushed all 14 previously-unpushed local commits to origin. Added a commit-cadence policy to AGENTS.md (see that commit's own entry) directly motivated by this incident: nearly a full day of uncommitted work was briefly exposed to total loss because it sat in the working tree only.

### 2026-09-04 16:30 +05:30 - Codex (GPT-5 / OpenAI) - [5b84673, 871f960] - harden migrated Code Generator generation

Completed the Build Preparation Markdown handoff migration: fenced-index parsing with CRLF tolerance, immutable identity-addressed admission, closed-navigation projections, blueprint/planner normalization, v5 queue and worker-release fencing, deferred resource placement, reference-only optional registry components, cached provider readiness, and serial route-batch calls. Replaced the stale Code Generator issue log with current root causes and follow-up checks. Parser/workspace/resource smoke checks, targeted planner/pipeline/service tests, Ruff, mypy, and Node syntax checks pass. A live run reached valid foundation/acquisition checkpoints before the configured provider returned 429 during route generation; no additional live calls were spent.

### 2026-09-04 11:24 +05:30 — Codex (GPT-5 / OpenAI) — [1f0ed68] — migrate Code Generator to Build Preparation brief contracts

Replaced the retired ZIP/object-store intake with strict parsing of Build Preparation's two Markdown briefs, immutable JSON-envelope admission, projection compilation, and closed-navigation enforcement. Wired pinned image/font/component candidates into deferred acquisition with explicit local fallbacks, made planner criteria compiler-owned, raised source validation to the configured generation ceiling, refreshed the production/development handoffs and UI, and updated the stale migration test; local parser, planner/session/resource/preflight, browser-harness, Ruff, mypy, and compile checks pass. Live acceptance was limited to three attempts and stopped at the requested cutoff before a preview was promoted.

### 2026-09-04 05:36 +05:30 - Codex (GPT-5 / OpenAI) - [389fa28] - ship the authenticated three-agent editorial studio

Restricted the normal `/app` product to Discovery, Content Architect, and Visual Design Director, with explicit start/revise/approve handoffs and approved Visual Direction as the honest terminal state; removed Build Preparation, Code Generator, and Preview calls, adapters, routes, and components from the product bundle without weakening their backend authorization. Split attached product auth from independently configurable local development harness auth through `auth.development_harness_mode`, retaining attached fail-closed production/test defaults. Rebuilt the auth and product surfaces around the restrained Editorial Proofing system with a self-hosted licensed Newsreader subset, asymmetric composition, responsive recomposition, accessible focus/reduced-motion behavior, persisted Discovery transcript reconstruction, observable stale/offline recovery, and branded loading/error/completion states. Updated D-063 and the frontend blueprint, and verified the production build, frontend suites, auth/bootstrap runtime suite, focused auth/config/route suite, task-owned Ruff checks, TypeScript, and mypy. The repository-wide pytest run reached the existing Build Preparation integration expectation that assumes a blocked offline result but received a successful live result; online Google acceptance remains externally blocked because the configured Supabase hostname does not resolve.

### 2026-09-04 01:35 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [1627f5d] - complete evidence-based Build Preparation brief fixes and diagnostic harness optimizations

Resolved four live-observed defects and prompt bloat in Build Preparation briefs and shared image retrieval:
(1) Added `purpose` and `guidance` to `resources` and `components` in `build_visual_brief()`'s machine-readable `build-preparation-visual-index` JSON block, exposing role intent and model crop/treatment notes programmatically rather than only in prose reference tables.
(2) Deduplicated Pixabay comma-separated tags case-insensitively while preserving first-seen order in `_clean_pixabay_tags()`, stripping noisy repeated tags from candidate `title` and `description` across both live API and cached lookups.
(3) Fixed duplicated route prefixes in auto-derived role IDs in `normalize_visual_input()`, changing `assumed-image:{route_id}:{section_id}:{ordinal}` and `assumed-component:{route_id}:{section_id}:{role_id}` to `assumed-image:{section_id}:{ordinal}` and `assumed-component:{section_id}:{role_id}`.
(4) Added explicit `navigation_contract` (`{"closed": true, "allowed_destinations": [...]}`) to `build_content_brief()`'s JSON index and an unambiguous closed-scope assertion sentence in the prose body to prevent downstream route/destination invention.
(5) Optimized model prompt packet in `_compose_visual_brief()` by stripping raw URLs, licenses, attribution, and extra registry metadata from candidate objects sent to `openai_luna` while leaving full metadata intact on brief assembly.
(6) Optimized `/build-preparation-fixture` developer harness with run-state button locks preventing race-condition double-clicks, direct "Copy Markdown" buttons for each brief, and 2-second timeout clipboard feedback.
Verified with 58 passing unit and API tests, clean ruff/mypy checks, and a live end-to-end browser execution against `openai_luna` on port 8001.

### 2026-09-04 00:45 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [a8ad4e7] - prune hallucination-prone AI skills and retain stack-respectful core

Audited and pruned `.agents/skills/` to eliminate framework and tool hallucinations across parallel coding agents (Claude Code, Codex). Deleted 11 conflicting skills that falsely mandated Tailwind CSS, Next.js Server Components, Framer Motion, GSAP, iPhone mobile mockups, Google Stitch, or pre-code image generation (`brandkit`, `design-taste-frontend`, `design-taste-frontend-v1`, `gpt-taste`, `high-end-visual-design`, `image-to-code`, `imagegen-frontend-mobile`, `imagegen-frontend-web`, `industrial-brutalist-ui`, `minimalist-ui`, `stitch-design-taste`). Preserved the three stack-respectful, universally safe skills: `no-ai-slop` (pure copywriting and anti-buzzword filter), `full-output-enforcement` (prevents LLM code truncation and placeholder shortcuts), and `redesign-existing-projects` (framework-agnostic audit methodology). Synchronized `skills-lock.json` and verified with 134 passing Vitest tests.

Rebuilt Build Preparation from a 5-model-call, ZIP/R2-packaged pipeline (~6,000 lines of PIL-based image download/pixel-inspection, component-source fetch, and pack/execution-contract machinery across `quality.py`, `materializer.py`, `providers.py`, `execution.py`, `contracts.py`, `packager.py`) into a 1-model-call pipeline that never downloads a byte: deterministic scope compilation (unchanged `compiler.py`), deterministic discovery-only provider research (new `resource_research.py` + a trimmed `providers.py` keeping every search-only Pexels/Pixabay/Fontsource/registry function and deleting every byte-fetching one), a single bounded `compose_visual_brief` model call that may only pick a candidate by index from the exact list it was given (validated structurally, never trusted), and deterministic Markdown assembly (new `brief_assembly.py`) producing `content-and-narrative-brief.md` (Content Architect's approved copy inserted verbatim, never model-touched) and `visual-and-build-brief.md` (design/layout/resource guidance prose plus reference tables). Both briefs persist directly on `portfolio_sessions.current_state["build_preparation"]` — no ZIP, no object storage, no pack version, no checkpoint system. Deleted `materializer.py`, `packager.py`, `quality.py`, `execution.py`, `contracts.py`, `checkpoint.py`, and five of six old prompt files outright; rewrote `agent.py`, `schemas.py`, `state.py`, `validators.py`, `fixture.py`, `fixture_runs.py`, `service.py`, `jobs/handlers/build_preparation.py`, the API download route, both fixture-harness HTML/JS pages, `config/app.toml`/`config/app.docker.toml`/`config/app.test.toml`, and `core/settings.py`'s `BuildPreparationConfig`. Made Code Generator's now-orphaned dependency on the deleted pack modules safe without attempting its full migration: `development_input.py` no longer imports `build_preparation.contracts`/`packager` and its ZIP-content admission fails closed with `PACK_INGESTION_NOT_MIGRATED`; `CodeGeneratorService.start()`'s session-bound production path fails closed with `CODE_GENERATOR_INGESTION_NOT_MIGRATED` immediately after the Build Preparation readiness check, rather than dereferencing removed fields; `_session_source_is_current` now always reports stale. Recorded D-062, explicitly superseding/partially revising D-009/011/013/018/021/025/028/029/030/031/032/033/035/051/060/061 and naming Code Generator's actual ingestion migration as separate, not-yet-done follow-up work. Rewrote the Build Preparation unit/API test suites for the new contract and the handful of Code Generator tests that referenced the deleted pack shape; full mypy/ruff pass clean across `src/`; 962 unit+API tests pass repo-wide.

### 2026-09-03 16:45 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [222419a] - document 5-user zero-cost deployment and complete GitHub Student Pack roadmap

Authored and refined `docs/github-student-pack-benefits.md` providing an exhaustive analysis of the GitHub Student Developer Pack (83 partner offers across 14 categories) tailored specifically for an operational scale of maximum 5 concurrent users. Modeled exact resource consumption, database footprint (<20MB PostgreSQL JSONB state, operating well within OryxenAI's 15-user capacity gate), and a 24-month zero-dollar runway across Heroku ($13/mo for 24 months = 24-month free web+worker dynos), Azure ($100 credit), custom domains (Namecheap .me, Name.com .dev/.app, .TECH), multi-viewport visual layout QA (Polypane, BrowserStack, LambdaTest), observability (<3% of Sentry 50k error quota, Datadog 10 hosts for 2 years, Honeybadger worker heartbeat), secret management (Doppler Team plan), and local S3 emulation (LocalStack Pro).



Applied the redesign-existing-projects and design-taste-frontend-v1 skills to eliminate remaining AI design clichés across the studio interface. Upgraded PipelineStagePreview into a Bento 2.0 architectural grid featuring an asymmetric 3-col (authoring & creative) / 2-col (compiler & synthesis) layout, unique discipline SVG icons, monospace stage codes (`STG-01` to `STG-05`), liquid glass refraction (`border-white/10` with `box-shadow: inset 0 1px 0 rgba(255,255,255,0.08)`), and perpetual micro-motion indicators (`bento-pip-pulse` and `bento-pip-active`). Enforced the Anti-Emoji Policy by replacing the unicode lock emoji in StartSurface with an inline SVG padlock vector. Added subtle atmospheric radial spotlight illumination to the start hero section, enabled `text-wrap: balance` on display headers and `text-wrap: pretty` on paragraph bodies, and ensured clean responsive collapse to single-column on viewports < 640px. Verified with 134 passing Vitest tests, clean Vite production build, passing ruff check, and browser verification confirming 0 console errors.

### 2026-09-03 14:35 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [28b8b1c] - deliver zero-scroll studio command center, fix engine polling invocation, and add live progress monitors

Overhauled the OryxenAI frontend into an agency-grade studio command center with zero scrolling required on standard viewports (< 730px). Eliminated the V8 `TypeError: Illegal invocation` bug in `frontend/src/data/polling.ts` by wrapping `setTimeout` and `clearTimeout` in safe closures, unblocking live engine status polling across all stages. Re-architected `StartSurface.tsx`, `ArchetypeSelector.tsx`, and `shell.css` into a compact, double-bezel command center (460px height footprint) featuring single-row segmented archetype selection (`SYS-01`, `CRT-02`, `PRD-03`, `RES-04`), monospace prompt textarea with `Ctrl+Enter` shortcut, and island button architecture with nested circular trailing icon. Added universal live engine progress monitors with animated radar beacons, elapsed stopwatches, and milestone checklists across Discovery, Content Architect, and Visual Design Director stages. Verified with 134 passing Vitest unit tests across 16 suites (including invocation safety test), clean production Vite build, 441 passing backend unit tests, and live browser verification showing 0 console errors and working engine start.

### 2026-09-03 13:55 +05:30 - Antigravity (Gemini 2.5 Pro / Google) - [2cc2cb9] - redesign studio hero, invert user journey, and modernize design tokens

Redesigned the studio frontend and authentication surfaces to an agency-grade, high-contrast dark atelier aesthetic. Inverted the user intake journey by moving the primary Command Center input box directly inside the Hero above the fold, embedding single-click archetype chips (`SYS-01`, `CRT-02`, `PRD-03`, `RES-04`) and quick-focus pills into the double-bezel header so users can immediately direct their portfolio without scrolling. Purged all AI-slop copy and banned visual clichés (eliminated the `#f3f0e8` beige paper palette and Georgia serif, replacing with deep obsidian midnight `#090d16`, frosted glass `#0f172a`, electric sapphire `#3b82f6`, and Plus Jakarta Sans / Cabinet Grotesk / JetBrains Mono). Upgraded auth shell (`/` & `/sign-in`) with ambient mesh backdrop, official Google SVG sign-in button, and double-bezel cards while preserving all DOM IDs and controller contracts. Updated ArchitecturalCanvas with luminescent drafting points and crosshair coordinates for the dark theme. Fixed 4 linter errors in test_openai_key.py. Verified with 133 passing Vitest tests across 16 suites, passing typechecks, clean production Vite build, 75 passing backend tests across auth and discovery routes, and visual browser subagent verification with 0 console errors.

### 2026-09-03 12:10 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [c461b49] - raise the generated-source size ceiling to a real value

The single-rendition fix (`5b4a33c`) stopped duplicate provider-side pre-rendering, but a fresh run still hit `SOURCE_TOTAL_TOO_LARGE`. Direct reproduction showed the deferred path was never the problem: `_pack_image_renditions` (the same local rendition generator a pack-embedded image has always used) legitimately produces a comparable responsive set from the one fetched original -- a real six-photo route measured ~10-13MB of legitimate renditions plus generated JS/CSS/content, and the prior 8MB ceiling had never actually been exercised against a real, full-content pack before this session. Raised `max_source_bytes` from 8MB to 32MB in `config/app.toml` and its Pydantic default. Confirmed via direct reproduction: diagnostics count 0 for the same pack/plan/ledger that previously failed. 926 unit tests pass; ruff clean. Fifth and, per reproduction, final blocker found in this D-060 live-verification pass.


---

## Compacted history

### 2026-09
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

## Summary (as of last compaction — 2026-09-05)

- Recent detailed entries retained: 16
- Compacted milestone bullets: 145
- Last updated: 2026-09-05 15:23 +05:30 — Codex (GPT-5 / OpenAI)
