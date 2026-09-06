# Frontend contract ledger

This is the behavior map to preserve while the frontend is redesigned. It is
intentionally more precise than a screen guide and less coupled than a component
tree. When implementation changes, update the affected row and its proof link;
do not replace a row with a screenshot.

## Ledger rules

- Backend routes, schemas, state machines, auth runtime, and tests are the
  primary evidence.
- `frontend/src/data/api-client.ts` is the product request inventory.
- `frontend/src/data/adapters/` is the current translation boundary.
- `frontend/src/app/AppShell.tsx` is the current mutation/polling choreography.
- `src/oryxenai/auth/static/` and `src/oryxenai/web/static/` contain the browser
  security/bootstrap boundaries, not merely legacy styling.
- A stable backend ID is a contract. Do not replace `session_id`, `job_id`,
  `question_id`, `route_id`, `section_id`, `resource_id`, or run IDs with array
  indexes or labels.
- A visual redesign can remove a DOM selector only after confirming it is not a
  bootstrap hook, test hook, `data-*` contract, accessible name, or cross-module
  integration point.

## 1. Route and auth ledger

| Route/surface | Entry source | Initial decision | Protected request rule | Success destination | Failure destination/proof |
| --- | --- | --- | --- | --- | --- |
| `/` | `auth/web.py` + `auth_shell.html` | Resolve existing session; detached mode redirects to `/app` | No protected API when signed out | `/app`, `/onboarding`, or `/admin` after `/me` | `/sign-in`, `/access-not-approved`, `/account-unavailable`, or safe in-place provider message; `auth-controller.test.mjs` |
| `/sign-in` | `auth/web.py` + auth controller | Show Google sign-in; do not show prior portfolio data | Sign-in initiation is provider-owned; product API waits for a session | Provider returns to configured callback | Inline safe error; no redirect loop; `auth-controller.test.mjs` |
| `/auth/callback` | `auth-controller.mjs` | Exchange PKCE code once, strip OAuth artifacts, then resolve | Only after successful session exchange | `/app`, `/onboarding`, or safe denial route | Canceled/failed callback clears private state and returns to sign-in; auth controller tests |
| `/access-not-approved` | `auth_shell.html` | Explain admission denial/capacity and offer sign-out/account switch | No portfolio request | Sign-out or owner-directed retry | Never flash `/me` private fields; auth controller tests |
| `/account-unavailable` | `auth_shell.html` | Explain suspended/deleted/unavailable account | No portfolio request | Sign-out or documented recovery | No private portfolio flash; auth controller tests |
| `/onboarding` | `auth_shell.html` + `PUT /api/v1/me/username` | Claim one username; preserve field on conflict | `authorizedFetch` only | `/app` after server acceptance | Inline safe error; `USERNAME_TAKEN` retains input; auth controller tests |
| `/app` attached | `product_shell.html` -> `app-auth-bootstrap.mjs` -> product bundle | Restore auth, call `/api/v1/me`, derive owner session | Bundle receives `authorizedFetch`; never reads token | Empty start or current portfolio stage | One refresh-on-401; second 401 clears/returns to sign-in; app-auth bootstrap tests |
| `/app` detached | `product_shell.html` -> `pipeline-bootstrap.mjs` | Load developer shell without Supabase login | Same-origin anonymous requests; no bearer header | Detached product | Never reuse detached fetch in attached product; pipeline bootstrap tests |
| `/admin` | `auth_shell.html` -> `auth-admin.mjs` | `/me` must resolve an active onboarded admin | Admin API calls use the shared authorized boundary | Admin console | Normal user is replaced to `/app` without admin content flash; auth controller/admin tests |
| Build Preparation fixture | `web/routes.py` templates + fixture JS | Route exists only when dev/fixture config permits | Detached anonymous or admin-authenticated depending on configured harness mode | Fixture run/progress/details | Feature-off/invalid run safe error; fixture route/API tests |
| Code Generator development | `web/routes.py` + codegen JS | Route exists only when development harness is enabled | Detached anonymous or admin-authenticated depending on harness mode | Durable run control room | Non-admin -> `/app`; expired auth uses shared refresh boundary; codegen auth tests |

