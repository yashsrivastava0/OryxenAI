# Frontend redesign context pack

> Attach this file together with [08-frontend-contract-ledger.md](08-frontend-contract-ledger.md)
> and [09-frontend-replacement-runbook.md](09-frontend-replacement-runbook.md) to an
> AI coding agent before it replaces or substantially revamps the frontend.
>
> This is a migration contract, not a visual brief. It protects behavior while
> leaving the coding agent free to change layout, components, styling, motion,
> and client implementation details.

## Mission

Replace the frontend without changing what the server means, who may do it, or
what a user can safely see. The new interface may look completely different,
but it must remain a truthful projection of the existing authenticated flows,
durable agent states, authorization boundaries, and recovery behavior.

The correct mental model is:

```text
server/auth state -> reviewed client boundary -> adapter/view model -> screen
user action -> reviewed API mutation -> durable job/state -> reconciliation -> screen
```

The visual layer is replaceable. The arrows, gates, IDs, request shapes, and
reconciliation rules are not replaceable unless a separate backend change is
explicitly requested and verified.

## Full-state context handoff — do not summarize it away

This pack is a safety mechanism for the coding agent, not a data-minimization
policy for the coding agent. When this pack is attached to a future frontend
task, pass the complete state context as well: raw API envelopes, complete
stage projections, jobs, schemas, prompts, fixtures, adapters, and tests. Do
not send only screenshots, a short product brief, or the currently visible
card fields. If the context is too large for one message, split it into
labeled stage packets and preserve every field; do not silently truncate or
invent a reduced schema.

The minimum context packet is:

| Context packet | Include completely | Why it matters |
| --- | --- | --- |
| Auth/account | `/api/v1/me` projection, role, onboarding, entitlement, `read_only`, `portfolio_session_id`, and auth/bootstrap route behavior | Determines which shell and mutations are legal. |
| Session | Session `id`, `status`, `current_state`, and `revision` | Establishes the server-authoritative owner/session identity and CAS behavior. |
| Discovery | The full Discovery stage envelope, `current_state.discovery`, jobs, questions, answers, intake, memory, brief, errors, attempts, and approval snapshot | Preserves the exact conversation, question generation, answer recovery, and brief output. |
| Content Architect | The full Content stage envelope, `current_state.content_architect`, jobs, source snapshot, preferences, route/section/claim data, handoff, warnings, errors, attempts, and approval snapshot | Preserves route count, section count, publication gates, and the complete content handoff. |
| Visual Design Director | The full Design stage envelope, `current_state.visual_design_director`, jobs, source hashes, preferences, visual systems, pages, scenes, assets, resources, warnings, compiler handoff, errors, attempts, and approval snapshot | Prevents a redesign from collapsing the rich visual direction into the current short summary. |
| Execution evidence | Agent schemas, prompts, `agent.py`, `state.py`, `service.py`, adapters, stage components, fixtures, and tests | Explains how every field is produced, changed, displayed, retried, or gated. |

The current `frontend/src/data/final-agent-output.ts` is a user-facing artifact
projection, not the complete context contract. A future coding agent must see
the raw state and source contracts even if a screen chooses a more organized
presentation. Context completeness and user-facing privacy are different
decisions: never hide state from the coding agent, while still keeping bearer
tokens, credentials, and unrelated transport secrets out of the browser UI.

## Read in this order

1. `AGENTS.md`, `DECISIONS.md`, and the relevant recent entries in `CHANGES.md`.
2. This file for the system boundary and current product vocabulary.
3. `08-frontend-contract-ledger.md` for route, auth, agent, state, and action
   mappings.
4. `09-frontend-replacement-runbook.md` for the search, implementation,
   screen-by-screen migration, and verification procedure.
5. Existing detailed research only when needed:
   `docs/Frontend/05-implementation-blueprint-and-acceptance-matrix.md`,
   `docs/Frontend/02-state-progress-and-edge-cases.md`, and
   `docs/Auth/01-user-flows-and-route-contract.md`.

If a document and executable source disagree, verify the source and tests before
coding. Do not silently update the UI around an uncertain contract.

## Scope map: the repository has more than one frontend

These surfaces share branding and backend code but are not one product screen.
Keep their routes, auth modes, vocabulary, and API clients separate.

