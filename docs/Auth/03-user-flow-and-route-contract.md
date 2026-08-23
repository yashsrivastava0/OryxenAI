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
  meaningful Discovery send;
- resume the same session across refreshes;
- show durable stage progress, retryable failures, and the stable preview;
- hide system/developer controls from normal users; and
- after verified success, show a completed read-only state with no **New
  portfolio** or **Regenerate** action.

### Admin console (`/admin`)

Keep it bounded:

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
| `/onboarding` | Authenticated + approved | Unique username form; no portfolio operations before completion. |
| `/app` | Active + onboarded | Owner workspace. |
| `/admin` | Admin | Administrative console. |

HTML shells contain no private state. APIs remain protected if JavaScript is
disabled or a shell is loaded directly.

## API routes

| Method/path | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/me` | Valid Supabase session | Verify identity; approve/bootstrap if configured; return safe local projection. |
| `PUT /api/v1/me/username` | Approved onboarding user | Atomically claim normalized username. |
| `POST /api/v1/auth/sign-out` (optional) | Authenticated | Server-side revocation hook if required by selected Supabase session design. |
| existing `/api/v1/sessions*` | Active + onboarded | Owner-scoped idempotent create/list/get; explicit admin scope only. |
| existing stage/run/job/source/preview APIs | Owner or admin | Preserve state machines after authorization. |
| `GET /api/v1/admin/users` | Admin | Bounded user list. |
| `POST /api/v1/admin/users/{id}/suspend` | Admin | Deny locally and revoke/ban with the current Supabase Admin API. |
| `POST /api/v1/admin/users/{id}/restore` | Admin | Restore local/provider access. |
| `DELETE /api/v1/admin/users/{id}` | Admin | Start resumable identity/data cleanup. |
| `GET /api/v1/admin/projects` | Admin | Bounded project list. |
| `DELETE /api/v1/admin/projects/{id}` | Admin | Fence work, revoke preview, clean storage, delete aggregate. |
| `POST /api/v1/admin/users/{id}/quota-reset` | Admin | Explicitly grant a new portfolio/variant after cleanup. |
| `GET /api/v1/admin/audit-events` | Admin | Recent safe admin actions. |

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
| 409 | `PORTFOLIO_ALREADY_SUCCEEDED` | Show final read-only portfolio. |
| 429 | `AUTH_RATE_LIMITED` | Back off; no tight retry loop. |
| 503 | `AUTH_PROVIDER_UNAVAILABLE` | Preserve safe local state and offer bounded retry. |

Never return provider secrets, raw tokens, authorization headers, cookies,
Google tokens, allowlist contents, or another user's email.
