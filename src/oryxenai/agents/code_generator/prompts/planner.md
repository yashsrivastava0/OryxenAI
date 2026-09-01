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
  containers, and motion tokens without fallback expressions. Every token
  `name` (color, spacing, size, radius, motion) must start with a lowercase
  letter, followed only by lowercase letters, digits, or hyphens - a bare
  number like `"1"` or `"7"` is rejected. Use a semantic or letter-prefixed
  identifier instead: `"space-1"`/`"s1"` rather than `"1"`, `"cobalt"` rather
  than `"Cobalt"` or `"#2457C5"`.
- Give every section exact selectors, viewport order, columns, measure, gap,
  width range, overlap ceiling, and sticky authority. Responsive changes must
  preserve approved copy and reading order.
- For every `route_shells` row, preserve the exact approved `section_order`
  and set `h1_owner` to the first section ID in that order. The trusted shell
  owns the main landmark but has no authority to invent a content heading;
  never use `trusted_shell`, `composer`, a file name, or a new ID as the
  heading owner.
- Give every route at least one content-specific distinctive move. Bind it to
  source and target selectors, a machine-readable geometric relationship,
  ratio range, viewport set, and the CSS properties that establish it. A data
  marker by itself is not implementation. Every required CSS property must be
  valid and effective on the exact `source_selector` element itself. Use
  composition/layout properties here; never require `object-fit` or
  `object-position` on a section/panel wrapper. Media fit and focal position
  belong to the resource placement and its rendered image.
  `source_selector` names the exact element that receives the required CSS
  declarations, not merely an ancestor section. For grid, asymmetric, rail,
  or alignment moves, copy the matching `section_regions[*].region_selector`
  into `source_selector`, put the exact `runtime_marker` on that same rendered
  element, and use `target_selector` for the affected descendant or peer.
- Place each required resource once in its approved section. In every
  `resource_placements[*].resource_slot_id`, copy the exact
  `resource_bindings.slots[*].resource_slot_id` value (for example, a
  `slot-...` ID). Never put a materialized resource `id`, provider asset ID,
  filename, or source ID in that field. The slot's nested
  `resolution.resource_id` identifies the concrete file but is not the slot
  identity. State selector, honest alt policy, fit, focal position, responsive
  `sizes`, loading policy, visible-ratio floor, and aspect-ratio range. The
  `sizes` value must be a browser-valid concrete policy: use numeric CSS
  lengths such as `40rem`, `72vw`, or `100vw` (or `calc`/`min`/`max`/`clamp`
  expressions), and never spell out a number such as `sixtyrem` or use an
  unknown unit.
  `element_marker` must be one literal `data-*="stable-token"` attribute on
  the generated `LocalImage` wrapper, and `element_selector` must be that same
  attribute as a CSS selector (`[data-*="stable-token"]`). Do not target the
  trusted nested `img`; runtime verification finds it inside the wrapper.
  `sizes` is CSS syntax, never prose: BAD `(max-width: sixtyrem) 100vw, 58vw`;
  GOOD `(max-width: 60rem) 100vw, 58vw`. If uncertain, use the literal
  `100vw` fallback. Do not spell out numbers or invent descriptive words in
  any CSS value.
  Representative media is never personal evidence.
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
