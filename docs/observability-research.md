# Lightweight LLM observability research note

**Status:** Research only. No observability code, dependency, dashboard, or
architecture decision has been added by this note.

**Audience:** A future Codex run or another implementation agent that is asked
to add simple cost and tracing visibility to OryxenAI.

## What is wanted

The goal is a small, easy-to-read dashboard that answers:

- Which portfolio/agent run happened?
- Which agent stage and model calls ran?
- How long did they take?
- How many input/output/cache tokens were used?
- What was the approximate cost?
- Which call, retry, or provider failed?

This is not a request for a large distributed-observability platform. Do not
start with a full metrics, logs, traces, collector, alerting, and evaluation
program.

## Working recommendation

Use **Langfuse** as the first implementation target:

- Use its Python SDK because the current backend and workers are Python.
- Use the free managed plan during research and low-volume development if
  sending metadata to a managed service is acceptable.
- Consider self-hosted Langfuse or Phoenix later if data must remain local.
- Instrument the existing shared `ModelClient` boundary once. Do not add
  provider-specific tracing code to every agent.
- Keep the first dashboard metadata-only: IDs, timing, token usage, cost,
  model/profile labels, status, and safe error categories. Do not upload
  resumes, prompts, generated portfolio content, or secrets by default.

Langfuse is attractive here because it provides a ready-made trace UI, token
and cost tracking, tags, sessions, and custom model pricing without requiring
OryxenAI to build a dashboard. Its SDK is OpenTelemetry-based, which leaves a
future escape route if the destination changes.

This is a working recommendation, not a final technology decision. Verify the
current Langfuse SDK, pricing, retention limits, self-hosting requirements, and
license terms when implementation begins.

## Minimal trace shape

Keep the trace hierarchy shallow:

```text
portfolio/run
  └── agent stage
        ├── durable job attempt
        ├── model call: operation A
        ├── model call: operation B
        └── model call: operation C
```

The natural root identifiers are the existing OryxenAI run, session, job, and
attempt identifiers. A future implementation should correlate the external
trace ID with those identifiers rather than inventing a second unrelated
identity system.

The shared model-call observation should contain only the useful fields:

- agent/stage and operation name;
- configured profile, provider, and model label;
- run ID, session ID, job ID, attempt number, and release/environment;
- elapsed time and provider response ID when available;
- input, output, cached, and reasoning token counts when available;
- batch size, retry number, status, and safe error code;
- estimated or provider-reported cost, clearly distinguished.

Do not trace every helper function, worker heartbeat, database query, or polling
loop in the first version. Those details would make the dashboard noisy without
answering the cost question.

## Cost and batching rules

Prefer usage counts returned by the provider. If usage is unavailable, a token
estimate may be recorded, but it must be marked as estimated rather than
presented as an exact bill.

Pricing should live in one configuration/pricing boundary, not in agent code or
individual provider adapters. The basic calculation is:

```text
cost = input tokens × input rate
      + output tokens × output rate
      + cached tokens × cached rate
```

The pricing model may later need additional usage types such as reasoning,
audio, image, or tool-related units. The first version only needs the fields
actually returned by the configured provider.

For a batch, create one parent `batch` observation and one child observation
for each provider request. Record `batch_size` and total provider usage on the
request observation. Do not pretend that the same full prompt cost was incurred
once per item unless the provider actually reports it that way. Per-item cost
allocation can be added later if the product needs it.

## Where a future implementation should attach

The likely small integration surface is:

1. Create a root trace when an explicit agent run begins.
2. Pass the trace correlation through the durable job payload or run metadata.
3. Start and finish one generation observation around each real model call in
   the shared `ModelClient` implementation.
4. Record the provider's normalized usage result after the response arrives.
5. Mark failures and retries on the same observation hierarchy.
6. Flush telemetry safely at the end of short-lived commands and workers.

The telemetry client must never be allowed to make an agent run fail. If the
dashboard is unavailable, the model operation and durable job should continue;
the failure should be logged locally as a non-business-critical telemetry
error.

## User decisions before implementation

The future implementation agent should ask for, or confirm, only these choices:

1. **Destination:** free managed Langfuse for the easiest start, or a local
   self-hosted destination for privacy.
2. **Data policy:** metadata/token/cost only, or whether carefully redacted
   prompt/output samples are allowed.
3. **Retention:** how long traces should remain available.
4. **Budget visibility:** whether a simple cost threshold notification is
   wanted now or can wait.

The user does not need to design the tracing code, span names, provider usage
normalization, or dashboard queries. Those are implementation-agent tasks.

## Alternatives considered

### Phoenix

Phoenix is a good local/open-source alternative and supports OpenTelemetry and
OpenInference-based tracing and cost tracking. It is worth choosing if the
primary requirement becomes local data residency. It is not the first choice
for the smallest possible setup because the dashboard/instrumentation path is
slightly more involved than using Langfuse's SDK directly.

### OpenTelemetry by itself

OpenTelemetry is a useful underlying standard, not the simple dashboard the
user is asking for. Use compatible attribute names where practical, but do not
build an OpenTelemetry Collector, metrics backend, and custom cost UI as the
first step.

### Provider proxies or agent frameworks

Do not add a proxy, LangChain, or another agent framework only for tracing.
OryxenAI already has a shared provider-neutral model boundary, so wrapping that
boundary is smaller and preserves the current architecture.

## Future implementation checklist

- [ ] Re-check current Langfuse and Phoenix capabilities and pricing.
- [ ] Add the selected telemetry dependency through the normal project setup.
- [ ] Add non-secret telemetry configuration to the existing configuration
      system; keep API keys in `.env`.
- [ ] Instrument the shared model-call boundary, not each agent separately.
- [ ] Correlate traces with existing run/job/attempt IDs.
- [ ] Capture provider-reported usage and calculate cost centrally.
- [ ] Default to metadata-only capture and redact sensitive values.
- [ ] Make telemetry failures non-blocking.
- [ ] Add a small test covering one successful call, one retry/failure, and one
      batch metadata record.
- [ ] Run a real low-volume smoke check and verify the dashboard visually.
- [ ] Document the dashboard URL and safe local shutdown/disable procedure.

## Sources to re-check at implementation time

- [Langfuse SDK overview](https://langfuse.com/docs/observability/sdk/overview)
- [Langfuse token and cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [Langfuse trace IDs and distributed tracing](https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing)
- [Langfuse self-hosting](https://langfuse.com/self-hosting)
- [Langfuse pricing](https://langfuse.com/pricing)
- [Phoenix overview](https://arize.com/docs/phoenix/)
- [Phoenix cost tracking](https://arize.com/docs/phoenix/tracing/how-to-tracing/cost-tracking)
- [OpenTelemetry GenAI attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)
