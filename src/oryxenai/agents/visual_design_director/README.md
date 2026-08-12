# Visual Design Director Agent

Visual Design Director is the third OryxenAI workflow stage. It converts an
**approved** Content Architect output into a complete visual-experience
direction — global visual language, per-route storyboards, scene-level
visual/interaction direction, asset intent, local resource references, and
a motion/interaction system — so a future deterministic Blueprint Compiler
and Code Generation Engine never have to invent the visual strategy while
building, but retain full implementation freedom over the actual
React/CSS/SVG.

## Responsibilities

- Establish a site-wide creative thesis and visual language (color
  behavior, typography, grid, shape, background, motion/interaction
  character, accessibility/performance philosophy) specific to the
  profile — never a shallow style label.
- Produce a storyboard for every Content Architect route: purpose, visitor
  takeaway, above-the-fold strategy, scene progression, responsive summary.
- Break each route into scenes — deliberate visual/interaction moments,
  distinct from Content Architect's sections — with layout, background,
  asset, motion, interaction, responsive, and accessibility intent.
- Emit asset briefs (purpose, crop/treatment/fallback intent) for every
  meaningful image requirement — never a concrete file.
- Reference a small local resource catalogue for adaptable design-pattern
  candidates (never mandatory bindings).
- Reconcile cross-page coherence when the site has enough routes to warrant
  it (navigation, typography/spacing, background systems, motion balance).
- Stop after producing direction; never invoke another agent.

## Non-responsibilities

Visual Design Director must NOT:

- Generate React, CSS, SVG, DOM structure, Tailwind classes, or any code.
- Specify exact pixel coordinates, hex values, component names, or
  animation-library calls — direction is relationships and constraints in
  words, not implementation.
- Invent, rename, add, or drop a Content Architect route.
- Acquire, download, or install any asset, package, or component.
- Acquire assets or call external APIs. Visual Design Director records
  image intent only; the hidden Build Preparation stage performs optional
  Pexels acquisition and materializes the result.
- Run the future Experience Blueprint Compiler, Resource & Asset Packager,
  or Code Generation Engine.

## Input: a compact approved Content Architect snapshot only

Visual Design Director never receives Discovery's raw resume/document text
or Content Architect's internal reasoning. It reads only Content
Architect's own approved output: `presentation_mode`, `site_story_strategy`,
`route_plan`, `page_content_packs` (final content, so density/length can be
gauged), `public_content_manifest`, `media_status`,
`visual_director_handoff` (Content Architect's real handoff field — content
hierarchy, density guidance, storytelling/diagram opportunities, available/
unavailable media, confidentiality restrictions, must-preserve facts, and
never-fabricate rules), and `privacy_and_confidentiality`, plus the
approved content hash + session revision (used to detect a stale source —
see below). Optional user `preferences` (visual_tone, motion_preference,
density_preference, accessibility_notes) may be supplied at start.

## The adaptive bounded workflow

Visual Design Director runs as **one durable job**
(`visual_design_director.build`). Its agent makes up to three sequential
model calls internally, never one call per page or scene:

1. **`establish_visual_language`** (always runs) — establishes the global
   visual language and shared systems (navigation, motion, interaction),
   and either writes the FULL per-route direction in this same call
   (`pages_included=true`, most single-page/hybrid portfolios) or defers it
   (`pages_included=false`, a real multi-page plan too large for one call).
2. **`direct_page_experience`** (only if stage 1 deferred pages) — writes
   final direction for every remaining route in one batched call.
3. **`integrate_site_experience`** (only if warranted — more than 2 routes,
   or a cross-page conflict was flagged) — a reconciliation pass for
   navigation/typography/background/motion coherence across routes; never
   adds or removes a route.

All three operations share one output contract, `VisualDesignDirectorOutput`,
discriminated by a `mode` field — the same pattern Content Architect's own
`ContentArchitectOutput` already uses across its three stages.

## Local resource catalogue

A small (~15-entry), checked-in, deterministic catalogue of design-pattern
references (`resources/catalogue.json`) — hero/timeline/diagram/gallery/
background/navigation/motion patterns. `resource_catalogue.py::find_candidates`
runs in plain Python **before** any model call, ranking entries by tag
overlap with structural facts already in the intake (presentation mode,
media availability, content density). The resulting shortlist is injected
into the prompt as data; the model may only ever reference a `resource_id`
that was actually in that shortlist — enforced structurally in
`validators.py`, never left to prompt discipline alone, per this codebase's
existing precedent for closed-set selections. This is intentionally NOT a
model tool-calling loop — the provider adapter here is single-shot
JSON-object-mode structured generation, not a function-calling agent.

