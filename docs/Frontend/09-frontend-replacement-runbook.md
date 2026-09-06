# Frontend replacement runbook for AI coding agents

Use this runbook when the visual frontend is being replaced, redesigned, or
ported screen by screen. It is designed for Codex, Claude Code, Cursor,
Antigravity, or another coding agent working in the repository.

The workflow is deliberately evidence-first:

```text
observe -> ledger -> preserve seam -> replace one posture -> test -> browser proof
       -> keep old fallback -> replace next posture -> cut over -> remove only after proof
```

## 0. Operating rules

Before editing:

- read `AGENTS.md`, `DECISIONS.md`, and the three files in this pack;
- inspect `git status --short --branch` and protect unrelated work;
- do not assume a UI document is current—verify backend routes, auth runtime,
  adapters, templates, and tests;
- do not change API/backend behavior as a side effect of a visual task; and
- do not delete the legacy bundle, auth shell, fixtures, admin console, or
  developer harness until the cutover gate explicitly proves they are no longer
  needed.

When a requested design needs unsupported behavior, write the requirement as a
separate proposal and continue with the closest honest existing behavior. Do not
fake streaming, cancellation, publishing, model selection, percentages, or
private reasoning in the UI.

## 1. Search strategy: build the map before the design

Run these searches from the repository root. The exact command syntax may vary
by shell, but the search categories must all be covered.

### A. Find all browser entry points and route shells

```text
rg -n "@(router|.*router)\.(get|post)|RedirectResponse|TemplateResponse|router\.mount" src/oryxenai/web src/oryxenai/auth
rg -n "product-root|auth-root|auth-pending|oryxenai-product-entry|script.*static|link.*stylesheet" src/oryxenai/web src/oryxenai/auth
rg -n "enable_product_preact_shell|pipeline_mode|development_harness_mode|fixture_enabled|code_generator_development" config src/oryxenai
```

Record route, template, bootstrap module, access mode, and feature/config gate
in the route ledger before changing a shell.

### B. Find every product API read and mutation

```text
rg -n "fetch\(|authorizedFetch|OryxenAIProtectedFetch|/api/v1/|Idempotency-Key" frontend/src src/oryxenai/web/static src/oryxenai/auth/static
rg -n "@router\.(get|post|put|delete)|APIRouter\(prefix" src/oryxenai/api src/oryxenai/auth
```

For each request, record HTTP method, path, request body, header requirements,
response projection, stable IDs, expected errors, and whether it is product or
developer-only. Search both client and server; never derive a contract from a
button label.

### C. Find state/status and adapter boundaries

```text
rg -n "status|needs_attention|approved|not_started|questions_|brief_|build_running|content_review|design_review|queued|planning|acquiring|generating|verifying|preview_pending|ready" frontend/src src/oryxenai/agents src/oryxenai/api/routes
rg -n "adapt[A-Z]|StageState|unsupported|latest_error|job_id|session_revision" frontend/src
```

Build the status table from executable state definitions and adapters. Do not
let components branch on backend enum strings after the replacement.

### D. Find auth, storage, and lifecycle hooks

```text
rg -n "createAuthorizedFetch|resolveAuthenticatedContext|refreshSession|401|signOut|clearPrivateState|safeRelativePath|canonicalDestination" src/oryxenai/auth src/oryxenai/web frontend/src
rg -n "sessionStorage|localStorage|BroadcastChannel|visibilitychange|setTimeout|setInterval|AbortController|Idempotency" src/oryxenai/auth src/oryxenai/web frontend/src
```

Every match must be classified as security boundary, state persistence,
reconciliation, diagnostics, or visual behavior. Security/lifecycle matches are
not styling details.

### E. Find test and browser proof anchors

```text
rg --files frontend/src/test tests/frontend tests/api tests/unit tests/integration tests/worker
rg -n "auth|onboarding|admin|stage|answer|approve|revise|stop|poll|multi-tab|read-only|product boundary|visual|accessibility|performance" frontend/src/test tests/frontend
```

Keep or port the behavioral tests before deleting the old component. Add a test
when the new screen changes a contract boundary; do not rely on visual snapshots
to prove auth or durable state.

## 2. Baseline before the first edit

Capture a before-state packet in the task notes (not in source control if it
contains private data):

1. clean/dirty Git status and the exact files owned by this redesign;
2. `npm run typecheck`, `npm test`, and `npm run build` from `frontend/`;
3. relevant backend/auth tests and the configured local health/doctor checks;
4. screenshots or browser notes for auth resolving, sign-in, onboarding, empty
   studio, Discovery question, Discovery review, Content review, Design review,
   attention, admin, and each developer harness that must remain functional;
5. one trace of a refresh during a working job, one sign-out, one failed request,
   and one second-tab mutation; and
