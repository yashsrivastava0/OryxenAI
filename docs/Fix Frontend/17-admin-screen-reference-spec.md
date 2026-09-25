# Admin screen reference specification

This is the visual and interaction handoff for the role-gated administrator
control plane at `/admin`. It is documentation and reference work only. The
implementer must preserve the existing server-authorized API, auth boundary,
typed confirmation flow, idempotency behavior, and safe projections.

## How to use this pack

Read the source contract first, then use the visual references for hierarchy,
density, spacing, and responsive composition:

- [Administrator console specification](10-admin-console-specification.md)
- [Admin shell template](../../src/oryxenai/auth/templates/auth_shell.html)
- [Admin browser controller](../../src/oryxenai/auth/static/auth-admin.mjs)
- [Admin styles](../../src/oryxenai/auth/static/auth.css)
- [Admin API routes](../../src/oryxenai/auth/admin/api.py)
- [Admin service projections](../../src/oryxenai/auth/admin/service.py)

The existing overview reference is [12-admin-control-center.png](visuals/12-admin-control-center.png).
The complete additional set is:

| Reference | Screen/state |
| --- | --- |
| [18-admin-users-ledger.png](visuals/18-admin-users-ledger.png) | Users ledger |
| [19-admin-projects-ledger.png](visuals/19-admin-projects-ledger.png) | Projects ledger |
| [20-admin-legacy-projects.png](visuals/20-admin-legacy-projects.png) | Legacy projects ledger |
| [21-admin-deleted-identities.png](visuals/21-admin-deleted-identities.png) | Deleted identities ledger |
| [22-admin-operations-ledger.png](visuals/22-admin-operations-ledger.png) | Operations ledger |
| [23-admin-audit-ledger.png](visuals/23-admin-audit-ledger.png) | Read-only audit ledger |
| [24-admin-action-confirmation.png](visuals/24-admin-action-confirmation.png) | Typed confirmation dialog |

The images are implementation references, not production assets. They are
intentionally illustrative. The source code and API contract win over any
label, field, count, tab, or action accidentally invented by image generation.
For example, some visual references may show a generic `Add user` affordance,
`Last active`, or navigation labels such as `Billing` or `Security`; these are
not part of the current admin contract and must not be implemented unless a
separate product decision and backend contract add them.

## Admin product boundary

`/admin` is a separate administrator control plane. It is not part of the
creator workflow or a persistent developer console. A normal
creator must never see administrator destructive controls in the `/app`
topbar. The only normal creator entry is a role-gated account-menu link when
the current identity is an administrator.

The admin page has one shell and six data views:

1. Users
2. Projects
3. Legacy
4. Deleted
5. Operations
6. Audit

The shell also has an initial loading/overview state, empty/error states, a
session-expiry state, and a typed confirmation dialog. These are states of the
same page, not new backend routes.

## Shared shell specification

At desktop widths, compose one full-width canvas with a readable maximum
content width. Keep the hierarchy calm and operational:

1. Compact topbar: OryxenAI, `Workspace administration`, current administrator
   identity, `Workspace`, `Refresh`, `Sign out`, and an avatar or initials.
2. Page heading: `Workspace administration` with one concise sentence that
   explains the control-plane purpose.
3. A small `role="status"` or existing polite live region. It must announce
   only meaningful transitions such as loading, refreshed, unavailable, or
   session ended.
4. Safe account details: username, role, and status. Never display a raw
   provider token, private claim, secret, or unmasked email.
5. A keyboard-reachable tablist with exactly `Users`, `Projects`, `Legacy`,
   `Deleted`, `Operations`, and `Audit`.
6. Four summary metrics: `Active users`, `Projects`, `Running jobs`, and
   `Pending operations`.
7. The selected ledger/list surface.
8. `Load more` only when the API returns `next_cursor`.

