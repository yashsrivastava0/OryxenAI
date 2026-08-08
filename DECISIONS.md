# OryxenAI — Decisions & Open Issues

Architecture Decision Record (ADR)-style log: real decisions with actual
trade-offs, open questions, deferred work, and things to revisit later. Not
implementation minutiae — those belong in commit messages or `CHANGES.md`.

**Logging policy — same discipline as `CHANGES.md`:** only log a real
decision with actual trade-offs here. Ask the user first if it's unclear
whether something rises to that level, rather than logging routine
implementation choices.

Ordering: reverse-chronological by decision date, newest at top. Entry IDs
(`D-001`, `D-002`, ...) are assigned once, in order of creation, and never
reused — so an ID's number does not necessarily match its visual position
after new entries are added above it; the ID is a stable reference, the
position is for readability.

**Never delete or rewrite an entry.** When a decision is superseded, add a
*new* entry describing the new decision, and edit only the *old* entry's
`Status` line to `superseded-by-D-0XX` — its Context/Decision/Rejected
alternatives text stays exactly as originally written, so this remains an
honest history, not a rewritten one. This file is NOT touched by
`CHANGES.md`'s size-based compaction — entries here are pruned only when
individually and unambiguously obsolete, by explicit human or agent
judgment, not automatically.

Every AI agent should check this file before making an architectural choice
that might already have been decided or rejected here.

**Entry template** (copy verbatim for every new entry, insert directly below
this header, above the current newest entry):

```markdown
## D-0XX — <short decision title>
- **Date:** YYYY-MM-DD
- **Status:** open | decided-not-yet-implemented | decided-implemented | superseded-by-D-0XX
- **Context:** What forced this choice — the situation, constraint, or
  problem that made a decision necessary.
- **Decision:** What was chosen, stated concretely.
- **Rejected alternatives:** What else was considered, and specifically why
  each was rejected (not just "considered and dismissed").
- **Consequence:** What this implies going forward — what becomes easier,
  harder, or ruled out; what would need to change to revisit this.
```

---

## D-008 — Visual Design Director's first real implementation mirrors Content Architect's architecture almost exactly

- **Date:** 2026-08-08
- **Status:** decided-implemented
- **Context:** D-006 left "how/when Visual Design Director gets its first
  real implementation" explicitly open. Content Architect (the second
  pipeline stage) was already a proven, fully-implemented pattern for
  exactly this shape of problem: convert an approved upstream snapshot into
  a structured output via a bounded, adaptive multi-call model workflow,
  behind a durable job and an explicit-start API.
- **Decision:** Built Visual Design Director as a close mirror of Content
  Architect: the same 5-status state machine shape (`not_started ->
  build_running -> design_review -> approved`, plus recoverable
  `needs_attention`), the same 3-operation bounded workflow pattern
  (`establish_visual_language` always runs; `direct_page_experience` only
  if stage 1 deferred per-route detail; `integrate_site_experience` only
  if warranted — same `>2 routes` threshold as Content Architect's own
  integration gate, plus an explicit `len(route_plan) > 1` guard so a
  single route never triggers integration even if a stage mis-flags it),
  the same envelope-only `validators.py` philosophy (structural/ID
  hard-rejects only — duplicate stable IDs, a blocked Content Architect
  route leaking into output, a scene missing responsive/reduced-motion
  intent, an asset missing a fallback — never synthesized "subjective
  quality" warnings; those became prompt-carried self-reporting instead,
  per D-002's bias), the same staleness mechanism (snapshot the upstream
  approval hash at start, re-check it on revise and again immediately
  before persisting a successful build), and JSONB-on-session-state
  persistence with no new DB table or migration (following the migration
  0003->0005 precedent against dedicated per-agent tables). One deliberate
  new piece: a small (~15-entry) checked-in local resource catalogue
  (`resource_catalogue.py` + `resources/catalogue.json`) queried via plain
  Python tag-overlap ranking *before* any model call — never a model
  tool-calling loop, since no such mechanism exists in this codebase's
  `ModelClient` protocol (single-shot JSON-object-mode structured
  generation only) and D-001 rules out adding one. A model may only ever
  reference a `resource_id` that was actually in the shortlist it was
  given for that call; unknown references are a validators.py hard reject,
  the same closed-set-selection discipline Content Architect already uses
  for blocked routes/claims.
