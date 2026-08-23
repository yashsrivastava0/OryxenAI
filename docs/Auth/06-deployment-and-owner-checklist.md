# Deployment and owner checklist

This separates tasks that require the project owner's accounts/consent from
work coding agents can complete. Never paste secret values into chat, source,
documentation, screenshots, logs, or commits.

## First owner decision

### If you own/can obtain an application domain

Use Clerk as recommended. You need DNS access. Clerk's Hobby service is free at
this project's size, but domain registration may not be.

### If you will not own a domain and require absolute zero spend

Tell the implementation planner to switch the identity provider to Supabase
Auth. Do not deploy Clerk development credentials. The authorization, username,
ownership, quota, admin, worker, and test design in these documents still
applies with the external subject changed to Supabase's user UUID. This can
support a small named-user/personal deployment, but it does not waive Google's
production publishing, homepage, privacy, or domain rules.

## What you must do for Clerk development

1. Create/sign in to a Clerk account.
2. Create one OryxenAI Clerk application.
3. In the development instance, enable Google for all users and disable other
   sign-in methods for v1.
4. Keep public sign-up open unless you deliberately choose an invite/allowlist
   plan; the product enforces its own portfolio quota.
5. Copy only these values into local `.env`:
   - development Clerk publishable key;
   - development Clerk secret key;
   - optional JWT public key if the chosen backend verification path uses it.
6. Provide the two intended admin Google email addresses through the proposed
   admin-bootstrap environment value. They should be distinct and verified.
7. Each admin tests a real Google sign-in in the development instance.

You do not provide a Google password. You do not create an OryxenAI password.

## What you must do for Clerk production

1. Choose the final HTTPS app origin, for example
   `https://app.your-domain.example`.
2. Add the custom domain to the hosting provider and verify TLS.
3. Create/activate Clerk's production instance for the owned root domain.
4. Add every DNS record Clerk requests. If using Cloudflare DNS, follow Clerk's
   guidance about DNS-only records during verification.
5. Create/configure a Google Cloud project and OAuth consent screen.
6. Create a **Web application** OAuth client.
7. Add the exact app origin under Google Authorized JavaScript origins.
8. Copy the exact Authorized Redirect URI displayed by Clerk into Google
   Authorized Redirect URIs. Do not invent this URI from memory.
9. Paste the Google Client ID and Client Secret into Clerk's production Google
   connection, not into OryxenAI source.
10. Publish a real homepage, privacy policy, and terms/support information on
    the application domain; configure the matching OAuth consent-screen fields.
11. Verify authorized domains/brand if Google requires it for the chosen
    production presentation, and request only basic identity scopes.
12. Put Google's external OAuth app into production for a reliable public
    deployment.
13. Add production Clerk keys and the exact allowed app origin to the hosting
    provider's environment settings, then redeploy.
14. Recreate any Clerk production settings that do not copy from development,
    including Google connection, paths, DNS, and webhook.
15. Test both admin accounts and a normal account on the final domain in an
    ordinary top-level browser window and an incognito profile.

Google’s testing mode can restrict access to configured test users. That is
useful for a closed demo, but Google documents a 100-test-user ceiling, warning
behavior, and a seven-day authorization lifetime. It is not the polished,
open production-ready state this project asks for.

## Proposed OryxenAI configuration names

The later implementation should keep non-secret policy in TOML and values in
environment variables. Names may be finalized by the plan, but one consistent
set is:

```text
CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
CLERK_JWT_KEY=
CLERK_WEBHOOK_SIGNING_SECRET=
ORYXENAI_ADMIN_BOOTSTRAP_EMAILS=
```

Committed `config/app.toml`/deployment overlays can hold:

```toml
[auth]
provider = "clerk"
required = true
allowed_origins = ["https://app.example.com"]
sign_in_path = "/sign-in"
after_sign_in_path = "/auth/continue"
normal_user_portfolio_limit = 1
normal_user_variant_limit = 1
```

Do not commit a real domain as an immutable architecture fact if deployments
will vary; use the production overlay/environment mechanism already established
by the repository.

The application should fail readiness/production startup when auth is required
but keys/origins are missing or development keys are used. Test configuration
may override the auth dependency with deterministic signed claims. A generic
“auth disabled” switch must be impossible in a production environment.

## What coding agents will implement later

- pin Clerk's Python dependency in `pyproject.toml`/`uv.lock`;
- use the official ClerkJS dashboard snippet/prebuilt UI with an explicitly
  reviewed major/version policy;
