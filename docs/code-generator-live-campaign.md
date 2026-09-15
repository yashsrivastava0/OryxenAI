# Code Generator live campaign

This is the durable handoff record for the reliability campaign authorized on
2026-09-09. It is intentionally small and append-oriented so a later Claude
Code session can resume without guessing which Build Preparation output or
which live-call budget remains.

## Final reliability campaign - five-run cap (2026-09-10)

This is the superseding record for the continuation campaign authorized by the
owner after the reliability plan was implemented. It keeps the historical
campaign sections below intact, while recording the five final full-pipeline
attempts and the deterministic fixes made between them.

- Maximum full pipeline calls: **5**; consumed: **5/5**; accepted `ready`
  portfolios: **0/2**. No sixth full pipeline call was made.
- Final code revision: `5eca499` (with `c3fabdc`, `7a01ee9`, `3f07609`,
  `f1e74d3`, `40434cf`, and `ed21a6a` as the preceding reliability fixes).
- Release target: web/desktop, using the configured `desktop` (1440x900) and
  `laptop` (1280x800) journeys. Mobile CSS and optional controls remain
  supported, but mobile is not a release gate for this campaign.
- Provider and toolchain preflights were green with zero portfolio model calls;
  the worker matched release `oryxenai-code-generator-v5-quality-v3`.

### Full-pipeline outcomes

| Slot | Pack | Run / idempotency key | Terminal outcome | First causal evidence | Disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | B - `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `2512c969-b0c3-44cd-ba29-1cea626c9d35` / `b7b5f35d-3d12-4ee3-bc78-8e6e7a6ea101` | `needs_attention` - `DOM_RUNTIME_FAILED` | Build and source passed; runtime had no console/page/network errors, but an approved experience paragraph was rendered only inside an unplanned collapsed `Disclosure`. | Fixed by `3f07609`: canonical route source is supplied to repairs and hidden approved content is a blocking source diagnostic. |
| 2 | B - `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `6de0fdb3-c019-4413-a142-78691ec5414a` / `2a9c3b24-473d-4235-88d7-b0acd33f1b8e` | `needs_attention` - `INTEGRATION_REVIEW_UNRESOLVED` | The required capability disclosure selector was assigned to the route composer, so it wrapped a duplicate label rather than the capability section it was meant to expose. | Fixed by `f1e74d3`: selector ancestry and exact section aliases now determine interaction ownership. |
| 3 | B - `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `7b74c97b-f95e-4b77-986c-a6aed0f99b78` / `94700ede-442a-4b65-afbc-cb2d434f0f0d` | `needs_attention` - `SOURCE_REPAIR_TOTAL_EXHAUSTED` | Typecheck reported a one-character near-miss in a generated content-key suffix (`...7620ec24` versus canonical `...7620e261`); the actionable route contract was hidden behind the later typecheck failure. | Fixed by `40434cf`: route-batch contract diagnostics run immediately after candidate application and before npm/typecheck. |
| 4 | B - `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `fe4a0224-8f5f-4c3e-86a2-a1aafef8d621` / `4f4ecd47-1135-44bb-a077-3f3e097d81ac` | `needs_attention` - `SOURCE_REPAIR_TOTAL_EXHAUSTED` | The generated source used statically provable literal object/tuple collections, but the Python pre-gate and scaffold AST audit did not agree; the run reported a large false-positive content-key bundle (plus a custom-property observation). | Fixed by `ed21a6a`: bounded object-field, nested-array, and tuple-destructuring maps are resolved consistently by both validators. |
| 5 | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `20bdd7df-4604-48e0-ba36-3022eab10f0a` / `a1ca232f-045e-4609-a72d-d4fa452785a6` | `needs_attention` - `SOURCE_CONTRACT_FAILED` | Source generation, clean build, and integration quality review completed. The only blocking result was a validator false negative for a statically-known JSX marker (`data-motion={index === 0 ? "current-role" : undefined}`) implementing `motion:home:experience:current-role`; quality findings were advisory. | Fixed offline by `c3fabdc`: source and TypeScript AST audits accept exact literal or static conditional JSX markers. No sixth run was available to re-run build, verification, and preview promotion. |

### Final disposition and handoff

The last run retained a valid 53-file source checkpoint (`93c27537190a996a6b8ddaa67d1468561430b49da6654c26a55293cbeb85a4e4`, manifest `4d1ea57b96349343506d99aa3c3468d19d28221eb4ce2976f90567b5b99f1912`) and a successful build, but the campaign ended before the final offline fix could be exercised through the verification and preview-promotion gates. It is therefore not a successful `ready` result, and no Azure deployment or verified preview is claimed. Optional image omission remains valid when the approved brief has no suitable media; a rendered required image that 404s or fails decoding remains blocking. Start a new explicitly authorized campaign to prove the final revision end to end on the target Linux/Azure toolchain.

## Reliability-plan implementation campaign — five-run cap (2026-09-09)

This is a new campaign after reliability commit `a503a4a`. It is separate from
the historical campaigns below and begins before any new full pipeline call.

- Maximum full pipeline calls: **5**.
- Used: **3/5**.
- Accepted cross-pack portfolios: **0/2**.
- Slot 1 run revision: `a503a4a` (`fix(code-generator): enforce reliable generation lifecycle`).
- Current runtime revision: `90e8349` (`fix(code-generator): normalize typography token names`).
- State: slots 1 through 3 completed with `needs_attention`; slot 4 is unreserved and awaits the post-compiler-fix live confirmation.
- Execution rule: one full pipeline at a time; stop at two accepted results or
  after slot 5, whichever comes first. A verification-only retry that reuses
  an accepted source is recorded separately and does not consume a full source
  generation slot.

### Planned slot order

| Slot | Pack | Reason | Status |
| --- | --- | --- | --- |
| 1 | `c0860464-a786-43d8-9c30-d12d7516c4b8` | C reproduces the latest repair path and exercises its route-scoped abstract image slot. | needs_attention |
| 2 | `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | B provides a structurally different seven-section brief after slot 1 is diagnosed. | needs_attention |
| 3 | `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | A provides the remaining current seven-section variation and confirms the early disclosure gate. | needs_attention |
| 4 | choose after the preceding result | Confirm the typography-token fix against a structurally different pack if the run adds evidence. | unreserved |
| 5 | choose after the preceding result | Final authorized slot under the cap. | unreserved |

### Preflight record

The effective non-secret settings, scaffold/dependency/prompt identities,
input hashes, toolchain facts, gateway reachability, and provider readiness
were recorded before slot 1 was reserved. This section intentionally contains
no credentials, signed URLs, raw prompts, or private brief content.

- Preflight completed: 2026-09-09 20:53 +05:30.
- Provider: `ready`; six configured Code Generator profiles checked;
  `private_context_sent=false`.
- Toolchain: `ready`; Windows `amd64`; Node `v25.1.0`; npm `11.6.2`;
  scaffold profile `react-vite-v1`; all install, TypeScript, Vite build,
  browser, workspace/cache, gateway, and brief-path checks passed; `model_calls=0`.
- Scaffold hash: `15bccf3eccba8fa70423d75ad5c56613fa65df1c9e31411fbfa3676153e83113`.
- Dependency pins hash: `4fa0bc05ecb4c5cc6f6bbd1e16daf8f49ec7687e726400cd6e91f78819000026`.
- Preflight lock hash: `d63f9af7f3b2c6aceca3a13db098ff0f6a2b364c689580330950154f85d1ac71`.
- Prompt catalogue hash: `e59a6102e7e1970ebd250992facb58ad5c0cbb0651c9662eeefc20733187b907`.
- Effective image policy before plan: minimum `1`, preferred `2`, primary-route
  requirement `true`; production route concurrency `1`.
- Eligible current pack contract hashes: C `bf077c5a360964138755be1d11b5acf64b828fa777ce4a142954ab808b261128`,
  B `bf27265ec7e4c27b9151e881b02b516916608f472508bd9eb835055bf1076215`,
  A `d3858b6133cc66bda14222ac7009530cf13c1990687a3a5b63f7b7ebd15b4ab9`.
- Slot 2 readiness refresh: 2026-09-09 22:40 +05:30 on `4da1ddb`; provider
  preflight was `ready` with six profiles and `private_context_sent=false`,
  toolchain preflight was `ready` with all checks passing, and the preview
  gateway was reachable. No full pipeline call was made by these proofs.
- Post-fix readiness refresh: 2026-09-09 23:43 +05:30 on `9716681`; provider
  preflight was `ready` with six profiles and `private_context_sent=false`,
  toolchain preflight was `ready` with all checks passing and zero model calls,
  the preview gateway was reachable, and the worker release contract matched.
