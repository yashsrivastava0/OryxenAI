# OryxenAI API Usage, Cache, Retry, and Multi-Provider Remediation Plan

**Document type:** research and implementation guidance

**Evidence snapshot:** OpenAI Platform usage checked on 2026-09-06; local OryxenAI database and source checked on the same investigation

**Audience:** OryxenAI maintainers and coding agents that will diagnose or change model routing, caching, retries, workers, or provider adapters

**Status:** Actionable findings. This document is not a substitute for rechecking the live Platform dashboard and current repository configuration before a production change.

## 1. Executive conclusion

OryxenAI's recent API usage is materially higher than expected for a small prepaid balance. The primary cost pattern is not OpenAI Batch API usage and not expensive cache reads. It is a combination of:

- large Code Generator prompts and many Code Generator stages;
- repeated source-repair, integration-review, planner, and route-generation attempts;
- prompt-cache writes that are rarely reused;
- a retry and stale-worker pattern that is bounded in some code paths but not consistently bounded across every layer;
- a large queue of Code Generator jobs that can create more spend if a worker is restarted;
- insufficient provider-call telemetry to reconcile every Platform request with a durable application operation.

The immediate priority is to prevent the queued work from draining without review. The next priority is to make every request attributable and to enforce one global retry budget per user operation. Cache improvements come after the request graph is controlled; otherwise caching can make repeated expensive work cheaper per token while still allowing too many total calls.

The future multi-provider design must preserve these controls. Adding another provider or model must not create a second hidden retry layer, a second untracked fallback request, a new cache namespace that is mistaken for a cache hit, or a cost estimator that uses a stale rate card.

## 2. Live usage evidence

The following values were read from the authenticated OpenAI Platform dashboard. They are observations for the investigation window, not hardcoded application policy.

| Measurement | Observed value | Interpretation |
| --- | ---: | --- |
| Credit grant | $10.00 | The credit-grants page showed a $10 grant received on Sep 4, 2026. |
| Available balance | $4.63 | Approximately 46.3% of the grant remained at the time of checking. |
| Credit consumed | $5.37 | This matched the project usage amount shown against the $100 monthly spend limit. |
| Sep 5–Sep 6 usage window | $4.68 | Almost all recent spend occurred on Sep 5 in the selected UTC window. |
| Model requests | 407 | Requests were concentrated in Responses and Chat Completions. |
| Input tokens | 17,722,496 | Average input was approximately 43,544 tokens per request. |
| Output tokens | 1,357,393 | Average output was approximately 3,337 tokens per request. |
| Model | `gpt-5.6-luna` | Only one model was visible in the selected dashboard period. Recheck routing before relying on this value. |
| Project | `Default project` | Only one project was visible in the dashboard selector. |
| API key label | `yash- prod- res` | Only one key label was visible; the plaintext secret was never read or displayed. |

The usage category breakdown was approximately:

| Usage category | Spend | Share of the $4.68 window |
| --- | ---: | ---: |
| Cache writes | $3.424 | 73.2% |
| Output | $1.230 | 26.3% |
| Cached input reads | $0.012 | 0.3% |
| Ordinary input | $0.011 | 0.2% |

The token breakdown was:

- Cache-write tokens: approximately **16,907,990**.
- Cached input tokens: **711,854**.
- Uncached input tokens: **102,652**.
- Cache-read ratio: approximately **4%**.
- Cache reads per write: approximately **0.04x**.

This means the application was creating roughly 16.9 million cache-write tokens while reusing only about 0.7 million cached tokens. The cache is active, but it is not currently amortizing the prompt volume effectively.

