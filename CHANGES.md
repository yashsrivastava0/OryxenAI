# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-08-28 03:35 +05:30 - Codex (GPT-5 / OpenAI) - [27b9679] - retry denied Windows process-group launches
The worker continued to receive `[WinError 5]` at process creation even after
batch commands were routed through `cmd.exe`. The bounded process runner now
retries an allowlisted Windows batch command without only the optional new
process-group flag when that flag is denied, retaining no-window execution and
the existing process-tree cleanup path when the group can be created.

### 2026-08-28 03:28 +05:30 - Codex (GPT-5 / OpenAI) - [90f2a82] - launch Windows batch toolchains reliably
The live worker exposed `[WinError 5] Access is denied` when its process
runner attempted to spawn the PATH-resolved `npm.CMD` directly, stopping the
frontend resume before route validation. Allowlisted `.cmd`/`.bat` commands
now cross the Windows command-interpreter boundary with their validated argv,
while native executables retain the no-shell process path.

### 2026-08-28 03:24 +05:30 - Codex (GPT-5 / OpenAI) - [253b1fa] - preserve toolchain launch diagnostics
The tenth frontend resume was repeatedly stopping before source validation with
only `TOOLCHAIN_START_FAILED`, although the same configured offline install
worked in isolation. Process-start diagnostics now retain the operating-system
error and the worker surfaces it in the bounded source diagnostic, making a
native launch failure observable and actionable.

### 2026-08-28 03:12 +05:30 - Codex (GPT-5 / OpenAI) - [414b0c7] - enforce route-batch anchor IDs before composition
The resumed frontend run showed that route batches could checkpoint validly
resolving modules while using shortened DOM IDs (`hero`, `experience`) instead
of the authoritative route-scoped IDs required by the V4 audit. Batch
checkpointing now validates its deterministic anchor's route, content, DOM-ID,
and assigned-marker literals, and stale checkpoints are reopened when that
contract fails so the owning Luna operation receives the repair.

### 2026-08-28 03:07 +05:30 - Codex (GPT-5 / OpenAI) - [ab3672f] - validate route-batch local export bindings
The tenth live frontend run showed that path resolution alone allowed a route
batch to checkpoint self-imports and invalid named re-exports; the later whole-
site audit then reported them against the composer. Route batches now validate
named local imports/re-exports against target-module exports before checkpoint,
reopen stale invalid batches on resume, and receive explicit one-component-per-
owned-file guidance.

### 2026-08-28 03:02 +05:30 - Codex (GPT-5 / OpenAI) - [8ee6947] - bound retry diagnostics to the active work unit
The route-batch import guard correctly found five stale imports, but the
retry context also carried unrelated composer history and crossed the 120,000
character ceiling before Luna was called. Generation prompts now include only
diagnostics owned by the active work unit, keeping the actionable repair data
while preserving the configured context limit.

### 2026-08-28 02:48 +05:30 - Codex (GPT-5 / OpenAI) - [eb55728] - validate route-batch imports before checkpoint recovery
The resumed tenth run proved that valid batch ownership was not enough: model
source could checkpoint imports that only failed once the composed route was
audited. Route batches now receive an exact trusted-module import map and a
bounded resolver before checkpointing; same-run retries reopen stale batches
and reset only the failed attempt's repair budget, preserving the durable run
and its accepted foundation.

### 2026-08-28 02:40 +05:30 - Codex (GPT-5 / OpenAI) - [d620d1f] - isolate V4 composer authority and resume terminal generation
The tenth live frontend run showed that the composer still received batch-owned
content IDs, facts, and route bindings even after its content instruction was
disabled; Luna consequently retyped copy and failed the host coverage contract.
The V4 composer context now removes those ownership fields, and the standalone
UI plus service recover terminal queued/checkpointed runs through an explicit
same-run resume path without consuming another full-pipeline attempt.

### 2026-08-28 02:24 +05:30 - Codex (GPT-5 / OpenAI) - [c0b4087] - give same-run generation retries fresh durable job identities
After the composer contract fix, the standalone UI correctly attempted to
resume the failed run, but the generation service reused the completed
idempotency key from the earlier resume and left the run queued without a new
worker job. Generation retry keys now include the run revision, preserving
checkpoint reuse while ensuring every terminal retry is executable and
observable.

