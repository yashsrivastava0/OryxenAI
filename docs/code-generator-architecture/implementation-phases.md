# Code Generator — approval-gated implementation phases

## Purpose and authority

This file divides the decided Code Generator architecture into four
implementation phases. It is an execution-control document, not an
implementation and not permission to begin all four phases.

Use it together with:

- [`AGENTS.md`](../../AGENTS.md);
- [`DECISIONS.md`](../../DECISIONS.md), especially D-013 and D-015;
- [Code Generator implementation handoff](README.md);
- [Generation pipeline](generation-pipeline.md);
- [Preview, quality, and evaluation](preview-quality-and-evaluation.md); and
- [Live preview and deployment](live-preview-and-deployment.md).

If this file conflicts with an active decision, the decision wins. If a phase
plan discovers a real architectural conflict, stop and ask the user instead of
silently changing the architecture.

Do not tailor the work to or name a particular model. The implementation must
use the repository's configured provider-neutral boundaries.

## Mandatory plan → approval → implementation workflow

Each phase is a separate user-approved unit of work.

When the user asks to **create a plan for Phase N**:

1. Read this entire file, the documents listed above, the current implementation
   under `src/oryxenai/agents/code_generator/`, `DECISIONS.md`, and the working
   tree.
2. Inspect the exact code and tests that Phase N would touch.
3. Produce a plan for **Phase N only**.
4. Include:
   - current-state findings;
   - exact scope and explicit non-scope;
   - proposed files/modules and responsibilities;
   - schemas, state transitions, jobs, API, frontend, and configuration affected;
   - migration or compatibility work, if any;
   - test cases and final verification commands;
   - risks, assumptions, and decisions that need user confirmation; and
   - the phase completion evidence that will be reported.
5. Do not edit files, install dependencies, make external calls, or implement
   anything while only preparing the plan.
6. End after presenting the plan and wait for explicit user approval.

When the user explicitly approves the Phase N plan:

1. Implement only the approved phase.
2. Preserve unrelated and pre-existing working-tree changes.
3. Do not start, partially scaffold, or "prepare ahead" for Phase N+1 beyond
   interfaces explicitly required by the approved Phase N contract.
4. Run the phase's focused tests throughout implementation.
5. Run all verification commands listed in the approved plan before declaring
   the phase complete.
6. Update documentation and `CHANGES.md` as required by `AGENTS.md`.
7. Report implemented behavior, verification results, remaining known issues,
   and the exact boundary left for the next phase.
8. Stop. The next phase begins only after a new plan request and approval.

If the approved plan must materially change during implementation, pause and
request approval for the changed plan. Do not hide scope expansion inside a
routine fix.

## Temporary development boundary

The four phases develop Code Generator **standalone**. They must not integrate
it with Build Preparation or the main session flow yet.

During development:

- input comes through a `DevelopmentInputAdapter`;
- the adapter accepts either a checked-in privacy-safe pack-v3 fixture or a
  user-uploaded pack-v3 ZIP from the developer frontend;
- Code Generator validates that input through the same admission contract the
  future production adapter will use;
- no Code Generator endpoint calls Build Preparation service/state;
- no Build Preparation approval automatically starts Code Generator;
- no existing Discovery, Content Architect, Visual Design Director, or Build
  Preparation state machine is changed to know about Code Generator;
- the existing deterministic mock remains available wherever current tests or
  generic mock routes still require it, until the later integration task
  explicitly retires it; and
- all standalone routes and mutation paths are protected by an explicit
  development setting and are absent or disabled in production.

The long-term main flow remains:

```text
Discovery
  -> Content Architect
  -> Visual Design Director
  -> Build Preparation
  -> Code Generator
```

Every transition remains explicit. Wiring the final arrow, adding the production
session endpoints, and retiring the temporary input adapter are a **future
integration task outside these four phases**.

The core service must therefore depend on a neutral admitted-input reference,
not on a Build Preparation service object. The future integration should be an
adapter change, not a rewrite of generation.

## Rules shared by all phases

- Do not add screenshot capture, video/frame capture, image comparison, a
  vision-review role, or an image-input requirement.
- A headless browser may later inspect text, DOM, accessibility state, URLs,
  focus, bounding numbers, console errors, and requests only.
- Models return strict structured text and never receive unrestricted shell,
  filesystem, browser, network, package-manager, storage, or promotion tools.
