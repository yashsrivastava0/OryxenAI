Write the human- and machine-readable handoff for the future Code Generator.
Create one detailed site overview and one route-by-route brief for every
approved route. Ground route data in the supplied public Content Architect
projection and the supplied Visual Design Director direction. Explain the
audience and narrative, route and section purpose, content references,
responsive behavior, interaction and motion behavior, accessibility, available
resources, acceptance criteria, and what the Code Generator may decide freely.
Explain the pack's file/authority boundary in the overview so a consumer knows
where to find routes, local resources, execution bindings, provenance, and
fallbacks. The overview is guidance, not a second implementation contract.

Do not prescribe a fixed portfolio screen count, route count, shared component
count, card count, or layout. Describe the approved route set as public-scope
coverage, not as a generic portfolio template. The Code Generator may choose
the visual composition, number of internal scenes, responsive grouping, and
component usage that best serves the approved audience and content, while it
must still cover the exact admitted route/section IDs and honor the executable
resource bindings. Do not write restrictive design language such as "no
additional routes" as though it were a visual recommendation; if a route is
outside the approved public scope, say that changing scope requires upstream
approval. Do not add facts, metrics, dependencies, resource IDs, or private
information.
For each route, `resource_ids` MUST be a subset of the non-null
`selected_resource_id` values in the Stage 2 selections supplied in this task.
Use the executable local resource bindings, placement, accessibility,
responsive, reduced-motion, export, hash, license, and provenance metadata
provided in the packet. Do not copy Visual Design Director resource IDs, asset
IDs, scene IDs, or provider asset IDs into `resource_ids`. If Stage 2 selected
nothing, return `resource_ids: []` and explain the custom fallback in the route
brief. Code Generator may choose visual styling and composition within these
bindings, but it may not reacquire a known Build Preparation role.
