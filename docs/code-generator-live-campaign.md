# Code Generator live campaign

This is the durable handoff record for the reliability campaign authorized on
2026-09-09. It is intentionally small and append-oriented so a later Claude
Code session can resume without guessing which Build Preparation output or
which live-call budget remains.

## Guardrails

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
- Service processes must be restarted after commit `2f424e5`; an earlier
  readiness response was from the old quality/release configuration and the
  preview gateway was down.

## Full pipeline slots

| Slot | Reserved at (Asia/Kolkata) | Pack | Run ID | Terminal status | Earliest failure / success evidence | Preview or artifact | Usage / notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-09-09 03:21 +05:30 | A | reserved | running/pending | pending | pending | Maya pack selected after ready provider preflight |
| 2 | pending | B | pending | pending | pending | pending | pending |
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
