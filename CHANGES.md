# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-14 12:24 +05:30 — Codex (GPT-5) — [250417d] — Add art-directed motion to public portfolio previews

Upgraded the three public sample portfolios with distinct interaction systems:
Devon's telemetry grid and console scan, Leila's animated market signals and
offset proof layout, and Noa's layered paper/poster collage. Added subtle
grain, pointer-responsive lighting, scroll-aware section state, staggered
screen reveals, responsive overflow protection, and reduced-motion fallbacks.
The preview controller now returns every newly opened sample to Home before
showing it.

### 2026-09-14 12:14 +05:30 — Codex (GPT-5) — [e7296f8] — Separate destructive admin reset from creator shell

Removed the destructive pipeline-reset control, modal, and styling from the
creator workspace. Administrator access remains available through the
authenticated `/admin` surface and the admin account entry point.

### 2026-09-14 12:08 +05:30 — Codex (GPT-5) — [5e96a52] — Turn public examples into scrollable portfolio previews

Expanded the three public sign-in examples into self-contained, fictional
mini-portfolios: Devon Lee (software developer), Leila Ortiz (business
developer), and Noa Park (creative director). Each preview now has a distinct
palette, visual motif, four scrollable screens, sticky section navigation,
hero-to-work jump links, hover/motion treatments, responsive layout, and
reduced-motion support. Added route/content assertions to the public-shell API
test and kept the preview entirely local and unauthenticated.

### 2026-09-14 11:59 +05:30 — Codex (GPT-5) — [efb226e] — Keep intake actions and responsive shell accessible

Reserved the Discovery intake action area in normal document flow, raised
the UI guidance counter to 3,000 words while retaining the 30,000-character
guard, added the committed-approval acknowledgement, and tightened mobile
journey/inspector layering. The browser fixture now loads the same shared
tokens as the product shell.

### 2026-09-14 11:54 +05:30 — Claude Sonnet 5 — [c6eaa33] — Namespace generation retries and receipts by explicit attempt epoch

Committed reliability work that had been sitting reviewed-and-passed but
uncommitted since 2026-09-11. Added a shared `semantic_decline.py`
boundary so generation, final repair, and integration polish interpret a
model's honest `cannot_complete` response identically. Namespaced
`GenerationCallReceipt` identity by `attempt_epoch` so redelivery within
one epoch stays one logical attempt while an explicit retry starts
separate call history. Deduplicated resource requests and dependency
receipts by content key instead of naive list concatenation, so
redelivery no longer re-appends receipts a prior attempt already
recorded. `_reset_generation_projection_for_explicit_retry` now resets
every work unit's transient state and bumps `attempt_epoch`, fixing
checkpointed owners retaining rejected integration-polish source across
an explicit retry. Reviewed across three rounds ending PASS
(`semantic-review/2026-09-11-110557-pr-2.md`).

### 2026-09-14 11:54 +05:30 — Claude Sonnet 5 — [a0cae30] — Make native verification acceptance preview-first (D-094)

Committed D-094's implementation, also reviewed and already used in a
real live campaign on 2026-09-11 but never previously committed.
Downgrades several previously-blocking checks (missing quality receipt,
source-contract diagnostics, build diagnostics once a runnable build
exists, post-startup runtime-verifier exceptions) to advisories under a
new `code_generator_verification.preview_first_acceptance` flag (native
profile only). Rebuilds resource/dependency ledgers and a new
`generated/resource-assets.json` from the durable run before
verification so re-admission of the immutable brief doesn't lose mutable
acquisition overlays. Also fixed a real gap found while committing this:
`generation_orchestrator.py::_review_and_polish`'s preview-first return
caught a bare `Exception` around `_integration_review` (which
re-validates worker authorization) with no `AuthorizationFenceError`
carve-out — a fenced-off run's rejection would have been silently
swallowed. Added the missing re-raise and two regression tests, since
`preview_first_acceptance` had zero test coverage before this commit.

### 2026-09-14 11:54 +05:30 — Claude Sonnet 5 — [49d6e0d] — Fail-closed brief ingestion dispatch for post-67d5a75 wire shape

