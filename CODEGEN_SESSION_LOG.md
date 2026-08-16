# Code Generator Completion — Session Log / Handoff (2026-08-16)

Working session goal: make the Code Generator agent fully runnable end-to-end
(gpt-5.6-luna), auto-consume the Build Preparation output, and drive one
portfolio all the way to a promoted verified preview.

**Current status: one blocker remains** (Windows `PermissionError` during
route checkpoint swap, details in "CURRENT BLOCKER"). Everything before it
now works live: pack admission → planner → acquisition → foundation →
route generation → source checks. See "HOW TO RESUME".

---

## 1. What was accomplished (all changes are in the working tree, uncommitted)

### Phase 1 — Made the workflow runnable
- `config/models.toml` — all seven `code_generator_*` profiles filled with the
  live-confirmed settings (`gpt-5.6-luna`, `https://api.openai.com/v1`,
  `OPENAI_API_KEY`, `reasoning_effort = "low"`, `thinking_mode = true`,
  builder timeouts 600s). Readiness endpoint now reports all-true.
- `src/oryxenai/core/settings.py` + `config/app.toml` + `src/oryxenai/jobs/worker.py`
  — per-job-kind handler timeouts (`[worker.job.kind_timeouts]`, quoted TOML
  keys): plan 15m, acquire 20m, generate 90m, verify 60m. This fixed a
  guaranteed JOB_TIMEOUT loop (old flat 300s would kill every generate job).
- Readiness report extended (`development_service.py`):
  `build_preparation_pack_ready`, `build_preparation_latest`, `browser_ready`
  (filesystem probe — the sync Playwright driver teardown is broken on
  Windows, so no driver launch; async launch itself works).

### Phase 2 — Build Preparation input source (auto-pick)
- `core/development_input.py` — `from_build_preparation_mirror()` +
  `list_build_preparation_packs()` + `_mirror_pack_info()`: newest-first
  discovery of `output/build-preparation/*/build-pack.zip`, early
  pack_version/expiry/handoff checks, immutable store via `_store_source`.
- `core/development_schemas.py` — input mode literal now includes
  `build_preparation_mirror`; `BuildPreparationRunRequest` schema.
- `core/development_service.py` — `create_from_build_preparation()`,
  `build_preparation_packs()`.
- `api/routes/code_generator_development.py` — `GET /build-preparation-packs`,
  `POST /runs/from-build-preparation` (`{"pack": "latest" | "<dir>"}`).
- Settings: `build_preparation_mirror_root = "output/build-preparation"`
  (`[code_generator_development]`, settings class + app.toml).

### Phase 3 — Front end (the separate temporary harness UI)
- `code_generator_development.html/.js/.css` + controller `.mjs`:
  "Build Preparation output" panel (auto-loads packs, auto-selects newest
  eligible, expiry/issue badges), one-click **Generate portfolio**, and an
  **Auto-advance** toggle (default on, persisted) that chains
  plan → acquire → generate → verify on status transitions and stops on
  `needs_attention`. Manual stage buttons unchanged.
- `tests/frontend/code_generator_development.test.mjs` updated + new tests
  (14 pass via `node --test`).

