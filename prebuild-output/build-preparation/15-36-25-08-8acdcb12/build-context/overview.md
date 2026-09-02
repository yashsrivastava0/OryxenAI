# Build handoff

## Audience and narrative
Build a focused, moderate-density, single-page portfolio for hiring teams and product leaders evaluating end-to-end UI/UX and Product Designers. The narrative is that Arjun Mehta makes complex product experiences easier to use by understanding friction, shaping clearer flows, testing interactions, and scaling reusable patterns. Lead with positioning and selected work; use approach, experience, and systems sections as supporting evidence; close with a safe LinkedIn-led connection path.

## Approved public scope
The approved route is `home` at `/`. It must cover exactly these section IDs in the approved content order: `home:hero`, `home:selected-work`, `home:approach`, `home:experience`, `home:design-systems`, and `home:about-connect`. This is public-scope coverage, not a prescribed portfolio template. The generator may choose the visual composition, internal scenes, grouping, and component usage. Changing public route or section scope requires upstream approval.

## Authority and pack boundary
Use the Content Architect projection for route topology, section IDs, public copy, links, claims, and privacy boundaries. Use the Visual Design Director projection for visual language, responsive behavior, motion behavior, forbidden concepts, and resource-role intent. Use Stage 2 selections and their executable metadata for resource bindings. Routes and section references are in `approved_content.public_content_manifest`, `approved_content.route_plan`, `approved_content.page_content_packs`, and `approved_content_context`. Selected resources, provenance, licensing, retrieval/source metadata, and selection rationale are in `selections`, `existing_resources`, and `candidate_resources`. Execution status and materialization constraints are in `visual_direction.quality_boundary`, `materialization_constraints`, and the selected-resource metadata. Fallbacks are the approved semantic/text-led alternatives in each selection. Do not reacquire a known Build Preparation role, call providers at runtime, or treat assumed VDD IDs as executable resource IDs.

## Visual and runtime direction
Use a technical-editorial language with charcoal, mineral, and cobalt accent; asymmetric text-led sections with structured reading edges; generous opening space and denser evidence chapters; Space Grotesk as the selected local display/body family where materialized. Motion is brief, low-amplitude structural emphasis only. Reduced motion must provide a complete static equivalent with no sequencing or parallax. Dense compositions stack on narrow screens, essential content remains visible without hover, and all interactive content remains keyboard and touch accessible.

## Privacy and evidence boundary
Use only approved generalized public copy. Do not publish the phone number, exact metrics, screenshots, project visuals, testimonials, awards, client details, named case-study URLs, or unsupported claims about teams, timelines, production status, or ownership. Supplied external URLs are unverified; retain only approved public links and validate them before release. Employer and project names remain a permission-sensitive concern even where present in planning data; do not restore richer detail without upstream approval.

## Resource state
Stage 2 selected five decorative image resources, one optional selected-work component resource, one experience component resource, and one font resource. The packet does not provide local paths, hashes, or complete executable materialization bindings for these selections, so treat materialization/provenance completion as an execution gap. Do not substitute stock, fabricated local assets, generated markers, or runtime provider calls for approved image roles. If an image is not executable, use its specified text-led/static fallback and record the gap. The selected-work component may fall back to the approved semantic section. The experience component has an approved semantic native-list fallback because the selected provider component is not a genuine timeline.

## Generator freedoms
Choose layout, typography scale within the approved language, spacing values, visual grouping, number of internal scenes, responsive grouping, semantic HTML structure, and whether optional component resources are used. You may implement selected-work detail exploration with the selected SmoothUI resource only after validating its source and dependencies, or use the approved semantic fallback. You may implement experience as the approved accessible static list/timeline. Do not invent content, routes, claims, metrics, assets, dependencies, file paths, resource IDs, or provider IDs.

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

- `home` at `/` — prepared resource IDs: `resource-pixabay-d85095d80f5f23be1e95`, `resource-pixabay-2bf5c084e29d1ae09db4`, `resource-pexels-ee43d84747dcbbaf047e`, `resource-pexels-50a37c58f60863c47869`, `resource-pexels-5b499fef9eeb34b769ae`, `resource-smoothui-d7a42b9814bfe7c97f23`, `resource-magicui-0bcd9511bdad151cae2f`, `resource-fontsource-b69f66a0c66ec46921e7` — 11 acceptance criteria

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

- Arjun Mehta is a Senior UI/UX Designer based in Bengaluru.
- The approved route is `home` at `/`.
- The approved section IDs are `home:hero`, `home:selected-work`, `home:approach`, `home:experience`, `home:design-systems`, and `home:about-connect`.
- The audience is hiring teams and product leaders, with design and engineering collaborators as a secondary audience.
- The public narrative is research-to-systems: understand friction, shape clearer paths, test interactions, and scale patterns.
- Pending metrics, screenshots, project visuals, named case-study URLs, testimonials, awards, client details, and the supplied phone number are excluded.
- The visual language is technical editorial with charcoal, mineral, and cobalt accent.
- Reduced motion requires a complete static equivalent.
- Runtime network assets are not allowed.
- Stage 2 selected resource IDs are the only permissible route resource IDs.

## Free to change

- Choose composition, layout, internal scenes, responsive grouping, and component usage.
- Choose semantic HTML, spacing, type scale, and accessible interaction implementation.
- Use the approved semantic fallback when a selected resource is not executable or is semantically unsuitable.
- Omit decorative imagery only through the specified fallback when local executable bindings are unavailable.

## Runtime requirements

```json
{
  "materialization": "validate local path, hash, provenance, license, exports, and dependencies before release",
  "network_assets": false,
  "reduced_motion": "complete static equivalent with no sequencing or parallax",
  "resource_policy": "selected resources only; no runtime provider calls; no fabricated local markers",
  "responsive": "stack dense compositions on narrow screens",
  "touch": "essential content remains visible without hover"
}
```
