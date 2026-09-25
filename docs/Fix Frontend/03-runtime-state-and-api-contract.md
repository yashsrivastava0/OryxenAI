# Runtime state and API contract

This document describes the minimum backend/frontend coordination required to make the UI truthful. The existing server-authoritative model remains intact.

## Existing identity distinction

- `current_run_id`: the durable development/session run identity;
- `jobs[].id`: the durable background job identity.

They must never be compared as if they were the same value. The current frontend adapter passes `current_run_id` into job selection, so it often receives no job even when a job exists.

## Terminal failure behavior

The UI must converge to `attention` for all terminal failure paths:

1. Agent code catches a known/provider/model/validation failure and persists `needs_attention`.
2. Worker timeout exhausts retries.
3. Worker receives a terminal handler exception or a failed result.
4. A selected active job is already `failed` or `cancelled` while the run projection is stale.

Authorization-fence failures remain security failures. They must not be converted into a blind retry loop. The UI should show that the session needs refreshing or support intervention when no server-authorized retry exists.

## Frontend adapter rules

- select the job by `active_job_id`;
- use a compatibility fallback by active job kind/stage only when the new field is absent;
- treat `failed` and `cancelled` active jobs as `attention` even if the run status is still a working value;
- prefer the safe run-level error, then the active job's safe error, then a fixed generic message;
- expose `retry_available` separately from `safeError.retryable`;
- never normalize an unknown backend status to `complete` or `available`.

The retained stage adapters follow the same pattern: accept `unknown`, validate the minimal envelope, normalize only known statuses, and retain the complete agent-owned output separately from presentation cards.

## Polling rules

- Subscribe only while the normalized stage state is `working`.
- Unsubscribe immediately after `review`, `complete`, `attention`, `locked`, or `unsupported`.
- Preserve current backoff and hidden-tab pause behavior.
- A failed job must stop polling after the next successful state fetch.
- A transient network error may mark the connection stale and retry; it must not change the server stage state to attention.
- Show a last-updated or refresh affordance when a connection is stale.

## Approval and start semantics

Discovery approval is saved first. Starting Content Architect is a separate explicit command, and approval never starts work automatically. Content Architect approval is terminal for the active workflow.

```text
approve Discovery brief
  → show the approved brief
  → allow an explicit Content Architect start request
  → after Content Architect approval, stop the active workflow
```

Never roll back a successful approval in the browser. Do not show Content Architect as working until its start response confirms it.

## Invariants to preserve

- Google/Supabase authentication and ownership boundaries;
- active/onboarded/admin/read-only authorization behavior;
- server-side approval gates and immutable approved snapshots;
- optimistic session revision and compare-and-swap behavior;
- per-operation idempotency keys;
- worker authorization and release/contract fencing;
- the terminal Content Architect approval boundary;
