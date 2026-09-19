# Code Generator Issues

Audit date: 2026-09-19
Scope: the production Code Generator session stage, Build Preparation handoff, durable worker pipeline, toolchain, preview promotion, and authenticated frontend preview theater.

This is an issue-finding report only. No implementation fix was made during this audit. The existing historical file `code generator issues.md` was left untouched; this file is the current architecture-focused audit.

## Executive conclusion

The main reason a generated portfolio can finish code generation but still be unavailable to the user is a broken preview delivery contract between the worker container, preview gateway, and browser. The Docker overlays use a container-local `localhost` URL as the public preview URL while using the correct service-DNS URL only for health checks. With public readback required, promotion is attempted from the worker against the worker's own localhost, fails, restores the pointer, and leaves the run in `preview_pending` without an active preview. The frontend then has no browser-level error state for this failure.

There are also upstream causes that prevent the pipeline from ever reaching preview: stale Build Preparation briefs can be admitted, API preflight proves a different process than the worker that actually builds the site, offline npm lock generation is not compatible with the clean verification install, and model route generation is asked to reconstruct large approved-content arrays from a type-only content interface. These are pipeline-contract issues, not isolated UI defects.

## Priority summary

| ID | Priority | Issue | Primary failure symptom |
| --- | --- | --- | --- |
| CG-001 | P0 | Docker preview URL uses the wrong network namespace | Verification/promotion ends in `preview_pending`; no usable active preview |
| CG-002 | P0 | Code Generator admits stale Build Preparation output | Expensive generation from obsolete briefs, then stale-source rejection/no preview |
| CG-003 | P1 | API preflight is not proof of worker readiness | Start looks ready but the worker fails on npm/browser/environment/toolchain |
| CG-004 | P1 | Lockfile creation and verification use incompatible npm contracts | Acquire or clean build fails on optional platform dependency trees |
| CG-005 | P1 | Model source-generation boundary hides approved values while requiring literal reconstruction | Route batch returns `cannot_complete`; no build or preview |
| CG-006 | P1 | Server preview readback is not the same as browser reachability | API may report a URL that the user's browser cannot load; blank theater |
| CG-007 | P1 | Build execution is not isolated/serialized against Windows Node/Vite process contention | `VITE_NODE_SPAWN_EPERM`, repeated verification failures, retry dependence |
| CG-008 | P1 | Verification feature/configuration flags do not form one enforced capability gate | Deployment configuration can claim verification is disabled while session Code Generator still runs it |

The first five should be treated as release blockers for a reliable Generate → Preview flow. CG-006 and CG-007 are required for operational reliability. CG-008 should be resolved before relying on environment overlays as safety controls.

## Detailed findings

### CG-001 — Docker preview URL is container-local, so promotion cannot produce a user preview

**Priority:** P0 — confirmed configuration/system-design break in Docker and the isolated Docker Code Generator path.

**Evidence:**

- `config/app.docker.toml:78` sets `preview_base_url = "http://localhost:4174/preview"`.
- `config/app.docker.toml:81` correctly sets the worker-to-gateway health URL to `http://preview-gateway:4174/health/live`.
- `config/app.docker.toml:89` sets `preview_public_readback_required = true`.
- `config/app.docker.codegen-run.toml:53` repeats the same split: public/base URL `http://127.0.0.1:4174/preview`, internal health URL `http://preview-gateway:4174/health/live`.
- `src/oryxenai/preview/promotion.py:377-401` performs public readback using `preview_base_url`; `src/oryxenai/preview/promotion.py:440-501` makes HTTP requests to that URL and restores the active pointer if readback fails.
- `src/oryxenai/preview/promotion.py:403-416` returns the same base URL to the frontend as the active preview URL.

**Failure path:**

1. The worker is in its own container. `localhost:4174` there means the worker container, not `preview-gateway` and not the user's browser.
2. The preview gateway may be healthy through service DNS, so the internal health check can pass.
3. Candidate storage and pointer promotion then use the worker's `preview_base_url` for required public readback.
4. The worker cannot reach its own `localhost:4174/preview/<host>/` because the gateway is a different container. Readback fails.
5. Promotion restores the pointer and the verification handler persists `PREVIEW_PUBLIC_READBACK_FAILED`/`preview_pending` behavior. No `active_preview` is available for the user.