The redirect allowlist is deliberately narrow: configured destinations are
validated to the local reviewed `/app` and `/admin` routes. Do not add a generic
`next=` redirect during a visual rewrite.

## 2. Product boot ledger

| Contract | Current source | Preserve exactly |
| --- | --- | --- |
| Mount point | `product_shell.html`, `frontend/src/main.tsx` | `#product-root` exists before boot and is the only product mount. |
| Entry discovery | `web/routes.py`, `product_shell.html` | Read the Vite manifest entry; do not hardcode a hashed asset filename. |
| Bootstrap API | `app-auth-bootstrap.mjs`, `pipeline-bootstrap.mjs` | Bundle exports `boot`, `stop`, `restart`. |
| Auth-pending hide | `base.html`, `frontend/src/styles/shell.css` | Private product content remains hidden until auth resolution; retain the structural `body.auth-pending` rule in the replacement stylesheet. |
| Session identity | `MeProjection.portfolio_session_id` | Normal users use the server-provided owner session. Admin session hints are account-scoped and not an authorization mechanism. |
| Read-only | `/api/v1/me` and product mutations | `read_only` suppresses mutations in the UI, but the server remains authoritative. |
| URL state | `frontend/src/app/url-state.ts` | Current safe values are `stage=discover|content|design` and `view=start|work|artifact|progress`; invalid values are ignored and locked stages fall back. |
| Teardown | `main.tsx`, `AppShell.tsx`, poller/invalidation modules | Sign-out/session change/unmount stops polling, listeners, cross-tab channels, and private render state. |

## 3. Stage/action ledger: current authenticated product

Every row below is an explicit server-backed action. A new screen may move the
button or change its appearance, but it must keep the same action ID, request,
server result reconciliation, and recovery path.

### Discovery

**Upstream gate:** none after a portfolio session exists.

**Backend status -> normalized state:**

| Backend status | UI state | Required posture |
| --- | --- | --- |
| `not_started` | `available` | Start surface; no stage call before the user supplies intake. |
| `questions_queued` / `questions_running` | `working` | Semantic progress; durable job continues if the user leaves. |
| `questions_ready` / `answers_in_progress` | `input` | Show unanswered questions by stable ID and server-supplied kind/options. |
| `brief_running` | `working` | Explain that the brief is being shaped; do not invent percentage/ETA. |
| `brief_review` | `review` | Safe brief document, revision action, approval action. |
| `approved` | `complete` | Read-only brief plus Content handoff. |
| `needs_attention` or failed/cancelled active job | `attention` | Preserve answers/intake and offer only the supported retry. |
| unknown/malformed required shape | `unsupported` | Safe refresh/recovery; never enable approval/start. |

| Action ID | Request | Body/headers | On success | Preservation rule |
| --- | --- | --- | --- | --- |
| `discovery.start` | `POST /api/v1/sessions/{id}/discovery/start` | `{ message, document_text?, goal }`; optional `Idempotency-Key` | Adapt returned Discovery projection and jobs | Plain text intake is supported; do not invent file extraction. |
| `discovery.answer` | `PUT .../discovery/answers` | `{ complete, answers: [{ question_id, mode, value }] }` where mode is `answered` or `skipped` | Reconcile by question ID and session revision | Local draft is cleared only after confirmed response. |
| `discovery.generate_brief` | `PUT .../discovery/answers` | `{ complete: true, answers: [] }` | Enter brief work state | Never assume all questions are answered from local UI state. |
| `discovery.revise` | `POST .../discovery/revise` | `{ revision_request }` | Poll/reconcile revised brief | Existing artifact remains visible until durable new state arrives. |
| `discovery.approve` | `POST .../discovery/approve` | `{}` | Mark Discovery complete | Approval is server-authoritative and must not be faked optimistically. |
| `discovery.approve_and_start_content` | `approve` then `POST .../content-architect/start` | Content start uses `{ preferences: {} }` and its idempotency key | Select Content and show its durable state | This is one user gesture but two existing explicit endpoint calls; do not add a new combined endpoint. |
| `discovery.stop` | `POST .../discovery/stop` | `{}` | Stop durable work and preserve input | Re-enable/refetch polling if the stop request fails. |

