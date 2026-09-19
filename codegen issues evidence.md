# Code Generator Issues — Evidence and Failure Traces

This companion file records the traced boundaries behind `codegen issues.md`. It is intended for the engineer who will implement the fixes. It does not contain fixes.

## End-to-end path audited

```text
Build Preparation state
  -> CodeGeneratorService.start()
  -> immutable brief envelope + compiled projections
  -> durable plan job
  -> durable acquisition job
  -> progressive route/foundation generation
  -> clean npm/typecheck/Vite build
  -> browser/runtime verification
  -> candidate storage + active pointer promotion
  -> server public readback
  -> API active_preview URL
  -> frontend iframe
```

The pipeline has multiple independent identity and environment boundaries. A portfolio can be valid at one boundary and still be unusable at the next one.

## Failure trace A — Docker preview never reaches the browser

| Boundary | Current value/behavior | Result |
| --- | --- | --- |
| Worker health probe | `http://preview-gateway:4174/health/live` | Can reach the gateway through Compose DNS |
| Worker public readback | `http://localhost:4174/preview` in `app.docker.toml` | Resolves inside the worker container, not the gateway |
| Promotion policy | `preview_public_readback_required = true` | Failed readback restores the pointer and blocks active promotion |
| Frontend URL | Receives the configured base URL from `ActivePreview` | Even a returned localhost URL is not the user's gateway URL |

The failure is a topology/configuration mismatch, not a generated React defect. The preview origin must be defined from the browser's perspective, while internal health/readback must use a separately configured reachable path or an explicit gateway validation service.

## Failure trace B — stale upstream approval is discovered too late

```text
Content/Visual approval changes
  -> BuildPreparationService.get_state() can calculate approved_upstream_changed
  -> CodeGeneratorService.start() reads JSONB state directly
  -> status is still READY, Markdown is nonempty
  -> plan/acquire/generate/build work is allowed
  -> verification handler finally calls _session_source_is_current()
  -> stale candidate is not promoted
```

The system has a stale detector, but it is not placed at the admission boundary. This turns a cheap handoff check into a late terminal generation failure.

## Failure trace C — false-green API readiness

```text
API process checks npm/browser/provider
  -> job is committed
  -> separate worker claims job
  -> worker has different PATH, cache, browser, filesystem, or preview network
  -> acquisition/build/runtime fails
```

The worker release/pipeline fence protects code compatibility, but it does not prove that the worker's executable/toolchain facts match the API's preflight facts. The 2026-09-18 campaign showed that process launch method alone could change Node/npm/browser discovery.

## Failure trace D — npm contract split

```text
DependencyManager._create_lock()
  -> npm install --package-lock-only --offline
  -> optional platform dependency entries may be malformed/pruned
DependencyManager._install()
  -> npm install --offline may repair the local tree
Verification run_clean_build()
  -> deletes node_modules
  -> npm ci --offline revalidates the lock strictly
  -> invalid/out-of-sync lock stops the build before Vite
```

The receipt currently records a lock hash, but the important acceptance property is not only “a lockfile exists.” It is “the exact lockfile survives the exact clean install used by verification on the worker's platform.”

## Failure trace E — approved content is present in the workspace but not usable by the route model

The foundation writes the approved content module. Route context then deliberately compacts that module to:

```ts
export type ApprovedContentId = "...literal ids...";
export declare function contentValue(contentId: ApprovedContentId): string;
```

This protects privacy/context size and prevents the model from retyping approved prose, but it leaves the model responsible for placing every exact literal ID into a large array-heavy JSX implementation. The live campaign showed the model returning a semantic `cannot_complete` response even though the approved values existed in the trusted workspace and the ID union was supplied.

The problem is a missing host-owned intermediate step: the model is choosing layout and code structure while also acting as a high-volume compiler for approved content bindings. A repair prompt cannot reliably eliminate this class of failure.

## Preview state semantics that must remain distinct

| State | Meaning | User-facing consequence |
| --- | --- | --- |
| Candidate preview | Stored artifact exists but required verification/promotion is incomplete | May be shown only as explicitly unverified diagnostics |
| Active preview | Atomic pointer promotion and configured readback succeeded | Safe to present as the user's verified preview |
| `preview_pending` | Candidate/promotion state is retained but active promotion has not completed | Must not look like a successful generation |
| `needs_attention` | A required source/build/runtime/promotion gate failed | Must expose a retryable, actionable reason |

The current frontend intentionally renders a candidate when no active preview exists. That is acceptable only if the browser URL is reachable and the unverified badge remains prominent. It does not solve the Docker URL mismatch or a silent iframe failure.

## Boundary checklist for the eventual fix work

- [ ] Public preview origin is browser-resolvable from the actual authenticated app origin.
- [ ] Worker-to-gateway URL and browser/public URL are separate settings with validation.
- [ ] Promotion readback exercises the same externally visible host/path that the iframe uses.
- [ ] Build Preparation freshness is checked before any Code Generator model/provider call.
- [ ] Run source reference includes the exact current upstream approved hashes and contract version.
- [ ] Worker readiness receipt covers Node/npm/browser/cache/gateway and is tied to run admission.
- [ ] Lockfile generated by acquisition passes the same clean install path as verification.
- [ ] Route generation does not require a model to hand-emit dozens of approved content bindings.
- [ ] Windows build concurrency is bounded before Vite starts child processes.
- [ ] Disabled verification is an enforced capability state, not an unused TOML flag.
- [ ] Frontend iframe reports load, timeout, HTTP/CSP, and origin failures in traceability diagnostics.

## Evidence sources

- `src/oryxenai/agents/code_generator/service.py`
- `src/oryxenai/agents/code_generator/core/brief_ingestion.py`
- `src/oryxenai/agents/code_generator/core/dependency_manager.py`
- `src/oryxenai/agents/code_generator/core/generation_orchestrator.py`
- `src/oryxenai/agents/code_generator/core/generation_contract.py`
- `src/oryxenai/agents/code_generator/core/build_runner.py`
- `src/oryxenai/jobs/handlers/code_generator_verification.py`
- `src/oryxenai/preview/promotion.py`
- `frontend/src/stages/generation/GenerationStage.tsx`
- `config/app.docker.toml`
- `config/app.docker.codegen-run.toml`
- `docs/code-generator-repair-plan-campaign-2026-09-18.md`
- `DECISIONS.md` D-099
