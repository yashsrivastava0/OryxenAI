# Site overview

## Audience and narrative
This public-scope site introduces grounded engineering work to visitors evaluating a privacy-safe systems practice. Its narrative moves from positioning to evidence: the approved opening presents “Durable systems,” followed by the approved QueueGuard evidence section. Preserve an evidence-first hierarchy and do not add unsupported metrics or private content.

## Approved public scope
The approved route set contains `home` at `/`, with the admitted sections `hero` and `project` in that order. The public navigation exposes Home targeting `home`. Changing public scope or adding unsupported content requires upstream approval.

## Visual and interaction direction
Use a restrained-evidence editorial language with charcoal, mineral, and cobalt accent relationships; asymmetric text-led composition and structured reading edges are encouraged, not mandatory. Flat cards, anchor-style navigation, subtle hover treatment, and minimal, brief low-amplitude structural emphasis are approved directions. The Code Generator may choose the visual composition, internal scene grouping, layout, and component usage that best serve the approved content.

## Responsive, motion, and accessibility
Dense compositions stack on narrow screens. Essential content must remain visible without hover, and all essential content must remain in document flow. Decorative imagery, when available, stacks below essential copy and crops without hiding content. Reduced motion must provide the complete static state with no sequencing, parallax, or required movement. Use semantic structure, logical heading hierarchy, keyboard-accessible controls, visible focus, sufficient contrast, meaningful link names, and decorative empty alt text unless an approved decorative image becomes semantic in the final composition.

## Pack authority and boundaries
Use the approved Content Architect projection for route IDs, paths, section IDs, public copy, claims, navigation, and privacy boundaries. Use the Visual Design Director projection for visual language, scene intent, responsive behavior, motion, accessibility, forbidden concepts, and must-not-fabricate rules. Stage 2 `selections` are the authority for selected resource IDs; route `resource_ids` may contain only their non-null `selected_resource_id` values. Executable local resource bindings, including local path, placement, accessibility, responsive and reduced-motion metadata, export details, hash, license, and provenance, are authoritative when present. The packet contains selections but no executable local materialization bindings, so image and font roles remain execution gaps and must use their approved fallbacks until valid local bindings are supplied. Do not reacquire known roles, call provider networks at runtime, invent source bytes, IDs, URLs, paths, hashes, provenance, dependencies, or facts.

## Implementation boundary
The Code Generator may decide composition, internal scene count, responsive grouping, typography application within the approved local font contract, component reuse, spacing, and exact interaction implementation. It must still cover the exact admitted route and section IDs, preserve approved public copy and claims, honor offline execution, and keep decorative resources non-evidentiary.

## How Code Generator consumes this pack

`overview.md` is explanatory context, not the implementation authority. The
consumer first admits `build-pack.zip`, verifies the ZIP, expiry, manifest,
projection hashes, approvals, licenses, execution slots, and route contracts,
then builds its planner context from the following files:

- `site/contract.json` — the approved public routes, paths, sections, content,
  criteria, and route file references.
- `design/visual-direction.json` — the approved visual language, composition
  intent, responsive outcomes, accessibility, and motion direction.
- `execution/contract.json` — the one authoritative resolution for every known
  resource slot: local paths, import paths, exports, dependencies, hashes,
  provenance, and fallback behavior.
- `resources/projection.json` and `resources/ledger.json` — materialized
  resources, decisions, placements, and the reason each resource is present.
- `provenance/approvals.json`, `provenance/targets.json`,
  `provenance/licenses.json`, and `provenance/checksums.json` — admission,
  target, licensing, and byte-integrity evidence.
- `routes/` — route-scoped briefs, public data, and resource maps.
- `resources/images/`, `resources/components/`, `resources/fonts/`, and
  `resources/recipes/` — the local material and typed local implementations
  available inside the admitted pack.

The planner writes a local workspace from those admitted files. It imports
prepared component source from the generated resource tree, references local
images and fonts, merges only the allowed dependency bindings, and records a
source manifest. Known Build Preparation roles are not searched for again.
Only a genuinely emergent need that is absent from the execution contract can
enter Code Generator's separate, receipt-bound acquisition path.

## Approved route inventory

The route set below is the current approved public scope. It is a coverage
boundary, not a visual template or a recommendation about how many screens a
portfolio should have.

- `home` at `/`

## Composition guidance (advisory)

- This briefing does not set a fixed screen count, route count, shared
  component count, card count, or layout. Choose the composition that best
  serves the approved audience and content.
- Cover every admitted route and semantic section, but decide how to express
  them: a long-form route may use multiple scroll scenes, responsive states,
  or nested interaction surfaces; multiple approved routes may become separate
  public screens. Adding a new public route requires upstream approval rather
  than an assumption in this document.
- Treat prepared component bindings as available implementation material for
  their named roles, not as a quota. Use the declared exports/import paths when
  they improve the experience; otherwise preserve the binding's declared
  accessible fallback. Do not substitute a remote component or reacquire the
  known role.
- Infer the portfolio's information architecture from the approved person,
  work, and audience. An executive-oriented portfolio may emphasize trust,
  leadership, outcomes, and a clear contact path when those facts are
  approved. A software-oriented portfolio may emphasize capabilities,
  experience, selected work, technical decisions, and evidence when those
  facts are approved. Neither archetype authorizes invented claims, metrics,
  employers, projects, or credentials.
- Preserve the contract's responsive, keyboard, accessibility, and
  reduced-motion outcomes while freely choosing visual hierarchy, spacing,
  grouping, and implementation detail.

## Handoff review checklist

Before generation, confirm that the selected route and section coverage is
exact, every known visual role resolves to its prepared local material or
declared typed fallback, imports and exports match the execution contract, and
all local references remain inside the workspace. Before preview promotion,
verify the generated source and runtime at the approved routes and responsive
states, including keyboard and reduced-motion behavior. The overview can guide
that work, but the JSON contracts and local files remain the source of truth.

## Fixed facts

- The only approved route is `home` at `/`.
- The approved sections are `hero` and `project`.
- The approved public content is “Durable systems” and “QueueGuard”.
- Private content is excluded.
- Metrics must not be fabricated.
- QueueGuard must be preserved.

## Free to change

- The Code Generator may choose composition, internal scene count, component usage, spacing, and responsive grouping.
- The Code Generator may use approved text-led/static fallbacks while executable local resource bindings are unavailable.

## Runtime requirements

```json
{
  "approved_routes": [
    "home"
  ],
  "offline": true,
  "reduced_motion": "complete static equivalent",
  "resource_validation": "hard-fail on unsafe source, missing local path, missing hash, missing provenance, invalid dependency, or invalid license",
  "responsive": "stack dense compositions on narrow screens",
  "runtime_network_assets": false,
  "touch": "essential content remains visible without hover"
}
```
