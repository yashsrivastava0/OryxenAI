# Code Generator — implementation handoff

**Status:** standalone and explicit production-session workflows implemented.
The v2 production overlay is defined in
[v2-production-architecture.md](v2-production-architecture.md); this file
retains the detailed four-phase implementation contract from D-013/D-015.
Verify runtime completeness in `src/oryxenai/agents/code_generator/`, its
service/job/API wiring, and the test suite.

Code Generator turns one eligible Build Preparation pack into one locally
self-contained React/Vite/TypeScript portfolio and atomically promotes it as the
session's current preview. Reliability comes from progressive generation,
compiler/runtime feedback, durable checkpoints, and controlled resource
acquisition. It does not use a vision model, screenshots, frame capture, image
comparison, or a post-generation visual judge.

## Product outcome

The stage is designed around three outcomes, in this order:

1. **Generate deliberately.** Convert the approved content and visual direction
   into a concrete site plan, acquire any justified missing resources, establish
   the shared visual foundation, generate route batches, and integrate the site
   as a coherent whole.
2. **Stay repairable while advancing.** Validate every accepted checkpoint with
   cheap source and compiler feedback so a small model receives narrow,
   actionable diagnostics before errors spread across the repository.
3. **Promote only a working build.** Require source-contract integrity, a clean
   type check and production build, and text/DOM/runtime smoke tests before
   replacing the current preview.

Visual quality is created during planning, resource selection, foundation
generation, route composition, and the final integration pass. The approved
Visual Design Director contract remains binding, but there is no screenshot or
vision-based acceptance gate. A successful build alone does not make the design
good; the generator prompts and structured plans must carry the design intent
all the way into source.

## Boundary and authority

- The authoritative production input is a fresh, eligible, hash-verified Build
  Preparation pack using the v3 readiness contract defined by D-018.
- Code Generator does not read raw intake, Discovery memory, upstream internal
  notes/reasoning, or arbitrary session fields.
- Content Architect remains authoritative for public facts, content, routes,
  and acceptance criteria. Visual Design Director remains authoritative for
  the approved visual and interaction direction.
- Code Generator may add implementation resources within approved creative
  freedom. It may not invent portfolio facts, replace user media with unrelated
  stock, violate forbidden subjects, change route scope, or contradict approved
  direction.
- Model/provider selection and operation profiles live only in
  [`config/models.toml`](../../config/models.toml). Business logic contains no
  provider or model-name branch.
- Models return strict structured text. They receive no image input and no raw
  shell, filesystem, browser, network, package-manager, storage, or promotion
  tool.
- Trusted Python code owns input admission, workspaces, resource adapters,
  dependency resolution, package/lock files, commands, diagnostics,
  checkpoints, artifact storage, and preview promotion.
- The generated application has no runtime resource fetching. Images, fonts,
  icons, component source, and style resources are materialized locally before
  the final build.
- There is no cross-stage supervisor and no automatic chaining. A caller
  explicitly starts Code Generator after Build Preparation is eligible.

The original standalone sequence remains documented in
[Approval-gated implementation phases](implementation-phases.md). The v2
production overlay now binds the approved Build Preparation package and exact
temporary object to the portfolio session, queues the same durable workflow,
and keeps the developer fixture/upload UI as a separate diagnostic surface.

## Build Preparation pack v3

D-018 requires Build Preparation to provide:

- `site/contract.json`, the exact approved route/content/fact/criterion
  contract;
- `design/visual-direction.json`, the complete approved non-reasoning visual
  contract;
- `execution/contract.json`, the exact slot inventory with a local file,
  approved package binding, typed local recipe, or explicit execution gap for
  every known need;
- `resources/ledger.json`, recipe manifests, locally admitted resources, and
  provenance/licence records;
- target, provenance, licence, and handoff reports; and
- file hashes plus upstream approval/hash identity.

Code Generator rejects a stale, corrupt, unsafe, contradictory, incomplete, or
unsupported pack before a model call. It does not reconstruct authoritative
facts or routes from prose.

Known resource requirements are prepared upstream. Code Generator receives the
fixed v3 bindings rather than vague fallback prose or the provider catalogue.
Required visual slots must be concrete local media, importable local component
source, or an admitted package binding; a recipe or comment marker cannot
satisfy a required visual slot.
Only an unexpected need discovered during source generation can invoke D-015's
separate receipt-bound acquisition path.

## Generation roles

The roles below are operation profiles inside one durable Code Generator stage,
not separately started business agents. Multiple roles may use the same
configured model.

