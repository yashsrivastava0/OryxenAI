# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-19 16:15 +05:30 — Codex (GPT-5) — [188af32] — Align mapped content validation with generated source

The route-batch pre-toolchain gate now recognizes bounded indexed tuple maps
such as `entries.map((item) => contentValue(item[0]))`, matching the existing
runtime/source audit instead of spending repair budget on a false missing-key
diagnostic. The v4 repair contract also allows unchanged pending candidate
bodies to be retained while the model returns only complete bodies it actually
changes; related architectural rule: D-101.

### 2026-09-19 00:00 +05:30 — Codex (GPT-5) — [e713ff2] — Enforce Code Generator handoff, worker, and preview contracts

Code Generator admission now re-composes the approved Content Architect and
Visual Design Director handoff before queuing work, and both production and
standalone starts require a fresh worker heartbeat with the matching pipeline
release plus Node/npm/browser capability. Preview promotion now separates the
browser-facing URL from the worker-verifier URL for Docker, while the product
frontend completes the generated preview postMessage handshake and surfaces a
timeout instead of silently showing a blank iframe. Added focused regression
coverage and configuration overlays for the split preview origins.

### 2026-09-19 00:00 +05:30 — Codex (GPT-5) — [a1f7fde] — Prove generated dependency locks with the verification install

The Code Generator dependency stage now runs the exact configured clean
verification install against its staged package manifest and lockfile before
publishing `node_modules` and the lock. This closes the acquisition/verification
contract gap that allowed npm optional-platform lock entries to fail only after
generation. Added focused tests for the command contract and atomic admission.

### 2026-09-19 00:00 +05:30 — Codex (GPT-5) — [2976b91] — Consolidate deployment documentation

Grouped the eight deployment documents into two canonical combined guides,
preserved every source body, retained numbered compatibility stubs, and added
canonical README navigation. Verified source parity and local Markdown links;
no runtime behavior changed.

### 2026-09-19 00:00 +05:30 — Codex — [87d60a7] — Corrected Code Generator audit confidence

Rechecked the Code Generator issue reports against the route-generation
context, stale-source validator, preview bridge, and configuration overlays.
Corrected the report to preserve approved-content context as evidence, mark
the route-context failure as requiring reproduction, qualify Docker preview
behavior by effective overlay, and downgrade the Windows process-contention
finding until its cause is isolated.

### 2026-09-19 00:00 +05:30 — Codex — [392277c] — Code Generator architecture and preview issue audit

Added `codegen issues.md` and `codegen issues evidence.md`, documenting the
highest-impact Build Preparation handoff, worker/toolchain, npm, generation,
preview-promotion, browser-delivery, Windows-runtime, and configuration-gate
failures found in the current Code Generator implementation. No implementation
fixes were made; the pre-existing dirty worktree was preserved.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [f0b8d7a] — T09 live campaign attempt 1: environment fixes and a real content-generation finding

Ran the first attempt of the docs/code-generator-repair-plan-2026-09-16.md
T09 live campaign (user-authorized, real model spend) against pack
`604405bb`. Diagnosed and fixed local environment blockers unrelated to the
repair plan itself: stale multi-day-old dev processes occupying port 8000,
`Start-Process`-spawned background windows resolving `node`/`npm` from a
different environment than an interactive shell (making toolchain-preflight
falsely report `node: false`), and a genuine `dependency_manager.py` lockfile
defect where `npm install --package-lock-only --offline` can produce a
lockfile with blank `version` fields for `@tailwindcss/oxide`'s nested
optional multi-platform dependencies, which a later strict `npm ci --offline`
then rejects. Traced a subsequent `SOURCE_REPAIR_EXHAUSTED` failure to a
real, evidenced content-generation finding: the model declined to write an
array-heavy content section (multiple experience entries) citing "no
materialized runtime approved content values," even though the intentional
`contentValue(id)` type-excerpt pattern (documented in `route_batch.md`)
supplies every valid literal ID for exactly this purpose. Full narrative,
evidence, and follow-ups in
`docs/code-generator-repair-plan-campaign-2026-09-18.md`. Reverted the
temporary `allow_network_install=true` diagnostic override and stopped the
native stack cleanly. 1 of 5 campaign attempts consumed; attempts 2-5 remain.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [c3cfe3a] — Fix test_service.py module collision blocking a full-suite run

