# Security and edge cases

## Security objective

No internet-facing auth system is completely secure. The target is a small,
provider-backed, fail-closed design with explicit trust boundaries, least data,
object authorization, bounded session/revocation behavior, safe errors, and
deployed-browser verification.

Supabase handles Google identity proof and session issuance. OryxenAI remains
responsible for admission, roles, ownership, quota, admin safety, logs,
persistence, preview isolation, provider spending gates, and deployment.

## Token verification

For every protected FastAPI request:

- require `Authorization: Bearer <Supabase access token>`;
- accept only the configured Supabase issuer and audience;
- verify signature, allowed algorithm, key ID, expiry, not-before if present,
  and UUID subject;
- use the exact project JWKS endpoint and a bounded cache;
- refresh JWKS once for an unknown key ID, never on every request;
- reject decoded-but-unverified tokens and algorithm confusion;
- apply only a small configured clock skew; and
- require a current active local `app_users` row after cryptographic identity
  verification.

The confirmed project exposes an asymmetric signing key. Recheck at
implementation time; do not silently fall back to trusting a legacy shared
secret. If the project later uses a shared-secret signer, follow Supabase's
current online validation guidance explicitly.

The pinned Supabase browser client manages session refresh. OryxenAI must not
copy tokens into custom storage, render them into HTML, include them in URLs,
forward them to workers/previews, or log them.

## First-login identity and allowlist safety

On the first authenticated `/api/v1/me` request:

1. Verify the JWT.
2. Resolve the current user through the Supabase Auth server using the caller's
   token and publishable key.
3. Use only the verified top-level identity/email returned by Auth.
4. Match normalized email against the two bootstrap administrators or normal
   allowlist.
5. For a normal user, transactionally enforce the 15-user capacity.
6. Upsert by immutable Supabase `sub` and create local entitlement once.

Never use `user_metadata` for role, allowlist, owner, quota, or status. Never
accept those values from a profile/onboarding request body.

An authenticated but unapproved Supabase identity receives 403 and no local
user, entitlement, portfolio, run, or job.

## Authorization on every object

Apply owner-or-admin checks to:

- sessions and all agent-stage reads/writes;
- runs, attempts, events, jobs, plans, sources, errors, and quality receipts;
- Build Preparation objects and metadata;
- Code Generator start, retry, regenerate, promotion, and preview controls;
- downloads/exports; and
- every admin mutation.

Foreign and nonexistent identifiers return the same 404. Hiding a UI action is
not authorization.

## Origin, CORS, redirects, and CSRF

Prefer one application origin. Bearer tokens reduce cookie-CSRF exposure, but
state-changing requests still require defense in depth:

- exact configured allowed origins; no wildcard credentials;
- reject unexpected `Origin` on unsafe methods when present;
- no CORS unless a later deployment explicitly needs an exact HTTPS frontend;
- allow only exact Supabase callback/redirect destinations;
- validate app `return_to` as a local relative route;
- no open redirects, backslashes, protocol-relative URLs, or arbitrary hosts;
- state-changing operations use POST/PUT/PATCH/DELETE; and
- generated previews never receive app credentials.

## Content Security Policy

Serve the pinned Supabase browser bundle from OryxenAI static assets. Build the
application CSP from the exact deployment:

- restrictive `default-src`;
- self-hosted scripts/styles where possible;
- exact Supabase project HTTPS/WebSocket connections required by Auth;
- exact Google account/frame endpoints required by the chosen redirect flow;
- `object-src 'none'`, restrictive `base-uri`, `form-action`, and
  `frame-ancestors`;
- no broad wildcard added to make OAuth work; and
- separate preview CSP that cannot call the app or Supabase.

## Secrets and environment

Local `.env` or the hosting secret store may contain:

- `SUPABASE_SECRET_KEY` (server only);
- database/object-storage/model-provider credentials;
- bootstrap administrator and normal-user allowlists; and
- other deployment-specific secrets.

The Supabase URL and publishable key are browser-safe but environment-specific.
Do not dump the environment or return secret presence details to normal users.
Production must reject missing/mismatched project, issuer, audience, key, or
origin configuration.

The Google Client Secret stays in Supabase. OryxenAI does not need the downloaded
Google OAuth JSON file.

## Session revocation and local denial

Supabase user deletion does not necessarily invalidate every already-issued
access token immediately. OryxenAI therefore checks local status on every
request. Suspension/deletion denies locally first, then calls the current
Supabase Admin API to revoke/ban/delete provider access. If that provider call
fails, the local account remains denied and cleanup is retryable.

Do not cache role/status/entitlement decisions across requests.

## Logging and privacy

Redact:

- authorization/cookie headers and Supabase/Google tokens;
- OAuth codes, state, query, and fragment artifacts;
- publishable/secret keys and database credentials;
- full emails in ordinary logs; and
- raw resume/intake content from auth/admin audit events.

