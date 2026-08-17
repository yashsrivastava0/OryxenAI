# OryxenAI — Decisions & Open Issues

Architecture Decision Record (ADR)-style log: real decisions with actual trade-offs, open questions, deferred work, and architectural history. Not routine implementation minutiae (which belong in commit messages or `CHANGES.md`).

**Logging policy — same discipline as `CHANGES.md`:** Log only real decisions with actual trade-offs. Ask the user first if ambiguous.

Ordering: Reverse-chronological by decision date, newest at top. Entry IDs (`D-001`, `D-002`, ...) are stable references and never reused.

Every AI agent (Codex CLI, Claude Code, Cursor, OpenCode, Google Antigravity, or any other) must check this file before making architectural choices.

**Entry template** (copy verbatim for new entries, insert directly below this header, above newest entry):

```markdown
## D-0XX — <short decision title>

- **Date & Time:** YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>)
- **Status:** open | decided-not-yet-implemented | decided-implemented | superseded-by-D-0XX
- **Context:** Constraint or problem forcing a choice.
- **Decision:** What was chosen, stated concretely.
- **Rejected alternatives:** What else was considered and specifically why rejected.
- **Consequence:** Forward implications, trade-offs, and revisit criteria.
```

---

## Active Decisions

## D-027 — Verified major tasks end in task-scoped local commits

