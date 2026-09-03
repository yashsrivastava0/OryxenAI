# Security Architecture, Worker Fencing & Edge Cases

Status: **Implemented**. This document details the cryptographic verification boundaries, provider secret handling, durable worker fencing, preview origin isolation, Content Security Policy, and the system edge-case matrix.

---

## Cryptographic Token Verification

All protected API endpoints require an `Authorization: Bearer <Supabase access token>` header. Token verification is performed locally by `SupabaseJwtVerifier` (`src/oryxenai/auth/jwt.py`) using cryptographic public keys obtained from the Supabase project JWKS endpoint:

```text
[ Incoming Request ]
        |
        v
Extract Bearer Token
        |
        +---> 1. Parse JWT Header -> extract "kid" and "alg"
        +---> 2. Validate "alg" in (RS256, ES256, PS256)
        +---> 3. Fetch public key from bounded JWKS cache
        |        (If "kid" unknown, refresh cache once from https://<ref>.supabase.co/auth/v1/.well-known/jwks.json)
        +---> 4. Cryptographically verify signature using public key
        +---> 5. Validate standard claims:
        |        - iss == "https://<ref>.supabase.co/auth/v1"
        |        - aud == "authenticated"
        |        - exp > now() (with configured clock skew)
        |        - nbf <= now()
        |        - sub is a valid UUID
        v
[ Cryptographically Verified Supabase Subject UUID ]
        |
        v
Load local active user from app_users WHERE supabase_user_id = sub
```

### Key Security Controls
1. **Asymmetric Key Authority**: The project uses an asymmetric signing key. Decoded-but-unverified tokens and algorithm confusion attacks (e.g. `none` or HMAC with a public key) are rejected.
2. **Bounded JWKS Caching**: Public keys are cached with a configurable TTL (default 1 hour). If a token presents an unknown `kid`, the verifier refreshes the JWKS endpoint exactly once before failing closed.
3. **No Provider Secrets in Browser**: Only the Supabase project URL and publishable key are delivered to the client. The service-role secret key (`SUPABASE_SECRET_KEY`) is strictly server-only.
4. **Modern Admin Secret Headers**: Modern Supabase `sb_secret_...` keys are transmitted as HTTP headers (`apikey: <secret>`) to the Supabase Admin API, never misrepresented as Bearer JWTs.

---

## Object-Level Authorization & IDOR Prevention

Authentication proves identity; authorization determines access. Every session, stage, and run endpoint enforces object-level authorization via `PortfolioAccess` (`src/oryxenai/auth/authorization.py`):

1. **Owner Predicates**: Normal user requests execute with explicit SQL filters (`owner_user_id = current_user.id` and `legacy_quarantined = false`).
2. **Admin Authority**: Users with `role=admin` can access any session, including legacy-quarantined rows.
3. **Indistinguishable 404s**: Requesting a session or child resource owned by another user returns an identical `404 Not Found` to prevent account enumeration.
4. **Transitive Authorization**: Stage states, agent runs, job logs, and preview metadata do not have separate public lookups; they join back to the protected parent session aggregate.

---

## Durable Worker Authorization Fence (`WorkerAuthorizationFence`)

Because durable jobs execute asynchronously in background worker processes after an API request completes, browser tokens cannot authorize background work. Authorization must be bound to durable persistence:

```text
[ API Request ]
   ├── Verifies User JWT & checks local role
   ├── Snapshots owner_user_id & actor_user_id onto durable job/run row
   └── Enqueues job in background_jobs
            |
            v
[ PostgreSQL Job Queue ]
            |
            v
[ Background Worker Process ]
   └── WorkerAuthorizationFence.recheck()
        ├── 1. Reloads current app_users row for snapshot owner
        ├── 2. Reloads current portfolio_sessions row
        ├── 3. Verifies owner_user_id matches session owner
        ├── 4. Checks that user status == 'active'
        ├── 5. Checks that session is not deleted or quarantined
        └── If check fails:
             -> Fail closed with AUTHORIZATION_FENCE_REJECTED
             -> Suppress stage completion & preview promotion
             -> Abort successor job enqueueing
```

The worker never relies on client metadata or calls Supabase to recreate a past browser session. Database relationships remain authoritative.

