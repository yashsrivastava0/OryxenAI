# User flow and route contract

## Roles and application states

There are two roles:

- `user`: one admitted account, one portfolio, one variant, one verified
  success.
- `admin`: cross-user authority and quota exemption.

Effective local states:

- `onboarding_required`: admitted identity without a username;
- `active`: product access allowed;
- `suspended`: identity may still exist, but all product access is denied; and
- `deletion_pending`: deny access while idempotent cleanup completes.

Role, status, username, admission, ownership, and quota come from PostgreSQL on
every protected request. Supabase `user_metadata`, Google profile data, browser
state, and query parameters are not authorization sources.

Phase 3 adds a database-authoritative entitlement projection to `/me`. Normal
users receive one canonical portfolio session, one bound Code Generator run /
variant, and at most one verified promoted success. The projection is a safe
capability summary only; every mutation reloads the entitlement and current
owner/actor state on the server.

## Minimal screens

### Sign in (`/sign-in`, with `/` as controller)

Show:

- OryxenAI name and one-sentence purpose;
- one **Continue with Google** button;
- safe loading, canceled, provider-unavailable, rate-limited, and denied states;
- a short privacy statement and production privacy/terms links.

The button starts a full-page Supabase Google OAuth redirect. Do not show
passwords, a separate sign-up choice, model selectors, session IDs, or
infrastructure diagnostics.

If a Supabase session already exists, call `/api/v1/me` before rendering private
application data and route to onboarding, app, admin availability, or a denied
state.

### Auth callback (`/auth/callback`)

Complete the Supabase client callback/session restoration, remove auth query or
fragment artifacts from browser history, then call `/api/v1/me`. Refresh and
duplicate callback tabs must be idempotent.

### Username onboarding (`/onboarding`)

Show only to an approved local user without a username. The accepted contract:

- lowercase ASCII;
- 3-30 characters;
- first and last character alphanumeric;
- interior letters, numbers, `_`, or `-`;
- globally unique normalized value;
- no email address fallback;
- reserved names including `admin`, `api`, `app`, `auth`, `health`, `preview`,
  `settings`, `static`, `support`, and `system`;
- normal users cannot rename in v1.

Client availability checks are advisory. The database unique constraint is
authoritative. Concurrent conflict returns `409 USERNAME_TAKEN` without
revealing another identity.

### Portfolio workspace (`/app`)

After onboarding:

- fetch only the caller's portfolio;
- claim one session through an idempotent **Start portfolio** action or first
  meaningful Discovery send; the server returns the same bound session on every
  repeat or concurrent request;
- resume the same session across refreshes;
- show durable stage progress, retryable failures, and the stable preview;
- hide system/developer controls from normal users; and
- after verified success, show a completed read-only state with no **New
  portfolio** or **Regenerate** action. A queued global generation lane,
  same-variant retry, preview-pending state, and safe provider-credit failure
  remain truthful and refresh-safe.

### Admin console (`/admin`)

Phase 4 serves the bounded administrator console. The following lifecycle
surface is implemented behind the administrator dependency:

- counts and health summary;
- paginated users with username, masked email, role/status, admission, and
  entitlement state;
- projects with owner, stage/job/preview state;
- suspend, restore, delete user, delete project, reset entitlement, retry, and
  regenerate actions;
- explicit destructive confirmations; and
- recent safe audit events.

There is no global bulk-wipe button. Full authority is preserved through
targeted audited operations.

## End-to-end flows

### Approved new normal user

```text
GET / or /sign-in
  -> Continue with Google
  -> Supabase / Google full-page redirect
  -> /auth/callback
  -> Supabase session resolves
  -> GET /api/v1/me
  -> verify Supabase identity + verified email
  -> email is in ORYXENAI_ALLOWED_USER_EMAILS
  -> capacity transaction admits normal user (maximum 15)
  -> username missing -> /onboarding
  -> PUT /api/v1/me/username
  -> /app
```

### Authenticated but unapproved identity

```text
Google/Supabase authentication succeeds
  -> GET /api/v1/me
  -> email is neither bootstrap admin nor normal allowlist
  -> 403 ACCESS_NOT_APPROVED
  -> no app_users row, entitlement, session, run, or job is created
```

### Returning user

```text
GET /
  -> Supabase session active
  -> GET /api/v1/me
  -> local user active + username present
  -> /app
  -> owner-scoped session read
  -> resume durable state
```