- **Date & Time:** 2026-08-17 15:46 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Multiple AI coding agents work in the same repository, but completed major tasks have often remained mixed in one long-lived dirty worktree. `CHANGES.md` records the work but does not create a recoverable Git boundary, making later review, attribution, rollback, and handoff harder.
- **Decision:** Any finished, verified unit large enough for `CHANGES.md` must create a local task-scoped commit by default. Agents inspect the starting and final diffs, stage only owned files or exact hunks, review and validate the staged patch, use a concise conventional commit subject, report the commit hash and remaining status, and never treat a local commit as permission to push. If pre-existing edits cannot be separated safely, the agent commits the isolatable portion and reports the precise overlap instead of absorbing another contributor's work.
- **Rejected alternatives:** Leaving all completed work uncommitted (continues an unauditable shared diff); committing after every save or tiny edit (creates noisy history); using `git add -A` in a dirty worktree (can capture another agent's work, secrets, or generated files); or automatically pushing every commit (changes an external system without explicit authorization).
- **Consequence:** Major completed work gains an immediate local recovery and review point across Codex, Claude Code, Cursor, and other tools. Small, incomplete, blocked, or plan-only work remains uncommitted, unrelated dirty changes remain visible, and remote synchronization still requires an explicit user request.

## D-026 — Code Generator core is the sole standalone implementation namespace

- **Date & Time:** 2026-08-17 15:19 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** The Code Generator package root duplicated 27 `core/` modules through wildcard compatibility imports. Production code already used `core/` directly, 17 adapters were referenced only by internal tests, 10 had no repository consumer, and the additional `core/generation_schemas.py` facade had no direct consumer. The duplicate namespace obscured implementation ownership and exposed incidental imported names.
- **Decision:** Make `oryxenai.agents.code_generator.core.*` the sole internal namespace for the standalone workflow. Keep only `__init__.py`, `agent.py`, and `schemas.py` at the package root, remove every wildcard compatibility module plus the unused generation-schema facade, and migrate repository tests to direct `core.*` imports. Historical package-root workflow-module paths are not a supported external API and receive no deprecation period.
- **Rejected alternatives:** Keeping wildcard adapters (continues duplicate ownership and uncontrolled exports); replacing them with explicit deprecated re-exports (preserves files with no known external consumer); or moving the implementation back to the package root (reverses the established lean `core/` ownership boundary).
- **Consequence:** Old package-root workflow imports fail immediately and callers must use the canonical `core.*` modules. The registry-facing Agent import remains stable, while HTTP routes, job kinds, persisted contracts, generation behavior, and production-integration scope are unchanged.

## D-018 — Pack-v3 makes known resource decisions executable before Code Generator

- **Date & Time:** 2026-08-13 22:30 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** A reproduced consumer audit found that a structurally valid v2 pack could still contain only prose fallbacks for typography, icons, components, and abstract visuals. It also retained legacy route mirrors beside canonical files and normalized eligible provider lookup away before it could perform useful acquisition. Those defects leave a downstream builder to guess implementation decisions despite otherwise correct approved scope, provenance, archive hashing, and storage read-back.
- **Decision:** Supersede the consumer admission portion of D-013 with `build-preparation-pack-v3` / `build-preparation-contract-v3`. Preserve authoritative site and visual projections, but add a hash-covered `execution/contract.json`, `resources/ledger.json`, and declarative local recipe manifests. Every known slot resolves exactly once to locally materialized files, a target-package binding with permitted exports, a static typed recipe, or a route/scene-specific `VDD_EXECUTION_GAP`; known needs have no later-fetch escape hatch. V3 has one canonical route storage key per route and rejects aliases or duplicate route data. Standalone fixture/upload admission accepts only v3 and verifies execution, resource, recipe, licence, route mapping, and projection hashes before planner invocation. Configuration owns the initial trusted provider set and pins; Animate UI remains disabled pending a separate licence/distribution decision. Code Generator acquisition remains available only for genuinely emergent, receipt-bound needs under D-015.
- **Rejected alternatives:** Treating empty resource selection as an acceptable prose fallback (forces generator invention); rewriting old v2 archives in place (breaks immutable historical provenance); allowing Build Preparation to invent personal/project media or silently revise VDD (violates upstream authority); accepting duplicate route mirrors because the contract happens to point at one copy (invites accidental use); and giving the generator provider catalogues or arbitrary URLs (weakens reproducibility and policy enforcement).
- **Consequence:** Fresh generation produces only v3 packs for Code Generator, while v2 remains review-only diagnostics. Sparse but valid privacy-safe direction can use bounded system-typography, text composition, CSS/diagram, or omission recipes; a required unsatisfied scene fails closed and asks for explicit VDD revision. The production/main-flow adapter, source generation, preview, and automatic chaining remain outside this change.

---

## D-017 — Approve a complete safe public scope, then direct that exact scope

- **Date & Time:** 2026-08-13 20:22 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** D-016 correctly stopped an all-pending Content Architect result from being approved, but its prompting still treated ordinary portfolio facts as non-clearable whenever contact permission, team ownership, project permission, metrics, or scale were not individually confirmed. That made a normal profile likely to yield no public route at all. Separately, Visual Design Director was passed all non-blocked routes and could direct a pending route, while Build Preparation pack-v2 correctly requires VDD pages to equal Content Architect's approved public route set exactly. The result was either an operator-facing 409 with no clear safe baseline or a later cross-agent route mismatch.
- **Decision:** An approved Discovery snapshot authorizes a neutral portfolio baseline for ordinary supplied professional facts. Content Architect must use narrow, factual wording; omit contact details, metrics, named outcomes, individual-contribution assertions, and restricted material unless they are supported. Explicit privacy, NDA, do-not-publish, or confidentiality restrictions remain overriding blocks. At approval, Content Architect must have at least one approved route and every approved route must have one complete content pack, matching section sequence, approved claim references, a safe unique path, a public manifest, and a visual handoff. Visual Design Director receives and may emit only that approved route set; its pages are deterministically stamped with Content Architect's canonical path and purpose. Build Preparation keeps exact-set rejection as the final consumer backstop.
- **Rejected alternatives:** Treating every missing detail as a publication ban (strands ordinary profiles with no portfolio); auto-promoting pending claims or routes at approval (bypasses explicit restrictions); allowing VDD to carry pending pages and filtering them only in Build Preparation (turns a producer contract violation into a late opaque failure); accepting VDD path/purpose echoes as authoritative (permits downstream semantic drift).
- **Consequence:** Approval now means an actually compilable, privacy-respecting public scope rather than a top-level stamp alone. A model that cannot produce that scope fails at Content Architect review with targeted revision diagnostics; a VDD run cannot reintroduce review-only routes; and the v2 pack consumes one canonical route graph. Revisit only if Discovery adds a finer-grained publication authority model.

---

## D-016 — Content Architect approval requires at least one publishable route

- **Date & Time:** 2026-08-13 19:22 +05:30 — OpenCode (glm-5.2)
- **Status:** decided-implemented
- **Context:** Build Preparation's pack-v2 contract (`contracts._public_routes` / `compiler._public_route_ids`) treats a Content Architect `route_plan` entry's `publication_status == "approved"` as the authority for "is this route public". Content Architect's `apply_approval`, however, only stamps a separate top-level `approved = {approved_at, content_hash}` object computed from `page_content_packs` + `public_content_manifest` — it never touches `route_plan` entries' `publication_status`. So a run where the model emits `"pending"`/`"blocked"` for every route (exactly what `plan_content` prompts for unresolved-ownership routes) passed approval, then failed deep inside Build Preparation as `BUILD_PACK_V2_CONTENT_ROUTES_MISSING` with no dropped-route diagnostic.
- **Decision:** Make Content Architect's state machine (`apply_approval`) refuse approval when no `route_plan` entry has `publication_status == "approved"`, raising `NoPublishableRoutesError` carrying the per-route statuses. The service surfaces a 409 `CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES` so the operator revises/re-runs Content Architect at the right boundary. `route_plan` entries are never mutated — `pending`/`blocked` content stays gated, preserving the cross-agent invariant (VDD's `_stamp_page_compilability` mirrors CA's per-route status into page `publication_status`/`compilable`). Separately, split Build Preparation's failure into `BUILD_PACK_V2_CONTENT_ROUTES_EMPTY` (missing/empty `route_plan`) vs `BUILD_PACK_V2_CONTENT_ROUTES_NONE_APPROVED` (non-empty, none approved) and propagate dropped route_ids + their statuses into the issue `details`, plus enriched Stage 0 `scope_compiled` `dropped_routes` and named warnings.
- **Rejected alternatives:** Auto-promoting every `route_plan` entry to `publication_status="approved"` at approval (overwriting entries in `apply_approval`) — would publish content the model deliberately marked not-cleared, override the documented confidentiality gating, and silently skip the VDD stamping chain (would also force a VDD re-run to re-stamp pages). Build-Prep-boundary coercion that treats the top-level `approved` stamp as authoritative regardless of per-route status — same confidentiality bypass and weakens the closed-set v2 contract. Compatibility-mode synthesis from VDD pages when a real CA `route_plan` exists — guts the closed-set consumer boundary.
- **Consequence:** A formulation the model judges entirely non-clearable no longer produces a dead Build Preparation pack; it fails loudly at approval with an actionable 409. The closed-set pack-v2 contract remains strict. Getting a successful pack after this fix requires a Content Architect re-run that emits at least one `approved` route (samples prove the model can, even for NDA-heavy profiles), then re-approve CA, re-run/approve VDD, then re-run Build Preparation. Revisit if a future stage needs to derive publishability from something other than the model's per-route judgement.

---

## D-015 — Code Generator uses progressive text-only generation with mediated resource acquisition

- **Date & Time:** 2026-08-13 11:59 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** D-014 made screenshot capture, an image-capable reviewer, a large visual-evidence matrix, and a closed pre-generation resource set central to Code Generator acceptance. The product owner has rejected vision-model and screenshot verification because their cost and operational complexity do not improve the generator itself. The closed resource set is also too restrictive: Build Preparation cannot predict every image, font, icon, style primitive, or adaptable component that becomes necessary once real source is being composed. Reliability must come primarily from a better staged generator, compiler/runtime feedback, and explicit resource authority—not from a post-hoc visual judge.
- **Decision:** Supersede D-014. Implement Code Generator as one explicitly started durable stage with narrow configured operation roles—planner, resource scout, foundation builder, route builder, integrator, and repairer—behind the provider-neutral text/structured-output boundary; profiles may share one configured model. The stage advances through admitted-input planning, initial resource reconnaissance, trusted scaffold/dependency resolution, foundation generation, route batches, integration, text/DOM verification, repair, and atomic preview promotion, persisting an immutable checkpoint after every accepted step. No operation accepts image input, captures or compares screenshots/frames, calls a vision model, or produces a visual-review verdict. Visual quality is built in through the approved visual contract, explicit composition/resource/token plans, narrow builder contexts, and a final text/source-based integration pass; it is not a separate promotion gate. Code Generator may supplement the Build Preparation pack both when initial planning finds a gap and when a builder or repairer discovers a justified need. Models emit typed resource/dependency requests but receive no raw shell, filesystem, browser, network, package-manager, or promotion tool. Trusted acquisition adapters search only configured image, font, icon, component-source, and style-resource providers; enforce upstream source policy, creative-freedom limits, provenance, licence, type, size, decode/sanitization, and hash rules; materialize accepted resources locally; and record immutable receipts. Trusted dependency management alone may update the manifest and lockfile for supported component dependencies. `node_modules` and build output are disposable, excluded from model output and checkpoints, and recreated from the receipt-bound lockfile; acquisition may use controlled network, while generation, build, preview, and the generated portfolio remain offline/local-resource-only. Replace D-014's seven-gate screenshot matrix and two one-shot phase corrections with three lean blockers—source/contract integrity, clean type/build/artifact integrity, and headless text/DOM/runtime smoke checks—with configured finite repair cycles driven by normalized compiler, build, console, request, accessibility, and interaction diagnostics. Keep D-014's explicit start, durable idempotency, isolated workspaces, stable-current-preview, and crash-safe atomic promotion semantics.
- **Rejected alternatives:** Keeping screenshots but removing only the visual model (still creates capture/storage/matrix complexity without a decision-maker); build-only acceptance (misses route and interaction runtime failures); continuing to require Build Preparation to supply every possible resource (prevents composition-aware additions discovered during coding); giving a model unrestricted web, shell, npm, or filesystem tools (makes provenance, reproducibility, and recovery unreliable); accepting remote runtime hotlinks (makes the portfolio depend on third parties after generation); and an unbounded autonomous repair conversation (cannot guarantee termination or idempotent worker recovery).
- **Consequence:** `docs/code-generator-architecture/` remains the implementation contract for D-013 and D-015. The standalone four-phase workflow now provides the resource/dependency request schemas, configured acquisition adapters, provenance and dependency receipts, progressive checkpoints, diagnostic context assembly, bounded repair, clean text/DOM verification, and atomic preview promotion described here. Build Preparation remains the preferred source of approved resources; Code Generator supplementation cannot contradict user-media semantics, fixed facts, forbidden subjects, route authority, or the approved visual direction. Production session integration and automatic chaining remain a separate future task.

---

## D-014 — Code Generator v1 uses bounded generation, verification, repair, and atomic preview promotion

- **Date & Time:** 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** superseded-by-D-015
- **Context:** Code Generator is still a deterministic mock, while the product requires generation that fails safely, produces a content-specific advanced portfolio, and exposes no portfolio with route, code, runtime, interaction, responsive, accessibility, or visual-direction defects. The stage also needs to survive at-least-once worker delivery and regeneration without losing the last known-good preview. A free-running coding agent, unbounded repair conversation, or one-shot repository response cannot provide those invariants.
- **Decision:** Implement one explicitly started durable Code Generator stage whose configured planner, builder, and image-capable reviewer roles operate only through the provider-neutral boundary and native strict structured outputs; correction reuses the builder profile. Use three idempotent jobs—`code_generator.plan`, `code_generator.generate`, and `code_generator.verify_and_preview`—with immutable hashed checkpoints and durable receipts. Admit only Build Preparation pack v2; freeze a validated `SitePlan`; generate bounded, non-overlapping `FileChangeSet` objects inside a deterministic fixed React/Vite/TypeScript scaffold; and let trusted code own toolchain files, dependency-free routing, local assets, assembly, commands, and promotion. Require an exact-set verification matrix across source/static/type/build gates and isolated all-route browser, responsive, interaction, accessibility, reduced-motion, motion-frame, and image-based visual review. Normalize blocking failures into stable fingerprints and use a linear repair policy: one envelope reissue per model operation, one non-repeatable source/build correction slot for Gates 1-2, one non-repeatable browser/visual slot for Gates 3-5, and at most two corrective model calls total. Reuse correction receipts after redelivery; a repeated fingerprint exits as `STRATEGY_RECURRED`, while a consumed phase regression, out-of-scope change, or attempted third correction exits with an actionable terminal report. Persist `active_preview`, `current_attempt`, and `pending_promotion`; keep exactly one stable current preview on a dedicated preview origin and replace it only through crash-safe conditional receipt/pointer writes plus session CAS. Expose only GET state, POST start, and POST regenerate session routes; do not auto-chain, expose candidates or preview history, publish, or add approval/revision endpoints.
- **Rejected alternatives:** A single prompt that returns a whole repository (too large and has no enforceable ownership); a model with shell/filesystem/network/package or promotion tools (crosses the trust boundary); a multi-agent supervisor or open-ended coding loop (duplicates the durable queue and cannot bound retries); build-only acceptance (does not prove routes, interactions, responsive behavior, accessibility, or visual quality); publishing an unverified candidate or clearing the old preview at regeneration start (breaks the stable-preview invariant); and user-visible preview history in v1 (adds state and API surface unrelated to producing one reliable current result).
- **Consequence:** Implementation follows the ordered handoff in `docs/code-generator-architecture/README.md`. The shared provider contract must gain configured strict-schema and typed image-input capabilities; worker claiming must enforce configured free capacity and accepted job kinds; production mock mutation routes must be disabled; and the generator must persist enough fingerprints and receipts to resume idempotently and explain terminal failure. Model selection remains in `config/models.toml`; the checked-in `react-vite-v1` scaffold and exact toolchain are selected by a config-driven supported-runtime profile and immutable digest. Publishing and other non-MVP extensions require later decisions.

---

## D-013 — Repair only reproduced Build Preparation pack defects and issue pack v2

- **Date & Time:** 2026-08-13 10:36 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Code Generator consumer review reproduced three defects in the admitted Build Preparation v1 boundary. First, the production projection and archive omit approved global Visual Design Director fields—including visual language and shared navigation, motion, interaction, accessibility/performance, preservation, fabrication, compiler-handoff, and full asset-intent constraints—even though upstream approval hashing covers them. Second, the archive has route-scoped prose/data but no authoritative machine-readable route, criterion, fact, runtime, freedom, or file-reference contract; current VDD inline-page validation can also omit an approved route, while path echoes and lossy storage slugs can drift or collide. Third, asset source policy is carried but not enforced: approved-user, curated-local, or generated-local intent can enter external stock lookup, and critical external needs may never become required for handoff. These are reproduced omissions or false admissions, not generic requests to improve upstream creativity.
- **Decision:** Narrowly supersede D-012 and create semantic `build-preparation-pack-v2`. Add hash-covered `site/contract.json`, deterministically derived from the approved Content Architect projection, containing the canonical route graph and paths, collision-proof storage keys, ordered section/content references, stable fact/criterion/runtime/freedom IDs, and route-file pointers. Add hash-covered `design/visual-direction.json` containing the approved non-reasoning global and route-scoped visual contract plus full asset intent. Require exact Content Architect/VDD/package route equality whenever VDD pages are present; stamp canonical route facts from Content Architect; reject unsafe, duplicate, case-colliding, contradictory, partial, or ceiling-truncated scope. Enforce acquisition policy: only `optional_external_acquisition + needs_acquisition` may use configured stock providers; approved-user media must be locally verified or fall back honestly; curated-local and generated-local visual needs never use stock; critical external needs are `required_for_handoff`; negative concepts and forbidden subjects remain binding. Give the pack and target contract independent supported schema versions, hash every projection, and make `handoff-report.json` fail closed on missing, invalid, stale, mismatched, or incomplete evidence. Code Generator rejects or regenerates v1 packs and has no resource-acquisition path. Freeze every other Build Preparation responsibility and contract unless a future consumer reproduces another admitted-package defect and identifies its correct owner.
- **Rejected alternatives:** Inferring route paths or global visual rules inside Code Generator (would create a second, lossy source of truth); reading arbitrary upstream session state alongside the archive (breaks the immutable handoff boundary); silently treating v1 packs as v2 (hides missing input); and broadly redesigning Build Preparation, changing its model workflow, or adding quality features without a reproduced pack defect (reopens a verified stage speculatively).
- **Consequence:** The VDD coverage validator and Build Preparation receive one versioned, regression-tested boundary patch before real Code Generator work. Existing model workflow, provenance, per-route content, object-storage, read-back, staleness, job, API, and all unenumerated behavior remain frozen. Fresh v2 fixtures become the only Code Generator production inputs; historical packs remain diagnostic artifacts. D-012's consumer-evidence ownership rule survives, but its v1 freeze is superseded by this precisely bounded repair.

---

## D-012 — Freeze Build Preparation v1 and validate it through Code Generator consumption

- **Date & Time:** 2026-08-12 20:45 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** superseded-by-D-013
- **Context:** Independent production-handoff review found and fixed concrete Build Preparation admission, provenance, resource-planning, dependency, path-safety, and fixture-concurrency defects. The repaired contract now gives Code Generator approved route content, visual direction, local/provenanced resources, exclusive fallbacks/later-fetch rules, target constraints, and a deterministic `handoff-report.json`. Continuing to refine Build Preparation without a real consumer would be speculative and would delay Code Generator; conversely, declaring every future integration problem the fault of either stage would hide genuine contract defects.
- **Decision:** Freeze the Build Preparation v1 contract and begin Code Generator development. Treat an admitted, freshly regenerated pack as Code Generator's authoritative input; the currently reviewed historical packs remain immutable and are not production inputs when their handoff report or upstream approval is incomplete. Generic composition, repetitive sections/cards, weak responsive execution, poor animation, or failure to follow valid package instructions belong to Code Generator. Reopen Build Preparation or an upstream agent only when a reproducible consumer-contract failure shows that the admitted package omitted, contradicted, corrupted, or falsely admitted required facts, routes, visual direction, resources, provenance, paths, fallbacks, or target constraints.
- **Rejected alternatives:** Indefinitely polishing Build Preparation before Code Generator exists (rejected because no consumer evidence can justify further changes); treating every Code Generator problem as proof that Build Preparation failed (rejected because implementation quality belongs downstream); declaring every package/contract problem a Code Generator bug (rejected because admission and package correctness remain Build Preparation's responsibility).
- **Consequence:** Code Generator work may start immediately against the frozen contract and approved test fixtures. Before the first production build, approve the current Visual Design Director direction and regenerate so the package passes deterministic admission and R2 read-back verification. The first end-to-end build is a consumer-contract validation, but it does not reopen Build Preparation by default; any proposed upstream change must cite a reproduced package defect and its correct owner.

---

## D-011 — Rebuild Build Preparation as a real agent, from zero, superseding D-010

- **Date & Time:** 2026-08-11 (local) — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Implementation:** The new agent, durable wiring, deterministic ZIP packaging, verified temporary artifact storage, local debug mirror, and tests are implemented. Code Generator remains untouched and deferred.
- **Context:** The D-010 Portfolio Production Compiler (`src/oryxenai/build_preparation/`, 5,228 implementation lines + 1,457 test lines) was reported as producing empty output and not fetching images. Investigation found the code itself works (real Pexels/shadcn HTTP calls, real R2 upload/verify) but the fixture harness silently defaults to skipping all live provider calls, and the checked-in sample input has no photo requirement to trigger one — a design/discoverability problem, not a broken call. Separately, the module is ~2.2x the size of Visual Design Director for a non-creative packaging stage, lives outside `src/oryxenai/agents/`, and has no `AgentKey` entry — inconsistent with the established agent pattern (D-008).
- **Decision:** Retire `src/oryxenai/build_preparation/` entirely (no reuse of its code as a base) and rebuild Build Preparation from zero as agent #4 at `src/oryxenai/agents/build_preparation/`, mirroring the Content Architect/Visual Design Director file pattern (schemas/state/agent/service/validators/prompts, job handler, API routes, JSONB persistence, `AgentKey.BUILD_PREPARATION`). Keep Render + Supabase + R2 (no infra migration). Use the model liberally via structured-output calls wherever it adds real synthesis value (translating resource intent into provider queries, site-wide coherent selection, and — new — writing the screen-by-screen build brief itself), rather than minimizing model calls. Add Unsplash as a free-tier fallback behind Pexels with reactive rate-limit failover. Drop the per-image responsive-rendition matrix and full static-source import/export admission parsing in favor of a single verified rendition per asset and lighter hash/allowlist/dependency checks — Code Generator's own downstream build/typecheck already re-verifies component correctness. Full design in `docs/build-preparation-agent-proposal.md`.
- **Rejected alternatives:** Patching the existing `build_preparation/` module in place (rejected — architecture itself, not just a bug, was the complaint); a fully deterministic zero-model-call redesign (rejected by the user — this is meant to be a real AI agent, not a pure compiler); AI-generated image fallback via OpenAI images (rejected — stock photography with an honest typography/custom-visual fallback is sufficient and avoids new provenance/cost questions); migrating storage/hosting to Azure free tier (rejected — current Render/Supabase/R2 setup already works with live credentials).
- **Consequence:** `docs/portfolio-production-compiler-proposal.md` is marked superseded but kept for historical record. The new agent code, retired legacy package references, job/API/DB wiring, verified packaging/storage path, and tests are implemented under this decision. Code Generator remains untouched and deferred.

---

## D-010 — User-visible Portfolio Production Compiler as the pre-code boundary

- **Date & Time:** 2026-08-10 17:51 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** superseded-by-D-011
- **Context:** Fixture review of Build Preparation showed fallback-only manifests were insufficient handoffs for Code Generator. User needs observable progress without turning Code Generator into a rigid template assembler.
- **Decision:** Replaced preparation internals with a 5-operation Portfolio Production Compiler: experience compilation, site-wide resource planning, provider lookup/admission, site-wide selection, and context compilation/package verification (plus adaptive cross-route call if multi-route). Targets React/Vite/TS/Tailwind/React Router/Motion/Lucide, Pexels for photos, public shadcn-compatible registries (Magic UI/Aceternity). Persists immutable ZIP to temporary R2.
- **Rejected alternatives:** Hidden stage, multiple business agents/supervisors, per-scene calls, critic/repair loops, mandatory fixed visual templates/quotas, runtime provider access, dynamic package installs, Unsplash, remote fonts, production MCP.
- **Consequence:** Transitional fallback compiler will be retired after production compiler verification passes. Code Generator remains deferred and consumes extracted pack without provider/network access.

---

## D-009 — Deployment-independent temporary Build Preparation packs

- **Date & Time:** 2026-08-09 21:15 UTC — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Worker and API run in separate disposable containers; shared disk and Postgres byte storage are unsuitable for handoffs to Code Generator.
- **Decision:** Materialize one immutable, hash-verified ZIP per preparation run and upload to private S3/Cloudflare R2 under session/version namespace. Persist only object metadata, hash, and expiry in session JSONB.
- **Rejected alternatives:** Shared Docker named volumes/local disk (fails across multi-host deployments), PostgreSQL byte storage (bloats DB), permanent downloads/public signed URLs (artifacts are private pre-code inputs).
- **Consequence:** R2 storage credentials and TTL lifecycle policy required in production; expired packs regenerate from canonical approved upstream state.

---

## D-008 — Visual Design Director mirrors Content Architect architecture

- **Date & Time:** 2026-08-08 19:49 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Stage 3 needed implementation following Content Architect's proven bounded workflow pattern.
- **Decision:** Built VDD mirroring Content Architect: 5-status state machine, 3-operation workflow (`establish_visual_language`, `direct_page_experience`, `integrate_site_experience`), envelope-only validation, hash staleness check, JSONB session state persistence. Added deterministic in-process tag-overlap local resource catalogue (`catalogue.json`) queried before model calls.
- **Rejected alternatives:** `decision_basis` provenance field, internal-note leak backstop, deterministic code-computed visual quality heuristics in `validators.py`.
- **Consequence:** Future Code Generator work should check if this mirror pattern applies before inventing new patterns.

---

## D-007 — Restructure AI-agent context files around canonical AGENTS.md

- **Date & Time:** 2026-08-08 16:02 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Multiple AI tools (Claude Code, Codex CLI, Cursor, Antigravity) worked on repo; `CODEX.md` was not auto-discovered by standard tools and contained contradictions.
- **Decision:** Made `AGENTS.md` canonical cross-tool context. Reduced `CODEX.md` to redirect. Created `CLAUDE.md` (`@AGENTS.md` import), `CHANGES.md` (compacting changelog), and `DECISIONS.md` (ADR log).
- **Rejected alternatives:** Keeping `CODEX.md` canonical, merging decisions into `CHANGES.md`.
- **Consequence:** All AI sessions read `AGENTS.md` first; single source of truth for project facts.

---

## D-005 — Jinja2 + vanilla JS testing harness instead of framework frontend

- **Date & Time:** 2026-08-08 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Needed developer UI to test Discovery/Content Architect chat flow before final product frontend was designed.
- **Decision:** Minimal Jinja2 + vanilla JS server-rendered testing harness (`src/oryxenai/web/`) without external framework dependencies.
- **Rejected alternatives:** Building full React/Next.js product UI prematurely before core agent behavior stabilized.
- **Consequence:** Harness is developer-only and throwaway-adjacent; conversational contract documented in `docs/frontend-behavior-spec.md`.

---

## D-004 — Kept dormant discovery_opencode_go profile in config/models.toml

- **Date & Time:** 2026-08-07 21:00 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** After switching live model provider (D-003), old OpenCode Go profile became unused.
- **Decision:** Preserved dormant profile in `config/models.toml` for easy one-line rollback if needed.
- **Rejected alternatives:** Deleting unused profile for code cleanliness.
- **Consequence:** `config/models.toml` may contain multiple profiles per agent; only active profile referenced by code is used.

---

## D-003 — Switched Discovery/Content Architect to OpenAI API directly

- **Date & Time:** 2026-08-07 20:10 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go usage quota exhausted (`GoUsageLimitError`), blocking development.
- **Decision:** Pointed `[profiles.discovery]` and `[profiles.content_architect]` directly to OpenAI API via `OPENAI_API_KEY`. Extended `ModelCapabilities` for provider-specific API quirks (e.g. `uses_max_completion_tokens`).
- **Rejected alternatives:** Waiting for monthly quota reset, hardcoding provider special-cases in agent logic.
- **Consequence:** Preserved rollback path (D-004); generic `ModelCapabilities` system handles provider differences.

---

## D-002 — v1 Discovery over-engineering, then v2 simplification

- **Date & Time:** 2026-08-07 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Earlier Discovery implementation had source document tables, repair-prompt loops, 20-file few-shot libraries, and fact-graph validation layers.
- **Decision:** Stripped over-engineered components: intake stored as session JSONB, inline contrastive prompt examples, envelope-only output validation.
- **Rejected alternatives:** Retaining complex validation and multi-table graph machinery.
- **Consequence:** Established repository bias toward envelope-only validation and prompt-carried examples over heavy structural machinery.

---

## D-001 — Explicit Python agents over an agent framework

- **Date & Time:** 2026-08-06 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Needed structure for agent model execution before tool-calling/routing requirements were known.
- **Decision:** Used plain Python protocols (`Agent`, `ModelClient`) and Pydantic models without external frameworks.
- **Rejected alternatives:** LangChain, LangGraph, CrewAI, AutoGen (imposed premature abstractions and obscured testability).
- **Consequence:** Frameworks deferred until concrete need demonstrated; agents own explicit schemas, prompts, and execution.

---

## Compacted & Superseded History

- **D-006** — 2026-08-08 15:30 UTC — Claude Code (Claude Sonnet 5 / Anthropic) — Visual Design Director & Code Generator deferred; no auto-chaining from Content Architect *(superseded by D-008 on Visual Design Director implementation)*

---

## Compaction & Archiving Procedure (for AI tools: Codex, Claude, Cursor, OpenCode, Antigravity)

**Trigger:** If `DECISIONS.md` reaches or exceeds **350 lines**, run compaction before appending a new decision entry.

**Procedure:**
1. **Active Decisions:** Keep decisions with `Status: open`, `Status: decided-not-yet-implemented`, or `Status: decided-implemented` under `## Active Decisions` using high-density bullet points.
2. **Superseded Decisions:** Move superseded entries to `## Compacted & Superseded History` as concise single-line entries:
   `- D-0XX — YYYY-MM-DD HH:MM TZ — <Agent/Tool> (<Model/Provider>) — <short title> (superseded by D-0YY)`
3. **Summary Recomputation:** Recompute the `## Summary` block below reflecting active vs. superseded counts and tool distribution.

---

## Summary (as of last update — 2026-08-13)

- Total decisions logged: 15
- Active decisions: 11 (D-001 through D-005, D-007 through D-009, D-011, D-013, D-015)
- Superseded decisions: 4 (D-006 compacted under history; D-010, D-012, and D-014 remain expanded because the file is below the 350-line trigger)
- By tool: Codex (6), Claude Code (4), Unspecified/Retroactive (5)
- Last updated: 2026-08-13 — Codex (GPT-5 / OpenAI)
