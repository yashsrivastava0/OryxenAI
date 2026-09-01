# Code Generator: diagnose-first reliability & preview pass

**Handoff note:** This plan was written and partially executed by Claude Code
(Claude Sonnet 5). That session hit its usage limit mid-diagnosis. Codex (or
whichever agent picks this up next) should read this entire document before
touching anything — it contains not just the plan but the exact live
investigation state, reproduction commands, and a specific unresolved bug
that needs to be finished, not restarted from scratch.

---

## 0. READ THIS FIRST — orientation

Before doing anything else, read, in order:

1. `AGENTS.md` (repo root) — canonical cross-tool project context. Read this
   before anything else, including this file.
2. `DECISIONS.md` — architecture decisions D-001 through D-053. This plan
   references specific decision IDs below; do not act against a decision
   without reading it directly first.
3. `CHANGES.md` — the running change log. Read the top 20-ish entries to see
   the most recent work. As of this handoff, the top entry is the
   `CHANGES.md` backfill commit `8119578` described below.
4. This file, in full, including the "current state at handoff" section
   below — it is not boilerplate, it contains a live bug you need to finish
   diagnosing.

**Multi-agent protocol reminder (from `AGENTS.md`):** log commit-sized work
to `CHANGES.md` using its own template (there's a copy-paste template near
the bottom of that file), log real architectural decisions to `DECISIONS.md`,
never hardcode a model/provider/count that config already owns, and end every
finished unit of work in a task-scoped local git commit — but never push,
amend, rebase, or force anything without being explicitly asked. When you
finish a phase or sub-step, append to `CHANGES.md` and commit, exactly like
the existing entries in that file already do. Identify yourself accurately in
the commit trailer and the `CHANGES.md` entry header (e.g. `Codex (GPT-5 /
OpenAI)`) — do not claim to be Claude Code if you are not.

---

## 1. Current state at handoff — READ CAREFULLY, resume here

This section is the most important part of this document. It describes
exactly what has been done, what is currently running, and a live bug whose
**root cause is now confirmed** but whose **remediation has not yet been
executed**. Do not re-run Phase 0's diagnosis from scratch — read this, then
go straight to executing the numbered remediation in section 1.2 item 8.

### 1.1 What is fully done

- **Phase 1 (CHANGES.md backfill) is DONE.** Commit `8119578` on branch
  `codex/code-generator-control-room` backfilled two missing `CHANGES.md`
  entries (for commits `9b2d28f` and `b4f7daa`, which existed in git history
  but had no changelog entry), fixed a stale `[pending]` SHA tag (now
  `[e5d55f9]`), and ran the file's own compaction procedure (was 261 lines,
  now 227). Nothing further needed here.

### 1.2 Root cause CONFIRMED, remediation NOT YET EXECUTED — resume here

**Phase 0 (live diagnostic run) is IN PROGRESS.** Here is exactly what
happened, in order. Do not repeat these steps blindly — verify current state
first (processes may have been stopped/restarted since), then continue the
investigation from step 8.

1. Confirmed native processes were **already running** (not started by this
   session): API on `127.0.0.1:8000` (PID 38108 at the time, no `--reload`)
   and a second instance on `127.0.0.1:8001` (`--reload`, used for testing
   per commit `8a918f3`'s origin-allowlist fix), preview gateway on
   `127.0.0.1:4174`, at least one worker process (`python -m
   oryxenai.jobs.worker`), and native PostgreSQL on `127.0.0.1:5432`. Docker
   Desktop was **not running** at all (`docker ps` failed to connect) — this
   is pure native mode, driven by `config/app.native.toml`.
2. Verified health directly:
   `http://127.0.0.1:8000/health/live` → `{"status":"alive"}`.
   `http://127.0.0.1:4174/health/live` → `{"status":"ok","service":"preview-gateway"}`.
   So in **this specific environment**, the preview gateway was already up —
   Gap 1 (preview-gateway-off-by-default) did not reproduce here because
   someone had already started it manually. That does not mean Gap 1 is
   fake — it's a real default-topology problem in `compose.yaml` — it just
   didn't block this particular diagnostic run. Still fix it in Phase 2.
3. Called `GET http://127.0.0.1:8000/api/v1/development/code-generator/readiness`.
   Key results: `build_preparation_pack_ready: true`, best/latest pack =
   `15-36-25-08-8acdcb12` (eligible, not expired, expires
   `2026-08-28T10:06:34Z`), `preview_gateway_ready: true`,
   `provider_wire_ready: true`, but **`can_start_latest`/`can_start_best`
   were both `false`**, blocked by `readiness_blockers: ["provider_preflight_required"]`.
   Also note: `profiles.foundation: true` in this response — this confirms
   the Phase 4 finding below that the dead `code_generator_foundation_builder`
   profile is still being preflighted even though it's never actually called.
4. Called `POST http://127.0.0.1:8000/api/v1/development/code-generator/provider-preflight`
   with body `{}`. Result: `{"status":"ready","checked_profiles":["openai_luna"], ...}`.
   **This confirms the OpenAI Luna API key/credentials are currently valid
   and reachable.** (Matches the ad hoc `test_openai_key.py` script's
   expected "credits available" outcome at the repo root.)
5. Called `POST http://127.0.0.1:8000/api/v1/development/code-generator/runs/from-build-preparation`
   with header `Idempotency-Key: 47adbc0e-994c-431c-973c-12f429b65f57` (any
   fresh UUID works; this exact one is now consumed) and body
   `{"pack":"best"}`. **Note: this endpoint requires the `Idempotency-Key`
   header — omitting it returns `400 IDEMPOTENCY_KEY_REQUIRED`.**
   Got HTTP 202 back with:
   - `run_id: f7c2eece-1ab3-4f2b-8ff3-a573fe9c2ece`
   - `job_id: 3193daba-7d28-4dff-bdca-7d516c4e3d90`
   - `status: "queued"`, `coordinator_stage: "plan"`, `auto_advance: true`
   - `selected_pack_receipt.pack_id: "15-36-25-08-8acdcb12"`
   **This is live-generation budget spend #1 of the ~10-run budget** (it
   never actually reached a model call, per below, so arguably it shouldn't
   count against the budget much — use judgment when tracking spend).
6. Polled `GET .../runs/{run_id}` every 15s for 25 minutes. **The status
   never changed from `"queued"`.** `updated_at` never advanced past the
   original `created_at` (`2026-08-26T19:27:37Z`). No worker ever appears to
   have claimed this job.
7. Queried the `background_jobs` table directly (bypassing the API, to get
   ground truth — same technique as the project's own
   `docs/code-generator-architecture/what-was-the-error.md` precedent) using
   a throwaway Python script that reuses the app's own `get_settings()` /
   `get_engine()` (so it never touches `.env` secrets directly — see the
   reusable script in section 1.4 below). Findings:
   - **`job_id: 3193daba-7d28-4dff-bdca-7d516c4e3d90` does not exist as a row
     in `background_jobs` at all.**
   - The single most recent row in the *entire* `background_jobs` table
     (any job kind) has `created_at = 2026-08-26T17:46:06Z` — **over two
     hours before** the API call in step 5, which itself claimed to have
     just created a job.
   - There are 11 historical `job_kind = 'code_generator.plan'` rows, all
     with `execution_lane = 'model-generation'`, spanning
     `2026-08-26T14:20` through `17:46` UTC. **10 succeeded, 1 failed.**
   - **Critically: none of those 10 successful `plan` jobs ever produced a
     follow-on `code_generator.acquire` row.** Auto-chaining
     (`core/coordinator.py::advance_after()`) appears to have silently never
     fired, for every historical run on this machine, not just the new one.
