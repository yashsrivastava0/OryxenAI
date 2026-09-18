# Code Generator repair plan — live campaign log (2026-09-18)

Separate from `docs/code-generator-live-campaign.md` (the earlier D-094
campaign, closed 2/4). This is a new campaign under
`docs/code-generator-repair-plan-2026-09-16.md` (T09), bounded to 5 new
full-generation attempts, started after T01–T05 and T07's core fix were
implemented and unit/integration-tested.

## Environment setup

The native stack (`scripts/run-native.ps1 dev`) was already occupied by a
3-day-stale, still-responding `uvicorn --reload` process on port 8000, plus
duplicate stale worker/preview-gateway processes dating back to 2026-09-14.
`Start-Process`-spawned background windows were also found to launch with a
different (stale/reduced) environment than an interactive shell — `node`/`npm`
resolved via `shutil.which` inside those processes even though they resolved
fine everywhere else, which made `toolchain-preflight` report `node: false`,
`browser: false` even though Node, npm, and Playwright's browser were all
correctly installed. Killed the stale processes (with explicit user
permission — the harness blocks unattended process termination) and started
api/worker/preview directly as backgrounded shell commands instead of via
`Start-Process`, using the documented alternate port 8001. This produced a
fully green `toolchain-preflight` (`node`, `npm`, `install`, `typecheck`,
`build`, `browser`, `preview_gateway` all `true`).

## Candidate selection

