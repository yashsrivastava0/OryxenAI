# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

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

### 2026-09-08 15:10 +05:30 - Codex (GPT-5 / OpenAI) - [ddc2e77] - app: integrate Build Preparation, provider safety, and complete output rail

Extended the authenticated `/app` journey through an explicit Build
Preparation handoff after approved Content and Visual Design. Added durable
state adaptation, progress/attention/stale recovery UI, and a safe right rail
with exact persisted full-JSON copy controls for Discovery, Content Architect,
Visual Design Director, and Build Preparation. Kept Code Generator/Preview
outside the product flow and preserved explicit handoffs.

Completed the provider-neutral free-tier hardening from PLAN.MD: post-response
usage/cost/request telemetry (including wallet vs promotional consumption),
safe attributable provider errors, quota observation/redaction, in-flight
capacity preservation, and terminal accounting failure behavior, with the
wallet column migration and admin date/model filters. Verified with `uv run
pytest -q` (1,024 passed, 170 skipped), Ruff, mypy, frontend typecheck/Vitest,
Vite production build, browser-auth tests, and migration-head checks.

### 2026-09-08 11:14 +05:30 - Codex (GPT-5 / OpenAI) - [3a6cf25] - frontend: bust legacy bundle cache on bootstrap

The legacy pipeline bootstrap now imports its mutable static bundle with a
per-boot query string. This prevents browsers from retaining a pre-deployment
`app.js` module after a normal workspace refresh, so the newly committed
per-agent JSON copy controls are visible without a manual cache-clearing step.
Verified with the two browser-bootstrap regression suites (10 tests).

### 2026-09-08 11:10 +05:30 - Codex (GPT-5 / OpenAI) - [b07582d] - frontend: per-agent full JSON copy controls

Updated the development pipeline's Agent Workspace sidebar so each available
agent has its own Copy JSON control, while the selected-output control remains
available in the header. Discovery now copies JSON instead of a Markdown-only
summary, and Content Architect, Visual Design Director, and Build Preparation
copy the complete safe agent-owned projections while excluding raw intake,
source snapshots, credentials, run/job metadata, and worker errors. Added the
clipboard API with a select-and-copy fallback and explicit copy status text.
Verified with static JavaScript syntax checking, focused web/API tests, and the
frontend Vitest suite (72 tests).

### 2026-09-08 10:35 +05:30 - Codex (GPT-5 / OpenAI) - [7f2fbd0] - discovery retry/provider metadata fix
Fixed repeated manual Discovery retries reusing the worker attempt number and colliding with the durable AgentRun idempotency constraint. Also keeps job-attempt tracing metadata internal to the OpenAI-compatible adapter; added regression coverage, and verified the live Experiential Luna browser flow reaches questions.

### 2026-09-08 05:25 +05:30 - Codex (GPT-5 / OpenAI) - [9d256f3] - model-routing: provider-neutral Experiential/Gemini routing, quota ledger, bounded recovery

Implemented PLAN.MD's first-four provider strategy: Experiential GPT-5.6 Luna is the personal-input route, explicitly sanitized/synthetic lightweight work can use independently observed Gemini Free Tier capacity, and no normal first-four call uses `OPENAI_API_KEY`. Added operation-level routing profiles, one durable normal/recovery budget, zero SDK retries, route-aware cache identity, PostgreSQL usage/attempt/reservation/capacity telemetry, provider reconciliation hooks, safe attributable frontend errors, and the native Gemini adapter. Added the Windows `tzdata` runtime dependency required for Pacific daily quota windows, plus the compatibility receipt fix needed by the complete suite. Live probes succeeded on `EXPLABS`/`gpt-5.6-luna` and `GEMINI_1`/`gemini-3.5-flash-lite`; full verification: 1,002 passed, 169 skipped, mypy clean, migration `0022_model_usage_ledger` at head. Records D-078.

### 2026-09-07 18:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [7f09506] - code-generator: unverified candidate preview for needs_attention runs; fix stale-job cost bug and uncommitted export_receipt write

