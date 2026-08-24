# Authorization, quota, and data model

Implementation status: Phase 2 ownership is implemented in
`0015_portfolio_ownership`, and Phase 3 entitlement/worker fencing is
implemented in `0016_auth_entitlements_worker_fencing`. Existing rows are
legacy/admin-only; new API-created rows are explicitly owned. Normal users now
have one entitlement row that binds one session, one production generation
run/variant, and one verified success. Administrator audit/lifecycle remains
Phase 4 and is intentionally not present.

## Identity is not authorization

Supabase authentication answers: “Which Supabase subject made this request, and
is the session valid?” OryxenAI authorization answers:

- Is that subject an active local user?
- Is onboarding complete?
- Does the user own this portfolio session/run?
- Is the user an admin?
- May this operation consume or change the one-portfolio entitlement?

Those checks belong in shared FastAPI dependencies/services and PostgreSQL.
They must not be reimplemented inconsistently in each route or delegated to the
browser.

## Proposed tables/columns

The Phase 1 identity tables are applied by `0014_auth_foundation`; the Phase 2
session ownership fields are applied by `0015_portfolio_ownership`. The Phase 3
entitlement table is applied by `0016_auth_entitlements_worker_fencing`; the
audit table remains future Phase 4 design.

### `app_users`

| Column | Purpose |
| --- | --- |
| `id UUID PK` | Stable internal identifier used by OryxenAI foreign keys. |
| `supabase_user_id UUID UNIQUE NOT NULL` | Verified Supabase `sub`; immutable external identity mapping. |
| `primary_email TEXT NOT NULL` | Normalized verified primary email for admin/support display and bootstrap, never resource ownership. |
| `username TEXT UNIQUE NULL` | Normalized app username; null means onboarding required. |
| `display_name TEXT NULL` | Convenience value from Google/Supabase, not unique or authoritative. |
| `avatar_url TEXT NULL` | Optional display value; render with safe URL policy/referrer handling. |
| `role TEXT NOT NULL` | Checked set: `user`, `admin`; default `user`. |
| `status TEXT NOT NULL` | Checked set: `active`, `suspended`, `deletion_pending`, `deleted`. |
| `onboarding_completed_at` | Null until username is claimed. |
| `deleted_at TIMESTAMPTZ NULL` | Marks the retained authorization tombstone after deletion. |
| `last_seen_at`, `created_at`, `updated_at` | Operations/support timestamps. |

Do not store Google/Supabase access tokens. Do not store a password hash. Do
not store role in `user_metadata` or another user-editable JSON blob.

### `app_user_capacity`

Use one singleton row as the transaction lock for normal-user admission:

| Column | Purpose |
| --- | --- |
| `scope TEXT PK` | Stable value such as `normal-users`. |
| `normal_user_limit INTEGER NOT NULL` | Config-consistent limit; 15 for the accepted policy. |
| `revision INTEGER NOT NULL` | Concurrency and audited policy updates. |

On approved first login, lock this row, count non-deleted normal users, and
insert only when below 15. Administrators do not consume the limit. Suspended
normal users retain a slot; a completed audited deletion releases it. The
minimal deleted user tombstone remains excluded from capacity but blocks the
same still-allowlisted email from silently registering again. Do not trust a
frontend count or race two independent `COUNT`/`INSERT` transactions.

### `portfolio_sessions.owner_user_id` (implemented in Phase 2)

Add a foreign key to `app_users.id` plus an owner/created-time index. Add an
explicit legacy-quarantine flag/check so a row is either owned or quarantined.
The accepted migration marks every existing unowned row legacy/admin-only; new
product rows must be owned.

Repository methods should make the policy visible in their names, for example:

- `get_owned_by_id(session_id, owner_user_id)` for normal requests;
- `list_owned_recent(owner_user_id, limit)`;
- explicitly admin-only `get_by_id_for_admin` / `list_recent_for_admin`.

A generic internal lookup remains for trusted service callers; Phase 3 worker
fencing now rechecks the durable owner/actor/session graph before work and
finalization. Product routes use the explicit owned/admin repository methods
through centralized `PortfolioAccess`; they never filter a global query in
Python.

### `portfolio_entitlements`

Use one row per non-admin user, transactionally locked for create/generation
operations:

| Column | Purpose |
| --- | --- |
| `user_id UUID PK/FK` | Exactly one entitlement row per normal user. |
| `portfolio_session_id UUID UNIQUE NULL` | The user's one project slot. |
| `generation_run_id UUID UNIQUE NULL` | The one design variant/run bound on first Code Generator start. |
| `successful_run_id UUID UNIQUE NULL` | Set only after verified stable-preview promotion. |
| `consumed_at TIMESTAMPTZ NULL` | Successful portfolio timestamp. |
| `revision INTEGER` | Optimistic/concurrent admin reset protection. |
| timestamps | Audit/support. |

An admin bypasses the normal quota in service policy and may own many sessions.
Do not represent “unlimited” as an enormous magic counter.

### `admin_audit_events`

Store:

- actor `app_user_id`;
- action (`user.suspend`, `project.delete`, `quota.reset`, and so on);
- target type/id;
- request ID;
- outcome and small safe details;
- creation timestamp.

Do not store raw Supabase/Google objects, tokens, cookies, full intake documents,
or destructive request payloads in the audit row.

Phase 3 also stores local owner/actor/context snapshots on `agent_runs`,
`code_generator_runs`, and `background_jobs`. Portfolio jobs receive the
trusted `model-generation` execution lane; a PostgreSQL partial unique index
permits at most one running credit-consuming job across workers. The
`portfolio_entitlements` row and these snapshots are checked again by the
worker and by preview finalization.

## Role/permission matrix (Phase 2 and Phase 3 current slice)

| Capability | Normal user | Admin |
| --- | --- | --- |
| View/update own app profile | Yes, username only during onboarding | Any user through explicit admin action |
| Create portfolio session | One owned session; repeated/concurrent create returns the same binding | Owned sessions; all bounded |
| List/read sessions | Own non-legacy sessions only | All, bounded, including legacy |
| Run/revise/approve stages | Own non-legacy session, within existing state rules | Any session, including legacy, within existing state rules |
| Retry a failed Code Generator stage | Same run/variant only | Any retry allowed by workflow |
| Explicit Code Generator regeneration | No | Yes |
| View stable preview URL | Own project | Any project |
| Delete own project/account | Not in minimum v1 | Any target through admin API |
| Suspend/restore/delete users | No | Yes |
| Reset quota | No | Yes |
| View diagnostics/development tools | No | Yes in dev; development endpoints absent in prod |

“Admin can do anything” means admin authorization can operate on every business
resource. It does not mean bypassing model/state safety gates, forging provider
results, reading secrets, or turning on disabled development routes in
production. Administrator lifecycle/audit authority is explicitly Phase 4.
Entitlement and worker-fencing authority are Phase 3 server/database behavior.

## Exact one-portfolio semantics

The user requirement combines “one successful portfolio,” “one iteration,” and
“only one portfolio accessible.” Implement it as these separate invariants:

### One project slot

A normal user has one `portfolio_session_id`. A repeated create request returns
or resumes that same session. A second distinct session is rejected. Deleting
the underlying session does not automatically grant a new slot; only an admin
quota reset does.

### One design variant

On the first eligible Code Generator `/start`, atomically bind
`generation_run_id` to the run/variant. Later `/retry` requests may resume that
same run and its stable design variant. `/regenerate`, which deliberately
creates a new variant in the current code, returns
`409 GENERATION_VARIANT_LOCKED` for a normal user.

This distinction is important:

```text
automatic/manual recovery -> same run + same variant -> allowed before success
explicit regeneration     -> new run/new variant      -> normal user denied
```

### One success

Set `successful_run_id` only when all of these are true:

- the Code Generator run belongs to the entitled session/user;
- required source/build/DOM/runtime and quality gates passed;
- immutable preview objects and receipt were read back and verified;
- the active pointer was conditionally promoted;
- the run/session was finalized with a nonempty `active_preview` matching that
  receipt.

Do not consume success at Discovery approval, Build Preparation readiness,
Code Generator start, source completion, build success alone, or
`pending_promotion`.

The success update must participate in the existing crash-safe promotion
finalization/reconciliation path. It is idempotent for the same successful run
and rejects a different run for a normal user.

### After success

For a normal user:

- project and stable preview remain readable;
- new stage revisions, new generation, and regeneration are disabled;
- retry is unnecessary because the run is ready;
- admin may delete or reset deliberately.

If product policy later wants pre-generation revisions after success, that is a
new decision because it can imply another generation.

## Transaction/concurrency rules

Even with 15 users, double-clicks, retries, and multiple tabs can race.

### Session creation

1. Begin transaction.
2. Lock the normal user's entitlement row (`SELECT ... FOR UPDATE`).
3. If a session is already bound, return it.
4. Otherwise create an owned session and bind it.
5. Commit.

An `Idempotency-Key` remains useful but is not the only concurrency control.

### Code Generator start

1. Authorize owner/admin and current state.
2. Lock entitlement for a normal user.
3. If `successful_run_id` exists, reject as completed.
4. If `generation_run_id` exists, return/resume that run or direct the caller to
   retry; do not create a variant.
5. Otherwise create the normal start and bind its run/variant in the same
   transaction as enqueue state.

### Promotion success

1. Revalidate run/session/owner and pending promotion token.
2. Complete the existing conditional pointer/read-back protocol.
3. Lock entitlement and bind the matching `successful_run_id` idempotently.
4. Finalize active preview/session state.

Reconciliation after a crash must be able to finish steps 3-4 without creating
another success or variant.

### Admin quota reset

Require explicit project handling:

- normally delete/archive the current project and revoke its active preview;
- clear generation/success binding with a revision check;
- write an audit event;
- allow the next user create/start to claim a new slot/variant.

Do not offer an implicit reset merely because the user deleted browser storage
or lost a session link.

## Owner guard behavior

A shared dependency/service should accept `CurrentUser` plus `session_id` and:

- validate UUID shape;
- load the session with an owner predicate for normal users;
- load any session only after a server-side admin role check;
- return 404 for both nonexistent and foreign sessions;
- reject suspended/deleting users before touching business state;
- reject onboarding-incomplete users except on `/me` and username routes.

The same rule applies transitively to run IDs and job IDs. A run lookup must
join or otherwise prove its portfolio session owner. A guessed run/job ID must
not expose events, plan, source, errors, or preview metadata.

## Durable jobs

At enqueue time record or bind:

- `portfolio_session_id`;
- `owner_user_id` snapshot;
- initiating `actor_user_id` (an admin can act on another owner's project);
- run/attempt/idempotency identifiers already required by the workflow.

At execution/finalization, the worker loads current database ownership and
checks it against the bound owner. If the session/user is suspended,
deletion-pending, missing, or reassigned unexpectedly, fail closed and do not
publish output. Workers never call Supabase to authorize a historic browser
request.

## Admin deletion semantics

### Suspend user

1. Set local status to suspended so OryxenAI denies immediately.
2. Use the current Supabase Admin API to ban/revoke provider access.
3. Record outcome. If the provider call fails, keep a retryable safe state;
   local authorization remains denied.

### Delete project

1. Mark project deletion-pending so new writes stop.
2. Cancel/neutralize queued work; running handlers must fail finalization after
   seeing the marker.
3. Remove the stable preview pointer first so the capability URL stops serving.
4. Delete retained preview/build objects according to object-store semantics.
5. Delete the session aggregate and cascading database rows.
6. Keep or reset the owner's quota only according to the explicit admin action.
7. Audit the operation.

### Delete user

1. Deny locally and revoke/ban the Supabase identity using the current Admin API.
2. Mark `deletion_pending`.
3. Delete/clean owned projects as above.
4. Delete the Supabase Auth identity with the server-only secret key.
5. Convert the local row to a minimal `deleted` authorization tombstone. Retain
   only the subject/email binding and audit-safe fields needed to prevent a new
   Supabase UUID for the same still-allowlisted Google email from being admitted
   automatically; remove presentation/profile data under the retention policy.
6. Finalize the audit event.

Make the workflow resumable. If storage cleanup fails, keep a banned,
deletion-pending record instead of re-enabling a partially deleted user.
Readmission of a deleted email requires a separate explicit, audited admin
action that resolves the old tombstone before a new provider identity can be
bound. Merely remaining in `ORYXENAI_ALLOWED_USER_EMAILS` is insufficient.

Prevent accidental total lockout: deleting/demoting an admin should require a
second active admin or a documented break-glass bootstrap path.
