# Frontend implementation blueprint and acceptance matrix

> Status: implementation-ready; reviewed 2026-09-02 (see
> [06-cross-model-review-and-decisions](06-cross-model-review-and-decisions.md)).
> This document describes how to build the researched frontend after review. It
> does not authorize backend, database, agent, entitlement, or Preview protocol
> changes.

## 0. How to implement this document

This file is the complete, self-contained implementation guide. Build it in the
five phases in §19, in order — do not start a phase before the previous one's
stop gate passes, and do not skip ahead because a later phase looks easier.
Sections §1-§18 are reference material each phase draws on; §19 is the only
section that tells you what to do and when.

**Non-negotiables, true in every phase:**

- No client router, no state library, no data-fetching library, no component
  kit, no animation library, no CSS-in-JS (§6, runtime dependency list).
- No stage ever auto-starts the next one. Every transition needs an explicit
  user action.
- Preview only ever shows an active, promoted, verified build — never an
  unpromoted candidate (§8, §8.10).
- The three auth invariants in Phase 1 (§19) must hold at the end of every
  phase, not just Phase 1: the `body.auth-pending` hide rule has a home, one
  controller decides routing, and the redirect allowlist stays exactly `/app`
  and `/admin`.
- Normal users never see developer vocabulary: no percentages/ETAs, no raw
  logs, no provider/storage names, no model picker (§9).

**Design tokens** (full detail in `03-visual-system-architecture-and-evidence.md`
§2 if anything below is ambiguous — but this table is enough to start building):

| Token | Value | Role |
| --- | --- | --- |
| `--canvas` | `#F3F0E8` | Warm application background |
| `--paper` | `#FCFBF7` | Reading and artifact surface |
| `--ink` | `#171A19` | Primary text and strong controls |
| `--graphite` | `#626660` | Secondary text and technical labels |
| `--rule` | `#D3CFC4` | Dividers, inactive journey, field boundaries |
| `--signal` | `#3157E7` | Current stage, focus, links, primary action — the only decorative accent |
| `--positive` | `#287356` | Confirmed approval, verification, completion |
| `--attention` | `#A9601E` | User action or recoverable warning |
| `--critical` | `#B33F3A` | Terminal/destructive error |
| `--preview-frame` | `#202422` | Neutral theater around generated portfolios |

Type: one self-hosted `Newsreader` serif for display/thesis/artifact-title
moments only; `system-ui` sans-serif for everything else (navigation, controls,
body copy); `ui-monospace` only for trace IDs, durations, and route paths.
Base spacing unit 4px (4, 8, 12, 16, 24, 32, 48, 64, 96). Never invent a color,
font, or spacing value outside this set — that is what makes the result look
generic instead of deliberate.

**If you need more context than this file gives you**, the rest of the package
in this same folder, one line each: `README.md` explains why (the product
premise, in one paragraph); `01-product-experience-and-information-architecture.md`
covers screens and user journeys in prose; `02-state-progress-and-edge-cases.md`
has the full backend-status-to-UI-state tables and edge-case behavior; `03` has
the complete visual system and component-language rules; `04` is background
research, skip it unless you want the reasoning behind a specific choice; `06`
is a short log of what changed in review and why — read it if a section here
references it by name.

## 1. Outcome and boundaries

The implementation should deliver one coherent normal-user journey from sign-in to
verified Preview while keeping the current backend behavior intact.

The frontend must:

- resolve authentication without exposing private content;
- place first-time and returning users in the correct `/app` posture;
- support the explicit Discover -> Content -> Design -> Prepare -> Generate flow;
- make review, revision, approval, handoff, progress, attention, and recovery clear;
- integrate only the production Code Generator session API;
- show only the active promoted Preview on its separate origin;
- remain useful after refresh, navigation, tab switching, and temporary network loss;
- be lightweight enough for low-cost hosting and ordinary laptops/phones; and
- express the Editorial Swiss / Living Draft visual system consistently.

It must not:

- change or auto-chain an agent;
- change authentication or entitlement rules;
- replace the Preview runtime/gateway;
- merge development fixtures into the product;
- expose model/provider/storage internals;
- invent percentages, ETAs, logs, reasoning, versioning, publishing, or unsupported
  agent controls; or
- remove the temporary Code Generator development harness while it remains needed.

## 2. Canonical frontend model

### 2.1 Product nouns

Use these nouns consistently in code and copy:

| Product noun | Meaning | Do not call it |
| --- | --- | --- |
| Portfolio | The person's durable work and eventual site | Project list, workspace collection |
| Stage | One ordered product phase | Agent swarm, model step |
| Artifact | A reviewable stage output | Chat answer, raw response |
| Run | One durable execution behind a stage | Conversation |
| Preview | The currently promoted verified generated site | Published site, production, live website |
| Handoff | An explicit user action that starts the next stage | Automatic continuation |
| Attention | A durable state requiring a supported user action | Generic error toast |

Implementation identifiers may retain backend names inside adapters. Product
components and copy use the vocabulary above.

### 2.2 Normalized stage vocabulary

Every backend-specific stage adapter outputs one of:

```ts
type StageState =
  | "locked"
  | "available"
  | "working"
  | "input"
  | "review"
  | "attention"
  | "complete"
  | "unsupported";
```

Definitions:

| State | Meaning | Main UI |
| --- | --- | --- |
| `locked` | An upstream gate is not complete | Quiet future milestone; no disabled action |
| `available` | The stage can be started explicitly | Handoff/start panel |
| `working` | Server-backed work is active | Semantic milestone surface |
| `input` | The user can supply an answer or source | Conversation/question surface |
| `review` | A durable artifact can be revised or approved | Artifact surface |
| `attention` | Work stopped and a supported recovery is available | Attention panel |
| `complete` | Stage completion boundary is confirmed | Read-only artifact plus next handoff |
| `unsupported` | A required unknown status/shape was received | Safe recovery panel and refetch |

The `unsupported` state must never be normalized to complete or available. It is a
forward-compatibility safety valve while agent contracts evolve.

### 2.3 Journey view model

```ts
type JourneyStageId =
  | "discover"
  | "content"
  | "design"
  | "prepare"
  | "generate"
  | "preview";

interface JourneyStageVM {
  id: JourneyStageId;
  ordinal: number;
  label: string;
  state: StageState;
  statusText: string;
  attentionCount: number;
  isSelectable: boolean;
  completedAt?: string;
}

interface PortfolioStudioVM {
  sessionId: string | null;
  sessionRevision: number | null;
  readOnly: boolean;
  currentStage: JourneyStageId;
  recommendedView: "start" | "work" | "artifact" | "progress" | "preview";
  journey: JourneyStageVM[];
  connection: "confirmed" | "checking" | "stale" | "offline";
  lastConfirmedAt?: string;
}
```

The adapter derives `currentStage` from durable gates and active work, not from the
last tab the user selected. URL selection can inspect earlier completed stages but
cannot unlock a future one.

## 3. Route and navigation contract

### 3.1 Server routes retained