Switched from the scratch-script harness to the real `/dev/code-generator-
development` control room (API + worker + preview gateway, driven by real
browser clicks) at the owner's request, to watch a run and see a preview
the way a real user would. Two real bugs surfaced by doing this live that
neither code review nor unit tests had caught: (1) starting a real worker
immediately began reprocessing 95 job rows the scratch script had left
permanently `queued` since 2026-09-05 (it calls handlers directly and
never marks the underlying row complete) -- real paid OpenAI calls against
runs that already concluded days ago, with the new run stuck at the back
of a 96-job queue; caught within seconds via the worker log, stopped,
cancelled the 95 stale rows with a reason recorded, restarted clean --
not a pipeline defect, an operational hazard from mixing the scratch
harness with a real worker. (2) The new preview feature below silently
didn't persist on first implementation: `compare_and_swap()` never commits
internally, and none of its three call sites (nor a manual verification
script) called `db.commit()` after it -- the write looked successful and
raised nothing, but silently rolled back. Caught only by checking the
actual API response after implementing, not by trusting a green test run;
fixed all three call sites plus the script.

Added the feature itself: a needs_attention run's own already-built
`dist/` (real since the earlier auto-build fix) now shows in the dev
harness's preview panel instead of "Preview unavailable," via a new
dev-only route serving that run's export folder directly off disk
(path-traversal-checked, reusing the existing `_safe_path`/
`_inject_preview_base`/`_headers` helpers the promoted-preview and
ephemeral candidate gateways already use). Clearly labeled "Unverified
candidate · not promoted" (amber, distinct from both the mint "verified"
and coral "error" states) so it can never be mistaken for a passed run.
`export_failed_run`'s three call sites now also write an `export_receipt`
onto the run row so the run-state API and Output tab can find the export
at all -- previously only the promoted-success path populated this field.
Live-verified end-to-end (not just unit tests): triggered a real run from
the UI, watched it progress stage-by-stage, confirmed the candidate route
serves real assets (JS/CSS/fonts/images, all 200), confirmed the embedded
preview bridge handshake completes, watched the actual generated
portfolio render in the frame, and confirmed the state survives a full
page reload. `uv run pytest`: 996 passed, same 1 pre-existing unrelated
failure; `node --test tests/frontend/code_generator_development.test.mjs`:
17/17 passed. This run's own pipeline outcome (zero repair rounds needed
at whole-site review -- a first this session -- then a new
`RUNTIME_REGION_WIDTH_RATIO` finding affecting 3 regions identically,
suggesting one shared systemic cause) is logged in `code generator
issues.md`, not fixed this pass.

### 2026-09-07 16:10 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [5bef169, ac5543e] - code-generator: root-cause both prior live failures via real DB history, fix 3 more validator/prompt bugs, live-tested with 2 more runs

Owner asked for the two prior live failures (`e624bd75`, `c8cd8f1c`) to be
understood at their actual root cause, not just described, then re-verified
before calling anything done. Read the real DB-persisted repair/review
history (`code_generator_events`, `generation_projection`,
`integration_review`) instead of only the terminal `SafeIssue` summary.
Found and fixed: (1) `e624bd75` lost its entire route batch to a 3-round
repair-budget exhaustion on a motion-beat check requiring the blueprint's
exact double-quoted `[data-motion-target="..."]` literal verbatim --
`[attr='value']`/`[attr=value]` are equally valid CSS the check couldn't
recognize, the same class of naive-substring blind spot as several prior
fixes, just for quote style. Added `_literal_present` (exact match first,
quote-tolerant attribute-selector regex fallback) in `source_validation.py`,
applied to the beat marker/selector checks and `_css_rule_contains`. (2)
`c8cd8f1c`'s real defect (distinctive-move marker on a nested div while the
actual grid/max-width lived on its parent) survived 5 polish rounds because
the whole-site reviewer reports it under its own code
(`distinctive-move-selector-mismatch`), not the structural code
`repair_source.md` already had a dedicated bullet for -- extended that
bullet to cover the review's own code. `uv run pytest`: 993 passed (+1),
same 1 pre-existing unrelated failure.

Live-verified with the 2 more runs the owner authorized (`e7784314`,
`4dbcabae`). Neither of the 2 just-fixed defect classes recurred. `e7784314`
got past generation cleanly this time but still hit
`INTEGRATION_REVIEW_UNRESOLVED` on two different findings (a missing
progressive-disclosure control, a hero frame missing an aspect-ratio) --
logged, not chased. `4dbcabae` reached the deepest pipeline state this
engagement has recorded on fully fresh content (`generate: succeeded` -> DOM
verification -> one repair round -> whole-site re-review), ending
`needs_attention` on one narrow new finding: a CSS `gap` shorthand
partially overridden by `column-gap` alone left `row-gap` correctly
cascading but never present as a literal property name, which a
finding/check requiring that exact name couldn't recognize -- same
blind-spot pattern, this time for CSS shorthand vs. longhand. Fixed with
route_batch.md (avoid the shorthand-plus-partial-override pattern) and
repair_source.md (split into explicit longhands when a finding names one)
guidance. All 3 post-fix exports (`c8cd8f1c`, `e7784314`, `4dbcabae`)
confirmed `build_attempt: success` with a real `dist/` -- the auto-build
fix is proven across multiple runs now, not a one-off. Still zero `ready`
outcomes across all 4 live runs this session; see `code generator
issues.md` for the full evidence trail and one new unresolved observation
(no verification screenshots captured on `4dbcabae`, cause not yet
determined).