---

## Global Execution Lane Concurrency

To prevent multiple credit-consuming model runs from exhausting API budgets concurrently, jobs entering planning or source generation declare `execution_lane = 'model-generation'`.

This concurrency limit is enforced at the database level:
```sql
CREATE UNIQUE INDEX uq_background_jobs_model_generation_active
    ON background_jobs (execution_lane)
    WHERE execution_lane = 'model-generation' AND status IN ('queued', 'running');
```
If a credit-consuming job is already executing, any newly enqueued portfolio generation waits cleanly in the queue without duplicate billing or racing workers.

---

## Generated Preview Trust Boundary

Preview sites generated by Code Generator execute in browser sandboxes on a **separate origin**:

1. **Opaque Capability URLs**: Previews are served through the preview gateway (`/preview/{host}/{path}`) from private object storage (S3/R2).
2. **Credential Isolation**: The preview host never receives Supabase authentication tokens, session cookies, or access to the OryxenAI API origin.
3. **Restricted Headers**: Previews are served with `X-Frame-Options: SAMEORIGIN` (scoped to preview host), `X-Content-Type-Options: nosniff`, and `noindex, nofollow` to prevent search engine indexing.
4. **Immediate Revocation**: Deleting a project removes the active preview pointer first, immediately terminating the preview capability.

---

## Content Security Policy (CSP) & Security Headers

OryxenAI enforces defense-in-depth headers across all HTML shells:

```text
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'unsafe-inline' https://apis.google.com;
    connect-src 'self' https://*.supabase.co wss://*.supabase.co https://accounts.google.com;
    img-src 'self' data: https:;
    style-src 'self' 'unsafe-inline';
    frame-src 'self' https://accounts.google.com;
    object-src 'none';
    base-uri 'self';
    frame-ancestors 'none';

X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store, no-cache, must-revalidate
```

---

## System Edge-Case Matrix

| Scenario | System Defense & Observed Behavior |
| --- | --- |
| **User cancels Google OAuth** | Supabase redirects back with error parameters; `auth-controller.mjs` returns cleanly to `/sign-in` without creating database records. |
| **Duplicate / refreshed callback tab** | OAuth exchange is idempotent; subsequent `/api/v1/me` lookup resolves the existing `app_users` row without duplicating capacity. |
| **16th user races registration** | `app_user_capacity` row is locked (`SELECT ... FOR UPDATE`); the 16th transaction detects capacity full and returns `409 USER_CAPACITY_REACHED`. |
| **Username collision race** | Database `UNIQUE` constraint on `app_users.username` resolves race; losing caller receives `409 USERNAME_TAKEN`. |
| **Expired / revoked access token** | API returns `401 AUTH_INVALID`; client attempts one token refresh via Supabase client; if refresh fails, user is directed to `/sign-in`. |
| **JWKS signing key rotated** | Verifier encounters unknown `kid`, refreshes JWKS cache once, and succeeds if key was rotated by provider. |
| **Admin deletes user while job runs** | `WorkerAuthorizationFence` detects user `deletion_pending` or `deleted` and rejects finalization with `AUTHORIZATION_FENCE_REJECTED`. |
| **Deleted user signs in again** | JIT provisioning checks `deleted_app_users` tombstone table; automatic registration is denied until an admin approves readmission. |
| **IDOR / Tampered Session ID** | SQL queries enforce `owner_user_id = current_user.id`; foreign or manipulated UUIDs return standard `404 Not Found`. |
| **Double Code Generator start** | Entitlement locks row; second start returns existing `generation_run_id` without creating duplicate variant runs. |
| **Normal user calls `/regenerate`** | Service rejects request with `409 GENERATION_VARIANT_LOCKED`; only `/retry` of the existing variant is permitted. |
| **Model provider credit exhausted** | Worker logs redacted credit exhaustion diagnostic and transitions run to `needs_attention`; success slot is unconsumed. |
| **Crash during preview promotion** | Reconciler checks promotion receipt and finishes atomically; `successful_run_id` stamped idempotently. |
| **Last admin self-deletion** | `AdminService` counts active admins; rejects deletion/demotion with `LAST_ADMIN_PROTECTED`. |
