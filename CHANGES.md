# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

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

### 2026-09-06 14:06 +05:30 - Codex (GPT-5 / OpenAI) - [f208540] - docs(frontend): capture full agent behavior and output context

Expanded the frontend redesign handoff with a state-complete context rule and
an explicit ledger of Discovery question generation, internal agent operation
counts, Content Architect batching, Visual Design Director output fields, and
current final-result presentation. Added incremental requirements for a
temporary issue-tracing popup, a complete structured Visual Design Director
reader, and right-sidebar copying of each stage's full agent-owned JSON without
changing the working auth, adapter, polling, or handoff architecture.
No application source changed; the existing frontend verification remains the
baseline for this documentation-only update.

### 2026-09-06 13:50 +05:30 - Codex (GPT-5 / OpenAI) - [ebfbc94] - docs(frontend): add redesign contract and replacement runbook

Created an attachable frontend migration pack for future AI coding agents:
the redesign context pack defines the replaceable visual boundary and protected
runtime seams, the contract ledger maps routes/auth/stages/statuses/actions and
proof obligations, and the replacement runbook defines the repository search,
screen-by-screen migration, dual-run cutover, rollback, and verification gates.
Linked the pack from `docs/Frontend/README.md`; no application source or backend
behavior changed. Verification: frontend typecheck, Vitest, production Vite
build, and browser/auth module tests all pass.

### 2026-09-06 13:15 +05:30 - Codex (GPT-5 / OpenAI) - [cdf8952] - pipeline: guarantee approval-ready Content and one-click handoff

Traced the live Content approval 409 to an approved home route referencing a
certification claim still marked `pending`. Content Architect now runs the same
deterministic public-scope check before presenting review output and spends at
most one remaining call from its existing three-call ceiling on a targeted
integration correction; unresolved output fails before review and claim status
is never promoted merely to pass. Existing invalid saved drafts route one
approval click into a bounded revision, after which changed copy still requires
review. Discovery approval and explicit Content start are now one frontend user
action, while remaining two idempotent backend calls rather than background
auto-chaining. Added safe copy-ready final JSON projections to Discovery,
Content, and Design review surfaces (excluding intake/auth/job data), retained
Build Preparation's existing diagnostic JSON control, and corrected skipped
answer rendering. Verification: 143 Content unit/API tests, 71 frontend tests,
full Python mypy, focused Ruff, frontend typecheck, and production Vite build.
Records D-075.

### 2026-09-06 03:12 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [1956d58] - output/, .gitignore, README.md, .env.example, docs/run/run.md - device handoff: curate kept output, fix stale docs, document port override

Final task of this engagement: prepared the branch for a fresh device to
continue Code Generator work. Deleted all `output/build-preparation/` packs
and `output/code-gen-output/` runs except the one pack and two runs
referenced in `code generator issues.md`'s 2026-09-06 handoff, and fixed
`.gitignore`'s nested-negation ancestor chain so those specific kept paths
are actually tracked (a bare `output/*` rule silently blocks re-inclusion of
anything under an already-excluded directory without an explicit
`!dir/` + `dir/*` + `!dir/child/` chain). Corrected README.md's badly stale
top banner and non-goals list (it still said Code Generator and Phases 3-4
auth were "out of scope" — both have been implemented for weeks; see
AGENTS.md), added Node/npm and browser prerequisites, and added a prominent
pointer to `code generator issues.md` for whoever picks up the reliability
work next. Documented the existing (but under-documented)
`DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` settings in `.env.example`, README.md,
and `docs/run/run.md` as the supported fix for native PostgreSQL's port
`5432` colliding with another local install — the exact conflict hit
repeatedly this session — rather than inventing a new override mechanism.
No source code changed; all 261 code_generator tests and full lint/type
checks were already green from the prior commit and are unaffected.

### 2026-09-06 02:35 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [83179f3 and 8 prior commits] - live-testing iteration closes 8 more real gaps; failed runs now export

Continued live-testing (per the user's "keep going until fixed" instruction)
found and fixed 8 more real, distinct Code Generator bugs beyond D-072's
five: non-required resources wrongly treated as blocking; a distinctive-move
CSS selector check with zero tolerance for a legitimate ancestor-scoping
prefix; the planner's collision retry widened from 2 to 3 bounded attempts;
a duplicate-file-path response now canonicalizes (keeps the last entry)
instead of rejecting; `repair_source.md` given the same section-file
import-depth guidance `route_batch.md` already had; `Reveal`/`StaggerGroup`
now forward marker attributes onto their own wrapper; a host-side easing
normalizer plus a corrected `planner.md` prompt (its own prose read too
close to a literal CSS value); and identical runtime diagnostics across
viewports now dedupe by fingerprint before repair sees them. Two
consecutive fresh live runs reached `generate: succeeded` -> final
verification -- the deepest and most consistent this engagement has gone --
and one produced this project's first real screenshots of a generated
portfolio (genuinely good-looking; see D-074). Separately, added
`export_failed_run()` so `output/code-gen-output/` preserves a run's
source/build/screenshots even when it ends in `needs_attention`/`failed`,
per explicit user request; wired into the plan/acquire/generate and
verification failure choke-points. 261 code_generator tests pass (up from
232 at D-068); full evidence trail in D-074 and `code generator issues.md`.

### 2026-09-06 02:13 +05:30 - Codex (GPT-5 / OpenAI) - [7c94916] - discovery: restore authenticated answer submission

Corrected the product frontend to send Discovery's API action modes
(`answered`/`skipped`) instead of question presentation kinds, which had
caused every option click to fail validation. Added a typed answer boundary,
consistent skip support, and regressions for all answer shapes. Unknown
non-auth API failures now preserve their safe server message instead of being
misreported as an expired authentication session; real HTTP 401 handling is
unchanged.

### 2026-09-06 01:51 +05:30 - Codex (GPT-5 / OpenAI) - [ae89b61] - worker: release stale shared-lane blockers

Allowed-handler workers now release an expired foreign job only when it
blocks a shared execution lane needed by due work they can run. This fixes
repeat Discovery stalls behind stale Code Generator leases and adds the
restricted-worker regression missing from D-073.

### 2026-09-06 01:19 +05:30 - Codex (GPT-5 / OpenAI) - [68f1cd1] - pipeline: make stalled agent runs observable and recoverable

Added safe job lifecycle metadata, foreground scheduling and lease recovery,
local metadata-only test traces, and deterministic Discovery questions for
substantive long pastes. Identical completed starts now return the stored
result without duplicate job/model work; records D-073.

### 2026-09-06 01:08 +05:30 - Codex (GPT-5 / OpenAI) - [861e981] - discovery: recover stalled jobs and support stop

Added foreground scheduling and stale-lease recovery so Discovery requests
cannot remain behind an abandoned model-generation job, plus durable stop
fencing at the Discovery API, state, run, and worker-result boundaries.

---

## Compacted history

### 2026-09
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

## Summary (as of last compaction — 2026-09-07)

- Recent detailed entries retained: 15
- Compacted milestone bullets: 22
- Last updated: 2026-09-07 14:48 +05:30 — Claude Code (Sonnet 5 / Anthropic)
