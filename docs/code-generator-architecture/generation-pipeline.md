# Code Generator generation pipeline

## Normative implementation contract

This document is the detailed handoff for implementing D-013 and D-015. The
short overview is [README.md](README.md). If this document conflicts with the
active decision, the decision wins.

The implementation target is one durable Code Generator stage that creates a
React/Vite/TypeScript static portfolio. It is progressive rather than one-shot:
plan, acquire, generate foundation, compile, generate route batches, compile,
integrate, build, smoke-test, repair, and promote.

The pipeline is entirely text-and-code driven. It must not:

- request or require a vision-capable model;
- capture, store, compare, or review screenshots or animation frames;
- send image bytes or rendered pages to a model;
- use a pixel score or subjective visual-review gate; or
- give a model unrestricted shell, filesystem, browser, network, npm, storage,
  or deployment tools.

Images and fonts may still be used by the generated portfolio. Trusted code
validates their files and metadata; a text model may reason over provider
metadata, descriptions, tags, dimensions, licence, and intended placement, but
never image pixels.

## 1. Input contract and authority

### Required admitted pack

The sole production input is an immutable Build Preparation pack with the
supported v2 semantic schema. A representative layout is:

```text
manifest.json
handoff-report.json
site/
  contract.json
  routes/
    <route-storage-key>/
      brief.md
      data.json
design/
  visual-direction.json
resources/
  plan.json
  manifest.json
  images/...
  components/...
  icons/...
provenance/
  approvals.json
  sources.json
target/
  target-contract.json
```

The exact pack schema, target schema, and supported versions live in code and
configuration. Code Generator never infers support from filenames alone.

### Admission sequence

Trusted deterministic code performs admission before any model call:

1. download the immutable object named by current Build Preparation state;
2. verify object metadata, total hash, size ceiling, and expiry;
3. copy it to a generation-specific immutable input key and read it back;
4. extract into a new read-only directory with traversal, symlink, device-name,
   control-character, case-collision, duplicate, and size protections;
5. verify every manifest path, byte size, media type, and file hash;
6. validate the handoff report, pack schema, target schema, approval hashes,
   route equality, provenance, licence fields, and resource references;
7. re-read current session revision and approved upstream hashes; and
8. persist `InputReceipt`.

No partial, historical, stale, locally guessed, or v1 pack is silently adapted.
Admission failure creates a safe terminal issue without a model call.

### Authority order

When two fields disagree, the lower item may not override the higher:

1. checked-in security/orchestration policy and supported-runtime profile;
2. canonical Content Architect facts, public content, route graph, and
   acceptance criteria in `site/contract.json`;
3. approved Visual Design Director direction in
   `design/visual-direction.json`;
4. Build Preparation provenance, resource bindings, fallbacks, and target
   constraints;
5. validated `SitePlan` and later `PlanDelta` records;
6. builder or repairer proposals.

Code Generator may elaborate implementation and add resources inside declared
creative freedom. It may not change public truth, publication scope, route
identity, user-media meaning, negative concepts, forbidden subjects, or target
security.

### InputReceipt

```text
InputReceipt
  schema_version
  generation_id
  session_id
  source_object
    key
    version_or_etag
    size
    sha256
  immutable_copy
    key
    version_or_etag
    size
    sha256
  pack_schema
  target_schema
  handoff_report_hash
  site_contract_hash
  visual_direction_hash
  resource_manifest_hash
  approval_hashes
  canonical_route_ids[]
  admitted_file_manifest_hash
  admitted_at
```

All later model requests, acquisition receipts, checkpoints, diagnostics,
builds, and promotions bind this receipt hash.

## 2. One stage, narrow operation roles

The Code Generator is one explicitly started business stage. Its internal roles
are configured operation profiles, not independently persisted agents and not a
supervisor hierarchy.

| Profile key | Receives | Produces |
| --- | --- | --- |
| `code_generator_planner` | authoritative contracts, admitted resource summary, target public API | `SitePlan`, `WorkGraph` |
| `code_generator_resource_scout` | plan need, existing bindings, textual provider metadata | `ResourceRequest[]` or candidate selection |
| `code_generator_foundation_builder` | global plan, shared resources, scaffold API, owned paths | `GenerationResult` |
| `code_generator_route_builder` | route-batch plan/data, shared signatures, bindings, owned paths | `GenerationResult` |
| `code_generator_integrator` | plan, manifests, route summaries, selected source slices | `IntegrationResult` |
| `code_generator_repairer` | `DiagnosticBundle`, affected source, plan/binding slice, owned paths | `GenerationResult` |

