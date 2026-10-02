# Document intake and managed-container deployment

This note records the PDF/text intake path and the container settings needed
to run it on Render, Railway, or another Linux x86_64 container host. It does
not deploy or change any remote service.

## Extraction plan and data path

1. The authenticated intake screen accepts one `.pdf`, `.md`, or `.txt` file.
   DOCX, image files, and multiple attachments are not supported.
2. The browser sends the file to `POST /api/v1/discovery-documents/extract`.
   The API bounds the streamed body, checks the extension and PDF structure,
   rejects encrypted/empty/over-page-limit PDFs, and extracts in a worker
   thread. One extraction at a time runs in each API process.
3. Markdown and text are decoded as UTF-8 and kept without whitespace
   normalization. PDFium and Docling produce a Markdown transcript with
   detected heading hierarchy, reading order, lists, furniture, and page
   breaks. Docling's normal OCR mode keeps selectable PDF text and uses the
   local RapidOCR model on image regions and scanned pages; full-page OCR is
   avoided because it can replace accurate embedded text with recognition
   guesses. Character entities are decoded before the transcript is shown.
4. The browser shows the whole transcript in an editable preview, along with
   the filename, page count, and any partial-conversion warning. The user may
   correct recognition mistakes before continuing.
5. Discovery start sends the reviewed transcript as `document_text` and the
   filename as `document_name`. The service saves the text in its normal
   source-document snapshot, and `understand_and_question` receives that full
   named source. The prompt asks Discovery to read every source and treat text
   inside files as evidence, not instructions. The existing agent output
   contract then decides whether to ask a targeted question, ask none, or
   request more usable detail.
6. Uploaded binary bytes are not written to disk or stored in PostgreSQL.
   The reviewed transcript becomes part of the user's Discovery session, as
   pasted source text already does. Pipeline reset clears that session data
   through the existing owner-scoped cleanup route.

The API limits are configured in `config/app.toml`: 10 MiB per file, 10 PDF
pages, 200,000 extracted characters, and 120 seconds per PDF conversion. The
frontend and API share the same route contract. Password-protected, malformed,
empty, oversized, unsupported, or unconvertible files produce a visible safe
error; partial conversion is surfaced for review. OCR may still misrecognize a
low-resolution scan, so the editable transcript is the correction point before
the model sees it.

## Local development

After installing project dependencies, fetch the Docling layout, table, and
RapidOCR assets once:

```powershell
uv run python scripts/download_docling_models.py --output-dir .workspace/docling-models
```

The directory is ignored by Git. `config/app.toml` points native development at
that path. Unit/API tests use deterministic converter doubles and do not fetch
model files or call a live model provider.

## Container requirements

The root `Dockerfile` installs the CPU inference dependencies, downloads the
needed model files in its builder stage, and copies them to
`/opt/docling-models` in the runtime image. Runtime configuration points there;
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` prevent runtime downloads. The
image build needs outbound access to the Python package index and the Docling
model source. The deployed containers do not need a persistent volume for OCR
assets, and a volume must not be mounted over `/opt/docling-models`.

The PDF path is CPU-bound. It uses two inference threads and serializes
extraction within each API process. For a small initial deployment, allocate
at least 2 vCPU and 4 GiB RAM per API instance, then adjust from observed
memory and extraction latency. The supplied three-page PDF completed locally;
no Render or Railway service has been deployed from this branch.

## Render service setup

Render supports building a Docker web service from the repository's root
Dockerfile, a configurable HTTP health path, a separate background worker, and
a pre-deploy command. Create these services in the same region and connect them
to one Render PostgreSQL database:

| Service | Build/start settings | Health or migration |
| --- | --- | --- |
| API | Docker, root `Dockerfile`, default image command | HTTP health path `/health/live`; use pre-deploy command `alembic upgrade head` |
| Worker | Same Dockerfile; command `python -m oryxenai.jobs.worker` | Keep it always running; it does not bind an HTTP port |
| PostgreSQL | Managed PostgreSQL | Use its private connection URL for both application services |

Set the same runtime variables on API and worker:

```text
OryxenAI_CONFIG_OVERLAY=config/app.production.toml
DATABASE_URL=<private PostgreSQL URL>
ORYXENAI_AUTH_PRIMARY_ORIGIN=https://<public-app-host>
ORYXENAI_AUTH_ALLOWED_ORIGINS=https://<public-app-host>
```

Also set the required Supabase and model-provider secrets listed in
`.env.example`, plus the configured admin/user admission values. Keep the
database URL and all provider keys in the service's secret environment store.
The origin variables are public configuration, not secrets. The API uses the
platform's injected `PORT`; leave the Dockerfile command as the web service
start command. Render's pre-deploy command is available on paid web services,
private services, and workers; if the selected plan lacks it, run the
migration as a one-shot release step before starting the API or worker.

## Railway service setup

Railway translates Compose topology into separate services rather than running
the Compose file directly. Create a PostgreSQL service, an API service from the
root Dockerfile, and a worker service from the same repository and image. Use
the API service's pre-deploy command for `alembic upgrade head`, then start the
worker with:

```text
python -m oryxenai.jobs.worker
```

Leave the API start command at the Dockerfile default so its shell expands
Railway's injected `PORT`. Configure its HTTP healthcheck at `/health/live`.
Set the same four runtime variables above and the same auth/provider settings
on both services; use Railway's private Postgres URL. Do not enable sleep for
the worker because the PostgreSQL-backed queue requires a continuously running
consumer.

`DATABASE_URL` accepts PostgreSQL URLs from managed hosts and rewrites the
`postgres://` or `postgresql://` scheme to SQLAlchemy's asyncpg driver while
preserving the rest of the URL. It takes precedence over TOML database
coordinates. The existing `DATABASE_URL` field in `config/app.toml` remains
available for local or file-based configuration.

## Acceptance after deployment

1. Confirm the API reports healthy and the worker connects to the same
   PostgreSQL database after the migration completes.
2. From an isolated test account, upload a selectable PDF, a scanned test PDF,
   an `.md`, and a `.txt` file. Compare the PDF preview to each page and verify
   text/Markdown line breaks remain intact.
3. Start Discovery from each transcript and inspect the saved source document
   to confirm the complete text and filename reached the worker input.
4. Check malformed, encrypted, over-size, over-page-limit, and empty uploads
   return a visible error without creating a Discovery source.
5. Reset the test pipeline in Discovery, Content Architect, and Studio; verify
   the same sticky header button remains at one position and the session returns
   to empty Discovery.

Platform references: [Render Docker services](https://render.com/docs/docker),
[Render health checks](https://render.com/docs/health-checks),
[Render deploy commands](https://render.com/docs/deploys),
[Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles),
[Railway health checks](https://docs.railway.com/deployments/healthchecks), and
[Railway Compose mapping](https://docs.railway.com/guides/docker-compose).
