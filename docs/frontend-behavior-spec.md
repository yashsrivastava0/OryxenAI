# Frontend Behavior Spec — Discovery / Content Architect Chat Flow

> This document captures the conversational/UX contract implemented in the
> current test frontend (`src/oryxenai/web/`), so a future production
> frontend rebuild does not have to re-derive this reasoning from `app.js`.
> It describes what actually ships, not aspirational behavior.

## 1. Purpose and audience

`src/oryxenai/web/` is a developer test harness, not the intended production
UI — but it is currently the only way anyone exercises the Discovery →
Content Architect flow end to end. Several non-obvious UX decisions live only
in `app.js` today (option-count limits, approval detection, what fraction of
an agent's output is worth showing a user). This document is the durable
record of those decisions, independent of the specific DOM/JS implementation,
so a real frontend can reproduce the same behavior instead of losing it.

## 2. Session and agent lifecycle

Both Discovery and Content Architect are simple, mostly-linear state
machines persisted server-side (`DiscoveryStatus`, `ContentArchitectStatus`).
The frontend polls `GET .../discovery` / `GET .../content-architect` and
renders based on `status` alone — there is no separate event stream.

The right-side Agent workspace adds two lightweight views on top of that
state: **Full outputs** and **Live activity**. Full outputs are selected from
the persisted Discovery, Content Architect, Visual Design Director, and Build
Preparation projections. Live activity is a client-derived timeline: it
records user/API actions and adds an entry only when a polled stage or durable
job changes. It is intentionally not a token-level model trace or a separate
backend event stream.

Discovery: `not_started → questions_queued → questions_running →
questions_ready → answers_in_progress → brief_running → brief_review →
approved`, with `needs_attention` reachable from any non-terminal state on
failure.

Content Architect: `not_started → build_running → content_review →
approved`, with the same `needs_attention` escape hatch, and
`content_review → build_running` as the "revise" edge.

**`approved` is terminal in both state machines — there is no revise-after-
approve.** Once a stage is approved, that agent's flow is permanently done;
the only forward motion from there is starting the next agent. This is why
the "next agent" button/prompt never needs to disappear and reappear across a
revision cycle — a revision can only happen *before* approval.

## 3. Question interaction contract

Discovery's questions are 100% LLM-generated per request (see
`agents/discovery/prompts/understand_and_question.md`) — there is no
hardcoded question bank in code. The frontend enforces a bounded, friendly
interaction shape on top of whatever the model returns, rather than trusting
model compliance:

- For `single_select`/`multi_select` questions, the frontend renders **at
  most 3** concrete option buttons (the prompt is instructed to return at
  most 3, but the frontend caps the array defensively regardless).
- A 4th, always-present **free-text "something else" box** lets the user
  answer with anything not covered by the 3 presets. Submitting it (or
  clicking a preset button) answers the question immediately — whichever the
  user does first wins; there is no "change your answer after clicking"
  affordance.
- For `multi_select`, the free-text value (if non-empty) is appended to the
  checked option values when "Submit answer" is clicked, rather than
  replacing them.
- **Skip** is a separate action, always available when the question's
  `allow_skip` flag is true (the default). Skipping submits `value: null`,
  `mode: "skipped"` — this is distinct from an empty free-text submission,
  and is rendered in the chat as "Skipped", not the literal answer value.
- If a select-kind question arrives with a missing or empty `options` array
  (a model/validation gap), the frontend never throws — it falls back to
  showing only the free-text box and Skip, with a short inline note.

This gives every question exactly three answer paths: pick one of up to 3
suggested options, type something else, or skip and let Discovery infer a
reasonable default from context.

Two prompt-level additions reduce how often the model needs any of this
fallback behavior in the first place: a persona-awareness instruction (phrase
questions differently for a technical vs. non-technical/business profile),
and a one-question contact-info gap check (friendly-ask for a public contact
channel — email/phone/LinkedIn/GitHub — only when the source material
supplies none at all, always skippable, never invented).

## 4. Approval and next-agent confirmation contract

Approving a stage **never auto-starts the next agent** — approval only
finalizes the current stage's output. A distinct confirmation step follows:
"Discovery approved — the portfolio brief is ready for the next stage. Would
you like to move to the next agent?" with a button, and the composer is also
listening for a natural-language "yes" while that prompt is active.

Natural-language intent detection reuses one heuristic (`looksLikeApproval`,
a short regex-based classifier — not an LLM call) for two different
purposes: detecting "this brief looks good, approve it" while a brief is
under review, and detecting "yes, let's move on" while a next-agent prompt is
showing. These two uses never overlap in practice, since a next-agent prompt
only appears after a stage has already reached its terminal `approved`
status.

Content Architect approval offers the explicit Visual Design Director start
action. Visual Design Director approval offers the explicit Build Preparation
start action. Approval still never auto-starts the next stage; each transition
is a separate user action.

## 5. What's shown vs. hidden per agent