| Route | Purpose | Frontend behavior |
| --- | --- | --- |
| `/` | Auth controller entry | Resolve existing provider session, then replace to the safe destination |
| `/sign-in` | Google sign-in | Show the focused sign-in experience |
| `/auth/callback` | Provider callback | Resolve once; prevent callback loops and duplicate navigation |
| `/access-not-approved` | Provider/admission denial | Safe explanation plus account-switch/sign-out |
| `/account-unavailable` | Suspended, deleted, capacity, or unavailable account | Safe terminal/retry behavior based on server code |
| `/onboarding` | One-time username claim | Inline validation and server-authoritative completion |
| `/app` | Normal-user home and portfolio studio | Resolve posture from `/me` and portfolio state |
| `/admin` | Existing administrator console | Remains separate from the normal-product redesign scope |

Development-only routes such as Build Preparation fixtures and the Code Generator
control room remain independently gated. The normal product never links to them.

### 3.2 `/app` URL state

Use query parameters rather than a client router:

```text
/app?stage=discover&view=work
/app?stage=content&view=artifact
/app?stage=preview&view=preview&route=%2Fprojects
```

Allowlist:

- `stage`: `discover`, `content`, `design`, `prepare`, `generate`, `preview`;
- `view`: `start`, `work`, `artifact`, `progress`, `preview`;
- `route`: a path present in the active promoted route contract; and
- `viewport`: `fit`, `mobile`, `tablet`, `desktop`.

Rules:

1. Unknown keys may remain in the address bar but do not affect product behavior.
2. An invalid allowed key is removed with `history.replaceState`.
3. A locked stage is replaced by the current reachable stage.
4. `route` is ignored unless Preview is active and it matches the promoted manifest.
5. No portfolio text, artifact content, token, error message, run ID, or provider data
   enters the URL.
6. Selecting a stage/view uses `pushState`; normal state reconciliation uses
   `replaceState` to avoid polluting browser history.
7. `popstate` revalidates the URL against the latest server state.
8. A refresh reconstructs the same safe view from URL plus server state.

### 3.3 Destination resolver

After one authorized `GET /api/v1/me`:

```text
unauthenticated              -> /sign-in
provider/access denied       -> /access-not-approved
suspended/deleted/unavailable-> /account-unavailable
onboarding_required          -> /onboarding
admin opening /admin         -> /admin
normal onboarded user        -> /app
normal user opening /admin   -> /app
```

An intended destination is accepted only when it is a reviewed same-origin path.
Reject scheme-relative URLs, absolute URLs, encoded protocol tricks, backslashes,
control characters, and auth callback recursion. Use `location.replace` for auth
resolution so the browser Back button does not re-enter transient callback states.

## 4. Existing API inventory and frontend use

All product API requests use the existing `/api/v1` prefix and bearer-authenticated
request boundary. The server remains authoritative. The frontend never calls model
providers, object storage, or the Preview artifact store directly.

### 4.1 Identity and portfolio

| Method and path | Request | Frontend use |
| --- | --- | --- |
| `GET /me` | None | Identity, role, onboarding, entitlement, read-only and action eligibility |
| `PUT /me/username` | `{ username }` | Complete one-time onboarding |
| `POST /sessions` | `{ name?: string }` | Create the one allowed portfolio when entitlement permits |
| `GET /sessions` | `limit` query | Admin/development needs; normal product should prefer entitlement-bound ID |
| `GET /sessions/{session_id}` | None | Session identity, revision, coarse current-state projection |

The normal product does not ask a user to name a project before they can begin. If
the API requires a session name, use a calm default product name and offer no fake
project-management surface. A naming feature can be designed later if it becomes a
real user need.

### 4.2 Discovery

| Method and path | Request | Result/use |
| --- | --- | --- |
| `GET /sessions/{id}/discovery` | None | Canonical Discovery projection and related jobs |
| `POST .../discovery/start` | `{ message, document_text, goal, model_profile? }` | Start/restart supported intake operation |
| `PUT .../discovery/answers` | `{ complete, answers[] }` | Save current answers; each answer carries question ID, mode, and value |
| `POST .../discovery/revise` | `{ revision_request }` | Request a brief revision |
| `POST .../discovery/approve` | Empty object | Approve the brief |

Normal product policy:

- never expose `model_profile`;
- do not offer file upload until an approved extraction contract exists;
- allow plain text paste for source material;
- show adaptive questions one at a time while preserving completed answers;
- keep the user's local draft through a recoverable conflict; and
- render the brief as a safe document, not raw Markdown/JSON.

### 4.3 Content Architect

| Method and path | Request | Result/use |
| --- | --- | --- |
| `GET /sessions/{id}/content-architect` | None | Canonical content artifact/status |
| `POST .../content-architect/start` | `{ preferences, model_profile? }` | Explicitly start or supported retry |
| `POST .../content-architect/revise` | `{ revision_request }` | Rebuild from a natural-language revision |
| `POST .../content-architect/approve` | Empty object | Approve content artifact |

Normal product sends an empty or explicitly supported `preferences` object. It does
not expose model profile or fabricate preference controls that the product has not
defined.

### 4.4 Visual Design Director

| Method and path | Request | Result/use |
| --- | --- | --- |
| `GET /sessions/{id}/visual-design-director` | None | Canonical visual-direction artifact/status |
| `POST .../visual-design-director/start` | `{ preferences, model_profile? }` | Explicitly start or supported retry |
| `POST .../visual-design-director/revise` | `{ revision_request }` | Rebuild from a natural-language revision |
| `POST .../visual-design-director/approve` | Empty object | Approve visual direction |

The frontend describes visual direction in user language. It may expose named page
intentions, palette/type/resource intentions, and important interactions when they
exist; it must not expose internal candidate lookup or model operations.

### 4.5 Build Preparation

| Method and path | Request | Result/use |
| --- | --- | --- |
| `GET /sessions/{id}/build-preparation` | None | Status, staleness, safe warnings/events, package eligibility |
| `POST .../build-preparation/start` | `{ model_profile?: null }` | Explicitly start preparation |
| `POST .../build-preparation/regenerate` | Empty or allowed start body | Supported recovery when server allows it |
| `GET .../build-preparation/download` | None | Existing technical artifact download; omit from normal product initially |

The normal product neither exposes pack contents nor names storage vendors. The
download endpoint remains available to authorized development/technical workflows
but is not a primary creator action.

### 4.6 Code Generator

| Method and path | Request | Result/use |
| --- | --- | --- |
| `GET /sessions/{id}/code-generator` | None | Production generation status, safe progress, retry data, active Preview |
| `POST .../code-generator/start` | Empty object plus `Idempotency-Key` | Bind eligible prepared artifact and explicitly start generation |
| `POST .../code-generator/regenerate` | Empty object plus `Idempotency-Key` | Existing capability; normal entitlement usually suppresses it |
| `POST .../code-generator/retry` | Empty object plus `Idempotency-Key` | Retry the supported failed stage when entitlement permits |

Only these production session endpoints are integrated. Do not call the standalone
development-harness run/event/file/plan endpoints from `/app`.

### 4.7 Response and error envelope

Stage responses contain:

- `session_id`;
- `session_revision`;
- one stage projection; and
- related `jobs` where exposed.

Errors use:

```json
{
  "error": {
    "code": "STABLE_CODE",
    "message": "Safe human-readable message.",
    "details": {},
    "request_id": "correlation reference"
  }
}
```

Frontend rules:

- prefer a reviewed product message for known codes;
- use the server message only when it is already safe and useful;
- reveal `request_id` under “Technical reference” for support;
- never assume `details` is safe for primary display;
- never show a stack trace, provider payload, storage path, or raw response; and
- preserve the last confirmed view during recoverable request failure.