Profiles may map to the same configured model. All require native strict
structured text output and a verified output ceiling appropriate to their
operation. None requires image input.

The provider-neutral adapter returns typed outcomes for success, refusal, empty
output, truncation, schema violation, transport failure, and provider failure.
It records safe request identity, usage, finish state, latency, role/profile,
schema hash, and response ID where available. It never persists reasoning
content or depends on provider conversation state.

## 3. Durable execution graph

### Jobs

One attempt uses three registered durable jobs:

| Job | Responsibilities | Durable completion |
| --- | --- | --- |
| `code_generator.plan` | admit pack, plan site/work, resolve initial resource and dependency needs | input, plan, work graph, initial ledgers |
| `code_generator.generate` | create scaffold, execute foundation and route units, resolve emergent needs, integrate, progressively repair | complete accepted source checkpoint |
| `code_generator.verify_and_preview` | clean install, final gates, eligible repair, artifact upload/read-back, promotion | active preview or terminal report |

An acquisition action is a receipt-driven substep inside the job that owns the
request. It is not a new business-stage call and cannot auto-chain another
OryxenAI agent.

### Work-unit state

Every generation work unit follows:

```text
pending
  -> context_ready
  -> model_requested
  -> needs_resources | needs_dependencies | changes_proposed
  -> request_resolved -> context_ready
  -> changes_validated
  -> source_checked
  -> checkpointed
```

Terminal unit states are `failed_input`, `failed_policy`,
`failed_capability`, `failed_generation`, and `superseded`.

A durable work-unit key includes generation, input, plan, work-graph, operation,
profile, prompt, context, ownership, prior-checkpoint, and request-round hashes.
At-least-once redelivery reuses the exact accepted response, resource receipt,
dependency receipt, repair receipt, or checkpoint. It never repeats a completed
side effect.

### Attempt state

`current_attempt` stores:

- input, plan, work graph, resource ledger, and dependency ledger hashes;
- active job, phase, work unit, and request/repair round;
- immutable source checkpoints and accepted call receipts;
- safe progress events and normalized diagnostics;
- configured acquisition and repair budget consumption;
- final source/build/verification/promotion identities; and
- a terminal report when applicable.

`active_preview` remains separate and immutable throughout a new attempt.
`pending_promotion` exists only after the final candidate passes.

## 4. Planning contracts

### SitePlan

The planner emits strict structured data:

```text
SitePlan
  schema_version
  based_on_input_receipt
  creative_thesis
    narrative
    visual_principles[]
    distinctive_moves[]
      move_id
      criterion_ids[]
      source_expectation
    forbidden_generic_moves[]
  visual_system
    color_tokens
    typography_intent
    spacing_scale
    surface_rules
    layout_grammar
    responsive_rules[]
    motion_rules[]
    reduced_motion_rule
  shell
    navigation
    global_regions[]
    shared_interactions[]
  routes[]
    route_id
    path
    storage_key
    purpose
    section_order[]
    content_bindings[]
    fact_ids[]
    criterion_ids[]
    composition
    responsive_behavior
    interaction_ids[]
    planned_resource_slots[]
    owned_paths[]
  shared_component_contracts[]
    component_id
    export_name
    purpose
    props_contract
    owner_path
  interactions[]
    interaction_id
    route_id
    accessible_name
    trigger
    expected_outcome
    target
  resource_inventory[]
  acceptance_coverage[]
```

Deterministic validation requires:

- exact route equality with the site contract;
- known route, section, fact, criterion, scene, and approved resource IDs;
- complete public content/fact/criterion coverage;
- one root route and valid normalized paths/storage keys;
- disjoint owned paths;
- explicit mobile/narrow and desktop/wide behavior for composition that changes;
- a reduced-motion outcome for every planned nonessential motion;
- an expected outcome for every interactive-looking control;
- a source expectation for every distinctive move; and
- no fixed fact or binding invented from prose.

### WorkGraph

```text
WorkGraph
  schema_version
  based_on_site_plan
  units[]
    work_unit_id
    kind                  # foundation | route_batch | route_compose | integrate
    route_ids[]
    section_ids[]
    depends_on[]
    owned_paths[]
    required_shared_exports[]
    resource_slot_ids[]
    criterion_ids[]
    context_estimate
    output_estimate
  terminal_integration_unit
```

Trusted code constructs or validates the graph from the plan:

- exactly one foundation unit exists;
- route coverage is exact with no lost or duplicate section;
- dependencies are acyclic;
- concurrent units have disjoint ownership;
- integration depends on all source-producing units;
- batching respects configured context/output/work-unit ceilings; and
- content is never truncated merely to fit a call.