Running the whole `tests/unit` tree in one `pytest` invocation (as the
repair plan's verification commands require) failed at collection:
five different agent test directories each have their own
`test_service.py`, but `tests/unit/agents/code_generator/` and
`tests/unit/auth/` were missing the `__init__.py` that the sibling
agent test directories already have. Added the same empty
`__init__.py` to both, matching the existing convention. Also
confirmed (not fixed, unrelated) that 10 other failures — 5
`test_settings*.py`, 5 `build_preparation` component-retrieval tests —
are a pre-existing config-overlay/test-invocation mismatch, not a
regression: both pass cleanly with `OryxenAI_CONFIG_OVERLAY` unset.
Full `tests/unit` now collects and runs (1176 passed).

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [no code change] — Verified T08 portable exports against a real build (docs/code-generator-repair-plan-2026-09-16.md)

Verified T08's export contract directly against a real, test-generated
export (`output/code-gen-output/15-10-18-09-2026-a6fea704`, a synthetic
fixture build with no real user data): copied `source/` to a fresh
temp directory with no `node_modules`, ran `npm ci` from the committed
`package-lock.json`, `npm run check` (source audit + typecheck), and
`npm run build` — all succeeded independently with zero references
back into this repository. Served the built `dist/` with
`scripts/preview-codegen-export.py`: root URL, a static asset, and a
nested SPA route all returned 200 with real content; a missing asset
correctly returned a real 404 body instead of the SPA HTML fallback.
Confirmed no local absolute paths or credentials in the exported
source or `portfolio.json` (one grep hit was a false positive — a
`../routes/home/index` import path, not a leaked filesystem path).
Confirmed `ResourceUrl.ts` resolves all asset/route URLs from
`document`/`window.location` only, with no application API or database
dependency. Found no gap requiring a code change; the existing
`portfolio_export.py`/scaffold README/package.json contract already
satisfies the plan's Definition of Done for this item.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [a64003a] — Fetch Code Generator state only when relevant (T07, F04)

`AppShell.tsx`'s `refetchCurrentSession` fetched `getCodeGenerator`
unconditionally alongside every other stage, so the backend's correct
409 `ENTITLEMENT_BINDING_CONFLICT` for a not-yet-reachable Code
Generator stage made the entire refetch report connection state
"stale" for any session still in Discovery/Content/Design/Prepare —
reproduced live in the prior session's walkthrough (ISSUE-01: console
errors; ISSUE-02: a user-visible "latest check did not complete"
banner right after Content Architect approval). Now fetches Code
Generator only once Build Preparation is approved, or when a
session-keyed ref shows generation was already started for this exact
session (so a momentarily-stale upstream response can't hide an
existing preview); connection freshness is computed only from requests
actually attempted. Extracted the decision into a new pure, exported
`shouldFetchGenerationState()`, matching the existing
`resolveInitialStage()` testability pattern. Verified: 136 frontend
tests (5 new), tsc clean, production build succeeds.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [9270762] — Forbid hiding failure evidence in the repair prompt (T05)

Investigated T05 of `docs/code-generator-repair-plan-2026-09-16.md`
("make smaller-model generation easier to satisfy"). Found
`generation_prompt_builder.py`'s input-packet/output-acceptance
machinery already mature (mode enums, receipt hashing, context
ceilings, prefix-caching key ordering, dozens of specific per-diagnostic
repair rules refined from real failures) and satisfying most of the
plan's checklist already. Found one real gap: `repair_source.md` had no
blanket rule against satisfying a failing check by deleting the broken
element instead of fixing it. Added explicit rules — missing text
cannot be fabricated, a broken image cannot be fixed by hiding/deleting
it, a failed interaction cannot be fixed by removing its marker/handler
— and bumped the repair prompt version (v8 → v9) so old receipts aren't
reused under the new contract. Verified: 435 tests (1 new), ruff/mypy
clean.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [b361125] — Retry alternate resource candidates on materialize failure (T03)

