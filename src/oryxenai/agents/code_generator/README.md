# Code Generator Agent

## Current purpose

This package has two deliberately separate surfaces:

- agent.py is the registry-compatible, model-backed structured planner surface.
- core/ is the live, feature-gated standalone development workflow. It accepts
  only an admitted Build Preparation v3 pack and owns planning,
  resource/dependency admission, progressive source generation, verification,
  and preview promotion.

The standalone workflow is not wired into portfolio sessions and never
auto-chains from Build Preparation. The package-root Python surface is limited
to `__init__.py`, `agent.py`, and `schemas.py`; standalone implementation belongs
in `core/`, prompts belong in `prompts/`, and the checked-in React/Vite scaffold
contains source and a real lockfile but never `node_modules`.

## Registry planner surface

The generic CodeGeneratorAgent validates the planner request and invokes the
same trusted-prompt, strict structured-output planner operation used by the
durable workflow through the provider-neutral ModelClient boundary. It exposes
planning through the shared Agent protocol; it does not orchestrate the
standalone durable jobs.

## Standalone development workflow

The developer workflow accepts only build-preparation-pack-v3 fixture or upload
ZIPs. It records an independent durable run and event stream, validates a typed
SitePlan plus WorkGraph, reconciles resources and dependencies through trusted
receipt-backed adapters, then generates a React/Vite/TypeScript workspace in
foundation, route-batch, composition, and integration units.

Every model operation receives its trusted prompt separately from one canonical
untrusted JSON payload, uses a strict response schema, and leaves a prompt
receipt. The planner must produce concrete creative, visual, responsive,
accessibility, interaction, component, resource, and acceptance contracts;
empty design prose is rejected before source generation.

Generation owns immutable source checkpoints. Final verification recreates the
toolchain cleanly, performs source/build/DOM-runtime gates, uses only bounded
repair, and atomically promotes an immutable preview receipt. A configured
package manager must create the lockfile and installation: the workflow never
synthesizes package locks or node_modules.

When enabled, use the standalone developer page at /code-generator-development.
Its readiness panel reports only non-secret prerequisites; it does not claim a
model or local toolchain is usable until configuration actually supports it.

## Non-responsibilities

- Does not perform Discovery, Content Architect, or Visual Design Director work.
- Does not read portfolio-session state or automatically chain any stage.
- Does not let a model use shell, filesystem, browser, package-manager,
  storage, deployment, or arbitrary network tools.
- Does not use screenshots, visual scoring, vision-model input, or a fake
  package installation to promote a portfolio.
