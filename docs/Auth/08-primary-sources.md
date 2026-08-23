# Primary sources

Research date: 2026-08-23. These are official provider/project sources. No
third-party tutorial or other AI output is treated as authoritative. Recheck
time-sensitive pricing, limits, SDK signatures, and dashboard instructions at
implementation/deployment time.

## Clerk

- [Pricing](https://clerk.com/pricing) — Hobby capacity, custom domain,
  session/log and feature limits.
- [Set up a Clerk application](https://clerk.com/docs/getting-started/quickstart/setup-clerk)
  — dashboard/application start.
- [JavaScript quickstart](https://clerk.com/docs/js-frontend/getting-started/quickstart)
  — package or official script tags, UI bundle, publishable key, `Clerk.load()`.
- [JavaScript SignIn view](https://clerk.com/docs/js-frontend/reference/components/authentication/sign-in)
  — prebuilt `mountSignIn()` behavior.
- [JavaScript Session object](https://clerk.com/docs/js-frontend/reference/objects/session)
  — short-lived session token retrieval/caching.
- [Official Python SDK repository](https://github.com/clerk/clerk-sdk-python) —
  package install, request authentication, authorized parties, async Backend
  API support.
- [Google social connection](https://clerk.com/docs/guides/configure/auth-strategies/social-connections/google)
  — shared development credentials, production custom credentials, Google
  origins/redirect URI, testing/production status.
- [Production deployment](https://clerk.com/docs/guides/development/deployment/production)
  — owned domain, production keys, DNS, OAuth, CSP, authorized parties.
- [Development and production environments](https://clerk.com/docs/guides/development/managing-environments)
  — why development instances/keys are not production substitutes.
- [Redirect customization](https://clerk.com/docs/guides/development/customize-redirect-urls)
  — sign-in/up redirect rules.
- [Sign-up and sign-in options](https://clerk.com/docs/guides/configure/auth-strategies/sign-up-sign-in-options)
  — provider, username, password, and user-model options.
- [Request authentication](https://clerk.com/docs/reference/backend/authenticate-request)
  — request/token verification and `authorizedParties`.
- [Manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)
  — cookie/header token sources and claim validation.
- [Session tokens](https://clerk.com/docs/guides/sessions/session-tokens) —
  default claims including authorized party.
- [User metadata](https://clerk.com/docs/guides/users/extending) — metadata
  visibility, token size/freshness and Backend API tradeoffs.
- [Manage/delete users](https://clerk.com/docs/guides/users/managing) —
  dashboard and Backend API deletion.
- [Ban a user](https://clerk.com/docs/reference/backend/user/ban-user) — ban
  revokes sessions and prevents sign-in.
- [Sync data with webhooks](https://clerk.com/docs/guides/development/webhooks/syncing)
  — eventual consistency, retry/failure caveat, user events.
- [Webhook overview](https://clerk.com/docs/guides/development/webhooks/overview)
  — signature verification, replay, retry.
- [CSP requirements](https://clerk.com/docs/guides/secure/best-practices/csp-headers)
  — required script/connect/image/worker/style/frame sources.
- [System limits](https://clerk.com/docs/guides/how-clerk-works/system-limits) —
  environment-specific rate limits.
- [Testing overview](https://clerk.com/docs/guides/development/testing/overview)
  and [Playwright auth-state testing](https://clerk.com/docs/guides/development/testing/playwright/test-authenticated-flows)
  — deterministic auth testing without real Google UI automation.

## Supabase

- [Changelog](https://supabase.com/changelog) — reviewed first for recent Auth,
  API, and platform changes.
- [Pricing](https://supabase.com/pricing) — Free Auth/DB allowances and pause
  summary.
- [Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
  — Google project, scopes, origins, Supabase callback, browser OAuth flow.
- [Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls) — Site URL
  and allowlisted redirects.
- [JWT guidance](https://supabase.com/docs/guides/auth/jwts) — claims, JWKS, and
  verified-token guidance.
- [Python get claims](https://supabase.com/docs/reference/python/auth-getclaims)
  — Python verification option.
- [Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
  — low-activity pause and restoration.
- [Connect to PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)
  — direct, shared session pooler, and transaction pooler use cases.

## Google OAuth

- [OAuth 2.0 policies](https://developers.google.com/identity/protocols/oauth2/policies)
  — owned/authorized domains, secure origins, production homepage, privacy,
  terms, and prohibition on embedded user-agents.
- [Manage app audience and publishing status](https://support.google.com/cloud/answer/15549945)
  — Testing versus In production behavior, test-user limit, and testing-mode
  authorization lifetime.
- [OAuth app verification help](https://support.google.com/cloud/answer/13463073)
  — when scope or brand verification applies.
- [Brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)
  — authorized-domain ownership and homepage/privacy-policy requirements.

## Other evaluated providers

- [Firebase Google sign-in](https://firebase.google.com/docs/auth/web/google-signin)
- [Firebase server ID-token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [Firebase pricing](https://firebase.google.com/pricing)
- [Auth0 pricing](https://auth0.com/pricing)
- [Auth0 FastAPI API quickstart](https://auth0.com/docs/quickstart/backend/fastapi)

## Hosting constraints

- [Render free services](https://render.com/docs/free) — sleep, cold start,
  ephemeral filesystem, database expiry, and unsupported free service types.
- [Render Blueprint specification](https://render.com/docs/blueprint-spec) —
  free plan is not available to background workers.
- [Render background workers](https://render.com/docs/background-workers) —
  worker service model.
- [Vercel function limits](https://vercel.com/docs/functions/limitations) —
  maximum duration and runtime constraints.

## Repository sources

These checked-in files establish the current integration surface and remain
more authoritative than a static research summary if code changes later:

- `AGENTS.md`
- `DECISIONS.md`
- `src/oryxenai/main.py`
- `src/oryxenai/api/dependencies.py`
- `src/oryxenai/api/routes/`
- `src/oryxenai/db/models/portfolio_session.py`
- `src/oryxenai/db/repositories/portfolio_sessions.py`
- `src/oryxenai/jobs/handlers/`
- `src/oryxenai/agents/code_generator/service.py`
- `src/oryxenai/preview/gateway.py`
- `src/oryxenai/web/routes.py`
- `src/oryxenai/web/static/app.js`
- `docs/code-generator-architecture/free-host-deployment.md`
- `docs/code-generator-architecture/live-preview-and-deployment.md`
