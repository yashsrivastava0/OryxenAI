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
  be an admitted local binding, declared slot, or explicit fallback. Give every
  interaction a short stable id (`interaction:<route>:<name>`) — the route
  source must embed a literal `data-interaction-id="<that exact id>"` attribute,
  so the id must be filesystem- and JSX-safe (letters, digits, colons,
  hyphens only). Leave `target` empty or a valid CSS selector (never prose,
  never a bare section id); leave `expected_url` empty for external links and
  anchors — set it only for in-app navigations starting with `/`.
- Each `acceptance_coverage.source_marker` is a SHORT embeddable token —
  `marker:<criterion_id>` — that the route source will embed verbatim inside a
  data attribute. Never write prose, sentences, or ID lists as a marker.
- Bind every required execution slot from the execution contract to the route
  that renders it, in `resource_slots`, reusing the slot ids verbatim.

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
  inside the scaffold's source tree (`src/...` only).
- The terminal integration unit's `depends_on` lists EVERY other unit id
  verbatim — enumerate them exhaustively, including the foundation unit and
  every route/compose unit.

PREFER THE SIMPLEST GRAPH THAT COVERS THE WORK. A single-route portfolio with
eight or fewer sections is exactly three units, in order:

1. `unit:foundation` — kind `foundation`, no route scope.
2. `unit:route:<route_id>` — kind `route_batch`, covering ALL of the route's
   sections in one batch (no split, no compose unit).
3. `unit:integration` — kind `integration`, terminal, depending on both.

Only split a route into multiple batches plus a compose unit when the route
genuinely has too many sections for one batch, and only add further route
units when there are further routes.

Path ownership follows the scaffold's fixed idiom — declare `owns_paths`
exactly this way, because the trusted route registry, the builder prompts,
and the validators all assume it:

- The foundation unit owns `src/design/**` and `src/components/shared/**`
  (and may own `src/lib/**` for shared helpers). NEVER plan `src/styles/**` —
  the scaffold's token system lives under `src/design/`.
- Each route unit owns exactly `src/routes/<storage-key-dir>/**` where
  `<storage-key-dir>` is the site contract's `storage_key` for that route with
  any leading `routes/` prefix REMOVED (a storage_key of
  `routes/home-4ea140588150` therefore yields `src/routes/home-4ea140588150/**`
  — never `src/routes/routes/...`), plus optionally
  `src/components/<route-short-name>/**` for that route's private components.
  NEVER plan a route directory named after the route_id when the storage_key
  differs.
- The integration unit owns no files. It is a terminal audit/reconciliation
  pass over the finished tree; return an empty change set after confirming
  the scaffold shell, route coverage, and shared contracts. The executable
  shell (`src/app/**`, `src/main.tsx`) is scaffold-owned and immutable, while
  `src/generated/**` and `src/content/**` are pipeline-owned.

Do not emit source files, dependency requests, acquisition requests, URLs,
commands, or raw reasoning. The following source phases will be accountable
to the IDs and outcomes you define, so use stable IDs and make requirements
concrete enough to verify from text and DOM evidence.