### 2026-08-28 02:20 +05:30 - Codex (GPT-5 / OpenAI) - [772bef1] - align V4 composer content contract with work ownership
The tenth live frontend run reached route composition after the context ceiling
fix, but the V4 composer was instructed to report every approved route content
key even though its WorkUnit owns only the route shell and no sections. The
validator correctly expected no content coverage for that unit and exhausted
repairs on the contradictory contract. V4 composer contracts now direct the
model to render the completed section batches and reserve content-key coverage
for the section-owning route batches; a regression test locks the boundary.

### 2026-08-28 02:08 +05:30 - Codex (GPT-5 / OpenAI) - [70b024d] - version the detached generator module with the shell
The detached development page versioned its bootstrap module but imported the
main Code Generator module without the computed asset version, allowing the
browser to retain stale controls after a frontend fix. The shell now passes the
main module version through the bootstrap and dynamically imports that exact
version, ensuring the standalone UI exercises the committed implementation.

### 2026-08-28 02:00 +05:30 - Codex (GPT-5 / OpenAI) - [5edcb30] - resume bounded generation after a context failure
The tenth live frontend run completed both route batches but stopped before the
composer model call because its bounded context was 122,064 characters. The
composer now receives only source-relevant existing-file names and no duplicate
generated-content interface; the measured context is 115,003 characters against
the 120,000-character ceiling. Same-run generation retries preserve the durable
generation projection and accepted work-unit checkpoints, and the standalone
frontend exposes that path as Resume generation instead of requiring a fresh
portfolio run.

### 2026-08-28 01:44 +05:30 - Codex (GPT-5 / OpenAI) - [e12d787] - defer route-batch whole-site audit
The ninth live frontend generation produced valid route-batch responses, but
the post-batch source audit still inspected the scaffold route shell before
the composer owned it. Its repair diagnostics therefore asked the batch
operation to mutate the trusted route shell. Route batches now run repository
and toolchain checks without the whole-site AST audit; composition and final
integration retain the audit at the correct ownership boundary.

### 2026-08-28 01:38 +05:30 - Codex (GPT-5 / OpenAI) - [d5247dd] - make V4 resource coverage explicit
The eighth live frontend generation passed the planner and model source calls,
but both route batches reported only the image slots they used. The host
correctly requires the coverage array to match the complete work-unit
assignment, including optional package, recipe, and component slots. The
normative generation contract and route-batch prompt now expose and require
that exact ordered list, with focused prompt-contract regression coverage.

### 2026-08-28 01:30 +05:30 - Codex (GPT-5 / OpenAI) - [169ea5f] - expose bounded generated-content interface
The seventh live frontend generation passed planning and resource acquisition
but the route batch could not safely generate because its operation context
omitted the trusted `src/content/generated-content.ts` API. Route work now
receives a compact interface excerpt containing the exact approved content-key
union and frozen export signatures, while approved prose remains supplied by
the route-scoped contract instead of being duplicated in the context. Added a
regression test for API presence and prose compaction.

### 2026-08-28 01:19 +05:30 - Codex (GPT-5 / OpenAI) - [fb1c209] - require explicit V4 typography roles
The sixth live frontend generation reached the live Luna planner but returned
an invalid V4 token system because omitted typography roles were defaulted to
`body`, producing duplicate body roles. The schema now requires every
typography binding to carry an explicit `body` or `display` role, and the
planner contract states the exact one-body/optional-display invariant. Added a
regression test proving an omitted role is rejected before generation.

### 2026-08-28 01:09 +05:30 - Codex (GPT-5 / OpenAI) - [cbe4491] - bound Code Generator operation context to its work unit
The fifth live frontend generation proved a separate source-generation failure:
the route model request serialized approximately 245k characters because the
context builder walked unrelated generated manifests and public-content source,
exceeding the configured 120k ceiling before the first route call. Context
assembly now scopes plans, visual/resource/execution projections, trusted APIs,
and direct route dependencies to the active work unit, preserving the complete
inputs for host validation and keeping the route/composer contracts bounded.
Added regression coverage for excluding unrelated source and historical ledger
payloads.

