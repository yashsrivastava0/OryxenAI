# Security and edge cases

## Security objective

No internet-facing auth system is “completely secure.” The correct objective is
a small, provider-backed, fail-closed design with explicit trust boundaries,
least data, strong object authorization, revocable sessions, safe errors, and
verified deployment behavior.

Clerk handles identity proof and session issuance. OryxenAI remains responsible
for authorization, tenant isolation, quota, admin safety, logs, persistence,
generated-preview isolation, and deployment configuration.

## Required controls

### Token verification

Use Clerk's official Python backend SDK `authenticate_request` (names may vary
by the pinned SDK release) with:

- accepted token type restricted to session tokens;
- exact production/development `authorized_parties` origins;
- Clerk JWT public key for networkless verification where supported;
- issuer/signature, expiry/not-before, and subject validation;
- a small default clock skew only;
- no fallback that trusts a decoded but unverified JWT.

Clerk session tokens are short-lived and ClerkJS refreshes them. The browser
obtains `Clerk.session.getToken()` for API calls. Do not persist the token in
`localStorage`, render it into HTML, print it, or forward it to the worker or
generated preview.

### Authorization on every object

Authentication without an owner predicate is still vulnerable. Apply
owner-or-admin checks to:

- sessions and every agent-stage operation;
- runs, events, jobs, plans, source manifests/files, and errors;
- Build Preparation packs and object metadata;
- Code Generator preview/quality/source endpoints;
- deletion, retries, approval, revise, and regeneration;
- any future download/export URL.

Foreign and nonexistent UUIDs should produce the same 404 behavior.

### CSRF, origin, and CORS

Prefer same-origin browser/API deployment. Send a Clerk bearer session token in
the authorization header for fetch requests. Validate Clerk's `azp` through
`authorizedParties`; Clerk warns that omitting it can enable a subdomain-cookie
leak/CSRF class of attack.

- no wildcard allowed origins;
- no credentialed `Access-Control-Allow-Origin: *`;
- if a separate frontend is later used, allow only its exact HTTPS origin and
  test preflight, auth headers, redirects, and logout;
- state-changing operations remain POST/PUT/DELETE and use same-site/origin
  checks as defense in depth;
- validate `return_to` to prevent open redirects.

### Content Security Policy

The current app has basic security headers but no Clerk-specific CSP. Clerk's
plain JavaScript UI requires its configured Frontend API plus image,
bot-protection, worker, frame, connection, and runtime style sources. Build a
manual policy from the current Clerk CSP guide and the exact production FAPI
domain; do not paste a stale wildcard-heavy example.

Preserve at least:

- restrictive `default-src`;
- exact Clerk/FAPI and protection hosts required by the active configuration;
- `frame-ancestors` appropriate to app pages;
- `object-src 'none'`, safe `base-uri`, and no unexpected form targets;
- existing preview CSP as a separate policy. Do not grant generated preview
  code Clerk or app API origins.

### Secrets and configuration

Secret values belong only in `.env` locally and hosting-provider secret stores:

- `CLERK_SECRET_KEY`;
- optional webhook signing secret;
- Google OAuth client secret (stored in Google/Clerk dashboards, not needed by
  OryxenAI runtime when Clerk owns the connection);
- database/object-store/provider credentials.

The Clerk publishable key and allowed origins are not secrets but are
environment-specific. Never use development keys in production or production
keys in tests. Never log environment dumps.

### Role safety

- Default every JIT-created user to `user`.
- Bootstrap admin only after fetching a verified primary email from Clerk's
  Backend API and matching the normalized server-side two-email allowlist.
- Persist the role in PostgreSQL.
- Never accept `role`, quota, owner ID, Clerk user ID, or email from a profile
  update body.
- Never authorize from Clerk `unsafeMetadata`; avoid custom role claims for v1.
- Admin endpoints repeat the DB role check and create an audit event.

### Password and provider-token safety

OryxenAI never asks for a Google password. It also does not request/store a
Google OAuth access or refresh token because it does not need Google APIs. Use
only the basic identity scopes required for profile/email. Fewer scopes make
Google consent and verification simpler.

### Logging and privacy

Continue request IDs, but redact:

- `Authorization`, `Cookie`, `Set-Cookie`, Clerk/Google tokens, webhook
  signature/secret, OAuth code, and auth query artifacts;
- full emails in normal logs (mask or log internal user ID);
- raw intake/resume content from auth/audit logs.

Store only the verified primary email, username, optional display/avatar, role,
status, and external subject required for the product. Define a deletion and
audit retention policy before deployment. Add privacy/terms content before a
public launch.

## Edge-case behavior matrix

