# OryxenAI — Decisions & Open Issues

Architecture Decision Record (ADR) log of architectural choices, trade-offs, and invariants. Read before making design changes.

**Policy:**
- Log only real architectural decisions with concrete trade-offs (not routine code changes).
- Maintain reverse-chronological order (newest first under `## Active Decisions`). Entry IDs (`D-001`, `D-002`, ...) are permanent and never reused.
- Keep entries high-density, concise, and machine-readable for AI agents.

**Entry Template:**
```markdown
## D-0XX — <short decision title>

- **Date & Time:** YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>)
- **Status:** open | decided-not-yet-implemented | decided-implemented | superseded-by-D-0YY
- **Context:** Constraint or problem forcing a choice.
- **Decision:** What was chosen, stated concretely.
- **Rejected alternatives:** What else was considered and specifically why rejected.
- **Consequence:** Forward implications, trade-offs, and invariants.
```

---

## Active Decisions

## D-049 - Temporarily detach authentication from the main pipeline

- **Date & Time:** 2026-08-25 16:30 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Authentication is implemented, but repeated login, token refresh,
  and account-switching friction slows development of the main Discovery to
  Build Preparation workflow. Browser-held state also allowed stale errors and
  stage state to survive refreshes.
- **Decision:** Add a config-driven `auth.pipeline_mode` with `detached` and
  `attached` values. Local development uses `detached`; Docker/test and
  production-like environments remain `attached`. Detached mode applies only
  to the main pipeline session and its four stage APIs. Admin, authenticated
  product, fixture, run, and Code Generator surfaces remain protected. Detached
  sessions are ownerless but explicitly classified, persist durable state in
  PostgreSQL, and expose no bearer-auth or Supabase browser bootstrap. The
  browser stores only an opaque session UUID and rehydrates state from the API;
  all API/HTML responses use no-store cache policy.
- **Rejected alternatives:** Disabling authentication globally, making the
  browser authoritative, storing pipeline JSON in local/session storage,
  preserving stale sessions after a restart, or letting restart reuse the old
  session row. Those choices would expose protected development surfaces,
  reproduce the stale-refresh bug, or leave jobs/artifacts and agent state
  attached to the wrong run.
- **Consequence:** A visible Restart Pipeline action is available throughout
  the detached workspace. It fences old jobs, marks the old session pending
  deletion, removes exact session-scoped database children and external/local
  Build Preparation artifacts, then creates a fresh detached session at
  revision 0 with empty state. Cleanup failures are retryable and do not claim
  a successful reset. Reattaching authentication later is a configuration and
  browser-bootstrap change, while the durable session/restart boundary remains.

## D-048 - Make Google registration open by deployment configuration

- **Date & Time:** 2026-08-24 18:30 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** The initial three-account allowlist was useful for provider setup,
  but it also blocked legitimate Google users and was confused with Google's
  separate OAuth test-user restriction. The product needs simple public
  registration while retaining a hard normal-user capacity limit.
- **Decision:** Add a reviewed `auth.admission_mode` with `open` and
  `allowlist` values. The product and Docker deployment use `open`: any
  verified Google identity may be admitted as a normal user until the database
  capacity of 15 is full. Bootstrap administrators remain controlled by the
  server-only admin email list and do not consume capacity. Restricted
  environments can select `allowlist`, which requires
  `ORYXENAI_ALLOWED_USER_EMAILS`. Keep provider-side Google Testing/publishing
  configuration separate from application admission.
- **Rejected alternatives:** Removing the server-side capacity gate, trusting a
  browser toggle, adding passwords/OTP, or silently treating an OAuth app in
  Google's Testing state as public. A full HttpOnly-cookie SSR conversion was
  also deferred because this Jinja/vanilla browser client needs a simple
  bearer-authenticated API boundary.
- **Consequence:** New users can onboard without a code change or per-email
  allowlist update when Google OAuth is published for the deployment. Browser
  sessions still use Supabase's managed PKCE refresh flow; tokens remain
  client-held by design and are never rendered in HTML, URLs, logs, or API
  responses. The owner must publish the Google OAuth app and add production
  origins/redirects before arbitrary external accounts can complete Google
  sign-in.

## D-047 - Complete Phase 4 administrator lifecycle with resumable local authority

- **Date & Time:** 2026-08-24 14:40 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Phase 3 left administrator lifecycle, deletion/reset safety, and
  audit authority deferred. Destructive work must remain bounded, resumable,
  and database-authoritative while the provider identity and temporary preview
  stores are external systems.
- **Decision:** Add one linear Alembic revision for lifecycle state, safe admin
  operations/audit, and identity/project tombstones. Require active onboarded
  administrators, explicit target confirmation, bounded idempotency keys, and
  short transactions. Fence queued/running work before cleanup; remove only
  exact session-scoped preview, artifact, and local run paths; call the
  server-only Supabase Admin API for provider suspend/restore/delete; and
  require explicit audited readmission after deletion. Preserve normal-user
  entitlement semantics across promotion/demotion and permit reset only after
  verified project deletion.
- **Rejected alternatives:** Browser-only admin state, provider metadata roles,
  broad storage-prefix deletion, automatic deleted-identity readmission,
  SECURITY DEFINER shortcuts, unbounded admin lists, and treating a failed
  provider/storage call as a completed local deletion.
- **Consequence:** Administrator actions are visible as safe local operation
  records, retryable failures can resume without inventing a second operation,
  deleted identities cannot re-enter through ordinary JIT admission, and the
  implementation is complete through local Phase 4. Owner-completed browser
  acceptance and production cloud deployment remain separate gates.

## D-043 - Supabase Google identity with database-authoritative authorization