Enumerated local Build Preparation packs via
`GET /api/v1/development/code-generator/build-preparation-packs`. 6 eligible,
all single-route. Selected two structurally different candidates (confirmed
via each pack's own navigation-destination list, not full private content):

- `604405bb-51e2-4de0-8e67-1a2f8e08878a` (2026-09-15) — 7 sections, 3
  resources, navigation destinations including
  `featured-projects`/`experience`/`research-education`.
- `0ffb7b6e-d712-440f-a768-cf9b6f0340a5` (2026-09-12) — 5 sections, 8
  resources, a different professional domain per the prior session's own
  investigation notes.

Only the first was reached this session; the second remains unattempted.

## Attempt 1 (pack `604405bb`) — run `bed7bbd5` (abandoned), then `10abe899`

### Acquisition: a real, reproducible local npm/lockfile issue

The first acquire attempt failed with `DEPENDENCY_INSTALL_FAILED`: `npm ci
--offline` could not resolve `@tailwindcss/oxide-wasm32-wasi`'s own nested
optional dependencies (`@emnapi/core`, `@emnapi/runtime`,
`@emnapi/wasi-threads`, `tslib`). These are optional dependencies of an
optional, never-installed-on-Windows platform variant of `@tailwindcss/oxide`
(the actual applicable variant is `oxide-win32-x64-msvc`), but `npm ci
--offline` still requires resolvable version metadata for every listed
package, including inapplicable-platform ones.

Traced through several retries:
1. Warming the offline cache (`scripts/warm-npm-cache.ps1`) fixed the
   scaffold's own base dependencies but not this specific optional-platform
   sub-tree, since the warmer's own manifest doesn't include `lucide-react`
   merged into the *existing* scaffold lockfile the way `dependency_manager.py`
   does for a real run.
2. Manually caching individual packages (`npm cache add <pkg>@<version>`) fixed
   one missing entry at a time but kept surfacing the next one, and eventually
   an `Invalid Version: ''` error — confirming the actual defect is a
   **malformed lockfile** (blank `version` fields on those nested optional
   entries), not a missing cache entry. No amount of cache-warming fixes a
   blank version string; npm rejects it before any registry/cache lookup.
3. A real (non-`ci`) `npm install` against the same `package.json` correctly
   self-heals this lockfile shape, confirming `dependency_manager.py`'s own
   `_install()` step (which intentionally uses `npm install`, not `npm ci`,
   per its own comment) is the correct path — but the run's *existing*,
   already-written lockfile was still wrong until repaired.
4. With the user's explicit approval, temporarily set
   `code_generator_dependencies.allow_network_install = true` in
   `config/app.native.toml` for this diagnostic session only (reverted
   afterward — confirmed via `git diff` showing no residual change) and
   regenerated the lockfile with network access, which produced a lockfile
   that also passed a subsequent **offline** `npm ci` cleanly.

This is a real, reproducible defect worth a follow-up: `dependency_manager.py`'s
`_create_lock()` (`npm install --package-lock-only --offline`) can produce a
lockfile that a later strict `npm ci --offline` (used by the build/verification
gate) rejects as "out of sync," specifically for packages whose dependency
tree includes `@tailwindcss/oxide`-style multi-platform optional sub-trees.
Not fixed in this session — recreating it cleanly from scratch (without the
several rounds of manual cache surgery this session did) needs its own
focused investigation.

### Workspace corruption from process interruption (self-inflicted, not a product bug)

While iterating on the acquire retries above, `Stop-Process -Force` was used
on the worker process while it likely held an in-flight file operation. The
run's workspace (`bed7bbd5`) ended up with an empty `src/` tree and missing
`tsconfig.*`/`vite.config.ts`/`index.html`, which is not a real code defect —
it's a side effect of forcibly killing a worker mid-write. This run was
abandoned rather than hand-repaired further. Lesson for any future live
campaign: do not `Stop-Process -Force` a worker while a job is actively
running; use the durable job queue's own graceful shutdown instead, or only
restart between jobs.

### Fresh run `10abe899-82f2-4fc3-bd87-d44da204c0f4` — a genuine content-generation finding

Started fresh (this is the actual "1 full-generation attempt" charged against
the 5-attempt budget; `bed7bbd5` is not counted separately since it never
reached a real model-authored route). Planning and acquisition succeeded
cleanly. The deterministic foundation step passed its own source audit
(confirmed real values in `src/content/generated-content.ts`: 1767 lines,
real approved copy). Route batch 2 (`home-experience`, `home-research-education`,
`home-capabilities` sections, 5 capability-disclosure interactions) failed
after 1 repair round with a **model-authored** diagnostic code
(`MISSING_APPROVED_SOURCE_VALUES`, not found anywhere in this codebase's
Python source — confirmed the model invented this code itself as part of its
structured `cannot_complete` response):

> "The supplied generated-content module exposes only type declarations and
> no materialized runtime approved content values in the available context.
> Complete section source cannot be generated without fabricating or
> retyping approved content."

Traced the actual context sent to the model
(`.workspace/code-generator-generation/10abe899.../ledger/contexts/*.json`,
`shared_source["src/content/generated-content.ts"]`): it is a deliberate
`.d.ts`-style type-only excerpt (`export declare const PUBLIC_CONTENT:
readonly PublicContentPack[];` plus the full `ApprovedContentId` literal
union and `contentValue()`'s declared signature) — by design, the model is
meant to call `contentValue("content:home:home:experience:entries-0-...")`
for each individual approved value rather than being shown (and risking
retyping) the actual text. `route_batch.md` does instruct this pattern
explicitly ("Call `contentValue(\"<literal-approved-content-id>\")` directly
for every approved content key... the source audit must be able to prove the
executable literal").

This section's content shape is array-heavy (multiple experience entries,
each with several fields, each needing its own literal `contentValue(...)`
call — a dozen-plus individual literal calls for one batch). The model
appears to have concluded it could not comply without "fabricating," which
reads as it treating the *volume* of individually-enumerated literal calls
as equivalent to "missing values," rather than recognizing that the full
list of valid IDs was already supplied in the type excerpt for exactly this
purpose. This is a plausible, real prompt-clarity gap for array/repeated
content structures specifically — not confirmed as reproducible on a second
input, and not fixed in this session given the campaign's time/budget
already spent on the acquisition-stage detour above. Flagging as a concrete,
evidenced follow-up rather than guessing at a prompt change without a
second confirmed reproduction.

### Attempt accounting

- Full-generation attempts consumed: 1 of 5 (fresh run `10abe899`; the
  abandoned `bed7bbd5` workspace corruption was self-inflicted infrastructure
  handling, not a second charged attempt).
- Real model calls consumed: 1 director + 1 planner call (both reused
  correctly across the acquire retries via response-id/cache — verified no
  duplicate director/planner calls were made across retries), plus foundation
  generation and route-batch-1 (succeeded), plus route-batch-2's 2 model
  calls (initial + 1 repair round) before decline.
- Artifact/preview status: none reached — no build, no preview, this attempt
  terminated at `needs_attention` during route generation.

## Session outcome

Stopped after attempt 1 to report findings rather than continue spending
against the 5-attempt budget on a session that had already consumed
significant unplanned time on environment issues unrelated to the repair
plan's actual fixes (T01–T08, all separately unit/integration-tested and
already committed). `config/app.native.toml`'s temporary
`allow_network_install = true` was reverted; the native stack was stopped
cleanly. Attempts 2–5 remain available for a future session, ideally after:

1. A focused fix/regeneration of `dependency_manager.py`'s lockfile-creation
   robustness for `@tailwindcss/oxide`-style optional multi-platform trees
   (or, at minimum, a documented one-time local remediation so a fresh
   campaign doesn't re-hit the acquisition-stage detour above).
2. A decision on whether to investigate the array-content `contentValue()`
   prompt-clarity finding with a second reproduction before changing
   `route_batch.md` again.