- Post-compiler-fix readiness refresh: 2026-09-10 00:02 +05:30 on `90e8349`;
  provider preflight was `ready` with six profiles and
  `private_context_sent=false`, toolchain preflight was `ready` with all checks
  passing and zero model calls, the preview gateway was reachable, and exactly
  one worker matched the release contract.

### Reserved slots

| Slot | Reserved at | Pack | Code revision | Content hash | Visual hash | Contract hash | Idempotency key | Run ID | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-09-09 20:56:11 +05:30 | `c0860464-a786-43d8-9c30-d12d7516c4b8` | `a503a4a` | `0e88ebced8c350b04aab1bdeff4c1f430a0b3e5c7999379c3244e11df929e527` | `e3444c79571cdb92fbdc3be8356d056fd7203930946dafa18624198dc6cfa918` | `bf077c5a360964138755be1d11b5acf64b828fa777ce4a142954ab808b261128` | `542c3c11-415d-468c-947f-8d4654845fef` | `4dfd10cc-52bd-4fc7-8a6d-96addf47b26e` | needs_attention |
| 2 | 2026-09-09 22:44:09 +05:30 | `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `4da1ddb` | `db560919f26b359ce7836c40339c887b3faa001637452c2d672d1193b9155435` | `ff324462dc980bf29deb05bc4533716e55940babb40497170d668d8492f21f74` | `bf27265ec7e4c27b9151e881b02b516916608f472508bd9eb835055bf1076215` | `6fc66f93-259a-4ade-8341-e694e72a742f` | `2f22c091-32e7-47dc-bc99-aef25d4e8058` | needs_attention |
| 3 | 2026-09-09 23:43:58 +05:30 | `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `9716681` | `a839ee313e9786e3e77d60a4fa6bdce5a1f55dccff5f92349ac46e88419c5210` | `389ce59c85baafce6b734b105bff05bbbb7454d68a6a84f9848429e691cd0427` | `d3858b6133cc66bda14222ac7009530cf13c1990687a3a5b63f7b7ebd15b4ab9` | `d0d38741-9e93-4a47-8ae8-320e4ac2516e` | `bc4319fb-da84-4c00-88fc-9485a9087d9d` | needs_attention |

### Slot 1 result — Pack C

- Run: `4dfd10cc-52bd-4fc7-8a6d-96addf47b26e`; durable job: `c7b49a1a-8900-4349-a6de-86a21198978d`.
- Durable outcome: `needs_attention`, terminal code `INTEGRATION_REVIEW_UNRESOLVED`.
- Admission, planning, acquisition, and source generation completed. The run accepted a 62-file source checkpoint with hash `ae525b31bce45ec6d0a5ef6055121c4a6517ab8aa3f4186f303e13b8be992127`, source manifest hash `937d9a7a1c4b2e36ab28b96b0d7afa898917ba9b5ba68d76586bd4e6279576db`, and 2,154,124 bytes.
- The generation projection records 13 model calls/attempts and one repair round. The bounded whole-site review exhausted three integration polish rounds; verification and preview promotion did not run.
- The original receipt classified two subjective findings as blocking. `14bb97c` replaced keyword severity inference with explicit host-owned mappings, and `c8a66e7` plus `80a925c` keep terminal, run, quality, and product read projections truthful for historical data. The current read projection is accepted with all three findings advisory; this does not make the source a successful portfolio.

### Slot 2 execution - Pack B

- Durable run: `2f22c091-32e7-47dc-bc99-aef25d4e8058`; job: `9b75bb1c-5a7c-4369-b4cb-1e64ce565b0f`.
- The single POST was accepted with idempotency key `6fc66f93-259a-4ade-8341-e694e72a742f`; initial persisted status was `queued`.
- Durable outcome: `needs_attention`, terminal code `INTEGRATION_REVIEW_UNRESOLVED`. Admission, planning, acquisition, and source generation completed.
- Accepted checkpoint: `checkpoint-45ab339bb9940d8268e6`; checkpoint hash `45ab339bb9940d8268e63715b94aba6b88d607ddab30a27497c4a44bf372f5b4`; source manifest `dcfc97a0dde4af1fbfbd3592c37ea68fe36af77d78bc59fb7058884a095f4186`; 60 files and 2,173,891 bytes.
- Generation projection: 14 call receipts/attempts, three integration repair rounds, and repair budget used 3. Verification did not start and no preview was promoted.
- Final normalized quality findings: `blueprint-desktop-column-mismatch` advisory and `noninformative-disclosure` blocking. The blocking finding was an empty education Details panel: `<Disclosure label="Details"><span aria-hidden="true" /></Disclosure>` in `home-education-7cdb08f7.tsx` line 12. The grid-span observation conflicts with neither D-076 nor the runtime recipe contract and is now explicitly advisory.
- Commit `9716681` adds the early host-owned disclosure gate and clarifies the abstract grid-span contract in the generation/review prompts. Slot 3 is reserved only after this docs and service checkpoint is complete.

### Slot 3 reservation - Pack A

- Reserved at 2026-09-09 23:43:58 +05:30 with code revision `9716681` and idempotency key `d0d38741-9e93-4a47-8ae8-320e4ac2516e`.
- Pack `5f144f04-2789-48c6-9b1c-6bd11c87abdb` is the eligible Maya Bennett pair: one route, seven sections, eight resources, three components; content hash `a839ee313e9786e3e77d60a4fa6bdce5a1f55dccff5f92349ac46e88419c5210`, visual hash `389ce59c85baafce6b734b105bff05bbbb7454d68a6a84f9848429e691cd0427`, contract hash `d3858b6133cc66bda14222ac7009530cf13c1990687a3a5b63f7b7ebd15b4ab9`.
- Durable run `bc4319fb-da84-4c00-88fc-9485a9087d9d` and job `a6cd565a-663d-46ce-a9b6-6955e3d21f41` were accepted at 2026-09-09 23:44:56 +05:30 with initial status `queued`.

### Slot 3 result - Pack A

- Durable outcome: `needs_attention`, terminal code `SOURCE_REPAIR_TOTAL_EXHAUSTED`; the run stopped during `generating_routes` after four bounded source repair rounds.
- Admission, planning, acquisition, foundation generation, and route batches one and two completed. The accepted checkpoint was `checkpoint-206348a511a77972369a` with hash `206348a511a77972369a79299c62545d94a5b7ca92e9663091a1a2ac3134572a`, source manifest `e0536ea55d794f68f5a14437f8f78ac9a8f4dac6a3096152e587915741ccb693`, 59 files, and 1,068,723 bytes.
- The generation projection persisted seven call receipts/attempts, four repair rounds, and budget used four. Route batch three remained pending; compose, integration review, verification, and preview promotion did not run.
- Root cause: the blueprint's `type-body`/`type-label`/`type-heading`/`type-display` names made the compiler emit `--type-type-*`, while the route response used canonical `--type-heading-*` and `--type-label-*` names. Commit `90e8349` normalizes the schema and compiler vocabulary and adds regressions.

## Current continuation campaign — five-run cap (2026-09-09)

This section supersedes the earlier four-slot campaign table below. The owner
authorized at most five full pipeline calls for this continuation. All five
were consumed in sequence, each was investigated before the next reservation,
and no sixth full pipeline call was made. Provider preflight and static checks
were run outside that budget.

### Eligible Build Preparation packs

| Pack | Profile | Evidence |
| --- | --- | --- |
| `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | Maya Bennett | Valid pair; 1 route, 7 sections, 8 resources, 3 components. |
| `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | Akash Ojha | Valid, structurally different pair; 1 route, 7 sections, 8 resources, 3 components. |
| `c0860464-a786-43d8-9c30-d12d7516c4b8` | Varun Dhawan | Valid pair; 1 route, 6 sections, abstract-systems illustration resource category. |

The empty-title/section pairs remain negative fixtures and were not selected.
The older four-route pair remains an offline regression fixture only.

### Full pipeline outcomes

| Run | Pack | Outcome | Earliest durable failure |
| --- | --- | --- | --- |
| `55234cbb-32f3-475f-8716-affce08c8c3f` | Maya | `needs_attention` | Acquire: `DEPENDENCY_INSTALL_FAILED` because native Windows could not start the configured `npm` shim; fixed in `d1c5645`. |
| `beb5e244-8787-4dcb-8c08-67fac19bcbe5` | Akash | `needs_attention` | Acquire: offline `npm ci` lacked platform optional/transitive cache entries; fixed in `2b2714a`. |
| `e5e32ac3-89d4-48ad-bbaf-4eb5e8927ee6` | Akash | `needs_attention` | Plan: incomplete content-key coverage/image placement; fixed in `97d83dd`. |
| `e39ee9e6-b71a-430b-bc7a-934046579f27` | Akash | `needs_attention` | Generation: admitted component imported unsupported `rough-notation`; fixed in `59bf982`. |
| `291ed5d7-6a7d-44c8-b024-fbb7dbf8c5c8` | Varun | `needs_attention` | Generation: bounded repair exhausted on stale `create` for an already-created stylesheet; fixed in `29fc598` by reconciling repair operations against the candidate tree. |