| Role | Main responsibility | Output |
| --- | --- | --- |
| **planner** | Convert the admitted contracts into one implementable composition and work graph | `SitePlan`, `WorkGraph` |
| **resource scout** | Find resource gaps and express constrained search intent | `ResourceRequest[]` |
| **foundation builder** | Create tokens, typography, shared APIs, and shared creative components around the trusted shell | `GenerationResult` |
| **route builder** | Implement one deterministic batch of routes/sections against frozen shared contracts | `GenerationResult` |
| **integrator** | Reconcile route composition, shared behavior, design-system use, and manifest coverage | `IntegrationResult` |
| **repairer** | Correct source from compiler/build/DOM diagnostics within explicit path ownership | `GenerationResult` |

No reviewer role receives rendered images. The integrator reviews contracts,
source, manifests, and diagnostic summaries as text.

## End-to-end pipeline

```text
eligible pack v3
  -> admit + create isolated workspace
  -> plan site + work graph
  -> initial resource reconnaissance
  -> trusted acquisition/dependency resolution
  -> generate and check shared foundation
  -> generate and check route batches
       -> acquire justified emergent resources when requested
  -> integrate the complete site
  -> clean install + typecheck + production build
  -> text/DOM/runtime smoke checks
  -> compiler-guided repair when eligible
  -> atomically promote one current preview
```

Every arrow persists a receipt. Every accepted source step creates an immutable
checkpoint. A worker restart reconstructs the next operation from receipts; it
does not replay successful model calls or trust process-local memory.

### 1. Admit and create the workspace

Trusted code downloads the immutable pack, verifies object and file hashes,
validates handoff eligibility and staleness, safely extracts it into a read-only
input area, and fingerprints the complete input. It then copies a versioned
neutral scaffold into a generation-specific workspace.

No input data can grant tools or change checked-in policy. No model call occurs
until admission succeeds.

### 2. Plan the site and work graph

The planner produces:

- one creative thesis tied to approved visual criteria;
- global tokens and typography intent;
- route/section composition and responsive behavior;
- shared component and interaction contracts;
- exact content, fact, asset, and acceptance mappings;
- an initial resource inventory;
- disjoint source ownership; and
- a dependency-ordered `WorkGraph`.

The work graph uses meaningful batches, not one call per page or section and not
one whole-repository response. A large route may be split into section groups
with one later route-composition unit. All route and content coverage comes from
the authoritative site contract.

### 3. Resolve initial resource gaps

The resource scout compares the plan with the pack's admitted resources. It may
request a local image, font, icon, component source, or vetted style resource
when the existing pack or fallback cannot support the intended composition.

Trusted adapters search configured sources, inspect metadata, enforce policy and
licence rules, verify file type/size/decode safety, sanitize source resources,
hash accepted bytes, and materialize them in the workspace. The resulting
`ResourceLedger` is immutable input to builders.

### 4. Generate the shared foundation

The foundation builder receives only the global plan, relevant approved data,
resolved shared resources, trusted scaffold API, and its owned paths. It creates:

- design tokens and local font declarations;
- global layout, focus, motion, and reduced-motion rules;
- the site shell and navigation presentation;
- shared creative components and their typed public APIs; and
- shared styles used by multiple routes.

The assembler validates paths, imports, ownership, facts, resource references,
and placeholders before accepting the change set. It then runs the configured
cheap source checks and TypeScript check. Eligible failures go immediately to a
narrow repair operation before route generation starts.

### 5. Generate route batches

Each route batch receives the frozen plan slice, route content/data, shared
signatures, locally bound resources, and exclusive owned paths. It emits
complete files plus coverage and resource-use manifests.

After a batch is assembled, its imports and types are checked against the current
checkpoint. Disjoint batches may run concurrently only within configured
capacity. A failed batch cannot mutate the prior accepted checkpoint.

### 6. Acquire resources discovered during coding

A foundation, route, integration, or repair result may include typed
`resource_requests`. This supports the second acquisition scenario: a need that
becomes clear only while implementing a specific scene or fixing a real error.

The orchestrator pauses the affected work unit, de-duplicates the request,
validates it against creative freedom and upstream source policy, invokes the
same trusted acquisition path, records a `ResourceReceipt`, applies a
versioned `PlanDelta`, and reruns only the affected operation with the new local
binding.

The model cannot provide an arbitrary URL or command and cannot turn a request
into network access by itself. Failed optional acquisition selects the declared
local fallback. A required request that has no honest fallback becomes an
actionable terminal issue.

### 7. Integrate the site

The integrator receives the plan, source/export manifests, route summaries,
resource/dependency ledgers, and source slices within its owned integration
paths. It checks, as text and structure:

- the creative thesis and distinctive moves are represented in source;
- all routes use the intended shared visual system without becoming identical;
- responsive and reduced-motion contracts are implemented;
- images, typography, components, and style resources have explicit placement;
- navigation and interactions follow the shared API;
- no placeholder or generic fallback displaced required content; and
- every fact, route, criterion, and resource maps to generated source.

