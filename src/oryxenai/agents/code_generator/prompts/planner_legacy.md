# Operation: compile a legacy internal SitePlan

This compatibility operation exists only for explicitly configured pre-v4
runs and readers. Return one complete SitePlan covering the exact admitted
routes, ordered sections, criteria, interactions, and resource slots. Do not
invent visible copy, assets, URLs, dependencies, or file paths. Return an empty
work-graph unit list and empty execution bindings; host code owns path,
resource, and work-graph compilation.

When a legacy blueprint is required, keep every ID and upstream section order
exact and provide concrete responsive, accessibility, resource-placement, and
reduced-motion intent. Return only the strict SitePlan object.
