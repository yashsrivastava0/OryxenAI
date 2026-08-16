Produce one SitePlan for the admitted portfolio contract. This is a design and
implementation plan, not source generation.

Ground every route and section in the approved public content. Derive a
specific creative thesis from the supplied visual direction, then make it
operational through a typed visual system, shell contract, reusable component
contracts, interaction contracts, resource slots, acceptance coverage, and a
dependency-ordered WorkGraph.

Plan for a visually advanced portfolio without fabricating content: articulate
what makes this portfolio distinct through hierarchy, spatial composition,
typographic contrast, restrained color, evidence treatment, and a small
motion vocabulary. Make distinctness structural, not cosmetic:

- Give every route a different committed layout strategy (asymmetric editorial
  hero, evidence-led archive, narrative timeline, side-rail reading, …) so no
  two routes read as one template with different text; name the strategy in
  each route's composition.
- Define the spatial system concretely: section cadence, content rhythm,
  element gaps, and where deliberate visual pauses carry the thesis — concrete
  enough that the builders can map it onto the scaffold's `--section-gap`,
  `--content-gap`, `--element-gap`, and `--space-*` tokens.
- Define the typographic hierarchy as scale steps (display, headline, body,
  caption) with pairing/contrast intent the foundation can map onto the fluid
  `--text-*` scale and font variables.
- Plan motion as choreography: which routes get entrance reveals, what
  staggers, what one signature moment is — every motion choice must have a
  reduced-motion equivalent that keeps all meaning (static, fully visible
  content).
- Treat evidence (facts, metrics, claims) as a first-class visual problem:
  numbers and proof get distinct typographic treatment, not body paragraphs.

- Every interaction must have a keyboard-accessible outcome; every resource must
  be an admitted local binding, declared slot, or explicit fallback.
- Each `acceptance_coverage.source_marker` is a SHORT embeddable token —
  `marker:<criterion_id>` — that the route source will embed verbatim inside a
  data attribute. Never write prose, sentences, or ID lists as a marker.

The WorkGraph is validated structurally — honor this contract exactly:

- `unit_id` values are unique and non-empty; every `depends_on` entry names an
  existing unit; the graph is acyclic and dependency-ordered.
- Exactly ONE unit has `terminal: true`, and it is `kind: "integration"`.
- `foundation` and `integration` units MUST leave `route_id` empty, and
  `route_ids`/`section_ids` as empty lists — only route units carry scope.
- Every `route`/`route_batch` unit covers exactly ONE admitted route (single
  `route_id`, or `route_ids` with exactly one entry) and owns at least one of
  that route's sections. If you split a route into multiple batches, their
  combined `section_ids` must equal that route's full section set exactly, and
  you must add exactly one `route_compose` unit for that route whose
  `depends_on` lists every one of its batches (the compose unit itself carries
  no sections).
- Every admitted route appears in at least one route unit; no invented routes.
- `owns_paths` are disjoint across ALL units (no path owned twice) and stay
  inside the scaffold's source tree (e.g. `src/...`).
- The terminal integration unit's `depends_on` lists EVERY other unit id
  verbatim — enumerate them exhaustively, including the foundation unit and
  every route/compose unit.

Do not emit source files, dependency requests, acquisition requests, URLs,
commands, or raw reasoning. The following source phases will be accountable
to the IDs and outcomes you define, so use stable IDs and make requirements
concrete enough to verify from text and DOM evidence.
