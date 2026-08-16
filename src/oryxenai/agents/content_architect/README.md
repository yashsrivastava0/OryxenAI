# Content Architect Agent

Content Architect is the second OryxenAI workflow. It converts an **approved**
Discovery result into final, grounded, publish-ready portfolio content and a
justified site/route architecture, so the Visual Design Director and Code
Generation Engine never need to invent copy, achievements, links, or route
purposes.

## Responsibilities

- Decide professional positioning, narrative thesis, and single-page vs
  hybrid vs multi-page presentation — on merit, never for appearance.
- Produce final public copy for every justified route: nav labels, hero,
  about, project/work-sample stories, experience summaries, capability
  grouping, achievements/education treatment, contact/closing CTA.
- Carry claim-level grounding (source, evidence status, individual vs team
  ownership, publication status) for every important claim, and gate
  publication so unresolved material never reaches finished public copy.
- Produce a handoff for the Visual Design Director (content hierarchy,
  density guidance, storytelling opportunities, confidentiality
  restrictions, must-preserve facts) without picking exact visual decisions.
- Record the provenance of major site-strategy decisions (audience,
  presentation mode, CTA) so later stages know what's user-confirmed versus
  a safe default.
- Stop after producing content; never invoke another agent.

## Non-responsibilities

Content Architect must NOT:

- Re-interview the user or repeat Discovery.
- Change facts the user already approved in Discovery.
- Invent employers, dates, metrics, awards, testimonials, links, or outcomes.
- Pick exact visual components, layouts, typography, colors, or motion.
- Generate React, CSS, SVG, or any portfolio code.
- Perform external research or crawl links.

## Input: a compact approved snapshot only

Content Architect never receives the raw resume, `document_text`, or even
Discovery's full brief markdown. It reads only the compact, already-approved
Discovery output: `brief.title`, `user_summary`, the structured `profile`
(facts only), `open_items`, and the Discovery brief's approval hash +
session revision (used to detect a stale source — see below). The full
prose brief is deliberately excluded: `profile` + `user_summary` already
carry the grounded facts, and re-sending the entire brief on every call
(including every revision) would duplicate information, inflate latency and
token cost, and risk later stages reading stale Discovery prose instead of
this agent's own finalized output. Optional user `preferences` (goal,
audience, tone, density) may be supplied at start.

## The adaptive bounded workflow

Content Architect runs as **one durable job** (`content_architect.build`).
Its agent makes up to three sequential model calls internally, never one
call per page or section:

1. **`plan_content`** (always runs) — decides the site/story strategy and
   route plan, and either writes the FULL final content in this same call
   (`content_included=true`, most single-page/hybrid portfolios) or defers
   it (`content_included=false`, a real multi-page plan too large for one
   call).
2. **`write_pages`** (only if stage 1 deferred) — writes final content for
   every remaining route in one batched call.
3. **`integrate_content`** (only if warranted — a cross-route
   inconsistency was flagged, or the route plan has more than 2 routes) —
   a short reconciliation pass for terminology/nav consistency across
   routes; never adds a claim or a route.

All three operations share one output contract, `ContentArchitectOutput`,
discriminated by a `mode` field. This mirrors how Discovery's own
`QuestionSetOutput` already varies required fields by `mode` within one
schema.

## Flow

1. `POST /api/v1/sessions/{id}/content-architect/start` requires Discovery to
   be `approved`. It snapshots the approved brief + profile + the Discovery
   brief's approval hash, then enqueues `content_architect.build`.
2. The worker runs the build (1–3 model calls as above) and moves the state
   to `content_review`.
3. `POST .../content-architect/revise` re-runs the build with a
   natural-language `revision_request` and the current authoritative content
   as `prior_output` (allowed only while under review).
4. `POST .../content-architect/approve` hashes the final content and marks
   the run `approved` (terminal).

## Claim grounding and publication gating

Every claim carries three **independent** fields — never blended into one:

- `evidence_status` (`verified` | `unverified` | `unresolved`) — is the
  statement itself backed by the source?
- `ownership` (`individual` | `team` | `unclear`) — whose contribution is it?
- `publication_status` (`approved` | `pending` | `blocked`) — has it cleared
  review to appear in finished public copy? An approved Discovery snapshot
  authorizes neutral, factual wording for ordinary supplied profile facts;
  missing metrics, contact permission, individual ownership, scale, or a
  separate project permission are reasons to omit or generalize the detail,
  not to block the whole route. Explicit privacy, NDA, confidentiality, or
  do-not-publish restrictions remain blocking.