Question invariants:

- preserve server order and stable `question_id`;
- use `kind`, `options`, and `allow_skip` as supplied;
- submit `answered`/`skipped` modes, not presentation labels;
- support text, single-select, multi-select, and boolean values;
- keep an unsent text draft scoped by question ID; and
- if a refresh removes/replaces a question, do not submit the old answer to the
  new question or discard an unsent draft without telling the user.

### Content Architect

**Upstream gate:** Discovery `approved`.

| Backend status | UI state | Required posture |
| --- | --- | --- |
| `not_started` and Discovery not approved | `locked` | Explain the gate; do not show a start action. |
| `not_started` and Discovery approved | `available` | Explicit Start Content action. |
| `build_running` | `working` | Semantic progress plus supported Stop action. |
| `content_review` | `review` | Readable artifact, revision, approval. |
| `approved` | `complete` | Read-only content artifact plus explicit Design handoff. |
| `needs_attention` or failed/cancelled job | `attention` | Safe error and supported retry/start. |
| unknown/malformed required shape | `unsupported` | Refetch/recovery only. |

| Action ID | Request | Body/headers | On success |
| --- | --- | --- | --- |
| `content.start` | `POST /api/v1/sessions/{id}/content-architect/start` | `{ preferences: {} }` plus idempotency key | Adapt `content_architect` and jobs. |
| `content.revise` | `POST .../content-architect/revise` | `{ revision_request }` | Keep old artifact visible until review returns. |
| `content.approve` | `POST .../content-architect/approve` | `{}` | Mark complete; do not start Design automatically. |
| `content.stop` | `POST .../content-architect/stop` | `{}` | Stop work; preserve approved Discovery. |

The safe review projection includes user summary, positioning, route plan,
section/page content packs, decision basis, unresolved issues, and meaningful
warnings. It excludes private intake, internal reasoning, provider calls,
catalogue mechanics, job metadata, and raw response envelopes.

### Visual Design Director

**Upstream gate:** Content Architect `approved`.

| Backend status | UI state | Required posture |
| --- | --- | --- |
| `not_started` and Content not approved | `locked` | Explain the gate. |
| `not_started` and Content approved | `available` | Explicit Start Design action. |
| `build_running` | `working` | Semantic progress plus supported Stop action. |
| `design_review` | `review` | Visual-direction artifact, revision, approval. |
| `approved` | `complete` | Read-only creative handoff; current product ends here. |
| `needs_attention` or failed/cancelled job | `attention` | Safe error and supported retry/start. |
| unknown/malformed required shape | `unsupported` | Refetch/recovery only. |

| Action ID | Request | Body/headers | On success |
| --- | --- | --- | --- |
| `design.start` | `POST /api/v1/sessions/{id}/visual-design-director/start` | `{ preferences: {} }` plus idempotency key | Adapt Design and jobs. |
| `design.revise` | `POST .../visual-design-director/revise` | `{ revision_request }` | Keep old artifact until review returns. |
| `design.approve` | `POST .../visual-design-director/approve` | `{}` | Save creative handoff; do not call Build Preparation. |
| `design.stop` | `POST .../visual-design-director/stop` | `{}` | Stop work; preserve approved Content. |

The safe review projection includes the creative thesis, design keywords,
color/type/motion intent, page directions, adaptable resource candidates,
conflicts, and warnings. Resource IDs may be displayed as human-readable
adaptation notes, but the normal product should not expose catalogue lookup or
provider mechanics.

## 4. Later-agent ledger: implemented but not current `/app` product scope

These rows are here so a redesign does not accidentally delete or absorb the
later agents. They are not permission to add controls to the current product.