Every implemented stage's full output is available to the user (nothing is
withheld), but the chat surfaces a **curated subset by default**. The Agent
workspace is the single place to inspect and copy the complete output for a
stage. It includes a readable preview and a readonly copy-ready text area,
plus a one-click clipboard action with a select-all fallback.

Discovery: the chat shows `brief.user_summary` (a ~150–350 word, plain-
paragraph summary the model writes specifically for this purpose) in
preference to the full `brief.markdown`; a "View full output" button opens the
workspace with the complete markdown, operation envelope, and structured
profile. The copy-ready value combines those parts without including the raw
resume/document intake.

Content Architect: mirrors the same pattern. `user_summary` (a ~120–250 word
summary produced by the `plan_content` stage) is the primary display,
falling back to `site_story_strategy.positioning` only if empty (an older
persisted state without the field). The route list is always shown. Any
non-empty `unresolved_issues` and `warnings` are surfaced as short bullet
lists, and a one-line count is shown for `privacy_and_confidentiality` notes
— these were previously only visible in the raw-JSON panel, which is why
Content Architect's chat output initially read as "too little."

Visual Design Director and Build Preparation use the same workspace. Their
persisted stage state is exposed as a full JSON copy-ready output, while the
preview shows the human-facing summary when one exists. The UI reads these
values from the stage API responses; it does not read checked-in fixture
files such as `src/oryxenai/output/visual_design_director_Output.md`. Future
full-content agents should persist their complete output in their stage state
so this generic workspace can expose it without another frontend rewrite.

Deliberately never surfaced in the curated view for either agent: internal
review annotations (`PageContentPack.internal_notes` in Content Architect),
worker/job metadata, and prompt-version/model-metadata fields — these exist
for debugging and are only reachable via the raw-JSON panel.

## 6. Provider-selection contract

A model/provider dropdown exists on the home page (`#provider-select`,
separate from the unrelated dev-harness `#agent-select` used for mock agent
runs under "Advanced"). Today it has one enabled option ("OpenAI — GPT-5.6
Luna", value `""`, meaning "use the default configured profile") and two
disabled placeholder entries ("Anthropic Claude", "Google Gemini") for
providers that don't have a working adapter yet.

The selection flows end-to-end, not just cosmetically:

1. The frontend sends `model_profile` in the Discovery/Content Architect
   `start` request bodies.
2. `DiscoveryService.start()` validates it against an enabled-profile
   allow-list (currently just `{""}` — matching what the dropdown can
   actually send) and stores it on `DiscoveryState.model_profile`, then
   copies it into every subsequent run's `input_payload` (answers, revise)
   so the choice is **sticky for the whole session** without the frontend
   resending it. The dropdown is disabled once a session starts, since
   changing it mid-session has no effect on the profile already committed.
2. `ContentArchitectService.start()` inherits the choice from the approved
   Discovery snapshot by default if none is explicitly passed — one
   coherent per-session choice rather than asking twice.
3. Job handlers read `model_profile` from `input_payload` and pass it as
   `override_profile_name` to `build_provider_client(default_profile_name,
   model_config, override_profile_name=...)`. If the override profile
   doesn't exist, isn't a supported provider, or has no resolvable API key,
   this logs a warning and **silently falls back** to the agent's default
   profile — an unknown or disabled selection must never break the agent.
4. The resolved profile name is threaded into `DiscoveryAgent`/
   `ContentArchitectAgent` and passed through as the (previously declared
   but unused) `model_profile` parameter on `ModelClient.generate_structured`
   for traceability/logging — it does not dynamically switch providers
   mid-call, since each adapter instance is bound to one profile at
   construction. A genuine per-call dynamic provider switch would need every
   adapter to support rebuilding its client from an arbitrary profile at
   call time, which is a larger change than what today's single-working-
   provider dropdown warrants.

## 7. Streaming-readiness notes

Streaming (SSE/WebSocket push of partial model output) is explicitly out of
scope for the current implementation. Everything today is plain
`fetch()` + polling (`pollDiscovery`/`pollContentArchitect`, ~1.2–1.5s
interval). This was a deliberate choice, not an oversight — but the response
shapes were kept structured JSON per poll (not collapsed into an opaque
string) specifically so a future SSE/WebSocket layer could push the same
JSON shape incrementally without a breaking schema change.

The current Live activity view is the small amount of observability available
before push events exist. It shows stage transitions, durable job transitions,
queued requests, approvals, and errors. Refreshing a session rebuilds the
timeline from the current persisted state and the actions observed in that
browser tab; it does not imply that every server-side event was captured.

## 8. Known limitations

- Document attachment only accepts plain text files up to 200KB; PDF
  extraction is explicitly rejected with a message, not silently dropped.
- The activity view is polling-based and best-effort until a server-side event
  stream is added; it does not show token-level model progress.
- The provider dropdown only has one functioning value; the other entries
  are visible but disabled until a second real provider adapter (e.g.
  Anthropic, Gemini) is built — those providers don't speak the same
  OpenAI-compatible chat/completions protocol the current single adapter
  class handles, so adding one is a new adapter class, not just a config
  entry.
