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
| **Pull Request** | [PR #1](https://github.com/yashsrivastava0/OryxenAI/pull/1) | Target: `deployment` (Base fixed; mergeable: MERGEABLE) |
| **CI Quality Gate** | ❌ Failing (Docker Smoke Test) | Blocked on `BLOCKER-001` below; all 1,433 pytest tests pass |
| **Azure VM Deploy Trigger** | ⏸️ Force-Disabled (`false &&`) | Requires explicit operator go-ahead before re-enabling |
| **Last Updated** | 2026-09-22 16:35 +05:30 | Maintained across multi-agent sessions |

---

## Active Blockers

### [BLOCKER-001] `preview-gateway` fails in CI Docker smoke test on empty `DB_PORT_OVERRIDE`
- **Subsystem:** CI Docker Smoke Test (`.github/workflows/ci.yml:185`, `compose.yaml:92`)
- **First Seen:** 2026-09-22 15:30 +05:30 by Claude Sonnet 5
- **Error Signature:**
  ```text
  pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  db_port_override
    Input should be a valid integer, unable to parse string as an integer [input_value='']
  ```
- **Root Cause:** `.env.example` specifies `DB_PORT_OVERRIDE=`. `compose.yaml` attaches `env_file: .env` to `preview-gateway` (which unlike `app`/`worker` has no compose-level `DB_PORT_OVERRIDE: "5432"` override). Pydantic parses literal `""` as an invalid integer rather than falling back to default/`None`.
- **Diagnosed Fix (Ready to Apply):** In `.github/workflows/ci.yml` step `"Prepare throwaway .env for dev Compose smoke test"`, strip blank `DB_HOST_OVERRIDE=` and `DB_PORT_OVERRIDE=` lines or provide default int `"5432"` before starting containers.
- **Status:** Diagnosed; not yet applied (paused per operator instruction).

### [BLOCKER-002] PR #1 unmerged pending CI quality check
- **Subsystem:** GitHub Actions Branch Protection (`deployment-ci-gate`)
- **Root Cause:** Blocked strictly on `BLOCKER-001` passing the `quality` check.
- **Status:** Awaiting `BLOCKER-001` fix and green CI.

### [BLOCKER-003] Azure deploy workflow step force-disabled
- **Subsystem:** CD Pipeline (`.github/workflows/ci.yml:209`)
- **Root Cause:** Leading `false &&` in `deploy` job `if:` condition keeps deployment paused.
- **Policy Guardrail:** Merging PR #1 and removing `false &&` both require a **fresh, explicit operator go-ahead**.

---

## Resolved Issues (Compacted Ledger)

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
