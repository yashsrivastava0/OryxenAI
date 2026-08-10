# Portfolio Build Preparation

Build Preparation is the hidden pre-code stage between approved Visual Design
Direction and the future Code Generation Engine. It is one durable operation,
`build_preparation.prepare`, with two API operations:

- `GET /api/v1/sessions/{session_id}/build-preparation`
- `POST /api/v1/sessions/{session_id}/build-preparation/start`

The start operation requires approved Content Architect and Visual Design
Director state. It compiles a versioned Experience Blueprint, Resource
Manifest, Global Experience Context, and route/page packets, then writes one
immutable ZIP pack to the configured private S3-compatible object store. The
database stores only the object key, hash, size, expiry and provenance metadata
under the session's JSONB state. The worker's temporary local workspace is
deleted after upload.

Production uses Cloudflare R2 (`artifact_storage.provider = "r2_s3"`) with a
three-day configurable TTL. The non-secret endpoint and bucket live in the
base configuration and can be replaced by an app overlay; put access-key
values in `.env` or the hosting provider's secret store. Configure an object
lifecycle rule for the `temporary/` prefix. Tests use the process-local `memory` provider and
inject fake resource providers; they never contact R2, registries or Pexels.

The pack is self-sufficient for future code generation: registry source and
selected images are materialized before the job succeeds. Missing credentials,
provider outages, unsuitable media, unsupported dependencies and absent local
assets become warnings or explicit custom-implementation requirements rather
than fabricated resource IDs. No package installation or provider network
access is required during code generation.

## Temporary fixture preview

When the developer UI is enabled, the checked-in Visual Design artifact at
`src/oryxenai/output/visual_design_director_Output.md` can be tested without a
portfolio session at `/build-preparation-fixture`. The page calls
`POST /api/v1/build-preparation/fixture/run`, runs the deterministic compiler
and bundle pipeline, and displays the resulting Blueprint, Manifest, Context,
page packets, warnings, and temporary object reference. Fixture output is
always marked `publishable: false`; it accepts review-state VDD input only for
debugging and never changes upstream approval state or database session state.
The fixture path does not contact registries or Pexels, so it remains a
deterministic local test of package compilation and materialization.