Committed brief-ingestion compatibility work that had been sitting
reviewed-and-approved but uncommitted since 2026-09-11.
`brief_ingestion.py::_prepare_brief_indexes` now distinguishes current
raw, current namespaced, legacy-declared namespaced, and unversioned
compatibility Build Preparation inputs before applying format-specific
validation and projection behavior, so old namespaced-plural inputs keep
their historical topology while current formats get per-route owner
expansion with synthesized-ID-collision rejection. Adds a privacy-safe
post-67d5a75 regression fixture
(`tests/fixtures/code_generator_build_preparation_post_67d5a75_v1/`).
Reviewed across three rounds ending APPROVED
(`semantic-review/2026-09-11-123024-pr-3.md`).

### 2026-09-14 11:40 +05:30 — Codex (GPT-5) — [7e503f0] — Public portfolio examples before sign-in

Added a public, fictional three-example showcase to the sign-in landing page.
Each example opens a local native-dialog portfolio preview without authentication,
with an explicit path back to creating a portfolio. Added responsive styling,
keyboard dismissal/focus restoration, and API coverage for the public markup.

### 2026-09-14 11:15 +05:30 — Antigravity (Gemini 3.8) — [e53ebfb] — Administrator control plane matching reference specifications 12 and 18–24

Implemented the role-gated administrator control plane at `/admin` matching `17-admin-screen-reference-spec.md` and 8 visual references (`12-admin-control-center.png` and `18-admin-users-ledger.png` through `24-admin-action-confirmation.png`):
- Pinned topbar with live session indicator, workspace link, refresh, sign-out, and monogram administrator badge.
- Editorial header with live announcement region and safe account details card.
- Six-tab navigation strip (`Users`, `Projects`, `Legacy`, `Deleted`, `Operations`, `Audit`) with active indicators.
- Four summary metric cards (`Active users`, `Projects`, `Running jobs`, `Pending operations`) populated via `GET /api/v1/admin/summary`.
- High-fidelity ledgers with status pills (`● Active`, `● Running`, `● Paused`, `● Complete`, `● Failed`), role badges, safe date formatting, and legal action clusters.
- Prominent Deletion Boundary warning banner for deleted identity tombstones with authorized readmission gating.
- Operations ledger exposing `Resume safely` strictly when `resumable: true`.
- Strictly read-only Audit Trail ledger with zero mutation affordances.
- Accessible typed confirmation modal (`<dialog>`) with backdrop blur, dynamic action badge/title, exact target verification, optional reason field, and idempotency key safety.
- Passes all 20 auth frontend unit tests and all 76 backend auth unit and API tests.

### 2026-09-14 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [e37e302] - Deployment setup preflight improvements

Made the deployment wizard derive active model credentials from
`config/models.toml`, require those keys during setup/doctor, reject example
hostnames, and recover a stopped Docker daemon through the official install
path. Documented the database-migration limitation of application rollback.

### 2026-09-14 00:00 +05:30 - Codex (GPT-5 / OpenAI) - [88ba402] - Simple Azure VM deployment path

Implemented the beginner-friendly Azure deployment contract: one guided
`azure-deploy.sh` command installs Docker, renders VM-local production config,
builds exact-commit images, runs migrations, starts health-checked services,
backs up and rolls back releases, and operates Compose-managed Caddy. Updated
Compose port binding/logging/healthchecks, production configuration,
deployment runbooks, AI-assisted operations guidance, and CI validation.

### 2026-09-13 21:40 +05:30 — Antigravity (Gemini 3.8) — [cdac290] — Discovery question experience redesign and local review refactor

Refactored the Discovery interview questioning surface for full parity with design references (`16-discovery-mcq-question.png` and `17-discovery-text-question.png`) and research guidance in `12-discovery-question-experience-research.md`:
- Replaced unstyled inline controls with full-width interactive selectable cards (`.choice-tile`) for multi-select, single-select, and boolean modes, featuring hover lift, custom indicator icons, and active cobalt selection highlighting (`#f0f5ff` fill with `#1a56db` border).
- Enforced local selection review for single-select and boolean questions (§2.2): choices update local state and selected styling without triggering immediate network requests; submission requires explicit user activation of `Next question` / `Submit answer`.
- Implemented editorial layout hierarchy with clean `DISCOVERY` eyebrow, question progress counter, Newsreader serif prompt headline, subtle graphite help reason, and uppercase group cues (`SELECT ALL THAT APPLY`, `SELECT ONE`, `YOUR ANSWER`).
- Refactored the free-text answer experience into a spacious, rounded composer with focus styling, contextual placeholder, and a real-time `✓ Draft saved` indicator persisted to `safeSessionStorage`.
- Unified the reserved action dock with high-contrast cobalt `Next question` primary action, in-flight `Saving answer…` state, quiet `Skip question` secondary action, and non-destructive inline error recovery.
- Scoped live-region accessibility: removed broad `aria-live` from the outer card and introduced a dedicated transition announcer to eliminate repetitive screen-reader announcements during typing or polling.
- Added browser-test fixtures (`discovery-question-mcq`, `discovery-question-text`, `discovery-question-single`), verified live browser rendering at 1536×695 (zero overflow), and added unit test suite (`ConversationSurface.test.ts`). Passes all 20 frontend Vitest test suites (119 tests) and 158 backend Discovery unit tests.

