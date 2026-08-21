# Live preview and deployment

This document specifies how OryxenAI serves the single verified portfolio
preview in local and deployed environments. "Live" means that the stable preview
updates after an atomic promotion; it does not mean exposing generated code while
it is being written.

## Decision

Each portfolio session receives one stable, opaque hostname on a dedicated
registrable preview domain:

```text
https://<opaque-session-host>.<dedicated-preview-domain>/<client-route>
```

The preview domain must be a different registrable domain from the OryxenAI app,
not merely another subdomain of the app's domain. Wildcard DNS and TLS route the
opaque host to the preview gateway. The hostname reveals no user, session,
generation, or build identifier and remains stable across regenerations.

The generated Vite application uses `base: "/"`. Assets are root-relative and
the trusted dependency-free router owns client routes. There is one current
verified preview per session and no user-visible preview history,
alternate-build selector, generation URL, or generation API. Internal immutable
artifacts and receipts exist only for verification, crash recovery, audit, and
configured cleanup.

Unpromoted candidates are available only through a protected verifier endpoint
with service authentication. They are never embedded for the user, opened in a
user tab, or served from the stable preview hostname.

## Runtime topology

The cloud implementation has three small boundaries:

- private object storage holds immutable candidate artifacts, verification
  reports, immutable promotion receipts, and the stable host's active pointer;
- a preview gateway serves only the artifact named by a valid active pointer,
  applies SPA routing and security headers, and fails closed on any receipt/hash
  mismatch; and
- a text/DOM runtime verifier loads candidates through its protected endpoint
  and returns the structured evidence required by
  [Preview, quality, and evaluation](preview-quality-and-evaluation.md).

The application API and worker coordinate generation state but never proxy
portfolio assets. The preview gateway receives no model credentials or
application cookies and cannot read arbitrary session data.

Conceptual private keys are:

```text
preview/
  candidates/<opaque-candidate-id>/<build-hash>/...
  verification/<opaque-candidate-id>/...
  receipts/<promotion-id>.json           # immutable
  hosts/<opaque-session-host>/active.json # one conditional pointer
```

Storage layout is not a product version API. Only `active.json` is reachable
through the stable host, and only indirectly through the gateway.

## Preview lifecycle

A session has one of four preview conditions:

| Condition | Stable host behavior |
| --- | --- |
| no promotion yet | no preview URL is presented; direct access returns a neutral unavailable response |
| active | serves the current verified artifact |
| regenerating | continues serving the same active artifact |
| failed / `needs_attention` | continues serving the same active artifact, or remains unavailable if none has passed |

Starting generation never clears or mutates the active pointer. Planning,
resource acquisition, source generation, build, DOM/runtime, upload, or
promotion failure never replaces it. A new build becomes visible only after
all three gates pass and the promotion protocol completes.

## Crash-safe promotion protocol

Promotion is a resumable state transition, not an overwrite followed by a best-
effort database update:

1. Upload the immutable candidate and reports, then read them back and verify
   type, size, and hash.
2. Recompute promotion integrity from the three passing gate reports and confirm
   that input, plan, resource/dependency ledgers, source, build, profile,
   evidence, and report hashes still describe the current generation.
3. CAS the session from the expected generation revision to
   `pending_promotion`, recording a unique promotion ID, candidate/build hashes,
   expected previous active-pointer ETag (or explicit absence), and all report
   hashes. This durable record is written before visibility changes.
4. Create `receipts/<promotion-id>.json` conditionally with
   `If-None-Match: *`, read it back, and verify its canonical bytes/hash.
5. Recheck the pending token and current input generation, then conditionally
   replace `hosts/<opaque-session-host>/active.json` using the recorded ETag
   (`If-Match`) or absence precondition (`If-None-Match: *`). Read back and
   verify that it names the exact immutable receipt.
6. CAS the session's matching `pending_promotion` token into `active_preview`,
   echoing the exact active receipt and pointer ETag. Only then does the API
   report promotion complete.

Conditional conflict means another worker or generation won; the loser does not
retry as a blind overwrite. A reconciler handles every crash boundary:

- pending record and old pointer: validate freshness and resume the conditional
  pointer step, or abandon the pending record while preserving the old active;
- pointer names the pending receipt but database finalization is absent: verify
  receipt/artifact again and complete the matching CAS;
- database says active but read-back disagrees: fail closed, repair the state
  from the verified receipt/pointer pair, and do not serve an ambiguous object;
- pending candidate is stale, superseded, corrupt, or conflicts with a newer
  token: mark that attempt failed and leave the current active unchanged.

Promotion work is serialized per session. Reconciliation is idempotent and uses
the same preconditions; it never invents a new receipt. Superseded candidates and
old receipts are removed later by configured retention policy, after they are no
longer needed for reconciliation. They are not exposed as user-selectable
builds.

