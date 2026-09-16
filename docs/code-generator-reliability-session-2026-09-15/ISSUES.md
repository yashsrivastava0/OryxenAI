# Issues Found - Code Generator Reliability & Preview Integration Session

Session: 2026-09-15 - Spec: code-generator-reliability-and-preview-integration
Format: one entry per issue. Severity is my own assessment, not a claim.

---

## ISSUE-01 - Speculative Code Generator state poll returns 409 during Discovery/Content/Design

- Severity: Low (cosmetic console error, no functional impact observed)
- Where: Frontend polls GET /api/v1/sessions/{id}/code-generator before Code
  Generator has ever been started for the session (Discovery/Content Architect/
  Visual Design Director stages).
- Symptom: Backend correctly rejects with 409 Conflict,
  {"error":{"code":"ENTITLEMENT_BINDING_CONFLICT", ...}}. Surfaces as an
  uncaught browser console error on at least two separate stage transitions
  (Discovery start, Content Architect approval) during a real, authenticated
  browser walkthrough with a genuinely new session.
- Not yet root-caused: which exact frontend polling logic issues this
  speculative check, and whether it should simply not poll Code Generator state
  until Build Preparation is approved, or should treat this specific error code
  as an expected/silent "not applicable yet" response instead of logging it.
- Reproduced: twice, consistently, at Discovery-start and Content-approval,
  in the same live walkthrough (run/session 9eb9a394-63ba-48e8-92ad-2f5cda953c7b).

## ISSUE-02 - "The latest check did not complete" banner after Content Architect approval

- Severity: Low (non-blocking; approval itself succeeded)
- Where: Frontend, immediately after clicking "Approve & continue" on the
  Content Architect stage.
- Symptom: A visible banner reads "The latest check did not complete.
  Showing the last confirmed state." This is the same speculative
  Code-Generator-poll 409 from ISSUE-01, but here it is shown to the user
  instead of only appearing in the console. The actual approval was saved
  correctly ("Approval is saved. Start the next stage when you are ready."),
  and the stage advanced correctly (Content checkmarked, Design became active).
- Likely same root cause as ISSUE-01.

## ISSUE-03 - "Approve and Continue" on Design stage appears stuck (user-reported, not yet independently confirmed)

- Severity: Unknown - potentially significant if confirmed with a healthy
  backend.
- Reported by: the project owner, from their own prior testing, described
  as: clicking "Approve and Continue" on the Design (Visual Design Director)
  stage does not advance; described as a build-up-pressure/stuck-container
  symptom.
- What happened when I hit something similar: clicking "Approve & continue"
  on Visual Design Director in my own walkthrough triggered a spike from 2 to
  10 console errors, ending in net::ERR_CONNECTION_REFUSED on every API
  endpoint - the native API process had crashed entirely at that exact moment.
  This is NOT yet confirmed to be the same defect the owner observed. My
  case had a fully dead backend; a genuinely stuck-but-backend-healthy button
  click is a distinct hypothesis that still needs isolated testing.
- Status: UNRESOLVED / NOT YET ISOLATED. Needs a clean retest once the
  native stack is confirmed healthy (GET /health/ready returns 200) before
  clicking Approve on Design, to determine whether the click itself hangs
  independent of backend availability.

## ISSUE-04 - Native API process crashed during live session, would not restart via automated tooling

- Severity: High (operationally) - blocked all further live verification.
- Symptom: uvicorn process serving the native API died sometime after
  Visual Design Director's approval click. No process was bound to port 8000
  afterward. net::ERR_CONNECTION_REFUSED on every endpoint from that point on.
- Restart attempts (all failed to bring the API back up):
  1. scripts/run-native.ps1 dev (background) - no new uvicorn process spawned.
  2. Direct uv run uvicorn via a detached Start-Process wrapper - same.
  3. scripts/run-native.ps1 dev again - spawned only 1 of the expected 3
     child processes (api/worker/preview), and that 1 child exited immediately
     with no children of its own - consistent with uvicorn crashing at
     startup, not a slow bind.
- A separate, likely-related finding: even a trivial background command
  (writing one line to a file) silently failed to execute during this same
  window - strongly suggesting the tooling (background process execution),
  not the application code, was impaired at that moment, most plausibly due to
  heavy concurrent load on this machine (multiple codex/chrome/node
  processes actively running/starting at the same time, confirmed via
  Get-Process) - the same category of environmental contention design.md's
  own root-cause investigation attributed the earlier VITE_NODE_SPAWN_EPERM
  incident to.
- Also found: duplicate leftover worker/preview.gateway processes from
  a prior session (dated 2026-09-14) still running at the time of the crash -
  not confirmed to be the cause, but a real, pre-existing environmental
  untidiness worth cleaning up separately.
