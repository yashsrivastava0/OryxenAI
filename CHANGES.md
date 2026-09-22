# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [pending commit] - Add fully automatic CD via a self-hosted GitHub Actions runner on the Azure VM

Per the owner's request to stop deploying by hand, added a `deploy` job to
`.github/workflows/ci.yml` (`needs: quality`, restricted to `push`/
`workflow_dispatch` on `deployment`) that runs `azure-deploy.sh deploy
${{ github.sha }}` then `verify` directly on the VM's own GitHub Actions
runner — no SSH secrets, no NSG change, ever, since the runner polls GitHub
over outbound HTTPS instead of GitHub SSHing in. Registered and started the
runner (`azure-oryxenai` label, systemd service, `oryxenaiadmin`) on the VM
at `/home/oryxenaiadmin/oryxenai`, confirmed `active (running)` and
boot-enabled. No approval gate for now, per explicit "fully automatic,
temporarily" instruction — trivially reversible (two-line comment left in
the workflow showing how). Recorded as D-110, superseding D-107 (moved to
Compacted & Superseded History). Corrected a stale "GitHub Actions not
required, SSH manually" line in `docs/project-status.md`.

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [bf6c6ff] - Fix production Docker network egress bug found during first live Azure deploy

The first real rehearsal deploy against the Azure VM built all 4 images
successfully (confirming the `d60d40b` npm/npx fix) but then failed with
`EAI_AGAIN` during npm-cache warm-up. Root cause: `compose.production.yaml`'s
`backend` network was Docker-`internal`, with `app`/`worker`/`migrate`/
`preview-gateway` attached only to it — blocking *all* outbound routing for
those services, not just inbound exposure, which would also have blocked
live Supabase/model-provider/npm calls in production. Removed
`internal: true` from `backend` (D-109); inbound isolation is unaffected
since only `caddy` publishes a host port. Verified locally with Docker
Desktop: DNS resolution + a real HTTPS 200 from a `worker` container on the
fixed network, then the exact failing warm-cache command re-run clean. Full
local suite re-run after the fix: `ruff check`/`ruff format --check`/`mypy
src` clean, `pytest` 1433 passed/5 skipped, frontend `typecheck`/`test`
(144 passed)/`build` clean. Documented in `docs/azure-issue.md`. Not yet
redeployed to the VM — pending explicit approval per the operator's
instruction.

### 2026-09-21 - Claude Sonnet 5 (Anthropic) - [3615b35] - Close CI/security gaps found in production readiness audit

