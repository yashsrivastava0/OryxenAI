# OryxenAI authentication research

Status: research and implementation handoff only. No authentication code,
database migration, Clerk tenant, Google OAuth client, or deployed environment
is created by these documents.

Last researched: 2026-08-23. Provider prices and dashboard steps are
time-sensitive and must be rechecked against the linked official sources when
implementation or deployment begins.

## Recommendation

Use **Clerk as the only identity provider**, with **Google as the only v1
sign-in method**. Use Clerk's prebuilt JavaScript `<SignIn />` view on the
existing Jinja2/vanilla-JS frontend and Clerk's official Python backend SDK to
verify every protected FastAPI request.

Keep application authorization in OryxenAI's PostgreSQL database:

- Clerk proves who the caller is.
- `app_users` stores the OryxenAI username, role, status, and Clerk subject.
- `portfolio_sessions.owner_user_id` establishes ownership.
- a quota record binds a normal user to one project and one design variant.
- backend dependencies enforce owner-or-admin access on every session, run,
  stage, and administrative route.

Do not ask for, receive, or store a Google password. Google displays and
processes its own credential screen. OryxenAI receives only Clerk's verified
identity/session result and stores the minimum app data it needs.

### Important free-deployment qualification

Clerk's Hobby plan is large enough for this project, but a Clerk production
instance requires a domain the owner controls and production Google OAuth
credentials. Clerk includes custom-domain support on Hobby, but registering a
domain can cost money. A Clerk development instance is not an acceptable
production workaround.

If the project must deploy without an owned domain and without any spend,
choose **Supabase Auth instead of Clerk**, not in addition to Clerk. Supabase
itself can host the Google OAuth callback on its free plan without a custom app
domain, but the app must own more of the sign-in UI/session integration and a
dormant free Supabase project can pause. Google still applies its own OAuth
publishing, homepage, privacy, authorized-domain, and test-user rules, so this
is a personal/test fallback rather than a way around Google's production
requirements. It is detailed in
[02-provider-evaluation.md](02-provider-evaluation.md).

## Exact product policy proposed for planning

1. One top-level **Continue with Google** entry point handles both sign-up and
   sign-in. There is no separate password flow.
2. A first-time authenticated person chooses one unique OryxenAI username.
   Their Google display name/avatar may be shown as a convenience, but email is
   not their public username and ownership is never keyed by email.
3. A normal user owns one portfolio session and one design variant. Failed
   infrastructure/model attempts may retry the same variant. Explicit
   regeneration to a new variant is denied.
4. The quota is consumed only when Code Generator has a verified, hash-bound,
   promoted `active_preview`. Earlier stages and failed builds do not count as
   a successful portfolio.
5. After that success, the normal user's project becomes read-only apart from
   viewing it and signing out. Deleting it does not silently restore quota.
6. An admin has no portfolio quota and may inspect any user/project, suspend or
   restore users, delete any project, reset a normal user's quota, and delete a
   user. Destructive operations are audited and target one resource at a time.
7. Two initial admins are bootstrapped from two verified Google email addresses
   supplied through deployment secrets. Their `admin` role is then persisted
   server-side. No role comes from client-editable metadata.

## Why this is the smallest complete design

- It uses the current server-rendered frontend instead of introducing React or
  Next.js solely for authentication.
- Clerk owns OAuth, session issuance, account protection, and sign-in UI.
- OryxenAI already owns PostgreSQL, durable jobs, sessions, and all business
  state, so it also owns roles, object authorization, and quotas.
- No Clerk Organizations, custom JWT role claims, application passwords,
  password reset, invite system, Redis, or new auth microservice is needed.
- Just-in-time user provisioning is synchronous and reliable; webhooks are
  reconciliation aids, never a prerequisite for first-login routing.

## Research set

- [01-current-system-auth-surface.md](01-current-system-auth-surface.md) — the
  current unauthenticated routes and repository-specific integration risks.
- [02-provider-evaluation.md](02-provider-evaluation.md) — Clerk, Supabase
  Auth, Firebase Auth, Auth0, and self-built auth comparison.
- [03-user-flow-and-route-contract.md](03-user-flow-and-route-contract.md) —
  screens, redirects, APIs, status codes, and browser behavior.
- [04-authorization-quota-and-data-model.md](04-authorization-quota-and-data-model.md)
  — users, ownership, roles, the one-portfolio rule, workers, and deletion.
- [05-security-and-edge-cases.md](05-security-and-edge-cases.md) — security
  controls, threats, failures, and edge-case behavior.
- [06-deployment-and-owner-checklist.md](06-deployment-and-owner-checklist.md)
  — exactly what the project owner and coding agents must configure.
- [07-implementation-handoff.md](07-implementation-handoff.md) — bounded work
  packages and acceptance criteria for the future planning session.
- [08-primary-sources.md](08-primary-sources.md) — dated primary-source index.

## Facts the next planning session must not lose

- Adding a sign-in screen alone is not auth. Every existing route that accepts
  a `session_id` can currently read or mutate that session without ownership
  checks.
- A normal user's same-variant retry and an explicit new-variant regeneration
  are different operations and must remain different.
- Workers cannot verify a browser token after the request is gone. The API must
  authorize before enqueueing, bind the owner/actor to durable work, and the
  worker must recheck that binding before finalization.
- The current preview gateway intentionally receives no app cookies. Auth
  protects who can discover/control a preview; the stable opaque preview URL is
  an unlisted capability URL, not a private authenticated document.
- Free hosting does not mean always-on. Render free web services sleep and have
  no free background-worker instance; Supabase free projects can pause; Vercel
  functions do not replace OryxenAI's durable worker.

## Primary recommendation sources

- [Clerk JavaScript quickstart](https://clerk.com/docs/js-frontend/getting-started/quickstart)
- [Clerk Google social connection](https://clerk.com/docs/guides/configure/auth-strategies/social-connections/google)
- [Clerk Python SDK repository](https://github.com/clerk/clerk-sdk-python)
- [Clerk production deployment](https://clerk.com/docs/guides/development/deployment/production)
- [Clerk pricing](https://clerk.com/pricing)
- [Supabase Auth Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