The fifth run acquired and materialized local image renditions but did not
reach a route checkpoint, clean build, preview, or `ready` state. Its planner,
route-batch contexts, calls, export, and source assets remain available for
offline inspection. The exact trace and fix are recorded in `code generator
issues.md`. Do not claim a successful ready run or Azure deployment from this
campaign.

## Archived prior four-slot campaign guardrails

- Maximum full pipeline LLM runs: **4**.
- Stop immediately after **one successful `ready` run**, or after a second
  success used as a cross-pack confirmation.
- A failed run is investigated from its earliest durable event/artifact before
  another slot is reserved. No direct handler invocation is allowed; live runs
  use the normal API → PostgreSQL job → worker → preview gateway path.
- Provider preflight and offline/static checks happen before slot 1. Provider
  credentials and model/profile selection remain configuration-owned.

## Selected Build Preparation inputs

| Slot candidate | Directory | Profile | Contract evidence | Status |
| --- | --- | --- | --- | --- |
| A | `output/build_preparation/5f144f04-2789-48c6-9b1c-6bd11c87abdb` | Maya Bennett | 1 route / 7 sections / 8 resources / 3 components; content `a839ee313e9786e3e77d60a4fa6bdce5a1f55dccff5f92349ac46e88419c5210`; visual `389ce59c85baafce6b734b105bff05bbbb7454d68a6a84f9848429e691cd0427`; contract `d3858b6133cc66bda14222ac7009530cf13c1990687a3a5b63f7b7ebd15b4ab9` | eligible |
| B | `output/build_preparation/ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | Akash Ojha | 1 route / 7 sections / 8 resources / 3 components; content `db560919f26b359ce7836c40339c887b3faa001637452c2d672d1193b9155435`; visual `ff324462dc980bf29deb05bc4533716e55940babb40497170d668d8492f21f74`; contract `bf27265ec7e4c27b9151e881b02b516916608f472508bd9eb835055bf1076215` | eligible |

The older `output/build-preparation/20-46-08-09-6b899b90` pair is retained for
offline regression comparison only. The two empty-title/section pairs are
negative rejection fixtures and must never be selected for a paid run.

## Preflight evidence

- `DevelopmentInputAdapter` compile probe: A and B accepted; malformed pairs
  rejected with `BRIEF_ROUTE_INVALID` before any model call.
- Provider preflight at 2026-09-09 03:20 +05:30 returned `ready` for all six
  configured Code Generator profiles; `private_context_sent=false`.
- Npm cache warm: configured supported pins installed in a disposable project,
  then a separate offline `npm ci` succeeded.
- Ruff, mypy, compileall, frontend TypeScript, and `docker compose config`
  passed. The frontend Vite/Vitest process is blocked by Windows `spawn EPERM`;
  this does not affect the backend contract or TypeScript check.
- Services were restarted from commits `2f424e5`/`45c38e3`; readiness reported
  `quality-gate-v3`, worker release `oryxenai-code-generator-v5-quality-v3`,
  reachable preview gateway, and provider preflight `ready`.

## Full pipeline slots

| Slot | Reserved at (Asia/Kolkata) | Pack | Run ID | Terminal status | Earliest failure / success evidence | Preview or artifact | Usage / notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-09-09 03:21 +05:30 | A | `4d009f48-050e-48a7-9611-82f3a5eecd91` | **ready** | Initial restricted worker hit Node/Vite `spawn EPERM`; after tracing, an elevated worker rebuilt the same checkpoint, browser smoke tests passed, and all 43 runtime observations were advisory | Preview `http://127.0.0.1:4174/preview/preview-6esue4fssmj3unpkzxeclt6onwqnxdwazwrdptyikrbtashb/`; export `output/code-gen-output/03-34-09-09-2026-4d009f48`; build `a07ca2b24ed904431d377df474ba8a47a7adfec3b1942bfe8440eabf08622f10` | One full pipeline slot; verification retry reused the accepted source checkpoint and did not start another planner/generation pipeline |
| 2 | **not reserved** | B | — | — | Stop after slot-1 success | — | Akash pack retained for future confirmation only |
| 3 | unreserved | — | — | — | — | — | Stop after two successes; reserve only after root-cause fix if required. |
| 4 | unreserved | — | — | — | — | — | Hard cap; reserve only after root-cause fix if required. |

## Handoff checklist

1. Restart API, worker, and preview gateway from this worktree and verify
   readiness reports the current quality-gate/release IDs and a reachable
   gateway.
2. Run provider preflight without portfolio data.
3. Reserve slot 1, run pack A, and poll the durable run/events/verification
   projections. If it fails, trace the first persisted failure and update this
   table before changing code or reserving slot 2.
4. If needed, reserve slot 2 with pack B only after offline regression tests
   pass. Stop on the first ready result, or after the second ready result.
5. Record any additional fix commit and the exact preview URL/artifact path;
   do not claim Azure deployment from local Docker/config validation alone.

## Pre-live-fix confirmation campaign — bounded five-run cap (2026-09-10) — CLOSED

This is a new campaign after the 2026-09-10 final five-slot campaign. The
historical `Final reliability campaign` table above is unchanged. All five
live slots have now been consumed (a Claude Code -> Codex -> Claude Code
handoff occurred between slots 2 and 3, same shared 5-run budget), closing
this campaign with **one `ready` result (slot 5)** and four root-caused,
fixed, and offline-verified defects (slots 1-4). The campaign was
authorized for at most five full-pipeline runs, stopping at two
cross-pack ready results, an insufficient balance, or the fifth consumed run.

### Offline gate before slot 1

- The requested settings reconciliation is present: Pydantic defaults now
  match the effective 2/4/3 values in `config/app.toml`; that file was not
  edited. The dead `repair_depth` field remains by deliberate D-089
  non-decision.
- The focused settings unit suite passed (19 tests), mypy and Ruff lint for
  `settings.py` passed, and the targeted source/audit/repair/contract/export/
  image suites passed (138 tests) after the route-motion normalizer fix.
- After the slot-2 lifecycle fix, the required targeted suites passed 139
  tests. The exact slot-2 accepted source tree was copied to a disposable
  overlay, the host cue materializer was applied, and both `source:audit` and
  `typecheck` exited 0. The broader `pytest -k code_generator -q` selection
  was started after this fix but stopped at handoff; its last completed
  pre-fix baseline was 356 passed with four documented baseline/environment
  failures and 912 deselected.
- The verification-worker file had one already-documented
  `PLAN_SECTION_COVERAGE` fixture failure; the broader `-k code_generator`
  baseline had four documented pre-existing/environment failures alongside
  its passing tests. Repository-wide Ruff, format, and mypy gates also report
  unrelated dirty-worktree/untracked-file issues; these are recorded in the
  session handoff and are not attributed to the settings hunk.

### Exact checkpoint replays

Each saved tree was copied to a disposable temporary directory with its warm
`node_modules`; the saved trees were not modified and no model call or npm
install was used.

| Pack / historical slot | Saved tree | `source:audit` | `typecheck` | Evidence |
| --- | --- | --- | --- | --- |
| A / slot 5 | `.workspace/code-generator-generation/20bdd7df-4604-48e0-ba36-3022eab10f0a/repo/` | exit 0 | exit 0 | The conditional JSX motion-marker false negative fixed by `c3fabdc` produces no diagnostics. |
| B / slot 3 | `.workspace/code-generator-generation/7b74c97b-f95e-4b77-986c-a6aed0f99b78/repo/` | exit 1; 295 route-contract diagnostic lines | exit 0 | Route-contract failures surface in the audit independently before the clean typecheck result. |
| B / slot 4 | `.workspace/code-generator-generation/fe4a0224-8f5f-4c3e-86a2-a1aafef8d621/repo/` | exit 1; 295 older route-source diagnostic lines | exit 0 | Zero diagnostics match the literal object/tuple content-map false-positive pattern. |

For slot 2 diagnosis, the accepted tree at
`.workspace/code-generator-generation/f8a3d88c-9546-40fe-ae6b-714e775c4e24/repo/`
was copied without modifying the saved source. Applying the committed
selected-work normalizer to the copied generated section produced the missing
cue, and the disposable overlay passed `npm run source:audit` and
`npm run typecheck` with exit 0.

