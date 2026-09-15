# Code Generator control room / reliability handoff — 2026-09-14

**Status: mid-task handoff. The owner is switching the driving AI session.
This document is the complete context needed to resume without re-deriving
any of it.** Written by Claude Code (Sonnet 5) at the point of handoff,
~12:15 IST on 2026-09-14, branch `codex/code-generator-control-room`.

## 1. What the owner actually asked for (original request, paraphrased)

The owner wants, after Build Preparation output is approved and they click
"Generate": the Code Generator starts, a side panel opens showing real
progress (not fabricated), and genuine errors surface with a copyable trace
ID and an easy recovery path. The **repeatedly stressed top priority**:
*the Code Generator must reliably produce error-free portfolio code*,
proven via a new **5-run live test campaign** using the latest Build
Preparation output as input. The owner explicitly authorized full autonomy
("based on your authority, you can do anything") and asked for a detailed
plan before implementation — that plan was produced, researched, and
approved (see §3 for its full content, since it lives outside this repo at
`C:\Users\Yash Srivastava\.claude\plans\validated-cuddling-kazoo.md`, a path
only this Claude Code installation can read).

Two explicit decisions the owner already made when asked directly:
- **Progress UI**: keep the already-built, real backend-milestone-driven
  progress design (rejected the literal "fake"/decorative progress idea —
  see §2 for why).
- **Live campaign input**: use the 5 real Build Preparation outputs already
  sitting on disk in the live mirror (`output/build_preparation/`), not
  fresh live upstream generation per slot.
- **Push to origin**: approved and done (see §4).
- **Proceeding despite other concurrent AI sessions actively committing to
  this same branch right now**: owner said go ahead (see §5, this is very
  much still live and relevant).

## 2. Key research findings (do not re-derive these — verified directly against source)

- **The Code Generator "control room" side panel described by the owner is
  already built and shipped**, not something to build from scratch:
  `frontend/src/stages/generation/GenerationStage.tsx` (Preact/TS, commit
  `f003023`, 2026-09-13) has a real 5-milestone stepper (Plan/Acquire/
  Build/Verify/Preview) driven by actual backend `coordinator_stage`/`phase`
  values, a live preview theater (iframe), an attention/retry card, and a
  closed-by-default right-side traceability drawer with Trace ID/Active Job
  ID/Session ID/Error Code and a "Copy diagnostic report" button — an
  inline code comment literally reads `RIGHT-SIDE TRACEABILITY POP-UP
  DRAWER (USER'S EXPLICIT REQUIREMENT)`. It's wired into
  `frontend/src/app/AppShell.tsx`, gated behind Build Preparation approval,
  fires only on an explicit "Generate Portfolio" click (never auto-chained).
