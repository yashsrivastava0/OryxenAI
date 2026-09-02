# State, progress, and edge cases

## 1. State model

The browser renders a projection of durable server state. It is never the authority
for stage completion, approval, entitlement, preview readiness, retryability, or
ownership.

Every stage adapter normalizes its backend status into one of six UI states:

| UI state | Meaning | General treatment |
| --- | --- | --- |
| `locked` | An upstream gate is incomplete | Visible in the journey, not actionable |
| `ready` | The user may start or continue the stage | One primary action |
| `working` | Durable work is queued or running | Stable context plus semantic progress |
| `review` | A durable artifact needs a user decision | Artifact and explicit review actions |
| `needs_attention` | Work cannot advance without recovery | Safe explanation and supported recovery |
| `complete` | The stage’s durable completion condition is satisfied | Readable artifact and handoff action |

`preview` is the terminal experience state. It is ready only when the Code Generator
state contains an active promoted preview that can be framed by the configured
preview origin.

### Normalized frontend projection

The future client should keep backend payloads behind stage adapters and render a
small view model:

```ts
type JourneyStage =
  | "discovery"
  | "content"
  | "design"
  | "prepare"
  | "generate"
  | "preview";

type JourneyState =
  | "locked"
  | "ready"
  | "working"
  | "review"
  | "needs_attention"
  | "complete";

type AttentionState = "background" | "update" | "action_required";
type PreviewViewport = "mobile" | "tablet" | "desktop" | "fit";

interface StageViewModel {
  stage: JourneyStage;
  state: JourneyState;
  label: string;
  statusText: string;
  attention: AttentionState;
  primaryAction: null | {
    id: string;
    label: string;
    enabled: boolean;
  };
  artifactAvailable: boolean;
  lastConfirmedAt: string | null;
  safeError: null | {
    summary: string;
    nextAction: string | null;
    technicalReference: string | null;
  };
}
```

This is a frontend interface, not a proposed API response. Adapters must preserve the
original payload for request construction without passing it indiscriminately into
components.

## 2. Status normalization

### Discovery

Authoritative enum: `src/oryxenai/agents/discovery/schemas.py`.

| Backend status | UI state | User-facing behavior |
| --- | --- | --- |
| `not_started` | `ready` | Show intake and “Start my portfolio” |
| `questions_queued` | `working` | “Discovery is queued” |
| `questions_running` | `working` | “Preparing the next questions” |
| `questions_ready` | `ready` | Show the first unanswered question |
| `answers_in_progress` | `ready` | Resume the next unanswered question |
| `brief_running` | `working` | Keep answers visible; “Drafting your brief” |
| `brief_review` | `review` | Open the brief artifact and review controls |
| `approved` | `complete` | Approved brief plus “Continue to Content” |
| `needs_attention` | `needs_attention` | Show safe error and the supported retry |

The adapter also inspects the question/answer projection. `questions_ready` with no
remaining answerable question is treated as stale client data and triggers a
refetch; it must not render an empty composer.

### Content Architect

Authoritative enum: `src/oryxenai/agents/content_architect/schemas.py`.

| Backend status | UI state | User-facing behavior |
| --- | --- | --- |
| `not_started` | `ready` only after Discovery approval; otherwise `locked` | Explain the upstream gate |
| `build_running` | `working` | “Structuring your portfolio content” |
| `content_review` | `review` | Content artifact, revision, approve |
| `approved` | `complete` | Approved artifact plus “Continue to Design” |
| `needs_attention` | `needs_attention` | Safe error and supported retry |

### Visual Design Director

Authoritative enum: `src/oryxenai/agents/visual_design_director/schemas.py`.

| Backend status | UI state | User-facing behavior |
| --- | --- | --- |
| `not_started` | `ready` only after Content approval; otherwise `locked` | Explain the upstream gate |
| `build_running` | `working` | “Developing the visual direction” |
| `design_review` | `review` | Design artifact, revision, approve |
| `approved` | `complete` | Approved artifact plus “Prepare build” |
| `needs_attention` | `needs_attention` | Safe error and supported retry |

