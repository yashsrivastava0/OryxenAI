# Deployment CI/CD pipeline — issue log

Read this before touching PR #1, the `deployment-sync-2026-09-22` branch,
the required "quality" GitHub Actions check, or the Azure VM deploy
pipeline. This is a dedicated, timestamped log of every bug found and
fixed (or still open) while getting CI green and eventually getting a
real Azure deployment out. It exists so any AI tool (Claude Code, Codex
CLI, Antigravity, Cursor, or a human) picking this up later — in this
session or a completely new one — knows exactly what's broken, what's
already fixed, and when, without re-diagnosing from scratch.

This file complements, and does not replace:
- [`docs/azure-issue.md`](../azure-issue.md) — the earlier SSH/NSG
  connectivity saga (a separate, already-resolved problem class).
- [`docs/deployment/ci-cd-runbook.md`](ci-cd-runbook.md) — the
  operational how-to for the CD pipeline itself (branch protection, `gh`
  CLI usage, the self-hosted runner).
- [`CHANGES.md`](../../CHANGES.md) / [`DECISIONS.md`](../../DECISIONS.md)
  — the project-wide change/decision log, which records commit-sized
  summaries, not this file's blow-by-blow diagnostic detail.

**Update this file after every deployment/CI-pipeline session, whether it
ends in success or failure**, per `AGENTS.md`'s protocol:
1. Update "Currently open issues" below — add, amend, or remove items.
2. Append a new dated entry under "Session log" with what you found,
   what you changed (commit SHAs), and the exact result (including the
   next failure uncovered, if any) with a timestamp.

---

## Currently open issues (as of 2026-09-22 15:58 +05:30)

1. **`preview-gateway` container fails to start in the CI Docker smoke
   test.**
   - Error: `pydantic_core._pydantic_core.ValidationError: 1 validation
     error for Settings / db_port_override / Input should be a valid
     integer, unable to parse string as an integer [input_value='']`
   - Cause: `.env.example` ships `DB_PORT_OVERRIDE=` as an empty string.
     `compose.yaml`'s `env_file: .env` directive sets this as a literal
     empty-string environment variable inside the container, and Pydantic
     tries to parse `""` as an `int` and fails — an env var explicitly set
     to an empty string is treated differently from one that's simply
     unset (which would fall through to the field's own default/`None`).
   - Fix (diagnosed, **not yet applied** — work stopped here per an
     explicit operator instruction after several push-and-check
     iterations): in `.github/workflows/ci.yml`'s "Prepare throwaway .env
     for dev Compose smoke test" step, either strip the blank
     `DB_HOST_OVERRIDE=`/`DB_PORT_OVERRIDE=` lines out of the copied
     `.env.example` before Docker Compose reads it, or simply don't
     append/keep them in the throwaway file at all.
   - Status: this is the **last** stage failing. Every stage before
     Docker build/smoke test — lint, format check, mypy, the full
     1433-test pytest suite (Linux CI), frontend typecheck/test/build,
     pip-audit, Gitleaks — passes cleanly. See the 2026-09-22 session log
     entry below for the full chain of Docker-smoke-test-only issues that
     were found and fixed to get this far.

2. **PR #1 (`deployment-sync-2026-09-22` -> `deployment`) is not merged.**
   Blocked on issue #1 above — the required `quality` status check
   (branch protection ruleset `deployment-ci-gate`) must be green first.
   No merge has been attempted.

3. **No live Azure deployment has been attempted with any of tonight's
   fixes.** The `deploy` job's trigger remains deliberately
   force-disabled (a leading `false &&` in its `if:` condition in
   `.github/workflows/ci.yml`) pending explicit operator go-ahead. Per
   the standing instruction: merging PR #1 and removing that
   force-disable each independently need a **fresh, explicit go-ahead in
   the moment**, even once issue #1 is fixed and CI is green.

4. **PR #1 previously had a wrong base branch** (targeted `main` instead
   of `deployment`) — this is now **fixed** (see session log), listed
   here only so nobody re-checks and gets confused by old screenshots or
   cached PR views showing the old huge diff.