For a small single-route site, foundation and route work may be combined only
when configured estimators prove the combined context and output fit. For a
large route, contiguous section groups own separate directories and one
route-compose unit owns only the route entry/layout.

## 5. Resource and dependency contracts

### Why Code Generator can acquire

Build Preparation supplies the best known resource set before code exists. Code
Generator has two additional acquisition triggers:

1. **Initial gap:** the planner/resource scout identifies a concrete planned
   placement that the pack's resources and fallbacks cannot serve well.
2. **Emergent need:** a builder, integrator, compiler diagnostic, or repair
   operation discovers a concrete need while source exists.

No quota forces acquisition. A text-led site may need no image or custom font.
A rich site may need several resources. The plan and placement justify the
request.

### ResourceRequest

```text
ResourceRequest
  schema_version
  request_id
  based_on
    input_receipt
    site_plan
    current_checkpoint?
  origin
    phase
    work_unit_id
    role
    origin_kind          # initial_gap | emergent_generation | diagnostic_repair
  category               # image | texture | font | icon | illustration |
                         # component_source | style_primitive
  placement
    route_id?
    section_id?
    scene_id?
    component_id?
    purpose
  why_existing_is_insufficient
  query
    positive_terms[]
    negative_terms[]
    forbidden_subjects[]
  technical_constraints
    media_types[]
    minimum_dimensions?
    aspect_ratio?
    max_bytes?
    font_weights?
    required_exports?
  source_constraints
    allowed_source_kinds[]
    upstream_source_policy?
    attribution_allowed
    vendoring_required
  requiredness            # required | preferred
  fallback
    kind
    implementation
  affected_work_unit_ids[]
```

The model cannot provide an arbitrary fetch URL, command, package version, or
credential. A request is search intent, not authority.

Trusted validation rejects:

- a placement, route, section, scene, or component unknown to the plan;
- a request with no concrete use;
- stock substitution for approved user media;
- material that would imply an unapproved personal/project fact;
- forbidden or negative subjects;
- a category/source combination disallowed by policy;
- duplicate requests already satisfied by the ledger;
- requirements outside target/runtime capability; and
- request rounds beyond configured ceilings.

### Candidate discovery and selection

Each category has configured adapters. Adapters expose normalized textual
metadata and never make their raw client available to a model.

```text
ResourceCandidate
  candidate_id
  provider_key
  provider_resource_id
  category
  title
  description
  tags[]
  technical_metadata
  canonical_source
  licence
  attribution
  vendoring_policy
  dependency_metadata?
```

Trusted policy filters candidates first. The resource-scout profile may rank
the remaining candidates using only the request and textual metadata. Trusted
code then verifies and materializes the selected candidate.

There is no semantic pixel review. For bitmap/vector files, deterministic
inspection is limited to actual bytes: response type, magic bytes, decode,
dimensions, animation policy, metadata stripping, decompression limits,
sanitization, and content hash.

### Category behavior

**Images, textures, and illustrations**

- Prefer pack-provided resources when suitable.
- Query configured providers using positive/negative terms and placement
  constraints.
- Download only when provider licence and vendoring terms permit it.
- Store content-addressed local files with attribution/licence records.
- If a provider requires runtime hotlinking, reject it for the local-only target
  and try another provider or fallback.
- Never label decorative stock as the user's real project output or evidence.

**Fonts**

- Prefer an admitted local font or configured system stack.
- A fetched font requires a licence allowing local web embedding.
- Materialize only required formats/weights within configured size ceilings.
- Trusted code writes the local font manifest and licence record; the foundation
  builder may author token values and class usage but not invent font files.
- Failure falls back to the declared system stack without blocking unless the
  approved direction explicitly made that font resource required.

**Icons**

- Prefer the supported local icon library or admitted SVG source.
- Sanitize fetched SVG and reject scripts, event attributes, external
  references, embedded raster data outside policy, and unsafe XML.
- Decorative icons are hidden from accessibility APIs; meaningful icons require
  an accessible label through component usage.

**Component source**

- Search configured source registries, not arbitrary web pages.
- Fetch source, metadata, licence, file tree, and dependency declarations.
- Sanitize paths and source policy before vendoring under
  `src/components/vendor/<resource-key>/`.
- Adaptation is allowed; provenance and the original licence remain recorded.
- Registry install commands are never executed directly.

**Style primitives**

- Accept only structured/source-level resources from configured catalogues:
  patterns, effects, token presets, or small CSS/TS helpers with a clear
  licence.