### 2026-08-28 00:45 +05:30 - Codex (GPT-5 / OpenAI) - [d1a229d] - phase-aware V4 source checks
The fourth live frontend generation confirmed that the complete V4 route audit
was being applied while the deterministic foundation and route-batch phases
still intentionally contained the scaffold route shell. Source/toolchain
checks now support deferring the whole-site AST audit during those early
phases; the audit remains required for route composition and final integration.
Added regression coverage for the explicit audit deferral.

### 2026-08-28 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [8c07530] - trusted source audit and token emission reliability
The third live frontend generation passed planning, acquisition, and TypeScript
typechecking but exposed two deterministic scaffold/compiler defects before
promotion: the source audit read JSX element fields from the wrong TypeScript
AST shape, and V4 typography roles could emit duplicate custom properties when
a type step shared the role name. The audit now handles JSX elements and
self-closing elements correctly, while typography emission is collision-safe;
regression coverage asserts unique body/display variables.

### 2026-08-27 11:40 +05:30 - Codex (GPT-5 / OpenAI) - [caead48] - transactional optional dependency fallback
The first live frontend generation reached source generation but failed at the
trusted toolchain because acquisition recorded `lucide-react` as
`rejected_fallback` while its partially mutated workspace manifest still
required the uncached package. Dependency resolution now runs lockfile and
offline installation in a disposable sibling workspace, publishing the
manifest, lockfile, and installed modules only after success. A rejected
optional package therefore cannot poison the later npm toolchain check, while
successful admitted dependencies still replace the workspace as one complete
installed set. The regression test verifies that a failed optional install
leaves no package manifest behind.

### 2026-08-27 12:05 +05:30 - Codex (GPT-5 / OpenAI) - [d4fe70f] - host-owned V4 blueprint identity contract
The live frontend planner context contained no semantic owner IDs even though
the trusted prompt required Luna to echo them, allowing duplicate owners to
reach the V4 validator. Added a deterministic route/section identity manifest,
exact host-side identity validation, prompt grounding, and regression tests so
V4 planning cannot invent or reuse region ownership identities.

### 2026-08-27 03:32 +05:30 — Codex (GPT-5 / OpenAI) — [1e3610e] — make the native dev launcher reliable from this workspace
The first clean smoke test exposed two Windows launcher issues in the new
one-command native path: `uv` was trying to use a user-level cache that was
not accessible in this workspace, and `Start-Process` split the repository
path at the space in `Yash Srivastava` when composing the hidden child
services. The native PowerShell and shell helpers now use the repository-local
`UV_CACHE_DIR`, and the PowerShell launcher quotes its script path before
starting exactly one API, worker, and preview child. A clean `dev` start was
then verified with API and preview health responses, one worker's established
connections to canonical PostgreSQL 5432, and no listener on 5545 or 8001.

### 2026-08-27 03:18 +05:30 — Codex (GPT-5 / OpenAI) — [78ee3ea] — remove unreachable foundation model machinery and correct architecture docs
Removed the unreachable Code Generator foundation model profile, routing entry,
prompt lookup, prompt file, and preflight/profile admission. The V3/V4
foundation stage remains a live deterministic compiler boundary for generated
tokens and approved content; its WorkGraph unit, lifecycle status, source audit,
and `foundation_builder` resource-provenance role remain intact. Updated the
operation-role documentation to describe the deterministic compiler and added
a current-contract note to the historical v2 architecture document. Corrected
the preview deployment guide from the never-built wildcard-DNS topology to the
implemented single-origin `/preview/{host}/{path}` gateway path. The existing
safe diagnostic mapping also remains statically typed after the cleanup.