- **Date & Time:** 2026-08-23 20:48 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** OryxenAI needs a minimal Google-only login for a small allowlisted deployment without owning passwords or adding a third identity service beside managed PostgreSQL and future AWS hosting. Login alone is insufficient because all current session/stage/run routes are globally ID-addressable, durable jobs outlive browser tokens, normal users get one successful portfolio, and two administrators require cross-project authority. The owner configured and redaction-safely verified one Supabase/Google development project and deliberately deferred production/AWS resources.
- **Decision:** Use Supabase Auth as the only identity provider and Google as the only v1 sign-in method. FastAPI verifies exact Supabase JWT issuer/audience/signature/expiry/subject and resolves verified first-login identity before applying a server-side email allowlist. PostgreSQL stores immutable Supabase subject mapping, unique username, role/status, a config-driven maximum of 15 normal accounts, two bootstrap administrators outside that capacity, resource ownership, one-session/one-variant/one-promoted-success entitlement, durable owner/actor bindings, and admin audit. Existing unowned sessions are legacy/admin-only. Roles and authorization never come from `user_metadata`, browser state, query parameters, or email ownership. Normal retries reuse the bound variant; admins are entitlement-unlimited but remain subject to workflow safety and external provider spending limits. AWS and production Supabase/Google setup are separate later deployment work.
- **Rejected alternatives:** Clerk plus Supabase, because it adds a second token/user lifecycle and another service; public first-come registration, because strangers could consume model credit and the 15 slots; application passwords/OTP/phone or self-built OAuth/session handling, because they add recovery and abuse/security ownership; client metadata roles or frontend-only quota; assigning legacy sessions to the first login; one deployment per generated portfolio; and creating AWS early enough to waste its promotional clock.
- **Consequence:** The local implementation provides config/secret validation, a pinned Supabase browser client, server JWT/JWKS verification, Alembic-owned user/capacity/entitlement/ownership/audit schema, route/repository ownership, worker finalization fencing, Google/onboarding/admin UI, deterministic tests, and fail-closed production configuration. An authenticated but unapproved identity creates no application or generation state. Owner-completed live browser acceptance and production deployment remain separate gates; no AWS resource is authorized by this decision.

## D-044 - Execute authentication Phase 1 without advancing authorization phases

- **Date & Time:** 2026-08-23 23:45 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** The owner authorized the first execution phase of D-043 in a dirty multi-agent checkout. The authentication foundation must be independently testable and useful while existing portfolio resources remain unowned; silently adding ownership, entitlements, worker fencing, or administrator lifecycle would cross the explicit phase boundary.
- **Decision:** Phase 1 consists of Supabase Google-only session restoration, server-side asymmetric JWT/provider verification, allowlisted just-in-time `app_users` admission, two bootstrap administrators outside the 15-normal-user capacity row, unique username onboarding, `/api/v1/me`, and a temporary direct HTML route/controller shell. The existing portfolio APIs and generated-preview authorization remain unchanged until their explicitly authorized later phases. No production cloud resource is created.
- **Rejected alternatives:** Treating `/me` as complete portfolio authorization; auto-chaining the existing developer UI into authenticated product routes; deriving role from email on every returning request or from `user_metadata`; and implementing Phase 2-4 ownership/lifecycle work opportunistically in the Phase 1 commit.
- **Consequence:** Phase 1 can prove identity, admission, refresh, logout, route progression, and local database constraints without claiming production authorization. Phase 2 must retrofit owner/admin dependencies and resource scoping before existing portfolio APIs are suitable for normal-user production use.

## D-045 - Execute Phase 2 as session ownership and API authorization retrofit

- **Date & Time:** 2026-08-24 02:00 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Phase 1 established the Supabase identity boundary while existing portfolio sessions and nested APIs remained globally ID-addressable. The next bounded phase must isolate normal users without silently adding entitlement, worker, administrator-lifecycle, or deployment work.
- **Decision:** Add `portfolio_sessions.owner_user_id` with `ON DELETE RESTRICT` and an explicit fail-closed `legacy_quarantined` state in one Alembic revision. Quarantine every pre-Phase-2 session, create new product sessions only from the authenticated local user, and centralize active/onboarded/owner/admin decisions in FastAPI dependencies and `PortfolioAccess`. Normal SQL queries are owner-scoped and exclude legacy rows; active onboarded admins can operate across owned and legacy sessions. Protect every existing session-nested API family, make system/model/development/fixture/mock surfaces admin-only or production-absent, and require the bearer-authenticated product/developer browser boot to resolve `/me` before protected workspace code.
- **Rejected alternatives:** Assigning legacy rows to the first login; trusting session IDs, email, browser storage, request bodies, or JSONB for ownership; filtering global queries in Python; adding owner/actor fields to jobs/runs before the worker-fencing phase; enabling browser Data API policies; or leaving developer endpoints mounted behind runtime-only 404s.
- **Consequence:** Phase 2 proves cross-user session isolation and admin legacy access while preserving existing stage state machines. Multiple normal-owned sessions remain temporarily allowed until Phase 3 entitlement; durable owner/actor bindings and worker finalization fencing remain deferred to Phase 3, administrator lifecycle/audit to Phase 4, and no production cloud resource is created.

## D-046 - Enforce Phase 3 entitlement and worker safety in PostgreSQL-backed durable state

- **Date & Time:** 2026-08-24 04:00 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Phase 2 isolated session ownership, but normal users could still create multiple sessions/variants and durable jobs/runs did not retain enough local identity to reject late work after ownership or entitlement changes. Provider/model work also needed one cross-worker credit lane and a crash-safe success boundary.
- **Decision:** Add one `portfolio_entitlements` row per active normal user in migration `0016_auth_entitlements_worker_fencing`, lock it for session/generation/finalization mutations, and bind one owned session, one production Code Generator run/variant, and one verified promoted success. Persist local session/owner/actor/context snapshots on portfolio `agent_runs`, production Code Generator runs, and background jobs. Reauthorize those snapshots immediately before portfolio work, successor enqueue, preview promotion, and central finalization. Classify all registered model-calling jobs through a closed policy and enforce one PostgreSQL `model-generation` lane with a partial unique running index. Keep administrators entitlement-unlimited but subject to ownership/state/quality/provider gates; leave lifecycle, reset/delete, audit, live multi-account acceptance, and deployment to Phase 4.
- **Rejected alternatives:** Browser/local-storage quota, an in-process worker mutex, email/username ownership snapshots, trusting job payloads, consuming success at run/source/build/pending-promotion time, creating a new normal variant on retry, holding entitlement locks over provider/storage work, or adding Supabase Admin API/SECURITY DEFINER shortcuts.
- **Consequence:** Normal session creation and Code Generator start/retry are server-idempotent; failed or credit-exhausted work preserves the same variant and leaves success unconsumed; exact preview promotion/reconciliation consumes success once and makes normal mutations read-only. A changed owner/status/entitlement/lease fails closed with a safe non-retryable fence error, while non-credit system jobs can run alongside the global generation lane.