### 2026-09-07 14:48 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [3f5b2aa] - code-generator: auto-build failed exports, fix two live-confirmed generation defects

Filtered an externally-authored output-analysis doc
(`docs/research/code-gen-output-analysis.md`) against actual code state
per the owner's explicit "don't trust it wholesale" instruction — most of
its findings were already fixed (cross-referenced against D-077 and this
file) and correctly left alone. Fixed what was still real: (1)
`export_failed_run()` now attempts a best-effort clean build
(`run_clean_build`) before exporting a needs_attention/failed run, so its
`dist/` and an honest `build_attempt` status ship automatically instead of
requiring a manual `npm ci`/`npm run build` to inspect it — the
"auto-build" capability the owner asked for; it already existed for
promoted runs, this closes the gap on the failure path. (2) Discovered
live, mid-session: the generation stage's own needs_attention path
(`generation_orchestrator.py::_fail`) never called `export_failed_run` at
all — a second, independent gap, and the majority-case one, since most
runs this engagement has recorded fail during generation rather than
after it. Wired the same best-effort export into it. (3) Added explicit
geometry-repair guidance to `repair_source.md` for
`blueprint-resource-role-mismatch` findings (a resource rendered as a
square block instead of its specified narrow edge-accent role survived 2
repair rounds unfixed last session — the guidance now gives a mechanical
target instead of a vague description). (4) Added guidance to
`route_batch.md` against gating tab/selector content behind unmounting
JSX conditionals, after confirming a live defect where 3 of 4 project
detail blocks were never mounted in the DOM at all. `uv run pytest`: 992
passed, 1 pre-existing unrelated failure (confirmed present on a clean
tree, same as last pass).

