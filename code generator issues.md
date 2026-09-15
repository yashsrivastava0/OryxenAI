# Code Generator Issues & Operational Handoff

> Compacted issue log for the Code Generator / Build Preparation handoff. Preserves active findings, root causes, permanent fixes, environment gotchas, and architectural lessons; heavily compacts stale historical narratives and redundant campaign notes.

---

## 1. Current State & Active Frontier (as of 2026-09-11 16:48:56 +05:30 — Kiro, configured runtime)

- **Newest campaign milestone:** Run `09e10d36-c692-4d3f-a01b-6449420418be`
  (Maya Bennett, bounded preview-first campaign Slot 2) is durably **`ready`**
  at revision 85. Its clean build hash is
  `686f734e7f40b796d5778401925331f0bf1de6672046f18f2e7a55200ac36fe5`;
  the promoted preview was loaded in real Chromium with HTTP 200, complete DOM,
  substantial rendered content, and no console/page/request errors. The
  campaign stopped at **2/4** full runs; Slots 3 and 4 were never reserved.
- **Canonical complete handoff:** see the final `Complete Kiro session handoff`
  section in `docs/code-generator-live-campaign.md`. It records the user
  constraints, Run 1 context-limit diagnosis, exact prompt-scoping fix, Run 2
  effective-resource projection diagnosis, D-094 preview-first policy,
  verification-only artifact recovery, npm-cache recovery, hashes, paths,
  validation, operator commands, and dirty-worktree attribution boundary.
- **Earlier milestones retained:**
  - Run `ff3398b1` (Pack A / Arjun Mehta, Campaign B Slot 5) reached `ready`
    with all three gates and a Chrome-verified promoted preview.
  - Run `4d009f48` (Maya Bennett variable brief, 2026-09-09) reached `ready`
    with a clean build and promoted preview.
- **Current open/frontier findings:**
  - Strict profiles still enforce D-092 image obligations. The new native-only
    `preview_first_acceptance` flag does not declare missing generated image
    use fixed; it preserves `SOURCE_ROUTE_IMAGE_MINIMUM_MISSING` and
    `SOURCE_PRIMARY_ROUTE_IMAGE_MISSING` as advisories when a real build and
    preview exist. Hosted/default profiles remain strict.
  - `generation_orchestrator.py::_review_and_polish()` has a broad
    preview-first exception catch without the verifier's explicit
    `AuthorizationFenceError` carve-out. Outer fences remain and the live run
    showed no authorization failure, but future hardening should make this
    local boundary explicitly match D-094.
  - The separate semantic-decline/redelivery work reviewed in
    `semantic-review/2026-09-11-102120-pr-2.md` remains `NEEDS_CHANGES`; its
    explicit-retry, crash-safety, receipt-counting, and stale-polish findings
    are unrelated to and unresolved by this campaign.
  - The prior Priya run `74c82e9d` remains evidence of a model-output
    completeness gap: a planned image wrapper omitted the actual
    `<LocalImage>`. The suspected `_route_source_map` double-hash was disproven.
- **Environment warning:** `.workspace` contains ignored input, checkpoint,
  acquisition-material, npm-cache, and preview state needed for local
  redelivery. If it is cleaned, recover only from exact hash-matching exports
  or supported admission/acquisition paths—never by patching database state or
  bypassing integrity checks.

---

## 2. Operational Hazards & Environment Gotchas

1. **Host Memory Pressure & Resumability:**
   - 16GB RAM machines experience severe memory pressure when running multiple heavy applications. Subprocesses (`npm install`, Vite build, Playwright) may be killed by the OS.
   - The durable PostgreSQL queue resumes in-flight jobs cleanly on restart. If a job terminates mid-flight, check `code_generator_runs.status`/`coordinator_stage` in Postgres and resume rather than restarting from scratch.
2. **Uvicorn Windows Subprocess Incompatibility (`scripts/run-native.ps1 api`):**
   - Running the API with `--reload` forces uvicorn onto `asyncio.SelectorEventLoop`, which does NOT support `asyncio.create_subprocess_exec` on Windows, causing bare `NotImplementedError` on all subprocess operations.
   - **Resolution:** Run the native API without `--reload` when executing subprocess-based toolchain/build operations. The background worker is unaffected.