- Do not copy whole sites, scrape arbitrary CSS, or treat a reference image as
  source.
- The integrator must map the primitive to an approved visual principle and
  remove unused vendor code.

### ResourceReceipt and ledger

```text
ResourceReceipt
  schema_version
  request_hash
  disposition            # admitted | fallback | rejected
  selected_candidate_id?
  provider_key?
  canonical_source?
  licence
  attribution
  original_hash?
  materialized_files[]
    local_path
    media_type
    size
    sha256
    inspection
  dependencies[]
  satisfied_placements[]
  fallback?
  policy_version
  acquired_at

ResourceLedger
  schema_version
  based_on_input_and_plan
  receipts[]
  active_bindings[]
    binding_id
    request_id_or_pack_need_id
    local_paths[]
    placement_ids[]
    disposition
  ledger_hash
```

The same canonical request under the same provider result snapshot reuses its
receipt. Different bytes for an already accepted content-addressed identity are
a terminal provider/integrity conflict.

### DependencyRequest

Only component/style resources may justify a new package dependency:

```text
DependencyRequest
  schema_version
  request_id
  requesting_resource_receipt
  package_name
  required_api_or_exports[]
  compatibility_constraints
  reason_existing_stack_is_insufficient
  fallback_component_strategy
```

The model may name an API need, but trusted dependency policy decides whether a
package is supported and which configured compatible version is used.

### DependencyReceipt

```text
DependencyReceipt
  schema_version
  based_on
    toolchain_profile
    scaffold_manifest_hash
    prior_manifest_hash
    prior_lock_hash
    resource_receipt_hash
  decision               # admitted | existing | rejected_fallback
  package_name?
  resolved_version?
  transitive_summary?
  licence_result
  vulnerability_policy_result
  install_script_result
  manifest_hash
  lock_hash
  cache_receipt?
  fallback?
```

Package policy rejects unconfigured registries, unsupported packages/versions,
git/path/URL dependencies, lifecycle scripts outside policy, native compilation
outside the supported toolchain, licence failures, dependency confusion,
resolution drift, and target incompatibility.

## 6. Generation response and emergent-request protocol

### Tagged GenerationResult

Every builder/repairer response uses one of three mutually exclusive modes:

```text
GenerationResult
  schema_version
  operation_id
  based_on_context_receipt
  mode                    # changes | requests | cannot_complete

  changes?                # present only when mode=changes
    files[]
      path
      operation           # create | replace
      complete_utf8_content
    exported_signatures[]
    content_coverage[]
    criterion_coverage[]
    resource_usage[]
    interaction_coverage[]
    self_check

  requests?               # present only when mode=requests
    resource_requests[]
    dependency_requests[]

  cannot_complete?        # present only when mode=cannot_complete
    code
    safe_reason
    missing_authority_or_capability
```

A response cannot mix file changes and requests. This prevents partial source
from referencing a resource that has not yet been admitted.

### Emergent request algorithm

For `mode=requests`, trusted orchestration:

1. validates every request against the current plan, ownership, ledger, policy,
   and configured request budget;
2. de-duplicates it by canonical request hash;
3. acquires or selects fallback through the adapter path;
4. resolves any component dependency through the dependency manager;
5. writes immutable resource/dependency receipts;
6. creates a validated `PlanDelta` limited to bindings, placement details, and
   affected work-unit context;
7. invalidates no completed work outside the recorded affected set;
8. rebuilds the same operation context from the same prior source checkpoint
   plus the new receipts; and
9. reruns the operation under a new durable idempotency key.

`PlanDelta` cannot change facts, routes, section order, approved direction, or
path ownership except to add a generated vendor-resource path owned by trusted
code. A resource request that would require such a change is rejected.

If acquisition fails:

- a preferred request uses its declared fallback and resumes;
- a required generator-originated request may be simplified to an honest local
  implementation if the plan allows;
- an upstream-required need with no honest fallback exits with owner and next
  action; and
- transport/provider failure follows durable job retry policy before fallback
  or terminal classification.

## 7. Prompt and context assembly

Every model request is reconstructed from immutable artifacts. It contains, in
order:

1. checked-in trusted system policy;
2. a checked-in operation contract naming role, output schema, owned paths,
   forbidden authority, completion conditions, and immutable hashes;
3. a canonical delimited untrusted data projection;
4. trusted scaffold public APIs/signatures relevant to the operation;
5. active resource/dependency bindings relevant to the placement;
6. for repair only, a normalized `DiagnosticBundle` and bounded source slices;
7. an output self-check represented as structured fields, not hidden reasoning.

