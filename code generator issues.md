# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## Current state — 2026-09-04 (evening pass)

- All 7 Code Generator model profiles (director, planner, resource_scout,
  route_builder, route_composer, integrator, repairer) now route through
  **ScaleMax** (`provider = "scalemax"`, `base_url =
  https://api.scalemax.pro/v1`, `api_key_env = SCALEMAX_API_KEY`) instead of
  direct OpenAI, keeping the same `gpt-5.6-luna` model. No new adapter code
  was needed — the existing generic `OpenAICompatibleAdapter` already builds
  its client purely from the profile's `base_url`/`api_key_env`; only a
  profile-config change plus one `providers/factory.py` dispatch-dict entry
  were required.
- Live-verified against the supplied test pack
  `output/build-preparation/01-31-04-09-94ae4a9c/` (1 route, 6 sections, 7
  resource / 4 component candidates, all eligible) across 4 fresh runs this
  session, using a second, isolated native instance on port 8001 (the
  already-running port-8000 process turned out to be stale, pre-dating the
  D-062/D-064 Markdown-brief migration — do not assume port 8000 is current
  without checking `GET .../build-preparation-packs` returns
  `source_version: "build-preparation-brief-v1"` first).

## Findings and fixes (this pass)

| Area | Finding | Durable resolution |
|---|---|---|
| Provider rate limit | The prior blocker, `PROVIDER_RATE_LIMIT_ERROR` from direct OpenAI during route generation, is resolved by the ScaleMax switch. 4 fresh runs against ScaleMax produced zero rate-limit errors; every `chat/completions` call returned 200. | Route all 7 profiles through ScaleMax (`config/models.toml`); `providers/factory.py` gains a `"scalemax"` dispatch entry (reuses `_openai_compatible`); `model_runtime.py`'s Anthropic-effort-on-OpenAI-transport guard extended to include `"scalemax"`. |
| Director schema compliance | Run 1 and run 2 both reached `needs_attention` at the **plan** stage with `PLANNER_OUTPUT_INVALID` — actually the **director's** own `CreativeDirectionSetV3` validation, mislabeled by the shared job-error mapper (any `ValidationError` during the plan phase gets this generic code). Real cause, captured via new temporary-then-kept diagnostic logging: ScaleMax returned HTTP 200 for a `strict: true` `json_schema` request, but the model's JSON did not conform — missing required fields (`motion_vocabulary`, `resource_use`, `distinguishing_moves`), wrong-typed fields (`hierarchy`/`composition`/`typography`/`color_logic` as non-strings), a wrong `schema_version` literal, and (run 3, after the `schema_version` prompt fix) an invented extra property `motion` instead of `motion_vocabulary`. This is direct evidence ScaleMax's gateway does **not** reliably enforce strict JSON-schema-constrained decoding the way real OpenAI does, despite accepting the request. | Two fixes: (1) `creative_operation.py` now logs a safe (loc+msg only, no model content) validation summary on the final failed attempt, so this class of failure is diagnosable without spending another live call. (2) `opencode_go.py`'s `_generate_structured_impl`, when `strict_schema=True` (every Code Generator call), now *also* restates the exact strict schema as explicit prompt text ("use only these property names, never invent/rename/omit one, copy any literal enum value exactly") in addition to the `response_format` request — a no-op for a gateway that already enforces it, a real safety net for one that doesn't. Also strengthened the shared `system.md` with an explicit "never omit a required field" rule. Run 4 (with both fixes) passed director/planner validation cleanly on the first attempt. |
| Caching (this session's second priority) | `prompt_cache_ttl = "5m"` was declared on every profile but was dead config for the OpenAI-compatible path — only the Anthropic adapter ever read it. Worse, the untrusted-input wire payload was always serialized with `sort_keys=True`, which interleaves each call's unique keys (`diagnostics`, `plan`, ...) alphabetically among the large, byte-identical-across-calls foundation content (`shared_source`, `site_contract`, ...), destroying any provider-side prefix-cache opportunity before it could start. | Added an opt-in `request_context={"key_order": [...]}` hook (via the existing, previously-unused `request_context` parameter already on `ModelClient.generate_structured`) so Code Generator's own call sites can put invariant per-run content first and per-call content last in the wire JSON, without changing the JSON shape any prompt or model sees — zero effect on Discovery/Content Architect/Visual Design Director/Build Preparation, which never pass it. Applied to director/planner (`PLANNER_FOUNDATION_KEY_ORDER`), route batch/compose/integrate/repair (`ROUTE_UNIT_KEY_ORDER`), and final repair (`FINAL_REPAIR_KEY_ORDER`) — see `generation_prompt_builder.py`. Also added an optional `prompt_cache_key` (`f"codegen:{generation_id}:{role_profile}"`), sent only when a profile declares the new `supports_prompt_cache_key` capability (set for the 7 Code Generator profiles), mirroring the existing `store` capability-gated pattern. **Not independently confirmed live**: usage/token data (including any `prompt_tokens_details.cached_tokens` ScaleMax might report) is never persisted to disk in this pipeline, so a real cache-hit count could not be checked post-hoc this session. A future session wanting to confirm real savings should temporarily log `result.usage` for one repeated-call pair. |
| Batch API | Considered per the user's request to look at "batch" processing for cost. Rejected, consistent with D-040: Code Generator's stages are sequentially dependent within one durable job (each call's result gates the next), which does not fit an asynchronous, delayed-turnaround batch API. |

## New blocker found this pass (run `de0ee1f3-3a61-4f84-92e8-047820dbb1a7`)

- With both fixes above in place, run 4 got further than any run this
  session: admission → plan → acquire → **generate** (foundation, both route
  batches, route compose, 3 full integration-review/repair polish rounds) —
  a real portfolio source tree was produced. It landed in `needs_attention`
  at the generate stage with `INTEGRATION_REVIEW_UNRESOLVED`: *"The completed
  source tree did not pass the bounded whole-site quality review after 3
  polish rounds."* `max_integration_polish_rounds` is Pydantic-bounded
  `ge=1, le=3` — a deliberate hard ceiling, not a config value to casually
  raise without evidence the repair loop is actually converging slowly
  rather than failing to converge at all.
- The review's own findings (`integration_review` column,
  `code_generator_runs` table) are genuine, specific, and plausible-to-fix,
  not generic placeholders: a missing persistent chapter-rail nav pattern
  (`quality-hierarchy-001`), a hero CSS grid applied to the wrong DOM level
  relative to its rendered wrapper (`quality-composition-001`), missing
  explicit heading font-weights (`quality-typography-001`), and one
  advisory-only interaction refinement. Three of the four are `severity:
  "blocking"`.
- This is qualitatively different from the rate-limit and schema-compliance
  blockers above — the model consistently reached real review feedback and
  attempted real repairs across 3 rounds but didn't fully converge in time.
  Whether that's a Luna-via-ScaleMax capability limit on this specific
  polish loop, or a fixable repair-prompt/context gap, needs more live
  evidence before deciding — don't assume either without a fresh run.

## Remaining external blocker

- None from the provider/rate-limit class — resolved this pass.

## Next verification target

- Resume or re-run against the same pack and check whether the 3
  integration-review findings above (chapter rail, hero grid/wrapper,
  heading weights) get fully resolved with the existing bounded budget on a
  repeat attempt (repair calls are non-deterministic), or whether they
  recur identically — recurrence would point at a genuine repair-loop gap
  worth prompt/context investigation rather than a one-off model miss.
