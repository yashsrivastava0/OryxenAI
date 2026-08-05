OryxenAI Discovery — Full Implementation Plan
Locked-in decisions (from your answers)
1. Phasing: single continuous pass (no mid-stream pauses).
2. Schema: replace v1 → v2, no v1 data migration (no production data; all Discovery work untracked).
3. Live verification: ON — run the real deepseek-v4-pro smoke test + thinking benchmark using the key in .env.
4. State machine: tighten it (all apply_* validate transitions).
5. Git: commit current v1 baseline on main first (no push).
6. Migration 0004: add it for finish_reason/latency_ms/usage columns + actually write prompt_version.
7. Fake client: rewrite the 2 existing samples/*.json to v2 shape.
Architectural boundaries I will NOT cross (Section 1, 2, 53)
- No Content Architect / Visual Director / Code Generator behavior, no agent chaining, no supervisor, no web fetching, no OCR.
- No LangChain/CrewAI/AutoGen/Temporal/Redis/Celery/etc.
- Domain modules (discovery/*.py except via the adapter) never import OpenAI/DeepSeek classes.
- App, worker, fake-client, API, frontend start without OPENCODE_GO_API_KEY.
- No destructive git; no secret printing; no applied-migration modification; format only changed files.
Phase 0 — Verification Matrix & Baseline (deliverable A, +Part A audit)
T0.1 Commit v1 baseline
Files: whole working tree (currently untracked).
Change: git add -A && git commit -m "chore: snapshot v1 Discovery baseline before v2 upgrade" on main. No push.
Why: gives a clean v1 diff point; per your decision.
Verify: git status clean; git log --oneline -3 shows the new commit atop bdc8822.
T0.2 Build the 54-row + Section-30 verification matrix
File: PLANforDiscoveryAgent.md (append Section 31.A later; I'll draft it now and finalize in T19).
Content: one row per original DoD criterion (52-DoD list at PLAN:3066-3122) plus the new Section-30 criteria. Columns: Requirement | Reported | Repo evidence (file:line) | Runtime/test evidence | Actual status | Gap | Required action.
Already-determined statuses from my audit (sample, not exhaustive):
- Six evaluation fixtures pass → FAILED (tests/fixtures/discovery/*.json have zero test references; confirmed by grep).
- Factual Auto rejected → PARTIALLY VERIFIED (validator-only at validators.py:98; agent returns invalid anyway at agent.py:108-113).
- Repair bounded to 1 → PARTIALLY VERIFIED (Call B only; Call A never repairs; no test asserts the bound).
- store=false → OUTDATED (settings.py:192 field exists but adapter opencode_go.py:185-189 never sends it).
- Reasoning leakage prevented → PARTIALLY VERIFIED (adapter only reads message.content; no guard test).
- 54/54 reproduced → NOT fully reproduced (6+ qualitative criteria FAILED/PARTIAL).
Why: Section 31-A deliverable; honest baseline.
Verify: matrix present in PLAN; every FAILED/PARTIAL row has an action in T1–T19.
T0.3 Quantitative baseline snapshot (documented)
Commands (read-only now; will rerun at T19): uv run pytest --collect-only -q → 330; uv run pytest -q → current pass count; uv run ruff check .; uv run ruff format --check .; uv run mypy src; uv run alembic current → 0003; docker compose config.
Record: baseline numbers in PLANforDiscoveryAgent.md for the baseline-vs-candidate report (Section 26.5, Section 31-E).
Verify: baseline numbers captured.
Phase 1 — Provider Capability Model & Adapter Hardening (Sections 7, 7.1, 7.3, 8, 28)
T1.1 src/oryxenai/agents/shared/providers/capabilities.py (NEW)
Content: ModelCapabilities(BaseModel) with model_config = ConfigDict(extra="forbid") and fields exactly: json_object_mode: bool, json_schema_mode: bool, thinking_mode: bool, reasoning_content: bool, temperature_control: bool, usage_metadata: bool, response_id: bool, context_cache_metadata: bool, supports_store_parameter: bool. Plus DEFAULT_OPENCODE_GO = ModelCapabilities(json_object_mode=True, json_schema_mode=False, thinking_mode=True, reasoning_content=True, temperature_control=True, usage_metadata=True, response_id=True, context_cache_metadata=False, supports_store_parameter=True) — defaults representing the configured endpoint's observed/advertised shape (the live smoke test in T3 will confirm/refute these).
Why: Section 7.1; capability assumptions become explicit, not silent.
Verify: unit test asserts all fields exist and DEFAULT_OPENCODE_GO.json_object_mode is True.
T1.2 src/oryxenai/agents/shared/providers/opencode_go.py (EDIT)
Changes:
- Import ModelCapabilities; expose self._capabilities resolved from a profile field (add capabilities: ModelCapabilities | None to ModelProfile in T1.4, fallback to DEFAULT_OPENCODE_GO).
- Thinking mode: when profile.reasoning_effort is non-empty, send reasoning={"effort": profile.reasoning_effort} (or the OpenCode-supported key — confirmed by the live smoke test in T3). When empty, omit (non-thinking). Do NOT enable thinking by default until T3 proves JSON + thinking coexist reliably (Section 7.3).
- reasoning_content discard: after reading response.choices[0].message.content, explicitly assert getattr(message, "reasoning_content", None) is never copied into StructuredModelResult or any log. Add a guard test.
- store=false: pass store=False to chat.completions.create when profile.store is False AND self._capabilities.supports_store_parameter is True. Otherwise omit (avoid an unsupported-param 400).
- Forward finish_reason/usage/response_id/latency into StructuredModelResult (already done at opencode_go.py:134-141); confirm latency_ms is real.
Why: Sections 7.2, 7.3, 8, 28.
Verify: unit test asserts thinking param only sent when reasoning_effort set; store only sent when capability true; reasoning_content never in result/logs.
T1.3 src/oryxenai/agents/shared/providers/errors.py (EDIT)
Add error classes / codes (with code literals and retryable flags):
- ModelEmptyOutputError(code="MODEL_EMPTY_OUTPUT", retryable=True).
- ModelOutputTruncatedError(code="MODEL_OUTPUT_TRUNCATED", retryable=True) — detected via finish_reason == "length".
- ModelJsonInvalidError(code="MODEL_JSON_INVALID", retryable=True) — wraps json.JSONDecodeError.
- ModelSemanticallyInvalidError(code="MODEL_SEMANTICALLY_INVALID", retryable=False) — after a failed repair.
- ModelCapabilityUnsupportedError(code="MODEL_CAPABILITY_UNSUPPORTED", retryable=False).
- NetworkRetryExhaustedError(code="NETWORK_RETRY_EXHAUSTED", retryable=False).
Map these at the adapter: empty/whitespace → MODEL_EMPTY_OUTPUT; finish_reason=="length" → MODEL_OUTPUT_TRUNCATED; JSONDecodeError → MODEL_JSON_INVALID; post-repair invalid → MODEL_SEMANTICALLY_INVALID.
Why: Section 8; closes the 15-of-24 missing code gap (T0.2 audit).
Verify: grep finds all 6 new literals in errors.py and tests/.
T1.4 src/oryxenai/core/settings.py (EDIT)
Add to ModelProfile: capabilities: ModelCapabilities | None = None (now 11 fields). Default None → adapter resolves to DEFAULT_OPENCODE_GO.
Verify: get_profile("discovery").capabilities is None; adapter falls back correctly.
T1.5 src/oryxenai/agents/shared/providers/attempt_policy.py (NEW)
Content: AttemptBudget(BaseModel) with transport_retry: int = 1, completed_response_recovery: int = 1, semantic_repair: int = 1, worker_max_attempts: int = 3, and a derived total_model_calls_max (= 1 transport + 1 recovery-with-repair = up to 3 model calls per logical operation, capped). A remaining() helper. Persisted into agent_runs.model_metadata as attempt_budget.
Why: Section 8 total bound.
Verify: unit test asserts total_model_calls_max and that worker retry does NOT restart an already-completed response blindly.
T1.6 src/oryxenai/db/models/agent_run.py (EDIT) + migration 0004
Add columns: finish_reason: Mapped[str | None], latency_ms: Mapped[float | None], usage: Mapped[dict | None] (JSONB). prompt_version already exists (agent_run.py:43) but executor drops it — fix in T1.7.
Migration migrations/versions/0004_discovery_run_metadata.py: ALTER TABLE agent_runs ADD COLUMN finish_reason TEXT NULL, ADD COLUMN latency_ms DOUBLE PRECISION NULL, ADD COLUMN usage JSONB NULL. downgrade() drops them. Round-trip tested in T19.
Why: Section 8 persistence; closes "finish_reason captured but not persisted" gap.
Verify: alembic upgrade head → 0004; alembic downgrade -1 → 0003; upgrade head → 0004.
T1.7 src/oryxenai/agents/shared/executor.py (EDIT) + db/repositories/agent_runs.py (EDIT)
Changes:
- executor.py:180 currently mark_succeeded(run_id, result.output, state_after) — forward prompt_version=result.prompt_version and model_metadata=result.model_metadata.
- mark_succeeded repo signature gains optional finish_reason, latency_ms, usage kwargs; writes new columns when provided.
- The worker path (jobs/handlers/discovery.py:386-394) already passes prompt_version=result.prompt_version and model_metadata to mark_run_succeeded — extend the repo to also write finish_reason, latency_ms, usage from result.model_metadata.
Why: Section 8; executor currently leaves prompt_version NULL.
Verify: after a run, agent_runs.prompt_version is non-null, finish_reason/latency_ms/usage populated.
Phase 2 — Live Capability Smoke Test + Thinking Benchmark (Sections 7.2, 7.3)
T3.1 tests/live/__init__.py + tests/live/test_opencode_capability.py (NEW)
Marker: @pytest.mark.live (registered in pyproject.toml); skipped unless RUN_LIVE_DISCOVERY=1 AND OPENCODE_GO_API_KEY set. Synthetic tiny payload (a 2-line fake prompt, no resume, no real PII).
Asserts (Section 7.2 list): model accepted; response_format={"type":"json_object"} accepted; prompt requests JSON; JSON object returned; finish_reason captured; empty content recognized; whitespace-only recognized; truncated (finish_reason=="length") recognized; reasoning_content not in content/no leakage; usage safe; unsupported params not relied on; provider errors map; client closes cleanly.
Why: Section 7.2; closes "live capability NOT VERIFIED".
Verify: pytest tests/live -m live runs end-to-end with the key.
T3.2 scripts/live-discovery-eval.ps1 (NEW)
What: runs 15–25 synthetic cases (built in T13) against the real endpoint; captures valid-JSON rate, empty-truncation rate, schema-pass rate, semantic-pass rate, repair rate, median/p95 latency, input/output tokens, thinking enabled vs disabled. Dumps sanitized summaries to reports/live-discovery/<timestamp>.json (no raw outputs containing synthetic contact details).
Why: Section 27.
Verify: report file exists; numbers present; no raw PII.
T3.3 Thinking-vs-non-thinking benchmark decision
Run Profile A (thinking disabled + JSON) and Profile B (thinking enabled + JSON) over the same corpus. Only select Profile B if (Section 7.3): valid JSON always, acceptable latency, no reasoning leakage, better eval scores, acceptable empty/truncation rates. Persist the decision (which profile) in config/models.toml reasoning_effort value and document in README. If Profile A wins, default reasoning_effort="" stays.
Why: Section 7.3 explicit benchmark policy.
Verify: decision recorded with evidence in prompts/CHANGELOG.md and README.
Phase 3 — State-Machine Tightening (per your decision)
T4.1 src/oryxenai/agents/discovery/state.py (EDIT)
Changes:
- apply_source_edit (state.py:65): validate the transition (or define an explicit "any → INPUT_READY" allowance).
- apply_answer_edit (:77), apply_brief_edit (:86), apply_approval (:95), apply_needs_attention (:199): each call _validate_transition with a documented allowed-source set. Add the missing edges to _VALID_TRANSITIONS (:26-58) so the helpers can validate (e.g., APPROVED → INPUT_READY already exists; ensure edit/approve paths' source states are allowed).
- Keep approval's side effects (immutable snapshot) intact.
Why: T0.2 finding — these helpers skip validation; save_answers overrides status.
Verify: new tests assert invalid edit/approve/source-edit raises InvalidTransitionError.
T4.2 src/oryxenai/agents/discovery/service.py (EDIT)
Change: save_answers (:396-409) no longer overrides status unconditionally; it uses apply_answer_edit/apply_answers_in_progress and respects those helpers' validated status. Adjust the call sites (questions ready/answers/brief review/approved states) to use the helper output directly.
Verify: existing happy-path tests still pass; new test asserts a save_answers from a disallowed state raises.
T4.3 tests/unit/agents/discovery/test_state_machine.py (EDIT)
Add tests: invalid source-edit from BRIEF_RUNNING (must reject unless allowed), invalid approval from BRIEF_QUEUED, invalid brief edit from INPUT_READY.
Phase 4 — Modular Prompt Architecture v2 (Sections 9, 10, 11.1–11.8)
T5.1 Prompt module tree (NEW files)
Create:
src/oryxenai/agents/discovery/prompts/
  core_identity.md
  trust_boundary.md
  grounding_policy.md
  source_interpretation.md
  prepare_questions.md
  question_policy.md
  build_brief.md
  downstream_handoff_policy.md
  output_rules_call_a.md
  output_rules_call_b.md
  repair.md
  examples/
    call_a/  (6 golden + 3 anti)
    call_b/  (6 golden + 3 anti)
    anti_examples/
  CHANGELOG.md
- Delete the 4 old flat files (system.md, prepare_questions.md, build_brief.md, repair_output.md) — their content migrates into the modules above (Section 9 "adapt to existing conventions; avoid unnecessary fragmentation, but preserve clear logical modules" — I keep logical modules, not 30 micro-files).
- Assembly order (Section 9): core_identity → trust_boundary → grounding_policy → source_interpretation → operation-specific (prepare_questions OR build_brief) → question_policy (Call A only) → downstream_handoff_policy (Call B only) → output_rules_call_a OR output_rules_call_b → few-shot examples (≤2, tag-selected) → <source_packet trust="untrusted" encoding="json"> CDATA → final 1-line reminder.
- Static material before dynamic user data. Dynamic content never inserted mid-instructions.
Why: Sections 9, 10, 11.1–11.8.
Verify: test_prompt_assembly_order asserts static blocks precede source packet; packet is CDATA-wrapped.
T5.2 src/oryxenai/agents/discovery/prompt_builder.py (REWRITE)
Changes:
- Version constants → discovery.core.v2, discovery.call_a.v2, discovery.call_b.v2, discovery.repair.v2, discovery.examples.v2.
- build_instructions(operation, source_packet, config, output_language) loads modules in the stable order above; injects the JSON schema generated via DiscoveryAnalysisResult.model_json_schema() (Call A) or DiscoveryBrief.model_json_schema() (Call B) into output_rules_call_a/b — schema-first (Section 11.1).
- Few-shot selection: load examples/call_a/index.json (tag → file map); select ≤2 examples by matching scenario tags in the source packet (e.g., complete_profile, sparse_profile, conflict_heavy, multilingual, confidential, no_resume); include anti-examples for high-risk fields when the scenario warrants.
- Returns (system, full_task, version, manifest) where manifest is a dict of module_name → sha256[:16] for every module loaded — persisted in T1.7's model_metadata.
- build_repair_instructions: concrete "Correct only the listed validation failures. Preserve all valid data and provenance. Do not add professional facts. Do not invent source IDs. Do not change unrelated decisions. Return one complete JSON object." (Section 24).
- Long-context structure (Section 11.7): build an indexed source packet — source manifest + section manifest + source IDs + line hints + high-signal facts from deterministic preprocessing + compaction warnings + duplicate warnings + requested output language + product constraints. Final reminder after the packet, not buried.
- Stable-prefix (Section 11.8): static rules + schema + reusable examples form a stable prefix; session-specific resume/answers sit at the end. Cache metadata captured only if the provider returns it (Section 11.8 — do NOT claim caching is active without evidence).
Why: Sections 9–11.8, 24.
Verify: test_schema_drift (T5.5) pins prompt-declared fields to Pydantic schema; test_module_manifest asserts manifest stable across calls.
T5.3 Few-shot golden examples (12 files)
examples/call_a/*.json: complete_backend, sparse_student, conflict_heavy, multilingual_en_request, confidential_nda, no_resume_each. examples/call_b/*.json: the paired brief per scenario. Each is a fully-populated v2 object demonstrating evidence refs, concise questions, omission handling, sparse behavior, safe Auto, conflict handling, injection resistance (per Section 16/20 minimum richness).
Why: Section 11.2; replaces zero-example state.
Verify: test_examples_are_valid_v2 loads each, parses via DiscoveryAnalysisResult/DiscoveryBrief, asserts non-empty facts/questions/strategy.
T5.4 Contrastive anti-examples (Section 11.3)
examples/anti_examples/*.md: BAD "improved performance by 40%" (no metric in source) vs GOOD qualitative-only vs BEST omit+ask; BAD "greatest strengths?" vs GOOD "which capability should lead: API design, data systems, reliability, or another?". Used by selection only when the scenario is high-risk for that failure mode.
Verify: anti-examples contain the BAD/REASON/GOOD labels.
T5.6 prompts/CHANGELOG.md (NEW)
What changed (v1 → v2 module split, schema-first, examples, repair wording, long-context indexing), why (audit gaps), which fixtures exposed each weakness, metrics improved (filled post-T19), known limitations.
Why: Section 29.
Verify: file exists and references real fixture names.
Phase 5 — Call A Schema v2 (Sections 15, 16)
T6.1 src/oryxenai/agents/discovery/schemas.py (EDIT — DiscoveryAnalysisResult)
Replace the 9-field v1 shape with v2:
schema_version: int = 2, operation: str, source_assessment: SourceAssessment{overall_usability, resume_structure, detected_languages, requested_output_language, compacted, duplicate_content_detected, prompt_injection_detected, warnings[], ignored_content[]}, profile_overview: ProfileOverview{professional_summary, career_stage, primary_role_candidates[{label, supporting_fact_ids, confidence}], secondary_capability_candidates[], evidence_density}, normalized_profile: NormalizedProfessionalProfile (existing, kept), facts: list[FactCandidate] (reuse), conflicts (reuse), uncertainties: list[Uncertainty{id, category, summary, related_fact_ids, recommended_action}], questions (reuse, but whyItMatters field added), auto_decisions (reuse), omission_candidates (add reason: "unsupported"|"uncertain"|"confidential"|"off_topic"), readiness: Readiness{can_build_brief, recommended_question_count, blocking_conflict_ids, limitations[]}, quality_checks: QualityChecksA{all_supported_facts_have_evidence, factual_auto_answer_count, unsupported_metric_count}.
All extra="forbid". Bounded lists. schemaVersion==2 enforced.
Why: Section 15/16.
Verify: DiscoveryAnalysisResult.model_json_schema() valid; v1 sample (now obsolete) fails v2 parse.
T6.2 Update all imports/usages
agent.py, validators.py, service.py (assign_stable_analysis_ids), fake_client.py adapter path, worker handler, prompt builder — all updated to v2 field names.
Phase 6 — Call B Schema v2 (Sections 19, 20)
T7.1 src/oryxenai/agents/discovery/schemas.py (EDIT — DiscoveryBrief)
Replace the 19-field v1 shape with v2 conceptual groups (Section 19):
- schema_version=2, operation.
- executive_summary{strategy_summary, portfolio_scope, readiness, main_opportunity, main_limitation}.
- identity_and_goal{primary_target_role{label, basis_fact_ids, decision_source, confidence}, secondary_strengths[{label, basis_fact_ids}], audiences[{label, priority}], portfolio_goal{summary, basis}, career_stage{value, confidence, note}} — no invented seniority (Section 19.2).
- positioning_strategy{positioning_direction, differentiators[{statement, basis_fact_ids, confidence}], evidence_strengths[], credibility_boundaries[]} — every differentiator references fact IDs (Section 19.3).
- content_strategy{recommended_section_priority[{section, priority, purpose}], content_density{recommendation, reason}, featured_projects[{project_id, priority, selection_reason, target_role_relevance, supported_project_scope, supported_personal_contribution[{summary, basis_fact_ids}], narrative_focus[], recommended_content_depth, evidence_to_preserve[], unknowns_to_omit[], confidentiality{level, restrictions[]}}], experience_focus[], capability_clusters[{label, items[], basis_fact_ids}], items_to_omit[{item, reason}]}.
- presentation_direction{tone{value, source, explanation}, voice_rules[], theme_preference{value, source, guidance}, motion_preference{value, source, guidance}, visual_density, technical_editorial_balance, patterns_to_avoid[]}.
- cta_and_contact{primary_cta_intent, secondary_cta_intent, publishable_contact_choices[{kind, source, fact_id}], private_or_omitted_contact[{kind, reason}]}.
- confidentiality_and_omissions{rules[{scope, rule, applies_to, fact_ids}], deliberate_omissions[]}.
- unresolved_items[{id, severity, summary, downstream_behavior}] — material conflicts preserved (Section 19).
- claim_policy{must_use_fact_ids[], allowed_user_asserted_fact_ids[], requires_careful_wording[{fact_id, guidance}], must_not_claim[]}.
- downstream_handoff{content_architect{central_story, content_hierarchy[], evidence_to_preserve[], writing_constraints[]}, visual_design_director{desired_impression, content_implications[], presentation_constraints[]}, universal_constraints[]} — no final copy/components/layout/code (Sections 19.8, 1).
- decision_log[{decision, source, related_fact_ids}].
- quality_checks{all_factual_strategies_reference_facts, unsupported_metrics_included, skipped_facts_converted_to_claims, factual_auto_decisions_included, unresolved_material_conflicts_preserved, final_portfolio_copy_included}.
All extra="forbid", bounded, schemaVersion==2.
Why: Section 19/20.
Verify: v2 parse; v1 sample fails; no hero/about/component/layout/code fields exist.
T7.2 Frontend mapping to simple sections (Section 25.4)
Files: web/templates/index.html, web/static/app.js (EDIT).
Keep 11 visible sections (target role/goal, audience, positioning, featured work, experience emphasis, capabilities, content priorities, tone/presentation, CTA/contact, confidentiality/omissions, unresolved items). Map v2 detail to these. Decision log + downstream metadata in a collapsible "developer mode" panel only. No raw JSON as the primary review experience.
Verify: JS renderDiscoveryBrief() reads v2 fields without crashing; textContent only; discoveryBriefEdits() serializes back to v2 with source="user_edit".
Phase 7 — Stricter Semantic Validators (Sections 23.1, 23.2, 23.3)
T8.1 src/oryxenai/agents/discovery/validators.py (REWRITE — Call A, Section 23.1)
Add all 29 Call A checks: supported schema version, no extra fields (Pydantic), unique fact IDs, unique question IDs, valid source IDs, evidence excerpt locatability, supported facts have evidence, user_asserted facts point to a user source, presentation defaults don't support professional facts, ≤8 questions, no duplicate/near-duplicate questions, no question already answered by high-confidence source evidence, Auto forbidden for factual categories, options match question type, conflict refs exist, fact refs exist, no invented email/phone/URL, no unsupported metric, no unsupported employment/education, no hidden-reasoning fields, output language matches request, proper nouns preserved, evidence excerpts short/bounded, injection text not represented as policy.
Verify: parametrized tests per check.
T8.2 validators.py (REWRITE — Call B, Section 23.2)
Add all 24 Call B checks: every fact reference exists; primary role supported or user-selected; every differentiator references supporting facts; featured projects exist; project personal contributions supported or user-asserted; team scope vs personal contribution separate; no skipped answer became a fact; no factual Auto decision; confidential info not recommended for publication; private contact not public by default; no unsupported metrics/seniority/leadership; unresolved material conflicts preserved; deliberate omissions not reintroduced; brief has enough strategic detail for the evidence; sparse profiles don't get filler; no final hero/about/project copy; no component/layout/code; language correct; downstream constraints present; decision log consistent.
Verify: parametrized tests per check.
T8.3 Detail-adequacy checks (Section 23.3)
Two branches: "dense profile" requires positioning direction + ≥1 differentiator + credibility boundaries + content priority + per-project (selection reason, evidence refs, unknowns or explicit empty, content-depth) + content-density recommendation + claim policy + downstream handoff + omissions + CTA/contact + unresolved list. "Sparse profile" permits fewer differentiators, requires explicit limitations, recommends shorter portfolio, never synthesizes filler. Selectivity by profile_overview.evidence_density + readiness.can_build_brief.
Verify: dense fixture passes; sparse fixture does NOT get filler flagged.
T8.4 Agent enforces, not just reports (closes T0.2 gap)
agent.py (EDIT): both Call A and Call B now enforce — on not validation.is_valid, attempt one repair (Call A gains repair parity); if repair still invalid, return status="failed" with MODEL_SEMANTICALLY_INVALID (NOT return the invalid output with validation.is_valid:false). The agent no longer "logs and returns anyway".
Verify: test asserts an invalid Call A returns status="failed", not a usable analysis.
Phase 8 — Repair Behavior (Section 24)
T9.1 Repair instructions (T5.2 already covered) + attempt policy enforcement
agent.py: _attempt_repair for BOTH operations. Repair payload includes original_output, validation_errors (exact list), valid_source_ids, valid_fact_ids, current_output_schema, operation_name. One attempt only (T1.5 budget). Repair failure → MODEL_OUTPUT_INVALID.
Verify: test runs a perpetually-invalid brief through the agent; asserts exactly one repair call (fake_client.requests count); final status "failed".
Phase 9 — Sample-Output Overhaul (Section 21)
T10.1 Rewrite the 2 existing samples to v2
Files: samples/call_a_normal_output.json, samples/call_b_normal_output.json (REWRITE per your decision). Full v2 shape, non-empty featured projects, real selection reasons, evidence refs, unknowns, downstream handoff, decision log, quality checks — human-readable as a quality reference (Section 21 final paragraph).
Verify: FakeDiscoveryModelClient loads + parses them to v2; happy-path tests green.
T10.2 36 behavioral golden scenarios
tests/fixtures/discovery/<scenario>/{input.json, expected_call_a.json, answers.json, expected_call_b.json, assertions.yaml} for the 36 listed in Section 21 (list reproduced in my plan summary above — complete_backend…Unicode/RTL/emoji/ZWJ).
assertions.yaml focuses on facts present/absent, provenance validity, conflicts detected, questions required/prohibited, Auto rules, omissions, confidentiality, downstream detail, language, readiness — not exact prose. At least several fully populated and human-readable (Section 21).
Why: Section 21; closes "samples are inert/shape-only".
Verify: every scenario dir has all 5 files; several full-populated; assertions.yaml parses.
T10.3 Wire the previously-inert 6 fixtures
Load complete_backend_engineer, sparse_student_profile, conflicting_dates, nda_protected, no_metrics, injection_resume in T12's parametrized tests (their expected flags become executable assertions).
Why: closes the largest single test gap (T0.2 #1).
Verify: tests reference these files by name (grep non-zero).
Phase 10 — Evaluation Corpus & Metrics (Section 26)
T11.1 tests/eval/__init__.py + tests/eval/test_discovery_eval.py (NEW)
Deterministic metrics (Section 26.1, must be zero on corpus): unsupported factual-claim count, facts without valid evidence, invalid evidence refs, conflicts missed, factual Auto decisions, wrong-language outputs, private-contact publication, confidentiality violations, unsupported metrics/seniority/leadership, stale result applied, JSON parse failures, semantic-repair rate, empty-output rate, truncation rate.
Strategy rubric (Section 26.2, 12 dims): role clarity, audience clarity, positioning usefulness, evidence use, project-selection quality, personal-contribution separation, content prioritization, omission quality, confidentiality handling, downstream usefulness, appropriate scope, non-genericity. Deterministic where possible; a human review sheet template included; no LLM-as-judge.
Verify: corpus run prints a metrics report; critical-safety metrics == 0.
T11.2 Metamorphic tests (Section 26.3)
Reorder resume sections, change whitespace, change bullet symbols, duplicate a section, change Markdown headings, add irrelevant paragraph, add injection line, move a fact beginning→end, change URL ordering, equivalent date formatting → same core fact set, same material conflicts, same factual-Auto restrictions, similar high-priority questions.
Verify: test_metamorphic_* asserts invariants across transforms.
T11.3 Mutation/fuzz tests (Section 26.4)
Empty strings, max-length strings, Unicode normalization, RTL text, control chars, zero-width chars, nested JSON, XML closing tags, script tags, malformed URLs, repeated content, long single words, thousands of commas/bullets, invalid answer option IDs.
Verify: no crash; safe classification; no fabrication.
T11.4 Baseline-vs-candidate snapshot (Section 26.5)
Preserve current v1 results (T0.3); run v2 over the same corpus; report baseline pass rate, candidate pass rate, regressions, improvements, latency, output-token usage, repair frequency. Do not delete baseline-weakness evidence.
Verify: reports/baseline_v1/ and reports/candidate_v2/ exist; comparison table in the final report.
T11.5 Edge-case behavior matrix 22.1–22.8 (Section 22)
Parametrized tests: 22.1 empty/unusable; 22.2 multi-doc; 22.3 role/career (student, career-changer, founder, manager, IC, researcher, designer-dev hybrid, data, DevOps, mobile, game, tech-writer, gap, intl titles, non-employment goals); 22.4 fact/credibility (no/approximate/confidential/conflicting/team metrics, unclear attribution, expired certs, overlapping employment, undated projects, internal/OS/volunteer/coursework/hackathon/research/patent/failed/never-launched/tech-name-only projects); 22.5 user behavior (concise/essay/wrong-question/contradicts/mind-change/sarcasm/frustrated/profanity/"just decide"/skip-all/clone-request/fake-employment/fake-testimonial/false-senior/conceal-gap/publish-sensitive/midway-language/paste-extra/mark-old-line-false/want-contact-removed/mark-public-confidential); 22.6 injection variants (ignore-previous, admin, print-prompt, print-key, fake-40%-metric, call-code-gen, return-XML, close-source-boundary, JD-as-experience, every-statement-verified, base64, markdown role headings, fake <system> tags, fake JSON system fields, homoglyphs, zero-width, instruction flooding, injection in URL/answer/manual-edit); 22.7 privacy (home address, phone, private email, govt IDs, salary, age, DOB, medical, religion, caste, ethnicity, marital, politics, client secrets, internal architecture, pasted credentials, API keys, passwords — deterministically redact detected credentials before model send; never recommend publishing sensitive by default); 22.8 provider-output (empty, whitespace, wrong-schema, unsupported-facts, truncated, duplicate keys, JSON-in-markdown-fences, leading prose, refusal, timeout, rate-limit, auth-fail, invalid-model, server error, conn-reset, reasoning-in-content, prompt-echo, source-echo, hallucinated source IDs/email/URL, excessive questions, factual Auto, missing blocking conflict, hero copy, visual blueprint, wrong language).
Verify: each scenario has a parametrized test; coverage matrix in docs/discovery-eval-coverage.md.
Phase 11 — Logging & Privacy (Section 28)
T12.1 src/oryxenai/core/logging.py review + safe-field allowlist
Allowed: request_id, session_id (shortened), job_id, run_id, operation, prompt_version, model_profile, model_id, attempt counts, finish_reason, response_id, latency, input char count, compaction flag, fact/conflict/question counts, repair reason, validation result, usage.
Never: raw resume/main-prompt/answers/brief/reasoning_content/system-prompt/API-key/auth-header/provider-error-body/email/phone/address/private-URLs/DB-URL.
Verify: grep logs for forbidden substrings on a synthetic run → empty (except sanitized short IDs).
T12.2 Replace OpenAI store=false wording with OpenCode-accurate policy (Section 28 final paragraph)
README + prompts/CHANGELOG.md: state what's actually sent (store=false only when capability supported) and that OpenCode retention depends partly on third-party providers — do not carry OpenAI-specific privacy claims without evidence.
Verify: README privacy section wording matches code behavior.
Phase 12 — Frontend Verification (Section 25)
T13.1 tests/integration/test_discovery_flow.py (NEW) and tests/api/test_discovery_flow.py (NEW)
Full httpx.AsyncClient flow: create session → PUT intake → POST questions → worker (FakeDiscoveryModelClient patched) → GET questions → PUT answers → POST brief → worker → PATCH brief → POST approve → assert immutable approved_brief snapshot; assert no later-agent job enqueued (assert no row with agent_key IN ("content_architect","visual_design_director","code_generator") exists).
Why: closes the HTTP-layer gap (T0.2 #15).
Verify: test passes end-to-end.
T13.2 Conflict / idempotency / stale HTTP tests
- Two-tab 409 (stale expected_revision → HTTP 409 with DISCOVERY_REVISION_CONFLICT).
- Duplicate NEXT idempotent (POST /approve twice → 200 both, one snapshot).
- Stale question_version → DISCOVERY_QUESTIONS_STALE.
- Stale approval invalidated by post-approval edit → DISCOVERY_APPROVAL_INVALIDATED.
- Factual question never shows "Choose for me" in the response shape (no allows_auto on factual).
- Post-approval edit invalidates approval.
Verify: each asserts HTTP status + body code.
T13.3 Frontend behavior (Section 25)
Intake refresh-safe (sessionStorage restoration), one-at-a-time, Auto labels visible, brief edits get user_edit provenance, approval immutable/idempotent, NEXT stops.
Verify: via Playwright-free DOM assertion on the rendered template + JS unit where feasible (the repo uses vanilla JS; keep that).
Phase 13 — Agent Run Metadata Flow
T14.1 Forward all metadata end-to-end
Already covered in T1.7: executor + worker handler write prompt_version, model_metadata, finish_reason, latency_ms, usage, attempt_budget, input_hash (= compute_source_hash of the snapshotted input), output_hash (= brief_hash or analysis hash).
Verify: post-run DB inspection shows non-null values; unit test on agent_runs row.
Phase 14 — Documentation (Section 29)
T15.1 src/oryxenai/agents/discovery/README.md (REWRITE)
Full Section 29 list: responsibilities, non-responsibilities, Call A algorithm, Call B algorithm, prompt module architecture, prompt versions, DeepSeek/OpenCode adapter behavior, JSON-mode requirements, thinking-mode policy (with the T3.3 decision + evidence), capability probe, retry budget, evidence model, question-selection rubric, Auto policy, brief depth, downstream handoff, sample corpus, evaluation metrics, live-test procedure, privacy behavior, failure behavior, state transitions, approval behavior.
T15.2 prompts/CHANGELOG.md (already T5.6).
T15.3 PLANforDiscoveryAgent.md — append Section 31 final report (A–I) at T19.
Verify: README covers every Section-29 bullet.
Phase 15 — Acceptance Verification (Section 30)
T16.1 Full command suite
Run and record exact counts/skips for:
uv sync --frozen; uv lock --check; uv run ruff format --check .; uv run ruff check .; uv run mypy src; uv run pytest --collect-only -q; uv run pytest (default, no live); uv run pytest -m live (separate, with key); uv run alembic upgrade head; uv run alembic downgrade -1; uv run alembic upgrade head; docker compose config; docker compose up -d --build smoke (app healthcheck green, worker heartbeat present); fake-client e2e (the T13 flow); live OpenCode capability test (T3 numbers).
T16.2 Docker smoke (Section 30)
docker compose config (parse) → docker compose up -d --build → wait for app healthcheck /health/live → assert worker heartbeat row present → docker compose down.
Verify: all 4 services healthy.
T16.3 Section-30 acceptance checklist
Run every Section-30 bullet item; mark each VERIFIED/PARTIAL/FAILED with evidence. The Repository-verification, Prompt-architecture, Output-quality, Provider-behavior, Evaluation, Frontend-and-state, and Engineering-quality subsections.
Phase 16 — Final Report (Section 31, deliverables A–I)
T17.1 Section 31.A — Independent verification result
All 54 original DoD + Section-30 criteria: criterion | verified status | evidence | gap | change made | final status. Explicit "54/54 reproduced? — YES/NO" with corrected count.
T17.2 Section 31.B — Report discrepancies
Every mismatch (test count, fixture count, endpoint count, state count, migration, Docker, provider, sample quality, prompt quality, live verification) I found, with the v1-vs-v2 resolution.
T17.3 Section 31.C — Prompt-system changes
Files changed (old → new), versions, module architecture, example-selection policy, repair policy, long-context strategy, injection defenses.
T17.4 Section 31.D — Schema and output changes
Call A/B changes, frontend mapping, migration impact (0004), backward compatibility (v1→v2 replaced), sample-output improvements.
T17.5 Section 31.E — Evaluation results
Scenario count, baseline results (v1), candidate results (v2), critical violations (must be 0), regressions, improvements, repair rate, live-model results (real numbers from T3.2).
T17.6 Section 31.F — Provider verification
Mocked adapter verified ✓; live OpenCode Go endpoint verified with real numbers (valid-JSON rate, empty/truncation rate, latency, leakage) OR NOT VERIFIED (honest if the endpoint fails); thinking mode tested; reasoning leakage test; empty/truncation tests. Do NOT blur mocked and live.
T17.7 Section 31.G — Commands and outcomes
Exact commands + exact counts/skips (pass/skip/fail/xfailed), distribution, alembic round-trip, docker smoke, fake-client e2e, live-provider evaluation.
T17.8 Section 31.H — Remaining limitations
Only actual ones: e.g. live latency/p95 confidence limited by sample size; OpenCode third-party retention policy needs separate confirmation; developer frontend remains a harness; no later agents implemented.
T17.9 Section 31.I — Exact next step
"Run privacy-safe human review of several realistic Discovery sessions, then refine the Discovery Agent before beginning Content Architect." Do not begin another agent.
Execution order (dependency-respecting)
T0.1 commit v1 ─ T0.2 matrix ─ T0.3 baseline
   │
   ├─→ T1 capabilities/errors/attempt_policy/migration0004/executor ─┐
   ├─→ T3 live smoke + thinking benchmark (uses T1 adapter) ────────┤
   ├─→ T4 state-machine tightening ─────────────────────────────────┤
   ├─→ T5 prompts v2 modules + examples + CHANGELOG ────────────────┤
   ├─→ T6 Call A v2 schema + usages ─→ T7 Call B v2 schema + frontend│
   │                                                               │
   └──→ T8 validators v2 + agent enforce ─→ T9 repair behavior ──────┤
                                       │                           │
                                       ├─→ T10 samples v2 + 36 ──→ T11 eval/metrics/metamorphic/fuzz/baseline ─→ T16.2 edge matrix
                                       │                           │
                                       ├─→ T12 logging/privacy ───┤
                                       ├─→ T13 HTTP tests ──────── ┤
                                       ├─→ T14 metadata flow ───── ┤
                                       └─→ T15 docs ───────────────┴─→ T16 acceptance ─→ T17 final report
Verification gates (must pass before finishing)
 1. uv run ruff format --check . && uv run ruff check . && uv run mypy src clean.
 2. uv run pytest -q — all green; zero skipped-required; live tests separate under -m live.
 3. Critical-safety metrics on the corpus = 0 (unsupported claims, factual Auto, private-contact publication, reasoning leakage, stale-results-overwrite).
 4. alembic upgrade head→downgrade -1→upgrade head round-trip OK at 0004.
 5. docker compose up -d --build smoke: app + worker + postgres + migrate healthy; worker heartbeat row present; app health/live 200.
 6. Full HTTP flow (T13.1) green; no later-agent job created.
 7. Live OpenCode smoke green (or honestly marked NOT VERIFIED if the endpoint refuses).
 8. State-machine invalid-transition tests green.
 9. Schema-drift tests green (prompt fields == Pydantic schema fields); v1 samples fail v2 parse; v2 samples parse.
10. git status shows only intended changes (no format-only churn on untargeted files).
That's the full plan. It covers all 31 sections of the assignment, respects every locked-in decision, and the verification gates ensure the final report's "54/54" claim will this time be backed by real evidence (or honestly marked as exceptions). Ready to execute on your clearance.