# User flow and route contract

## Roles and state

There are only two product roles:

- `user`: owns one portfolio workspace and one design variant.
- `admin`: may operate on any user/project and is quota-exempt.

An authenticated account has these effective access states:

- `onboarding_required`: derived when identity exists but the unique username
  has not been chosen.
- `active`: normal access.
- `suspended`: sign-in identity may exist, but OryxenAI denies product access.
- `deletion_pending`: deny access while idempotent cleanup completes.

Role, persisted status, and the username used to derive onboarding state come
from PostgreSQL on every protected request, not from query parameters, browser
state, Google profile fields, or client-writable metadata.

## Minimal screen set

### 1. Sign in (`/sign-in`, with `/` as entry)

Show:

- OryxenAI name and one-sentence purpose;
- one **Continue with Google** action using Clerk's prebuilt sign-in view;
- loading, provider-unavailable, canceled, and blocked-account states;
- a short privacy statement; the final external production homepage/sign-in
  must link to the published privacy policy and terms required by the chosen
  OAuth/provider configuration.

Do not show password fields, a separate sign-up decision, model choices,
session UUIDs, or infrastructure diagnostics.

If Clerk reports an active session, resolve `/api/v1/me` and redirect to
`/onboarding` or `/app`. Never render the app and then discover the user is
signed out.

### 2. Username onboarding (`/onboarding`)

This is shown only for a newly provisioned user without a username. Display the
verified Google display name/avatar as optional context and ask for one app
username.

Recommended username contract:

- lowercase ASCII only;
- 3-30 characters;
- first/last character alphanumeric;
- interior characters may be letters, numbers, `_`, or `-`;
- stored in normalized lowercase form under a database unique constraint;
- reserved: `admin`, `api`, `app`, `auth`, `health`, `preview`, `settings`,
  `static`, `support`, `system`, and product/brand-confusing variants;
- no email address used as a fallback username;
- one choice during onboarding; later rename is admin-only in v1.

The server is authoritative. Client availability checks improve UX but do not
reserve a name. Submission handles a concurrent unique conflict with `409
USERNAME_TAKEN` and suggests alternatives without revealing another user's
email or identity.

### 3. Portfolio workspace (`/app`)

This becomes the existing Discovery homepage. On load:

- resolve the authenticated application user;
- fetch only the caller's portfolio session;
- create/bind the one session lazily on the first meaningful Discovery send,
  or explicitly through one idempotent **Start portfolio** action;
- resume the exact session across refreshes;
- show stage progress, failures, retry, and the final stable preview;
- hide developer diagnostics from normal users.

A successful normal-user portfolio shows a clear completed/read-only state. It
does not show **New portfolio** or **Regenerate**. A retry action is shown only
when the current same-variant run is retryable.

### 4. Admin console (`/admin`)

Keep it small:

- counts and health summary;
- users: username, masked email, role/status, created/last seen, quota state;
- projects: owner, stage status, job status, preview state;
- actions: suspend/restore, delete project, reset quota, delete user;
- explicit confirmation for destructive actions;
- audit list for admin mutations.

Normal users get a 404 or safe redirect for the page and 403 for admin APIs. Do
not ship a bulk **delete everything** control; an admin can delete any resource
one target at a time, which preserves full authority without one-click
catastrophe.

## End-to-end flows

### New user

```text
GET / or /sign-in
  -> Continue with Google
  -> top-level Google/Clerk redirect
  -> return to /auth/continue
  -> Clerk session resolves
  -> GET /api/v1/me (JIT provision by verified Clerk subject)
  -> username missing
  -> /onboarding
  -> PUT /api/v1/me/username
  -> /app
  -> start/resume Discovery
```

The bootstrap API fetches Clerk's backend user only when no local subject row
exists, verifies the primary email, applies the two-email admin bootstrap if
matched, creates the local user, and returns a safe application projection.
Webhook timing is not on this critical path.

### Returning user

```text
GET /
  -> Clerk session active
  -> GET /api/v1/me
  -> active + username present
  -> /app
  -> GET /api/v1/sessions (owner-scoped)
  -> resume one session and its durable stage state
```

If the session expired, redirect to sign-in with a validated relative return
path. If the account is suspended/deleting, show the corresponding safe
account state and do not call project APIs.

### Admin

The first two admin identities follow the new-user flow, but their verified
emails match the server-side bootstrap allowlist and their persisted role is
`admin`. `/app` offers normal portfolio work with no quota. `/admin` offers
cross-user operations.

Admin access is still identity-bound and audited. “Full authority” does not
mean bypassing token verification, accepting role values from the browser, or
letting generated preview code reach admin APIs.

