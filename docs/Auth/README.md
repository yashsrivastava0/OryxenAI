# OryxenAI authentication handoff

Status: provider and product policy are decided, the development provider is
configured, and implementation has not started.

Last verified: 2026-08-23. Provider behavior, prices, SDKs, and dashboard
screens are time-sensitive; recheck the linked primary sources when coding or
deploying.

## Final decision

Use **Supabase Auth** with **Google as the only v1 sign-in method**. Keep all
application authorization in OryxenAI and PostgreSQL:

- Supabase proves the caller's external identity and issues the session JWT.
- `app_users` maps the immutable Supabase user UUID to an OryxenAI user.
- PostgreSQL stores username, role, status, admission, ownership, and quota.
- FastAPI verifies every protected request and applies owner-or-admin policy.
- Durable work records owner and actor identity before enqueueing and rechecks
  ownership before finalization.

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
6. A normal user owns one portfolio session and one design variant.
7. Failed attempts may retry the same variant. Explicit regeneration is denied
   for normal users.
8. Only a verified, hash-bound, promoted `active_preview` consumes the user's
   one successful portfolio.
9. After success, a normal user's project is readable but no longer mutable.
   Deletion does not silently restore entitlement; only an audited admin reset
   does.
10. Administrators are quota-exempt and may manage all users and projects, but
    cannot bypass model/provider safety gates or spending limits.
11. Existing unowned sessions are quarantined as legacy/admin-only data.
12. The last active administrator cannot delete or demote themselves.

## Confirmed development provider

The non-secret development coordinates and dashboard decisions are recorded in
[09-confirmed-setup.md](09-confirmed-setup.md). Real keys remain only in the
git-ignored `.env` or provider dashboard.

Redaction-safe verification confirmed:

- all five expected local environment entries are declared;
- the configured project URL matches the recorded project;
- two distinct bootstrap administrator entries are present;
- the normal-user allowlist is currently empty by design;
- Supabase Auth settings are reachable;
- the Google provider is enabled;
- the project JWKS endpoint exposes a signing key; and
- OAuth initiation redirects to Google.

This does **not** yet prove a completed browser login, a token exchange, username
onboarding, FastAPI authorization, or a normal-user flow. Those require the
implementation. A separate normal Google test account must be added to both the
Google test-user list and `ORYXENAI_ALLOWED_USER_EMAILS` before final acceptance.

Run the safe setup checker from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online
```

The checker reports presence and booleans only. It never prints a key, token,
password, administrator email, or allowlist entry.

## Minimal user flow

```text
signed out -> /sign-in -> Google/Supabase redirect -> /auth/callback
           -> GET /api/v1/me
           -> unapproved: 403 access-not-approved
           -> approved new user: /onboarding -> unique username -> /app
           -> returning active user: /app
           -> administrator: /admin available
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
- Every object lookup includes owner-or-admin authorization.
- Business tables remain backend-only; do not rely on the browser Data API.
- Production starts fail closed if auth is required but provider coordinates,
  keys, issuer/audience, or exact origins are invalid.

## Deployment boundary

Do not create AWS resources during auth implementation. Create the AWS Free
account only when deployment is ready so its promotional clock is not wasted.
Production will use separate Supabase/Google configuration and final HTTPS
origins.

Auth does not replace the existing runtime requirements: managed PostgreSQL,
API, durable worker, private object storage, and one shared preview origin.

## Document set

- [01-current-system-auth-surface.md](01-current-system-auth-surface.md) -
  current unprotected routes and integration risks.
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
