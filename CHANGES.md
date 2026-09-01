# OryxenAI — Change Log

Append-only record of major changes, commit hashes, and rationale across AI tools and sessions.

**Logging & Commit Policy (Strict for AI Agents):**
- **Major Work Only:** Log finished features, fixes, refactors, or architecture/schema changes (commit-sized units). Do not log micro-edits or individual file saves.
- **Commit Mandatory:** Per D-027 and AGENTS.md, every major finished task must end in a local task-scoped Git commit. The resulting commit short-SHA must be recorded in the entry header.
- **Order & Compaction:** Newest entries first under `## Recent changes`. Compact old entries to single lines under `## Compacted history` when the file exceeds ~250 lines.

---

## Recent changes

### 2026-09-02 02:30 +05:30 - Codex (GPT-5 / OpenAI) - [dfce00f] - impose distinctive move strength floor
Added host-owned minimum deviation and range-spread checks to V4 distinctive moves so weak near-neutral geometry fails during planning. Sticky narrative rails retain their discrete 1.0 contract, while existing authored asymmetric ranges remain valid.

### 2026-09-02 02:20 +05:30 - Codex (GPT-5 / OpenAI) - [c0c1f67] - guard visual identity at Code Generator admission
Added the belt-and-suspenders admission check over compiled `site/contract.json` facts and `design/visual-direction.json` global direction. Contradictory packs now fail before planning with the same stable `PACK_VISUAL_IDENTITY_MISMATCH` code, including packs already present in the local mirror.

### 2026-09-02 02:15 +05:30 - Codex (GPT-5 / OpenAI) - [a622d7d] - reject visual direction identity mismatches
Added a conservative repeated proper-name consistency check at the Build Preparation boundary, using approved Content Architect facts as the identity authority. The check hard-fails contradictory visual direction while preserving the existing projection shape and does not reject a single incidental capitalized phrase.

### 2026-09-02 02:01 +05:30 - Codex (GPT-5 / OpenAI) - [5f4be9a] - bridge compiler tokens into shadcn Tailwind slots
Added the fixed shadcn semantic-slot contract, color-token cross-reference validation, deterministic CSS aliases, and the static Tailwind v4 theme bridge. Updated the creative/planning prompts and verified provider schema compatibility plus focused unit coverage; token values remain portfolio-authored and compiler-emitted.

### 2026-09-02 01:35 +05:30 - Codex (GPT-5 / OpenAI) - [b760acb] - wire Tailwind v4 into the Vite scaffold
Added the locked Tailwind v4 engine, Vite plugin, CSS entry import, and supported-package catalogue entries to the React/Vite generation scaffold. Verified clean install, production build, TypeScript check, source audit, and emitted Tailwind preflight/utilities.

### 2026-09-02 01:25 +05:30 - Codex (GPT-5 / OpenAI) - [1cf313f] - bound final repairs by diagnostic group
Final verification now reconstructs per-group repair usage from durable receipts, preserves a shared run-wide ceiling, and conservatively buckets legacy receipts. Final V4 repair calls also reject acceptance after a failed gate and require bounded changes or an honest inability result, with unit and PostgreSQL-backed regression coverage.

### 2026-09-02 01:05 +05:30 - Codex (GPT-5 / OpenAI) - [234a05d] - restore Code Generator per-role model profiles
Restored the seven dedicated Code Generator role profile bindings in `config/app.toml`, added a settings regression check that loads the committed configuration, and recorded the routing boundary decision. Live role selection is now independently configurable while remaining provider-neutral.

### 2026-09-02 00:45 +05:30 - Codex (GPT-5 / OpenAI) - [aecfe40] - v4 selector and responsive image-size contracts
Normalized provider-echoed V4 distinctive-move sources to the exact executable layout region, allowed marker-qualified CSS evidence in the AST audit, and rejected non-browser-valid image `sizes` policies before source generation. The live baseline now clears the corresponding source-generation contracts.

### 2026-09-01 22:31 +05:30 - Codex (GPT-5 / OpenAI) - [b780266] - native PostgreSQL alignment
Fixed native role-alignment SQL to cast asyncpg parameters to text before PostgreSQL `format()`, making `align-db` work against the active PostgreSQL 18 cluster. Verified the shared local credential alignment and SCRAM logins for `postgres` and `oryxen` without logging the password.

