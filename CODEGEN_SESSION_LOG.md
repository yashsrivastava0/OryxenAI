# Code Generator Completion — Session Log & Handoff

**Current Status:** **Phases 1–4 operational; visual/resource hardening implemented and locally verified.**
The standalone Code Generator workflow is wired through the API and durable PostgreSQL worker. This handoff records the follow-up changes that make the Build Preparation handoff executable (real local visuals and components), keep nested previews working, reduce browser verification to a bounded runtime smoke pass, and make future exports timestamp-first. Production session integration remains deferred per D-015; a fresh live output still needs visual review.

---

## 1. Key Accomplishments & Architectural Changes

### Core Workflow & Model Wiring (Phases 1–4)
- **Model Profiles & Worker Timeouts:** Configured provider-neutral `code_generator_*` profiles in `config/models.toml` (strict JSON schema, 600s timeouts). Configured per-kind worker timeouts in `config/app.toml` / `src/oryxenai/jobs/worker.py` (plan: 15m, acquire: 20m, generate: 90m, verify: 60m).
- **Build Preparation Ingestion:** Added auto-discovery of v3 mirror packs (`output/build-preparation/*/build-pack.zip`), `GET /build-preparation-packs`, and `POST /runs/from-build-preparation` endpoints.
- **Structured Planner & Agent:** Replaced legacy mock with `planner_operation.py` and `CodeGeneratorAgent` executing trusted structured `SitePlan` and `WorkGraph` generation with strict OpenAI schema compliance (`_strict_json_schema` in `opencode_go.py`).
- **Resource Acquisition:** Wired LLM-based `resource_scout.py` (with deterministic fallback) for emergent needs; skips execution-contract-resolved slots (D-022); materializes concrete local assets (D-025).
- **Scaffold & Visual Quality:** Built comprehensive token and motion system (`src/design/tokens.css`, `global.css`, `motion.css`) with reduced-motion support; upgraded generation prompts for grounded, verbatim copy and distinct route layouts.
- **Harness UI:** Added Build Preparation pack browser, one-click portfolio generation, and stage auto-advance toggle in `code_generator_development.html/.js/.css`.

### Hardening, Fixes & Verification (Phase 4)
- **Windows Filesystem Safety:** Implemented atomic directory swaps, path sanitization (`_unit_dir_slug`), and bounded retry/backoff in `fs_safe` / `checkpoint_store.py` to prevent transient `PermissionError` locks (D-023).
- **Source & Content Verification:** Allowed verbatim approved links (`_strip_approved_links`), raised ungrounded copy threshold to 5+ words, set `index.tsx` verification anchors, and added case-insensitive matching for CSS-transformed public copy.
- **Offline Toolchain:** Warmed offline npm cache (`scripts/warm-npm-cache.ps1`) and enforced absolute `npm_config_cache` across all runners.
- **DOM & Runtime Gate:** Anchored interaction journeys to literal markers, asserted approved external links without navigation, and validated fallback route rendering.
- **Portfolio Export:** Exported promoted candidate `source/`, `dist/`, and receipt-bound `portfolio.json` to `output/code-gen-output/<run-id>/` (D-024).

---

## 2. Verified Live E2E Runs

- **Runs `c93c86e0-dae7-4eab-b5ca-d7f13f991310` & `cb1fba07-90d8-4b74-9eb7-ffb71a60d1cd`:**
  - Consumed Build Preparation v3 pack `12-42-16-08-0aa7c140`.
  - Passed all stages: admission → planning → acquisition → foundation/route/integration generation → source checks → clean build → runtime DOM smoke.
  - Reached `ready` status, promoted preview on port 4174, and generated complete run exports under `output/code-gen-output/<run-id>/`.

---

## 3. Environment & Running Instructions

- **PostgreSQL:** Docker container `oryxenai-postgres-1` on port 5544 (migrations at `head`).
- **API Server:** `.\scripts\run-api.ps1` (or `uv run uvicorn oryxenai.main:app --port 8000`).
- **Background Worker:** `.\scripts\run-worker.ps1` (or `uv run python -m oryxenai.jobs.worker`).
- **Automated Driver:** `uv run python scratch/codegen_e2e_driver.py [run_id]` (automates auto-advance and transition logging).
- **Toolchain Cache:** `.\scripts\warm-npm-cache.ps1` (re-populates `.workspace/npm-cache`).
- **Required Env Vars:** `OPENAI_API_KEY`, `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY` in `.env`.