6. the built asset path/manifest behavior and the current fallback behavior.

If the baseline fails, record the failure and distinguish it from the redesign.
Do not “fix” unrelated failures while replacing the UI unless the user asks.

## 3. Build the contract ledger before building the new look

Fill [08-frontend-contract-ledger.md](08-frontend-contract-ledger.md) for any
row that is missing or changed. At minimum, every screen must name:

- route and bootstrap entry;
- auth and role/access prerequisite;
- server read projection;
- server mutation and idempotency behavior;
- stage status mapping and action eligibility;
- refresh/polling/visibility/multi-tab behavior;
- error/recovery behavior;
- private fields intentionally not rendered; and
- automated plus browser proof.

This is the mechanism that lets a new visual design correlate with the working
frontend. The correlation key is not a CSS class. It is the tuple:

```text
(route, auth state, session/stage ID, durable status, user action ID, proof)
```

## 4. Preserve the shell seam first

Implement the new product shell behind the existing server/bootstrap boundary
before replacing stage screens.

The first replacement slice must prove:

- attached `/app` waits for auth and `/api/v1/me` before private content;
- signed-out users make no protected product request;
- a valid session reaches the new shell without a sign-in flash;
- one 401 refreshes and retries once; a second 401 clears private UI and routes to
  sign-in;
- onboarding, denial, unavailable-account, and normal-admin redirects remain
  correct;
- detached mode still uses the anonymous same-origin boundary;
- `boot`, `stop`, and `restart` work repeatedly without duplicate listeners or
  pollers; and
- the `body.auth-pending` structural hide rule has an explicit home in the new
  CSS layer.

Do not mount a second competing auth controller inside the new framework.
Reuse the existing `auth-runtime.mjs` and bootstrap entry unless a separate
security change is being reviewed.

## 5. Replace screen by screen, in dependency order

### Slice 1: public/auth screens

Replace visual markup/styles for resolving, sign-in, callback, denial,
unavailable, onboarding, and admin one at a time. Keep the existing controller
DOM hooks or update the controller and its tests in the same change.

Proof required:

- callback query artifacts are removed;
- unsafe configured destinations are rejected;
- no private content flashes on signed-out/denied/suspended paths;
- username conflict retains the value and provides focusable error feedback;
- normal users cannot see admin content; and
- sign-out stops product activity and removes private client state.

### Slice 2: empty and returning `/app` shell

Implement the app frame, account controls, connection banner, journey, and
start/resume posture without changing stage behavior. The shell must derive the
portfolio session from `/me`, not from an arbitrary URL or a user-created project
list.

Proof required:

- no session -> one clear start surface;
- existing session -> canonical server state after refresh;
- invalid/locked stage URL -> safe reachable-stage fallback;
- read-only `/me` -> mutation controls absent/suppressed; and
- the last confirmed content remains visible during network loss.

### Slice 3: Discovery

Port the Discovery adapter and current behaviors before polishing the visual
conversation:

- start from plain text intake;
- question presentation by server `kind` and stable ID;
- answer modes `answered` and `skipped`;
- question-scoped draft persistence;
- working/queued/stalled explanation and supported stop/check action;
- brief review as a safe document;
- revision keeping the old artifact until new durable state arrives; and
- approval plus the existing explicit Content-start handoff.

Proof required:

- answer option clicks send API action modes rather than presentation kinds;
- refresh never submits an answer to the wrong question;
- a failed request keeps the draft and allows retry;
- an unknown Discovery status becomes unsupported, not complete; and
- no raw intake/auth/job data leaks through artifact copy or diagnostics.

### Slice 4: Content Architect

Port the stage as a document review, not an unsupported chat surface. Preserve
the upstream Discovery gate, `content_review`/`approved` distinction, route and
section IDs, revision behavior, approval, stop, and the explicit handoff to the
Design start surface.

Proof required:

- Content cannot start before approved Discovery;
- long route/section artifacts remain readable and bounded;
- Content approval does not silently start Design;
- the known public-scope approval failure leads to the bounded safe revision
  path, not a false approval; and
- warnings and unresolved issues remain visible when they change user action.

### Slice 5: Visual Design Director

Port visual direction as a reviewable artifact: creative thesis, visual language,
page directions, and safe adaptation notes. Preserve the Content gate, revision,
approval, stop, and terminal creative-handoff posture.

Proof required:

- Design cannot start before approved Content;
- route IDs remain correlated with Content routes;
- unknown resource/status data fails closed;
- approval never calls Build Preparation; and
- a complete Design state remains readable and read-only after refresh.

### Slice 6: developer/admin surfaces

Treat admin, Build Preparation fixture, legacy `/dev`, and Code Generator
development as separate migrations. Their detailed controls are valuable for
operators and evaluators but are not normal creator UX.