Independent audit (deployment/infra, CI/testing, auth/security) found and
fixed: the real mypy CI blocker (Windows-only `subprocess.CREATE_NO_WINDOW`/
`CREATE_NEW_PROCESS_GROUP` type-check on Windows dev machines but not on
Linux CI; pinned `mypy platform = "linux"` plus getattr-guarded the 3 call
sites in `process_runner.py`), and a latent test-isolation bug (`ci.yml` set
`OryxenAI_CONFIG_OVERLAY` job-wide, silently breaking plain unit tests that
assert `config/app.toml` defaults; scoped it to only the migration step,
letting the existing autouse fixture handle integration/worker tests).
Also added Caddy-edge HSTS/security headers, removed the working weak
`POSTGRES_PASSWORD` default from `.env.example` (with a `doctor()` check),
added a minimal per-IP rate limiter plus the `--proxy-headers` fix it needs
to see real client IPs behind Caddy, noindex-tagged the auth shells, wired
frontend lint/typecheck/Vitest/build into CI, and corrected the stale
pre-npm-fix release SHA in `docs/project-status.md`. A GitHub-Environment-
gated automatic-deploy CI job was built, then reverted per explicit
correction mid-session: the intended model is GitHub CI (verification only)
with Azure deployment staying a manual SSH step — recorded as D-107/D-108.
Confirmed via the GitHub UI that this fix targets the actual latest failing
CI run (#10 on `3994513`) line-for-line, and that the existing Actions
allowlist/ruleset (`deployment-ci-gate`, PR-required, no bypass) already
covers every action this workflow uses. Local verification: ruff, ruff
format, mypy (both platform assumptions), full pytest (1438 tests, run in
memory-safe batches), frontend typecheck/Vitest (144 tests)/build, Docker
build, and production Compose config validation all passed; the dev-compose
container smoke test was blocked only by a local port conflict (5544, this
machine's native Postgres), not a real issue. `PLAN.MD` was left untouched —
it has unrelated in-progress edits from another session.

### 2026-09-21 - Codex (GPT-5) - [d60d40b] - Fix production npm runtime toolchain

The first Azure deployment built the image but failed during offline npm-cache
warm-up because the runtime Dockerfile copied npm/npx symlink launchers as
regular files. The runtime now copies the npm package, recreates both links,
and smoke-checks `npm --version` and `npx --version` during the image build.
Recorded the exact failure, correction, and pre-push verification results in
the deployment history. The corrected release still requires a Linux VM image
build and runtime acceptance after publication.

### 2026-09-21 - Codex (GPT-5) - [a861465] - Reconcile live deployment readiness

Recorded the current Namecheap DNS resolution, Azure/SSH guest checks, Docker
installation gap, exact verified application SHA, and local-versus-remote
deployment branch state. This keeps the pre-deployment checklist aligned with
the latest operator evidence without claiming that Azure application
deployment or production acceptance has occurred.

### 2026-09-21 - Codex (GPT-5) - [91f0d18] - Pass final local release checks

Cleared the final local release-gate findings: aligned the Discovery retry
expectation with the configured policy, narrowed Code Generator reconciliation
for strict type checking, resolved the trusted Node executable in the browser
fixture, and applied repository formatting. Ruff lint, Ruff format check,
Mypy, the full pytest suite, and production Compose configuration validation
passed on the exact application release commit.

### 2026-09-21 10:12 +05:30 - Codex (GPT-5) - [353ef25] - Complete VM-local production storage hardening

Production Compose now bind-mounts PostgreSQL, Code Generator state, previews,
exports, and Caddy state below a configurable VM data root, with non-root
ownership, disk thresholds, filesystem/database backups, restore dry-runs,
read-back checks, and R2-free setup/doctor requirements (D-106). Local Docker
build, migration, health, Caddy, restart/engine-restart persistence, and
credential-free log gates passed; Azure deployment and the legacy generic
artifact-storage local implementation remain explicit follow-up blockers.

### 2026-09-20 22:44 +05:30 - Codex (GPT-5) - [d0d3a67] - Select VM-local persistent storage for the first Azure release

Recorded the first-release storage decision as VM-local persistent Docker-backed
storage instead of Cloudflare R2. Updated the deployment strategy, readiness
matrix, runbook, owner checklist, operations guide, combined deployment guide,
status/history, and project status to require local-filesystem provider
configuration, shared artifact/preview volumes, non-root ownership, disk checks,
backup/restore, restart survival, and preview readback. R2 references remain
only as compatibility or historical context; the Docker/config follow-up is
still required before deployment.

### 2026-09-20 17:39 +05:30 - Codex (GPT-5) - [ccd9024] - Make production Compose stack self-contained

Reworked production packaging around one pinned Compose stack. The production
file now owns PostgreSQL, one-shot migrations, separate app/worker/preview-
gateway services, and Caddy with only ports 80/443 public; it also adds the
internal service network, persistent volumes, health/dependency gates, the
non-root application image, locked frontend/Python installs, safer build
context, and aligned release-script, CI, and deployment documentation. Docker
build, sanitized Compose config, isolated smoke startup, migration, health,
Caddy routing, non-secret log scan, and runtime-user checks passed locally.

### 2026-09-20 14:55 +05:30 - Codex (GPT-5) - [743a4e4] - Keep Code Generator previews available through quality-review failures

Whole-site quality-review output is now an advisory gate when the generated
source passes the strict source, build, and runtime checks. The verification
worker stores an owner-scoped unverified candidate preview instead of hiding a
buildable portfolio, while active-preview promotion and success entitlement
remain fail-closed until the receipt is valid. Added one bounded, model-free
retry for the classified Windows Vite child-process spawn race. Deterministic
Code Generator, integration, frontend, and generated-portfolio build checks
pass; the two permitted live attempts were consumed during diagnosis and no
third live pipeline run was made.

### 2026-09-20 01:59 +05:30 — Codex (GPT-5) — [55e5692] — Recover Code Generator stage handoffs and native preview execution

The durable coordinator now finalizes the completed Plan attempt before
creating Acquire, redelivers checkpointed stage handoffs safely, and
self-heals stranded terminal jobs before exposing attention in the product.
Unexpected Code Generator worker errors receive one bounded redelivery, and
native API launch no longer enables Windows reload mode that blocks
Node/Playwright preview subprocesses (D-042).

### 2026-09-20 00:38 +05:30 — Codex (GPT-5) — [2224697] — Always expose Code Generator retry after terminal job failure

The Generate & Preview recovery action now remains available for any
non-stale attention state, including a failed active job that still reports
its previous planning status. The production retry capability reconciles that
terminal job before queueing the same-run stage again, with route, service,
adapter, and browser regression coverage.

### 2026-09-20 00:03 +05:30 — Codex (GPT-5) — [c3e1f17] — Make auth shell test deterministic under test overlay

The API shell test helper now explicitly selects the local `open` admission
mode instead of inheriting the integration overlay's restricted `allowlist`
setting. The focused production-shell test passes with the CI overlay enabled.

### 2026-09-19 23:50 +05:30 — Codex (GPT-5) — [50bf74d] — Clear Code Generator diagnostics name collision

Renamed the route-batch diagnostics local in the generation orchestrator so
the strict mypy check no longer reports a same-scope redefinition. Runtime
behavior is unchanged; the type-check failure is removed without a broad
formatting rewrite.

### 2026-09-19 23:48 +05:30 — Codex (GPT-5) — [f2f4aba] — Reconcile deployment preparation artifacts

Committed the deployment-strategy audit documents, readiness and GitHub CI/CD
guidance, the project-status cross-link, and the repository ignore rules for
browser captures and pytest temp directories. The release guidance continues
to require a clean exact-SHA deployment pointer and does not include secrets,
caches, or browser/tool artifacts.

### 2026-09-19 22:46 +05:30 — Codex (GPT-5) — [500e58c] — Reconcile Code Generator terminal state and add direct frontend acceptance

Terminal Code Generator failures now reconcile the run to a safe
`needs_attention` state only after automatic retries are exhausted, while the
frontend uses the server retry flag, surfaces safe job diagnostics, and stops
polling truthfully. Added a config-driven standalone-to-product Generate &
Preview fixture, exact local preview origins, and deterministic regression
coverage (D-104).

### 2026-09-19 20:00 +05:30 — Antigravity (Gemini 3.8 Flash) — [763ddfb] — Unify auth fallback views into Living Draft Editorial Studio theme

Consolidated all non-admin auth routes (`/`, `/sign-in`, `/auth/callback`,
`/onboarding`, `/access-not-approved`, `/account-unavailable`) under the canonical
Living Draft Editorial Studio shell (`.sign-in-workspace` with header and the
6-stage interactive studio showcase). Completely removed the legacy unstyled
`.auth-card-outer::before` pseudo-element and fallback layout that leaked
unformatted `IDENTITY PROOF` text and unstyled progress steps. Extended
`body:not([data-page="admin"])` flex styling and added dedicated styling for the
progress, onboarding, access review, unavailable, and workspace-ready panels
while strictly preserving all DOM IDs, form inputs, and test assertion hooks.
Passed all 93 Python auth tests, 51 Node frontend tests, and 141 Vitest tests.

### 2026-09-19 19:44 +05:30 — Codex (GPT-5) — [08c6031] — Connect Build Preparation to the live preview control room

Build Preparation completion now unlocks Code Generator in the same polling
cycle, and its primary action starts generation directly while navigating to
the control room. Replaced fabricated preparation evidence with the actual
route/resource/component indexes, removed unsupported follow-up chat controls,
and added exact-origin preview protocol helpers, reload/degraded states, and a
gateway-injected fallback bridge. Verified the frontend build, full Vitest
suite, gateway tests, Ruff, and preview-handshake regression.

### 2026-09-19 19:41 +05:30 — Codex (GPT-5) — [ac1fb98] — Run required toolchain preflight before Code Generator admission

The static Code Generator control room now runs the disposable toolchain
preflight before provider compatibility and paid planning, keeps the launch
button busy during the proof, and explains pending preflight readiness without
leaking the raw blocker code. The same sequencing covers fixture and upload
fallback starts. Focused static tests and the local disposable preflight pass.

## Compacted history

### 2026-09
- 2026-09-19 — [761a5d8] — Preserved bounded repair evidence and resolved JSX motion targets.
- 2026-09-19 — [ddab99a] — Made worker capability receipts fail closed for new Code Generator work (D-100).
- 2026-09-19 — [188af32] — Aligned mapped-content validation with generated source and retained bounded repair deltas (D-101).
- 2026-09-19 — [e713ff2] — Enforced Code Generator handoff, worker, and split preview-origin contracts.
- 2026-09-19 — [a1f7fde] — Proved generated dependency locks with the exact verification install.
- 2026-09-19 — [2976b91] — Consolidated deployment documentation and canonical navigation.
- 2026-09-19 — [87d60a7] — Corrected Code Generator audit confidence and qualified the route-context, Docker-overlay, and Windows process findings.
- 2026-09-19 — [392277c] — Audited the Code Generator architecture and preview issue surface, preserving the findings for implementation follow-up.
- 2026-09-18 — [f0b8d7a] — Ran the first live repair campaign attempt, fixed local environment blockers, and documented an evidenced content-generation finding.
- 2026-09-18 — [c3cfe3a] — Fixed test module-name collisions so the full unit tree could collect, while documenting unrelated overlay mismatches.
- 2026-09-18 — [no code change] — Verified portable Code Generator exports with clean install, build, route, asset, and secret/path checks (T08).
- 2026-09-18 — [a64003a] — Fetched Code Generator state only when reachable, preventing pre-approval entitlement conflicts from marking the product shell stale (T07, F04).
- 2026-09-18 — [9270762] — Forbade hiding repair evidence by deleting broken elements and bumped the repair prompt version (T05).
- 2026-09-18 — [b361125] — Retried alternate Code Generator resource candidates on materialize failure within one bounded search result set (T03).
- 2026-09-18 — [c617449] — Made verified Code Generator success truthful, kept unverified candidates inspectable, and recorded D-099 (T04).
- 2026-09-18 — [b087ca3] — Made the image policy feasible across approved slots and shared placement validation across realization and final-source checks (T02).
- 2026-09-16 — [9d2aa0b] — Committed stage-duration tracking, diagnostic context, stale-stage navigation repair, and test-database protection.
- 2026-09-15 — [93cc34e] — Added the beginner Azure deployment strategy and its release/rollout handoff decisions.
- 2026-09-14 — [f594a11, d0894d6, 62c4ac7, cf71c87] — Consolidated Azure deployment evidence, truthful Generate previews, canonical status/release gates, and Windows Vite preflight diagnostics.
- 2026-09-14 — [250417d, e7296f8, 5e96a52, efb226e, c6eaa33] — Delivered public-preview motion/examples, accessible intake/review states, shared shell tokens, and attempt-scoped generation receipts.
- 2026-09-14 — [a0cae30, 49d6e0d, 7e503f0, e53ebfb, e37e302, 88ba402] — Hardened preview-first verification and brief ingestion, shipped public examples/admin control, and documented the beginner Azure VM contract.
- 2026-09-13 — [cdac290, f003023, ff5acf7, 15450bf] — Refined Discovery research handoff and delivered the Code Generator control room, preview theater, traceability drawer, and reference pack.
- 2026-09-13 — [0e2b303, f74d145, fd127de, aeb0fef, bfea878] — Hardened auth restore states and completed the editorial frontend overhaul with safe handoffs and responsive review states (D-095 lineage).
- 2026-09-12 — [df96f4d, 7aa452b] — Authored the frontend remediation research pack, evidence map, and screen references.
- 2026-09-11 — [pending commit, a0cae30, c8c9333, 67d5a75, no commit] — Completed the D-095/D-094 frontend and preview work, fixed Visual Design Director output recovery, restored rich first-four-stage output, and documented the D-090 model-completeness investigation.
- 2026-09-10 — [01e9ed0, 882574e, 1563282, 11a8fe3] — Tightened QualityFindingV2/schema retries, image floors, and campaign-B acceptance evidence (D-090/D-092).
- 2026-09-10 — [06eb2c0, e7d9284, 6c22712, fd9669d, d9caf30] — Corrected selected-work tokens, trusted motion recognition, verification evidence, route-path coverage, and host-side lifecycle materialization (D-090/D-091).
- 2026-09-10 — [22db99c, 68e1693, 39076d0, 7a01ee9, 3f07609, f1e74d3, 40434cf, ed21a6a, c3fabdc, 5eca499] — Normalized motion/repair budgets, refreshed image pins, hardened Windows exports, and closed the five-run desktop generation gaps.
- 2026-09-10 — [90e8349] — Fixed fluid type-step token double-prefixing at the schema/compiler boundary.
- 2026-09-09 — [9716681, 4da1ddb, 14bb97c, c8a66e7, 80a925c] — Hardened host-owned quality findings and Windows toolchain preflight, leaving Pack C honestly blocked when unresolved.
- 2026-09-09 — [a503a4a, 66d8287, 59409b5, 2f424e5] — Implemented the reliability plan, authored frontend/agent integration references, fixed worker-cache portability, and hardened brief-driven generation.
- 2026-09-09 — [78a9c77, bc7b5a6, f20779f, 051afa6] — Retired the static pipeline shell, added audited pipeline reset, clarified planner tokens, and detected undeclared npm imports.
- 2026-09-09/08 — [e99ed55, 29fc598, a2ae087, 2790e9d, 44304ff, ddc2e77, 3a6cf25, b07582d, 7f2fbd0, 9d256f3, d6b6777, bb7078b, 5731cf5, 78eacc7] — Established the Code Generator campaign handoff, bounded repair authority, Azure overlays, Generate & Preview gate, provider-neutral handoffs, and scoped telemetry.
- 2026-09-07/06/05 — [7f09506, 5bef169, ac5543e, 3f5b2aa, 78117e7, 446d4c7, 87f97f4, 7578b9a, f7546d4, 6707cce, 5768ce7, 618a038, fa9be97, f208540, ebfbc94, cdf8952, 1956d58, 7c94916, 83179f3, ae89b61, 68f1cd1, 861e981, cdf7a18, 903477a, a2a8a60, 963375b, 7a0c68f, caa8f33, 34c638b, d6cde91, 8a2066a, 5b86779, aedf96c, 0ce8ecd, 9fabd58] — Closed candidate-preview, runtime, deployment/auth, provider, resource/repair, motion, and canonical-output foundations.

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

## Summary (as of last compaction — 2026-09-21)

- Recent detailed entries retained: 19
- Compacted milestone bullets: 28
