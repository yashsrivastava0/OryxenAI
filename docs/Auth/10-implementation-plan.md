# Supabase authentication implementation plan

Status: Phase 1, Phase 2, and Phase 3 execution are implemented in the
checkout. This document remains the repository-grounded plan for the
four-phase authorization project. Phase 4 administrator lifecycle, full
multi-account browser acceptance, and deployment handoff remain deferred. No
production cloud resources were created.

## Four-phase execution map

- **Phase 1 (implemented):** Supabase Google-only identity, JWT/JWKS/provider
  boundary, allowlisted admission, capacity, username onboarding, `/me`, and
  the temporary auth shell.
- **Phase 2 (implemented):** `portfolio_sessions` ownership and legacy
  quarantine, centralized onboarded/owner/admin policy, all existing product
  API route families, admin/development surface gating, and bearer-authenticated
  product/developer browser boot.
- **Phase 3 (implemented):** one-portfolio/variant/success entitlement,
  generation admission, durable owner/actor bindings, global model-generation
  lane, provider-credit fencing, and verified preview finalization.
- **Phase 4 (deferred):** administrator lifecycle/audit, full multi-account
  browser acceptance, and production deployment handoff.

## Current phase boundary

- Preserve the completed Supabase/Google/private `.env` setup; do not recreate
  providers, clients, keys, or test identities.
- Phase 1 owns `src/oryxenai/auth/`, the auth foundation migration,
  configuration, safe `/me` routes, and the temporary browser controller.
- Phase 2 now owns session ownership, route authorization, development-surface
  gating, and authenticated product/developer boot.
- Do not use this completion as authorization for administrator-lifecycle or
  deployment work; those remain Phase 4.
- Reinspect the live repository and provider changelog before later phases;
  never assume a future checkout matches this audit.

## Objective

Add Google-only Supabase authentication and complete OryxenAI authorization:

- application allowlist;
- maximum 15 normal users plus two initial administrators;
- unique username onboarding;
- owner isolation on all resources;
- one normal-user project, variant, and promoted success;
- unlimited audited administrator entitlement;
- durable owner/actor fencing; and
- deployment-safe configuration without deploying AWS now.

## Locked decisions

These do not require another planning choice:

- Supabase Auth, not Clerk.
- Google only; no password/OTP/phone.
- Jinja2 + vanilla JavaScript remain.
- Full-page OAuth redirect and `/auth/callback`.
- FastAPI/PostgreSQL own authorization.
- Allowlist from `ORYXENAI_ALLOWED_USER_EMAILS`.
- Bootstrap admins from `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` after verified
  Supabase identity resolution.
- Two admins do not consume the 15 normal slots.
- Existing unowned sessions become legacy/admin-only.
- Roles/status/ownership/quota never come from `user_metadata` or the browser.
- One normal session, one design variant, retry same variant, one verified
  promoted success, read-only afterward.
- Admins can manage any business resource but cannot bypass state/quality or
  external spending gates.
- Preview URLs remain unlisted capabilities, not private authenticated pages.
- No AWS or production provider resources during this implementation.

## Repository evidence inspected

- `main.py` installs the Phase 1/2 auth, product, and conditional development
  routers.
- `api/dependencies.py` constructs active/onboarded/current-user,
  owner/admin, and admin-only boundaries around existing services.
- session/stage/run routes use the authorized `PortfolioAccess` session.
- `PortfolioSession` and migration `0015` provide owner and legacy state.
- `PortfolioSessionRepository` exposes explicit owned/admin methods; trusted
  internal lookups are now supplemented by Phase 3 worker fencing.
- durable agent/code-generator/job rows bind local owner/actor/context snapshots
  for new portfolio work; Phase 4 admin lifecycle is still deferred.
- `web/routes.py` exposes product `/app` always and developer pages only under
  configured development flags.
- `web/static/app.js` receives the shared authorized request boundary only
  after Supabase session plus `/api/v1/me` resolution.
- development-only fixture and Code Generator surfaces are conditionally
  mounted and must stay absent/admin-only in production.
- migrations are linear through the current checked-in head and are applied by
  the existing one-shot Alembic service.
- tests use deterministic overlays and a dedicated PostgreSQL database.

Re-run this audit immediately before coding because other agents may change the
repository.

## Prerequisite status

Ready:

- Supabase development project and Google provider configured;
- `.env` contains provider URL/keys and two bootstrap entries;
- one separate normal identity is privately present in both the Google test-user
  list and `ORYXENAI_ALLOWED_USER_EMAILS`;
- Auth settings, Google enabled state, JWKS, and OAuth initiation verified;
- strict online prerequisite verification passed with `0 failures, 0 warnings`;
- no secrets committed; and
- policy decisions accepted.

Nothing else owner-controlled is required before local Phase 1 verification. A
real Google callback/token exchange and the complete normal/admin browser flows
remain later live-acceptance work, not permission to create new infrastructure.

## Phase 0 - freeze the handoff

Deliverables:

- Supabase-first Auth docs;
- confirmed sanitized setup record;
- D-043 accepted architecture decision;
- redaction-safe prerequisite verifier; and
- this implementation plan.

Gate: no Clerk-first instruction remains except an explicitly rejected/historical
reference; secret scanning and documentation checks pass.

## Phase 1 - configuration, dependencies, and startup validation

### Backend configuration

Add `AuthConfig` to `core/settings.py` and `[auth]` sections to base, Docker,
and test overlays. Policy fields should include:

- provider and required mode;
- issuer, audience, allowed signing algorithms;
- exact allowed application origins;
- sign-in/callback/app paths;
- normal-user limit 15;
- one portfolio and one variant limits;
- token clock skew and JWKS cache TTL; and
- provider timeout/retry bounds.

Environment-bound values:

- `SUPABASE_URL`;
- `SUPABASE_PUBLISHABLE_KEY`;
- `SUPABASE_SECRET_KEY`;
- `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`; and
- `ORYXENAI_ALLOWED_USER_EMAILS`.

Parse/deduplicate normalized emails. Reject overlap between bootstrap admins
and normal allowlist. Require exactly two distinct bootstrap admins in required
development/production auth mode. The development normal allowlist already has
one private test entry. Production may use a separately reviewed allowlist, but
required deployments must not start with an accidental empty admission policy.

Production validation must reject localhost, HTTP, wildcard origins, missing
keys, project/issuer mismatch, test override, and auth-disabled mode. Local/test
profiles remain explicit and safe.

### Backend dependencies

- Pin a maintained JWT library with asymmetric cryptography/JWKS support.
- Reuse the existing bounded async HTTP client approach for Supabase Auth/Admin
  calls rather than adding a second network stack.
- Do not use the secret key for ordinary user-token verification.

### Browser dependency

Add a minimal checked-in web package/lock/build step that pins the official
Supabase JavaScript client and produces a self-hosted static browser bundle.
Do not use an unversioned runtime CDN. Keep the current Jinja/vanilla-JS app.

Likely files:

- `.env.example`;
- `pyproject.toml`, `uv.lock`;
- `config/app.toml`, `config/app.docker.toml`, `config/app.test.toml`;
- `src/oryxenai/core/settings.py`;
- new web package/lock/build files and `web/static/auth-client.js` output;
- `src/oryxenai/main.py`/security headers;
- doctor/readiness paths; and
- settings/doctor tests.

Phase gate:

- missing/malformed settings fail safely;
- no secret value appears in diagnostics;
- production cannot start with local/test auth configuration; and
- pinned browser/backend dependency checks pass.

## Phase 2 - Ownership schema and repositories (implemented)

Load the PostgreSQL best-practice guidance immediately before migration SQL.
Use one new linear Alembic revision. Keep locks/transactions short and index
every foreign key used for joins/cascades. The ownership portion is implemented
by `0015_portfolio_ownership`; the Phase 3 entitlement and durable identity
binding designs are implemented by `0016_auth_entitlements_worker_fencing`.
The audit design remains Phase 4 material.

### `app_users`

Proposed columns:

- internal UUID primary key, consistent with current exposed IDs;
- `supabase_user_id UUID UNIQUE NOT NULL`;
- normalized `primary_email TEXT NOT NULL` with reviewed uniqueness policy;
- normalized `username TEXT NULL UNIQUE` plus format/reserved enforcement in
  domain validation and database-compatible checks;
- optional display name/avatar;
- checked `role` (`user`, `admin`);
- checked `status` (`active`, `suspended`, `deletion_pending`, `deleted`);
- deleted timestamp and a minimal retained authorization tombstone that prevents
  automatic re-admission under a newly created Supabase subject;
