# Owner and deployment checklist

This separates owner-controlled accounts/secrets from coding-agent work. Never
paste secret values, passwords, payment details, OTPs, or root credentials into
chat, source, documentation, tests, screenshots, logs, or commits.

## Final owner decision

- Identity provider: Supabase Auth.
- Sign-in method: Google only.
- Registration: application allowlist.
- Capacity: 15 normal users plus two initial administrators.
- Authorization: FastAPI and PostgreSQL.
- Deployment: deliberately deferred; do not create AWS yet.

## Development setup already completed

- Supabase Free development project created in Mumbai.
- Google external testing app created.
- Basic identity scopes only.
- Google web client created.
- Supabase callback configured in Google.
- Google Client ID/Secret configured privately in Supabase.
- Google provider enabled with nonce skipping off and email required.
- Local site and callback URLs configured for localhost and `127.0.0.1` on
  port 8000.
- Two administrator identities added as Google test users and stored privately
  in the bootstrap setting.
- Required `.env` entries declared without committing values.
- No application tables created manually; Alembic remains authoritative.

See [09-confirmed-setup.md](09-confirmed-setup.md) for the sanitized values and
verification evidence.

## Pending owner item

A separate non-admin Google test account does not yet exist. Before the final
normal-user live acceptance test:

1. Choose/create one Google account that is not either administrator.
2. Add it to the Google OAuth application's test users.
3. Add its normalized email to `ORYXENAI_ALLOWED_USER_EMAILS` in `.env`.
4. Restart the API/worker so cached settings reload.
5. Do not add it to `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`.
6. Run new-user onboarding and one-project isolation tests with it.

This is not a blocker for planning or deterministic implementation tests. It is
a blocker for claiming the normal-user Google flow is live-verified.

## Local environment contract

Expected `.env` names:

```text
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
ORYXENAI_ADMIN_BOOTSTRAP_EMAILS=
ORYXENAI_ALLOWED_USER_EMAILS=
```

Rules:

- The publishable key may be sent to the browser.
- The secret/service-role key is server-only.
- The Google Client Secret remains in Supabase, not OryxenAI.
- Allowlist/bootstrap emails are deployment policy and must not appear in
  client configuration or normal diagnostics.