| Agent | Production/session API | Safe gate | Durable output | Current frontend home |
| --- | --- | --- | --- | --- |
| Build Preparation | `GET/POST /api/v1/sessions/{id}/build-preparation`, `.../start`, `.../regenerate`, `.../download` | Approved Content + approved Design; input hashes/staleness matter | `content-and-narrative-brief.md` and `visual-and-build-brief.md` with checked JSON indexes | Legacy product/development surfaces and backend; no normal `/app` control. |
| Code Generator | `GET/POST /api/v1/sessions/{id}/code-generator`, `.../start`, `.../retry`, `.../regenerate` | Immutable approved brief pair, entitlement, worker release/contract, mutable/read-only policy | Durable generation state and only an atomically promoted verified Preview | Production API/admin/development harness; no normal `/app` control in the current release. |
| Code Generator development | `/api/v1/development/code-generator/...` | Development harness configuration; detached/admin mode | Detailed events, plans, acquisition, generation, verification, source files, preview | `code-generator-development.html` + `code-generator-development.js`. |

Do not call the standalone development endpoints from the normal product. Do
not display Build Preparation ZIPs, Code Generator source trees, internal work
graphs, provider receipts, or unpromoted preview candidates to a normal user.

## 5. Reconciliation ledger

| Concern | Required behavior | Current evidence |
| --- | --- | --- |
| Initial load | Resolve `/me`, use server session ID, then fetch session/stage projections | `AppShell.refetchCurrentSession`, `app-auth-bootstrap.mjs` |
| Polling | One in-flight request per resource; immediate fetch; visible cadence; capped backoff; stop at review/complete/attention/unsupported | `frontend/src/data/polling.ts`, `polling.test.ts` |
| Visibility | Pause scheduled polls while hidden; refetch immediately on return | `PollCoordinator` visibility listener |
| Cross-tab | Same-origin BroadcastChannel message `{ type, sessionId, at }`; visible receiver refetches | `frontend/src/data/invalidation.ts`, `multi-tab.test.ts` |
| Slow responses | Do not allow an older response to overwrite a confirmed newer mutation; preserve session revision | `AppShell` reconciliation and current adapter tests; add a generation guard if the replacement changes fetch architecture |
| Network loss | Retain last confirmed content, show non-modal connection state, retry boundedly | `ConnectionBanner`, `PollCoordinator`, resilience tests |
| Mutation uncertainty | A timeout is not a durable failure; refetch the stage before offering a duplicate action | `AppShell` mutation catch/refetch paths |
| Idempotency | Persist unresolved action keys by session/action; clear only after confirmed response | `frontend/src/data/idempotency.ts`, auth cleanup prefixes |
| Read-only | Hide/suppress product mutations from `/me.read_only`; still let the server reject forbidden requests | `AppShell`, `MeProjection`, product-boundary tests |
| Sign-out | Stop activity, clear private render/storage, sign out locally, replace to `/sign-in` | `logoutCurrentBrowser`, auth controller tests |

## 6. Error and privacy ledger

The UI must distinguish these classes rather than show one generic toast:

| Class | Examples | Preserve | Recovery |
| --- | --- | --- | --- |
| Auth/session | `AUTH_REQUIRED`, `AUTH_INVALID` | No private UI after invalidation | One refresh, then sign-in. |
| Admission/account | `ACCESS_NOT_APPROVED`, `USER_CAPACITY_REACHED`, `ACCOUNT_SUSPENDED`, `ACCOUNT_DELETED` | Safe public explanation only | Dedicated safe route/sign-out. |
| Onboarding | `USERNAME_TAKEN`, `USERNAME_LOCKED` | Entered username where allowed | Inline correction or one-time-state explanation. |
| Authorization/entitlement | `AUTHORIZATION_FENCE_REJECTED`, `ENTITLEMENT_BINDING_CONFLICT`, `PORTFOLIO_READ_ONLY`, `GENERATION_VARIANT_LOCKED` | Last confirmed artifact/state | Refetch `/me` and session; suppress forbidden mutation. |
| Concurrency | stale session/revision/CAS conflict | Local unsent draft | Refetch; explain that another tab changed the source; explicit resubmit. |
| Durable stage | `needs_attention`, failed/cancelled job | Approved upstream artifact and saved input | Supported retry/restart only. |
| Provider availability | credit/provider unavailable | Current session/auth | Honest temporary message; do not sign out or loop. |
| Client/network | timeout, offline, render exception | Last confirmed surface | Banner, bounded retry, error boundary/reload. |
| Unsupported contract | unknown status/required field | Safe shell and support reference | Refetch/reload; never infer success. |

