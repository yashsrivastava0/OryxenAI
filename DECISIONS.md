# OryxenAI — Decisions & Open Issues

Architecture Decision Record (ADR) log of architectural choices, trade-offs, and invariants. Read before making design changes.

**Policy:**
- Log only real architectural decisions with concrete trade-offs (not routine code changes).
- Maintain reverse-chronological order (newest first under `## Active Decisions`). Entry IDs (`D-001`, `D-002`, ...) are permanent and never reused.
- Keep entries high-density, concise, and machine-readable for AI agents.
- When superseded, move the entry to `## Compacted & Superseded History` with a single-line summary referencing the superseding decision.

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

## D-068 — Close the QUALITY_REVIEW_REJECTED_AFTER_REPAIR and INTEGRATION_POLISH_INCOMPLETE control-flow gaps; extend the resource-catalogue pattern to motion

- **Date & Time:** 2026-09-05 14:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** D-067 left the pipeline at its documented frontier: a live run reached final verification for the first time and landed on `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` with one easily-fixable finding (an ARIA target pointing at a paragraph instead of a heading), scores otherwise ≥4. Direct code tracing (confirmed against a second, independent Plan-agent pass) showed this was a pure control-flow gap, not a capability or budget problem: `_attempt_repair`'s post-repair whole-site re-review rejection raises `VerificationFailure` from outside its own bounded retry loop, so it can never consume another round of the existing 6-total/3-per-unit repair budget — the observed case had used only 1 of 6 rounds. Given ~40 prior live-bugfix commits and a pipeline that had just reached its best-ever result, the evidence did not support a rewrite. Live testing this session (after the fix below) surfaced the identical class of gap one stage earlier: the mid-generation whole-site polish loop's owner-scoped repair call (`_review_and_polish`) raised `INTEGRATION_POLISH_INCOMPLETE` and killed the entire run the moment a repair attempt reported `cannot_complete` (repair_source.md's honest escape hatch), even on the very first attempt, even though the outer polish-round loop is already bounded (`max_integration_polish_rounds`, D-067) specifically to give a different round another try. Separately, the single most expensive, most-repeated call in the whole pipeline (whole-site integration review, up to 8x/run, up to ~600,000 chars of context) had zero `request_context` prefix-caching support, unlike 4 of the other 5 call sites. The scaffold's motion system was also found to be completely empty (`motion.css` only a reduced-motion safety net) — every portfolio's animation is invented from scratch by the model in every route_batch/route_compose call, the one remaining unconstrained surface in a pipeline that already uses a deterministic catalogue-and-select pattern for images/fonts/components.
- **Decision:** (1) `_attempt_repair` (`jobs/handlers/code_generator_verification.py`) refactored into `_run_bounded_repair`/`_rereview_after_repair`/`_diagnostics_from_quality_findings` helpers; a rejected post-repair re-review now gets exactly one bounded extra repair+re-review attempt (converting the rejection's blocking findings into `Diagnostic`s and reusing the existing numeric budget) before raising terminally — the re-review itself runs at most twice total, never a third time, regardless of remaining budget. (2) `_review_and_polish`'s owner-scoped repair call now logs and `break`s (skipping that owner for the round) instead of raising on a non-"changes" result, letting the pre-existing bounded polish-round loop keep trying or converge to the pre-existing `INTEGRATION_REVIEW_UNRESOLVED` terminal state. (3) Added `INTEGRATION_REVIEW_KEY_ORDER` (`generation_prompt_builder.py`) and wired `request_context`/`prompt_cache_key` into `integration_review_operation.py`, ordering run-invariant content before the two always-changing scalars (`round`, `source_manifest`) and the large `assembled_source` dict — confirmed live via non-zero `cached_prompt_tokens` in persisted usage. (4) Added `core/motion_pattern_catalogue.py` (3 patterns: reveal-fade-rise, reveal-clip-lines, stagger-group) and an optional `MotionBeatV4.pattern_id` field; when set, `generation_contract.py` instructs route_batch/route_compose to apply a named trusted `SharedSystems.tsx` component exactly instead of hand-authoring new CSS/JS — confirmed live, the planner set `pattern_id` on a real beat on the first live attempt. Also captured raw model `usage` at 3 call sites that previously discarded it (director, redirect-director, final-repair), and added advisory screenshot capture to DOM/runtime verification (zero extra cost, the browser context is already open) since the pipeline had never once captured visual evidence of a generated portfolio.
- **Rejected alternatives:** A ground-up Code Generator rewrite — rejected given ~40 hard-won live-bugfix commits and a pipeline that reached a near-passing final verification on its very last real run; the evidence supported surgical fixes, not a rewrite. Raising `max_repair_rounds_total`/`max_repair_rounds_per_unit` to fix the first gap — rejected, per D-067's own reasoning still standing: the fix works within the existing ceiling and adds its own independent hard cap of exactly one extra attempt, rather than loosening a budget with only one data point. An OpenAI Batch API for the caching work — rejected again per D-040/D-066: still an architectural mismatch for this sequentially-dependent pipeline. A general per-profile cost-tracking/pricing feature — rejected as disproportionate plumbing for a ~$5 total live-verification budget; raw usage capture plus hand-computed cost against the real price sheet is sufficient. Shipping more than 3 motion patterns in this pass — rejected in favor of the 3 lowest-implementation-risk patterns first (no rAF loop or scroll-progress math), deferring count-up/parallax-drift/hover patterns to a follow-up.
- **Consequence:** Two live runs against the eligible pack this session (~$0.06-$0.21 total at published Luna rates) confirmed Fix (3)'s real cache hits and Fix (4)'s live catalogue usage, and surfaced (and got a same-session fix for) the `INTEGRATION_POLISH_INCOMPLETE` gap. Two further attempts were killed by real system memory pressure (not a code defect) before reaching final verification, so Fix (1)'s exact retry firing was not directly witnessed live this session — its bound is proven by 2 new + 1 unchanged regression test instead (`test_attempt_repair_retries_once_after_quality_rejection_then_accepts`, `test_attempt_repair_gives_up_after_one_quality_rejection_retry`). A future session should re-run against the same pack once memory pressure eases and confirm Fix (1) live; `code generator issues.md` should be updated with whatever it finds.

## D-067 — Identify the duplicate path in SOURCE_DUPLICATE_PATH; raise the integration-polish ceiling on live evidence

- **Date & Time:** 2026-09-05 00:55 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** The account behind `OPENAI_API_KEY` was recharged with a corrected key (confirmed live via a cheap, no-content preflight call before any paid generation ran), so Code Generator moved back off ScaleMax onto direct OpenAI. A live run then hit a new, real defect: the v4 duplicate-file-path check in `generation_orchestrator.py` (`_validate_v4_generation_coverage`) raised `SourceValidationError("SOURCE_DUPLICATE_PATH", ...)` without a `file=` value, unlike its sibling checks — the repair model, given a diagnostic naming no file, correctly reported it couldn't make a bounded fix rather than guess (the project's own "honest cannot_complete over guessing" design working as intended, just starved of the one fact it needed). Separately, two independent live runs this session — one on ScaleMax, one on direct OpenAI, same pack — both converged the integration-review polish loop steadily each round (3 blocking findings down to 1, then one lone "bounded motion correction" per the reviewer's own words) but ran out of the `max_integration_polish_rounds` budget (`Field(default=3, ge=1, le=3)`) while still making real progress, not while stuck.
- **Decision:** The duplicate-path check now finds the actual duplicated path(s) and passes the first one as `file=`, with a message naming it explicitly (`generation_orchestrator.py`); new unit test `test_v4_duplicate_path_identifies_the_offending_file`. `max_integration_polish_rounds` raised from `Field(default=3, ge=1, le=3)` to `Field(default=5, ge=1, le=6)` in `core/settings.py`, `config/app.toml` updated to match.
- **Rejected alternatives:** Raising `max_repair_rounds_total`/`max_repair_rounds_per_unit` (the separate final-verification repair budget, D-056/D-058) in the same pass — rejected for now: only one live data point exists showing it too tight (a `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` on a single `missing-section-heading` finding after the polish-ceiling fix let a run reach final verification for the first time), versus two independent cross-provider data points that justified the polish-ceiling raise. A second confirming run is needed before touching an already-separately-reasoned budget. Guessing which file was duplicated instead of computing it — rejected as exactly the kind of invented-authority shortcut the project's validation layer exists to prevent.
- **Consequence:** A live OpenAI run with both fixes reached final verification (build + repair + whole-site re-review) for the first time this session — past the previous universal generate-stage bottleneck entirely — before landing in `needs_attention` on the separate, narrower `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` gate (one real, specific, easily-fixable accessibility finding: a paragraph used where a heading should be). See `code generator issues.md` for the current frontier and next verification target.

## D-066 — Route Code Generator through ScaleMax and restate strict schemas as prompt text

- **Date & Time:** 2026-09-04 20:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Direct OpenAI hit `PROVIDER_RATE_LIMIT_ERROR` during route generation even after D-065's serialization. The user supplied a second OpenAI-protocol gateway, ScaleMax, live-verified serving the same `gpt-5.6-luna` model. Switching surfaced a second, unrelated live-only defect: ScaleMax accepts a `strict: true` `json_schema` request (200 OK) but does not reliably enforce it — the director's `CreativeDirectionSetV3` response omitted required fields, mistyped others, and (once the obvious literal-mismatch was fixed) invented an unlisted property (`motion` instead of `motion_vocabulary`). Separately, `prompt_cache_ttl` was configured on every Code Generator profile but was dead code for the OpenAI-compatible adapter (only Anthropic's adapter read it), and the untrusted-input wire payload's `sort_keys=True` serialization interleaved each call's unique keys among the large content that repeats byte-for-byte across a run, defeating any provider-side prefix caching before it could start.
- **Decision:** All 7 Code Generator profiles (`config/models.toml`) move to `provider = "scalemax"` (new dispatch entry in `providers/factory.py`, reusing the existing generic `OpenAICompatibleAdapter` — no new adapter class needed), same model/timeouts/budgets otherwise. `opencode_go.py`'s `_generate_structured_impl` now always restates the exact strict schema as explicit prompt text when `strict_schema=True` (every Code Generator call), in addition to the `response_format` request — redundant-but-harmless for a gateway that already enforces it, a real safety net for one that doesn't. `system.md` gained an explicit "never omit a required field, copy literal enum values exactly" rule. Added an opt-in `request_context={"key_order": [...]}` hook on the previously-unused `request_context` parameter already present on `ModelClient.generate_structured`, so Code Generator's own call sites (director/planner, route batch/compose/integrate/repair, final repair) can place invariant per-run content first and per-call content last in the wire JSON — same JSON shape, no prompt/schema change, zero effect on any other agent, which never sets it. Added an optional `prompt_cache_key` (`codegen:{generation_id}:{role_profile}`), gated by a new `supports_prompt_cache_key` capability flag set only on the 7 Code Generator profiles, mirroring the existing `store` capability-gated pattern.
- **Rejected alternatives:** A bespoke ScaleMax adapter class — rejected because the existing generic OpenAI-protocol adapter already takes `base_url`/`api_key_env` entirely from the profile. Downgrading `structured_output_mode` away from `native_json_schema` for all 7 roles — rejected on 2 data points from one role (director) as too broad a reaction; the narrower prompt-text-restatement fix targets the observed failure directly without discarding a working guarantee elsewhere. An OpenAI-style Batch API for cost — rejected per D-040's reasoning, unchanged: Code Generator's stages are sequentially dependent within one durable job, which does not fit batch's asynchronous turnaround. Reordering the wire payload's actual key insertion order everywhere it's built — rejected as far more invasive than a single opt-in serialization parameter with a safe default.
- **Consequence:** A live run against the supplied test pack got through admission, planning, acquisition, foundation generation, both route batches, route composition, and 3 integration-review/repair polish rounds — the deepest any run reached this session — before landing in `needs_attention` on `INTEGRATION_REVIEW_UNRESOLVED` (a real, specific, mostly-plausible-to-fix review finding set, not a crash or silent failure). See `code generator issues.md` for the full findings table and the new blocker. Real cache-hit savings from the `request_context`/`prompt_cache_key` work were not independently confirmed this session — usage/token data is never persisted to disk in this pipeline, so no post-hoc check was possible; a future session should temporarily log `result.usage` to confirm.

## D-065 — Serialize route-batch provider calls in the bounded generation lane

- **Date & Time:** 2026-09-04 16:05 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Concurrent route-batch generation calls trigger provider 429 rate-limit exhaustion, obscuring whether generation itself is sound.
- **Decision:** Set `route_concurrency = 1` for Code Generator in `config/app.toml`. Keep work-graph parallel-safe, but serialize billable calls and resume from same-run checkpoints.
- **Rejected alternatives:** Raising retries or starting fresh runs (wastes quota without increasing provider capacity); eliminating route batching (bounds context & section ownership); treating 429 as success (publishes incomplete code).
- **Consequence:** One provider call in flight at a time; 429 rate limits are retried once after window reset without re-executing completed foundation/acquisition steps. Readiness status uses shared TTL cache.

## D-064 — Code Generator consumes Markdown briefs through a fenced v5 pipeline

- **Date & Time:** 2026-09-04 16:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** D-062 replaced Build Preparation ZIP packs with two Markdown briefs. Code Generator required admission migration, release fencing, and protection against registry import drift.
- **Decision:** Parse and hash fenced brief JSON indexes at admission. Run active consumer under `code-generator-v5` queue namespace with worker release fencing. Canonicalize distinctive ratios and typography before blueprint validation. Pinned visual references fetch at generation time; optional component registry source is kept in durable materials as reference-only while generated site builds local accessible equivalents.
- **Rejected alternatives:** Restoring ZIP creation/byte embedding (recreates D-062 storage/expiry bloat); allowing v4 workers to claim v5 jobs (mixed rollout schema mismatches); relaxing schemas globally (fails closed on malformed plans; normalizes only deterministic rounding).
- **Consequence:** Markdown briefs directly consumable by standalone and session Code Generator paths. Old workers cannot claim v5 jobs. Pinned images/fonts remain local and browser-addressable; missing optional components fallback safely.

## D-063 — Authenticated product release ends at approved Visual Design Direction

- **Date & Time:** 2026-09-04 05:08 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Normal-user Preact shell exposed incomplete Build Preparation, Code Generator, and Preview stages, while local detached auth mode bypassed real product auth.
- **Decision:** `/app` product journey exposes exactly Discovery, Content Architect, and Visual Design Director, ending at approved direction. Stage transitions require explicit POST calls; no auto-chaining. Product uses `auth.pipeline_mode = "attached"`; developer harnesses use `auth.development_harness_mode = "detached"`.
- **Rejected alternatives:** Displaying later stages as disabled/"coming soon" (advertises incomplete flow); leaving product in detached mode (bypasses auth acceptance); weakening backend authorization on later stages.
- **Consequence:** Verified end-to-end 3-agent creative journey with attached Supabase/Google authentication. Build Preparation and Code Generator remain accessible only via developer routes/APIs until explicitly released.

## D-062 — Build Preparation emits two Markdown briefs instead of a versioned resource pack

- **Date & Time:** 2026-09-03 18:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented (Code Generator consumer follow-up completed by D-064)
- **Context:** Build Preparation accumulated ~6,000 lines of byte-downloading, pixel inspection, ZIP packaging, and R2 upload machinery that duplicated downstream Code Generator capabilities.
- **Decision:** Simplify Build Preparation to: (1) Stage 0 scope compilation; (2) search-only discovery research (`resource_research.py` + discovery-only `providers.py`, zero byte downloads); (3) single bounded model call (`compose_visual_brief`) picking candidates by index from researched list or null; (4) deterministic assembly of `content-and-narrative-brief.md` (verbatim Content Architect text) and `visual-and-build-brief.md` (model direction + resource tables), each with one fenced JSON index block. Persist directly on `portfolio_sessions.current_state["build_preparation"]`. Delete packager, materializer, quality, execution, contracts, and checkpoint modules.
- **Rejected alternatives:** Retaining pack-shaped JSON/ZIP without bytes (preserves unnecessary packaging ceremony); prose-only Markdown without structured JSON block (breaks deterministic ID compilation); simultaneous Code Generator rewrite in one pass.
- **Consequence:** Supersedes D-009, D-011, D-013, D-018, D-021, D-025, D-028, D-035, D-051, D-060, D-061. Upstream makes resource decisions; downstream Code Generator acquires bytes at generation time.

## D-059 — Single root .env configuration and pure adapter normalization for Frontend Phase 2

- **Date & Time:** 2026-09-02 22:30 +05:30 — Antigravity (Gemini 2.5 Pro / Google)
- **Status:** decided-implemented
- **Context:** Frontend Phase 2 needed configuration alignment with backend settings, preventing secret leakage and synchronizing cross-tab stage state.
- **Decision:** Use single root `.env` for repository. Frontend build has zero embedded secrets; reads public runtime config dynamically from FastAPI. Client adapters normalize backend responses into pure immutable state models. Synchronize cross-tab stage changes via `BroadcastChannel`.
- **Rejected alternatives:** Maintaining separate frontend `.env`; client-side secret access; manual polling across tabs.
- **Consequence:** Zero client secret exposure; single source of truth for configuration; real-time tab state synchronization.

## D-058 — A cannot-complete repair result consumes one budgeted round, not the whole budget

- **Date & Time:** 2026-09-02 15:30 +05:30 — Claude Code (Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** In final verification, an honest `cannot-complete` or host-side content validation error aborting immediately bypassed multi-round repair budgets.
- **Decision:** In `_attempt_repair` (`code_generator_verification.py`), catch `FinalRepairError` and `SourceValidationError` separately. Check `RepairBudget.can_attempt`; while budget allows, retry with `bounded-simplification` strategy hint. Update `projection.repair_rounds` on every attempt. Genuine infrastructure crashes still fail immediately.
- **Rejected alternatives:** Treating any repair exception as immediately terminal; retrying infrastructure/provider network crashes within one job invocation.
- **Consequence:** Honest single-round repair failures do not prematurely terminate runs with remaining budget; receipts accurately track attempted rounds.

## D-057 — Compiler-owned bridge for fixed shadcn semantic slots

- **Date & Time:** 2026-09-02 02:01 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Tailwind registry components use fixed shadcn semantic classes (`--color-<slot>`), which resolve to unbound colors without a theme bridge.
- **Decision:** Add `shadcn_theme_bindings` optional literal-key mapping from shadcn slots to model's exact `colors[].name`. Emit deterministic `--color-<slot>` aliases through checked-in Tailwind v4 `@theme inline` bridge. Provider JSON schema is closed; invalid slots fail local validation with single corrective retry.
- **Rejected alternatives:** Hardcoding palette values (violates D-034); trusting provider cssVars authority; making every slot mandatory.
- **Consequence:** Standard shadcn/Tailwind components adopt portfolio-specific color tokens deterministically before generation.

## D-056 — Final verification repair budgets are per diagnostic group

- **Date & Time:** 2026-09-02 01:15 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Multiple verification gates (source, build, runtime) sharing a single synthetic `final` repair budget caused premature exhaustion on one gate.
- **Decision:** Apply configured per-unit repair ceiling independently to each diagnostic group (source, build, runtime), while enforcing one shared total ceiling and fingerprint recurrence policy. Failed repair must return bounded source change or honest `cannot-complete`.
- **Rejected alternatives:** Raising global per-unit limit (masks repeated failures); removing per-unit ceiling (unbounded looping on single gate).
- **Consequence:** Independent gates utilize separate repair budgets without exceeding run-wide limit; receipt history remains fail-closed.

## D-055 — Code Generator uses dedicated per-role model profiles

- **Date & Time:** 2026-09-02 01:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Standalone Code Generator has 7 distinct roles (director, planner, scout, builder, composer, integrator, repairer), but app routed all through a single profile.
- **Decision:** Route each role in `config/app.toml` through matching dedicated profile IDs in `config/models.toml`. Keep role profiles separate from general pipeline default profile.
- **Rejected alternatives:** Single shared profile for all roles (prevents per-role optimization and granular receipt auditing); hardcoding providers in agent code.
- **Consequence:** Role-specific model tuning, context window adjustments, and provider routing without modifying code.

## D-054 — Shared preview gateway is part of the default Docker stack

- **Date & Time:** 2026-08-27 03:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Standalone preview gateway was profile-gated in Docker Compose, leaving hosted environments unable to serve verified preview objects.
- **Decision:** Include `preview-gateway` in default Docker Compose topology alongside API and worker. Probe via `http://preview-gateway:4174/health/live`. Previews remain immutable S3-compatible objects; local dev uses filesystem storage.
- **Rejected alternatives:** Leaving gateway profile-gated; creating dedicated container per portfolio preview; merging isolated dev harness into main production stack.
- **Consequence:** Consistent containerized preview boundary across local and hosted environments.

## D-053 — Extend temporary detached auth to the Code Generator standalone dev harness

- **Date & Time:** 2026-08-25 21:10 +05:30 — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Standalone Code Generator harness (`code_generator_development.py`) was admin-gated, preventing local iteration when `pipeline_mode = "detached"`.
- **Decision:** Mirror D-052 router-split pattern: mount `detached_router` (no auth dependency) when `pipeline_mode == "detached"`, and `router` (`require_admin`) in attached modes. Keep session-bound production routes (`code_generator.py`) fully protected.
- **Rejected alternatives:** Removing auth from production Code Generator routes; inventing an ad-hoc bypass mechanism.
- **Consequence:** Standalone development harness operates login-free in detached mode; production routes retain full Phase 3/4 auth and entitlement enforcement.

## D-052 — Extend temporary detached auth through the Build Preparation fixture

- **Date & Time:** 2026-08-25 20:09 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Build Preparation fixture required administrator API token and redirected to sign-in even when main pipeline was detached.
- **Decision:** In `auth.pipeline_mode = "detached"`, Build Preparation fixture and progress APIs accept anonymous requests; browser skips Supabase bootstrap. Attached, Docker, and production modes retain strict admin authentication.
- **Rejected alternatives:** Disabling auth globally; client-only bypass without API alignment.
- **Consequence:** Supersedes D-049. Native developer fixture opens directly without login friction; protected production environments remain fail-closed.

## D-050 — Detached pipeline model selection and privacy-free preflight

- **Date & Time:** 2026-08-25 11:54 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Detached development required switching model profiles for testing without leaking credential configuration or sending portfolio context during preflight.
- **Decision:** Expose detached-only APIs for allowlisted profile labels and fixed-schema, no-context preflight. Selection persists in Discovery and is inherited by downstream stages. Attached modes fail closed.
- **Rejected alternatives:** Exposing provider endpoints/credentials to frontend; preflighting with real user documents; allowing stages to diverge profiles mid-run.
- **Consequence:** Privacy-safe preflight; persistent run-level model selection in detached development.

## D-048 — Make Google registration open by deployment configuration

- **Date & Time:** 2026-08-24 18:30 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Initial 3-account email allowlist blocked valid Google OAuth onboarding and conflicted with Google's OAuth testing limits.
- **Decision:** Introduce `auth.admission_mode`: `open` admits any verified Google account up to database capacity of 15 normal users; `allowlist` restricts admission via `ORYXENAI_ALLOWED_USER_EMAILS`. Bootstrap admins bypass normal-user capacity.
- **Rejected alternatives:** Removing server capacity gate; client-side access toggles; application-level passwords/OTP.
- **Consequence:** Self-serve onboarding for early access up to 15-user quota; strict server-side capacity enforcement.

## D-047 — Complete Phase 4 administrator lifecycle with resumable local authority

- **Date & Time:** 2026-08-24 14:40 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Administrator actions (user deletion, portfolio reset, audit logging) required database-authoritative safety across external Supabase and preview storage systems.
- **Decision:** Add linear Alembic migration for lifecycle state, admin operations audit, and identity tombstones. Require active onboarded admin, target confirmation, bounded idempotency keys, and short DB transactions. Fence queued work; delete only exact session-scoped storage/local paths; call Supabase Admin API for provider user suspension/deletion; require explicit audited readmission. Entitlement resets permitted only after verified project deletion.
- **Rejected alternatives:** Browser-only admin checks; provider metadata roles; broad storage prefix deletion; automatic deleted-user readmission; treating failed provider calls as completed deletion.
- **Consequence:** Safe, resumable, audited admin lifecycle operations; deleted users cannot re-enter via JIT admission.

## D-046 — Enforce Phase 3 entitlement and worker safety in PostgreSQL-backed durable state

- **Date & Time:** 2026-08-24 04:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Normal users required enforcement of 1 session, 1 variant, and 1 promoted portfolio success, while background jobs required immunity to late ownership changes.
- **Decision:** Create `portfolio_entitlements` row per normal user in migration `0016_auth_entitlements_worker_fencing`. Persist local session/owner/actor snapshots on jobs and runs. Worker reauthorizes snapshots immediately before claiming work, enqueuing successors, and finalizing preview promotion. Enforce single global PostgreSQL `model-generation` concurrency lane via partial unique index. Admins are entitlement-unlimited.
- **Rejected alternatives:** Client-side quota; in-process worker mutex; trusting job payloads; consuming success entitlement before verified promotion.
- **Consequence:** Multi-worker safe entitlement enforcement; server-idempotent Code Generator execution; changed owner/entitlement fences late jobs fail-closed.

## D-045 — Execute Phase 2 as session ownership and API authorization retrofit

- **Date & Time:** 2026-08-24 02:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Pre-existing portfolio sessions were globally ID-addressable and lacked user ownership boundaries.
- **Decision:** Add `portfolio_sessions.owner_user_id` with `ON DELETE RESTRICT` and `legacy_quarantined` state. Quarantine all pre-Phase-2 sessions. FastAPI dependencies and `PortfolioAccess` enforce ownership: normal users see only owned non-legacy sessions; admins can access owned and legacy sessions. Protect all nested stage routes.
- **Rejected alternatives:** Assigning legacy sessions to first login; client-asserted user IDs; in-memory Python filtering; browser Data API policies.
- **Consequence:** Strict multi-tenant session isolation; legacy test sessions quarantined to admin view.

## D-044 — Execute authentication Phase 1 without advancing authorization phases

- **Date & Time:** 2026-08-23 23:45 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Required an independently testable identity layer without prematurely mutating portfolio ownership or worker authorization.
- **Decision:** Phase 1 delivers: Supabase Google-only session restoration, server-side asymmetric JWT/JWKS verification, JIT `app_users` admission with 15-user capacity gate, 2 bootstrap admins, username onboarding, and `GET /api/v1/me`. Portfolio routes left unchanged pending Phase 2.
- **Rejected alternatives:** Combining identity, ownership, and entitlements into one mega-migration; client metadata authorization.
- **Consequence:** Isolated identity foundation; clean separation between authentication and downstream authorization phases.

## D-043 — Supabase Google identity with database-authoritative authorization

- **Date & Time:** 2026-08-23 20:48 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Needed managed authentication for small allowlisted deployment without managing passwords, custom OAuth tokens, or redundant identity services.
- **Decision:** Use Supabase Auth solely as IDP with Google sign-in. FastAPI verifies asymmetric Supabase JWTs. PostgreSQL is authoritative for user records, usernames, roles, 15-account capacity, resource ownership, and entitlement state. Roles/authorization never derived from client metadata or query parameters.
- **Rejected alternatives:** Clerk (adds redundant service); public registration without capacity gate; custom password/OTP auth; frontend-only quota.
- **Consequence:** Authoritative local database authorization backing external Google identity; fail-closed token validation.

## D-042 — Stable retry and explicit new-variant semantics

- **Date & Time:** 2026-08-23 00:00 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Retries on infrastructure failures must not burn external model calls or overwrite verified previews, while intentional regenerations must produce distinct creative work.
- **Decision:** Automatic retries and POST `/retry` reuse the run's immutable variant receipt, fingerprint, accepted checkpoints, and preview. Explicit POST `/regenerate` creates a new run/variant, checks fingerprint divergence from recent variants, and fails closed if output is too similar.
- **Rejected alternatives:** Creating new design variant on every retry; in-place mutation of accepted variants; deleting active preview before replacement is verified.
- **Consequence:** Idempotent, safe retries; controlled, verifiable design diversity on intentional regeneration.

## D-041 — Code Generator V4 provider-compatible contracts and preview truth

- **Date & Time:** 2026-08-21 22:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** V3 generation allowed schema drift between development and session paths, marker-only visual assertions, and loose preview gateway CSP.
- **Decision:** Introduce mapping-free v4 typed contracts (creative, blueprint, search-intent, source-envelope, quality-receipt, typed-token). Compile semantic route ownership deterministically; execute whole-site review across dev and session runs; retain verified candidates as `preview_pending` on publication failure; enforce strict iframe embed-origin CSP on preview gateway.
- **Rejected alternatives:** Replacing v3 in place without backward-compatibility; marker text as visual proof; wildcard iframe CSP.
- **Consequence:** Fail-closed validation on missing executable evidence; precise provider diagnostic receipts; resilient preview preservation.

## D-040 — Configuration-driven Anthropic default and model routing

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Needed unified model switching across engines without scattering provider conditionals in agent code.
- **Decision:** Route all engines through shared `ModelRouter` and provider-neutral `ModelClient`. Committed profile uses Anthropic Claude Sonnet 5 with `ANTHROPIC_API_KEY`, adaptive thinking, and schema declarations. Configuration lives in `config/models.toml`; API exposes non-secret metadata only.
- **Rejected alternatives:** Hardcoding provider branches in agents; client-driven provider overrides; silent fallback to mocks for live jobs.
- **Consequence:** Changing model or provider is a TOML configuration change; live operations fail closed when credentials or capabilities are missing.

## D-039 — Backend-only Docker and shared hosted portfolio previews

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Ephemeral free-tier container hosting makes per-portfolio containers expensive and fragile. Static React/Vite portfolios need lightweight hosting.
- **Decision:** Docker packages only OryxenAI API, background worker, migration environment, browser verifier, and shared preview gateway. Generated portfolios remain portable source trees + `dist/`. Hosted previews use immutable S3-compatible objects behind shared gateway; local dev uses filesystem.
- **Rejected alternatives:** Spawning a container or deployment per portfolio; serving preview HTML directly from container filesystem; running generated app as dev server.
- **Consequence:** Inspectable, portable static outputs; shared preview origin eliminates per-site infrastructure costs.

## D-038 — Promotion requires content-addressed artifact reuse and terminal diagnostics

- **Date & Time:** 2026-08-21 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Provider schema errors, invalid plan layouts, and browser verification crashes were causing infinite retries or false-positive promotions.
- **Decision:** Provider capability negotiation at shared boundary; 1 bounded correction attempt for invalid planner output; route workspaces are source-only with shared dependencies; browser verification runs in isolated directories with tokens; preview promotion allowed only when source, build, and DOM runtime checks agree.
- **Rejected alternatives:** Hardcoded portfolio repair heuristics; unbounded model retries; reinstalling node_modules per route wave.
- **Consequence:** Deterministic, bounded repair cycles; terminal failures persist diagnostic reports without silent retry looping.

## D-037 — Provider wire contracts and no-context Code Generator admission

- **Date & Time:** 2026-08-21 00:30 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Model providers reject typed schema mappings before planning, while readiness checks could claim success without exercising the live provider.
- **Decision:** Declare wire capabilities in config. Adapter emits native JSON Schema for supported subset, using schema prompting + local validation for typed mappings. Require no-context provider preflight before live runs; retry structurally invalid planner responses once with bounded feedback.
- **Rejected alternatives:** Hardcoded per-portfolio schemas; silent provider fallback; treating API ping as model readiness.
- **Consequence:** Provider incompatibilities caught before sending portfolio data; actionable admission errors in UI before durable jobs launch.

## D-036 — Enforce generated source and runtime contracts without visual evidence

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Generating visual layout requires concrete source and DOM invariants rather than unverified LLM text claims.
- **Decision:** Deterministic TypeScript source audit and exact DOM/runtime checks (AST syntax, imports, exports, non-empty text, interactive element contrast/reachability). Multi-viewport headless Chromium verification before promotion.
- **Rejected alternatives:** Trusting LLM claims of layout validity; relying solely on `vite build` without runtime DOM verification.
- **Consequence:** Every promoted portfolio is guaranteed syntactically valid, type-clean, and geometrically renderable across desktop and mobile viewports.

## D-034 — Design-neutral Code Generator V3 with compiler-owned behavior

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Free-form HTML generation produced visual drift, broken responsiveness, and inconsistent styling.
- **Decision:** Replace free-form generation with typed `ExperienceBlueprint`. Compiler owns color token mappings, Tailwind layout classes, and semantic slot bindings. LLM provides design intent and section semantics, not raw markup.
- **Rejected alternatives:** Allowing model to emit arbitrary CSS/inline styles; template-only portfolio stamping.
- **Consequence:** Architectural consistency across generated portfolios while maintaining aesthetic distinctiveness.

## D-033 — Fenced Code Generator stage attempts and immutable workflow artifacts

- **Date & Time:** 2026-08-20 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Stale workers or retried jobs could overwrite later stage progress on long generation runs.
- **Decision:** Persist immutable stage receipts and unique attempt tokens for every generation step. CAS revision checks reject late or stale worker writes.
- **Rejected alternatives:** In-memory worker locking; unconditional stage state overwrites.
- **Consequence:** Zombie or delayed background workers fail closed without corrupting active generation runs.

## D-032 — Session-bound Code Generator with compiled visual execution

- **Date & Time:** 2026-08-19 12:34 +05:30 — Codex (model/provider omitted)
- **Status:** decided-implemented
- **Context:** Code Generator required binding to persistent portfolio session state rather than running only as a detached harness.
- **Decision:** Production Code Generator runs as durable session job (`code_generator.build`), consuming approved handoff briefs. Persist progressive state directly on session JSONB.
- **Rejected alternatives:** Decoupling code generation entirely from portfolio database sessions; running code generation inside HTTP request lifecycle.
- **Consequence:** Resumable, session-tracked portfolio generation with database-authoritative run status.

## D-031 — Shared local Pexels/Pixabay image retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Generated sites need real photographic assets without allowing unvetted web scraping or runtime hotlinking.
- **Decision:** Shared image retrieval service queries Pexels/Pixabay APIs, validates licensing and aspect ratios, and stores local references. Downstream generator materializes bytes into local assets.
- **Rejected alternatives:** Hotlinking external image URLs; model-hallucinated image URLs; AI image generation for realistic evidence.
- **Consequence:** License-compliant, local browser-addressable image assets in every generated portfolio.

## D-030 — Priority-based dynamic component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Rich interactive components required selection without bundling large monolithic component libraries.
- **Decision:** Query component registries by semantic tags based on approved design requirements. Selected components provide local recipes or fallback to accessible Tailwind primitives.
- **Rejected alternatives:** Installing all components upfront; bundling huge UI libraries into every portfolio.
- **Consequence:** Lean generated bundles containing only the components strictly required by the design.

## D-029 — Cache-free live component retrieval

- **Date & Time:** 2026-08-18 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Stale component cache caused version mismatches and broken imports during generation.
- **Decision:** Component discovery queries upstream registries per run; validate retrieved source against schema before admittance.
- **Rejected alternatives:** Storing persistent binary component cache across generation runs.
- **Consequence:** Clean component admittance without cache invalidation bugs.

## D-027 — Verified major tasks end in task-scoped local commits

- **Date & Time:** 2026-08-17 15:46 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Multi-agent collaboration across different AI tools and branches requires clean, verifiable git boundaries.
- **Decision:** Completed, verified units of work that qualify for `CHANGES.md` must end with a task-scoped local Git commit. Stage only task-owned files; never use `git add .` in dirty worktrees.
- **Rejected alternatives:** Leaving code uncommitted for user to commit; bulk staging entire repository.
- **Consequence:** Repository invariant: atomic, traceable, task-scoped commits across all AI tools.

## D-026 — Code Generator core is the sole standalone implementation namespace

- **Date & Time:** 2026-08-17 14:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Code Generator code was split between standalone development prototypes and production session code.
- **Decision:** Consolidate Code Generator logic under `src/oryxenai/agents/code_generator/core/`. Standalone harness and production service share identical core compilation, planning, and verification modules.
- **Rejected alternatives:** Maintaining duplicate generator logic for standalone harness vs production session.
- **Consequence:** Single implementation path; fixes in standalone harness automatically benefit production generation.

## D-024 — Export complete verified portfolios with receipt-bound metadata

- **Date & Time:** 2026-08-17 12:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Users require clean, self-contained portfolio exports ready for independent deployment.
- **Decision:** Export builds clean ZIP containing verified source tree, `dist/`, asset references, and export manifest with audit receipts.
- **Rejected alternatives:** Exporting raw unbuilt source; omitting verification receipts.
- **Consequence:** Standalone deployable portfolio artifacts with full provenance metadata.

## D-023 — Harden generated filesystem transitions on Windows

- **Date & Time:** 2026-08-17 11:10 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Windows file locks (antivirus, indexer, Vite) caused transient `PermissionError` during atomic directory replacement.
- **Decision:** Route directory swaps, tree deletion, and atomic writes through `fs_safe` layer with extended paths (`\\?\`), exponential backoff retry, and explicit error handling.
- **Rejected alternatives:** Ad-hoc try/except per file call; ignoring deletion failures; disabling directory replacement.
- **Consequence:** Atomic checkpoints and directory promotion reliably succeed on Windows platforms.

## D-022 — Skip acquisition for execution-contract-resolved resource slots

- **Date & Time:** 2026-08-17 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Re-fetching already resolved resources wasted bandwidth and introduced network failure points.
- **Decision:** Acquisition engine checks execution contract; skips network retrieval for pre-resolved slots, executing fetches only for gap slots.
- **Rejected alternatives:** Unconditionally refetching all assets on every step.
- **Consequence:** Minimal external API calls; fast, deterministic asset compilation.

## D-020 — Approved external links are content, not runtime navigation

- **Date & Time:** 2026-08-15 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** External portfolio links (GitHub, LinkedIn, live demos) were colliding with SPA router navigation.
- **Decision:** External URLs are treated strictly as content data, rendering standard HTML `<a>` anchors with `target="_blank"` and `rel="noopener noreferrer"`. Router handles only internal route IDs.
- **Rejected alternatives:** Routing external URLs through SPA router; converting external links to synthetic pages.
- **Consequence:** Clean separation between internal SPA routes and external portfolio references.

## D-019 — Normalize strict-schema generation payloads by mode tag

- **Date & Time:** 2026-08-15 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Models emitting JSON objects in structured output mode require discriminated envelope schemas.
- **Decision:** Tag generation payloads with an explicit `mode` enum (`foundation`, `route`, `review`, `repair`). Validate envelopes strictly against mode-specific schemas.
- **Rejected alternatives:** Unvalidated loose JSON dicts; single monolithic schema for all generation phases.
- **Consequence:** Type-safe model output parsing with early structural rejection of malformed outputs.

## D-017 — Approve a complete safe public scope, then direct that exact scope

- **Date & Time:** 2026-08-14 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Downstream agents inventing new routes or sections caused scope creep and inconsistent portfolios.
- **Decision:** Content Architect defines and user approves complete public scope (routes, sections, navigation). Visual Design Director and Code Generator must execute that exact scope without inventing new pages or omitting approved ones.
- **Rejected alternatives:** Allowing later agents to add surprise pages or drop approved sections.
- **Consequence:** Upstream scope approval is binding on all downstream generation stages.

## D-016 — Content Architect approval requires at least one publishable route

- **Date & Time:** 2026-08-13 00:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Approving an empty or draft-only content structure caused downstream build failures.
- **Decision:** Enforce validation rule: approved content snapshot must contain at least one valid, publishable route with content.
- **Rejected alternatives:** Allowing empty approved state; deferring route existence checks to Code Generator.
- **Consequence:** Downstream agents always receive non-empty, actionable route scope.

## D-015 — Code Generator uses progressive text-only generation with mediated resource acquisition

- **Date & Time:** 2026-08-13 14:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Monolithic generation of full site code in a single prompt hit context limits, hallucinated dependencies, and suffered syntax corruption.
- **Decision:** Deconstruct generation into progressive, text-only sequential stages: planning -> foundation & design system -> route waves -> cross-route review -> bounded repair. Resource acquisition (images, fonts, components) is mediated by deterministic code, never LLM tool loops.
- **Rejected alternatives:** Single-prompt full codebase generation; allowing LLM direct web access.
- **Consequence:** Supersedes D-014. Predictable token consumption, deterministic file boundaries, and granular error isolation.

## D-008 — Visual Design Director mirrors Content Architect architecture

- **Date & Time:** 2026-08-09 18:00 +05:30 — Codex (GPT-5 / OpenAI)
- **Status:** decided-implemented
- **Context:** Third pipeline stage needed an architecture consistent with Content Architect without conversational chat overhead.
- **Decision:** Mirror Content Architect's pattern: explicit start via POST endpoint, single durable job (`visual_design_director.build`), 1-3 sequential model calls (`establish_visual_language`, optional `direct_page_experience`, optional `integrate_site_experience`), deterministic tag-overlap lookup over checked-in resource catalogue, JSONB persistence on session state, hash-checked approval.
- **Rejected alternatives:** Interactive chat UI for Visual Design Director; auto-chaining from Content Architect approval; agentic tool-calling loop for catalogue search.
- **Consequence:** Supersedes D-006. Architectural uniformity across pipeline stages; predictable bounded execution.

## D-007 — Restructure AI-agent context files around canonical AGENTS.md

- **Date & Time:** 2026-08-08 20:00 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Multiple AI tools (Codex, Claude Code, Antigravity, Cursor) active in the repository require consistent, authoritative context without duplicate drift.
- **Decision:** Establish `AGENTS.md` as canonical root context file for all tools. `CLAUDE.md`, `.cursorrules`, and tool configurations reference `AGENTS.md`. Maintain config-driven policy: never hardcode model names, API keys, or live status in prose.
- **Rejected alternatives:** Maintaining separate, divergent context files for each AI assistant.
- **Consequence:** Unified cross-tool protocol; zero discrepancy between AI coding assistants.

## D-005 — Jinja2 + vanilla JS testing harness instead of framework frontend

- **Date & Time:** 2026-08-08 00:00 UTC — Claude Code (Claude Sonnet 5 / Anthropic)
- **Status:** decided-implemented
- **Context:** Needed lightweight UI to test Discovery and stage APIs before committing to a heavy frontend architecture.
- **Decision:** Built initial test UI with Jinja2 templates, vanilla JS, and CSS served directly by FastAPI.
- **Rejected alternatives:** Premature Next.js or React setup during core engine stabilization.
- **Consequence:** Rapid iteration on engine APIs without frontend build toolchain friction.

## D-004 — Kept dormant discovery_opencode_go profile in config/models.toml

- **Date & Time:** 2026-08-07 20:30 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go provider was rate-limited, but preserving the configuration for future fallback was desirable.
- **Decision:** Retain `discovery_opencode_go` profile in `config/models.toml` while routing active profiles through OpenAI/Anthropic.
- **Rejected alternatives:** Deleting the provider configuration entirely.
- **Consequence:** Fast provider re-enabling via TOML profile reassignment without code changes.

## D-003 — Switched Discovery/Content Architect to OpenAI API directly

- **Date & Time:** 2026-08-07 20:10 UTC — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** OpenCode Go rate limit quota exhausted during early development.
- **Decision:** Pointed active engine profiles directly to OpenAI API. Introduced `ModelCapabilities` layer to abstract provider differences (e.g. `uses_max_completion_tokens`).
- **Rejected alternatives:** Waiting for provider quota reset; hardcoding provider checks in agent code.
- **Consequence:** Provider neutrality established; generic capabilities abstraction handles wire differences.

## D-002 — v1 Discovery over-engineering, then v2 simplification

- **Date & Time:** 2026-08-07 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Initial Discovery had dedicated document tables, repair loops, 20-file few-shot libraries, and fact graph validation.
- **Decision:** Simplified to session JSONB storage, inline contrastive prompt examples, and envelope-only validation. Markdown brief content is free-text.
- **Rejected alternatives:** Preserving complex multi-table validation graph and schema validation on free-text briefs.
- **Consequence:** Standard established: envelope validation + prompt-carried examples over heavy framework machinery.

## D-001 — Explicit Python agents over an agent framework

- **Date & Time:** 2026-08-06 (retroactive) — Unspecified (Unspecified)
- **Status:** decided-implemented
- **Context:** Required agent architecture before tool-calling and routing requirements were fully established.
- **Decision:** Plain Python protocols (`Agent`, `ModelClient`) and Pydantic schemas without external frameworks.
- **Rejected alternatives:** LangChain, LangGraph, CrewAI, AutoGen.
- **Consequence:** High testability, zero framework lock-in, explicit model boundaries, full architectural control.

---

## Compacted & Superseded History

- **D-061** — 2026-09-03 11:35 +05:30 — Claude Code (Sonnet 5) — Build Preparation 100-year pack TTL (superseded by D-062 Markdown briefs)
- **D-060** — 2026-09-03 01:45 +05:30 — Claude Code (Sonnet 5) — Deferred materialization of pack bytes (superseded by D-062 Markdown briefs)
- **D-051** — 2026-08-25 11:54 +05:30 — Codex (GPT-5) — Source-bound Build Preparation JSONB checkpoints (superseded by D-062 Markdown briefs)
- **D-049** — 2026-08-25 16:30 +05:30 — Codex (GPT-5) — Temporary detached authentication in main pipeline (superseded by D-052)
- **D-035** — 2026-08-20 00:00 +05:30 — Codex (GPT-5) — Build Preparation v4 delegated acquisition (superseded by D-062 Markdown briefs)
- **D-028** — 2026-08-17 22:00 +05:30 — Codex (GPT-5) — Real provider material mandatory for visual handoff slots (superseded by D-062 Markdown briefs)
- **D-025** — 2026-08-17 14:00 +05:30 — Codex (GPT-5) — Required visual handoff uses executable local bindings (superseded by D-062 Markdown briefs)
- **D-021** — 2026-08-16 00:00 +05:30 — Codex (GPT-5) — Keep one canonical storage-key route owner (superseded by D-062 Markdown briefs)
- **D-018** — 2026-08-15 00:00 +05:30 — Codex (GPT-5) — Pack-v3 makes known resource decisions executable before Code Generator (superseded by D-062 Markdown briefs)
- **D-014** — 2026-08-13 10:36 +05:30 — Codex (GPT-5) — Code Generator v1 bounded generation, verification, repair, preview promotion (superseded by D-015)
- **D-013** — 2026-08-12 21:00 +05:30 — Codex (GPT-5) — Repair Build Preparation pack defects & issue pack v2 (superseded by D-062 Markdown briefs)
- **D-012** — 2026-08-12 20:45 +05:30 — Codex (GPT-5) — Freeze Build Preparation v1 and validate through Code Generator (superseded by D-013)
- **D-011** — 2026-08-11 00:00 +05:30 — Codex (GPT-5) — Rebuild Build Preparation as real agent from zero (superseded by D-062 Markdown briefs)
- **D-010** — 2026-08-10 17:51 +05:30 — Codex (GPT-5) — Portfolio Production Compiler pre-code boundary (superseded by D-011)
- **D-009** — 2026-08-10 00:00 +05:30 — Codex (GPT-5) — Deployment-independent temporary Build Preparation packs (superseded by D-062 Markdown briefs)
- **D-006** — 2026-08-08 15:30 UTC — Claude Code (Sonnet 5) — Visual Design Director & Code Generator deferred (superseded by D-008)

---

## Summary (as of last update — 2026-09-05)

- Total decisions logged: 66
- Active decisions: 50
- Compacted & superseded decisions: 16
- Last updated: 2026-09-05 — Claude Code (Sonnet 5 / Anthropic)
