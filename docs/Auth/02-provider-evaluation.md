# Authentication provider evaluation

## Evaluation criteria

The useful criteria for OryxenAI are not enterprise feature count. They are:

- one reliable Google sign-in/sign-up flow;
- compatibility with Jinja2, vanilla JavaScript, FastAPI, and PostgreSQL;
- server-side token verification and user administration;
- a free allowance far above roughly ten users;
- low setup and maintenance burden for AI coding agents;
- safe production-domain and redirect behavior;
- no application-owned passwords;
- no need to redesign the durable worker or add a frontend framework.

## Comparison

| Option | Fit | Free allowance at research date | Main benefit | Main cost/risk | Result |
| --- | --- | --- | --- | --- | --- |
| Clerk | Excellent when an owned domain is available | Hobby: 50,000 monthly retained users per app; Google/social connections included | Prebuilt accessible sign-in UI, vanilla ClerkJS, official Python backend SDK, user ban/delete APIs | Production requires an owned domain, production keys, and custom Google OAuth credentials; Hobby has fixed seven-day sessions and short log retention | **Recommended** |
| Supabase Auth | Good, especially for a personal/test deployment without an app domain | Free: 50,000 MAU and social OAuth | Can share the existing managed Postgres vendor; Supabase hosts its OAuth callback | More app-owned UI/session code; Google production-domain rules still apply; free projects can pause; authorization still belongs in FastAPI | **Fallback, not combined with Clerk** |
| Firebase Auth | Technically good | Spark supports non-phone auth; published auth limits are far above ten users | Very mature Google sign-in and Python Admin token verification | Adds Firebase/service-account administration while OryxenAI data remains PostgreSQL; less benefit than Clerk/Supabase for this stack | Not selected |
| Auth0 | Technically good | Free plan publishes up to 25,000 external active users | Mature FastAPI/API authorization tooling | Tenant, application, API audience, action/role configuration is more than this two-role personal app needs | Not selected |
| Build OAuth/session auth ourselves | Poor | Hosting-only cost | No vendor UI | We would own OAuth state/PKCE, cookies, key rotation, account linking, abuse protection, recovery, deletion, and security maintenance | Rejected |

Pricing is not a permanence guarantee. Recheck the provider pages at planning
and deployment time.

## Why Clerk is the primary recommendation

ClerkJS is the foundational browser SDK and its prebuilt `mountSignIn()` view
works with ordinary JavaScript. That matches the checked-in frontend without a
React/Next migration. The official `clerk-backend-api` Python package supports
request authentication and async Backend API operations.

The division of responsibility is clean:

```text
Google -> Clerk sign-in UI/session -> Clerk-signed session token
                                      |
browser fetch ------------------------+
                                      v
FastAPI verifies token -> app_users -> owner/admin policy -> PostgreSQL/jobs
```

Use the prebuilt view, not a custom OAuth state machine. The same Google button
signs in an existing user or creates a new one. OryxenAI then performs its own
synchronous first-request bootstrap and username onboarding.

Clerk should not own OryxenAI roles or portfolio quotas:

- Custom token claims can be stale for the token refresh interval.
- Fetching Clerk metadata on every request adds latency and Backend API use.
- `unsafeMetadata` is client-editable and cannot authorize anything.
- Roles, ownership, quota, deletion state, and audit records belong next to the
  resources they govern in PostgreSQL.

Clerk's subject (`user_...`) is the external identity key. The application may
fetch the Clerk user once during just-in-time provisioning to obtain the
verified primary email and display details. Returning requests resolve the
subject locally.

## Clerk production requirements

Development is intentionally easier: Clerk supplies shared Google credentials
for a development instance. Production is different:

1. Own a domain and be able to change its DNS.
2. Create/activate a Clerk production instance for that domain.
3. Use production `pk_live_...` and `sk_live_...` values, never dev keys.
4. Create a Google web OAuth client, configure the consent screen, add the app's
   exact JavaScript origin, and paste Clerk's exact Authorized Redirect URI into
   Google Cloud.
5. Put the Google OAuth app into production for a real public deployment.
6. Configure exact `authorizedParties`/allowed origins; no wildcard.
7. Configure Clerk-required CSP sources for the app's Clerk Frontend API,
   images, styles, workers, bot-protection frames, and connections.

