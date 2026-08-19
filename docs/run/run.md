# Runbook: OryxenAI agent pipeline

This runbook records the verified Docker startup for the Discovery, Content
Architect, Visual Design Director, and Build Preparation stages. It is for
local reuse on the Windows checkout and does not create agents, source files,
or a second frontend.

## Frontend and services

- Frontend: `http://localhost:8000`
- Liveness: `http://localhost:8000/health/live`
- API agent listing: `http://localhost:8000/api/v1/agents`
- PostgreSQL host port: `5544`
- API container: `oryxenai-app-1`
- Worker container: `oryxenai-worker-1`
- Database container: `oryxenai-postgres-1`

The frontend root contains the Discovery flow and the persisted Agent
Workspace for later outputs. Discovery approval does not automatically start
the next stage. Start Content Architect and Visual Design Director explicitly
from the workspace after their upstream approval is available.

## Normal startup

Run these commands from `C:\Users\yashx\Desktop\OryxenAI`:

```powershell
docker compose build migrate app worker
docker compose up -d migrate app worker
docker compose ps
```

The migration service must exit successfully before the API and worker start.
Expected final state:

- `oryxenai-postgres-1`: healthy
- `oryxenai-app-1`: up and healthy, port `8000`
- `oryxenai-worker-1`: up and healthy
- `oryxenai-migrate-1`: exited with code `0`

Rebuild the image when migration files or application code changed. The
Compose image copies the repository into the container; using an old cached
image can hide current migration files.

## What happened during the verified run

1. The initial Docker inspection was blocked by Windows permission on the
   Docker named pipe. Running Docker commands with the required local Docker
   access resolved that; the PostgreSQL container was already running.
2. Initially only PostgreSQL was running. The first
   `docker compose up -d migrate app worker` failed because the cached image
   could not find migration `0011_codegen_coordinator`.
3. `docker compose build migrate app worker` rebuilt all three existing
   application images from the current checkout. No source file was edited.
4. The rebuilt migration then failed at `0012_codegen_session` because the
   persistent database was stamped at `0011_codegen_coordinator` but did not
   contain `portfolio_sessions`. Read-only inspection showed that the volume
   contained only the old Code Generator tables, with 5 development runs and
   25 events.
5. The existing Code Generator rows were preserved. The missing shared
   application tables were repaired transactionally using the current schema:
   `portfolio_sessions`, `agent_runs`, `background_jobs`, and
   `service_heartbeats`, including their required indexes. No `DROP`,
   `TRUNCATE`, volume deletion, or source-file change was used.
6. Rerunning `docker compose up -d migrate app worker` completed migration
   `0012_codegen_session` with exit code `0`, then started the API and worker.

## Verification performed

```powershell
docker compose ps

$health = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/live
$root = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/
$agents = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/v1/agents

docker exec oryxenai-postgres-1 psql -U oryxen -d oryxenai -Atc `
  "select version_num from alembic_version;"
```

Observed results:

- Liveness returned HTTP `200` with `{"status":"alive"}`.
- Frontend root returned HTTP `200`.
- The agent endpoint returned Discovery, Content Architect, and Visual
  Design Director.
- The database revision was `0012_codegen_session`.
- API, worker, and PostgreSQL were healthy.
- The three live profiles resolved their configured API-key environment name
  to `OPENAI_API_KEY`, and the key was present inside the app container. The
  key value was never printed. Startup verification did not make a live model
  request; the user starts that from the frontend.

## If the run fails again

### `Can't locate revision identified by '0011_codegen_coordinator'`

The image is stale. Rebuild the existing services and retry:

```powershell
docker compose build migrate app worker
docker compose up -d migrate app worker
```

### `relation "portfolio_sessions" does not exist` at `0012_codegen_session`

Do not run `docker compose down -v`, drop the database, or reset the volume;
that can remove existing Code Generator work. First inspect the migration
revision and table list read-only. If the database is again stamped at
`0011_codegen_coordinator` while only the old Code Generator tables exist,
repair only the missing shared tables using the current ORM/migration schema,
then rerun the normal Compose startup. Preserve existing rows and verify the
final migration revision is `0012_codegen_session`.

### Docker named-pipe access denied

Confirm Docker Desktop/Engine is running and rerun the Docker command with the
local Docker permission required by the Windows environment. This is an
environment access issue, not an agent or model failure.

## Stage order and live execution

Use the frontend at `http://localhost:8000`:

1. Start and complete Discovery, then approve its brief.
2. Explicitly start Content Architect after Discovery approval; wait for the
   durable worker job and approve its output.