- onboarding/last-seen/created/updated timestamps as `TIMESTAMPTZ`.

The current repository consistently uses UUIDs; retain that convention rather
than adding a new extension solely for UUIDv7 at this scale.

### `app_user_capacity`

One singleton row serializes normal-user admission. Store scope, configured
limit, revision, and timestamps. Resolve Supabase identity outside the locked
transaction, then:

1. lock the singleton row;
2. recheck subject/email admission;
3. count active/suspended/deletion-pending normal accounts according to policy;
4. atomically insert/upsert the user if below 15; and
5. commit before any external provider call.

Use a consistent lock order everywhere: capacity row, app user, entitlement,
session/run. Do not make HTTP calls while holding database locks.

### `portfolio_entitlements`

- one row per normal user;
- unique nullable session binding;
- unique nullable Code Generator run/variant binding;
- unique nullable successful run binding;
- consumed timestamp and revision;
- indexed foreign keys and explicit deletion/reset semantics.

Admins bypass this service policy; do not create a magic huge quota.

### `admin_audit_events`

- UUID primary key;
- actor user FK/index;
- action, target type/ID, request ID, outcome, safe details, timestamp;
- retention-compatible behavior when target/actor is later deleted;
- no tokens, allowlists, full emails, raw intake, or destructive payload dump.

### Ownership and legacy quarantine

Add to `portfolio_sessions`:

- nullable `owner_user_id` FK/index; and
- explicit `legacy_quarantined BOOLEAN NOT NULL` plus a check requiring either
  an owner or quarantine.

Migration marks every existing row quarantined. New product creation always
sets owner and `legacy_quarantined=false`. Admin-only repository methods may
read legacy rows; normal paths never can.

### Durable identity bindings

After exact model audit, add nullable structured session/owner/actor bindings
where generic/system jobs require nullability, especially `background_jobs`,
`agent_runs`, and production session-bound Code Generator runs/attempts. Index
FKs. System probes remain explicitly unowned; product jobs require a bound
session owner.

### Supabase Data API hardening

OryxenAI business data continues through SQLAlchemy/FastAPI, not browser
PostgREST. Migration/deployment must:

- review currently exposed schemas;
- revoke `anon`/`authenticated` privileges from business tables where those
  roles exist;
- avoid relying on default table exposure behavior;
- use RLS as defense in depth if a table is exposed; and
- index every ownership predicate.

Do not add `SECURITY DEFINER` as a shortcut. Any unavoidable privileged
function belongs in a private schema with explicit caller checks and revoked
public execute privileges.

Likely files:

- new migration after the current head;
- new auth/capacity/entitlement/audit models;
- `portfolio_session.py`, generic run/job models;
- model exports;
- new repositories and owner-scoped repository methods; and
- migration/model/repository tests.

Phase gate:

- upgrade from current data preserves and quarantines legacy sessions;
- downgrade behavior is reviewed safely;
- all checks/FKs/indexes exist;
- duplicate subject/username and capacity races are deterministic; and
- Supabase advisors/security review finds no unresolved issue before production.

## Phase 1 - Supabase identity and current-user boundary (implemented)

Create `src/oryxenai/auth/` with narrow modules:

- domain types (`CurrentUser`, safe identity projection, auth states);
- JWT/JWKS verifier;
- bounded Supabase Auth/Admin HTTP client;
- admission/JIT provisioning service;
- FastAPI dependencies; and
- provider-safe errors/redaction helpers.

### Request authentication

1. Extract one bearer token; reject ambiguity.
2. Verify configured algorithm/signature through JWKS.
3. Validate exact issuer, audience, expiry, not-before, subject UUID, and the
   expected authenticated token role/type.
4. Load local user by Supabase subject.
5. Recheck local status/role/onboarding/entitlement every request.

JWKS cache is process-local, bounded, and refreshes once for an unknown key ID.
Provider network failure never creates an unauthenticated fallback.

### JIT provisioning

If no local user exists:

1. call Supabase `/auth/v1/user` with caller token + publishable key;
2. require matching subject and verified/usable email;
3. reject a matching deleted-email tombstone unless an explicit audited admin
   readmission cleared it;
4. compare normalized email to bootstrap admins/normal allowlist;
5. reject unapproved identity without local data;
6. resolve admin first; otherwise serialize normal admission under capacity;
7. atomic upsert by immutable subject; and
8. create normal entitlement exactly once.