---

## Session log

### 2026-09-22, ~11:30–15:58 +05:30 — Claude Sonnet 5 (Anthropic)

Continuing a prior session's Azure deployment task. Started from: PR #1
open but targeting the wrong base branch, its required `quality` check
failing on 3 tests, and the `deploy` job trigger force-disabled pending
go-ahead. Full narrative, in order:

1. **~11:35** — Discovered PR #1 was opened against `main`, not
   `deployment` (`gh pr view` showed `baseRefName: "main"`,
   `mergeable: "CONFLICTING"`, diff +123,346/-25,733). `main` and
   `deployment` had diverged long ago at commit `73c623c`. Retargeted via
   `gh pr edit 1 --base deployment`; diff dropped to the real ~1091/-23
   gap and `mergeable` flipped to `MERGEABLE`.

2. **~12:00–13:00** — Fixed the npm.cmd cross-platform resolver bug
   (`1be4b13`): `config/app.toml`/`config/app.test.toml` hardcoded
   `npm_executable = "npm.cmd"` (Windows-only), inherited by
   `config/app.docker.toml` (the real Azure/Docker production overlay) —
   a live production bug, not just CI. Fixed both configs to `"npm"` and
   hardened `resolve_npm_executable()` in `process_runner.py` to fall
   back to bare `"npm"` on non-Windows. Also applied a first-pass fix to
   the separately-failing Output Inspector browser test (`80687eb`,
   assertion-style only — later proven insufficient).

3. **13:16–13:22** — Pushed; CI runs `35701329546`/`35701323749` (started
   07:46 UTC): **2 failed, 1431 passed**. The npm fix let real npm
   actually execute for the first time on Linux CI (previously it never
   started at all), which unmasked a *new* failure:
   `npm error code ENOTCACHED` on an unrelated package — the offline npm
   cache (`.workspace/npm-cache`) starts completely empty on a fresh
   runner; there was no CI equivalent of the Windows-only, manually-run
   `scripts/warm-npm-cache.ps1`. Also confirmed the Output Inspector fix
   was genuinely insufficient: Playwright's `expect(...).to_be_hidden()`
   failed after its full 5-second retry window, proving a real functional
   bug, not a snapshot-timing race.

