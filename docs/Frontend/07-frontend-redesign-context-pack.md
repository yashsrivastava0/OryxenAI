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
| Authenticated product | `/app` | `product_shell.html` -> `app-auth-bootstrap.mjs` -> built `frontend/` bundle; legacy `app.js` is the fallback/legacy shell | Attached bearer session; owner/admin server authorization | This is the normal-user redesign target. Keep the bootstrap seam and three-stage boundary. |
| Detached product/developer shell | Detached `/app` plus `/dev` when configured | Detached `/app` uses `pipeline-bootstrap.mjs`; `/dev` uses the developer branch of `app-auth-bootstrap.mjs` and the same compatible product bundle | Anonymous same-origin requests in configured detached mode | Keep detached behavior isolated. Never use it to justify weakening attached auth. |
| Build Preparation diagnostic | `/dev/build-preparation-fixture`, `/build-preparation-fixture`, and `/.../progress` | Jinja shell plus `build-preparation-fixture.js` / `build-preparation-progress.js` | Feature/config gated; detached or admin depending on mode | Preserve as an operational diagnostic. Do not fold it into normal `/app` accidentally. |
| Code Generator development control room | `/dev/code-generator-development`, `/code-generator-development` | Jinja shell plus `code-generator-development.js` and controller/bootstrap modules | Development harness mode; attached admin or detached according to config | Preserve its durable run/plan/acquire/generate/verify/preview controls separately from creator UX. |
| Generated preview | Exposed by Code Generator/preview gateway, not a normal `/app` screen in the current release | Generated-site runtime and, in the development harness, a sandboxed iframe | Verified promoted artifact only | Never show an unpromoted candidate or treat Preview as public publishing. |

The current normal product ends at approved Visual Design Direction. Build
Preparation and Code Generator are implemented backend/development capabilities,
but their controls must remain outside normal `/app` until a separate release
decision adds them.

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