The surface should use the existing warm cream, deep ink, cobalt, and fine
rule direction. Keep editorial serif type for page and section headings and a
clean sans-serif for controls and dense metadata. Decorative marks are
secondary. Do not add charts, gradients, neon, glass panels, external media,
raw JSON, stack traces, secrets, or an always-open developer rail.

The generated images use table-like ledgers because they make the information
architecture easy to compare. The current browser controller renders safe
`article.admin-row` rows. It is acceptable to improve the visual row layout,
but preserve semantic headings, keyboard access, text alternatives, and the
existing data/action rules.

## Exact data and action contract

Use API data rather than fixture labels or visual-reference values. The
administrator service currently projects the following safe fields.

| View | Read endpoint | Display fields | Actions |
| --- | --- | --- | --- |
| Users | `GET /api/v1/admin/users` | `id`, `username`, `masked_email`, `role`, `status`, onboarding state, safe timestamps, entitlement summary | `suspend` or `restore`; normal-user `reset_entitlement` and `promote`; admin `demote`; `delete` where server-authorized; never for self or deleted rows |
| Legacy | `GET /api/v1/admin/legacy-projects` | project/session identity, owner information, `status`, legacy marker, safe timestamps | `delete` only where server-authorized |
| Deleted | `GET /api/v1/admin/deleted-identities` | tombstone `id`, former role, masked email, deletion date, `readmission_approved` | `readmit` only when `readmission_approved` is false |
| Operations | `GET /api/v1/admin/operations` | operation `id`, `action`, `target_type`, target id when safe, `status`, `step`, attempt count, `last_error_code`, updated time, `resumable` | `Resume safely` only when `resumable` is true |
| Audit | `GET /api/v1/admin/audit-events` | event id, action, target type, outcome, safe details, safe timestamp | strictly read-only |

The summary is read from `GET /api/v1/admin/summary` and maps to the four
metrics already rendered by `renderSummary` in `auth-admin.mjs`:

```text
Active users       ← summary.users.active
Projects           ← summary.projects.active
Running jobs       ← summary.jobs.running
Pending operations ← summary.pending_operations
```

Display an identity using a safe human-readable projection where available.
Never expose raw UUIDs as the primary label. For a missing display identity,
use the existing safe fallback rather than fabricating a name.

## Screen-by-screen implementation brief

### 1. Initial admin control center

Reference: [12-admin-control-center.png](visuals/12-admin-control-center.png).

Purpose: establish the administrator's context before they inspect a view.

Hierarchy:

- topbar and administrator status;
- `Workspace administration` heading and control-plane explanation;
- account details;
- six-tab navigator;
- four summary metrics;
- Users selected by default;
- first page of the Users ledger and `Load more` when applicable.

On initial load, retain this shell and replace only data regions with compact
skeletons or `Loading safe administrator data.`. A slow request must not blank
the page or shift the topbar.

### 2. Users ledger

Reference: [18-admin-users-ledger.png](visuals/18-admin-users-ledger.png).

Purpose: inspect identities and perform server-authorized lifecycle actions.

Each row should make the following obvious without opening a drawer:

- username or safe fallback as the row heading;
- role, status, and masked email as secondary metadata;
- entitlement facts only when useful and already projected by the API;
- an action cluster that contains only actions legal for that row.

Use text statuses such as `Active`, `Suspended`, `Deleted`, and `Admin`, with
color as a secondary cue. Hide self-actions. Do not add `Add user`, search,
bulk selection, invite flows, or password controls to this screen.

Loading keeps the Users tab selected. Empty results show a direct message,
`Nothing is visible in this view.`. A mutation closes only after the accepted
server response, refreshes the view, and reports the safe result.

### 3. Projects ledger

Reference: [19-admin-projects-ledger.png](visuals/19-admin-projects-ledger.png).

Each row should show:

- project/session display identity;
- current project status;
- owner username and masked email where available;
- only safe activity or generation facts already projected by the service;

