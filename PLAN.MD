# Current workflow cleanup plan

## Objective

Keep the active OryxenAI product limited to its supported Discovery and
Content Architect workflow. The approved content plan is the terminal output
of the current product.

## Preservation boundaries

- Preserve Git history and do not contact GitHub.
- Preserve database rows, stored user output, archives, and append-only logs.
- Do not run migrations against the application database as part of local
  source cleanup.
- Preserve unrelated working notes and user files.

## Implementation state

- Active agent and worker registries expose only the supported planning
  workflow.
- API route registration, current-state projection, model profiles, product
  UI, and service configuration are aligned with that workflow.
- Existing stored records remain available to authorized cleanup and audit,
  but are excluded from current product state.
- Current-facing project context and developer entry points describe the
  supported workflow.
- Some source-only and historical materials remain in the checkout. Their
  broad recursive removal was rejected because the proposed operation also
  included archive and storage cleanup code. Do not infer they are active from
  their presence; do not repeat the rejected operation through an indirect
  workaround.
- No tests, live model calls, database migrations, deployment, or remote
  repository operations have been performed in this task.

## Completion checks

Before treating cleanup as complete, review the staged diff, run the approved
static quality checks, and confirm that Discovery and Content Architect
remain registered and reachable. Any future deletion of source-only archives
must preserve account cleanup and historical data behavior.

## Preserved pre-existing working notes

These unrelated dependency pin notes were present in this modified plan and
are retained:

    actions/checkout@*
    astral-sh/setup-uv@*
    gitleaks/gitleaks-action@*
