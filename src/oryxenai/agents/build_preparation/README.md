# Build Preparation Agent

Build Preparation is the fourth explicit pipeline stage. It compiles approved
Content Architect content and the Visual Design Director projection into two
Markdown briefs for Code Generator -- nothing else. It never decides what the
portfolio says (that is Content Architect's job, inserted verbatim), never
downloads or verifies a resource byte, and never fetches component source.
It researches real candidate resources through direct provider search and
hands Code Generator a short, factual list of what it found; the actual bytes
are fetched by Code Generator's own acquisition adapters at generation time.

The session-backed main workflow requires both upstream approvals before this
stage can start; it never silently fabricates the missing handoff. The
detached diagnostic fixture may still demonstrate the presentation-only
visual assumption layer for incomplete inputs (see `visual_input.py`), which
is exactly the fallback used when Visual Design Director hasn't produced full
direction yet. Build Preparation never invents portfolio facts, evidence,
people, employers, metrics, or private media.

## Pipeline

1. **Scope** (`compiler.py::compile_stage0`) -- pure, no I/O. Compiles the
   approved public route scope and the deterministic list of resource
   "needs" from Content Architect + Visual Design Director.
2. **Resource research** (`resource_research.py::discover_resources`) --
   deterministic query construction (no model call) plus real, discovery-only
   provider search (Pexels, Pixabay, Fontsource, and real UI-component
   registries via `providers.py`). No bytes are downloaded; every result is
   reduced to a small `ResourceCandidateLink`/`ComponentSuggestion` (provider,
   ID, URL, license -- nothing more) before it ever reaches a prompt.
3. **Compose the visual brief** (at most one model call,
   `compose_visual_brief`) -- the model receives the compiled scope, the
   approved visual direction, and every candidate already found, and may only
   pick a candidate by index or write `null`. Picking an index it was not
   given is a hard validation failure (`validate_visual_brief_output`). This
   is the entire "never invent a resource" guarantee -- enforced structurally,
   not by trusting the model.
4. **Assemble both briefs** (`brief_assembly.py`, pure Python, no model) --
   `content-and-narrative-brief.md` is built entirely from Content Architect's
   approved copy, inserted verbatim (plus the model's optional SEO
   suggestions, clearly labeled as a Build Preparation addition, never
   approved copy). `visual-and-build-brief.md` combines the model's prose with
   the deterministic resource/component tables.
5. **Persist** -- both briefs, their content hashes, and the compiled scope
   are stored directly on `portfolio_sessions.current_state["build_preparation"]`
   (the same JSONB-on-session-state pattern every other agent already uses).
   A local debug mirror (two plain `.md` files) is written for developer
   inspection when enabled -- never the source of truth.

There is no ZIP, no object storage, no pack version, and no execution-contract
slot taxonomy. A pack used to exist because Build Preparation once embedded
real image/font/component bytes; once it stopped doing that, the packaging,
verification, and expiry machinery around those bytes stopped earning its
complexity.

## What Code Generator consumes

Two Markdown documents, each with exactly one machine-readable fenced JSON
block near the top (the only structured data either file contains) followed
by prose and tables for human and model readability:

- `content-and-narrative-brief.md` -- a `build-preparation-content-index`
  block (approved route/section IDs) followed by the complete approved
  public content, verbatim.
- `visual-and-build-brief.md` -- a `build-preparation-visual-index` block
  (route list, resource roles with real candidate links, component roles
  with real suggestions, target contract, recommended dependencies) followed
  by the model's design-language and per-route guidance prose, reference
  tables, and an explicit statement that Code Generator has final authority
  to adapt, replace, or ignore any suggestion here.

Code Generator's own ingestion of this new contract (replacing the old
pack-v3/v4 ZIP admission) is tracked as explicit follow-up work -- see
`DECISIONS.md`. It is not silently assumed done.

## Folder structure

```text
build_preparation/
  agent.py              single-call orchestration (Stage 0 -> research -> model call -> assembly)
  compiler.py            pure Stage 0 scope compiler (unchanged from earlier packs)
  resource_research.py   deterministic query construction + discovery-only provider search
  providers.py           discovery-only Pexels/Pixabay/Fontsource/registry clients (no downloads)
  brief_assembly.py       deterministic Markdown assembly for both briefs
  debug_mirror.py        local .md debug mirror (courtesy copy, never source of truth)
  visual_input.py         presentation-fallback normalizer when VDD is thin/absent
  input_integrator.py     CA/VDD -> compact agent-input projection composer
  service.py, state.py, schemas.py, validators.py, prompt_builder.py
  fixture.py, fixture_runs.py   detached development harness
  prompts/                trusted system + compose_visual_brief prompts
```

## State and routes

```text
NOT_STARTED -> RUNNING -> READY
                  `-----> NEEDS_ATTENTION -> RUNNING
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/build-preparation` | State, jobs, and staleness |
| POST | `/api/v1/sessions/{id}/build-preparation/start` | Start from approved Content Architect and approved Visual Design Director projections |
| GET | `/api/v1/sessions/{id}/build-preparation/download?doc=content\|visual` | Download one of the two Markdown briefs |
| POST | `/api/v1/sessions/{id}/build-preparation/regenerate` | Re-run from current approved upstream |

The state is stored under `portfolio_sessions.current_state["build_preparation"]`.
The worker rechecks the approved upstream source reference before applying its
result, so stale work cannot overwrite newer approved state.

## Detached harness

When the development UI and Build Preparation fixture flag are enabled:

- `/build-preparation-fixture` accepts pasted or uploaded Visual Design Director JSON and an approved Content Architect JSON projection; a missing or partial VDD is normalized from the approved CA projection;
- `/build-preparation-fixture/progress` shows every stage event, both rendered briefs, and the full JSON;
- `POST /api/v1/build-preparation/fixture/run` runs the same scope -> research -> compose -> assemble pipeline without a session, approval state, or database write.

The harness auto-picks the newest matching files in `Input-Output-Of-Engine/`
by filename (tokens `visual`/`design`/`director` and `content`/`architect`),
falling back to the configured `fixture_input_path`/`fixture_content_input_path`.
It is deterministic and offline by default (`live_model=False`); its two
explicit options enable the configured model and live resource providers for
a real run. When the local debug mirror is enabled, each run is stored under
a sortable timestamp plus an eight-character run prefix.
