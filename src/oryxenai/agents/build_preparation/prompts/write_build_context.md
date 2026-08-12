Write the human- and machine-readable handoff for the future Code Generator.
Create one site overview and one screen-by-screen brief for every approved
route. Ground route data in the supplied public Content Architect projection
and the supplied Visual Design Director direction. Explain purpose, sections,
content references, responsive behavior, interaction and motion behavior,
accessibility, available resources, acceptance criteria, and what the Code
Generator may decide freely. Do not add routes, facts, metrics, dependencies,
resource IDs, or private information.
For each route, `resource_ids` MUST be a subset of the non-null
`selected_resource_id` values in the Stage 2 selections supplied in this task.
Do not copy Visual Design Director resource IDs, asset IDs, scene IDs, or
provider asset IDs into `resource_ids`. If Stage 2 selected nothing, return
`resource_ids: []` and explain the custom fallback in the route brief.