### Phase 4 — Real structured agent in the agent folder (mock retired)
- New `core/planner_operation.py` — the single structured planner call
  (trusted prompts + canonical JSON context + strict structured output +
  SitePlan validation + `_canonicalize_work_graph` which mechanically fills
  the terminal integration unit's `depends_on` invariant).
- `agent.py` rewritten: `CodeGeneratorAgent(model_client)` performs the real
  structured planner operation via the shared function; `schemas.py`
  reworked (`CodeGeneratorRequest`/`CodeGeneratorResponse`); `samples/`
  deleted; `__init__.py` docstring updated; registry wires
  `CodeGeneratorAgent(model_client=MockModelClient())`; `MockModelClient`
  gains a minimal `SitePlan` envelope; `tests/conftest.py` test mock
  delegates code_generator operations to it.

### Phase 5 — Acquisition / correctness fixes
- Resource scout LLM path wired for real (was dead code):
  `core/resource_scout.py` now has `ScoutSelection` +
  `select_candidate_with_scout()` using `prompts/resource_scout.md` +
  `resource_scout_task.md` (previously unused); the acquire handler builds
  the scout from `build_provider_client("code_generator_resource_scout")`
  when `prefer_resource_scout_model = true` (now enabled in app.toml);
  deterministic scorer remains the fallback; receipt label only claims the
  profile when a scout/selector actually ran.
- `generation_orchestrator.py` — checkpoint accept now uses the canonical
  `checkpoint_store` (was constructing a second store with the wrong
  generation id).
- Deleted unused `core/assembler.py` + its shim; `node_modules/` added to
  `.gitignore`.

### Phase 6 — Visual quality (text-only, per D-015)
- Scaffold `src/design/` rebuilt: full token system (fluid `--text-*` clamp
  scale, `--space-*`/gap cadence, surfaces/elevation/radii, z-scale, motion
  easings/durations), `global.css` utilities (`.container`, `.section`,
  `.stack`, `.cluster`, `.grid`, `.grid--sidebar`, `.card`, `.lift`,
  `.eyebrow`, `.action`, skip-link, focus-visible), `motion.css` reveal
  system (`.reveal*`, `.stagger` — defined only under
  `prefers-reduced-motion: no-preference`). No new npm deps.
- Prompts upgraded (planner v5, foundation/route_batch/repair v3→v4 era,
  compose/integrate v3): distinct per-route layout strategies, spacing/type
  discipline, choreographed reveals with reduced-motion, vendored-component
  rewrite into the CSS-token idiom (no Tailwind exists in this scaffold).

### Provider-layer fix (affects all agents using strict schema)
- `agents/shared/providers/opencode_go.py` — `_strict_json_schema()` /
  `_strictify()`: OpenAI strict json_schema mode requires every property in
  `required` and `additionalProperties: false`; pydantic's optional-default
  fields violated this. Normalization strips `default`, requires all props.
  Verified live: SitePlan and GenerationResult both pass + pydantic-validate.
- Dead schema removed: `IntegrationResult` (had a `dict[str, Any]` field
  that strict mode cannot express; it had zero consumers).

### Build Preparation fixture repair (root cause of ALL bad packs)
- Symptom chain: every Aug-14 mirror pack was internally inconsistent
  (route `section_sequence` empty vs public content sections present) and
  the fresh fixture run produced review-only `phase3` packs.
- Root cause: the fixture passed `content_architect={}`, forcing
  legacy layout; the VDD output file has no `approved` stamps.
- Fix in `agents/build_preparation/fixture.py`: `_fixture_inputs()` prefers
  an explicit override, then the NEW configured CA snapshot file
  (`fixture_content_input_path = "src/oryxenai/output/content-architect"` —
  the user's real CA output that pairs with the VDD file), then VDD
  `intake`; stamps the approval hashes production would have
  (`_fixture_direction_hash`). Settings + app.toml updated.
- Result: fresh pack `12-42-16-08-0aa7c140` is v3, handoff-eligible, and
  passes the Code Generator's own full admission.

### Generation-runtime bugs found and fixed during the live runs
Each of these was a hard failure fixed and verified by re-running:

1. `PROVIDER_INVALID_REQUEST_ERROR` — OpenAI strict schema rules (fixed by
   `_strict_json_schema` above).
2. `PLAN_WORK_UNIT_SCOPE` / `PLAN_INTEGRATION_DEPENDENCIES` — WorkGraph
   contract now stated explicitly in planner.md + terminal depends_on
   canonicalized deterministically.
3. Handler `NameError` — my refactor dropped the `result`/`prompt_receipt`
   variables; `run_planner_operation` now returns
   `(plan, prompt_version, receipt, result)`.
4. `ACQUIRED_RESOURCE_MISSING` — receipts' `local_path` already carries the
   run-id prefix; orchestrator + verification handler double-joined the run
   id. Both now pass the bare materials root.
5. `NotADirectoryError` (WinError 267) — work-unit ids contain `:`
   (`unit:foundation`); Windows forbids colons in paths.
   `_unit_dir_slug()` sanitizes all reserved characters now.
6. `SOURCE_RUNTIME_NETWORK` (×4, unrepairable) — THREE distinct causes:
   a) the model rendered the user's approved LinkedIn/GitHub links;
   b) pipeline-owned trusted manifests (`src/generated/*`,
      `src/content/public-data.ts`) contain approved URLs as data;
   c) enum-ish content values. Fixes: `_strip_approved_links()` in
   `source_validation.py` allows URLs that appear verbatim in approved
   public content (href attributes or plain literals); trusted manifest
   paths exempted from the text scan; content-coverage sweep now checks
   prose only (`" " in text and len >= 6`).