The context builder records:

```text
ContextReceipt
  schema_version
  operation_id
  role_profile
  prompt_versions
  output_schema_hash
  ordered_input_hashes[]
  owned_paths[]
  context_hash
  context_estimate
  output_ceiling
  created_at
```

Calls never receive previous chat transcripts, provider response chains,
unrelated routes, raw source documents, credentials, arbitrary provider URLs,
full object-store paths, inspiration corpora, or screenshots.

### Context by operation

| Operation | Context |
| --- | --- |
| plan | site contract, visual direction, resource summary, target public contract |
| initial resource scout | planned slot, current bindings/fallbacks, source policy |
| foundation | global plan, shell/shared contracts, shared resources, trusted APIs, owned paths |
| route batch | route/section plan, public data, shared signatures, route resources, owned paths |
| candidate selection | request plus policy-filtered textual candidate metadata |
| integration | plan, coverage/manifests, route summaries, selected source slices, ledgers |
| repair | diagnostic bundle, affected plan slice, dependencies/resources, implicated source and signatures |

## 8. Isolated workspace and generated repository

### Workspace tree

```text
generation-workspace/
  input/                              # read-only admitted pack
  ledger/
    input-receipt.json
    site-plan.json
    work-graph.json
    plan-deltas/
    resources/
      requests/
      receipts/
      ledger.json
    dependencies/
      requests/
      receipts/
      ledger.json
    contexts/
    calls/
    checkpoints/
    diagnostics/
    repairs/
  repo/
    package.json
    package-lock.json
    index.html
    vite.config.ts
    tsconfig.json
    tsconfig.app.json
    tsconfig.node.json
    src/
      main.tsx
      app/
        AppRouter.tsx
        ErrorBoundary.tsx
        PreviewBridge.ts
      generated/
        route-registry.ts
        resource-manifest.ts
        content-manifest.ts
        interaction-map.ts
        acceptance-map.ts
      design/
        tokens.css
        fonts.css
        global.css
        motion.css
      components/
        primitives/
        shared/
        vendor/
          <resource-key>/
      routes/
        <route-storage-key>/
          index.tsx
          sections/
          route.css
      content/
        public-data.ts
      types/
        generated-contracts.ts
    public/
      resources/
        images/
        fonts/
        icons/
        other/
      licences/
    tests/
      generated/
        runtime-contract.json
    node_modules/                       # disposable
    dist/                               # disposable until build admitted
  artifacts/
    source-manifest.json
    source.zip
    build-manifest.json
    candidate.zip
    verification-report.json
```

The checked-in scaffold is copied; the worker does not run an interactive
project generator. It begins behaviorally complete and visually neutral, with a
router, error boundary, preview bridge, base reset, public types, security
defaults, and deterministic manifest generation.

### Ownership

| Area | Owner |
| --- | --- |
| package/lock, Vite/TypeScript config, entry HTML | trusted scaffold/dependency manager |
| `src/main.tsx`, `src/app/**`, `src/generated/**`, public data/types | trusted deterministic code |
| local resource bytes, vendor placement, licence files | trusted acquisition/materializer |
| `src/design/**`, shell presentation, shared creative source | foundation builder within declared files |
| `src/routes/<storage-key>/**` | assigned route work unit |
| bounded integration files | integrator |
| only diagnostic `allowed_paths` | repairer |
| source/build manifests, commands, `dist`, promotion | trusted deterministic code |

The model never owns configuration, manifests, lockfiles, generated registries,
resource bytes, licences, or runtime/promotion code.

### File-change admission

For every proposed change, the assembler requires:

- normalized UTF-8 source;
- create/replace only inside the operation's exact ownership set;
- no traversal, absolute/device path, hidden metadata, case collision,
  duplicate, symlink, or disallowed extension;
- configured per-file and response size ceilings;
- matching context/prior-checkpoint hashes;
- imports limited to owned source, trusted aliases, local resources, and the
  dependency ledger;
- facts/content drawn only from admitted public data;
- no TODO, lorem ipsum, placeholder link, fake success, missing interaction
  outcome, or undeclared remote reference; and
- complete coverage/self-check fields.

The whole change set is applied to an isolated copy of the prior checkpoint.
Any rejection discards the copy. Accepted files are formatted by trusted
tooling, manifests are regenerated, cheap checks run, and only then is a new
immutable source checkpoint stored.

## 9. React/Vite dependency and `node_modules` lifecycle

### Base scaffold case

