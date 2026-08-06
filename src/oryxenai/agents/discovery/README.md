# Discovery Agent

Discovery is the first complete OryxenAI workflow. It turns a user prompt and
optional pasted resume text into a grounded, reviewable strategy brief. It
stops after the user explicitly approves that brief with the `NEXT` action.

## Responsibilities

- Understand who the user is professionally and what role the portfolio
  should target.
- Extract atomic, evidence-backed facts with locatable provenance.
- Detect conflicts, uncertainty, and omission needs.
- Ask only high-value questions (at most eight, one at a time).
- Make automatic choices only for presentation decisions.
- Produce a rich strategic brief that later agents can use.
- Stop after explicit approval.

## Non-responsibilities

Discovery must NOT:

- Write final hero/about/project copy, exact components, layouts, or code.
- Invoke, enqueue, or simulate the Content Architect, Visual Design
  Director, or Code Generator.
- Fetch URLs, scrape GitHub/LinkedIn, OCR, or analyze images.
- Fabricate employment, education, dates, clients, awards, metrics, or
  personal contributions.
- Assume every user is a developer, wants employment, or wants a dark theme.

## Flow

1. `PUT /api/v1/sessions/{id}/discovery/input` normalizes and stores an
   immutable source revision.
2. `POST .../discovery/questions` creates an idempotent `agent_run` and durable
   worker job for Call A.
3. Call A returns a source assessment, profile overview, normalized profile,
   evidence-backed facts, conflicts, uncertainties, omissions, safe automatic
   presentation choices, readiness, and quality checks.
4. `PUT .../discovery/answers` stores typed answers, skips, and presentation
   auto decisions under the session's Discovery state.
5. `POST .../discovery/brief` creates Call B through the worker.
6. `PATCH .../discovery/brief` applies typed user edits (deep-merged, with
   `user_edit` provenance) without another model call.
7. `POST .../discovery/approve` creates an immutable approved brief snapshot.
   It does not enqueue Content Architect or any later agent.

The current aggregate lives in
`portfolio_sessions.current_state["discovery"]`. Immutable source revisions
are stored in `discovery_source_documents`; model inputs, outputs, metadata,
and stale results remain in `agent_runs`.

## Call A algorithm

1. Assess source usability (usable / usable-with-gaps / sparse / unusable).
2. Extract atomic facts; normalize without inventing data.
3. Validate provenance candidates (excerpts must be locatable).
4. Detect conflicts (dates, titles, ownership, metrics, confidentiality…).
5. Record uncertainties with recommended actions.
6. Score and select questions (downstream impact, credibility, conflict
   value, information gain, already-answered penalty, effort, sensitivity).
7. Select safe automatic presentation defaults only.
8. Return `DiscoveryAnalysisResult` v2 with readiness and quality checks.

## Call B algorithm

1. Reconcile source facts and user answers.
2. Resolve only explicitly resolved conflicts; preserve unresolved material
   conflicts.
3. Select one primary target role where supported.
4. Define audience, goal, and evidence-backed positioning with credibility
   boundaries.
5. Select featured projects with per-project evidence, depth, unknowns, and
   confidentiality.
6. Define content strategy, omissions, tone/theme/motion direction, and CTA.
7. Build the downstream handoff for later agents.
8. Run grounding verification and return `DiscoveryBrief` v2.

## Grounding and safety

- Supported facts require evidence that can be located in the normalized source.
- Unknown information is omitted or asked about, never fabricated.
- Material conflicts remain visible until the user resolves them.
- `auto` is accepted only for presentation choices such as tone, theme, motion,
  ordering, emphasis, and CTA phrasing.
- Factual gaps are skipped or omitted by Auto-fill; they are never invented.
- Resume text, prompts, links, and answers are untrusted data and are serialized
  in a CDATA-wrapped `<source_packet trust="untrusted">` after all static
  instructions.
- URLs are validated but never fetched by Discovery.
- Deterministic semantic validation runs after every model output for both
  Call A and Call B; the agent enforces the result (repair once, then fail
  with `MODEL_SEMANTICALLY_INVALID` — invalid output is never delivered).

## Model integration

The domain depends on the provider-neutral `ModelClient.generate_structured()`
contract. The configured Discovery profile uses the OpenCode Go adapter with
`deepseek-v4-pro`, `chat/completions`, and
`response_format={"type":"json_object"}`.

- **JSON mode:** the Pydantic JSON schema for the operation is injected into
  the prompt (schema-first; a drift test pins prompt fields to the schema).
- **Thinking mode:** benchmarked live (2026-08-06). The OpenCode Go endpoint
  rejects the `reasoning` parameter (`MODEL_CAPABILITY_UNSUPPORTED`), so the
  production profile uses non-thinking JSON mode (`reasoning_effort=""`).
