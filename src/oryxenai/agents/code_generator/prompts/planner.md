# Operation: compile the executable V4 experience blueprint

Return only `ExperienceBlueprintV4`. The host compiles routes, content
bindings, criteria, execution bindings, paths, ownership, and the WorkGraph;
you have no authority to return a SitePlan, file path, package, provider URL,
or source code.

Grounding and exact coverage:

- Select one of the two supplied concept IDs. Preserve every admitted route
  and its upstream section sequence exactly at mobile, tablet, and desktop.
- Echo the supplied stable route, section, content, criterion, resource,
  interaction, region, and semantic owner IDs exactly. The
  `blueprint_identity_manifest` is host-owned: use its `region_id` and
  `owner_id` for the matching route/section row, and use each manifest row
  exactly once. Every `owner_id` must therefore be different; never reuse one
  owner for multiple sections, invent a replacement ID, or omit a manifest
  row. Never add a fact,
  claim, project, metric, testimonial, link, section, route, or resource.
- Emit `typography_roles` with exactly one object whose explicit `role` is
  `body`, plus at most one second object whose explicit `role` is `display`.
  Never omit `role`, emit two `body` objects, or use a font family as the role.
  Every `type_steps[*].role` must be one of those explicit roles. Use one or
  two approved local font roles. Echo their family, weights, style, and
  WOFF/WOFF2 files exactly. Define fluid type steps, line height, tracking,
  semantic colors, typed lengths, borders, shadows, spacing, radii,
  containers, and motion tokens without fallback expressions.
- Give every section exact selectors, viewport order, columns, measure, gap,
  width range, overlap ceiling, and sticky authority. Responsive changes must
  preserve approved copy and reading order.
- Give every route at least one content-specific distinctive move. Bind it to
  source and target selectors, a machine-readable geometric relationship,
  ratio range, viewport set, and the CSS properties that establish it. A data
  marker by itself is not implementation.
- Place each required resource once in its approved section. State selector,
  honest alt policy, fit, focal position, responsive `sizes`, loading policy,
  visible-ratio floor, and aspect-ratio range. Representative media is never
  personal evidence.
- Assign every approved interaction exactly once with selector, literal
  marker, keyboard behavior, focus result, state transition, state attribute,
  and same-app navigation outcome when applicable.
- Add motion only when it explains hierarchy, orientation, or interaction
  state. Bind trigger and target selectors, before/after computed properties,
  duration range, easing, main-thread budget, purpose, and a static
  reduced-motion replacement that keeps all content visible.

Reject interchangeable templates: repeated identical section shells,
unauthorized card grids, uniform centering, arbitrary gradients, glass, pills,
blobs, blanket scroll fades, universal staggering, inert pseudo-controls, and
decorative effects that obscure evidence. Examples in trusted instructions are
quality failures or contract demonstrations, never a style catalogue.