### 2026-09-13 20:50 +05:30 — Antigravity (Gemini 3.8) — [f003023] — Code Generator split control room, preview theater, and traceability drawer

Implemented full editorial and functional parity with the Code Generator visual specifications (`13-code-generator-preview-workspace.png`, `14-code-generator-preview-working.png`, and `15-code-generator-preview-attention.png`):
- Split control room layout with 420px activity and composer column on the left and full-width live preview theater on the right.
- Vertical 5-milestone stepper (`Plan`, `Acquire`, `Build`, `Verify`, `Preview`) supporting `Available`, `Working` (with active progress bar and pulse indicator), `Attention` (with red exclamation badge and stopped milestone status), and `Complete` states.
- Dedicated desktop-only preview viewport controls per explicit directive, omitting mobile toggle while preserving desktop fit/scale toggles and secure preview framing with status badges (`🛡️ Previous verified preview`, `⚠️ Candidate preview (unverified)`).
- Preserved-preview Attention Card matching Image 15 with 3 status pillars (*Preview preserved*, *Polling stopped*, *Retry available*), one-click retry, and details trigger.
- Traceability Pop-Up Drawer: Right-side slide-over drawer exposing session ID, trace ID, active job ID, failed coordinator stage, error codes, specific issue breakdowns, collapsible raw technical JSON, and a prominent one-click "📋 Copy diagnostic report" action formatting a comprehensive Markdown triage bundle for instant developer debugging and traceability.
- Passes all 20 frontend Vitest test suites (119 tests), Vite production build, and all 410 Code Generator / API backend unit tests.

### 2026-09-13 20:05 +05:30 — Codex (GPT-5) — [ff5acf7] — Code Generator preview theater research and references

Added competitor-informed preview workspace research and three new 16:10
implementation-reference images for the Code Generator: split activity and
composer workspace, bounded live preview while working, and preserved-preview
attention recovery. Existing reference images were left unchanged.

### 2026-09-13 19:56 +05:30 — Codex (GPT-5) — [15450bf] — Discovery question research handoff, evidence copies, and visual references

Added the self-contained Discovery question research pack with forensic findings, official accessibility/form guidance, MCQ/free-text contracts, evidence mapping, implementation routing, two byte-for-byte screenshot copies, and two new UI references. Existing Code Generator visual files were preserved unchanged.

### 2026-09-13 18:20 +05:30 - Codex (GPT-5) - [0e2b303] - stylesheet fallback for completed auth restore

Added a cache-safe product-shell stylesheet that hides the temporary auth
progress banner when the pending state clears or the Preact workspace mounts,
covering partial/stale bootstrap paths that can otherwise leave the banner
above a fully loaded stage.

### 2026-09-13 18:14 +05:30 - Codex (GPT-5) - [f74d145] - hide completed auth bootstrap banner

Fixed the successful `/app` restore path so the temporary “Restoring your
workspace” progress banner is hidden once the authenticated workspace is
ready, while retaining the existing accessible recovery behavior.

### 2026-09-13 18:09 +05:30 - Codex (GPT-5) - [fd127de] - auth bootstrap timeout and recovery state

Bound browser session restoration so a stalled Supabase/session/API check
cannot leave `/app` on the initial "Restoring your workspace" progress copy
forever. Auth runtime-load failures and unexpected bootstrap rejections now
reveal a safe recovery message while preserving the existing session; added a
regression test for a never-resolving session restore.

### 2026-09-13 17:55 +05:30 — Antigravity (Gemini 3.8) — [aeb0fef] — frontend visual overhaul: full editorial parity with visual design references

