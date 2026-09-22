# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and architectural rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Strictly Append-Only for AI Agents (Zero Auto-Compaction):** AI agents must append new entries under `## Recent changes` using the Entry Template below. **AI agents must NEVER run auto-compaction, deletion, or truncation on this file.**
  - *Rationale & Edge Cases:* Automated compaction by LLMs causes severe git merge conflicts across concurrent multi-agent sessions (Codex, Claude Code, Antigravity, Cursor); risks silent loss of critical commit SHAs and ADR references (`D-XXX`); and burns tokens on full-file rewrites. Compaction is strictly operator-directed.

---

## Recent changes (Tier 1 — Uncompacted / Standard Detail)

### 2026-09-22 21:10 +05:30 — Claude Sonnet 5 (Anthropic) — [pending] — AGENTS.md
Added a "Fresh-machine setup and secrets policy" section to AGENTS.md covering new-device onboarding steps, exactly what counts as a secret and where each lives (local `.env`, VM-local production `.env`, CI's throwaway `.env`), the `credential_free_logs()` safety property to preserve, and a short list of actions an AI agent should always ask the operator about first. Also corrected two now-stale claims elsewhere in the same file ("first deployment path... not executed" and the matching "What to implement next" entries) to reflect that the live deploy (`07132fe`) already happened. Prompted by the operator wanting a clean, self-documenting handoff point for any future AI session or contributor on a fresh machine.

### 2026-09-22 20:25 +05:30 — Claude Sonnet 5 (Anthropic) — [e6864e4, 8feb06a, 86cf523, 89496e7, 07132fe] — scripts/azure-deploy.sh, PRs #1-#5
Completed the first successful live deployment to the Azure VM (release `07132fe823cd0a2279c8ae3dddab9b90277771f6`; confirmed reachable at `https://app.oryxenai.me` and `https://preview.oryxenai.me` via curl and a full browser render of the sign-in page). PR #1's merge triggered the newly-enabled auto-deploy and got every service healthy on the first attempt, but `verify_internal()`'s `credential_free_logs()` then blocked on a false-positive "leak" of `ANTHROPIC_API_KEY` into all five containers' logs (including postgres and caddy, which never see that variable). Root cause: `env_value()` never stripped a trailing `\r`, so a blank/CRLF-terminated value could substring-match broadly. Fixed via 4 follow-up PRs (#2-#5): CRLF stripping in `env_value()`, an 8-character minimum-length guard, and safe (non-secret) length/hash/container-name diagnostics for any future recurrence.

### 2026-09-22 17:20 +05:30 — Claude Sonnet 5 (Anthropic) — [3817d17, a29ddf5, 242c8dc, 2ede02a] — compose.yaml, config/app.docker.toml, .github/workflows/ci.yml
Got the CI quality gate fully green by fixing four layered Docker smoke-test bugs, each masked by the previous one: `preview-gateway` missing `DB_HOST_OVERRIDE`/`DB_PORT_OVERRIDE` (unlike `app`/`worker`); `app.docker.toml`'s `[auth] required = true` needing Supabase coordinates the CI throwaway `.env` never set; `app.docker.toml` incorrectly using R2/`artifact_storage` for preview storage instead of `local_fs` (per D-106, every other overlay including production already used `local_fs`); and the smoke test expecting an open 200 from `/api/v1/system/status`, which `d288077` had since admin-gated. Also re-enabled the `deploy` job's auto-trigger (removed the `false &&` guard added in `cbe7c7e`) per explicit operator go-ahead. PR #1 is now `MERGEABLE`/`CLEAN`.

### 2026-09-22 16:40 +05:30 — Antigravity (Gemini 3.8 Flash) — [0f0cc58, ea85d5c] — docs/deployment/deployment-issues.md, AGENTS.md
Established context-bounded multi-agent compaction architecture for `docs/deployment/deployment-issues.md` (< 400 lines hard limit). Converted 130-line narrative session log into high-density Compacted Resolved Ledger preserving all error signatures, root causes, and commit SHAs; embedded operational protocol for Codex, Claude Code, Antigravity, and Cursor; added overflow archive directory.

### 2026-09-22 — Claude Sonnet 5 (Anthropic) — [d57e3c0, f7b05d6, 4bdea92, 1847d80, cb76076] — scaffolds/, .github/workflows/ci.yml
Regenerated `scaffolds/react-vite-v1/package-lock.json` (`d57e3c0`) under Node 22 / npm 10.9 to resolve `@emnapi/core` lockfile mismatch on Linux CI (full pytest suite passed: 1,433 passed, 5 skipped). Fixed 4 downstream CI/Compose bugs: Gitleaks explicit `GITHUB_TOKEN` requirement (`f7b05d6`), throwaway `.env` creation for Compose (`f7b05d6`), Compose Postgres password synchronization (`1847d80`), and bootstrap admin email requirement in `config/app.docker.toml` (`cb76076`). Added failure log dump step for Compose containers (`4bdea92`).

### 2026-09-22 — Claude Sonnet 5 (Anthropic) — [5837913, e1fb376] — frontend/src/components/OutputInspector.tsx, .github/workflows/ci.yml
Switched Escape-key listener in `OutputInspector.tsx` to `useLayoutEffect` (`5837913`) to eliminate race condition where Playwright dispatched Escape before passive `useEffect` listener attached. Wired `scripts/warm-npm-cache.sh` into CI workflow (`e1fb376`) to resolve `ENOTCACHED` failures on fresh Linux CI runners.

### 2026-09-22 — Claude Sonnet 5 (Anthropic) — [1be4b13, 80687eb] — config/, src/oryxenai/agents/code_generator/core/process_runner.py
Fixed cross-platform npm invocation bug (D-111): changed Windows-specific `npm.cmd` override to portable `"npm"` across `config/app.toml` and `config/app.test.toml`, and hardened `resolve_npm_executable()` to fall back safely on non-Windows. Corrected Output Inspector Playwright assertions (`80687eb`). Retargeted PR #1 from `main` to `deployment` via `gh pr edit 1 --base deployment`, eliminating merge conflicts and reducing diff to ~1091/-23 lines.

### 2026-09-22 — Claude Sonnet 5 (Anthropic) — [cbe7c7e, 7cb4102] — .github/workflows/ci.yml, docs/deployment/ci-cd-runbook.md
Implemented fully automatic CD pipeline via self-hosted GitHub Actions runner on Azure VM running `azure-deploy.sh deploy` directly over outbound HTTPS (D-110, superseding D-107). Added `docs/deployment/ci-cd-runbook.md`. Temporarily added `false &&` to deploy step trigger (`cbe7c7e`) to prevent automatic deployment until explicitly authorized by operator.

### 2026-09-22 — Claude Sonnet 5 (Anthropic) — [bf6c6ff] — compose.production.yaml, docs/azure-issue.md
Fixed production Docker egress failure (D-109): removed `internal: true` from `compose.production.yaml`'s `backend` network, restoring outbound internet access for `worker`, `app`, and `migrate` (needed for npm cache warm-up, Supabase, and model provider calls) while preserving inbound port isolation.

### 2026-09-20 01:59 +05:30 — Codex (GPT-5) — [55e5692] — src/oryxenai/agents/code_generator/
Recovered Code Generator durable stage handoffs: coordinator now finalizes Plan before Acquire, safely redelivers checkpointed handoffs, and self-heals stranded terminal jobs before alerting user (D-042). Disabled Windows reload mode during native API launch that blocked Node/Playwright preview subprocesses.

---

## Key Active Milestones

### CI/CD, Containerization & Azure Infrastructure
- **2026-09-22 — [7cb4102, cbe7c7e] — Self-Hosted Actions Runner CD:** Implemented outbound-polling runner on Azure VM, removing SSH port exposures and external runner IP restrictions (D-110, supersedes D-107).
- **2026-09-22 — [bf6c6ff] — Bridge Network Egress:** Corrected Docker Compose network topology to allow outbound HTTPS egress while maintaining inbound isolation (D-109).
- **2026-09-22 — [1be4b13] — Cross-Platform Toolchain Resolution:** Unified `npm` binary resolution across Windows, Linux, and Docker environments (D-111).
- **2026-09-21 — [3615b35, d60d40b] — Production Hardening & Symlink Fix:** Enforced strict Linux mypy pins, HSTS headers, rate limiting, and fixed official Node.js npm/npx symlink copying in production Dockerfile (D-107, D-108).
- **2026-09-20..21 — [353ef25, d0d3a67, ccd9024] — VM-Local Persistent Storage:** Selected VM-local persistent disk/volumes over Cloudflare R2 for single-VM release simplicity; encapsulated services behind Caddy reverse proxy on 80/443 (D-106).

### Code Generator & Preview Engine
- **2026-09-20 — [55e5692, 743a4e4] — Durable Stage Handoffs & Advisory Review:** Coordinator safely redelivers checkpointed stage handoffs; whole-site quality review made advisory for unverified candidate previews when strict build/runtime checks pass (D-042, D-105).
- **2026-09-19 — [500e58c, 08c6031] — Preview Theater & Build Preparation Unlock:** Connected Build Preparation completion to unlock Code Generator directly; enabled standalone Preact preview theater testing via `/api` Vite proxy (D-103, D-104).
- **2026-09-19 — [ddab99a, 188af32, e713ff2] — Fail-Closed Worker Capabilities:** Worker capability receipts fail closed; mapped-content validation aligned with generated source; enforced split preview-origin security (D-100, D-101).
- **2026-09-18 — [c617449, b087ca3, 9270762] — Truthful Preview Verification:** Forbade hiding repair evidence by deleting broken elements; established truthful candidate verification and bounded image placement floors (D-099).

### Pipeline Agents & Editorial Studio Shell
- **2026-09-19 — [763ddfb, 0e2b303] — Living Draft Editorial Studio:** Unified authenticated product navigation under Preact Editorial Studio shell with stage handoffs (D-095).

---

## Entry Template (For AI Agents — Append to Tier 1)

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — [<commit-sha>] — <files/areas, comma-separated>
<One or two concise sentences: what changed, root cause/rationale, and related ADR references (e.g. D-0XX). Never write verbose debugging narratives or reproduction essays here; put diagnostic logs in docs/deployment/deployment-issues.md.>
```