## 5. Bootstrap and data-loading sequence

### 5.1 Auth shell

1. Server renders the lightweight shell and public runtime config.
2. Show the static Living Draft mark and “Checking your session…”; do not render
   private placeholders that reveal previous work.
3. Restore/resolve the provider session.
4. Make one authorized `GET /api/v1/me`.
5. Resolve the safe route from account state.
6. Stop all pending auth requests/listeners before navigating.

If auth resolution fails, remain in the auth shell and offer retry. Do not bounce
between `/`, `/sign-in`, and `/auth/callback`.

### 5.2 `/app` shell

1. Render stable public chrome, then resolve auth before private content mounts.
2. Read entitlement from `/me`.
3. If no portfolio exists and creation is allowed, render `StartSurface` without
   calling stage APIs.
4. If a portfolio ID exists, fetch `GET /sessions/{id}`.
5. Derive a coarse reachable/current stage from the session projection.
6. Fetch the canonical current-stage endpoint and the nearest approved artifact
   needed for context.
7. If an active Preview may exist, fetch Code Generator state.
8. Normalize responses, validate URL selection, and reveal the selected surface.
9. Start one visibility-aware poll only if the normalized current stage is working.

Independent stage GETs may be performed concurrently after session ownership is
confirmed, but do not request all stages blindly on every refresh. The journey rail
can use coarse session projection until a selected stage is loaded canonically.

### 5.3 No blank-screen rule

Loading boundaries preserve the smallest stable parent:

- auth resolution keeps auth composition visible;
- stage loading keeps shell and journey visible;
- artifact reload keeps its heading/measure visible;
- Preview loading keeps toolbar/frame dimensions and, when valid, the old verified
  frame visible; and
- reconnect keeps last confirmed content visible with a non-modal banner.

Skeletons may represent known document lines or controls. Do not use a generic grid
of shimmering cards.

## 6. Adapter contracts

### 6.1 Adapter rules shared by all stages

Each adapter is a pure function with fixture tests. It must:

- accept `unknown`, validate the minimal required envelope, and return a discriminated
  success or unsupported result;
- ignore unknown optional fields;
- never mutate the raw response;
- map backend values to product vocabulary in one place;
- output safe text, IDs, times, and action eligibility;
- preserve an opaque raw revision/reference only where a later request requires it;
- sort stable lists deterministically when backend order is not part of the contract;
- handle absent/empty partial projections; and
- fail closed on a new required status.

Components do not branch on raw enum strings.

### 6.2 Discovery status map

| Backend status | Normalized state | Product copy / action |
| --- | --- | --- |
| `not_started` | `available` | “Begin with your story” / start |
| `questions_queued` | `working` | “Preparing the right questions” |
| `questions_running` | `working` | “Understanding your material” |
| `questions_ready` | `input` | Show current unanswered question |
| `answers_in_progress` | `input` | Continue current question set |
| `brief_running` | `working` | “Shaping your portfolio brief” |
| `brief_review` | `review` | Brief, revise, approve |
| `approved` | `complete` | Read-only approved brief plus Content handoff |
| `needs_attention` | `attention` | Safe error plus supported retry/recovery |
| anything else | `unsupported` | “This stage returned a newer state. Refresh to continue.” |

Question adapter rules:

- preserve server order;
- identify answers by stable question ID;
- use server-supplied kind/options/skip capability;
- never invent an “Other” option;
- do not mark a question complete from local input alone; and
- if the current question disappears after reconciliation, retain the local text as
  an unsent draft and explain the state change.

### 6.3 Content and Design status maps

| Backend status | Normalized state | Product behavior |
| --- | --- | --- |
| `not_started` | `available` only if upstream gate is approved; otherwise `locked` | Explicit start |
| `build_running` | `working` | Stage-specific semantic progress |
| `content_review` / `design_review` | `review` | Artifact, revision composer, approval |
| `approved` | `complete` | Read-only artifact and next handoff |
| `needs_attention` | `attention` | Safe error and supported restart/retry |
| anything else | `unsupported` | Fail closed and refetch |

Artifact adapters produce section IDs, headings, safe body content, route summaries,
warnings that matter to the user, and approval metadata. Internal reasoning,
provider calls, prompt modes, hashes, and catalogue lookup details are omitted.

### 6.4 Build Preparation map

Top-level status:

| Backend status | Normalized state | Product behavior |
| --- | --- | --- |
| `not_started` | `available` only when Content and Design are approved | Explain preparation and start |
| `running` | `working` | Show grouped preparation milestones |
| `ready` and eligible/not stale | `complete` | Explain verified handoff and allow Generate |
| `ready` but stale/ineligible | `attention` | Explain that approved inputs changed; show supported regeneration |
| `needs_attention` | `attention` | Show safe failure and regenerate only when allowed |
| anything else | `unsupported` | Safe fallback |

Current internal stage strings remain adapter-only. Group them defensively:

| Observed internal stage/event family | Product milestone |
| --- | --- |
| `stage_0` | Checking the approved plan |
| `stage_1`, `stage_2` | Resolving portfolio materials |
| `stage_3`, `stage_4`, `phase_2` | Compiling the build context |
| `materialize`, `stage_5`, `package`, `artifact_storage`, `phase_3` | Packaging and verifying the handoff |
| unknown while `running` | Preparing the build package |

This grouping is an observational compatibility layer, not a promise that internal
names will remain stable. Completed milestones must come from explicit events or
durable fields; do not infer completion only because a later polling response is
slow.

The adapter may expose:

- current milestone;
- completed product milestones;
- route count when reliable;
- safe warnings with clear impact;
- artifact expiry/staleness when meaningful; and
- handoff eligibility.

It omits resource candidates, query/provider receipts, local paths, object keys,
hashes, model calls, staging-tree contents, and raw events.

### 6.5 Code Generator map

| Backend status | Normalized state | Product milestone / behavior |
| --- | --- | --- |
| `not_started` | `available` only when prepared and entitled | Start generation |
| `queued` | `working` | Waiting for the generation lane |
| `planning` | `working` | Planning the portfolio build |
| `acquiring` | `working` | Preparing approved resources |
| `generating` | `working` | Building portfolio routes |
| `verifying` | `working` | Checking build and responsive behavior |
| `preview_pending` | `working` | Finalizing the verified Preview |
| `ready` with valid active Preview | `complete` | Open Preview |
| `ready` without usable active Preview | `attention` | Preview unavailable; refetch/reconnect, never claim success visually |
| `needs_attention` | `attention` | Preserve old Preview and expose retry only if entitled |
| anything else | `unsupported` | Safe fallback |

The production response contains additional planning, source, attempt, issue,
quality, trace, duration, storage-readiness, and advisory fields. Product exposure
is intentionally narrower:

- status and current semantic milestone;
- safe issue/advisory summaries that change a user's action;
- retry availability from `/me` plus server state;
- elapsed time as neutral context, never an ETA;
- active verified Preview route/receipt data; and
- a support reference under details.

Do not show design fingerprint, model profile, source files, work graph, provider
data, storage readiness, raw quality projection, internal attempt IDs, or stage
durations as a dashboard.

### 6.6 Preview adapter

Output only a validated structure:

```ts
interface PreviewVM {
  state: "absent" | "opening" | "ready" | "stale" | "unavailable";
  stableOrigin?: string;
  stableBaseUrl?: string;
  routes: Array<{ id: string; path: string; label: string }>;
  selectedPath?: string;
  promotedAt?: string;
  isPreviousVerifiedResult: boolean;
}
```

Validation requirements:

- origin must match configured reviewed Preview origin exactly;
- scheme must follow environment policy;
- path must use the stable opaque host/mount contract;
- selected path must be in the promoted route contract;
- fragments and external URLs from the generated document do not mutate host state;
- invalid receipt data yields `unavailable`, not a navigable URL; and
- no bearer token, session data, or account information is appended to the frame URL.

## 7. Action eligibility and mutation choreography

### 7.1 Single source of truth

The visibility of a mutation requires both:

1. the normalized stage state permits the action; and
2. the `/me` entitlement projection does not forbid it.

The server makes the final decision. A visible action can still receive a conflict
if state changed between read and write; the UI must reconcile rather than override.

### 7.2 Action matrix

| Situation | Primary action | Secondary action |
| --- | --- | --- |
| No portfolio, creation allowed | “Start my portfolio” | None |
| Discovery available | “Begin discovery” | None |
| Discovery question | “Save and continue” or “Create my brief” based on server mode | Back to prior answered question where safe |
| Brief review | “Approve brief” | “Request a revision” |
| Discovery approved | “Continue to content” | Review brief |
| Content review | “Approve content” | “Request a revision” |
| Content approved | “Continue to design” | Review content |
| Design review | “Approve direction” | “Request a revision” |
| Design approved | “Prepare the build” | Review direction |
| Preparation ready | “Generate my portfolio” | Review preparation summary |
| Generation ready | “Open Preview” | Review journey |
| Recoverable failure | Specific “Retry…” action | Review technical reference |
| Read-only success | “Open Preview” | Review approved artifacts |

There is one visually primary action per state. Approval wording includes the object
being approved; generic “Continue” is reserved for a handoff explanation, not a
consequential approval.

### 7.3 Mutation lifecycle

1. Validate only known client constraints; server validation remains authoritative.
2. Preserve the user's entered text before starting the request.
3. Disable only conflicting controls, not the whole shell.
4. Use a stable pending label such as “Approving brief…” rather than a spinner alone.
5. Create/reuse an idempotency key for Code Generator mutations and any other
   endpoint that formally honors one.
6. On 2xx/202, store the returned projection and immediately reconcile canonical
   state as required; HTTP acceptance alone is not completion.
7. Broadcast an opaque state invalidation after confirmed mutation.
8. Move focus only when the user initiated a view change or validation requires it.
9. On ambiguous network failure, GET canonical state before offering to resubmit.
10. On conflict, keep the draft, refetch, explain, and require explicit resubmission.

Store an unresolved idempotency key in `sessionStorage` under a session/action-scoped
name. Remove it only after reconciliation confirms the action or the user explicitly
starts a new logical action. Never store the request content beside it.

### 7.4 Optimistic behavior

Allowed:

- local textarea changes;
- selected completed stage/view;
- disclosure state;
- viewport selection; and
- immediate button press feedback.

Not allowed:

- marking an answer saved;
- advancing a stage;
- marking an artifact approved;
- claiming work started/completed;
- replacing active Preview; or
- declaring the portfolio read-only.

Those states require server confirmation.

## 8. Component contracts

### 8.1 `AppShell`

Responsibilities:

- render brand mark, journey region, selected surface, account menu, and connection
  banner;
- preserve shell geometry during stage loading;
- clear all private child content on terminal auth failure/sign-out;
- own surface and shell error boundaries; and
- expose a skip link to the current work surface.

It does not fetch stage data directly; it consumes store state and dispatches typed
actions.

### 8.2 `JourneyRail`

Inputs: normalized journey, current selection, read-only state.

Behavior:

- ordered list with visible numbers and labels;
- completed and current stages are selectable;
- future locked stages are descriptive, not fake disabled buttons;
- an attention stage gets icon plus text, not color alone;
- horizontal compact rail on medium widths; vertical editorial margin on wide
  screens; and
- a single current-stage selector on mobile opens a bottom sheet/list.

The living line animates only when a new durable transition is detected during the
current page lifetime.

### 8.3 `StartSurface`

Content:

- concise thesis: turn experience into a verified portfolio;
- one primary “Start my portfolio” action;
- a plain-language six-stage overview; and
- reassurance that nothing publishes automatically.

No template gallery, project naming form, model selector, testimonial carousel,
pricing block, or fake example dashboard.

### 8.4 `ConversationSurface`

Responsibilities:

- render prior user/assistant turns with strong speaker semantics;
- show only the current actionable question prominently;
- render kind/options/help/skip behavior from the server;
- use one persistent composer whose label names the current task;
- preserve unsent input across safe rerenders and conflicts; and
- scroll only after the user's own submission or deliberate navigation.

The transcript is not an `aria-live` region. Only the meaningful state transition is
announced through `StatusAnnouncer`.

Composer details:

- ordinary `<textarea>` with visible label;
- grows to a bounded maximum, then scrolls internally;
- `Enter` adds a newline; a clearly documented modifier may submit on desktop;
- composition/IME input never submits mid-composition;
- paste remains plain text;
- no attachment, image, voice, URL-fetch, or command controls without contracts; and
- if a server length limit becomes public, reflect it; do not invent a client-only
  maximum that can discard source material.

### 8.5 `ArtifactSurface`

Responsibilities:

- show artifact title, approval/revision state, readable sections, section
  navigation, and safe metadata;
- render the bounded supported Markdown subset as DOM nodes;
- retain headings and section anchors across refresh;
- collapse secondary metadata before primary content; and
- expose approved artifacts read-only after handoff.

On wide screens, a narrow section index may sit beside a 68-74 character reading
measure. On small screens, the index becomes a “Sections” disclosure. Avoid nested
cards; use sheets, rules, and whitespace.

### 8.6 `RevisionComposer`

- appears only in `review` or a specifically supported recovery state;
- labels the artifact it will revise;
- explains that revision reruns that stage and may replace the current draft;
- keeps a local unsent draft in `sessionStorage` only when necessary;
- clears the draft after confirmed acceptance; and
- never appears during Build Preparation or Code Generator because those endpoints
  do not accept natural-language steering.

### 8.7 `HandoffPanel`

Includes:

- what was completed;
- what the next stage uses;
- what the next stage will do in user language;
- a reminder that starting it is explicit; and
- one outcome-named primary action.

It never auto-counts down or auto-starts.

### 8.8 `ProgressSurface`

Inputs: stage label, product milestones, current safe event, elapsed neutral context,
and leave/return explanation.

Behavior:

- completed milestone: check and completion label;
- current: active marker and concise present-tense description;
- future: quiet label;
- unknown backend substage: retain current known milestone and generic safe copy;
- no percentage, ETA, token stream, raw log, or animated skeleton replacing the
  whole screen; and
- secondary approved-artifact summary remains available.

### 8.9 `AttentionPanel`

Must answer:

1. What stopped, in safe product language?
2. What work is preserved?
3. Is an older verified Preview still available?
4. What exact recovery action is supported?
5. What reference can support use if recovery fails?

Unknown or non-retryable failures offer refresh/reconnect/support guidance rather
than a button that repeats a potentially destructive operation.

