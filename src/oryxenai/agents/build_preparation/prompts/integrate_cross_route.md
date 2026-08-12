Reconcile the already-written context across multiple approved routes.
Preserve all route IDs, approved facts, selected resource IDs, and target
constraints. Improve shared navigation, terminology, responsive behavior,
resource reuse, and site-wide visual consistency. Do not add facts, routes,
dependencies, provider IDs, or resources. Return the complete replacement
context, not a patch and not commentary.
Each route `resource_ids` list MUST contain only non-null selected resource IDs
from the supplied Stage 2 selection plan. Never reuse Visual Design Director
resource IDs, asset IDs, scene IDs, or provider asset IDs; use an empty list
when no Stage 2 resource was selected.