8. **ROOT CAUSE CONFIRMED (2026-08-27, via direct live TCP-connection
   inspection — do not re-derive this, act on it):** the port-8000 API
   process and the worker process were connected to **two entirely
   different PostgreSQL server instances**. Proof, not inference:
   ```
   Get-NetTCPConnection -State Established | Where OwningProcess -eq <api-8000-pid>
     -> 127.0.0.1:5545   (established)
   Get-NetTCPConnection -State Established | Where OwningProcess -eq <worker-pid>
     -> 127.0.0.1:5432   (4 established connections, real pool)
   ```
   Port `5545` is served by `postgres.exe -D ".workspace/postgres-native-5545"
   -p 5545 -h 127.0.0.1` — a distinct, separately-launched PostgreSQL
   instance with its own data directory, started at local time
   `2026-08-26 16:54:14`. **`grep -rn "5545" config/ scripts/ docs/` returns
   zero matches anywhere in the repo.** This is not a misconfigured overlay
   and there is no config file to "fix" — it is a stray, manually-launched
   Postgres instance that some earlier session pointed the port-8000 API
   process at (almost certainly via an ad hoc `DB_PORT_OVERRIDE=5545`
   environment variable set directly in whatever terminal launched it,
   since neither `.env` nor any checked-in `config/*.toml` contains this
   value). This single finding fully explains the stuck run from steps 5-7
   above: the API wrote the new run+job to the 5545 database; the worker,
   polling 5432, never saw it — not a code bug, an environment/process
   mismatch.

   **This does NOT fully explain finding #7's second half** (10 historical
   `code_generator.plan` successes, already correctly sitting in the 5432
   database where the worker *can* see them, never auto-chaining to
   `acquire`) — that remains independently attributable to the `b4f7daa`
   worker-staleness hypothesis below and must be checked separately, not
   assumed fixed by the DB realignment alone.

   **Exact remediation — do this precisely, don't improvise:**
   1. **Inventory every related process before touching anything.** There
      are currently *two* API processes (port 8000, no `--reload`; port
      8001, `--reload`) and *two* worker processes running simultaneously
      (one near-idle, one with the real DB pool). Get PIDs and exact
      command lines for all of them:
      ```powershell
      Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "uvicorn oryxenai.main|jobs.worker|preview.gateway" } |
        Select-Object ProcessId, CreationDate, CommandLine | Format-Table -Wrap
      ```
   2. **Check for in-flight work before stopping anything** — query both
      databases (5545 and 5432) for any `background_jobs` row with
      `status='running'` right now; if one exists, let it finish or fail
      naturally before killing its owning process.
      ```powershell
      # repeat once with OryxenAI_CONFIG_OVERLAY=config/app.native.toml (port 5432)
      # and once with a throwaway override pointed at port 5545 if you need
      # to inspect what's stranded there before abandoning it.
      ```
   3. **Stop every stray process** (both API instances, both worker
      instances, and the port-5545 `postgres.exe`) rather than layering a
      freshly-started correct process on top of old ambiguous ones. Do not
      leave two API instances or two workers running afterward — pick one
      of each, matching what `scripts\run-native.ps1` launches.
   4. **Start fresh, only via the canonical script**, so there is no
      ambient shell environment variable that could reintroduce a stray
      override:
      ```powershell
      scripts\run-native.ps1 migrate
      scripts\run-native.ps1 api      # separate terminal/background process
      scripts\run-native.ps1 worker   # separate terminal/background process
      scripts\run-native.ps1 preview  # separate terminal/background process
      ```
   5. **Re-verify alignment the same way it was proven broken** — confirm
      the new API process's established DB connection is to `5432`, not
      `5545`, before creating any new run.
   6. **Abandon the original stuck run/job** (`f7c2eece-1ab3-4f2b-8ff3-a573fe9c2ece`
      / `3193daba-7d28-4dff-bdca-7d516c4e3d90`) — it lives entirely inside
      the orphaned 5545 database, which nothing will query again once
      realignment is done. Do not try to "recover" or retry that specific
      run_id; start a brand new run (new Idempotency-Key) against the
      now-correctly-aligned stack for validation.
   7. **Separately verify the `b4f7daa` worker-staleness hypothesis, even
      after the DB fix**, since it's a distinct bug from the DB split:
      compare the freshly-restarted worker process's start time against
      `git log -1 --format=%cI b4f7daa` (its commit time). Since the new
      worker was just started fresh in step 4, it will trivially be running
      current code — but confirm this explicitly and say so in the
      `CHANGES.md` entry, rather than leaving it ambiguous which of the two
      fixes (DB realignment vs. code freshness) was actually load-bearing
      for any given symptom. If a *third* stray worker process turns out to
      still be running old code and wins a job-claim race against the fresh
      one, that would reintroduce nondeterministic behavior — hence step 3's
      "stop every stray process," not just "start a new correct one."
   8. **Write a `CHANGES.md` entry for this finding specifically** — it
      deserves its own entry (matching the detail level of the existing
      `2a6fb12`/`60a41a3` entry as a template), not just a generic "phase
      complete" note, since it fully explains the "issues keep coming up"
      symptom pattern and future sessions need to be able to find this
      root cause without re-deriving it from scratch.

9. **Superseded hypothesis (kept for record — the mechanism above is more
   precise than this, but the underlying suspicion about `b4f7daa` staleness
   is still independently worth checking per step 7 above):**
   - The currently-running worker process(es) were started at local time
     `2026-08-26 19:44:10` (= `2026-08-26T14:14:10Z`).
   - Commit `b4f7daa` ("skip authorization context for development-mode
     advance" — the exact fix for `advance_after()` silently failing to
     enqueue the next stage for detached/development runs) has an author
     timestamp of `2026-08-26 22:52:44 +05:30` = **`2026-08-26T17:22:44Z`**
     — **three hours after** the worker process started.
   - Python worker processes do not hot-reload source files. If the
     currently-running worker process loaded its code before `b4f7daa` was
     written to disk, it is still executing the **pre-fix, buggy** version
     of `advance_after()` from memory — which would fully explain finding
     #7 (every historical `plan` success failing to chain to `acquire`).
   - **This hypothesis does NOT explain finding #6/7's dangling `job_id`**
     (a job the API claims to have created but that never landed in the
     `background_jobs` table at all — vs. the 11 historical jobs, which DID
     land in the table and ran to completion). That is a separate, more
     acute question: is the live API process (port 8000, PID 38108 at
     inspection time) writing to a *different* database than the
     `config/app.native.toml` overlay my diagnostic script used? Two facts
     cut against a full database mismatch: (a) port `5544` (what the
     *default*, non-native `config/app.toml` points at) has **no listener
     at all** right now since Docker Desktop is down, so the API couldn't
     be functioning against that config; (b) the API's health/readiness/
     preflight/run-creation calls all worked and returned plausible data.
     But a mismatch on database *name* (not host/port) on the same
     `127.0.0.1:5432` server, or some other subtler config/env difference
     between however that specific API process was originally launched and
     what `config/app.native.toml` specifies, has **not been ruled out**.

### 1.3 Resolution status — root cause is CONFIRMED, do not re-investigate

