# Runtime state and API contract

This document describes the minimum backend/frontend coordination required to make the UI truthful. The existing server-authoritative model remains intact.

## Existing identity distinction

Code Generator exposes at least two different identities:

- `current_run_id`: the durable development/session run identity;
- `jobs[].id`: the durable background job identity.

They must never be compared as if they were the same value. The current frontend adapter passes `current_run_id` into job selection, so it often receives no job even when a job exists.

## Required Code Generator projection

The session response keeps its existing shape and adds these response-level fields under `code_generator`:

```json
{
  "active_job_id": "uuid-or-null",
  "active_job_kind": "code_generator.v5.plan-or-null",
  "retry_available": true
}
```

`active_job_id` is selected server-side from `coordinator_stage`:

| `coordinator_stage` | Run field |
|---|---|
| `plan` | `background_job_id` |
| `acquire` | `acquire_job_id` |
| `generate` | `generation_job_id` |
| `verify` | `verification_job_id` |

`active_job_kind` is copied from the selected job. If the stage has no job, both active fields are `null`.

`retry_available` is computed from the server's current run state, entitlement/read-only policy, source freshness, and retry route eligibility. The UI must not infer retry eligibility from a generic error string.

The existing `jobs` array remains a safe summary only: ID, kind, status, attempt, execution lane, and safe error. Do not expose payloads, worker leases, prompts, provider response bodies, credentials, or internal reasoning.

## Terminal failure behavior

The UI must converge to `attention` for all terminal failure paths:

1. Agent code catches a known/provider/model/validation failure and persists `needs_attention`.
2. Worker timeout exhausts retries.
3. Worker receives a terminal handler exception or a failed result.
4. A selected active job is already `failed` or `cancelled` while the run projection is stale.

For Code Generator jobs, terminal timeout/handler failure reconciliation must persist a safe run-level failure projection when no retry remains. This may use the existing `terminal_failure` and `issues` fields; it does not require a database migration. The safe projection must include a user summary, stable error code, retryability, and support/reference data only when already approved for client exposure.

Authorization-fence failures remain security failures. They must not be converted into a blind retry loop. The UI should show that the session needs refreshing or support intervention when no server-authorized retry exists.

## Frontend adapter rules

The Code Generator adapter must:

- select the job by `active_job_id`;
- use a compatibility fallback by active job kind/stage only when the new field is absent;
- treat `failed` and `cancelled` active jobs as `attention` even if the run status is still a working value;
- prefer the safe run-level error, then the active job's safe error, then a fixed generic message;
- expose `retry_available` separately from `safeError.retryable`;
- preserve active and candidate previews during attention;
- never normalize an unknown backend status to `complete` or `available`.

All other stage adapters follow the same pattern: accept `unknown`, validate the minimal envelope, normalize only known statuses, and retain the complete agent-owned output separately from presentation cards.

## Polling rules

- Subscribe only while the normalized stage state is `working`.
- Unsubscribe immediately after `review`, `complete`, `attention`, `locked`, or `unsupported`.
- Preserve current backoff and hidden-tab pause behavior.
- A failed job must stop polling after the next successful state fetch.
- A transient network error may mark the connection stale and retry; it must not change the server stage state to attention.
- Show a last-updated or refresh affordance when a connection is stale.

## Approval and start semantics

The combined button remains one explicit user command; it is not automatic chaining. It performs guarded server calls in order:

```text
approve current stage
  → if approved, start next stage with its own idempotency key
  → if start fails, show approved state plus “Start next stage”
```

Never roll back a successful approval in the browser. Never show the next stage as working until the start response confirms it.

## Invariants to preserve

- Google/Supabase authentication and ownership boundaries;
- active/onboarded/admin/read-only authorization behavior;
- server-side approval gates and immutable approved snapshots;
- optimistic session revision and compare-and-swap behavior;
- per-operation idempotency keys;
- worker authorization and release/contract fencing;
- entitlement and one-generation restrictions;
- verified preview promotion and cross-origin preview isolation;
- no automatic Build Preparation → Code Generator chain.