- The coding agent may inspect presence/shape through redaction-safe tooling,
  never print values.

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online
```

The online form checks provider settings, JWKS, and OAuth initiation. It does
not perform an interactive Google login.

## Non-secret application policy to add during implementation

The implementation plan will add config-driven policy equivalent to:

```toml
[auth]
provider = "supabase"
required = true
sign_in_path = "/sign-in"
callback_path = "/auth/callback"
after_sign_in_path = "/app"
normal_user_limit = 15
normal_user_portfolio_limit = 1
normal_user_variant_limit = 1
```

Allowed origins, issuer, audience, and redirects must be environment/overlay
specific. Do not scatter localhost or future production URLs through code.

Production startup must fail readiness when auth is required but project URL,
keys, issuer/audience, or exact origins are missing/mismatched. Test auth
overrides must be impossible in production.

## Coding-agent responsibilities

- Pin backend JWT/crypto and browser Supabase dependencies with lockfiles.
- Add auth settings and redacted doctor checks.
- Implement JWT/current-user/admission dependencies.
- Add user, capacity, entitlement, ownership, audit, and durable-actor database
  migrations through Alembic.
- Quarantine all current unowned sessions.
- Protect every API/repository/service boundary.
- Implement sign-in, callback, onboarding, app controller, and admin UI.
- Enforce 15 normal users, one portfolio, one variant, one verified success.
- Bind owner/actor to durable jobs and recheck before finalization.
- Implement suspend/restore/delete/reset as resumable audited workflows.
- Harden browser CSP, redirects, token injection, refresh, and sign-out.
- Add deterministic unit/API/PostgreSQL/browser tests.
- Perform manual Google smoke only when the owner supplies the test identity.
- Keep Auth docs, `DECISIONS.md`, `CHANGES.md`, and `AGENTS.md` truthful.

## Future production setup - do not do now

Create production infrastructure only when the auth implementation, migrations,
tests, and local browser flow are ready.

### Supabase and Google

1. Create a separate production Supabase project.
2. Create a separate production Google OAuth client/application as required by
   Google's environment guidance.
3. Configure final HTTPS Site URL and exact callback/redirect paths.
4. Configure only basic identity scopes.
5. Add the production Google Client ID/Secret to Supabase.
6. Add production Supabase URL/keys to the host secret store.
7. Use the proper direct/session-pooler PostgreSQL connection for persistent
   API and worker processes.
8. Apply Alembic once through the migration service before API/worker start.
9. Verify Data API exposure/RLS/grants for application tables.

### AWS timing and spending

Do **not** create the AWS account until the deployment is ready. The promotional
clock starts at account creation.

At deployment time:

1. Create an AWS India account and select **Free account plan**, not Paid.
2. Complete only the documented refundable verification charge.
3. Enable root MFA; never give root credentials to an AI.
4. Create a bounded IAM deployment identity or local CLI profile.
5. Do not join AWS Organizations or enable Control Tower.
6. Configure credit-balance, forecast, and expiration alerts.
7. Require explicit owner approval before any paid-plan upgrade or paid-only
   service.
8. Use one measured EC2 host for app/worker/preview processes, private S3 for
   artifacts, and CloudFront/shared preview routing.
9. Avoid NAT Gateway, managed RDS, multiple always-on instances, OpenSearch,
   unbounded logs, and per-portfolio deployments for the initial small app.

AWS credit does not pay external model-provider bills, a purchased domain, or
other vendors.

## Generation cost controls

- Maximum 15 admitted normal users.
- One successful portfolio per normal user.
- One generation job executing at a time in the deployed policy.
- Failed attempts retry the same variant.
- Normal users cannot regenerate.
- Stop safely when the configured model provider reports no usable credit.
- Never auto-fallback to a more expensive model.
- Admin entitlement is unlimited, but external provider spending gates remain
  authoritative.
- Use prepaid/provider limits until an explicit monthly budget is accepted.
- Temporary packs/failed builds receive lifecycle cleanup; verified releases
  remain durable.

## Production URL worksheet

Fill only when production resources exist:

```text
App origin:                 https://________________
Sign-in URL:                https://________________/sign-in
Auth callback URL:          https://________________/auth/callback
Supabase project URL:       https://________________.supabase.co
Supabase callback in Google:https://________________.supabase.co/auth/v1/callback
Google JavaScript origin:   https://________________
API allowed origin:         https://________________
Preview origin/domain:      https://________________
Privacy policy URL:         https://________________
Terms/support URL:          https://________________
```

Use exact URLs. Do not use wildcard production redirects or invent the
Supabase provider callback.

## Deployment acceptance

### Identity and routing

- signed-out `/` performs no protected fetch and shows Google sign-in;
- cancel/provider errors return safely;
- unapproved identity gets 403 and no product state;
- approved new normal user completes username onboarding once;
- returning normal user resumes one session;
- both administrators reach `/admin` and own unlimited sessions;
- sign-out, back, refresh, and direct URLs reveal no private data.

### Authorization and quota

- user A cannot read/write user B resources by changing any ID;
- every stage/run/job/source/preview control proves owner/admin;
- the sixteenth normal admission is rejected under a race test;
- normal double-create returns one session;
- retry keeps the variant and failed work does not consume success;
- normal regenerate is denied;
- verified promotion consumes success once and freezes normal writes;
- admin reset/delete/regenerate is explicit and audited.

### Operations

- migration, API, worker, database, Auth, object storage, and preview each have
  separate current evidence;
- no secrets/tokens/allowlist/email lists appear in logs or responses;
- suspension denies immediately even if provider cleanup is delayed;
- deletion fences queued/running jobs and revokes preview first;
- backup/restore and last-admin safeguards are exercised;
- cloud/provider budget alerts and fail-closed credit behavior are proven.

## Owner-facing sources

- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase JWTs](https://supabase.com/docs/guides/auth/jwts)
- [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Google OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
