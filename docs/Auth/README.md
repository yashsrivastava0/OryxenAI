# OryxenAI authentication handoff

Status: Authentication Phases 1 and 2 are implemented and locally tested.
Phase 2 adds session ownership, legacy quarantine, owner/admin API policy, and
authenticated product/developer boot. Phase 3 portfolio entitlement/worker
fencing and Phase 4 administrator lifecycle/live deployment acceptance remain
deferred. No production cloud resources were created.

Last verified: 2026-08-24. Provider behavior, prices, SDKs, and dashboard
screens are time-sensitive; recheck the linked primary sources when coding or
deploying.

## Final decision

Use **Supabase Auth** with **Google as the only v1 sign-in method**. Keep all
application authorization in OryxenAI and PostgreSQL:

- Supabase proves the caller's external identity and issues the session JWT.
- `app_users` maps the immutable Supabase user UUID to an OryxenAI user.
- PostgreSQL stores username, role, status, admission, ownership, and quota.
- FastAPI verifies every protected request and applies owner-or-admin policy.
- Phase 3 will bind owner and actor identity to durable work before enqueueing
  and recheck authorization before finalization.

Do not ask for, receive, or store a Google password. Do not store Google access
or refresh tokens because OryxenAI does not call Google APIs on a user's behalf.

Clerk is not part of the selected stack. Do not combine Clerk and Supabase Auth
or retain Clerk-specific keys, subjects, webhooks, SDKs, routes, or UI.

## Confirmed product policy

1. One **Continue with Google** action handles both first sign-in and return.
2. Registration is application-allowlisted through
   `ORYXENAI_ALLOWED_USER_EMAILS`.
3. Two bootstrap administrator emails are supplied privately through
   `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` and persist as database-authoritative
   administrators after verified first login.
4. At most 15 normal users may be admitted; administrators do not consume
   those slots.
5. A first-time approved user chooses one unique OryxenAI username.
6. Phase 2 temporarily permits a normal user to create multiple explicitly
   owned sessions; Phase 3 will enforce one portfolio session and one design
   variant.
7. Phase 3 will make failed attempts retry the same variant and deny explicit
   regeneration for normal users.
8. Phase 3 will make only a verified, hash-bound, promoted `active_preview`
   consume the user's one successful portfolio.
9. Phase 3 will make a successful normal-user project readable but no longer
   mutable; deletion and audited reset remain later lifecycle policy.
10. Administrators are quota-exempt and may manage all users and projects, but
    cannot bypass model/provider safety gates or spending limits.
11. Existing unowned sessions are quarantined as legacy/admin-only data; new
    product sessions are explicitly owned by the authenticated local user.
12. Normal users receive owner-scoped session/stage/run access; active
    onboarded admins may operate across owned and legacy sessions.
13. The last active administrator cannot delete or demote themselves (the
    lifecycle operation remains Phase 4).

## Confirmed development provider

The non-secret development coordinates and dashboard decisions are recorded in
[09-confirmed-setup.md](09-confirmed-setup.md). Real keys remain only in the
git-ignored `.env` or provider dashboard.

Redaction-safe verification confirmed:

- all five expected local environment entries are declared;
- the configured project URL matches the recorded project;
- two distinct bootstrap administrator entries are present;
- one separate non-admin test identity is present in the private normal-user
  allowlist and Google test-user list;
- Supabase Auth settings are reachable;
- the Google provider is enabled;
- the project JWKS endpoint exposes a signing key; and
- OAuth initiation redirects to Google; and
- the strict online prerequisite run completed with `0 failures, 0 warnings`.

The local implementation proves the deterministic controller, callback/session
logic, server-side JWT/provider boundaries, safe `/me` projection, admission
constraints, ownership/legacy repository policy, route inventory, and
temporary product/developer shells through unit/API tests. A real Google
browser login and the production-origin flow remain later acceptance work; no
additional account or secret is created by this phase.

Run the safe setup checker from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online -RequireNormalUser
```

The checker reports presence and booleans only. It never prints a key, token,
password, administrator email, or allowlist entry.

For a deployment, select a deployment-owned TOML overlay with
`[app].env = "production"`, `[app].enable_dev_ui = false`, and
`[auth].required = true`. Replace the local origins with exactly one reviewed
HTTPS `primary_origin` and one matching `allowed_origins` entry. Startup then
fails closed for the committed localhost origins, missing provider
coordinates, mismatched issuer, wildcard origins, or an empty required
admission policy. The local base configuration intentionally keeps the two
port-8000 origins for development and tests.

## Minimal user flow

```text
signed out -> /sign-in -> Google/Supabase redirect -> /auth/callback
           -> GET /api/v1/me
           -> unapproved: /access-not-approved
           -> suspended/deleting: /account-unavailable
           -> approved new user: /onboarding -> unique username -> /app
           -> returning active user: /app
           -> administrator: /app, with explicit /admin available
```

Use a full-page redirect. Do not automate a real Google password in CI.

## Security boundary

- The browser may receive only the Supabase URL and publishable key.
- The Supabase secret/service-role key is server-only.
- Never authorize from `user_metadata`, browser storage, query parameters, or
  caller-supplied email/role/owner fields.
- On first login, resolve verified identity through Supabase Auth before
  allowlist or admin bootstrap decisions.
- Returning requests resolve the external `sub` to current local role/status.
- Phase 1 protects the identity boundary and `/me`/username routes. Phase 2
  protects every existing portfolio object lookup with active/onboarded
  owner-or-admin policy and keeps legacy sessions admin-only.
- Business tables remain backend-only; do not rely on the browser Data API.
- Production starts fail closed if auth is required but provider coordinates,
  keys, issuer/audience, or exact origins are invalid.

## Deployment boundary

Do not create AWS resources during Phase 1. Create the AWS Free account only
when deployment is ready so
its promotional clock is not wasted. Production will use separate
Supabase/Google configuration and final HTTPS origins.

Auth does not replace the existing runtime requirements: managed PostgreSQL,
API, durable worker, private object storage, and one shared preview origin.

## Document set

- [01-current-system-auth-surface.md](01-current-system-auth-surface.md) -
  current auth/ownership routes and integration risks.
- [02-provider-evaluation.md](02-provider-evaluation.md) - selected Supabase
  topology and rejected alternatives.
- [03-user-flow-and-route-contract.md](03-user-flow-and-route-contract.md) -
  screens, redirects, APIs, and status behavior.
- [04-authorization-quota-and-data-model.md](04-authorization-quota-and-data-model.md)
  - roles, ownership, quotas, concurrency, and deletion.
- [05-security-and-edge-cases.md](05-security-and-edge-cases.md) - token,
  browser, provider, admin, and failure controls.
- [06-deployment-and-owner-checklist.md](06-deployment-and-owner-checklist.md) -
  owner setup and future deployment work.
- [07-implementation-handoff.md](07-implementation-handoff.md) - bounded work
  packages and definition of done.
- [08-primary-sources.md](08-primary-sources.md) - dated primary-source index.
- [09-confirmed-setup.md](09-confirmed-setup.md) - sanitized record of completed
  external setup and verification evidence.
- [10-implementation-plan.md](10-implementation-plan.md) - repository-grounded
  implementation order, file map, tests, rollout, and gates.

## Primary sources

- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase JWT guidance](https://supabase.com/docs/guides/auth/jwts)
- [Supabase signing keys](https://supabase.com/docs/guides/auth/signing-keys)
- [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Google OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
