# Discovery Agent

Discovery is the first complete OryxenAI workflow. It turns a user prompt and
optional pasted resume text into a grounded, reviewable strategy brief. It
stops after the user explicitly approves that brief with the `NEXT` action.

## Flow

1. `PUT /api/v1/sessions/{id}/discovery/input` normalizes and stores an
   immutable source revision.
2. `POST .../discovery/questions` creates an idempotent `agent_run` and durable
   worker job for Call A.
3. Call A returns a normalized profile, evidence-backed fact candidates,
   conflicts, omissions, safe automatic presentation choices, and up to eight
   questions.
4. `PUT .../discovery/answers` stores typed answers, skips, and presentation
   auto decisions under the session's Discovery state.
5. `POST .../discovery/brief` creates Call B through the worker.
6. `PATCH .../discovery/brief` applies typed user edits and records
   `user_edit` provenance without another model call.
7. `POST .../discovery/approve` creates an immutable approved brief snapshot.
   It does not enqueue Content Architect or any later agent.

The current aggregate lives in
`portfolio_sessions.current_state["discovery"]`. Immutable source revisions
are stored in `discovery_source_documents`; model inputs, outputs, metadata,
and stale results remain in `agent_runs`.

## Grounding and safety

- Supported facts require evidence that can be located in the normalized source.
- Unknown information is omitted or asked about, never fabricated.
- Material conflicts remain visible until the user resolves them.
- `auto` is accepted only for presentation choices such as tone, theme, motion,
  ordering, emphasis, and CTA phrasing.
- Factual gaps are skipped or omitted by Auto-fill; they are never invented.
- Resume text, prompts, links, and answers are untrusted data and are serialized
  outside the static developer instructions.
- URLs are validated but never fetched by Discovery.

## Model integration

The domain depends on the provider-neutral `ModelClient.generate_structured()`
contract. The configured Discovery profile uses the OpenCode Go adapter with
`deepseek-v4-pro`, `chat/completions`, and
`response_format={"type":"json_object"}`. This is JSON-mode output, not the
OpenAI Responses API's strict typed parsing. Every result is parsed with its
Pydantic output model, then checked by deterministic semantic validators.

Call B allows one bounded semantic repair attempt. A failed repair is persisted
as a controlled `MODEL_OUTPUT_INVALID` result. The application and worker can
start without `OPENCODE_GO_API_KEY`; only a real model operation needs it.

## State and concurrency

Discovery has explicit states from `not_started` through `approved`, with
`needs_attention` for controlled failures. API writes use the portfolio
session revision as an optimistic compare-and-swap token. Worker results carry
source and answer revisions; a late result is retained in `agent_runs` as
stale and cannot overwrite newer user work.

Duplicate enqueue requests use a deterministic operation key. Duplicate `NEXT`
requests return the existing approved state. Editing input, answers, or the
brief invalidates downstream results and approval.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/v1/sessions/{id}/discovery` | User-safe current state and job status |
| PUT | `/api/v1/sessions/{id}/discovery/input` | Save a new source revision |
| POST | `/api/v1/sessions/{id}/discovery/questions` | Queue Call A |
| PUT | `/api/v1/sessions/{id}/discovery/answers` | Save typed answers |
| POST | `/api/v1/sessions/{id}/discovery/brief` | Queue Call B |
| PATCH | `/api/v1/sessions/{id}/discovery/brief` | Apply typed manual edits |
| POST | `/api/v1/sessions/{id}/discovery/approve` | Create immutable approval |

Errors use the existing envelope and safe codes such as
`DISCOVERY_REVISION_CONFLICT`, `DISCOVERY_QUESTIONS_STALE`,
`DISCOVERY_BRIEF_STALE`, `DISCOVERY_NOT_READY`, `DISCOVERY_RESULT_STALE`, and
`MODEL_OUTPUT_INVALID`.

## Frontend harness

The existing Jinja2 and vanilla JavaScript harness contains the complete
developer flow: intake, link validation, one-question-at-a-time navigation,
Back/Next, Choose for me, Skip, Auto-fill remaining, brief editing, polling,
refresh restoration, and the visually distinct approval action. It uses
`textContent` and DOM APIs for dynamic output, does not place credentials or
resume text in browser storage, and does not display raw provider errors.

## Tests and commands

Normal tests use `FakeDiscoveryModelClient` and require no credentials. The
OpenCode adapter is tested at its SDK boundary without network access. Run:

```powershell
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest tests/unit/ -q
uv run alembic upgrade head
```

Integration and worker tests use the configured dedicated PostgreSQL test
database when available. A live OpenCode smoke test, if added, must be
explicitly opt-in and use synthetic data only.
