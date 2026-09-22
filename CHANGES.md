# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and architectural rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Strictly Append-Only for AI Agents (Zero Auto-Compaction):** AI agents must append new entries under `## Recent changes` using the Entry Template below. **AI agents must NEVER run auto-compaction, deletion, or truncation on this file.**
  - *Rationale & Edge Cases:* Automated compaction by LLMs causes severe git merge conflicts across concurrent multi-agent sessions (Codex, Claude Code, Antigravity, Cursor); risks silent loss of critical commit SHAs and ADR references (`D-XXX`); and burns tokens on full-file rewrites. Compaction is strictly operator-directed.

---

## Recent changes (Tier 1 — Uncompacted / Standard Detail)

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

## Key Architectural Milestones (Tier 2 — Moderately Compacted / High-Value History)

### CI/CD, Containerization & Azure Infrastructure
- **2026-09-22 — [7cb4102, cbe7c7e] — Self-Hosted Actions Runner CD:** Implemented outbound-polling runner on Azure VM, removing SSH port exposures and external runner IP restrictions (D-110, supersedes D-107).
- **2026-09-22 — [bf6c6ff] — Bridge Network Egress:** Corrected Docker Compose network topology to allow outbound HTTPS egress while maintaining inbound isolation (D-109).
- **2026-09-22 — [1be4b13] — Cross-Platform Toolchain Resolution:** Unified `npm` binary resolution across Windows, Linux, and Docker environments (D-111).
- **2026-09-21 — [3615b35, d60d40b] — Production Hardening & Symlink Fix:** Enforced strict Linux mypy pins, HSTS headers, rate limiting, and fixed official Node.js npm/npx symlink copying in production Dockerfile (D-107, D-108).
- **2026-09-20..21 — [353ef25, d0d3a67, ccd9024] — VM-Local Persistent Storage:** Selected VM-local persistent disk/volumes over Cloudflare R2 for single-VM release simplicity; encapsulated services behind Caddy reverse proxy on 80/443 (D-106).
- **2026-09-15 — [93cc34e] — Azure Deployment Strategy:** Formulated one-VM Azure Compose rollout and verification runbooks.

### Code Generator & Preview Engine
- **2026-09-20 — [55e5692, 743a4e4] — Durable Stage Handoffs & Advisory Review:** Coordinator safely redelivers checkpointed stage handoffs; whole-site quality review made advisory for unverified candidate previews when strict build/runtime checks pass (D-042, D-105).
- **2026-09-19 — [500e58c, 08c6031] — Preview Theater & Build Preparation Unlock:** Connected Build Preparation completion to unlock Code Generator directly; enabled standalone Preact preview theater testing via `/api` Vite proxy (D-103, D-104).
- **2026-09-19 — [ddab99a, 188af32, e713ff2] — Fail-Closed Worker Capabilities:** Worker capability receipts fail closed; mapped-content validation aligned with generated source; enforced split preview-origin security (D-100, D-101).
- **2026-09-18 — [c617449, b087ca3, 9270762] — Truthful Preview Verification:** Forbade hiding repair evidence by deleting broken elements; established truthful candidate verification and bounded image placement floors (D-099).
- **2026-09-14 — [a0cae30, 49d6e0d, 250417d] — Preview-First Verification & Public Samples:** Shipped public-preview motion/examples, attempt-scoped generation receipts, and hardened brief ingestion.

### Pipeline Agents & Editorial Studio Shell
- **2026-09-19 — [763ddfb, 0e2b303] — Living Draft Editorial Studio:** Unified authenticated product navigation under Preact Editorial Studio shell with stage handoffs (D-095).
- **2026-09-13 — [cdac290, f003023] — Traceability Drawer & Reference Pack:** Shipped control room inspector, traceability diagnostics drawer, and Discovery brief research handoff.
- **2026-09-10 — [01e9ed0, 06eb2c0, 22db99c] — Quality Findings & Motion Contracts:** Hardened QualityFindingV2 schemas, image floors, and fluid typography tokens across compiler boundaries (D-090, D-091, D-092).
- **Foundational — [D-002] — Discovery v2 & Pipeline Contracts:** Simplified Discovery to envelope-only JSONB state storage without over-engineered fact-graphs; established bounded 1-3 model call contracts for Content Architect and Visual Design Director.

### Authentication, Ownership & Admin Control Plane
- **2026-09-13..14 — [0e2b303, f74d145, fd127de] — Auth Phases 1–3:** Established Supabase Google OAuth session restore, verified-provider JIT admission, username onboarding, and owner-scoped portfolio sessions.
- **2026-09-14 — [e37e302, 88ba402] — Auth Phase 4:** Implemented audited administrator lifecycle, destructive cleanup/reset, and local admin control console.

---

## Compacted History (Tier 3 — Heavily Compacted Routine Work)

- **2026-09-18..21 — [91f0d18..392277c]** — Cleared release-gate findings, diagnostics name collisions, test module-name collisions, preflight toolchain checks, and Windows temporary lock file fixes across 18 intermediate commits.
- **2026-09-11..16 — [9d2aa0b..df96f4d]** — Stage duration tracking, test database protection, Visual Design Director output recovery, and frontend remediation research across 12 commits.
- **2026-09-08..10 — [90e8349..e99ed55]** — Fluid type tokens, preflight toolchain hardening, undeclared npm import detection, and bounded repair authority across 24 commits.
- **2026-09-05..07 — [7f09506..9fabd58]** — Initial pipeline foundation: candidate preview, durable jobs, PostgreSQL state storage, ModelClient provider abstraction, and mock runner across 35 commits.

---

## Entry Template (For AI Agents — Append to Tier 1)

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — [<commit-sha>] — <files/areas, comma-separated>
<One or two concise sentences: what changed, root cause/rationale, and related ADR references (e.g. D-0XX). Never write verbose debugging narratives or reproduction essays here; put diagnostic logs in docs/deployment/deployment-issues.md.>
```