### 2026-08-27 03:08 +05:30 — Codex (GPT-5 / OpenAI) — [e945f54] — truthful preview readiness and hosted Docker contract
Made the shared preview gateway part of the default Compose topology and
passed the hosted storage credentials into that service. Readiness now probes a
typed internal health URL asynchronously with a short timeout, no redirects,
and 2xx-only success; native configuration derives a loopback target while
Docker uses `preview-gateway` service DNS because `localhost` is container-local
and `0.0.0.0` is only a bind address. Configuration and UI diagnostics
distinguish a missing/invalid health target from an unreachable gateway.

The hosted `config/app.docker.toml` overlay now alone enables strict public
preview readback and keeps artifact-backed storage. The isolated
`oryxenai-codegen` overlay remains local-filesystem-backed and lenient, and
native/test behavior remains lenient. The browser-facing `preview_base_url`
contract is unchanged. Added settings, probe, route, frontend, Compose, and
native-launcher coverage/documentation; no database or migration changes were
made.

### 2026-08-27 02:57 +05:30 — Codex (GPT-5 / OpenAI) — [b92a86c] — native process alignment and code-generator diagnostics
The stuck detached run was caused by two independently verified operational
conditions. The port-8000 API had an established PostgreSQL connection to the
manually launched `.workspace/postgres-native-5545` instance, while the worker
had established connections to the canonical PostgreSQL instance on port 5432;
the run therefore existed in a database the worker could never poll. Port 5545
does not occur anywhere in checked-in configuration, scripts, or documentation,
so the remediation was process cleanup rather than a repository config change.
The duplicate API (8000/8001) and worker processes were inventoried, the
identified APIs/workers, preview process, and only the rogue 5545 PostgreSQL
instance were stopped, and the canonical 5432 instance was kept running. The
orphaned run `f7c2eece-1ab3-4f2b-8ff3-a573fe9c2ece` and job
`3193daba-7d28-4dff-bdca-7d516c4e3d90` were deliberately abandoned rather than
recovered. A clean worker was started after `b4f7daa`; no pre-fix worker
remained, and a fresh run proved plan success creates the acquire successor.

The same fresh-run evidence exposed a separate deterministic Phase 1b defect:
the WorkGraph compiler replaced multiple unique V4 semantic section owner IDs
with one route-batch ID, making the persisted `ExperienceBlueprintV4` invalid
when revalidated. Compilation now preserves semantic owners and leaves
executable ownership to the WorkGraph. Safe bounded planner/acquisition
validation summaries were also surfaced through the existing redacted issue
path. Focused tests cover both fixes. The subsequent live run reached
generation and stopped only because offline npm cache mode lacked
`lucide-react`; that is recorded as a toolchain/environment limitation, not a
database-split or auto-advance failure.

### 2026-08-26 22:53 +05:30 — Claude Code (Claude Sonnet 5 / Anthropic) — [b4f7daa] — code_generator/core/coordinator
`advance_after()` always built a real `DurableAuthorizationContext` when auto-enqueuing the next stage, even for detached development runs with no owner/actor/session; that context's `authorization_context_version` was always 0, which tripped `JobService.enqueue`'s guard against version-0 contexts on portfolio-bound work before it ever reached the development-run recognition path — silently blocking every auto-chained stage advance in the detached control room. Passed `context=None` for non-session runs, mirroring the existing `run_mode`-based payload_key split so development runs go through the `run_mode` check instead.

### 2026-08-26 22:52 +05:30 — Claude Code (Claude Sonnet 5 / Anthropic) — [9b2d28f] — code_generator/core/development_planner
The V4 blueprint validator required a font role's `local_files` to exactly equal every WOFF/WOFF2 file under its admitted binding, even when the role's declared weights used only a subset of that binding's files — any shared multi-weight font resource (the common case) failed this check deterministically regardless of model output quality. Now requires `local_files` to be a subset of the admitted binding's files, matching the binding's own `font_weights`/`local_paths` split and the role's independent weights selection.

### 2026-08-26 16:40 +05:30 — Codex (GPT-5 / OpenAI) — [e5d55f9] — safe detached-run database diagnostics
Classified local PostgreSQL credential failures as an actionable 503 for the detached Code Generator, and added redaction for environment assignments, configured secret values, nested API details, and provider preflight messages. Added focused unit coverage so the control room cannot echo database or provider credentials.