- Only trusted code may fetch resources, mutate package/lock files, execute
  commands, manage workspaces, or promote previews.
- Images, fonts, icons, components, and style resources must be locally
  materialized with provenance and licence receipts. The generated site has no
  runtime dependency on those providers.
- Facts, routes, public content, user-media meaning, forbidden subjects, and
  approved visual direction remain immutable authorities.
- All durable side effects require idempotency keys and reusable receipts.
- `node_modules`, temporary workspaces, and `dist` are disposable. They never
  enter source checkpoints.
- Configuration owns provider/profile selection, versions, ceilings, timeouts,
  paths, and feature flags. Do not hardcode them in business logic or prose.
- Progress events must describe persisted facts. Do not invent percentages,
  stream fake activity, or claim a stage has completed before its receipt exists.
- Normal automated tests use fixtures/mocks. Live provider tests remain
  explicitly opt-in.

## Phase dependency map

```text
Phase 1: standalone spine, admission, planning, frontend shell
    |
    v
Phase 2: controlled resources and dependencies
    |
    v
Phase 3: progressive source generation and integration
    |
    v
Phase 4: final verification, repair, preview, and hardening
    |
    v
Future task: integrate with Build Preparation and the main flow
```

Do not reorder the phases. Later phases depend on durable contracts and receipts
created by earlier phases.

---

## Phase 1 — Standalone spine, admission, planning, and frontend shell

**Status: complete.** The standalone admission/planning spine and its
completion-gate backfill are verified; Phase 2 acquisition is now available as
an explicit follow-up operation.

### Goal

Create a real standalone Code Generator run that can accept a pack-v3
development input, admit it safely, produce a validated `SitePlan` and
`WorkGraph`, persist durable progress, and expose that progress in a dedicated
developer frontend.

Phase 1 does not generate portfolio source or a preview.

### Required implementation scope

#### Core contracts

Implement the Phase 1 subset of the normative schemas and validators:

- admitted input reference;
- `InputReceipt`;
- pack-v3 manifest, site-contract, visual-direction, target, provenance,
  execution contract, resource ledger, recipes, and handoff projections needed
  for admission;
- `SitePlan`;
- `WorkGraph`;
- `ContextReceipt` and planner call receipt;
- safe issue/error envelope;
- progress event;
- `current_attempt` and standalone run projections.

Validate exact route, content, fact, criterion, visual-direction, file-reference,
hash, licence, schema-version, and path safety. Do not duplicate the full raw
pack into database state.

#### Durable standalone run

Add the state machine, repository/service boundary, job registration, and
idempotent `code_generator.plan` handler needed for:

```text
created -> queued -> admitting -> planning -> planned
                                  \-> needs_attention
```

The handler must:

1. resolve the development input;
2. create and read back an immutable input copy;
3. validate and safely extract it;
4. persist `InputReceipt`;
5. call the configured planner through strict structured output;
6. validate `SitePlan` and `WorkGraph`; and
7. persist receipts and truthful progress events.

Worker redelivery must reuse admission and planner receipts.

#### Development input adapter

Provide two safe input modes behind one interface:

- select a checked-in privacy-safe fixture by stable fixture ID; or
- upload a ZIP through the development API with explicit size, type, filename,
  extraction, and archive-safety limits.

Do not accept an arbitrary local/server path, storage URL, or Build Preparation
run ID.

#### Standalone development API

The exact route names may be refined in the approved Phase 1 plan, but the
surface must support:

- create a development run from fixture or upload;
- get the complete safe run projection;
- list or retrieve persisted progress events; and
- retrieve the validated plan/work-graph summary for developer inspection.

These routes must be mounted only when the development feature is enabled.

#### Developer frontend shell

Create a dedicated page, separate from the existing multi-agent harness. Plain
HTML/Jinja, CSS, and browser JavaScript are appropriate; use separate template,
stylesheet, and script files rather than one giant inline file.

Phase 1 UI must provide:

- a clear **New run** area with fixture selection and ZIP upload;
- a start action with validation and useful errors;
- a stage rail showing admission and planning states;
- a live event stream based on persisted backend events;
- input identity, route count, plan/work-unit summaries, and safe issues;
- reconnect/refresh behavior that restores the current run by run ID; and
- a deliberately empty preview panel explaining that preview becomes available
  in Phase 4.

The page should already establish the intended polished product shape:

```text
+--------------------------------------------------------------+
| Run identity | current status | elapsed | primary actions     |
+------------------+---------------------------+---------------+
| Stage rail       | Main workspace            | Activity      |
| - Input          | Plan/work graph summary   | Event stream  |
| - Planning       | Future preview canvas     | Issues        |
| - Resources      |                           | Receipts       |
| - Foundation     |                           |               |
| - Routes         |                           |               |
| - Integration    |                           |               |
| - Build & smoke  |                           |               |
+------------------+---------------------------+---------------+
```

It must be responsive, keyboard usable, readable without raw JSON, and visually
intentional. Collapsible raw JSON may exist as secondary developer detail.
Do not show fake future-stage activity.

### Expected implementation areas

The Phase 1 plan should inspect and likely touch:

- `src/oryxenai/agents/code_generator/`;
- shared model-client strict-output capabilities;
- `src/oryxenai/jobs/` registration/handler code;
- database repository/state support and a migration only if genuinely needed;
- development API routing and app feature flags;
- `src/oryxenai/web/templates/` and `src/oryxenai/web/static/`;
- `config/app*.toml` and `config/models.toml`; and
- unit, API, integration, and worker tests under `tests/`.

Do not assume every listed area needs modification; the Phase 1 planning pass
must inspect first.

### Explicit non-scope

- resource/provider acquisition;
- package dependency changes;
- React/Vite source generation;
- `code_generator.generate`;
- final build, runtime smoke checks, repair, preview serving, or promotion;
- Build Preparation integration or main-flow session routes.

### Phase 1 completion gate

Phase 1 is complete only when automated evidence proves:

- a valid checked-in pack and an uploaded equivalent produce the same admitted
  identity and validated planning shape;
- unsafe, stale, malformed, oversized, unsupported, or contradictory packs fail
  before the planner call;
- planner output is strict, validated, receipt-bound, and idempotently reused;
- worker restart/redelivery resumes without repeating accepted work;
- development routes are unavailable when the feature is disabled;
- the frontend can start a run, poll/restore it, and display persisted events and
  plan summaries; and
- existing agents and their tests remain behaviorally unchanged.

Stop after reporting Phase 1 evidence. Do not begin Phase 2.

---

## Phase 2 — Controlled resource and dependency acquisition

### Goal

Add the trusted resource system that can satisfy both pre-generation gaps and
later emergent requests, while keeping all network/package authority outside the
model.

Phase 2 proves acquisition independently before source generation depends on it.

### Required implementation scope

#### Resource contracts and ledger

Implement and validate:

- `ResourceRequest`;
- normalized `ResourceCandidate`;
- `ResourceReceipt`;
- `ResourceLedger`;
- `PlanDelta` limited to resource bindings;
- `DependencyRequest`;
- `DependencyReceipt`; and
- dependency-ledger identity.

Requests must record their origin, concrete placement, insufficiency reason,
textual query, technical/source constraints, requiredness, fallback, and
affected work units.

#### Trusted adapters

Add configured adapters for the supported categories:

- images/textures/illustrations;
- locally embeddable fonts;
- icons;
- adaptable component source; and
- vetted style primitives.

Reuse safe existing provider primitives where appropriate, but do not call Build
Preparation service/state or alter Build Preparation behavior. Code Generator
must own its validation, request/receipt, policy, and materialization boundary.

Adapters must enforce:

- configured provider/source allowlists;
- positive, negative, and forbidden textual concepts;
- user-media truth and no stock substitution;
- licence, attribution, and vendoring rules;
- byte type, size, decode, decompression, path, and hash limits;
- SVG/source sanitization;
- local content-addressed placement; and
- explicit fallback or terminal classification.

There is no pixel-semantic review. A text operation may select among
policy-filtered candidates using metadata, descriptions, tags, dimensions, and
licence data only.

#### Trusted dependency manager

Implement the explicit cases:

1. resource uses the existing scaffold dependencies;
2. admitted component needs a supported configured dependency;
3. dependency is unsupported and a source/generated fallback is selected; and
4. resolution/provider failure is retried or classified safely.

Only trusted code may update package/lock files. `node_modules` must be
recreated after a lock/toolchain change and excluded from checkpoints,
artifacts, prompts, logs, and object storage.

#### Phase 2 development API and UI

Extend the standalone run so a planned run can execute initial resource
resolution through durable, idempotent work. The frontend must add:

- acquisition stage/status;
- resource-request cards with placement and reason;
- candidate/selection/fallback status;
- provider, licence, attribution, local binding, and dependency summaries;
- warnings and rejected-request explanations; and
- event-stream updates without exposing secrets or signed provider details.

Raw provider responses must not become the primary UI.

### Explicit non-scope

- foundation, route, or integration source generation;
- builder-originated emergent requests (the protocol is implemented now but is
  exercised end to end in Phase 3);
- final build, runtime verifier, repair, preview, or promotion;
- main-flow integration.

### Phase 2 completion gate

Phase 2 is complete only when automated evidence covers:

- a resource-complete pack makes no unnecessary provider call;
- successful image, font, icon, component, and style acquisition;
- preferred-resource failure using an honest fallback;
- required-resource failure producing an actionable issue;
- duplicate request/worker delivery reusing the same receipt;
- forbidden subject and user-media substitution rejection;
- unsafe licence, URL, bytes, SVG, font, archive, component path, and source
  rejection;
- existing, supported-new, and unsupported dependency cases;
- lockfile change recreating `node_modules`;
- proof that `node_modules` never enters a checkpoint/artifact; and
- frontend restoration and truthful display of resource/dependency events.

Stop after reporting Phase 2 evidence. Do not begin Phase 3.

---

## Phase 3 — Progressive source generation and integration

**Status: complete.** The standalone source-generation spine, trusted scaffold,
progressive checkpoints, emergent acquisition, source/type repair, and developer
workflow are implemented and verified. Phase 4 verification and preview are
implemented as a separate durable stage.

### Goal

Generate a complete, locally self-contained React/Vite/TypeScript source tree
through narrow, durable work units: shared foundation, route batches, route
composition where needed, and whole-site integration.

The phase ends with a complete source checkpoint that passes source policy and
TypeScript checks. It does not yet expose a preview.

### Required implementation scope

#### Trusted scaffold and workspace

Add the versioned neutral scaffold and isolated workspace ownership described in
the generation pipeline. Trusted code owns:

- package/lock and toolchain configuration;
- entry/runtime/error-boundary/preview-bridge code;
- route, content, resource, interaction, and acceptance manifests;
- public truth projections;
- local resource bytes and licences; and
- source checkpoint manifests.

Model-owned paths must be explicit and disjoint. The assembler accepts only
complete, normalized, validated `GenerationResult` changes.

#### Generation operations

Implement configured strict-output operations for:

- foundation generation;
- route-batch generation;
- route composition when a large route was split;
- whole-site text/source integration; and
- source/type diagnostic correction required before dependent work advances.

Every call receives only its plan slice, public data, shared signatures,
resource/dependency bindings, owned paths, and relevant prior receipt hashes.

#### Progressive checkpoints

For each work unit:

1. build a deterministic context receipt;
2. invoke or reuse the operation receipt;
3. validate tagged `GenerationResult`;
4. resolve any `mode=requests` resource/dependency request through Phase 2;
5. rerun only the affected operation with receipt-bound local resources;
6. apply changes to an isolated copy of the prior checkpoint;
7. run path/import/source/format/type checks;
8. accept a new immutable checkpoint only when those checks pass; and
9. emit persisted progress events.

Foundation checks must pass before route work begins. A failed route batch
cannot corrupt other completed batches.

#### Emergent resource scenario

Exercise the second required acquisition path end to end:

- a foundation, route, integration, or diagnostic operation discovers a
  justified missing resource;
- the work unit pauses without applying partial files;
- Phase 2 validates/acquires/falls back and records receipts;
- a constrained `PlanDelta` updates bindings only; and
- the same work unit resumes idempotently with the new local binding.

#### Phase 3 frontend

Extend the developer page with:

- active foundation/route/integration work unit;
- completed versus pending route batches;
- accepted checkpoint identity and generated file counts;
- emergent resource pauses/resumptions;
- source/type diagnostics and correction status; and
- a clear "source ready; final build/preview not run" state.

Do not render partial generated work in the preview frame and do not simulate an
editor/token stream.

### Explicit non-scope

- final clean production build as promotion evidence;
- headless DOM/runtime journeys;
- final build/runtime repair;
- candidate artifact upload/read-back;
- preview gateway, stable active pointer, or iframe preview;
- Build Preparation/main-flow integration.

### Phase 3 completion gate

Phase 3 is complete only when automated evidence proves:

- sparse single-route and rich multi-route fixtures produce complete source
  without page/section/component quotas;
- large-route splitting preserves exact section/content/criterion coverage;
- foundation APIs are frozen before route calls and ownership never overlaps;
- unsafe paths, config/package mutation, fabricated facts, placeholders,
  undeclared imports, runtime remote resources, and oversized output fail
  safely;
- an emergent resource request pauses, resolves, resumes, and uses the admitted
  local binding;
- source/type diagnostics can correct an eligible work unit before dependants
  continue;
- restart/redelivery at every work-unit boundary reuses receipts/checkpoints;
- final Phase 3 source passes source-policy and TypeScript checks; and
- source checkpoints contain neither `node_modules` nor `dist`.

Stop after reporting Phase 3 evidence. Do not begin Phase 4.

---

## Phase 4 — Verification, finite repair, stable preview, and hardening

### Goal

Turn the complete source checkpoint into a clean production artifact, verify it
through the three text/code/DOM gates, perform finite diagnostic repair when
eligible, and display the atomically promoted preview in the standalone
developer frontend.

Phase 4 completes the standalone Code Generator. It still does not connect it
to Build Preparation or the main session flow.

### Required implementation scope

#### Clean build and three gates

Implement:

1. source and contract integrity;
2. clean type/build/artifact integrity; and
3. text/DOM/runtime smoke verification.

Recreate `node_modules` from the receipt-bound lock/toolchain state. Build the
production Vite artifact and verify entry/chunk/CSS/resource closure.

The headless runtime verifier must exercise:

- every approved direct route;
- internal navigation edges;
- back/forward and designed unknown-route behavior;
- declared interactions and outcomes;
- expected public content;
- keyboard/focus and accessible-name/state baseline;
- reduced-motion behavior where declared;
- relevant narrow/wide overflow/availability assertions;
- console/page/CSP failures; and
- local asset requests plus absence of outbound runtime requests.

It must not call screenshot/video APIs or create image/frame artifacts.

#### Diagnostic repair

Implement normalized `Diagnostic`, `DiagnosticBundle`, `RepairReceipt`, and
`TerminalFailureReport` behavior for source, type/build/artifact, and DOM/runtime
failures.

Repair must:

- stay inside validated allowed paths;
- receive exact errors, relevant source, plan/resource/dependency context, and
  prior strategies;
- support an emergent resource/dependency request only through Phase 2;
- use configured per-unit and total ceilings;
- widen context or simplify a failing local implementation only while budget
  remains;
- rerun affected checks immediately; and
- rerun all three final gates before promotion.

Security, truth, source-policy, stale-input, ownership, or unsupported-target
violations never gain broader authority through repair.

#### Candidate storage and stable preview

Implement the local/development form of the decided preview protocol:

- immutable candidate and verification artifacts;
- upload/write plus read-back hash verification;
- `pending_promotion`;
- conditional promotion receipt;
- conditional stable active pointer;
- final state compare-and-swap;
- crash reconciliation; and
- retention of the prior active preview during regeneration or failure.

The preview gateway must serve the exact promoted `dist`, apply direct-route SPA
behavior and asset 404 rules, and remain isolated from application secrets and
cookies.

#### Complete developer frontend

Finish the separate frontend as a polished generation control surface. It must
show:

- truthful phase/work-unit progress and live persisted events;
- resource/dependency activity;
- build and verification gate results;
- normalized actionable issues and repair attempts;
- current-versus-previous preview state during regeneration;
- automatic preview activation as soon as promotion completes;
- the real generated portfolio in an isolated iframe;
- route selector derived from the promoted route contract;
- mobile, tablet, desktop, and fit viewport controls;
- refresh and open-in-new-tab actions; and
- clear empty, running, ready, failed, stale, and regenerating states.

The visual design should feel like a purposeful modern generation workspace,
not an unstyled form or a raw JSON dump. Use a coherent spacing/color/type
system, strong status hierarchy, restrained motion with reduced-motion support,
accessible controls, responsive rearrangement, and readable event/resource/
diagnostic cards.

The UI must not:

- show a fake percentage;
- expose an unverified candidate or partially executing workspace;
- claim a preview is ready before promotion;
- replace a working preview when regeneration fails; or
- hide errors behind a generic failure message when safe structured diagnostics
  exist.

#### Final hardening