Clerk explicitly says development instances have a relaxed security posture,
are capped, use different cross-site session mechanics, and are not suitable
for production workloads. A host-provided `*.vercel.app` domain cannot be used
for Clerk production because Clerk needs DNS control; the same ownership issue
applies to relying solely on other host-controlled subdomains.

## Supabase Auth fallback

Use this path only when the owner confirms there will be no owned application
domain. Supabase Auth can use Google OAuth with:

- a Google Cloud web OAuth client;
- the Supabase project's callback URL as Google's authorized redirect URI;
- the deployed host URL as the Supabase Site URL/allowed redirect; and
- a browser `signInWithOAuth({ provider: "google" })` call.

This removes Clerk's production-domain requirement, not Google's rules. Google
Testing status is limited to named test users and has testing-mode warnings and
authorization lifetime restrictions. A public production OAuth app must follow
Google's homepage, privacy/terms, secure-origin, publishing, and applicable
domain/brand-verification rules. For this reason, the no-domain path is suitable
for a small known-user demo, but an owned domain remains the recommendation for
a polished public deployment.

The FastAPI backend must still verify the access token, map `sub` to an
application user, and perform the same role/owner/quota checks documented here.
Do not rely on `user_metadata` for authorization. If Supabase tables are exposed
through the Data API, they also require RLS with ownership predicates; `TO
authenticated` alone is not object authorization.

Using Clerk for identity does not prevent using Supabase as managed PostgreSQL.
That is the preferred Clerk topology: Clerk Auth plus Supabase Postgres. Do not
also enable Supabase Auth, because two identity systems create duplicate users,
two token formats, ambiguous logout/deletion, and more routes to test.

## Why the other options lose

Firebase Auth has an excellent Google flow and its Python Admin SDK can verify
ID tokens. It is not a bad product; it simply adds a Firebase project and
service-account credential without replacing OryxenAI's PostgreSQL ownership
and quota work or providing as direct a prebuilt UI fit as Clerk.

Auth0 provides a FastAPI SDK and a generous free plan, but its normal setup
introduces tenant/application/API-audience concepts and more authorization
configuration. OryxenAI needs two local roles and one owner relation, not a
general enterprise identity architecture.

Self-built email/password auth is outside the acceptable risk/complexity
budget. Even a correct password database would add verification email,
reset/recovery, breach response, password hashing policy, credential stuffing
protection, and session revocation. There is no product benefit here.

## Sign-in methods

### V1: Google only

This is the recommendation. It is one button, one recovery story (the Google
account), one end-to-end flow, and no OryxenAI password. Use a full-page redirect
so mobile browsers work reliably; Google does not permit OAuth in embedded
WebViews.

### Optional later: email verification code

If users without Google accounts become a real requirement, enable Clerk email
verification code/OTP through the prebuilt sign-in view. Do not add an
application password. Email OTP adds delivery, spam, retry, lockout, and
recovery tests, so it should not be part of the first minimum flow.

Two separate Google admin accounts provide basic administrator recovery. Each
admin should enable strong two-step verification on their Google account.

## Official sources

- [Clerk pricing](https://clerk.com/pricing)
- [Clerk JavaScript quickstart](https://clerk.com/docs/js-frontend/getting-started/quickstart)
- [Clerk JavaScript SignIn view](https://clerk.com/docs/js-frontend/reference/components/authentication/sign-in)
- [Clerk Python SDK](https://github.com/clerk/clerk-sdk-python)
- [Clerk Google connection](https://clerk.com/docs/guides/configure/auth-strategies/social-connections/google)
- [Clerk environments](https://clerk.com/docs/guides/development/managing-environments)
- [Clerk production deployment](https://clerk.com/docs/guides/development/deployment/production)
- [Supabase pricing](https://supabase.com/pricing)
- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Firebase Google sign-in](https://firebase.google.com/docs/auth/web/google-signin)
- [Firebase server token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [Auth0 pricing](https://auth0.com/pricing)
- [Auth0 FastAPI API quickstart](https://auth0.com/docs/quickstart/backend/fastapi)
