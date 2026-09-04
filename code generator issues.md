# Code Generator Issues

Short, current issue log for the Code Generator / Build Preparation handoff.
Replace stale campaign notes when the contract or root cause changes; keep only
findings that help diagnose the next persistent failure.

## Current state — 2026-09-04

- The supplied Build Preparation output is a pair of Markdown briefs with
  fenced `build-preparation-content-index` and
  `build-preparation-visual-index` JSON. It contains one closed `home` route,
  six sections, seven image candidates, four optional component suggestions,
  and no ZIP/R2 payload or image bytes.
- The v5 run `69200916-794c-4cae-9cf1-7ebaeb34696c` successfully admitted,
  planned, acquired, and checkpointed its foundation. Route generation then
  reached the provider rate limit; no source or preview failure was observed
  after the fixes below.

## Findings and fixes

| Area | Finding | Durable resolution |
|---|---|---|
| Input persistence | Markdown admission wrote only a content-addressed JSON file, while `GenerationWorkspace` resumed from `admitted/<identity>`. This produced `ADMITTED_INPUT_MISSING`. | Publish an immutable identity-addressed `brief-envelope.json` copy during admission, verify read-back, and reuse it for fresh and resumed runs. |
| Queue persistence | A pre-migration worker could claim a migrated job because the queue kind was shared. | Use the v5 job-kind namespace plus pipeline/release fences; readiness rejects mixed incompatible workers. |
| Brief parsing | The old ZIP unpacker/stubs rejected the new pair of Markdown briefs. | Parse both fenced JSON contracts, validate hashes/closed navigation, and compile route-scoped projections without inventing pages or links. |
| Brief transport | Windows CRLF uploads did not match the line-anchored fence/heading parser, although the same files worked after text-mode newline conversion. | Normalize CRLF/CR to LF for parsing while retaining the original Markdown bytes for provenance hashes and immutable storage. |
| Planner contract | Providers returned narrow distinctive-move ratios and font roles pointing at remote/nonexistent files. | Deterministically widen/clamp numeric ranges and bind typography roles to admitted local font paths before schema validation. |
| Optional components | Raw shadcn/MagicUI registry files imported provider-only aliases (`@/registry/...`) and were copied into `src`, causing a source AST failure even though the route did not use them. MagicUI also returned 404. | Treat unbound component suggestions as reference-only in both planned and emergent acquisition; keep licensed bytes in durable materials, use an accessible local equivalent in generated routes, and fall back on optional provider errors. |
| Resource placement | Deferred image/font bytes were acquired successfully but lacked plan-time destinations, so generated imports could not reliably find them. | Compile deterministic intended paths from the visual brief and remap acquired files into `public/resources/pack/...` (fonts/images) during workspace materialization. |
| Provider pressure | The route-batch scheduler allowed several structured model requests at once, so provider 429s could be mistaken for generator failures and retried repeatedly. | Set the bounded route-generation concurrency to one; keep retries/resumes on the same checkpoint instead of replaying earlier calls. |
| Runtime observability | Readiness polling could repeat a billable provider preflight or report a false missing receipt. | Readiness now inspects the shared in-process TTL cache; only the explicit preflight endpoint makes provider calls. |

## Remaining external blocker

- `PROVIDER_RATE_LIMIT_ERROR` stopped route generation for run
  `69200916-794c-4cae-9cf1-7ebaeb34696c`. This is provider capacity/rate
  limiting, not a source or persistence diagnosis. A same-run generate retry
  resumes from the accepted foundation checkpoint and avoids repeating the
  completed planning/acquisition calls.

## Next verification target

- Resume one bounded v5 run and require: route source checkpoint, clean build,
  DOM/geometry verification, atomic preview promotion, and no generated
  `src/generated/resources/acquired` component files unless an explicit
  executable destination exists.
