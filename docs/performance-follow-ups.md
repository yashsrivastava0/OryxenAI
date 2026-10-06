# Performance follow-ups

## PERF-001 — Discovery / Content Architect takes approximately 1–2 minutes

- **Status:** Implemented and verified locally. Render release awaits operator approval.
- **Reported:** 2026-10-06 by the operator, after a friend signed in from a
  separate device and successfully generated a portfolio.
- **Environment:** Live Render service `oryxenai` at `https://app.oryxenai.me`,
  using `config/app.render-free.toml`; released application commit `b00f072`.
- **Symptom:** The operator reported an approximately 1–2 minute wait during
  Discovery / Content Architect. Portfolio generation completed correctly,
  but the wait felt too long.
- **Evidence limits:** This is a user estimate, not a measured trace. The exact
  slow operation, whether the delay applies to one or both stages, run/session
  identifiers, input size, and warm-versus-idle service state are not recorded.
- **Findings:** Live Content Architect logs showed sequential planning and writing
  operations. Local uncached sample comparisons identified model reasoning time
  as a reducible cost. Queue polling and the frontend Studio hold added separate
  delays. Render Free wake-up remains a hosting delay; local measurements do
  not quantify the user's original live run.

### Implemented changes

- Retain the configured models and Free hosting. Reduce Content Architect
  reasoning effort after measuring sparse and rich samples. Keep token limits,
  grounding, coverage, readiness checks and conditional follow-up operations.
- Reduce idle worker polling from five to two seconds; keep existing concurrency
  and database pool limits for the small Render instance.
- Include the pending deterministic theme rendering and labelled sparse-input
  fixes. Check sample labels in their required heading locations rather than
  counting matching disclaimer text throughout the page.
- Reduce the initial Studio presentation hold by five seconds; an unfinished
  backend build still remains in progress.
- Add configured typical timing ranges with elapsed time and queue/overrun
  explanations, plus the operator-provided favicon and app icon.
- Log content-free queue, handler and model-stage timing for live diagnosis.

### Local live-model comparison — 2026-10-06

Medians from three uncached runs for each repository sample, using the same
configured model and theme. These measure local agent execution, not Render
cold start or a multi-user queue. All Content Architect samples needed only
the planning operation; optional writing/integration still remain available.

| Operation | Sparse input | Rich input |
| :--- | ---: | ---: |
| Explorer questions, existing settings | 6.1 s | 7.1 s |
| Explorer brief, existing settings | 20.9 s | 31.7 s |
| Content Architect, medium reasoning baseline | 55.8 s | 66.0 s |
| Content Architect, low reasoning | 35.0 s | 34.8 s |

All recorded agent runs passed their output validation. All saved Content
Architect outputs passed strict host rendering. Faster sparse and rich pages
passed required browser verification at 320, 390, 768 and 1280 pixels, without
console errors, missing resources or overflow. These checks establish sample
correctness, not identical generative wording or a guarantee for every input.

Reproduce explicitly with separate output files:

```powershell
uv run python scripts/live_performance.py --engines content_architect --ca-effort medium --output .workspace/performance/medium-review.json
uv run python scripts/live_performance.py --engines content_architect --ca-effort low --output .workspace/performance/low-review.json
```

This is opt-in live-provider testing; standard pytest remains deterministic.
See the final verification record below before releasing.

### Release follow-up

After approval, release the exact CI-passing staging SHA using the branch
procedure in `AGENTS.md`. Reconcile deployment ancestry without rewriting
remote history if necessary. Measure warm and idle-start runs on Render with
the new timing logs; adjust configured display ranges from that evidence.

### Verification record

- Python lint and source typing passed. Frontend unit tests, type checking and
  the production build passed. Browser tests cover each estimate on desktop
  and mobile, Studio hold bounds, and unfinished builds.
- Native Alembic schema validation passed. The production light Docker image
  built and its combined Render launcher applied migrations in a disposable
  PostgreSQL container. API/worker startup, readiness, authentication boundaries,
  icon responses and the public estimate metadata passed local smoke checks.
- An explicitly authorized live-model flow used repository input and an
  injected identity in that container's separate `oryxenai_test` database.
  Explorer questions took 10.6 s and the brief 32.2 s. The fuller Content
  Architect handoff took 80.8 s, including a necessary integration operation;
  this demonstrates why the one-operation benchmark is not a universal
  completion promise. The initial Studio backend build took 1.5 s. Explicit
  approvals, sandboxed preview, the requested content edit and byte-identical
  restore were verified. The initial smoke assertions had obsolete palette
  and restore assumptions; the helper now uses the current typed answers and
  validates restored page bytes rather than expecting a reused version ID.
- The clean full pytest run passed with a new workspace cache and JUnit report.
  An earlier run's cache-writing finalizer hit local permissions on an old cache
  file after the restart; using the new cache resolved that environment issue.
  Live-provider tests remained skipped by default, as intended.
- Formatting passed for tracked and task-created files. The unrestricted
  `ruff format --check .` also sees unrelated untracked research notes
  `docs/deployment/version-2/08-render-edge-cases-and-community-solutions.md`
  and `09-resilience-and-load-strategy.md`, whose code fences need formatting.
  Those notes are left untouched and excluded from this task's commit.
- No release or remote branch push occurred. After approval, staging CI and
  the approved deployment promotion still need to run for the exact SHA.