Live-verified with the 2 fresh full-pipeline runs the owner authorized
(`e624bd75`, `c8cd8f1c`, canonical brief pack, real OpenAI calls). Neither
reached `ready` — run 1 hit a new, unrelated motion-beat defect
(`SOURCE_REPAIR_EXHAUSTED` on `motion:home:approach-progress`, logged for
a future pass, not fixed here); run 2 hit `INTEGRATION_REVIEW_UNRESOLVED`
after 5 polish rounds. What is directly confirmed: run 1 (before fix #2)
produced zero export; run 2 (after fix #2) shipped a real `dist/` with
`build_attempt: success` in its `portfolio.json` — the auto-build fix
working end to end on an actual failed run. Neither run reproduced the
resource-role-mismatch or content-unmounting defect classes, though with
one data point each that's supporting evidence, not proof. See `code
generator issues.md` for full evidence and the honest reliability
caveat — general pipeline reliability (reaching `ready` unattended)
remains unproven.

### 2026-09-07 12:10 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [78117e7] - code-generator: implement PLAN.MD Step 1 + 5 generation-time authoring fixes, live-verified as the deepest run yet

Implemented a second externally authored reliability handoff (`PLAN.MD`)
in full for Step 1 (truthful scaffold toolchain) and the generation-side
authoring fixes behind 5 of its 13 confirmed findings, deliberately
deferring the Step 3 component rewrite (RegionLayout/ReadableCopy/
MediaFrame) and Steps 5/7/8/9 (context reduction, candidate-isolation/
export forensics, campaign budget persistence, dev-harness polish) as
larger lifts the owner's own instructions said to deprioritize this pass —
see D-077. Scaffold: `dev`/`preview`/`check` npm scripts added;
`typecheck` now actually checks the app (it ran against the root
`tsconfig.json`'s empty `files: []` before, checking nothing) via both
project configs; `@types/node` fixed a real latent `ROUTES` typing bug the
new typecheck immediately caught; README added. Generation-time fixes:
threaded Content Architect's approved cross-route nav edges into
generation (previously impossible for `data-navigation-target` to ever
appear in output at all); accepted a statically-known `.map()` content
binding the real TS-AST audit already resolved but a stricter Python
pre-gate rejected first; stopped demanding trusted-motion-pattern
implementation details that live entirely in files a section's own source
never contains (unsatisfiable by construction for every correct trusted
beat); clarified distinctive-move ratio direction and peer-selector
requirements; paired every `aspect-ratio` with `min-width: 0`/`max-width:
100%` and anchored responsive breakpoints at the exact configured
768px/1440px verification widths; bumped touch target 36px -> 44px.
`uv run pytest tests/unit/agents/code_generator/`: 260 passed, 1
pre-existing unrelated failure (confirmed present on a clean tree).

Live-verified via one fresh run (`7df7af45-bcf6-41ad-9d63-ce5271df9f0a`)
against the canonical brief pack: reached `generate: succeeded`, DOM/
runtime verification, one bounded repair round, and a full whole-site
quality re-review — the deepest state this engagement has recorded — with
zero navigation/content-binding/motion/touch-target diagnostics anywhere.
Confirmed directly in the real generated source and by building and
viewing it in a browser (see `code generator issues.md` for exact
evidence: `data-navigation-target`, aspect-ratio pairing, 768/1440
breakpoints, 44px control size, a real `<Reveal>` usage). The run still
ended `needs_attention` on one genuine composition finding (an image's
`aspect-ratio: 1/1` read as too prominent for its intended "narrow tactile
edge accent" role) — a correct reviewer judgment, not a bug. Also surfaced
and logged, not fixed this pass: a thematically unrelated hero fallback
image from live resource search, and two Windows-specific operational
notes (an offline-npm-cache warm-up this pass's own new dependency
required once, and a directory-lock footgun from leaving a shell cd'd
into a run's workspace).

### 2026-09-06 21:15 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [446d4c7, 87f97f4, 7578b9a, f7546d4, 6707cce] - code-generator: verify an external plan, then fix 10 real bugs across 5 live-tested runs

Started from a reliability-repair plan authored by another model (no live
calls or repo changes made by it) and verified every claim against actual
code before acting — several matched the still-open frontier in `code
generator issues.md` almost exactly, confirming the static review was
grounded; its proposed `ResolvedExecutionContract` v6 rearchitecture was
deliberately not adopted (unsupported by any DECISIONS.md entry, and this
project's real history is targeted live-bugfix commits, not rewrites).
Fixed and mostly live-verified: a JS regex-literal blind spot in the
shared comment stripper; final repair receiving zero source content for
every DOM/runtime diagnostic plus a wrong-directory fallback guess; a
motion check comparing author-style transforms against browser-computed
matrix strings via plain substring match; a font-weight check that never
triggered a load for an unrendered-but-valid weight; runtime resource
checks blind to acquisition fallback disposition; a self-inflicted
realization-hash staleness regression from that same fix (caught by the
very next live run); a fragment-only CTA href (`href="#section"`) crashing
the entire generated page on render; a region column-count check treating
an undocumented abstract "columns_*" design-grid span as a literal CSS
track-count requirement; a distinctive-move CSS-property check blind to
its own planner-assigned runtime marker; and — the highest-impact find —
the region width/readable-measure checks measuring the CSS border box
instead of the content box, which structurally guaranteed a 1.000 ratio
for any region using the extremely common "full-bleed section, inset via
padding" pattern regardless of design quality, very likely explaining a
large share of this whole engagement's past "layout looks wrong"
findings. Across 5 fresh live runs, the pipeline went from crashing before
verification ever ran to reaching real DOM/runtime layout checks cleanly;
the width-ratio false-positive is confirmed eliminated live. Logged one
finding (runtime checks blind to acquisition disposition) that was
investigated, initially deferred as unsafe to guess at, then fixed
correctly once a reliable acquisition-ledger join was found — and one
genuine architectural tension (the model's own reasonable responsive
breakpoints not aligning with this project's 3 fixed checked viewport
widths) deliberately left open rather than rushed. 272 code_generator
tests pass (up from 255), same 1 pre-existing unrelated failure; full
detail and the remaining frontier in `code generator issues.md`.

### 2026-09-06 17:15 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [5768ce7] - feat(discovery): revamp /app discovery workspace with editorial swiss living draft aesthetic

Revamped the authenticated `/app` Discovery experience into an "Editorial Swiss — The Living Draft" studio workbench matching the approved design concept and `/sign-in` design system. Replaced the marketing hero with an input-first hierarchy (`PORTFOLIO STUDIO / DISCOVERY` / `Bring your work into focus.`), bringing the primary source textarea and Start Discovery CTA comfortably above the fold on all laptop viewports (1440x900, 1366x768, and 1280x720). Upgraded JourneyRail to a real 6-stage drafting rail (`01 Discover` through `06 Preview`) with active cobalt node sweep and locked milestones reflecting true server state. Built a single editorial workbench with live counters, status chips, 2x2 inline progressive disclosure rows, and continuous spatial morphing into `DISCOVERY / ANALYZING SOURCE` and focused single-question cards with collapsible prior answers. Preserved 100% of backend contracts, CAS revision concurrency, and durable job handlers. Verified with Vitest (72/72), Vite production build (177ms), pytest (9/9), ruff, and Playwright screenshot verification across all target viewports.

### 2026-09-06 15:50 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [618a038] - feat(auth): add official logo, fix back-button cta, and elevate living draft motion

Refined Screen 1 (`/sign-in`) based on direct user review and brand assets. Replaced the temporary geometric icon with the official OryxenAI 3-layer isometric rounded hexagon logo (`brand-mark.png`) in the sticky top header and inside the Portfolio Brief hero card. Fixed the browser Back-button CTA stuck state by introducing BFCache/pageshow, focus, and visibilitychange reset handlers in both `auth-controller.mjs` and `sign-in-showcase.mjs`, ensuring "Continue with Google" immediately restores to enabled when returning from Google accounts. Elevated the Living Draft aesthetic by adding a 38px architectural drafting grid on the showcase column, 4 corner registration crosses (`+`), and a 1px traveling cobalt hairline sweep. Tuned carousel auto-advance pacing to 3.8s with smooth spring curves (`cubic-bezier(0.16, 1, 0.3, 1)`). Verified via Playwright real-browser navigation/back-button test, Node test runner (16/16), pytest (5/5), ruff, and mypy across desktop, laptop, and mobile viewports.

### 2026-09-06 15:28 +05:30 - Antigravity (Gemini 3.8 Flash / Google) - [fa9be97] - feat(auth): redesign screen 1 sign-in with editorial swiss studio layout

Redesigned Screen 1 (`/sign-in`) strictly according to the approved "Editorial Swiss — The Living Draft"
visual target while preserving all backend/auth/business logic and leaving all other screens and stages
unmodified. Transformed the old oversized, scroll-first layout into a 44/56 two-column editorial studio
composition. The left column positions the Google OAuth CTA, value proposition, and trust signals comfortably
above the fold across viewports (including short-height 1366x768 and 1280x720 laptops) with compliant Google
branding and identity microcopy. The right column introduces an interactive 6-stage portfolio studio rail with
a living draft traveling cobalt highlight and a 5-card layered editorial showcase carousel featuring subtle
desktop pointer parallax, live status chip cross-fading, auto-advance with pause controls, keyboard navigation,
and complete `prefers-reduced-motion` safety. Verified with Node test runner (16/16), pytest (5/5), mypy,
ruff, and browser captures across desktop, laptop, and mobile viewports.

---

## Compacted history

### 2026-09
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [f208540] - Documented a frontend context/output ledger and copy-controls requirements for future redesign agents; no application source changed.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [ebfbc94] - Added a frontend redesign contract/replacement runbook pack (context, contract ledger, migration/rollback runbook) for future migration agents.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [cdf8952] - Fixed a Content approval 409 on pending-claim routes, bounded a one-click Discovery-to-Content handoff, and added safe copy-ready JSON to review surfaces; records D-075.
- 2026-09-06 - Claude Code (Sonnet 5 / Anthropic) - [1956d58] - Curated kept `output/` artifacts, fixed a `.gitignore` nested-negation bug, corrected stale README claims, and documented `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE`.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [7c94916] - Fixed Discovery's frontend to send correct answer action modes instead of presentation kinds, restoring authenticated answer submission.
- 2026-09-06 - Claude Code (Sonnet 5 / Anthropic) - [83179f3 and 8 prior commits] - Closed 8 more live-tested Code Generator bugs beyond D-072 and added failed-run export (`export_failed_run`); records D-074.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [ae89b61] - Fixed stale shared-execution-lane blocking that stalled Discovery behind old Code Generator leases.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [68f1cd1] - Added safe job lifecycle metadata, foreground scheduling/lease recovery, and deterministic Discovery questions for long pastes; records D-073.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [861e981] - Added foreground scheduling and stale-lease recovery for Discovery, plus durable stop fencing across the API/state/run/worker-result boundaries.
- 2026-09-06 - Codex (GPT-5 / OpenAI) - [cdf7a18] - Added durable cancellation fencing for Content Architect/Visual Design Director, a reusable three-stage job projection, and bounded trace export/copy support.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [963375b] - Recorded R2 storage/credentials readiness while VM-side configuration remained pending.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [caa8f33] - Completed the authenticated three-stage Preact product handoff (Discovery/Content Architect/Visual Design Director) with retry/session fixes.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [7a0c68f] - Recorded a redacted local `.env` audit ahead of production `.env` creation.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [a2a8a60] - Recorded completed Azure VM provisioning, networking, and SSH handoff checkpoint.
- 2026-09-05 - Claude Code (Sonnet 5 / Anthropic) - [d6cde91] - Added bounded live-search fallback for expired pinned Pixabay URLs during Code Generator acquisition and normalized mechanical token/CSS length mistakes; records D-072.
- 2026-09-05 - Claude Code (Sonnet 5 / Anthropic) - [34c638b] - Fixed a silent `--color-accent` token collision between raw colors and shadcn theme slots, enriched content-key/distinctive-move repair diagnostics; records D-071.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [8a2066a] - Added provider-neutral `BudgetedModelClient` to reserve prompt/completion charges before transmission and stop at a session cost cap; records D-070.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [5b86779] - Added session-scoped PostgreSQL caching for validated structured model results across Discovery/Content Architect/Visual Design Director/Build Preparation; records D-069.
- 2026-09-05 - Claude Code (Sonnet 5 / Anthropic) - [aedf96c] - Closed repair control-flow gaps, added review prompt prefix-caching, introduced the deterministic motion pattern catalogue; records D-068.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [0ce8ecd] - Added canonical first-deployment path (Azure Linux VM, Docker Compose, Supabase auth, Cloudflare R2, Caddy HTTPS) with a production-overlay runbook.
- 2026-09-05 - Codex (GPT-5 / OpenAI) - [903477a, e1173df] - Established Azure VM provisioning checkpoints and portal session recovery handoffs.
- 2026-09-05 - Antigravity (Gemini 3.8 Flash / Google) - [9fabd58] - Consolidated all agent outputs under single canonical `output/` directory, purging obsolete prebuild artifacts.
- 2026-09-04 - Claude Code (Sonnet 5 / Anthropic) - [112d1a6] - Added commit-cadence policy to the multi-agent protocol.
- 2026-09-04 - Claude Code / Codex - [6ab319a, 5d8a93b, 6cec47b, 5b84673, 871f960] - Synced docs and hardened Code Generator after the Build Preparation brief-contract migration.
- 2026-09-04 - Codex (GPT-5 / OpenAI) - [1f0ed68] - Migrated Code Generator to consume Build Preparation Markdown brief contracts directly.
- 2026-09-04 - Codex (GPT-5 / OpenAI) - [389fa28] - Shipped authenticated three-agent editorial studio.
- 2026-09-04 - Antigravity (Gemini 3.8 Flash / Google) - [1627f5d] - Fixed Build Preparation brief/image-retrieval defects and optimized model prompt packet size.
- 2026-09-04 - Antigravity (Gemini 2.5 Pro / Google) - [a8ad4e7] - Rebuilt Build Preparation into 1-model-call zero-byte-download pipeline producing two Markdown briefs directly on session state (D-062), superseding prior pack-era decisions.
- 2026-09-03 - Antigravity (Gemini 2.5 Pro / Google) - [28b8b1c, 2cc2cb9, e78e70b] - Redesigned studio into zero-scroll dark architectural atelier with live telemetry and progress monitors.
- 2026-09-02 - Antigravity (Gemini 2.5 Pro / Google) - [9b5ea36, f9e8eef, 47a57b0] - Delivered Preact frontend foundation (Phases 2, 3, 5): app shell, conversation surface, preview handshake, and honest milestone adapters.
- 2026-09-02 - Codex / Claude Code - [280982e, e8c6b55, 1cf313f, 234a05d, 20f72e2] - Hardened Code Generator V4 admission, design tokens, shadcn Tailwind v4 bridge, and bounded repair.

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

## Summary (as of last compaction — 2026-09-08)

- Recent detailed entries retained: 22 (due for compaction to 15-20 on the next major entry)
- Compacted milestone bullets: 31
- Last updated: 2026-09-09 00:35 +05:30 — Claude Code (Sonnet 5 / Anthropic)