Overhauled the studio shell and stage components to match 100% of the 12 reference mockups (`docs/Fix Frontend/visuals/`). Removed conflicting 240px left activity rail, nested grids, and cramped columns in favor of a centered Swiss-editorial canvas (`#FBF9F5` warm paper, `#171A19` deep ink, `#1A56DB` cobalt accent, Newsreader serif headings). Centered the horizontal 5-stage stepper (`StageNavigator`) in the topbar, added in-flow `StageContextStrip`, implemented sticky glassmorphic `ActionDock` with step guidance and primary/secondary actions, and created slide-over `OutputInspector`. Fully modernized Discovery intake (`02`) with 3 starter prompt cards and live word counter, Discovery review (`03`) with 3-column key details and inline revision composer, Content review (`04`) with route tabs and section cards, Design storyboard (`05`) with 4 intent cards and SVG scene banners, Build Preparation (`06`) with 4 KPI cards and geometric evidence tiles, and Generation (`07`-`09`) with handoff summary, 5-phase pipeline, 5 semantic milestones, and preserved preview. Passes all 19 frontend Vitest test suites (114 tests) and TypeScript type checks with 0 errors.

### 2026-09-13 15:20 +05:30 - Codex (GPT-5) - [bfea878] - frontend remediation: centered stage shell, safe handoffs, and responsive review states

Implemented the Fix Frontend handoff in the existing Preact/TypeScript/Vite
product shell. Added the centered five-stage journey/canvas composition with
compact tablet/mobile stage selection, labeled intake/answer/revision
composers, committed-approval then explicit destination-specific next-stage
starts, server-driven job/retry projection, safe async attention states,
metadata-only Build Preparation resource evidence, and a developer-only
closed-by-default Output Inspector. Removed the creator topbar reset while
retaining the admin account action and `/admin` access. Added Playwright
viewport fixtures using the existing dependency; visual reference files were
not changed.

### 2026-09-12 18:45 +05:30 — Codex (configured runtime) — [df96f4d] — frontend remediation handoff detail and admin reference

Extended `docs/Fix Frontend/` with explicit input/composer and destination-specific next-agent controls, partial-approval recovery guidance, administrator console specification, screen-to-source implementation map, admin evidence routing, responsive/admin acceptance checks, deferred enhancement notes, and the new `visuals/12-admin-control-center.png` reference. The original eleven visuals remain unchanged; no application source or unrelated worktree changes were modified.

### 2026-09-12 18:24 +05:30 — Codex (configured runtime) — [7aa452b] — frontend remediation research pack, evidence map, screen references

Created `docs/Fix Frontend/` as a self-contained implementation handoff for the audited frontend remediation: root-cause analysis, FE-001–FE-020 evidence mapping, runtime/API contract diagnosis, screen and component specifications, responsive/accessibility rules, acceptance matrix, implementation runbook, and eleven generated UI reference images. No application code, authentication boundary, CSP, or unrelated worktree changes were modified.

## Compacted history