### Initial administrators

Each verified Google email in `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` follows the same
flow. First approved login persists `role=admin`; administrators do not consume
the 15 normal-user slots. Both identities require separate Google accounts.

### Sign out

1. Stop polling and pending UI timers.
2. Clear rendered identity/project data and remembered session ID.
3. Call `supabase.auth.signOut()` through the pinned client.
4. Replace navigation with `/sign-in`.
5. Protected APIs return 401 if stale page history is revisited.

## Web routes

| Route | Access | Behavior |
| --- | --- | --- |
| `/` | Public controller | Resolve Supabase session, then route to sign-in, onboarding, app, or denied state. |
| `/sign-in` | Public | Google-only sign-in. Signed-in users leave this route after `/me`. |
| `/auth/callback` | Public shell | Complete provider callback and resolve `/me`; never accept arbitrary external `next`. |
| `/access-not-approved` | Public shell | Safe explanation for an authenticated Google identity that is not admitted; offer sign-out only. |
| `/account-unavailable` | Public shell | Safe suspended/deletion-pending state; offer sign-out/support only. |
| `/onboarding` | Authenticated + approved | Unique username form; no portfolio operations before completion. |
| `/app` | Active + onboarded | Owner workspace. |
| `/admin` | Admin | Administrative console. |

HTML shells contain no private state. APIs remain protected if JavaScript is
disabled or a shell is loaded directly.

Phase 2 owns `/app` from the product web router and keeps `/dev`, fixture
pages, and the Code Generator development page conditional on development
settings. The HTML remains public so direct refresh works, but product and
development JavaScript must resolve the Supabase session and `/api/v1/me`
before loading protected workspace code. A normal user opening `/dev` is
replaced with `/app`; the underlying APIs independently require admin.

## One controller decision for every page load

Keep route behavior deterministic and small. `/`, `/sign-in`,
`/auth/callback`, and every direct protected-page load use the same controller
after the callback (if any) has restored the Supabase session:

1. No Supabase session: clear local project state and replace the current page
   with `/sign-in`. Do not call a protected OryxenAI API.
2. Session present: call `GET /api/v1/me` once with the bearer token.
3. `ACCESS_NOT_APPROVED`: replace with `/access-not-approved`; never create
   local product data.
4. Suspended/deletion-pending/deleted: replace with `/account-unavailable`.
5. Approved but no username: replace with `/onboarding`, regardless of the
   originally requested local page.
6. Active and onboarded: replace with `/app` unless the requested page is
   `/admin` and the local role is admin.
7. Admin: `/app` is still the ordinary landing page; `/admin` is an explicit
   console destination, not a second automatic post-login branch.

Use `location.replace` for auth-state canonicalization so back navigation does
not replay a callback or reveal a previously rendered private page. Preserve at
most one reviewed relative destination (`/app` or `/admin`); reject absolute
URLs, protocol-relative URLs, encoded backslashes, unknown routes, and foreign
origins.

## Refresh, direct URL, and deployment behavior

- FastAPI must serve the corresponding HTML shell for a direct browser request
  to every listed page route; deployment must not depend on a development-only
  SPA fallback.
- Refreshing `/app`, `/onboarding`, or `/admin` reruns the controller before
  private data is requested or rendered.
- Refreshing `/auth/callback` after successful exchange is harmless: restore
  the existing session, remove OAuth artifacts, and route through `/me`.
- A signed-out direct request to `/admin`, `/app`, or `/onboarding` lands on
  `/sign-in`; a non-admin direct request to `/admin` lands on `/app` while its
  admin APIs independently return 403.
- Unapproved or unavailable shells render no email, role, allowlist, project,
  or provider diagnostics.
- Static assets and minimal health endpoints stay public. All business APIs
  under `/api/v1` require the documented identity/authorization dependency.
- Local development permits only the two configured port-8000 origins.
  Production uses one exact HTTPS application origin supplied by configuration
  and allowlisted in Supabase; no localhost or wildcard production redirect is
  accepted.
- The simplest deployment is one application origin serving Jinja shells,
  static assets, and FastAPI APIs. Do not split the frontend onto another host
  merely for auth. Generated previews remain on their separate opaque preview
  origin and do not become trusted application pages.

## API routes

