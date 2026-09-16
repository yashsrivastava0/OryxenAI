# Bugfix Requirements Document

## Introduction

Code Generator is the final stage of the OryxenAI pipeline
(Discovery → Content Architect → Visual Design Director → Build Preparation →
Code Generator). Given an approved Build Preparation brief pair, its
production session (`POST /api/v1/sessions/{session_id}/code-generator/start`)
is supposed to plan, acquire resources, generate a React/Vite/TypeScript
source tree, run a clean build, verify it in a real browser, and promote an
atomic preview — reaching `CodeGeneratorSessionStatus.ready` with an
`active_preview` the frontend can render.

The most recent live evidence
(`docs/code-generator-control-room-handoff-2026-09-14.md`) shows a real
production-shaped run (`af3bf8f7-d155-4e18-a5b0-48a683f5a647`) halting at
`needs_attention` with terminal code `TYPE_BUILD_ARTIFACT_FAILED`. The root
diagnostic is a Windows-specific Vite child-process spawn denial (`spawn
EPERM` inside Vite's own `windowsSafeRealPathSync`/`optimizeSafeRealPathSync`
helper) while `vite.config.ts` loads in the run's isolated generation
workspace. `build_runner.py` already recognizes and classifies this failure
(`VITE_NODE_SPAWN_EPERM`, `is_vite_windows_spawn_failure`) as
infrastructure-owned, but classification is not the same as the run
succeeding — the investigating session was interrupted before determining
whether this is a systemic, currently-active environment problem on this
machine, or something specific to how the isolated generation workspace
spawns child processes, and never got a generation attempt past this gate.

Separately, the frontend's Generate & Preview experience
(`frontend/src/stages/generation/GenerationStage.tsx`) was implemented and
committed by an interrupted prior session (`d0894d6`, `ecb8257`) with a real
5-milestone stepper, a verified-vs-candidate preview distinction, a
traceability drawer, and retry/regenerate actions wired to existing
callbacks — confirmed present in current source, along with the Publish/
Deploy UI removal and the stage-transition crossfade. What has never been
confirmed is that this UI reflects a real, successfully completed backend run
when driven from an authenticated browser against the live stack, and it does
not yet surface any estimated-time indicator (no such field exists in
`GenerationViewModel`, the session schema, or any config today).

This bugfix has two coupled defects to resolve — a backend reliability gap
that prevents a `ready` terminal state, and a frontend/backend integration
gap that has never been proven end-to-end — plus one net-new capability
(estimated generation time) that the user explicitly requested as part of
making the flow trustworthy. Fixing the reliability gap must generalize
across varying valid Build Preparation input, not just the one historical
brief pack already on disk, since Build Preparation output legitimately
varies portfolio to portfolio. Any full Code Generator pipeline
(plan → acquire → generate, matching the existing "full pipeline call"
accounting used throughout `docs/code-generator-live-campaign.md`) consumed
while diagnosing and fixing this is bounded to a maximum of 5 for this
effort, mirroring every prior live campaign's cap in that same file.
Production deployment, DNS, Azure, and multi-account acceptance are
explicitly out of scope; the finish line is a genuinely working local
generate → progress-with-estimate → verified-preview flow.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a session-scoped Code Generator run reaches the `building` stage on
this Windows development machine THEN the system sometimes fails the clean
build with terminal code `TYPE_BUILD_ARTIFACT_FAILED`, root-diagnosed as a
`VITE_NODE_SPAWN_EPERM` child-process spawn denial inside Vite's own
Windows path-resolution helper, and the run stops at `needs_attention`
without reaching `ready` — with no confirmed root cause distinguishing a
systemic machine-level Node/Vite/antivirus problem from something specific
to how the isolated generation workspace spawns processes.

1.2 WHEN a verify-stage retry is issued against a run that has already hit
`VITE_NODE_SPAWN_EPERM` THEN the system fails again in a materially shorter
time than the original attempt (observed: ~30s vs. ~420s), and no explicit
diagnostic step exists that would tell an operator whether retrying,
restarting native services, or something else entirely is the correct
recovery action.

1.3 WHEN the frontend's Generate & Preview screen (`GenerationStage.tsx`,
already implemented with a 5-milestone stepper, verified/candidate preview
distinction, and traceability drawer) is driven from a real authenticated
browser against a real running backend for a full generate-to-preview
attempt THEN the system has never had this exact flow confirmed to work,
because no session in the project's history has completed the walkthrough
described in `docs/code-generator-control-room-handoff-2026-09-14.md`
Phase 3.

1.4 WHEN a user starts generation from the frontend THEN the system displays
milestone progress (Plan/Acquire/Build/Verify/Preview) with no estimate of
how long the remaining or total work will take, because no estimated-time
field exists in `GenerationViewModel`, `CodeGeneratorSessionState`, or any
Code Generator config today.

1.5 WHEN Code Generator reliability work is diagnosed and fixed using one
specific historical Build Preparation brief pack (for example the pack
behind run `af3bf8f7-...`) THEN there is currently no requirement or check
confirming the fix also generalizes to a second, structurally different,
valid Build Preparation brief pack — leaving open the possibility that a fix
is over-fit to one known input while remaining brittle to legitimate
variation in Build Preparation output.

### Expected Behavior (Correct)