3. Explicitly start Visual Design Director after Content Architect approval;
   wait for the durable worker job and approve its output.

The backend uses durable PostgreSQL jobs and the separate worker. Normal tests
may use fixtures, but this runbook's user flow is live-provider capable and
must not silently replace a requested live AI call with fixture output.

## Build Preparation frontend and run

The frontend is available at:

- Main pipeline: `http://localhost:8000/`
- Detached Build Preparation runner: `http://localhost:8000/build-preparation-fixture`
- Detached run details: `http://localhost:8000/build-preparation-fixture/progress`
- Liveness: `http://localhost:8000/health/live`

The detached page is the easiest way to run Build Preparation from pasted or
uploaded Content Architect and Visual Design Director JSON. It exposes two
explicit options: `Use configured live model` and `Use live resource providers`.
Enable both for a real run. An offline run is diagnostic-only and cannot be a
Code Generator handoff.

### Configure secrets

From the repository root, create `.env` once and fill in the secret values
locally. Do not paste token values into this runbook, terminal output, or Git:

```powershell
Set-Location C:\Users\yashx\Desktop\OryxenAI
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Build Preparation's configured secret names are:

- `POSTGRES_PASSWORD` for PostgreSQL.
- `OPENAI_API_KEY` for the configured live model profile. The active model,
  provider, endpoint, and limits remain config-driven in `config/models.toml`;
  do not hardcode them in this runbook.
- `PEXELS_API_KEY` and `PIXABAY_API_KEY` for live image retrieval. The
  configured provider policy is in `config/app.toml`.
- `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` for verified temporary artifact
  upload/read-back. The endpoint, bucket, and expiry policy remain in
  `config/app.toml`.

Rebuild and restart after changing `.env` or application/config files:

```powershell
docker compose build migrate app worker
docker compose up -d migrate app worker
docker compose ps
```

### Production session run

Use this path when Discovery, Content Architect, and Visual Design Director
have been completed and approved in the main frontend. Build Preparation does
not auto-chain from Visual Design Director. Start it explicitly with the
approved session ID:

```powershell
$sessionId = "<approved-session-uuid>"
$body = @{ } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/sessions/$sessionId/build-preparation/start" `
  -ContentType "application/json" `
  -Body $body
```

Poll the state until the durable worker finishes:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/sessions/$sessionId/build-preparation"
```

`ready` is not by itself the Code Generator gate. Admit a pack only when the
returned handoff report says `handoff_eligible=true`. `needs_attention` means
the package may be useful for review, but an unresolved component, image,
font, approval, or provenance gap must be fixed before downstream generation.

### Detached frontend run

Open `http://localhost:8000/build-preparation-fixture`, paste or upload the
approved Content Architect projection and Visual Design Director output, check
both live options, and select `Run Phase 3`. The page links to the run details
and the local debug package when the run completes.

Use the production session route when possible. The Compose app mounts
`Input-Output-Of-Engine` read-only, so the detached page can auto-pick the
attached CA/VDD outputs. Use the paste/upload controls for an explicit
override or use approved state in the production session instead.

### Issues found during the verified live run

- Docker initially hit a Windows named-pipe permission issue. This was local
  Docker access, not an agent or model failure.
- The first live attempt needed explicit outbound network permission for the
  model and resource providers. If the provider calls cannot leave the
  machine, the run must fail visibly; it must not silently use fixtures.
- A live model response exposed additional responsive/reduced-motion query
  fields and Stage 3/4 context envelope fields that the strict input schemas
  did not accept. The schemas and normalization were aligned in commit
  `237e0ed`, and the focused Build Preparation tests passed.
- One live Stage 2 response returned a need ID with a trailing comma while
  matching candidates. The pipeline now closes model selections against the
  deterministic Stage 0 need set, discards unknown/duplicate IDs, and records
  an explicit fallback instead of raising a `KeyError`.
- A live Stage 5 handoff-review request returned a provider HTTP `400` after
  deterministic admission had completed. Stage 5 review is advisory now: the
  error is recorded as `MODEL_REVIEW_UNAVAILABLE`, eligibility remains fail-
  closed, and the local/R2 package is retained for review.
- The verified live run completed model calls, provider retrieval, packaging,
  and R2 upload/read-back, but correctly returned `handoff_eligible=false`.
  The remaining gaps were one unresolved approved component role, duplicate
  decorative image bytes, and an upstream VDD execution gap. Revise and
  explicitly re-approve the affected VDD/resource decisions, then regenerate.
- Do not start a second worker to work around a slow run. The API and one
  durable worker must share the same database; duplicate workers can make
  diagnosis ambiguous even though job claiming is protected.
