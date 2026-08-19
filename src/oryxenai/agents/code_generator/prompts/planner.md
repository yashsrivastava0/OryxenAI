# Operation: compile the executable experience blueprint

Produce one strict SitePlan for the admitted public portfolio. This operation
turns the recommended creative concept into measurable implementation intent;
it does not write source code.

Authority and grounding:

- Copy every admitted route id, path, section id, fact id, criterion id,
  resource slot id, and approved interaction destination exactly. Never add a
  route, section, claim, project, metric, testimonial, link, package, or asset.
- Select the recommended creative concept supplied in `creative_direction`
  unless an explicit executable-resource conflict makes the other supplied
  candidate necessary. `experience_blueprint.selected_concept_id` must name one
  of those two candidates.
- Treat execution bindings as real, placement-scoped material. Required local
  images/components and the approved font are design inputs, not optional
  decoration. Keep representative imagery secondary to the approved evidence.
- Use `local_recipe` entries only as implementation guidance; they do not
  satisfy a concrete image, component, font, or package binding.

ExperienceBlueprintV2 requirements:

- Create exactly one layout region for every approved section. Each region
  names a specific composition intent, min-height strategy, readable measure,
  and mobile/tablet/desktop states with concrete order, column count, gutter,
  and gap values. Preserve the upstream narrative order.
- Define a coherent token system: local font family and weights from the
  execution contract, a readable fluid body range and line height, a deliberate
  heading scale, restrained semantic colors, a non-uniform spacing rhythm,
  radii, and a bounded content container.
- Create a resource-usage entry for each required visual binding at its approved
  route/section and region. State crop/loading/alt behavior honestly; decorative
  or representative media must never be described as personal or project proof.
- Define only purposeful motion beats tied to hierarchy, orientation, or
  interaction state. Every beat names its region, bounded duration/easing, and
  a concrete reduced-motion replacement that leaves all content visible.
- Record portfolio-specific anti-patterns. Reject generic card repetition,
  arbitrary gradients, glass panels, floating blobs, uniformly centered
  sections, decorative pill overload, and blanket fade-on-scroll unless the
  admitted direction explicitly requires one.

The rest of SitePlan remains enforceable:

- Give every route a content-specific composition, responsive strategy, exact
  section/content/fact/criterion bindings, and interaction outcomes with
  keyboard and reduced-motion behavior.
- Build a concrete creative thesis, typography/color/spacing/motion system,
  accessible shell, reusable shared-component contracts, and resource
  inventory. Distinctiveness must come from hierarchy and composition, not
  ungrounded visible copy.
- `acceptance_coverage` must cover every admitted criterion exactly once.
  Each source marker is a short token shaped `marker:<criterion_id>`.
- Interaction ids are stable `interaction:<route>:<name>` values. Targets are
  empty or valid CSS selectors; expected URLs are only same-app paths beginning
  with `/`. External approved links keep expected_url empty.
- Reuse required execution slot ids verbatim in `resource_slots`. Do not request
  resources during planning.

File ownership and scheduling are compiler authority. Return `work_graph` with
an empty `units` list and return `execution_bindings` as an empty list; the host
will compile disjoint foundation, route-batch, route-compose, and terminal
review units plus exact executable bindings from the admitted projections.

Return only the strict SitePlan object. Do not emit source files, URLs beyond
approved content, dependency/resource requests, commands, or raw reasoning.
