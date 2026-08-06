# Discovery prompt changelog

## v2 (2026-08-06)

### What changed

- Replaced the four flat prompt files (`system.md`, `prepare_questions.md`,
  `build_brief.md`, `repair_output.md`) with a modular tree:
  `core_identity.md`, `trust_boundary.md`, `grounding_policy.md`,
  `source_interpretation.md`, `prepare_questions.md`, `question_policy.md`,
  `build_brief.md`, `downstream_handoff_policy.md`,
  `output_rules_call_a.md`, `output_rules_call_b.md`, `repair.md`, and
  `examples/` with golden call_a/call_b examples and anti-examples.
- Assembly order is now fixed: identity -> trust boundary -> grounding ->
  source interpretation -> operation rules -> policies -> output contract
  -> few-shot examples -> dynamic source packet (CDATA) -> final reminder.
- Schema-first: the Pydantic JSON schema for the operation is injected into
  the output contract so prompt and model contracts cannot silently drift.
- Few-shot examples: up to two golden examples selected deterministically
  by scenario tags (complete, sparse, conflict_heavy, multilingual,
  confidential, no_resume). Previously there were zero examples.
- Contrastive anti-examples for unsupported metrics, weak questions, and
  factual Auto decisions.
- Repair instructions are now explicit and bounded: correct only listed
  validation errors, preserve valid data, do not add facts or invent IDs.
- Versions: `discovery.core.v2`, `discovery.call_a.v2`, `discovery.call_b.v2`,
  `discovery.repair.v2`, `discovery.examples.v2`. Module hashes are
  persisted in `agent_runs.model_metadata.prompt_modules`.

### Why

The v1 prompts were instruction-only with no examples, no schema contract,
no explicit source-classification policy, and an 11-line repair prompt.
The independent verification audit (2026-08-06) found: zero few-shot
examples, no schema-drift protection, no contrastive guidance, and a repair
prompt that did not carry valid source/fact IDs.

### Which fixtures exposed the weakness

- `tests/fixtures/discovery/injection_resume.json` — no prompt policy told
  the model how to classify embedded instructions.
- `tests/fixtures/discovery/no_metrics.json` — no metric anti-example.
- `tests/fixtures/discovery/conflicting_dates.json` — no conflict-handling
  guidance beyond generic text.

### Metrics (filled after acceptance run, 2026-08-06)

- Baseline v1: valid JSON rate untested live; no schema drift protection;
  no few-shot guidance; Call A never repaired.
- Candidate v2 (real provider, 15 synthetic cases, non-thinking JSON mode):
  - valid_json_rate = 1.0
  - schema_pass_rate = 0.933
  - semantic_pass_rate = 0.6 (remaining failures recovered by the bounded
    one-attempt repair step)
  - empty_rate = 0.0, truncation_rate = 0.0
  - median latency ≈ 80s per Call A on deepseek-v4-pro
- Thinking-enabled profile: rejected by the endpoint
  (MODEL_CAPABILITY_UNSUPPORTED) — not selected.
- Application-level corpus: 36/36 scenario assertion suites pass; critical
  factual-safety metrics are zero.

### Known limitations

- Example selection is tag-based and heuristic; it does not search the full
  resume for scenario signals beyond the tags listed above.
- The live thinking-mode benchmark may change `reasoning_effort`; if
  thinking is enabled, module hashes remain stable because they hash the
  static files, not the live configuration.