The Platform dashboard uses UTC-oriented date reporting and separates usage from credit-grant and billing records. The $11.80 paid invoice should not be treated as the API credit balance; the credit-grants page is the source for the available prepaid credit. Use the [OpenAI Platform usage reference](https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object) and the [billing overview](https://platform.openai.com/settings/organization/billing/overview) when rechecking the account.

At the observed $4.68-per-day pace, the remaining balance could last approximately one day. This estimate is unsafe if the queued Code Generator work is resumed, because one active generation can issue many model calls.

## 3. Local OryxenAI evidence

### 3.1 Code Generator activity is much larger than the pre-code estimate

The earlier research document focuses mainly on the pre-code stages and describes a normal pre-code flow of roughly 5–9 model calls. That is not a complete description of the current live workload.

The local database contained the following Code Generator activity since Sep 4:

- 42 Code Generator runs were present.
- 23 runs were created on Sep 5.
- 15 of the Sep 5 runs were in `needs_attention` at the time of inspection.
- Sep 5 error events included:
  - 5 `PLANNER_OUTPUT_INVALID` failures;
  - 4 `SOURCE_REPAIR_EXHAUSTED` failures;
  - 4 `INTEGRATION_REVIEW_UNRESOLVED` failures;
  - 1 `INTEGRATION_POLISH_INCOMPLETE` failure;
  - 1 `QUALITY_SOURCE_STALE` failure.
- A later Sep 6 event included `QUALITY_REALIZATION_STALE`.
- The persisted final Code Generator receipts accounted for approximately 273 model-call receipts in the matching investigation period, before accounting for smaller pre-code traffic and calls that failed before a final receipt was persisted.

The dashboard showed 407 requests. The difference between the dashboard count and the final receipts is a reconciliation warning. The most likely contributors are failed first attempts, planner/schema correction attempts, model calls from stale or replayed workers, and requests that are not represented in the final successful receipt. It also means that the application cannot currently prove which exact operation produced every billed request.

### 3.2 The queue contains an immediate spend risk

At the time of inspection, 55 Code Generator jobs were queued and due for execution. The most recent jobs included planning, acquisition, generation, and verification stages. The most recent worker heartbeat was stale, so the queue was not necessarily draining at that moment; restarting a worker could cause the backlog to execute.

One historical `code_generator.v5.generate` row showed `attempt = 5` while `max_attempts = 3`. This does not prove that the provider was called exactly five times, because the job attempt counter can also reflect stale-lease recovery. It does prove that the durable job lifecycle can re-claim a job beyond the configured normal retry budget. That is an unusual pattern and must be fixed or explicitly explained before more workers are started.

### 3.3 The retry budget exists at several independent layers

OryxenAI currently has multiple mechanisms that can repeat work:

1. The OpenAI-compatible SDK can retry transport failures according to the model profile's `max_retries`.
2. The provider adapter can make a second structured-output request when a provider rejects the strict schema.
3. The planner operation has its own validation loop with up to three attempts.
4. Creative direction and generation validation have their own correction loops.
5. The durable worker can retry a failed job up to the worker retry limit.
6. A stale lease can cause a running job to be reclaimed.
7. The Code Generator has request rounds, source repair rounds, and integration-polish rounds.
8. A caller can submit a new stage attempt after `needs_attention`.

Each layer may look bounded by itself, while their product becomes large. For example, a planner call that has a schema correction, is inside a requeued job, and is later manually restarted can produce several billable requests even though no single loop is infinite.

### 3.4 Current configured limits are too permissive for development billing

The checked-in configuration currently includes these relevant values:

- Worker retry budget: `max_attempts = 3`, described as one initial attempt plus two retries.
- Planner validation budget: three model attempts.
- Code Generator request rounds: up to four.
- Code Generator repair rounds per unit: up to three.
- Code Generator total repair rounds: up to six.
- Code Generator integration-polish rounds: up to five.
- Code Generator profiles: some have SDK `max_retries = 1`.

The settings are visible in [`config/app.toml`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/config/app.toml>) and [`config/models.toml`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/config/models.toml>). These values are not necessarily wrong for a production-quality generation workflow, but they are unsafe as a default while the cost ledger and stale-worker behavior are unresolved.

## 4. What normal behavior should look like

For one user-triggered portfolio operation, normal behavior should satisfy all of the following:

- The operation receives a durable operation ID and a maximum request budget before the first model call.
- Every provider request has a stable internal call ID, operation ID, stage, attempt number, profile, provider, model, prompt version, schema version, and parent job ID.
- A retry is only made for a classified retryable condition.
- A validation correction is counted as a provider request, not hidden inside a helper.
- A fallback to another provider or model is counted as a provider request and has its own budget.
- A stale lease never starts a second owner while the first owner may still be running.
- A job cannot be claimed when its durable attempt count has reached its maximum.
- A terminal failure stops the stage and records a clear next action instead of automatically restarting the whole workflow.
- A cache hit and a cache write are recorded separately.
- The final internal cost estimate can be compared with the Platform usage window using the same UTC boundaries.
- Repeated identical requests reuse the result cache or provider prompt cache; unique user revisions are not expected to be cache hits.
- A user-facing operation fails closed when it reaches its request, token, time, or cost budget.

The important distinction is:

```text
one normal attempt
  -> one provider request

one bounded correction
  -> at most one additional provider request

one job retry
  -> at most one additional attempt of the stage

workflow restart
  -> explicit, separately budgeted, and never automatic by default
```

For cost-controlled development, “maximum two attempts” should mean **two total provider attempts: one initial request plus one retry**, not two retries after the initial request.

## 5. Retry and failure policy to adopt

### 5.1 Recommended global policy

Use a single policy document and a single request-budget object shared by every provider adapter and every agent stage.

Recommended development defaults:

| Layer | Recommended maximum | Notes |
| --- | ---: | --- |
| Provider SDK transport retries | 0 by default | Allow 1 only for an explicitly classified connection failure, never for invalid input or provider quota errors. |
| Structured-output correction | 1 correction | Two total provider requests for the operation. Persist both outcomes. |
| Planner attempts | 2 total | The current three-attempt planner loop should be reduced while cost debugging is active. |
| Creative-direction attempts | 2 total | This is already close to the desired policy. |
| Route-generation validation attempts | 2 total | One initial response and one correction response. |
| Durable job attempts | 2 total | One initial job attempt and one retry. |
| Request/resource rounds | 2 total | A model request round must consume the same operation budget. |
| Repair rounds per unit | 1 by default | A second repair requires explicit policy or a remaining cost budget. |
| Total repair rounds per run | 2 | Stop with diagnostics after the ceiling. |
| Integration-polish rounds | 2 | Stop and report unresolved findings after the ceiling. |
| Whole-workflow automatic restart | 0 | Require an explicit caller action. |

The user-requested “max 2” policy should be implemented consistently as a **total-attempt ceiling**, with the initial call included. Do not set every integer named `max_attempts` to two without first identifying whether it counts provider calls, job claims, workflow restarts, repair rounds, or route work units.

### 5.2 Error classification

Only the following should normally be retryable, and each should consume one retry budget unit:

- transient network connection failure;
- provider timeout where the request may not have been accepted, with idempotency and duplicate-risk handling;
- temporary provider overload or rate limit, if the response explicitly indicates retryability;
- stale database lease recovery when there is evidence that the original owner is no longer active.

The following should normally be terminal for the current stage:

- invalid API credentials;
- exhausted prepaid credit or project spend limit;
- invalid model or unsupported capability;
- invalid user input;
- repeated structured-output validation failure after the one correction;
- a deterministic source or schema contract violation;
- a quality failure after the repair ceiling;
- authorization or ownership failure;
- a missing or stale immutable input snapshot.

A failed request that returned a provider response can still be billable. The failure classifier must therefore record usage whenever the provider returned usage metadata, even when the output is rejected locally.

### 5.3 Prevent retry multiplication

The code should enforce one hierarchy:

```text
operation budget
  -> stage budget
      -> provider request budget
          -> one optional transport retry
```

The SDK, provider adapter, agent operation, job worker, and caller must not each independently decide to retry the same failure. The lowest layer should classify the error and return it upward; the highest layer with an available budget should decide whether to retry.

For every request, include:

- `operation_id`;
- `stage`;
- `provider_profile`;
- `provider`;
- `model`;
- `request_attempt`;
- `job_attempt`;
- `workflow_attempt`;
- `retry_reason`;
- `parent_request_id` when correcting or retrying;
- `idempotency_key`;
- `client_request_id` sent to the provider;
- provider response ID when available;
- token and cache usage;
- whether the call was a normal request, correction, fallback, repair, or replay.

If a call cannot be recorded, the operation should fail closed rather than continuing with unobservable spend.

## 6. Queue, lease, and worker remediation

The `attempt = 5` and `max_attempts = 3` observation must be treated as a queue-integrity issue, even if the cause is stale recovery rather than ordinary retry logic.

### Required changes

1. Add a database-level or repository-level guard so `claim_due` cannot claim a queued job whose `attempt >= max_attempts`.
2. Add the same guard to stale-job recovery. A stale job at the retry ceiling should become terminal or `needs_attention`, not be re-claimed.
3. Record a `lease_recovery` event with the old worker ID, old lease timestamp, new worker ID, attempt number, and reason.
4. Ensure the heartbeat interval is comfortably shorter than the lease duration for every long-running Code Generator stage.
5. Ensure a worker cannot recover a job while another process still owns a valid lease.
6. Make the job's lease token mandatory in completion and failure updates, which prevents an old worker from completing a job after a newer worker has reclaimed it.
7. Add a startup safety gate: if the due queue contains more than the configured development threshold, require an explicit operator confirmation or run only a single diagnostic job.
8. Add a queue-drain mode that processes no model jobs until the operator reviews the queue.
9. Do not automatically enqueue successor stages after an error unless the stage has remaining budget and the error is explicitly retryable.
10. Preserve all queued jobs for inspection; do not delete or reset the backlog as a cost fix without a documented decision.

### Immediate operational recommendation

Until the queue and lease behavior are corrected:

- do not restart the worker against the existing 55-job backlog;
- inspect each queued Code Generator job's portfolio/run ID, stage, age, and idempotency key;
- cancel or quarantine only the jobs that are confirmed obsolete through the normal application workflow;
- run one small privacy-safe generation after the queue is controlled;
- verify the Platform request count and spend before enabling broader generation.

## 7. Cache strategy: what to keep and what to change

OryxenAI has two different kinds of caching and they must not be treated as the same feature.

### 7.1 Durable result cache

The local `StructuredResultCache` stores a completed structured result keyed by the agent, operation, full prompt material, schema, profile fingerprint, and input payload fingerprint.

This is an exact-result cache. It is safe for deterministic replays and identical requests, but it naturally has low reuse when the user changes answers, a revision, a portfolio snapshot, or a generation ID. That is expected behavior, not a cache failure.

Recommended rules:

- Keep the full input fingerprint in the durable result-cache key.
- Include tenant, owner, session, approved-snapshot hash, schema version, prompt version, provider profile, and model family when the output is user-specific or sensitive.
- Never share a user-specific completed result across users merely because the prompt text looks similar.
- Store the cache outcome as `hit`, `miss`, `lease_wait`, `write`, `expired`, `invalidated`, or `error`.
- Count a result-cache hit as zero provider requests and record the avoided request explicitly.
- Use a short development TTL until the prompt/schema contract is stable.
- Invalidate results when the prompt manifest, schema version, model profile, or policy version changes.

The local database showed only a small number of exact result-cache hits. That cache is working for identical operations, but it cannot explain the Platform-wide prompt-cache numbers and cannot by itself stop unique Code Generator runs from spending money.

### 7.2 Provider prompt cache

Provider prompt caching reuses an eligible prefix of a later request. It is not a completed-answer cache. The model still runs for each request, and dynamic input and output tokens are still processed.

OpenAI guidance recommends putting stable content first, dynamic user-specific content last, using a consistent `prompt_cache_key` for repeated common prefixes, and tracking cached input tokens. See the [official OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5).

The current 4% hit rate indicates that the stable prefix is not being reused often enough. The most likely causes are:

- the cache key changes between generation runs;
- large dynamic context appears before the cache breakpoint;
- prompt, schema, or model profile fingerprints change on every retry;
- retries rebuild the prefix with a new request-specific value;
- provider or model failover changes the cache namespace;
- the cache TTL is shorter than the time between repeated requests;
- different agents use different prompt manifests and therefore cannot share a prefix;
- a failed request creates a new write but the next request changes enough content that it cannot read it.

### 7.3 Code Generator cache-key problem

The Code Generator currently passes a cache key shaped like:

```text
codegen:{generation_id}:{role_profile}
```

Because `generation_id` is specific to a generation, every new generation creates a new prompt-cache namespace. This is appropriate for isolating some run-specific context, but it is a poor key for a stable system prompt, schema, and role contract that should be reused across runs.

Use two conceptual layers instead:

```text
stable prefix key:
  provider + model + profile + operation + prompt_version + schema_version

user/run partition:
  tenant or approved snapshot boundary, when required for privacy

dynamic request body:
  generation ID, route content, diagnostics, files, user revisions
```

The dynamic run information should appear after the stable cache breakpoint. Do not put a unique generation ID in the stable prefix unless the provider's cache semantics or the privacy model explicitly require it. If the provider cannot safely share a prefix across tenants, partition the key by tenant or project while still reusing the stable prefix within that boundary.

### 7.4 Do not optimize for cache-hit percentage alone

A high hit rate is not automatically a good outcome if the application is making too many model calls. Track all of these together:

- total provider requests;
- total input tokens;
- cached input tokens;
- cache-write tokens;
- uncached input tokens;
- output tokens;
- reasoning tokens;
- result-cache hits;
- provider-cache reads;
- provider-cache writes;
- cost by stage and operation;
- cost per successful user outcome.

The primary success metric should be **cost per successful portfolio outcome**, not cache-hit percentage by itself.

### 7.5 Cache test matrix

Before changing production prompts, add a controlled test matrix:

| Scenario | Expected result |
| --- | --- |
| Same operation, same input, same profile, repeated within TTL | Durable result-cache hit; no provider request. |
| Same stable prompt, different user payload after breakpoint | Provider cache may read the stable prefix; dynamic tokens remain uncached. |
| Same input but prompt version changed | Durable result cache miss and provider cache miss are expected. |
| Same input but model or provider changed | Cache miss is expected; do not count it as a cache defect. |
| One validation correction | At most two provider requests total; both are logged. |
| One transient transport failure | At most one bounded retry; the retry relationship is logged. |
| Stale worker recovery at retry ceiling | No provider request; job becomes terminal or needs operator attention. |
| Ten repeated identical requests | Provider writes should occur once or at a small bounded number, followed by reads; verify actual dashboard behavior. |

## 8. Multi-provider and multi-model architecture requirements

Future OryxenAI plans include multiple LLM providers, multiple models, and different engines for different agents. That should be supported without reintroducing the current cost problem.

### 8.1 Keep a provider-neutral model boundary

Agents must call a provider-neutral `ModelClient` or equivalent contract. Agent code should never contain a literal provider name, model name, API key value, provider-specific retry loop, or provider-specific usage field.

The profile registry should decide:

- provider adapter;
- model identifier;
- base URL or endpoint;
- credential reference, such as an environment variable name;
- structured-output capability;
- reasoning capability and default effort;
- prompt-cache capability and TTL;
- maximum context and output limits;
- SDK retry policy;
- timeout policy;
- rate and concurrency limits;
- data-retention or residency constraints;
- pricing-card version;
- quality tier and fallback tier.

The existing config-driven model profile approach is the right direction. Extend it instead of bypassing it in agent code.

### 8.2 Use profiles, not model names in prompts or business logic

An agent should request a role such as:

```text
discovery_intake
content_strategy
visual_direction
code_planner
code_route_builder
code_repairer
```

The routing layer should map that role to a provider/model profile for the environment. A test profile, a low-cost development profile, and a production profile can then use different providers without changing the agent workflow.

Do not make a prompt say that a particular model is authoritative. The profile configuration is the source of truth.

### 8.3 Normalize usage across providers

Every adapter must return a normalized usage object with optional fields:

```text
input_tokens
input_uncached_tokens
input_cached_tokens
cache_write_tokens
output_tokens
reasoning_tokens
total_tokens
request_count
provider_request_id
client_request_id
```

Providers may use different names or may not expose cache-write and reasoning details. Missing fields must be represented as unknown or null, not silently converted to zero when that would hide a billing gap.

The normalized record must also include:

- `provider_profile_version`;
- `pricing_card_version`;
- `estimated_cost_currency`;
- `estimated_cost_status`, such as `exact`, `estimated`, or `unavailable`;
- the raw provider usage field names in redacted metadata when allowed;
- whether the request was a retry, fallback, cache correction, or normal call.

### 8.4 Keep provider cache namespaces separate

Prompt caches are not a cross-provider shared memory layer. A request that fails over from Provider A to Provider B should be expected to miss Provider B's cache. Record this as a provider switch, not as a cache failure.

Use a cache namespace that includes at least:

```text
provider / model / profile / operation / prompt version / schema version
```

Add tenant or project partitioning when the stable prefix contains user-specific or confidential information. Never use one global result-cache key across providers if the providers have different model behavior or output contracts.

### 8.5 Bound failover

Provider failover must be part of the same operation budget:

```text
primary provider request
  -> one allowed transport retry, if safe
  -> one fallback provider request, if policy allows
  -> terminal failure with next action
```

Do not allow each provider to use its own full retry budget after failover. For development, a strong default is one primary attempt plus one fallback attempt, with no additional automatic workflow restart.

Every failover must record:

- why the primary failed;
- whether the primary may have accepted the request;
- whether the output was absent or rejected;
- which provider/model was selected next;
- whether the cache was expected to miss;
- the remaining request and cost budget.

### 8.6 Provider-specific capability negotiation

At startup or deployment validation, check each selected profile for the capabilities required by its agent:

- native structured outputs;
- maximum output size;
- reasoning controls;
- prompt-cache controls;
- streaming support if required;
- tool or function-calling support;
- timeout and concurrency limits;
- usage telemetry fields;
- data-retention policy.

If a profile cannot meet the contract, fail before a user operation starts. Do not discover a missing capability halfway through a multi-stage workflow and silently switch to a more expensive fallback.

### 8.7 Isolate credentials and spending

Use separate project/key boundaries for:

- local development;
- automated tests;
- staging;
- production;
- optional provider-specific experiments.

The application should load only the credential reference for the selected profile. Secrets must remain in environment variables or a secret manager, never in logs, prompts, reports, browser code, or telemetry payloads.

Per-provider and per-project budget limits should be lower than the organization-wide maximum. A provider routing change should not be able to spend from an unrelated project simply because the same environment variable is present.

## 9. Cost accounting and rate-card remediation

The local `openai_luna` pricing configuration currently contains a custom rate card used for estimated telemetry. The research report also uses those rates for per-call dollar estimates. The live Platform totals do not line up cleanly with those configured estimates.

This is a reporting discrepancy, not necessarily a provider billing error. The local estimator must be treated as a versioned estimate until it is reconciled with the Platform's actual line items.

Required changes:

- Store pricing by provider, model, input type, cache-read type, cache-write type, output type, and effective date.
- Store the pricing-card version used for every estimate.
- Do not use a frozen price table in a narrative document as the billing source of truth.
- Recompute estimates whenever the configured model profile changes.
- Compare daily local totals with the Platform dashboard using the same UTC window.
- Report the reconciliation gap as a first-class metric.
- Do not claim model-replacement savings until a representative quality and cost evaluation has been run with current provider pricing.

Recommended reconciliation target after instrumentation:

```text
unattributed provider requests <= 5%
local-to-platform input-token gap <= 5%
local-to-platform output-token gap <= 5%
local-to-platform spend gap <= 10% while usage data is settling
```

If a provider does not expose enough usage information to meet the target, mark that provider's estimate as incomplete and apply a conservative budget reserve.

## 10. Observability that coding agents should add

The current database stores useful final receipts, but it does not provide a complete provider-call ledger. Add a durable or append-only call ledger with one row per attempted provider request, including failed and corrected calls.

Suggested fields:

```text
call_id
operation_id
portfolio_session_id
owner_user_id_hash
job_id
job_kind
stage
operation
workflow_attempt
job_attempt
request_attempt
retry_reason
fallback_from_provider
provider
provider_profile
provider_profile_version
model
prompt_version
schema_version
prompt_cache_key_hash
cache_breakpoint_id
client_request_id
provider_request_id
started_at
finished_at
status
error_class
error_code
input_tokens
input_uncached_tokens
input_cached_tokens
cache_write_tokens
output_tokens
reasoning_tokens
total_tokens
estimated_cost
pricing_card_version
```

Do not store raw API keys, full sensitive prompts, resume text, private user content, or model output in this ledger unless an explicit privacy policy allows it. Store hashes, references, sizes, and safe diagnostics.

At minimum, log a redacted line for every request:

```text
call_id operation stage provider model request_attempt job_attempt status input_tokens cached_tokens cache_write_tokens output_tokens provider_request_id
```

Use a unique client request ID on every provider request so a timeout can be reconciled with the provider even when the application did not receive a normal response. The [OpenAI API debugging reference](https://platform.openai.com/docs/api-reference/debugging-requests?lang=curl) documents the purpose of client request IDs for this kind of investigation.

## 11. Recommended implementation order

### Phase 0: contain spend

1. Keep the worker stopped until the queued Code Generator jobs are reviewed.
2. Lower the development project spend limit and configure a low alert threshold.
3. Use a separate development project/key from any production or shared environment.
4. Confirm every running checkout, worker, test process, and harness that can read the model credential.
5. Do not launch a broad generation test while the queue contains unreviewed work.

### Phase 1: make requests measurable

1. Add the provider-call ledger.
2. Record failed attempts, schema corrections, fallbacks, and stale replays.
3. Add client and provider request IDs.
4. Add per-operation request, token, and estimated-cost budgets.
5. Add a daily local spend summary grouped by provider, model, profile, stage, and retry reason.
6. Build a reconciliation report against the Platform dashboard's UTC window.

### Phase 2: enforce the two-attempt policy

1. Change the worker retry policy to two total attempts.
2. Change planner validation to two total model attempts.
3. Keep one optional structured-output correction only.
4. Reduce repair and integration-polish limits to two total rounds, with one repair as the default.
5. Prevent stale recovery and queued claiming at the retry ceiling.
6. Make explicit workflow restart the only way to begin another full stage attempt.
7. Add tests for every retryable path.

### Phase 3: fix prompt-cache reuse

1. Map each prompt into stable prefix, dynamic request body, and output schema.
2. Move run-specific IDs, diagnostics, source files, and user revisions after the cache breakpoint.
3. Replace run-unique cache keys for reusable prefixes with versioned profile/operation keys, partitioned for privacy where necessary.
4. Keep prompt ordering and schema serialization deterministic.
5. Track cache reads, writes, misses, and miss reasons separately.
6. Benchmark identical requests and realistic revisions before and after the change.

### Phase 4: support multiple providers safely

1. Define a provider-neutral normalized usage and error contract.
2. Make profile routing the only place that selects provider and model.
3. Add capability checks before an operation begins.
4. Apply one shared operation budget across primary, retry, and fallback providers.
5. Namespace caches by provider/model/profile/prompt/schema version.
6. Add provider-specific pricing cards and reconciliation tests.
7. Evaluate quality, latency, output validity, cache behavior, and cost before routing a production agent to a new provider.

### Phase 5: optimize model assignment

Only after Phases 0–4 are working:

- use a lower-cost model for classification, simple question selection, resource selection, and deterministic-support tasks when evaluations permit;
- reserve the strongest model for decisions that materially affect portfolio quality or source correctness;
- reduce reasoning effort for stages where evaluation shows no measurable benefit;
- reduce output ceilings to the smallest value that passes the contract;
- keep the current model as a fallback only when the fallback is within the operation budget;
- measure cost per accepted portfolio, not just token cost per request.

## 12. Acceptance tests for the fix

The remediation should not be considered complete until these tests pass:

### Retry tests

- A planner validation failure produces no more than two provider requests.
- A creative-direction validation failure produces no more than two provider requests.
- A route-generation validation failure produces no more than two provider requests.
- A transient provider error produces no more than one retry.
- A failed provider request and its retry both appear in the call ledger.
- A provider fallback consumes the same operation budget as the primary provider.
- An invalid credential, exhausted credit, or unsupported model does not retry.

### Queue tests

- A queued job at `attempt == max_attempts` cannot be claimed.
- A stale running job at the retry ceiling becomes terminal or needs attention without another provider call.
- A stale old worker cannot complete a job after a newer worker owns the lease.
- A job attempt cannot exceed its configured maximum without an explicit operator action and an audit event.
- A queue with more than the development threshold triggers the safety gate.

### Cache tests

- An identical durable-cache request returns without a provider request.
- A repeated prompt with the same stable prefix produces cached input tokens after the first write when the provider supports it.
- A prompt with a changed dynamic payload does not invalidate the stable prefix unnecessarily.
- Changing model, provider, prompt version, or schema version produces a deliberate cache miss.
- Sensitive user-specific result cache entries cannot be returned to another owner or tenant.
- Cache writes and cache reads are both visible in telemetry.

### Multi-provider tests

- Switching a profile changes provider behavior without changing agent code.
- A provider with no native structured-output support is rejected or routed through a tested adapter policy before a live run.
- A provider with incomplete usage fields reports unknown values instead of false zeroes.
- Provider failover creates a separate call record and does not reset the operation budget.
- Provider-specific cache misses are represented as expected namespace changes.
- Credentials are resolved only through configured secret references.

### Billing reconciliation tests

- A controlled test run's local request count matches provider request count within the expected delayed-reporting window.
- Local input, cached, cache-write, output, and reasoning totals can be grouped by UTC day.
- The reconciliation report identifies unattributed requests rather than silently ignoring them.
- The local estimate includes a pricing-card version and never presents a stale estimate as the Platform bill.

## 13. Guidance for future coding agents

Before changing model, provider, retry, cache, worker, or cost code:

1. Read `AGENTS.md`, `DECISIONS.md`, and the current model/config files.
2. Check `git status --short --branch` and preserve unrelated work.
3. Search all provider call sites, not only the primary adapter.
4. Search for every retry loop, SDK retry setting, fallback path, stale-lease path, and manual requeue path.
5. Build a request graph for the affected operation before editing it.
6. Confirm whether the path uses durable result caching, provider prompt caching, or both.
7. Never assume a cache hit from the presence of a cache key; verify returned cached-token telemetry.
8. Never count only successful final receipts; include failed and corrected provider requests.
9. Do not run a broad live model test without an explicit request budget and a disposable development project.
10. Use fixtures and mocks for ordinary tests; live calls are opt-in and must be clearly scoped.
11. Run targeted tests for the changed retry/cache/provider behavior before the full suite.
12. Recheck the live Platform dashboard after the change using the same UTC window.

The agent should report any new discrepancy in this format:

```text
Observed dashboard requests:
Observed dashboard input/output/cache tokens:
Observed dashboard spend:
Local provider-call ledger requests:
Local provider-call ledger token totals:
Unattributed requests:
Retry/fallback/stale-replay count:
Queue state:
Likely cause:
Confidence:
Next safe action:
```

## 14. Source and repository references

- [OryxenAI LLM calls and model replacement analysis](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/docs/research/llm-calls-and-model-replacement-analysis.md>)
- [`config/app.toml`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/config/app.toml>)
- [`config/models.toml`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/config/models.toml>)
- [`src/oryxenai/agents/shared/model_cache.py`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/shared/model_cache.py>)
- [`src/oryxenai/agents/shared/providers/opencode_go.py`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/shared/providers/opencode_go.py>)
- [`src/oryxenai/agents/code_generator/core/generation_orchestrator.py`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/code_generator/core/generation_orchestrator.py>)
- [`src/oryxenai/agents/code_generator/core/planner_operation.py`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/agents/code_generator/core/planner_operation.py>)
- [`src/oryxenai/jobs/repository.py`](<C:/Users/Yash Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/jobs/repository.py>)
- [OpenAI model guidance on prompt caching and request efficiency](https://developers.openai.com/api/docs/guides/latest-model)
- [OpenAI Platform usage reference](https://platform.openai.com/docs/api-reference/usage/audio_transcriptions_object)
- [OpenAI Platform billing overview](https://platform.openai.com/settings/organization/billing/overview)
- [OpenAI API debugging and client request IDs](https://platform.openai.com/docs/api-reference/debugging-requests?lang=curl)

## 15. Final decision record for this investigation

The current observed behavior should be treated as a cost-control incident in development, not as normal steady-state usage. The project should first enforce a two-total-attempt policy, stop unreviewed queue drainage, repair stale-job attempt enforcement, and add complete call-level telemetry. Prompt caching should then be redesigned around stable prefixes and measured reuse. Multi-provider routing should be added only behind the same normalized budgets, telemetry, capability checks, and cache namespaces.

The intended end state is not “use caching everywhere” or “retry every failure twice.” The intended end state is a bounded, observable request graph in which every provider call is attributable, every repeat is justified, every cache write has a realistic chance of reuse, and every provider/model can be swapped through configuration without bypassing those controls.