Slots 1 and 2 were reserved and consumed after the user supplied a fresh
provider check showing configured-key presence, successful model access (HTTP
200), and a successful live quota/credit test (HTTP 200). The earlier direct
balance attempt was inconclusive because the credit-grants endpoint returned
HTTP 403 and the browser billing overview required an interactive login; the
stale balance figures from earlier notes remain inadmissible.

### Live outcomes — append one row immediately after each run

| Slot | Balance check | Pack | Run ID | Terminal outcome | First causal evidence | Preview / acceptance evidence | Usage / notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Fresh user-supplied provider key/model/quota check; HTTP 200 | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `dd721d1e-cde9-4349-af50-27660ab6d779` | `needs_attention` - `SOURCE_REPAIR_EXHAUSTED` | Initial receipt `e170f1a784920512ef8fdefed1cb3849d28b41bcd9164493c401ad254bb21970` contained `fiftych`/`sixtyfivech`, a trusted hero-selector mismatch, and custom selected-work motion without the required guarded opacity/setter; final terminal evidence was the missing selected-work guard. | No verification, build, or preview promotion; accepted checkpoint `0584a38d4ab6058d064e249cfc4c83c44374262cf76099724609cef62aa57442` was pre-route foundation, so no ready result. | Full live slot 1/5 consumed. Generation job `d0b600f9-cc6b-440d-adc3-25eb5e5023c5` succeeded without a worker error; repair receipts `3343dd8d62d5a81a1313bdc8b228211134a772218d0a1ba38a423f44a7a76d72` and `f51d9622fdb8c79de6895b03a19894999261c0557f8521bde913015eaa5f4b44`. Host fix `22db99c` is offline-verified; retry A only after service restart and re-preflight. |
| 2 | Fresh user-supplied provider key/model/quota check; HTTP 200 | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `f8a3d88c-9546-40fe-ae6b-714e775c4e24` | `needs_attention` - `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` | DB run evidence points to the accepted checkpoint `b89f1e433d7e3339831da46c7112c79cdeef57e84a552a938446aaa89ca53c29`; integration review had one blocking `missing-selected-work-lifecycle-cue` finding at `src/routes/home-4ea14058/sections/home-selected-work-2f0991ad.tsx:5`. The section rendered its intro and three work articles but no conceptual lifecycle cue/marker. | No accepted ready result or promoted preview. Plan, acquire, generate, and verify jobs all succeeded without an error payload; the bounded repair receipt `5ac54cd735290adb8b6582ce6eb44971575c5413cfc563b1fab113f34e02ddfe` (ledger file `65c8da3a510d5134ac4c6ce25bd6d57e7d833272b9ee3f081e7ba31fa9d4d61c.json`) changed only hero CSS, leaving the blocking selected-work cue absent. | Full live slot 2/5 consumed. Commit `d9caf30` materializes the blueprint-required cue deterministically; targeted suites passed 139 and the exact accepted-tree overlay passed `source:audit`/`typecheck` with exit 0. Retry A only after service restart and fresh preflight. |
| 3 | Fresh provider key/quota check (GET /v1/models HTTP 200; trivial gpt-4o-mini completion HTTP 200) | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `5cf49daa-7ff5-404c-b884-d17cae272598` | `needs_attention` - `SOURCE_CONTRACT_FAILED` | Accepted checkpoint `b3d5da49e957053ce94c72daa2d759e7725f9822b6cda1f0503c7ea95057e7a3`; two blocking diagnostics on motion beat `motion:home:hero-lifecycle-reveal` (`SOURCE_MOTION_BEAT_UNIMPLEMENTED`, `SOURCE_MOTION_REDUCED_MOTION_MISSING`) at `src/routes/home-4ea14058/sections/home-hero-ecdc18c2.tsx`. The model correctly rendered the trusted `<Reveal>` component for catalogue pattern `reveal-fade-rise`, but `typescript_ast_audit.py`'s final motion-beat check had no trusted-pattern exception (unlike `source_validation.py`'s pre-gate and the route-motion normalizer) and demanded CSS/reduced-motion evidence that legitimately lives in `SharedSystems.tsx`/`motion.css`. | No verification success or promoted preview; repair_receipts empty (rejected at the final source-contract gate, not during bounded repair). | Full live slot 3/5 consumed. Commit `e7d9284` mirrors the existing trusted-pattern exception into `typescript_ast_audit.py`; verified 2 → 0 diagnostics against the exact rejected checkpoint offline. Retry A for slot 4 after this fix. API this session ran without `--reload` on port 8001 to avoid a local Windows uvicorn/asyncio SelectorEventLoop subprocess bug unrelated to Code Generator logic (see `code generator issues.md`). |
| 4 | Fresh provider key/quota check (GET /v1/models HTTP 200; trivial gpt-4o-mini completion HTTP 200); fresh toolchain+provider preflight | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `0b56cda5-59a4-4bd6-b8f0-2fe548d5d0e3` | `needs_attention` - `SOURCE_REPAIR_EXHAUSTED` | Accepted checkpoint `e619daae8ee9abe8f777992e7da452f4eedb5ffe22a8b590c8af4fdf1e1a34bd` (foundation only). After 2 genuine model repair rounds, 3 final blocking `SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND` diagnostics on `home-selected-work-2f0991ad.css` (`--color-accent-signal`, `--color-border-subtle`, `--color-ink-secondary`) -- all from `d9caf30`'s deterministic lifecycle-cue normalizer, which hardcoded assumed color token names that don't exist in this run's own generated tokens (color names are chosen per run by the model, never fixed). Two earlier transient diagnostics on the hero section were already resolved by the model's own repair before termination. | No verification success or promoted preview; the broken CSS lived in normalizer-injected code the model is never asked to repair, so it recurred unchanged across both rounds while the model fixed its own real mistakes elsewhere. | Full live slot 4/5 consumed. Commit `06eb2c0` resolves real tokens dynamically instead of hardcoding assumed names; verified 3 → 0 undefined references against this run's real tokens offline. Live services were killed twice by host OS memory pressure from unrelated desktop apps during this slot; the durable job queue resumed the in-flight run cleanly both times with no code change needed. One slot (5) remains. |
| 5 | Fresh provider key/quota check (GET /v1/models HTTP 200; trivial gpt-4o-mini completion HTTP 200); fresh toolchain+provider preflight | A - `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | `ff3398b1-86cb-49cd-b12b-5f5857ded187` | **`ready`** | All three verification gates passed with zero blocking diagnostics: `source_contract` (0 blocking), `type_build_artifact` (0 blocking), `dom_runtime` (0 blocking, 57 advisory layout findings -- e.g. a few regions rendering 2 columns where the contract expects 1, one distinctive-move width ratio outside its declared range -- none blocking, all real and worth a future pass, not fabricated as zero). `active_preview` populated with a real promoted preview and receipt hash. | Promoted preview `http://127.0.0.1:4174/preview/preview-3uc4dd7inyzsszvpaakxjgppqyni72d4wckhsmke7zxkkzzn/` was loaded in an actual Chrome tab (not inferred from DB status alone): real generated content rendered across every section (Hero, Positioning, Selected Work with 3 real case studies, Capabilities with 4 skill categories, Experience with 3 roles, Credentials with an honest "pending verification" placeholder, Connect); a live nav-link click (`Capabilities`) updated the URL hash and the nav's active state correctly; zero console errors/exceptions; every real network request (document, JS bundle, CSS bundle, 3 font files) returned HTTP 200; the route has no `<img>` elements at all, so the "no broken images" bar is met trivially (zero visible images is explicitly valid under the acceptance checklist). `dist/index.html` confirmed present on disk. Mobile was not evaluated (not a release gate, D-088); only desktop/laptop were checked, matching the executed-check list (`direct:home`, `direct:home:laptop`). | Full live slot 5/5 consumed -- **campaign closed at 4 fixes + 1 ready result** (the "5 slots consumed" stop condition, not the "2 cross-pack ready" one). Live services were killed twice more by host OS memory pressure during this slot (worker resumed the run from a clean durable state each time, no code impact); the preview gateway alone was restarted once more after promotion, purely to load the browser verification. |

Campaign B is now closed (5/5 slots consumed). No sixth slot or automatic
follow-on campaign is permitted. One `ready` result was achieved (slot 5);
the "two cross-pack ready" bonus condition was not reached since only Pack
A was ever exercised (every slot 1-4 failure required a same-pack retry
before any pack could advance). A future campaign, if authorized, should
start with Pack B given Pack A is now confirmed capable of a clean `ready`
result on this revision.

