# Administrator console specification

The administrator surface is a separate, role-gated control plane at `/admin`. It is not part of the creator's stage navigator and must not be styled or positioned as a destructive control inside the ordinary `/app` workflow.

The existing implementation already provides the basic shell in `src/oryxenai/auth/templates/auth_shell.html`, the browser controller in `src/oryxenai/auth/static/auth-admin.mjs`, the visual tokens in `src/oryxenai/auth/static/auth.css`, and server-authorized routes in `src/oryxenai/auth/admin/api.py`. This document tells the implementing AI what to preserve, what to relocate, and what to validate.

Reference image: [12-admin-control-center.png](visuals/12-admin-control-center.png). The image communicates hierarchy and density only; live names, counts, statuses, and timestamps must come from the API.

## Purpose and boundary

The admin page supports safe workspace lifecycle administration:

- inspect aggregate workspace health;
- inspect users, projects, legacy projects, deleted identities, durable administrator operations, and audit events;
- request server-authorized lifecycle actions;
- recover resumable administrator operations;
- issue the existing administrator-only Code Generator retry/regenerate commands where the server allows them.

The creator shell may expose `Administration` from the account menu only when the current identity is an administrator. It must not display `Reset Pipeline` in the creator topbar. The existing reset command may remain in the admin-only account surface or be surfaced inside this console only if its current server-authorized handler is reused; do not invent a new backend mutation endpoint as part of this documentation/remediation handoff. The current source location to audit is `frontend/src/app/AppShell.tsx`.

## Screen anatomy

At desktop width, use one readable full-width admin canvas with these regions in order:

1. compact topbar: OryxenAI, current administrator identity, workspace link, refresh, sign out;
2. page heading: `Workspace administration` and a sentence explaining that this is the control plane;
3. live status line with `role="status"` or the existing polite live-region behavior;
4. safe account details: username, role, status;
5. tablist: `Users`, `Projects`, `Legacy`, `Deleted`, `Operations`, `Audit`;
6. summary band: `Active users`, `Projects`, `Running jobs`, `Pending operations`;
7. the selected ledger/list surface;
8. pagination via `Load more` when the response includes `next_cursor`.

Do not add charts, external images, raw JSON, UUIDs, secrets, or a second permanent developer rail. This is a dense ledger, not a second portfolio-generation dashboard.

## Tab contracts

| Tab | API read route | Row identity | Safe row metadata | Permitted controls |
|---|---|---|---|---|
| Users | `GET /api/v1/admin/users` | username or safe fallback | role, status, masked email | suspend/restore, reset entitlement for normal users, promote/demote, delete, subject to server rules |
| Projects | `GET /api/v1/admin/projects` | project/session display identity | status, owner username | delete, Code Generator retry, Code Generator regenerate where active and authorized |
| Legacy | `GET /api/v1/admin/legacy-projects` | legacy project identity | status, owner/legacy marker | delete, subject to server rules |
| Deleted | `GET /api/v1/admin/deleted-identities` | tombstone identity | former role, masked email, readmission state | readmit only when the row is awaiting approval |
| Operations | `GET /api/v1/admin/operations` | operation identity | action, status, step, safe error code | `Resume safely` only when `resumable` is true |
| Audit | `GET /api/v1/admin/audit-events` | event identity | action, outcome, target type | read-only |

The list controller must keep the selected tab, cursor, and live status coherent during refresh. Empty results use `Nothing is visible in this view.` or an equivalent direct empty state, not a blank canvas.

## Button and confirmation behavior

Every mutating row action opens the existing typed-target confirmation dialog before sending a request. The dialog includes:

- action and target summary;
- exact target confirmation input;
- optional reason field capped by the existing request schema;
- Cancel and Confirm buttons;
- clear statement that the action is server-authorized and may be irreversible;
- focus on the confirmation input when opened;
- focus return to the source button when closed without completion.

The browser must preserve the existing `Idempotency-Key` per logical action/target until the request succeeds or the user intentionally starts a new attempt. Do not create a second client-side mutation protocol.

Do not show an action that the current row cannot legally perform. In particular:

- hide self-mutating administrator actions where the server forbids them;
- hide destructive actions for deleted rows or non-active projects;
- never claim a delete, demotion, readmission, or entitlement reset completed before the accepted operation response and subsequent refresh;
- use the server's safe error text for last-admin, self-action, cleanup, readmission, and retry conflicts.

## Admin error and loading states

Initial load: show a compact skeleton or `Loading safe administrator data.` status without replacing the page shell.

Refresh: preserve the selected tab and current page position unless the user explicitly requests a reset; announce only the transition to refreshed or unavailable.

Unauthorized/session-expired: clear private client state, announce that the administrator session ended, and redirect to `/sign-in` through the existing auth runtime.

Provider/operation failure: keep the row and tab visible, show a direct safe error in the live status region, re-enable controls, and retain the idempotency key if the operation is retryable.

Resumable operation: show `Resume safely` only when the server returns `resumable: true`; after acceptance, refresh the Operations tab and report the new safe status.

## Responsive and accessibility contract

- desktop: summary in four columns; rows can use a compact action cluster;
- tablet: summary in two columns; tab strip wraps or scrolls inside its own container;
- mobile: summary in one column, row metadata stacks, action buttons become full-width or two-column within the row, and the confirmation dialog fits the viewport;
- all tabs are keyboard reachable with a visible selected state; the existing `role="tablist"`/`role="tab"` semantics must remain valid;
- `aria-selected` changes with the selected tab; live status announcements are concise and transition-based;
- focus is never moved to a background refresh result unless the user initiated the refresh;
- reduced-motion users receive the same state changes without entrance or dialog animation;
- no content or action depends on color alone; `Active`, `Suspended`, and operation statuses include text.

## Acceptance checks

1. A normal creator never sees the destructive admin reset in the `/app` topbar.
2. An authorized administrator can reach `/admin` from the account menu and return to `/app`.
3. `/admin` renders all six tabs and the four safe summary metrics from API data.
4. Users, projects, deleted identities, operations, and audit rows show only safe display fields.
5. Mutations use the existing typed confirmation and idempotency behavior.
6. An unauthorized user cannot access admin data or mutation routes, even if a client-side link is guessed.
7. A session-expiry response clears private state and returns the user to sign-in.
8. Mobile validation has no horizontal overflow, clipped action labels, or inaccessible dialog controls.