### 8.10 `PreviewSurface`

Toolbar contains only:

- route selector sourced from promoted routes;
- `fit`, `mobile`, `tablet`, and `desktop` viewport buttons;
- refresh; and
- open verified Preview in a new tab.

Frame behavior:

- title names the user's portfolio Preview;
- iframe uses the reviewed sandbox/allow policy from Preview architecture;
- host and frame remain separate origins;
- toolbar remains stable while the frame opens;
- load timeout produces a Preview-specific recovery without changing generation
  status;
- viewport buttons change only product-frame width, not generated CSS;
- a previous verified frame remains visible while a new promoted URL is being
  confirmed;
- the frame's box (CSS `width`/`height` or `aspect-ratio` matching the selected
  profile) is reserved before the iframe's `load` event, so layout never shifts
  once content arrives; and
- when the profile does not fit the available space, scale visually via a
  fixed-size wrapper (`overflow: hidden`) plus `transform: scale()` on the
  iframe — never by resizing the iframe outside the four verified profiles.

There is no edit, inspect, screenshot, publish, share, history, device chrome,
address-bar imitation, arbitrary URL entry, or source toggle.

### 8.11 `DetailsSheet`

Contains secondary, safe information only:

- approval/completion time;
- selected safe warnings;
- short activity history;
- request/trace reference when useful; and
- explanation of Preview versus publishing.

It must not become a dumping ground for backend JSON. On mobile it uses a modal
sheet/dialog; on desktop it can be a non-modal side sheet.

### 8.12 `ConnectionBanner` and `StatusAnnouncer`

`ConnectionBanner` is persistent while state is uncertain and disappears silently
after recovery. It does not create a toast for every poll.

`StatusAnnouncer` has one polite live region and announces only:

- user submission accepted;
- new actionable question ready;
- artifact ready for review;
- approval confirmed;
- stage needs attention;
- Preview ready/unavailable; and
- connection restored after the interface was explicitly stale/offline.

It never announces timers, every event, every poll, or decorative animation.

## 9. Screen-level content specification

### 9.1 Auth resolving

- Eyebrow: `ORYXENAI / PORTFOLIO STUDIO`
- Heading: `Opening your studio`
- Status: `Checking your session...`
- After a longer network wait: `Connecting to the service. This can take a little
  longer after inactivity.`
- Action after a real failure: `Try again`

Do not say the AI is “thinking.”

### 9.2 Sign-in

- Heading: `Your work, shaped into a portfolio.`
- Supporting copy: one sentence about guided discovery, deliberate content/design,
  and a verified Preview.
- Primary action: `Continue with Google`
- Trust copy: `Nothing is published automatically.`
- Secondary account recovery/switching copy only where the auth controller supports
  it.

### 9.3 Onboarding

- Heading: `Choose how you appear in OryxenAI`
- Explain that the username is one-time if that remains server policy.
- Visible requirements must mirror server validation.
- Primary action: `Save username`
- Server conflicts remain inline; focus the error and retain the entered value.

### 9.4 First portfolio

- Heading: `Begin with what you want your portfolio to say.`
- Explain that existing resume/bio text can be pasted, but a polished input is not
  required.
- The primary start action creates the entitlement-bound portfolio, then takes the
  user to Discovery.
- No misleading file uploader until text extraction is supported end to end.

### 9.5 Returning portfolio

Lead with the most relevant fact:

| Durable situation | Heading/action |
| --- | --- |
| Current question | `Continue discovery` |
| Artifact awaiting approval | `Review your [brief/content/direction]` |
| Stage running | `[Stage] is in progress` |
| Attention | `[Stage] needs your attention` |
| Prepared | `Your build handoff is ready` |
| Preview ready | `Your verified Preview is ready` |
| Read-only success | Preview first, with `Review the journey` secondary |

Avoid generic “Welcome back” as the only hierarchy.

### 9.6 Approval confirmation

Use a compact inline confirmation, not a blocking browser confirm:

- object being approved;
- consequence: the next stage consumes this approved snapshot;
- assurance: the next stage will not start automatically; and
- actions: `Approve [object]` and `Keep reviewing`.

If server policy makes approval irreversible, say so plainly. Do not imply
reversibility that is not available.

### 9.7 Completion

- Heading: `Your portfolio is ready to preview.`
- Clarify: verified Preview, not publicly published.
- Keep journey/artifacts accessible.
- If read-only, state that the completed portfolio is preserved and explain any
  future change path only when the product supports one.
- No confetti, sound, artificial score, or forced new tab.

## 10. Error taxonomy and recovery

### 10.1 Frontend categories

| Category | Examples | Surface | Recovery |
| --- | --- | --- | --- |
| Authentication | required, invalid, expired | Clear private shell, auth page | One refresh attempt then sign-in |
| Admission/account | not approved, suspended, deleted, capacity | Dedicated safe account page | Switch/sign out or documented owner action |
| Onboarding | username taken/locked/invalid | Inline field error | Edit if allowed; otherwise safe explanation |
| Authorization/ownership | unauthorized session, fence rejected | Replace private content | Refetch `/me`; route to allowed destination |
| Entitlement/read-only | variant locked, binding conflict, read-only | Stage/action panel | Reconcile and suppress forbidden mutation |
| Validation | request field invalid | Inline near initiating control | Retain data and correct |
| Concurrency | session revision/CAS conflict | Persistent stage notice | Refetch, preserve draft, explicit resubmit |
| Provider capacity/credit | stable model-provider failure | Attention panel | Retry only if server/entitlement allows |
| Worker/stage failure | needs-attention projection | Stage attention panel | Supported retry/regenerate |
| Network/offline | fetch failure/timeout | Connection banner | Backoff and manual retry |
| Preview transport | iframe load/handshake failure | Inside Preview frame | Refresh/reconnect/open new tab |
| Unsupported response | new status or malformed required shape | Surface boundary | Refetch/reload and technical reference |
| Client render | component exception | Surface or shell boundary | Reload surface/application safely |

### 10.2 Known auth/product error behavior

| Stable code family | User-facing response |
| --- | --- |
| `AUTH_REQUIRED`, `AUTH_INVALID` | Stop private polling, clear private render state, restore once, then sign in |
| `AUTH_PROVIDER_UNAVAILABLE`, `AUTH_RATE_LIMITED` | Keep auth shell, explain temporary availability, offer bounded retry |
| `ACCESS_NOT_APPROVED` | Access-not-approved route with account switch/sign-out |
| `ACCOUNT_SUSPENDED`, `ACCOUNT_DELETED` | Account-unavailable route; no portfolio flash |
| `ADMIN_REQUIRED` | Normal user returns to `/app` |
| `ONBOARDING_REQUIRED` | `/onboarding`, preserving safe intended destination |
| `USERNAME_TAKEN` | Inline conflict and focus; retain username |
| `USERNAME_LOCKED` | Explain one-time state; do not keep editable form |
| `USER_CAPACITY_REACHED` | Account-unavailable capacity explanation; no retry loop |
| `GENERATION_VARIANT_LOCKED`, `PORTFOLIO_READ_ONLY` | Reconcile `/me`, hide mutation, keep Preview/artifacts |
| `ENTITLEMENT_BINDING_CONFLICT`, `AUTHORIZATION_FENCE_REJECTED` | Fail closed, refetch identity/session, show support reference if persistent |
| `MODEL_PROVIDER_CREDIT_EXHAUSTED` | Attention state with honest availability language; retry only if authorized |

