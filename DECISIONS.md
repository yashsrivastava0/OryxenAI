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

- Total decisions logged: 32
- Active decisions: 28 (D-001–D-005, D-007–D-009, D-011, D-013, D-015–D-032)
- Superseded decisions: 4 (D-006, D-010, D-012, D-014)
- By tool: Codex (22), Claude Code (4), OpenCode (1), Unspecified/Retroactive (5)
- Last updated: 2026-08-19 — Codex (model/provider omitted)