For every such surface, preserve its own entry route, config gate, auth mode,
endpoint family, durable run identifier, URL restoration behavior, and teardown.
Do not reuse a normal-user adapter for a raw diagnostic projection merely because
both contain a field named `status`.

## 6. Use a dual-run/cutover strategy

The repository already has a useful safety shape: the server can serve a built
product bundle, and the legacy product shell remains a fallback/legacy surface.
Use that shape while migrating.

Recommended cutover sequence:

1. Add the new shell behind the existing product-entry/feature boundary.
2. Keep the old bundle buildable and bootable.
3. Migrate one posture or stage at a time; run old and new against the same
   deterministic fixture responses where possible.
4. Compare contract events, not DOM structure: route, action ID, request path,
   request body, resulting status, session revision, and safe error state.
5. Browser-test the new path at desktop, mobile, keyboard-only, reduced-motion,
   offline/reconnect, and two-tab conditions.
6. Switch the default only after the acceptance gates pass.
7. Remove superseded normal-product files only after rollback is no longer needed
   and the change is separately reviewed. Never remove developer fixtures/harnesses
   as cleanup by implication.

If a feature flag or alternate route is introduced for canarying, keep it
server-configured and local/reviewed. Do not accept a client query parameter as
an authorization or rollout decision.

## 7. Verification gates

### Contract gate

- Every current route and surface has a ledger row.
- Every product API call is present in the new client or intentionally excluded
  with a reason.
- No new endpoint, backend status, or user action was invented silently.
- Stable IDs, session revision, idempotency, and read-only behavior are preserved.

### Auth/security gate

- Signed-out, callback, denied, unavailable, onboarding, normal, admin, and
  detached flows each have a browser or module test.
- No private data or protected request occurs before auth resolution.
- Bearer tokens never enter screen components, URLs, diagnostics, or logs.
- One-refresh-on-401 and second-401 invalidation still pass.
- Logout tears down polling/listeners/frames and clears private state.

### Agent/state gate

- All Discovery, Content, and Design statuses map through adapters.
- Unknown/malformed required states show `unsupported` and cannot approve/start.
- Working states poll only while visible and stop at stable states.
- Revision/approval actions reconcile server state instead of assuming success.
- The existing Discovery-to-Content gesture and later explicit handoffs remain
  semantically unchanged.

### Resilience gate

- Refresh during each working stage restores the durable state.
- Network loss keeps the last confirmed view and offers bounded recovery.
- Background-tab return refetches before presenting a new state.
- A second tab invalidates/refetches without overwriting an unsent draft.
- A slow old response cannot overwrite a newer confirmed mutation.

### Accessibility/visual gate

- Keyboard focus, labels, roles, live announcements, dialogs, and error focus
  remain usable.
- Reduced motion preserves information and removes loops/travel effects.
- Long artifacts, question forms, approval controls, and attention recovery work
  at mobile width and zoom.
- Visual snapshots supplement behavior tests; they never replace them.

### Build/release gate

- `npm run typecheck`, `npm test`, and `npm run build` pass from `frontend/`.
- Relevant backend/auth/frontend tests pass with the configured test command.
- Built assets are served through the manifest path, not a hand-edited output.
- The old fallback/rollback path is still available until cutover is approved.
- Review `git diff --check`, the staged patch, and the final route/contract ledger.

## 8. Copy/paste instruction for the coding agent

```text
You are replacing the OryxenAI frontend under a contract-preserving migration.
Read AGENTS.md, DECISIONS.md, docs/Frontend/07-frontend-redesign-context-pack.md,
08-frontend-contract-ledger.md, and 09-frontend-replacement-runbook.md first.

Before coding, audit routes/templates/bootstrap/auth runtime/API clients/adapters/
state machines/tests with rg and fill the ledger for any missing row. Preserve
the tuple (route, auth state, session/stage ID, durable status, user action ID,
proof). Change visual design freely only after that tuple is mapped.

Keep attached auth, detached development, admin, Build Preparation fixture, and
Code Generator development surfaces separate. Keep boot(options), stop(),
restart(options), #product-root, the auth-pending hide rule, authorizedFetch,
one-refresh-on-401, server-authoritative state, stable IDs, session revision,
idempotency, polling, cross-tab invalidation, read-only enforcement, and safe
artifact rendering. Components must consume adapters, not raw backend statuses.

Migrate in slices: auth -> app shell -> Discovery -> Content -> Design ->
admin/developer surfaces. Keep the old fallback buildable. After each slice run
typecheck/tests/build plus the relevant auth/state/browser proof. Do not invent
endpoints, auto-chain stages, expose private/model/job/storage internals, or
delete legacy/harness code until the cutover gate proves it is safe.
```
