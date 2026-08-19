# Code Generator v2 production architecture

This document defines the production session path that consumes one immutable,
eligible Build Preparation pack and produces one verified portfolio preview.
The pack projections, runtime configuration, Pydantic contracts, and receipts
are authoritative; this document explains how those boundaries fit together.

## Outcomes and invariants

Code Generator v2 must:

- consume the exact Build Preparation artifact recorded on the portfolio
  session, whether the backing store is R2 or an injected test store;
- never infer production input from a local mirror, folder recency, or a
  mutable `latest` pointer;
- prove provider reachability with a fixed no-context request before creating
  a durable run, so private portfolio context is not sent into a known-dead
  call;
- use strict structured operations with separate trusted prompts and untrusted
  pack context;
- compile file ownership and execution bindings deterministically rather than
  allowing a model to invent paths, dependencies, or resource identifiers;
- make visual quality observable through an experience blueprint, source
  checks, a whole-site review, clean build, and browser geometry/runtime gates;
- expose only an atomically promoted, verified candidate; and
- retain the previous active preview when regeneration fails or becomes stale.

No route/page count is hardcoded. The approved Content Architect scope in the
pack determines the public routes and sections. A one-route software engineer
portfolio normally remains one public route when that is the approved scope;
Code Generator can create internal layout regions and components but cannot
invent an About, Projects, or Contact page.

## Authority boundary

| Concern | Authority | Code Generator behavior |
| --- | --- | --- |
| Public routes, sections, facts, copy, links, criteria | `site/contract.json` | Preserve exactly; never fabricate or expand scope |
| Visual intent and constraints | `design/visual-direction.json` | Convert into two concepts and one measurable blueprint |
| Known images, components, fonts, icons, recipes | `execution/contract.json` plus resource/provenance projections | Compile exact local/package bindings; do not reacquire |
| Pack identity and expiry | Build Preparation state plus `manifest.json` | Bind run to object key, ETag when present, size, SHA-256, scope, and run id |
| Emergent coding gaps | Code Generator request contracts | Acquire only when no admitted execution binding can satisfy the need |
| File ownership and scheduling | deterministic host compiler | Generate disjoint work units; reject writes outside ownership |
| Model/provider choice | `config/models.toml` and app profile references | Never accept arbitrary request-time provider/model overrides |
| Promotion eligibility | deterministic source/build/browser gates | Promote atomically only after every required gate passes |

Build Preparation local mirrors are diagnostic conveniences. Production reads
the session's `ArtifactReference`, checks object metadata, downloads the bytes
inside the planning worker, verifies size and SHA-256, stores one immutable
workspace copy, and runs the same pack-v3 admission used by local development.

## Explicit session API

The stage is never auto-chained from Build Preparation:

- `GET /api/v1/sessions/{session_id}/code-generator`
- `POST /api/v1/sessions/{session_id}/code-generator/start`
- `POST /api/v1/sessions/{session_id}/code-generator/regenerate`

Start/regenerate requires `Idempotency-Key`. Admission requires Build
Preparation `ready`, `handoff_eligible`, upstream approval verification, zero
execution gaps, a non-expired package, matching package/object identity, object
store `HEAD`, configured credentials, strict-schema capabilities, the package
manager, and the browser runtime.

Provider preflight uses a fixed schema and contains no pack, session, content,
or resource data. Successful transport identities are cached briefly in
process. A preflight failure returns its safe provider code before a run or job
is created.

One `code_generator_runs` record represents a production or development
attempt. Production records add `portfolio_session_id`, the complete Build
Preparation source reference, artifact/preflight receipts, creative direction,
integration review, and a session-scoped idempotency key. Development routes
remain a compatibility harness over the same implementation and tables.

## Structured agent workflow

The coordinator schedules durable stages; it is not a free-running supervisor
and does not expose tools to models.

```text
explicit start
  -> fixed no-context preflight
  -> code_generator.plan
       -> verified artifact download and pack-v3 admission
       -> creative director: exactly two grounded concepts + recommendation
       -> planner: selected concept + ExperienceBlueprintV2
       -> host compiler: execution bindings + disjoint WorkGraph
  -> code_generator.acquire
       -> known pack slots skipped
       -> only justified emergent gaps use trusted adapters
  -> code_generator.generate
       -> foundation
       -> section-bounded route batches
       -> route composition where a route was split
       -> deterministic source audit
       -> structured whole-site review
       -> at most one owner-scoped integration polish pass
  -> code_generator.verify_and_preview
       -> stale-source check
       -> final source contract
       -> clean typecheck/build/artifact closure
       -> browser routes, navigation, assets, accessibility, geometry, reduced motion
       -> finite diagnostic repair when eligible
       -> atomic preview promotion and export
```

All calls use the provider-neutral `ModelClient` boundary. Prompts and output
schemas are version/hash bound in context and call receipts. No operation gets
shell, filesystem, browser, package-manager, object-store, or arbitrary web
tools. The host performs every side effect after validation.

## Experience blueprint

The creative director compares exactly two materially different concepts.
Each concept must make content-specific decisions about hierarchy,
typography, composition, color, motion, available resources, distinctive
moves, and anti-patterns. The planner selects one supplied concept and produces
an `ExperienceBlueprintV2` with:

- one layout region per approved section;
- mobile, tablet, and desktop order/columns/gutters/gaps for every region;
- a bounded content measure and explicit min-height strategy;
- semantic colors, non-uniform spacing, local typography and weights, scale,
  line height, radii, and container width;
- placement/crop/loading/alt policy for every required visual binding;
- purposeful motion beats with duration, easing, target region, and a concrete
  reduced-motion replacement; and
- explicit anti-patterns to prevent generic card grids, arbitrary gradients,
  glass surfaces, floating decoration, uniform centering, and blanket fades.

Semantic validation rejects missing/duplicate section regions, unknown
concepts, unbound typography, missing required visual placements, cross-section
resource placement, and motion that lacks a valid target or reduced-motion
replacement.

## Deterministic work graph and source ownership

The model's `work_graph` and `execution_bindings` are transport placeholders.
After the model call, the compiler replaces them with authority-derived data:

- foundation owns generated token CSS and `SharedSystems`;
- each route batch owns at most the configured section count and its exact TSX
  and CSS files;
- a split route receives one composer that owns only `index.tsx` and
  `route.css` and imports every batch in approved order; and
- one read-only terminal integration unit depends on every prior unit.

Ownership paths never overlap. Batch prompts receive only their assigned
sections and bindings. Composer prompts receive completed dependency source,
so they can wire the route without rewriting approved copy. Final source
coverage evaluates the complete route subtree, while the trusted registry and
route `index.tsx` remain the executable anchor.

## Resource consumption and acquisition

Pack components and fonts are copied into importable
`src/generated/resources/pack/` paths. Pack images remain browser-served local
files and are resolved through the trusted `publicResourceUrl` helper, which
derives the current root or nested preview mount. Acquired TS/TSX/CSS and font
files likewise enter importable source paths; acquired media enters `public/`.
Same-site links use the companion `publicRouteUrl` helper, so routing remains
correct at the origin root and under a session preview mount. Generated sites
make no provider request at runtime.

Every required concrete binding must appear in executable source. A slot id,
comment, manifest entry, or recipe mention does not count. Final validation
checks component imports/use, package exports, image/font path use, licenses,
local import resolution, approved URLs, content anchors, criterion markers,
and interaction markers.

Emergent acquisition is allowed only for a planner/generator need absent from
the pack execution contract. Requests carry route/section/work-owner scope,
why existing material is insufficient, technical/source constraints,
fallback, and the input/plan/checkpoint hashes. Adapters perform real
policy-bounded retrieval and local materialization. Provider failure yields a
safe retry/fallback/needs-attention result; it never authorizes fabricated
bytes or a remote runtime URL.

## Quality and error prevention

Quality is a sequence of enforceable contracts, not a single style prompt:

1. Response schemas reject malformed tagged results and unknown fields.
2. Semantic planning checks exact routes, sections, criteria, interactions,
   blueprint coverage, and executable bindings.
3. Source writes are complete-file, UTF-8, size-bounded, network-free,
   dependency-allowlisted, content-grounded, and ownership-scoped.
4. Each unit runs source/type checks and has a finite diagnostic repair budget.
5. Production sessions receive a read-only whole-site review scoring
   distinctiveness, composition, typography, resource fit, and motion. Every
   accepted score must be at least 4/5. Findings name the owning unit and can
   trigger one owner-scoped polish round followed by re-review.
6. The final clean build verifies dependency closure and static artifact
   completeness.
7. Browser journeys load every route at mobile, tablet, and desktop sizes,
   plus reduced-motion mode. They check approved text/ids, navigation, unknown
   routes, local requests, images, console/page/CSP failures, main landmarks,
   overflow, content bounds, collapsed/colliding sections, extreme gaps,
   typography/line height, clipping, touch targets, and unsafe animation under
   reduced motion.

Geometry thresholds and viewport profiles live in application configuration.
Failures become typed diagnostics eligible for the existing bounded final
repair policy; they never silently downgrade promotion requirements.

## Retry, staleness, and preview safety

Artifact-store transport failures follow durable job retry policy. Hash,
expiry, schema, eligibility, ownership, or semantic failures are permanent for
that attempt and surface as `needs_attention` with a safe next action.

The session projection reports staleness when Build Preparation run, scope,
artifact, or expiry changes. Verification repeats that comparison before any
pending reconciliation or promotion. A stale candidate is never promoted.

Preview host identity is derived from the portfolio session, not an attempt.
The active object pointer changes only after source, build, runtime, and
staleness gates pass. A regeneration therefore keeps serving the prior active
preview throughout work and after failure; success swaps the pointer
atomically.

## Verification and operational evidence

Normal tests use injected model clients, artifact stores, adapters, and browser
verifiers. Live model/provider execution remains opt-in because a real pack can
contain private portfolio-derived context. The selected development pack can
be verified offline through exact SHA-256 pack-v3 admission without sending it
to a provider.

Use repository commands and configuration as the current source of truth for
coverage, models, provider endpoints, limits, and environment readiness. Do
not infer production readiness from a historical exported portfolio or a
local mirror alone.