### Build Preparation

Authoritative enum and fields:
`src/oryxenai/agents/build_preparation/schemas.py`.

| Backend status | UI state | User-facing behavior |
| --- | --- | --- |
| `not_started` | `ready` only after Content and Design approval; otherwise `locked` | Show “Prepare build” |
| `running` | `working` | Show mapped preparation milestone |
| `ready` | `complete` only when the handoff remains eligible, unexpired, and non-stale | Show “Generate portfolio” |
| `needs_attention` | `needs_attention` | Explain failure or upstream action |

Additional rules:

- `stale=true` overrides `ready` and becomes `needs_attention` with “Regenerate
  preparation.”
- Missing, expired, changed, or unverified artifact metadata prevents Generation.
- `current_stage` and events are translated by a versioned adapter. Unknown stage
  values produce the honest fallback “Preparing the build package,” not a guessed
  milestone.
- Provider names, raw candidate records, storage keys, and signed URLs do not enter
  the normal-user view model.

### Code Generator

Authoritative enum and fields:
`src/oryxenai/agents/code_generator/session_schemas.py`.

| Backend status | UI state | User-facing behavior |
| --- | --- | --- |
| `not_started` | `ready` only with an eligible preparation pack and entitlement | Show “Generate portfolio” |
| `queued` | `working` | “Generation is queued” |
| `planning` | `working` | “Planning the portfolio build” |
| `acquiring` | `working` | “Gathering approved materials” |
| `generating` | `working` | “Building the portfolio” plus safe checkpoint text |
| `verifying` | `working` | “Checking routes, layout, and runtime” |
| `preview_pending` | `working` | “Finalizing the verified Preview” |
| `ready` with active preview | `complete` | Open Preview |
| `ready` without active preview | `needs_attention` | Refetch once, then show a safe readiness inconsistency |
| `needs_attention` | `needs_attention` | Preserve prior Preview and show supported retry |

Additional rules:

- `stale=true` blocks a new generation action and points back to preparation.
- `active_preview` may remain available during working or failed states. The Preview
  journey destination is then `complete`, while Generate remains `working` or
  `needs_attention`.
- `read_only=true` from the entitlement projection removes generation, retry, and
  regeneration controls regardless of the stage payload.
- Normal-user regeneration is never inferred from an administrator or development
  route.

## 3. Honest progress

### User-facing milestone sequence

Progress uses checkpoints, not percentages:

```text
Discover
  questions -> brief -> review -> approval

Content
  building -> review -> approval

Design
  building -> review -> approval

Prepare
  validate approvals -> resolve materials -> package -> verify handoff

Generate
  queue -> plan -> acquire -> build -> verify -> promote
```

The latest confirmed checkpoint receives a check. The current checkpoint receives a
plain active marker. Future checkpoints are quiet. The UI never estimates time from
attempt count, token usage, elapsed time, or the number of internal operations.

### What may be shown

- The current durable stage.
- Completed semantic checkpoints.
- A safe route or page name when the server explicitly exposes it.
- Whether the system is retrying, waiting for a shared generation lane, or needs user
  action when those facts are explicit.
- Elapsed time as neutral context after a meaningful delay, without an ETA.

### What must not be shown

- A fabricated percentage.
- “Almost done” without a terminal checkpoint.
- Raw model output or hidden reasoning.
- Token-by-token text.
- Unverified generated files or candidate UI.
- Internal provider names, model profile IDs, storage operations, lease/heartbeat
  details, or stack traces.

## 4. Polling and freshness

The existing workflow is polling-based. Do not introduce an event-stream dependency
without a separate backend decision.

### Polling policy

1. Fetch the selected session and relevant stage projection immediately after auth.
2. Allow only one in-flight request per resource.
3. Poll a working stage every 1.5 seconds while the document is visible.
4. Stop stage polling on review, complete, or needs-attention states.
5. On `visibilitychange` to hidden, cancel scheduled polls but do not abort a request
   that is already committing its response.
6. On return to visible, refetch `/me`, the session, the active stage, and Code
   Generator preview state immediately.
