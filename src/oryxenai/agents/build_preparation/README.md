# Build Preparation Agent

Build Preparation is the fourth explicit pipeline stage. Stage 0 deterministically
compiles approved Content Architect and Visual Design Director projections into
public route scope and resource needs. Phase 2 then runs a bounded workflow:

1. compose one provider query per deterministic need, including the configured
   image and component roles from the approved Visual Design Director output;
2. search Pexels for photos, resolve Fontsource fonts, and resolve registry
   components and Lucide icons through bounded, cached provider clients;
3. select only from the returned closed candidate set, then resolve every
   known need as local material, a verified target-package binding, a typed
   local recipe, or an explicit upstream execution gap;
4. write route-scoped Build Context, optionally integrating cross-route
   constraints when the configured route threshold is reached; and
5. materialize a local `build-context` tree with provenance, licenses, safe
   component source, image inspection metadata, a complete resource decision
   plan, and a resources manifest.

Before packaging, the agent writes `handoff-report.json`. Code Generator may
consume a pack only when `handoff_eligible` is true, which requires both
approved upstream hashes. Detached or unapproved fixture packages remain
downloadable for review but are never production-eligible. A selected Pexels
image is locally materialized and pixel-inspected, and a selected registry
component is copied as importable source. Provider failure, an offline run, a
blank/flat image, a placeholder component, or a metadata-only remote image
creates an actionable `VDD_EXECUTION_GAP`; no generated-local visual, blank
PNG, wrapper, or visual recipe can satisfy an image/component slot. Unsplash
remains a diagnostic metadata source and cannot be used by the static target.

Image-rich directions target five real images (maximum six) and four real
components (maximum six) by default. These are policy targets, not invented
assets: the approved VDD projection may explicitly lower them for a text-led
or privacy-limited portfolio. Build Preparation records the target policy,
actual local material counts, provider calls/cache hits/rate-limit events, and
every missing role in the handoff summary.

For historical diagnostic trees only, `resources/plan.json` records every selected and unselected need, its routes
and scenes, fallback, adaptation guidance, and whether Code Generator may fetch
one equivalent during Code Generation. Such a fetch must replace—not duplicate—
the recorded fallback and is never permitted at portfolio runtime. In current
pack-v3 output, known image/component roles do not receive a later-fetch escape
hatch: they remain local material or an explicit execution gap. The target
ships a dependency ceiling and starter `package.json`, not a synthetic lockfile;
Code Generator generates the real lockfile after choosing its final dependency
subset.

Pack-v3 instead writes `execution/contract.json` as the only implementation
inventory for Code Generator, plus `resources/ledger.json` and hash-covered
declarative recipe files. Every slot is route/scene scoped and resolves exactly
once to local material, an approved target dependency/export, a typed local
recipe, or `VDD_EXECUTION_GAP`. Known needs never become prose-only fallbacks
or later-fetch instructions; only genuinely emergent needs may use Code
Generator's separate receipt-bound acquisition path.

Phase 3 packages the staged tree into one deterministic pack-v3 ZIP, verifies it
through the configured artifact store, and restores the verified bytes to a
local debug mirror when enabled. A complete approved input writes hash-covered
`site/contract.json`, `design/visual-direction.json`, approval/target
projections, resource projection, execution contract, resource ledger, and v3
handoff report. Historical packs, including v2, are diagnostic-only and cannot
be admitted by Code Generator.

## Folder structure

```text
build_preparation/
  agent.py, service.py, state.py, schemas.py, validators.py
  compiler.py, fixture.py, providers.py, materializer.py, packager.py
  prompt_builder.py
  ../../storage/artifacts.py  configured memory/S3-compatible artifact store
  prompts/                    trusted system + operation prompts
  samples/                    privacy-safe checked-in inputs when present
```

## State and routes

```text
NOT_STARTED -> RUNNING -> READY
                  `-----> NEEDS_ATTENTION -> RUNNING
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/build-preparation` | State, jobs, and staleness |
| POST | `/api/v1/sessions/{id}/build-preparation/start` | Start from approved CA + VDD |
| POST | `/api/v1/sessions/{id}/build-preparation/regenerate` | Re-run from current approved upstream |

The state is stored under `portfolio_sessions.current_state["build_preparation"]`.
The worker rechecks the approved upstream source reference before applying its
result, so stale work cannot overwrite newer approved state.

## Detached harness

When the development UI and Build Preparation fixture flag are enabled:

- `/build-preparation-fixture` accepts pasted or uploaded Visual Design Director JSON and an optional approved Content Architect JSON projection; leaving the latter blank preserves the VDD-only harness behavior;
- `/build-preparation-fixture/progress` shows every stage event and the full JSON;
- `POST /api/v1/build-preparation/fixture/run` runs the same Stage 0 → Phase 3
  pipeline without a session, approval state, or database write.

The harness is deterministic and offline by default, but an offline run is
diagnostic-only when visual roles are present: it cannot claim a ready handoff.
Its two explicit options enable the configured model and resource providers for
a live smoke run. Live providers are bounded by request ceilings, short retry
windows, response caching, duplicate-query suppression, and rate-limit header
tracking; provider exhaustion stops with a visible gap instead of retrying
indefinitely.
When the local debug mirror is enabled, each run is stored under a sortable
timestamp plus an eight-character run prefix; the package manifest retains the
full run ID.
