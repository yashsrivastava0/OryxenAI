# OryxenAI deployment

This document preserves the Version 1 Azure VM deployment architecture and
runbooks. Its Azure recommendation is superseded by the
[Version 2 Railway deployment strategy](./version-2/deployment-strategy.md),
which keeps the app, worker, and PostgreSQL in one Railway project and retains
Supabase Auth. Use Version 2 for a new migration; use the Azure instructions
below only to inspect or maintain the existing deployment during rollback.

## Version 1 pre-deploy note — 2026-09-14 (historical)

This 2026-09-14 snapshot said the VM and network were provisioned and the app
had not yet been started. It predates the later deployment reported in the
2026-09-30 issue ledger, so it is historical evidence only.

For the original Version 1 Azure options research, read the
[deployment strategy pack](<../../doc/deployment strategy/README.md>). For the
replacement, use the [Version 2 Railway strategy](./version-2/deployment-strategy.md).

## Consolidated deployment documents

The Version 2 replacement guide is the current recommendation. The preserved
Version 1 Azure runbooks are grouped into these documents:

- [Version 2 Railway strategy](./version-2/deployment-strategy.md) — selected
  target, service setup, Supabase changes, migration sequence, branch policy,
  cost comparison, and end-to-end acceptance.
- [Deployment guide](./deployment-guide.md) — research, setup, runbook,
  acceptance, and AI-assisted operations.
- [CI/CD runbook](./ci-cd-runbook.md) — the self-hosted GitHub Actions runner
  that deploys automatically on push, how to set it up from scratch, the
  real SSH key and Windows-permission gotchas hit while building it, and how
  to re-add an approval gate.
- [VM-local storage runbook](./vm-local-storage-runbook.md) — bind-mounted
  paths, ownership, capacity, retention, backup/restore, and persistence
  checks for the first release.
- [Deployment status and history](./deployment-status-and-history.md) — Azure
  status checkpoints and the live deployment session log.
- [VM cost automation](./vm-cost-automation.md) — the daily auto-shutdown
  (01:00 IST) / auto-start (07:00 IST) schedule, why that window, and the
  Logic App implementation detail. The VM is intentionally unreachable
  during that window every day — read this before assuming it's down.
- [Document intake and managed-container deployment](./document-extraction.md)
  — PDF/text extraction strategy, bundled offline OCR assets, and the API,
  worker, database, and migration settings for Render or Railway.

The numbered files below remain compatibility entry points for older links;
their complete content is preserved in the two canonical documents.

The original Version 1 checkpoint pointed to the Compose path and
scripts/azure-deploy.sh. Its working-tree and deployment status are stale.
For Azure rollback, verify the live VM and database before using the
[Azure checkpoint](./06-live-azure-vm-status.md) and
[VM runbook](./02-azure-vm-runbook.md).

## Version 1 selected shape (historical)

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

## Why Version 1 used the Azure VM (historical)

- It uses the Compose topology already present in the repository.
- The worker remains a real separate process, so durable jobs and long-running
  model calls can continue while the API handles requests.
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

## Version 1 preview expectation (historical)

The deployed preview is intentionally public by possession of its opaque URL.
It is not an authenticated preview and it is not a public publishing system.
That matches the goal for this deployment: the user should be able to open the
generated portfolio immediately from the application and from the direct
preview URL.

## Version 1 external services (historical)

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

## Version 1 cost expectations (historical)

Azure can be close to zero out of pocket while the Student credit is active,
but the VM is not a permanent free resource. The Azure account must remain
within its credit/spending limit. Supabase Free is more than enough for two
users. VM disk capacity, backups, and retention are the storage cost and
reliability considerations. The Student Pack domain offer normally covers the
first year; renewal is not assumed to be free.

## Version 1 deployment order (historical)

The steps below apply only if maintaining the old Azure deployment or using
it during rollback. For the replacement migration order, use the
[Version 2 Railway strategy](./version-2/deployment-strategy.md).

For a new Azure VM wizard, use the historical
[pre-provisioning checkpoint](./04-current-azure-deployment-status.md) and the
[Chrome browser-agent setup prompt](./05-chrome-browser-agent-azure-setup-prompt.md).
The Version 1 note said the wizard was complete for that VM; verify live Azure
state before acting and do not create duplicate resources during rollback.

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

## Current source Studio deployment notes

- The Studio needs only the web process, the worker and PostgreSQL: bundles are
  stored in PostgreSQL and theme files ship inside the image, so no object store
  or shared volume is required. Any container host works; a serverless platform
  can host the static frontend only, because the worker needs a long-lived process.
- `PREVIEW_GRANT_SECRET` (32+ random characters) is optional. Set it when more than
  one API instance serves previews or when preview links should survive a restart.
- Browser verification is off in the deployment overlays because the default image
  has no browser. To enable it, build with `--build-arg INSTALL_CHROMIUM=true` and set
  `[code_generator.verification] browser = "best_effort"` (or `"required"`) in the
  overlay. A host that cannot start the browser records that in the page receipt
  and still publishes in `best_effort`.