## D-042 - Stable retry and explicit new-variant semantics

- **Date & Time:** 2026-08-23 00:00 +05:30 - Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Durable jobs and publication failures can be delivered more than once, while an explicit regeneration must be able to produce a meaningfully different design. Treating both actions as a new creative run would waste calls and could replace a verified preview unnecessarily.
- **Decision:** Automatic infrastructure/build/browser/publication retries and the session `retry` endpoint reuse the existing run's immutable design-variant receipt, fingerprint, accepted checkpoints, and active preview. Explicit `regenerate` creates a new run and variant receipt, compares its content-free fingerprint against recent accepted variants, and fails closed after its bounded redirected creative attempt remains too similar.
- **Rejected alternatives:** Generating a new variant for every retry; relying only on an HTTP idempotency key without binding retry state to the run; mutating the accepted variant in place; or deleting the previous preview before the replacement is publicly verified.
- **Consequence:** Retry is safe to repeat without creative drift or unnecessary model calls, regeneration is the only deliberate source of variant change, and the last verified preview remains available while a replacement is pending or fails.

## D-041 - Code Generator V4 provider-compatible contracts and preview truth

- **Date & Time:** 2026-08-21 22:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** V3 generation was structurally strong but still allowed a development/session quality-path split, provider-sized resource queries to drift from receipts, marker-only visual intent, and a preview gateway with incorrect CSP/cache/health behavior.
- **Decision:** Add mapping-free v4 creative, blueprint, search-intent, source-envelope, quality-receipt, typed-token, and design-realization contracts while retaining v3 read compatibility. Compile semantic route ownership and measurable runtime obligations deterministically; run the same whole-site review for v4 development and production paths; use exact bounded provider query strings; preserve verified candidates as `preview_pending` on publication failure; and make the shared gateway expose its own health endpoints, exact embed-origin allowlists, and no-store active HTML.
- **Rejected alternatives:** Replacing v3 in place; accepting arbitrary token maps or nullable tagged unions; using marker text as visual evidence; truncating provider queries after hashing; treating object upload as public preview readiness; wildcard iframe CSP; or inheriting the API health check for the gateway.
- **Consequence:** V4 runs fail closed on missing executable evidence or stale upstream authority, provider receipts identify the exact transport query, and a verified prior preview remains available through storage/gateway outages. Existing v3 fixtures and exports remain readable during migration.

## D-040 — Configuration-driven Anthropic default and model routing

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** OpenAI credits are temporarily unavailable, while every model-backed engine must use the Anthropic credential now. Future provider/model changes must remain easy to make per engine without scattering provider branches through agents, handlers, or the UI.
- **Decision:** Route every active engine through the shared `ModelRouter` and provider-neutral `ModelClient` factory. The committed profiles use Anthropic Claude Sonnet 5 with `ANTHROPIC_API_KEY`, adaptive thinking, native JSON-schema capability declarations, and bounded prompt caching. The routing table and selectable UI profiles live in `config/models.toml`; the API/UI expose only non-secret profile metadata. Real operations fail closed when the configured credential or adapter is unavailable; deterministic test clients remain test-only.
- **Rejected alternatives:** Hard-coding Anthropic branches in each agent; retaining a frontend-only provider dropdown; making OpenAI the active default while its balance is unavailable; silently falling back to mocks for live jobs; or adding Batch API semantics to the interactive durable workflow now.
- **Consequence:** Reassigning an engine to another configured profile or adding a provider requires a profile/routing change plus one shared adapter/factory implementation, rather than agent rewrites. Batch submission remains a future cost optimization for suitable asynchronous workloads, not part of current interactive execution.

## D-039 — Backend-only Docker and shared hosted portfolio previews

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Free hosted services have ephemeral filesystems, sleep/cold starts, and uneven worker support. Generating a Docker image or public deployment for every portfolio would be expensive, difficult to inspect, and unnecessary for a static Vite/React result. Code Generator failures also need source-linked evidence during development.
- **Decision:** Docker packages only the OryxenAI API, durable worker, migration/toolchain environment, browser verifier, and shared preview gateway. Every generated portfolio remains a portable source tree plus verified `dist/`; generated Docker artifacts are excluded from exports. Hosted previews use immutable S3-compatible objects and a conditional active pointer behind one shared gateway, while local development uses filesystem storage. The developer surface exposes bounded accepted-source slices for file/line diagnostics. Hosted readiness fails closed when durable worker or preview storage prerequisites are unavailable.
- **Rejected alternatives:** One Docker container, deployment, or public URL per generated portfolio; serving previews from a container's local filesystem; publishing unverified source; embedding the generated app as a long-running development server; or treating a free web service heartbeat as proof that the durable worker is available.
- **Consequence:** The generated app is easy to inspect, repair, and preview without a per-portfolio runtime. Free-host deployments must provide managed PostgreSQL, private object storage, a real worker runtime, and a shared preview origin; sleep and cold-start behavior remain platform constraints rather than hidden application state.

