# OryxenAI Authentication & Authorization

Status: **Phases 1, 2, 3, and 4 are fully implemented** in the codebase and verified locally.
Phase 1 delivers the Supabase Google-only identity boundary, JWT/JWKS verifier, capacity gate, and username onboarding.
Phase 2 delivers portfolio session ownership, legacy session quarantine, and owner/admin route dependencies.
Phase 3 delivers single-portfolio/variant/success entitlements, durable worker fencing, and the global execution lane.
Phase 4 delivers the audited administrator lifecycle, resumable deletion, entitlement reset, and the local `/admin` console.

Owner-completed multi-account browser acceptance on Google OAuth and production cloud deployment remain separate gates. No production cloud resources have been created.

Last verified: 2026-09-02.

---

## Core Architecture & Provider Topology

OryxenAI uses **Supabase Auth** exclusively for **Google OAuth 2.0 / OpenID Connect identity proof**, while keeping **all application authorization, entitlements, quotas, and lifecycle state inside OryxenAI and PostgreSQL**:

```text
[ Browser / Client ]
        |
        | 1. Full-page redirect -> Google OAuth -> /auth/callback
        v
[ Supabase Auth ] ---- (issues asymmetric JWT session token) ----> [ Browser ]
                                                                       |
        +--------------------------------------------------------------+
        | 2. Authenticated Bearer fetch
        v
[ FastAPI API ]
   ├── SupabaseJwtVerifier (asymmetric RS256/ES256/PS256 against project JWKS)
   ├── AuthService (JIT provisioning, admission checks, 15-user capacity gate)
   └── PortfolioAccess (SQL owner predicates; admin bypass; legacy quarantine)
        |
        v
[ PostgreSQL ] (app_users, app_user_capacity, portfolio_entitlements, admin_audit_events)
        |
        v
[ Durable Background Jobs ]
   └── WorkerAuthorizationFence (rechecks owner/actor snapshot before execution/finalization)
```

### Key Principles

1. **No Application-Managed Passwords**: Google owns the credential screen. OryxenAI never receives, stores, or handles Google passwords or provider access/refresh tokens.
2. **PostgreSQL is Database-Authoritative**: Roles (`user`, `admin`), account status (`active`, `suspended`, `deletion_pending`, `deleted`), username, capacity, entitlements, and ownership are stored in PostgreSQL. Client `user_metadata` or query parameters are never trusted for authorization.
3. **Dual Admission Modes**:
   - `auth.admission_mode = "open"` (default): Any verified Google account can sign up until the database capacity limit of 15 normal users is reached.
   - `auth.admission_mode = "allowlist"`: Only verified Google emails in `ORYXENAI_ALLOWED_USER_EMAILS` are admitted.
4. **Bootstrap Administrators**: Two administrator emails (`ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`) are assigned `role=admin` on first login and are excluded from the 15 normal-user limit.
5. **Exact One-Portfolio Policy**: Normal users receive 1 portfolio session, 1 Code Generator design variant, same-variant retry on failure, exactly 1 verified promoted success, and server-enforced read-only state after success.
6. **Worker Reauthorization Fencing**: Durable jobs record owner and actor snapshots; `WorkerAuthorizationFence` ensures jobs abort if a user or session has been deleted, suspended, or quarantined before output is finalized.
7. **Attached vs. Detached Pipeline Mode**:
   - `attached` (production/Docker): Enforces full bearer token authentication across all routes.
   - `detached` (local agent development): Bypasses login for Discovery through Build Preparation, providing a `Restart Pipeline` control while keeping admin and Code Generator routes protected.

---

## Confirmed Development Coordinates

- **Supabase Project Reference**: `diiestlnmpaarhhexwhi` (`oxygen-ai-development`, Mumbai, `ap-south-1`).
- **Google Auth Platform**: `Oxygen.ai` external web application client.
- **Scopes**: `openid`, `userinfo.email`, `userinfo.profile`.
- **Local Allowed Origins**: `http://localhost:8000`, `http://127.0.0.1:8000`.
- **Supabase Provider Redirect**: `https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback`.
- **App Callback Path**: `/auth/callback`.

Verification checker command:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online -RequireNormalUser
```

---

## Documentation Index

This directory provides comprehensive, non-redundant documentation of the implemented authentication and authorization architecture:

1. [**01-user-flows-and-route-contract.md**](01-user-flows-and-route-contract.md)
   - User flows, web shells (`/sign-in`, `/auth/callback`, `/onboarding`, `/app`, `/admin`).
   - Browser controller state machine and self-hosted pinned client (`auth-client.js`).
   - Attached vs. detached development pipeline modes (`Restart Pipeline`).
   - Full API route catalog (Current User, Sessions, Admin Console) and error contract.

2. [**02-data-model-and-lifecycle.md**](02-data-model-and-lifecycle.md)
   - Database migrations (`0014_auth_foundation` through `0017_auth_admin_lifecycle`).
   - PostgreSQL models: `app_users`, `app_user_capacity`, `portfolio_sessions`, `portfolio_entitlements`, `deleted_app_users`, `admin_audit_events`, `admin_operations`, `deleted_portfolio_projects`.
   - Role/permission matrix and exact one-portfolio entitlement state machine.
   - Administrative lifecycle operations: suspend, restore, delete user, delete project, entitlement reset, promote/demote, readmit, and resume operation.

3. [**03-security-and-worker-fencing.md**](03-security-and-worker-fencing.md)
   - Cryptographic JWT/JWKS verification and provider secret header handling (`apikey: sb_secret_...`).
   - Object-level authorization and IDOR prevention (`PortfolioAccess`).
   - Durable worker fencing (`WorkerAuthorizationFence`) and global `model-generation` lane locking.
   - Separate preview origin isolation and Content Security Policy (CSP).
   - Comprehensive edge-case handling matrix.

4. [**04-deployment-and-operations.md**](04-deployment-and-operations.md)
   - Environment variables contract and non-secret application settings (`[auth]`).
   - Verified development evidence and automated diagnostic scripts.
   - Production hosting architecture (Render + Cloudflare R2 + Supabase).
   - Owner acceptance checklist for live Google OAuth browser testing.