Complete worker capacity/kind isolation, cancellation/timeouts, subprocess-tree
cleanup, feature-flag enforcement, safe logging, retention/reconciliation, and
end-to-end recovery behavior needed by the standalone stage.

Document the neutral future input-adapter interface and production integration
requirements, but do not wire them.

### Explicit non-scope

- reading Build Preparation state or object references;
- production session `/code-generator` start/regenerate routes;
- automatic chaining;
- public portfolio publishing, custom domains, analytics, or preview history;
- screenshot/vision verification;
- redesigning upstream agents.

### Phase 4 completion gate

Phase 4 is complete only when automated evidence covers:

- clean install and build from a receipt-bound source checkpoint;
- all three gates passing for a privacy-safe multi-route generation;
- direct route, navigation, history, unknown route, interaction, focus,
  reduced-motion, console, request, CSP, asset, and overflow failures;
- precise diagnostic normalization and eligible finite repair;
- repeated/exhausted/non-repairable failure producing one safe terminal report;
- resource/dependency requests made during repair using only the trusted path;
- immutable candidate/report read-back and atomic promotion;
- crash/conflict/staleness recovery at each promotion boundary;
- failed regeneration preserving the prior active preview;
- frontend refresh restoring the run and auto-loading the promoted preview;
- preview route/viewport/refresh/new-tab controls operating on the real artifact;
- development mutation routes disabled outside the development setting;
- no screenshot, video, frame, visual-comparison, typed-image, or vision-review
  operation/artifact in tests, logs, requests, or output trees; and
- the repository's complete lint, formatting, type-check, and test commands
  passing, with any environment-dependent integration prerequisites reported
  precisely.

Stop after reporting Phase 4 evidence. Do not integrate with the main flow.

---

## Future integration task — deliberately not one of the four phases

After all four phases are complete and separately approved, request a new plan
for production integration.

That future plan may:

- implement a `BuildPreparationInputAdapter` that resolves the current eligible
  pack into the same admitted-input reference used by development;
- add the production session GET/start/regenerate routes;
- connect Code Generator state to the existing session without changing
  upstream authority;
- remove or retain the deterministic mock based on compatibility evidence;
- decide whether the standalone development frontend remains feature-gated as a
  diagnostic harness; and
- verify the complete explicit flow from Discovery through Code Generator.

It must not be bundled into Phase 4 merely because the standalone generator is
working.

## Copy-paste requests for future sessions

### Request a phase plan

```text
Read AGENTS.md, DECISIONS.md, and
docs/code-generator-architecture/implementation-phases.md completely.
Create the implementation plan for Phase N only. Inspect the current code and
tests first. Include exact scope, files/modules, contracts/state/jobs/API/UI,
compatibility or migration work, tests, verification commands, risks, and
explicit non-scope. Do not implement or edit any file. Stop after the plan and
wait for my approval.
```

Replace `N` with `1`, `2`, `3`, or `4`.

### Approve implementation

```text
Implement the approved Phase N plan only. Follow
docs/code-generator-architecture/implementation-phases.md, preserve unrelated
working-tree changes, run the approved focused and final verification, update
the required documentation/change log, report concrete evidence, and stop
without beginning Phase N+1.
```

## Phase status

| Phase | Status | Completion evidence |
| --- | --- | --- |
| Phase 1 — standalone spine and planning | complete | `tests/unit/agents/code_generator/`, `tests/integration/test_code_generator_development_worker.py`, `tests/frontend/code_generator_development.test.mjs` |
| Phase 2 — resources and dependencies | complete | `tests/unit/agents/code_generator/`, `tests/integration/test_code_generator_development_worker.py`, `tests/worker/test_code_generator_acquisition_redelivery.py`, `tests/frontend/code_generator_development.test.mjs` |
| Phase 3 — progressive source generation | complete | `tests/unit/agents/code_generator/`, `tests/integration/test_code_generator_generation_worker.py`, `tests/api/test_code_generator_development_routes.py`, `tests/frontend/code_generator_development.test.mjs` |
| Phase 4 — verification and preview | complete | `tests/unit/agents/code_generator/`, `tests/unit/preview/`, `tests/integration/test_code_generator_verification_worker.py`, `tests/api/test_code_generator_development_routes.py`, `tests/frontend/code_generator_development.test.mjs` |
| Future Build Preparation/main-flow integration | deferred | outside this plan |

Only update a phase to `complete` after its approved plan has been implemented
and its completion gate has passed. A plan approval alone does not change
status.