**This section originally sent the reader off to re-derive the root cause.
That derivation is now done — see item 8 in section 1.2 above ("ROOT CAUSE
CONFIRMED") for the full mechanism and the exact numbered remediation
steps.** Do not re-run the "is it a DB mismatch or a job-creation bug"
investigation below from scratch — it's answered: **it's a DB mismatch**
(port-8000 API → stray Postgres on 5545; worker → correct Postgres on
5432), proven via direct established-TCP-connection inspection, not
inferred. Go to section 1.2 item 8's numbered remediation list and execute
it in order.

The diagnostic script below is kept because it's still useful for
**re-verifying** the fix after remediation (confirm the run row now exists
where expected, confirm no stray `5545` connection remains) — use it that
way, not to re-open the "which hypothesis is true" question.

1. **Re-check current environment state first** — processes may have been
   stopped or restarted since this was written; the exact PIDs above will
   have changed. Re-run the inventory command from section 1.2 item 8, step
   1, and the established-connection check from step 5, before assuming
   anything about current state.

2. **After remediation, use this script to confirm the fix worked** — point
   it at whatever `run_id`/`job_id` your fresh (post-remediation) run
   produced, not the old orphaned ones. If it finds both rows cleanly, and
   `current_database()`/`inet_server_port()` report `5432`, the fix is
   verified.

   Use this script (save it anywhere convenient, e.g.
   `scripts/diagnostics/check_codegen_run.py` — it's fine to leave this
   checked in under `scripts/` if useful, or delete it once the
   investigation is closed):

   ```python
   import asyncio
   import os
   import sys

   os.environ.setdefault("OryxenAI_CONFIG_OVERLAY", "config/app.native.toml")

   from sqlalchemy import text
   from oryxenai.core.settings import get_settings
   from oryxenai.db.session import get_engine

   RUN_ID = sys.argv[1] if len(sys.argv) > 1 else "f7c2eece-1ab3-4f2b-8ff3-a573fe9c2ece"
   JOB_ID = sys.argv[2] if len(sys.argv) > 2 else "3193daba-7d28-4dff-bdca-7d516c4e3d90"

   async def main():
       settings = get_settings()
       engine = get_engine(settings)
       async with engine.connect() as conn:
           print("=== code_generator_runs row for RUN_ID ===")
           r = await conn.execute(
               text("SELECT id, status, coordinator_stage, background_job_id, created_at, updated_at "
                    "FROM code_generator_runs WHERE id = :rid"),
               {"rid": RUN_ID},
           )
           row = r.mappings().first()
           print(dict(row) if row else "NO ROW FOUND")

           print("\n=== background_jobs row for JOB_ID ===")
           r2 = await conn.execute(
               text("SELECT id, job_kind, status, locked_by, heartbeat_at, execution_lane, "
                    "created_at, updated_at, error_payload FROM background_jobs WHERE id = :jid"),
               {"jid": JOB_ID},
           )
           row2 = r2.mappings().first()
           print(dict(row2) if row2 else "NO ROW FOUND")

           print("\n=== most recent 5 background_jobs rows, any kind ===")
           r3 = await conn.execute(
               text("SELECT id, job_kind, status, execution_lane, created_at, updated_at "
                    "FROM background_jobs ORDER BY created_at DESC LIMIT 5")
           )
           for row3 in r3.mappings():
               print(dict(row3))

           print("\n=== db server identity/time ===")
           r4 = await conn.execute(text("SELECT current_database(), inet_server_addr(), inet_server_port(), now()"))
           print(r4.first())
       await engine.dispose()

   asyncio.run(main())
   ```

   Run it with:
   ```powershell
   $env:OryxenAI_CONFIG_OVERLAY = "config/app.native.toml"
   uv run python "scripts\diagnostics\check_codegen_run.py"
   ```

3. **Restart cleanly using the canonical script** — this is now step 3-4 of
   section 1.2 item 8's remediation list, not an open choice. Stop every
   stray process first (both API instances, both worker instances, the
   port-5545 Postgres), then start exactly one of each via
   `scripts\run-native.ps1`. Check `git status --short` and query for any
   `status='running'` job first (section 1.2 item 8, step 2) so you don't
   interrupt real in-flight work. The "two API instances is an established
   pattern per `8a918f3`" note from the original draft of this section
   still applies to *testing on an alternate port deliberately* — it does
   not justify leaving a stray, wrongly-configured extra instance running
   indifferently. Know which processes you have running and why.

4. **This costs zero live-generation budget** — realigning processes and
   confirming via TCP-connection/DB inspection involves no model calls.
   Only spend a fresh run (new Idempotency-Key) once remediation is
   verified via step 2's script above. That run is what closes out Phase 0
   and moves into Phase 1b for whatever else turns up as it progresses
   through acquisition, generation, and verification — including
   independently confirming the `b4f7daa` worker-freshness check (section
   1.2 item 8, step 7).

### 1.4 Historical `code_generator.plan` run IDs (for reference, already used)

These 11 job rows already exist in `background_jobs` (all `job_kind =
'code_generator.plan'`, all `execution_lane = 'model-generation'`) — useful
if you want to inspect what a successful plan output actually looks like
without spending new budget (query `code_generator_runs` joined by whatever
`background_job_id` matches, or check `result`/`payload` columns on these
job rows directly):

10 succeeded between `2026-08-26T14:20Z` and `17:46Z`; 1 failed at
`17:03:57Z`–`17:05:17Z`. Exact job IDs were printed during the live session
but not preserved verbatim in this document — re-run the query in section
1.3's script (drop the `WHERE` clause, just `ORDER BY created_at DESC`) to
get them fresh if needed.

---

## 2. Context (why this plan exists)

The ask was "drastic changes" to the Code Generator agent because portfolio
generation keeps hitting issues, with full authority granted to change,
simplify, or remove anything — including the architecture — to guarantee
three things: (1) generation never errors, (2) generated portfolios never
error (routes, navigation, runtime all work), (3) generated portfolios look
visually advanced and distinct per profession, never generic AI-template
output. On top of that, a Lovable/Replit/emergent.sh-style live preview is
wanted, working the same way locally and once actually deployed.

Deep exploration (three parallel research passes over the implementation,
the architecture docs, and `DECISIONS.md`/`CHANGES.md`, followed by direct
firsthand verification of the highest-stakes claims, then an independent
planning pass that re-verified everything against the live code, then the
live diagnostic run documented in section 1) converged on one central
finding that reframes the task: **this is not a broken or naively-built
system.** It is 52 files deep in `src/oryxenai/agents/code_generator/core/`,
backed by 53 recorded architecture decisions (`DECISIONS.md` D-001–D-053),
with a real deterministic "anti-AI-slop" static auditor, typed
design-token/blueprint contracts, Playwright multi-viewport DOM/geometry
verification, and a crash-safe atomic preview-promotion system — all already
built specifically to guarantee the same three things being asked for now.
Vision-model/screenshot-based QA was tried and explicitly rejected **three
times** (D-014→D-015, reaffirmed D-032/D-034/D-036/D-041) because it didn't
improve quality. Per-portfolio containers were explicitly rejected (D-039).
A framework rewrite (LangChain/CrewAI-style) was rejected project-wide
(D-001). **None of these should be reopened without new evidence.**

What actually explains "issues keep coming up": the user-facing surface for
exactly this workflow — the no-auth "detached generation control room"
(`/code-generator-development`, commit `7c44add`) — was built the day before
this request and needed **four same-day follow-up fixes** already (and, per
section 1's live investigation, likely a fifth: a stale worker process not
having picked up the latest fix). The untracked
`Input-Output-Of-Engine/resume.md` (a real resume, Docker-mounted read-only)
plus fresh Aug-25 Content-Architect/Visual-Design-Director outputs and a
`prebuild-output/` Build Preparation run are direct evidence someone was
actively trying to generate a real portfolio through this brand-new surface
and hitting a cascade of real, specific bugs — the same pattern as every
entry already in `CHANGES.md` (rate-limit backoff, credit-exhaustion
wording, ID drift, empty worker logs, over-strict validators, and now an
auth-context bug blocking auto-chaining). **That is a diagnose-and-fix
problem, not a rewrite-the-architecture problem.**

The one concrete, confirmed product gap is the live preview: it is fully
built (`src/oryxenai/preview/*`, `src/oryxenai/storage/preview.py`) but not
reliably reachable by default. The user has explicitly chosen — after seeing
the tradeoff — to keep the existing **verified-only preview + semantic
progress bar** design (never Lovable-style live-streaming of broken/WIP
code), specifically because it is both the already-built option and the
simpler one, and because the user twice emphasized not wanting complexity
added to this agent's architecture. **Do not build a live-WIP-streaming
preview. This was explicitly decided against.**

**Intended outcome of this plan:** verify the real, current failure modes
live (not guess), fix them at the same root-cause granularity the project's
own history already uses, make the existing preview system actually reach
users by default, and only touch visual-quality prompts/contracts if a real
live run shows they need it — while leaving the sound parts of this
architecture alone.

---

## 3. Hard constraints — do NOT reopen these without new evidence

- [ ] **No vision-model or screenshot-based quality gating.** Tried and
      explicitly rejected three times (D-014→D-015, D-032, D-034, D-036,
      D-041). Do not propose adding a vision model "to check if the output
      looks good."
- [ ] **No per-portfolio containers/deployments.** Docker packages only the
      OryxenAI backend (D-039). The generated portfolio is a source tree +
      static `dist/`, served through the shared preview gateway — never its
      own container.
- [ ] **No live-streaming of in-progress/broken generated code into the
      preview.** `docs/code-generator-architecture/live-preview-and-deployment.md`
      explicitly rejects this ("would add a second meaning of 'preview' and
      weaken the promoted-only invariant"); the user confirmed this choice
      explicitly, prioritizing simplicity over Lovable/Replit-style
      spectacle. The only preview surface is the verified/promoted one, plus
      a semantic progress indicator (planning → generating → building →
      verifying → promoted) — never raw streamed code or a broken mid-build
      site.
- [ ] **No caching of component-registry/discovery responses.** Explicit
      rejection at D-029. (Image caching at D-031, 24h TTL for
      Pexels/Pixabay, is unrelated and correct as-is — leave it alone.)
- [ ] **Do not switch Code Generator's model off OpenAI `gpt-5.6-luna`**
      (`config/models.toml [profiles.code_generator_*]`). The user
      explicitly asked for Luna here, even though every other agent
      (Discovery/Content Architect/Visual Design Director/Build
      Preparation) now defaults to Anthropic Claude Sonnet 5 (D-040). This
      divergence is intentional — leave it.
- [ ] **No agent framework** (LangChain/LangGraph/CrewAI/AutoGen/etc.) —
      D-001, project-wide.
- [ ] **Do not hardcode generic visual templates/palettes.** Explicitly and
      repeatedly rejected (D-030, D-034). Route/page counts are correctly
      never hardcoded today — they're driven entirely by the upstream
      Content Architect/Visual Design Director/Build Preparation contract;
      do not change that. **Hardcoding scaffolding/tech stack** (React +
      Vite + TypeScript, no Tailwind, custom dependency-free router, the
      `scaffolds/react-vite-v1/` tree) **is explicitly fine** per the user's
      own words ("project scan folder, project structure, tech stack... we
      can hardcode") — leave the scaffold's tech-stack choice alone; only
      generic *visual design output* must never be hardcoded/generic.
- [ ] **Never** run destructive git operations (force-push, `reset --hard`,
      `checkout --` over uncommitted work) without explicit authorization.
      Never use `git add -A` / `git add .` in this working tree — there are
      pre-existing modified files that are **not yours**: `Input-Output-Of-Engine/*.md`,
      `docs/architecture.md` were already modified before this plan started
      and belong to other work. Stage only files/hunks you actually touched
      for the task at hand. Run `git status --short` before every commit and
      review `git diff --cached --stat`.
- [ ] **Never delete** `prebuild-output/`, `Input-Output-Of-Engine/resume.md`,
      or the two ad hoc scripts (`test_anthropic_key.py`, `test_openai_key.py`)
      without an explicit decision — see Phase 4 below for the narrow,
      already-scoped exception (only remove things that section names
      exactly, nothing more).
- [ ] **Never silently substitute a mock/fixture response for a live model
      call** when the user has asked for live/real generation. Per
      `AGENTS.md`: execute the configured live LLM/API workflow by default.

---

## 4. Live-generation budget

The user authorized roughly **10 full live end-to-end Code Generator runs**
against the real Luna API for this work (no per-run call-count cap within
each run — only the *count of full runs* is budgeted). Spend it
deliberately:

- [ ] 1 run already spent getting stuck at "queued" (section 1.2, step 5) —
      arguably shouldn't count heavily since it never reached a model call,
      but be aware of it.
- [ ] Budget ~1-2 more runs to get a **first successful full pipeline run**
      once the section 1.3 investigation is resolved.
- [ ] Budget ~1 run per batch of related fixes after that (Phase 1b), not
      one run per individual fix.
- [ ] Only spend budget on Phase 3 (visual-quality) evidence-gathering if a
      real completed run's output looks generic to a human. Do not spend
      runs manufacturing extra profession fixtures "to prove"
      cross-profession distinctiveness unless evidence already looks
      concerning — that's a separate, explicit scope decision, not
      something to assume into this work.
- [ ] Track how many runs you've spent as you go (add a line to this
      section or to `CHANGES.md` each time) so the next agent, if there is
      one, knows how much budget remains.

---

## 5. Phase checklist (high level)

- [x] **Phase 1** — Restore `CHANGES.md` session-continuity history. **DONE**
      (commit `8119578`).
- [ ] **Phase 0** — Live diagnostic run. **IN PROGRESS** — resume at section
      1.3 above. Do not skip this or assume you know what's broken; finish
      diagnosing first.
- [ ] **Phase 1b** — Fix whatever Phase 0 finds, using the prioritized
      playbook below.
- [ ] **Phase 2** — Close the preview-reliability gap (concrete fixes
      already identified, listed below).
- [ ] **Phase 3** — Visual-quality confidence pass. **Evidence-gated** — do
      not start this until Phase 0/1b produce a real rendered site to look
      at.
- [ ] **Phase 4** — Cleanup (dead code removal, doc drift fixes). Do this
      last; it has no functional dependency on the other phases.

Sequencing: **Phase 1 (done) → Phase 0 (resume) → Phase 1b → Phase 2 → Phase
3 (if warranted) → Phase 4 (last).**

Each phase should end with: a `CHANGES.md` entry (following its own
template, running the compaction check if the file passes ~250 lines again),
a `DECISIONS.md` entry **only** for the Phase 2 compose-topology change
(everything else is a routine fix, not a new architectural decision), and a
task-scoped local git commit. `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, and `uv run mypy src` should all be clean
before considering any source-touching phase done.

---

## 6. Phase 1b — Fix what Phase 0 finds

Follow the project's own established pattern: typed diagnostic → root cause
→ targeted fix → `CHANGES.md` entry → commit. Use this prioritized
failure-class checklist (ranked by how often each exact shape has already
occurred in this project's own history) so you have a ready playbook instead
of starting from zero:

- [ ] **1. Deterministic validator over-strictness** (highest-frequency
      class — `9b2d28f`'s exact-set-vs-subset font check is the template).
      Any validator in `core/typescript_ast_audit.py`,
      `core/generation_contract.py`, or `core/design_realization.py`
      asserting *exact* equality against model output shape rather than
      subset/superset tolerance is a candidate — grep for `==` comparisons
      against model-derived collections first.
- [ ] **2. Detached/dev-mode plumbing bugs in shared session machinery**
      (`b4f7daa`'s class — **and the current section-1 investigation may be
      exactly this class again**). Check `core/coordinator.py`'s
      `advance_after()` and anywhere job-enqueue guards are shared between
      session-bound and development-run code paths. If section 1.3 confirms
      the worker just needed a restart to pick up `b4f7daa`, also check
      whether there's a *second*, still-unfixed instance of the same
      version-0-authorization-context guard tripping somewhere else in the
      chain (e.g. does `acquire → generate` or `generate → verify`
      auto-chaining share the same code path as `plan → acquire`? If so it
      should already be fixed by the same commit; if there's a separate
      code path, it may need the identical fix applied there too).
- [ ] **3. Provider error-message classification gaps** (`5d6886a`'s class —
      new wording not in the credit/error marker tables). Check the
      classification tables (search for `_CREDIT_MARKERS` or similar in
      `agents/shared/providers/`) before assuming it's a pipeline bug.
- [ ] **4. Cross-agent handoff ID/role drift** (`2a6fb12`, `8e93fc2`'s
      class) — less likely here since Phase 0 reuses an existing Build
      Preparation mirror rather than re-running Content Architect/Visual
      Design Director, but watch for it if upstream stages get re-run
      later.
- [ ] **5. Un-backed-off registry/provider rate limits** (`2f9403b`'s
      class). Any registry/provider touch that doesn't share the existing
      rate-limit-memory pattern (`_PROVIDER_RATE_STATE` or equivalent).
- [ ] **6. Logging blind spots** (`60a41a3`'s class) — if a diagnosis stalls
      because a log stream is unexpectedly empty, confirm
      `configure_logging()` is actually called in that entrypoint first.
- [ ] **7. Secret/credential redaction gaps** (`e5d55f9`'s class) — any
      newly surfaced error message reaching the control room UI must go
      through the same redaction path that fix added.
- [ ] **8. Gap 1's preview-reachability symptom** — the actual fix belongs
      in Phase 2, not a one-off patch here.
- [ ] **9. Local toolchain/environment confounds** (missing Playwright
      browser install, stale competing worker process, dependency drift) —
      rule these out explicitly, per
      `docs/code-generator-architecture/what-was-the-error.md`'s precedent;
      don't miscount them as generator defects. **The current stuck-job
      investigation in section 1 may itself turn out to be exactly this
      category** (stale worker process) — confirm before writing it up as a
      "core pipeline bug."

---

## 7. Phase 2 — Close the preview-reliability gap

**Confirmed root cause** (verified directly against the code, not assumed):
`PreviewPromoter`'s URL is built from `preview_base_url`
(`config/app.toml` → `http://127.0.0.1:4174/preview`), and
`preview_public_readback_required = false` locally means **promotion
succeeds and reports "Verified preview promoted" even when nothing is
listening on port 4174** — the run doesn't fail or fall back, it silently
produces an iframe `src` nobody can load. This is compounded by
`src/oryxenai/agents/code_generator/core/development_service.py`'s
`preview_gateway_ready` check (~line 150) only verifying that
`preview_host`/`preview_port` are non-empty config values — never an actual
reachability probe — so the control room's own readiness banner can say
"ready" while the gateway process doesn't exist. This is a fully
self-consistent explanation for "issues keep coming up" around preview, even
though in the specific session that wrote this plan, the gateway happened to
already be running (section 1.2, step 2).

Concrete fixes:

- [ ] **1. `compose.yaml`** — remove `profiles: ["codegen"]` (line ~101)
      from the `preview-gateway` service (lines 97-121). It already has
      `restart: unless-stopped`, a real healthcheck, and depends only on
      `worker: condition: service_started`; nothing about it needs opt-in
      gating now that the control room is the primary way this system gets
      exercised. `docker compose up` then starts
      postgres → migrate → app + worker + preview-gateway by default. Leave
      `build-validation` (line ~127) profile-gated — that one is genuinely
      a separate, opt-in one-off validation tool.
      **This changes default Docker topology (5 services instead of 4) —
      log it as a `DECISIONS.md` entry, not just a `CHANGES.md` fix**,
      since it's a real architectural choice per this project's own logging
      protocol. Use the template near the top of `DECISIONS.md` and give it
      the next sequential `D-0XX` number (check the current highest number
      first — it may have moved past D-053 by the time you do this).
- [ ] **2. `src/oryxenai/agents/code_generator/core/development_service.py`**
      (`preview_gateway_ready`, ~line 150) — replace the config-presence
      check with a short-timeout (1-2s) HTTP probe against the gateway's
      own `/health/live` (already exposed by `create_preview_app` in
      `src/oryxenai/preview/gateway.py`), and distinguish "not configured"
      from "configured but unreachable" in the blocker text
      `code-generator-development.js` already renders. This turns the
      failure mode from "silently looks broken" into "tells you why before
      you click Generate."

      **Important detail — do not probe `preview_base_url` directly, add a
      distinct `preview_health_url` config value instead.** Verified
      directly: in `config/app.docker.toml`, `preview_base_url =
      "http://localhost:4174/preview"` and `preview_host = "0.0.0.0"`.
      Neither is a valid target for the `app`/`worker` container to
      *reach* the `preview-gateway` container from inside Docker's network
      — `localhost` inside a container means that container itself, and
      `0.0.0.0` is a bind address, never a dial target. A probe using
      either would always fail inside Docker even when the gateway is
      genuinely healthy, defeating the whole point of this fix. Add a
      separate `preview_health_url` field: for native/local configs it can
      default to being derived from the existing `preview_host`/
      `preview_port` (already `127.0.0.1:4174` there, which *is* valid),
      but **`config/app.docker.toml` must explicitly set it to
      `http://preview-gateway:4174/health/live`** — Docker Compose's
      service-name DNS, resolvable container-to-container regardless of
      published host ports. Document this reasoning in a one-line comment
      next to the new field so it isn't "fixed" back to `localhost` by a
      future edit that doesn't know why it's different.
- [ ] **3. Native (non-Docker) dev path** — `scripts\run-native.ps1`'s
      `preview` case already works; the gap is that nothing tells a
      developer they need `migrate` + three terminals (`api`, `worker`,
      `preview`) first. Add a `dev` case to `scripts\run-native.ps1` that
      `Start-Process`-launches `api`, `worker`, and `preview` as background
      processes from one invocation, reusing the existing switch-case
      bodies — no new abstraction, just composing what's already there.
      Also add the ordering note to `AGENTS.md`'s canonical local commands
      section.
- [ ] **4. Do not** flip `preview_public_readback_required` to `true`
      locally — that would make local generation *fail* (block promotion)
      whenever the gateway isn't running, which hurts dev iteration speed
      more than it helps. The fix is making the gateway actually run by
      default (above) plus an honest readiness probe, not making local
      promotion stricter.
- [ ] **5. Docker preview contract — DECIDED, implement exactly this** (no
      further investigation needed, this was verified directly against
      `compose.yaml` and `docs/run/run.md`): free-tier vs. paid hosting
      needs no code difference — `docs/code-generator-architecture/free-host-deployment.md`
      is accurate and already covers this via `preview_storage_provider`
      flipping `local_fs` → `artifact_storage` (R2-backed `S3PreviewStorage`),
      pure config per the project's config-driven-policy rule. But there
      are **two different Docker overlays that must NOT be treated the
      same**:
      - **`config/app.docker.toml`** — the real hosted/production-like
        overlay. Every service in the default `compose.yaml` stack sets
        `OryxenAI_CONFIG_OVERLAY: config/app.docker.toml` (`migrate`, `app`,
        `worker`, `preview-gateway`, `build-validation`). It already
        correctly sets `preview_storage_provider = "artifact_storage"` but
        is **currently missing** `preview_public_readback_required = true`
        — confirmed by direct inspection it silently inherits `false` from
        base `config/app.toml`, contradicting that file's own comment
        ("Hosted Docker profiles turn this on so promotion proves the
        URL"). **Add `preview_public_readback_required = true` to this
        file's `[code_generator_verification]` section.** This makes
        promotion fail-closed in hosted/production contexts: a candidate
        isn't `ready` until a real HTTP round-trip proves the public
        preview URL is actually reachable — matching this project's
        general "fail closed in production/attached contexts" pattern
        (e.g. D-050) while staying lenient for local dev iteration speed.
      - **`config/app.docker.codegen-run.toml`** — a *different*, isolated
        Docker overlay used only by the standalone Code Generator
        dev/test harness (its own separate Compose project
        `-p oryxenai-codegen`, its own database, per
        `docs/run/run.md:373-383`). It uses `preview_storage_provider =
        "local_fs"`, not hosted storage, and alternate port-8001-flavored
        origins — this is Docker-flavored *local* iteration, not a hosted
        deployment. **Leave `preview_public_readback_required` unset
        (i.e. `false`) here** — do not add the strict readback requirement
        to this file.
- [ ] **6. Verify the fix**: remove any manual workaround (starting
      processes by hand) entirely, run `docker compose up` (or a fresh
      native start following the new `dev` script path) from a clean state,
      and confirm the control room reaches a real, loadable preview without
      any manual intervention. Open the actual preview URL in a plain
      browser tab (not just the iframe) to confirm it's genuinely reachable.

---

## 8. Phase 3 — Visual-quality confidence (evidence-gated — do NOT pre-emptively touch)

Only act on this phase if a real completed run's rendered output looks
generic to a human. **If it looks good: say so, stop, and do not modify
prompts or thresholds "just in case."** This is consistent with not
rewriting what verification shows already works — a lesson already learned
once on this project (the Discovery agent was assumed to be "low-grade" and
turned out to be well-built; the real problems were narrower and
environmental).

If real evidence of generic output shows up, the tightening surface is
already precisely scoped in
`src/oryxenai/agents/code_generator/core/typescript_ast_audit.py`:

- [ ] `_audit_v4_anti_slop` (~line 638) requires `repeated >= 3` identical
      section shells, `>= 3` unauthorized gradient/glass/pill/blob
      occurrences, near-total centering
      (`centered >= max(3, len(sections)-1)`), or near-total fade-reveal
      motion before flagging anything — plus `_GENERIC_CLASS_RE`
      (`.card/.surface/.grid/.reveal/.stagger`) and
      `SOURCE_CSS_TOKEN_FALLBACK` (rejects `var()` fallback values).
- [ ] The smallest targeted move is tightening **one** specific threshold
      (e.g. `repeated >= 3` → `>= 2`, since 3 identical section shells is
      already a lot on a small site) or adding **one** narrow new check in
      the same function — **not** a prompt rewrite across
      `director.md`/`planner.md`/`route_batch.md`/`route_compose.md`.
- [ ] Only escalate to prompt changes if **both** the static audit and the
      LLM-judge integration review pass while a human still sees generic
      output — that would mean the checks aren't measuring the right thing,
      not that the model needs different instructions.
- [ ] If prompt/contract changes do end up warranted, they're a good
      candidate for an independent second-model review before locking in
      (get a second opinion from a different model/tool before committing),
      given this project's own past practice of doing exactly that before
      major prompt/architecture changes.

**Honest caveat:** the only fixture on hand
(`Input-Output-Of-Engine/resume.md`) is a single UI/UX Designer profile —
one good run against it is real evidence the *mechanism* works, not evidence
of "distinctly different across professions" specifically. Deciding whether
to spend more of the live-generation budget manufacturing other profession
fixtures to test that claim is a separate, explicit call to make only if
Phase 0/1b's result looks concerning.

---

## 9. Phase 4 — Cleanup (last, no functional dependency on other phases)

### 9.1 Dead foundation-builder model machinery

Confirmed genuinely unreachable (the foundation work unit has been 100%
deterministic since V3; `core/generation_orchestrator.py` ~line 732 has a
comment explicitly stating this boundary — and section 1.2's live readiness
check confirmed `profiles.foundation: true` is still being preflighted even
though it's dead), but scope the removal precisely:

- [ ] Remove: `config/models.toml` `[profiles.code_generator_foundation_builder]`
      + its `.capabilities` block, and its `[routing.engine_profiles]`
      entry.
- [ ] Remove: the `"foundation"` entries from the profile/prompt-file lookup
      dicts in `core/generation_prompt_builder.py`, and the now-orphaned
      `prompts/foundation.md`.
- [ ] Remove: `foundation_profile` from the preflight-list construction in
      `service.py` and `development_service.py`.
- [ ] Re-verify `tests/integration/test_code_generator_generation_worker.py`
      (~line 129) still passes — it references `role: "foundation_builder"`
      on a `RequestOrigin`, which is a **different, still-live** provenance
      tag for emergent resource-acquisition requests, not the dead
      model-call profile. **Do not delete this test reference.**
- [ ] **Do not remove**: the `WorkUnit(kind="foundation", ...)` compiler
      path in `work_graph_compiler.py`,
      `DevelopmentRunStatus.GENERATING_FOUNDATION`, the deterministic
      branch in `generation_orchestrator.py` (~lines 732-777), or the
      `"foundation_builder"` literal in `RequestOrigin.role`
      (`development_schemas.py`) — all of these are real and live.
- [ ] Run
      `grep -rn "foundation_profile\|code_generator_foundation_builder\|foundation\.md" src/ config/`
      immediately before deleting anything, as a final confirmation check.
- [ ] Treat this as its own small, isolated commit (it touches 6+ files) so
      it's easy to revert independently if the pre-delete grep turns up
      something unexpected.

### 9.2 Doc drift

- [ ] `docs/code-generator-architecture/v2-production-architecture.md` —
      still framed around V2/pack-v3 concepts with no V4/pack-v4 mention;
      add a banner pointing at D-034/D-041 as the current contract, or
      refresh it.
- [ ] `docs/code-generator-architecture/live-preview-and-deployment.md` —
      describes a wildcard-DNS/dedicated-registrable-domain subdomain
      topology that was **never built**; the real `PreviewGateway` is a
      simpler, working, single-origin path-prefixed router
      (`/preview/{host}/{path}`). **Correct the doc to describe what's
      actually built** rather than leaving it describing a more complex
      design nobody should build next, given the explicit "nothing
      complicated" direction from the user.
      (`free-host-deployment.md` and `preview-quality-and-evaluation.md`
      were verified accurate — leave them alone.)

### 9.3 Root-level ad hoc scripts

- [ ] `test_anthropic_key.py`/`test_openai_key.py` are untracked diagnostic
      scripts at repo root. **Do not delete unilaterally.** Flag for an
      explicit keep/move-to-`scripts/`/delete decision once Phase 0/1b
      confirms provider credentials are stable through this work. If you
      end up using them again during this investigation, that's a good sign
      they should move to `scripts/` rather than be deleted.

---

## 10. Verification / definition of done

- [ ] `uv run pytest` after every phase — especially
      `tests/integration/test_code_generator_generation_worker.py`,
      `tests/integration/test_code_generator_verification_worker.py`,
      `tests/api/test_code_generator_development_routes.py`, and the
      `tests/frontend/code_generator_development*.test.mjs` suite — before
      considering that phase done.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`,
      `uv run mypy src` after any source edit (Phase 1b, Phase 2, Phase 4).
- [ ] **Live proof over passing tests for the actual goals.** A completed
      run (and any Phase 1b/2 re-verification runs) must show, firsthand: a
      real generation reaching `ready`, a real preview loading in a plain
      browser tab (not just the iframe), and a human judgment call on
      whether the output looks visually distinctive rather than generic —
      this is the same standard applied to this project's own past
      live-verification passes (see `docs/code-generator-architecture/what-was-the-error.md`
      for the precedent of what "proven" looks like here).
- [ ] After Phase 2, confirm the fix by removing any manual workaround
      entirely and re-running from a clean `docker compose up` (or the new
      native `dev` script) to prove the default path now works unattended.
- [ ] Before declaring this plan complete, re-read section 1 of this file
      and confirm every item there has either been resolved or explicitly
      superseded by new findings — do not leave the stuck-job mystery
      unresolved while moving on to other phases.




 # Code Generator Reliability and Preview Pass                                                         
                                                                                                        
  ## Summary                                                                                            
                                                                                                        
  The updated PLAN.MD and live evidence establish two separate causes:                                  
                                                                                                        
  - The port-8000 API wrote the stuck run to a rogue PostgreSQL instance on port 5545.                  
  - The worker was connected to the canonical PostgreSQL instance on port 5432, so it could never see   
    that run.                                                                                           
                                                                                                        
  - A second, independent issue remains: the worker was started before commit b4f7daa, so its in-       
    memory code may predate the detached-mode auto-advance fix.                                         
                                                                                                        
  - 5545 appears nowhere in checked-in configuration, scripts, or documentation. This is an             
    operational process problem, not a repository configuration problem.                                
                                                                                                        
  The implementation will first cleanly realign the running processes, validate a fresh run, and only   
  change application code when a failure reproduces after that clean restart.                           
                                                                                                        
  The already-completed Phase 1 changelog backfill at commit 8119578 remains complete.                  
                                                                                                        
  ## Ordered implementation                                                                             
                                                                                                        
  ### Phase 0 — Clean process remediation and live validation                                           
                                                                                                        
  1. Inspect the current worktree and preserve all pre-existing changes. Do not modify the unrelated    
     files, prebuild-output/, resume.md, or root diagnostic scripts.                                    
                                                                                                        
  2. Inventory every related process before stopping anything:                                          
      - API listeners on ports 8000 and 8001.                                                           
      - All oryxenai.jobs.worker processes.                                                             
      - All preview.gateway processes.                                                                  
      - PostgreSQL listeners on ports 5432 and 5545.                                                    
      - Exact command lines, PIDs, creation times, and PostgreSQL data directories.                     
                                                                                                        
     Historical PIDs such as 38108 and 26432 are evidence only; they must not be reused blindly.        
                                                                                                        
  3. Query both PostgreSQL instances for currently running background_jobs rows before stopping         
     processes. Use read-only diagnostics and temporary connection overrides only where necessary; do   
     not add a 5545 value to repository configuration.                                                  
                                                                                                        
     Any genuine in-flight job must be allowed to finish or fail naturally before its owning process    
     is stopped.                                                                                        
                                                                                                        
  4. Stop only the identified stray processes:                                                          
      - Both logical API instances, including the alternate port-8001 test instance.                    
      - Both worker instances.                                                                          
      - The PostgreSQL instance backed by .workspace/postgres-native-5545.                              
                                                                                                        
     Keep the canonical PostgreSQL instance on port 5432 running. Do not use broad process-name         
     termination and do not delete the orphaned 5545 data directory.                                    
                                                                                                        
  5. Start a clean native stack only through scripts\run-native.ps1, from a PowerShell session with no  
     stale DB_HOST_OVERRIDE or DB_PORT_OVERRIDE variables:                                              
                                                                                                        
     scripts\run-native.ps1 migrate                                                                     
     scripts\run-native.ps1 api                                                                         
     scripts\run-native.ps1 worker                                                                      
     scripts\run-native.ps1 preview                                                                     
                                                                                                        
     The API reload parent/child processes count as one logical API service. There must be only one     
     API listener on port 8000, one worker service, and one preview gateway.                            
                                                                                                        
  6. Reconfirm the alignment using both network and database evidence:                                  
      - API connections point to PostgreSQL 5432.                                                       
      - Worker connection pool points to PostgreSQL 5432.                                               
      - No active application process connects to 5545.                                                 
      - current_database(), inet_server_addr(), and inet_server_port() report the expected canonical    
        database.                                                                                       
                                                                                                        
      - API and preview health endpoints return successfully.                                           
                                                                                                        
  7. Explicitly verify the b4f7daa freshness hypothesis:                                                
      - Compare git log -1 --format=%cI b4f7daa with the new worker’s creation time.                    
      - Confirm the new worker started after the fix was committed.                                     
      - Confirm no old worker remains that could win a job-claim race.                                  
      - Record this separately from the database split; do not describe the two findings as one cause.  
                                                                                                        
  8. Abandon the orphaned run and job:                                                                  
      - Run: f7c2eece-1ab3-4f2b-8ff3-a573fe9c2ece                                                       
      - Job: 3193daba-7d28-4dff-bdca-7d516c4e3d90                                                       
                                                                                                        
     Do not recover, retry, or delete them. They belong entirely to the abandoned 5545 database. Use a  
     new idempotency key and create a fresh run against the clean 5432 stack.                           
                                                                                                        
  9. Validate the fresh run through the complete pipeline:                                              
                                                                                                        
     plan → acquire → generate → verify → ready                                                         
                                                                                                        
     Confirm that:                                                                                      
      - The run and job rows exist in the same 5432 database.                                           
      - plan success creates the expected acquire successor.                                            
      - Worker logs show current code and normal heartbeat/claim behavior.                              
      - The run reaches ready with a real promoted preview.                                             
      - The result is recorded as one live-generation budget run.                                       
                                                                                                        
  10. Add a dedicated CHANGES.md entry for the root-cause finding. It must explicitly record:           
                                                                                                        
  - API-to-5545 and worker-to-5432 established connections.                                             
  - The absence of 5545 from checked-in repository configuration.                                       
  - The duplicate API/worker process situation.                                                         
  - The operational cleanup performed.                                                                  
  - The abandoned run/job IDs.                                                                          
  - The independent b4f7daa worker-freshness verification.                                              
  - Which evidence proved each symptom was fixed.                                                       
                                                                                                        
  ### Phase 1b — Targeted fixes only if the clean run reproduces a defect                               
                                                                                                        
  If the clean run succeeds, do not modify the coordinator or generation pipeline.                      
                                                                                                        
  If a defect reproduces, diagnose it at the same root-cause granularity as the existing history:       
                                                                                                        
  - Check deterministic validator over-strictness before changing prompts.                              
  - Check every detached/development auto-advance boundary for authorization-context assumptions.       
  - Check provider error classification and credit/rate-limit handling.                                 
  - Check cross-agent handoff IDs and roles.                                                            
  - Check logging initialization before treating an empty log as evidence.                              
  - Ensure newly surfaced errors use the existing secret-redaction path.                                
  - Rule out Playwright/browser installation, dependency drift, and competing processes before calling  
    the issue a generator defect.                                                                       
                                                                                                        
  - Keep preview reachability work in Phase 2 rather than adding a one-off Phase 1b workaround.         
                                                                                                        
  Each related fix batch receives:                                                                      

  - Focused tests.                                                                                      
  - One deliberate live validation run.                                                                 
  - A compact CHANGES.md entry.                                                                         
  - A task-scoped local commit.                                                                         
                                                                                                        
  Do not reopen the already-decided Luna routing, verified-only preview architecture, or coordinator    
  architecture without new post-restart evidence.                                                       
                                                                                                        
  ### Phase 2 — Preview reliability and Docker topology                                                 
                                                                                                        
  #### Default Compose topology                                                                         
                                                                                                        
  Update compose.yaml so preview-gateway is no longer under profiles: ["codegen"].                      
                                                                                                        
  The default stack must start:                                                                         
                                                                                                        
  postgres → migrate → app + worker + preview-gateway                                                   
                                                                                                        
  Keep build-validation profile-gated because it remains a separate opt-in one-shot validation          
  service. Update the Compose comments to describe the new default topology.                            
                                                                                                        
  Record this as the next architecture decision, currently expected to be D-054, after checking the     
  current highest decision number. The ADR must explain:                                                
                                                                                                        
  - Why the shared preview gateway is now part of the default stack.                                    
  - Why this removes the off-by-default preview failure.                                                
  - Why the generated portfolio still does not receive its own container.                               
  - Why the standalone oryxenai-codegen workflow remains separate.                                      
                                                                                                        
  #### Internal preview health probing                                                                  
                                                                                                        
  Add a typed preview_health_url configuration field to CodeGeneratorVerificationConfig.                
                                                                                                        
  Readiness must perform a real asynchronous HTTP probe using the existing httpx dependency:            
                                                                                                        
  - GET the configured health URL.                                                                      
  - Use a short timeout of approximately 1–2 seconds.                                                   
  - Do not follow redirects.                                                                            
  - Treat only a successful 2xx response as ready.                                                      
  - Treat a missing or invalid URL as preview_gateway_not_configured.                                   
  - Treat timeout, connection failure, or non-2xx response as preview_gateway_unreachable.              
                                                                                                        
  The readiness response must continue exposing preview_gateway_ready, but it must now reflect actual   
  reachability instead of merely checking that host and port values are populated.                      
                                                                                                        
  Configuration values:                                                                                 
                                                                                                        
  - Native/base local configuration: derive the health URL from the dialable preview_host and           
    preview_port, normally 127.0.0.1:4174.                                                              
                                                                                                        
  - config/app.docker.toml:                                                                             
                                                                                                        
    preview_health_url = "http://preview-gateway:4174/health/live"                                      
                                                                                                        
  - config/app.docker.codegen-run.toml: use the same Compose service-name URL for its isolated Docker   
    project, while keeping its local/lenient promotion contract.                                        
                                                                                                        
  The reason for the Docker-specific URL must be documented beside the setting:                         
                                                                                                        
  - localhost inside the API/worker container refers to that same container.                            
  - 0.0.0.0 is a bind address, not a dial target.                                                       
  - preview-gateway is resolvable through Docker Compose service-name DNS.                              
                                                                                                        
  Convert DevelopmentService.readiness() to an async method and update its route caller to await it.    
  Preserve the existing response shape apart from truthful blocker values. Update the control-room      
  JavaScript to render clear human labels for the new blocker codes.                                    
                                                                                                        
  Do not use preview_base_url for this internal liveness check.                                         
                                                                                                        
  #### Public preview contract                                                                          
                                                                                                        
  Set this exact key only in the hosted/production-like overlay:                                        
                                                                                                        
  # config/app.docker.toml                                                                              
  preview_public_readback_required = true                                                               
                                                                                                        
  Do not add this key to:                                                                               
                                                                                                        
  - config/app.docker.codegen-run.toml.                                                                 
  - config/app.toml.                                                                                    
  - Native/local configuration.                                                                         
  - Test configuration.                                                                                 
                                                                                                        
  The effective local and standalone Docker-dev behavior remains lenient (false). The hosted overlay    
  remains strict and fail-closed.                                                                       
                                                                                                        
  Keep preview_base_url as the browser-facing public preview URL. It must not be replaced by the        
  internal preview-gateway URL. Any actual hosted deployment using app.docker.toml must configure       
  preview_base_url to an HTTP(S) origin reachable by both the worker’s public-readback request and the  
  user’s browser. The internal health URL is only for service-to-service liveness.                      
                                                                                                        
  Free-tier versus paid hosting requires no code-path difference. Storage behavior remains config-      
  driven:                                                                                               
                                                                                                        
  - Hosted overlay: artifact_storage / R2-backed storage.                                               
  - Standalone Docker development: local_fs.                                                            
  - Native/local development: existing local filesystem behavior.                                       
                                                                                                        
  #### Native developer path                                                                            
                                                                                                        
  Extend scripts\run-native.ps1 with a dev service option.                                              
                                                                                                        
  dev must launch exactly one logical API, worker, and preview gateway using the existing service       
  cases. It must not silently run migrations or introduce a new process abstraction.                    
                                                                                                        
  The documented order becomes:                                                                         
                                                                                                        
  scripts\run-native.ps1 migrate                                                                        
  scripts\run-native.ps1 dev                                                                            
                                                                                                        
  Add this ordering note to the canonical local commands in AGENTS.md.                                  
                                                                                                        
  #### Phase 2 verification
                                                                                                        
  Verify both paths without manual process workarounds:                                                 
                                                                                                        
  - Default docker compose up starts the preview gateway automatically.                                 
  - Docker readiness succeeds through http://preview-gateway:4174/health/live.                          
  - The standalone oryxenai-codegen project still uses its own database, local_fs, port-8001-flavored   
    origins, and lenient readback.                                                                      
                                                                                                        
  - A real promoted preview opens in a plain browser tab.                                               
  - Hosted strict promotion fails closed if the configured public preview URL is unreachable.           
  - Hosted promotion succeeds only after the public preview HTTP round-trip passes.                     
                                                                                                        
  ### Phase 3 — Evidence-gated visual quality                                                           
                                                                                                        
  Do not begin this phase until a real completed run has produced a rendered site.                      
                                                                                                        
  If human inspection shows the portfolio is visually distinctive and profession-appropriate:           
                                                                                                        
  - Record that result.                                                                                 
  - Do not change prompts, thresholds, or templates.                                                    
                                                                                                        
  If the output is genuinely generic:                                                                   
                                                                                                        
  1. Inspect the existing TypeScript AST audit and integration-review evidence.                         
  2. Tighten one narrow static-audit threshold or add one narrow check in the existing audit function.  
  3. Run one live validation for the related change batch.                                              
  4. Escalate to prompt changes only if static audit and LLM integration review both pass while human   
     inspection still finds generic output.                                                             
                                                                                                        
  5. Obtain an independent second-model review before committing major prompt or contract changes.      
                                                                                                        
  Do not add vision-model or screenshot gating, live-WIP preview streaming, generic profession          
  templates, or framework rewrites. The single available resume fixture proves only that the mechanism  
  works for one profile; do not claim cross-profession distinctiveness without evidence.                
                                                                                                        
  ### Phase 4 — Cleanup                                                                                 
                                                                                                        
  #### Dead foundation model machinery                                                                  
                                                                                                        
  After functional work is stable, remove only the confirmed unreachable model-profile machinery:       
                                                                                                        
  - code_generator_foundation_builder profile and capabilities in config/models.toml.                   
  - Its routing entry.                                                                                  
  - "foundation" model/prompt lookup entries.                                                           
  - prompts/foundation.md.                                                                              
  - foundation_profile from service and development-service preflight construction.                     
                                                                                                        
  Run the repository-wide grep immediately before deletion.                                             
                                                                                                        
  Do not remove the live deterministic foundation work-unit path, GENERATING_FOUNDATION, compiler       
  behavior, or RequestOrigin.role == "foundation_builder" references. Keep the integration test         
  reference that covers resource-acquisition provenance.                                                
                                                                                                        
  Make this an isolated cleanup commit.                                                                 
                                                                                                        
  #### Documentation drift                                                                              
                                                                                                        
  Update:                                                                                               
                                                                                                        
  - docs/code-generator-architecture/v2-production-architecture.md with a current-contract banner or    
    refresh tied to D-034/D-041.                                                                        
                                                                                                        
  - docs/code-generator-architecture/live-preview-and-deployment.md to describe the implemented shared  
    path-prefixed gateway:                                                                              
    /preview/{host}/{path}.                                                                             
                                                                                                        
  Leave the already-accurate free-host deployment and preview-quality documents unchanged except for    
  necessary cross-links.                                                                                
                                                                                                        
  Update docs/run/run.md where its Docker commands or comments still imply that the main preview        
  gateway is profile-gated, while preserving the separate oryxenai-codegen workflow.                    
                                                                                                        
  Leave test_anthropic_key.py and test_openai_key.py untouched. Do not move or delete them in this      
  task. Revisit them only through a separately authorized cleanup decision.                             
                                                                                                        
  ## Interfaces and compatibility                                                                       
                                                                                                        
  - New configuration key: preview_health_url.                                                          
  - DevelopmentService.readiness() becomes asynchronous internally.                                     
  - Existing readiness JSON fields remain available.                                                    
  - New blocker values distinguish configuration absence from gateway unreachability.                   
  - No database schema or migration changes.                                                            
  - No new public API endpoint.                                                                         
  - PreviewPromoter remains verified-only and atomic; only the hosted overlay changes the strict        
    public-readback flag.                                                                               
                                                                                                        
  - Returned preview URLs continue to use the configured browser-facing preview_base_url.               
                                                                                                        
  ## Verification and acceptance                                                                        
                                                                                                        
  After each source-touching phase, run:                                                                
                                                                                                        
  uv run pytest                                                                                         
  uv run ruff check .                                                                                   
  uv run ruff format --check .                                                                          
  uv run mypy src                                                                                       
                                                                                                        
  Add or update tests for:                                                                              
                                                                                                        
  - Successful preview health probe.                                                                    
  - Missing or invalid health URL.                                                                      
  - Timeout/connection failure.                                                                         
  - Non-2xx gateway response.                                                                           
  - Lenient readback for native, test, and app.docker.codegen-run.toml.
  - Async readiness route behavior.
  - Frontend rendering of the new blocker messages.
  - Existing promotion rollback and public-readback tests.

  - One clean native process topology.
  - API and worker sharing PostgreSQL 5432.
  - A fresh run reaching ready.
  - Correct plan → acquire auto-chaining.
  explicitly superseded.

  ## Commit and worktree protocol

  For every completed unit:

  - Inspect git status --short --branch before work and before staging.
  - Stage only files owned by that unit.
  - Never use git add . or git add -A.
  - Review the complete staged patch, git diff --cached --check, and staged statistics.
  - Add the required CHANGES.md entry.
  - Add a DECISIONS.md entry only for the Compose topology decision.
  - Create a task-scoped local commit.
  - Never push, rebase, amend, reset, or overwrite unrelated work.

  The live-generation budget remains approximately ten full runs. The already-stuck run did not reach   
  a model call, but it must still be tracked. Spend roughly one or two fresh runs on the first clean    
  pipeline validation, then one run per related fix batch. Spend additional Phase 3 runs only if human  
  inspection provides evidence that visual quality needs work.