Known stage-specific codes should be mapped beside their adapters. Unknown codes use
safe server message plus reference only if the message passes the reviewed response
contract.

### 10.3 Timeout policy

Do not label a durable run failed because one HTTP request timed out. Distinguish:

- request timeout: connection uncertain; keep last state and GET again;
- no stage change for a long time: continue showing working if server still says
  working, with elapsed neutral context;
- durable needs-attention: show stage recovery; and
- Preview load timeout: Preview transport issue, not generation failure.

## 11. Polling, reconciliation, and multi-tab behavior

### 11.1 Coordinator policy

- Immediate fetch on subscription.
- One in-flight request per resource key.
- Working stage cadence: approximately 1.5 seconds while visible.
- Failure backoff: approximately 1.5, 3, 6, and 12 seconds, capped at 15 seconds,
  with small jitter.
- Honor a valid `Retry-After` before local scheduling.
- Stop at `review`, `complete`, `attention`, or `unsupported` until a user/refetch
  action requires more.
- Cancel scheduled polls when hidden; do not cancel a response already being
  committed solely because visibility changed.
- On visibility return, refetch `/me`, session, active stage, and Code Generator
  state if a Preview may exist.
- Abort on sign-out, session change, or surface teardown.

### 11.2 Stale-response defense

Each request records resource key and generation counter. Commit the response only
if it is still the latest request for that key. Prefer the greater session/run
revision when comparable. Never let a slow earlier poll overwrite the response from
a confirmed mutation.

### 11.3 Cross-tab invalidation

Use one same-origin `BroadcastChannel`. Messages include only:

```ts
{ type: "state-invalidated", sessionId: string, at: number }
```

A visible receiving tab refetches. A hidden tab waits for visibility. A tab with an
unsent draft keeps it but marks it as based on an older revision. If the browser
lacks `BroadcastChannel`, focus/visibility refetch is the complete fallback.

## 12. Responsive specification

### Wide desktop (`>= 1280px`)

- Vertical journey rail in the editorial margin.
- Main work region uses the largest available width.
- Artifact measure remains capped; unused width may hold section index/details.
- Preview can dominate the full work region with toolbar above.

### Laptop (`900-1279px`)

- Compact horizontal journey above content or narrow vertical rail where space
  remains comfortable.
- One dominant surface plus optional overlay/details sheet.
- Never force conversation, artifact, activity, and Preview into simultaneous
  columns.

### Tablet (`600-899px`)

- Horizontal scroll-free journey summary or stage selector.
- Full-width artifact/conversation surface.
- Details become a sheet.
- Preview toolbar wraps by logical groups without shrinking hit targets.

### Mobile (`< 600px`)

- Top bar: brand, current stage, account/menu.
- Stage list opens as a bottom sheet or dedicated overlay.
- Sticky action region only when it does not cover input/content.
- Artifact section navigation becomes a disclosure.
- Preview defaults to `fit`; viewport presets may create an internally scrollable
  frame wider than the device only when clearly indicated.
- Full start, answer, review, approve, monitor, and Preview tasks remain possible.
- Development inspectors and source editing remain absent.

### Height and input edge cases

- Use dynamic viewport units with safe fallback.
- Respect safe-area insets for bottom actions.
- Do not lock the page behind `100vh` when the mobile keyboard opens.
- Keep current question and send action reachable after zoom.
- Preview frame and toolbar must not trap vertical page scroll.

## 13. Accessibility acceptance

### Semantics and focus

- One `<main>` with a programmatic heading matching the current surface.
- Landmarks for header/navigation/main/complementary regions.
- Journey is an ordered list; selected completed stages are links/buttons with clear
  accessible names.
- Native labels and descriptions for every form field.
- Inline errors linked with `aria-describedby`; invalid field receives focus after
  failed submission.
- Dialogs have heading, initial focus, Escape/close behavior, and focus return.
- No positive `tabindex`, keyboard trap, or hover-only action.

### Dynamic state

- `aria-busy` is scoped to the affected surface, not the entire app during every
  poll.
- One polite announcer; no live transcript/activity region.
- Focus does not jump when a background stage changes.
- When a user action opens a new stage, focus the new page heading.
- When an artifact arrives in the background, announce availability and leave focus
  in place.

### Visual and motion

- Text/control contrast meets WCAG AA at minimum.
- Focus indicator is at least 2 px, high contrast, and not removed by radius/overflow.
- Status always includes text/icon/structure in addition to color.
- Layout works at 200% zoom and with text-only zoom.
- Forced-colors mode keeps borders, focus, selected state, and controls visible.
- `prefers-reduced-motion: reduce` removes travel, sweep, smooth scroll, and loading
  stroke animation; state changes remain immediate and understandable.
- Touch targets are at least 44 by 44 CSS pixels for primary interactive controls.

### Preview caveat

The host toolbar/frame must pass these checks independently. The generated site must
have its own verification/accessibility criteria; host compliance cannot be used as
evidence for iframe content compliance.

## 14. Performance and asset acceptance

### Budgets

| Budget | Required limit |
| --- | --- |
| Auth initial JavaScript | <= 50 kB compressed; target <= 35 kB |
| `/app` initial JavaScript | <= 90 kB compressed |
| Any lazy stage chunk | <= 50 kB compressed |
| Initial product CSS | <= 35 kB compressed; target <= 25 kB |
| Initial self-hosted display font | <= 50 kB WOFF2 |
| Product-shell raster images | 0 required bytes |
| Decorative inline SVG | <= 4 kB for the main mark |
| LCP at p75 | <= 2.5 seconds |
| INP at p75 | <= 200 ms |
| CLS at p75 | <= 0.1 |
| Main-thread long task caused by product UI | No recurring task above 50 ms |

The slightly wider hard CSS/auth caps allow build variance; the lower targets guide
implementation. Any exception needs measured evidence and review.

### Required techniques

- Preact and stage code split at meaningful surface boundaries.
- No client router, component framework, motion library, icon package, code editor,
  syntax highlighter, canvas, WebGL, Lottie, or runtime CSS-in-JS.
- Self-host one display-font subset with `font-display: swap`; system font for UI.
- Inline/checked-in SVG icons only.
- `content-visibility` for long offscreen artifact sections where supported.
- Parse artifact content only when its revision changes.
- Stable dimensions for font fallback, Preview, marks, and loading surfaces.
- Stop scheduled work in hidden tabs.
- Serve hashed compiled assets; do not hand-edit build output.

### Measurement gates

At minimum measure:

- cold signed-out auth route;
- restored-session `/app` route;
- a long Discovery transcript;
- the largest representative Content and Design artifact;
- a 30-minute active progress session;
- Preview with each viewport mode; and
- mobile keyboard plus slow/cold API behavior.

Bundle size must be checked in CI. Browser performance should be recorded on a
representative mid-range device or throttled profile, not inferred from a desktop
development machine.

## 15. Styling implementation map

### 15.1 Theme layers

```text
tokens.css       -> color, type, spacing, radius, motion, z-index
reset.css        -> small predictable element baseline
shell.css        -> app/auth layout and responsive regions
components.css   -> component-owned class blocks
utilities.css    -> only a tiny reviewed set for accessibility/layout
print.css        -> artifact readability if print is retained as a useful browser action
```

