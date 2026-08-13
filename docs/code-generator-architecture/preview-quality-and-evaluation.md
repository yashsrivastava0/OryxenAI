# Preview, quality, and evaluation

This document defines the minimum blocking evidence required before a generated
candidate can replace the current preview. It follows D-015: verification is
text, source, compiler, artifact, DOM, and runtime based.

There is no vision model, screenshot capture, animation-frame capture, pixel
comparison, visual regression image, or subjective visual-quality gate.

## What "quality" means without vision

The architecture separates two concerns:

- **Design quality is generated proactively.** The approved visual direction is
  converted into explicit tokens, composition rules, distinctive moves,
  resource placements, route plans, responsive behavior, and shared-component
  contracts. Foundation, route, and integration operations implement and
  reconcile those contracts while source is still easy to change.
- **Correctness is verified deterministically.** Source policy, types, build
  output, routes, public content, declared interactions, focus, accessible
  states, requests, assets, and runtime errors are checked before promotion.

The system can prove that a named design move is planned, mapped to source, and
implemented with its required resources/classes/components. It cannot prove
that the rendered result is beautiful, balanced, or fashionable without
looking at pixels. D-015 accepts that tradeoff and invests in better generation
contexts rather than pretending a non-visual check can judge appearance.

## Candidate identity

Verification binds one immutable identity:

```text
CandidateIdentity
  input_receipt_hash
  site_plan_hash
  work_graph_hash
  resource_ledger_hash
  dependency_ledger_hash
  source_checkpoint_hash
  source_manifest_hash
  scaffold_toolchain_profile_hash
  verification_profile_hash
```

The build and final report add their own hashes. Evidence from a different
input, plan, ledger, source tree, toolchain, or build is never reused.

## Lean VerificationPlan

Trusted code derives a small `VerificationPlan` from the site contract,
`SitePlan`, generated route/interaction/acceptance manifests, and configured
runtime profile.

```text
VerificationPlan
  schema_version
  based_on_candidate_identity
  source_checks[]
  build_checks[]
  runtime_journeys[]
    journey_id
    route_id?
    start_path
    viewport_profile
    motion_profile
    steps[]
      action
      target?
      expected_url?
      expected_content_ids[]
      expected_accessible_state?
  expected_local_resources[]
  expected_check_ids[]
```

This is not a route × viewport × motion × frame cross-product.

The plan includes:

- one direct-load journey for every public route;
- one internal-navigation journey covering each navigation edge without
  duplicating routes unnecessarily;
- one back/forward and one designed unknown-route journey for the site;
- every declared interaction at least once in a relevant route journey;
- narrow and wide journeys only where responsive DOM/overflow/interaction
  behavior differs;
- reduced-motion journeys only for routes or interactions that declare motion;
- expected public content/fact/criterion IDs;
- all locally bound resources used by source; and
- configured keyboard, focus, accessible-name/state, and request assertions.

Trusted code owns check IDs. Models cannot delete a failing journey or mark it
not applicable.

## Gate 1 — source and contract integrity

Gate 1 runs on the complete source checkpoint and generated manifests.

Blocking checks:

- all paths are safe and inside trusted/model ownership;
- every local import resolves and every package import exists in the dependency
  ledger;
- package, lock, Vite, TypeScript, runtime, and generated-manifest files have
  only their trusted owners;
- route registry exactly matches the approved route graph;
- all required content, fact, criterion, interaction, and resource IDs map to
  source;
- every locally referenced image, font, icon, and vendor component has an
  admitted receipt and safe path;
- no arbitrary remote URL, runtime fetch, remote font/image/script/style,
  service worker, secret/environment access, dynamic code execution, or
  unsupported browser capability exists;
- no fabricated portfolio fact, lorem ipsum, TODO, placeholder link, empty
  section, fake form success, or interactive-looking control without a declared
  outcome remains;
- user-media and forbidden-subject policy is preserved; and
- the integrator's design-implementation report maps every approved distinctive
  move and global visual rule to concrete owned source.

Mapping a design rule to source is not a visual verdict. It only prevents the
generator from silently omitting its own approved plan.

## Gate 2 — type, build, and artifact integrity

Gate 2 starts from a clean workspace:

1. recreate `node_modules` from the exact receipt-bound manifest, lockfile,
   toolchain profile, and configured cache;
2. run configured formatting/parser checks;
3. run TypeScript type checking;
4. run the trusted production Vite build;
5. inspect the production entry, chunks, CSS, and local resources;
6. reject missing or extra build references, disallowed source maps/debug
   output, unsupported media types, and configured size-policy violations; and
7. create a deterministic per-file build manifest.

The Vite development server, hot reload, an old installed tree, or a prior
successful `dist` directory is never accepted as build evidence.

Any missing dependency/cache entry, toolchain mismatch, or trusted-command
failure is classified separately from generated-source errors. The repair model
does not invent infrastructure fixes.

## Gate 3 — text/DOM/runtime smoke

The candidate gateway serves the exact production artifact. A headless browser
executes `VerificationPlan.runtime_journeys` and emits structured results only.
Screenshot and video APIs are disabled by policy, and no image artifact is
created.

Each relevant journey checks:

