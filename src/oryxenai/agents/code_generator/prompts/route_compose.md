Compose the assigned split route from its completed section groups. Preserve
the frozen route authority, section order, shared exports, facts, and resource
bindings exactly. The `<generation-contract>` block in your instructions
lists the exact anchor literals (route_id, section_ids,
marker tokens, interaction attributes) that must survive composition
unchanged — re-verify them by string search before returning.

The composition pass may resolve layout rhythm, landmark structure, section
transitions, and route-local interaction wiring, but it may not rewrite
already-owned section content or create a second visual language. Bind the
route's rhythm to the scaffold tokens (`--section-gap`, `--content-gap`,
`--element-gap`) so transitions between composed sections feel intentional
rather than accidental, and sequence the entrance with `.reveal` + `.stagger`
only where the plan calls for choreography. This target has no utility-class
framework: compose with tokens and route-scoped CSS, never foreign classes.

Ensure the route remains coherent from desktop to mobile and that reduced
motion retains all meaning and controls. `index.tsx` is the composition
anchor: it must contain the route's `route_id`, import and render every batch
in approved section order, preserve each acceptance-coverage `source_marker`,
and wire every planned interaction. Approved copy and `data-content-id`
markers remain in the batch modules; do not duplicate or rewrite them in the
composer. Verification evaluates the complete route subtree and rendered DOM.
Use `publicRouteUrl` from the trusted `src/app/ResourceUrl.ts` module for every
same-site route `href` so navigation works both at the origin root and under a
nested preview base.

Return complete files for only the owned integration paths, with precise
coverage. Do not emit package changes, remote assets, arbitrary links, or
unapproved source content.
