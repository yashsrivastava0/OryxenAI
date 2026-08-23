# Implementation handoff for the next planning session

This is not an implementation plan approval and contains no completed code. It
defines the bounded work packages and evidence a future plan must cover.

## Recommended scope statement

Implement Clerk Google-only authentication for OryxenAI's existing
Jinja2/vanilla-JS frontend and FastAPI/PostgreSQL backend. Add unique username
onboarding, database-authoritative `user`/`admin` roles, owner isolation for all
session-derived resources, one-project/one-variant/one-success policy for normal
users, unlimited audited admin operations, and deployment-safe configuration,
tests, and runbooks. Preserve the separate durable worker and generated-preview
trust boundaries.

## Planning gate

Before coding, obtain one answer from the owner:

> Is there an owned domain available for the deployed application?

- Yes -> implement Clerk.
- No, and deployment must be zero-spend -> replace only the identity-provider
  slice with Supabase Auth and retain the rest of this design.

Also obtain the two admin Google email addresses through a secret/configuration
channel at deployment time, not in a committed document.

## Work packages the plan must include

### 1. Configuration and dependencies

- Clerk backend SDK pin/lock.
- auth settings with exact allowed origins and fail-closed production
  validation.
- `.env.example` names only; doctor reports presence/shape, never values.
- test dependency overrides/fixtures that cannot activate in production.
- production CSP and reverse-proxy origin/proto behavior.

Likely source areas: `pyproject.toml`, `uv.lock`, `.env.example`,
`config/app*.toml`, `src/oryxenai/core/settings.py`, doctor/health tests.

### 2. Database migration and domain model

- `app_users`, `portfolio_entitlements`, `admin_audit_events`.
- `portfolio_sessions.owner_user_id` and indexes/constraints.
- explicit legacy-session quarantine/assignment.
- models/repositories with owner-scoped methods and concurrency tests.

Load the repository's PostgreSQL best-practice skill before authoring the
migration. Continue using Alembic; do not introduce a second schema tool merely
because Supabase may host PostgreSQL.

### 3. Authentication/current-user boundary

- Clerk request verification with session-token restriction and exact
  authorized parties.
- `CurrentUser` projection and active/onboarding/admin dependencies.
- synchronous JIT provisioning using verified Clerk backend user data.
- safe 401/403/404/409/503 errors.
- cache/reuse SDK configuration without caching stale role/quota decisions.

Likely source areas: a new `src/oryxenai/auth/` package,
`src/oryxenai/api/dependencies.py`, `src/oryxenai/api/errors.py`, app factory and
tests.

### 4. Username onboarding and identity reconciliation

- `/api/v1/me` and atomic username claim.
- reserved/normalized username validation.
- `user.updated`/`user.deleted` webhook with raw-body signature verification
  and event idempotency.
- admin bootstrap from two normalized verified emails.
- no role/quota/owner input fields in user-facing schemas.

### 5. Ownership retrofit across the entire API

Inventory every route again at implementation time. Apply shared owner/admin
guards to sessions, all five production stages, run history, Code Generator
run/preview/source/quality data, and any job endpoint. Make diagnostics/admin or
development-only as documented.

Do not stop after protecting `/sessions`; nested services/repositories and
direct run IDs must also prove ownership.

### 6. Quota and design-variant enforcement

- one normal-user session slot with row locking/idempotency;
- bind first Code Generator run/variant;
- allow `/retry` only on that same run/variant;
- deny `/regenerate` and second starts for normal users;
- consume success only at verified active-preview finalization/reconciliation;
- freeze normal mutations after success;
- admin bypass and explicit quota reset.

This work must integrate with current Code Generator service and promotion
reconciler rather than bolt a counter onto the frontend.

### 7. Browser UI and route controller

- public sign-in, auth continuation, username onboarding, protected app, and
  admin shells;
- official ClerkJS prebuilt sign-in view configured for Google only;
- central fetch token injection/one-time refresh;
- boot-order changes so APIs are not called before auth/onboarding;
- resume only owner-scoped session;
- explicit sign-out cleanup;
- normal-user removal of developer/session-list/new/regenerate controls;
- accessible loading/error/focus behavior.