## D-038 — Promotion requires content-addressed artifact reuse and terminal diagnostics

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Live Code Generator attempts could fail before or after planning because provider schemas were not wire-compatible, generated plans were semantically invalid, route workers duplicated heavyweight dependency trees, browser verification could crash or miss mounted interactions, and a stale or root-owned build artifact could make a valid candidate appear unavailable.
- **Decision:** Keep provider capability negotiation and local validation at the shared boundary; use one bounded correction attempt for invalid structured output; make route workspaces source-only with shared dependencies and single-flight installs; normalize only deterministic source-contract defects; materialize and hash-check pack resources; run browser checks in writable isolated directories with explicit preview tokens; verify every persisted manifest before reuse; and persist terminal reports with candidate-gateway diagnostics without silently reclassifying them as retryable jobs.
- **Rejected alternatives:** Hardcoded portfolio-specific output repairs; unbounded model retries; copying or installing dependencies independently in every route wave; accepting heartbeat/readiness as generation success; reusing a path-only `dist`; deleting/resetting the shared persistent volume; or hiding a terminal provider/build error behind worker retries.
- **Consequence:** Generation remains portfolio-specific and fail-closed while common environmental and contract failures become deterministic, diagnosable, and bounded. Promotion is allowed only after source, build, and DOM/runtime evidence agree on the same materialized candidate.

## D-037 - Provider wire contracts and no-context Code Generator admission

- **Date & Time:** 2026-08-21 00:30 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The configured Anthropic Code Generator profiles used generic thinking/schema flags. Sonnet rejected typed mapping schemas before planning, while readiness could claim success without exercising the configured provider.
- **Decision:** Declare structured-output, thinking, and effort wire capabilities in config; let the Anthropic adapter emit native JSON Schema only for its supported subset and use trusted schema prompting plus local validation for incompatible typed mappings. Require a fixed no-context provider preflight before live development starts, preserve safe provider diagnostics, and retry one structurally invalid planner response with bounded validator feedback.
- **Rejected alternatives:** Provider/model branches in agent logic; hardcoded portfolio schemas or visual fallbacks; silently switching providers; treating a credential check or heartbeat as provider readiness; unbounded planner retries.
- **Consequence:** Provider request incompatibilities fail before portfolio context is sent when possible, arbitrary portfolio-specific token maps remain supported without input-specific hardcoding, and the UI receives an actionable admission/error state before durable work begins.

## D-036 - Enforce generated source and runtime contracts without visual evidence

- **Date & Time:** 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Build and coarse browser smoke could pass while generated routes still contained duplicate landmarks, broken fragments, ignored interactions/resources, or runtime paths hidden behind the preview mount.
- **Decision:** Add a deterministic TypeScript source audit and exact DOM/runtime gate. V3 source must resolve local imports/exports, expose the trusted SharedSystems behavior, use approved route sections and distinctive-move markers, avoid runtime network APIs, and preserve ownership. Browser journeys must cover every configured route/interaction check with exact route/section/landmark, accessibility-state, local-resource, reduced-motion, geometry, and evidence-set assertions. Preview-mounted paths are normalized against the logical route allow-list.
- **Rejected alternatives:** Screenshots or vision review as a required gate; build-only validation; coarse category checks that omit individual journeys; trusting logical URLs without accounting for the preview mount.
- **Consequence:** A candidate cannot promote with an inert, structurally contradictory, remotely dependent, or incompletely exercised generated site; the gate remains text/DOM based and deterministic.

## D-035 - Explicit Build Preparation v4 delegated acquisition

- **Date & Time:** 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Some approved visual roles can remain unresolved after Build Preparation has exhausted its configured providers, but letting Code Generator invent resources would break provenance, privacy, and reproducibility.
- **Decision:** Build Preparation emits pack-v4 delegated slots only when the explicit delegation feature is enabled and upstream attempts have completed. Each delegated slot carries a closed provider/category policy, bounded candidate and retry limits, and no-invention semantics. Code Generator translates only those slots into deterministic requests and uses the existing Pexels/Pixabay, Fontsource, and component-source retrieval boundaries; v3 packs remain readable for rollback.
- **Rejected alternatives:** Silent delegation in every pack; model-invented URLs, IDs, dependencies, or budgets; treating unresolved delegation as an execution gap; removing strict v3 compatibility.
- **Consequence:** Required delegated roles fail closed without promotion, optional roles use only declared fallbacks, and every acquired byte/source remains locally materialized with provenance and executable-use requirements.

## D-034 - Design-neutral Code Generator V3 with compiler-owned behavior

- **Date & Time:** 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The prior generation contract allowed generic scaffold palettes, no-op shared systems, route-batch shell duplication, retyped approved copy, and unassigned interactions to survive model output.
- **Decision:** Replace the active creative contract with typed ExperienceBlueprintV3 fields for token groups, route shells, layout regions, distinctive moves, interaction assignments, resource placements, motion beats, and anti-patterns. Compile tokens and approved content deterministically, keep only semantic behavior in trusted SharedSystems, give route composers sole shell ownership, and execute independent route batches in isolated workspaces before deterministic merge. Styling and composition remain portfolio-authored model output; defaults are not a substitute.
- **Rejected alternatives:** A fixed house palette or generic scaffold; model-authored behavior primitives; one full accumulated source tree in every route prompt; route batches that emit their own landmarks; mandatory screenshot/vision review.
- **Consequence:** The same contract governs development and explicit production starts, visual values remain portfolio-specific, and structural ownership/resource/content drift is rejectable before browser verification.

## D-033 - Fenced Code Generator stage attempts and immutable workflow artifacts