## Gateway routing and isolation

For the stable hostname the gateway:

1. validates the opaque host syntax and reads one valid active pointer and its
   immutable receipt;
2. verifies receipt/artifact hashes before serving;
3. serves exact fingerprinted assets with explicit content types and immutable
   cache policy;
4. returns a real 404 for missing asset paths and never substitutes HTML for an
   asset miss;
5. applies SPA fallback to navigation requests so direct client-route loads work,
   while the application renders its designed unknown-route screen; and
6. serves HTML and active metadata with short/no cache so an atomic promotion is
   observed without changing the hostname.

Traversal, encoded separators, dot segments, control characters, oversized
requests, and unsupported methods are rejected. Preview pages set `noindex`, a
no-referrer policy, restrictive permissions and cross-origin headers, and the
same CSP verified during candidate testing.

The preview origin has no app cookies, secrets, credentials, application API
access, or service-worker scope. The app embeds it in a capability-minimal
cross-origin iframe. The parent accepts `postMessage` only from the exact stable
origin and through a small versioned message schema. External links use safe
new-tab behavior. Any capability such as downloads must be admitted by the site
contract and granted explicitly.

## Local parity

Local development and CI serve the production `dist` artifact on a dedicated
loopback port separate from the FastAPI app, for example:

```text
http://127.0.0.1:<preview-port>/
```

The local gateway is not `vite dev` or `vite preview`. It implements the same
active-receipt check, root Vite base, SPA fallback, asset-miss behavior, content
types, cache semantics, CSP, security headers, and iframe contract as the cloud
gateway. Generated code cannot branch on the adapter. A relaxed local CSP is a
failed parity test, not a developer convenience.

The local port is bound to loopback only, allocated without colliding with the
application port, and recorded in ephemeral developer state. Local candidate
verification uses a separate protected/unguessable endpoint or server instance;
the user-facing local preview still resolves only the current verified receipt.

## Preview UI contract

The application preview surface contains only:

- a route selector generated from the promoted route contract;
- viewport controls for **mobile**, **tablet**, **desktop**, and **fit**;
- refresh, which reloads the current route on the same stable host; and
- open in new tab, which opens that same stable host and route.

The fixed controls correspond to 390x844, 768x1024, and 1440x900; `fit` uses the
available frame and is a convenience, not verification evidence. Selecting a
route performs ordinary application navigation so history behavior remains
real. The UI does not expose source files, candidate frames, generation history,
or alternate builds.

## Progress while generating

The product may show semantic durable-job progress outside the preview iframe:

```text
admitted -> planning -> acquiring resources -> generating foundation
         -> generating routes -> integrating -> building
         -> text/DOM runtime smoke -> promoted
```

Events name completed semantic checkpoints and, where useful, the current route
batch. They do not claim percentages, stream tokens/files, render unverified
code, or simulate a live editor. Refresh reconstructs progress from durable
state. On failure, show the failed phase and a safe explanation while leaving
the active preview untouched.

Only semantic progress is shown. User-visible candidate rendering, hot reload,
and continuously executing generated workspaces are not part of this
architecture because they would add a second meaning of "preview" and weaken
the promoted-only invariant.

## Sample-build parity gate

A checked-in privacy-safe sample site must pass through the same trusted
scaffold, production build, receipt, gateway, and text/DOM runtime-verification
contracts as generated portfolios. CI runs it through both local and cloud
adapters when the cloud profile is enabled and compares semantic reports for:

- root and direct nested-route loads, in-app navigation, back/forward, refresh,
  and the designed unknown route;
- exact asset delivery and a missing-asset 404;
- CSP, security headers, iframe isolation, and absence of unexpected requests;
- mobile/tablet/desktop/fit UI controls and open-in-new-tab URL behavior; and
- active-preview continuity during a failed regeneration plus successful atomic
  replacement after promotion.

Byte-for-byte HTTP responses are not required across adapters; route outcomes,
headers/security policy, content and asset hashes, and verifier assertions are.

## Explicit scope boundary

This design deploys the preview gateway and verifier, not the user's public
portfolio. Public hosting providers, custom domains, analytics, deployment
history, alternate-build activation, and persistent development environments
are outside the Code Generator implementation. They require a separate product
decision and are not optional adapters hidden in this plan.

For the free-service deployment constraints and the exact Docker boundary, see
[Free-host deployment contract](free-host-deployment.md). In particular, free
hosted services must persist preview objects outside the container and must not
be treated as if they provide a free background worker automatically.

## Primary references

- Cloudflare Browser Rendering: [Playwright support](https://developers.cloudflare.com/browser-run/playwright/)
- Cloudflare Workers: [single-page application routing](https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/)
- Vite: [static deployment](https://vite.dev/guide/static-deploy.html)
- MDN: [`iframe` sandboxing](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe)
