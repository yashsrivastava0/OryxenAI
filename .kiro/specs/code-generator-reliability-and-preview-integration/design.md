# Code Generator Reliability & Preview Integration Bugfix Design

## Overview

This bugfix has two coupled defects and one net-new capability, all scoped by
`bugfix.md`:

1. A backend build-reliability gap: run `af3bf8f7-d155-4e18-a5b0-48a683f5a647`
   halted at `needs_attention` with `TYPE_BUILD_ARTIFACT_FAILED`, root-
   diagnosed at the time as a Windows `spawn EPERM` inside Vite's own
   `windowsSafeRealPathSync`/`optimizeSafeRealPathSync` helper.
2. A frontend/backend integration gap: `GenerationStage.tsx`'s real
   5-milestone stepper, verified/candidate preview distinction, and
   traceability drawer have never been proven against a real authenticated-
   browser run driven by a real completed backend generation.
3. A net-new estimated-time indicator, requested explicitly, that must be
   grounded in a real non-fabricated source.

**The design's root-cause finding, stated up front:** this design phase
empirically reproduced the exact failing build command, in the exact failed
run's own workspace, three independent ways, under the same kind of heavy
concurrent build/process load the original handoff document suspected — and
it succeeded cleanly every time. No code change to the spawn layer, to
`process_runner.py`, or to the generated scaffold's `vite.config.ts`/
`package.json` is proposed, because no defect was found in any of them. See
"Hypothesized Root Cause" below for the full diagnostic trail and why this
conclusion is evidentially different from either "the bug is fixed" or "the
bug never existed." The design's actual scope narrows to: (a) a diagnostic
observability improvement so a *future* recurrence is distinguishable from a
transient contention event without re-deriving this investigation, (b) the
frontend defects and the estimated-time indicator, both fully unblocked
regardless of the build outcome, and (c) an authenticated end-to-end
verification pass and a second-pack generalization run, both of which
consume the requirements' 5-call full-pipeline budget.

## Glossary

- **`spawn EPERM`**: A Windows child-process creation denial surfaced by
  Node's `child_process` layer, here observed inside Vite 6's own
  `windowsSafeRealPathSync` helper while Vite loads `vite.config.ts` — before
  any generated application code is evaluated.
- **Isolated generation workspace**: The per-run directory tree under
  `.workspace/code-generator-generation/<run_id>/repo/`, containing the
  generated React/Vite/TypeScript source, its own `node_modules`, and its own
  `vite.config.ts`. `build_runner.py::run_clean_build` recreates
  `node_modules`/`dist` here on every clean build.
- **Harness invocation**: A build/typecheck/install command run through
  `process_runner.py::run_command`, which uses `asyncio.create_subprocess_exec`
  (never a shell), a filtered/safe environment, and Windows-specific
  `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW` creation flags.
- **Manual/plain invocation**: The identical command (`npm run build`, or
  `npx vite build --configLoader runner`) run directly in an interactive
  PowerShell session in the same directory, with no `process_runner.py`
  involvement.
- **`build_command`**: The exact argv Vite build is invoked with. Resolved
  from `settings.code_generator_verification.build_command`, which is
  `["npm.cmd", "run", "build"]` in the committed `config/app.toml` base but
  is overridden to `["npm", "run", "build"]` by `config/app.native.toml` —
  the overlay actually loaded by every canonical `scripts/run-native.ps1`
  command (`OryxenAI_CONFIG_OVERLAY = "config/app.native.toml"`). Both
  resolve to the scaffold's own `npm run build` script
  (`npm run check && vite build --configLoader runner`).
- **Stage budget**: The `worker.job.kind_timeouts` entries in
  `config/app.toml` (e.g. `code_generator.plan = 900.0`), the only
  currently-populated, non-hardcoded, per-stage duration data in this
  codebase today.
- **`stage_durations_ms`**: An existing field on `CodeGeneratorSessionState`,
  `DevelopmentRunProjection`, and `DevelopmentRunState` — declared in three
  schemas but, confirmed by a full-repository grep, **written by no code
  path today**. It is dead schema, not live historical data, as of this
  design.
- **Second brief pack**: A Build Preparation debug-mirror directory under
  `output/build-preparation/` containing `content-and-narrative-brief.md` +
  `visual-and-build-brief.md`, distinct from the pack already consumed by
  run `af3bf8f7-...` (`10-05-14-09-ea2ff472`, run_id
  `ea2ff472-8c63-4954-a501-65dff17cbd79`).

## Bug Details

### Bug Condition

The observed failure, restated concretely (full detail already lives in
"Overview" above and is investigated exhaustively in "Hypothesized Root
Cause" below — this section exists only to give the required Bug Details
section its own anchor, not to duplicate that material):

- **Run**: `af3bf8f7-d155-4e18-a5b0-48a683f5a647`.
- **Terminal state**: `needs_attention`.
- **Terminal code**: `TYPE_BUILD_ARTIFACT_FAILED`.
- **Root diagnostic**: `VITE_NODE_SPAWN_EPERM` — a Windows-specific child-
  process spawn denial (`spawn EPERM`) inside Vite's own
  `windowsSafeRealPathSync`/`optimizeSafeRealPathSync` helper, surfaced
  while `vite.config.ts` loads.