- **Date & Time:** 2026-08-20 00:00 +05:30 - Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** At-least-once jobs and mutable run JSON allowed duplicate or late workers to overwrite newer Code Generator state, while checkpoints and candidate material still depended on workspace paths.
- **Decision:** Every Code Generator stage may carry a normalized attempt token bound to run, stage, job, expected revision, input fingerprint, worker release, and trace. Finalization is accepted only while that token remains current. Workflow input, acquisition, checkpoints, accepted source, and candidates use immutable content-addressed artifact references; local filesystem storage is the development implementation and the existing S3-compatible boundary is the production adapter. Safe failure classification is centralized into retryable infrastructure, permanent input/policy, repairable generated-source, and terminal classes.
- **Rejected alternatives:** Extending mutable run JSON as the only attempt record; accepting a late handler based on run ID alone; mutable path-based artifact references; provider-specific artifact logic in handlers; treating every failure as retryable or terminal.
- **Consequence:** Duplicate delivery and stale workers can be discarded without regressing state, workers can rehydrate exact bytes from a fresh workspace, and UI diagnostics can expose trace/attempt/readiness metadata without portfolio content or secrets. Existing v3 callers remain compatible until the remaining generation and verification phases adopt the new contracts.

## D-032 — Session-bound Code Generator with compiled visual execution

- **Date & Time:** 2026-08-19 12:34 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** The standalone generator could admit a local pack but production sessions had no exact R2 consumption path, provider failures occurred only after durable work began, model-authored work ownership conflicted with route batching, and text/DOM smoke lacked enforceable composition and geometry quality.
- **Decision:** Production Code Generator is an explicit, idempotent session stage over the same durable core. Start binds the eligible Build Preparation run/scope/object key/ETag/size/SHA/expiry, performs fixed no-context provider and local-toolchain preflight, then downloads and re-verifies the artifact in the worker. Structured calls compare two grounded concepts, compile an `ExperienceBlueprintV2`, generate disjoint host-owned route batches, and perform one bounded owner-scoped integration polish. Known pack slots remain authoritative; only emergent gaps use mediated acquisition. Promotion requires non-stale input, final source/build closure, all-route mobile/tablet/desktop and reduced-motion browser journeys, configurable geometry checks, and atomic replacement of the session-stable preview.
- **Rejected alternatives:** Local-mirror recency as production input; request-time model overrides; a free-running supervisor/tool-calling model; model-authored paths and dependencies; one giant source response; screenshot/vision gates; build-only acceptance; generic style prompts without typed spatial/resource/motion contracts; promoting a candidate after upstream Build Preparation changes.
- **Consequence:** Production and development attempts share one persistence/workflow implementation while preserving explicit caller sequencing. Failures retain safe provider/artifact/contract diagnostics and the previous active preview. Visual distinctiveness is still model-authored, but resource identity, work ownership, quality thresholds, browser geometry, staleness, and promotion remain deterministic host authority.

## D-031 — Shared local Pexels/Pixabay image retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Build Preparation and Code Generator both need real contextual imagery during generation, while the final static site must not hotlink a provider or duplicate provider-specific selection logic.
- **Decision:** Both stages use the shared image retrieval service for structured intent, bounded Pexels/Pixabay search, 24-hour filesystem response caching, rate-aware retries, deterministic relevance/quality/aspect/popularity/diversity ranking, selected-byte download, pixel validation, intelligent crop/resize/compression, hashing, and local provenance-bound materialization. Pexels is tried first for normal images; Pixabay is used when results are weak or unavailable; important imagery queries both. Unsplash remains disabled unless local vendoring and the provider are explicitly configured.
- **Rejected alternatives:** Hardcoded component keywords; a separate smart retrieval agent; browser-runtime provider URLs; downloading every candidate; permanent Unsplash/Pixabay hotlinks; caching component registry responses; making either agent own a second provider implementation.
- **Consequence:** Provider outages degrade to the other configured image provider and unresolved required visual roles remain visible as readiness gaps. The same shared cache volume can be mounted by worker processes, while component retrieval remains deliberately cache-free under D-029.

## D-030 — Priority-based dynamic component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Portfolios vary from a single-page profile to multi-route, interaction-heavy sites. A fixed component count either wastes free-provider requests or leaves important roles unresolved.
- **Decision:** Component count is derived per run from approved needs. Required roles are attempted first; optional roles are ranked by importance, distinct interaction role, and route/scene coverage, then admitted until the configured per-run maximum. Required roles are never silently discarded when they exceed the maximum; the run reports the condition and remains subject to provider request/rate limits. Build Preparation owns known approved roles and Code Generator applies the same policy only to genuinely emergent component requests. LLMs compose queries and rank candidates from a closed, policy-filtered metadata set; they cannot create provider IDs, URLs, source, dependencies, or budget exceptions.
- **Rejected alternatives:** Fixed “always fetch N” component counts; date-based selection; letting the LLM decide the request budget; fetching every candidate's source; dropping required roles silently; treating Code Generator as a second source of already-resolved Build Preparation roles.
- **Consequence:** Small portfolios spend little retrieval budget, complex portfolios receive broader real source coverage, and optional decoration degrades honestly before required interaction roles do. Rate protection is handled by per-run budgets and provider cooldowns, not durable response caching.

## D-029 — Cache-free live component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Component libraries are free upstream registries with undocumented or changing quotas. Reusing provider responses can hide upstream changes and violates the requirement that selected components come from the current real source.
- **Decision:** Component discovery and source retrieval never persist or reuse provider responses. Build Preparation and Code Generator share one bounded retrieval service: direct REST/registry JSON is authoritative for shadcn, Magic UI, Smooth UI, and Cult UI; discovery returns metadata, and source is fetched only after selection, with recursive `registryDependencies`, strict host/path/dependency validation, SHA-256/license/source provenance, 429 fail-fast behavior, and bounded timeout/5xx retries. MCP is an optional injected discovery/source adapter for registries without a suitable HTTP path, never a required downloader and never an `npx` subprocess. The local shared `cn()` utility is vendored in the target scaffold rather than retrieved from a provider.
- **Rejected alternatives:** Provider response caches or durable component mirrors; fetching every candidate's source before ranking; MCP as the only production transport; shelling out to registry CLIs; silently installing unknown dependencies; accepting metadata-only or synthetic component source.
- **Consequence:** Every selected component reflects a fresh upstream fetch in the current run and can fail closed when a provider is unavailable or rate-limited. Existing infrastructure/toolchain caches remain separate and are not component-retrieval truth.