- add auth settings and redacted doctor output;
- implement token verification/current-user dependencies;
- add user, entitlement, owner, and audit migrations/models/repositories;
- protect every current route and remove development surfaces from production;
- add sign-in, continuation, onboarding, app, and admin shells;
- inject short-lived bearer tokens through the central fetch helper;
- implement JIT provisioning and verified webhook reconciliation;
- enforce one session/variant/success and admin bypass;
- make suspension/deletion/quota reset idempotent and auditable;
- add unit/API/PostgreSQL/browser tests and production smoke runbook;
- update `AGENTS.md`, README, architecture/decision/change records only when
  implementation status and decisions actually change.

## Database/hosting setup you may need to provide

Auth does not replace the current runtime infrastructure:

- managed PostgreSQL credentials;
- a place to run the API;
- a separate durable worker runtime;
- private R2/S3-compatible object storage;
- a preview gateway and its separate preview origin/domain when hosted;
- model/resource-provider credentials for real generation.

If Supabase hosts PostgreSQL, use the connection method appropriate to the
runtime: direct IPv6 for a compatible persistent backend, shared pooler session
mode for a persistent IPv4-only backend, and transaction mode for serverless
clients. OryxenAI is a persistent API/worker, not a browser Data API client.

Run Alembic migrations as the existing one-shot deployment step before API and
worker start. Never let both processes race migrations.

## Free-service reality

No set of free tiers can honestly promise an always-on production SLA:

- Clerk Hobby has ample identity capacity for ten users, but production needs
  an owned domain and has plan-specific session/log/security limits.
- Supabase Free includes ample auth capacity and a small PostgreSQL database,
  but low-activity projects can pause after a week and need manual restoration.
- Render Free web services sleep after 15 minutes and can take about a minute to
  wake. Their filesystem is ephemeral.
- Render does not offer a free Background Worker instance, while OryxenAI's
  checked-in architecture requires a durable worker process.
- Render's free PostgreSQL expires after the documented limited period, so it
  is not durable project storage.
- Vercel's function duration model does not replace the long-running durable
  worker and browser-verification pipeline.

Therefore “free” is suitable for a hobby/demo deployment with cold starts and
manual care. Auth can be correct, but full-platform always-on readiness needs a
worker-capable host and durable services. Do not report the deployed product as
perfectly ready from an auth callback test alone.

## Production URL worksheet

Fill this in during deployment; do not guess values:

```text
App origin:                     https://________________
Sign-in URL:                    https://________________/sign-in
Auth continuation URL:         https://________________/auth/continue
Clerk Frontend API domain:      https://________________
Clerk Authorized Redirect URI: https://________________  (copy from Clerk)
Google JS origin:               https://________________
Clerk webhook URL:              https://________________/api/v1/auth/webhooks/clerk
API allowed origin/party:       https://________________
Preview origin/domain:          https://________________  (separate trust boundary)
```

Do not add paths to Google's Authorized JavaScript origins; origins are
scheme+host+optional port. Do not substitute the app callback for Clerk's
provider callback URI.

## Deployment acceptance run

### Identity and routing

- fresh browser `/` shows only the sign-in entry;
- Google cancel and provider error return safely;
- new Google user returns, is provisioned once, must choose username, then
  reaches `/app`;
- returning user bypasses onboarding and resumes the same portfolio;
- sign-out, back, refresh, and direct protected URLs do not reveal data;
- two admin accounts reach `/admin`; normal user cannot.

### Authorization

- user A cannot read/write user B session, run, job, source, or preview metadata
  by changing IDs;
- all existing agent routes have owner/admin dependencies;
- system/development/fixture routes are absent or admin-only as specified;
- suspended/deleted sessions stop working promptly.

### Quota and generation

- repeated session creation returns the same normal-user project;
- double/multi-tab Code Generator start creates one variant;
- failed run retries same variant without consuming success;
- direct normal-user regenerate is denied;
- verified promotion consumes exactly one success;
- post-success create/start/regenerate are denied and final preview remains
  readable;
- admin generation is unlimited and admin quota reset is explicit/audited.

### Operations

- migration, API, worker, database, Clerk, object storage, and preview gateway
  each have current evidence;
- production Google OAuth uses production status and final URLs;
- no secrets/tokens/emails appear in logs or responses;
- admin project deletion revokes preview and handles queued/running jobs;
- backup/recovery and last-admin protections are exercised.

## Owner-facing primary sources

- [Set up a Clerk account/app](https://clerk.com/docs/getting-started/quickstart/setup-clerk)
- [Configure Google in Clerk](https://clerk.com/docs/guides/configure/auth-strategies/social-connections/google)
- [Deploy Clerk to production](https://clerk.com/docs/guides/development/deployment/production)
- [Clerk environment differences](https://clerk.com/docs/guides/development/managing-environments)
- [Render free limitations](https://render.com/docs/free)
- [Render Blueprint service plans](https://render.com/docs/blueprint-spec)
- [Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
- [Google OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
- [Google app audience and publishing status](https://support.google.com/cloud/answer/15549945)
