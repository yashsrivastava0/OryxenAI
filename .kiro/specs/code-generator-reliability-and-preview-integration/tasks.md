# Implementation Plan

## Overview

This task list implements `design.md`'s Code Generator reliability and
preview-integration bugfix: additive diagnostic context for the
`VITE_NODE_SPAWN_EPERM` branch, a backend-computed `stage_estimate` derived
only from recorded stage durations and configured job-kind timeout budgets,
and the frontend consumption/rendering of that estimate. Work is organized
into four phases — backend additive changes, backend unit/property tests,
frontend consumption, and verification — with verification deliberately
last since it is the only phase that spends the requirements' bounded
full-pipeline-call budget.

This plan implements `design.md`'s finding that no reproducible bug
condition exists for `VITE_NODE_SPAWN_EPERM` on this machine today (see
"Hypothesized Root Cause" and "Bug Condition — formal specification, stated
honestly as unconfirmed"). Because of that finding, this bugfix does not
follow the standard Property 1 = exploration-test-fails-then-passes shape.
Instead:

- **Property 1 (Bug Condition)** is satisfied by the diagnostic-context
  capture itself (Fix Implementation item 1) — there is no separate
  "exploration test that fails on unfixed code," because the design phase
  already ran that exploration (four independent reproduction attempts, all
  succeeded) and documented it in `design.md`. Task 1 below is that
  property's implementation and its own verification in one, per
  `design.md`'s explicit adaptation of the methodology.
- **Property 2 (Preservation)** is a true preservation property in the
  standard sense and gets a standalone task, ordered after the additive
  changes exist (since "preservation" here means "existing tests still pass
  and the new code path never fires outside its exact existing
  classification branch," which can only be checked once that code exists).
- **Property 3 (no fabrication)** and **Property 4 (generalization)** each
  get their own tasks, per `design.md`'s Correctness Properties section.

Every task below cites the `bugfix.md` requirement clause(s) and/or
`design.md` Correctness Property it implements. Tasks are grouped into
phases; **Phase D (verification)** must run last and is the only phase that
consumes the requirements' 5-full-pipeline-call budget (`bugfix.md` 2.2).

## Task Dependency Graph

```
Phase A — Backend additive changes (no shared-state ordering constraint
          between A1/A2, but A3 depends on A2's field existing)
  A1. Diagnostic context capture in build_runner.py  ─┐
  A2. Populate stage_durations_ms in coordinator.py   ─┼─→ A3. stage_estimate
                                                         │   in service.py::get_state
                                                         │   (depends on A2)
       (A1 is independent of A2/A3 — different file,     │
        different code path, no shared field)            │
                                                          ▼
Phase B — Backend unit tests (each depends on its own Phase A task existing)
  B1. Unit tests for A1 (build_runner.py)      ← depends on A1
  B2. Unit tests for A2 (coordinator.py)       ← depends on A2
  B3. Unit tests for A3 (service.py)           ← depends on A3
  B4. Property-based test — Property 3 (no fabrication)   ← depends on A3
  B5. Property-based test — Property 2 (preservation)     ← depends on A1, A2, A3

Phase C — Frontend additive change (depends on A3's response shape existing,
          since the adapter reads progress.stage_estimate)
  C1. Frontend adapter: read stage_estimate       ← depends on A3 (response shape)
  C2. Frontend unit test for C1                   ← depends on C1
  C3. GenerationStage.tsx: render estimate in isWorking only ← depends on C1

Phase D — Verification (consumes 5-full-pipeline-call budget; runs LAST,
          after A/B/C are complete and unit-tested)
  D1. Authenticated end-to-end verification (bugfix.md 2.3)  ← depends on A,B,C complete
  D2. Second-pack generalization run (bugfix.md 2.5, Property 4) ← depends on A,B,C complete
  D3. Checkpoint — full suite + budget accounting              ← depends on D1, D2
```

Execution waves below group tasks that can run in parallel (no dependency
between tasks in the same wave) while respecting the dependency chain
already described in the ASCII diagram above and in each task's own
"_Depends on_" annotation:

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": [1, 2],
      "description": "Phase A backend additive changes with no shared dependency between them (A1 diagnostic context capture; A2 stage_durations_ms population)."
    },
    {
      "wave": 2,
      "tasks": [3],
      "description": "Phase A backend-computed stage_estimate; depends on task 2's stage_durations_ms field."
    },
    {
      "wave": 3,
      "tasks": [4, 5, 6, 7, 8],
      "description": "Phase B backend unit and property-based tests, each depending on its own Phase A task (1, 2, or 3)."
    },
    {
      "wave": 4,
      "tasks": [9],
      "description": "Phase C frontend adapter change; depends on task 3's backend response shape."
    },
    {
      "wave": 5,
      "tasks": [10, 11],
      "description": "Phase C frontend unit test and GenerationStage.tsx rendering, both depending on task 9."
    },
    {
      "wave": 6,
      "tasks": [12, 13],
      "description": "Phase D verification tasks; both depend on Phases A, B, and C being complete."
    },
    {
      "wave": 7,
      "tasks": [14],
      "description": "Final checkpoint; depends on tasks 12 and 13."
    }
  ]
}
```

---

## Tasks

### Phase A: Backend Additive Changes (Fix Implementation)

- [x] 1. Diagnostic context capture on the `VITE_NODE_SPAWN_EPERM` branch
  - **Property 1: Bug Condition** - Concurrent-process and prior-duration context on Vite Windows spawn denial
  - **IMPORTANT — read before starting**: per `design.md`'s "Hypothesized Root Cause" and "Bug Condition — formal specification, stated honestly as unconfirmed," no concrete input could be made to satisfy `isBugCondition` during design (four independent reproduction attempts against the exact failed run's own workspace all succeeded). There is therefore **no unfixed-code exploration test to write and watch fail** for this bugfix — do not attempt to fabricate one. This task implements Property 1's actual guarantee directly: that when the existing `VITE_NODE_SPAWN_EPERM` branch fires (on any future occurrence), the emitted diagnostic carries enough context to distinguish a transient recurrence from a persistent one.
  - In `src/oryxenai/agents/code_generator/core/build_runner.py`, inside `_run()`, extend the existing branch that currently checks `"spawn eperm" in normalized_output and ("windowssaferealpathsync" in normalized_output or "optimizesaferealpathsync" in normalized_output)` (the branch that already constructs the `_VITE_WINDOWS_SPAWN_DENIED` diagnostic)
  - Add a best-effort, stdlib-only helper that counts currently-running `node`/`npm` OS processes at the moment of failure (Windows via `tasklist`, POSIX via `/proc` or `ps`), following the same best-effort-only posture already established for Windows enumeration denials in `code generator issues.md` §2.2 — a failure to enumerate must never itself raise or fail the diagnostic construction
  - Append this process count, plus a comparison of this verify attempt's elapsed duration against the previous verify attempt's duration on the same run (read from `stage_durations_ms`, written by task 2 below), into the existing `Diagnostic.normalized_message` free-text field — no new diagnostic code, no new schema field, no change to `is_vite_windows_spawn_failure`'s classification logic or to whether the failure consumes repair budget
  - Do not add retry logic, alternate spawn flags, a `shell=True` fallback, or any other change to the spawn mechanism itself — `design.md` is explicit that doing so would be "treating an unreproduced failure as a confirmed defect"
  - _Bug_Condition: isBugCondition(input) from design.md — `input.build_command_output CONTAINS "spawn EPERM" AND CONTAINS_ONE_OF ["windowsSafeRealPathSync", "optimizeSafeRealPathSync"]`, retained as documented-but-unconfirmed per design.md_
  - _Expected_Behavior: Correctness Property 1 from design.md — "if a VITE_NODE_SPAWN_EPERM diagnostic is emitted, SHALL attach concurrent-process-count and prior-attempt-duration context... sufficient to distinguish a transient recurrence from a persistent one"_
  - _Preservation: no change to is_vite_windows_spawn_failure classification, to whether the branch consumes repair budget, or to any other diagnostic code path (Preservation Requirements 3.1 table)_
  - _Requirements: 2.1, 2.2_

- [x] 2. Populate `stage_durations_ms` at each coordinator stage transition
  - In `src/oryxenai/agents/code_generator/core/coordinator.py`'s `advance_after()`, at the point where a stage attempt is finalized (the existing `repo.finalize_stage_attempt(...)` call for the `completed_attempt_stage`) and before the next stage's attempt/job is created, compute the elapsed milliseconds for the stage that just completed
  - Persist that duration into the run's existing `stage_durations_ms` dict (already declared on `DevelopmentRunProjection`/`DevelopmentRunState`/`CodeGeneratorSessionState` per `design.md`'s Glossary — confirmed by repo-wide grep as declared-but-never-written), keyed by stage name, through the same `compare_and_swap` update the function already performs for `coordinator_stage`/`status`/`job_field` — add the new key to the existing `values: dict[str, object] = {...}` dict rather than introducing a second write
  - Ensure only the just-completed stage's entry is written; all other stages' existing entries in the dict must be left untouched (this is exactly what Property 2's preservation check will assert in task 6)
  - This task has no user-visible behavior on its own; it is the data dependency for tasks 1's prior-duration comparison and task 3's `observed_and_budget` estimate source
  - _Expected_Behavior: `design.md` Fix Implementation item 2 — "record the elapsed milliseconds for the stage that just completed into the run's existing `stage_durations_ms` dict... persist it through the same `compare_and_swap` update path"_
  - _Preservation: no new schema field (the field already exists on three schemas); no change to any other value in the `compare_and_swap` payload (Preservation Requirements 3.1, 3.4)_
  - _Requirements: 2.4 (data dependency), 2.1 (data dependency for task 1)_

- [x] 3. Backend-computed `stage_estimate` in `service.py::get_state`
  - In `src/oryxenai/agents/code_generator/service.py`'s `get_state()`, extend the existing `payload["progress"] = {...}` dict construction (currently `coordinator_stage`, `current_attempt`, `plan_summary`, `source_summary`) to add a `stage_estimate` sub-object, computed server-side only
  - Implement the three-step priority order from `design.md` Fix Implementation item 3: (1) for any stage already completed in this run, use its recorded `stage_durations_ms` entry from task 2; (2) for any stage not yet completed, fall back to `settings.worker.job.kind_timeouts["code_generator.<stage>"]` (the already-configured `code_generator.plan`/`.acquire`/`.generate`/`.verify_and_preview` budgets); (3) sum elapsed-so-far (`started_at` to now) against `estimated_total_ms` to produce `estimated_remaining_ms`
  - Emit exactly the shape design.md specifies: `{"elapsed_ms": <int>, "estimated_total_ms": <int>, "estimated_remaining_ms": <int>, "source": "configured_budget" | "observed_and_budget"}` — `source` is `"configured_budget"` only when zero `stage_durations_ms` entries exist for this run, `"observed_and_budget"` when at least one does
  - Do not add a new endpoint or change any existing key already in `payload["progress"]`; this is strictly additive to the existing dict
  - Do not compute this on the frontend — `config/app.toml`'s stage budgets are server-only configuration today and must remain so, per `design.md`'s explicit rationale for computing this backend-side
  - _Expected_Behavior: Correctness Property 3 from design.md — "the displayed estimated-time value SHALL be derived only from `config/app.toml`'s `worker.job.kind_timeouts` `code_generator.*` budgets and the run's own `started_at`/`coordinator_stage`... and the system SHALL NEVER render a constant or arbitrary... value that does not trace back to one of these two sources"_
  - _Preservation: no change to any existing key in `payload["progress"]`; new field must be additive-only so a session with no `stage_durations_ms` data (e.g. `not_started`) still returns a valid, unbroken response (Preservation Requirements 3.1)_
  - _Requirements: 2.4_
  - _Depends on: Task 2 (reads `stage_durations_ms`)_

### Phase B: Backend Unit Tests

**Test file placement**: all new backend unit tests go under
`tests/unit/agents/code_generator/`, following this project's existing
convention — confirmed by the sibling file
`tests/unit/agents/code_generator/test_build_runner.py` — never inside
`src/oryxenai/agents/code_generator/` itself, per AGENTS.md's "no test files
exist inside any agent directory."

- [x] 4. Unit tests for diagnostic context capture (task 1)
  - Add a new test to `tests/unit/agents/code_generator/test_build_runner.py`, alongside the existing `test_build_runner_classifies_vite_windows_spawn_denial_as_infrastructure` (which already fixture-injects a `ProcessResult` with the exact `spawn EPERM`/`windowsSafeRealPathSync`/`optimizeSafeRealPathSync` text via `monkeypatch.setattr(build_runner, "run_command", fake_run_command)` — follow this same pattern)
  - Fixture-inject a fake process-count function (do not depend on real OS/`tasklist`/`ps` state in the test) and assert the resulting `Diagnostic.normalized_message` contains the concurrent-process-count value
  - Fixture-inject a prior `stage_durations_ms["verify"]` value on the settings/run context and assert the resulting message contains a comparison against it
  - Assert `issue.code` is still exactly `"VITE_NODE_SPAWN_EPERM"` and `issue.owner` is still exactly `"infrastructure"` — i.e., the existing classification assertions from the pre-existing test must still hold for this new context-carrying variant
  - _Requirements: 2.1, 2.2_
  - _Depends on: Task 1_

- [x] 5. Unit tests for `stage_durations_ms` writes (task 2)
  - Create `tests/unit/agents/code_generator/test_coordinator.py` (new file — no existing coordinator test file was found in this codebase)
  - Assert that calling `advance_after()` for a completed stage writes a non-negative millisecond duration into `stage_durations_ms` for the stage that just completed
  - Assert that all other pre-existing entries in `stage_durations_ms` are left byte-identical (untouched) after the call — this is the concrete, checkable form of Property 2's "every non-spawn-diagnostic code path is byte-identical" for this specific file
  - Assert the write goes through the same `compare_and_swap` call already used for `coordinator_stage`/`status`, not a separate write (inspect the call args passed to the repository's `compare_and_swap`)
  - _Requirements: 2.4_
  - _Depends on: Task 2_

- [x] 6. Unit tests for `stage_estimate` computation (task 3)
  - Create `tests/unit/agents/code_generator/test_service.py` (new file — confirmed no existing `service.py` test file exists for this agent, unlike `discovery`/`content_architect`/`visual_design_director`, which each have their own `test_service.py`; follow their structure/fixture conventions where applicable)
  - Assert `get_state()`'s `payload["progress"]["stage_estimate"]["source"]` is exactly `"configured_budget"` when the run's `stage_durations_ms` is empty
  - Assert `source` is exactly `"observed_and_budget"` when at least one stage has a recorded duration
  - Assert the computed `estimated_total_ms` for an all-budget case (empty `stage_durations_ms`) equals the exact sum of the relevant `worker.job.kind_timeouts` entries present in test settings — never a value not traceable to that config
  - Assert a `not_started` session (no run, no `stage_durations_ms` data at all) still returns a valid `payload["progress"]` without raising — the additive field must degrade gracefully to absent/empty, not break the existing response shape
  - _Requirements: 2.4_
  - _Depends on: Task 3_

- [x] 7. Property-based test — Property 3 (no fabrication)
  - **Property 3: No Fabrication** - Estimated-time arithmetic is always exactly reconstructible from real sources
  - Add to `tests/unit/agents/code_generator/test_service.py` (same file as task 6, or a dedicated `test_service_stage_estimate_properties.py` sibling if the project's PBT convention favors separate files — check existing PBT test file naming elsewhere in `tests/unit/agents/code_generator/` first and match it)
  - Generate random combinations of `stage_durations_ms` entries (0 to 4 of the 4 stages populated, each a random non-negative duration) and random `worker.job.kind_timeouts` configs for the remaining stages
  - Assert the computed `estimated_total_ms` is always exactly `sum(observed durations for completed stages) + sum(configured budgets for incomplete stages)` — property-test the arithmetic invariant directly, per `design.md`'s Property-Based Tests section, "since this is the concrete, checkable form of 'never a fabricated constant'"
  - Run this test and confirm it passes before proceeding
  - _Requirements: 2.4_
  - _Depends on: Task 3_

- [x] 8. Property-based test — Property 2 (preservation)
  - **Property 2: Preservation** - Non-spawn-diagnostic code paths are unaffected by the new branch
  - Add to `tests/unit/agents/code_generator/test_build_runner.py`
  - **Observation-first methodology, applied to this additive-only case**: since no existing code path is modified (only new, additive branches are added), "observed behavior on unfixed code" is simply the current passing behavior of `test_build_runner.py`'s existing tests. Confirm those existing tests (`test_clean_build_serializes_package_installs`, `test_build_runner_classifies_vite_windows_spawn_denial_as_infrastructure`) still pass unmodified after tasks 1-3 are implemented — per `design.md`'s "Preservation Checking" pseudocode, this is itself the preservation check, and "any existing test that needs to change to keep passing is a signal this design's 'additive only' framing was wrong somewhere and needs re-examination before proceeding, not a test to simply update"
  - Generate random `ProcessResult` outputs (varying `returncode`, `combined_output` content, `timed_out`) that do **not** match the `spawn eperm`/`windowssaferealpathsync`/`optimizesaferealpathsync` pattern
  - Assert `_run()`'s new context-capture code (from task 1) never executes for any of them — i.e., the new code is reachable only from the exact existing classification branch, never a broader one
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7_
  - _Depends on: Task 1, Task 2, Task 3 (all additive backend changes must exist to confirm nothing outside their exact branches is affected)_

### Phase C: Frontend Consumption

- [x] 9. Frontend adapter: read `progress.stage_estimate`
  - In `frontend/src/data/adapters/generation.ts`'s `adaptCodeGenerator()`, read `raw.progress.stage_estimate` — mirroring the existing pattern already used for `raw.progress.plan_summary`/`raw.progress.source_summary` in the same function
  - Add `estimatedRemainingMs`, `estimatedTotalMs`, and `estimateSource` fields to the `GenerationViewModel` interface and to every return path of `adaptCodeGenerator()` (including the early `unsupported`-state return, which must set these to `undefined`, not `0` or a fabricated default, per `design.md`'s Unit Tests section: "leaves those fields undefined (not zero, not a fabricated default) when absent")
  - **Explicit scope boundary — do not touch anything else in this file**: this task modifies only the reading of `progress.stage_estimate` and its three new output fields. Every other field, branch, and computation in `adaptCodeGenerator()` (status mapping, `coordinatorStage` derivation, `preview`/`candidatePreview` adaptation, `safeError`, `retryAvailable`, etc.) must remain byte-identical to its current form
  - _Expected_Behavior: `design.md` Fix Implementation item 3, "Frontend consumption" — "`adaptCodeGenerator()` reads `raw.progress.stage_estimate`... and adds `estimatedRemainingMs`/`estimatedTotalMs`/`estimateSource` to `GenerationViewModel`"_
  - _Requirements: 2.4_
  - _Depends on: Task 3 (the backend response shape this reads must exist first)_

- [x] 10. Frontend unit test for the adapter change
  - In `frontend/src/data/adapters/generation.test.ts` (existing file, following its existing `describe("adaptCodeGenerator", ...)` structure and its existing fixture imports from `./generation.fixtures`)
  - Add a new fixture (or extend `generation.fixtures.ts`, matching how `generationWorking`/`generationReady`/etc. are already defined) that includes a `progress.stage_estimate` object, and assert `adaptCodeGenerator()` maps it into `estimatedRemainingMs`/`estimatedTotalMs`/`estimateSource` correctly
  - Assert that when `progress.stage_estimate` is absent from the raw payload (e.g., using the existing `generationNotStarted` or `generationWorking` fixture unmodified), the three new fields are `undefined` — not `0`, not a fabricated default
  - Run the existing full `generation.test.ts` suite and confirm every pre-existing test (`keeps the stage locked...`, `maps working and ready states...`, `requires regeneration for stale output`, `retains the last verified preview...`, `does not confuse current_run_id with a job id`, `uses the coordinator stage for legacy responses...`) still passes unmodified — this is this file's own preservation check for Property 2
  - _Requirements: 2.4_
  - _Depends on: Task 9_

- [x] 11. `GenerationStage.tsx`: render the estimate only during `isWorking`
  - In `frontend/src/stages/generation/GenerationStage.tsx`, add a small, human-readable rendering of the estimate (e.g., "About 6 minutes remaining") near the active milestone in the existing `codegen-stepper` block
  - Render this **only** when `isWorking` is true — never during `isAvailable`, `isAttention`, or `isComplete`, per `design.md`'s explicit rationale: "an estimate is meaningless once the run isn't actively progressing"
  - Add a small, pure formatting helper (`ms` → "About N minutes") local to this component or a shared frontend util — no additional backend computation is needed for display formatting, per `design.md`
  - **Explicit scope boundary — this is the single most important constraint on this task**: `design.md`'s "Preservation Requirements" table (clause 3.5) and its own read-source confirmation state that `GenerationStage.tsx`'s already-shipped elements are all present and correct in current source: the verified-vs-candidate preview badges (`badge-verified`/`badge-candidate` in the browser address bar), the traceability drawer (Trace ID/Active Job ID/Session ID/Error Code fields, "Copy diagnostic report" via `handleCopyReport`), the 5-milestone stepper's existing status/description logic, the stage-transition crossfade, and the confirmed absence of any Publish/Deploy UI. **Do not edit, restructure, or "clean up" any of these existing elements or their surrounding JSX/handlers/CSS classes.** The only change in this file is the new, additive estimate-rendering block described above. If implementing the estimate naturally suggests refactoring nearby code, do not do so — file it as a separate follow-up instead.
  - _Preservation: Preservation Requirements 3.5 — "this bugfix SHALL only add the estimated-time indicator and fix genuine defects surfaced by real browser verification, not redesign or regress this already-working UI"_
  - _Requirements: 2.4_
  - _Depends on: Task 9_

### Phase D: Verification (consumes the 5-full-pipeline-call budget — run LAST)

**Do not start this phase until Phases A, B, and C are complete and all new
unit/property-based tests pass.** Per `bugfix.md`'s explicit cap, this phase
and any other full Code Generator pipeline call consumed anywhere in this
effort are jointly bounded to a maximum of 5 total calls
(`plan → acquire → generate` attempts). Track and report the running count
as each task below executes.

- [~] 12. Authenticated end-to-end verification (bugfix.md 2.3)
  - Follow `design.md`'s "Authenticated End-to-End Verification Plan" exactly: start the local native stack via `scripts/run-native.ps1 migrate` (once) then `scripts/run-native.ps1 dev` (fans out to backgrounded `api`/`worker`/`preview` processes, each loading `config/app.native.toml`) — **do not run these via a blocking foreground shell command; if a long-running process is needed, direct the user to start it manually per this project's long-running-command convention**
  - Walk the 6-step browser journey from `design.md` verbatim: sign in, click Generate (confirm `POST /api/v1/sessions/{session_id}/code-generator/start` with an `Idempotency-Key` header in the network tab), watch the milestone stepper progress against real polled `coordinator_stage` changes, confirm the new estimated-time text appears during `working` and changes plausibly, confirm the preview iframe loads a real `active_preview.url`, open the traceability drawer and confirm all four ID fields are non-placeholder
  - **Budget conservation, per `design.md`'s explicit guidance**: prefer reusing an existing `ready` session for steps 5-6 (preview/drawer inspection) and reserve a fresh `/start` specifically for confirming the stepper/estimate behavior live — this walkthrough consumes one pipeline-call slot only if a fresh `/start` is used, zero slots if fully reusing an existing `ready` run
  - Apply `design.md`'s exact pass/fail definition: **pass** = zero uncaught browser console errors, all API/preview requests return 2xx, the milestone stepper's active stage always matches the polled `coordinator_stage`, the estimated-time text is present during `working` with a traceable `source`; **fail** = any uncaught console error, any non-2xx response, a stepper/state mismatch, or an untraceable estimate value
  - If a `VITE_NODE_SPAWN_EPERM` diagnostic is emitted during this run, assert the new concurrent-process-count and prior-duration context (task 1) are present and non-empty in the persisted `terminal_failure` — this is `design.md`'s Fix Checking test case 3
  - _Expected_Behavior: Correctness Property 1 (fallback branch) and bugfix.md 2.3 — "the system SHALL render genuine backend-driven milestone progress, a working preview iframe... and zero uncaught browser console errors"_
  - _Requirements: 2.2, 2.3, 2.4_
  - _Depends on: Phases A, B, C complete_

- [~] 13. Second-pack generalization run (bugfix.md 2.5)
  - **Property 4: Generalization** - Fix reaches `ready` (or an independently-diagnosed failure) for a second, structurally different Build Preparation pack
  - Follow `design.md`'s "Second-Pack Generalization Plan" exactly: run `POST /api/v1/development/code-generator/runs/from-build-preparation` with `{"pack": "16-33-12-09-0ffb7b6e"}` — the confirmed structurally-different second pack (different content hash, route/section count, navigation contract, and professional domain — quant trading vs. agentic AI — from the already-consumed `10-05-14-09-ea2ff472` pack)
  - Wait for the run to reach a terminal state; assert it independently reaches `ready` with a real `active_preview`, **or** an independently-diagnosed, non-Windows-spawn failure fully root-caused on its own merits per bugfix.md 2.6 — a new `needs_attention` on this second pack must not be waved through, it is a distinct defect class requiring the same diagnostic rigor as the primary run
  - This run consumes one of the 5 full-pipeline-call budget slots
  - _Expected_Behavior: Correctness Property 4 from design.md — "running the full Code Generator pipeline against each SHALL each independently reach `ready`... demonstrating the result is not overfit to the one pack already exercised"_
  - _Requirements: 2.5, 2.6_
  - _Depends on: Phases A, B, C complete_

- [~] 14. Checkpoint — full suite, budget accounting, and sign-off
  - Run the complete backend unit/property-based test suite (`tests/unit/agents/code_generator/`, including all new files/tests from tasks 4-8) and confirm every test passes, including every pre-existing test that must remain unmodified per Preservation Requirements
  - Run the complete frontend Vitest suite for `frontend/src/data/adapters/generation.test.ts` and confirm every pre-existing and new test passes
  - Report the total count of full Code Generator pipeline calls (plan→acquire→generate attempts) consumed across tasks 12 and 13 combined, and confirm it does not exceed the requirements' cap of 5 (bugfix.md 2.2) — this count should also include any full-pipeline call consumed earlier during design-phase diagnosis, if that count was tracked and reported at design time
  - Confirm no task in this plan touched production deployment, DNS, Azure VM configuration, or multi-account browser acceptance, per Preservation Requirement 3.7
  - If any question or ambiguity arises during this checkpoint, ask the user rather than guessing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_
  - _Depends on: Task 12, Task 13_

## Notes

- **Full-pipeline-call budget**: every full Code Generator pipeline call
  (`plan → acquire → generate` attempt) consumed anywhere in this effort —
  including Phase D's verification tasks and any call already spent during
  design-phase diagnosis — is jointly capped at 5 total, per `bugfix.md`
  2.2. Track and report the running count as Phase D executes; do not start
  Phase D until Phases A, B, and C are complete and all new unit/property
  tests pass.
- **When ambiguity arises**: if a question or ambiguous situation comes up
  at any point in this plan, particularly during the final checkpoint, ask
  the user rather than guessing.