Do not authorize from `user_metadata`. Optional display/avatar values are
untrusted presentation data and require output safety.

### Dependencies

- `get_optional_identity` for public controller routes;
- `get_current_user` for any valid admitted local identity;
- `require_active_user`;
- `require_onboarded_user`;
- `require_admin`; and
- `require_session_owner_or_admin` plus nested resource guards.

Phase gate: deterministic token/admission test matrix passes, provider errors
are bounded/redacted, and unapproved users create no rows.

## Phase 2 - `/me` continuity, route protection, and browser integration (implemented)

Phase 1 already owns the `/me` and username implementation. The Phase 2 work
in this section is the route/access inventory, owner/admin retrofit, conditional
development surfaces, and authenticated browser integration that consumes that
identity boundary.

Add:

- `GET /api/v1/me` safe projection;
- `PUT /api/v1/me/username` atomic claim; and
- optional explicit server sign-out/revocation route only if current Supabase
  session semantics require it.

Then retrofit every route family. The first implementation pass must generate a
route/access inventory test so newly added routes cannot silently omit policy.

### Public

- health live/ready (minimal);
- sign-in/callback HTML shells;
- static assets; and
- preview capability origin under its separate contract.

### Active normal or admin

- safe product metadata;
- owner-scoped sessions/stages/runs/jobs/source/preview controls.

### Admin/dev only

- system status/probes;
- bounded cross-user views;
- fixture/development routes when development mode is enabled.

### Absent in production

- mock-run routes;
- Build Preparation fixture surfaces; and
- Code Generator development harness.

Repository and service methods must carry owner/actor semantics so a future
route cannot bypass policy by calling a generic ID lookup.

Phase gate: A/B/admin matrix across every route and nested ID family passes;
foreign and nonexistent return indistinguishable 404s.

## Phase 3 - capacity entitlement, generation policy, and worker fencing (implemented)

Implemented by migration `0016_auth_entitlements_worker_fencing`,
`src/oryxenai/auth/entitlements.py`, `worker_fence.py`, `finalization.py`, the
central job policy/repository changes, and the existing production workspace
boot integration. The following contract is the source-of-truth summary of
the completed phase; Phase 4 owns administrator lifecycle and deployment.

### Session claim

For normal user: lock entitlement, return existing session or create exactly
one owned session and bind it. Admins create unlimited owned sessions.

### Code Generator start/retry/regenerate

- first normal start binds the production run/variant transactionally;
- duplicate start returns/resumes the same run;
- retry preserves existing immutable variant receipt;
- normal regenerate returns `GENERATION_VARIANT_LOCKED`;
- admin regenerate follows current safety/quality gates.

### Success

Bind `successful_run_id` only inside current crash-safe promotion and
reconciliation after source/build/DOM/runtime/quality/public read-back and exact
`active_preview` are proven. The same run is idempotent; a different normal run
is rejected. Afterward normal mutation is denied.

### Durable jobs

API writes session owner and initiating actor when enqueueing. Worker reloads
current local user/session before applying or promoting output. Suspension,
deletion, missing owner, reassignment, or legacy quarantine prevents
finalization.

### Cost admission

Deployed policy runs one generation job at a time. Provider readiness/credit
must remain fail-closed. No automatic more-expensive model fallback. Admin
quota exemption never bypasses provider limits.

Phase gate: concurrency and crash/reconciliation tests prove one session,
variant, and success without duplicate paid work.

## Phase 4 - browser acceptance, administrator lifecycle, and deployment handoff (deferred)

Add templates/static modules for:

- sign-in;
- auth callback/loading/error;
- access not approved;
- onboarding;
- authenticated app controller;
- suspended/deletion-pending state; and
- admin console shell.

Use the canonical route table and single controller algorithm in
[03-user-flow-and-route-contract.md](03-user-flow-and-route-contract.md). The
minimum page set is `/`, `/sign-in`, `/auth/callback`,
`/access-not-approved`, `/account-unavailable`, `/onboarding`, `/app`, and
`/admin`. Every direct or refreshed protected page resolves auth before private
fetches; do not depend on a host-specific SPA fallback.

Refactor current boot:

1. initialize pinned Supabase client from rendered public configuration;
2. resolve provider session;
3. call `/me` with bearer token;
4. choose screen/route;
5. only then initialize current Discovery/app behavior;
6. centralize token injection/one refresh in `fetchJson()`; and
7. clear polling/data/session pointer before provider sign-out.

Do not render the secret key or private emails. Strip OAuth artifacts from
history. Validate local return destinations. Preserve accessible focus,
loading, error, mobile, and reduced-motion behavior.

Normal UI removes global session list, developer tools, new portfolio, and
regenerate controls as policy requires. The API remains authoritative.

Phase gate: browser tests prove no protected fetch before auth, refresh-safe
state, onboarding, owner resume, read-only success, admin access, and sign-out
back/refresh safety.

## Phase 7 - admin lifecycle

Implement bounded APIs/UI for:

- list users/projects/audit;
- suspend/restore;
- delete project;
- reset entitlement;
- delete user;
- admin retry/regenerate; and
- legacy-session inspection/cleanup.

All destructive operations:

- validate admin locally;
- block last-admin deletion/demotion;
- require target-specific confirmation/idempotency;
- deny locally before external cleanup;
- fence queued/running work;
- revoke preview pointer before object cleanup;
- call the current Supabase Admin API outside database locks;
- persist retryable deletion state on partial failure;
- finish with a minimal local deleted-identity tombstone so an unchanged
  allowlist cannot recreate access automatically; and
- audit safe outcome.

Phase gate: partial provider/storage failures remain denied and resumable; audit
contains no secrets/PII payloads.

## Phase 8 - verification

### Deterministic tests

- token verification, JWKS cache/rotation, first-login provider response;
- admin/allowlist/unapproved/capacity admission;
- deleted identity re-login and explicit audited readmission;
- username validation/race;
- user states and dependencies;
- every route's A/B/admin matrix;
- one-session/variant/success concurrency;
- worker deletion/suspension fencing;
- admin lifecycle/idempotency/last-admin/audit;
- redirect/origin/CSP and log redaction.

Use locally signed JWT fixtures or dependency injection. Normal suites never
call Google/Supabase.

### PostgreSQL

- migrate current legacy data forward;
- FK/check/index/grant/RLS review;
- subject/username/capacity/upsert races;
- entitlement and promotion reconciliation;
- deletion with queued/running jobs; and
- audit retention behavior.

### Browser

- signed-out boot without protected calls;
- deterministic authenticated sessions for CI;
- new user/onboarding/conflict/return/refresh/sign-out;
- two-user foreign-ID isolation;
- completed normal read-only state; and
- admin console operations.

### Live development

1. Run the prerequisite verifier:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online -RequireNormalUser
   ```

2. Start existing API/worker/database stack.
3. Manually sign in each real admin through Google.
4. Run the already configured separate normal test account through its complete
   live flow without printing or automating its credentials.
5. Never automate Google passwords in Playwright.

### Commands

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run alembic upgrade head
```

Use focused tests during phases, then the full suite. Browser/runtime evidence
is separate from API health.

## Phase 9 - documentation, commit, and deployment handoff

- Update `AGENTS.md` only after implementation is true.
- Update README/architecture/runbooks and Auth docs.
- Record implementation status in D-043 or a superseding decision as needed.
- Add one commit-sized `CHANGES.md` entry.
- Review secret scan, `git diff --cached --check`, staged stat/full patch.
- Commit only task-owned paths; do not push unless requested.

Then stop. Production Supabase/Google/AWS setup is a separate explicit task.

## Rollback strategy

- Database downgrade/forward migration must preserve quarantined legacy data.
- If auth rollout fails before public deployment, revert application routes and
  keep schema additive; do not expose unauthenticated production APIs.
- In production, disable new sign-in/admission while retaining fail-closed
  protected routes; never use an `auth disabled` bypass.
- Keep prior verified preview pointers while auth/API recovery occurs.
- Export/backup application DB and object metadata before provider migration.

## Owner gates

Before implementation starts:

- owner explicitly starts the implementation phase (approval of this handoff
  does not start coding); and
- existing unrelated worktree files remain untouched.

Before live normal-user completion claim:

- the already configured separate normal Google test account completes the
  visible browser flow.

Before deployment:

- local/full tests and visible browser flow pass;
- production URLs/domain choice are known;
- production Supabase/Google are created;
- AWS Free account is created only then;
- external model budget/credit policy is explicitly set; and
- owner approves any paid-plan activation.