7. After a network failure, keep the last confirmed UI, mark it as unconfirmed, and
   retry at approximately 1.5, 3, 6, then 12 seconds, capped at 15 seconds.
8. Honor a safe `Retry-After` response before the local backoff.
9. Abort requests when the session/view changes or the user signs out.
10. Stop all private activity before clearing the shell on logout or terminal auth
    failure.

### Freshness language

| Condition | Copy |
| --- | --- |
| Request in flight after reconnect | “Checking for updates…” |
| Last request failed but state exists | “Offline. Showing the last confirmed state.” |
| Server state refreshed | Remove the offline banner without a toast |
| Session revision changed elsewhere | “This portfolio changed in another tab.” |
| State cannot be reconciled | “Reconnect to confirm the latest state.” |

Do not show a global error toast for every failed background poll. A persistent,
non-modal connection banner is more useful and less noisy.

## 5. Action safety

### Writes

- Disable the initiating control immediately and label it with the specific pending
  action.
- Generate and retain a unique idempotency key only for mutation endpoints whose
  public contract accepts it (currently the production Code Generator start,
  regenerate, and retry endpoints).
- Keep an unacknowledged supported key in `sessionStorage` until reconciliation
  confirms the action, so a local render does not accidentally generate a second
  logical action. A user explicitly starting a new logical action gets a new key;
  reissuing the same uncertain supported request reuses its key.
- For mutations without a public idempotency-header contract, prevent duplicate
  submission in the client and GET canonical state after an ambiguous network
  outcome before offering another submission. Do not imply that an ignored header
  provides safety.
- Never infer success solely from HTTP acceptance; refetch durable state.
- Do not allow double approval, double retry, or simultaneous stage starts.

### Optimistic concurrency conflict

On a session revision or compare-and-swap conflict:

1. keep the user’s unsent revision text locally;
2. refetch the stage;
3. explain that the portfolio changed elsewhere;
4. restore the text in a clearly labelled draft field when it is still applicable;
5. require the user to submit again against the new state.

Do not silently overwrite an approved artifact or replay a stale approval.

### Multi-tab synchronization

Use a `BroadcastChannel` scoped to the authenticated application. Messages contain
only `state-invalidated`, the opaque session ID, and a timestamp; they never contain
portfolio content or bearer tokens.

- A confirmed write broadcasts invalidation.
- Other visible tabs refetch and reconcile.
- A tab with unsent text retains the draft and marks it against the new revision.
- If `BroadcastChannel` is unavailable, normal focus/visibility refetch remains the
  fallback; do not copy private state into `localStorage`.

## 6. Authentication edge cases

Authoritative behavior remains in the auth controller and route contract.

| Situation | Required UI behavior |
| --- | --- |
| First signed-out visit | Show sign-in; make no protected portfolio request |
| Existing valid session | Resolve `/me` once, then replace to `/app` |
| OAuth canceled | Clear callback artifacts and return to sign-in with a calm message |
| Callback repeated in another tab | Let the first valid exchange win; the other tab resolves current auth state |
| Auth network failure | Keep the auth shell, offer retry, and avoid a redirect loop |
| First protected 401 | Refresh once and retry the exact request |
| Second 401 or failed refresh | Stop polling, clear private UI/storage hints, sign out locally, replace to sign-in |
| Provider/model transiently unavailable while on `/app` (`AUTH_PROVIDER_UNAVAILABLE`, `MODEL_PROVIDER_CREDIT_EXHAUSTED`) | Keep the user signed in; show a safe inline message; never force a full sign-out — corrects a bug in the current implementation where this path falls through to sign-out instead of the safe message the auth-shell controller already shows for the same codes (see `06` §3.2) |
| Provider not approved | Show access-not-approved and account-switch/sign-out actions |
| Capacity reached | Show account-unavailable; do not suggest repeated registration attempts |
| Username taken | Keep input, focus inline error, permit another value |
| Suspended/deleted account | Remove private app UI and show the safe account state |
| Normal user opens `/admin` | Replace to `/app`; do not render the admin shell first |
| Unsafe `next` destination | Discard it and use the reviewed local default |
| Logout | Stop work, clear private DOM and storage hints, call provider sign-out, replace to sign-in |