**Why this is architectural:** the same setting is being used for two different audiences: worker-to-gateway networking and browser-facing public addressing. A service-DNS URL is valid inside Compose but not in the browser; `localhost` is valid for neither the worker-to-gateway call nor a browser outside that container.

**Required design decision:** define separate, explicit internal gateway and browser/public preview origins, and bind the promotion/readback contract to the browser-visible origin. The deployment path must render and validate the public origin before a job can be admitted.

### CG-002 — Code Generator can start from a stale Build Preparation handoff

**Priority:** P0 — confirmed handoff consistency gap.

**Evidence:**

- `src/oryxenai/agents/build_preparation/service.py:203-232` computes `approved_upstream_changed` and `approved_upstream_unavailable` when Build Preparation state is read.
- `src/oryxenai/agents/code_generator/service.py:149-155` checks only `preparation.status == READY` and that both Markdown strings are nonempty when starting Code Generator. It does not ask Build Preparation for its current staleness calculation or recompute the approved Content Architect/Visual Design Director source reference.
- `src/oryxenai/agents/code_generator/service.py:1085-1107` checks stale reasons only after a Code Generator session state already exists.
- `src/oryxenai/jobs/handlers/code_generator_verification.py:325-343` performs the authoritative stale-source rejection late, immediately before verification/promotion.

**Failure path:**

1. Content Architect or Visual Design Director is changed and re-approved after Build Preparation produced its Markdown pair.
2. Build Preparation can report that its state is stale, but Code Generator reads the raw JSONB state directly and sees `READY`.
3. Code Generator admits and binds the old Markdown pair, then spends model calls, resource acquisition, source generation, and build time on it.
4. Verification eventually discovers that the session source is no longer current and refuses to promote it, or a caller sees output derived from the wrong approved inputs.

**Impact:** the system detects an invalid handoff at the most expensive and user-confusing point. This creates “generation failed/no preview” reports even though the actual defect occurred before Code Generator started. It also weakens the promised immutable approved-pair boundary: the pair is immutable after admission, but admission itself is not guaranteed to be the latest eligible pair.

**Required design decision:** Code Generator start must consume a single Build Preparation admission result that includes a fresh upstream source reference and a non-stale decision. A `READY` JSONB projection alone is not sufficient.

### CG-003 — API preflight proves the API process, not the worker that executes the portfolio

**Priority:** P1 — confirmed process-boundary design gap; live campaign evidence exists.

**Evidence:**

- `src/oryxenai/agents/code_generator/service.py:953-1060` performs start-time checks for provider profiles, credentials, npm availability, browser availability, and provider preflight from the API request process.
- The actual clean build runs in the durable worker through `src/oryxenai/agents/code_generator/core/build_runner.py:293-369` and the verification handler.
- `src/oryxenai/agents/code_generator/core/development_service.py:340-475` has a more complete disposable toolchain preflight and worker-contract readiness path, but the production session `CodeGeneratorService.start()` does not bind a successful toolchain receipt from the worker to the run.
- `docs/code-generator-repair-plan-campaign-2026-09-18.md` records a real mismatch: stale/background process environments reported `node: false` and `browser: false` even though an interactive environment was healthy; duplicate stale worker/preview processes also affected live runs.

**Failure path:**

1. API process passes npm/browser/provider checks.
2. Job is committed to PostgreSQL and claimed by a separate worker/container with a different PATH, npm cache, browser installation, filesystem, or preview network.
3. The worker fails during acquisition, clean build, browser launch, or preview readback after the user has already been told generation is ready.

**Impact:** false-green admission and false-red admission are both possible. The UI cannot distinguish a portfolio/source problem from an execution-environment problem, and retries do not change the underlying worker capability.

**Required design decision:** make worker readiness a durable, identity-bound capability receipt. It must include the worker release, pipeline contract, Node/npm/browser facts, npm cache/install proof, preview gateway reachability, and the configuration identity used for the job. Start should refuse work unless a compatible worker has recently proved the same contract.

### CG-004 — Dependency acquisition can produce a lockfile that the verification gate rejects

**Priority:** P1 — confirmed live failure and current cross-stage contract mismatch.

**Evidence:**