### 2026-09
- 2026-09-11 — [pending commit] — Kiro: full frontend visual/UX revamp (D-095) — unified stage handoffs, curated per-stage views, theater-mode Generate & Preview, design-token/motion foundation, auth-page parity. Still uncommitted as of 2026-09-14.
- 2026-09-11 — [now committed as a0cae30 on 2026-09-14] — Kiro: made native Code Generator acceptance preview-first (D-094); closed the live campaign at 2/4 with a browser-verified `ready` preview.
- 2026-09-11 — [c8c9333] — Fixed Visual Design Director's recurring MODEL_OUTPUT_INVALID by inlining the missing content_ref rule for single-route pages.
- 2026-09-11 — [67d5a75] — Restored rich first-four-stage output and bounded Gemini recovery across Discovery/Content Architect/Visual Design Director/Build Preparation (D-093).
- 2026-09-11 — [no commit; investigation only] — Disproved a suspected `_route_source_map` double-hash bug; the real gap was a model-output completeness defect (D-090 follow-up).
- 2026-09-10 — [01e9ed0] — Named the exact empty field in `QualityFindingV2` validation errors for the bounded schema-correction retry.
- 2026-09-10 — [882574e, 1563282] — Raised the default image floor to `minimum_visible_images=2`/`require_primary_route_image=true` (D-092).
- 2026-09-10 — [11a8fe3] — Closed campaign B at slot 5 with a browser-verified `ready` result.
- 2026-09-10 — [06eb2c0] — Fixed the selected-work lifecycle normalizer to resolve real per-run color tokens instead of hardcoded names.
- 2026-09-10 — [e7d9284] — Recognized trusted catalogue motion patterns in the final V4 source audit.
- 2026-09-10 — [6c22712] — Repaired a verification regression test's route-path mismatch left incomplete across a multi-agent handoff (D-090).
- 2026-09-10 — [fd9669d] — Surfaced the real issue code in terminal-failure/export evidence instead of the generic `needs_attention` status (D-091).
- 2026-09-10 — [d9caf30] — Added an idempotent host-side materializer for the selected-work lifecycle cue.
- 2026-09-10 — [22db99c] — Normalized route motion contracts (CSS lengths, trusted selectors, custom-motion fallback, observer wiring) after live Pack A drift.
- 2026-09-10 — [68e1693] — Reconciled Code Generator repair-budget defaults with `config/app.toml` and documented D-089's retained unused field.
- 2026-09-10 — [39076d0] — Refreshed stale image pins by stable asset ID and hardened dist exports against partial/retry failures on Windows.
- 2026-09-10 — [7a01ee9, 3f07609, f1e74d3, 40434cf, ed21a6a, c3fabdc, 5eca499] — Closed desktop generation reliability gaps (preview/export, source/interaction ownership, contract ordering, static content-map, conditional-motion audit) from the five-run campaign.
- 2026-09-10 — [90e8349] — Fixed fluid type-step token double-prefixing (`--type-type-heading-*` -> `--type-heading-*`) at the schema/compiler boundary.
- 2026-09-09 — [9716681] — Caught inert disclosure panels (aria-hidden empty content) as a host-owned source diagnostic; aligned `columns_*` review guidance with D-076.
- 2026-09-09 — [4da1ddb] — Made toolchain preflight cleanup best-effort so a Windows enumeration denial can't discard a valid toolchain proof.
- 2026-09-09 — [14bb97c, c8a66e7, 80a925c] — Replaced keyword-based severity inference with explicit host-owned quality findings; Pack C stopped honestly at `INTEGRATION_REVIEW_UNRESOLVED`.
- 2026-09-09 — [a503a4a] — Implemented the Code Generator reliability plan: pending-proposal completion, serial attempt accounting, hashed image obligations, marker-bound layout recipes, toolchain preflight, truthful atomic exports (D-0XX, R01-R12 in `code generator issues.md`).
- 2026-09-09 — [66d8287] — Authored a 6-document frontend/agent integration reference suite under `docs/frontend/` for the major frontend revamp.
- 2026-09-09 — [59409b5] — Fixed `run-worker.ps1` to use a writable repo-local `uv` cache instead of a lockable global one.
- 2026-09-09 — [2f424e5] — Hardened brief-driven Code Generator: brief-mirror admission, planner retry/canonicalization, npm import scanning, host-owned quality findings, unverified-preview candidates, npm cache warmer, Azure VM Docker wiring.
- 2026-09-09 — [78a9c77] — Retired the temporary static Discovery/pipeline shell; `/app` now requires the manifest-selected Preact bundle.
- 2026-09-09 — [bc7b5a6] — Added an administrator-only pipeline reset capability (full session reset back to Discovery, admin-audited).
- 2026-09-09 — [f20779f] — Clarified planner guidance distinguishing a brief's design-language words from literal `colors[*].name` tokens after a live naming collision.
- 2026-09-09 — [051afa6] — Added undeclared-npm-import detection via source scan for pinned/deferred components, closing the empty-`dependency_metadata` gap.
- 2026-09-08 — [a2ae087] — Checked in Azure production Compose/Caddy/TOML deployment overlays matching the VM runbook.
- 2026-09-08 — [2790e9d] — Released the authenticated Generate & Preview stage with the promoted-preview iframe bridge and Build Preparation gate (D-081); detailed history remains in Git.
- 2026-09-09 — [e99ed55] — Investigated five failed Code Generator runs and authored the implementation and five-slot campaign handoff for pending retention, accounting, visual quality, truthful exports, and preflight.
- 2026-09-09 — [29fc598] — Reconciled stale `create`/`replace` repair tags against the owned candidate tree while preserving strict initial-generation semantics and bounded repair authority.
- 2026-09-08 — [44304ff] — Added honest repair-decline handling, shared-cause runtime correlation, stable prompt-cache keys, tighter observed repair ceilings, and a dedicated Code Generator job-attempt policy.
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

## Summary (as of last compaction — 2026-09-14)

- Recent detailed entries retained: 18
- Compacted milestone bullets: 38