### 2026-08-26 14:15 +05:30 — Codex (GPT-5 / OpenAI) — [8a918f3] — native detached origin allowlist
Allowed both native development ports in the local origin policy so the detached Code Generator control room can be tested on an alternate port while another local server remains on 8000. This fixes `ORIGIN_NOT_ALLOWED` for the live provider preflight without adding authentication or session behavior.

### 2026-08-26 13:59 +05:30 — Codex (GPT-5 / OpenAI) — [7c44add] — Code Generator detached control room, export handoff
Added the no-auth standalone control room with Build Preparation mirror bootstrapping, OpenAI `openai_luna` routing, responsive preview/timeline/inspector UI, and manual debug controls while preserving the attached auth boundary for later reattachment. Completed exports now persist a safe receipt and emit `generation-report.md` plus evaluator metadata so coding agents can diagnose the generator and fix the generator rather than the generated portfolio.

### 2026-08-26 10:10 +05:30 — Codex (model/provider omitted) — [9b39fe3] — Build Preparation resource relevance
Replaced generic repeated resource searches with profession-aware image roles and
semantic component roles, then added component-source and perceptual-image guards.
Provider/model packets are bounded, cooldown skips are reported separately from
real rate limits, and focused plus full-suite verification passed locally.

### 2026-08-25 23:35 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [5d6886a] - shared/providers/errors
Live account credit exhaustion during pipeline testing surfaced a real
classification gap: Anthropic's "credit balance is too low..." message
matched none of `_CREDIT_MARKERS` (tuned for OpenAI's vocabulary), so it
fell through to the generic `PROVIDER_INVALID_REQUEST_ERROR` bucket instead
of `MODEL_PROVIDER_CREDIT_EXHAUSTED`. Added Anthropic-specific markers;
reproduced live before and after — now classifies correctly.

### 2026-08-25 23:20 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [8e93fc2] - build-preparation/visual_input
Live full-pipeline run (real Discovery→CA→VDD→Build Preparation for a
fictional UI/UX designer profile) surfaced `role_for()`'s fallback silently
promoting any unrecognized section_id ("problem", "outcome",
"design-system-note") to the high-importance "selected-work" role,
required for handoff. Generic decorative images for these sections then
failed to materialize and correctly-but-wrongly blocked the whole pack
(5x `REQUIRED_RESOURCE_NOT_MATERIALIZED`). Added a genuinely low-stakes
"context" fallback role instead.

### 2026-08-25 23:15 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [2f9403b] - shared/component_retrieval
Same live run: cult-ui.com returned 429 on 15/15 consecutive component
registry requests across one Build Preparation run — no cross-query memory
of a prior rate limit, unlike the image-fetch path's existing
`_PROVIDER_RATE_STATE`. Added an equivalent per-provider backoff window to
`_get_json`; re-run after the fix hit cult-ui.com once, then correctly
skipped it.

### 2026-08-25 23:00 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [2a6fb12, 60a41a3] - visual_design_director prompts, jobs/worker
Live-reproduced a 3x Visual Design Director validation failure
(`validation_categories=['assets','references']`): `integrate_site_experience`'s
full-pages reconciliation pass rewrote `asset_briefs.content_ref` into
invented composite forms (e.g. "novapay:case-hero") since several routes
legitimately reuse the same section_id and the model tried to disambiguate;
that prompt had no explicit ID-stability guidance for the rewrite, unlike
`direct_page_experience.md`. Added it; the next live attempt passed
cleanly. Also fixed `worker.py` never calling `configure_logging()`,
discovered because the worker log was completely empty while debugging
this — every `logger.info`/`.warning` call was silently dropped.

### 2026-08-25 21:20 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [ed9de3b] - build-preparation, materializer, providers, execution
Gave component materialization the same alternate-candidate retry loop
images already had (`_materialize_component_candidate`,
`ComponentMaterializationError`), instead of one rejection sending a
component straight to an execution gap. Removed ~190 lines of unreachable
dead code in `materialize_build_context` (a second photo-materialization
branch guarded by the same condition as the retry loop above it, which
always `continue`s) and `ProviderLookup._blocked_until` (read but never
assigned, so it never fired). Enriched `VDD_EXECUTION_GAP` messages to
distinguish "candidates were rejected, last reason: X" from "nothing was
ever attempted." `uv run pytest -k "build_preparation or
code_generator_development"` (106 passed, 7 skipped), ruff, and mypy all
clean on the touched files.

### 2026-08-25 21:10 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [40d0477] - code_generator_development, routes
Extended D-052's detached-auth pattern to the standalone Code Generator dev
harness: added `code_generator_development.detached_router` (no
`require_admin`) and select it over the admin-gated router in
`api/routes/__init__.py` when `auth.pipeline_mode == "detached"`. Production
Code Generator session routes (`code_generator.py`) are untouched. Recorded
as D-053.

### 2026-08-25 21:00 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [53cd913] - web/routes, web/static/app.js
Fixed the concrete cause of "Could not create a session. Is the API
running?": `/dev` hardcoded `pipeline_mode="attached"` regardless of
`config/app.toml`, forcing the full Supabase login flow even when
`auth.pipeline_mode` was `"detached"`. `/dev` now follows
`settings.auth.pipeline_mode` like `/app` already did. Also stopped
`createSessionQuiet`/`sendMessage` from collapsing every session-create
failure into the same generic string — the UI now surfaces the actual
status/code/message. `uv run pytest -k detached` passed (3 passed, 5
skipped) after the change. Live browser end-to-end verification is still
pending: this local machine's port 5544 (expected native PostgreSQL) is
currently held by Docker Desktop's WSL relay rather than a real Postgres
instance, so every DB connection attempt times out — a pre-existing local
environment condition, not caused by this change.

### 2026-08-25 20:20 +05:30 - Codex (model/provider omitted) - [87cad46] - detached Build Preparation auth boundary
Extended local detached mode through the Build Preparation fixture and progress
APIs, bypassed Supabase bootstrap with the anonymous no-store request boundary,
and redirected detached `/sign-in` to `/app`. Attached, Docker, test, and
production-like modes retain the admin boundary; added API/frontend regression
coverage (D-052).

### 2026-08-25 16:10 +05:30 — Codex (model/provider omitted) — [b70dde2] — detached fixture profile selection
Fixed the detached Build Preparation frontend and CLI so the internal
`build_preparation` engine route is not passed as a selectable profile. Live
runs now preserve a selectable profile from the approved VDD input, including
the configured Luna profile, while retaining normal engine routing otherwise.

### 2026-08-25 15:44 +05:30 — Codex (model/provider omitted) — [c9f0a95] — native Luna Build Preparation handoff
Hardened the native live Build Preparation path for bounded Luna output-shape
recovery, fixture approval stamping, Unicode CLI output, and bounded image
candidate retries. Aligned Code Generator admission with non-blocking optional
execution gaps; verified a live `build-preparation-pack-v3` ZIP through the
exact generator upload/admission path with zero blocking issues.

### 2026-08-25 15:06 +05:30 — Codex (model/provider omitted) — [62166f3] — durable model-output retries
Converted deterministic output-contract failures from terminal handler errors
into bounded, privacy-safe retries across Discovery, Content Architect, and
Visual Design Director. Successful retries now clear stale job errors; the
failed live OpenAI Luna VDD run recovered on attempt two to `design_review`,
and focused worker/integration verification passed.

### 2026-08-25 13:03 +05:30 — Codex (model/provider omitted) — [5f272b3] — migration and native doctor acceptance fix
Shortened the Build Preparation checkpoint revision ID to fit Alembic's
version column, added a chain-wide revision-length guard, and made the native
doctor reject revision-stamped databases that are missing required core
tables. Verified a complete base-to-head replay against the disposable empty
acceptance schema.

---

## Compacted history

### 2026-08
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

## Summary (as of last compaction — 2026-08-27)

- Recent detailed entries retained: 18
- Compacted milestone bullets: 53
- Last updated: 2026-08-27 — Claude Code (Claude Sonnet 5 / Anthropic)
