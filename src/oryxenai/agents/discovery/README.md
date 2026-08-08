# Discovery Agent

Discovery is the first OryxenAI workflow. It turns a user message, an optional
attached document, and an optional goal into a detailed Portfolio Discovery
Brief. It asks only high-value questions along the way, then stops after the
user explicitly approves the brief.

## Responsibilities

- Understand what the user wants and what the portfolio should target.
- Ask only high-value questions (at most 8, asked one at a time in the chat).
- Produce a detailed, readable, editable Portfolio Discovery Brief (free
  Markdown) that hands off context to later content, visual-design, and
  code-generation work.
- Stop after explicit approval.

## Non-responsibilities

Discovery must NOT:

- Write final hero/about/project copy, exact components, layouts, or code.
- Invoke, enqueue, or simulate the Content Architect, Visual Design Director,
  or Code Generator.
- Fetch URLs, scrape the web, OCR, or analyze images.
- Fabricate employment, education, dates, clients, awards, metrics, or
  personal contributions.

## Flow

1. `POST /api/v1/sessions/{id}/discovery/start` stores the raw input
   (`message`, `document_text`, `goal`) as-is and enqueues the
   `discovery.understand_and_question` job. **Input is never validated** —
   the agent accepts any input and decides how to handle it.
2. The worker runs Operation A: one model call returns an interaction mode —
   `NEEDS_DETAILS` (ask the user for material), `ASK_QUESTIONS` (0..7
   specific questions), or `READY_FOR_BRIEF` (enough material) — plus an
   `assistant_message`, the questions, and a compact `memory_update`.
3. `PUT .../discovery/answers` stores the answers as-is; with `complete: true`
   it enqueues `discovery.build_or_revise_brief`.
4. `POST .../discovery/revise` re-runs Operation B with a natural-language
   `revision_request` and the current brief (allowed only while under review).
5. The worker runs Operation B: one model call produces three complementary
   outputs — the full detailed brief as free Markdown (`brief_markdown`,
   persisted and eventually handed to later stages), a short user-facing
   summary (`user_summary`, what the chat UI shows by default), and a
   compact structured profile of categorized facts (`profile`: name,
   experience, education, projects, skills, links). All three are saved to
   session state; only `user_summary` is the primary rendered view.
6. `POST .../discovery/approve` snapshots the approved brief by hash.

The legacy job kinds `discovery.prepare_questions` / `discovery.build_brief`
and operation names `prepare_questions` / `build_brief` remain registered as
aliases so in-flight runs keep working.

## State machine

Statuses (9): `not_started, questions_queued, questions_running,
questions_ready, answers_in_progress, brief_running, brief_review, approved,
needs_attention`. Linear flow; any non-terminal status can fail into
`needs_attention` with a visible `latest_error`, and retry returns to the
queue. `brief_review -> brief_running` exists so revision re-runs Operation B.
The state also carries `attempt`/`max_attempts`/`started_at` so the UI can
show progress and elapsed time, plus `memory` (compact conversation memory)
and `operation_a` (last Operation A output for refresh recovery).

## Output contract

Only the transport envelope is validated (`validators.py`), never the brief
content:

- Operation A (`QuestionSetOutput`) — `mode` is one of `NEEDS_DETAILS`,
  `ASK_QUESTIONS`, `READY_FOR_BRIEF`; `assistant_message` non-empty; questions
  have an `id`, non-empty `text`, a valid `kind`, and options for select
  kinds; mode-specific question-count rules (NEEDS_DETAILS/READY_FOR_BRIEF
  must have zero questions, ASK_QUESTIONS at least one).
- Operation B (`BriefOutput`) — `mode` is `BRIEF_READY`, `assistant_message`,
  `brief_title`, `brief_markdown`, and `user_summary` non-empty; `open_items`
  and `memory_update` are lists/dicts when present; `profile` (if present) is
  checked for SHAPE only against `StructuredProfile` — its field values are
  never judged for accuracy. `profile.projects` length is NOT a validation
  error (a resume can genuinely list more than a handful of real projects,
  and that's a fact about the input, not a model mistake — rejecting and
  retrying could only ever fail again the same way); `DiscoveryAgent`
  truncates it to `[discovery].max_projects` after validation instead.

A model output that fails the contract raises `DiscoveryModelOutputError`
(surfaced as `MODEL_OUTPUT_INVALID`, retryable — it's usually a one-off
generation-quality issue on the same input). Truly unexpected exceptions
surface as `MODEL_OPERATION_FAILED` (not retryable). Either way the failure
only reaches `needs_attention` once retries are exhausted — see "Failure
behavior" below.

## Prompts

Three prompt files. The system prompt is loaded first, then the operation
prompt with the output JSON schema injected and the raw user input appended
as untrusted CDATA:

- `prompts/system.md`
- `prompts/understand_and_question.md`
- `prompts/build_or_revise_brief.md`

How the model produces the output and how detailed the brief should be is the
prompt's logic; there is no repair loop and no few-shot library.

## Model integration

There is no demo mode. The worker always builds the live provider adapter for
the `[profiles.discovery]` profile in `config/models.toml` (currently real
OpenAI, `gpt-5.6-luna`, via the generic OpenAI-protocol adapter — swapping to
any other OpenAI-compatible provider is a config change only, never a code
change: see `ModelCapabilities` in `providers/capabilities.py`); missing
configuration raises a controlled `ProviderConfigError`. The mock-runs dev
harness uses the deterministic `MockModelClient` fallback so it never makes
network calls.

## Failure behavior

- Retryable failures (provider timeout/rate-limit/server errors, and
  `DiscoveryModelOutputError` — invalid model output) are retried silently by
  the worker with backoff, up to `[worker.retry].max_attempts` (default 3).
  `discovery.status` stays at its running value and `attempt` increments each
  try; nothing is shown to the user while retries remain, so a transient hit
  doesn't produce a dead-end error racing the worker's own automatic retry.
- Once a failure is non-retryable, or the last attempt is exhausted,
  `needs_attention` is set with the error code/message and the UI shows a
  "Try again" action.
- The worker renews a claimed job's lease while its handler is still running
  (`Worker._renew_lease_loop`, `jobs/worker.py`) so a legitimately slow
  generation is never mistaken for an abandoned job and re-dispatched a
  second, concurrent time.

## HTTP surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/discovery` | Current state (status, error, attempt, elapsed) |
| POST | `/api/v1/sessions/{id}/discovery/start` | Store input, enqueue Operation A (202) |
| PUT | `/api/v1/sessions/{id}/discovery/answers` | Save answers; `complete: true` enqueues Operation B |
| POST | `/api/v1/sessions/{id}/discovery/revise` | Natural-language brief revision (202) |
| POST | `/api/v1/sessions/{id}/discovery/approve` | Approve the reviewed brief |