Private content must never remain visible while auth is unresolved after a refresh.

## 7. Portfolio and stage edge cases

### Session creation

- A normal user with no session sees one “Start my portfolio” action.
- Concurrent create requests resolve to the entitlement-owned canonical session.
- If a session exists, the browser resumes it instead of offering another project.
- Administrator multi-session behavior stays in admin/developer workflows.
- Detached development sessions remain a separate mode and are not described as
  normal user portfolios.

### Upstream changes and staleness

- Re-approval upstream may stale Build Preparation or Generation.
- A stale downstream stage remains reviewable but loses its forward action.
- The journey selects the earliest stage requiring action.
- Copy names the relationship: “Design changed after this preparation package was
  created. Prepare the build again.”
- Never silently reuse a stale package or claim that the existing Preview reflects new
  approvals.

### Read-only completion

- The entitlement projection is checked before rendering mutating controls.
- The default `/app` view becomes Preview.
- Approved artifacts remain readable.
- Unsupported restart, regenerate, and revision controls are absent.
- If the Preview is temporarily unreachable, read-only status remains unchanged; the
  user gets a Preview recovery state, not an offer to generate again.

### Job retry and worker recovery

- The UI reflects safe durable status rather than attempting to infer worker health.
- Automatic backend retry appears as “Trying this step again” only when explicitly
  exposed.
- User retry appears only when the API says the terminal state is retryable and the
  entitlement permits it.
- If retry would create a duplicate or is no longer eligible, refetch and explain the
  new durable state.

### Provider and capacity failures

Translate safe error classes without naming a configured provider:

| Safe class | Product message | Action |
| --- | --- | --- |
| Credit/quota exhausted | “Generation is temporarily unavailable.” | Try again only when marked retryable; otherwise return later |
| Rate limited | “The generation service is busy.” | Honor retry timing |
| Provider unavailable | “The generation service could not respond.” | Supported retry |
| Validation or upstream gap | Explain the missing approval/material in user language | Return to the named stage |
| Infrastructure/storage failure | “The verified package/preview could not be finalized.” | Retry if supported; preserve prior Preview |

Technical details may include a safe error code and trace reference behind a
disclosure. Never expose secrets, raw prompts, stack traces, signed URLs, or internal
filesystem paths.

## 8. Preview edge cases and security

### Preview state matrix

| Code Generator / gateway condition | Preview surface |
| --- | --- |
| No active preview | Empty state: “Preview will appear after verification” |
| Working, no prior preview | Progress remains primary; no iframe |
| Working, prior active preview | Prior Preview remains available and labelled current |
| `preview_pending` | Keep prior Preview if present; show finalization status outside it |
| New preview promoted | Swap to the new active URL only after the refreshed receipt is authoritative |
| Generation failed, prior preview exists | Preserve the prior Preview and show failure outside it |
| Generation failed, no preview | Show recovery; do not render a candidate |
| Gateway request fails | Keep receipt metadata and show reconnect/refresh controls |
| Selected route absent from new receipt | Replace to the first promoted route |
| Iframe posts unknown message | Ignore and optionally record a safe diagnostic; never mutate host state |

### Frame boundary

- Use an exact configured preview origin; never derive trust from a substring or
  suffix match.
- Apply the smallest sandbox capability set admitted by the existing preview
  architecture.
- Do not pass auth tokens, application cookies, portfolio source data, or account
  identity into the iframe.
- Validate `postMessage` origin, schema version, type, and field bounds.
- Generated content never controls host navigation, account actions, or API requests.
- External links open safely in a new tab.
- Do not register a generated-site service worker under the product origin.

### Route and viewport controls

- Derive routes from the promoted receipt and preserve their declared order.
- Mobile is 390×844, tablet is 768×1024, and desktop is 1440×900; fit uses available
  space and is not verification evidence.
- If the viewport cannot fit, scale the frame visually while preserving the logical
  dimensions and show the scale value to assist debugging only when useful.