- **Rejected alternatives:** Adding a `decision_basis`-equivalent (Content
  Architect has one for presentation-mode/audience/CTA provenance) —
  rejected because Visual Design Director's choices are already captured
  as prose inside `visual_language`/`meta`, and no demonstrated gap called
  for structured provenance on top. Adding an internal-note-leak backstop
  analogous to Content Architect's (which guards against internal QA prose
  leaking into visitor-facing section content) — rejected because Visual
  Design Director has no equivalent visitor-facing prose field;
  `compiler_handoff` is internal by design already. Adding deterministic
  code-computed "quality" heuristics to `validators.py` (e.g. counting
  scenes with motion, flagging long copy) instead of prompt-carried
  self-reporting — considered and explicitly rejected per D-002's bias
  toward envelope-only validation absent a demonstrated failure mode; this
  was confirmed with the user as the preferred approach before
  implementation.
- **Consequence:** Any future real implementation work on Code Generator
  (still open) should default to checking whether this same
  mirror-Content-Architect pattern applies before inventing something new.
  If a real, specific failure mode later demonstrates envelope-only
  validation is insufficient for Visual Design Director specifically
  (e.g. a model reliably produces excessive motion despite the
  self-report prompt instruction), revisit the rejected
  deterministic-heuristics alternative above rather than assuming it was
  permanently ruled out.

---

## D-007 — Restructure AI-agent context files around a canonical AGENTS.md

