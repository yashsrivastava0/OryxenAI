# Deployment options research

Research basis: September 5, 2026. This document is intentionally focused on
a first deployment for a very small demo where the main success criterion is
that the complete agent-to-preview flow works.

## Decision

Use one Azure Linux VM with the repository's Docker Compose stack, Supabase
Google authentication, Cloudflare R2, and an optional Student Pack domain.

This is the best fit because the current application is not one stateless web
process. It is an API, a PostgreSQL-backed durable queue, a separate worker,
and a separate preview gateway. The worker can run long Code Generator stages,
and the preview gateway must read generated artifacts after a container or
process restart.

## Current Student Pack facts

Use the live [GitHub Student Pack offers catalog](https://education.github.com/pack/offers)
as the authority immediately before activation.

Relevant offers currently visible in the catalog include:

| Offer | Use here | Important limitation |
| --- | --- | --- |
| Microsoft Azure | VM credits and other Azure services | Eligibility, credit expiry, and educational/noncommercial terms apply |
| Heroku | Alternative hosted application credit | Does not map cleanly to the current API + worker + preview topology |
| Namecheap | One `.me` domain and related introductory offer | Domain renewal after the offer period is not assumed to be free |
| GitHub Pages | Future static hosting for a separately published site | Cannot run the OryxenAI API, worker, or preview gateway |

The current official catalog should be checked rather than relying on older
repository notes about DigitalOcean. If a personal dashboard shows a legacy
DigitalOcean credit, it can be considered a fallback, but it is not part of
this plan.

## Provider comparison

| Provider/path | Fit for this repository | Decision |
| --- | --- | --- |
| **Azure VM** | One machine can run the existing Compose topology, persistent volumes, Chromium, Node, API, worker, and gateway | **Selected** |
| Heroku | Student credit is useful, but low-cost dyno/process limits, ephemeral filesystem, and worker/preview separation add changes | Reject for first deployment |
| Render Free | Free web services sleep, free disks are ephemeral, free PostgreSQL expires, and there is no suitable free Background Worker | Reject |
| Railway | Very easy Docker deployment, but post-trial free resources are too small for the generator and the project/service limits make the topology awkward | Temporary experiment only |
| Supabase-hosted PostgreSQL | Good managed database, but the current settings and Compose flow are VM/PostgreSQL-oriented; moving it adds connection-pooling and migration work | Keep Supabase for Auth only initially |
| Cloudflare R2 | S3-compatible storage matches the current artifact and preview adapters; small demo usage should fit the free allowance | Use |
| Cloudflare Workers | Cheap edge hosting, but the current Python preview gateway would need a rewrite and the worker has tight CPU/memory limits | Reject |
| GitHub Pages | Static-only | Future optional output host, not the application host |

## Azure choice

[Azure for Students](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students)
provides a limited credit offer without requiring a credit card for eligible
students. The [Azure student page](https://azure.microsoft.com/en-us/free/students)
also lists small free service allowances, but the smallest VM sizes are too
memory-constrained for a Docker image that includes Python, Node/npm,
Chromium, and Code Generator verification.

Choose a currently available VM with 2 vCPUs and at least 4 GiB RAM; 8 GiB is
the preferred target. A B-series size such as `B2as_v2` or `B2als_v2` may be
appropriate when available, but the Azure portal's current regional SKU and
price are authoritative. Do not remove the Azure spending limit merely to
keep the VM running: when a credit/spending limit is reached, resources may
stop rather than silently generating a bill. See [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).

## Why not Heroku despite the Student Pack credit?

Heroku's [Student offer](https://www.heroku.com/students/) is attractive, but
the repository needs API, worker, preview gateway, and durable storage. Heroku
dyno filesystems are ephemeral, and its low-cost plans restrict process
capacity. The current Docker Compose contract explicitly expects a worker and
shared object-backed preview storage. Making Heroku work would require a
custom worker arrangement and additional storage changes, increasing first
deployment risk.

## Why not Render Free?

Render's [free instance documentation](https://render.com/docs/free) describes
sleeping free web services and ephemeral filesystems. Render's service model
does not provide the free background-worker shape required by the existing
durable queue. Its free PostgreSQL option is also time-limited. The result
would be a provider-specific workaround rather than a simple deployment.

## Why not Railway as the final choice?

Railway is convenient for Docker, but its [free trial and free plan](https://docs.railway.com/pricing/free-trial)
are time/resource limited. After the trial, per-service memory and project
limits are not a comfortable match for this image and its three long-running
services. It remains useful for a short throwaway test, not the stable first
deployment.

## Supabase and R2 roles

Supabase Free is sufficient for Google identity and two users; see
[Supabase pricing](https://supabase.com/pricing). Use a separate production
Supabase project so local and deployed OAuth settings do not interfere. Free
projects can pause after inactivity, so open the deployed app periodically or
restore the project when needed; see [Supabase free-project pausing](https://supabase.com/docs/guides/platform/free-project-pausing).

Keep PostgreSQL on the VM for the first deployment. The application already
expects the durable queue and application state to be in the same PostgreSQL
deployment, and the current Docker migration service is ready for that shape.

Use a private R2 bucket for:

- temporary Build Preparation material where configured;
- generated source/build artifacts; and
- promoted preview objects under the configured preview prefix.

R2 currently advertises a free Standard storage/operation allowance and free
internet egress; see [R2 pricing](https://developers.cloudflare.com/r2/pricing/).
R2 is still usage-metered and may require a payment method. Configure a budget
alert and a short lifecycle for temporary objects; see [R2 billing policy](https://developers.cloudflare.com/billing/understand/billing-policy/).

## What remains outside host credits

Azure, Supabase, and R2 do not automatically cover:

- model provider requests;
- Pexels, Pixabay, or other image-provider quotas;
- model-generated image/font/component downloads when configured;
- domain renewal after the Student Pack period; or
- optional observability and email services.

The deployment runbook therefore never hardcodes a model or provider. It
points to `config/models.toml` and requires the environment variables named by
the active profiles.

## Final tradeoff

This path uses a few external accounts, but it minimizes moving parts inside
the application. The VM is intentionally simple: one place to run, inspect,
restart, and back up. The user experience remains the existing product flow,
and the preview is served by the existing shared gateway rather than by a new
publishing platform.