Routes carry the same `publication_status`. `blocked` material can never be
referenced from `page_content_packs`/`public_content_manifest` — this is
enforced structurally in `validators.py` (a hard reject, not just a prompt
instruction), because a real model was observed to leak an unresolved
project into public output as a confidently-titled route despite prompt
instructions saying not to. `pending` material is review-only: it can remain
in the Content Architect review output, but it is excluded from the approved
public scope handed to Visual Design Director and Build Preparation.

Approval is an admission gate, not only a top-level hash stamp. At least one
route must be `approved`; every approved route must have a safe unique path,
title and purpose, exactly one non-empty content pack whose section sequence
matches the route plan, and only approved claim references. The public
manifest and Visual Design Director handoff must also be present. A failure
returns an actionable 409 so the operator can request a revision before a
later-stage pack fails.

## Sections, not loose blocks

Each `page_content_packs` entry is `{route_id, sections, internal_notes}`.
Each `sections[]` entry is machine-addressable: `section_id`, `purpose`,
`content` (the actual visitor-facing copy — free-form per section type),
`claim_ids` (every claim the section's copy relies on — validated against
`claim_grounding`, and a section can never cite a `blocked` claim),
`priority`, `optional`, `mobile_condensation`, and `link_targets`. This
gives the Visual Design Director, revisions, and the Code Generation Engine
an unambiguous page structure instead of loosely related, unlabeled blocks.

`internal_notes` is the *only* place review/QA reasoning may live ("needs
confirmation before publishing", generalization rationale). It must never
leak into a section's `content` — `validators.py` scans section content for
a small set of internal-review key names (`status_note`, `evidence_status`,
`publication_check`, ...) as a structural backstop, since this too was
observed leaking through despite prompt instructions.

## Decision provenance

`decision_basis` records why each major site-strategy decision (presentation
mode, primary audience, primary CTA, tone, density) was made: `user_confirmed`
(a stated preference set it), `source_derived` (the snapshot's facts imply
it), or `safe_default` (nothing was supplied, so a reasonable default was
chosen). Downstream stages use this to know what they may preserve
automatically versus what remains open to revision.

## Staleness

Every `start`/`revise` call — and the job handler again, immediately before
persisting a successful build — compares the live Discovery brief's approval
hash against the hash snapshotted when this Content Architect run began. If
Discovery has since been re-approved with different content, the operation
is rejected with `CONTENT_ARCHITECT_STALE_SOURCE` rather than silently
building on outdated facts.

## State machine

Five statuses: `not_started, build_running, content_review, approved,
needs_attention`. Deliberately simpler than Discovery's own machine —
there's no separate queued/running pair or per-stage status, because one job
kind covers the whole adaptive workflow (see `state.py` for why this is an
intentional simplification, not an oversight).

## Output contract

Only the transport envelope is validated (`validators.py`), never the
content's prose: `mode` matches the operation and is consistent with
`content_included`; every `route_plan` entry has a unique, non-empty
`route_id`/`path`/`purpose`; every `claim_grounding` entry has a unique,
non-empty `claim_id`, and a `verified` claim must carry a `source_reference`;
`page_content_packs`/`public_content_manifest` are required non-empty
exactly when the operation is supposed to produce them; every
`page_content_packs` section has a pack-unique `section_id` and only cites
`claim_ids` that exist and are not `blocked`; no `blocked` route/claim is
referenced from public output; `visual_director_handoff` is required
non-empty only for `integrate_content`. The configured route ceiling is an
admission boundary: an over-ceiling route plan or content-pack set is
rejected rather than silently truncated, because truncation would make the
approved public scope incomplete.

A model output that fails the contract raises
`ContentArchitectModelOutputError` (surfaced as `MODEL_OUTPUT_INVALID`,
retryable). Truly unexpected exceptions surface as `MODEL_OPERATION_FAILED`
(not retryable). Either way the failure only reaches `needs_attention` once
retries are exhausted, same as Discovery.

## Prompts

Four prompt files. The system prompt is loaded first, then the operation
prompt with the shared output JSON schema injected and the raw source packet
appended as untrusted CDATA:

- `prompts/system.md`
- `prompts/plan_content.md`
- `prompts/write_pages.md`
- `prompts/integrate_content.md`

## Model integration

There is no demo mode for the durable worker path. It always builds the live
provider adapter for the `[profiles.content_architect]` profile in
`config/models.toml`; missing configuration raises a controlled
`ProviderConfigError`. The mock-runs dev harness uses the deterministic
`MockModelClient` fallback so it never makes network calls.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/content-architect` | Current state (status, error, attempt, elapsed) |
| POST | `/api/v1/sessions/{id}/content-architect/start` | Snapshot approved Discovery, enqueue build (202) |
| POST | `/api/v1/sessions/{id}/content-architect/revise` | Natural-language content revision (202) |
| POST | `/api/v1/sessions/{id}/content-architect/approve` | Approve the reviewed content |