| Scenario | Required behavior |
| --- | --- |
| User cancels Google consent | Return to sign-in with a safe retry message; no local user/session is created. |
| OAuth callback is refreshed/backed into | Clerk completion is idempotent; resolve `/me` and route normally, no duplicate user. |
| Existing Google user clicks “sign up” | Clerk's Google flow resolves the existing identity; OryxenAI JIT lookup returns the same local user. |
| New user opens two callback tabs | Unique Clerk subject + transactional upsert yields one `app_users` row. |
| Two users claim same username | Database unique constraint picks one; loser gets `409 USERNAME_TAKEN`. |
| Same user submits username twice | Same normalized username is idempotent; a different rename is denied in v1. |
| Invalid/expired token | 401; refresh once through ClerkJS, then clear state and sign in. No infinite retry. |
| Token has wrong origin/issuer/key | 401 and safe log with reason class only. |
| Clerk UI/API is unavailable | Sign-in/bootstrap shows provider unavailable and bounded retry; no unauthenticated bypass. |
| Database is cold/paused | 503/readiness failure; preserve Clerk session and retry later, do not create partial quota/user state. |
| Render app is cold | Show provider loading/cold-start behavior; timeout is not interpreted as bad credentials. |
| User is suspended while tab is open | Next API call is 403, timers stop, app data clears, Clerk session is banned/revoked. |
| Admin deletes a user with running jobs | Local deletion marker blocks finalization; Clerk ban revokes access; cleanup retries idempotently. |
| User guesses another session/run/job UUID | Same 404 as nonexistent; no metadata leak. |
| User edits `sessionStorage` session UUID | Backend owner guard rejects; browser clears invalid remembered ID. |
| Normal user double-clicks create/start | Entitlement row lock/idempotency returns one session/run. |
| Code generation fails before promotion | Success quota remains unconsumed; retry resumes same run/variant. |
| User calls `/regenerate` directly | Normal user gets variant-locked 409 even if UI hides the button. |
| Promotion crashes between object pointer and DB update | Existing reconciler completes exact run; quota update is idempotent and bound to the same receipt. |
| Success exists but user deletes browser data | Server entitlement still blocks another project. |
| User signs in with another Google account | It is a separate Clerk/local user and receives a separate entitlement; do not merge automatically. |
| Google email/display name changes | Ownership remains on Clerk subject/internal user ID; sync display data safely without changing role. |
| Admin bootstrap email signs up again after identity deletion | Treat as the configured break-glass admin behavior; audit it and consider removing bootstrap allowlist after both stable admins exist. |
| Last admin attempts self-delete/demotion | Deny until another active admin exists or an explicit break-glass procedure is confirmed. |
| Webhook is forged/replayed/out of order | Verify signature, persist event ID/idempotency, tolerate ordering, and never use webhook arrival for immediate login. |
| Clerk `user.deleted` arrives after local admin cleanup | Idempotent no-op/reconciliation. |
| Preview URL is leaked | It remains an unlisted capability and can be opened; admin/project deletion revokes the active pointer. Strict privacy is separate scope. |
| Browser back after sign-out | No private server data in HTML; protected fetch returns 401; cached UI was cleared before navigation. |
| Cookies/storage blocked | Clerk UI shows a recoverable auth error; app never pretends the user is signed in. |
| User signs in inside an embedded WebView | Do not support; use top-level system browser because Google blocks OAuth WebViews. |
| Auth provider rate limit | Surface 429 with backoff; no polling loop or user creation retry storm. |

## Admin-specific risk controls

The two admin accounts are the largest-impact identities. For v1:

- use two distinct Google accounts controlled by different trusted people;
- enable Google two-step verification and retain recovery methods;
- do not share browser profiles or credentials;
- require an explicit confirmation containing the target username for delete;
- consider a short “recent sign-in” requirement for user deletion/quota reset if
  Clerk exposes a reliable first-factor age in the pinned integration;
- prevent deletion of the last active admin;
- audit every admin mutation.

Clerk Hobby does not include every advanced production security feature. Do not
claim application MFA if the selected plan/configuration does not provide it.

## Webhook position

Webhooks are useful for reconciling identity changes/deletion, but Clerk notes
that delivery is asynchronous and can fail. Therefore:

- `/api/v1/me` creates the local user synchronously on first authenticated
  request;
- `user.updated` refreshes safe profile fields only;
- `user.deleted` marks/deletes locally through an idempotent handler;
- the endpoint is public from an auth-routing perspective but rejects every
  request without a valid webhook signature;
- raw body bytes must be preserved for verification;
- event IDs are deduplicated.

## Security acceptance checks

- no-token requests to every protected API produce 401;
- valid normal token + foreign UUID produces 404 for every resource family;
- normal token cannot access admin/development/system operations;
- user-supplied role/owner/quota fields are rejected as extra input;
- wrong `azp`, issuer, audience (if configured), signature, expired token, and
  pending session are rejected;
- logs and responses contain no token/cookie/secret;
- CSP works with Clerk and still blocks unauthorized origins;
- logout plus back/refresh cannot retrieve private API data;
- suspension revokes access in both app DB and Clerk;
- deletion removes preview visibility and safely handles running jobs;
- quota/variant tests pass under concurrent requests.

## Official security references

- [Clerk manual JWT verification](https://clerk.com/docs/guides/sessions/manual-jwt-verification)
- [Clerk request authentication](https://clerk.com/docs/reference/backend/authenticate-request)
- [Clerk session tokens](https://clerk.com/docs/guides/sessions/session-tokens)
- [Clerk CSP requirements](https://clerk.com/docs/guides/secure/best-practices/csp-headers)
- [Clerk webhook synchronization caveats](https://clerk.com/docs/guides/development/webhooks/syncing)
- [Clerk ban user](https://clerk.com/docs/reference/backend/user/ban-user)
- [Supabase JWT guidance](https://supabase.com/docs/guides/auth/jwts)
