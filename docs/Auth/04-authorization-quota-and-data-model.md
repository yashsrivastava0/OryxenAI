# Authorization, portfolio entitlement, and data model

This document summarizes current server-enforced authorization. The auth
models, entitlement repository, and route dependencies are authoritative.

## Entitlement

Each normal user has one PortfolioEntitlement row. It binds that user's
portfolio_session_id, records deletion/reset lifecycle state, and increments a
revision when the binding changes. A normal user can create one owned portfolio
session. An active administrator follows the configured administrator policy.

The entitlement is a capability projection, not a client-side permission
check. Every mutating request recomputes and enforces the binding on the server.

## Session and run ownership

portfolio_sessions stores owner_user_id, active/quarantined status, current
JSONB state, and a revision counter. agent_runs and background_jobs carry
session ownership and actor context where applicable. State and run APIs return
current schema projections rather than raw historical payloads.

## Durable-work authorization

A portfolio-bound job includes a trusted owner, actor, session, entitlement
revision, and authorization context version. WorkerAuthorizationFence checks
the current account, ownership, lease, payload binding, and entitlement
revision before processing and applying results. A stale or unauthorized job
cannot mutate the portfolio.

## Administrator lifecycle

Administrative operations are recorded in audit tables and have resumable
states. Account and portfolio deletion use explicit transactions and declared
foreign-key ordering. Associated stored artifacts are removed through the
archive-storage boundary after authorization. Existing historical records are
not removed by ordinary stage starts, approvals, or reads.

## Data lifecycle rules

- Do not trust an identifier from the client as proof of ownership.
- Do not expose historical JSON fields through current state projections.
- Preserve records and stored outputs unless an authorized deletion or
  retention operation explicitly removes them.
- Keep entitlement and worker checks server-side.
- Apply migrations explicitly; never reset the application database during
  normal tests or cleanup.