## D-028 — Real provider material is mandatory for visual handoff slots

- **Date & Time:** 2026-08-17 22:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Offline Build Preparation fixtures were marking deterministic blank PNGs and a tiny generated component wrapper as handoff-ready. The result hid provider failures, produced only one generic image/component, and gave Code Generator no trustworthy visual material.
- **Decision:** Image-rich approved directions target five real images (maximum six) and four real components (maximum six), with policy overrides for text-led or privacy-limited work. Build Preparation may use LLM calls only for bounded query/context/placement orchestration. Images must be downloaded and pixel-inspected from an approved provider; components must come from an approved registry/MCP source and pass source/dependency/provenance checks. Provider requests are concurrency/request bounded and rate-limit aware; component response caching is superseded by D-029. Missing, unavailable, flat, placeholder, metadata-only, or synthetic visual material becomes `VDD_EXECUTION_GAP`. Code Generator admission rejects gaps, generated-local visuals, and visual recipes.
- **Rejected alternatives:** Deterministic generated-local images/components; blank or wrapper source; accepting remote-only image metadata; using a visual recipe or prose fallback to satisfy an image/component slot; unbounded provider retries; treating provider failure as a ready handoff.
- **Consequence:** Offline fixtures remain reviewable but cannot claim readiness when visual roles are unresolved. A production-ready pack now contains provenance-bound local pixels/source, truthful material counts and provider diagnostics, and an actionable upstream revision path when authority or provider material is missing.

## D-027 — Verified major tasks end in task-scoped local commits

- **Date & Time:** 2026-08-17 15:46 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Shared dirty worktree across multiple AI tools hindered auditability, rollback, and attribution.
- **Decision:** Finished, verified major units (`CHANGES.md` level) must create a local task-scoped Git commit by default. Stage only owned files/hunks; review diff; use conventional commit messages; report hash. Never push or use `git add .` on a shared dirty worktree. Report overlapping file conflicts if unseparable.
- **Rejected alternatives:** Leaving work uncommitted in dirty tree; committing micro-saves; blanket `git add -A`; auto-pushing without explicit user instruction.
- **Consequence:** Clean local commit boundaries across AI tools; pushes remain strictly user-initiated.

## D-026 — Code Generator core is the sole standalone implementation namespace

- **Date & Time:** 2026-08-17 15:19 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Package root duplicated 27 `core/` modules via wildcard compatibility imports, creating duplicate namespaces and dead imports.
- **Decision:** `oryxenai.agents.code_generator.core.*` is the sole internal namespace for the standalone workflow. Package root retains only `__init__.py`, `agent.py`, and `schemas.py`. Deprecated root workflow imports removed without deprecation period.
- **Rejected alternatives:** Retaining wildcard adapters; explicit deprecated re-exports; moving implementation back to package root.
- **Consequence:** Direct `core.*` imports enforced for tests and internals; registry-facing `CodeGeneratorAgent` remains stable.

## D-025 — Required visual handoff uses executable local bindings

- **Date & Time:** 2026-08-17 13:29 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Visual slots could collapse into prose/comments or missing recipe references during generation.
- **Decision:** Build Preparation guarantees one concrete visual component per public route plus editorial visuals; provider fallbacks use deterministic local PNG/TSX. Code Generator copies component source to importable paths and serves media via local pack URL. Trusted shell and `global.css` entrypoint are immutable. Default browser verification is a bounded route/asset smoke pass.
- **Rejected alternatives:** Comment-token evidence; forcing all slots to recipes; remote image fetches at generation time; full browser journey per interaction.
- **Consequence:** Guarantees executable visual baseline; browser verification proves runtime integrity, not subjective design taste.

## D-024 — Export complete verified portfolios with receipt-bound metadata

- **Date & Time:** 2026-08-17 11:15 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Promoted candidate needed persistence outside ephemeral workspace without coupling promotion to export success.
- **Decision:** On atomic promotion, export clean `source/`, built `dist/`, and `portfolio.json` metadata (run ID, preview URL, candidate hash, pack ref, routes) to run-scoped `output/code-gen-output/<run-id>/`. Export errors are logged as advisory events without blocking preview.
- **Rejected alternatives:** Exporting only `dist/`; shared export folder (cross-run collision); rollback promotion on export error.
- **Consequence:** Copy-ready, isolated export per run; promotion remains resilient.

## D-023 — Harden generated filesystem transitions on Windows

