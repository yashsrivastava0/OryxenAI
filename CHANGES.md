# OryxenAI — Change Log

Compact record of major work. Git history holds full diffs; see `DECISIONS.md` for rationale and `docs/deployment/deployment-issues.md` for deployment diagnostics. Operator-directed compaction may condense older prose but preserves commit and decision references.

## Recent changes

### 2026-10-01 21:30 +05:30 — Claude Code (Anthropic) — [ae83099] — Discovery screens restored and verified in the browser

Found by driving the signed-in local app: a September stylesheet rewrite (1029296) had dropped the rules for 53 classes that the Discovery working card, question card, ready card and error panel still use, so those screens rendered as unstyled text. Restored them from the last good stylesheet (mapping one missing colour token), stopped the approve and step labels from wrapping or doubling their arrow, scrolled the progress card into view after a revision, and showed plain operation names in the error panel instead of internal keys. Added an error-state fixture to the browser harness. Verified end to end in the real UI with a large resume: brief, revision applied, approval, then Content Architect review with the cost restriction held; the local API and worker were restarted on the new code. No push or deployment.

### 2026-10-01 17:50 +05:30 — Claude Code (Anthropic) with Codex (OpenAI) — [c756896] — Discovery speed, reliability, multi-user lane

Traced slow and failing Discovery to a very large span-linked dossier the model had to emit exactly, no recovery after a validator miss or gateway error, and one global model lane that queued every user. The model now writes a compact draft and the server builds and repairs the stored dossier (D-120); Discovery routes to GPT-6 Luna with one same-route recovery, streaming, and tighter timeouts; the model lane holds configurable concurrent jobs (migration 0026) and parallel first reservations no longer collide in the usage ledger. Fixed a redelivery revision check, revision-retry text loss, and the question and brief working copy in the UI. Verified live through the real worker with three and four concurrent users (question calls 4-7 s, briefs 24-49 s, all approved), a realistic resume kept every role, project and restriction, and the full Python and frontend suites, lint, types and build passed. No push or deployment; the VM needs its production overlay re-rendered and the migration applied on the next release.

### 2026-10-01 14:05 +05:30 — Antigravity (Google) — [f8d7bfc] — AGENTS.md, README.md context and documentation overhaul

Modernized AGENTS.md with machine-readable metadata, timestamp (2026-10-01), and an agent fast-track cheatsheet matrix optimized for Claude Code, OpenAI Codex CLI, and Antigravity. Redesigned and beautified README.md with 2026 developer aesthetics, Shields.io badges, a Mermaid sequence workflow, clean API matrices, and interactive details blocks. Verified ruff linting, formatting, and mypy type checks. No push or deployment.

### 2026-10-01 14:30 +05:30 — Claude Code (Anthropic) — [f5e5d14] — Content Architect GPT-6 Luna route

Added a dedicated `experiential_luna_6` profile (`gpt-6-luna`, same EXP Labs credential) and routed only Content Architect's engine and operation entries to it; Discovery stays on its existing profile (D-119). Verified through live runs of all three Content Architect samples, each valid in one call at roughly 47-63 seconds, with the NDA restriction held. Pricing for the new profile is copied from the existing one until real rates are supplied. No push or deployment.

### 2026-10-01 13:05 +05:30 — Claude Code (Anthropic) — [2bdc7f8] — Content Architect output, prompts, validators, review UI

Replaced the generic route and page-pack output with one typed page content tree that mirrors the pinned portfolio template, and rewrote the prompts around its real regions (exactly four pillars, organization names only, finished copy sized to each slot). Claims and a six-way dossier coverage ledger now bind to page field paths, with one shared rule module behind the validators, readiness gate, approval, and service (D-118). The review stage now shows structured section cards, an evidence and coverage inspector, and a client-side live preview of the pinned design in place of the mocked route panel. Verified with the full Python and frontend suites, lint, type checks, build, a browser render, and three live model runs (strong, sparse, and NDA samples) that each passed in one call. No push or deployment.