Pack order is A → B → C → A after successful cross-pack results. A failed
pack is retried before advancing, but only after its root cause is fixed and
re-verified offline; slots 2, 3, and 4 all retried A and all failed, and
slot 5 -- the last slot in this campaign's budget -- also retried A,
reaching `ready`. Pack A is first because its
furthest historical run is the direct target of the offline-confirmed
conditional-marker fix. Pack A is
`5f144f04-2789-48c6-9b1c-6bd11c87abdb`, Pack B is
`ba4b986e-7841-4cfb-94a0-d56fbe1b7956`, and Pack C is
`c0860464-a786-43d8-9c30-d12d7516c4b8`.

Every ready row must explicitly cover clean build/source checks, desktop and
laptop browser errors and failed requests, broken-image absence and admitted
paths, navigation/interactions, resolved blocking review findings, promoted
preview reachability, iframe reconnect after refresh/route change, and a real
`dist/index.html`. Mobile is not a release gate under D-088. No sixth run or
automatic follow-on campaign is permitted.
## Post-67d5a75 variable-input campaign — absolute four-run cap (2026-09-11)

This is a new, separately authorized campaign. Historical tables above remain
closed and unchanged. The budget applies only to a new full Code Generator
plan/acquire/generate pipeline; upstream first-four work and offline compiler,
test, build, or browser checks do not consume a slot. Verification-only
redelivery of an already accepted source checkpoint also does not consume a
slot.

- Absolute maximum full Code Generator pipelines: **4**.
- Used: **2/4**. Slot 1 created full pipeline run
  `580b382b-8df2-4eb0-a0ea-966320782d9c`; Slot 2 created full pipeline run
  `09e10d36-c692-4d3f-a01b-6449420418be`; slots 3-4 remain unreserved.
- Priya Vasudevan input is prohibited for every live slot.
- Reserve one slot at a time. Diagnose and fix a failure before reserving the
  next slot. Never create a fifth slot or pipeline.
- Adaptive stop: stop after the first browser-verified success when its
  content and resource/component topology materially differs from Priya; seek
  one complementary success only if needed and only within the same four-slot
  ceiling.
- Acceptance requires durable `ready`, promoted `active_preview`, and a real
  authenticated `/app` browser check with zero generation, runtime, console,
  or failed-network errors. A clean build/export alone is insufficient.

### Post-change compatibility input and offline baseline

- Source session: non-Priya Maya compatibility session
  `033eb7de-9c13-41d6-8bec-cd806a3776b3`.
- Current upstream provenance: Content Architect prompt
  `content_architect.plan_content.v5`; VDD prompt
  `visual_design_director.establish_visual_language.v6` with system v4; Build
  Preparation prompt `build_preparation.compose_visual_brief.v3`; routing
  policy `precode_fallback_v2`.
- Build Preparation run `4b5e206a-1974-4851-a274-01c74901b03a` reached
  `ready` on the same durable job after one same-job cache-backed redelivery.
  The redelivery made zero provider calls and did not create a Code Generator
  pipeline.
- Privacy-safe regression fixture:
  `tests/fixtures/code_generator_build_preparation_post_67d5a75_v1/`.
  It preserves the current producer topology—1 route, 7 ordered unnamespaced
  sections, 9 resource roles, and 3 component roles—while replacing identity,
  organization, link, metric, provider-candidate, and runtime metadata.
- Immutable fixture hashes: content
  `40f9bc8b1e50ef7249a9569107004318e1037299b37fb2e78242bd7dd41f8a0a`;
  visual
  `be310a99769978e26372e94f1d6f59b7f4c28da61a4e253ed07662ec31c4cca1`.
- Compiler-defined structural signature:
  `bp-structure-v1:9e6cdb32b0ba7eaea1954eef35e8ae45fceb9a454116b6fc303af146c039d7a3`.
- Pre-fix pure-compiler probe: rejected before any Code Generator model call
  with `BRIEF_SECTION_SCOPE_INVALID`, because the current producer emits
  route-owned section IDs such as `hero` while the consumer hard-required
  `home:hero`. This is retained as the fail-closed compatibility regression;
  it must pass through explicit v1 dispatch before slot 1 can be reserved.

### Full Code Generator slots

| Slot | Reserved at | Input / structural signature | Run ID | Terminal outcome | Browser acceptance | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `2026-09-11 13:07 +05:30` | Maya BP `4b5e206a`; `bp-structure-v1:b20e9207...`; content `e6d4588c...`; visual `f095a836...`; revision `39b401d+scoped-working-tree`; key `206d62b8...` | `580b382b-8df2-4eb0-a0ea-966320782d9c` | `needs_attention` — `GENERATION_CONTEXT_LIMIT` (`179274 > 170000`) | not reached | failed; root-cause fix required |
| 2 | `2026-09-11 14:23 +05:30` | Maya BP `4b5e206a`; `bp-structure-v1:b20e9207...`; content `e6d4588c...`; visual `f095a836...`; revision `39b401d+context-scope-fix-working-tree`; key `2dc1d1aa...` | `09e10d36-c692-4d3f-a01b-6449420418be` | `needs_attention` — `SOURCE_CONTRACT_FAILED` after three verification rounds | not reached | failed; image-binding contract diagnosis required |
| 3 | — | — | — | — | — | unreserved |
| 4 | — | — | — | — | — | unreserved |

### Slot 1 result — Maya

- Durable run `580b382b-8df2-4eb0-a0ea-966320782d9c` and initial job
  `839f80df-609c-4661-9669-b1251d2ed85b` consumed full-pipeline slot 1/4.
- Terminal outcome: `needs_attention`, code `GENERATION_CONTEXT_LIMIT`, during
  `generating_routes` at work unit `route-home-4ea14058-batch-1`.
- The bounded generation context measured 179,274 characters against the
  configured 170,000-character ceiling. The largest fields were `plan=49666`,
  `visual_direction=46586`, `shared_source=32836`,
  `generation_contract=20771`, and `site_contract=14370`.
- Admission, creative direction, planning, resource acquisition, and the
  deterministic foundation completed. The foundation checkpoint is
  `d8adc9b47e3b43a4d96f063d07bfef616006e4758e71a08ef17107132dcafab5`
  (60 files; 1,759,538 bytes). No route-generation model call occurred before
  rejection.
- Site-plan hash: `e169b912adee10c157f1c8dd4e6ae44dce48819e53f786ba24933295fffdb63d`;
  resource-ledger hash:
  `4671f94c381ff9c2134a882316227ab9623bdf50918b5b98d41e00ab356ea131`;
  dependency-ledger hash:
  `176a295f7d63602386fc3d8723406f50c90fd6fcd831f844bc88baf62e5aa902`.
- Build/runtime verification, preview promotion, and browser acceptance were
  not reached. Slot 2 was reserved only after deterministic context scoping
  passed exact-artifact replay, broad offline tests, focused semantic review,
  and fresh provider/toolchain/worker readiness checks.
### Slot 2 result — Maya

- Durable run `09e10d36-c692-4d3f-a01b-6449420418be`, initial job
  `3e1c627e-6da7-457b-988d-a876b295e1f9`, generation job
  `5c469125-3765-46f5-a0ed-19bd789726b5`, and verification job
  `7c34ef52-89d6-4ef3-a769-35191a187cf1` consumed slot 2/4.
- The Run 1 context-ceiling fix succeeded live: foundation, all three route
  batches, composition, and integration completed. Integration quality was
  accepted with only advisory findings.
- Terminal outcome: `needs_attention`, code `SOURCE_CONTRACT_FAILED`, after
  three bounded verification rounds. The remaining blocking diagnostics were
  `SOURCE_ROUTE_IMAGE_MINIMUM_MISSING` and
  `SOURCE_PRIMARY_ROUTE_IMAGE_MISSING`; no runtime/browser journey ran and no
  preview was promoted.
- Final accepted source checkpoint:
  `64f9ff0427c74601948d9061519193d165f3bf895566f2bd1b91e9a9156f653d`;
  source manifest:
  `31c45802959315124e552c3bd6d4df810255072fe779283342968f3e9425c727`;
  74 files and 1,836,584 bytes. Quality receipt:
  `84b125d6884e9babbd6aa06753796e3c979a687b0a744a73d442d6d5cb0a2e5f`.
- The failure is internally contradictory: generated route source contains
  admitted `LocalImage` usages and acquisition downloaded image resources,
  while the host-owned source-contract projection counted no materialized
  primary-route image. Diagnose the resource-ID/local-path projection and
  verifier matching offline before Slot 3 is reserved.

### Campaign closure — preview-first Run 2 ready (2026-09-11)

This closure supersedes the interim Slot 2 outcome and strict acceptance wording
above. The owner explicitly prioritized the first buildable, serveable preview
and directed that generated content, quality, image, geometry, console, and
runtime findings must not fail such a preview. No additional full pipeline was
created after Slot 2.