Avoid a general utility framework. Component class names should describe product
roles such as `.journey-rail`, `.artifact-sheet`, and `.handoff-line`, not visual
accidents such as `.rounded-card-3`.

### 15.2 Visual conformance checklist

- Canvas, paper, ink, graphite, rule, signal, and semantic colors come only from
  tokens.
- Signal blue remains the only decorative accent.
- Ordinary sections use whitespace/rules, not independent elevated cards.
- Display serif appears only in major thesis/artifact transitions.
- UI controls remain system sans-serif.
- Monospace is limited to route paths and support references.
- Rounded pills are status-only.
- One sheet shadow maximum in a view.
- Generated portfolio styling never escapes the Preview frame.
- Living Draft line is recognizable across auth, journey, loading, and completion
  without being continuously animated.

### 15.3 Browser baseline

Target the current and previous stable major versions of Chrome, Edge, Firefox, and
Safari, plus current iOS Safari. Treat View Transitions, BroadcastChannel, and
`content-visibility` as progressive enhancements with the fallbacks specified here.
Do not ship large polyfills for decorative or optimization-only features.

Confirm this baseline at implementation kickoff because browser support changes.

## 16. Proposed source layout and build integration

```text
frontend/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    app/
      AppShell.tsx
      store.ts
      url-state.ts
      destination.ts
    auth-shared/
      tokens.css
      living-draft-mark.ts
    components/
      JourneyRail.tsx
      ArtifactSurface.tsx
      ProgressSurface.tsx
      AttentionPanel.tsx
      HandoffPanel.tsx
      ConnectionBanner.tsx
      StatusAnnouncer.tsx
    stages/
      discovery/
      content/
      design/
      preparation/
      generation/
    preview/
      PreviewSurface.tsx
      preview-adapter.ts
      preview-messages.ts
    data/
      api-client.ts
      errors.ts
      polling.ts
      invalidation.ts
      adapters/
    styles/
    test/

src/oryxenai/web/static/product/  # generated, never hand-edited
```

The exact number of files can remain small during implementation; the tree indicates
ownership boundaries, not a demand for boilerplate. Co-locate tests with frontend
source if the chosen runner supports it, while all Python tests continue under the
repository's existing `tests/` policy.

The FastAPI/Jinja shell should reference the generated Vite manifest or a small
deterministic asset mapping. Use Vite's `manifest: true` build output
(`dist/.vite/manifest.json`) and a small Python helper that resolves entry names to
hashed filenames at render time, rather than hand-maintaining asset paths in Jinja
templates. Production serves compiled static assets from the existing application
boundary. It does not run a Node frontend server.

Authentication keeps its current small ES-module controller and consumes the shared
compiled tokens/mark rather than mounting Preact on every auth page.

**Deployment target:** confirmed as Render free-tier web services plus the existing
Cloudflare R2 artifact storage, per
`docs/code-generator-architecture/free-host-deployment.md` (see
[06](06-cross-model-review-and-decisions.md) §5 for the resolved conflict with an
early AWS contingency in `docs/Auth/04-deployment-and-operations.md`). The
compiled `src/oryxenai/web/static/product/` output ships inside the same backend
Docker image already described there; no separate static-hosting deployment is
introduced.

## 17. Verification strategy

### 17.1 Unit tests

- URL parser/serializer and locked-stage correction.
- Safe intended-destination validator.
- Every status adapter, including unknown and malformed payloads.
- Action eligibility from stage plus entitlement.
- Error-code mapping and safe fallback.
- Poll cadence, deduplication, backoff, visibility, and stale-response defense with
  fake timers.
- Idempotency-key reuse/removal behavior.
- Broadcast invalidation payload privacy.
- Safe artifact renderer: escaped HTML, allowed/disallowed links, input cap, plain-
  text fallback.
- Preview origin/path/route/message validation.
- Reduced-motion state behavior independent of animation events.

### 17.2 Component tests

- Keyboard and focus behavior for journey, dialogs, composer, artifact navigation,
  Preview toolbar, and details sheet.
- Each loading/empty/error/review/read-only component state.
- One primary action per state.
- No hidden future-stage action in the tab order.
- Live announcer emits only meaningful transitions.
- Draft preserved after conflict and cleared after confirmed acceptance.
- Old Preview retained while replacement is uncertain or fails.

### 17.3 Integration tests against FastAPI

- Auth bearer injection and one-refresh-on-401 behavior.
- First portfolio creation and entitlement binding.
- Every explicit stage start without automatic successor calls.
- Discovery answer/revise/approve sequence.
- Content and Design revise/approve sequence.
- Preparation start, ready, stale, failure, and regenerate behavior.
- Generation start/retry, read-only transition, and active Preview promotion.
- Structured error envelope handling.
- Session revision conflict reconciliation.
- Sign-out aborts polling and clears private UI.

### 17.4 End-to-end browser tests

Use deterministic backend fixtures for ordinary frontend acceptance; live model runs
are a separate opt-in acceptance layer.

Critical journeys:

1. signed-out visit -> Google sign-in initiation;
2. existing valid session -> `/app` without sign-in flash;
3. first admission -> username onboarding -> empty start;
4. first portfolio -> Discovery input -> questions -> brief review;
5. brief revise -> revised review -> approve -> explicit Content start;
6. Content review/revise/approve -> explicit Design start;
7. Design review/revise/approve -> explicit preparation start;
8. preparation running -> leave -> return -> ready;
9. generation queued through verification -> promoted Preview;
10. failed generation with an older active Preview preserved;
11. read-only successful account refresh and deep link;
12. network loss and restoration during an active run;
13. two tabs changing the same stage with unsent draft preservation;
14. protected deep link through expired auth;
15. invalid/unauthorized session URL or stale entitlement;
16. mobile completion of question, revision, approval, monitoring, and Preview;
17. reduced motion and forced colors;
18. keyboard-only journey and Preview navigation; and
19. unknown adapter status fails safely without enabling an action.

### 17.5 Visual regression set

Capture stable screenshots at representative sizes for:

- auth resolving, sign-in, onboarding error;
- first portfolio;
- Discovery current question and brief review;
- Content/Design long artifact and approval confirmation;
- preparation/generation working and attention;
- Preview absent/opening/ready/old-result-preserved;
- read-only completion;
- connection banner/details sheet; and
- reduced-motion/forced-colors variants where the test system supports them.

Visual snapshots supplement semantic assertions; they do not replace interaction or
accessibility tests.

## 18. Acceptance matrix