- **Date:** 2026-08-08
- **Status:** decided-implemented
- **Context:** Multiple AI coding tools (Claude Code, OpenAI Codex CLI,
  Google Antigravity, Cursor) and multiple models/providers (OpenAI/GPT,
  xAI/Grok, Zhipu/GLM, Anthropic/Claude) now work on this repo across
  devices. The project's real substantive context lived in `CODEX.md`, but
  no real tool auto-discovers a file by that name — `AGENTS.md` is the
  actual open standard Codex CLI/Cursor/Copilot/Gemini CLI read
  automatically. `CODEX.md` had also drifted into self-contradiction (it
  called Content Architect both "implemented end to end" and still "a
  mock" in two different sections), and there was no shared record of who
  changed what/where/when/why, nor a durable place for open decisions.
- **Decision:** Made `AGENTS.md` the canonical, substantive file (absorbing
  and reconciling `CODEX.md`'s content — verified against the repo that
  Content Architect has `agent.py`/`service.py`/`state.py`/`validators.py`
  while Visual Design Director and Code Generator have only
  `agent.py`/`schemas.py`/samples, i.e. Content Architect is genuinely
  implemented and the other two are genuinely still mocks). Reduced
  `CODEX.md` to a short redirect. Added `CLAUDE.md` as an `@AGENTS.md`
  import plus Claude-Code-only notes. Added `CHANGES.md` (a compacting
  changelog) and this file, `DECISIONS.md`, as two separate logs with
  different lifecycles.
- **Rejected alternatives:** (a) Keeping `CODEX.md` as canonical and making
  `AGENTS.md` the redirect — rejected because real tools auto-read
  `AGENTS.md` by filename, so the actual substantive content needs to live
  there for auto-discovery to work at all. (b) Putting decisions/open-issues
  content as a section inside `CHANGES.md` — rejected because it needs a
  different lifecycle (survives changelog compaction untouched, tracks
  open/superseded status over time) than a timestamped append-only log.
- **Consequence:** Any future AI session should read `AGENTS.md` first, not
  `CODEX.md`. Project facts should be edited in exactly one place
  (`AGENTS.md`) going forward. Every agent working on this repo is expected
  to check this file before an architectural choice and to log commit-sized
  work to `CHANGES.md` — see `AGENTS.md`'s "Multi-agent collaboration
  protocol" section.

## D-006 — Visual Design Director and Code Generator deferred; no auto-chaining from Content Architect

- **Date:** 2026-08-08
- **Status:** superseded-by-D-008 (Visual Design Director side only — Code Generator remains open)
- **Context:** Content Architect is now implemented end to end as stage 2 of
  the pipeline, but the pipeline has two more designed stages (Visual Design
  Director, Code Generator) that turn approved content into an actual
  deployable site.
- **Decision:** Both remain deterministic mocks for now. Content Architect
  approval never auto-invokes anything downstream — every stage requires an
  explicit caller.
- **Rejected alternatives:** Auto-chaining Content Architect → Visual Design
  Director on approval — rejected because no agent supervisor/sequencing
  layer exists yet, and building one prematurely (before the two downstream
  agents have real implementations) was judged over-engineering, the same
  reasoning that led to D-002's Discovery simplification.
- **Consequence:** This is genuinely open — how/when Visual Design Director
  gets its first real implementation is undecided. Check here before
  starting that work to avoid duplicating a design already in progress
  elsewhere.

## D-005 — Server-rendered Jinja2 + vanilla JS testing harness instead of a framework frontend, for now

- **Date:** 2026-08-08 (recorded retroactively; decision predates this file)
- **Status:** decided-implemented
- **Context:** The project needs a frontend to exercise the Discovery/
  Content Architect chat flow during development, but the eventual product
  frontend is a separate, larger, undecided effort.
- **Decision:** Built a minimal Jinja2 + vanilla-JS server-rendered testing
  harness (`src/oryxenai/web/`) — no React/Vite/Tailwind/CDN dependency —
  scoped explicitly as a developer test harness, not the product UI.
- **Rejected alternatives:** Building a real framework-based frontend
  (React/Next.js) up front — rejected as premature before the underlying
  agent behavior and conversational contract were validated; see
  `docs/architecture.md` §5 for the fuller rationale.
- **Consequence:** This harness is intentionally throwaway-adjacent. The
  full conversational/UX contract it implements (question-option rules,
  approval flow, provider selection, streaming-readiness) is captured
  separately in `docs/frontend-behavior-spec.md` specifically so a future
  real-frontend rebuild doesn't have to re-derive it from this code.

## D-004 — Kept the dormant `discovery_opencode_go` profile in `config/models.toml` for rollback rather than deleting it

- **Date:** 2026-08-07
- **Status:** decided-implemented
- **Context:** Once the live model provider changed (see D-003), the
  previously-live `discovery_opencode_go` config profile became unused.
- **Decision:** Kept it as a named, inert profile in `config/models.toml`
  rather than deleting it, so rolling back to OpenCode Go is a one-line
  config change (repointing which profile name a handler uses), not a
  re-implementation.
- **Rejected alternatives:** Deleting the unused profile for cleanliness —
  rejected because the rollback path has real, plausible value (a second
  provider-quota incident, a cost comparison) and costs nothing to keep
  dormant in a committed config file.
- **Consequence:** `config/models.toml` will have more than one profile per
  agent from time to time as providers are compared/rotated — this is
  expected, not drift, as long as only one profile per agent is actually
  referenced by live code at any given time.

## D-003 — OpenCode Go quota exhaustion → switched Discovery/Content Architect to the real OpenAI API directly

- **Date:** 2026-08-07
- **Status:** decided-implemented
- **Context:** Discovery's live model calls were routed through OpenCode Go
  (`provider = "opencode_go"`). That gateway's monthly usage quota was
  exhausted (`GoUsageLimitError`, "Monthly usage limit reached") on
  2026-08-07 around 20:09 UTC, blocking all further live verification.
- **Decision:** Switched the live `[profiles.discovery]` (and later
  `[profiles.content_architect]`) config to `provider = "openai"` hitting
  `https://api.openai.com/v1` directly with `OPENAI_API_KEY` — same model
  name, different account/quota pool entirely, decoupling Discovery's
  availability from OpenCode Go's shared quota. This also surfaced a real
  capability difference: this model on the real OpenAI endpoint rejects a
  non-default `temperature` and requires `max_completion_tokens` instead of
  `max_tokens` (OpenCode Go's gateway had silently normalized both away).
  Fixed generically via the existing `ModelCapabilities` system
  (per-profile flags like `uses_max_completion_tokens`), not by
  special-casing the string `"openai"` anywhere in agent code.
- **Rejected alternatives:** Waiting for OpenCode Go's monthly quota reset —
  rejected because it blocked active development with no clear ETA, and a
  real, working alternate credential (`OPENAI_API_KEY`) was already
  available. Special-casing provider-specific parameter handling instead of
  extending `ModelCapabilities` — rejected because the same class of quirk
  will recur for other providers (Anthropic, Gemini) as they're added, and
  the capabilities system already existed for exactly this purpose.
- **Consequence:** The dormant OpenCode Go profile is preserved for rollback
  (see D-004). Any new provider added later should declare its own
  `ModelCapabilities` rather than assume OpenAI-shaped request/response
  behavior — check capabilities empirically before trusting docs/memory
  about a specific model's quirks.

## D-002 — v1 Discovery over-engineering, then v2 simplification

- **Date:** 2026-08-07 (recorded retroactively; decision predates this file)
- **Status:** decided-implemented
- **Context:** An earlier, more elaborate Discovery implementation
  (git commit `d6b5b90`, "checkpoint v2 discovery before simplification")
  had a separate immutable source-documents table, a repair-prompt loop, a
  20-file few-shot example library, and a fact/conflict-graph validation
  layer.
- **Decision:** Deliberately removed all four as over-engineering, landing
  on the current, simpler design: raw intake stored directly as JSONB on
  session state (no separate table), no repair loop, inline BAD/GOOD
  contrastive examples inside the prompts instead of a separate few-shot
  library, and envelope-only output validation (business content, like the
  brief's Markdown, is intentionally not schema-validated). Completed and
  live-smoke-verified in commit `ff291ef`.
- **Rejected alternatives:** Keeping the more elaborate v2 machinery on the
  theory that more validation/structure is always safer — rejected after
  direct verification found the extra machinery added complexity without a
  corresponding correctness benefit; the simplified version passed the same
  live-verification bar.
- **Consequence:** Future Discovery/Content Architect work should default
  to this same bias — prefer envelope-only validation and prompt-carried
  examples over building new structural machinery, unless a real, specific
  failure mode demonstrates the simpler approach is insufficient.

## D-001 — Explicit Python agents over an agent framework

- **Date:** 2026-08-06 (recorded retroactively; decision predates this file)
- **Status:** decided-implemented
- **Context:** The project needed a way to structure model-calling agent
  code (Discovery, Content Architect, and future stages) early, before the
  actual required behavior (tool calling, routing, memory) was known.
- **Decision:** Used ordinary Python protocols (`Agent`, `ModelClient`) and
  small Pydantic models instead of an agent framework.
- **Rejected alternatives:** LangChain, LangGraph, CrewAI, AutoGen — all
  rejected as premature: these frameworks impose abstractions (tool-calling
  conventions, message schemas, memory stores, supervisor patterns) that
  were speculative before the actual agent behavior was known, and make
  agents harder to test/inspect/reason about in isolation. See
  `docs/architecture.md` §1 for the fuller rationale.
- **Consequence:** A framework can still be introduced later, but only when
  a concrete need is demonstrated (real tool calling, complex routing) —
  not by default. Each agent keeps owning its directory with its own
  schemas, prompts, and samples, making its contract explicit and
  reviewable without framework-level indirection.