- **Stage**: `building` — the clean-build step
  (`build_runner.py::run_clean_build`) inside the run's isolated generation
  workspace, before any generated application code is evaluated.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type BuildInvocation
         (repo_dir, build_command, concurrent_process_count, prior_attempt_duration_ms)
  OUTPUT: boolean

  RETURN input.build_command_output CONTAINS "spawn EPERM"
         AND input.build_command_output CONTAINS_ONE_OF
             ["windowsSafeRealPathSync", "optimizeSafeRealPathSync"]
END FUNCTION
```

This is the same predicate stated in full, with its confirmed-unreproducible
status explained, under "Testing Strategy" → "Bug Condition — formal
specification, stated honestly as unconfirmed." It is repeated here only as
the Bug Details anchor `bugfix.md` clauses 1.1/1.2 describe; see that
section for why no concrete input could be found that satisfies it during
this design phase.

### Examples

- **Original failure (`bugfix.md` 1.1)**: run `af3bf8f7-...` halts at
  `needs_attention` with `TYPE_BUILD_ARTIFACT_FAILED` /
  `VITE_NODE_SPAWN_EPERM` during the `building` stage — expected: reach
  `ready` with a real `active_preview`; actual: stopped short, no confirmed
  root cause at the time.
- **Retry asymmetry (`bugfix.md` 1.2)**: a verify-stage retry against the
  same run fails again in ~30s versus the original attempt's ~420s, with no
  diagnostic step telling an operator whether retrying, restarting native
  services, or something else is the correct recovery action.
- **Unproven frontend/backend integration (`bugfix.md` 1.3)**: the already-
  implemented `GenerationStage.tsx` stepper/preview/traceability UI has
  never been confirmed against a real authenticated-browser run driven by a
  real completed backend generation.
- **Missing estimate (`bugfix.md` 1.4)**: milestone progress renders with no
  estimated remaining/total time, since no such field exists anywhere today.
- **Single-pack risk (`bugfix.md` 1.5)**: reliability diagnosis has so far
  used only one historical Build Preparation pack, leaving open whether a
  fix would be over-fit to that one input.

## Expected Behavior

Per `bugfix.md` 2.1/2.2, restated here as this bugfix's success definition
rather than re-derived:

> 2.1: the system SHALL have a conclusively determined root cause for the
> `VITE_NODE_SPAWN_EPERM` failure mode, SHALL apply a fix appropriate to
> that root cause, and SHALL allow the clean build to complete for a valid
> Build Preparation input without manual intervention.
>
> 2.2: a full Code Generator pipeline run against a valid Build Preparation
> brief pair SHALL reach `CodeGeneratorSessionStatus.ready` (or
> `DevelopmentRunStatus.ready`) with a real, browser-loadable
> `active_preview`, within the 5-full-pipeline-call budget.

The concrete, checkable form of this expectation is Correctness Properties
1 and 4 below, and the "Fix Checking" pseudocode under "Testing Strategy."
Because this design phase's investigation (see "Hypothesized Root Cause")
found the clean build already completing without manual intervention under
every condition tested, satisfying 2.1/2.2 does not require a spawn-layer
code change — only the diagnostic-context, timing, and estimated-time
additions in "Fix Implementation," proven against a real run per the
"Authenticated End-to-End Verification Plan" and a second pack per the
"Second-Pack Generalization Plan." What must NOT change while reaching this
behavior is documented separately, per-clause, in "Preservation
Requirements (Unchanged Behavior)" below.

## Hypothesized Root Cause

**Stated up front, as the actual finding of this design phase:** the
hypothesized root cause of the `af3bf8f7-...` failure is a **transient,
contention-driven spawn failure, not reproduced under empirical testing** —
not a confirmed code defect in this codebase's spawn path, the isolated
generation workspace, or a systemic machine-level Node/Vite/antivirus
problem. This is a legitimate hypothesized root cause in its own right, not
a placeholder standing in for one; the rest of this section is the
empirical investigation that led to it, retained in full because it is the
evidence for the hypothesis, not incidental detail.

### What was reproduced, concretely, in this design phase

All commands below were run directly against
`.workspace/code-generator-generation/af3bf8f7-d155-4e18-a5b0-48a683f5a647/repo`
— the literal isolated generation workspace of the failed run, whose
`node_modules` and `vite.config.ts` were never deleted since 2026-09-14, so
this is the closest possible repro of the original failure, not a
reconstruction.

| # | Command | Path | Result |
|---|---|---|---|
| 1 | `npm run build` | Plain PowerShell, in `repo/` | **Success**, 9.02s, produced `dist/index.html` + CSS + JS chunks |
| 2 | `npx vite build --configLoader runner` | Plain PowerShell, in `repo/` | **Success**, 2.93s |
| 3 | `process_runner.run_command(["npm.cmd", "run", "build"], cwd=repo, ...)` — the exact function `build_runner.py` calls, called directly from a Python one-liner | Programmatic, through the actual harness code, no shell | **Success**, `returncode=0`, `timed_out=False`, 3.58s, full Vite success output captured in `ProcessResult.combined_output` |
| 4 | `npm create vite@latest -- --template react-ts` + `npm install` + `npm run build` | Fresh scratch project, `%TEMP%\vite-scratch-diag`, entirely outside any generation workspace | **Success**, 521ms |

Machine state at the time of test #3/#4: `Get-Process` showed **8 active
`codex` processes and ~24 `node`/`node_repl` processes** running
concurrently — i.e., this diagnostic ran under real, heavy, concurrent
multi-agent build/process load, the same category of condition the original
2026-09-14 handoff document explicitly flagged as its leading suspicion in
its own §5 ("worth investigating whether the other session(s) are also
running builds/npm processes concurrently right now, which on a single
Windows machine can plausibly cause exactly this kind of child-process-
spawn contention"). Despite that load, all four reproductions succeeded.

`node --version` → `v25.1.0`, `npm --version` → `11.6.2`, both resolving
cleanly via `where.exe` to `C:\Program Files\nodejs\`. No environment
degradation was observed.

### Mapping to the three candidate causes from the task

- **(a) something specific to how this codebase spawns child processes**
  (missing `shell=True`, a stripped environment variable, a cwd/path issue)
  — **not observed**. Test #3 ran through the literal harness code path
  (`process_runner.run_command`, with its real Windows
  `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW` flags and its real
  environment-variable stripping) and succeeded identically to the plain
  shell invocation in test #1. If (a) were the true cause, test #3 should
  have failed while test #1 succeeded; it did not.
- **(b) something specific to the isolated generation workspace itself**
  (path length, path characters, antivirus/indexer lock on that specific
  tree, inherited permissions) — **not observed**. The workspace path is 132
  characters (`Get-Location` measured), nowhere near Windows' 260-character
  legacy limit, and contains no unusual characters. Tests #1–#3 all ran
  *inside* this exact directory and all succeeded. If (b) were the true
  cause, tests #1–#3 should all have failed identically while test #4 (a
  different directory) succeeded; instead all four succeeded.
- **(c) a genuinely systemic, currently-active machine-level Node/Vite/
  antivirus problem** — **not observed**. Test #4, a fresh scratch Vite
  project sharing nothing with the generation workspace, also built cleanly,
  and did so under the same concurrent-load conditions as tests #1–#3.

**Conclusion: none of (a)/(b)/(c) reproduces today.** The most consistent
reading of the evidence — the original failure's own symptom shape (a
build-config-load-time `spawn EPERM`, not a content-dependent failure;
identical failure on retry in ~30s vs. the original ~420s, i.e., an
immediate spawn-level failure rather than something re-derived from
generation content) plus this design phase's inability to reproduce it under
comparable or heavier concurrent load — is a **transient, contention-driven
spawn failure specific to the exact moment of the original run**, most
likely aggravated by the same concurrent multi-agent build activity the
original handoff's §5 documented as actively occurring in that exact time
window (`git log` showed commits landing from three different AI sessions
within minutes of the failure). This is not a provable claim — a transient
race condition cannot be reproduced on demand by definition — but it is the
only hypothesis consistent with every observation collected, and no
alternative hypothesis survived a direct, harness-faithful repro attempt.

### What this means for the fix, honestly

Per the task's own instruction ("do not propose a fix for a cause you didn't
actually observe... design the safest bounded next diagnostic step instead
of a blind fix"), **this design proposes no code change to
`process_runner.py`, `build_runner.py`'s spawn/command logic,
`vite.config.ts`, or the scaffold's `package.json`**, because doing so would
be patching a failure this design phase could not reproduce, against a root
cause it could not confirm. `build_runner.py` already has the correct
posture for this failure class: `is_vite_windows_spawn_failure` already
classifies it as `owner="infrastructure"` rather than a source defect, so it
already does not consume repair budget or misattribute the failure to
generated code.

What this design *does* add (see "Fix Implementation" below) is a bounded,
purely additive diagnostic improvement: capture and surface enough
concurrent-process context on any *future* `VITE_NODE_SPAWN_EPERM`
occurrence that the next person investigating does not have to re-run this
same multi-step manual investigation to tell "transient contention" apart
from "the bug is real and back." This directly serves 2.1's requirement for
a "conclusively determined root cause" for the failure *mode*, without
requiring a code change to a spawn path this design could not fault.

**Scope flag for the reader:** requirements clause 2.1 asks for the fix to
"allow the clean build to complete... without manual intervention." Given
this design phase's finding, the build already does complete without manual
intervention under every condition tested. The requirements did not
anticipate a "root cause is transient/unreproducible" outcome; this design
does not silently expand scope to invent a spawn-layer change to satisfy the
letter of 2.1 when no defect was found to fix. Section "Fix Checking" below
defines exactly how 2.1/2.2 are still satisfied on their own terms — a real
full-pipeline run reaching `ready` — using the diagnostic addition as a
safety net rather than a preventive rewrite.

## Preservation Requirements (Unchanged Behavior)

Restated per-clause from `bugfix.md` §"Unchanged Behavior", with the exact
files/functions this design must not alter:

| Clause | Must-not-change | Enforced by not touching |
|---|---|---|
| 3.1 | Every existing blocking check outside the Windows-spawn path (admission, authorization/fencing, checkpoint integrity, dependency install success, source contract validation, runtime/browser verification, atomic preview promotion) | `final_source_validation.py`, `verification_plan.py`, `design_realization.py`, `checkpoint`-related code, all authorization/fencing modules — none are edited by this design |
| 3.2 | `preview_first_acceptance` default (`false` in `CodeGeneratorVerificationConfig`, `settings.py:754`); strict-profile behavior unchanged | `settings.py`'s `preview_first_acceptance: bool = False` default is untouched; the `true` value already lives only in `config/app.native.toml`, an existing overlay this design does not modify |
| 3.3 | `CODE_GENERATOR_BRIEF_INVALID` / not-ready rejection when Build Preparation isn't `READY` or hashes mismatch | No change to `service.py::start`'s brief-pair validation gate |
| 3.4 | Never auto-chain from Build Preparation approval | No change to any stage-transition/auto-advance wiring; the explicit `/start`, `/retry`, `/regenerate` session routes remain the only entry points |
| 3.5 | `GenerationStage.tsx`'s already-shipped elements — verified/candidate badges, traceability drawer's four ID fields, "Copy diagnostic report", crossfade with `prefers-reduced-motion` — behave exactly as in commits `d0894d6`/`ecb8257` | This design's frontend changes are strictly additive (one new estimated-time element) and remove nothing already confirmed present in the read source; no existing JSX block, handler, or CSS rule for these elements is edited |
| 3.6 | One-immutable-generation-variant / post-success read-only entitlement rules (`PortfolioReadOnlyError`, `GenerationVariantLockedError`, `EntitlementBindingConflictError`) | No change to any auth/entitlement module |
| 3.7 | No production deployment, DNS, Azure, or multi-account browser work performed or claimed | This design's "Authenticated End-to-End Verification" plan is explicitly scoped to the local native stack only |

A concrete verbatim check I already performed against the handoff's own
claim under 3.5: the handoff document names four still-open frontend
defects reviewed in the same commit range. Reading the current
`GenerationStage.tsx` confirms the Publish/Deploy UI removal and the
"already implemented" milestone stepper/traceability drawer/verified-vs-
candidate distinction are all present in current source exactly as the
handoff described them as fixed — meaning 3.5's preservation boundary
starts from a source state already consistent with what `bugfix.md` says is
"already implemented," not from a stale prior state.

## Correctness Properties

Property 1: Bug Condition — Build reaches `ready` for any valid Build
Preparation input on this development machine

_For any_ full Code Generator pipeline run (`plan → acquire → generate →
verify`) against a valid, hash-matching, `READY` Build Preparation brief
pair, where the run's own clean build step (`build_runner.py::run_clean_build`)
is invoked through the harness's real `process_runner.run_command` path with
no other change to spawn behavior, the fixed system SHALL either (a) reach
`CodeGeneratorSessionStatus.ready` / `DevelopmentRunStatus.ready` with a
real, Chromium-verified, browser-loadable `active_preview`, or (b) if a
`VITE_NODE_SPAWN_EPERM` diagnostic is emitted, SHALL attach concurrent-
process-count and prior-attempt-duration context to that diagnostic
sufficient to distinguish a transient recurrence from a persistent one
without requiring a fresh manual investigation.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation — Every non-spawn-diagnostic code path is
byte-identical in behavior

_For any_ input exercising `build_runner.py`, `process_runner.py`, or any
other file this design does not modify (see Preservation Requirements
table), the fixed system SHALL produce exactly the same result as the
current system, since this design makes no code change to the spawn,
build-command-resolution, or verification-gate logic itself — only an
additive diagnostic-context capture on the existing
`VITE_NODE_SPAWN_EPERM` branch inside `_run()`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6, 3.7**

Property 3: Estimated-time indicator never fabricates a value

_For any_ session state the frontend renders during an active
(`working`-state) Code Generator run, the displayed estimated-time value
SHALL be derived only from `config/app.toml`'s `worker.job.kind_timeouts`
`code_generator.*` budgets and the run's own `started_at`/`coordinator_stage`
— both real, already-persisted, non-hardcoded values — and the system SHALL
NEVER render a constant or arbitrary percentage/time value that does not
trace back to one of these two sources.

**Validates: Requirements 2.4**

Property 4: Fix generalizes across structurally different Build Preparation
input

_For any_ two valid, `READY`, hash-matching Build Preparation brief pairs
that differ in route count, section count, navigation contract, and subject-
matter content (not merely in name/persona text), running the full Code
Generator pipeline against each SHALL each independently reach `ready` (or
an independently-diagnosed, non-Windows-spawn failure fully root-caused on
its own terms), demonstrating the result is not overfit to the one pack
already exercised by run `af3bf8f7-...`.

**Validates: Requirements 2.5**

## Fix Implementation

### 1. Diagnostic context capture on `VITE_NODE_SPAWN_EPERM` (backend)

**File**: `src/oryxenai/agents/code_generator/core/build_runner.py`

**Function**: `_run()` (the branch that currently constructs the
`_VITE_WINDOWS_SPAWN_DENIED` diagnostic, around the existing
`"spawn eperm" in normalized_output` check)

**Change**: When this branch fires, additionally capture, best-effort and
non-blocking:
- A count of currently-running `node`/`npm` OS processes at the moment of
  failure (a single `psutil`-free, stdlib-only process enumeration; Windows
  via `tasklist`, POSIX via `/proc` or `ps`, wrapped in the same
  best-effort-only posture `code generator issues.md` §2.2 already
  documents for Windows enumeration denials — a failure to enumerate must
  never itself fail the diagnostic).
- The elapsed wall-clock duration of *this* verify attempt versus the
  elapsed duration of the *previous* verify attempt on the same run, if one
  exists (`run.stage_durations_ms`, see item 3 below — this is exactly the
  historical-timing gap the original handoff's own observation, "~30s vs.
  ~420s", was reasoning from informally; this makes that comparison a first-
  class, inspectable field instead of something an operator has to notice
  in raw logs).

This information is attached to the existing `Diagnostic.normalized_message`
(already free text, already `owner="infrastructure"`) — no new diagnostic
code, no new schema field, no change to how `is_vite_windows_spawn_failure`
classifies the failure, and no change to whether it consumes repair budget.
This satisfies Property 1's "attach context" branch without touching spawn
behavior itself, keeping Property 2 (preservation) intact.

**Why this is the correct-sized response given the root-cause finding**:
adding retry logic, alternate spawn flags, or a `shell=True` fallback would
be treating an unreproduced failure as a confirmed defect. Adding
observability is the "safest bounded next diagnostic step" the task
explicitly asked for when a clean repro isn't available either way — and
here a repro *was* available, and it was clean (no failure), which is an
even stronger reason not to touch the mechanism itself.

### 2. Populate `stage_durations_ms` (backend — supports both diagnostics and the time estimate)

**Files**:
`src/oryxenai/agents/code_generator/core/coordinator.py` (stage-transition
recording), `src/oryxenai/agents/code_generator/core/development_schemas.py`
/`session_schemas.py` (already declare the field; no schema change needed).

**Change**: At each stage transition the coordinator already performs
(`plan → acquire → generate → verify → preview`), record the elapsed
milliseconds for the stage that just completed into the run's existing
`stage_durations_ms` dict, keyed by stage name, and persist it through the
same `compare_and_swap` update path the coordinator already uses for
`coordinator_stage`/`status`. This is populating a field that already
exists on three schemas but has zero writers today — not introducing a new
concept, just wiring up dead schema to the transition points that already
exist.

This is what makes the "previous verify attempt duration" comparison in
item 1 possible, and is the first building block toward a future,
better-than-config-budget time estimate (observed historical duration)
without this bugfix depending on that richer estimate to satisfy 2.4 today
(see item 3 — the estimate itself still uses config budgets as its primary
source, since `stage_durations_ms` starts empty on every fresh deployment
and only accumulates within a single run's own lifetime, not across runs).

### 3. Estimated-time computation (backend-computed, frontend-consumed)

**Where the estimate is computed**: **Backend**, inside
`service.py::get_state`'s existing `payload["progress"]` construction (the
same dict that already carries `coordinator_stage`, `current_attempt`,
`plan_summary`, `source_summary`). Computing it backend-side (not frontend-
only) keeps `config/app.toml`'s stage-budget values — which are
server-only configuration, never sent to the browser today — as the single
source of truth, and avoids duplicating the `worker.job.kind_timeouts` →
`code_generator.*` key-mapping logic in TypeScript.

**Real, non-hardcoded source, in priority order**:
1. If the run has at least one completed stage with a recorded
   `stage_durations_ms` entry for that stage name (from item 2), use that
   observed duration for stages already completed in *this* run.
2. For any stage not yet completed in this run, fall back to
   `settings.worker.job.kind_timeouts["code_generator.<stage>"]` (the
   already-configured, already-loaded `code_generator.plan` /
   `.acquire` / `.generate` / `.verify_and_preview` values) as a budget
   ceiling, not a fabricated guess — it is what this codebase's own worker
   uses as the authoritative maximum for that exact stage today.
3. Sum: elapsed-so-far (from `started_at` to now) is compared against the
   sum of (observed-durations-for-completed-stages +
   remaining-configured-budgets-for-incomplete-stages) to produce
   `estimated_remaining_ms` and `estimated_total_ms`.

**Shape added to the API response** (additive field on the existing
`payload["progress"]` dict, no new endpoint, no schema-breaking change):

```json
"progress": {
  "coordinator_stage": "generate",
  "current_attempt": 1,
  "plan_summary": {...},
  "source_summary": {...},
  "stage_estimate": {
    "elapsed_ms": 184000,
    "estimated_total_ms": 8100000,
    "estimated_remaining_ms": 7916000,
    "source": "configured_budget"
  }
}
```

`source` is one of `"configured_budget"` (falls back entirely to
`worker.job.kind_timeouts`) or `"observed_and_budget"` (mixes at least one
real `stage_durations_ms` entry with remaining-stage budgets) — this lets
the frontend (or a future debugging session) tell at a glance whether a
given estimate is budget-only or partially observed, without guessing.

**Frontend consumption**: `frontend/src/data/adapters/generation.ts`'s
`adaptCodeGenerator()` reads `raw.progress.stage_estimate` (mirroring how it
already reads `raw.progress.plan_summary`/`raw.progress.source_summary`) and
adds `estimatedRemainingMs`/`estimatedTotalMs`/`estimateSource` to
`GenerationViewModel`. `GenerationStage.tsx` renders this as a small,
human-readable string (e.g. "About 6 minutes remaining") next to the active
milestone in the stepper, only while `isWorking` — never during `available`,
`attention`, or `complete` states, since an estimate is meaningless once the
run isn't actively progressing. Formatting (`ms` → "About N minutes") is a
small pure frontend helper; no additional backend computation needed for
display formatting.

This satisfies 2.4 exactly: the source is real and configured
(`config/app.toml`), never an arbitrary constant, and Property 3 is directly
checkable by inspecting the two allowed sources.

### 4. Frontend: no code change required for the two "already fixed" defects

The handoff document (§2) named two frontend defects: leftover Publish/
Deploy UI, and a missing stage-transition crossfade. This design phase read
the current `GenerationStage.tsx` in full and confirmed **neither defect is
present in current source** — there is no "Publish"/"Deploy" string
anywhere in the file, and the action set already matches the truthful
"Open verified preview" / "Regenerate" / "Retry" pattern the handoff
prescribed as the fix. `bugfix.md` clause 3.5 itself already documents this
as "already implemented in commits `d0894d6` / `ecb8257`." This design adds
no work item for these two defects; doing so would contradict both the
read source and the requirements' own preservation clause 3.5.

## Authenticated End-to-End Verification Plan (2.3)

**Setup required**: Per AGENTS.md's canonical commands and
`scripts/run-native.ps1`'s own service list, "real running native stack"
means three independently-started native processes, not Docker:

```powershell
.\scripts\run-native.ps1 migrate   # once, before first run
.\scripts\run-native.ps1 dev       # starts api + worker + preview, each backgrounded hidden
```

`dev` fans out to three child `powershell.exe` processes (`api`, `worker`,
`preview`), each loading `config/app.native.toml` as
`OryxenAI_CONFIG_OVERLAY`. This is also the exact overlay this design's root-
cause analysis already confirmed configures `build_command = ["npm", "run",
"build"]` and `preview_first_acceptance = true` — i.e., the E2E run in this
section exercises the same configuration this design's diagnostics were run
against, not a different one.

**Journey to walk, browser-authenticated, against `/app` (never `/dev/...`
harness pages)**:
1. Sign in (Google via Supabase), reach an owned portfolio session with
   Content Architect, Visual Design Director, and Build Preparation already
   approved (reuse an existing approved session if one exists locally, to
   avoid spending model-call budget on upstream stages that are out of this
   bugfix's scope).
2. Click "Generate Portfolio" — confirm the request hits
   `POST /api/v1/sessions/{session_id}/code-generator/start` with an
   `Idempotency-Key` header (network tab).
3. Watch the milestone stepper progress through Plan → Acquire → Build →
   Verify → Preview, confirming each transition corresponds to a real
   `coordinator_stage` change in the polled state response (network tab),
   not a client-side timer.
4. Confirm the new estimated-time text appears during `working` state and
   changes/decreases plausibly over the course of the run.
5. On completion, confirm the preview iframe loads a real
   `active_preview.url`, confirm the "Open verified preview" link opens that
   same URL in a new tab with a 200 response.
6. Open the traceability drawer; confirm Trace ID, Active Job ID, Session
   ID, and Error Code (or its absence on a clean success) are all present
   and non-placeholder; exercise "Copy diagnostic report".

**Pass/fail definition** (lifted directly from `bugfix.md` 2.3 and the
handoff's own Phase 3 definition of done, not invented fresh):
- **Pass**: zero uncaught browser console errors during the entire journey;
  the preview iframe renders real content (not a blank/error frame); all
  API/preview network requests return 2xx; the milestone stepper's active
  stage always matches the polled `coordinator_stage`; the estimated-time
  text is present during `working` and traces to `stage_estimate.source`
  being one of the two allowed values.
- **Fail**: any uncaught console error, any non-2xx response on the
  documented journey, a stepper stage that visibly disagrees with the
  polled state, or an estimated-time value with no traceable `source`.

This walkthrough consumes one slot of the requirements' 5-full-pipeline-call
budget (2.2) if run against a fresh `/start`, or zero slots if reusing an
already-`ready` session purely to inspect drawer/preview behavior — the
tasks phase should prefer reusing an existing `ready` run for steps 5-6 and
reserve a fresh `/start` specifically for confirming the stepper/estimate
behavior live, to conserve budget.

## Second-Pack Generalization Plan (2.5)

**What a second valid pack actually is, confirmed by reading source and
disk**: `development_input.py::_mirror_entries()` probes
`output/build-preparation` (the `build_preparation_mirror_root` config
default) for directories containing both
`content-and-narrative-brief.md`/`visual-and-build-brief.md`. Four such
directories exist on disk today beyond the one already consumed by
`af3bf8f7-...`:

| Mirror directory | run_id | Persona / domain | Sections | Nav contract size |
|---|---|---|---|---|
| `10-05-14-09-ea2ff472` (already consumed) | `ea2ff472-...` | Elena Rostova, Quantitative Trading Systems Architect | 7 | 8 destinations |
| `16-33-12-09-0ffb7b6e` | `0ffb7b6e-d712-440f-a768-cf9b6f0340a5` | Dr. Aditya Vikram Joshi, Agentic AI Systems Architect | 5 | 6 destinations |
| `19-21-13-09-1f16420f` | `1f16420f-...` | (not yet inspected — candidate) | — | — |
| `21-08-11-09-b09b2506` | `b09b2506-...` | (not yet inspected — candidate) | — | — |

This design confirmed by direct file read that `0ffb7b6e` is genuinely
structurally different from the already-consumed pack — different content
hash, different route/section count, different navigation contract, and a
different professional domain (quant trading vs. agentic AI) — not a
re-skinned name swap. This is a real second data point, not an assumed one.

**How to run it**: `development_input.py::from_build_preparation_mirror`
already accepts an explicit `pack` argument by directory name (not only
`"latest"`/`"best"`), so the tasks phase can address this exact pack
directly:

```
POST /api/v1/development/code-generator/runs/from-build-preparation
{"pack": "16-33-12-09-0ffb7b6e"}
```

**Pass/fail for generalization**: per 2.5, this run must independently
reach `ready` (or an independently-diagnosed, non-Windows-spawn failure
fully root-caused on its own merits — 2.6 applies here too, since any new
`needs_attention` on this second pack is a distinct defect class this
bugfix must root-cause with the same rigor as the primary run, not wave
through). This run consumes one of the 5 full-pipeline-call slots.

## Testing Strategy

### Validation Approach

This bugfix's validation differs from a typical bug condition workflow in
one respect worth stating plainly: the root-cause investigation itself
already constitutes the "exploratory bug condition checking" phase, and it
did not surface a reproducible bug condition to check against on unfixed
code. What follows adapts the methodology to that finding rather than
pretending a `C(X)` bug condition was confirmed when it was not.

### Exploratory Bug Condition Checking — already performed during design

**Goal**: Surface counterexamples demonstrating the bug BEFORE implementing
any change.

**What was actually run** (see "Hypothesized Root Cause" for full detail): the
exact failing build command, in the exact failed run's own workspace,
through (1) a plain shell, (2) `npx` directly, (3) the literal
`process_runner.run_command` harness function, and (4) a fresh scratch Vite
project as a machine-health control. All four succeeded.

**Result**: **No counterexample was found.** This refutes the possibility
of treating the spawn failure as a currently-reproducible, deterministic bug
condition on this machine today. It does not refute that the original
failure happened — the handoff document's own captured stack trace and
terminal code are real, first-hand evidence of a real event — but this
design phase could not turn that event into a repeatable `isBugCondition`
predicate, and says so rather than fabricating one.

### Bug Condition — formal specification, stated honestly as unconfirmed

```
FUNCTION isBugCondition(input)
  INPUT: input of type BuildInvocation
         (repo_dir, build_command, concurrent_process_count, prior_attempt_duration_ms)
  OUTPUT: boolean

  // This predicate could not be made to return true against any concrete
  // input tried during this design phase, including inputs designed to
  // maximize the chance of reproducing the original failure (same
  // workspace, same command, comparable-or-heavier concurrent load).
  // It is retained in this form, rather than removed, because it documents
  // the exact shape of input the original failure occurred on, for anyone
  // who does encounter a fresh VITE_NODE_SPAWN_EPERM occurrence after this
  // bugfix ships and needs to compare it against this design's own failed
  // repro attempts.
  RETURN input.build_command_output CONTAINS "spawn EPERM"
         AND input.build_command_output CONTAINS_ONE_OF
             ["windowsSafeRealPathSync", "optimizeSafeRealPathSync"]