### 2026-09-01 09:28 +05:30 — Codex (GPT-5 / OpenAI) — [d41eba1] — harden Code Generator generation, source evidence, repair, and polish contracts
Live retries exposed a chain of independent failures after the accepted-mode fix: rejected candidate bytes were unavailable to later repairs; raw-text selector checks miscounted strings/comments as JSX; route interaction, resource, motion, heading, distinctive-move, and export evidence could be attributed to the wrong owner or accepted without executable source; and integration polish could checkpoint a malformed replacement before source audit. Rejected attempts are now durable repair context, source checks use shared comment/JSX lexing and canonical V4 plan identities, generated image bindings resolve through the trusted manifest/`LocalImage`, final repair receives bounded source/style pairs, and every configured owner-scoped polish round must pass source/type validation before checkpointing. Planner, generation, integration-review, repair, scaffold, Windows toolchain, and legacy no-blueprint foundation compatibility contracts were aligned with regression coverage; D-032 records the finite three-round default.

The Code Generator unit suite, Ruff, and Mypy pass. A repository-wide run exposed only the previously documented legacy foundation-profile regression; both failing PostgreSQL tests pass after the compatibility fix. Live runs advanced through route generation, integration, and a successful build, but the newest run still ended `needs_attention` before preview promotion, so this is not a claim that the requested two accepted portfolios were achieved. The shared commit also contains pre-existing engine-input, `PLAN.MD`, and architecture-document changes that entered the index concurrently; this entry makes no Code Generator ownership claim for those files.

### 2026-08-28 19:30 +05:30 - Codex (GPT-5 / OpenAI) - [26d1a61] - integrate Build Preparation into the four-stage pipeline
Connected the main native workflow as Discovery → Content Architect → Visual Design Director → Build Preparation. A shared DB projection integrator now gives Build Preparation the approved public Content Architect handoff and approved Visual Design Director handoff, strips private content notes, normalizes visual inputs, and stamps one source reference used by both the API and worker. The session route now requires both approvals and exposes verified ZIP download with stale/expiry/object checks.

The main UI now presents the four-stage gate rail, package source hashes, package metrics/findings, download and regeneration actions, and detached/no-auth messaging; the diagnostic fixture remains explicitly standalone. Native model routing selects the configured Luna profile for the four pipeline stages while Code Generator routes remain separate. Focused unit, API, integration, static, and browser checks pass. A synthetic live UI run reached the configured Luna provider but was rejected for unavailable provider credit; no mock response was substituted.

### 2026-08-28 18:28 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - accepted-mode fix (557201b) confirmed live; new, separate bug found (not yet fixed)
Confirmed via three separate live runs on the fresh real pack: zero
`GENERATION_UNIT_ACCEPTED_WITHOUT_CHANGES` occurrences after 557201b,
across runs that previously hit it reliably. The model now correctly
uses `mode="changes"` or honestly declines with `mode="cannot_complete"`
instead of falsely claiming "accepted". This was the session's actual
blocking bug and it is fixed.

A new, separate bug surfaced once that one was out of the way: a
route-batch unit's first call correctly returns `mode="changes"` with
real files, but if that response is later rejected by a downstream
check, the retry's `cannot_complete` response cites `safe_reason:
"existing_files is empty and no rejected or current source bodies
were supplied"` - and on disk, no `candidate-<unit>/` directory exists
at all for that run, confirming the rejected attempt's content was
never persisted anywhere `_operation_context`'s `previous_attempt_files`
logic could read it back from on the retry. Not yet diagnosed further
(no code change) - this needs the same kind of focused, evidence-first
investigation as the accepted-mode bug got, not a rushed guess. Left
for a fresh investigation pass rather than continuing under time
pressure on top of an already very long debugging session.

### 2026-08-28 18:05 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [557201b] - root cause found: forbid accepted mode unconditionally in _model_result
Traced the retry evidence from the previous entry to its exact cause.
`_run_unit`'s main dispatch loop reassigns its local `operation`
variable to `"repair"` after ANY validation failure
(`SourceValidationError`, `run_source_checks` diagnostics, route-batch
contract diagnostics) purely to select the repair prompt for the
retry - a different, mid-generation meaning of the string "repair"
than `FinalRepairer`'s standalone post-generation operation (a
separate function that never routes through `_model_result` at all).
The prior fix's allowlist (`operation not in {"integrate", "repair"}`)
treated both as the same thing, so a mid-generation diagnostic-retry
was allowed to answer "accepted" instead of fixing the diagnostic -
exactly what happened: route-batch-1's first call correctly returned
real changes, hit a validation diagnostic, retried with `operation`
now "repair", and answered "accepted" on the retry, which the
allowlist let straight through. `_model_result` has exactly two
callers and both already treat "accepted" as unconditionally invalid
on their own terms regardless of operation, so `validation_context`
now forbids it unconditionally rather than trying to enumerate which
operation names are safe.

