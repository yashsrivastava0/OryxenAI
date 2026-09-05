# OryxenAI deployment

This is the simplest deployment path for the current repository when the
priority is that a user can complete the pipeline and see the generated
portfolio preview. It is designed for a very small demo, normally no more
than two active normal users, rather than for a scalable public service.

## Recommended shape

Run the repository's existing Docker topology on one Azure Linux VM. Keep the
existing Supabase Google sign-in and use one Cloudflare R2 bucket for the
artifact and preview objects.

```text
                         +----------------------+
                         | Supabase Auth        |
                         | Google sign-in       |
                         +----------+-----------+
                                    |
Browser --> app.<domain> --> Caddy --> API/UI :8000
                              |
Browser --> preview.<domain> ->+------> preview gateway :4174
                              |
                    one Azure VM / Docker Compose
                              |
       PostgreSQL --> migrate --> API + durable worker
                              |
                         Cloudflare R2
              artifacts, generated sites, preview objects
```

The VM runs PostgreSQL, the migration job, FastAPI, the durable worker, and
the shared preview gateway. The generated portfolio remains a static
artifact; it does not get its own container or deployment.

## Why this is the first deployment

- It uses the Compose topology already present in the repository.
- The worker remains a real separate process, so durable jobs and long
  Code Generator work are not hidden inside an HTTP service.
- A VM provides persistent Docker volumes for PostgreSQL and worker state.
- Supabase remains the existing authentication provider; no auth rewrite is
  needed.
- R2 matches the current hosted artifact-storage and preview-storage code.
- Caddy supplies HTTPS for the exact origin required by the current auth
  configuration.
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
3. Cloudflare R2 for hosted artifacts and previews.
4. An optional GitHub Student Pack `.me` domain. A domain is strongly
   recommended because Supabase production auth requires an exact HTTPS origin.

Model and image-provider API usage remains a separate dependency. Host credits
do not pay those provider invoices. The active logical profiles and their
credential environment-variable names remain defined by
[`config/models.toml`](../../config/models.toml) and [`.env.example`](../../.env.example).

## Cost expectations

Azure can be close to zero out of pocket while the Student credit is active,
but the VM is not a permanent free resource. The Azure account must remain
within its credit/spending limit. Supabase Free is more than enough for two
users. R2 is expected to stay within its small free allowance for a demo, but
it is usage-metered and may require a payment method. The Student Pack domain
offer normally covers the first year; renewal is not assumed to be free.

## Deployment order

For the live human/AI handoff, read the [current Azure deployment status](./04-current-azure-deployment-status.md)
before continuing the VM wizard. It is a checkpoint, not a replacement for
this general deployment plan.

Follow the documents in this order:

1. Read [the options research](./01-deployment-options-research.md) and claim
   only the accounts actually needed.
2. Follow [the Azure VM runbook](./02-azure-vm-runbook.md) to provision the VM,
   configure Supabase/R2, create the production overlay, and start Compose.
3. Execute [the acceptance and operations checklist](./03-acceptance-and-operations.md)
   before calling the deployment usable.

The old [`docs/github-student-pack-benefits.md`](../github-student-pack-benefits.md)
is background research, not the deployment source of truth. Offers and prices
must be rechecked in the provider dashboards immediately before redemption.
