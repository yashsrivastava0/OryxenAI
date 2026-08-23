# Current system authentication surface

This is a source-grounded audit of the current checkout. It explains what the
future auth implementation must protect; it is not a claim that any protection
already exists.

## Current trust model

OryxenAI currently has no user identity or authorization layer. The caller can
create a portfolio session, list recent sessions, read a session by UUID, and
call each stage by supplying that UUID. The repositories load by session ID
alone.

Relevant source locations:

- `src/oryxenai/main.py` installs request IDs, logging, security headers, health,
  API routes, and optionally the developer web UI. It has no auth middleware.
- `src/oryxenai/api/dependencies.py` builds repositories/services but has no
  `CurrentUser`, owner, or admin dependency.
- `src/oryxenai/api/routes/sessions.py` creates, lists, and retrieves global
  sessions.
- `src/oryxenai/db/models/portfolio_session.py` has no owner column.
- `src/oryxenai/db/repositories/portfolio_sessions.py` selects only by UUID and
  lists sessions globally.
- `src/oryxenai/web/static/app.js` stores a selected session UUID in
  `sessionStorage` and its central `fetchJson()` helper sends no auth token.
- `src/oryxenai/preview/gateway.py` deliberately serves the active artifact by
  opaque preview host and does not receive app identity or cookies.

The immediate vulnerability after adding multiple real users would be an IDOR
(insecure direct object reference): a valid user who learns another session UUID
could request or mutate it unless every lookup is owner-scoped.

## Route inventory and required future posture

| Current surface | Examples | Future posture |
| --- | --- | --- |
| Health | `/health/live`, `/health/ready` | Public, minimal response; never expose secrets or user state. |
| Web homepage | `/` | Public sign-in entry or redirect; authenticated users continue to onboarding/app. |
| Static files | `/static/*` | Public, immutable/cacheable as appropriate. |
| Session API | `/api/v1/sessions`, `/api/v1/sessions/{id}` | Authenticated; normal users see only their one project, admins may see all. |
| Agent stages | `/sessions/{id}/discovery`, `content-architect`, `visual-design-director`, `build-preparation`, `code-generator` | Authenticated owner-or-admin for every read and write. |
| Run history | `/sessions/{id}/runs` | Authenticated owner-or-admin; mock execution absent in production. |
| Registry/model metadata | `/agents`, `/model-profiles` | Normal product UI gets only necessary safe options; detailed provider/developer metadata is admin/dev-only. |
| System diagnostics | `/system/status`, `/system/worker-probes/*` | Admin-only except the minimal health routes. |
| Build fixture | API and `/build-preparation-fixture*` web routes | Development-only and admin-only when enabled. |
| Code Generator development harness | `/development/code-generator/*`, `/code-generator-development` | Absent in production; admin/developer-only locally. |
| Stable generated preview | preview gateway origin | Retain the current opaque, unlisted capability URL unless a later decision explicitly pays the complexity of private signed access. |
| Auth webhook | proposed `/api/v1/auth/webhooks/clerk` | Public network route but signature-verified; never protected by user login. |

## Browser behavior that must change

The current app boots immediately, checks infrastructure, lists all sessions,
and restores any UUID found in `sessionStorage`. Auth must change that order:

1. Load Clerk and resolve signed-in state.
2. If signed out, do not call protected APIs and render/redirect to sign-in.
3. If signed in, obtain a short-lived session token and call `/api/v1/me`.
4. Complete username onboarding when required.
5. Only then restore the remembered session. The backend must still verify
   ownership; browser storage is never authority.
6. On sign-out, clear the remembered OryxenAI session UUID, polling timers,
   rendered stage data, and Clerk session, then return to `/sign-in`.

The existing `fetchJson()` helper is a useful single integration point. It can
attach `Authorization: Bearer <Clerk session token>`, retry once after a token
refresh on a 401, and then fail closed to sign-in. Tokens must stay in Clerk's
memory/cookie mechanisms and must not be copied into `localStorage` or logged.

## Persistence implications

`portfolio_sessions` is the aggregate root for agent runs and session-stage
JSONB. Adding an owner there allows existing child tables to inherit access via
their session relationship. Code Generator runs already optionally reference a
portfolio session, so production run access can be authorized through the
session.

Migration must explicitly handle existing unowned development data. Safe
choices are:

- assign named legacy sessions to an admin during a controlled migration; or
- quarantine them as legacy/system-owned and expose them only to admins.

Never make all old rows visible to the first user who signs in. Do not guess
ownership from a session name or email-like text inside JSONB.

## Durable worker boundary

The API and worker are separate processes. The browser's Clerk token is valid
for the API request, not for a job that may execute minutes later. Correct
authorization therefore has two stages:

1. API: verify token, load `app_users`, authorize session ownership/role, enforce
   quota, and only then create the run/job.
2. Worker: use trusted database IDs, verify the session still belongs to the
   owner bound at enqueue time and is not deleting/suspended, then apply output
   with the existing revision/attempt fencing.

The job payload may echo an `owner_user_id`/`actor_user_id` for diagnostics, but
the database relationship is authoritative. A payload value alone must never
grant access.

## Preview boundary

The checked-in preview architecture intentionally uses a separate registrable
origin with no app cookies, user identity, or API access. That isolation is a
security feature for generated code. The smallest compatible auth design is:

- the authenticated app API decides whether a caller may learn/control a
  session's stable preview URL;
- the preview host remains opaque and unlisted, with `noindex` and restrictive
  headers;
- anyone who receives the exact preview URL can open it;
- deleting a project removes its active pointer so that the stable URL stops
  serving it, followed by object-retention cleanup.

Strictly private previews would require a separate signed-capability/cookie
design at the gateway. Do not accidentally forward Clerk cookies or give
generated JavaScript access to the application origin.

## Deployment facts that affect auth

The current topology needs an API, migration step, durable worker, managed
PostgreSQL, private object storage, and a preview gateway. Auth works best on
the same origin as the Jinja frontend and FastAPI API; splitting a Vercel
frontend from a Render API adds CORS, two deployments, token forwarding, and
domain configuration without helping this small app.

For the first deployed auth implementation, prefer one app origin such as
`https://app.example.com` serving Jinja, static JS, and `/api/v1`. The separate
preview origin remains intentionally unauthenticated by Clerk.

The repository's existing deployment contract remains authoritative for the
worker and preview topology:

- [Free-host deployment contract](../code-generator-architecture/free-host-deployment.md)
- [Live preview and deployment](../code-generator-architecture/live-preview-and-deployment.md)