- **Date & Time:** 2026-08-17 11:10 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Windows file locks (antivirus, indexer, tsc/npm) and path constraints caused transient `PermissionError` on atomic directory replace.
- **Decision:** Route directory swaps, tree removal, and atomic writes through `fs_safe` layer with extended paths (`\\?\`), bounded retry/backoff, stale target cleanup, and explicit failure semantics.
- **Rejected alternatives:** Ad-hoc retries per call site; ignoring all deletion errors; disabling recursive cleanup safety checks.
- **Consequence:** Atomic checkpoints and promotion survive transient Windows file locking.

## D-022 — Skip acquisition for execution-contract-resolved resource slots

- **Date & Time:** 2026-08-17 11:05 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Pack-v3 already resolves known slots to recipes or package bindings; re-acquiring them duplicates work and causes conflicting receipts.
- **Decision:** Acquisition skips slots resolved in execution contract; scout runs only for genuine emergent needs. Dependency additions route through `DependencyManager`.
- **Rejected alternatives:** Reacquiring all slots; treating resolved slots as missing; unrestricted npm package installs.
- **Consequence:** Pack-v3 remains authoritative for known slots; Code Generator handles only emergent implementation gaps.

## D-021 — Keep one canonical storage-key route owner

- **Date & Time:** 2026-08-17 11:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Divergence between route IDs and storage keys created duplicate route files and ambiguous ownership.
- **Decision:** Canonical verification anchor is `src/routes/<storage_key>/index.tsx`. Planner, contracts, prompts, repair, and validators use slugged storage key without `routes/` prefix. Generated route registries are trusted pipeline output.
- **Rejected alternatives:** Re-deriving paths from route IDs; permitting both aliases; letting model prose override pack mapping.
- **Consequence:** Exactly one source owner and literal verification anchor per route.

## D-020 — Approved external links are content, not runtime navigation

- **Date & Time:** 2026-08-17 10:55 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Offline DOM verification cannot navigate to external URLs (LinkedIn, GitHub); blank target URLs in planner are valid if in trusted ledger.
- **Decision:** Derive journeys from literal `data-interaction-id`. Same-app links may navigate; external/prose links use non-navigating `assert_link` to verify href and accessible name offline.
- **Rejected alternatives:** Clicking external links (breaks offline invariant); dropping link assertions; selector-guessing from prose.
- **Consequence:** Offline, fail-closed runtime verification preserves link accessibility without network calls.

## D-019 — Normalize strict-schema generation payloads by mode tag

- **Date & Time:** 2026-08-17 10:50 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** OpenAI strict JSON schema requires all nullable properties to be present, populating unused fields in union responses.
- **Decision:** `GenerationResult` normalizer treats declared `mode` as authoritative, keeps only matching payload, strips non-matching null/empty fields, and rejects empty matching payloads.
- **Rejected alternatives:** Rejecting any payload with extra null fields; inferring mode from non-empty fields.
- **Consequence:** Coexistence of strict transport schema with semantic one-of payloads.

## D-018 — Pack-v3 makes known resource decisions executable before Code Generator

- **Date & Time:** 2026-08-13 22:30 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Pack-v2 allowed prose-only fallbacks for typography, icons, components, and visuals, forcing Code Generator to invent decisions.
- **Decision:** Superseded pack-v2 consumer admission with `build-preparation-pack-v3`. Added `execution/contract.json`, `resources/ledger.json`, and local recipe manifests. All known slots resolve to local files, package bindings, typed recipes, or explicit `VDD_EXECUTION_GAP`. Single canonical storage key per route. Fixture/upload admission accepts only v3 with full hash verification.
- **Rejected alternatives:** Accepting prose fallbacks; in-place archive rewriting; arbitrary web/URL fetches by Code Generator.
- **Consequence:** V3 packs guarantee executable local bindings before Code Generator runs; emergent acquisition handles only coding discoveries.

## D-017 — Approve a complete safe public scope, then direct that exact scope

- **Date & Time:** 2026-08-13 20:22 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Content Architect over-gated ordinary facts as pending, leading to 0 approved routes or route mismatches with Visual Design Director.
- **Decision:** Approved Discovery authorizes neutral baseline public copy. CA must approve at least 1 route, with complete content pack, section sequence, claim references, unique path, and visual handoff. VDD receives and directs only the approved CA route set, stamped with canonical paths.
- **Rejected alternatives:** Treating unverified details as publication bans; auto-clearing unverified claims at approval; passing pending routes to VDD.
- **Consequence:** Approval guarantees a complete, compilable public route graph across CA, VDD, and Build Preparation.

## D-016 — Content Architect approval requires at least one publishable route

- **Date & Time:** 2026-08-13 19:22 +05:30 — OpenCode (glm-5.2)
- **Status:** decided-implemented
- **Context:** CA allowed approval when all routes were `"pending"`/`"blocked"`, causing downstream Build Preparation pack failure `BUILD_PACK_V2_CONTENT_ROUTES_MISSING`.
- **Decision:** CA `apply_approval` raises `NoPublishableRoutesError` (HTTP 409 `CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES`) if no route is `publication_status == "approved"`. Build Preparation splits route diagnostics into `BUILD_PACK_V2_CONTENT_ROUTES_EMPTY` vs `NONE_APPROVED`.
- **Rejected alternatives:** Auto-promoting pending routes to approved on approval; bypassing route status checks in Build Preparation.
- **Consequence:** Non-clearable profiles fail loudly at CA stage with actionable 409 instead of producing corrupt packs.

## D-015 — Code Generator uses progressive text-only generation with mediated resource acquisition

- **Date & Time:** 2026-08-13 11:59 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** D-014's screenshot/vision-model matrix was operationally expensive and didn't improve code quality; closed pre-generation resource set prevented necessary in-flight discoveries.
- **Decision:** Supersede D-014. Implement text-only Code Generator with staged operation roles (planner, resource scout, foundation, route builder, integrator, repairer). Advances through planning, acquisition, foundation, route batches, integration, text/DOM verification, finite repair, and atomic preview promotion. No vision models or screenshot gates. Acquisition adapters mediate local materialization of emergent resources. 3 lean verification gates: source contract, clean type/build, and headless text/DOM/runtime smoke.
- **Rejected alternatives:** Screenshots without vision models; build-only verification; unmediated model tools (shell/web); unbounded repair loops.
- **Consequence:** Architecture documented in `docs/code-generator-architecture/`. High quality via structured prompts, tokens, and deterministic compiler/DOM gates.

## D-013 — Repair only reproduced Build Preparation pack defects and issue pack v2

- **Date & Time:** 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Pack-v1 omitted approved global VDD fields, lacked machine-readable route contracts, and had unenforced asset acquisition policies.
- **Decision:** Superseded D-012 with `build-preparation-pack-v2`. Added `site/contract.json` (canonical routes, section refs, criteria IDs) and `design/visual-direction.json`. Enforced exact CA/VDD route equality and stock acquisition policies (`optional_external_acquisition` only).
- **Rejected alternatives:** Inferring routes in Code Generator; reading upstream session state directly; silently treating v1 as v2.
- **Consequence:** Versioned, hash-verified pack-v2 boundary between Build Preparation and Code Generator (later extended by D-018 to pack-v3).

## D-011 — Rebuild Build Preparation as a real agent, from zero, superseding D-010

- **Date & Time:** 2026-08-11 (local) — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Legacy compiler (`src/oryxenai/build_preparation/`) was overly complex, had discovery issues, and didn't follow agent patterns (D-008).
- **Decision:** Retired old compiler; rebuilt Build Preparation as standard agent at `src/oryxenai/agents/build_preparation/` (`AgentKey.BUILD_PREPARATION`, state/validators/job/API). Uses structured model calls for resource planning and build briefs, Unsplash fallback for Pexels, single verified image rendition, and deterministic ZIP packaging to temporary R2.
- **Rejected alternatives:** In-place patching; zero-model pure compiler; OpenAI image generation; moving infrastructure to Azure.
- **Consequence:** Standardized agent architecture across pipeline; verified temporary artifact upload to R2.

## D-009 — Deployment-independent temporary Build Preparation packs

- **Date & Time:** 2026-08-09 21:15 UTC — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** API and worker run in independent disposable containers; shared disk or database byte storage was unsuitable for build packs.
- **Decision:** Materialize immutable hash-verified ZIP per preparation run and upload to private S3/R2 storage with TTL lifecycle. Session JSONB stores only metadata, hash, and expiry.
- **Rejected alternatives:** Shared Docker volumes (multi-host failure); DB byte blobs (database bloat); public URLs.
- **Consequence:** Production requires R2 credentials; expired packs deterministically regenerate from approved upstream state.

## D-008 — Visual Design Director mirrors Content Architect architecture

- **Date & Time:** 2026-08-08 19:49 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Visual Design Director needed implementation following Content Architect's proven bounded workflow pattern.
- **Decision:** Built VDD with 5-status state machine, 3-operation workflow (`establish_visual_language`, `direct_page_experience`, `integrate_site_experience`), envelope-only validation, hash staleness checks, and JSONB session persistence. Tag-overlap local resource catalogue (`catalogue.json`) queried in Python before model calls.
- **Rejected alternatives:** Complex provenance fields; deterministic heuristic code validators.
- **Consequence:** Reusable pipeline agent pattern established across stages.

## D-007 — Restructure AI-agent context files around canonical AGENTS.md

- **Date & Time:** 2026-08-08 16:02 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Multiple AI tools (Claude Code, Codex CLI, Cursor, Antigravity) worked on repo; inconsistent context caused configuration drift.
- **Decision:** `AGENTS.md` is canonical context. `CODEX.md` and `CLAUDE.md` redirect to it. Created `CHANGES.md` (changelog) and `DECISIONS.md` (ADR log).
- **Rejected alternatives:** Maintaining separate per-tool context files; merging ADRs into `CHANGES.md`.
- **Consequence:** Single source of truth for cross-tool AI sessions.

## D-005 — Jinja2 + vanilla JS testing harness instead of framework frontend

- **Date & Time:** 2026-08-08 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Needed lightweight UI to test agent chat flows before final product frontend was designed.
- **Decision:** Server-rendered Jinja2 + vanilla JS harness (`src/oryxenai/web/`) without external framework dependencies.
- **Rejected alternatives:** Building full React/Next.js app before agent protocols stabilized.
- **Consequence:** Simple developer harness; conversational contract specified in `docs/frontend-behavior-spec.md`.

## D-004 — Kept dormant discovery_opencode_go profile in config/models.toml

- **Date & Time:** 2026-08-07 21:00 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Switching active model provider left old profile unused.
- **Decision:** Keep dormant provider profiles in `config/models.toml` for zero-code rollback.
- **Rejected alternatives:** Deleting dormant profiles.
- **Consequence:** Easy provider switching via config profile assignment.

## D-003 — Switched Discovery/Content Architect to OpenAI API directly

- **Date & Time:** 2026-08-07 20:10 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go rate limit quota exhausted, blocking development.
- **Decision:** Pointed profiles directly to OpenAI API via `OPENAI_API_KEY`. Added `ModelCapabilities` abstraction for provider quirks (e.g. `uses_max_completion_tokens`).
- **Rejected alternatives:** Waiting for quota reset; hardcoding provider branches in agent code.
- **Consequence:** Generic provider capability layer handles API differences.

## D-002 — v1 Discovery over-engineering, then v2 simplification

- **Date & Time:** 2026-08-07 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Initial Discovery implementation had dedicated document tables, repair loops, 20-file few-shot libraries, and graph validation.
- **Decision:** Simplified to session JSONB storage, inline contrastive prompt examples, and envelope-only validation.
- **Rejected alternatives:** Preserving multi-table validation graph.
- **Consequence:** Repository standard established: envelope validation + prompt-carried examples over heavy framework machinery.

## D-001 — Explicit Python agents over an agent framework

- **Date & Time:** 2026-08-06 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Needed agent architecture before tool-calling and routing requirements were clear.
- **Decision:** Plain Python protocols (`Agent`, `ModelClient`) and Pydantic schemas without external frameworks.
- **Rejected alternatives:** LangChain, LangGraph, CrewAI, AutoGen.
- **Consequence:** High testability, zero framework lock-in, explicit model boundaries.

---

## Compacted & Superseded History

- **D-014** — 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI) — Code Generator v1 bounded generation, verification, repair, atomic preview promotion (superseded by D-015)
- **D-012** — 2026-08-12 20:45 +05:30 — Codex (GPT-5 / OpenAI) — Freeze Build Preparation v1 and validate through Code Generator (superseded by D-013)
- **D-010** — 2026-08-10 17:51 +05:30 — Codex (GPT-5 / OpenAI) — Portfolio Production Compiler pre-code boundary (superseded by D-011)
- **D-006** — 2026-08-08 15:30 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — Visual Design Director & Code Generator deferred (superseded by D-008)

---

## Summary (as of last update — 2026-08-19)

- Total decisions logged: 38
- Active decisions: 34 (all logged decisions except D-006, D-010, D-012, and D-014)
- Superseded decisions: 4 (D-006, D-010, D-012, D-014)
- Last updated: 2026-08-23 — Codex (model/provider omitted)