- **Two confirmed, still-unfixed frontend defects** in that same file
  (verified directly in source, not just docs):
  1. Leftover **Publish/Deploy UI** at `GenerationStage.tsx` lines
     ~679, 687, 691, 706–709 ("Publish unavailable until verification
     completes", "Publish after verification", "🚀 Publish when ready —
     Deploy your project"). This contradicts the platform's actual scope
     (no publishing capability exists anywhere in the codebase) and the
     newer, stricter design doc (`docs/Fix Frontend/17-generation-ready-
     preview-research.md`, which explicitly forbids any Publish/Deploy
     claim). **Not yet fixed.**
  2. **No stage-transition animation**: `AppShell.tsx` swaps `activeStage`
     via plain `useState` with no transition wrapper; `.stage-frame` in
     `frontend/src/styles/shell.css` (~line 426) has no crossfade. The
     owner wants a smooth transition from Build-Prep-approved into
     Generate. **Not yet fixed.**
- **The "fake coding" idea directly contradicts already-written, already-
  approved design docs**: `docs/Fix Frontend/17-generation-ready-preview-
  research.md`, `docs/code-generator/preview.md` §47, and
  `docs/Fix Frontend/06-component-and-view-model-contracts.md:63` all
  explicitly forbid fabricated percentages/ETAs/fake terminal output —
  mandate real milestone progress instead. Owner confirmed: keep it real
  (§1). **No further action needed on this point** — it's resolved, not
  open.
- **The real reliability blocker was process, not generator logic**: three
  independent, already-reviewed-and-passed backend fixes had been sitting
  **uncommitted since 2026-09-11** in this shared, multi-agent worktree.
  One of them (`preview_first_acceptance`, D-094) had already been used
  successfully in a real live campaign on 2026-09-11 but the code was never
  committed, and had **zero test coverage**. **This has now been fully
  fixed and committed — see §4, this part of the task is DONE.**
- **A confirmed real bug was found and fixed along the way**: a bare
  `except Exception` in `generation_orchestrator.py::_review_and_polish`
  silently swallowed `AuthorizationFenceError` under preview-first mode — a
  genuine authorization-fence bypass (a fenced-off run's rejection would
  have been silently tolerated as an ordinary review failure). **Fixed and
  test-covered — see §4, DONE.**
- **A live-campaign process already exists and is well-established**:
  `docs/code-generator-live-campaign.md` is an append-only ledger of prior
  4–5-run campaigns, with a documented dev-harness mechanism
  (`src/oryxenai/api/routes/code_generator_development.py`, mounted at
  `/api/v1/development/code-generator/...`, detached/no-auth locally by
  default). The file's own closing rule: *"If a future owner explicitly
  authorizes a new campaign, start from fresh readiness and accounting
  rather than silently extending this closed 2/4 campaign."* The owner's
  "5 full pipeline runs" ask is exactly that authorization. **A new
  campaign section has NOT yet been written into that file — this is
  outstanding, see §6.**

## 3. What was completed and verified (Phase 0 — DONE, pushed to origin)

Four commits landed on `codex/code-generator-control-room`, in this order,
each individually test/lint/type-checked before staging (`uv run pytest`
targeted + broad suites, `uv run ruff check`, `uv run mypy src`):

1. **`49d6e0d`** — `fix(code-generator): fail-closed brief ingestion
   dispatch for post-67d5a75 wire shape`. Files: `brief_assembly.py`,
   `validators.py` (build_preparation), `brief_ingestion.py`,
   `development_input.py`, `development_schemas.py` (code_generator/core),
   plus the two test files and new fixture
   `tests/fixtures/code_generator_build_preparation_post_67d5a75_v1/`.
   Reviewed APPROVED at `semantic-review/2026-09-11-123024-pr-3.md`.
2. **`a0cae30`** — `feat(code-generator): make native verification
   acceptance preview-first (D-094)`. Files: `code_generator_verification.py`,
   `design_realization.py`, `verification_plan.py`, `config/app.native.toml`,
   plus **the `AuthorizationFenceError` fix** (import +
   `except AuthorizationFenceError: raise` added to
   `generation_orchestrator.py::_review_and_polish`, ~line 2154) and **two
   new regression tests** added to
   `tests/unit/agents/code_generator/test_phase2_design_neutral.py`
   (`test_review_and_polish_tolerates_generic_failure_under_preview_first`,
   `test_review_and_polish_reraises_authorization_fence_under_preview_first`).
3. **`c6eaa33`** — `fix(code-generator): namespace generation retries and
   receipts by explicit attempt epoch`. Files: `development_service.py`,
   `final_repair.py`, new `semantic_decline.py`, new test files, plus the
   remaining (non-Body-C) hunks in `generation_orchestrator.py` — including
   a real small bug I found and fixed in passing: a new dependency-receipt
   dedup loop (`for receipt in emergent_dependency_receipts: ...`) reused
   the name `receipt` already bound to `ResourceReceipt` type earlier in
   the same function, which mypy correctly rejected; renamed the loop
   variable to `emergent_receipt`. Reviewed PASS at
   `semantic-review/2026-09-11-110557-pr-2.md`.
4. **`d956193`** — `docs(changes): log the code generator reliability
   commits; compact history`. Added 3 CHANGES.md entries for the above, and
   ran the file's own documented compaction procedure (it had exceeded 250
   lines: 31 entries under "Recent changes" → compacted to the 18 most
   recent, moved 13 older ones into `## Compacted history`, recomputed the
   Summary block).

**Excluded on purpose, left uncommitted**:
`src/oryxenai/agents/code_generator/core/final_source_validation.py` shows
`M` in `git status` but has a completely empty `git diff HEAD` — a line-
ending/mtime artifact (repo uses `core.autocrlf=true`). Never staged it,
should stay that way (or get reset with `git checkout -- <path>` — safe,
since the diff is empty).