Privacy rules:

- never put tokens, resume text, raw intake, model prompts, raw job payloads, or
  complete private state into diagnostics, URLs, BroadcastChannel messages, or
  error copy;
- final artifact copy controls are field-whitelisted and exclude intake/auth/job
  data;
- generated content is untrusted; render Markdown as safe text/allowed markup;
  never inject arbitrary HTML; and
- keep provider/storage/path/hash details in developer-only surfaces.

## 7. Screen-to-contract map

Use this map to plan the redesign screen by screen. A screen is not complete
until its row has a source anchor and a proof.

| Screen posture | Required data | Allowed primary actions | Must remain true |
| --- | --- | --- | --- |
| Auth resolving | Public shell only | Wait/retry where supported | No private placeholder or protected product request before valid auth. |
| Sign in | Public auth config | Continue with Google | PKCE callback and account selection behavior remain intact. |
| Admission denied/unavailable | Safe auth error | Sign out/switch account | No portfolio flash; no retry loop for terminal admission. |
| Username onboarding | `/me` onboarding state | Claim username | Server validates; conflict keeps input and focus. |
| Empty portfolio | `/me` entitlement | Start portfolio/intake | No fake project dashboard; do not call stage API before intake. |
| Discovery input | Discovery available/input view | Paste notes, answer/skip question, create brief | Question IDs, answer modes, draft preservation, and server revision remain intact. |
| Discovery working | Stage/job view | Check again, stop where supported | Durable work continues if user leaves; no percentage/ETA. |
| Discovery review | Safe brief artifact | Revise, approve-and-start Content | Approval is server-backed; no optimistic completion. |
| Content available/working | Content adapter/job | Start/stop | Upstream Discovery gate and semantic progress remain visible. |
| Content review/complete | Safe Content artifact | Revise, approve, continue to Design | Approval does not silently start Design. |
| Design available/working | Design adapter/job | Start/stop | Upstream Content gate and semantic progress remain visible. |
| Design review/complete | Safe Design artifact | Revise, approve | Approval is terminal for current `/app`; no Build Preparation call. |
| Needs attention | Safe error + upstream preserved | Supported retry/refetch | Do not erase approved upstream work or invent a recovery action. |
| Read-only portfolio | `/me.read_only`, approved artifacts | Read/copy/navigate | All mutation controls are absent or disabled with an honest reason. |
| Admin console | `/me.role=admin`, paginated admin data | Bounded audited admin actions | Separate permissions, confirmation text, idempotency keys, and no normal-user exposure. |
| Developer harness | Harness-specific projections | Run/acquire/generate/verify/preview controls | Keep raw diagnostics and detailed controls out of normal product. |

## 8. Ledger update template for a new screen/action

Copy this block into the redesign worklog whenever the agent adds or materially
changes a screen:

```md
### [screen or action ID]
- User purpose:
- Route/entry:
- Auth/access prerequisite:
- Server read source:
- Server mutation (method/path/body/headers):
- Stable IDs preserved:
- Backend statuses mapped:
- Normalized UI states:
- Primary/secondary actions and eligibility:
- Poll/reconciliation behavior:
- Error and recovery behavior:
- Private data intentionally omitted:
- Source anchors:
- Automated proof:
- Browser/visual proof:
```

Do not mark a row complete with only a screenshot or only a passing typecheck.