END FUNCTION
```

### Fix Checking

Since no reproducible bug condition exists to check a fix against, "fix
checking" for this bugfix takes the form the requirements themselves
define success as (2.1/2.2): a real full-pipeline run reaching `ready`.

**Pseudocode:**
```
run := startFullPipeline(validBuildPreparationPack)
WAIT UNTIL run.status IN {ready, needs_attention}
IF run.status == needs_attention AND run.terminal_failure.code == "VITE_NODE_SPAWN_EPERM" THEN
  ASSERT run.terminal_failure.normalized_message CONTAINS concurrent_process_context
  // The diagnostic-context addition (Fix Implementation item 1) is what
  // Property 1 actually guarantees on this branch — not that the branch
  // never fires again, which this design cannot promise.
ELSE
  ASSERT run.status == ready
  ASSERT run.active_preview.url is browser-loadable
END IF
```

**Test Cases**:
1. **Primary pack, fresh `/start`**: `10-05-14-09-ea2ff472`'s content is
   already consumed by `af3bf8f7-...`; the tasks phase should use
   `/retry` on the existing `af3bf8f7-...` run first (cheapest option — no
   new full-pipeline call, since retry-from-`needs_attention` re-enters at
   the failed stage per the coordinator's existing resume semantics) before
   consuming a fresh `/start` slot.
2. **Second pack, fresh `/start`**: `16-33-12-09-0ffb7b6e`, per the
   Second-Pack Generalization Plan above. Consumes one full-pipeline slot.
3. **Diagnostic-context assertion**: if either run 1 or 2 hits
   `VITE_NODE_SPAWN_EPERM` again, assert the new context fields (concurrent
   process count, prior-duration comparison) are present and non-empty in
   the persisted `terminal_failure`.

### Preservation Checking

**Goal**: Verify every file this design does not modify behaves identically
before and after.

**Pseudocode:**
```
FOR ALL existing_unit_test IN {test_build_runner.py, test_process_runner-adjacent suites,
                                 test_phase2_design_neutral.py, code_generator integration suite} DO
  ASSERT test_passes_before_change(existing_unit_test)
  ASSERT test_passes_after_change(existing_unit_test)