Keep retry and regenerate visually distinct from delete. They still use the
same typed confirmation and idempotency behavior. Do not create a new
developer dashboard, preview editor, or raw job payload panel in this view.

### 4. Legacy projects ledger

Reference: [20-admin-legacy-projects.png](visuals/20-admin-legacy-projects.png).

Purpose: make quarantined older projects inspectable without mixing them into
the normal creator workflow.

Use a clear `Legacy projects` heading or view label, a short explanation that
these projects are quarantined from the creator workflow, and a compact list
of project identity, status, owner/legacy marker, and safe dates. Show only a
server-authorized `Delete` action. Do not imply that legacy projects can be
restored, edited, published, or sent through a new generation path.

### 5. Deleted identities ledger

Reference: [21-admin-deleted-identities.png](visuals/21-admin-deleted-identities.png).

Purpose: inspect tombstones and perform authorized readmission only when it is
still awaiting approval.

Show:

- tombstone identity;
- former role;
- masked email;
- deletion time or other safe date;
- `Awaiting approval` or `Readmission approved` state;
- `Readmit identity` only on an awaiting row.

Rows already approved are read-only. Do not show restore/delete actions,
unmask email, sign-in credentials, or a claim that readmission has completed
before the accepted response and subsequent refresh. Explain the boundary in
plain language: deleted identities cannot sign in until the authorized
readmission process completes.

### 6. Operations ledger

Reference: [22-admin-operations-ledger.png](visuals/22-admin-operations-ledger.png).

Purpose: expose safe progress and recovery for audited administrator lifecycle
operations.

Show a row-level progression from action to status to current step. The safe
fields are:

- operation identity;
- action;
- target type and safe target reference where appropriate;
- status;
- current step;
- attempt count or updated time when useful;
- last safe error code;
- `Resume safely` only when `resumable` is true.

`resumable` is server-derived. The current service marks an operation
resumable only for retryable failures in the allowed delete action set. Never
infer it from a red status, and never make a failed operation appear
recoverable when the server says otherwise. Raw stack traces, payloads, or
provider messages are never shown.

### 7. Audit ledger

Reference: [23-admin-audit-ledger.png](visuals/23-admin-audit-ledger.png).

Purpose: give administrators a safe, read-only history of actions and
outcomes.

Use a calm ledger with event identity, action, outcome, target type, safe
target reference/details, and created time. Outcomes must include text such as
`Succeeded` or `Rejected`; never rely on color alone. There are no row action
buttons, checkboxes, delete controls, retry controls, export claims, or edit
affordances. Do not expose raw request IDs, provider details, or arbitrary
`safe_details` without deliberate safe formatting.

### 8. Typed confirmation dialog

Reference: [24-admin-action-confirmation.png](visuals/24-admin-action-confirmation.png).

Every mutating action opens the existing `dialog` before a request is sent.
The dialog must contain:

- `Confirm administrator action` heading;
- action and target summary;
- clear statement that the action is server-authorized and may be
  irreversible;
- exact target confirmation input, focused on open;
- optional reason field, capped by the existing request schema;
- `Cancel` and `Confirm` actions;
- visible invalid/mismatch feedback without losing the target context.

Cancel closes the dialog and returns focus to the source button. Escape closes
it. Confirm remains disabled or rejected until the exact target value matches.
On submit, reuse the existing `Idempotency-Key` per action/target. Keep that
key for retryable failure and clear it only after a successful request or when
the user intentionally starts a new attempt. Do not display the key itself.

For `Resume safely`, the same confirmation boundary applies even though the
request body is different. The server remains authoritative.

## Non-data states that must be designed

### Loading

Keep the topbar, heading, tabs, and account context visible. Use stable-height
skeletons or direct loading copy. Disable only the control that initiated the
request when possible; do not make the whole page appear inert.

### Empty

Keep the selected tab, heading, and status line. Show
`Nothing is visible in this view.` with enough explanation to distinguish an
empty view from a failed request. Do not use a blank panel.