### 2026-08-28 17:56 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - new evidence on the accepted-mode bug: it is a retry, not a first-time call (root cause still open)
On the fresh real pack (post context-ceiling fix), planning and
acquisition succeeded and route-batch-1 got a genuine, correct
`mode="changes"` response on its first model call (confirmed: cache
file `ae66e576...json`, real file content). ~13 seconds later a SECOND
call for the exact same unit produced `mode="accepted"` (cache file
`23dd3d5e...json`), and that is the one the run failed on with
`GENERATION_UNIT_ACCEPTED_WITHOUT_CHANGES`. This means the earlier
"first-time generation never has anything to accept" framing behind
the three prior fix attempts (5a89eb0, c354841, 2a4a345) is incomplete:
this specific failing call was a retry of a unit that DOES already
have prior content in its context (most likely triggered by a
SourceValidationError on the first response, which feeds the rejected
attempt back into context for a repair-round retry) - not a truly
first-time call with nothing to accept. The retry still passes
`operation="route_batch"`, which the existing validator still gates
via `forbid_accepted_result=True`, so it is not yet clear why the
validator did not block it even under this corrected understanding;
isolated testing continues to prove both validators correctly reject
this exact payload/context shape outside the worker process. No code
change from this entry - flagging the corrected mental model for
whoever continues, since the earlier "blanket-forbid for route_batch"
premise itself may need to become context-aware (checkpoint/prior
content aware) rather than purely operation-name-based, once the
non-firing mystery is actually resolved.

### 2026-08-28 17:46 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [d36c053] - raise the generation context ceiling for rich real content; produced a fresh eligible Build Preparation pack
The original expired pack was replaced by regenerating one live: the
default VDD fixture file (`Input-Output-Of-Engine/Visual Design
Director output.md`) turned out to have been overwritten with an
incomplete mid-build snapshot at some point this session, so restored
the last committed complete version (`git show 5ca0b85:...`) and paired
it with the current real, approved Content Architect output via
Build Preparation's detached fixture endpoint. That run also revealed
`build_preparation`'s configured Anthropic profile has an exhausted
credit balance (a billing issue, not a code bug - flagged for the user
separately) - routed around it with an explicit `model_profile=
"openai_luna"` override, which worked. The resulting pack materialized
correctly but the fixture endpoint's default output directory doesn't
match where Code Generator's own pack discovery scans
(`build_preparation.fixture_output_dir` vs `code_generator_development.
build_preparation_mirror_root` are two different config keys pointing
at two different directories) - copied the pack across rather than
chasing that config split under time pressure. The resulting fresh
live run then hit `GENERATION_CONTEXT_LIMIT` on real, richer 6-section
content even after existing per-unit scoping; see the paired commit
for that fix's own detail.

### 2026-08-28 17:15 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [664d88e] - explain token name format in the planner prompt
The only eligible Build Preparation pack expired, so switched to
Code Generator's own fixture-based `/runs` entry point (bypasses
Discovery/CA/VDD/Build Preparation entirely, same real live pipeline
otherwise) to keep testing. Two fresh fixture runs
(`privacy-safe-v3-rich`, then plain `privacy-safe-v3`) both failed
`PLANNER_OUTPUT_INVALID` on "token names must be lowercase semantic
identifiers" - the schema requires `^[a-z][a-z0-9-]*$` for color/
spacing/size/radius/motion token names, but `planner.md` never stated
that rule, so a natural choice like a bare numeric spacing scale
("1", "7") fails validation. Same pattern as this session's earlier
token_compiler.py/route_batch.md fixes. Retrying to see if this
resolves planning.

