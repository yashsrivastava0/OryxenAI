# User Flows, Browser Integration & Route Contract

Status: **Implemented**. This document specifies the user experience, browser lifecycle, controller state machine, attached/detached pipeline modes, and the authoritative FastAPI route catalog.

---

## Roles and Account States

### Roles
- `user`: Admitted normal user. Bound to exactly one portfolio session, one Code Generator design variant, and at most one verified promoted success.
- `admin`: Platform administrator. Exempt from normal-user portfolio quotas; authorized across all user accounts, active sessions, and quarantined legacy sessions.

### Account States
- `onboarding_required`: Admitted Google identity without an OryxenAI username.
- `active`: Normal active user or administrator with product access.
- `suspended`: Identity recognized but all platform and API operations are denied.
- `deletion_pending`: Account queued for idempotent multi-step deletion; access denied.
- `deleted`: Account tombstone retained to record deletion history and block silent re-registration.

Authorization decisions are evaluated against PostgreSQL on every protected request. Client-supplied `user_metadata`, Google OAuth profiles, browser storage, and query strings are never used for authorization.

---

## Web Shells and User Experience

All user interfaces are rendered as Jinja2 HTML shells and enhanced with vanilla JavaScript. HTML shells contain no private business state, ensuring security if loaded directly or without JavaScript.

| Path | Access Level | Description & Behavior |
| --- | --- | --- |
| `/` | Public controller | Root dispatcher: verifies Supabase session, routes to sign-in, onboarding, app, or error screens. |
| `/sign-in` | Public | Single **Continue with Google** action. Initiates full-page OAuth redirect. Displays no passwords or model pickers. |
| `/auth/callback` | Public shell | Receives OAuth return, exchanges PKCE code via pinned Supabase client, scrubs URL fragments, and calls `GET /api/v1/me`. |
| `/onboarding` | Authenticated + approved | Form to choose a unique lowercase username (3-30 characters). Blocks portfolio actions until completed. |
| `/app` | Active + onboarded | Main portfolio workspace. Loads owner-scoped session, stage progress, and preview controls. |
| `/admin` | Active + onboarded admin | Administrative console: summary metrics, user/project inventory, audit events, and lifecycle operations. |
| `/access-not-approved` | Public shell | Explanation screen for authenticated Google accounts not admitted by capacity or allowlist. |
| `/account-unavailable` | Public shell | Safe notice for suspended or deleting accounts. Offers sign-out only. |

---

## Browser Controller Algorithm

The browser boot sequence in `auth-controller.mjs` and `app-auth-bootstrap.mjs` enforces a single deterministic controller order across `/`, `/sign-in`, `/auth/callback`, and protected pages:

```text
               +-----------------------------+
               | Page Load / History Restore |
               +-----------------------------+
                              |
              1. Pinned Supabase Client init
              2. Check Supabase Auth Session
                              |
             +----------------+----------------+
             |                                 |
       [No Session]                     [Session Active]
             |                                 |
     Show /sign-in page             Send Bearer to GET /api/v1/me
             |                                 |
             |                   +-------------+-------------+
             |                   |                           |
             |             [HTTP 403 / 409]            [HTTP 200 OK]
             |                   |                           |
             |         ACCESS_NOT_APPROVED:            Check Account
             |          -> /access-not-approved            Status
             |         ACCOUNT_SUSPENDED:                    |
             |          -> /account-unavailable   +----------+----------+
             |                                    |          |          |
             |                               No Username   User       Admin
             |                                    |          |          |
             |                             /onboarding     /app       /app
             |                                                        (or /admin)
             |                                    |          |          |
             +------------------------------------+----------+----------+
                                                  |
                                            On Sign-Out
                                                  |
                                1. Cancel in-flight polling / timers
                                2. Clear rendered DOM & session ID hint
                                3. supabase.auth.signOut()
                                4. location.replace("/sign-in")
```

1. **Client Resolution**: Load the self-hosted pinned client (`auth-client.js`).
2. **Session Verification**: Query active Supabase session. If absent, redirect to `/sign-in`.
3. **Synchronous JIT Admission**: Call `GET /api/v1/me` with the bearer token.
4. **Admission & Status Branching**:
   - `ACCESS_NOT_APPROVED` / `USER_CAPACITY_REACHED`: Navigate to `/access-not-approved`.
   - `ACCOUNT_SUSPENDED` / `ACCOUNT_DELETED`: Navigate to `/account-unavailable`.
   - Missing username: Force redirect to `/onboarding`.
   - Active user: Load `/app`. If an admin explicitly requests `/admin`, load `/admin`.