4. **~13:25–13:28** — Root-caused the Output Inspector bug for real:
   `OutputInspector.tsx` attached its Escape-key listener inside a
   passive `useEffect`, which Preact runs after the DOM commit/paint —
   Playwright's next action (the Escape keypress) could land in the
   window before the listener existed. Fixed by switching to
   `useLayoutEffect` (`5837913`). Separately discovered
   `scripts/warm-npm-cache.sh` (a bash script mirroring the `.ps1` one,
   already used by `compose.yaml`'s `codegen-cache-warm` profile) existed
   but was never wired into CI; added a step calling it
   (`e1fb376`).

5. **13:28–13:32** — Pushed; CI runs `35702271327`/`35702269134`: **1
   failed, 1432 passed** — Output Inspector fixed for real. The one
   remaining failure was the verification-worker integration test, now
   with `npm error code EUSAGE ... Missing: @emnapi/core@1.11.3 from lock
   file`. Reproduced this precisely in a real Linux environment (WSL
   Ubuntu, Node 22.20.0) and found the checked-in
   `scaffolds/react-vite-v1/package-lock.json` was written by a newer npm
   (11.x/12.x) that nests `@emnapi/core`/`@emnapi/runtime` differently
   than npm 10.x (Node 22's bundled version, matching CI) expects.

6. **~14:00–14:36** — Regenerated the lockfile with Node 22.20.0/npm
   10.9.3 (`d57e3c0`), confirmed the result installs cleanly under both
   that npm and this machine's own Windows npm 11.6.2 (no one-way
   breakage). **Also made a mistake here**: while investigating,
   overwrote the real local `.env` file's contents with a throwaway
   placeholder via `cp .env.example .env`, destroying real secrets in
   place. The operator recovered it via editor undo; two stray pasted
   lines (a bare JWT-looking token and a GitHub runner registration
   command) were found and removed at the operator's request. **Lesson
   for future sessions: never overwrite `.env` in the actual repo
   checkout without backing it up first** — use a disposable copy
   elsewhere, or back up and restore in the same atomic script with a
   trap, as later steps in this session did correctly.

7. **14:36–14:42** — Pushed; CI run `35708497113` (pull_request event):
   **1433 passed, 5 skipped** — every real test now passes on Linux CI.
   That run still failed overall, but only at a later step: Gitleaks
   (`gitleaks/gitleaks-action@v2` now requires an explicit `GITHUB_TOKEN`
   for `pull_request`-triggered scans, a breaking change in the action
   itself, unrelated to anything above). A parallel push-triggered run
   (`35708489961`) failed even later, at "Docker smoke test": `.env` file
   not found (`compose.yaml`'s `app`/`worker`/`migrate`/`preview-gateway`
   each declare `env_file: .env`, which CI never created before this
   point). The shared metrics dashboard showed **100% job failure rate
   for the whole month, 11 runs** at this point in the session.

8. **~15:08–15:36** — Fixed both of those (`f7b05d6`): added the
   `GITHUB_TOKEN` env passthrough for Gitleaks, and a throwaway `.env`
   creation step (mirroring the existing production-Compose-validation
   pattern) before Docker build. Next run got further but `migrate`
   exited 1 with no visible cause (`docker compose up -d --wait` doesn't
   stream container logs); added a "dump Compose logs on failure" step
   (`4bdea92`) to see it. That revealed
   `asyncpg.exceptions.InvalidPasswordError: password authentication
   failed for user "oryxen"` — the job-level `POSTGRES_PASSWORD:
   oryxen_test` env var wins Compose's own `${POSTGRES_PASSWORD}`
   variable substitution for the `postgres` service, while
   `app`/`worker`/`migrate` get their password from the throwaway
   `.env`'s literal content via `env_file`, which had been set to a
   *different* placeholder value. Fixed by writing the job's own
   `POSTGRES_PASSWORD` into `.env` instead of an independent value
   (`1847d80`).

9. **15:21–15:27** — Pushed; `migrate` now succeeds, `worker` becomes
   healthy, but `app` came up unhealthy: `ValueError: The bootstrap
   administrator count is invalid.` — `config/app.docker.toml` sets
   `[auth] required = true`, which unconditionally requires exactly 2
   syntactically valid emails in `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`
   (`.env.example` ships this blank). Added two fake addresses to the CI
   throwaway `.env` (`cb76076`) — no real Google/Supabase verification
   happens at this startup stage, so fake addresses are sufficient for a
   smoke test.

10. **15:30–15:36** — Pushed; `migrate`, `worker`, and `app` are now all
    healthy. `preview-gateway` is the new (and, as of this entry, only
    remaining) unhealthy container — see "Currently open issues" #1
    above for its exact cause and diagnosed fix. **Work stopped here per
    an explicit operator instruction** ("this is the last time you are
    trying to push... if it fails this time, you must stop") after this
    push also failed. No further pushes, merges, or deploy-trigger
    changes were made after this point.

**Net result this session:** every original failure this session started
with is fixed and confirmed on real Linux CI (npm resolution, empty
offline cache, stale lockfile, the Output Inspector timing bug, the PR's
wrong base branch). Four *additional*, previously-undiscovered CI/Compose
bugs were found and fixed along the way (Gitleaks token, missing `.env`,
password mismatch, missing bootstrap admin emails) — none of these were
in the original 3 reported failures; they were only reachable once the
earlier bugs stopped masking them. One bug remains (`DB_PORT_OVERRIDE`
empty-string parsing), fully diagnosed with its fix already known. PR #1
is not merged; no live Azure deploy was attempted.
