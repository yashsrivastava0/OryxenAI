# Authorization, Data Model & Administrator Lifecycle

Status: **Implemented**. This document details the PostgreSQL schema, Alembic migrations, one-portfolio entitlement state machine, and administrative lifecycle operations.

---

## Database Migrations

Authentication and authorization are deployed across four linear Alembic migrations:

1. **`0014_auth_foundation`**:
   - Creates `app_users` table for internal identity and role mapping.
   - Creates `app_user_capacity` singleton table to serialize normal-user registration.
2. **`0015_portfolio_ownership`**:
   - Adds `owner_user_id` foreign key and `legacy_quarantined` flag to `portfolio_sessions`.
   - Adds `session_mode` (`product`, `detached`, `legacy`).
   - Quarantines all pre-existing unowned sessions as legacy/admin-only data.
3. **`0016_auth_entitlements_worker_fencing`**:
   - Creates `portfolio_entitlements` table for one-portfolio/variant/success tracking.
   - Adds owner and actor snapshot columns to `agent_runs`, `code_generator_runs`, and `background_jobs`.
   - Adds `execution_lane` column to `background_jobs` with a partial unique index for the singleton `model-generation` lane.
4. **`0017_auth_admin_lifecycle`**:
   - Creates `admin_audit_events` table for immutable operational audit logging.
   - Creates `admin_operations` table for tracking multi-step resumable administrative workflows.
   - Creates `deleted_app_users` and `deleted_portfolio_projects` tombstone tables.
   - Applies Row-Level Security (RLS) policies as defense in depth.

---

## Implemented Data Models (`src/oryxenai/auth/models.py`)

### 1. `app_users`

Maps immutable Supabase authentication UUIDs to OryxenAI users:

```sql
CREATE TABLE app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL,
    primary_email TEXT NOT NULL,
    username TEXT UNIQUE NULL,
    display_name TEXT NULL,
    avatar_url TEXT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deletion_pending', 'deleted')),
    onboarding_completed_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_app_users_primary_email ON app_users(primary_email);
```

### 2. `app_user_capacity`

Singleton row that acts as a pessimistic concurrency lock for normal-user admission:

```sql
CREATE TABLE app_user_capacity (
    scope TEXT PRIMARY KEY,
    normal_user_limit INTEGER NOT NULL DEFAULT 15,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3. `portfolio_sessions` Ownership Columns

Applied by migration `0015`:

```sql
ALTER TABLE portfolio_sessions
    ADD COLUMN owner_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    ADD COLUMN legacy_quarantined BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN session_mode TEXT NOT NULL DEFAULT 'product' CHECK (session_mode IN ('product', 'detached', 'legacy'));