### Refreshing and stale data

Preserve the selected tab and current page position unless the user explicitly
requests a reset. Announce only `Loading safe administrator data.` and then a
single refreshed/unavailable transition. Do not move focus to a background
refresh result.

### Request failure

Keep the ledger and tab visible. Show a direct safe error in the status region,
re-enable the relevant controls, and allow a retry when the server indicates
the operation is retryable. Do not replace the whole page with a generic
technical error.

### Session expiry or unauthorized access

On an auth failure, clear private client state, announce `Your administrator
session ended.`, invalidate the browser session using the existing auth
runtime, and redirect to `/sign-in`. The client must not cache or continue to
render private administrator data after the boundary fails.

### Operation partially succeeds

If the server accepts a request but follow-up refresh fails, report the
accepted action separately from the unavailable refresh. Never show a stale
row as proof that the mutation failed, and never claim the page is current
without a successful read.

## Responsive composition

### Desktop: 1366–1536px

- Keep one centered admin canvas with generous side gutters.
- Use four summary columns.
- Keep row metadata and action cluster on one line when it fits.
- Do not let action labels compress into icons only.

### Tablet: approximately 768px

- Use two summary columns.
- Let the tablist wrap or scroll inside its own bounded region; it must not
  create page-level horizontal overflow.
- Stack row metadata before actions.
- Keep confirmation controls inside the viewport with a clear focus ring.

### Mobile: approximately 390px

- Use one summary column.
- Keep topbar controls compact; move low-priority identity details below the
  main title if necessary, without hiding session state.
- Use one-column rows with identity, metadata, status, then full-width actions.
- Use a full-width or viewport-safe dialog with no clipped buttons or fields.
- Preserve readable labels such as `Resume safely`, `Readmit identity`, and
  `Confirm`; do not rely on icon-only actions.

## Implementation guardrails

1. Do not add a new backend endpoint, mutation protocol, or client-side
   authorization rule.
2. Do not infer permissions from visual status. Render server-authorized
   actions only.
3. Do not invent fields from the images. The safe service projections are the
   source of truth.
4. Do not show raw JSON, UUIDs, provider secrets, request IDs, stack traces,
   or unmasked emails.
5. Do not add `Add user`, Billing, Security, Models, Settings, search,
   filtering, bulk actions, or export until separately specified and backed by
   an API contract.
6. Preserve `role="tablist"`, `role="tab"`, `aria-selected`, visible focus,
   polite status announcements, and reduced-motion behavior.
7. Preserve the existing `Idempotency-Key`, typed confirmation, auth-failure,
   pagination, and `next_cursor` behavior.
8. Keep the console operational and calm: one canvas, one selected ledger, one
   clear state message.

## Visual prompt record

These are the normalized prompts used for the new references. They describe
intent and composition only; the app contract above remains authoritative.

### 18 — Users ledger

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Users ledger. Use a compact topbar with OryxenAI, Workspace administration, administrator session active, Workspace, Refresh, Sign out, and admin avatar. Show the Users tab selected, four safe summary metrics, and a bounded readable ledger. Rows show username, role, status, masked email, and only server-authorized row actions. Use suspend/restore, reset entitlement for normal users, promote/demote, and delete only where legal; hide self-actions and deleted-row actions. Do not invent Add user, search, bulk controls, secrets, raw IDs, JSON, charts, external images, gradients, neon, or glass. Warm cream paper, deep ink, cobalt, fine rules, editorial serif headings, clean grotesk controls, generous whitespace, no clipped controls.
```

### 19 — Projects ledger

### 20 — Legacy projects

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Legacy projects ledger. Show the compact admin shell with Legacy selected, four safe summary metrics, a clear Legacy projects heading, a short quarantine explanation, and a bounded ledger. Rows show legacy project identity, status, owner or legacy marker, safe dates, and Delete only where server-authorized. Do not imply restore, edit, publish, or new generation. Do not invent navigation areas, raw JSON, secrets, UUIDs, external images, charts, gradients, neon, or glass. Warm cream paper, deep ink, cobalt, fine rules, editorial serif headings, clean grotesk controls, generous whitespace, no clipping.
```

