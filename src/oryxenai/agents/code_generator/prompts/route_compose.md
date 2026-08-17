Compose the assigned split route from its completed section groups. Preserve
the frozen route authority, section order, shared exports, facts, and resource
bindings exactly. The `<generation-contract>` block in your instructions
lists the exact anchor literals (route_id, section_ids, verbatim copy,
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
motion retains all meaning and controls. `index.tsx` stays the verification
anchor: after composition it must still contain the route's `route_id`, every
`section_id`, the approved copy verbatim, each acceptance-coverage
`source_marker` string, and a `data-interaction-id="<id>"` attribute per
planned interaction. Add the required route and criterion markers so
verification can trace the completed experience to the SitePlan.

Return complete files for only the owned integration paths, with precise
coverage. Do not emit package changes, remote assets, arbitrary links, or
unapproved source content.