It may make a bounded integration change or request a justified resource. It
does not render or inspect screenshots.

### 8. Build, smoke-test, and repair

Trusted commands recreate dependencies from the receipt-bound lockfile, run
source policy checks, type checking, the production Vite build, artifact
closure, and headless runtime checks. The browser runner is text-only: it
collects DOM assertions, URLs, accessible names/states, focus outcomes,
console/page errors, and request/asset failures. Screenshot and frame capture
are disabled and no image is sent to a model.

Eligible failures become a `DiagnosticBundle` containing the failed command or
interaction, normalized error, implicated route/file/symbol, bounded source
excerpts, relevant plan/resource context, and prior attempted strategies. The
repairer returns a scoped change set or a justified resource request. The
configured finite repair budget is shared across the generation and persisted
durably.

### 9. Promote atomically

Only the immutable artifact that passes the three lean gates below enters
`pending_promotion`. Promotion conditionally creates and reads back its receipt,
conditionally replaces the stable-host active pointer, and finally uses session
revision compare-and-swap to update `active_preview`.

A crash-safe reconciler resumes any boundary. A failed or stale regeneration
never clears or replaces the previous preview.

## Resource authority

Code Generator may acquire a resource in exactly two situations:

1. **Pre-generation gap:** planning proves the Build Preparation pack does not
   contain enough suitable material for an approved composition.
2. **Emergent implementation need:** a builder, integrator, compiler diagnostic,
   or repair operation identifies a concrete placement or dependency that could
   not reasonably be known before source existed.

Supported request categories are:

- editorial/decorative images and textures;
- locally packaged web fonts plus licence files;
- icons or illustrations from configured catalogues;
- adaptable component source from configured registries;
- vetted style primitives such as patterns or source-level effects; and
- dependencies required by an admitted component, through the trusted
  dependency manager only.

Every request records origin, intended route/scene/placement, why existing
bindings are insufficient, textual search terms, technical constraints,
forbidden concepts, preferred source kinds, requiredness, fallback, and affected
work units. Every admitted result records provider, canonical source, licence,
attribution, hashes, local paths, inspection/sanitization result, dependencies,
and the request it satisfies.

The stage may add decorative or editorial material within creative freedom, but
it may not present stock media as the user's actual project, workplace, award,
or personal evidence. `approved_user_media` is never silently substituted.

## Three lean acceptance gates

The earlier seven-gate visual-evidence matrix is removed. Promotion has only
three blocking gates:

1. **Source and contract integrity:** safe paths and ownership, resolved
   imports, exact route/fact/content/criterion coverage, valid local resources,
   no placeholders, no forbidden runtime network/secret/dynamic-code behavior,
   and consistent manifests.
2. **Type/build/artifact integrity:** clean dependency installation from the
   frozen lockfile, TypeScript success, production Vite build success, and
   complete entry/chunk/asset closure.
3. **Text/DOM/runtime smoke:** direct load for every declared route, internal
   navigation and unknown-route behavior, declared interaction outcomes,
   keyboard/focus/reduced-motion baseline, expected DOM content, and zero
   blocking console, page, request, or asset errors.

Checks use representative configured viewport profiles only where DOM behavior
or responsive overflow must be exercised. They do not capture pixels, score
visual taste, or compare layouts to images. Automated accessibility checks are
a practical baseline, not a complete accessibility certification.

## Workspace, dependencies, and `node_modules`

The generation workspace is disposable and isolated. Its important layout is:

```text
generation-workspace/
  input/                    # read-only admitted pack
  ledger/                   # plans, requests, receipts, diagnostics, checkpoints
  repo/                     # generated React/Vite/TypeScript source
    package.json            # trusted dependency manager owns
    package-lock.json       # trusted dependency manager owns
    node_modules/           # disposable; never model-authored or checkpointed
    public/resources/       # locally materialized images/fonts/icons
    src/...
    dist/                   # disposable build output until admitted
  artifacts/                # source/build manifests and candidate archive
```

Dependency behavior is explicit:

- If no new dependency is needed, use the scaffold manifest/lock unchanged.
- If fetched component source uses existing dependencies, vendor the source and
  record it without changing the lockfile.
- If an admitted component needs a supported dependency, the trusted dependency
  manager resolves a configured compatible version, writes the manifest and
  lockfile, records a `DependencyReceipt`, and recreates `node_modules`.
- If a dependency is unsupported, unsafe, unlicensed, incompatible, or requires
  install scripts outside policy, reject it and use a source-only or generated
  fallback.
- A model never writes `package.json`, `package-lock.json`, Vite/TypeScript
  configuration, or commands; it only emits a `DependencyRequest`.

