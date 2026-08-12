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

## Summary (as of last compaction — 2026-08-11)

- Total decisions logged: 11
- Active decisions: 9 (D-001 through D-005, D-007 through D-009, D-011)
- Superseded decisions: 2 (D-006 compacted under history; D-010 superseded by D-011, not yet compacted — file is well under the 350-line trigger)
- By tool: Codex (2), Claude Code (4), Unspecified/Retroactive (5)
- Last updated: 2026-08-11 — Claude Code (Claude Sonnet 5 / Anthropic)