| Area | Scenario | Pass condition |
| --- | --- | --- |
| Auth | Private session is still resolving | No portfolio content or protected request before valid session |
| Auth | Callback repeated/refreshed | Resolves once without loop or duplicated exchange UI |
| Auth | First 401 | Refreshes once and retries exact request |
| Auth | Second 401 | Stops work, clears private render, returns to sign-in |
| Auth | Normal user opens `/admin` | Replaced to `/app` without admin-content flash |
| Onboarding | Username conflict | Value retained, inline error focused, another value allowed |
| Home | No portfolio | One clear start action; no fake dashboard/projects |
| Home | Active run | Current stage/progress is the primary destination |
| Home | Review waiting | Required artifact review is more prominent than background history |
| Routing | Refresh a valid completed-stage link | Same safe stage/view restores |
| Routing | Locked/invalid stage link | Corrected to reachable stage without exposing data |
| Discovery | Question set changes after refresh | Answers keyed by ID; draft preserved; no wrong submission |
| Discovery | Brief approval | Confirmed before completion; next stage does not auto-start |
| Content | Long artifact | Readable, navigable, bounded rendering, no raw JSON |
| Design | Revision | Existing artifact stays visible until new durable review state |
| Prepare | Unknown internal substage | Generic honest preparation copy; no crash or false completion |
| Prepare | Pack becomes stale | Generate action removed; supported regeneration shown |
| Generate | Shared lane wait | Says waiting without percentage/ETA or repeated action |
| Generate | Retry eligible | One idempotent retry action; no new variant implication |
| Generate | Retry not eligible | No retry control; safe explanation from entitlement |
| Preview | Candidate build exists but not promoted | Candidate never appears in product frame |
| Preview | Replacement fails | Previous verified Preview remains visible and labelled |
| Preview | Invalid origin/route/message | Rejected; no navigation or host state mutation |
| Preview | Frame load times out | Preview-specific recovery; generation state remains intact |
| Read-only | Successful normal user returns | Preview/artifacts available; mutation controls absent |
| Network | Poll fails | Last state retained with one banner and capped retry |
| Network | Tab returns from background | Immediate canonical refetch before new animation |
| Multi-tab | Other tab writes | Visible tab refetches; unsent draft is not overwritten |
| Accessibility | Screen reader during polling | Only meaningful state transition announced |
| Accessibility | Reduced motion | All information remains; travel/loop/smooth motion removed |
| Accessibility | 200% zoom/mobile keyboard | Current content and actions remain reachable |
| Performance | Long session | No accumulating intervals/listeners or unbounded DOM activity |
| Security | Sign-out | Requests/listeners/frame torn down; private UI removed |
| Security | Artifact contains HTML/script-like text | Displayed as safe text; never executed |
| Security | Generated frame sends unexpected message | Ignored without side effect |
| Visual | Any core screen | Conforms to Editorial Swiss tokens and is not a generic card/grid AI shell |

## 19. Implementation sequence and stop gates

Five phases, each ending in a working, deployable state. Do not start a phase
before the previous one's stop gate passes. No phase auto-chains a backend stage
or weakens the verified-Preview boundary — that invariant never changes,
regardless of which phase is in progress.

### Phase 1: foundation, visual system, and auth continuity

Coded spike first, then the build/auth work it unblocks:

- Implement tokens, type subset candidate, living mark, one artifact specimen,
  one progress specimen, and one Preview frame shell.
- Implement adapter fixtures for current stage payloads.
- Measure production bundle and font output against §14's budgets.
- Add Vite/Preact build for `/app` only.
- Add API client, error normalization, store, URL codec, polling coordinator, and
  shared tokens.
- Restyle auth pages with shared tokens/mark without changing auth logic.

Two fixes that belong in this phase and nowhere later, because everything
downstream depends on auth staying correct:

- Fix the `resolveAuthenticatedContext()` error-code gap:
  `AUTH_PROVIDER_UNAVAILABLE` and `MODEL_PROVIDER_CREDIT_EXHAUSTED` currently
  fall through to a full local sign-out in the path that gates `/app`
  (`src/oryxenai/auth/static/auth-runtime.mjs` around
  `resolveAuthenticatedContext`), instead of the safe in-place message
  `routeController()` already shows for the same codes on the auth pages
  (`src/oryxenai/auth/static/auth-controller.mjs`). This is a real bug in the
  current implementation, not a redesign concern — see
  [06](06-cross-model-review-and-decisions.md) §3.2 for the full trace.
- Point `src/oryxenai/web/static/app-auth-bootstrap.mjs`'s `loadWorkspace` at the
  new Preact bundle's entry output instead of its current hardcoded
  `import("/static/app.js")`. This one line is workspace-loader wiring, not auth
  logic, and is in scope for this phase. Branch it on `isDeveloperPage`: `/dev`
  keeps loading the legacy bundle until Phase 5 cutover, `/app` loads the new
  one. The Preact entry must export the same `{ boot, stop, restart }` shape
  `bootProductShell()` already calls, so `bootProductShell()` itself needs no
  behavioral changes — see [06](06-cross-model-review-and-decisions.md) §3.3.
- Carry the structural
  `body.auth-pending > :not(#auth-bootstrap-progress) { visibility: hidden; }`
  rule (currently in `src/oryxenai/web/static/app.css`) into the new stylesheet
  layer (§15.1) before `app.css` is ever retired. This is what makes private
  content structurally unable to paint before auth resolves; it must always have
  a home, never a gap during the transition.

Stop gate: visual thesis/readability/bundle feasibility approved; adapter
boundaries in place; existing auth route/security tests plus new
redirect/failure acceptance pass, including the corrected
provider/credit-unavailable behavior above.

### Phase 2: app shell, Discovery, Content, and Design

- Build app shell, journey, start/resume, connection behavior, and cross-tab
  invalidation.
- Port Discovery start/questions/brief/revise/approve behavior.
- Add Content and Design artifact adapters/surfaces.
- Add revision, approval, and explicit handoffs between Discovery, Content, and
  Design.

Stop gate: refresh-safe Discovery parity, accessibility pass, and a realistic
long-artifact review on desktop and mobile.

### Phase 3: Build Preparation and Code Generator integration

- Add volatile Build Preparation adapter and progress/attention states.
- Add only production Code Generator session endpoints.
- Keep the development harness unchanged.

Stop gate: state/entitlement/error matrix and long-running session test.

### Phase 4: verified Preview

- Add active receipt validation, frame lifecycle, route/viewport/refresh/new-tab
  toolbar, exact-origin messaging, and previous-result preservation.
- Add the container-sizing hardening in §8.10: reserve the frame's box before
  load, and letterbox via a fixed-size wrapper plus `transform: scale()` rather
  than resizing the iframe outside the four verified profiles.

Stop gate: security, direct-route, iframe, failure, container-sizing/CLS, and
responsive acceptance.

### Phase 5: hardening and cutover

- Complete performance, accessibility, visual regression, and multi-tab testing.
- Verify compiled static asset packaging and low-cost deployment behavior.
- Remove only superseded normal-product assets after parity is proven.

Stop gate: all acceptance rows in §18 pass or each exception has an explicit
recorded decision. Do not remove developer fixtures/harnesses as incidental
cleanup.

## 20. Definition of implementation complete

Implementation is complete only when:

- auth through Preview is one visually coherent journey;
- every current durable state has a tested presentation and every unknown state
  fails safely;
- first-time, returning, attention, active-run, Preview-ready, and read-only users
  land correctly;
- no stage auto-starts and no unsupported control is visible;
- user drafts and last confirmed state survive realistic conflicts/network loss;
- only a verified promoted Preview is embedded, on its isolated origin;
- the old verified Preview survives a failed replacement;
- desktop, tablet, and mobile support their intended jobs;
- keyboard, screen-reader, zoom, contrast, and reduced-motion acceptance passes;
- production bundle, responsiveness, and long-session behavior meet the budgets;
- the normal product contains no developer-only fields, routes, or vocabulary;
- the Editorial Swiss / Living Draft identity is consistent without heavy imagery or
  runtime effects; and
- backend, agent, entitlement, and Preview invariants remain unchanged.