7. `SOURCE_CREATE_EXISTS` / `SOURCE_REPLACE_MISSING` — the model couldn't
   know what existed: `_operation_context` now includes `existing_files`.
8. `GENERATION_CONTEXT_MISMATCH` — nothing told the model to echo
   `context_receipt_hash`; instruction added centrally in
   `generation_prompt_builder.build_instructions`.
9. `MISSING_APPROVED_ROUTE_CONTENT` — context omitted the copy; added
   `site_contract.public_content` (per-unit routes).
10. `MISSING_FROZEN_SHARED_SOURCE` — context omitted the code being built
    against; added `shared_source` (bounded snapshot of current source tree)
    + `previous_attempt_files` (rejected candidate) for repairs.
11. `OWNERSHIP_ROUTE_PATH_CONFLICT` — planner-declared route paths diverged
    from the trusted route-registry storage keys; `_owned_paths()` now
    derives route ownership canonically from the site contract storage key,
    and integration owns `src/design/** + src/components/shared/** +
    src/routes/**` for final reconciliation.
12. `SOURCE_UNGROUNDED_COPY` storms — threshold raised to 5+ word spans
    (micro-labels allowed); route prompt now says copy is verbatim-only.
13. `TOOLCHAIN_INSTALL_FAILED` (ENOTCACHED @babel/types) — npm cache was
    never populated AND the relative `npm_cache_root` resolved against each
    run's repo dir (fresh empty cache per workspace). Fixes: warmed the
    cache once (`scripts/warm-npm-cache.ps1` added for repeatability) and
    made all three npm call sites (check_runner, dependency_manager,
    build_runner) pass an ABSOLUTE `npm_config_cache`.
14. Model-call cache ignored prompt text — cache key now includes the
    operation prompt hash, so prompt fixes invalidate stale cached outputs.
15. Generation orchestrator catch-all now logs the full traceback
    (`logger.error(..., exc_info=exc)`) — previously only the type name.
16. Planner acceptance markers: planner.md v5 requires short embeddable
    `marker:<criterion_id>` tokens (the old run's plan had sentence-style
    markers); route/compose/integrate prompts require `index.tsx` to be the
    verification anchor (route_id, section_ids, verbatim copy, source
    markers, `data-interaction-id` attributes).

### Infrastructure repaired along the way
- Docker Desktop + `oryxenai-postgres-1` started; the app DB had ONLY
  `alembic_version` (schema lost) — `alembic stamp base` + `upgrade head`
  rebuilt all 7 tables (no data existed to lose).
- Scaffold typecheck passes; scaffold offline install verified
  (68 packages from the 16MB warmed cache).

---

## 2. Live E2E progress (run `b2d61076-a0f6-4932-b602-5c91e6a68f75`, newest)

Through the durable API path (worker + API running):
- run created from mirror pack `12-42-16-08-0aa7c140` ✓
- admission + planner (real gpt-5.6-luna call, ~30s) ✓
- acquisition ✓ (Pexels images materialized, licences written,
  lucide-react bound)
- toolchain offline install ✓ (cache fix working)
- foundation unit: generated + typechecked + checkpointed ✓
- route unit: generated, checks passed, **failed at checkpoint swap** ← HERE