Keep Jinja2/vanilla JS. A React/Next migration is outside auth scope.

### 8. Admin lifecycle operations

- bounded lists;
- suspend/restore via local status plus Clerk ban/unban;
- delete project with job fencing, preview-pointer revocation, storage cleanup,
  and database cascade;
- delete user as an idempotent multi-step operation;
- quota reset;
- last-admin and self-destructive safeguards;
- audit events and confirmation UI.

Do not expose secrets, raw intake, or bulk wipe in the admin view.

### 9. Verification and deployment runbook

- unit/API/integration/browser tests listed below;
- local real Clerk development smoke (opt-in, no mocks silently substituted);
- production-domain Google smoke;
- exact route, refresh, logout, foreign-ID, quota, admin, cold-start, and delete
  evidence;
- deployment configuration for API/worker/database/object storage/preview;
- rollback that can disable new sign-ins without exposing unprotected routes.

## Test matrix

### Deterministic unit/API tests

- valid/invalid/missing/expired/wrong-origin/wrong-issuer token outcomes;
- JIT provisioning race and safe Clerk failure;
- username normalization/reserved/unique concurrency;
- user/admin/suspended/onboarding dependencies;
- owner A, owner B, admin across every route family;
- all direct run/job/source/preview identifiers;
- normal session/run/success quota state transitions;
- same-variant retry versus new-variant regeneration;
- admin bypass/reset/delete audit;
- webhook signature, replay, ordering, and deletion;
- logs/errors redact headers/cookies/tokens.

Use dependency injection or locally signed test JWT fixtures. Normal test suites
must not call Clerk or Google.

### PostgreSQL integration tests

- foreign keys/cascades and legacy migration behavior;
- unique Clerk subject and username;
- row-lock/double-create and double-start races;
- exactly-once success binding during duplicate promotion reconciliation;
- deletion while jobs are queued/running;
- audit persistence without sensitive content.

### Browser tests

- signed-out landing and no protected fetch before auth;
- automated Clerk development test user/session using Clerk-supported testing
  tools or a deterministic test auth boundary;
- new-user onboarding, conflict, return, refresh, sign-out/back;
- two-user ID isolation;
- normal completed read-only UI and admin console;
- mobile and desktop route/interaction smoke.

Do not automate a real Google password through Playwright. Run real Google OAuth
as a manual development and production smoke; provider bot/security challenges
make it the wrong deterministic CI mechanism.

## Definition of done

Auth is not done until all are true:

- production configuration fails closed and no secret is committed/logged;
- the Google sign-in callback works at the final HTTPS domain;
- first and returning routing works across refresh/direct URLs;
- username onboarding is unique and race-safe;
- every current resource API has owner/admin enforcement;
- normal user gets one project, one variant, one verified success;
- failures retry the same variant without consuming success;
- admin has unlimited portfolio access and tested lifecycle operations;
- durable workers cannot finalize work for deleted/reassigned ownership;
- preview control is authorized and preview capability behavior is documented;
- tests plus visible-browser local and deployed smoke pass;
- migrations, API, worker, database, Clerk, storage, and preview evidence are
  separately reported;
- `CHANGES.md` and a real `DECISIONS.md` entry are updated at implementation
  time, with no frozen provider pricing/test count/model names in status prose;
- task-owned work is committed locally, not pushed unless requested.

## Explicit non-goals for v1

- passwords/password reset;
- phone/SMS auth;
- passkeys or app-managed MFA;
- Clerk Organizations/teams;
- social account linking beyond Clerk defaults;
- public profiles based on username;
- normal-user self-delete/rename;
- billing/subscriptions;
- global bulk-delete button;
- private signed preview sessions;
- frontend framework migration;
- making the durable worker serverless;
- promising an always-on SLA from free tiers.

## Decisions the plan should record when accepted

The research itself should not change `DECISIONS.md`. When the owner accepts an
implementation plan, record at least:

- selected identity provider and owned-domain condition;
- identity/authentication provider versus PostgreSQL authorization boundary;
- Google-only v1 and no app passwords;
- unique app username ownership;
- one-project/one-variant/one-promoted-success semantics;
- two-admin bootstrap and server-authoritative roles;
- unlisted capability-preview boundary versus private preview exclusion.
