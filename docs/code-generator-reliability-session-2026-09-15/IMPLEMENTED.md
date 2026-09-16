# Implemented / Changed - Code Generator Reliability & Preview Integration Session

Session: 2026-09-15 - Spec: .kiro/specs/code-generator-reliability-and-preview-integration/
Format: one entry per task/change. Task numbers reference tasks.md in the spec folder.

---

## Task 1 - Diagnostic context capture on VITE_NODE_SPAWN_EPERM
- File: src/oryxenai/agents/code_generator/core/build_runner.py
- What: Added _count_node_process_matches() (best-effort, stdlib-only
  process count) and _prior_duration_note() (best-effort comparison against a
  prior recorded stage_durations_ms["verify"]), both attached to the existing
  VITE_NODE_SPAWN_EPERM diagnostic's free-text message. No spawn-mechanism
  change - design.md's own empirical investigation found no reproducible
  defect in the spawn path itself.
- Tests: 5 new tests in tests/unit/agents/code_generator/test_build_runner.py.
- Status: Complete.

## Task 2 - Populate stage_durations_ms at stage transitions
- Files: src/oryxenai/agents/code_generator/core/coordinator.py (plan-acquire-
  generate durations), src/oryxenai/jobs/handlers/code_generator_verification.py
  (verify stage's own duration, whole-handler wall time), plus a new DB column
  (code_generator_runs.stage_durations_ms, migration
  0024_codegen_stage_durations.py) and matching ORM field - this field
  existed only on Pydantic projection schemas before this task, not on the
  actual DB model; writing to it as originally scoped would have raised at
  runtime.
- Correction made mid-task: a regression this task introduced (two
  pre-existing, previously DB-free tests in test_portfolio_export.py started
  failing) was root-caused to a PRE-EXISTING bug (dated commit 39076d0c,
  2026-09-10) in the needs_attention/failed export block's exception handling
  - an optional DB-context read shared a try scope with the actual export
  call, so a DB failure silently skipped the export entirely. Isolated the
  context read into its own nested try/except. Verified against a clean HEAD
  that the bug predated this task.
- Incident during this task (disclosed in full to the user at the time):
  a test run accidentally targeted the real local oryxenai application
  database instead of oryxenai_test and wiped its row data via
  drop_all/create_all. Schema was restored via alembic upgrade head; row
  data was not recoverable. Root cause (a missing guard in
  tests/conftest.py::test_engine) was fixed as a separate, explicit
  out-of-band task at the user's direction - see below.
- Tests: new tests/unit/agents/code_generator/test_coordinator.py (3
  tests, real DB), 4 new integration-marked tests appended to
  test_portfolio_export.py.
- Status: Complete.

## Out-of-band - tests/conftest.py test-database guard
- File: tests/conftest.py
- What: Added a hard-failing RuntimeError guard in the test_engine
  fixture, firing before any drop_all/create_all if the resolved database
  is not exactly "oryxenai_test" - closing the exact gap that caused the
  data-loss incident above.
- Tests: new tests/unit/test_conftest_db_guard.py (4 tests, proven to
  actually fire via a fake settings object + a spy on get_engine that raises
  if ever reached - no second real database was touched to prove this).
- Status: Complete. Confirmed a no-op for every correctly-configured test
  run (full tests/integration/ + tests/worker/ suite re-run afterward,
  102 passed / 1 pre-existing unrelated failure / 1 skipped, identical with or
  without the guard).

## Task 3 (+ Task 7, bundled) - Backend stage_estimate computation
- File: src/oryxenai/agents/code_generator/service.py
- What: _compute_stage_estimate(), a pure function computing
  {elapsed_ms, estimated_total_ms, estimated_remaining_ms, source} from only
  two real sources: observed stage_durations_ms entries (task 2) for
  completed stages, and config/app.toml's worker.job.kind_timeouts
  code_generator.* budgets for incomplete ones. Wired additively into
  get_state()'s existing payload["progress"] dict. Explicitly maps
  stage_durations_ms's "verify" key to the differently-named
  "code_generator.verify_and_preview" config key (confirmed by reading
  config/app.toml directly - the two vocabularies diverge on this one stage).
- Tests: new tests/unit/agents/code_generator/test_service.py (22 tests,
  including the Task 7 property-based "no fabrication" invariant - 200-trial
  seeded random loops, since this codebase has no Hypothesis dependency).
- Status: Complete.

## Tasks 4, 5, 6 - Unit test coverage
- Confirmed already fully satisfied by tests written as part of Tasks 1, 2,
  and 3's own dispatches respectively - cross-checked each task's specific
  acceptance bullets against the actual test file contents before marking
  complete, rather than assuming overlap.
- Status: Complete (no additional work needed).

## Task 8 - Property-based preservation test
- File: tests/unit/agents/code_generator/test_build_runner.py
- What: 150-trial seeded random loop generating non-matching ProcessResult
  outputs, asserting _count_node_process_matches() is never called for any of
  them (a spy that raises if invoked - proving reachability, not just output
  absence). Verified the test actually catches a regression by temporarily
  broadening the classification branch, confirming the test failed, then
  reverting.
- Status: Complete.

## Task 9 - Frontend adapter reads progress.stage_estimate
- File: frontend/src/data/adapters/generation.ts
- What: adaptStageEstimate() helper + 3 new optional fields on
  GenerationViewModel (estimatedRemainingMs, estimatedTotalMs,
  estimateSource), read via the same isRecord guard pattern already used
  for plan_summary/source_summary. All three are undefined (never 0
  or a fabricated default) when absent.
- Status: Complete. tsc --noEmit clean.

## Task 10 - Frontend unit tests for the adapter change
- Files: frontend/src/data/adapters/generation.fixtures.ts, generation.test.ts
- What: New generationWorkingWithEstimate fixture + 3 new test cases
  (populated estimate maps correctly; undefined when progress exists but
  stage_estimate doesn't; undefined when no progress object exists at all).
- Status: Complete. 13/13 tests pass (10 pre-existing + 3 new).

## Task 11 - GenerationStage.tsx renders the estimate
- File: frontend/src/stages/generation/GenerationStage.tsx
- What: formatEstimatedTimeRemaining() helper + one new conditional
  element inside the existing milestone stepper, rendered only when
  isWorking && idx === activeIndex && typeof estimatedRemainingMs === "number".
  18 insertions, 1 deletion - no other existing element in this file touched
  (verified/candidate badges, traceability drawer, stepper logic, crossfade,
  Publish/Deploy absence all confirmed untouched).
- Known gap: no CSS rule yet for the new .step-estimate class - renders
  unstyled. Left as-is since styling was outside this task's stated scope.
- Status: Complete.

---

## Task 12 - Authenticated end-to-end verification (IN PROGRESS, not yet complete)

- Native stack started (scripts/run-native.ps1 migrate then dev);
  /health/ready confirmed 200 before starting.
- Real browser walkthrough performed via Playwright, using the project
  owner's own already-authenticated Google session, with Dr. Aditya Vikram
  Joshi's resume (Input-Output-Of-Engine/resume.md) as Discovery input.
- Discovery, Content Architect, and Visual Design Director all completed
  successfully with genuine, correct, non-mocked LLM output - see
  ISSUES.md for what did NOT show a defect.
- Two real, low-severity frontend defects found (ISSUE-01, ISSUE-02 in
  ISSUES.md) - a speculative Code Generator state poll returning an
  expected-but-unhandled 409 during earlier stages.
- One user-reported symptom not yet independently isolated (ISSUE-03): a
  stuck "Approve and Continue" on the Design stage, reported from the
  project owner's own prior testing.
- The native API process crashed (ISSUE-04) immediately after clicking
  "Approve & continue" on Visual Design Director - not yet confirmed
  whether this is the same defect as ISSUE-03, or a separate infrastructure/
  contention issue. 3 restart attempts during this session did not bring the
  API back up; a parallel finding that even trivial backgrounded shell
  commands were silently failing at the same time points toward machine-wide
  resource contention (concurrent AI-session load) as the likely cause,
  consistent with design.md's own prior root-cause finding for the
  Windows spawn EPERM issue - but this is not yet proven, only the best
  current hypothesis.
- Not yet reached: Code Generator's own plan-acquire-generate-verify
  pipeline has not yet been exercised in this live walkthrough - the crash
  happened one stage before reaching it (Design-Prepare transition, before
  Build Preparation or Code Generator were ever started).
- Pipeline-call budget consumed so far: 0 of the 5 allowed full Code
  Generator pipeline calls (Discovery/Content Architect/Visual Design
  Director calls are not counted against this cap per bugfix.md 2.2 -
  the cap applies specifically to Code Generator's own
  plan-acquire-generate attempts).

## Task 13 - Second-pack generalization run
- Not started. Blocked behind Task 12 reaching Build Preparation/Code
  Generator, which requires the native API to be healthy first.

## Task 14 - Final checkpoint
- Not started. Depends on Tasks 12 and 13.