- requested path and final URL;
- document title plus expected heading, landmark, and public content IDs;
- direct route load independent of in-app navigation;
- internal navigation, browser back/forward, and designed unknown-route
  behavior;
- declared interaction state, content, URL, download/copy outcome, focus, and
  accessible state;
- keyboard reachability and absence of focus traps for required controls;
- accessible names and states for required interactive elements;
- reduced-motion media-query behavior without missing content or outcomes;
- numeric horizontal-overflow and element-boundary assertions where the
  responsive plan requires them;
- uncaught page errors, rejected promises, blocking console errors, and CSP
  violations;
- local asset status and content type; and
- absence of unexpected or outbound requests.

The runner may inspect the accessibility tree, computed styles required for a
specific deterministic assertion, bounding boxes, media-query state, and DOM
text. Those are structured runtime values, not rendered-image evidence.

Automated accessibility checks are a blocking baseline for obvious functional
problems. They are not a claim of full accessibility certification.

## Promotion integrity

Promotion is not another quality gate. It is the atomicity check after all three
gates pass.

Trusted code requires:

- the expected verification check-ID set equals the executed passing set;
- all gate results bind the same candidate and build hashes;
- zero unresolved blocking diagnostics;
- immutable candidate/report upload and read-back success;
- current upstream/input identity still matches;
- conditional promotion receipt and active-pointer writes succeed; and
- final session compare-and-swap activates that exact receipt.

Counts alone are insufficient; check identity and candidate hashes must match.
Any ambiguity preserves the previous active preview.

## Blocking versus advisory findings

The contract uses only two effects:

| Effect | Meaning |
| --- | --- |
| **blocking** | The source contract, build, route, public truth, required resource, declared interaction, accessible outcome, security rule, or runtime execution is demonstrably wrong or incomplete. Candidate cannot promote. |
| **advisory** | A deterministic metric or heuristic suggests possible polish, density, bundle-size, or maintainability improvement but does not prove a user-facing contract failure. It is recorded and does not consume repair budget by itself. |

There is no numerical visual score and no averaging. A source/build/runtime
failure cannot be outweighed by strengths elsewhere.

Examples that block:

- missing approved route/content/fact/criterion mapping;
- unresolved import or type/build failure;
- missing local font/image/component resource;
- direct-route or navigation failure;
- uncaught runtime error or unexpected network request;
- broken declared interaction;
- inaccessible required control or lost required content under reduced motion;
- obvious horizontal overflow where the responsive contract forbids it; and
- attempted configuration, dependency, security, provenance, or truth escape.

Examples that remain advisory:

- a bundle approaching but not exceeding configured policy;
- repeated source structure that does not violate a shared-component contract;
- a design token that is declared but safely unused; or
- a possible visual-polish concern that cannot be established from text/DOM
  evidence.

Terms such as "ugly," "generic," "unbalanced," or "premium" are not
deterministic evidence and never appear as automated blockers.

## Repair evidence

All blocking findings in the current check pass are normalized before repair.
The repairer receives:

- gate/check ID, route/interaction ID, expected and observed result;
- compiler/build/console/request/accessibility error code and normalized text;
- owned file, symbol, import chain, or DOM locator when available;
- complete implicated source plus bounded relevant dependencies;
- affected plan, resource, dependency, and shared-API slices;
- allowed paths and checks that must pass afterward; and
- prior repair fingerprints and strategy summaries.

No screenshot is needed for these defects. The model fixes TypeScript, imports,
asset bindings, route code, DOM structure, interaction state, focus handling,
accessible semantics, CSS overflow, or reduced-motion logic from concrete text
and source evidence.

After an accepted repair, run the cheapest affected checks immediately and all
three final gates before promotion. Repair remains bounded by configured
per-unit and per-generation ceilings. A recurrence may receive a wider source
slice and a simplification instruction while budget remains; exhaustion writes
one actionable terminal report.

## Required regression coverage

Tests must cover:

- exact derivation of route, content, interaction, resource, narrow/wide, and
  reduced-motion journeys without a cross-product explosion;
- missing, duplicate, renamed, stale, or cross-build check evidence;
- route direct load, internal navigation, back/forward, unknown route, and
  missing-asset behavior under production gateway rules;
- public-content, console, page, request, CSP, keyboard, focus, accessible-name/
  state, reduced-motion, and overflow failures;
- source-policy, import, dependency-ledger, resource-ledger, package/lock
  ownership, placeholder, fabricated-fact, and runtime-network failures;
- clean dependency installation and proof that an old `node_modules`/`dist`
  cannot satisfy Gate 2;
- compiler/DOM diagnostic normalization, scoped correction, recurrence,
  simplification, exhaustion, and receipt reuse;
- immutable artifact/report hashes, promotion races, worker crash at each
  promotion step, staleness, and previous-preview retention; and
- a hard assertion that verifier/model request logs and output trees contain no
  screenshot, video, frame, typed-image, vision-review, or visual-comparison
  operation/artifact.

## Security baseline

Preview content runs on a registrably separate origin with no application
cookies, credentials, secrets, service-worker scope, or application API access.
The generated target is local-resource-only and uses the configured restrictive
content-security policy. Changing runtime network authority requires a
target-contract, gateway, verifier, and threat-model decision; it cannot be
introduced by a resource request or prompt.