5. **Session Isolation**: A remembered session ID hint in `localStorage` optimizes navigation but never grants authorization; the backend verifies ownership on every call.
6. **Sign-Out Cleansing**: On logout, stop all active timers, purge in-memory project data, clear the session ID hint, trigger `supabase.auth.signOut()`, and replace the URL with `/sign-in`.

---

## Attached vs. Detached Pipeline Modes

OryxenAI supports two pipeline operational modes via `auth.pipeline_mode` in `config/app.toml`:

### Attached Mode (`auth.pipeline_mode = "attached"`)
- Default for production and Docker environments.
- Every API endpoint requires an authenticated Bearer token.
- Sessions are owned by the authenticated `app_users.id`.
- Protected by `PortfolioAccess` and `WorkerAuthorizationFence`.

### Detached Mode (`auth.pipeline_mode = "detached"`)
- Designed for local development and rapid iteration of the upstream agent pipeline (Discovery → Content Architect → Visual Design Director → Build Preparation).
- Browser does not load Supabase or request Google credentials.
- Discovery preflights and locks the selected model profile.
- Creates detached sessions (`session_mode = "detached"`, `owner_user_id = NULL`, `legacy_quarantined = false`).
- **Restart Pipeline**: Exposes a prominent **Restart Pipeline** button in the UI:
  1. Aborts in-flight polling requests.
  2. Issues `POST /api/v1/sessions/{session_id}/restart` with a new replacement UUID.
  3. The server locks the old session, cancels running jobs, clears associated Build Preparation artifacts and S3/R2 storage, and deletes the session row.
  4. Returns a fresh, empty detached session at Discovery stage.
- Admin APIs and Code Generator production runs remain protected even in detached mode.

---

## API Route Catalog

All business endpoints live under `/api/v1` and use standard JSON envelopes.

### 1. Identity & Onboarding (`src/oryxenai/auth/api.py`)

| Method & Path | Auth Requirement | Purpose |
| --- | --- | --- |
| `GET /api/v1/me` | Valid Bearer JWT | Cryptographically verifies token; performs JIT provisioning or bootstrap admin assignment; returns user profile, role, onboarding status, and entitlement summary. |
| `PUT /api/v1/me/username` | Approved onboarding user | Validates and atomically claims a unique username (`^[a-z0-9][a-z0-9_-]{1,28}[a-z0-9]$`). Rejects reserved words (`admin`, `api`, `app`, `auth`, `health`, `preview`, `settings`, `static`, `support`, `system`). |

### 2. Portfolio Sessions (`src/oryxenai/api/routes/sessions.py`)

| Method & Path | Auth Requirement | Purpose |
| --- | --- | --- |
| `POST /api/v1/sessions` | Active user (or detached) | Creates or resumes an owned portfolio session. For normal users, transactionally locks entitlement and returns the existing session if already bound. |
| `GET /api/v1/sessions` | Active user | Lists recent sessions. Normal users see only their owned, non-quarantined sessions; admins see all recent sessions. |
| `GET /api/v1/sessions/{session_id}` | Owner or Admin (or detached) | Retrieves session status, state machine envelopes, and current revision. |
| `POST /api/v1/sessions/{session_id}/restart` | Detached pipeline mode | Fences and purges a detached session and its build artifacts; returns a clean replacement session. |

### 3. Stage & Agent Execution Routes

All child endpoints verify session ownership via the shared `PortfolioAccess` dependency:
- **Discovery**: `GET/POST /api/v1/sessions/{id}/stages/discovery/*`
- **Content Architect**: `GET/POST /api/v1/sessions/{id}/stages/content-architect/*`
- **Visual Design Director**: `GET/POST /api/v1/sessions/{id}/stages/visual-design-director/*`
- **Build Preparation**: `GET/POST /api/v1/sessions/{id}/stages/build-preparation/*`
- **Code Generator**: `GET/POST /api/v1/sessions/{id}/stages/code-generator/*`
- **Runs & History**: `GET /api/v1/sessions/{id}/runs`

Foreign or nonexistent session IDs return an identical `404 Not Found`.

### 4. Admin Console API (`src/oryxenai/auth/admin/api.py`)

Protected by `require_admin` dependency; requires an active onboarded user with `role=admin`:

| Method & Path | Purpose |
| --- | --- |
| `GET /api/v1/admin/summary` | Overall system metrics, normal user count, capacity limit, and active worker health. |
| `GET /api/v1/admin/users` | Cursor-paginated user list with masked email addresses and entitlement statuses. |
| `GET /api/v1/admin/users/{user_id}` | Detailed projection of a specific user, owned projects, and entitlement records. |
| `GET /api/v1/admin/deleted-identities` | Inventory of deleted-user tombstones. |
| `GET /api/v1/admin/projects` | Cursor-paginated list of active non-legacy portfolio projects. |
| `GET /api/v1/admin/projects/{session_id}` | Detailed project stage history and metadata. |
| `GET /api/v1/admin/legacy-projects` | Cursor-paginated list of pre-auth quarantined sessions. |
| `GET /api/v1/admin/audit-events` | Cursor-paginated audit trail of all administrative actions. |
| `GET /api/v1/admin/operations` | Cursor-paginated inventory of background administrative operations. |
| `GET /api/v1/admin/operations/{operation_id}` | Status, current step, and error details of a specific operation. |
| `POST /api/v1/admin/users/{user_id}/suspend` | Sets local status to `suspended` and calls Supabase Admin API to ban the provider user. |
| `POST /api/v1/admin/users/{user_id}/restore` | Restores account to `active` and unbans user in Supabase Auth. |
| `POST /api/v1/admin/users/{user_id}/delete` | Initiates resumable deletion: fences work, deletes projects, calls Supabase Admin API delete, records tombstone. |
| `POST /api/v1/admin/users/{user_id}/entitlement/reset` | Resets a normal user's entitlement, allowing them to create a new portfolio. |
| `POST /api/v1/admin/users/{user_id}/promote` | Promotes a normal user to `role=admin`. |
| `POST /api/v1/admin/users/{user_id}/demote` | Demotes an admin to `role=user` (checks normal user capacity and enforces single-project limits). |
| `POST /api/v1/admin/deleted-identities/{tombstone_id}/readmit` | Approves readmission of a previously deleted identity. |
| `POST /api/v1/admin/projects/{session_id}/delete` | Fences project, revokes preview capability pointer, deletes storage objects, and removes session row. |
| `POST /api/v1/admin/legacy-projects/{session_id}/delete` | Purges quarantined legacy project. |
| `POST /api/v1/admin/operations/{operation_id}/resume` | Retries an interrupted or failed administrative operation from its last safe step. |
| `POST /api/v1/admin/projects/{session_id}/code-generator/retry` | Triggers admin-authorized Code Generator retry. |
| `POST /api/v1/admin/projects/{session_id}/code-generator/regenerate` | Triggers admin-authorized Code Generator variant regeneration. |

---

## Standardized Error Contract

All authentication and authorization errors return RFC 7807-compatible envelopes with request IDs:

| HTTP Status | Error Code | Description & Client Behavior |
| --- | --- | --- |
| 401 Unauthorized | `AUTH_REQUIRED`, `AUTH_INVALID` | Missing, expired, or invalid Bearer token. Client refreshes token once; on repeated 401, clears storage and navigates to `/sign-in`. |
| 403 Forbidden | `ACCESS_NOT_APPROVED` | Authenticated Google user not permitted by allowlist or open capacity. Client navigates to `/access-not-approved`. |
| 403 Forbidden | `ACCOUNT_SUSPENDED`, `ACCOUNT_DELETED` | Account denied by admin action. Client navigates to `/account-unavailable`. |
| 403 Forbidden | `ADMIN_REQUIRED` | Non-admin caller attempted to access an admin route. Redirects to `/app`. |
| 403 Forbidden | `ONBOARDING_REQUIRED` | User attempted product actions without completing username onboarding. Redirects to `/onboarding`. |
| 404 Not Found | `SESSION_NOT_FOUND` | Returned identically for nonexistent session IDs and foreign-owned sessions to prevent user enumeration. |
| 409 Conflict | `USERNAME_TAKEN` | Requested username already exists. Form remains on `/onboarding`. |
| 409 Conflict | `USER_CAPACITY_REACHED` | The 15-normal-user limit is exhausted during open registration. |
| 409 Conflict | `PORTFOLIO_LIMIT_REACHED` | Normal user attempted to create a second distinct portfolio session. |
| 409 Conflict | `GENERATION_VARIANT_LOCKED` | Normal user attempted to trigger `/regenerate`. Regeneration is forbidden; only `/retry` of the bound variant is allowed. |
| 409 Conflict | `PORTFOLIO_READ_ONLY` | Normal user attempted mutations on a successfully promoted portfolio. GET remains open. |
| 409 Conflict | `AUTHORIZATION_FENCE_REJECTED` | Worker rejected task execution because owner or session was suspended, deleted, or reassigned. |
| 503 Unavailable | `MODEL_PROVIDER_CREDIT_EXHAUSTED` | Upstream LLM provider credit exhausted. Run fails cleanly without consuming the success entitlement. |
| 503 Unavailable | `AUTH_PROVIDER_UNAVAILABLE` | Supabase Auth or JWKS endpoint unreachable. Client backs off and retries. |
