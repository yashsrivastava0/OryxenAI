# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## Current state — 2026-09-04/05 (two passes)

All 7 Code Generator model profiles now route through **direct OpenAI**
(`provider = "openai"`, `api_key_env = OPENAI_API_KEY`, model `gpt-5.6-luna`)
— the account was recharged and a corrected key confirmed live via a cheap
preflight check (`ModelRuntime.preflight()`, a few dozen tokens, no
portfolio content) before any paid generation ran. **ScaleMax** (`provider =
"scalemax"`, same model, `SCALEMAX_API_KEY`/`SCALEMAX_BASE_URL`) was used for
most of the first pass and is fully wired and confirmed working — kept as a
config option (just flip `provider`/`base_url`/`api_key_env` on the 7
`code_generator_*` profiles) if OpenAI credit/rate issues recur.

Live-verified against the supplied test pack
`output/build-preparation/01-31-04-09-94ae4a9c/` (1 route, 6 sections, 7
resource / 4 component candidates, all eligible) across 7 fresh live runs
total this session (4 on ScaleMax, 3 on OpenAI), using a second, isolated
native instance on port 8001 (the already-running port-8000 process was
stale, pre-dating the D-062/D-064 Markdown-brief migration — do not assume
port 8000 is current without checking `GET .../build-preparation-packs`
returns `source_version: "build-preparation-brief-v1"` first).

## Findings and fixes — pass 1 (ScaleMax switch)

| Area | Finding | Durable resolution |
|---|---|---|
| Provider rate limit | The prior blocker, `PROVIDER_RATE_LIMIT_ERROR` from direct OpenAI during route generation, was resolved (that session) by switching to ScaleMax; ScaleMax runs produced zero rate-limit errors. Pass 2 confirmed direct OpenAI itself is also clean once the account has real credit — the original 429s were plausibly credit-tier-related, not a hard capacity wall. | `providers/factory.py` gained a `"scalemax"` dispatch entry (reuses the existing generic `_openai_compatible` adapter — no new adapter class needed); `model_runtime.py`'s Anthropic-effort-on-OpenAI-transport guard extended to include `"scalemax"`. |
| Director schema compliance (ScaleMax-specific) | ScaleMax returned HTTP 200 for a `strict: true` `json_schema` request, but the model's JSON did not conform — missing required fields, wrong-typed fields, a wrong `schema_version` literal, and an invented extra property (`motion` instead of `motion_vocabulary`). Direct evidence ScaleMax's gateway does not reliably enforce strict JSON-schema-constrained decoding the way real OpenAI does, despite accepting the request. | `opencode_go.py`'s `_generate_structured_impl`, whenever `strict_schema=True` (every Code Generator call, on any OpenAI-protocol provider), now *also* restates the exact strict schema as explicit prompt text in addition to the `response_format` request — a no-op for a gateway that already enforces it (confirmed: direct OpenAI never needed the repair-loop help this triggered), a real safety net for one that doesn't. `system.md` gained an explicit "never omit a required field, copy literal enum values exactly" rule. Also added a safe (loc+msg only) validation-summary log at the point of final failure, so this class of failure is diagnosable without spending another live call. |
| Caching | `prompt_cache_ttl = "5m"` was dead config for the OpenAI-compatible path (only the Anthropic adapter read it). The untrusted-input wire payload was always `sort_keys=True`, interleaving each call's unique keys among content that repeats byte-for-byte across a run, defeating provider-side prefix caching before it could start. | Added an opt-in `request_context={"key_order": [...]}` hook riding on `ModelClient.generate_structured`'s previously-unused `request_context` parameter — Code Generator's call sites (director/planner, route batch/compose/integrate/repair, final repair) place invariant per-run content first; zero effect on any other agent, which never sets it. Also an optional `prompt_cache_key`, capability-gated (`supports_prompt_cache_key`). **Confirmed the code path works** (a direct-OpenAI preflight call returned `cached_prompt_tokens: 0`, correctly — those calls are ~280 tokens, under OpenAI's ~1024-token minimum for caching to engage); **real cache-hit savings on an actual generation call were not checked** (would need a temporary `result.usage` log during a live run — not done this session). |
| Batch API | Rejected, consistent with D-040: Code Generator's stages are sequentially dependent within one durable job, which does not fit an asynchronous, delayed-turnaround batch API. |

