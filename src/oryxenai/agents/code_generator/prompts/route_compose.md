Compose the assigned split route from its completed section groups. Preserve
the frozen route authority, section order, shared exports, facts, approved
copy, resource bindings, and interaction assignments exactly. The
`<generation-contract>` block lists the anchor literals that must survive
unchanged; verify them by string search before returning. For every assigned
distinctive move, place its exact `data-distinctive-move-id="..."` marker on
the route-owned element that implements the move.

The composer owns only the route shell and route-level composition paths. It
may resolve layout rhythm, landmark structure, section transitions, and
route-local interaction wiring, but it may not rewrite already-owned batch
content or create a second visual language. Import and render one completed
section component for every approved section, in the exact approved order;
keep each section's `id`, `data-content-id`, and approved copy in that section
module. Do not retype content, create a second section wrapper, or import an
aggregator that owns multiple sections.

For the V4 contract, section modules are the only executable owners of section
anchors and approved content. The route composer must not import
`src/content/generated-content`, call `contentValue(...)`, build an
`approvedContent` array, or add a route-level `<h1>`. Render the completed
section components directly as children of `RouteShell`; the section module
that owns the hero owns the single page `<h1>`. Do not add `id="<section_id>"`
or `data-content-id="<section_id>"` wrappers around those components. The
source audit checks the composed route together with its child modules, so
duplicating an anchor in `index.tsx` creates duplicate DOM IDs and fails the
contract.

`RouteShell` already owns the single `main` landmark and its literal
`data-route-id`. Pass the exact route id to `RouteShell`, but do not add
another `id="<route_id>"`, `data-route-id="<route_id>"`, or nested shell in the
route composition. In particular, a route-level wrapper must not duplicate a
section module's DOM id or the shell's `main-content` id. The composer anchor
must contain every assigned source marker and every planned interaction id.

The route file is located at
`src/routes/<route-storage-key>/index.tsx`. Its exact relative import to the
trusted `src/components/generated/SharedSystems.tsx` module is
`../../components/generated/SharedSystems` (or use `@/components/generated/SharedSystems`).
Section modules are siblings below `./sections/`; do not climb above `src/`.

Use the exact emitted blueprint token names. Every emitted CSS custom
property carries its group prefix: a color token named `cobalt` compiles to
`--color-cobalt`, a spacing token named `5` compiles to `--space-5`, a size
token to `--size-<name>`, a radius token to `--radius-<name>`, a border to
`--border-<name>`, a shadow to `--shadow-<name>`. Always include that
prefix, even when it looks redundant with the token's own name (a spacing
token already named `space-5` still compiles to `--space-5`, not
`--space-space-5`). Do not assume or recreate a
default palette, `.card`, `.surface`, `.grid`, `.reveal`, `.stagger`, or other
generic scaffold primitive. The trusted `SharedSystems` signature supplies
the one main landmark, skip link, navigation, disclosure behavior, focus
return, and footer. Do not implement a second shell or modify `src/app/**`,
`src/generated/**`, `src/content/**`, `src/main.tsx`, package files, or the
route registry.

Keep the route coherent from mobile through desktop. Every interaction must
remain keyboard accessible and every motion beat must have a fully visible
reduced-motion equivalent. Use `publicRouteUrl` for same-site navigation and
only approved external URLs. Return complete files for only the owned paths,
with honest coverage and no arbitrary links, remote assets, or unapproved
source content.