- `src/oryxenai/agents/code_generator/core/dependency_manager.py:306-340` creates or mutates a lockfile with `npm install --package-lock-only --offline`.
- `src/oryxenai/agents/code_generator/core/dependency_manager.py:342-359` installs with offline `npm install`, and its comment acknowledges platform-aware optional dependency repair.
- `src/oryxenai/agents/code_generator/core/build_runner.py:303-311` uses a separate clean verification command whose configured default is `npm ci --offline`.
- `docs/code-generator-repair-plan-campaign-2026-09-18.md` records a reproducible run where the generated lockfile contained blank/invalid optional platform dependency versions in the Tailwind oxide subtree; later `npm ci --offline` failed with invalid-version/out-of-sync behavior. A temporary network-generated lockfile made the later offline clean install pass.

**Failure path:** acquisition commits a lockfile accepted by its own npm-install path; verification deletes `node_modules` and applies the stricter npm-ci path; npm rejects the lockfile before TypeScript, Vite, runtime verification, or preview promotion.

**Impact:** this is infrastructure-deterministic and cannot be repaired by a model. It blocks every portfolio whose admitted dependency tree exercises the platform-optional package shape. Cache warming is not sufficient when the lockfile itself is malformed.

**Required design decision:** acquisition and verification need one canonical package-manager contract. The exact lockfile produced for a generated workspace must be validated by the exact clean-build command before it is committed as an accepted dependency receipt. Platform-specific optional dependency resolution must be deterministic or explicitly downgraded to a safe fallback.

### CG-005 — Route generation hides approved values while requiring the model to reconstruct every literal reference

**Priority:** P1 — confirmed live model failure; current architecture remains fragile even though the prompt contains mitigations.

**Evidence:**

- `src/oryxenai/agents/code_generator/core/generation_orchestrator.py:4607-4658` includes `src/content/generated-content.ts` for route batches but replaces its body with `_compact_generated_content_interface`.
- `src/oryxenai/agents/code_generator/core/generation_orchestrator.py:4663-4708` exposes only the `ApprovedContentId` literal union and the `contentValue()` signature; approved runtime values are deliberately omitted.
- `src/oryxenai/agents/code_generator/core/generation_contract.py:726-747` requires direct literal `contentValue("...")` calls for every approved content key.
- `src/oryxenai/agents/code_generator/prompts/route_batch.md:210-270` instructs the model to emit all literal calls and explicitly says repeated/array-heavy content is not a reason to decline.
- `docs/code-generator-repair-plan-campaign-2026-09-18.md` records an actual route-batch failure with `MISSING_APPROVED_SOURCE_VALUES`: the model saw a type-only interface and a large set of IDs, but declined an array-heavy experience/capability section rather than producing the required source.

**Failure path:** a deterministic foundation contains the approved values, but the route model receives only a type-level API and a long ID inventory. For repeated arrays, each field must be emitted as a separate literal lookup. The model can interpret the absence of materialized values as an inability to complete, return `cannot_complete`, exhaust one repair, and stop the whole pipeline before build.

**Impact:** one model decision on one route batch prevents the entire portfolio from reaching clean build and preview. The host has the approved source but does not have a deterministic renderer or an intermediate representation that can turn the approved content tree into executable bindings.

**Required design decision:** separate creative layout generation from deterministic approved-content binding. The model should choose structure and binding locations; a host compiler should materialize content references and validate coverage, rather than requiring a model to hand-type dozens of literal IDs under a context ceiling.

### CG-006 — Preview promotion validates server reachability, not browser reachability, and the frontend has no iframe failure state

**Priority:** P1 — confirmed delivery-contract gap; directly affects “generated but not previewable.”

**Evidence:**

- `src/oryxenai/preview/promotion.py:377-401` performs public readback from the worker/server.
- `src/oryxenai/preview/promotion.py:403-416` returns a URL assembled from the configured base URL.
- `frontend/src/stages/generation/GenerationStage.tsx:147` chooses the active or candidate URL, and `:602-609` renders it directly in an iframe.
- The iframe has no `onLoad`, `onError`, timeout, origin check, or “preview gateway unreachable/CSP blocked” state. The UI can therefore show a blank theater while the state appears `ready`, or show a candidate URL that is not browser-reachable.

**Failure path:** the worker can reach a URL from its network namespace, but the user's browser cannot resolve or access it, or the preview response is blocked by an origin/CSP mismatch. The backend has already accepted the server-side readback, while the frontend only receives a string and renders it.