Investigated the Code Generator's acquisition-to-render chain per
`docs/code-generator-repair-plan-2026-09-16.md` T03. Found that only
the Build-Preparation-pinned candidate path fell back to a fresh live
search on materialize failure; an ordinary search-based request (no
pin) picked one ranked candidate and gave up immediately if it failed
to materialize (expired URL, rejected request), even when other
policy-approved candidates from the same search existed. Acquisition
now retries across the same filtered candidate list, deterministically
excluding each failed candidate, bounded entirely by that one search's
results — no new network search, no second image client. Reviewed F05
(images planned without rendering) and found no reproducible gap in
the existing `LocalImage` binding check. Verified: 441 tests (1 new),
ruff/mypy clean.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [c617449] — Make Code Generator verified success truthful, supersede D-094 (T04)

Implemented T04 of `docs/code-generator-repair-plan-2026-09-16.md` (F03).
`config/app.native.toml`'s `preview_first_acceptance` flag, as
implemented, downgraded *all* source-contract, build, and runtime
diagnostics to advisory when enabled — not only the generated-output
polish findings D-094 intended — and silently swallowed a
runtime-verifier exception (zero browser evidence) while still
promoting the run to `ready` with an `active_preview`. Removed the
flag's ability to affect blocking status anywhere: source diagnostics
are always blocking, a non-runnable build always gets its
`BUILD_ARTIFACT_UNAVAILABLE` diagnostic, a runtime-verifier exception
now raises `VerificationFailure("RUNTIME_VERIFIER_FAILED", ...)`
instead of being swallowed, and runtime blocking status always follows
`effective_finding_severity()`. Set native's `preview_first_acceptance
= false`, matching every other overlay. The existing unconditional
unverified-`candidate_preview` path is untouched — a safe-but-unverified
build stays inspectable but can never reach `ready`. Recorded D-099,
superseding D-094. Added an integration regression test proving the
exact previously-broken scenario now stops at `needs_attention`.
Verified: 458 tests, ruff/mypy clean.

### 2026-09-18 00:00 +05:30 — Claude Code (Sonnet 5) — [b087ca3] — Make Code Generator image policy feasible and site-wide (T02)

Implemented T02 of `docs/code-generator-repair-plan-2026-09-16.md`
(F01/F02). `build_image_policy_snapshot()` now clamps
`minimum_visible_images`/`preferred_visible_images` to the actual
approved image slot count at creation, closing an impossible-floor
bug where a brief with fewer approved slots than the configured
minimum could never pass planning. Added a shared
`required_image_placements()` selection helper (raising the new
`ImagePolicyError`, a `.code`/`.message`-carrying `ValueError`) that
`design_realization.py` and `final_source_validation.py` both now use
instead of their own divergent, primary-route-only logic, so an image
approved on a non-primary route (e.g. a case-study page) is actually
selected and checked at every stage instead of being silently ignored
by design realization and masked by final source validation. Added 13
regression tests. Verified: 434 unit tests, 23 integration/API tests,
ruff/mypy clean.

### 2026-09-16 11:10 +05:30 — Claude Code (Sonnet 5) — [9d2aa0b] — Commit stage-duration tracking, diagnostic context, and stale-stage navigation fix

Committed the `.kiro` "code-generator-reliability-and-preview-integration"
session's finished, tested work (tasks 1-11), which had been sitting
uncommitted since 2026-09-15: per-stage duration recording on
`code_generator_runs` (migration 0024), concurrent-process-count/prior-
duration context on the `VITE_NODE_SPAWN_EPERM` diagnostic, a backend-only
`stage_estimate` in `CodeGeneratorService.get_state()` sourced only from
observed durations or `config/app.toml` budgets, and its frontend rendering.
Also included an out-of-band `tests/conftest.py` guard (hard-fails
`test_engine` against any database but `oryxenai_test`) and a fix for
`AppShell.tsx`'s `refetchCurrentSession`, which had no forward-correction
branch and left a session with already-approved stages frozen on stale
Discovery content after a fresh `/app` load. Live end-to-end verification
(the spec's tasks 12-13) remains blocked/incomplete from the prior session.
Verified: 427 code-generator unit tests, 19 integration tests (real
PostgreSQL), 131 frontend tests, tsc/ruff/mypy all pass.

### 2026-09-15 00:00 +05:30 — Codex (GPT-5) — [93cc34e] — Add beginner Azure deployment strategy

Added the requested `doc/deployment strategy/` operator pack covering the
current implementation and deployment gaps, VM-local setup, exact-SHA release
workflow, deferred `deploy.me` activation, owner prerequisites, maintenance,
AI-assisted troubleshooting, backups, cost controls, and first-party research.
Recorded the dedicated `deployment` release pointer and the two-phase
server/public-domain rollout decisions without changing application code.

### 2026-09-14 00:00 +05:30 — Codex (GPT-5) — [f594a11] — lossless Azure deployment session log

Added an append-only deployment session record covering the Azure VM wizard,
review corrections, VM creation, SSH evidence, bootstrap packages, repository
implementation context, compilation and verification boundaries, mistakes, and
unconfirmed Docker/application steps. Linked it from the deployment index and
project-status handoff without recording secret values.

### 2026-09-14 15:09 +05:30 — Codex (GPT-5) — [d0894d6] — Make Generation previews truthful

Removed invented build progress, timestamps, and Publish/Deploy UI from the
Generation workspace. Added explicit verified-versus-candidate preview labels,
a regeneration action, preview-first tablet layout, reduced-motion-safe stage
transition, and fixture/browser coverage for those states.

### 2026-09-14 14:52 +05:30 — Codex (GPT-5) — [62c4ac7] — Refresh project and deployment status documentation

Added the canonical `docs/project-status.md` handoff and aligned `AGENTS.md`,
`README.md`, architecture notes, and deployment documents with the current
committed implementation, Azure VM checkpoint, R2/Supabase readiness, dirty
worktree release gate, and pending Azure end-to-end acceptance.

### 2026-09-14 14:05 +05:30 — Codex (GPT-5) — [cf71c87] — Code Generator Windows build diagnostics

Classified Vite's Windows `spawn EPERM` path-resolution failure as infrastructure rather than generated-source failure, bypassed source repair for that condition, and provided a preflight-and-retry recovery action with regression tests.

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

## Compacted history

### 2026-09
- 2026-09-14 — [5e96a52] — Turned public examples into scrollable fictional portfolio previews with distinct layouts, navigation, motion, responsive/reduced-motion behavior, and API assertions.
- 2026-09-14 — [efb226e] — Kept intake actions accessible, expanded guidance limits, added approval acknowledgement, tightened mobile layering, and shared shell tokens with the browser fixture.
- 2026-09-14 — [c6eaa33] — Namespaced generation receipts and retry state by explicit attempt epoch, deduplicated resource/dependency receipts, and standardized semantic decline handling.
- 2026-09-14 — [a0cae30] — Implemented D-094 preview-first native verification with rebuilt acquisition ledgers and authorization-fence regression coverage.
- 2026-09-14 — [49d6e0d] — Fail-closed brief ingestion dispatch distinguishing raw/namespaced/legacy Build Preparation wire shapes.
- 2026-09-14 — [7e503f0] — Public fictional three-example portfolio showcase before sign-in.
- 2026-09-14 — [e53ebfb] — Role-gated administrator control plane at `/admin` matching the reference spec and 8 visuals.
- 2026-09-14 — [e37e302] — Deployment wizard preflight: derive model credentials from config, reject example hostnames, recover stopped Docker.
- 2026-09-14 — [88ba402] — Simple beginner-friendly Azure VM deployment contract (`azure-deploy.sh`, Compose, Caddy).
- 2026-09-13 — [cdac290] — Discovery question experience redesign to full visual-reference parity.
- 2026-09-13 — [f003023] — Code Generator split control room, preview theater, and traceability drawer.
- 2026-09-13 — [ff5acf7] — Code Generator preview theater research and reference images.
- 2026-09-13 — [15450bf] — Discovery question research handoff, evidence copies, and visual references.
- 2026-09-13 — [0e2b303, f74d145, fd127de] — Auth bootstrap timeout/recovery state and completed-restore banner fixes.
- 2026-09-13 — [aeb0fef] — Frontend visual overhaul: full editorial parity with the 12 visual design references (D-095 lineage).
- 2026-09-13 — [bfea878] — Frontend remediation: centered stage shell, safe handoffs, responsive review states.
- 2026-09-12 — [df96f4d, 7aa452b] — Authored the `docs/Fix Frontend/` remediation research pack, evidence map, and screen references.
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

## Summary (as of last compaction — 2026-09-18)

- Recent detailed entries retained: 19
- Compacted milestone bullets: 51