3. **Stale `background_jobs` Queue Pileup:**
   - Invoking handlers directly via scratch scripts bypasses `background_jobs` claiming/completion, leaving rows in `queued` status indefinitely.
   - Starting a worker with leftover queued rows will cause it to burn API calls reprocessing stale runs oldest-first. Always cancel unneeded jobs (`UPDATE background_jobs SET status='cancelled' WHERE status IN ('queued','running','retrying')`) before launching a worker.
4. **`compare_and_swap` Requires Explicit Commit:**
   - `CodeGeneratorDevelopmentRepository.compare_and_swap()` executes the SQL `UPDATE` but does NOT commit internally. Callers must execute `await db.commit()` within the same session block, or updates (e.g. `export_receipt`) will silently roll back without error.
5. **Windows Directory Locks on Repos:**
   - Leaving a terminal shell inside `.workspace/code-generator-generation/<run_id>/repo/` locks the directory against deletion or rename, triggering `GENERATION_SWAP_FAILED`. Ensure no external processes hold open handles on the candidate tree.
6. **Offline npm Cache Warming (`.workspace/npm-cache`):**
   - The generator runs with `--offline` against a dedicated cache. Adding scaffold dependencies (e.g. `@types/node`) requires warming the offline cache (`npm_config_cache=<abs path> npm install`) once, otherwise runs fail with `TOOLCHAIN_INSTALL_FAILED` / `ENOTCACHED`.

---

## 3. Permanent Architectural Lessons & Root Causes (By Subsystem)

### 3.1 Validation, Lexing & AST Audits
- **`_route_source_map` Double-Hashing Disproven (2026-09-11):** `projections["site/contract.json"]["routes"]` always supplies bare placeholders (`routes/{route_id}`). `work_graph_compiler` and `source_manifest` consistently re-derive the semantic segment for this input. Only `plan.routes` contains pre-semanticized keys.
- **Trusted Motion Pattern AST Exemption (`e7d9284`):** Section files using catalogue-trusted patterns (`pattern_id: "reveal-fade-rise"`, `<Reveal>`) delegate animation styles to `motion.css`/`SharedSystems.tsx`. `typescript_ast_audit.py` now requires only the target marker and trusted JSX tag, skipping local CSS and `prefers-reduced-motion` checks.
- **Quote-Tolerant Selector Matching (`5bef169`):** `source_validation.py` uses `_literal_present` to tolerate single quotes, double quotes, or unquoted CSS attribute selectors (`[data-motion-target="val"]` vs `[data-motion-target='val']`).
- **Comment Stripper Regex-Literal Awareness (`source_lexing.py`):** JS regexes containing slashes (`.replace(/\/+$/, "")`) were previously misread as comment starts `//`, truncating source lines. Heuristic handles regex literals safely.
- **CSS Shorthand vs. Longhand Guidance (`ac5543e`):** Overriding only `column-gap` on a rule setting `gap` left `row-gap` cascading without the literal string `row-gap` appearing in the file. Guidance directs models to split into explicit longhands.
- **Diagnostics File Expansion for Route Diagnostics:** `diagnostics.py::build_bundle` expands `allowed_paths` into real source when DOM/runtime diagnostics supply `route_id` without explicit `.file`.

### 3.2 Host Normalizers & Schemas
- **Dynamic Color Token Lookup in Lifecycle Normalizer (`06eb2c0`):** `d9caf30` hardcoded assumed color token names (`--color-accent-signal`, etc.). `_resolve_existing_color_token()` now dynamically scans the route's actual generated CSS for `--color-*` variables by semantic keyword, omitting declarations if unresolvable.
- **Route-Batch Motion Normalizer (`22db99c`):** Normalizes spelled-out CSS length units (`fiftych` → `50ch`), anchors trusted selectors, and injects guarded fallback CSS for `:has()`.
- **Quality Finding Blank Field Identification (`01e9ed0`):** `QualityFindingV2` validator explicitly reports which required fields are empty (e.g. "empty field(s): evidence") so the 2-attempt schema retry receives actionable error feedback.
- **Fluid Typography Step Casing (`90e8349`):** Normalizes `type_steps` names to prevent double-prefixed tokens (`--type-type-heading-*` → `--type-heading-*`).
- **Duplicate Path Deduplication:** `generation_orchestrator.py` adopts last-write-wins semantics for duplicate file paths in a single model response rather than raising `SOURCE_DUPLICATE_PATH`.
- **Section Import Depth Guidance:** Explicitly document 3 levels (`../../../`) for section components and 2 levels for route composers (`index.tsx`).