### 2026-08-28 15:40 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [2a4a345] - add a diagnostic backstop for the still-unresolved accepted-mode bug (root cause open)
Three consecutive live retries (prose fix, operation-aware prompt-instruction
fix, validation-context schema check) all failed to stop the model
from returning `result="accepted"` for a first-time route-batch unit.
Isolated testing proves the new validator correctly rejects this exact
payload/context shape outside the worker process; inside the live
worker it evidently still is not firing, through a mechanism not yet
identified. Ruled out: stale bytecode (tried a full process restart
with the bytecode cache cleared), a non-editable/duplicate install
(confirmed the venv's editable install points at this `src/` tree),
and a pre-validated-instance short-circuit (the OpenAI-compatible
provider always returns a plain parsed dict). Added a loud, specific
backstop instead of continuing to guess: if an accepted envelope with
`forbid_accepted_result=True` ever reaches the post-validation point
regardless, it now raises `GENERATION_DIAGNOSTIC_VALIDATOR_DID_NOT_FIRE`
with the actual operation/context/envelope-class observed. Further
live testing is blocked: the only eligible Build Preparation pack
expired mid-investigation (`expires_at` 2026-08-28T10:06:34Z). This is
honestly an open investigation, not a claimed fix - flagged for the
next session/agent to pick up with fresh live budget and a fresh pack.

### 2026-08-28 15:21 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [c354841] - reject result:"accepted" at the schema level for fresh generation
The prose fix (5a89eb0) held for zero live attempts: with
`strict_schema=True` the provider enforces the JSON schema's own enum
directly, so a model sampling under constrained decoding can still
choose "accepted" regardless of surrounding instructions - two
consecutive live retries proved this (a different unit failed each
time). `GenerationResult`/`SourceGenerationEnvelopeV2`'s existing
`@model_validator(mode="after")` hooks now accept a `ValidationInfo`
and reject `mode`/`result="accepted"` when `_model_result` marks the
operation `forbid_accepted_result=True` (route_batch/route_compose;
integrate/repair still legitimately allow it) via
`model_validate(..., context=...)`. A live occurrence now raises a
real `ValidationError` that the existing 2-attempt schema-correction
retry loop catches and feeds back to the model explicitly, instead of
silently reaching `GENERATION_CHANGES_MISSING` with no path to
recovery.

### 2026-08-28 13:08 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [5a89eb0] - stop unconditionally offering result:accepted to fresh-generation calls
The prior fix's prose guidance in route_batch.md/route_compose.md did
not hold on a live retry: the model chose `result=accepted` for a
different unit (batch-1 instead of batch-2) despite it. The real cause
sat one layer deeper - `build_instructions()` unconditionally appended
"Set mode/result_tag to exactly one of changes/requests/accepted/
cannot_complete" to every operation's task text regardless of whether
that operation's context ever shows prior accepted content, and that
line, sitting closer to the generated output than the earlier prose,
evidently won out. It is now operation-aware: route_batch/route_compose
list only changes/requests/cannot_complete with an explicit "never a
valid choice here" line; integrate/repair (which do legitimately
review existing content) keep all four. Regression tests cover both
the `mode` (GenerationResult) and `result_tag`
(SourceGenerationEnvelopeV2, the actual live path) wording.