| Surface | Routes | Current entry boundary | Access model | Redesign rule |
| --- | --- | --- | --- | --- |
| Auth and account shell | `/`, `/sign-in`, `/auth/callback`, `/access-not-approved`, `/account-unavailable`, `/onboarding`, `/admin` | `auth_shell.html` -> `auth-page.mjs` -> `auth-controller.mjs` / `auth-runtime.mjs`; `/admin` additionally loads `auth-admin.mjs` | Supabase Google/PKCE plus server-authoritative `/api/v1/me` | May be restyled, but preserve every route outcome, redirect allowlist, no-private-flash rule, and logout cleanup. |
| Authenticated product | `/app` | `product_shell.html` -> `app-auth-bootstrap.mjs` -> built `frontend/` Preact bundle | Attached bearer session; owner/admin server authorization | This is the normal-user redesign target. Keep the bootstrap seam and four-stage boundary through Build Preparation. |
| Detached product/developer shell | Detached `/app` | Detached `/app` uses `pipeline-bootstrap.mjs` and the same Preact product bundle | Anonymous same-origin requests in configured detached mode | Keep detached behavior isolated. Never use it to justify weakening attached auth. |
| Build Preparation diagnostic | `/dev/build-preparation-fixture`, `/build-preparation-fixture`, and `/.../progress` | Jinja shell plus `build-preparation-fixture.js` / `build-preparation-progress.js` | Feature/config gated; detached or admin depending on mode | Preserve as an operational diagnostic. Do not fold it into normal `/app` accidentally. |
| Code Generator development control room | `/dev/code-generator-development`, `/code-generator-development` | Jinja shell plus `code-generator-development.js` and controller/bootstrap modules | Development harness mode; attached admin or detached according to config | Preserve its durable run/plan/acquire/generate/verify/preview controls separately from creator UX. |
| Generated preview | Exposed by Code Generator/preview gateway, not a normal `/app` screen in the current release | Generated-site runtime and, in the development harness, a sandboxed iframe | Verified promoted artifact only | Never show an unpromoted candidate or treat Preview as public publishing. |

The current normal product includes the approved Build Preparation handoff.
Build Preparation's controls are integrated in `/app` only after approved
Content and Design; Code Generator and Preview remain separate development
capabilities whose controls stay outside normal `/app`.

## What the redesign may change

The coding agent may change:

- visual identity, typography, color, spacing, composition, and motion;
- component boundaries and folder names inside the new client;
- whether a stage is presented as a page, panel, drawer, stepper, or document;
- framework details inside the product bundle, provided the server boot contract
  remains compatible; and
- how the same safe artifact fields are arranged for different screen sizes.

The coding agent must not change implicitly:

- server route paths, HTTP methods, request bodies, response field names, stable
  IDs, or error-code semantics;
- auth/session restoration, PKCE callback exchange, bearer injection, one-refresh
  retry, or sign-out cleanup;
- owner/admin/read-only enforcement or the `/api/v1/me` admission decision;
- stage gates, approval boundaries, durable job polling, idempotency behavior,
  session revision reconciliation, or cross-tab invalidation;
- the distinction between normal product, admin console, detached pipeline, and
  developer harness;
- what private intake, auth data, model/provider data, job internals, storage
  paths, hashes, or raw reasoning can be displayed to a normal user; or
- the stable `boot(options)`, `stop()`, `restart(options)` seam consumed by
  `app-auth-bootstrap.mjs` and `pipeline-bootstrap.mjs`.

If a desired visual interaction needs a new capability—such as cancellation,
streaming, file extraction, version history, publishing, or a new stage—record
it as a separate proposal. Do not simulate it in the client.

The requested tracing, Visual Design Director presentation, and full-JSON copy
features below are intentionally incremental presentation/debug enhancements.
They must fit inside the current boot, auth, adapter, polling, and durable
state architecture. Do not use them as a reason to hard-restrict the context,
replace the API client, or perform a complete frontend restructure.

## Non-negotiable runtime seams

### Server shell and bundle loading

`src/oryxenai/web/routes.py` chooses the product shell and resolves the Vite
manifest. `product_shell.html` provides `#product-root`, the product entry meta
tag, shared auth tokens, and one of the attached/detached bootstrap modules.