### 21 — Deleted identities

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Deleted identities ledger. Show the compact admin shell with Deleted selected, four safe summary metrics, and a bounded ledger with tombstone identity, former role, masked email, deletion time, readmission state, and Readmit identity only for rows awaiting approval. Approved rows are read-only. Include a calm boundary message that deleted identities cannot sign in until authorized readmission. Do not show restore/delete, unmasked email, credentials, raw JSON, secrets, UUIDs, external images, charts, gradients, neon, or glass. Warm cream, deep ink, cobalt, restrained warning accent, fine rules, editorial serif headings, clean grotesk controls, generous whitespace, no clipping.
```

### 22 — Operations

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Operations ledger. Show the compact admin shell with Operations selected, four safe summary metrics, a concise reconciled status line, and a bounded ledger with operation identity, action, status, current step, safe last error code, and action. Show Resume safely only when server-provided resumable is true. Use generic safe states such as running, retryable failure, complete, and non-retryable failure. Never show stack traces, secrets, raw payloads, UUIDs, invented settings, charts, external images, gradients, neon, or glass. Warm cream, deep ink, cobalt, restrained status colors, fine rules, editorial serif headings, clean grotesk controls, generous whitespace, viewport-safe.
```

### 23 — Audit

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Audit ledger. Show the compact admin shell with Audit selected, four safe summary metrics, a read-only audit trail status line, and a bounded ledger with event identity, action, outcome, target type or safe target reference, and timestamp. Make it unmistakably read-only: no action buttons, selection checkboxes, delete, retry, edit, or export claims. Outcomes use text and color as a secondary cue. Do not show raw request IDs, secrets, stack traces, JSON, UUIDs, external images, charts, gradients, neon, or glass. Warm cream, deep ink, cobalt, fine rules, editorial serif headings, clean grotesk controls, generous whitespace, no clipping.
```

### 24 — Typed confirmation

```text
Create one polished horizontal 1600x1000 (16:10) OryxenAI administrator Projects ledger with an accessible typed confirmation dialog open over it. Keep the compact admin shell and selected Projects tab visible behind a dimmed but legible background. Center a modal titled Confirm administrator action with action Delete project, a safe target summary, a warning that it is server-authorized and may be irreversible, an exact target confirmation input with visible focus ring, an optional reason field, Cancel, and Confirm delete. Show no destructive result, secrets, raw IDs, JSON, stack traces, external images, charts, gradients, neon, or glass. Warm cream, deep ink, cobalt, restrained red only for destructive affordance, fine rules, editorial serif heading, clean grotesk controls, viewport-safe modal.
```

## Completion checklist for the implementing AI

- [ ] `/admin` remains role-gated and separate from the creator workflow.
- [ ] The shell, six tabs, four summary metrics, selected ledger, and
      conditional `Load more` are present.
- [ ] All row display fields come from safe API projections.
- [ ] The action matrix matches the server-authorized action rules.
- [ ] Every mutation uses the existing typed confirmation and idempotency key.
- [ ] Operations expose `Resume safely` only for server-provided `resumable`.
- [ ] Audit remains strictly read-only.
- [ ] Loading, empty, request failure, stale data, and session expiry are
      visible, direct, and recoverable.
- [ ] No raw JSON, secrets, stack traces, unmasked email, raw UUID, or
      contract-inventing visual affordance leaks into product mode.
- [ ] Desktop, tablet, and mobile layouts have no page overflow or clipped
      labels/dialog controls.
- [ ] Keyboard tab semantics, focus return, Escape close, visible focus,
      concise status announcements, and reduced-motion behavior pass.
- [ ] The visual references are used for composition—not copied as new API
      behavior or production assets.