`node_modules` is never copied from Build Preparation, returned by a model,
stored in object checkpoints, placed in the source ZIP, or promoted with the
static site. It is recreated in an isolated process whenever the lockfile or
toolchain receipt changes. Acquisition may use configured network adapters;
the final clean install/build uses the frozen receipts and configured cache with
no general outbound network.

The exact scaffold, toolchain image digest, Node/npm versions, dependency
policy, provider adapters, limits, commands, and timeouts live in non-secret
configuration and checked-in runtime profiles, not in prompts or this prose.

## Durable jobs and session state

Three registered jobs form one idempotent attempt:

1. `code_generator.plan` admits input, creates the site/work plan, and resolves
   initial resources.
2. `code_generator.generate` advances foundation, route, emergent-resource,
   integration, and progressive-repair checkpoints.
3. `code_generator.verify_and_preview` performs the clean build, text/DOM smoke
   checks, final eligible repairs, artifact storage, and atomic promotion.

An internal acquisition step is receipt-driven work inside the owning job; it
does not start another business agent. Job keys bind session, generation,
input, plan, scaffold/toolchain, operation, and attempt identity.

Session state separates:

- `active_preview`: last promoted build and receipt; retained during all later
  attempts;
- `current_attempt`: active phase, work unit, ledgers, checkpoints,
  diagnostics, repair budget, and terminal report; and
- `pending_promotion`: verified candidate and conditional promotion token,
  never exposed as a user preview.

Expected statuses are `not_started`, `queued`, `planning`, `acquiring`,
`generating_foundation`, `generating_routes`, `integrating`, `building`,
`smoke_testing`, `repairing`, `ready`, and `needs_attention`. `stale` is
computed from current upstream approval and pack identity.

## Public API and preview invariant

The production session routes are:

- `GET /api/v1/sessions/{session_id}/code-generator`
- `POST /api/v1/sessions/{session_id}/code-generator/start`
- `POST /api/v1/sessions/{session_id}/code-generator/regenerate`

There are no revise, approve, retry-step, candidate-preview, history,
alternate-build, or public-hosting endpoints.

Each session has exactly one stable current preview, or none before its first
successful generation. Work in progress is never exposed. A passing
regeneration atomically replaces the current preview; a failing one keeps the
last known-good preview.

## Implemented stages

The historical implementation sequence is recorded in
[implementation-phases.md](implementation-phases.md):

1. standalone spine, admission, planning, and developer-frontend shell;
2. controlled resource and dependency acquisition;
3. progressive source generation and integration; and
4. final verification, finite repair, stable preview, and hardening.

Build Preparation still does not auto-chain. An explicit session start now
binds and verifies its R2 artifact before using these phases through the
production coordinator.

## Required acceptance scenarios

Coverage must demonstrate:

- sparse single-route and rich multi-route packs generate without imposing a
  page, section, card, or component quota;
- a resource-complete pack performs no unnecessary acquisition;
- a planning-time image/font/component gap is fetched, locally materialized,
  attributed, bound, used, and included in the build;
- a route builder can request a justified emergent resource, pause, receive a
  receipt-bound local binding, and resume idempotently;
- disallowed user-media substitution, forbidden subjects, unsafe licences,
  arbitrary URLs, dependency escape, install scripts, and unsupported component
  dependencies are rejected with honest fallbacks;
- manifest/lock changes recreate `node_modules`, while checkpoints and promoted
  artifacts never contain it;
- malformed output, unsafe paths, overlapping ownership, fabricated facts,
  unresolved imports, placeholders, and runtime network calls fail safely;
- source/type errors are repaired before later batches build on them;
- final type/build, route, navigation, interaction, focus, reduced-motion, DOM,
  console, request, and asset failures produce actionable text diagnostics;
- no test creates a screenshot, frame artifact, visual comparison, typed image
  request, or vision-model call;
- worker redelivery reuses model, resource, dependency, checkpoint, repair, and
  promotion receipts; and
- failed regeneration preserves the previous active preview.

## Document map

- [Approval-gated implementation phases](implementation-phases.md) — the four
  separately planned and approved implementation units, temporary standalone
  development boundary, frontend expectations, and completion gates.
- [Generation pipeline](generation-pipeline.md) — normative contracts,
  acquisition flow, work graph, workspace tree, dependency cases, diagnostics,
  and implementation checklist.
- [Preview, quality, and evaluation](preview-quality-and-evaluation.md) — the
  three text-only gates and evidence contract.
- [Live preview and deployment](live-preview-and-deployment.md) — stable preview
  origin, crash-safe promotion, local parity, and explicit deployment boundary.
- [`DECISIONS.md`](../../DECISIONS.md) — D-018 pack-v3 readiness and D-015
  generation/resource decision.