The supported-runtime profile selects a checked-in scaffold manifest, lockfile,
toolchain image, package-manager behavior, commands, dependency cache, and
public APIs. A normal generation copies those files unchanged and creates
`node_modules` from the frozen lockfile in the isolated workspace.

### Component uses existing dependencies

The acquisition adapter vendors admitted component source, its licence, and its
resource receipt. Imports must resolve against the existing dependency ledger.
The manifest and lockfile remain unchanged.

### Component needs a supported new dependency

The dependency manager:

1. validates the `DependencyRequest` and requesting resource receipt;
2. selects a version allowed by the configured target/runtime policy;
3. resolves metadata and lock changes in a network-enabled, secret-free
   acquisition subprocess;
4. permits only the configured registry and package graph;
5. disables or rejects lifecycle scripts according to policy;
6. validates the exact manifest/lock diff, licence, resolution, and cache;
7. writes immutable `DependencyReceipt`;
8. discards the old `node_modules`; and
9. recreates it from the new receipt-bound lockfile before source checks resume.

Models never author the manifest/lock diff and never issue install commands.

### Unsupported dependency

Reject the resource or dependency and follow its fallback:

- adapt the component to the existing stack;
- use source-only local implementation;
- use a simpler generated component;
- use CSS/DOM rather than a heavy effect library; or
- abandon a preferred embellishment without losing required content.

A resource must not force the whole portfolio into an incompatible framework or
build system.

### Repair-time dependency request

A repairer may request a dependency only when the diagnostic proves an admitted
component cannot work against the existing stack and the affected plan permits
replacement. The same trusted dependency path applies. Dependency addition is
not accepted merely to avoid fixing straightforward React/TypeScript/CSS.

### What happens to `node_modules`

`node_modules` is:

- always worker-created and generation-local;
- removed/recreated whenever the lockfile or toolchain identity changes;
- excluded from model context except for trusted type/signature summaries;
- excluded from source checkpoints, ZIPs, object storage, logs, preview
  artifacts, and promotion receipts;
- never copied from Build Preparation or a component registry; and
- safe to discard after the attempt.

The package cache may be shared read-only by toolchain/profile identity, but an
installed tree is never reused as durable truth. The final verification creates
a clean installed tree from the exact admitted manifest/lock and configured
cache. Missing cache/dependency material is infrastructure or dependency-policy
work, not a prompt hallucination target.

### Network boundaries

Network is allowed only to trusted configured model, resource, dependency, and
storage adapters in their explicit phases. Build commands receive no provider
credentials and no general outbound network. Generated source may not call
runtime network APIs or reference remote scripts, styles, fonts, images,
iframes, or video. The promoted static portfolio is self-contained.

## 10. Progressive generation and checks

### Foundation

Foundation generation establishes contracts before routes:

- token names and theme variables;
- local typography and font fallbacks;
- global layout/focus/motion/reduced-motion rules;
- shell and navigation presentation;
- shared component signatures; and
- interaction helpers permitted by target policy.

After assembly, run configured parse/import/source checks plus TypeScript. Fix
foundation failures before route calls start, because every route depends on
these APIs.

### Route batches

A route unit sees only its plan/data/bindings plus frozen shared signatures. It
must produce route source and coverage records together. Run import/source/type
checks after each accepted batch. Disjoint batches may execute in parallel, but
their acceptance/checkpoint updates are serialized against the expected prior
manifest.

### Integration

The integration role operates after all routes type-check. It reviews text and
source structure for:

- visual-contract implementation and distinctive-move coverage;
- appropriate variation between routes;
- consistent tokens, typography, navigation, interaction, and motion;
- correct resource placement and fallbacks;
- responsive/reduced-motion declarations;
- unused or duplicated vendor resources;
- manifest and acceptance completeness; and
- source-level generic fallbacks that contradict the plan.

It may change only declared integration paths. If a broad fix would violate
another unit's ownership, trusted code creates a specific follow-up work unit
instead of granting repository-wide edit authority.

### Clean build

After integration:

1. materialize a clean repo from the current source checkpoint;
2. recreate `node_modules` from the exact dependency receipt;
3. run source/contract checks;
4. run TypeScript;
5. run the configured production Vite build;
6. inspect entry, chunks, local resources, content types, size policy, source
   maps, and per-file hashes; and
7. persist a candidate build manifest.

No development server or hot-reload state is evidence for the final build.

## 11. Text-only diagnostics and repair

### Three blocker groups

1. `source_contract`
2. `type_build_artifact`
3. `dom_runtime`

There is no `visual`, `screenshot`, `frame`, or image-review blocker group.

### Diagnostic normalization

Trusted tooling turns raw output into:

```text
Diagnostic
  diagnostic_id
  group
  code
  severity               # blocking | advisory
  owner
  phase
  work_unit_id?
  route_id?
  interaction_id?
  command?
  normalized_message
  file?
  symbol?
  import_chain[]
  expected
  observed
  relevant_receipt_hashes[]
  fingerprint
```

Normalization removes temporary roots, storage keys, request IDs, timestamps,
UUIDs, volatile line/column noise, ANSI output, and duplicated stack frames.
It retains owned file, symbol/import, route, interaction, error class, and
contract IDs.

### DiagnosticBundle for the LLM

```text
DiagnosticBundle
  schema_version
  based_on_checkpoint
  failed_group
  diagnostics[]
  allowed_paths[]
  affected_plan_slice
  affected_resource_bindings[]
  dependency_signatures[]
  implicated_source_files[]
  bounded_related_source[]
  shared_api_signatures[]
  prior_repair_strategies[]
  required_checks_after_change[]
```

The bundle explains the actual failure, not just "fix the build." Examples:

- full TypeScript error code/message with implicated symbol and relevant type;
- Vite unresolved-import chain with allowed dependency/resource alternatives;
- route path, expected heading/content IDs, and observed DOM text;
- interaction trigger, expected state/URL/focus, and observed result;
- console/page error class and first owned source frame;
- failed local resource URL plus ledger/manifest binding; or
- accessibility rule, accessible name/state, element locator, and expected
  correction.

The repairer gets complete implicated files when they fit, plus only the
necessary dependents and signatures. It does not get an entire repository dump
by default.

### Repair behavior

Repair uses configured finite ceilings:

- request/reissue ceiling per model operation;
- repair rounds per work unit;
- total repair rounds per generation;
- emergent resource/dependency rounds; and
- context/output ceilings.

The first repair is narrowly scoped. If the same fingerprint recurs and budget
remains, the next bundle includes prior strategy plus a wider but still bounded
dependency/source slice and explicitly permits simplification or replacement of
the failing local implementation. Recurrence is recorded; it is not hidden by
temporary path or line-number changes.

After a repair:

1. validate and atomically apply the change set;
2. rerun the cheapest directly affected checks;
3. checkpoint only if those checks pass; and
4. rerun all three final gates before promotion.

Security/ownership escape, fabricated facts, forbidden media substitution,
unsupported target change, arbitrary dependency/network request, stale input,
or missing upstream authority is never repaired by granting more freedom.

### RepairReceipt

```text
RepairReceipt
  schema_version
  generation_id
  diagnostic_fingerprints[]
  strategy_summary
  based_on_checkpoint
  context_receipt
  allowed_paths[]
  resource_or_dependency_receipts[]
  changed_file_hashes[]
  corrected_checkpoint
  checks_rerun[]
  accepted_at
```

The idempotency key includes sorted diagnostic fingerprints, prior checkpoint,
allowed paths, strategy round, and context hash. Redelivery reuses it.

### TerminalFailureReport

When configured progress is exhausted or the issue is not generator-owned:

```text
TerminalFailureReport
  schema_version
  generation_id
  terminal_code
  owner
  phase
  input_plan_source_build_hashes
  diagnostics[]
  fingerprint_occurrences
  resource_dependency_failures[]
  accepted_checkpoint
  repair_receipts[]
  active_preview_preserved
  safe_user_summary
  recommended_next_action
```

Raw prompts, private source data, credentials, reasoning, and unredacted
provider errors are excluded from API responses and logs.

## 12. Final text/DOM/runtime verification

The final three gates are detailed in
[Preview, quality, and evaluation](preview-quality-and-evaluation.md).

The headless runtime verifier serves the production `dist` artifact through the
candidate gateway and records only structured text/DOM/runtime evidence:

- route and final URL;
- expected title, headings, landmark/accessibility tree summaries, and public
  content IDs;
- navigation, back/forward, unknown-route, and declared interaction outcomes;
- focus and accessible state before/after an interaction;
- reduced-motion media-query behavior and content availability;
- horizontal-overflow and element-boundary numeric assertions where configured;
- console/page exceptions and CSP violations; and
- requested local URLs, status/content type, and unexpected outbound requests.

It does not capture pixels. Viewport profiles exist only to exercise responsive
DOM behavior, overflow, interaction availability, and navigation—not to create
visual evidence.

## 13. Promotion and staleness

Promotion uses the crash-safe protocol in
[Live preview and deployment](live-preview-and-deployment.md):