- Status: environment-dependent, not yet reproduced on demand. Needs a
  clean retest once the machine is not under heavy concurrent multi-session
  load, to determine whether the crash is reproducible or was itself a
  one-off contention event.

---

## What did NOT show any defect (confirmed working, real LLM output)

For context/contrast - the following were verified against a real,
authenticated browser session, using Dr. Aditya Vikram Joshi's resume as
input, and produced genuinely correct, non-mocked, on-topic output:

- Discovery (understand_and_question + build_or_revise_brief): asked a
  relevant clarifying question grounded in the actual resume, then produced an
  accurate, well-structured brief correctly citing DarkStore-Mesh,
  Chronos-Memory-Mesh, MicroSandbox-RT, and NeuroRouting-Proxy as the strongest
  case studies, and correctly naming all four employers.
- Content Architect (plan_content): produced a real 7-section content
  structure with correctly tiered priorities (HIGHEST/HIGH/MEDIUM), grounded in
  the approved brief.
- Visual Design Director (establish_visual_language + direct_page_experience):
  produced a detailed, coherent creative direction (color/typography/motion/
  interaction) plus a 4-part scene storyboard with per-scene narrative goals,
  layout intent, responsive behavior, and accessibility intent.

None of these three stages showed any defect in this session.
## ISSUE-05 - RESOLVED: AppShell.tsx never advanced initial stage forward on page load

- Severity: High (this WAS the root cause of "Build Preparation not moving
  forward / not getting accepted")
- Where: frontend/src/app/AppShell.tsx, refetchCurrentSession's
  initialNormalizationDone block.
- Root cause (confirmed live, not theoretical): the block only ever
  corrected the initial activeStage BACKWARD (URL requested a stage ahead of
  approved progress -> fall back to an earlier one). It had no branch to
  correct FORWARD: when the URL requested/defaulted to "discover" but the
  backend had already approved Discovery, Content Architect, and Visual
  Design Director, the page stayed frozen on stale Discovery-stage content
  indefinitely. This reproduced even after a full hard reload (ruled out
  in-memory-only stale state) and even though every underlying data fetch
  (including GET .../build-preparation, confirmed via direct authenticated
  fetch to return 200 with correct {"status":"not_started",...} data)
  succeeded correctly - this was purely a render/normalization logic bug,
  not a network or backend defect.
- Confirmed via manual workaround before the fix: clicking the "Prepare" nav
  tab directly (bypassing the broken auto-normalization) immediately showed
  the correct, fully-working "Ready to prepare the build handoff" screen -
  proving BuildPreparationStage's own rendering was never broken, only the
  initial stage selection was.
- Fix: extracted a new pure, exported function resolveInitialStage(...) in
  AppShell.tsx, preserving all 4 existing backward-correction branches
  exactly as-is, and adding a new forward-correction branch that walks
  discoveryApproved -> contentApproved -> designApproved ->
  preparationApproved to find the furthest actionable stage whenever the
  requested/default stage was "discover" and none of the backward branches
  fired.
- Tests: new frontend/src/app/AppShell.test.ts (9 tests - all 4 pre-existing
  backward cases reproduced and passing unmodified, 5 new forward cases
  including the exact live-bug scenario). Full frontend suite: 131/131
  passing (up from 122), tsc --noEmit clean.
- Verified live after rebuilding the frontend (npm run build - this app
  serves a pre-built static bundle from src/oryxenai/web/static/product/,
  NOT a hot-reloading dev server, so the fix required a rebuild to take
  effect): a bare, cold navigation to /app now correctly and immediately
  lands on ?stage=prepare&view=artifact showing the real, working "Prepare
  build handoff" screen, with no manual nav click needed.
- Status: RESOLVED and verified live.

## Build Preparation intake - directly re-tested and confirmed working (2026-09-15, post-fix)

After the ISSUE-05 fix and frontend rebuild, clicked "Prepare build handoff"
directly (same session, run 9eb9a394-...). Result: genuinely accepted and
completed successfully in well under a minute -
"Build handoff prepared" / "READY FOR GENERATION" / "STABLE HANDOFF COMPILED".
Real output confirmed: 1 route bound, 3 resources researched & indexed (each
with source/license/dimensions), 3 component pattern suggestions, both
immutable briefs present (content-and-narrative-brief.md,
visual-and-build-brief.md). "Continue to Generate ->" is now live and
clickable.

CONCLUSION: Build Preparation's intake acceptance was never actually broken.
The reported "not moving forward and getting accepted" symptom was entirely
caused by ISSUE-05 (AppShell.tsx's frontend routing bug) - once that was
fixed, Build Preparation worked correctly on the very first real attempt.