### 2026-08-28 13:00 +05:30 - Claude Code (Claude Sonnet 5 / Anthropic) - [510d8d1] - explain result:"accepted" semantics and diagnose its misuse
Two fresh confirmation runs both hit `GENERATION_CHANGES_MISSING`
deterministically during route-batch generation. Adding the actual
`result` mode to the error (instead of the generic "did not include
changes" message) revealed the model was returning `result:"accepted"`
for a route batch that had never been generated before - a schema
value neither `route_batch.md` nor `route_compose.md` ever explained.
Also found `integrate.md` telling the model to return `files: []` for
"nothing to change", which `SourceGenerationEnvelopeV2`'s own
validator rejects; `"accepted"` is the schema's actual mechanism for
that case, just never named correctly in the prompt. Confirmed the
route-batch/compose fix and this correction don't conflict: the
integration unit kind returns through its own early branch before ever
reaching the dispatch code this touches.

---

## Compacted history

### 2026-08
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [86824a7] - Font bindings now preserve per-file weights and token compilation avoids double prefixes; prompts document the group-prefix convention.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [8f50f4b] - Quality-review rejection is persisted with its real diagnostics instead of being discarded during repair failure.
- 2026-08-28 - Claude Code (Claude Sonnet 5 / Anthropic) - [eef4c7d] - Test overlay now points at reachable PostgreSQL and marks the previously skipped integration files; it also documented a separate legacy foundation-profile regression.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5dc23b2] - V4 route composition audit now honors planner-owned paths and section ownership, while invalid repair responses stay out of the cache.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [65801b7] - Source audit preserves planner route storage keys instead of deriving a second path identity.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [17fd5e3] - Standalone UI exposes verification retry after a failed job returns the run to source-ready.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f20f5c5] - Terminal verification and new source generation clear stale job bindings so same-run retry remains available.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5e3ea5c] - Host-only source normalization rebinds quality receipts to the updated checkpoint hash before verification.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [a63162d] - Successful owner-scoped integration polish is persisted as the resumable source checkpoint.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [4c8f361] - Stated the v4 repair envelope invariant explicitly (exact signatures, coverage arrays) so valid corrections stop being rejected for missing transport metadata.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [1b447a4] - Preserved the v4 schema discriminator through repair-context compaction so returned coverage is interpreted through the correct envelope.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f72ab5e] - Trimmed repair context to route/contract/diagnostic essentials to fix a GENERATION_CONTEXT_LIMIT failure from supplying complete owned files.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [bf0e076] - Repair context now falls back to authoritative current file contents when no rejected candidate tree exists, fixing a repair-context authority gap.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [f536178] - Canonicalized the reviewer's "-composer" owner alias to the real "-compose" work unit ID, fail-closed for unknown owners.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [bb9454e] - Made the source audit trace content IDs consumed through a .map() callback, instead of failing to prove their contentValue() calls.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [93771b9] - Made the source audit resolve the @/ SharedSystems alias and array-held content IDs statically instead of rejecting both valid forms.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0b46913] - Made the source audit scaffold part of the trusted shell files restored on workspace open, so it can't silently regress to an older version.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [20ea8b8] - Scoped composer contexts to their exact owned paths only, fixing a second GENERATION_CONTEXT_LIMIT from a stale full-src-inventory filter.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0a6dcfe] - Enforced one literal section anchor/DOM id per owned TSX file for split route batches, and widened the V4 audit to count rendered section modules.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [0431996] - Cleared stale rejected-attempt diagnostics on same-run resume so retries validate against the restored source tree instead of replaying pre-repair audit findings.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [ffac6f6] - Bounded resumed source-generation context to owned-file inventory to stay under the 120k-character ceiling during repair.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [958b27a] - Added a worker-thread Popen fallback for Windows batch toolchain launches when async launch modes fail.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [27b9679] - Retried denied Windows process-group launches without the optional new-process-group flag.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [90f2a82] - Routed allowlisted .cmd/.bat toolchain commands through the Windows command interpreter to fix [WinError 5] Access is denied.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [253b1fa] - Preserved the OS-level error in toolchain start-failure diagnostics so a native launch failure is observable.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [414b0c7] - Enforced route-scoped (not shortened) DOM anchor IDs at route-batch checkpoint time, reopening stale checkpoints on violation.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [ab3672f] - Validated route-batch named local imports/re-exports against target-module exports before checkpoint, reopening stale invalid batches.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [8ee6947, 4bd5d7b] - Bounded retry diagnostics to the active work unit so unrelated composer history stopped crowding out the context ceiling (4bd5d7b's own entry was written then deleted as a near-duplicate of this one without swapping in its real hash; folded in here instead of left orphaned).
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [eb55728] - Gave route batches an exact trusted-module import map and bounded resolver before checkpointing, with same-run reopening of stale batches.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d620d1f] - Removed batch-owned content IDs/facts/route bindings from V4 composer context, and added a same-run resume path for terminal queued/checkpointed runs.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [c0b4087] - Gave same-run generation retries fresh durable job identities (keyed by run revision) so a terminal retry always gets a worker job.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [772bef1] - Aligned V4 composer content contract so composers reserve content-key coverage for section-owning route batches, not themselves.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [70b024d] - Fixed the detached generator shell to import the main Code Generator module at its computed asset version, preventing stale cached controls.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [5edcb30] - Trimmed composer context (dropped duplicate generated-content interface) to resolve GENERATION_CONTEXT_LIMIT, and added same-run "Resume generation" in the standalone frontend.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [e12d787] - Deferred the whole-site route audit out of the route-batch phase so batch diagnostics stop targeting the still-scaffold route shell.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d5247dd] - Made V4 resource coverage reporting require the complete work-unit slot assignment, not just used slots.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [169ea5f] - Exposed a bounded generated-content.ts interface excerpt to route-batch context instead of omitting it entirely.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [fb1c209] - Required every V4 typography binding to declare an explicit body/display role instead of silently defaulting to body.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [cbe4491] - Bounded Code Generator operation context to the active work unit's plans/projections/APIs/dependencies to fix a ~245k-character context overflow.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [d1a229d] - Made source/toolchain checks phase-aware so the whole-site AST audit defers until route composition/final integration.
- 2026-08-28 - Codex (GPT-5 / OpenAI) - [8c07530] - Fixed JSX-element AST field reads in the source audit and made V4 typography custom-property emission collision-safe.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [caead48] - Made optional dependency installation transactional (disposable sibling workspace) so a rejected fallback package can't poison the toolchain check.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [d4fe70f] - Added a deterministic route/section identity manifest and host-side identity validation so V4 planning can't invent or reuse region ownership IDs.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [1e3610e] - Fixed the native dev launcher's UV cache path and PowerShell path-quoting for repository paths containing spaces.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [78ee3ea] - Removed the unreachable Code Generator foundation model profile/routing/prompt (confirmed dead; foundation stays a deterministic compiler boundary) and corrected architecture docs.
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [e945f54] - Made the preview gateway part of the default Docker stack with a real async health probe, and set strict public-readback only on the hosted overlay (D-054).
- 2026-08-27 - Codex (GPT-5 / OpenAI) - [b92a86c] - Root-caused and fixed the stuck detached run: API/worker were split across a stray port-5545 Postgres and the canonical 5432 instance; stopped the stray process, abandoned the orphaned run, and fixed a WorkGraph compiler bug that collapsed unique V4 section owner IDs into one.
- 2026-08-26 - Claude Code (Claude Sonnet 5 / Anthropic) - [b4f7daa] - Fixed advance_after() building a real (version-0) authorization context for detached runs, which silently blocked every auto-chained stage advance.
- 2026-08-26 - Claude Code (Claude Sonnet 5 / Anthropic) - [9b2d28f] - Relaxed the V4 font-role file-set check to a subset match instead of requiring exact equality.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [e5d55f9] - Classified local PostgreSQL credential failures as an actionable 503 and added secret redaction across detached diagnostics.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [8a918f3] - Allowed both native dev ports in the local origin allowlist to fix ORIGIN_NOT_ALLOWED on an alternate port.
- 2026-08-26 - Codex (GPT-5 / OpenAI) - [7c44add] - Added the no-auth standalone Code Generator control room (Build Preparation mirror bootstrap, Luna routing, inspector UI) with safe export receipts/generation-report.md.
- 2026-08-26 - Codex (model/provider omitted) - [9b39fe3] - Replaced generic repeated resource searches with profession-aware image/component roles and added provider/rate-limit guards.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [5d6886a] - Added Anthropic-specific credit-exhaustion error markers, which previously fell through to a generic provider-error bucket.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [8e93fc2] - Fixed role_for()'s fallback wrongly promoting unrecognized sections to the required "selected-work" role; added a genuine low-stakes fallback.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [2f9403b] - Added per-provider rate-limit backoff to the component-registry fetch path, matching the existing image-fetch cross-query memory.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [2a6fb12, 60a41a3] - Added ID-stability guidance to the VDD full-pages reconciliation prompt (was inventing composite content_ref IDs) and fixed the worker never calling configure_logging().
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [ed9de3b] - Gave component materialization the same alternate-candidate retry loop as images, removed ~190 lines of dead code, and enriched execution-gap messages.
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [40d0477] - Added a detached-auth router for the standalone Code Generator dev harness, selected when auth.pipeline_mode == "detached" (D-053).
- 2026-08-25 - Claude Code (Claude Sonnet 5 / Anthropic) - [53cd913] - Fixed /dev hardcoding pipeline_mode="attached" instead of following config, and stopped the frontend collapsing session-create failures into a generic message.
- 2026-08-25 - Codex (model/provider omitted) - [87cad46] - Extended detached mode through Build Preparation fixture/progress APIs and redirected detached /sign-in to /app (D-052).
- 2026-08-25 - Codex (model/provider omitted) - [b70dde2] - Fixed the detached Build Preparation frontend/CLI exposing the internal build_preparation engine route as a selectable profile.
- 2026-08-25 - Codex (model/provider omitted) - [c9f0a95] - Hardened the native live Build Preparation path (Luna output-shape recovery, fixture stamping, image-candidate retries); verified a live pack ZIP end to end.
- 2026-08-25 - Codex (model/provider omitted) - [62166f3] - Converted deterministic output-contract failures into bounded, privacy-safe retries across Discovery/CA/VDD.
- 2026-08-25 - Codex (model/provider omitted) - [5f272b3] - Shortened the Build Preparation checkpoint revision ID to fit Alembic's version column and hardened the native doctor's schema check.
- 2026-08-25 - Codex (model/provider omitted) - [9055cc3] - Aligned test-profile timeouts across every bounded model workflow and added detached-only authorization inventory coverage for the model-profile preflight API.
- 2026-08-25 - Codex (model/provider omitted) - [c19e4a1] - Detached-only safe profile listing/preflight, sticky four-stage model selection, live Build Preparation progress, and native PostgreSQL/auth/migration diagnostics.
- 2026-08-25 - Codex (model/provider omitted) - [5b5df50] - Unified retry/timeout decisions, redacted per-operation receipts/live progress, and source/profile/candidate-bound Build Preparation stage checkpoints (D-051).
- 2026-08-25 - Codex (model/provider omitted) - [2614bde] - Centralized provider-neutral model runtime (profile routing, capability validation, preflight caching); removed live mock fallback.
- 2026-08-25 - Codex (GPT-5 / OpenAI) - [15cf585] - Config-driven detached development mode for Discovery-through-Build-Preparation, with session classification, no-store behavior, and a Restart Pipeline action.
- 2026-08-25 - Codex - [540d33a] - Canonical native/Docker dual-mode development runbook and the isolated Docker Code Generator overlay.
- 2026-08-24 - Codex (GPT-5 / OpenAI) - [a39bd7e] - Reduced Anthropic interactive latency for the first three agents (lower budgets/effort, safe JSON control-character recovery).
- 2026-08-24 - Codex (GPT-5 / OpenAI) - [563b2a6] - Forced Google account selection after sign-out via `prompt=select_account`.
- 2026-08-24 - Codex (Claude Sonnet 5 / Anthropic) - [3b3ed9f, 456db9c] - Routed all four model-backed agents through Anthropic Claude Sonnet 5; a live Build Preparation pack materialized and correctly landed `needs_attention` on two real VDD execution gaps.
- 2026-08-24 - Codex (GPT-5.6 Luna / OpenAI) - [9b95baf, bf8f63d] - Routed all four model-backed agents through a direct OpenAI Luna profile; live calls reached OpenAI but stopped at `credit_balance_exhausted` before any pack materialized.
- 2026-08-24 - Codex (model/provider omitted) - [e70b6ab, dddc1ba] - Open Google registration admission mode (open/allowlist, D-048) and matching auth-handoff documentation.
- 2026-08-24 - Codex (model/provider omitted) - [449b379, c5b5821] - Authentication redirect-flicker fix and final Supabase/PKCE/Admin-API readiness hardening ahead of owner browser acceptance.
- 2026-08-24 - Codex (model/provider omitted) - [b17227c] - Phase 4 administrator lifecycle, audit, and resumable deletion/reset.
- 2026-08-24 - Codex (model/provider omitted) - [90d5dfe] - Phase 3 portfolio entitlements, durable owner/actor snapshots, and worker fencing.
- 2026-08-24 - Codex (model/provider omitted) - [d288077, 48e5f6c] - Phase 2 session ownership/API authorization (D-045) and the Phase 1 Supabase Google-only auth foundation.
- 2026-08-23 - Codex - [c9ad71d, 0f9bc0d, a03ba6f] - Authentication research, prerequisite verification, provider selection, and minimum-route implementation handoff.
- 2026-08-23 - Codex - [5ca0b85] - Code Generator V4 source realization, quality/runtime contracts, preview hardening, and stable retry semantics.
- 2026-08-21 - Codex - [3437075, 26890c5] - V4 quality/read-back promotion gates, provider contracts, runtime verification, and preview reliability.
- 2026-08-21 - Codex - [5fcbdd4, 1b37748, 0b7a806, 7eac824] - Provider-neutral routing, standalone runbook, hosted preview architecture, generation, verification, and atomic promotion.
- 2026-08-21 - Codex (GPT-5 / OpenAI) - [0240f57] - Lightweight LLM observability research and metadata-only tracing recommendation.
- 2026-08-21 - Codex (GPT-5 / OpenAI) - [b6a2be5] - First-three-agent Docker startup recovery runbook and verified frontend/API/worker state.
- 2026-08-21 - Codex (live provider run) - [0e965fd] - Code Generator provider contract, planner admission, and Docker workspace portability.
- 2026-08-20 - Codex - [f726d03] - Native Claude Sonnet 5 Code Generator provider adapter and structured-output handling.
- 2026-08-20 - Codex (live Docker run) - [3ced105] - Standalone Code Generator Docker runtime recovery and live provider attempt.
- 2026-08-20 - Codex (live Docker run) - [8cdbfb8] - Docker route-generation workspace, dependency, and typecheck reliability fixes.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [6e2c072] - TypeScript source-contract audit and exact browser/runtime verification.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [e8d6ec1] - Build Preparation pack-v4 delegated acquisition and deterministic resource handling.
- 2026-08-20 - Codex (GPT-5 / OpenAI) - [86b3e8d] - Design-neutral Code Generator V3 generation, typed experience tokens, trusted shared systems, route-batch ownership, isolated scheduling, and source regressions.
- 2026-08-20 - Codex (GPT-5) - [0c4901f] - Fenced stage attempts, immutable workflow artifacts, trace metadata, retry classification, worker readiness, and content-addressed artifact repositories.
- 2026-08-19 - Codex (live provider run) - [8259231] - Grounded Build Preparation to Code Generator execution, exact-pack survival, verified preview promotion, and persistent local export.
- 2026-08-19 - Codex (live provider run) - [a01c030] - Docker fixture execution repair, read-only CA/VDD inputs, deterministic need IDs, package retention, and verified R2 read-back.
- 2026-08-19 - Codex (live provider run) - [33b7113] - Build Preparation execution runbook with verified links, secret names, detached/live commands, and handoff diagnostics.
- 2026-08-19 - Codex (live provider run) - [237e0ed] - Build Preparation response-schema alignment, normalization, live packaging, and R2 read-back diagnostics.
- 2026-08-19 - Codex (model/provider omitted) - [45eafdc] - Reusable Discovery/Content/Visual Docker runbook, migration repair, provider checks, startup, and verification steps.
- 2026-08-19 - Codex (live provider run) - [3c1ff43] - Code Generator provider fallback, source validation, responsive repair, runtime gates, and atomic preview/export.
- 2026-08-19 - Codex (model/provider omitted) - [8a85438] - Nested Build Preparation mirror discovery and exact-pack admission, with provider-consent retry remaining.
- 2026-08-19 - Codex (model/provider omitted) - [6afd672] - Production Code Generator v2, visual compiler, deterministic resources, workflow verification, and preview retention/promotion.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [6bdcb13] - Selected verified Build Preparation output and recorded pack identity, scope, bindings, hashes, and handoff distinction.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [da99302] - Build Preparation overview, authority files, resource flow, route inventory, handoff review, and regression coverage.
- 2026-08-18 - Codex (GPT-5 / OpenAI) - [273799b] - Contextual visual enrichment, alternate recovery, provenance bindings, aggregate diagnostics, and downstream reacquisition guards.
- 2026-08-13 - Codex (model/provider omitted) - [4c4f51d] - Four-phase Code Generator execution guide covering admission, planning, acquisition, generation, verification, repair, and preview.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [4c4f51d] - D-015 progressive text-only generation pipeline, trusted acquisition, workspace isolation, gates, and repair guidance.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [958b4d8] - Code Generator v1 architecture handoff, Build Preparation boundary repair, bounded generation, exact verification, and preview promotion.
- 2026-08-13 - Codex (GPT-5 / OpenAI) - [958b4d8] - Code Generator proposal refinement covering product pillars, deterministic orchestration, provider policy, workers, and preview promotion.
- 2026-08-18 — Codex (GPT-5 / OpenAI) — [cde016e, 42e92ec, 8909c09, 0bd8bb5, 646a0bb, 3e2831c] — Build Preparation boundary/semantic enrichment, local image retrieval, deterministic component-priority selection, and cache-free multi-provider component retrieval.
- 2026-08-17 — Codex / OpenCode — [e3d80c2, 3479c40, 2edc335, 7957f7e, 2903bd2] — Detached input pickup, provider diagnostics, real visual handoff, best-pack readiness, resource coordination, and preview-gateway hardening.
- 2026-08-17 — Codex (GPT-5 / OpenAI) — [fffd253, 9ed8fe4, d23bc09, e35dd62, 91aa906] — Code Generator workspace UI, checkpoint recovery, cross-agent Git policy, canonical core ownership, source contracts, and DOM/runtime/export verification.
- 2026-08-16–14 — Codex / OpenCode — [5bf4b5f, c091282] — Standalone Code Generator phases 1–4, provider/toolchain integration, progressive generation, clean builds, verification, repair, and atomic preview promotion.
- 2026-08-13 — Codex / OpenCode — [4c4f51d, d0a6b1d] — Pack-v3/v2 contracts, Code Generator admission/acquisition/planning, public-scope handoff guards, and the initial architecture/runbook documentation.
- 2026-08-12 — Codex (GPT-5 / OpenAI) — [0174a5b, 7c4580f] — Code Generator architecture research, Build Preparation admission & quality handoff, shared agent workspace UI.
- 2026-08-11 — Codex / Claude Code — [ea2267f, 39d16cf] — Build Preparation agent rebuild as Agent #4 (D-011), Phases 1–3 implementation (manifests, R2 storage, worker persistence, provider fallbacks).
- 2026-08-10 — Codex (GPT-5 / OpenAI) — [d4a4556] — Initial Portfolio Production Compiler implementation, Pexels integration, and fixture preview (D-010).
- 2026-08-08–09 — Codex / Claude Code — [bdc8822..a75810a] — Initial Discovery, Content Architect, and Visual Design Director agents, durable PostgreSQL worker queue, and core platform scaffolding.

---

## Compaction Procedure & Template (for AI Agents)

**Trigger:** If `CHANGES.md` reaches or exceeds **250 lines**, compact older entries before appending new work.

**Procedure:**
1. Keep the most recent **15–20** entries intact under `## Recent changes`.
2. Move older entries into consolidated single-line milestone bullets under `## Compacted history -> ### YYYY-MM`.
3. Recompute the `## Summary` block below.

**Entry Template (Copy verbatim for new entries, insert directly below `## Recent changes`):**

```markdown
### YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — [<commit-sha>] — <files/areas, comma-separated>
<One or two sentences: what changed, why, and related ADR references (e.g. D-0XX).>
```

---

## Summary (as of last compaction — 2026-09-02)

- Recent detailed entries retained: 20
- Compacted milestone bullets: 118
- Last updated: 2026-09-02 — Codex (GPT-5 / OpenAI)