### 2026-10-01 10:40 +05:30 — Codex (OpenAI) — [4e20499] — single-provider active agent routing

Removed alternate-provider fallbacks and optional model selection from the active Discovery and Content Architect routes (D-117). Fresh retries now snapshot the current routing policy, so saved answers remain usable after configuration changes. Reused the existing ignored local credential file without exposing or changing secrets; verified gateway access, a privacy-free live preflight, and an authenticated Discovery retry that reached detailed brief review through the configured primary. No push or deployment.

### 2026-09-30 23:30 +05:30 — Codex (OpenAI) — [1ecb98d] — Discovery answer flow and brief recovery

Fixed the follow-up job revision mismatch that failed after answer submission, and recovered saved answers from older failed question jobs. A completed contextual question batch now prepares the brief directly. Simplified the interface to one question at a time with three suggested choices and an always-visible custom answer; corrected active-job display and repaired mechanical dossier links without inventing claims. Verified the authenticated local flow through detailed brief review, the full Python and frontend suites, build, lint, type checks, and database readiness. No push or deployment.

### 2026-09-30 21:20 +05:30 — Codex (OpenAI) — [77f7749] — model accounting and stage retry

Traced the local Discovery failure to provider connection errors followed by an automatic redelivery that exhausted the run's call allowance and mislabeled the result as an accounting outage. Restarted the local worker and verified the saved intake reached its questions; made spent-call failures terminal for that run, separated allowance and settlement errors, and checked the affected Python flows. No push or deployment.

### 2026-09-30 15:00 +05:30 — Codex (OpenAI) — [cf9bac3] — Discovery, Content Architect, product UI, regressions

Preserved exact appended intake and readable answer evidence, rejected malformed question options and answers, showed contextual question batches together, and advanced zero-question Discovery to brief preparation in the product. Passed the complete approved dossier to every Content Architect writing call and required a single-page coverage ledger before review and approval (D-116). Verified with the full Python and frontend suites; no live model call or deployment.

### 2026-09-30 16:25 +05:30 — Codex (OpenAI) — [7f97920] — local Google login reliability

Traced the local Google callback through a failing `/api/v1/me` provider response; restarting the API restored onboarding without changing Supabase or Google settings. Added a bounded retry and safe diagnostics for JWKS failures, verified the authenticated browser flow and focused auth tests, and left deployment untouched.

### 2026-09-30 16:35 +05:30 — Codex (OpenAI) — [bc0e3a6] — Azure availability diagnosis

Verified that the public app is unreachable because the Azure VM is deallocated and its scheduled auto-start Logic App is disabled. Recorded the September 23 disable event and the recovery steps in the deployment issue ledger; no Azure state or deployment branch was changed.

### 2026-09-29 20:52 +05:30 — Codex (OpenAI) — [c2b8347] — Discovery agent, API, Preact workspace

Implemented the Discovery slice of D-116: immutable source snapshots, a source-linked dossier, adaptive clarification rounds, explicit continue and approval actions, and the Preact evidence inspector. Raised Discovery's configured context budget and removed project truncation so the dossier preserves the full supplied inventory.

### 2026-09-29 16:29 +05:30 — Codex (OpenAI) — [f25bf4a] — docs/architecture/, DECISIONS.md

Defined the target Discovery and Content Architect handoffs in full (D-116): source-complete dossier, contextual zero-to-three-question flow, two explicit approvals, finished public copy, and AI-written `index.html` verified with the pinned stylesheet. This was architecture documentation only; no runtime, model, or deployment change was made.

### 2026-09-29 01:25 +05:30 — Codex (OpenAI) — [0ada944] — docs/architecture/, docs/architecture.md, DECISIONS.md
Added the D-115 portfolio architecture proposal and agent playbook for user review, covering responsibilities, evidence handoffs, Content Architect planning and audit, fixed-CSS rendering, isolated preview, ordered edits, privacy-aware restoration, and bounded repair. Removed pinned model and hosting assumptions; no implementation, tests, live model calls, or deployment changes were made.