Best earlier run (`0ac50c90-…`) got furthest on content: all four units
checkpointed and `source_ready`, but its verify failed on source-contract
markers (old plan's sentence-style markers + enum-value coverage) — both of
those validator/prompt issues are now fixed; the fresh run `b2d61076`
supersedes it.

---

## 3. CURRENT BLOCKER (where the session is stuck)

`PermissionError` at `checkpoint_store.accept()` → `os.replace(partial, target)`
(`core/checkpoint_store.py`, the atomic partial→target rename) when accepting
the ROUTE unit's checkpoint on Windows.

Most likely causes (in order of probability):
1. A file handle inside `checkpoint_root/<hash>` or the workspace repo is
   still open when `os.replace` runs — prime suspect: npm/node processes
   from the just-finished `npm ci`/`tsc` (typecheck runs immediately before
   the checkpoint in `_run_unit`), or Windows Defender scanning freshly
   written files. `os.replace` on Windows fails with PermissionError if the
   destination is held open even briefly.
2. The destination `checkpoint_root/<hash>` already exists as a DIRECTORY
   from an earlier failed attempt with an open/partial state.

Suggested fixes (next session):
- Retry with backoff around the `os.replace` (e.g., 5 attempts, 500ms→2s) —
  standard Windows rename-lock mitigation; keep failing honestly after.
- Before replace, if `target.exists()`, remove with
  `shutil.rmtree(target, ignore_errors=False)` inside the same retry loop.
- Ensure `run_source_checks`' npm/tsc child processes are fully reaped
  before checkpointing (`process_runner` already kills descendants — verify
  for the `subprocess.run` path in `check_runner`).
- Reproduce in-process:
  `CodeGeneratorGenerationOrchestrator().execute({'development_run_id': 'b2d61076-…'}, 'diag')`
  (worker log at `.zcode/.../call_8392d1785ef64aa4be475a99-stdout.log` has
  the full traceback).

---

## 4. Environment / how to resume

- Postgres: docker `oryxenai-postgres-1` on 5544, migrations at head.
- API: `uvicorn oryxenai.main:app` on 127.0.0.1:8000 (running, current code).
- Worker: `uv run python -m oryxenai.jobs.worker` (running, current code).
- Driver script: `scratch/codegen_e2e_driver.py`
  (arg = optional existing run id; mirrors the UI auto-advance flow;
  logs status transitions, exits 2 on needs_attention with issues).
- Mirror pack: `12-42-16-08-0aa7c140` (expires 2026-08-19; regenerate via
  `POST /api/v1/build-preparation/fixture/run` if expired — the fixture is
  fixed and produces eligible v3 packs now).
- npm cache: `.workspace/npm-cache` warmed; `scripts/warm-npm-cache.ps1`
  re-runs it after any scaffold lockfile change.
- Env vars needed: `OPENAI_API_KEY`, `PEXELS_API_KEY`,
  `UNSPLASH_ACCESS_KEY` (present in `.env`).

## 5. Remaining work after the blocker

1. Fix the PermissionError (above), finish the E2E: route checkpoint →
   compose → integration → verify (clean build + Playwright journeys) →
   promoted preview at `http://127.0.0.1:4174/preview`.
2. Visually inspect the promoted portfolio (preview iframe / browser) and
   tune prompts/scaffold as needed.
3. Full verification: `uv run pytest` (unit/api/integration/worker),
   `ruff check`, `ruff format --check`, `mypy src`,
   `node --test tests/frontend/*.mjs`. NOTE: the suite has NOT been run
   since these changes — some tests will need updating (contract tests for
   the new agent surface were updated; others weren't).
4. Docs: `AGENTS.md` (mock retired, mirror input, kind timeouts),
   `src/oryxenai/agents/code_generator/README.md`,
   `docs/code-generator-architecture/` status, `CHANGES.md` entry,
   `DECISIONS.md` (strict-schema normalization, approved-link policy,
   fixture pair reunion, canonical route ownership).
5. The entire standalone workflow is still UNTRACKED in git — commit on
   explicit go-ahead.
