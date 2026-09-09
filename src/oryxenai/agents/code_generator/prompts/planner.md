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
- `content_ids` are host-owned bindings, not a summary field. For every
  `section_regions` row, copy the complete `content_key_manifest` array for
  its exact `(route_id, section_id)` pair in the supplied order, including
  long capability or project sections. Never shorten, reorder, paraphrase,
  or replace that array with a representative subset.
- Emit `typography_roles` with exactly one object whose explicit `role` is
  `body`, plus at most one second object whose explicit `role` is `display`.
  Never omit `role`, emit two `body` objects, or use a font family as the role.
  Every `type_steps[*].role` must be one of those explicit roles. Use one or
  two approved local font roles. Echo their family, weights, style, and
  WOFF/WOFF2 files exactly. Define fluid type steps, line height, tracking,
  semantic colors, typed lengths, borders, shadows, spacing, radii,
  containers, and motion tokens without fallback expressions. When a
  Tailwind/shadcn registry component is part of the approved resource set,
  emit `shadcn_theme_bindings` for its fixed semantic vocabulary: the only
  permitted keys are `background`, `foreground`, `card`, `primary`,
  `primary-foreground`, `secondary`, `muted`, `muted-foreground`, `accent`,
  `destructive`, `border`, `input`, and `ring`. Each value must copy an exact
  `colors[*].name`; never put a CSS value, a provider name, or an invented
  component slot in this mapping. If no approved component needs a slot, the
  mapping may omit that slot. None of `colors[*].name` may equal any of these
  same slot keys (do not name a raw color `accent`, `primary`, `border`, and
  so on) - a raw color token and a binding slot with the identical name
  compile to the exact same CSS custom property, so the binding would
  silently overwrite the raw color's real value with no error. Give the raw
  color a distinct, concrete name instead (for example `coral` or `brand`
  for the color an `accent` slot points at). A visual brief that describes
  "an accent color," "the primary action," "a muted background," or similar
  design language is naming a *design concept*, not dictating the literal
  `colors[*].name` string - reserve those exact words for the matching
  `shadcn_theme_bindings` key only, and pick an unrelated concrete name (a
  hue, material, or brand word) for the color token itself, even when the
  brief's own prose uses the slot word repeatedly. Every token
  `name` (color, spacing, size, radius, motion) must start with a lowercase
  letter, followed only by lowercase letters, digits, or hyphens - a bare
  number like `"1"` or `"7"` is rejected. Use a semantic or letter-prefixed
  identifier instead: `"space-1"`/`"s1"` rather than `"1"`, `"cobalt"` rather
  than `"Cobalt"` or `"#2457C5"`.
  For `type_steps[*].name`, use the bare semantic suffix such as `body`,
  `display`, `heading`, or `label`; do not include the compiler group prefix
  `type-`. The compiler emits the final `--type-<name>-...` custom properties.
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
  ratio range, viewport set, and the CSS properties that establish it. For
  every non-sticky move, choose a numeric range with `maximum_ratio -
  minimum_ratio >= 0.15` and at least one endpoint at least `0.15` away from
  `1.0` (for example `0.25..0.85`, `0.4..0.7`, or `1.2..1.8`). Do not round a
  valid asymmetric range into two nearly identical values. A data
  marker by itself is not implementation. Every required CSS property must be
  valid and effective on the exact `source_selector` element itself. Use
  composition/layout properties here; never require `object-fit` or
  `object-position` on a section/panel wrapper. Media fit and focal position
  belong to the resource placement and its rendered image.
  `source_selector` names the exact element that receives the required CSS
  declarations, not merely an ancestor section. For grid, asymmetric, rail,
  or alignment moves, copy the matching `section_regions[*].region_selector`
  into `source_selector`, put the exact `runtime_marker` on that same rendered
  element, and use `target_selector` for the affected peer.
  `source_selector` and `target_selector` must each resolve to exactly one
  element and must be true peers (siblings, or elements at the same
  structural level) -- never an ancestor/descendant pair, and never a
  selector that matches more than one element. A `width_ratio` relationship
  is defined as `source_selector width / target_selector width`: if the
  ratio needs to move, narrow the source or widen the target, never the
  reverse. Do not pair a region container against one of its own child rows
  as a `width_ratio` -- a container is never narrower than its own content,
  so that pairing can only ever measure at or above `1.0` regardless of
  design intent. For `implementation_kind: framed_evidence_sequence` or any
  move whose true target is a repeated set (multiple cards/rows sharing one
  selector), use `relationship: shared_alignment_axis` on two specific named
  peers instead of `width_ratio`; `width_ratio` is only for a single
  source/target element pair.
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
- Follow the host-provided `image_policy` in the planner context. When
  `minimum_visible_images` is greater than zero and approved image slots are
  available, place that many exact image slots, including one on the primary
  `/` route when `require_primary_route_image` is true. Bind each to a real
  approved section and a visible `LocalImage` wrapper. Do not satisfy this
  requirement with a component slot, a CSS-only ornament, or an invented
  resource ID. If the policy has no approved image slots, preserve the
  text-led direction and do not fabricate one.
  When approved optional local image material is available and the brief does
  not request a text-only or abstract treatment, prefer a restrained supporting
  image placement as visual guidance; this preference is not a release gate.
  When the brief explicitly calls for text, diagrams, or abstract artwork, omit
  photo placements and choose a deliberate text/list or CSS composition instead.
