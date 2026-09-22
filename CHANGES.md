# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [1be4b13, 80687eb] - Fixed both real CI failures blocking PR #1, and corrected the PR's target branch

Retargeted PR #1 from `main` to `deployment` (`gh pr edit 1 --base
deployment`) — it had been opened against the wrong base, which is what
was actually producing the huge +123k/-25k diff and the "CONFLICTING"
mergeable status (`main` and `deployment` diverged long ago at
`73c623c`); the brief's assumption that this was a stale GitHub
mergeability check was wrong. After retargeting, the diff dropped to the
real ~1091/-23 gap and `mergeable` flipped to `MERGEABLE`.

Fixed the npm.cmd cross-platform bug (`1be4b13`): `config/app.toml` and
`config/app.test.toml` hardcoded `npm_executable = "npm.cmd"`, inherited
by `config/app.docker.toml` (the real Azure/Docker production overlay)
via deep-merge — this was a live production bug, not just a CI artifact.
Changed both to the portable `"npm"` and hardened
`resolve_npm_executable()` (`process_runner.py`) to fall back to bare
`"npm"` on non-Windows instead of trusting an unresolved configured
value verbatim.

Fixed the Output Inspector browser test (`80687eb`): confirmed no overlap
with `PLAN.MD`'s active T02 preview-reload scope (different file, git
history predates it by a full commit-stream), then, after failing to
reproduce the race via CPU-throttled Playwright runs, corrected the
test's `is_hidden()`/`is_visible()` snapshot assertions to
`expect(...).to_be_hidden()/to_be_visible()`, matching the exact
"assert False where False = is_hidden()" failure signature.

All three of the originally reported failures are now addressed. Local
`uv run pytest` (1433 passed, 5 skipped), `ruff check`, `ruff format
--check`, and `mypy src` all pass; the Linux-CI-specific parts can only
be confirmed once PR #1's `quality` check reruns.

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [no code change yet] - Installed gh CLI, diagnosed 3 real CI failures blocking the first sync PR

Installed and authenticated the `gh` CLI (`winget install --id GitHub.cli`,
`gh auth login --web` as `yashsrivastava0`) so future sessions can read
Actions run/job logs directly instead of relaying them through the
operator — public unauthenticated REST calls return run/job *status* but
403 on log *content*, even for this public repo. Used it to pull the full
failure log for PR #1's `quality` check (blocked on merging the CD pipeline
work into `deployment`) and found three real failures, not flakes:
`tests/browser/test_frontend_remediation.py::test_developer_inspector_is_opt_in_and_drawer_is_accessible`
(not yet investigated — check for overlap with `PLAN.MD`'s active frontend
work before touching it);
`tests/integration/test_code_generator_verification_worker.py::test_verification_builds_and_promotes_a_clean_candidate`
and
`tests/unit/agents/code_generator/test_dependency_manager.py::test_supported_dependency_never_synthesizes_a_package_install_and_unsupported_uses_fallback`,
both traced to the same root cause: npm invocation resolves to the
Windows-only `npm.cmd` on Linux CI (`COMMAND_START_FAILED: ... No such file
or directory: 'npm.cmd'`) — **a real bug that will also break the Code
Generator's build-verification step on the actual (Linux) Azure VM in
production**, not merely a CI-environment artifact. Local `pytest -v
--strict-markers` (matching CI's exact invocation) still passes 100% clean
on Windows (1433 passed, 5 skipped), confirming this is Linux-specific and
can't be reproduced on the primary dev machine. Not yet fixed — see
`docs/deployment/ci-cd-runbook.md` and `docs/project-status.md` for the
current blocking state; `resolve_npm_executable()` in
`src/oryxenai/agents/code_generator/core/process_runner.py` is the
starting point for the fix.

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [cbe7c7e] - Document the CI/CD runbook and temporarily disable auto-deploy before a bulk push

Added `docs/deployment/ci-cd-runbook.md`: a standalone operational guide for
the self-hosted-runner CD pipeline so any future AI session or device can
set it up, operate it, and troubleshoot it without re-deriving this
session's context — covers the real working SSH key
(`oryxenai-demo-key.pem`) versus an unrelated, deleted `termius_windows` key
that never worked, the Windows `.pem` ACL/`icacls` fix, the GitHub runner
page defaulting to Windows even for a Linux target, runner health checks,
and how to re-add an approval gate. Linked from
`docs/deployment/README.md`; added a pointer from the now-superseded manual
section 6 of `deployment-guide.md`. Per an explicit operator instruction to
push every pending local commit to GitHub while explicitly not wanting a
live deploy yet, temporarily forced the `deploy` job's `if:` condition to
`false && ...` in `ci.yml` (reversible by deleting that clause) so the
push itself cannot trigger the now-fully-automatic pipeline before the
operator is ready for the first real deployment trial.

### 2026-09-22 - Claude Sonnet 5 (Anthropic) - [7cb4102] - Add fully automatic CD via a self-hosted GitHub Actions runner on the Azure VM

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

### 2026-09-21 10:12 +05:30 - Codex (GPT-5) - [353ef25] - Complete VM-local production storage hardening

Production Compose now bind-mounts PostgreSQL, Code Generator state, previews,
exports, and Caddy state below a configurable VM data root, with non-root
ownership, disk thresholds, filesystem/database backups, restore dry-runs,
read-back checks, and R2-free setup/doctor requirements (D-106). Local Docker
build, migration, health, Caddy, restart/engine-restart persistence, and
credential-free log gates passed; Azure deployment and the legacy generic
artifact-storage local implementation remain explicit follow-up blockers.

### 2026-09-20 01:59 +05:30 — Codex (GPT-5) — [55e5692] — Recover Code Generator stage handoffs and native preview execution

The durable coordinator now finalizes the completed Plan attempt before
creating Acquire, redelivers checkpointed stage handoffs safely, and
self-heals stranded terminal jobs before exposing attention in the product.
Unexpected Code Generator worker errors receive one bounded redelivery, and
native API launch no longer enables Windows reload mode that blocks
Node/Playwright preview subprocesses (D-042).

## Compacted history

### 2026-09
- 2026-09-21 — [a861465] — Reconciled live deployment readiness: DNS, Azure/SSH guest checks, Docker gap, verified SHA.
- 2026-09-21 — [91f0d18] — Cleared final local release-gate findings; full local suite and Compose config validation passed.
- 2026-09-20 — [d0d3a67] — Selected VM-local persistent Docker-backed storage over Cloudflare R2 for the first Azure release (D-106).
- 2026-09-20 — [ccd9024] — Made production packaging one self-contained Compose stack with only Caddy's 80/443 public.
- 2026-09-20 — [743a4e4] — Made whole-site quality-review output advisory when strict source/build/runtime checks pass (D-105).
- 2026-09-20 — [2224697] — Kept Code Generator retry available for any non-stale attention state, including a failed active job.
- 2026-09-20 — [c3e1f17] — Made the auth shell test deterministic by explicitly selecting the local `open` admission mode.
- 2026-09-19 — [50bf74d] — Cleared a Code Generator diagnostics name collision flagged by strict mypy (no runtime change).
- 2026-09-19 — [f2f4aba] — Reconciled deployment preparation artifacts: audit docs, CI/CD guidance, ignore rules.
- 2026-09-19 — [500e58c] — Reconciled Code Generator terminal state to safe `needs_attention` and added direct frontend acceptance (D-104).
- 2026-09-19 — [763ddfb] — Unified all non-admin auth routes under the Living Draft Editorial Studio shell.
- 2026-09-19 — [08c6031] — Connected Build Preparation completion to unlock Code Generator directly into the live preview control room.
- 2026-09-19 — [ac1fb98] — Ran required toolchain preflight before Code Generator admission.
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

## Summary (as of last compaction — 2026-09-22)

- Recent detailed entries retained: 9
- Compacted milestone bullets: 47
