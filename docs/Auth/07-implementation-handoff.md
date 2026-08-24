# Implementation handoff

This is the accepted architecture handoff and remains the boundary for the
full authorization project. Phases 1, 2, and 3 of the execution plan are now
implemented: the auth boundary, local identity/capacity foundation, `/me` API,
username onboarding, session ownership/legacy quarantine, route policy,
authenticated browser boot, one-session/variant/success entitlement, durable
owner/actor worker fencing, global generation admission, and verified preview
finalization are in the repository. Administrator lifecycle, full
multi-account browser acceptance, and production deployment remain Phase 4;
follow [10-implementation-plan.md](10-implementation-plan.md) for the
remaining deferred work.

## Scope statement

Implement Supabase Google-only authentication for OryxenAI's existing
Jinja2/vanilla-JavaScript frontend and FastAPI/PostgreSQL backend. Add an
application allowlist, maximum 15 normal users, two bootstrap administrators,
unique username onboarding, database-authoritative roles/status, owner
isolation, one-project/one-variant/one-promoted-success policy, audited admin
operations, deployment-safe configuration, tests, and runbooks. Preserve the
durable worker and separate generated-preview trust boundary.

## Confirmed prerequisites

- Supabase Auth selected; Clerk rejected.
- Development Supabase project and Google provider configured.
- Local provider URL and keys present in git-ignored `.env`.
- Two distinct bootstrap administrator entries present.
- One separate normal test identity is privately allowlisted and is a Google
  OAuth test user.
- Online Auth settings, Google provider, JWKS, and OAuth initiation verified.
- Strict prerequisite result: `0 failures, 0 warnings`.
- Existing sessions will be legacy-quarantined.
- AWS and production projects are intentionally not created.

Pending after the local Phase 3 implementation: complete the real Google
callback, onboarding, normal-user, and administrator multi-account browser
flows in the Phase 4 acceptance gate. Administrator lifecycle APIs, production
resources, and deployment remain intentionally uncreated.

## Work packages

### 1. Configuration and dependencies

- Add `AuthConfig` with provider, required mode, issuer/audience, exact origins,
  paths, 15-user limit, and one-project/variant policy.
- Add `SUPABASE_URL`, publishable key, secret key, bootstrap admins, and normal
  allowlist to settings with redacted validation.
- Fail production readiness on missing/mismatched auth settings or localhost.
- Pin a high-quality JWT/crypto library and official Supabase browser client.
- Commit lockfiles and serve the pinned browser bundle locally.
- Add deterministic test auth configuration that cannot activate in production.
- Update CSP and reverse-proxy scheme/origin handling.

Likely areas: `.env.example`, `pyproject.toml`, `uv.lock`, a small checked-in web
package/lock/build script, `config/app*.toml`, `core/settings.py`, doctor/health,
and settings tests.

### 2. Database migration and domain model

Before SQL authoring, load the Supabase/PostgreSQL best-practice skill.
Continue using Alembic; do not introduce Supabase declarative migrations.

Add:

- `app_users` with immutable `supabase_user_id`, normalized verified email,
  username, role, active/suspended/deletion-pending/deleted status, safe display
  fields, timestamps, and a minimal deleted-identity tombstone;
- `app_user_capacity` singleton to serialize the 15-normal-user admission gate;
- `portfolio_entitlements` for one session, bound variant/run, and success;
- `admin_audit_events`;
- `portfolio_sessions.owner_user_id` plus explicit legacy quarantine;
- owner/actor bindings on durable work needed for finalization fencing; and
- indexes, checks, foreign keys, deletion behavior, and concurrency constraints.

Migration marks all existing sessions legacy/admin-only and never assigns them
to the first login. Review Supabase Data API exposure and revoke browser roles
from business tables; add RLS only as defense in depth, not as a substitute for
FastAPI ownership.

### 3. Authentication/current-user boundary

- Add `src/oryxenai/auth/` for token verification, provider client, domain
  projection, admission, and error types.
- Verify exact Supabase issuer/audience/signature/algorithm/key/expiry/subject.
- Bound JWKS caching and refresh once on unknown key ID.
- Resolve verified Auth identity on first `/me` before email admission.
- Bootstrap the two admins; admit only normal allowlist entries; enforce 15
  normal accounts transactionally.
- Store no Google/provider token and never authorize from `user_metadata`.
- Add shared `CurrentUser`, approved/onboarded, owner, and admin dependencies.
- Return safe 401/403/404/409/429/503 errors.

### 4. Username and `/me`

- `GET /api/v1/me` performs synchronous JIT provisioning and returns a safe
  user/role/onboarding/entitlement/session projection.
- `PUT /api/v1/me/username` validates and atomically claims the accepted
  lowercase 3-30 character username.
- Normalize reserved names and concurrent conflict behavior.
- Repeated identical claim is idempotent; rename is denied for normal v1 users.
- Do not add a provider webhook unless a later proven requirement needs one.

### 5. Ownership retrofit

Implemented in Phase 2 by migration `0015_portfolio_ownership`, explicit
repository scopes, `PortfolioAccess`, route inventory coverage, and product /
developer browser boot integration.

Inventory routes again at implementation time. Protect:

- session create/list/get;
- Discovery, Content Architect, Visual Design Director, Build Preparation, and
  Code Generator routes;
- run history, attempts, jobs, events, plan, acquisition, source, quality,
  verification, and preview metadata;