#### Preview-first policy

- `preview_first_acceptance` remains configuration-owned and defaults to
  `false`; `config/app.native.toml` enables it for this native campaign. Strict
  hosted profiles retain their existing release policy.
- Under the native override, integration review, generated source-contract
  findings, and runtime-verifier findings are retained as advisories. The
  workflow still blocks when immutable input, authorization/fencing,
  checkpoint/source integrity, dependency installation, the clean production
  build, candidate-server startup, storage readback, or atomic promotion fails.
- The verifier reconstructs effective resource projections from the immutable
  acquisition ledger before source checks. This resolved the contradiction
  between admitted local resources and an empty verifier-side resource view.
- The focused lint, compile, type, unit, and verification-worker checks passed.
  The one isolated integration failure before cache recovery was the expected
  offline npm install failure, which correctly remained blocking because no
  build artifact existed.
- D-094 records the policy decision and rejected unconditional global
  fail-open behavior.

#### Verification-only recovery chronology

Every row below reused run `09e10d36-c692-4d3f-a01b-6449420418be` and its
accepted source. These are verification-only deliveries, not new
plan/acquire/generate pipelines, so the full-run count remained **2/4**.

| Idempotency key | Verification job | Result | Exact recovery before the next delivery |
| --- | --- | --- | --- |
| `4322626e-f629-4d89-b92d-eb8cc424e232` | `013827cb-00b6-4d03-a4ae-993b7ef5d0c7` | `INPUT_COPY_MISSING` | Replayed the original create-run key `2dc1d1aa-68d3-4d05-a7ae-faaaaa6e8213`, which returned the same run and restored input SHA-256 `b2bb4bc6b84d4b35beb1ed13075a45af7d1711f7fe5ccc1ef8698645b01dfa82` without reserving a slot. |
| `d2d80a69-cf1e-4490-a785-e869913a6a3d` | `c0f2bcf3-175c-45aa-8d01-e2ead02681f1` | `CHECKPOINT_MISSING` | Reaccepted the exact 74-file export through `CheckpointStore.accept`; checkpoint `64f9ff0427c74601948d9061519193d165f3bf895566f2bd1b91e9a9156f653d` and source manifest `31c45802959315124e552c3bd6d4df810255072fe779283342968f3e9425c727` matched the durable receipt. |
| `7db32c1e-4736-4c1d-903d-ad1e52dd1f18` | `63efdec5-ba7f-40a9-bf30-3661019e252f` | `ACQUIRED_RESOURCE_MISSING` | Restored only the 26 receipt-bound files: four local font files and 22 image renditions. Every source and dist copy matched its receipt SHA-256 and byte size; the second restore pass found all 26 already present. No licence records were fabricated. |
| `d7d91308-3f24-4048-944c-1bc800039aec` | `c34f9ffa-3efc-4677-8b1b-77780219259f` | `INSTALL_FAILED` on the absent pinned `yallist` tarball | Restored that exact public package to the configured offline npm cache. |
| `bc4224e1-6326-4e86-a5af-b07615d3e5e6` | `e7058d67-68cd-4021-91df-26e9c4616188` | `INSTALL_FAILED` on the next absent pinned package | Warmed the configured cache once from Run 2's exact `package-lock.json` in an isolated directory with install scripts disabled; the source package manifests remained byte-identical and the temporary directory was removed. |
| `087d0a6f-0999-47a8-ab0d-7b7dfb8b1f26` | `780117e3-7112-478c-af2f-e227b28669e9` | **`ready`** at revision 85 | Clean install, typecheck, production build, artifact closure, candidate serving, browser verification, storage readback, and promotion completed. |

Recovery integrity anchors:

- Restored immutable input:
  `.workspace/code-generator-development/inputs/b2/b2bb4bc6b84d4b35beb1ed13075a45af7d1711f7fe5ccc1ef8698645b01dfa82.json`.
- Restored admitted envelope:
  `.workspace/code-generator-development/admitted/7cffd7a9d6ca2860514ad634894fd368cf3dd27fcce2a54496d8350fe4db46fb/brief-envelope.json`.
- Restored checkpoint root:
  `.workspace/code-generator-checkpoints/09e10d36-c692-4d3f-a01b-6449420418be/64f9ff0427c74601948d9061519193d165f3bf895566f2bd1b91e9a9156f653d`.
- Resource projection source:
  `output/code-gen-output/14-36-11-09-2026-09e10d36/source/src/generated/resource-manifest.ts`, file SHA-256
  `14c0895db27ca29702d1a70ec46194a731341431c8227c7cf2c2ee2184e1c34c`,
  embedded ledger hash
  `149ab762562a1ea2fc401040ef3c470c84d3fe4fb6529027a1cdba4d81a82d21`.
- Restored material root:
  `.workspace/code-generator-materials/09e10d36-c692-4d3f-a01b-6449420418be/`.

#### Ready, promotion, and browser evidence

- All three verification gates report `passed`: `source_contract`,
  `type_build_artifact`, and `dom_runtime`. The resulting build manifest has
  31 entries, entry point `index.html`, total bytes 1,704,235, and build hash
  `686f734e7f40b796d5778401925331f0bf1de6672046f18f2e7a55200ac36fe5`.
- Candidate `candidate-fb13414d2c6cf195780ef8bf` was stored with candidate
  identity
  `fb13414d2c6cf195780ef8bf9de5d9f4a03ae72d8c008551bbafaff3a8139dfa`
  and artifact SHA-256
  `c1ab0ff035860a8a65e5910d1d14c694a32146f35ce819fdaac6a483e5d864f9`.
- Promoted preview:
  `http://127.0.0.1:4174/preview/preview-ra6izeqxllwudvgpixbh3ifwpgecfycde2schxxursnzaq5p/`.
  Promotion receipt hash:
  `c09c45018e4754cb86a0eb8d5f480ab5b2b01f9efe7abcebeb3084a04dccb310`;
  pointer ETag:
  `2c02210cdcc200b8e28b25c9964d1827a407de51066ddab5a9017c8228a707d9`.
- A separate real Chromium load of the promoted URL returned HTTP 200 and
  `document.readyState=complete`, rendered one main landmark, 26 headings, 17
  links, and 8,533 body-text characters, reached network idle, and produced no
  console errors, page errors, failed requests, or HTTP error responses.
- Preserved advisory codes are `QUALITY_REALIZATION_STALE`,
  `SOURCE_ROUTE_IMAGE_MINIMUM_MISSING`, `SOURCE_PRIMARY_ROUTE_IMAGE_MISSING`,
  `RUNTIME_ASSERTION_FAILED`, and `RUNTIME_ANCHOR_TARGET_MISSING`. Per the
  owner-approved preview-first rule, these do not invalidate the running
  preview.
- Final verified export:
  `output/code-gen-output/16-23-11-09-2026-09e10d36/` with both `source/` and
  runnable `dist/`.

#### Artifact locations and final accounting

- Run 1 recorded export:
  `output/code-gen-output/13-12-11-09-2026-580b382b/`. The folder is currently
  absent and Run 1 never produced a runnable `dist/`.
- Run 2 original generated source:
  `output/code-gen-output/14-36-11-09-2026-09e10d36/source/`.
- Run 2 original runnable build:
  `output/code-gen-output/14-36-11-09-2026-09e10d36/dist/`.
- Campaign outcome: **one promoted, browser-verified ready preview; 2/4 full
  runs consumed**. Slots 3 and 4 were never reserved. The adaptive stop rule
  is satisfied and this campaign is closed.

## Complete Kiro session handoff — Run 1/Run 2 preview campaign

### Handoff metadata

- **Author:** Kiro (configured runtime)
- **Finalized:** 2026-09-11 16:48:56 +05:30
- **Workspace:** `C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI`
- **Branch snapshot:** `codex/code-generator-control-room`, 131 commits ahead of
  its tracked remote at handoff time.
- **Commit status:** no commit was created. This is a shared, heavily dirty
  worktree; only task-owned documentation was added during this final handoff
  pass, and no files were staged, reset, cleaned, or reverted.
- **Canonical decision:** D-094 in `DECISIONS.md`.
- **Canonical issue summary:** `code generator issues.md`.
- **Campaign cap:** four full Code Generator plan/acquire/generate pipelines.
  Exactly two were consumed. Verification-only deliveries never reserved a
  new run. Slots 3 and 4 remain unused and this campaign is closed.

### User goal and non-negotiable acceptance rule

The owner authorized at most four full runs and required the campaign to stop
as soon as one generated portfolio produced a running preview. Generated
content, visual-quality, image, geometry, console, and runtime findings were
not allowed to fail a buildable and serveable preview. Integrity and viability
were still required: immutable input admission, authorization/fencing,
checkpoint consistency, a materialized production build, candidate-server
startup, storage readback, and atomic promotion could not be bypassed.