## Findings and fixes — pass 2 (direct OpenAI, duplicate-path fix, polish-round ceiling)

| Area | Finding | Durable resolution |
|---|---|---|
| `SOURCE_DUPLICATE_PATH` gave the repair model nothing to act on | A live OpenAI run's `v4` source envelope had two entries for the same file path. The host-side check (`_validate_v4_generation_coverage` in `generation_orchestrator.py`) raised `SourceValidationError("SOURCE_DUPLICATE_PATH", ...)` **without** a `file=` value — unlike its sibling checks. The repair model, given a diagnostic with no file reference, correctly (if unhelpfully) reported it couldn't make a bounded fix rather than guess — exactly the project's own "honest cannot_complete over guessing" design working as intended, just starved of the one fact it needed. | The check now finds the actual duplicated path(s) and passes the first one as `file=`, plus a message naming it explicitly. New unit test: `test_v4_duplicate_path_identifies_the_offending_file` in `test_v4_contracts.py`. A follow-up run with this fix in place did not hit this diagnostic again. |
| `max_integration_polish_rounds` ceiling (3) was too tight | **Two independent live runs — one on ScaleMax, one on direct OpenAI, same pack — both converged steadily each round and then ran out of budget while still making real progress**, not while stuck: ScaleMax run went from 3 blocking findings to 1 lone "bounded motion correction" per the reviewer's own words; OpenAI run (pass 2) similarly narrowed to one specific, well-described issue. This is real, reproducible, cross-provider evidence the ceiling itself — not model capability — was the limiter. | Raised `max_integration_polish_rounds` from `Field(default=3, ge=1, le=3)` to `Field(default=5, ge=1, le=6)` in `core/settings.py`, and `config/app.toml`'s value to match. **Confirmed live**: a repeat OpenAI run with the raised ceiling fully converged the integration-review loop and advanced past `generate` into `verify_and_preview` — the furthest any run has reached this session. |

## Current blocker (run `6f4cd2e2-08d6-424f-9c5a-e76169578e30`, direct OpenAI, both fixes above applied)

- With the polish-ceiling fix, a run reached **final verification** (clean
  build + repair + whole-site re-review) for the first time this session —
  past the previous universal bottleneck entirely. It landed in
  `needs_attention` with `QUALITY_REVIEW_REJECTED_AFTER_REPAIR`: after one
  repair round fixed the build/typecheck-level issues, the final whole-site
  re-review scored the site well (hierarchy=4, composition=4, typography=4,
  resource_fit=5, motion=4) but found **one** remaining blocking finding —
  `missing-section-heading`: the Experience section's `aria-labelledby`
  points at a `<p>` instead of a heading element, breaking the document
  outline/assistive-tech navigation. A real, specific, easily-fixable
  accessibility issue, not a structural failure.
- This gate's repair budget is `max_repair_rounds_total`/
  `max_repair_rounds_per_unit` (6/3), a **different, already-separately-
  reasoned** budget (D-056, D-058) than the one just raised, and shared with
  mid-generation repair. Only one data point exists for it being too tight
  here (vs. two independent cross-provider data points that justified
  raising the polish-round ceiling) — **do not raise it yet** without a
  second confirming run; it may simply need a fresh attempt, since repair
  calls are non-deterministic.

## Remaining external blocker

- None from the provider/rate-limit/schema-compliance class — resolved this
  pass, on both ScaleMax and direct OpenAI.

## Next verification target

- Re-run against the same pack with both fixes in place and check whether
  `QUALITY_REVIEW_REJECTED_AFTER_REPAIR` recurs on the same
  `missing-section-heading`-shaped issue (→ a real gap in how the final
  repair round is scoped/prompted, worth investigating) or resolves cleanly
  (→ was ordinary non-determinism, no further fix needed).