---

## 4. Deferred & Next Steps

1. **Doc Alignment:** Ensure `AGENTS.md`, `src/oryxenai/agents/code_generator/README.md`, and `docs/code-generator-architecture/` reflect the completed standalone workflow.
2. **Test Suite Verification:** Run full regression suite (`uv run pytest`, `uv run ruff check .`, `uv run mypy src`, `node --test tests/frontend/*.mjs`).
3. **Production Integration:** Wire into main session state machine and auto-chaining when scheduled (deferred per D-015).

---

## 5. Session continuation - 2026-08-17 13:48 +05:30

### What was investigated

The generated portfolio was technically passing the pipeline while still looking generic: required visual slots could resolve to recipes or prose, generated source could mention a resource without importing or rendering it, nested previews could lose their asset base path, and the browser gate was doing too much Playwright work without proving that the source contained a real visual system. The existing export directory also used UUID-only names, making it hard to identify when an artifact was produced.

### Implemented in this session

- **Build Preparation visual floor:** every public route now receives a required visual-component slot, and the required editorial visual resolves to a concrete local image or deterministic local TSX visual when provider material is unavailable. The materializer writes the PNG/component into the pack with provenance, dimensions, and a stable local path.
- **Executable resource contract:** pack components are copied into an importable generated-resource path; the source manifest records module versus URL bindings; source validation rejects comments, slot IDs, or manifest prose as fake evidence and requires an actual media URL, component import/render, or admitted package usage. Trusted shell, routing, and global CSS entrypoints remain protected from model overwrite.
- **Nested preview correctness:** the Vite base is relative, the scaffold reads the injected preview-base metadata, and the gateway/candidate server strip and restore nested mount prefixes consistently. This covers root and `/preview/<host>/` assets/routes rather than only a root-page screenshot.
- **Lean runtime verification:** default verification now checks route/navigation/assets/accessibility smoke behavior, overflow and main-landmark presence, image decode failures, and post-step shell health. Detailed interaction journeys are opt-in through the runtime contract instead of being generated for every possible interaction.
- **Timestamped exports:** the configured export timezone is used for a collision-safe folder named `HH-mm-DD-MM-YYYY-<shortid>`. Metadata retains UTC time plus timezone and folder, while the export remains run-isolated.
- **Documentation and decisions:** the architecture/README, prompts, `CHANGES.md`, and D-025 now describe executable visual bindings, the protected shell, and the bounded browser gate.

### Evidence collected

- Offline Build Preparation produced a `build-preparation-pack-v3` pack whose required editorial image resolved to `resources/images/resource-mock-9a7b843f5cb41f8d.png` (1600x1000) and whose required route component resolved to `resources/components/generated-local/.../PreparedVisualStory.tsx`.
- `uv run pytest tests/unit -q`: **607 passed** (with project-local temporary/cache directories).
- Post-cleanup compatibility regression: `uv run pytest tests/unit/agents/code_generator -q -o cache_dir=.workspace/pytest-cache-run`: **54 passed**. The first equivalent invocation also reached 100% but returned a pytest cache-write permission error from the existing `.workspace/cache/pytest`; rerunning with a writable cache directory passed.
- `uv run ruff check src tests scripts` passed; `uv run ruff format --check src tests scripts` passed for 319 files.
- A copied React/Vite scaffold passed offline `npm ci`, `npm run typecheck`, and the approved escalated `npm run build`; the built index uses relative asset URLs.
- `git diff --check` is clean apart from existing line-ending warnings.

### Still pending or blocked

- The historical UUID-named export under `output/code-gen-output/cb1fba07-90d8-4b74-9eb7-ffb71a60d1cd` predates these changes and was intentionally not rewritten. A fresh full run is required to inspect the promoted portfolio visually at root and nested routes and to tune model composition if it is still generic.
- Full `uv run pytest -q` did not finish within the 120-second command window; the partial run reached roughly 9% without a test failure. It needs a longer/infrastructure-backed run.
- `uv run mypy src` is blocked by the installed Pydantic plugin raising `Error constructing plugin instance of PydanticPlugin`; this is an environment/toolchain issue, not a newly observed runtime failure.
- Production session integration and automatic cross-agent chaining remain explicitly deferred by D-015. The standalone workflow is the current tested boundary.
- The approved sandbox escalation was needed only to work around Windows/esbuild traversal permissions during the scaffold build; no product fix is pending for that local restriction.