**Deleted**: `scripts/serve_dist.py` (untracked, undocumented ad hoc dev
script, hardcoded a stale/nonexistent run folder, its naive `/index.html`
fallback would mask real 404s). The canonical, documented tool is
`scripts/preview-codegen-export.py` (see
`src/oryxenai/agents/code_generator/README.md:90-103`). This deletion is
**not yet committed** (it's an untracked-file deletion, so `git status`
shows nothing for it — just confirm it stays deleted, or restore it from
`git log` history if the next owner wants it back for some reason before
continuing).

**Pushed**: `git push origin codex/code-generator-control-room` succeeded
as a clean fast-forward at the time (`e29aa23..79bd99a`). **Important**:
several more commits have landed from other sessions since then (see §5) —
before doing anything else, run `git status --short --branch` and `git log
--oneline -10` to see current real state; it has almost certainly moved
again.

**All verification that was run and passed** (re-run before trusting, given
concurrent activity may have changed things):
- `uv run pytest tests/unit/agents/code_generator tests/unit/agents/build_preparation -q` → 450 passed
- `uv run pytest tests/integration/test_code_generator_generation_worker.py -q` → 4 passed (note: this one is flaky when run in the same pytest session as other suites, or when another concurrent session is hitting the same Postgres test DB — always run it alone, and re-run once if it fails, before concluding anything is broken)
- `uv run ruff check` on all touched files → clean
- `uv run mypy src` → clean except one **pre-existing, unrelated, out-of-scope** error: `generation_orchestrator.py:1944: error: Name "diagnostics" already defined on line 1519 [no-redef]` — confirmed present on HEAD before any of this session's changes too (verified by temporarily swapping in the HEAD version of the file and re-running mypy). Not something this session's commits caused; not fixed; low priority.

## 4. What was in progress and got interrupted (Phase 1 — live campaign, INCOMPLETE)

**Native services are already running** (do not restart them without
checking first — another session may be using them): API responds on
`http://127.0.0.1:8000`, health/dev-harness routes work. A worker instance
was observed with `age_seconds: 10.9` at the moment I first checked
readiness (~06:32 UTC / 12:02 IST) — i.e., something (likely the other
active session) restarted the worker moments before I started.

**Readiness/preflight completed successfully**:
- `GET /api/v1/development/code-generator/readiness` → `can_start_latest: true`, `can_start_best: true`, `readiness_blockers: []` (after the two preflights below)
- `POST /api/v1/development/code-generator/provider-preflight` (with `Idempotency-Key` header, empty JSON body) → `status: "ready"`, 6 profiles checked
- `POST /api/v1/development/code-generator/toolchain-preflight` (same header pattern) → `status: "ready"`, all checks true, confirmed **5 eligible Build Preparation packs** on disk: `ea2ff472-8c63-4954-a501-65dff17cbd79` (latest/best), `1f16420f-e145-4c98-8549-894d5df9296c`, `0ffb7b6e-d712-440f-a768-cf9b6f0340a5`, `b09b2506-00ba-4714-a835-cb703e784558`, `4b5e206a-1974-4851-a274-01c74901b03a`