### 3.3 Scaffold & Runtime Verifier
- **Safe Fragment-Only Href Routing:** `ResourceUrl.ts::publicRouteUrl` now passes `#`-prefixed fragments through verbatim instead of throwing `Error: Unsafe local route path`, preventing CTA same-page links from crashing whole-page mounting.
- **Content-Box Measurement for Regions:** `runtime_verifier.py` measures content box (`rect.width` minus computed inline padding) instead of `getBoundingClientRect()` border box, resolving universal 1.000 ratio false-positives (`RUNTIME_REGION_WIDTH_RATIO`).
- **Multi-Column Intent Verification:** `RUNTIME_REGION_COLUMN_COUNT` checks whether multi-column layout is preserved (`computedColumns > 1`), rather than enforcing exact design-grid track counts (e.g. demanding literal 8 or 12 CSS columns).
- **Marker-Scoped Distinctive Move Checking:** `DistinctiveMoveRuntimeCheckV1` carries `runtime_marker`, allowing the verifier to inspect nested marked elements rather than incorrectly failing on the outer region container.
- **Transform Matrix Comparison:** Normalizes expected authored transforms via a detached DOM probe element before comparing against browser-computed `matrix(...)`/`matrix3d(...)` strings.
- **Font Verification Pre-Load:** Calls `await document.fonts.load(weight, family)` before `.check()` to avoid false negatives on unrendered weights.
- **Runtime Diagnostic Deduplication:** Dedupes diagnostics by `Diagnostic.fingerprint` across viewports before returning bundles to repair.
- **Dual `tsconfig` Typechecking (`78117e7`):** Scaffold checks both `tsconfig.app.json` and `tsconfig.node.json` rather than bare empty root `tsconfig.json`.

### 3.4 Resource Acquisition & Image Policy
- **Resilient Image Acquisition Fallback:** Pinned signed URLs (D-060) can expire between planning and generation. Acquisition wraps pinned candidate downloads in try/except and falls back to a fresh live search before failing.
- **Non-Required Resource Fallback Semantics:** `required=false` placements lacking local assets are treated as valid decorative opportunities, not blocking failures.
- **Hashed Image Obligations (D-092):** Generates and binds a hashed image policy across planning, realization, and verification to guarantee at least 2 visible images when assets exist.

### 3.5 Orchestrator, Prompts & Budgets
- **Stable Prompt Cache Keys (`44304ff`):** Rekeyed from per-generation IDs to `codegen:{role_profile}:{operation}:{operation_hash[:16]}`, enabling high cache reuse on system prompts and schemas across runs.
- **Bounded Repair & Honest Declines:** `FinalRepairDeclined` handles explicit model `cannot_complete` responses, stopping early instead of burning the remaining repair budget.
- **Tighter Budgets (2/4/3):** Pydantic defaults aligned with `config/app.toml`: 2 rounds per unit, 4 total repair rounds, 3 integration polish rounds, max 2 job attempts.
- **Auto-Build on Failed Exports (`3f5b2aa`):** `export_failed_run()` attempts a best-effort clean build (`npm ci` + `npm run build`), ensuring `needs_attention` exports provide inspection-ready `dist/` bundles.
- **Unverified Candidate Previews (`7f09506`):** Failed/attention runs with valid builds serve an unverified candidate preview in the dev harness iframe bridge.

---

## 4. Chronological Campaign & Fix Summary (Compacted)