CREATE INDEX ix_portfolio_sessions_owner ON portfolio_sessions(owner_user_id, created_at DESC);
```

### 4. `portfolio_entitlements`

Tracks the strict one-portfolio, one-variant, and one-success entitlement for normal users:

```sql
CREATE TABLE portfolio_entitlements (
    user_id UUID PRIMARY KEY REFERENCES app_users(id) ON DELETE CASCADE,
    portfolio_session_id UUID UNIQUE REFERENCES portfolio_sessions(id) ON DELETE SET NULL,
    generation_run_id UUID UNIQUE NULL,
    successful_run_id UUID UNIQUE NULL,
    consumed_at TIMESTAMPTZ NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5. `admin_audit_events`

Append-only record of all administrative actions:

```sql
CREATE TABLE admin_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID NOT NULL REFERENCES app_users(id),
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    request_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'resumed')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_admin_audit_events_actor ON admin_audit_events(actor_user_id, created_at DESC);
CREATE INDEX ix_admin_audit_events_target ON admin_audit_events(target_type, target_id);
```

### 6. `admin_operations`

Tracks asynchronous or multi-step administrative operations for safe resumption:

```sql
CREATE TABLE admin_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'succeeded', 'failed', 'cancelled')),
    step TEXT NOT NULL DEFAULT 'initialized',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error_code TEXT NULL,
    last_error_message TEXT NULL,
    actor_user_id UUID NOT NULL REFERENCES app_users(id),
    idempotency_key TEXT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    safe_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_admin_operations_status ON admin_operations(status, created_at DESC);
CREATE INDEX ix_admin_operations_target ON admin_operations(target_type, target_id);
```

### 7. Tombstone Tables

- **`deleted_app_users`**: Retains minimal identity hashes (`supabase_user_id`, `normalized_email`, `role_at_deletion`, `reason`, `tombstone_recorded_at`) so that a deleted user cannot re-register automatically without explicit administrative readmission.
- **`deleted_portfolio_projects`**: Records historical project metrics and timestamps after project deletion.

---

## Role & Permission Matrix

| Operation / Capability | Normal User (`role=user`) | Administrator (`role=admin`) |
| --- | --- | --- |
| Sign in / authenticate via Google | Permitted | Permitted |
| Claim username on onboarding | Permitted once (cannot rename) | Permitted |
| Create portfolio session | Permitted: exactly 1 owned session | Permitted: multiple owned sessions |
| List recent sessions | Own non-quarantined sessions only | All sessions, including quarantined legacy |
| Run Discovery / CA / VDD stages | Own sessions only | Any session |
| Run Code Generator (`/start`) | First run binds `generation_run_id` | Any session, binds run |
| Retry failed generation (`/retry`) | Permitted: same run and variant | Permitted |
| Regenerate variant (`/regenerate`) | **Forbidden**: returns 409 locked | Permitted |
| View active preview URL | Own project preview | Any project preview |
| Mutate session after success | **Forbidden**: returns 409 read-only | Permitted |
| Access Admin Console (`/admin`) | **Forbidden**: returns 403 / redirects to `/app` | Permitted |
| Suspend / Restore users | No access | Permitted (except last active admin) |
| Delete user / Reset entitlement | No access | Permitted (audited, multi-step) |
| Readmit deleted identity | No access | Permitted |
| Promote user to admin | No access | Permitted |
| Demote admin to user | No access | Permitted (validates normal user limits) |

---

## Exact One-Portfolio Entitlement Invariants

The platform enforces four explicit invariants for every normal user:

```text
[ New User ] -> Claim 1 Session Slot (portfolio_session_id)
                     |
                     v
[ Stage Pipeline ] -> Code Generator /start -> Atomically binds generation_run_id
                     |
         +-----------+-----------+
         |                       |
     [Failure]               [Success]
         |                       |
    /retry allowed           Promote to active_preview
  (keeps same variant)           |
  /regenerate denied             v
                         Atomically binds successful_run_id + consumed_at
                                 |
                                 v
                         [PORTFOLIO_READ_ONLY]
                         - GET / preview remain open
                         - Stage revisions frozen
                         - New sessions denied
```

1. **One Session Slot**: On `POST /api/v1/sessions`, the user's `portfolio_entitlements` row is locked (`SELECT ... FOR UPDATE`). If `portfolio_session_id` is set, that existing session is returned. Attempting to create an independent second session is rejected.
2. **One Design Variant**: On first Code Generator start, the run UUID is bound to `generation_run_id`. Later `/retry` requests re-run the same design variant. Any attempt to call `/regenerate` returns `409 GENERATION_VARIANT_LOCKED`.
3. **Exactly-Once Success Consumption**: `successful_run_id` and `consumed_at` are stamped only after source, build, DOM runtime, and visual quality gates pass, preview files are written to S3/R2 storage, and the preview capability pointer is promoted. Failure during generation never consumes the success slot.
4. **Post-Success Mutation Freeze**: Once `successful_run_id` is populated, the project aggregate transitions to read-only. All subsequent mutation requests return `409 PORTFOLIO_READ_ONLY`. Reads and preview serving remain active.

---

## Administrative Lifecycle Workflows (`AdminService`)

All administrative mutations are executed via `src/oryxenai/auth/admin/service.py` with mandatory confirmation tokens, target usernames, and idempotency keys:

### 1. User Suspension & Restoration
- **Suspend**: Updates local `app_users.status` to `suspended` and immediately calls Supabase Admin API (`POST /auth/v1/admin/users/{id}/ban`) to revoke provider access. Worker jobs and API requests reject suspended users.
- **Restore**: Sets local status back to `active` and unbans the user via the Supabase Admin API.

### 2. Multi-Step Resumable User Deletion
User deletion is orchestrated through `admin_operations` to ensure safety across database and external storage boundaries:
1. **Local Fence**: Mark `app_users.status = 'deletion_pending'`.
2. **Fence Projects**: Cancel all queued background jobs for owned sessions.
3. **Storage Cleanup**: Revoke preview capability pointers and clean up temporary Build Preparation packs and preview files in S3/R2.
4. **Database Cleanup**: Cascade-delete owned sessions and entitlement records.
5. **Provider Deletion**: Delete the identity in Supabase Auth via the service-role key.
6. **Tombstone Recording**: Insert a `deleted_app_users` row and mark the operation succeeded.

If an external network error occurs during storage or Supabase deletion, the operation records `failed`, the account remains fenced, and an administrator can safely resume it via `POST /api/v1/admin/operations/{id}/resume`.

### 3. Entitlement Reset
Allows an administrator to grant a normal user a new portfolio:
- Deletes or archives the user's current project.
- Revokes active preview pointers.
- Clears `portfolio_session_id`, `generation_run_id`, `successful_run_id`, and `consumed_at` on `portfolio_entitlements`.
- Records an audited event in `admin_audit_events`.

### 4. Last-Admin Safety
An administrator cannot suspend, delete, or demote their own account if they are the sole remaining active administrator in the database.
