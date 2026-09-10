# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-10 19:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [pending] - docs(code-generator): close campaign B with a ready result

Campaign-B slot 5 (Pack A, run ff3398b1), the last slot in the shared
5-run budget, reached `ready` with zero blocking diagnostics across all
three verification gates. Verified beyond DB status: the promoted preview
was loaded in an actual browser, confirming real content in every
section, working navigation, zero console errors, all resources 200, and
`dist/index.html` present. No new code fix was needed -- this confirms
slots 1-4's four fixes (22db99c, d9caf30, e7d9284, 06eb2c0) together.
Campaign B is now closed (5/5 consumed, 1 ready).

### 2026-09-10 18:50 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [06eb2c0] - fix(code-generator): resolve real color tokens in the selected-work lifecycle normalizer

Campaign-B live slot 4 (Pack A) exhausted its repair budget on three
SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND diagnostics, all from d9caf30's
deterministic lifecycle-cue normalizer hardcoding assumed color token
names (`--color-ink-secondary`/`--color-border-subtle`/`--color-accent-
signal`) that don't exist in this run's actual generated tokens -- color
names are chosen per run by the model, never fixed. Added
`_resolve_existing_color_token()` to look up real tokens by semantic
keyword instead, degrading gracefully when none resolve. Verified 3 → 0
undefined references against the exact rejected run. Slot 4 consumed, no
ready result; 1 slot remains.

### 2026-09-10 17:28 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [e7d9284] - fix(code-generator): recognize trusted motion patterns in the final source audit

Campaign-B live slot 3 (Pack A) rejected a correct, trusted `<Reveal>`-based
hero motion beat because `typescript_ast_audit.py`'s final V4 motion-beat
check, unlike `source_validation.py`'s pre-gate and the route-motion
normalizer, had no exception for catalogue `pattern_id` beats and demanded
CSS/reduced-motion evidence that legitimately lives in `SharedSystems.tsx`/
`motion.css` instead. Mirrored the existing exception; verified 2 → 0
diagnostics against the exact rejected checkpoint. Slot 3 consumed, no
ready result; retrying Pack A for slot 4.

### 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [6c22712] - fix(code-generator): repair the verification regression test's route-path mismatch

Traced five stray `output/code-gen-output/` folders (zero model calls each,
per `portfolio.json`) to one broken integration test,
`test_verification_builds_and_promotes_a_clean_candidate`, left incomplete
across a Claude Code -> Codex -> Claude Code handoff. Root cause: the test
hand-wrote its "real" route content to an invented path
(`src/routes/home-4ea140588150/`) unrelated to the route's actual bare
storage key (`home`), so the router-wired placeholder the scaffold writer
creates was validated instead. Fixed the path, added a real `<nav>` landmark,
and added the closed-navigation-contract anchors the admitted fixture
requires; the test now passes end to end (build, DOM/runtime verification,
screenshot capture, promotion). See D-090.

### 2026-09-10 15:55 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [fd9669d] - fix(code-generator): surface the real issue code in terminal-failure/export evidence

`code_generator_verification.py`'s `_execute()` early-failure branches
(raised before a `VerificationProjection` exists) returned no `"code"` key,
so a real issue code (observed live as `PLAN_SECTION_COVERAGE`) was masked
as the generic `"needs_attention"` status in exported `portfolio.json`
evidence. Added the real code to both branches; new regression test asserts
it survives into `terminal_failure.code`/`evidence_summary.primary_issue.code`.
See D-091.

### 2026-09-10 14:43 +05:30 - Codex (configured runtime) - [d9caf30] - fix(code-generator): materialize selected-work lifecycle cue

After live Pack A slot 2 reached verification but was rejected for the
blueprint-required selected-work lifecycle cue, added an idempotent host-side
materializer for the sparse `observe`/`shape`/`deliver` treatment. It is scoped
to the admitted v4 lifecycle thesis and leaves approved content, images, and
dist/export behavior unchanged. The targeted suites passed 139 tests and the
exact saved slot-2 tree passed source audit and typecheck in a disposable
overlay.

### 2026-09-10 14:00 +05:30 - Codex (configured runtime) - [22db99c] - fix(code-generator): normalize route motion contract drift

After live Pack A exposed deterministic CSS-length and route-motion contract
drift, added host-side normalization for spelled CSS lengths, trusted selector
anchors, custom-motion guard/fallback CSS, and exact observer wiring. The
targeted suites and direct Pack A route-contract replay passed; the bounded
campaign records the live failure separately.

### 2026-09-10 12:00 +05:30 - Codex (configured runtime) - [68e1693] - fix(code-generator): reconcile repair-budget defaults

Aligned the Code Generator Pydantic repair defaults with the effective
`config/app.toml` policy (2 per unit, 4 total, 3 integration-polish rounds)
and documented D-089's deliberate retention of the unused `repair_depth`
field. The change keeps repair bounded based on the evidence from the prior
five-slot campaign rather than raising limits for distinct root-causable
defects.

### 2026-09-10 10:22 +05:30 - Codex (OpenAI) - [39076d0] - fix(code-generator): refresh stale image pins and harden dist exports
Refreshed expired Pixabay `/get/` pins by stable asset ID, applied the configured raw image-size limit, made exports retry-safe on Windows, and stopped partial `dist` trees from being advertised as runnable. Added live-provider and regression coverage for the image/export paths.

### 2026-09-10 03:08 +05:30 - Codex (GPT-6 / OpenAI) - [7a01ee9, 3f07609, f1e74d3, 40434cf, ed21a6a, c3fabdc, 5eca499] - fix(code-generator): close desktop generation reliability gaps
Closed preview/export, source-ownership, interaction-ownership, contract-ordering, static content-map, and conditional-motion audit gaps found in the authorized five-run campaign; the desktop/web path is hardened and the full Code Generator unit suite passes.

### 2026-09-10 00:03 +05:30 - Codex (GPT-6 / OpenAI) - [90e8349] - fix(code-generator): normalize typography token names

Normalized prefixed fluid type-step names at the schema and compiler
boundaries, so a planner value such as `type-heading` produces the canonical
`--type-heading-*` properties instead of `--type-type-heading-*`. Added prompt
guidance plus validated and trusted-construction regressions. The full Code
Generator unit suite passes (312), mypy passes, and Ruff lint passes.

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

## Compacted history

### 2026-09
- 2026-09-09 — [66d8287] — Authored a 6-document frontend/agent integration reference suite under `docs/frontend/` for the major frontend revamp.
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

## Summary (as of last compaction — 2026-09-10)

- Recent detailed entries retained: 17
- Compacted milestone bullets: 38
- Last updated: 2026-09-10 19:53 +05:30 — Claude Code (Sonnet 5 / Anthropic)