**Impact:** preview failures are silent and indistinguishable from a still-loading page. The traceability drawer reports generation state but not the browser's actual load failure, response status, CSP failure, or effective origin.

**Required design decision:** treat preview as a three-party contract—worker, gateway, browser. Validate a browser-visible origin during deployment/start admission, return an explicit preview capability/status, and instrument the iframe load/error lifecycle with an actionable diagnostic.

### CG-007 — Build execution is not isolated from concurrent Windows Node/Vite processes

**Priority:** P1 — confirmed live operational failure mode.

**Evidence:**

- `src/oryxenai/agents/code_generator/core/build_runner.py:44` defines `_PACKAGE_INSTALL_LOCK`.
- `src/oryxenai/agents/code_generator/core/build_runner.py:303-311` uses that lock only around the npm install portion; typecheck/build and Vite execution are outside it.
- `src/oryxenai/agents/code_generator/core/build_runner.py:243-263` classifies Vite's `spawn EPERM` as `VITE_NODE_SPAWN_EPERM` after failure, but classification is not isolation.
- The 2026-09-18 live campaign records duplicate/stale processes and concurrent Node/npm activity around this exact failure.

**Failure path:** multiple workers, stale reload processes, or another local Node process share the Windows environment while Vite starts child processes/path-resolution helpers. The build fails before evaluating generated source. The repair budget cannot correct a host process denial.

**Impact:** source-valid portfolios fail nondeterministically at the build gate; retrying may succeed only because the competing process disappeared. This consumes model and worker time while presenting a portfolio-generation failure.

**Required design decision:** give build/verification a process-level execution lane or per-run isolated environment with explicit concurrency limits and graceful worker shutdown. The system should prove/serialize the host-level Vite operation before spending repair attempts.

### CG-008 — Verification enablement is split across configuration but not enforced as one capability gate

**Priority:** P1 — confirmed configuration/control-plane gap.

**Evidence:**

- `config/app.docker.toml:76` sets `[code_generator_verification].enabled = false`.
- `src/oryxenai/agents/code_generator/service.py:110-150` admits a session run based on Build Preparation state and does not check this flag.
- `src/oryxenai/jobs/handlers/code_generator_verification.py:118-276` defines the verification handlers; the handler path does not gate execution on `code_generator_verification.enabled`.
- `src/oryxenai/api/routes/__init__.py:50-54` always includes the production Code Generator router; the `code_generator_development.enabled` switch only controls the separate developer harness route.

**Impact:** operators cannot infer behavior from the overlay. A deployment may say verification is disabled while the authenticated session stage still queues verification, or may expect verification to be available while the selected overlay disables the developer surface. This makes “ready,” “generated,” and “previewable” environment claims unreliable.

**Required design decision:** define one capability gate for production Code Generator execution and make start, worker handlers, readiness, and frontend stage availability consume the same effective capability receipt. A disabled verification path must either be a deliberate terminal mode with an explicit no-preview state or be rejected before any model generation begins.

## Issues deliberately not counted as current release blockers

- The old unconditional frontend Code Generator GET was a real issue, but the current `frontend/src/app/AppShell.tsx:225-330` fetches it only after Build Preparation is approved or a prior generation status exists. It should remain regression-tested, but it is not the primary current preview failure.
- The historical preview-first acceptance behavior was superseded by `DECISIONS.md` D-099. Current verification code keeps source/build/runtime blockers fail-closed; this report does not treat the superseded policy as an active defect.
- The existing `code generator issues.md` contains older fixes and campaign notes. It was not overwritten or merged blindly into this report.

## Recommended fix order

1. Repair the preview origin/network contract and prove browser access in the exact Docker/production topology.
2. Make Build Preparation freshness an atomic admission precondition for Code Generator.
3. Bind worker toolchain readiness and configuration identity to the queued run.
4. Make dependency acquisition and clean verification use one lockfile/install contract.
5. Replace model-owned approved-copy retyping with deterministic host-side content binding.
6. Add browser-side preview diagnostics and isolate/serialize Windows build execution.
7. Unify the verification capability gate across configuration, API, worker, and frontend.

## Audit boundary

This report identifies architecture, system-design, contract, deployment, and reliability issues that can prevent a correct generated portfolio or a user-visible preview. It does not propose or apply code changes, does not claim a live Azure deployment was tested, and does not treat fixture-only success as production proof.