END FOR
```

**Testing Approach**: Because the only backend code change is additive
(new context fields on an existing diagnostic message, a new writer for an
already-declared-but-unused schema field, a new read-only `stage_estimate`
sub-object under an existing dict key), the existing test suite for
`build_runner.py`, `process_runner.py`, and `service.py::get_state` should
require zero modification to keep passing — this is itself the preservation
check. Any existing test that needs to change to keep passing is a signal
this design's "additive only" framing was wrong somewhere and needs
re-examination before proceeding, not a test to simply update.

**Test Cases**:
1. **`test_build_runner.py`'s existing `spawn EPERM` fixture test**
   (confirmed present at `tests/unit/agents/code_generator/test_build_runner.py`,
   asserting `is_vite_windows_spawn_failure` classification) must continue
   to pass unmodified — the classification logic itself is untouched.
2. **`service.py::get_state`'s existing response-shape tests** must
   continue to pass unmodified for any session that has no `stage_estimate`
   data yet (e.g., a `not_started` session) — the new field is additive and
   optional.
3. **Frontend**: `frontend/`'s existing Vitest suite for
   `adaptCodeGenerator()` must continue to pass unmodified for any raw
   payload lacking `progress.stage_estimate` — the adapter must treat its
   absence as "no estimate available," not an error.

### Unit Tests

- `build_runner.py`: a new test asserting that when the `spawn eperm` /
  `windowssaferealpathsync` branch fires, the resulting `Diagnostic.
  normalized_message` contains the concurrent-process-count and prior-
  duration context fields (using a fixture-injected fake process-count
  function so the test itself has no real OS/process dependency).
- `coordinator.py`: a new test asserting a stage transition writes a
  non-negative millisecond duration into `stage_durations_ms` for the stage
  that just completed, and leaves other stages' entries untouched.
- `service.py`: a new test asserting `get_state`'s `payload["progress"]
  ["stage_estimate"]` uses `source: "configured_budget"` when
  `stage_durations_ms` is empty, and `source: "observed_and_budget"` when at
  least one stage has a recorded duration; and that the computed
  `estimated_total_ms` for an all-budget case equals the sum of the
  relevant `worker.job.kind_timeouts` entries actually present in test
  settings (never a value not traceable to that config).
- Frontend (`generation.test.ts` or equivalent): a new test asserting
  `adaptCodeGenerator()` maps `progress.stage_estimate` into
  `estimatedRemainingMs`/`estimatedTotalMs`/`estimateSource` when present,
  and leaves those fields undefined (not zero, not a fabricated default)
  when absent.

### Property-Based Tests

- **Property 3 (no fabrication)**: generate random combinations of
  `stage_durations_ms` entries (0 to 4 stages populated, each a random
  non-negative duration) and random `worker.job.kind_timeouts` configs;
  assert the computed `estimated_total_ms` is always exactly reconstructible
  as `sum(observed durations for completed stages) + sum(configured budgets
  for incomplete stages)` — i.e., property-test the arithmetic invariant
  directly, since this is the concrete, checkable form of "never a
  fabricated constant."
- **Property 2 (preservation)**: generate random `ProcessResult` outputs
  (varying `returncode`, `combined_output` content, `timed_out`) that do
  NOT match the `spawn eperm` / `windowssaferealpathsync` pattern; assert
  `_run()`'s diagnostic-construction branch for this bugfix's new code never
  executes for any of them (i.e., the new context-capture code is reachable
  only from the exact existing classification branch, never a broader one).

### Integration Tests

- Full pipeline run against `af3bf8f7-...`'s existing checkpoint state via
  `/retry`, asserting it reaches `ready` (fix checking, test case 1).
- Full pipeline run against the second pack (`16-33-12-09-0ffb7b6e`) via a
  fresh `/start`, asserting it reaches `ready` or an independently-diagnosed
  non-spawn failure (fix checking, test case 2; generalization plan).
- `service.py::get_state` integration test against a real durable run row
  transitioning through stages, asserting `stage_estimate.elapsed_ms`
  increases monotonically across polls and `source` flips from
  `configured_budget` to `observed_and_budget` after the first stage
  completes.
