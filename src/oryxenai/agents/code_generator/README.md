# Code Generator Agent

## Current purpose

This package has three deliberately bounded surfaces over one implementation:

- agent.py is the registry-compatible, model-backed structured planner surface.
- service.py and the session API are the explicit production entrypoint. They
  bind one eligible Build Preparation artifact before durable work is queued.
- core/ is the shared durable generation workflow and the feature-gated
  standalone development harness. It accepts only an admitted Build
  Preparation v3 pack and owns planning, resource/dependency admission,
  progressive source generation, verification, and preview promotion.

Code Generator never auto-chains from Build Preparation. A caller starts the
session stage explicitly; the worker downloads the exact bound object, verifies
its recorded identity, and admits it through the same pack-v3 boundary as the
standalone harness. Workflow implementation belongs in `core/`, prompts belong
in `prompts/`, and the checked-in React/Vite scaffold contains source and a real
lockfile but never `node_modules`. Required visual slots are executable local
bindings: media is served from the prepared pack and component/font source is
imported from the generated resource tree; recipes and comments cannot satisfy
them.

## Registry planner surface

The generic CodeGeneratorAgent validates the planner request and invokes the
same trusted-prompt, strict structured-output planner operation used by the
durable workflow through the provider-neutral ModelClient boundary. It exposes
planning through the shared Agent protocol; it does not orchestrate the
standalone durable jobs.

## Production session API

All routes are under `/api/v1/sessions/{session_id}/code-generator`:

- `GET /` returns the current session projection, active preview, attempt, and
  durable jobs;
- `POST /start` requires an idempotency key and an empty JSON object, verifies
  the current Build Preparation package and object metadata, performs the fixed
  provider/toolchain preflight, then queues the first attempt;
- `POST /regenerate` repeats the same gates for a new attempt while retaining
  the previous promoted preview until replacement succeeds.

Model/provider selection comes only from `config/models.toml`; request bodies
cannot override it. The service reads only the approved Build Preparation
projection and artifact reference, not raw intake or upstream reasoning. The
production R2/object-store path verifies key, ETag, byte length, SHA-256,
expiry, package report, and every ZIP member before extraction.

## Durable generation workflow

The session and developer workflows record durable runs and event streams. The
production input is the verified object-store artifact; the developer harness
accepts build-preparation-pack-v3 fixtures, debug mirrors, or uploaded ZIPs.
Both validate a typed SitePlan and host-compiled WorkGraph, reconcile resources
and dependencies through trusted receipt-backed adapters, then generate a
React/Vite/TypeScript workspace in foundation, route-batch, composition, and
integration units.

Every model operation receives its trusted prompt separately from one canonical
untrusted JSON payload, uses a strict response schema, and leaves a prompt
receipt. The planner must produce concrete creative, visual, responsive,
accessibility, interaction, component, resource, and acceptance contracts;
empty design prose is rejected before source generation.

Generation owns immutable source checkpoints. Production planning first asks a
structured director for exactly two grounded concepts, then compiles a selected
responsive experience blueprint into deterministic, non-overlapping work. A
structured integration review can trigger one owner-scoped polish pass.

Final verification recreates the toolchain cleanly and performs source, build,
and browser gates. Every public route is exercised at configured mobile,
tablet, and desktop viewports, plus reduced-motion mode; geometry, local assets,
routing, navigation, accessibility, console errors, and outbound requests are
checked before an immutable preview receipt is promoted atomically. A configured
package manager must create the lockfile and installation: the workflow never
synthesizes package locks or `node_modules`.

When enabled, use the standalone developer page at /code-generator-development.
Its readiness panel reports only non-secret prerequisites; it does not claim a
model or local toolchain is usable until configuration actually supports it.

## Non-responsibilities

- Does not perform Discovery, Content Architect, or Visual Design Director work.
- Does not read raw portfolio intake or automatically chain any stage.
- Does not let a model use shell, filesystem, browser, package-manager,
  storage, deployment, or arbitrary network tools.
- Does not use screenshots or vision-model input to promote a portfolio; the
  source/resource contract owns design evidence and the browser is a runtime
  smoke check, not a substitute for it.
