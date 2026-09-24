# Current authentication and authorization surface

This note describes the current local source. The authorization dependencies,
route registration, and tests define the binding behavior.

## Identity and product boot

Supabase restores the browser session. The API verifies the identity token,
admits an approved identity, and returns a minimal local-user projection.
Username onboarding is required when the local identity has no completed
username claim. The browser loads the owner-scoped workspace only after this
boundary succeeds.

## Session ownership

Normal users may access only the portfolio session bound to their entitlement.
The server resolves ownership for each route and checks it again for mutations.
Historical or quarantined sessions do not become user-visible by guessing an
identifier.

Current product state and run responses are projected through active schemas.
Historical JSON fields and stored output are not exposed as current product
state.

## Durable work

Portfolio-bound jobs store trusted owner and actor identifiers, the session,
and an authorization context version. Workers validate the job lease, account
status, session ownership, actor permissions, and entitlement revision before
applying results.

## Administration

Administrator APIs require an active administrator identity and record
audited lifecycle operations. Account suspension, role changes, project
deletion, and entitlement reset use bounded service operations. Destructive
cleanup is resumable and removes related archival data only after an
authorized request.

## Route and implementation sources

- src/oryxenai/auth/api.py and src/oryxenai/auth/admin/api.py define auth
  and administrative routes.
- src/oryxenai/api/dependencies.py defines route authorization dependencies.
- src/oryxenai/api/routes/__init__.py defines registered product APIs.
- src/oryxenai/auth/worker_fence.py defines durable-work authorization.
- src/oryxenai/auth/admin/ defines audited lifecycle and cleanup.