- Select exactly one of the typed layout recipes for every section region:
  `text-with-supporting-media`, `work-detail-list`, or `timeline-list`. The
  exact `[data-region-id="..."]` element owns the direct children described by
  the recipe. `text-with-supporting-media` requires two real wide-screen
  children and stacks them into one `minmax(0, 1fr)` column on small screens;
  if the approved scope has no usable image, choose a single-column recipe or
  keep the supporting media as an honest optional fallback without an empty
  track. `work-detail-list` keeps repeated detail items in normal flow and
  `timeline-list` keeps dates and entries in an ordered list with a visible
  spine. All three recipes require `min-width: 0`, readable text measure,
  explicit row/column gaps, and a complete reduced-motion state. Do not
  invent a fourth recipe or add a wrapper that moves the region marker away
  from the element owning these direct children.
- Assign every approved interaction exactly once with selector, literal
  marker, keyboard behavior, focus result, state transition, state attribute,
  and same-app navigation outcome when applicable. When an interaction runs
  inside a section, make its `target_selector` section-scoped: prefix a local
  descendant selector with that section's exact `section_selector` (for
  example, `#capabilities [data-capability-group] button`). Keep the stable
  interaction ID in the `interaction:<route>:<section>:...` namespace when it
  names a section. Reserve unscoped selectors and route-level IDs for genuine
  route-shell behavior; the host uses these two signals to keep section
  controls out of the composer.
- Add motion only when it explains hierarchy, orientation, or interaction
  state. Bind trigger and target selectors, before/after computed properties,
  duration range, easing, main-thread budget, purpose, and a static
  reduced-motion replacement that keeps all content visible. A beat may
  optionally set `pattern_id` to one of three trusted, pre-built, tested
  implementations instead of inventing its own trigger/before-after/easing
  values — a menu you may reach for per beat where it genuinely fits, never
  a default or blanket instruction, and every other required field is still
  populated as normal. Every one of these three implementations fires only
  on a viewport (IntersectionObserver) trigger; none of them supports a
  `load` trigger, so set `trigger: viewport` on any beat using one of them:
  - `reveal-fade-rise`: viewport trigger; opacity 0->1 and
    translateY(28px->0); a smooth deceleration curve, ~600-900ms, plays once.
  - `reveal-clip-lines`: viewport trigger; text wrapped in an
    overflow:hidden clip box, inner span translateY(115%->0) and opacity
    0->1, staggered per line/word; a pronounced deceleration curve.
  - `stagger-group`: viewport trigger on a list; each child gets
    reveal-fade-rise with an index-driven transition-delay.
  Leave `pattern_id` empty for any beat that needs a different,
  purpose-specific motion. Every beat still requires a schema-valid
  `easing` value (`linear`, `ease`, `ease-in`, `ease-out`, `ease-in-out`, or
  a literal `cubic-bezier(...)`/`steps(...)` expression) even when
  `pattern_id` is set — the pattern's exact curve is already fixed in
  `motion.css`, so `ease-out` is a safe, valid choice here regardless of
  which pattern is used. Never write a spelled-together word like
  `easeOutCubic` or `easeOutExpo` as the `easing` value itself; those are
  not valid CSS and will be rejected.

Reject interchangeable templates: repeated identical section shells,
unauthorized card grids, uniform centering, arbitrary gradients, glass, pills,
blobs, blanket scroll fades, universal staggering, inert pseudo-controls, and
decorative effects that obscure evidence. Examples in trusted instructions are
quality failures or contract demonstrations, never a style catalogue. The
three trusted motion patterns above are a bounded implementation menu, not an
exception to this rule: applying one of them to every section would still be
the same rejected "blanket scroll fades, universal staggering" failure this
rule already names.