| Method/path | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/me` | Valid Supabase session | Verify identity; approve/bootstrap if configured; return safe local projection. |
| `PUT /api/v1/me/username` | Approved onboarding user | Atomically claim normalized username. |
| `POST /api/v1/auth/sign-out` (optional) | Authenticated | Server-side revocation hook if required by selected Supabase session design. |
| existing `/api/v1/sessions*` | Active + onboarded | One-session normal-user create/list/get; explicit admin scope only. |
| existing stage/run/job/source/preview APIs | Owner or admin | Preserve state machines after authorization. |
| `GET/POST /api/v1/sessions*` | Active onboarded user | Normal users see/create only owned non-legacy sessions; admins see bounded owned and legacy rows. |
| `/api/v1/system/*`, `/api/v1/model-profiles` | Admin | Developer/provider metadata and system diagnostics are not normal-user surfaces. |
| mock/fixture/development APIs | Development admin | Conditionally mounted only when their feature and dev UI are enabled; absent in production. |
| `GET /api/v1/admin/users` | Active onboarded admin | Bounded user list. |
| `POST /api/v1/admin/users/{id}/suspend` | Active onboarded admin | Deny locally and revoke/ban with the current Supabase Admin API. |
| `POST /api/v1/admin/users/{id}/restore` | Active onboarded admin | Restore local/provider access. |
| `POST /api/v1/admin/users/{id}/delete` | Active onboarded admin | Start resumable identity/data cleanup. |
| `GET /api/v1/admin/projects` | Active onboarded admin | Bounded project list. |
| `POST /api/v1/admin/projects/{id}/delete` | Active onboarded admin | Fence work, revoke preview, clean storage, delete aggregate. |
| `POST /api/v1/admin/users/{id}/entitlement/reset` | Active onboarded admin | Explicitly grant a new portfolio/variant after cleanup. |
| `GET /api/v1/admin/audit-events` | Active onboarded admin | Recent safe admin actions. |

Implementation may refine names but not access semantics.

## Redirect rules

- The OAuth `redirectTo` must exactly match a Supabase allowed redirect.
- Application return paths must be relative and allowlisted.
- Never reflect a caller-supplied absolute URL, scheme, host, or backslash.
- Onboarding overrides the requested destination.
- A non-admin who requests `/admin` goes safely to `/app`; the API remains 403.
- Suspended/deleting users reach an account-unavailable state, not a redirect
  loop.
- Development and production origins come from configuration, never scattered
  localhost literals.

## Error contract

Use the existing safe error envelope and request ID.

| HTTP | Code | UI behavior |
| --- | --- | --- |
| 401 | `AUTH_REQUIRED`, `AUTH_INVALID` | Refresh once; then clear and sign in. |
| 403 | `ACCESS_NOT_APPROVED` | Explain that the account is not approved; create no product state. |
| 403 | `ACCOUNT_SUSPENDED`, `ACCOUNT_DELETED`, `ADMIN_REQUIRED`, `ONBOARDING_REQUIRED` | Show the only permitted recovery action. |
| 404 | existing not-found | Same response for missing and foreign-owned objects. |
| 409 | `USERNAME_TAKEN` | Stay on onboarding. |
| 409 | `USER_CAPACITY_REACHED` | No normal-user admission beyond 15. |
| 409 | `PORTFOLIO_LIMIT_REACHED` | Resume the one project. |
| 409 | `GENERATION_VARIANT_LOCKED` | Retry same variant if eligible; no new variant. |
| 409 | `PORTFOLIO_READ_ONLY` | Show the final read-only portfolio; GET remains available. |
| 409 | `ENTITLEMENT_BINDING_CONFLICT` | Fail closed without signing out or exposing foreign state. |
| 409 | `AUTHORIZATION_FENCE_REJECTED` | Record a safe permanent worker denial; do not enqueue successor work. |
| 503 | `MODEL_PROVIDER_CREDIT_EXHAUSTED` | Keep the same run/variant and permit explicit later retry after credit is restored. |
| 429 | `AUTH_RATE_LIMITED` | Back off; no tight retry loop. |
| 503 | `AUTH_PROVIDER_UNAVAILABLE` | Preserve safe local state and offer bounded retry. |

Never return provider secrets, raw tokens, authorization headers, cookies,
Google tokens, allowlist contents, or another user's email.
