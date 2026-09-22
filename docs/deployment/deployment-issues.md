# Deployment CI/CD Pipeline — Issues & Fixes Ledger

Context-bounded, high-density issue tracker for deployment and CI/CD pipelines.

---

## AI Agent Operating Protocol (Codex, Claude Code, Antigravity, Cursor)

> [!IMPORTANT]
> **Strict Context Budget:** This file MUST stay **under 400 lines** total. Never write long narrative stories or verbose session essays here.
> Read the **Current Deployment State** and **Active Blockers** first.

### Operating Rules for All AI Tools:
1. **Triage First:** Check **Active Blockers** before touching CI, PRs, or deployment configs. Do not re-diagnose already resolved issues.
2. **Logging New Issues:** If CI or deployment fails, add an entry under `## Active Blockers` using the [Active Blocker Template](#active-blocker-template). Include literal error signatures, affected files, and root causes so subsequent agents do not hallucinate.
3. **Success-Driven Compaction (Mandatory):** Once a fix is verified and succeeds:
   - Convert the verbose blocker card into a concise 3–4 line entry under `## Resolved Issues (Compacted Ledger)`.
   - **Delete** the verbose blocker block from `## Active Blockers`.
   - Record the exact commit SHA, date, and agent name.
4. **Archiving Threshold:** If this file exceeds **350 lines** or the resolved ledger exceeds 15 entries, move the oldest resolved entries to [`docs/deployment/archive/deployment-issues-archive-2026.md`](archive/README.md).
5. **Operational Caution:** Never overwrite the local `.env` in the repository checkout without an explicit backup.

---

## Current Deployment State

| Parameter | Current Value | Notes |
| :--- | :--- | :--- |
| **Active Branch** | `deployment-sync-2026-09-22` | Synced with `deployment` |
| **Pull Request** | [PR #1](https://github.com/yashsrivastava0/OryxenAI/pull/1) | Target: `deployment` (mergeable: MERGEABLE, mergeStateStatus: CLEAN) |
| **CI Quality Gate** | ✅ Passing (Docker Smoke Test) | Green at `2ede02a`; all 1,433 pytest tests pass |
| **Azure VM Deploy Trigger** | ▶️ Enabled | `false &&` guard removed at `a29ddf5` per explicit operator go-ahead |
| **Last Updated** | 2026-09-22 17:20 +05:30 | Maintained across multi-agent sessions |

---

## Active Blockers

None open.

---

## Resolved Issues (Compacted Ledger)

- **[FIXED-012] `/api/v1/system/status` smoke-test check expected an open 200** (`2ede02a`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* Would have failed `curl -fsS .../system/status` with HTTP 401 the moment FIXED-009/010/011 got containers healthy; never reached before.
  - *Root Cause:* `d288077` added `require_admin` to the whole system router; the unauthenticated smoke test was never updated to match. An open 200 would actually be a security regression.
  - *Fix:* Assert the endpoint returns 401 (proves routing + auth enforcement) instead of expecting 200.

- **[FIXED-011] `app` crash-loops on `PreviewStorageError: Preview storage credentials are not configured.`** (`242c8dc`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* `app` container unhealthy at `create_app()` import time, right after FIXED-009/010 fixed `preview-gateway`.
  - *Root Cause:* `config/app.docker.toml` set `preview_storage_provider = "artifact_storage"` (R2), needing `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY` configured nowhere for this overlay. Per D-106, R2 is explicitly not part of the first-release config; every other overlay (including production) already uses `local_fs`.
  - *Fix:* Changed `config/app.docker.toml` to `preview_storage_provider = "local_fs"`, matching D-106 and every other overlay.

- **[FIXED-009/010] BLOCKER-001 (`preview-gateway` DB_PORT_OVERRIDE) + Supabase coordinates missing** (`3817d17`, `a29ddf5`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* `preview-gateway` crash-looped on `pydantic_core.ValidationError: db_port_override ... unable to parse string as an integer [input_value='']`.
  - *Root Cause:* `compose.yaml`'s `preview-gateway` was the only app-image service missing the `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` environment overrides `app`/`worker` already had; `compose.production.yaml` never had this gap (its `x-application` anchor applies the override to every service). Also preempted a second, code-reading-discovered issue: `config/app.docker.toml` sets `[auth] required = true`, so `app` would have crash-looped next on missing `SUPABASE_URL`/`PUBLISHABLE_KEY`/`SECRET_KEY` (same shape as FIXED-008).
  - *Fix:* Added `DB_HOST_OVERRIDE: postgres` / `DB_PORT_OVERRIDE: "5432"` to `preview-gateway` in `compose.yaml`; added dummy Supabase coordinates to the CI throwaway `.env` step (`3817d17`). Also re-enabled the `deploy` job's `false &&` guard removal (`a29ddf5`) per this session's explicit operator go-ahead.

- **[FIXED-001] PR #1 wrong base branch** (2026-09-22, Claude Sonnet 5)
  - *Symptom:* PR #1 showed merge conflict and massive +123k/-25k diff against `main`.
  - *Root Cause:* PR targeted `main` instead of `deployment`.
  - *Fix:* Retargeted via `gh pr edit 1 --base deployment`. Diff dropped to real ~1091/-23 lines; state became `MERGEABLE`.

- **[FIXED-002] `npm.cmd` cross-platform resolution failure** (`1be4b13`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* CI test runner crashed when spawning npm executable on Linux.
  - *Root Cause:* `config/app.toml` and `config/app.test.toml` hardcoded `npm_executable = "npm.cmd"` (Windows-only), inherited by `config/app.docker.toml`.
  - *Fix:* Changed default to bare `"npm"` in configs; hardened fallback in `resolve_npm_executable()` in `process_runner.py`.

- **[FIXED-003] Output Inspector drawer Escape-key listener timing race** (`5837913`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* Playwright `expect(...).to_be_hidden()` failed after 5s timeout on Escape press in Linux CI.
  - *Root Cause:* Key listener attached in passive `useEffect` (fires post-paint); Playwright dispatched Escape before listener attached.
  - *Fix:* Switched to synchronous `useLayoutEffect` in `OutputInspector.tsx`.

- **[FIXED-004] CI runner offline npm cache missing warmup** (`e1fb376`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* Verification worker integration test failed with `npm error code ENOTCACHED`.
  - *Root Cause:* `.workspace/npm-cache` is empty on fresh CI runner; `scripts/warm-npm-cache.sh` was never wired into CI.
  - *Fix:* Added CI step to run `scripts/warm-npm-cache.sh` before running test suite.

- **[FIXED-005] Scaffolds lockfile npm version incompatibility** (`d57e3c0`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* `npm error code EUSAGE ... Missing: @emnapi/core@1.11.3 from lock file` under `npm ci`.
  - *Root Cause:* `scaffolds/react-vite-v1/package-lock.json` was generated with npm 11.x/12.x which nested packages differently than Node 22's bundled npm 10.9.3.
  - *Fix:* Regenerated lockfile using Node 22.20.0 / npm 10.9.3. Confirmed clean install on both Windows npm 11.6 and Linux npm 10.9. Full pytest suite passed (1,433 passed, 5 skipped).

- **[FIXED-006] Gitleaks PR token & Dev Compose missing `.env`** (`f7b05d6`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* Gitleaks action failed on PR event; Docker smoke test failed due to missing `.env` file.
  - *Root Cause:* `gitleaks/gitleaks-action@v2` requires explicit `GITHUB_TOKEN` on PRs; Compose declarations specify `env_file: .env`.
  - *Fix:* Passed `GITHUB_TOKEN` to Gitleaks step; added pre-build step in CI creating throwaway `.env` from `.env.example`.

- **[FIXED-007] Postgres password mismatch in CI throwaway `.env`** (`4bdea92`, `1847d80`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "oryxen"`.
  - *Root Cause:* Compose postgres service used `${POSTGRES_PASSWORD}` from host shell (`oryxen_test`), but `.env` literal had different placeholder. Added failure Compose log dump (`4bdea92`) to reveal root cause.
  - *Fix:* Synchronized throwaway `.env` generation to write `POSTGRES_PASSWORD=${POSTGRES_PASSWORD}` (`1847d80`).

- **[FIXED-008] Missing bootstrap admin emails on Docker app startup** (`cb76076`, 2026-09-22, Claude Sonnet 5)
  - *Symptom:* `ValueError: The bootstrap administrator count is invalid.` during app startup health check.
  - *Root Cause:* `config/app.docker.toml` sets `[auth] required = true`, requiring exactly 2 valid emails in `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`.
  - *Fix:* Appended two dummy admin emails to CI throwaway `.env` (`ci-admin-1@example.com,ci-admin-2@example.com`).

---

## Operational Gotchas & Safety Invariants

> [!CAUTION]
> **Never overwrite `.env` in place:** During diagnostic testing, never run `cp .env.example .env` in the working directory without backing up `.env` first. Live secrets (database, tokens) can be destroyed. Always use throwaway paths or automated backup/restore traps.

---

## Templates for Future AI Sessions

### Active Blocker Template
```markdown
### [BLOCKER-XXX] <Title>
- **Subsystem:** <Workflow / Service / File>
- **First Seen:** <YYYY-MM-DD HH:MM TZ> by <Agent/Tool> (<Model>)
- **Error Signature:**
  \`\`\`text
  <Literal error message / stack trace snippet>
  \`\`\`
- **Root Cause:** <Concise factual diagnosis>
- **Diagnosed Fix:** <Actionable remediation steps>
- **Status:** <Open / Diagnosed / In Progress>
```

### Compacted Resolved Template
```markdown
- **[FIXED-XXX] <Title>** (`<commit-sha>`, <YYYY-MM-DD>, <Agent>)
  - *Symptom:* <Short description of failure>
  - *Root Cause:* <Factual root cause>
  - *Fix:* <Code or configuration change made>
```
