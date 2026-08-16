# Code Generator Agent

## Current purpose

This package has two deliberately separate surfaces:

- agent.py is the registry-compatible deterministic mock used by the legacy
  generic-agent harness.
- core/ is the live, feature-gated standalone development workflow. It accepts
  only an admitted Build Preparation v3 pack and owns planning,
  resource/dependency admission, progressive source generation, verification,
  and preview promotion.

The standalone workflow is not wired into portfolio sessions and never
auto-chains from Build Preparation. Package-root modules are compatibility
adapters only: implementation belongs in core/, prompts belong in prompts/,
and the checked-in React/Vite scaffold contains source and a real lockfile but
never node_modules.

## Registry mock

The generic CodeGeneratorAgent remains a deterministic mock for the existing
agent registry. It validates a generic request and returns samples/output.json;
it has no model call and does not participate in the standalone workflow.

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
