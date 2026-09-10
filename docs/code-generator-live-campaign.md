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

## Pre-live-fix confirmation campaign — bounded five-run cap (2026-09-10)

This is a new campaign after the 2026-09-10 final five-slot campaign. The
historical `Final reliability campaign` table above is unchanged. This
campaign starts with zero live slots consumed and is authorized for at most
five full-pipeline runs, stopping at two cross-pack ready results, an
insufficient balance, or the fifth consumed run.

### Offline gate before slot 1

- The requested settings reconciliation is present: Pydantic defaults now
  match the effective 2/4/3 values in `config/app.toml`; that file was not
  edited. The dead `repair_depth` field remains by deliberate D-089
  non-decision.
- The focused settings unit suite passed (19 tests), mypy and Ruff lint for
  `settings.py` passed, and the targeted source/audit/repair/contract/export/
  image suites passed (136 tests).
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
| B / slot 3 | `.workspace/code-generator-generation/7b74c97b-f95e-4b77-986c-a6aed0f99b78/repo/` | exit 1; 296 route-contract diagnostic lines | exit 0 | Route-contract failures surface in the audit independently before the clean typecheck result. |
| B / slot 4 | `.workspace/code-generator-generation/fe4a0224-8f5f-4c3e-86a2-a1aafef8d621/repo/` | exit 1; 295 older route-source diagnostic lines | exit 0 | Zero diagnostics match the literal object/tuple content-map false-positive pattern. |

No live slot has been reserved. The earlier direct balance attempt was
inconclusive because the credit-grants endpoint returned HTTP 403 and the
browser billing overview required an interactive login. The user then supplied
a fresh provider check showing configured-key presence, successful model access
(HTTP 200), and a successful live quota/credit test (HTTP 200). That current
evidence clears the one-run balance gate; the stale balance figures from
earlier notes remain inadmissible.

### Live outcomes — append one row immediately after each run

| Slot | Balance check | Pack | Run ID | Terminal outcome | First causal evidence | Preview / acceptance evidence | Usage / notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

Pack order is A → B → C → A after successful cross-pack results, with a failed
pack retried only after its root cause is fixed and re-verified offline. Pack A
is first because its furthest historical run is the direct target of the
offline-confirmed conditional-marker fix. Pack A is
`5f144f04-2789-48c6-9b1c-6bd11c87abdb`, Pack B is
`ba4b986e-7841-4cfb-94a0-d56fbe1b7956`, and Pack C is
`c0860464-a786-43d8-9c30-d12d7516c4b8`.

Every ready row must explicitly cover clean build/source checks, desktop and
laptop browser errors and failed requests, broken-image absence and admitted
paths, navigation/interactions, resolved blocking review findings, promoted
preview reachability, iframe reconnect after refresh/route change, and a real
`dist/index.html`. Mobile is not a release gate under D-088. No sixth run or
automatic follow-on campaign is permitted.