## Flow

1. `POST /api/v1/sessions/{id}/visual-design-director/start` requires
   Content Architect to be `approved`. It snapshots the approved output +
   the approved Content Architect projection hashes, then enqueues
   `visual_design_director.build`.
2. The worker runs the build (1-3 model calls as above) and moves the state
   to `design_review`.
3. `POST .../visual-design-director/revise` re-runs the build with a
   natural-language `revision_request` and the current authoritative
   direction as `prior_output` (allowed only while under review).
4. `POST .../visual-design-director/approve` hashes the final direction and
   marks the run `approved` (terminal).

## Staleness

Every `start`/`revise` call — and the job handler again, immediately before
persisting a successful build — compares the live Content Architect
approval's content hash, route-publication hash, and full VDD-input
projection hash against the snapshots taken when this Visual Design Director
run began. If story strategy, media availability, privacy/handoff guidance,
route intent, or public content has changed, the operation is rejected with
`VISUAL_DESIGN_DIRECTOR_STALE_SOURCE` rather than silently building on
outdated content.

## State machine

Five statuses: `not_started, build_running, design_review, approved,
needs_attention`. Same shape as Content Architect's own machine — one job
kind covers the whole adaptive workflow, so there is no separate
queued/running pair or per-stage status.

## Output contract

The direction's prose remains intentionally flexible, but final
compiler-facing references are validated (`validators.py`) after all model
calls are reconciled. `mode` matches the operation and is consistent with
`pages_included`; every page's `route_id` echoes a real, non-blocked
Content Architect route (never invented); `direct_page_experience`/
`integrate_site_experience` must cover every non-blocked route exactly
once; every `scene_id`/`asset_id`/`resource_id` is unique; every scene has
`responsive_behavior`; any scene with non-trivial `motion_intent` has
`reduced_motion_behavior`; any non-optional asset brief has both
`source_status` and `fallback_strategy`; every referenced `resource_id`
was actually in the catalogue shortlist given to that call;
`compiler_handoff` is required non-empty only for `integrate_site_experience`.
The final pass also rejects dangling scene `content_refs`, asset references,
asset-brief `content_ref` values, and page/scene resource references before
the output can reach review.
`asset_briefs`/`resource_candidates` are never required non-empty — a
text/diagram-only site with zero real assets and zero catalogue references
is a valid, celebrated outcome, not incompleteness. Subjective quality
concerns (excessive motion, long copy, high density, repeated composition,
weak optional assets) are prompt-carried self-reporting into the model's
own `warnings`/`conflicts` output, not code-computed heuristics — this
codebase's established bias is to prefer envelope-only validation over new
structural machinery unless a real, specific failure mode demonstrates it's
insufficient (see `DECISIONS.md`).

A model output that fails the contract raises
`VisualDesignDirectorModelOutputError` (surfaced as `MODEL_OUTPUT_INVALID`,
retryable). Truly unexpected exceptions surface as `MODEL_OPERATION_FAILED`
(not retryable). Either way the failure only reaches `needs_attention` once
retries are exhausted, same as Content Architect.

## Prompts

Four prompt files. The system prompt is loaded first, then the operation
prompt with the shared output JSON schema injected and the raw source
packet (including the resource-catalogue shortlist) appended as untrusted
CDATA:

- `prompts/system.md`
- `prompts/establish_visual_language.md`
- `prompts/direct_page_experience.md`
- `prompts/integrate_site_experience.md`

## Model integration

There is no demo mode for the durable worker path. It always builds the
live provider adapter for the `[profiles.visual_design_director]` profile
in `config/models.toml`; missing configuration raises a controlled
`ProviderConfigError`. The mock-runs dev harness uses the deterministic
`MockModelClient` fallback so it never makes network calls.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/visual-design-director` | Current state (status, error, attempt, elapsed) |
| POST | `/api/v1/sessions/{id}/visual-design-director/start` | Snapshot approved Content Architect output, enqueue build (202) |
| POST | `/api/v1/sessions/{id}/visual-design-director/revise` | Natural-language visual-direction revision (202) |
| POST | `/api/v1/sessions/{id}/visual-design-director/approve` | Approve the reviewed direction |