The implementation therefore did **not** delete verification or force a false
`ready`. It separated generated-output observations from the smaller set of
conditions required to truthfully claim that a preview exists and runs.

### Final outcome

| Full slot | Run | Result | Evidence | Accounting |
| --- | --- | --- | --- | --- |
| 1 | `580b382b-8df2-4eb0-a0ea-966320782d9c` | `needs_attention`, `GENERATION_CONTEXT_LIMIT` | Rejected before the first route model call because the deterministic context was 179,274 characters against a 170,000-character ceiling. No runnable `dist` was produced. | Slot 1/4 consumed. |
| 2 | `09e10d36-c692-4d3f-a01b-6449420418be` | **`ready`**, revision 85 | Complete source, clean production build, all three verification gates recorded, candidate stored, preview promoted, and promoted URL loaded in real Chromium. | Slot 2/4 consumed; campaign stopped. |
| 3 | — | not reserved | Stop condition already satisfied. | Unused. |
| 4 | — | not reserved | Stop condition already satisfied. | Unused. |

At handoff time the API still returned Run 2 as `ready`, its verification
projection as `ready`, and its promoted preview returned HTTP 200.

### Chronology, findings, and fixes

#### 1. Run 1 exposed prompt-context duplication, not a provider failure

Run 1 completed admission, creative direction, planning, acquisition, and the
trusted foundation. The first route batch then failed in
`_enforce_context_ceiling()` before any route-generation provider call. The
largest duplicated model-facing fields were:

- `plan`: 49,666 characters
- `visual_direction`: 46,586 characters
- `shared_source`: 32,836 characters
- `generation_contract`: 20,771 characters
- `site_contract`: 14,370 characters

The chosen fix kept the 170,000-character fail-closed ceiling unchanged. It
reduced only prompt input; complete immutable plans and projections still drive
host validators.

`generation_orchestrator.py::_operation_context()` now derives one trusted
`_unit_context_scope()` from work-unit ownership and builds deterministic,
operation-specific prompt projections:

- `_scoped_site_contract()` keeps only the assigned route, sections, facts,
  criteria, and approved public content.
- `_scoped_operation_plan()` filters routes, sections, content/fact/criterion
  IDs, interactions, resource bindings, V4 blueprint records, and the work
  graph to the current unit and direct dependencies.
- `_scoped_visual_direction()` retains global visual authority but removes
  out-of-scope route/section/resource records and repeated raw approved-brief
  Markdown.
- `_scoped_resource_ledger()` and `_scoped_execution_contract()` retain only
  usable metadata and current-unit resource slots.
- `_shared_source_for_unit()` changed from a broad repository walk to an
  operation-specific allowlist of trusted APIs, generated tokens/shared
  systems, direct dependency modules, and current resource interfaces.
- `_compact_generated_content_interface()` retains API signatures and only the
  current batch's `ApprovedContentId` union instead of repeating all approved
  prose.
- Route create/replace inventory is restricted to paths the unit can actually
  own.

Exact persisted replay after this change measured the three initial route
contexts at 114,653, 128,795, and 74,246 characters; corresponding bounded
repair contexts measured 131,556, 141,142, and 70,292 characters. All remained
below the unchanged ceiling. Run 2 then proved the change live by completing
all three route batches, composition, and integration.

Rejected approaches: raise/remove the ceiling, truncate arbitrary serialized
JSON, discard host validation data, or spend another full run before exact
replay. Those alternatives would hide growth, remove determinism, or waste the
four-run budget.

#### 2. Run 2 exposed a verifier-side effective-resource projection gap

Run 2 generated a complete accepted source checkpoint, but strict verification
reported `SOURCE_ROUTE_IMAGE_MINIMUM_MISSING` and
`SOURCE_PRIMARY_ROUTE_IMAGE_MISSING`. This contradicted the durable evidence:
acquisition had admitted local files and generated source contained resource
references.

Root cause: verification re-admitted the immutable Build Preparation envelope,
which reconstructs pre-acquisition projections. It restored source bytes but
did not rebuild the mutable durable overlays (`resources/ledger.json`,
`dependencies/ledger.json`, and `generated/resource-assets.json`) before final
source and runtime contracts were compiled. The existing validators therefore
saw an incomplete effective resource view.

The chosen fix reconstructs the same effective projections used during
source generation:

- `code_generator_verification.py::_materialize_effective_projections()`
  overlays durable resource/dependency ledgers, calls the existing trusted
  manifest materializer with the configured materials root, and stores the
  browser-facing image assets in `generated/resource-assets.json` before
  source identity, validation, repair, or runtime planning.
- `design_realization.py::_acquired_local_paths_by_slot()` maps
  `request-`, `deferred-`, and `delegated-` acquisition namespaces back to
  immutable execution slot IDs through request hashes and active bindings.
- `_generated_local_paths_by_slot()` adds browser-facing generated paths.
- `_admitted_resource_slot_ids()` and `_local_paths_by_slot()` union immutable
  execution paths, receipt-bound acquisition paths, and generated paths.
- `compile_design_realization()` and `verification_plan.py` now receive the
  reconstructed generated-resource projection.

This is projection reconstruction, not validator weakening. Existing source
manifest comparison still rejects `SOURCE_CHECKPOINT_DRIFT`; missing
receipt-bound bytes still reject `ACQUIRED_RESOURCE_MISSING`; source validators
still inspect actual executable references.

Rejected approaches: edit the database, mutate generated source to satisfy the
checker, disable image validators globally, fabricate licence files, or ignore
checkpoint hashes.

#### 3. Strict release policy conflicted with the owner's preview-first goal

The original strict pipeline could spend repair calls and finish
`needs_attention` even when the source already had a valid buildable export.
D-094 introduced a configuration-owned policy instead of an unconditional
fail-open change:

- `CodeGeneratorVerificationConfig.preview_first_acceptance` defaults to
  `false` in `settings.py`.
- Only `config/app.native.toml` enables it for this native campaign.
- `generation_orchestrator.py::_review_and_polish()` keeps the integration
  review receipt but does not spend owner-polish calls or block on generated
  review output in preview-first mode.
- Missing/stale quality receipts, final-source diagnostics, and runtime
  findings are retained in the durable projection as advisories.
- Build diagnostics are advisory only when a complete build manifest exists
  and every materialized `dist` file matches it. No artifact remains blocking.
- Runtime-verifier failures after candidate-server startup become advisory;
  authorization-fence failures are explicitly re-raised in verification.
- `_attempt_repair()` skips strict post-repair quality re-review in
  preview-first mode. The required repair-helper image-policy threading and
  the contradictory post-repair hard final-source guard were removed.
- Candidate-server startup, artifact storage/readback, pending-promotion
  reconciliation, and atomic promotion still follow the normal blocking path.

Rejected approaches: remove verification entirely, enable fail-open globally,
mark a run ready without a real `dist`, or treat a failed candidate server as a
preview.

**Review caveat:** `_review_and_polish()` currently catches `Exception`
broadly before its preview-first return and does not locally carve out
`AuthorizationFenceError` as the runtime-verification branch does. Outer worker
fences remain in place and this was not observed in the live run, but a future
hardening pass should make this local boundary explicitly match D-094's
invariant that authorization/fencing failures remain blocking.

#### 4. Verification redelivery exposed missing ignored durable artifacts

No third full run was created. Every recovery reused Run 2 and verified exact
hashes before writing anything:

1. Verification job `013827cb-00b6-4d03-a4ae-993b7ef5d0c7` failed
   `INPUT_COPY_MISSING`. Replaying the original create-run idempotency key
   `2dc1d1aa-68d3-4d05-a7ae-faaaaa6e8213` returned the same Run 2 and restored
   the immutable 71,571-byte input copy with SHA-256
   `b2bb4bc6b84d4b35beb1ed13075a45af7d1711f7fe5ccc1ef8698645b01dfa82`.
2. Job `c0f2bcf3-175c-45aa-8d01-e2ead02681f1` failed
   `CHECKPOINT_MISSING`. The exact exported source was reaccepted through
   `CheckpointStore.accept`; the durable checkpoint, source-manifest hash,
   file count, byte count, parent, and work-unit identity all matched.