- On mobile product UI, default to fit and emphasize opening the preview directly.
- Reserve the frame's box with CSS `width`/`height` or `aspect-ratio` matching the
  selected profile before the iframe's `load` event fires; never let the frame pop
  into a different size once content arrives (protects the CLS budget in `03` §9).
- Implement the "scale while preserving logical dimensions" rule as a fixed-size
  wrapper (`overflow: hidden` at the profile's true pixel size) with
  `transform: scale(available / device)` and `transform-origin: top left` on the
  iframe itself. Never change the iframe's actual `width`/`height` to a value
  outside the four profiles — that would show the generated site a viewport
  combination the backend's `runtime_verifier.py` never checked.

## 9. Loading and perceived performance

Different waits require different treatments:

| Wait | Preserve | Show |
| --- | --- | --- |
| Auth resolution | Brand shell | Living-draft loader and precise status |
| Initial portfolio load | Top bar and journey geometry | Stable skeleton matching the eventual layout |
| Agent work | Prior transcript/artifact | Current semantic milestone |
| Revision | Prior approved/review artifact | Nonblocking “Revising” banner |
| Build preparation | Approved source summary | Preparation milestones |
| Generation | Journey and prior Preview if any | Generation milestones |
| Preview frame navigation | Toolbar and frame dimensions | Inline frame loading layer |
| Reconnect | Last confirmed content | Persistent offline/checking banner |

Skeletons must match real layout dimensions and stop as soon as data is available.
Do not rotate fake status phrases to create an illusion of activity.

## 10. Accessibility contract

### Focus

- Route/view changes triggered by the user focus the new surface heading.
- Background state changes do not steal focus.
- When a question arrives while its composer is already active, update the labelled
  prompt without moving focus unexpectedly.
- An opened artifact sheet traps focus only when modal at the current breakpoint and
  restores focus to its opener.
- Inline validation focuses the first invalid field on submit.
- Terminal errors focus a summary only after a user-initiated action; background poll
  failures use the persistent banner without focus movement.

### Announcements

- One polite `role=status` region announces meaningful state changes such as “Content
  is ready to review” or “Preview is ready.”
- Do not announce timer ticks, every poll, every activity item, or decorative motion.
- Use assertive announcements only for a time-sensitive destructive/admin condition,
  not routine agent failures.
- Busy state belongs on the affected region, not the entire page.

### Controls and content

- All icon-only controls have visible tooltips and accessible names.
- Journey milestones are real links/buttons with current-state semantics.
- Tabs, disclosures, dialogs, and menus follow their native or WAI-ARIA keyboard
  pattern.
- Focus rings have at least 3:1 contrast against adjacent colors.
- Body text and controls meet WCAG AA contrast.
- Touch targets are at least 44×44 CSS pixels where space permits.
- The interface works at 200% zoom without loss of actions or content.
- `prefers-reduced-motion` removes the draft-line sweep, loading stroke motion, and
  View Transition animation while preserving immediate state changes.

## 11. Acceptance scenarios

The later frontend implementation is not complete until automated or browser-tested
coverage includes:

1. signed-out entry, successful callback, onboarding, returning session, and logout;
2. denied, unavailable, capacity, unsafe redirect, and double-401 paths;
3. first portfolio creation and canonical-session resume;
4. every backend status mapping for all five working stages;
5. explicit approval/start gates with no automatic successor start;
6. refresh or browser close/reopen during each running stage;
7. one logical write under double-click, retry, and multi-tab concurrency;
8. stale Build Preparation and Code Generator projections after upstream change;
9. retryable and non-retryable safe failures;
10. old Preview retained during regeneration/failure and replaced only after promotion;
11. route, viewport, refresh, and new-tab Preview behavior;
12. exact-origin rejection for invalid preview messages;
13. offline/reconnect and hidden-tab polling behavior;
14. keyboard-only completion of every user decision;
15. screen-reader announcements that exclude poll/activity noise;
16. reduced-motion behavior; and
17. wide desktop, laptop, tablet, and mobile layouts.