- **Capability probe:** `ModelCapabilities` declares what the endpoint
  supports. `store=false` is sent only when `supports_store_parameter` is true.
- **reasoning_content** is never captured, persisted, or logged; only the final
  `message.content` is read.
- **Retry budget:** one transport retry (SDK), one completed-response recovery
  (empty/whitespace/truncated/malformed/semantic), one semantic repair, worker
  `max_attempts` bounded. Total model calls per logical operation ≤ 2.
- **Observability:** `finish_reason`, `latency_ms`, `usage`, `prompt_version`,
  and a module-hash manifest are persisted on `agent_runs`.

## Prompt module architecture (v2)

```
prompts/
  core_identity.md              identity and professional understanding
  trust_boundary.md             untrusted-source policy
  grounding_policy.md           provenance + evidence-first rules
  source_interpretation.md      content classification + multi-document rules
  prepare_questions.md          Call A operation
  question_policy.md            question rubric and writing quality
  build_brief.md                Call B operation
  downstream_handoff_policy.md  Content Architect / Visual Director boundaries
  output_rules_call_a.md        Call A output contract (+ injected schema)
  output_rules_call_b.md        Call B output contract (+ injected schema)
  repair.md                     bounded repair instructions
  examples/call_a|call_b/       golden few-shot examples (tag-selected, ≤2)
  examples/anti_examples/       contrastive bad/good guidance
  CHANGELOG.md                  prompt change log
```

Versions: `discovery.core.v2`, `discovery.call_a.v2`, `discovery.call_b.v2`,
`discovery.repair.v2`, `discovery.examples.v2`. Assembly order is fixed:
identity → trust boundary → grounding → source interpretation → operation →
policy → output contract/schema → examples → dynamic source packet → final
reminder. Static material always precedes dynamic user data.

## State and concurrency

Discovery has explicit states from `not_started` through `approved`, with
`needs_attention` for controlled failures. All `apply_*` transitions are
validated (edits and approval included). API writes use the portfolio session
revision as an optimistic compare-and-swap token. Worker results carry source
and answer revisions; a late result is retained in `agent_runs` as stale and
cannot overwrite newer user work.

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
`DISCOVERY_BRIEF_STALE`, `DISCOVERY_NOT_READY`, `DISCOVERY_INPUT_INVALID`,
`DISCOVERY_APPROVAL_INVALIDATED`, `DISCOVERY_SOURCE_TOO_LARGE`,
`MODEL_OUTPUT_INVALID`, `MODEL_OPERATION_CANCELLED`, `MODEL_EMPTY_OUTPUT`,
`MODEL_OUTPUT_TRUNCATED`, `MODEL_JSON_INVALID`, `MODEL_SEMANTICALLY_INVALID`,
`MODEL_CAPABILITY_UNSUPPORTED`, and the `PROVIDER_*` family.

## Sample corpus and evaluation

- 36 golden behavioral scenarios under
  `tests/fixtures/discovery/scenarios/<name>/` (input, expected Call A,
  answers, expected Call B, assertions.yaml) covering the Section-21 list.
- `tests/eval/` runs the application-level assertions in normal CI and the
  full model-dependent assertions against the live provider under `-m live`.
- Deterministic metrics: unsupported-claim count, factual-Auto count,
  evidence validity, conflict detection, private-contact publication, etc.
- Metamorphic and mutation/fuzz tests guard against irrelevant-input drift
  and malformed-input crashes.
- Live eval runner: `scripts/live-discovery-eval.ps1` (opt-in, synthetic only,
  sanitized reports under `reports/live-discovery/`).

## Privacy behavior

Only safe fields are logged (request ID, job/run ID, operation, prompt
version, model, attempt counts, finish reason, latency, counts). Raw resume,
main prompt, answers, brief, `reasoning_content`, system prompt text, API
keys, and provider error bodies are never logged. The OpenCode Go request is
sent with `store=false` when the endpoint capability supports it; OpenCode's
content handling can depend on third-party model providers, so no OpenAI-
specific retention guarantees are claimed.

## Failure behavior

- Missing provider configuration or key → safe `PROVIDER_CONFIG_ERROR`; the
  app and worker still start.
- Empty/whitespace output → `MODEL_EMPTY_OUTPUT`.
- Truncated output → `MODEL_OUTPUT_TRUNCATED`.
- Malformed JSON → `MODEL_JSON_INVALID`.
- Semantic failure after one repair → `MODEL_SEMANTICALLY_INVALID`, state
  moved to `needs_attention`.
- Worker retries respect the bounded attempt policy; late results are marked
  stale, never applied over newer state.

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
database when available. Live provider tests are opt-in
(`RUN_LIVE_DISCOVERY=1` + `OPENCODE_GO_API_KEY`) and use synthetic data only.
