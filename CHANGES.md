# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

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

### 2026-09-06 01:06 +05:30 - Codex (GPT-5 / OpenAI) - [cdf7a18] - pipeline: cancellable stage jobs and safe trace export

Added durable cancellation fencing for Content Architect and Visual Design
Director, a reusable first-three-stage job projection, bounded client trace
export/copy support, and regression coverage.

### 2026-09-05 23:08 +05:30 - Codex (GPT-5 / OpenAI) - [963375b] - deployment: record R2 readiness

Recorded the user's report that R2 storage and credentials are already
available, while distinguishing the VM-side configuration still pending and
preserving the rule that no R2 secret values enter chat or source control.

### 2026-09-05 22:53 +05:30 - Codex (GPT-5 / OpenAI) - [caa8f33] - frontend: complete authenticated three-stage handoff

Completed the authenticated Preact product handoff for the first three
explicit stages. Fixed progressive Discovery answer persistence and retry
classification, surfaced stage-start failures, scoped admin session hints,
cleared private drafts/idempotency state on logout, built the frontend bundle
inside Docker, and extended the opt-in live smoke path through Content
Architect and Visual Design Director with explicit approvals.

### 2026-09-05 22:25 +05:30 - Codex (GPT-5 / OpenAI) - [7a0c68f] - deployment: record local environment audit findings

Recorded the redacted local `.env` audit in the live deployment checkpoint:
the file is Git-ignored and populated, but duplicate authorization variables
and one malformed line must be cleaned before a separate production `.env` is
created on the VM. No secret values were displayed or copied.

### 2026-09-05 22:19 +05:30 - Codex (GPT-5 / OpenAI) - [a2a8a60] - deployment: record live Azure VM and SSH checkpoint

Recorded the completed Azure VM provisioning, final networking/NSG settings,
current public/private addresses, cross-device SSH handoff, completed Ubuntu
package preparation, and the remaining Docker/application deployment gates.
Marked the older wizard document as historical so future agents use the live
post-creation checkpoint.

### 2026-09-05 21:15 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [d6cde91] - code-generator: resource acquisition, generation orchestrator, development schemas

Added bounded live-search fallback for expired pinned Pixabay URLs during Code Generator acquisition, avoided repeating structurally unfixable findings across mid-generation polish rounds, surfaced model refusal reasons, and normalized mechanical token/CSS length mistakes; records D-072.

### 2026-09-05 19:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [34c638b] - code-generator: prevent token collision and sharpen repair diagnostics

Fixed a silent `--color-accent` token collision between raw colors and shadcn theme slots at schema and compiler layers, enriched content-key and distinctive-move repair diagnostics with concrete near-miss/selector evidence, and added planner collision guidance; records D-071.

### 2026-09-05 16:40 +05:30 - Codex (GPT-5 / OpenAI) - [8a2066a] - core: enforce pre-call budget ceiling for live runs

Added provider-neutral `BudgetedModelClient` to serialize structured calls and reserve prompt plus maximum completion charges before transmission, stopping execution when a session cost cap is reached; records D-070.

### 2026-09-05 15:23 +05:30 - Codex (GPT-5 / OpenAI) - [5b86779] - core: scoped model-result caching and receipts

Added session-scoped PostgreSQL caching for validated structured model results across Discovery, Content Architect, Visual Design Director, and Build Preparation with single-flight leases, prompt-cache hints, and telemetry; records D-069.

### 2026-09-05 14:30 +05:30 - Claude Code (Sonnet 5 / Anthropic) - [aedf96c] - code-generator: repair control flow, review prefix caching, motion catalogue

Closed repair control-flow gaps by allowing one bounded extra repair attempt and resilient polish round skips on cannot-complete, added prompt prefix-caching for whole-site integration review, and introduced deterministic motion pattern catalogue; records D-068.

---

## Compacted history

### 2026-09
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

## Summary (as of last compaction — 2026-09-06)

- Recent detailed entries retained: 12
- Compacted milestone bullets: 12
- Last updated: 2026-09-06 01:32 +05:30 — Antigravity (Gemini 3.8 Flash / Google)
