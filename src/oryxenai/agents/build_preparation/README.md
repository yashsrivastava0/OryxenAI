# Build Preparation Agent

Build Preparation is the fourth explicit pipeline stage. Stage 0 deterministically
compiles approved Content Architect and Visual Design Director projections into
public route scope and resource needs. Phase 2 then runs a bounded workflow:

1. compose one provider query per deterministic need, including an optional,
   policy-approved non-evidentiary editorial-image opportunity when configured;
2. search Pexels first for photos, with Unsplash fallback, and resolve registry
   components and Lucide icons;
3. select only from the returned closed candidate set, or record an explicit
   custom-implementation fallback;
4. write route-scoped Build Context, optionally integrating cross-route
   constraints when the configured route threshold is reached; and
5. materialize a local `build-context` tree with provenance, licenses, safe
   component source, image inspection metadata, a complete resource decision
   plan, and a resources manifest.

Before packaging, the agent writes `handoff-report.json`. Code Generator may
consume a pack only when `handoff_eligible` is true, which requires both
approved upstream hashes. Detached or unapproved fixture packages remain
downloadable for review but are never production-eligible. A selected Pexels
image is locally materialized and pixel-inspected; provider failure uses the
approved custom visual fallback and does not block the handoff. Unsplash stays
a metadata-only reference and cannot be used by the static target.

`resources/plan.json` records every selected and unselected need, its routes
and scenes, fallback, adaptation guidance, and whether Code Generator may fetch
one equivalent during Code Generation. Such a fetch must replace—not duplicate—
the recorded fallback and is never permitted at portfolio runtime. The target
ships a dependency ceiling and starter `package.json`, not a synthetic lockfile;
Code Generator generates the real lockfile after choosing its final dependency
subset.

Phase 3 packages the staged tree into one deterministic ZIP, verifies it
through the configured artifact store, and restores the verified bytes to a
local debug mirror when enabled. It does not invoke Code Generator.

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

The harness is deterministic and offline by default. Its two explicit options
enable the configured model and resource providers for a live smoke run.
When the local debug mirror is enabled, each run is stored under a sortable
timestamp plus an eight-character run prefix; the package manifest retains the
full run ID.
