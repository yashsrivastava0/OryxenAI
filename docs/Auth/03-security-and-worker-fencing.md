# Security and durable-work authorization

This document summarizes the current identity, ownership, and worker
authorization boundaries. Source code remains authoritative.

## Identity verification

The browser obtains a Supabase session. The API verifies signed tokens using
the configured provider keys and issuer/audience policy. Only verified
identity claims enter the local account-admission flow. Browser-safe
publishable configuration is separate from server-only credentials.

## Session ownership

Every product session is owner-scoped. Request dependencies resolve the
authenticated user and check the session owner before returning state or
accepting mutations. Current session and run payloads are projected through
the active schemas so arbitrary historical JSON is not exposed.

## Durable worker fence

The API writes a trusted owner, actor, session, and authorization-context
snapshot on portfolio-bound jobs. The worker verifies:

1. The job is still running with the expected attempt and lease.
2. The portfolio session exists, is active, and has the expected owner.
3. The owner and actor are active; a distinct actor has administrator rights.
4. The payload session matches the job-bound session.
5. A normal user's entitlement is still bound to the same portfolio and
   revision.
6. Any referenced agent run matches the job's owner, actor, and session.

A fence failure stops persistence of the result. Client-provided ownership
fields are not trusted.

## Administrator lifecycle

Administrator operations are authenticated, authorized, audited, and
resumable. Deletion first prevents new work, cancels queued jobs, waits for
running work to settle, removes associated database rows in declared foreign
key order, and cleans stored archival objects. A partial failure remains
visible as pending cleanup and can be resumed.

Historical output storage is not a user-facing serving surface. It is
accessed only by controlled cleanup code during authorized lifecycle actions.

## Operational checks

- Keep provider credentials out of browser bundles, API responses, and logs.
- Keep owner checks on the server for every session-bound route.
- Treat the worker's stored identity snapshot as a request to reauthorize,
  not as permanent authority.
- Use docs/deployment/ for release-specific operational evidence.
