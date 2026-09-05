Repair only the bounded diagnostic bundle using the smallest safe source
change. Diagnostics do not grant authority to redesign routes, alter facts,
add dependencies, or weaken verification markers. The `<generation-contract>`
block carries the exact copy, marker, interaction, URL, and resource rules.

If a repair touches CSS, every emitted design-token custom property carries
its group prefix: a color token named `cobalt` compiles to `--color-cobalt`,
a spacing token named `5` compiles to `--space-5`, a size token to
`--size-<name>`, a radius token to `--radius-<name>`, a border to
`--border-<name>`, a shadow to `--shadow-<name>`. Always include that
prefix, even when it looks redundant with the token's own name (a spacing
token already named `space-5` still compiles to `--space-5`, not
`--space-space-5`) — never reference a bare token name as a custom
property.

Apply the diagnostic's correct repair:

Integration-review diagnostics may use a domain-specific code that is not
listed below. For any such diagnostic, treat its `requested_outcome` as a
binding repair requirement: inspect the quoted `evidence` and exact `marker`,
make the smallest change that satisfies that outcome inside the owned files,
and return a complete body for every changed file. Do not return an unchanged
file while claiming the finding is repaired. When a finding concerns DOM
hierarchy or reading order, JSX/HTML source order is authoritative. A CSS
`order` rule alone does not repair a desktop DOM-order finding. Preserve any
responsive ordering that the diagnostic explicitly requires. If a finding
names a trusted or compiler-owned file, leave it untouched and repair only the
owned source when the requested outcome is applicable there. Before returning,
re-read the returned bodies and verify that the diagnostic's observed state is
actually gone.

- `SOURCE_RUNTIME_NETWORK`: remove unapproved network references and runtime
  calls. Approved external links are content only.
- `SOURCE_REPLACE_MISSING` / `SOURCE_CREATE_EXISTS`: choose create or replace
  from the current `existing_files` state and return the complete file.
- `SOURCE_OWNERSHIP_ESCAPE` / `SOURCE_TRUSTED_FILE_MUTATION`: drop or move the
  change inside the owned paths; never edit the trusted runtime shell.
- `SOURCE_UNGROUNDED_COPY` / `SOURCE_CONTENT_COVERAGE_MISSING`: use exact
  approved copy or a short micro-label; never invent portfolio claims.
- `SOURCE_SECTION_COVERAGE_MISSING` / `SOURCE_ROUTE_ID_MISSING`: put the exact
  route/section ID and `data-content-id` literal in the route anchor file.
- `SOURCE_ACCEPTANCE_MARKER_MISSING`: put the exact marker token in the route
  anchor file.
- `SOURCE_INTERACTION_MARKER_MISSING`: put the exact literal
  `data-interaction-id="<interaction_id>"` on the interactive element in the
  anchor file; do not hide it behind a dynamic prop/helper.
- Any diagnostic that faults a placement for having no real local resource:
  check that placement's `required` field in `<generation-contract>` first.
  When `required` is false and no `local_paths` exist, this is the resource's
  own honest fallback working as designed, not a defect — render a tasteful,
  non-personal decorative or generated composition for that placement (no
  `LocalImage`, no invented photograph) instead. Never report
  `cannot_complete` solely because a non-required resource has no real
  binding; that authority exists for resources marked `required`.
- `SOURCE_EXECUTION_SLOT_UNUSED`: use executable resource binding. Import and
  render the admitted local component module, render a planned image through
  `LocalImage` with its exact short `resourceId` and no `sources` prop, or
  import the admitted package and export. Never use an acquisition-ledger path
  containing a run id and never invent a root-relative media URL. A slot ID,
  filename in a comment, manifest text, or prose mention does not count.
- `SOURCE_ROUTE_BATCH_IMAGE_BINDING_INVALID` / `RESOURCE_RUNTIME_PATH_MISMATCH`:
  remove every inline `sources` prop and render the trusted `LocalImage` with
  the exact short `resourceId`, sizes, loading, fit, focal position, and alt
  policy supplied by `PLANNED LOCAL IMAGE BINDINGS`. The trusted component
  resolves immutable paths, hashes, dimensions, and formats from the manifest.
- `SOURCE_ROUTE_BATCH_DISTINCTIVE_MOVE_INVALID`: put the exact runtime marker
  on the rendered element matched by the move's `source_selector`, then define
  every required CSS property on that exact selector. The CSS selector may be
  qualified by the same runtime-marker attribute, but never replace its route
  and section scope with a shorter class selector. If the source selector is a
  region selector, move the marker and declarations onto that exact region;
  declarations on its section ancestor or a descendant do not satisfy the
  move.
- `SOURCE_ROUTE_BATCH_MOTION_INVALID` / `MOTION_BEATS_NOT_IMPLEMENTED` (this
  also covers a whole-site review finding naming a mismatch between a motion
  state attribute and another marker on a different element): implement
  every exact motion marker, selector, before/after value, and reduced-motion
  final state. A viewport trigger needs IntersectionObserver state or a CSS
  view timeline, not a load-time animation. For essential content with a
  before opacity of 0, keep the unguarded CSS baseline at opacity 1; put
  opacity 0 only beneath `[data-motion-ready="true"]`, and call
  `setAttribute("data-motion-ready", "true")` only after confirming
  IntersectionObserver support. `Reveal`/`StaggerGroup` set
  `data-motion-ready` on their own wrapper, not on `children` — if a selector
  must combine it with another marker (a resource or interaction marker) on
  one element, pass that marker as a literal attribute directly to
  `Reveal`/`StaggerGroup` (for example `<Reveal data-resource-marker="...">`);
  a marker left on `children` lands on a different element than
  `data-motion-ready` and a compound selector requiring both will never
  match. If the two attributes genuinely belong on different elements
  instead, use a descendant selector (`[data-motion-ready="true"]
  [data-resource-marker="..."]`) rather than a compound one.
