# OryxenAI deployment

This is the simplest deployment path for the current repository when the
priority is that a first-time deployer can complete the pipeline and see the
generated portfolio preview. It is designed for a very small demo, normally
no more than two active normal users, rather than for a scalable public
service.

## Current status — 2026-09-14

The Azure VM and its network were provisioned, and SSH access was verified.
The application has **not** been deployed to Azure: Docker, the repository,
PostgreSQL, migrations, Caddy, the worker, and the preview gateway have not
yet been started on the VM.

For the current beginner-facing GitHub, Azure, authentication, model-runtime,
VM-storage, and deferred-domain readiness analysis, read the
[deployment strategy pack](<../../doc/deployment strategy/README.md>) before
using this historical deployment index.

## Consolidated deployment documents

The canonical deployment material is grouped into two documents:

- [Deployment guide](./deployment-guide.md) — research, setup, runbook,
  acceptance, and AI-assisted operations.
- [VM-local storage runbook](./vm-local-storage-runbook.md) — bind-mounted
  paths, ownership, capacity, retention, backup/restore, and persistence
  checks for the first release.
- [Deployment status and history](./deployment-status-and-history.md) — Azure
  status checkpoints and the live deployment session log.

The numbered files below remain compatibility entry points for older links;
their complete content is preserved in the two canonical documents.

The repository now contains the guided production Compose path and
`scripts/azure-deploy.sh`, but the shared development worktree is not clean.
Select and record an exact reviewed Git commit before deploying. Read the
[current project status](../project-status.md) first, then use the
[live Azure checkpoint](./06-live-azure-vm-status.md) and
[easy VM runbook](./02-azure-vm-runbook.md).

## Recommended shape

Run the repository's existing Docker topology on one Azure Linux VM. Keep the
existing Supabase Google sign-in and store generated artifacts and preview
objects on persistent VM-local Docker storage.

```text
                         +----------------------+
                         | Supabase Auth        |
                         | Google sign-in       |
                         +----------+-----------+
                                    |
Browser --> app.<domain> --> Caddy (Compose) --> API/UI :8000
                              |
Browser --> preview.<domain> ->+------> preview gateway :4174
                              |
                    one Azure VM / Docker Compose
                              |
       PostgreSQL --> migrate --> API + durable worker
                              |
                  VM persistent storage
              artifacts, generated sites, preview objects
```

The VM runs PostgreSQL, the migration job, FastAPI, the durable worker, the
shared preview gateway, and Caddy as Compose services. The generated
portfolio remains a static artifact; it does not get its own container or
deployment.

## Why this is the first deployment

- It uses the Compose topology already present in the repository.
- The worker remains a real separate process, so durable jobs and long
  Code Generator work are not hidden inside an HTTP service.
- A VM provides persistent Docker volumes for PostgreSQL and worker state.
- Supabase remains the existing authentication provider; no auth rewrite is
  needed.
- VM-local storage removes an external object-storage account from the first
  release; the production configuration must select the existing local-
  filesystem path and share the required volumes between worker and gateway.
- Compose-managed Caddy supplies HTTPS for the exact origin required by the
  current auth configuration, so there is no second native service to
  configure on the VM.
- There is no Kubernetes, Redis, Celery, per-portfolio hosting, or separate
  provider for each internal process.

## Preview expectation

The deployed preview is intentionally public by possession of its opaque URL.
It is not an authenticated preview and it is not a public publishing system.
That matches the goal for this deployment: the user should be able to open the
generated portfolio immediately from the application and from the direct
preview URL.

## External services

The smallest practical setup has these accounts:

1. Azure for the VM. Azure for Students provides a time-limited credit offer;
   keep its spending limit enabled. See the [Azure VM runbook](./02-azure-vm-runbook.md).
2. Supabase for Google authentication.
3. An optional GitHub Student Pack `.me` domain. A domain is strongly
   recommended because Supabase production auth requires an exact HTTPS origin.

Model and image-provider API usage remains a separate dependency. Host credits
do not pay those provider invoices. The active logical profiles and their
credential environment-variable names remain defined by
[`config/models.toml`](../../config/models.toml) and [`.env.example`](../../.env.example).

## Cost expectations

Azure can be close to zero out of pocket while the Student credit is active,
but the VM is not a permanent free resource. The Azure account must remain
within its credit/spending limit. Supabase Free is more than enough for two
users. VM disk capacity, backups, and retention are the storage cost and
reliability considerations. The Student Pack domain offer normally covers the
first year; renewal is not assumed to be free.

## Deployment order

For a new Azure VM wizard, use the historical
[pre-provisioning checkpoint](./04-current-azure-deployment-status.md) and the
[Chrome browser-agent setup prompt](./05-chrome-browser-agent-azure-setup-prompt.md).
The wizard is already complete for the current VM, so do not restart it or
create a duplicate resource group.

If the browser session has been lost or restarted, use the detailed [Chrome
browser-agent Azure setup prompt](./05-chrome-browser-agent-azure-setup-prompt.md)
from Azure Portal home. It includes the interaction protocol, pause points,
exact portal values, and the post-creation stopping point.

After the VM is created, use the [live Azure VM status checkpoint](./06-live-azure-vm-status.md)
as the current source of truth. The older [`04-current-azure-deployment-status.md`](./04-current-azure-deployment-status.md)
file is retained as historical pre-provisioning context. For the whole
implemented/pending/next-state picture, use [`docs/project-status.md`](../project-status.md).
For the lossless chronological record of the portal work, SSH session,
bootstrap commands, corrections, and unconfirmed steps, use the
[live Azure deployment session log](./08-live-azure-deployment-session-log-2026-09-14.md).

Follow the documents in this order:

1. Read [the options research](./01-deployment-options-research.md) and claim
   only the accounts actually needed.
2. Follow [the easy Azure VM runbook](./02-azure-vm-runbook.md) to configure
   Supabase and VM-local storage, then run the one-time setup wizard followed
   by one deploy command.
3. Execute [the acceptance and operations checklist](./03-acceptance-and-operations.md)
   before calling the deployment usable.

For routine maintenance, the only command family needed on the VM is:

```bash
./scripts/azure-deploy.sh status
./scripts/azure-deploy.sh logs
./scripts/azure-deploy.sh deploy <EXACT_RELEASE_SHA>
./scripts/azure-deploy.sh verify
```

The deployment script is the operational source of truth. The checked-in
Compose files remain the infrastructure source of truth, and the ignored
`.env` plus `config/app.production.local.toml` hold VM-specific values.

For the lowest-effort coding and incident workflow, use the
[AI-assisted operations guide](./07-ai-assisted-operations.md) with Codex or
Claude Code. It includes copyable prompts and the rule for sharing only
redacted logs.

The old [`docs/github-student-pack-benefits.md`](../github-student-pack-benefits.md)
is background research, not the deployment source of truth. Offers and prices
must be rechecked in the provider dashboards immediately before redemption.
