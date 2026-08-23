# Current system authentication surface

This is a source-grounded audit of the checkout before auth implementation. It
describes what must be protected; it is not a claim that protection exists.

## Current trust model

OryxenAI currently has no user identity or authorization layer. A caller can
create a portfolio session, list recent sessions, read a session by UUID, and
call each stage by supplying that UUID. Repositories load by ID alone.

Relevant source locations:

- `src/oryxenai/main.py` installs logging, security headers, health, APIs, and
  optional developer web routes, but no auth boundary.
- `src/oryxenai/api/dependencies.py` builds repositories/services but has no
  `CurrentUser`, owner, onboarding, or admin dependency.
- `src/oryxenai/api/routes/sessions.py` creates, lists, and retrieves global
  sessions.
- `src/oryxenai/db/models/portfolio_session.py` has no owner column.
- `src/oryxenai/db/repositories/portfolio_sessions.py` selects by UUID and
  lists globally.
- `src/oryxenai/web/static/app.js` stores a selected session UUID in
  `sessionStorage`; its central `fetchJson()` sends no auth token.
- `src/oryxenai/web/static/app.js` calls health, agent, session, and system APIs
  immediately on `DOMContentLoaded`, before identity is known.
- `src/oryxenai/preview/gateway.py` intentionally serves an opaque preview host
  without app identity or cookies.

Adding login UI without changing those paths would leave an IDOR: any signed-in
user who learns another UUID could read or mutate that portfolio.

## Route inventory and required posture

| Current surface | Examples | Required posture |
| --- | --- | --- |
| Health | `/health/live`, `/health/ready` | Public and minimal; no secrets or user state. |
| Web entry | `/` | Public controller that resolves sign-in/onboarding/app state. |
| Static files | `/static/*` | Public; CSP-constrained and cacheable as appropriate. |
| Auth callback | proposed `/auth/callback` | Public HTML shell; completes Supabase session then calls protected `/me`. |
| Session API | `/api/v1/sessions*` | Authenticated; one owned project for normal users, bounded all-project view for admins. |
| Agent stages | `/sessions/{id}/{stage}` | Authenticated owner-or-admin on every read and write. |
| Run history | `/sessions/{id}/runs` | Owner-or-admin; mock execution absent in production. |
| Registry/model metadata | `/agents`, `/model-profiles` | Only safe product options for normal users; detail is admin/dev-only. |
| System diagnostics | `/system/status`, `/system/worker-probes/*` | Admin-only except minimal health. |
| Build fixture | fixture APIs and web pages | Development-only and admin-only when enabled. |
| Code Generator development harness | `/development/code-generator/*`, `/code-generator-development` | Absent in production; admin/developer-only locally. |
| Stable preview | preview gateway origin | Opaque unlisted capability unless a later decision adds signed private previews. |

## Browser boot order that must change

The future order is:

1. Load the pinned Supabase browser client.
2. Resolve the current Supabase session.
3. If signed out, do not call protected APIs; show `/sign-in`.
4. If signed in, send the access token to `GET /api/v1/me`.
5. If the verified identity is not approved, show access-not-approved and do
   not create local user/project/job state.
6. Complete username onboarding when required.
7. Only then load the owner-scoped portfolio workspace.
8. A remembered session ID may improve navigation but never grants access.
9. On sign-out, stop polling, clear rendered state and remembered session ID,
   call Supabase sign-out, and replace the page with `/sign-in`.

The existing `fetchJson()` helper is the central integration point. It should
obtain the current Supabase access token, add `Authorization: Bearer`, refresh
once after a 401, then fail closed. Do not manually copy tokens into custom
storage or log them.

## Persistence implications

`portfolio_sessions` is the aggregate root for stage state and agent runs.
Adding an owner lets child records inherit authorization through the session.
Code Generator production runs already reference a portfolio session.

The accepted migration policy is:

- add owner and explicit legacy-quarantine state;
- mark every existing unowned session legacy/admin-only;
- require every new product session to have an owner; and
- never infer ownership from names, JSONB, email-like text, or first login.

Direct run/job/source/preview identifiers must join back to an authorized
session. Protecting only `/sessions/{id}` is insufficient.

## Durable worker boundary

A browser token authorizes an API request, not work that runs later:

1. API verifies the JWT, resolves the local user, checks role/status/ownership,
   enforces admission and quota, then creates the run/job.
2. Persist the owner and initiating actor on durable work.
3. Worker reloads current session/user state before finalization.
4. If ownership changed or the user/session is suspended, deleting, missing, or
   legacy-quarantined, fail closed and do not publish output.

Payload identity is diagnostic only. Database relationships are authoritative.
Workers do not call Supabase to recreate a historical browser authorization
decision.

## Preview boundary

Generated code remains on a separate origin with no application credentials.

- The authenticated app decides who may discover/control a preview URL.
- The preview host is opaque, unlisted, `noindex`, and restrictively headed.
- Anyone holding the exact URL can open it under the accepted v1 capability
  model.
- Project deletion first revokes the active preview pointer, then cleans stored
  objects.
- Never forward Supabase tokens/cookies or expose the application origin to
  generated JavaScript.

Strict private previews remain a separate future design.

## Deployment implications

Prefer one application origin serving Jinja, static assets, and `/api/v1`.
Splitting the frontend adds CORS and callback complexity without helping this
small deployment. The preview origin remains separate.

Auth does not remove the need for API, one-shot migration, durable worker,
PostgreSQL, private object storage, and a shared preview gateway. The existing
deployment documents remain authoritative:

- [Free-host deployment contract](../code-generator-architecture/free-host-deployment.md)
- [Live preview and deployment](../code-generator-architecture/live-preview-and-deployment.md)