- `SOURCE_ROUTE_COMPOSER_NAVIGATION_MISSING` /
  `APPROVED_ANCHOR_NAVIGATION_MISSING`: pass a compact `<nav>` through
  RouteShell's `navigation` prop with every literal section href from the
  generation contract.
- `SOURCE_ROUTE_BATCH_INTERACTION_STATE_MISSING` /
  `INTERACTION_STATE_NOT_REALIZED`: implement the exact state attribute/value,
  navigation, focus, and keyboard transition on the assigned target.
- Disclosure repairs render one capability/content list only. Synchronize the
  button's `aria-expanded` and `aria-controls` with `hidden={!open}` (or
  conditional rendering) on that single panel. The native semantic list is
  the static fallback; never duplicate the same items in a simultaneous
  fallback branch.
- `SOURCE_VISUAL_CONTRACT_MISSING`: include the missing preservation string.
- `SOURCE_CSS_INVALID_LENGTH`: replace the named spelled-out unit with a valid
  numeric CSS length or an admitted design token (`50ch`, not `fiftych`).
- `SOURCE_CSS_CUSTOM_PROPERTY_UNBOUND`: replace every undefined custom
  property with an exact compiler-emitted token, or define an intentional
  runtime custom property literally on the owning JSX element. Do not invent
  a parallel token name.
- `SOURCE_ROUTE_FONT_FACE_FORBIDDEN`: remove route-authored `@font-face`
  rules. The compiler-owned `src/design/generated-tokens.css` already emits
  the admitted local font faces and root-public URLs.
- `SOURCE_LOCAL_IMPORT_MISSING` / `SOURCE_UNDECLARED_IMPORT`: fix or remove the
  import using only files and packages admitted in the current context.
  Import paths resolve from the repository root, not the prompt's logical
  `src/...` labels; use the `@/` alias when possible. If using a relative
  import, the file being repaired sets the required depth: from a section
  file at `src/routes/<route-storage-key>/sections/<section-file>.tsx`, use
  exactly three `..` segments (`../../../components/generated/SharedSystems`,
  `../../../content/generated-content`); from the route composer at
  `src/routes/<route-storage-key>/index.tsx`, use exactly two
  (`../../components/generated/SharedSystems`). Never use four `..` segments
  from a section file — that leaves `src/` entirely and cannot resolve any
  trusted module.
- `SOURCE_ROUTE_H1_COUNT_INVALID` / `SOURCE_SECTION_ANCHOR_COUNT_INVALID` /
  `SOURCE_SECTION_DOM_ID_MISSING` / `SOURCE_SECTION_ORDER_INVALID`: for a V4
  route, section `.tsx` modules own their single literal section anchors and
  the route composer only renders those modules. Do not add duplicate wrapper
  anchors or a route-level `<h1>`; preserve the route-scoped section ID in
  `data-content-id` and implement the independent exact `section_selector`
  from `<generation-contract>` (for example, `#hero` requires `id="hero"`).
  Remove duplicate composer markup and preserve the hero section's sole
  heading. The route composer must not import
  `src/content/generated-content`, call `contentValue(...)`, or create an
  `approvedContent` array. If the composer imports that module, remove the
  import and its unused content projection. Resolve trusted relative imports
  from `src/routes/<route-storage-key>/index.tsx` (for example,
  `../../components/generated/SharedSystems`); do not use a third `..` segment
  to reach modules directly under `src/`.
- `SOURCE_PLACEHOLDER` / `SOURCE_SECRET_ACCESS`: remove the placeholder or
  secret access.
- `TYPECHECK_FAILED` / `TYPECHECK_STRUCTURE_INVALID`: fix only the named files
  and preserve the design intent.

For a v4 repair, preserve the v4 source-generation envelope. The arrays are
machine-checked, not prose: `content_ids`, `criterion_ids`, `resource_slot_ids`,
and `interaction_ids` must exactly equal the corresponding IDs required by the
current unit in `<generation-contract>` (use `[]` when that unit owns none).
For route, route-batch, or route-compose changes, populate
`exported_signatures` with one entry for every changed exported source file,
using its exact returned `path` and exported symbol name (for example,
`HomeRoute` for a file containing `export default function HomeRoute`). Include
no signatures for unchanged or omitted files. Include the complete changed file
bodies in `files`; never replace these arrays with sentences describing what
was preserved. Keep `self_check` truthful but do not omit the required envelope
arrays.

When rejected file bodies are supplied, return the complete corrected file.
Preserve public truth, route ownership, resource bindings, accessibility,
responsive behavior, and reduced-motion behavior. Re-check the diagnostic and
return only changed owned files with honest coverage. If it cannot be repaired
within the supplied authority, return `cannot_complete` with the precise gap.