The product bundle must continue to expose:

```ts
export function boot(options): void
export function stop(): void
export function restart(options): void
```

The current attached bootstrap passes an object containing `authorizedFetch`,
`storage`, `me`, `role`, `developer`, `serverSessionId`, and `readOnly`.
Detached boot may also pass `pipelineMode`. Accept compatible extra fields rather
than breaking the existing loader.

`boot()` must mount only into `#product-root`; `stop()` must remove private UI,
pollers, listeners, and frame activity; `restart()` must be equivalent to a
clean stop followed by boot.

### Authentication boundary

`src/oryxenai/auth/static/auth-runtime.mjs` owns the browser auth boundary:

- configuration comes from server-rendered public meta tags;
- Supabase uses the pinned local browser client and PKCE;
- protected requests accept only reviewed same-origin `/api/v1/...` paths;
- the access token is injected by `createAuthorizedFetch`, never by screen code;
- one `401` may refresh and retry the exact request once;
- a second `401` clears private state, stops activity, and routes to sign-in; and
- transient provider/credit conditions do not masquerade as an expired session.

The product bundle receives `authorizedFetch`; it must not instantiate a second
auth client, read tokens, call a provider directly, or build arbitrary URLs from
query parameters.

### Server-authoritative state

`/api/v1/me`, the session projection, stage projections, and related jobs are the
authority. Client state is a normalized cache of confirmed server facts. Local
storage is only for bounded, recoverable conveniences already supported by the
codebase: question drafts, unresolved idempotency keys, admin-session hints,
metadata-only diagnostics, and private cleanup.

Never store the resume, raw intake, auth token, complete agent output, or a new
parallel source of truth in browser storage.

### Stage adapters

Adapters accept `unknown`, validate the minimal envelope, map backend statuses to
the product vocabulary, and fail closed to `unsupported` for an unknown required
status or malformed envelope. Components consume adapter/view-model values; they
must not branch on raw backend status strings.

The shared product state vocabulary is:

```text
locked | available | working | input | review | attention | complete | unsupported
```

`unsupported` is a safe forward-compatibility state. It must never become
`available` or `complete` merely because a new server status is unfamiliar.

## Agent behavior and output detail that the redesign must preserve

The agent is allowed to redesign how these details are grouped, but not to
forget them. “Task count” below means internal model operations, not one model
call per question, page, or section.

### Discovery

- Input is the user's `message`, optional `document_text`, and optional `goal`;
  it is stored as-is and is not pre-normalized by the frontend.
- Operation A, `understand_and_question`, is one model call. It returns one of
  `NEEDS_DETAILS`, `ASK_QUESTIONS`, or `READY_FOR_BRIEF`, an
  `assistant_message`, a `questions[]` batch, and `memory_update`.
- The prompt asks for zero to seven formal questions; the active validation
  ceiling is the configured `max_questions` value (currently `8` in settings).
  Preserve the configured ceiling and the prompt behavior; do not turn the
  questions into a fixed questionnaire. This source-level 7-versus-8 distinction
  is intentional context for the next agent to verify, not a reason to invent a
  new limit.
- Questions are generated as one adaptive batch from the accumulated material
  and prior memory, then shown one at a time in the conversation. A question
  has a stable ID, text, optional help/reason, kind (`text`, `single_select`,
  `multi_select`, or `boolean`), options, `allow_skip`, and `allow_auto`.
  Select questions should have at most three concrete options; free text and a
  separate Skip action remain available where the contract allows it.
- The model must not re-ask supplied facts, must ask only material decisions,
  may auto-select presentation preferences only, and must not invent facts.
  A bare greeting or unusable material produces `NEEDS_DETAILS` with no formal
  question; “no questions” or “use your judgment” produces `READY_FOR_BRIEF`.
- When answers are complete, Operation B, `build_or_revise_brief`, is one more
  model call. It produces `BRIEF_READY`, `assistant_message`, `brief_title`,
  free Markdown `brief_markdown`, `user_summary`, a structured factual
  `profile`, `open_items`, and `memory_update`. A revision is the same bounded
  brief operation with a natural-language request and the existing brief.