Store only the minimum verified identity projection, username, optional safe
display/avatar, role, status, ownership, entitlement, and audit data. Define
audit/deletion retention and publish privacy/terms pages before public launch.

## Edge-case matrix

| Scenario | Required behavior |
| --- | --- |
| User cancels Google | Return safely to sign-in; create no local state. |
| Callback refreshed or opened twice | Session restore and `/me` upsert are idempotent. |
| Existing Google user uses the same button | Same Supabase subject and local user are resumed. |
| Two callback tabs provision one user | Unique subject plus transaction yields one row/slot. |
| Auth succeeds but email is not approved | 403; no user/project/job state. |
| Sixteenth normal user races admission | Capacity lock admits at most one up to 15; remainder get 409/403 policy response. |
| Admin email logs in | Verified match persists admin role; consumes no normal slot. |
| Two users claim one username | Unique constraint chooses one; loser gets 409. |
| Same user resubmits same username | Idempotent; different rename denied. |
| Missing/expired token | 401; refresh once, then clear and sign in. |
| Wrong issuer/audience/key/algorithm | 401; safe reason class only in logs. |
| JWKS rotation | Unknown key triggers one bounded refresh; failure stays 401/503, never bypass. |
| Supabase Auth unavailable | Provider-unavailable response with bounded retry. |
| Supabase/Postgres project paused | Readiness 503; preserve browser session and avoid partial provisioning. |
| User suspended with an open tab | Next API call is 403; polling/data clears; provider revocation retries. |
| Admin deletes user with running jobs | Local marker blocks worker finalization; cleanup is resumable. |
| Deleted email remains in the allowlist and signs in again | Retained local tombstone denies automatic re-admission; only an explicit audited admin readmission may clear/rebind it. |
| Foreign session/run/job/source ID | Same 404 as nonexistent. |
| Browser session ID is edited | Backend owner guard rejects; client forgets it. |
| Double create/start | Entitlement/idempotency returns one session/run. |
| Generation fails before promotion | Success remains unconsumed; retry keeps the variant. |
| Normal user calls regenerate directly | 409 variant locked. |
| Promotion crashes mid-finalization | Existing reconciler completes exact receipt; success binding is idempotent. |
| User clears browser data after success | Server entitlement still blocks another portfolio. |
| User signs in with another Google account | Separate subject/account; never merge automatically. |
| Google email changes | Ownership stays on immutable subject; role never changes from profile sync. |
| Last admin self-deletes/demotes | Denied until another active admin exists. |
| Preview URL leaks | Capability remains open to its holder; project deletion revokes pointer. |
| Browser back after sign-out | No private HTML; protected fetch is 401; UI was cleared. |
| Storage/cookies blocked | Recoverable auth error; never pretend signed in. |
| Embedded WebView | Unsupported; use top-level browser for Google OAuth. |
| Provider rate limit | 429/backoff; no provisioning retry storm. |

## Admin controls

- Two distinct Google accounts with Google two-step verification and recovery.
- Target-specific destructive confirmations.
- Local deny before provider/storage cleanup.
- Last-admin protection.
- Admin entitlement is unlimited, but model-provider credit and state/quality
  gates remain authoritative.
- Every mutation writes a safe audit event.
- No bulk wipe or secret-reading interface.

## Provider synchronization position

Do not introduce a provider webhook merely because the rejected Clerk design
had one. First login is synchronous through `/api/v1/me`; admin suspend/delete
is an explicit resumable workflow. If a future Supabase Auth hook/webhook is
required for out-of-band identity deletion, add it only with verified signatures
or database authority, idempotency, ordering tests, and a separate decision.

## Security acceptance

- no-token calls produce 401 on every protected API;
- approved normal token plus foreign IDs produces 404 across every family;
- unapproved identity produces no local or generation state;
- normal users cannot access admin/dev/system operations;
- caller-supplied role/owner/quota/external subject fields are rejected;
- token issuer, audience, signature, algorithm, key, expiry, and subject tests
  cover success and failure;
- logs/responses contain no tokens, keys, cookies, OAuth artifacts, or full
  allowlists;
- CSP supports Supabase/Google while blocking unapproved origins;
- sign-out/back/refresh cannot retrieve private API data;
- suspension denies locally even if provider revocation is delayed;
- deletion fences jobs and revokes preview before data cleanup;
- deleted-user tombstones prevent still-allowlisted automatic re-registration;
  and
- capacity/quota/variant tests pass under concurrency.

## Official references

- [Supabase JWT guidance](https://supabase.com/docs/guides/auth/jwts)
- [Supabase signing keys](https://supabase.com/docs/guides/auth/signing-keys)
- [Supabase Auth security](https://supabase.com/docs/guides/auth/security)
- [Supabase API security](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase product security](https://supabase.com/docs/guides/security/product-security)
