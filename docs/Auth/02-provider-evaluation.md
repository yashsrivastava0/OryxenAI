# Authentication provider evaluation

Status: decision accepted. Supabase Auth is the selected identity provider.

## Evaluation criteria

OryxenAI needs:

- one reliable Google sign-in/sign-up flow;
- compatibility with Jinja2, vanilla JavaScript, FastAPI, and PostgreSQL;
- server-side JWT verification and user administration;
- a free allowance far above 15 normal users and two administrators;
- low setup and maintenance burden for AI coding agents;
- environment-configurable development and production redirects;
- no application-owned passwords; and
- no redesign of the durable worker or generated-preview architecture.

## Final comparison

| Option | Main benefit | Main cost/risk | Decision |
| --- | --- | --- | --- |
| Supabase Auth | Google OAuth, session issuance, hosted callback, and managed PostgreSQL can share one provider | The app owns its sign-in shell and authorization; Free projects can pause | **Selected** |
| Clerk | Strong prebuilt UI and identity administration | Adds a third service beside Supabase PostgreSQL and AWS; production setup has additional domain/environment requirements | Rejected for this deployment |
| Firebase Auth | Mature Google login | Adds Firebase while business state remains PostgreSQL | Rejected |
| Auth0 | Mature general-purpose identity platform | More tenant/application/API configuration than this two-role personal app needs | Rejected |
| Self-built auth | No identity-vendor UI dependency | OryxenAI would own OAuth state, PKCE, session rotation, account recovery, abuse controls, and security maintenance | Rejected |

Provider pricing and SDK behavior are not permanent facts. Recheck primary
sources at implementation and deployment time.

## Selected topology

```text
Google -> Supabase Auth -> Supabase access token
                             |
browser fetch ---------------+
                             v
FastAPI verifies JWT -> app_users -> owner/admin policy -> PostgreSQL/jobs
```

Supabase handles identity proof and session issuance. OryxenAI handles:

- the application allowlist;
- the 15-normal-user admission ceiling;
- two initial administrators;
- unique username onboarding;
- local account status;
- portfolio ownership;
- one-project/one-variant/one-success entitlement;
- admin audit and lifecycle operations; and
- worker finalization safety.

The immutable external identity key is the Supabase JWT `sub`, stored as a UUID.
Email is used only for verified first-login admission/bootstrap and support
display. Ownership never depends on email, username, or client metadata.

## Browser integration

Use the official Supabase JavaScript client and a full-page
`signInWithOAuth({ provider: "google" })` flow. Pin the package and commit its
lockfile. The deployed application must serve the pinned browser asset itself;
do not depend on an unversioned third-party CDN at runtime.

The browser may receive:

- the Supabase project URL; and
- the publishable key.

It must never receive the secret/service-role key. Supabase's client may manage
its session token, but OryxenAI must not copy the token into custom storage,
logs, URLs, rendered HTML, or application records.

## Backend integration

FastAPI verifies Supabase access tokens using the project's exact issuer,
audience, expiry, subject, signing algorithm, and JWKS. The implementation must
support the project's current asymmetric signing key and fail closed on unknown
algorithms or keys. JWKS caching must be bounded and refresh once on an unknown
key ID.

On first approved login, the backend resolves the authenticated Supabase user
through the Auth server before using the verified email for bootstrap or
allowlist admission. Returning requests resolve `sub` locally and read current
role/status from PostgreSQL.

Never authorize from `user_metadata`. It is client-editable. Do not put role,
quota, ownership, or allowed-email policy into browser-controllable metadata.

## Database topology

During local implementation, OryxenAI may continue using the checked-in local
PostgreSQL workflow while Supabase supplies development identity.

At production deployment, Supabase PostgreSQL may host the same Alembic-managed
application schema. The persistent FastAPI API and worker should use the
appropriate direct or session-pooler connection. They are not browser Data API
clients.

Business tables must not become an accidental public API. At implementation
time:

- review Supabase's current Data API exposure behavior;
- keep browser access to application tables disabled/revoked;
- use RLS as defense in depth for any exposed schema/table; and
- never treat `TO authenticated` alone as object authorization.

## Google-only v1

One **Continue with Google** action handles new and returning users. Google owns
the credential screen. OryxenAI stores no password and no Google provider token.

Only the basic scopes are permitted:

- `openid`;
- `userinfo.email`; and
- `userinfo.profile`.

Do not add an email OTP/password fallback in v1. If a non-Google audience later
becomes a real requirement, evaluate it as a new decision with delivery,
recovery, abuse, and testing costs.

## Allowlist and capacity

An identity existing in Supabase does not automatically grant product access.
FastAPI admits only:

- a verified bootstrap administrator email; or
- a verified email in `ORYXENAI_ALLOWED_USER_EMAILS`.

Non-allowlisted identities receive a safe 403 before a portfolio or model job
is created. At most 15 normal users may be admitted. Administrators do not
consume those slots. Suspended users retain their slot; deleting a normal user
through the audited admin workflow releases it.

## Why not combine providers

Do not enable Clerk beside Supabase Auth. Two identity systems create duplicate
subjects, token formats, logout paths, deletion semantics, callback routes, and
test matrices. One provider is sufficient.

## Current development configuration

The owner has configured a Supabase Free project in Mumbai and a Google external
testing application with exact localhost origins, Supabase callback, basic
scopes, and two administrator test users. See
[09-confirmed-setup.md](09-confirmed-setup.md) for the sanitized record.

## Official sources

- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase social login](https://supabase.com/docs/guides/auth/social-login)
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase JWTs](https://supabase.com/docs/guides/auth/jwts)
- [Supabase signing keys](https://supabase.com/docs/guides/auth/signing-keys)
- [Supabase API security](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase billing](https://supabase.com/docs/guides/platform/billing-on-supabase)
- [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Google OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
