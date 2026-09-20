# OryxenAI deployment strategy

Status: preparation audit recorded on 2026-09-15 20:26:26 +05:30
(Asia/Kolkata). The Azure release itself has not been executed or accepted.
The evidence-based gate is summarized in
[readiness-matrix.md](readiness-matrix.md).

This folder is the beginner-facing operator guide requested for OryxenAI. It
contains no credentials. The repository's engineering deployment documents and
the deployment script remain the source of truth for implementation details.

## The chosen deployment

Use one existing Azure Ubuntu VM with Docker Compose:

```text
Internet
   |
   +-- Caddy :80/:443
         +-- app :8000
         +-- preview-gateway :4174

PostgreSQL, worker, caches, generated artifacts, and preview data stay on the
VM's persistent Docker-backed storage. Supabase provides Google
authentication. The first release does not use Cloudflare R2.
```

This is intentionally small and reversible. It does not add Kubernetes,
Redis, a container registry, a managed database, a PaaS control plane, or
another paid Azure service.

## Storage decision: VM-local persistent storage

The first Azure release uses the VM's persistent disk for generated artifacts
and preview objects. Compose-managed volumes or bind-backed directories under
the VM's OryxenAI data root must survive container replacement and ordinary
restarts. The worker writes the generated files and the shared preview
gateway reads them; no per-portfolio container is created.

The storage handoff must include explicit ownership for the non-root app and
worker, disk-usage checks, retention/cleanup rules, a PostgreSQL dump plus
filesystem backup procedure, and a restore/readback test. Never use
`docker compose down -v` during normal operations.

Cloudflare R2 credentials, endpoints, buckets, and lifecycle checks are not
part of this first-release path. Existing R2-compatible adapters may remain as
legacy compatibility, but the production configuration must select the
available local-filesystem path before deployment. If any required artifact
contract still has no local-filesystem implementation, treat that as a
release blocker rather than silently claiming VM storage is complete.

## Current state from the repository audit

| Area | What is true | What is still required |
| --- | --- | --- |
| Product pipeline | Discovery, Content Architect, Visual Design Director, Build Preparation, and Code Generator are implemented locally. | Prove the complete flow against live providers on Azure. |
| Azure | The VM, static public IP, VNet, subnet, and restricted SSH/HTTP/HTTPS rules are documented as provisioned. | Re-check power state, current IP, Docker, and repository state before operating it. |
| Deployment tooling | `scripts/azure-deploy.sh`, production Compose, Caddy, migrations, health checks, backup, and rollback paths exist. | Run setup and deploy a clean release SHA. |
| Production configuration | `config/app.production.toml` is a template; the ignored local production overlay is rendered from VM-local values. | Create a fresh VM `.env` and render the overlay. |
| Authentication | Supabase Google-only auth, admission, ownership, and admin controls exist. | Configure production origins and complete browser acceptance. |
| Artifact and preview storage | VM-local persistent Docker-backed storage is selected for the first release. | Configure the local-filesystem providers, shared volumes, ownership, disk checks, backup/restore, restart survival, and preview readback. |
| Release | The current worktree contains unrelated uncommitted Code Generator/frontend work and untracked tool artifacts. | Reconcile contributors, run checks, and select one clean SHA. |

The last documented live VM confirmation is historical; it is not proof that
the VM is currently running. The current local `.env` is also not a production
input: it has duplicate declarations, a malformed token-like line, extra
variables, and missing deployment coordinates. Never copy it to Azure.

## Two deployment phases

### Phase A — deploy the server first

Use the future hostnames `app.deploy.me` and `preview.deploy.me` while setting
up the production configuration. DNS registration and delegation can still be
deferred. Deploy, migrate, and validate the services through VM-local health
checks. The public login and HTTPS preview are not accepted yet.

### Phase B — activate the public site later

After the stack is healthy, obtain/control `deploy.me`, add A records for the
two hostnames, configure Supabase and Google production redirects, and let
Caddy obtain certificates. Only then run external verification and the full
browser acceptance suite.

The `.me` offer in the GitHub Student Developer Pack is a convenience, not a
deployment dependency; partner offers can change. The runbook assumes the
literal `deploy.me` domain will be available to the owner.

## Release workflow

GitHub Actions already supplies the quality gate. Create a `deployment` branch
only from a clean, reviewed release commit. Do not push the present dirty
worktree. The branch is a stable release pointer; development continues on
working branches and is merged into `deployment` after checks pass.

The VM should deploy an exact commit, not an unreviewed moving branch tip:

```bash
./scripts/azure-deploy.sh deploy <commit-sha>
```

The first release uses a human-approved exact-SHA deployment over the existing
restricted SSH path. There is no automatic deploy-on-push workflow yet. This
keeps the process understandable for a small two- or three-person
installation, avoids putting a VM SSH key in GitHub, and makes a release or
rollback identifiable. A future one-click workflow is described in
[github-and-ci.md](github-and-ci.md), but it is deliberately deferred until
the first manual release works.

## Read next

- [Owner checklist](owner-checklist.md) — information and dashboard actions required from the owner.
- [Readiness matrix](readiness-matrix.md) — evidence, blockers, and release gates.
- [GitHub and CI/CD](github-and-ci.md) — branch protection and future automation.
- [AI/open-source research](ai-and-open-source-research.md) — tool comparison and safe AI policy.
- [Beginner runbook](runbook.md) — the ordered deployment procedure.
- [Operations guide](operations.md) — updates, backups, costs, rollback, and AI assistance.
- [Research sources](research-sources.md) — first-party external guidance reviewed for this strategy.

## Repository sources of truth

- [Existing deployment index](../../docs/deployment/README.md)
- [Azure VM runbook](../../docs/deployment/02-azure-vm-runbook.md)
- [Acceptance and operations](../../docs/deployment/03-acceptance-and-operations.md)
- [Live Azure status](../../docs/deployment/06-live-azure-vm-status.md)
- [AI-assisted operations](../../docs/deployment/07-ai-assisted-operations.md)
- [Deployment script](../../scripts/azure-deploy.sh)
- [Production Compose](../../compose.production.yaml)
- [Production configuration template](../../config/app.production.toml)
- [Environment template](../../.env.example)
- [Model routing configuration](../../config/models.toml)

Some older documents refer to historical Render, native-Caddy, or non-existent
code-generator paths. Prefer the files above and the current source tree when
they disagree.