- model/agent metadata and system diagnostics;
- fixture/development surfaces; and
- all web shells and admin APIs.

Use owner-scoped repository/service methods. Direct nested IDs must prove their
session owner. Development APIs are absent in production, not merely hidden.

### 6. Quota, capacity, and durable generation

Implemented in Phase 3 with migration `0016_auth_entitlements_worker_fencing`,
the `PortfolioEntitlementRepository`, durable authorization snapshots,
`WorkerAuthorizationFence`, global execution-lane claim policy, and central
preview finalization. The normal-user retry/regenerate/success/read-only rules
are server-enforced; provider credit exhaustion is redacted and non-retryable
for the current attempt.

- One normal user admission slot among 15; admins excluded.
- One idempotent portfolio session per normal user.
- Bind first Code Generator run/design variant transactionally.
- Retry only that run/variant; deny normal regenerate.
- Consume success only during verified active-preview promotion/reconciliation.
- Freeze normal mutations after success.
- Bind owner and initiating actor to jobs/runs.
- Worker rechecks current local owner/status/deletion before publishing.
- Enforce one executing generation job in deployment policy.
- Preserve external model-credit fail-closed behavior and no expensive fallback.

### 7. Browser UI and controller

Phase 1-3 browser boot is integrated with the existing first-three-agent
workspace: `/api/v1/me` resolves the server-selected session and safe
entitlement projection before `app.js` loads; normal users receive read-only
controls after success and no developer/regenerate controls. The temporary
`/admin` shell is read-only until Phase 4.

- Add public sign-in and callback shells, onboarding, protected app controller,
  access-not-approved/account-unavailable states, and admin shell.
- Integrate the pinned Supabase JS client and central bearer-token fetch helper.
- Do not call protected APIs before Supabase session plus `/me` resolve.
- Remove auth artifacts from callback history.
- Restore only the owner-scoped session.
- Clear timers/data/session pointer on sign-out.
- Hide normal-user developer/new/regenerate controls.
- Preserve accessibility, focus, responsive behavior, and safe errors.

Do not migrate the frontend to React/Next.

### 8. Admin lifecycle

- Bounded user/project/audit lists.
- Local suspend first, then Supabase provider revoke/ban.
- Restore through explicit provider plus local transition.
- Delete project with job fencing, preview revocation, storage cleanup, and
  database cascade.
- Delete user as a resumable multi-step operation.
- Retain a minimal deleted email/subject tombstone so an unchanged allowlist
  cannot silently re-admit a newly recreated Supabase identity.
- Quota reset with explicit current-project handling.
- Prevent last-admin deletion/demotion and unsafe self-actions.
- Audit every mutation without secrets or intake content.

### 9. Verification and runbooks

- Deterministic unit/API tests use local signed JWT fixtures/dependency
  injection and never call Google.
- PostgreSQL tests cover migration, unique subject/username, capacity race,
  entitlement race, success finalization, ownership, deletion, and audit.
- Browser tests cover signed-out boot, callback controller, onboarding,
  returning user, two-user isolation, completed read-only state, admin, and
  sign-out/back.
- Run the redaction-safe live prerequisite checker.
- Manually smoke both admins and the already configured separate normal account
  through real Google in a top-level browser.
- Deployment smoke remains a later phase with production Supabase/Google/AWS.

## Required test matrix

### Token and admission

- valid, missing, malformed, expired, future, wrong issuer, wrong audience,
  wrong algorithm, unknown key, invalid signature, and missing subject;
- JWKS cache/rotation and provider outage;
- bootstrap admin, approved normal user, unapproved identity, duplicate login;
- deleted-but-still-allowlisted identity remains denied until audited readmission;
- normal-user capacity at 14/15/16 and concurrent admission;
- no authorization from `user_metadata`.

### Authorization

- normal A, normal B, admin across every route family;
- foreign session/run/job/source/preview IDs return 404;
- onboarding/suspended/deletion-pending policies;
- system/dev/fixture production exclusion;
- logs/errors redact tokens, keys, allowlists, cookies, and OAuth artifacts.

### Portfolio policy

- idempotent one-session creation;
- first-run binding and double-start race;
- same-variant retry versus new-variant regeneration;
- failure does not consume success;
- exactly-once success binding at promoted active preview;
- post-success read-only behavior;
- admin unlimited bypass, reset, deletion, and audit;
- last-admin safety.

## Definition of done

Auth is complete only when:

- production configuration fails closed and no secret is committed/logged;
- Google callback works at the configured HTTPS production origin;
- unapproved identities create no product state;
- two admins and one separate normal user pass live browser flows;
- username onboarding is unique and race-safe;
- no current resource is accessible by foreign IDs;
- 15-normal-user capacity and two-admin exclusion are proven;
- one project/variant/promoted success semantics are proven;
- workers cannot finalize for deleted/suspended/reassigned ownership;
- admin lifecycle and last-admin safeguards are proven;
- source, tests, migration, browser, provider, database, worker, storage, and
  preview evidence are reported separately;
- docs and decision/change logs are truthful; and
- task-owned work is committed locally and not pushed unless requested.

## Non-goals

- passwords, password reset, email OTP, phone/SMS, passkeys, or app-managed MFA;
- teams/organizations or social account merging;
- public registration;
- normal self-delete or username rename;
- billing/subscriptions;
- bulk wipe;
- private signed previews;
- frontend framework migration;
- serverless replacement of the durable worker;
- cloud deployment during the auth implementation; or
- an always-on SLA from free services.