2.1 WHEN a session-scoped Code Generator run reaches the `building` stage on
this development machine THEN the system SHALL have a conclusively
determined root cause for the `VITE_NODE_SPAWN_EPERM` failure mode
(systemic environment issue vs. generation-workspace-specific spawn/path
issue vs. another cause), SHALL apply a fix appropriate to that root cause,
and SHALL allow the clean build to complete for a valid Build Preparation
input without manual `cd`-and-manual-`npm run build` intervention.

2.2 WHEN the applied fix for 2.1 is in place and a full Code Generator
pipeline is run against a valid Build Preparation brief pair THEN the
system SHALL reach `CodeGeneratorSessionStatus.ready` (or the equivalent
durable `DevelopmentRunStatus.ready`) with a real, browser-loadable
`active_preview`, consuming no more than 5 total full Code Generator
pipeline calls (plan→acquire→generate attempts, matching this project's
existing "full pipeline call" accounting) across the whole diagnose-fix-
verify effort.

2.3 WHEN a user completes the full authenticated-browser journey — Build
Preparation approval, clicking Generate, watching milestone progress update,
and reaching a verified preview — against the real running native stack
(API + worker + preview gateway) THEN the system SHALL render genuine
backend-driven milestone progress, a working preview iframe pointed at a
real promoted preview URL, and zero uncaught browser console errors during
that journey.

2.4 WHEN a Code Generator run is actively progressing through its stages
THEN the frontend SHALL display an estimated time indicator (e.g., estimated
remaining time or estimated total time) derived from a real, non-hardcoded
source — such as configured per-stage budget values already present in
`config/app.toml` (`code_generator.plan`, `.acquire`, `.generate`,
`.verify_and_preview`) or observed historical run durations — and SHALL NOT
display a fabricated or arbitrary constant.

2.5 WHEN the fix from 2.1/2.2 is verified THEN the system SHALL also
demonstrate a successful `ready` result (or an equivalent, non-Windows-
spawn-related failure mode fully diagnosed on its own merits) for a second,
structurally different, valid Build Preparation brief pack — not only the
one historical pack already exercised in prior campaigns — so the fix is
shown to generalize rather than being narrowly fit to one known input.

2.6 WHEN a Code Generator run fails for a reason unrelated to the
Windows spawn issue during this effort's diagnosis (for example a
content-specific validator false positive, a resource-binding gap, or any
other defect class already documented in `code generator issues.md`) THEN
the system SHALL have that failure root-caused and fixed using the same
diagnostic rigor as prior entries in that file, rather than being left
unresolved or worked around superficially, within the same 5-full-pipeline-
call budget.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a Code Generator run is executed on non-Windows-Vite-spawn error
paths (immutable input admission, authorization/fencing, checkpoint
integrity, dependency installation success, source contract validation,
runtime/browser verification, atomic preview promotion) THEN the system
SHALL CONTINUE TO enforce every existing blocking check exactly as it does
today — this bugfix SHALL NOT relax, bypass, or globally disable any
existing validator, fencing check, or integrity gate to force a `ready`
result.

3.2 WHEN `preview_first_acceptance` is left at its existing configuration-
owned default (`false`, per `CodeGeneratorVerificationConfig` in
`settings.py`) on any non-native profile THEN the system SHALL CONTINUE TO
apply the existing strict release policy (integration review, source-
contract, and runtime findings remain blocking) exactly as today; this
bugfix's changes SHALL NOT alter that default or weaken strict-profile
behavior.

3.3 WHEN a Build Preparation brief pair has not reached `BuildPreparationStatus.READY`
with both Markdown briefs present, or its stored content/visual brief hashes
do not match the persisted Markdown bodies THEN the system SHALL CONTINUE TO
reject the Code Generator `start` call with the same `CODE_GENERATOR_BRIEF_INVALID`
/ not-ready error behavior it uses today.

3.4 WHEN Code Generator is not explicitly started via
`POST /api/v1/sessions/{session_id}/code-generator/start` (or `/retry`,
`/regenerate`) THEN the system SHALL CONTINUE TO never auto-chain from Build
Preparation approval, exactly as documented in AGENTS.md and the Code
Generator README.

3.5 WHEN the frontend's already-implemented Generate & Preview UI elements
(Publish/Deploy removal, verified-vs-candidate preview badges, the
traceability drawer's Trace ID/Active Job ID/Session ID/Error Code fields,
the "Copy diagnostic report" action, and the stage-transition crossfade with
`prefers-reduced-motion` support) are exercised THEN the system SHALL
CONTINUE TO behave exactly as already implemented in commits `d0894d6` /
`ecb8257`; this bugfix SHALL only add the estimated-time indicator and fix
genuine defects surfaced by real browser verification, not redesign or
regress this already-working UI.

3.6 WHEN a normal (non-admin) user's portfolio has already reached a
successful/entitled generation state THEN the system SHALL CONTINUE TO
enforce the existing one-immutable-generation-variant and post-success
read-only entitlement rules (`PortfolioReadOnlyError`,
`GenerationVariantLockedError`, `EntitlementBindingConflictError`) exactly as
implemented today.

3.7 WHEN this bugfix's diagnosis or fix work is performed THEN the system
SHALL CONTINUE TO stay within the explicitly authorized scope: no production
deployment, DNS, Azure VM configuration, or multi-account browser acceptance
work SHALL be performed or claimed as part of this effort.