1. upload immutable candidate and reports;
2. read back and verify hashes/types;
3. recheck input/upstream staleness;
4. persist `pending_promotion`;
5. conditionally create/read back the immutable promotion receipt;
6. conditionally replace/read back the stable-host active pointer; and
7. CAS the matching session state into `active_preview`.

Any conflict, corruption, stale input, failed gate, or lost CAS preserves the
previous active preview. Reconciliation resumes only from matching receipts.

## 14. Configuration ownership

Non-secret configuration owns:

- supported pack/target/generator/schema versions;
- role profile mapping and structured-output capabilities;
- work-unit/context/output/concurrency ceilings;
- acquisition categories, provider order, licence/source policies, file/type/
  size limits, and request-round ceilings;
- scaffold/toolchain image, package manager, registry/dependency policy, cache,
  trusted commands, and process limits;
- source/type/build/runtime checks and representative viewport profiles;
- repair/reissue/recurrence ceilings;
- object prefixes, retention, worker kind filters, leases, and timeouts; and
- preview adapter and promotion behavior.

Secrets remain indirect environment references resolved only by their owning
adapter. They never enter prompts, generated repositories, build processes,
reports, previews, or logs.

## 15. Implementation checklist

### Contracts and state

- Add strict schemas/validators for every contract in this document.
- Add Code Generator state transitions, service/repository/API contracts, three
  job handlers, and durable idempotency.
- Persist immutable input, plan, ledger, context, call, checkpoint, build,
  diagnostic, repair, and promotion receipts.
- Preserve `active_preview` independently from `current_attempt`.

### Provider and prompting

- Extend the shared model boundary for native strict structured text outputs.
- Do not add typed image inputs or an image-capability requirement.
- Implement configured role profiles with no provider/model branches.
- Keep trusted policy separate from delimited untrusted pack/source data.
- Reconstruct all prompts from receipts with no conversational memory.

### Resource/dependency acquisition

- Implement typed initial and emergent requests.
- Add configured adapters for locally vendorable images, fonts, icons,
  components, and style primitives.
- Enforce user-media semantics, forbidden subjects, provenance, licences,
  attribution, byte inspection/sanitization, content addressing, and fallback.
- Add trusted component dependency resolution and immutable manifest/lock/cache
  receipts.
- Prove models cannot supply arbitrary URLs/commands or mutate package files.

### Scaffold and source

- Check in a versioned neutral React/Vite/TypeScript scaffold.
- Implement the workspace tree and ownership table.
- Implement atomic tagged `GenerationResult` admission.
- Generate trusted content/resource/route/interaction/acceptance manifests.
- Exclude `node_modules`, `dist`, inputs, ledgers, and secrets from source
  checkpoints.

### Progressive generation

- Implement planner/work graph, foundation, route batches, integration, and
  resumable emergent acquisition.
- Run cheap source/import/type checks at every accepted checkpoint.
- Supply small models with exact shared signatures, owned paths, plan slices,
  bindings, and completion fields.
- Implement normalized diagnostics, widening-but-bounded recurrence context,
  simplification strategy, and finite repair.

### Verification and promotion

- Implement only the three text/code/DOM gates.
- Ensure browser tooling has screenshot/frame capture disabled and emits no
  image artifacts.
- Verify every route and declared interaction with structured assertions.
- Build from a clean receipt-bound dependency install.
- Upload/read back candidates and promote through conditional receipt/pointer
  writes plus session CAS.

### Required negative and recovery tests

- unsafe/stale/corrupt/incomplete pack and route/design/content drift;
- malformed/refused/empty/truncated model output and schema mismatch;
- path/ownership/config/package escape, fabricated fact, placeholder, remote
  runtime reference, and arbitrary resource URL;
- planning-time and emergent image/font/icon/component/style acquisition;
- duplicate request reuse, provider retry, fallback, forbidden media
  substitution, bad licence, malformed image/SVG/font/source, and hash conflict;
- dependency existing/admitted/rejected/repair-time cases and lockfile change
  recreating `node_modules`;
- proof that `node_modules` never enters a checkpoint or artifact;
- single/multi-route work graphs, large-route splitting, restart at every unit,
  disjoint concurrency, and source-check failure before dependent work;
- TypeScript, Vite, asset closure, route, navigation, interaction, focus,
  reduced-motion, console, request, CSP, and accessibility diagnostics;
- recurrence with wider context, simplification fallback, total repair
  exhaustion, and idempotent repair receipt reuse;
- explicit proof of zero screenshot calls/files, zero typed image requests, and
  zero vision-role readiness checks; and
- promotion conflict/crash/staleness plus failed regeneration preserving the
  previous preview.