### 2026-09-27 22:03 +05:30 — Codex (OpenAI) — [fb07691] — docs/architecture/, docs/architecture.md
Expanded the D-114 resume-to-portfolio proposal with source precedence, claim bindings, model packet and token limits, fixed-CSS/variable-HTML builds, sealed preview receipts, and serialized edit replay. Documented transport and theme-component gaps as blockers; the running application and deployment were unchanged.

### 2026-09-27 01:11 +05:30 — Codex (OpenAI) — [5e530d5] — docs/architecture/, DECISIONS.md, docs/architecture.md
Defined the proposed D-114 pipeline, stage and artifact contracts, browser-verified preview, revision flow, and non-Azure deployment target. The active two-stage product and deployment were unchanged.

### 2026-09-25 — Codex (OpenAI) — [e92f521] — active workflow, API and worker registries, product shell, documentation
Removed retired implementation packages and user-facing artifacts; aligned routes, workers, model routing, navigation, guides, and regression coverage with Discovery and Content Architect while retaining generic cleanup and migration history.

### 2026-09-24 — Codex (OpenAI) — [e5c95bd] — active API, worker, configuration, product UI, and project context
Removed downstream generation stages from the active workflow (D-113). Preserved historical outputs and migrations; legacy source remained in the checkout after a broad deletion was rejected by automatic review.

### 2026-09-23 — Codex (OpenAI) — [7e1531b] — reference PDF
Added and visually checked a source-audited pipeline reference covering agent contracts, prompts, persistence, workers, review UI, and checked-in samples.

### 2026-09-23 — Codex (OpenAI) — [a97a3e7] — Code Generator worker/preflight, config/models.toml, preview bridge, tests
Fenced worker claims on config-bound capability proofs, grouped equivalent profiles to avoid duplicate preflight calls, and corrected preview lifecycle reporting.

## Compacted history

- **2026-09-22 — Azure operations and branch policy:** configured daily VM cost scheduling (D-112); created the staging/deployment promotion rules [218da7b]; documented fresh-machine setup and secrets policy [ddbea9c].
- **2026-09-22 — First live deployment and credential-safe diagnostics:** deployed release [07132fe] through PRs [e6864e4, 8feb06a, 86cf523, 89496e7, 07132fe] and fixed false-positive secret detection in container logs.
- **2026-09-22 — CI, Docker, and deployment fixes:** resolved the Docker smoke-test layers and re-enabled the guarded deploy job [3817d17, a29ddf5, 242c8dc, 2ede02a]; added failure logs and corrected CI environment setup [d57e3c0, f7b05d6, 4bdea92, 1847d80, cb76076]. Compacted the deployment issue log [0f0cc58, ea85d5c].
- **2026-09-22 — Toolchain and CD:** fixed cross-platform npm resolution and preview assertions [1be4b13, 80687eb]; fixed Escape handling and npm cache warming [5837913, e1fb376]; established self-hosted Actions CD (D-110) [cbe7c7e, 7cb4102], and restored Docker network egress (D-109) [bf6c6ff].
- **2026-09-20–21 — Pipeline and infrastructure milestones:** durable handoffs and advisory review (D-042, D-105) [55e5692, 743a4e4]; preview theater and Build Preparation unlock (D-103, D-104) [500e58c, 08c6031]; fail-closed worker capabilities and preview-origin security (D-100, D-101) [ddab99a, 188af32, e713ff2]; truthful preview verification (D-099) [c617449, b087ca3, 9270762]; Editorial Studio shell (D-095) [763ddfb, 0e2b303]; production hardening and symlink fix (D-107, D-108) [3615b35, d60d40b]; VM-local storage and reverse proxy (D-106) [353ef25, d0d3a67, ccd9024].

## Entry template

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — [<commit-sha>] — <files/areas>
<One or two concise sentences describing the outcome, rationale, and related decision references. Keep deployment diagnostics in docs/deployment/deployment-issues.md.>
```