- **2026-09-11 (00:40):** Disproved `_route_source_map` double-hash hypothesis; isolated real gap in run `74c82e9d` as missing `<LocalImage>` inside planned wrapper div.
- **2026-09-10 (23:19):** `[01e9ed0]` Fixed schema-correction retry by naming exact empty fields in `QualityFindingV2`.
- **2026-09-10 (22:52):** `[882574e, 1563282]` Raised image floor to `minimum_visible_images=2` and `require_primary_route_image=true` (D-092).
- **2026-09-10 (19:50):** `[11a8fe3]` **Campaign B Slot 5 (Run `ff3398b1`, Pack A) achieved `ready`.** Promoted preview verified in Chrome. Campaign B closed (1/5 ready).
- **2026-09-10 (18:50):** `[06eb2c0]` Slot 4: Fixed unbound custom properties from hardcoded normalizer color names via `_resolve_existing_color_token()`.
- **2026-09-10 (17:28):** `[e7d9284]` Slot 3: Fixed false-positive AST check on catalogue motion patterns (`<Reveal>`). Documented uvicorn `--reload` subprocess bug.
- **2026-09-10 (15:55):** `[D-090, D-091]` Fixed integration test fixture route paths and preserved real issue codes (`PLAN_SECTION_COVERAGE`) in verification exports.
- **2026-09-10 (14:15):** `[d9caf30]` Added deterministic selected-work lifecycle cue normalizer.
- **2026-09-10 (14:00):** `[22db99c]` Added route-batch normalizer for spelled CSS lengths, selector anchors, and `:has()` fallback styling.
- **2026-09-10 (12:00):** Reconciled repair budget defaults to 2/4/3 across `settings.py` and `app.toml`.
- **2026-09-10 (00:03):** `[90e8349]` Fixed fluid typography token double-prefixing (`--type-type-*`).
- **2026-09-09 (23:39):** `[9716681]` Caught inert disclosure panels; aligned `columns_*` review guidance with D-076.
- **2026-09-09 (22:41):** `[4da1ddb]` Made toolchain preflight cleanup resilient to Windows directory enumeration denials.
- **2026-09-09 (22:22):** `[14bb97c, c8a66e7, 80a925c]` Replaced keyword-based severity inference with explicit host-owned findings; subjective observations marked advisory.
- **2026-09-09 (20:31):** `[a503a4a]` Implemented reliability plan R01–R12: proposal retention, attempt tracking, serial scheduler, hashed image obligations, layout recipes.
- **2026-09-09 (13:45):** 5-run variable campaign: PowerShell npm shim (`d1c5645`), lock repair (`2b2714a`), content key coverage (`97d83dd`), undeclared import gate (`59bf982`), repair tag reconciliation (`29fc598`).
- **2026-09-09 (03:00):** `[2f424e5]` Variable Build Prep pass; Run `4d009f48` (Maya) achieved **`ready`** with promoted preview.
- **2026-09-09 (00:xx):** `[44304ff, 2790e9d, a2ae087, 051afa6, f20779f]` Final repair decline escape hatch, stable prompt-cache keys, undeclared npm import scan, color token collision guidance, `/app` Generate & Preview stage.
- **2026-09-08:** `[7f09506, 5bef169, ac5543e, 3f5b2aa]` Candidate previews in dev harness, auto-build on failed exports, quote-tolerant selectors, CSS longhand guidance.
- **2026-09-07:** `[78117e7]` Scaffold dual typecheck, nav routing `data-navigation-target`, `.map()` content binding, touch targets 44px.
- **2026-09-06:** Box model content-box fix (`RUNTIME_REGION_WIDTH_RATIO`), multi-column loosening, motion transform matrix normalization, font pre-load check, fragment CTA pass-through.
- **2026-09-05:** Resilient image acquisition fallback for stale pinned URLs, polish loop finding dedup, spelled CSS length normalization.

---

## 5. Investigated & Proven Non-Bugs (By Design / Closed)

- **`_route_source_map` Double-Hashing:** Not a bug. Production contracts supply bare `routes/{route_id}` placeholders; semantic hashing is derived consistently.
- **`style_primitive` & `component_reference_only` Fallbacks:** By design; style primitives have no live provider and reference-only components have no local code paths.
- **Mobile Viewport Release Gate:** Explicitly excluded; mobile verification is advisory only, desktop and tablet are the release gates (D-088).
- **MagicUI Live Provider Rejections:** External live service rejections fall back cleanly to approved alternatives by design.
- **Postgres Port Configuration:** Default is 5432 (`config/app.native.toml`). Port 5545 was a machine-specific local service conflict workaround; use `.env` `DB_PORT_OVERRIDE` if conflicts arise.
