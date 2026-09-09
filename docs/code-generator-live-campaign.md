# Code Generator live campaign

This is the durable handoff record for the reliability campaign authorized on
2026-09-09. It is intentionally small and append-oriented so a later Claude
Code session can resume without guessing which Build Preparation output or
which live-call budget remains.

## Reliability-plan implementation campaign — five-run cap (2026-09-09)

This is a new campaign after reliability commit `a503a4a`. It is separate from
the historical campaigns below and begins before any new full pipeline call.

- Maximum full pipeline calls: **5**.
- Used: **1/5**.
- Accepted cross-pack portfolios: **0/2**.
- Slot 1 run revision: `a503a4a` (`fix(code-generator): enforce reliable generation lifecycle`).
- Current runtime revision: `4da1ddb` (readback compatibility and best-effort preflight cleanup fixes).
- State: slot 1 completed with `needs_attention`; slot 2 is queued and running through the durable pipeline.
- Execution rule: one full pipeline at a time; stop at two accepted results or
  after slot 5, whichever comes first. A verification-only retry that reuses
  an accepted source is recorded separately and does not consume a full source
  generation slot.

### Planned slot order

| Slot | Pack | Reason | Status |
| --- | --- | --- | --- |
| 1 | `c0860464-a786-43d8-9c30-d12d7516c4b8` | C reproduces the latest repair path and exercises its route-scoped abstract image slot. | needs_attention |
| 2 | `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | B provides a structurally different seven-section brief after slot 1 is diagnosed. | queued |
| 3 | `5f144f04-2789-48c6-9b1c-6bd11c87abdb` | A provides the remaining current seven-section variation. | unreserved |
| 4 | choose after the preceding result | Only if fewer than two accepted results remain and the run adds evidence. | unreserved |
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

### Reserved slots

| Slot | Reserved at | Pack | Code revision | Content hash | Visual hash | Contract hash | Idempotency key | Run ID | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-09-09 20:56:11 +05:30 | `c0860464-a786-43d8-9c30-d12d7516c4b8` | `a503a4a` | `0e88ebced8c350b04aab1bdeff4c1f430a0b3e5c7999379c3244e11df929e527` | `e3444c79571cdb92fbdc3be8356d056fd7203930946dafa18624198dc6cfa918` | `bf077c5a360964138755be1d11b5acf64b828fa777ce4a142954ab808b261128` | `542c3c11-415d-468c-947f-8d4654845fef` | `4dfd10cc-52bd-4fc7-8a6d-96addf47b26e` | needs_attention |
| 2 | 2026-09-09 22:44:09 +05:30 | `ba4b986e-7841-4cfb-94a0-d56fbe1b7956` | `4da1ddb` | `db560919f26b359ce7836c40339c887b3faa001637452c2d672d1193b9155435` | `ff324462dc980bf29deb05bc4533716e55940babb40497170d668d8492f21f74` | `bf27265ec7e4c27b9151e881b02b516916608f472508bd9eb835055bf1076215` | `6fc66f93-259a-4ade-8341-e694e72a742f` | `2f22c091-32e7-47dc-bc99-aef25d4e8058` | queued |

### Slot 1 result — Pack C

- Run: `4dfd10cc-52bd-4fc7-8a6d-96addf47b26e`; durable job: `c7b49a1a-8900-4349-a6de-86a21198978d`.
- Durable outcome: `needs_attention`, terminal code `INTEGRATION_REVIEW_UNRESOLVED`.
- Admission, planning, acquisition, and source generation completed. The run accepted a 62-file source checkpoint with hash `ae525b31bce45ec6d0a5ef6055121c4a6517ab8aa3f4186f303e13b8be992127`, source manifest hash `937d9a7a1c4b2e36ab28b96b0d7afa898917ba9b5ba68d76586bd4e6279576db`, and 2,154,124 bytes.
- The generation projection records 13 model calls/attempts and one repair round. The bounded whole-site review exhausted three integration polish rounds; verification and preview promotion did not run.
- The original receipt classified two subjective findings as blocking. `14bb97c` replaced keyword severity inference with explicit host-owned mappings, and `c8a66e7` plus `80a925c` keep terminal, run, quality, and product read projections truthful for historical data. The current read projection is accepted with all three findings advisory; this does not make the source a successful portfolio.

### Slot 2 execution — Pack B

- Durable run: `2f22c091-32e7-47dc-bc99-aef25d4e8058`; job: `9b75bb1c-5a7c-4369-b4cb-1e64ce565b0f`.
- The single POST was accepted with idempotency key `6fc66f93-259a-4ade-8341-e694e72a742f`; initial persisted status was `queued`.

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
