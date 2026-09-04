# Code Generator Agent

## Current purpose

This package has three deliberately bounded surfaces over one implementation:

- agent.py is the registry-compatible, model-backed structured planner surface.
- service.py and the session API are the explicit production entrypoint. They
  bind one eligible Build Preparation brief pair before durable work is queued.
- core/ is the shared durable generation workflow and the feature-gated
  standalone development harness. It accepts only an admitted Build
  Preparation brief pair and owns planning, resource/dependency admission,
  progressive source generation, verification, and preview promotion.

Code Generator never auto-chains from Build Preparation. A caller starts the
session stage explicitly; the worker reads the exact bound Markdown pair,
validates its fenced JSON indexes, and stores one immutable JSON envelope before
planning. Workflow implementation belongs in `core/`, prompts belong in
`prompts/`, and the checked-in React/Vite scaffold contains source and a real
lockfile but never `node_modules`. Brief resource decisions remain bounded
inputs: Code Generator fetches selected media, fonts, and component references
locally at generation time, while every optional failure has a declared local
fallback. Registry source without a plan-owned destination remains reference
material and is never copied into the generated source tree.

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
  the current Build Preparation brief pair and its hashes, performs the fixed
  provider/toolchain preflight, then queues the first attempt;
- `POST /regenerate` repeats the same gates for a new design variant while
  retaining the previous promoted preview until replacement succeeds;
- `POST /retry` requeues the first incomplete stage on the existing run,
  preserving its design variant, checkpoints, and previously promoted preview.

Model/provider selection comes only from `config/models.toml`; request bodies
cannot override it. The service reads only the approved Build Preparation
projection and brief reference, not raw intake or upstream reasoning. The
immutable envelope records both brief hashes, a contract hash, projection
hashes, and the closed navigation destinations that source verification enforces.

## Durable generation workflow

The session and developer workflows record durable runs and event streams. The
production input is the verified Markdown brief pair; the developer harness
accepts the same pair from a debug mirror, a deterministic fixture, or an uploaded
JSON envelope containing both documents.
Active blueprint runs validate a provider-safe ExperienceBlueprintV4, then
host-compile the typed SitePlan and WorkGraph; legacy runs retain their typed
SitePlan reader. The current brief consumer uses the release-fenced v5 queue
namespace, while v3/v4 rows remain readable for compatibility. Both paths
reconcile resources and dependencies through trusted receipt-backed adapters,
then generate a
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