### Empty-file audit and cleanup decision

The requested Code Generator files are not empty. Each package-root example is a compatibility adapter that re-exports the implementation from `src/oryxenai/agents/code_generator/core/`; several are imported by unit/integration/worker tests, and the adapters preserve the public import path. The repository scan found no zero-byte Python implementation files under `src/oryxenai/agents`. Zero-byte `__init__.py` files under `tests/` are package markers and were retained. The only proven-unused zero-byte tracked file was `.commandcode/taste/taste.md`; it had no source, test, script, or documentation references and was removed. No Code Generator implementation or compatibility adapter was deleted.

### Next execution plan

1. Run a fresh Build Preparation -> Code Generator workflow after this handoff change.
2. Inspect the generated source for actual resource imports/URLs, route-specific composition, motion usage, spacing, and content anchors.
3. Verify root and nested preview routes plus image/component runtime smoke diagnostics; record any remaining visual defects as source/prompt issues rather than hiding them behind Playwright steps.
4. Run the complete regression suite with a longer timeout and resolve the mypy/Pydantic environment mismatch.
5. Revisit production session integration only when the deferred D-015 boundary is deliberately opened.

## 6. Session continuation - 2026-08-17 17:09 +05:30

### Implemented in this continuation

- Replaced the dense developer harness presentation with a compact, vanilla
  HTML/CSS/JS workspace: one primary **Generate portfolio** action, newest
  eligible Build Preparation pack selection, semantic four-stage progress,
  readable durable-job events, route selection, viewport controls, and a
  promoted live iframe preview. Fixture, upload, manual stage, and diagnostic
  controls remain available under **Advanced / debug controls**.
- Added readiness fields (`can_start_latest` and explicit blocker codes) so the
  primary action is disabled for a truthful reason instead of failing after a
  click. The controller still uses the durable API and persists run restoration
  through the URL/local storage path.
- Hardened Build Preparation mirror discovery to run the complete pack-v3
  admission validator before a pack is advertised as eligible. In the live
  output directory, newer packs with a route/content mismatch are now marked
  ineligible; the UI selected `11-08-17-08-73059d72`, the newest fully admitted
  mirror.
- Closed a generator architecture gap exposed by live verification: the
  planner/prompt previously granted integration ownership of the immutable
  runtime shell while the validator prohibited those files. Integration is now
  a deterministic no-write audit, and every workspace open reasserts the
  scaffold's trusted `AppRouter`, preview bridge, error boundary, entrypoint,
  and global CSS. This prevents stale or model-written shell files from
  reaching a preview.
- Added regression coverage for trusted-shell mutation, scaffold reassertion,
  readiness/page contracts, and server-authoritative latest-pack selection.

### Evidence and remaining state

- Focused verification passed: Code Generator unit suite **56 passed**;
  frontend Node suite **15 passed**; development API route tests **2 passed**;
  Ruff check/format and JavaScript syntax checks passed.
- Isolated API smoke on port 8001 served the new page and reported
  `can_start_latest: true` with no readiness blockers. A live run admitted the
  corrected pack, planned three work units, and completed acquisition. The
  prior live run reached `source_ready` but exposed an invalid generated
  `AppRouter` regex; the stale-shell/integration fixes above address that
  boundary. The fresh retry after the fix reached the foundation retry and was
  stopped by a transient provider connection error, so a new provider-backed
  run is still needed for final `ready`/preview promotion evidence.
- Browser screenshot QA was not run because the in-app browser automation
  surface was unavailable in this environment; HTTP/API smoke and durable
  worker evidence were used instead. The existing local preview gateway and
  worker processes were left untouched except for the isolated smoke restart.

### Pending follow-up

1. Run one provider-available end-to-end generation after the shell fix and
   inspect the promoted portfolio at root and every generated route.
2. Confirm the generated export appears under the timestamp-first
   `output/code-gen-output/HH-mm-DD-MM-YYYY-<shortid>/` convention and review
   visual distinctiveness, resource bindings, animation, and nested preview
   assets.
3. Keep production session integration deferred until D-015 is deliberately
   reopened.