### Sign out

1. Stop all polling/timers.
2. Clear rendered user/project data and the stored selected session UUID.
3. Call Clerk sign-out.
4. Navigate with replacement to `/sign-in`.
5. Back navigation must not reveal cached sensitive page state; protected API
   calls return 401 and the app clears again.

## Proposed web routes

| Route | Access | Behavior |
| --- | --- | --- |
| `/` | Public | Resolve Clerk state; signed out -> sign-in, onboarding -> `/onboarding`, active -> `/app`. |
| `/sign-in` | Public | Mount the Clerk prebuilt sign-in view. Signed-in users leave this route. |
| `/auth/continue` | Public shell | Complete Clerk redirect/session tasks, then resolve `/api/v1/me`. Never accept an arbitrary external next URL. |
| `/onboarding` | Authenticated shell | Unique username form; no portfolio APIs until complete. |
| `/app` | Authenticated + onboarded | Owner workspace. |
| `/admin` | Admin | Minimal administrative console. |
| `/signed-out` (optional) | Public | Short confirmation then link to sign in; `/sign-in` is sufficient if omitted. |

The HTML shells contain no private state. APIs remain protected even if a user
manually loads a shell route or disables JavaScript.

## Proposed API routes

| Method/path | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/me` | Authenticated | Verify token; JIT-provision if needed; return safe app user, onboarding, role, quota, and owned session summary. |
| `PUT /api/v1/me/username` | Authenticated, onboarding | Atomically claim a normalized username. |
| `POST /api/v1/auth/webhooks/clerk` | Verified webhook signature | Reconcile `user.updated`/`user.deleted`; never required for immediate login. |
| existing `/api/v1/sessions*` | Authenticated | Owner-scoped create/list/get; admin scope explicitly selected server-side. |
| existing stage/run APIs | Owner or admin | Preserve current state machines after authorization. |
| `GET /api/v1/admin/users` | Admin | Bounded/paginated user list. |
| `POST /api/v1/admin/users/{id}/suspend` | Admin | Mark suspended and ban/revoke in Clerk. |
| `POST /api/v1/admin/users/{id}/restore` | Admin | Restore app and Clerk access. |
| `DELETE /api/v1/admin/users/{id}` | Admin | Start idempotent identity/data cleanup. |
| `GET /api/v1/admin/projects` | Admin | Bounded project list. |
| `DELETE /api/v1/admin/projects/{id}` | Admin | Cancel work, revoke preview pointer, clean storage, delete aggregate. |
| `POST /api/v1/admin/users/{id}/quota-reset` | Admin | Explicitly allow a new normal-user variant after cleanup/review. |
| `GET /api/v1/admin/audit-events` | Admin | Recent admin mutations with safe metadata. |

Exact route names may be refined in the implementation plan, but the access
semantics must not change.

## Redirect rules

- Use relative application paths for `return_to`; allow only a small set of
  routes or require a leading single `/` with no scheme/host/backslash.
- Never reflect a full user-supplied URL into an auth redirect.
- After sign-in, onboarding wins over the requested destination.
- After onboarding, use the validated destination or `/app`.
- A user visiting `/admin` without admin role goes to `/app` with a safe notice;
  the API response remains 403.
- A signed-in suspended user goes to an account-unavailable state, not an
  infinite `/sign-in` loop.

## API error contract

Use the repository's existing safe error envelope and request ID. Recommended
codes:

| HTTP | Code | Meaning / UI response |
| --- | --- | --- |
| 401 | `AUTH_REQUIRED` / `AUTH_INVALID` | Refresh Clerk token once; then clear and go to sign-in. |
| 403 | `ACCOUNT_SUSPENDED`, `ONBOARDING_REQUIRED`, `ADMIN_REQUIRED` | Show the precise allowed recovery action. |
| 404 | existing not-found code | Missing or foreign-owned resource; do not reveal which. |
| 409 | `USERNAME_TAKEN` | Stay on onboarding and suggest another name. |
| 409 | `PORTFOLIO_LIMIT_REACHED` | Resume/show the one project. |
| 409 | `GENERATION_VARIANT_LOCKED` | Same-variant retry may be allowed; new regeneration is not. |
| 409 | `PORTFOLIO_ALREADY_SUCCEEDED` | Show read-only final portfolio. |
| 429 | `AUTH_RATE_LIMITED` | Back off and show retry guidance; no tight loop. |
| 503 | `AUTH_PROVIDER_UNAVAILABLE`, existing readiness errors | Preserve local app state and offer bounded retry. |

Never return a Clerk secret, raw token, authorization header, cookie, Google
access token, or another user's email in an error.
