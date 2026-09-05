# Deployment, Configuration & Operations

Status: **Implemented locally; owner acceptance and production cloud deployment pending**. This document details environment configuration, settings schemas, diagnostic commands, hosting targets, and the owner acceptance checklist.

> **Current deployment target:** the first working demo deployment is now
> documented in [`docs/deployment/`](../deployment/README.md). It uses one
> Azure VM with the existing Docker Compose topology, Supabase Auth, and
> Cloudflare R2. The Render diagram below is retained as historical provider
> research and is not the runbook to follow.

---

## Environment Variables Contract

All secret credentials live exclusively in `.env` (which is git-ignored). `.env.example` documents variable names with placeholder values:

| Variable Name | Exposure | Required In | Purpose |
| --- | --- | --- | --- |
| `SUPABASE_URL` | Public / Browser-safe | Required | Canonical HTTPS URL of the Supabase project (e.g., `https://diiestlnmpaarhhexwhi.supabase.co`). |
| `SUPABASE_PUBLISHABLE_KEY` | Public / Browser-safe | Required | Modern `sb_publishable_...` or legacy `anon` public key sent to client browser. |
| `SUPABASE_SECRET_KEY` | **Strictly Server-Only** | Required | Modern `sb_secret_...` or legacy `service_role` secret key for backend Supabase Admin API calls. |
| `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` | **Server-Only** | Required | Comma-separated list of exact email addresses granted `role=admin` on first login (minimum 2 distinct emails). |
| `ORYXENAI_ALLOWED_USER_EMAILS` | **Server-Only** | Conditional | Comma-separated allowlist of permitted emails when `auth.admission_mode = "allowlist"`. Optional in `open` mode. |

Secrets must never appear in repository code, commits, logs, diagnostics, or frontend payloads.

---

## Non-Secret Application Configuration (`config/app.toml`)

Application policies are configured in committed TOML files (`config/app.toml`, overlaid by `config/app.docker.toml` or `config/app.test.toml`):

```toml
[auth]
provider = "supabase"
required = true
admission_mode = "open"          # "open" (capacity-gated) or "allowlist"
pipeline_mode = "attached"       # "attached" (normal auth) or "detached" (dev pipeline)
sign_in_path = "/sign-in"
callback_path = "/auth/callback"
after_sign_in_path = "/app"
normal_user_limit = 15
normal_user_portfolio_limit = 1
normal_user_variant_limit = 1
jwks_cache_ttl_seconds = 3600
token_clock_skew_seconds = 60
```

Production environments fail readiness if:
- `auth.required = true` but provider URL, keys, or bootstrap emails are missing.
- Allowed origins include `localhost`, HTTP schemes, or wildcards.
- Test authentication overrides are active.

---

## Prerequisite Verification Tooling

OryxenAI includes a dedicated, redaction-safe diagnostic script (`scripts/verify-auth-prerequisites.ps1`):

```powershell
# Basic offline check of environment variable shapes
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1

# Full online check (verifies Supabase endpoint, JWKS retrieval, and OAuth initiation)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online -RequireNormalUser
```

The online check validates network reachability and provider configuration without performing an interactive login or handling passwords.

---

## Historical Render Hosting Architecture

> [!IMPORTANT]
> The early exploratory AWS hosting scenario and this Render topology are
> historical provider research. The current first-deployment target is the
> single-Azure-VM topology in [`docs/deployment/`](../deployment/README.md).
> Keep the auth and configuration details in this document, but follow the
> Azure runbook for hosting.

```text
                                 [ Cloudflare DNS ]
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
         [ Render Web Service ]                  [ Render Web Service ]
           OryxenAI FastAPI API                   OryxenAI Preview Gateway
          (API + Web UI Shells)                  (Opaque Sandboxed Origin)
                     |                                       |
          +----------+----------+                            |
          |                     |                            |
          v                     v                            v
   [ Supabase Auth ]   [ Managed PostgreSQL ]     [ Cloudflare R2 Bucket ]
   (Google OAuth IDP)  (State, Quotas, Queue)    (Build Packs & Generated Sites)
                                |
                                v
                     [ Render Background Worker ]
                       Durable Background Jobs
```

- **API & Background Worker**: Deployed as containerized services on Render (separate processes sharing the same codebase).
- **Database & Identity**: Supabase Free/Pro tier provides managed PostgreSQL (Alembic-managed schema) and Google OAuth provider.
- **Storage**: Cloudflare R2 provides S3-compatible, zero-egress storage for Build Preparation pack ZIPs and preview sites.
- **Preview Gateway**: Independent service on a separate domain serving generated portfolios without user credentials or cookies.

---

## Owner Acceptance Checklist

Before production release, the repository owner must perform the live Google OAuth browser acceptance ceremony across the three configured identities:

### Phase A: Bootstrap Administrator 1
- [ ] Launch application locally with `./scripts/run-api.ps1` and `./scripts/run-worker.ps1`.
- [ ] Open a clean browser window to `http://localhost:8000/`.
- [ ] Click **Continue with Google** and authenticate with the first bootstrap admin Google account.
- [ ] Verify immediate promotion to `role=admin` without consuming a normal-user capacity slot.
- [ ] Navigate to `/admin` and confirm visibility of system metrics and user lists.

### Phase B: Bootstrap Administrator 2
- [ ] Open a separate private browsing session.
- [ ] Authenticate with the second bootstrap admin Google account.
- [ ] Verify `role=admin` access.
- [ ] Verify that neither admin can delete or demote their own account while fewer than two admins exist.

### Phase C: Normal Test User
- [ ] Authenticate with the separate configured normal Google test account.
- [ ] Verify redirect to `/onboarding` upon first login.
- [ ] Enter a valid username (e.g. `testuser`) and submit.
- [ ] Verify automatic redirect to `/app`.
- [ ] Create a portfolio and proceed through stages to Code Generator.
- [ ] Verify that attempting to call `/regenerate` returns `409 GENERATION_VARIANT_LOCKED`.
- [ ] Promote portfolio preview to active state.
- [ ] Verify that the project transitions to read-only (`409 PORTFOLIO_READ_ONLY` on modifications) while preview viewing remains active.

### Phase D: Unadmitted Account (Capacity & Allowlist Test)
- [ ] Attempt sign-in with an unauthorized Google account.
- [ ] In `allowlist` mode: verify immediate redirect to `/access-not-approved`.
- [ ] Verify no `app_users` or session records are created in PostgreSQL.