**Slot 1 was started and failed, twice, on the same transient-looking error**:
- Created via `POST /api/v1/development/code-generator/runs/from-build-preparation` with body `{"pack": "latest"}` and an `Idempotency-Key` header (a fresh GUID). **`run_id = af3bf8f7-d155-4e18-a5b0-48a683f5a647`**, used pack `ea2ff472-8c63-4954-a501-65dff17cbd79` (content hash `e0655b97...`, visual hash `269bf7be...`).
- Progressed automatically (`auto_advance: true`) through `planning → acquiring → generating_foundation → generating_routes → integrating → building`, then hit **`needs_attention`** at the `building` stage after ~420 seconds. Terminal code: **`TYPE_BUILD_ARTIFACT_FAILED`**, safe summary "The clean production build or artifact closure failed."
- Root diagnostic (the actual npm/vite error): `spawn EPERM` thrown from inside Vite's own `windowsSafeRealPathSync`/`optimizeSafeRealPathSync` helper (stack: `ChildProcess.spawn → spawn → execFile → exec → optimizeSafeRealPathSync → windowsSafeRealPathSync → getRealPath → tryResolveRealFileOrType → tryCleanFsResolve → tryFsResolve`), while loading `vite.config.ts` in the run's isolated workspace (`.workspace/code-generator-generation/af3bf8f7-d155-4e18-a5b0-48a683f5a647/repo/vite.config.ts`).
- I retried **just the verify stage** (`POST /api/v1/development/code-generator/runs/{run_id}/verify` with a fresh `Idempotency-Key`), reasoning it looked like a transient Windows environment issue (this exact codebase's `code generator issues.md` already documents a history of Windows-specific child-process/filesystem flakiness — e.g. `4da1ddb`: "Made toolchain preflight cleanup best-effort so a Windows enumeration denial can't discard a valid toolchain proof"). **It failed again, identically, in ~30 seconds** (much faster than the first attempt, consistent with an immediate spawn-level failure rather than something generation-content-dependent).
- **I was in the middle of investigating root cause directly** — had just `cd`'d into `.workspace/code-generator-generation/af3bf8f7-d155-4e18-a5b0-48a683f5a647/repo` to try running `npm run build` manually outside the harness, to determine whether this is (a) a genuinely systemic, currently-active Windows/Node/antivirus environment problem affecting any Vite build right now on this machine, possibly aggravated by the other concurrent session's own heavy build activity competing for the same OS-level spawn/filesystem resources, or (b) something specific to this harness/run. **I had not yet run that command** — no conclusion reached. This is the immediate next step for whoever picks this up.
- Two identical failures back-to-back (30s apart) is suspicious enough that it's worth taking seriously as possibly-more-than-random-transient, but the specific failure mode (`spawn EPERM` inside Vite's internal Windows path-resolution helper, at build-config-load time, not inside anything code-generation-specific) still looks environmental rather than a defect in the generated portfolio source itself. **Do not assume it's a real generated-code bug without first ruling out the environment**, especially given confirmed heavy concurrent git/build activity from other sessions on this exact machine during this exact window (see §5).

**Nothing has been written yet to `docs/code-generator-live-campaign.md` or
`code generator issues.md` for this campaign** — that's still to do, and
should happen once there's an actual root cause (environmental vs. real)
for Slot 1, not before.

**Background pollers**: I ran two background Bash polling loops during this
session (task ids `bkrbxk9n4` and `b4icw4b0s`); both have already completed
and require no cleanup. No other background processes were left running by
me. The native API/worker/preview-gateway processes themselves were **not**
started by me (they were already up) and I did not stop them — leave them
running unless the next owner has reason to restart them.

## 5. Critical operational context: this is a live, actively shared worktree AND working directory

This is not a "check the branch occasionally" situation — **another AI
session (or several) is committing to this exact branch, in this exact
local working directory, essentially continuously, throughout this whole
session.** Confirmed via repeated `git log`/`git status` checks:

- At session start: branch was "ahead 156" of origin.
- Mid-session, before I'd even finished Phase 0: it became "ahead 157",
  "ahead 162", "ahead 165" — multiple commits landed from "Codex (GPT-5)"
  and "Antigravity (Gemini 3.8)" (confirmed by their own `CHANGES.md`
  entries: `efb226e`, `79bd99a`, and — observed at the very moment of this
  handoff — `9bc3d8c`, `5e96a52`, `b1633f2`, `e7296f8`, all frontend/auth
  work, all landing in the few minutes around Slot 1's build failures).
- Since these commits are appearing directly in `git log` on the **same
  local branch checkout** (not just on `origin`), the other session(s) are
  operating on this same local repository, not a separate clone. Any
  destructive git operation (`reset --hard`, `clean -f`, force-push, etc.)
  risks destroying another live session's uncommitted or just-committed
  work. **Never use `git add .`/`git add -A` or any broad/destructive git
  command in this worktree** — always stage exact files, per AGENTS.md's
  own multi-agent protocol, which explicitly anticipates this exact
  situation.
- The owner was asked directly whether to proceed given this, and said yes
  — proceed, the other sessions are on unrelated areas (admin console,
  auth, deployment, frontend polish). That was true for the files touched
  by Phase 0's three backend commits. **It has not been re-verified for
  whatever the other sessions are doing right now** — before touching
  `frontend/src/styles/shell.css`, `GenerationStage.tsx`, or anything in
  `docs/Fix Frontend/`, run a fresh `git status` / `git diff` to check for
  new concurrent edits in those exact files, the same way I did before
  touching `generation_orchestrator.py`.
- This concurrency is also the leading suspect for Slot 1's `spawn EPERM`
  build failures (§4) — worth investigating whether the other session(s)
  are also running builds/npm processes concurrently right now, which on a
  single Windows machine can plausibly cause exactly this kind of
  child-process-spawn contention.

## 6. What remains (the rest of the approved plan, not yet started)

The full approved plan is at
`C:\Users\Yash Srivastava\.claude\plans\validated-cuddling-kazoo.md` on
this machine (Claude Code's local plan storage — not in the repo, not
visible to other tools). Reproduced in full below so nothing is lost:

### Phase 1 (continues) — finish the 5-run live campaign
1. Resolve Slot 1's `needs_attention` (§4) — determine root cause first
   (environmental vs. real), fix if real, then either retry Slot 1 or
   consume a fresh slot.
2. Continue through up to 5 slots total, using packs from
   `GET /api/v1/development/code-generator/build-preparation-packs`
   (5 eligible packs confirmed on disk, listed in §4).
3. Root-cause-and-fix inline on every `needs_attention`, exactly like prior
   campaigns documented in `docs/code-generator-live-campaign.md`: identify
   via the run's `terminal_failure`/`latest_error`, fix in source, add/
   extend a targeted unit test, then retry or consume a new slot.
4. **Adaptive stop**: stop as soon as one slot reaches a real,
   Chromium-verified `ready`/promoted preview — do not mechanically burn
   all 5 slots once that goal is met (established precedent: "Campaign B
   Slot 5 ... achieved ready. ... Campaign B closed (1/5 ready)").
5. Append a **new**, freshly-dated campaign section to
   `docs/code-generator-live-campaign.md` (do not extend the closed
   2026-09-11 campaign — start fresh readiness/accounting, per that
   section's own explicit resume rule). Follow the existing section format:
   intro/summary bullets, a slot outcome table, a "Full pipeline outcomes"
   narrative, validation-performed list, worktree-attribution note, closing
   operational-state/resume-rule note.
6. Log every fix made along the way to `code generator issues.md` in its
   existing compacted chronological format.
7. Commit each inline fix separately, scoped only to its own files — same
   staging discipline as Phase 0 (verify tests/lint/types before staging,
   `git add <exact files>` never `git add .`, check `git diff --cached
   --check`, write a real commit message, log to CHANGES.md if it's a real
   commit-sized unit).

### Phase 2 — finish the generation screen (two confirmed defects + existing runbook)
1. **Remove the Publish/Deploy UI** in `GenerationStage.tsx` (§2, exact
   lines given there). Replace with the truthful action set the docs
   already specify: "Open verified preview" / "Regenerate", wired to the
   existing `preview`/`candidatePreview`/`retry_available` fields — no new
   backend contract needed.
2. **Add the Build-Prep-approved → Generate stage transition animation**:
   short, one-shot crossfade on `.stage-frame` keyed off the `data-stage`
   attribute change in `AppShell.tsx`. Categorize as a "status change"/
   "preview-ready crossfade" per the allowed-motion list in
   `docs/code-generator/preview.md` §47 (no continuous ambient motion;
   respect `prefers-reduced-motion`).
3. **Execute the rest of the already-written runbook** for this screen:
   `docs/Fix Frontend/09-implementation-runbook.md` Phase 3 "Generation
   ready/preview execution detail" (cite as source of truth, don't
   re-derive), file routing in `11-implementation-file-map.md`. Covers:
   preserving server-authoritative `preview`/`candidatePreview`/
   `active_job_id`/`active_job_kind`/`safe_error`/`retry_available`;
   verified-vs-candidate visual distinction; dominant preview theater with
   closed-by-default diagnostics; route controls only when route data
   exists; 768–1199px tablet reflow to preview-first single-column order;
   bounded/`min-width:0` iframe wrapper; fixture-backed browser assertions
   at 4 viewports for ready/candidate-only/stale-ready/attention-with-
   preserved-preview states; use `visuals/20-generation-ready-preview.png`
   for hierarchy only (Markdown/API contract wins on conflict).
4. Run `npm run test` (Vitest) and typecheck/build (`tsc --noEmit && vite
   build`) in `frontend/` after these changes.
5. **Before starting this phase**: re-check `git status`/`git diff` on
   `GenerationStage.tsx`, `AppShell.tsx`, `shell.css`, and everything under
   `docs/Fix Frontend/` — other sessions were actively touching adjacent
   frontend files during this handoff window (§5); confirm no fresh
   conflicts before editing.

### Phase 3 — end-to-end live verification (final gate)
1. Use `claude-in-chrome` (or equivalent browser automation) against the
   real authenticated app (`product_shell.html` → `#product-root` — not any
   `/dev/...` diagnostic harness page).
2. Walk the full journey: Discovery → Content → Design → Build Preparation
   approval → click Generate → watch the panel progress in real time →
   force/reach a `needs_attention` state → open the trace-ID drawer and
   verify Trace ID/Active Job ID/Session ID/Error Code are present → verify
   "Copy diagnostic report" produces a complete report → verify retry
   recovers → reach a Chromium-verified `ready` preview.
3. Repeat at four viewports: 1536×695, 1366×768, 768×1024, 390×844.
4. **Definition of done**: zero uncaught console errors at any viewport;
   all preview/API requests return 2xx; the copied diagnostic report
   contains a real trace ID; no "Publish"/"Deploy" language appears
   anywhere in the Generation stage; the stage transition visibly animates
   (and visibly does not, under simulated `prefers-reduced-motion`);
   progress reflects genuine backend milestones only (no fabricated
   percentages).

### Housekeeping (carry forward)
- Do not push to origin again without asking first, except immediately
  after finishing another meaningful, verified chunk of work — the owner
  already approved one push (§3); treat each subsequent push as a fresh,
  small ask unless they've said otherwise by the time you read this.
- Never touch the unrelated dirty files from other contributors (admin
  console CSS/templates, `.agents/skills/*` deletions,
  `Input-Output-Of-Engine/*`, `docs/research/*`, `docs/resume/*`,
  `tests/test_gemini_api_keys.py`, and whatever else `git status` shows
  that isn't yours) — these belong to other sessions.

## 7. Quick reference — key facts to not re-derive

- Repo root: `C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI`
- Branch: `codex/code-generator-control-room`
- Real production frontend source: `frontend/src/` (Preact + Vite), compiled into `src/oryxenai/web/static/product/`, served via `product_shell.html`'s `#product-root`. NOT `src/oryxenai/web/templates/*` (thin FastAPI shell + unrelated dev-diagnostic harness pages only).
- Dev harness for Code Generator: `src/oryxenai/api/routes/code_generator_development.py`, mounted at `/api/v1/development/code-generator/...`, detached/no-auth by default locally (`development_harness_mode = "detached"`).
- Production session API: `/api/v1/sessions/{session_id}/code-generator` — `GET` / `POST .../start` / `POST .../retry` / `POST .../regenerate`, all mutations need an `Idempotency-Key` header.
- Native services start command (per AGENTS.md canonical commands): `.\scripts\run-native.ps1 migrate` then `.\scripts\run-native.ps1 dev`. (Already running as of this handoff — check before restarting.)
- Coarse status enum (`CodeGeneratorSessionStatus`): `not_started, queued, planning, acquiring, generating, verifying, ready, preview_pending, needs_attention`. Fine-grained (`DevelopmentRunStatus`, exposed as `phase`): `created, queued, admitting, planning, planned, acquiring, acquired, generating_foundation, generating_routes, integrating, source_ready, building, smoke_testing, repairing, ready, preview_pending, needs_attention`.
- Test/verify commands: `uv run pytest`, `uv run ruff check .`, `uv run mypy src`, `uv run alembic upgrade head` (backend); `npm run test` / `npm run build` in `frontend/` (frontend).
- This machine's userEmail (for attribution if needed): `aidevops@thealgorithmx.com`.

---
*End of handoff. Written by Claude Code (Sonnet 5) mid-task at the owner's explicit request to switch drivers.*