- The normal screen shows the conversation and then the brief as a readable
  review artifact. The full brief/profile/open items must remain available to
  the JSON-copy action; approval is explicit and the current gesture then
  starts Content through the existing two idempotent endpoint calls.

### Content Architect

- Input is only the approved Discovery snapshot: brief title, `user_summary`,
  structured profile, open items, approval hash/revision, and optional
  preferences. It is not a new Discovery interview and it does not receive raw
  resume text or the full Discovery Markdown brief.
- It is one durable job with one to three sequential model calls, never one per
  route or section:
  `plan_content` always runs; `write_pages` runs only when the plan defers
  content; `integrate_content` runs when cross-route reconciliation is needed
  or the plan has more than two routes. Approval-readiness correction may use
  the remaining bounded integration call.
- The plan chooses positioning, narrative, presentation mode, route plan,
  claim grounding, and either writes complete content in the same call or
  defers to one batched page-writing call. Page writing covers every approved
  or pending route in one response; it never asks for a separate call per
  page/section.
- The persisted output includes `user_summary`, `site_story_strategy`,
  `decision_basis`, `route_plan`, `claim_grounding`, `page_content_packs`,
  `public_content_manifest`, `omissions`, `unresolved_issues`,
  `privacy_and_confidentiality`, `media_status`, `visual_director_handoff`,
  `warnings`, and `stages_run`, plus state/source/approval metadata.
- The normal screen shows positioning, route count and details, section-level
  content packs, decision provenance, warnings, and unresolved issues. It must
  not collapse the complete route/section/claim state into only the short
  summary. Content approval is separate from the explicit Design start.

### Visual Design Director

- Input is the approved public Content Architect snapshot and optional visual
  preferences, plus a deterministic local resource-catalogue shortlist. It
  receives approved public route/page content and handoff guidance, not a new
  raw-resume path.
- It is one durable job with one to three sequential model calls, never one per
  page or scene: `establish_visual_language` always runs; `direct_page_experience`
  runs only when pages were deferred; `integrate_site_experience` runs for
  cross-page reconciliation (more than two routes or an explicit conflict).
- The complete output includes `user_summary`, `meta`, `source_refs`,
  `visual_language`, `shared_visual_systems`, `navigation_direction`,
  `motion_system`, `interaction_system`, `pages`, `asset_briefs`,
  `resource_candidates`, `accessibility_and_performance`, `must_preserve`,
  `must_not_fabricate`, `conflicts`, `warnings`, `compiler_handoff`,
  `resource_policy`, `stages_run`, and the source/preferences/run/approval
  state around that output.
- Each page can contain route-level purpose, visitor takeaway, storyboard,
  section rhythm, emphasis, background evolution, evidence/interaction moments,
  closing action, navigation behavior, responsive summary, scenes, asset IDs,
  resource IDs, and acceptance criteria. Each scene can contain stable IDs,
  content refs, layout/proportion/layer intent, assets/resources, motion and
  interaction states, transitions, responsive/accessibility behavior,
  reduced-motion behavior, performance risk, failure-safe static state, and
  acceptance criteria. Resource and asset IDs must remain exact.
- The current screen exposes only a small thesis/page/resource slice. The
  redesign must present the complete Visual Design Director output in a clean,
  scannable hierarchy; the requested presentation specification is recorded in
  the enhancement section below.

### Explicit handoffs

No stage is silently auto-started by the backend or by background polling.
The current product has one deliberate two-endpoint user gesture: the Discovery
approval action calls Discovery `approve`, then Content `start` with its existing
idempotency key, and then selects Content. This is still user-triggered explicit
orchestration, not a worker chain. A redesign must preserve that meaning and must
not introduce additional hidden chaining.

The later current-product behavior is:

- Content approval saves Content only; “Continue to Design” selects the Design
  stage, where the user still chooses its explicit Start action.
- Design approval saves the creative handoff and ends the current normal product.
- Build Preparation and Code Generator are not called from normal `/app`.

## Product vocabulary and visibility boundary

Use product language in visible copy:

| Product term | Meaning | Avoid exposing as primary copy |
| --- | --- | --- |
| Portfolio | One durable owner-scoped work product | project dashboard, chat collection |
| Stage | A gated phase of the portfolio journey | model step, agent swarm |
| Artifact | Reviewable output from a stage | raw response |
| Run | Durable execution behind a stage | hidden “thinking” stream |
| Handoff | User-confirmed movement to the next stage | automatic continuation |
| Attention | Durable state with supported recovery | generic failure toast |
| Preview | Verified promoted generated site | published, production, live site |

Normal users may see meaningful milestones, safe warnings, support references,
and artifact content. They must not see exact percentages/ETAs, provider names,
model profiles, storage vendors, prompt/reasoning traces, raw job payloads,
temporary paths, hashes, or stack traces.

This visibility rule does not reduce the context passed to the coding agent.
The agent receives the full state data and complete output contracts. It only
defines what the normal product chooses to render as user-facing UI.

## Requested incremental enhancements

These are additive requirements for the redesign, not permission to replace the
working architecture.

### 1. Temporary issue-tracing popup

Use the existing `client-diagnostics.ts` trace timeline and trace ID as the
source. Add a non-blocking, accessible popup/toast that appears when a real
issue is detected: an API error, worker-stalled condition, `needs_attention`,
unsupported state, render/runtime error, or failed mutation. It should show a
short human explanation, the short trace ID, and optional `Copy trace`/dismiss
actions. It must not replace the persistent stage error or recovery action.

The popup is temporary: deduplicate the same issue, allow manual dismissal,
auto-remove after a short configurable duration, clear its timer on unmount or
logout, announce through `role="alert"`/live-region semantics, and respect
reduced-motion settings. Successful responses and cache notices should not
produce an issue popup. Keep trace payloads metadata-only and bounded; the
complete state still goes to the coding agent as context.

### 2. Complete Visual Design Director presentation

Replace the current minimal Design artifact slice with a polished structured
reader. Keep the existing adapter and raw state, but organize all output into:

1. overview and `user_summary`;
2. creative thesis and `visual_language`;
3. shared visual systems, navigation, motion, interaction, and accessibility;
4. a route/page storyboard for every page, with stable route IDs and counts;
5. expandable scene cards with the full scene-level behavior and responsive/
   reduced-motion/failure-safe fields;
6. asset briefs and their source/fallback/accessibility intent;
7. resource candidates with provenance, adaptation, priority, and fallback;
8. must-preserve/must-not-fabricate rules, conflicts, warnings, and unresolved
   constraints; and
9. the final `compiler_handoff` when present.

Do not make this a wall of raw JSON or hide fields behind a summary. Use clear
headings, stable IDs, counts, route/scene navigation, readable long text, and
progressive disclosure for deeply nested detail. Preserve approval/revision
controls and do not add implementation code to this stage.

### 3. Copy the complete agent JSON from the right sidebar

Add a right-hand sidebar action for each generated stage artifact: Discovery,
Content Architect, Visual Design Director, and any later stage that is surfaced
in the same product shell. The action is disabled before that stage has a
generated response and is available in review and approved states.

The button must copy a pretty-printed, exact JSON object from the selected
stage's complete persisted agent response/state—not a reconstruction from the
visible cards and not the current convenience allowlist alone. Preserve every
agent-produced field, nested array, stable ID, warning, omission, conflict,
handoff, and empty-field shape that the stage response exposes. The universal
security boundary still excludes bearer credentials and unrelated platform
transport wrappers; this is not permission to drop agent output fields.

Show a short success state such as “JSON copied,” a clear clipboard-unavailable
fallback (selectable read-only text or download), and an accessible label naming
the stage. Copying is read-only: it must not start a request, mutate state,
advance a stage, or create an idempotency key. Add tests proving the copied JSON
matches the raw stage payload, including the full Visual Design Director fields.

## Definition of a safe replacement

A replacement is safe only when a new agent can show, for each screen and action:

1. the source route and auth boundary;
2. the server endpoint or server state it represents;
3. the adapter/view-model mapping used by the screen;
4. the preserved action eligibility and error/recovery path; and
5. an automated or browser proof that refresh, auth expiry, network loss, and
   an unknown state do not produce a false success or private-data flash.

The next file is the filled contract ledger that makes those five proofs
mechanical instead of relying on visual similarity.
