# Free-host deployment contract

This is the deployment contract for the OryxenAI backend and Code Generator
preview. It is intentionally separate from the local development workflow:
development uses local filesystem mirrors, while a hosted service must treat
the container filesystem as disposable.

## What Docker is used for

Docker packages OryxenAI's backend toolchain in one reproducible image:

- FastAPI API process;
- PostgreSQL migration command;
- durable PostgreSQL worker process;
- Chromium/Node toolchain used by Code Generator verification; and
- the shared preview-gateway process.

The generated portfolio is not a Docker application. A successful run produces
a normal portable Vite/React project and a verified `dist/` directory. The
gateway serves that static `dist/` from private object storage. There is no
Dockerfile, per-portfolio image, container, long-running development server,
or public deployment created for each user generation.

## Hosted data ownership

| Data | Development | Hosted requirement |
| --- | --- | --- |
| durable jobs and run state | PostgreSQL | managed PostgreSQL |
| candidate files, receipts, and active pointer | local preview root | private S3-compatible storage (R2/S3) |
| source/checkpoint workspace | `.workspace/` | disposable container filesystem |
| developer export | `output/code-gen-output/` | disposable debug mirror or explicitly configured object storage |
| user-visible preview | local shared gateway | shared gateway URL on a separate preview origin |

`preview_storage_provider = "local_fs"` is the development default. The
Docker deployment overlay uses `"artifact_storage"`, which reuses the existing
private S3-compatible coordinates and credentials while writing under the
`preview/` prefix. Missing hosted storage configuration or credentials is a
readiness failure; the service must not silently fall back to local disk.

## Render-like free services

The minimum hosted topology is:

```text
managed PostgreSQL
        |
API web service (Docker) ---- private preview bucket
        |                              |
durable worker process (same image)   shared preview gateway web service
```

The API and worker continue to use separate processes in the normal Docker
topology. If a selected free provider cannot run a background worker, that is
an infrastructure limitation, not a reason to create one Docker container per
portfolio. Use a provider-supported worker-capable service, or an explicitly
configured web-service worker wrapper that binds the provider's required
`$PORT` and is monitored as a worker. Do not claim hosted readiness until the
worker is actually consuming jobs and renewing heartbeats.

Render's free web services sleep after inactivity and have an ephemeral
filesystem; its free plan also does not provide a free Background Worker. The
deployment therefore must keep all durable state in managed PostgreSQL and
object storage, and must accept cold-start latency. See Render's [free
instance limitations](https://render.com/docs/free) and [service types in the
Blueprint specification](https://render.com/docs/blueprint-spec). Render web
services can run the repository Docker image; the worker topology still needs
an available worker runtime or an explicit provider-compatible wrapper. See
[Render web services](https://render.com/docs/web-services).

Vercel-like static deployment can host a separately published `dist/`, but it
is optional and is not the OryxenAI preview source of truth. The product
preview remains the shared gateway URL, because it preserves one stable host,
receipt/hash validation, active-preview continuity during failed regeneration,
and private candidate storage. Function runtimes are not used as the durable
worker.

## Preview request lifecycle

1. Code Generator writes source into a disposable workspace.
2. It runs source, build, and DOM/runtime verification.
3. Only the verified `dist/` files and receipts are uploaded immutably.
4. A conditional active pointer is promoted for the user's opaque preview
   host.
5. The application embeds the shared preview URL in a sandboxed cross-origin
   iframe.

A failed generation leaves the prior active preview unchanged. A preview URL
does not imply that the portfolio has been publicly deployed or that its
source is public.

## Current development boundary

No hosted deployment is performed by the Code Generator development workflow.
Local development continues to use `local_fs`, the checked-in preview gateway,
and `output/code-gen-output` as a debug export. This contract is verified by
unit tests and configuration; live hosted acceptance still requires a real
managed database, object-storage credentials, worker runtime, and public
preview-origin smoke test.