3. Job `63efdec5-ba7f-40a9-bf30-3661019e252f` failed
   `ACQUIRED_RESOURCE_MISSING`. The resource manifest itself first matched
   SHA-256
   `14c0895db27ca29702d1a70ec46194a731341431c8227c7cf2c2ee2184e1c34c`
   and embedded ledger hash
   `149ab762562a1ea2fc401040ef3c470c84d3fe4fb6529027a1cdba4d81a82d21`.
   Four font files and 22 responsive image renditions were copied only from
   exact source-export paths into their receipt-declared material paths. All
   26 source copies and all 26 optional dist copies matched receipt SHA-256
   and size. Staging used temporary siblings plus atomic moves and readback;
   a second execution reported all 26 already present. Licence JSON files were
   intentionally not fabricated because they were not receipt
   `materialized_files`.
4. Job `c34f9ffa-3efc-4677-8b1b-77780219259f` reached the clean build and failed
   `INSTALL_FAILED`: the configured offline npm cache lacked the lockfile-pinned
   `yallist@3.1.1` tarball.
5. After restoring that exact package, job
   `e7058d67-68cd-4021-91df-26e9c4616188` exposed the next absent locked
   package (`vite@6.4.1`), proving the cache—not source or lockfile—was
   incomplete.
6. The cache was then warmed once from Run 2's exact `package-lock.json` in an
   isolated temporary directory, with install scripts disabled. The source
   package manifests remained byte-identical; the temporary install directory
   was removed.
7. Final job `780117e3-7112-478c-af2f-e227b28669e9`, idempotency key
   `087d0a6f-0999-47a8-ab0d-7b7dfb8b1f26`, completed the clean build,
   candidate server, browser verification, storage readback, and promotion.

These ignored local artifacts are required for redelivery on this machine. If
`.workspace` is cleaned, recover them only from immutable, hash-matching
exports or rerun the supported admission/acquisition paths; do not patch run
rows or relax integrity checks.

### Final Run 2 evidence

- Run ID: `09e10d36-c692-4d3f-a01b-6449420418be`
- Status/revision: `ready` / `85`
- Accepted source checkpoint:
  `64f9ff0427c74601948d9061519193d165f3bf895566f2bd1b91e9a9156f653d`
- Source manifest:
  `31c45802959315124e552c3bd6d4df810255072fe779283342968f3e9425c727`
- Source size: 74 files, 1,836,584 bytes
- Candidate identity:
  `fb13414d2c6cf195780ef8bf9de5d9f4a03ae72d8c008551bbafaff3a8139dfa`
- Build hash:
  `686f734e7f40b796d5778401925331f0bf1de6672046f18f2e7a55200ac36fe5`
- Candidate artifact SHA-256:
  `c1ab0ff035860a8a65e5910d1d14c694a32146f35ce819fdaac6a483e5d864f9`
- Promotion receipt hash:
  `c09c45018e4754cb86a0eb8d5f480ab5b2b01f9efe7abcebeb3084a04dccb310`
- Preview pointer ETag:
  `2c02210cdcc200b8e28b25c9964d1827a407de51066ddab5a9017c8228a707d9`
- Promoted URL:
  `http://127.0.0.1:4174/preview/preview-ra6izeqxllwudvgpixbh3ifwpgecfycde2schxxursnzaq5p/`
- Final verified export:
  `output/code-gen-output/16-23-11-09-2026-09e10d36/`

All three gate receipts (`source_contract`, `type_build_artifact`, and
`dom_runtime`) recorded `passed` under the configured policy. Preserved
advisories are:

- `QUALITY_REALIZATION_STALE`
- `SOURCE_ROUTE_IMAGE_MINIMUM_MISSING`
- `SOURCE_PRIMARY_ROUTE_IMAGE_MISSING`
- `RUNTIME_ASSERTION_FAILED` for one expected public sentence
- `RUNTIME_ANCHOR_TARGET_MISSING` for `#flagship_projects`

These are visible for later polish and were deliberately not hidden. They are
not build/serve failures.

A separate real Chromium load of the promoted URL returned HTTP 200,
`document.readyState=complete`, one `<main>`, 26 headings, 17 links, one mounted
root child, and 8,533 rendered text characters. It reached network idle with no
console errors, page errors, failed requests, or HTTP error responses.

### Artifact and recovery paths

Run 1 recorded path (currently absent; never contained runnable `dist`):

```text
C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\13-12-11-09-2026-580b382b
```

Run 2 original source:

```text
C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\14-36-11-09-2026-09e10d36\source
```

Run 2 original runnable build:

```text
C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\14-36-11-09-2026-09e10d36\dist
```

Run 2 final verified export:

```text
C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\16-23-11-09-2026-09e10d36
```

Restored input and envelope:

```text
.workspace/code-generator-development/inputs/b2/b2bb4bc6b84d4b35beb1ed13075a45af7d1711f7fe5ccc1ef8698645b01dfa82.json
.workspace/code-generator-development/admitted/7cffd7a9d6ca2860514ad634894fd368cf3dd27fcce2a54496d8350fe4db46fb/brief-envelope.json
```

Restored checkpoint and materials:

```text
.workspace/code-generator-checkpoints/09e10d36-c692-4d3f-a01b-6449420418be/64f9ff0427c74601948d9061519193d165f3bf895566f2bd1b91e9a9156f653d
.workspace/code-generator-materials/09e10d36-c692-4d3f-a01b-6449420418be
```

### Operator commands

The promoted preview is available while the native preview gateway remains
running:

```text
http://127.0.0.1:4174/preview/preview-ra6izeqxllwudvgpixbh3ifwpgecfycde2schxxursnzaq5p/
```

To serve the already-built Run 2 output directly on port 4175:

```powershell
& "C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\.workspace\venv\Scripts\python.exe" -m http.server 4175 --bind 127.0.0.1 --directory "C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\14-36-11-09-2026-09e10d36\dist"
```

Then open `http://127.0.0.1:4175/`; stop the server with `Ctrl+C`.

To reinstall from the exact lockfile, rebuild, and run the generated source:

```powershell
Set-Location "C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\output\code-gen-output\14-36-11-09-2026-09e10d36\source"
$env:npm_config_cache = "C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI\.workspace\npm-cache"
npm.cmd ci --ignore-scripts --offline --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw "production build failed" }
npm.cmd run preview -- --host 127.0.0.1 --port 4175
```

### Validation performed

The following checks were completed before declaring the campaign closed:

- Ruff lint on the campaign-owned Python files.
- Python compile checks on the changed modules.
- Targeted mypy checks for verification, design realization, and verification
  planning.
- Focused tests for context scoping, effective resource projection, advisory
  policy, repair behavior, and verification flow.
- The full Code Generator unit suite.
- `uv run pytest tests/integration/test_code_generator_verification_worker.py -q`.
  Before cache recovery, its clean-candidate case alone failed at offline npm
  installation because no build artifact could be created; this was correctly
  blocking. The exact-lock cache warm subsequently allowed the real Run 2
  clean build and promotion to complete.
- Focused semantic review of the deterministic context projection approved the
  Run 1 fix.
- Real Chromium smoke of the promoted URL.
- Task-scoped `git diff --check` on implementation and documentation files.

No test count is frozen here; rerun the commands for current coverage.

### Worktree attribution and unrelated active work

The campaign does not have a clean commit boundary. Its implementation hunks
coexist with other contributors' edits in the same files. Attribute only these
campaign changes:

- deterministic prompt-context scoping helpers and their call from
  `_operation_context()`;
- `_review_and_polish()`'s config-scoped preview-first return;
- effective acquisition/generated-resource projection reconstruction in final
  verification;
- generated/acquired path mapping in design realization and verification plan;
- preview-first quality/source/build/runtime behavior and its repair guard;
- the default-off setting, native opt-in, D-094, campaign ledger, issue summary,
  and change-log entry.

Do **not** attribute the new semantic-decline module, generation attempt epochs,
content-addressed pending proposals, request-transition receipts, explicit
retry reset behavior, or broader at-least-once redelivery changes to this
campaign. They are separate in-flight work. The review at
`semantic-review/2026-09-11-102120-pr-2.md` concerns that separate work and has
a `NEEDS_CHANGES` verdict with confirmed retry/crash-safety findings; this
campaign did not resolve or approve those findings.

The remaining worktree also contains unrelated tracked modifications,
deletions, and untracked files. Future agents must inspect `git status` and
stage exact files or hunks only. Never use `git add .`, `git add -A`, reset,
clean, or broad restore in this worktree.

### Current operational state and resume rule

At the handoff snapshot, one API, one worker, and one preview gateway were
running with `config/app.native.toml`; API readiness and the preview endpoint
were healthy. The running preview is local only—no public deployment is
claimed.

The requested campaign is complete. Do not reserve Slot 3 or Slot 4 merely to
polish the current advisories. If the local services stop, use the direct
`dist` command above or restart the normal native services. If a future owner
explicitly authorizes a new campaign, start from fresh readiness and accounting
rather than silently extending this closed 2/4 campaign.