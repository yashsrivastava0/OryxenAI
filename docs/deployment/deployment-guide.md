# OryxenAI deployment guide (combined)

This canonical guide preserves the original deployment research, setup, runbook, acceptance, and AI-assisted operations documents in one place.

## Included source documents

- [Deployment options research](#source-01-deployment-options-research)
- [Easy Azure VM deployment](#source-02-azure-vm-runbook)
- [Deployment acceptance and operations](#source-03-acceptance-and-operations)
- [Chrome browser-agent setup](#source-05-chrome-browser-agent-azure-setup-prompt)
- [AI-assisted operations](#source-07-ai-assisted-operations)

<!-- BEGIN SOURCE: 01-deployment-options-research.md -->
<a id="source-01-deployment-options-research"></a>

# Deployment options research

Research basis: September 5, 2026, with the deployment decision and current
status refreshed on September 14, 2026. This document is intentionally focused on
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

### Why R2 instead of Azure Blob for the first release?

This is not only a price decision. The current repository already stores
artifacts and previews through an S3-compatible adapter using `boto3` and a
configurable endpoint. Cloudflare R2 exposes that S3-compatible API, so the
existing code can be used with an endpoint, bucket, access key ID, and secret
access key. See the repository adapters in
[`src/oryxenai/storage/artifacts.py`](../../src/oryxenai/storage/artifacts.py)
and [`src/oryxenai/storage/preview.py`](../../src/oryxenai/storage/preview.py).

Azure Blob Storage is a valid alternative, but its native integration uses
Azure Blob REST/SDK interfaces and Azure authorization choices. It is not a
drop-in replacement for the current `boto3` S3 endpoint configuration. Moving
would require an Azure Blob adapter, settings and credential changes, URL or
readback adjustments, tests, and another production acceptance pass.

For this two-user demo, R2's current Standard allowance includes 10 GB-month
of storage, 1 million Class A operations, and 10 million Class B operations,
with no R2 egress charge; usage is still metered. See the current
[R2 pricing](https://developers.cloudflare.com/r2/pricing/). Azure Blob is
also usage-priced by storage, operations, redundancy, and transfer; see
[Azure Blob pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/).
Using R2 leaves the Azure student credit primarily for the VM and avoids
adding another Azure storage resource and provider-specific deployment path.

Therefore the first deployment keeps R2. Azure Blob can be introduced later
if an all-Azure requirement becomes more important than preserving the
already-tested adapter boundary and the simplest initial release.

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

<!-- END SOURCE: 01-deployment-options-research.md -->

<!-- BEGIN SOURCE: 02-azure-vm-runbook.md -->
<a id="source-02-azure-vm-runbook"></a>

# Easy Azure VM deployment

This is the source-of-truth runbook for the first deployment. It uses one
Ubuntu Azure VM and Docker Compose. The repository's
`scripts/azure-deploy.sh` command installs Docker, creates the VM-local
configuration, builds the release, runs migrations, starts the worker, and
starts the Compose-managed Caddy HTTPS proxy.

You do not install Caddy separately, edit `/etc/caddy`, or run separate
commands for the app and worker.

The workflow is intentionally simple:

```text
Azure VM + Git checkout
        |
        +-- ./scripts/azure-deploy.sh setup     (one time)
        +-- ./scripts/azure-deploy.sh deploy    (every release)
        +-- ./scripts/azure-deploy.sh verify    (after DNS/HTTPS is ready)
```

**Current checkpoint (2026-09-14):** the Azure VM exists and SSH was
verified, but the repository has not been cloned there and Docker has not
been installed. Complete the release gate and external-coordinate checks
before starting the VM setup below. Do not deploy the shared dirty worktree.

Never paste real credentials into this document, GitHub issues, or an AI chat.
The script stores them only in the VM-local, ignored `.env` file.

## 1. One-time external setup

### Azure VM

Use the existing Ubuntu VM documented in
[`06-live-azure-vm-status.md`](./06-live-azure-vm-status.md), or create a
similar Ubuntu LTS VM with:

- two vCPUs and at least 4 GiB RAM; 8 GiB is more comfortable for generation;
- an SSH public key;
- a static public IP;
- a persistent OS disk.

In the VM network security group allow only:

```text
TCP 22   SSH (restrict the source IP when practical)
TCP 80   HTTP certificate issuance and redirect
TCP 443  HTTPS application traffic
```

Do not expose PostgreSQL `5432`, host port `5544`, API port `8000`, or preview
port `4174`. Compose binds those ports to the VM loopback interface.

### DNS

Create two A records pointing to the VM's static public IP:

```text
app.<DOMAIN>      <VM_STATIC_PUBLIC_IP>
preview.<DOMAIN>  <VM_STATIC_PUBLIC_IP>
```

Wait until both names resolve before running the final HTTPS check. Caddy
automatically requests and renews certificates after ports 80 and 443 are
reachable.

### Supabase

In the production Supabase project, enable Google sign-in and set:

```text
Site URL:      https://app.<DOMAIN>
Redirect URL:  https://app.<DOMAIN>/auth/callback
```

Use the exact same `https://app.<DOMAIN>` origin in the VM configuration.

### Cloudflare R2

Create one bucket for generated artifacts and previews. Keep these values
ready for the setup prompts:

- account ID;
- bucket name;
- access key ID; and
- secret access key.

The bucket endpoint is generated by the deployment script from the account ID.

### GitHub checkout access

The VM must be able to fetch the branch for future deployments. For a private
repository, the easiest repeatable option is a GitHub SSH key:

```bash
ssh-keygen -t ed25519 -C "oryxenai-azure-vm"
cat ~/.ssh/id_ed25519.pub
```

Add the displayed public key to the GitHub account or repository, then test:

```bash
ssh -T git@github.com
```

Do not share `~/.ssh/id_ed25519`; only the `.pub` file is copied to GitHub.

## 2. First SSH session

From Windows PowerShell, replace the three placeholders and connect:

```powershell
ssh -i "<PATH_TO_AZURE_PRIVATE_KEY>" <VM_USER>@<VM_STATIC_PUBLIC_IP>
```

On the VM, install the small set of bootstrap tools:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git openssl
```

Clone the exact branch selected during the release gate. Do not copy a branch
name from an old handoff without checking `git log` and `git status` first:

```bash
git clone --branch <DEPLOYMENT_BRANCH> \
  git@github.com:<GITHUB_OWNER>/<GITHUB_REPOSITORY>.git \
  ~/oryxenai
cd ~/oryxenai
chmod +x scripts/azure-deploy.sh
```

If the repository is public, an HTTPS clone URL can be used instead. For a
private repository, configure GitHub SSH access before the clone.

## 3. Run the one-time setup wizard

From `~/oryxenai`, run:

```bash
./scripts/azure-deploy.sh setup
```

The wizard will:

1. install Docker Engine and the Docker Compose plugin from Docker's official
   Ubuntu repository;
2. copy `.env.example` to the ignored `.env` file;
3. ask for the two hostnames, Supabase values, R2 values, administrator emails,
   normal-user allowlist, and a PostgreSQL password;
4. require keys used by the active routing profiles and offer optional prompts
   for the other provider keys named in `config/models.toml`; and
5. render the ignored `config/app.production.local.toml` file with the host,
   R2 account, and bucket values.

The active keys are derived from the model configuration rather than
hardcoded in the deployment script. The model/profile mapping remains in
[`config/models.toml`](../../config/models.toml), so adding an engine later
does not require changing the deployment script.

The setup wizard finishes by running `doctor`. Fix every error it reports.
Warnings about DNS can be ignored until the DNS A records have propagated.

Because Docker group membership takes effect on a new login, reconnect once
after setup if the wizard tells you to:

```bash
exit
ssh -i "<PATH_TO_AZURE_PRIVATE_KEY>" <VM_USER>@<VM_STATIC_PUBLIC_IP>
cd ~/oryxenai
```

## 4. Deploy the current branch

Run:

```bash
./scripts/azure-deploy.sh deploy
```

The command fetches the configured branch, resolves it to an exact commit,
builds the application image tagged with that commit, warms the offline npm
cache, runs PostgreSQL migrations, starts the app/worker/preview services, and
starts Caddy. The database volume is retained across deployments.

The command performs internal loopback health checks. It does not claim that
public HTTPS is ready until DNS and Caddy have had time to converge.

Then run:

```bash
./scripts/azure-deploy.sh verify
```

`verify` checks the public app and preview HTTPS endpoints. If certificates are
still being issued, wait a minute and run it again.

## 5. First browser acceptance

Open `https://app.<DOMAIN>` and complete the Google sign-in flow. Confirm:

1. the app loads over HTTPS;
2. the approved Google account can complete username onboarding;
3. the Discovery flow can be started and approved;
4. the next stage can be started explicitly;
5. the worker processes a durable job; and
6. a generated preview opens through both the app and its direct preview URL.

The detailed acceptance matrix is in
[`03-acceptance-and-operations.md`](./03-acceptance-and-operations.md).

## 6. Every future update

From the VM checkout:

```bash
cd ~/oryxenai
git status --short --branch
./scripts/azure-deploy.sh doctor
./scripts/azure-deploy.sh deploy <EXACT_RELEASE_SHA>
./scripts/azure-deploy.sh status
```

The VM checkout must not contain tracked edits. Make changes on the normal
development branch, review and commit them, push the selected release to
GitHub, and let the VM fetch that exact commit. Do not deploy a moving branch
when a release SHA is available.

To deploy a different branch once:

```bash
./scripts/azure-deploy.sh deploy <branch-name>
```

To deploy an exact commit, which is useful for a known-good rollback or an AI
generated fix:

```bash
./scripts/azure-deploy.sh deploy <40-character-commit-sha>
```

## 7. The only day-to-day commands you need

```bash
# Health and release state.
./scripts/azure-deploy.sh status
./scripts/azure-deploy.sh doctor
./scripts/azure-deploy.sh verify

# Recent logs, or selected services.
./scripts/azure-deploy.sh logs
./scripts/azure-deploy.sh logs app worker

# Edit VM-local credentials/settings and regenerate the production overlay.
./scripts/azure-deploy.sh configure

# Make a compressed PostgreSQL backup in ~/oryxenai-backups.
./scripts/azure-deploy.sh backup

# Return to the previous release recorded by the script.
./scripts/azure-deploy.sh rollback
```

Never use `docker compose down -v` for routine maintenance: `-v` removes the
PostgreSQL volume and can erase sessions and durable jobs.

If a release fails, first run `status` and `logs`. If the failure is caused by
the new application code, use `rollback`; if it is a configuration problem,
use `configure`, then `doctor`, then `deploy` again.

The rollback command rebuilds the previous application image; it does not
downgrade PostgreSQL migrations. Before rolling back across a release that
changed the database schema, check the migration history and keep the backup
created by the deployment script.

## 8. Adding a future engine

Keep the deployment contract stable. Add the engine code and its model profile
in the normal branch, add its API key name to `.env.example` if needed, and
add a Compose service only if the engine truly needs a separate process. The
next `deploy` rebuilds the tagged image and starts the new service. If the
service has a health endpoint, add its healthcheck to `compose.yaml` so
`docker compose --wait` can prove the release is ready.

The VM does not need a new deployment platform, a new manually installed
daemon, or a new deployment document for an ordinary engine addition.

## References

- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose startup order and health checks](https://docs.docker.com/compose/how-tos/startup-order/)
- [Docker Compose `up --wait`](https://docs.docker.com/reference/cli/docker/compose/up/)
- [Azure Linux VM SSH connection](https://learn.microsoft.com/en-us/azure/virtual-machines/linux-vm-connect)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)

<!-- END SOURCE: 02-azure-vm-runbook.md -->

<!-- BEGIN SOURCE: 03-acceptance-and-operations.md -->
<a id="source-03-acceptance-and-operations"></a>

# Deployment acceptance and operations

The deployment is successful only when a real user can sign in, move through
the explicit agent stages, and open the generated portfolio preview. A green
container list alone is not acceptance.

**Current checkpoint (2026-09-14):** no Azure application acceptance item in
this document has been completed yet. The VM and SSH path are ready, but the
application, Docker Compose services, production configuration, DNS, HTTPS,
and live agent-to-preview flow are still pending. Local tests and development
harness campaigns are useful evidence, but they do not check off the Azure
acceptance items below.

The supported operator interface is `./scripts/azure-deploy.sh`. It wraps the
two Compose files, keeps the production overlay generated from `.env`, and
records the last two release SHAs. Use the raw Compose commands below only
when diagnosing a problem the script output does not explain.

## A. Infrastructure smoke test

- [ ] DNS resolves `app.<DOMAIN>` and `preview.<DOMAIN>` to the VM.
- [ ] HTTPS certificates are valid.
- [ ] `https://app.<DOMAIN>/health/live` returns successfully.
- [ ] `https://app.<DOMAIN>/health/ready` reports the database ready.
- [ ] `https://preview.<DOMAIN>/health/live` returns successfully.
- [ ] PostgreSQL, app, worker, preview gateway, and Compose-managed Caddy are
  all running.
- [ ] The migration service completed successfully.
- [ ] The worker logs show a heartbeat after startup.

## B. Authentication smoke test

Use a clean browser session:

- [ ] Open `https://app.<DOMAIN>`.
- [ ] Sign in with Google.
- [ ] The callback returns to `https://app.<DOMAIN>/auth/callback`.
- [ ] The first account reaches onboarding when required.
- [ ] The account reaches `/app` after onboarding.
- [ ] A configured second user can sign in independently.
- [ ] The two bootstrap administrators can reach `/admin` if admin checks are
  being tested.

If the callback fails, check the exact Supabase Site URL, Redirect URL,
`primary_origin`, and `allowed_origins`. All four must describe the same HTTPS
application origin.

## C. Full generation acceptance

Perform this with a small, privacy-safe portfolio input first:

1. Start Discovery and wait for the worker to process it.
2. Answer the questions and approve the brief.
3. Explicitly start Content Architect and wait for its result.
4. Approve the content result.
5. Explicitly start Visual Design Director and wait for its result.
6. Approve the visual direction.
7. Explicitly start Build Preparation and confirm both Markdown briefs exist.
8. Explicitly start Code Generator.
9. Confirm the worker claims the Code Generator jobs and continues renewing
   heartbeats.
10. Wait for source generation, dependency acquisition, build checks, browser
    verification, and preview promotion to finish.
11. Open the generated preview inside the application.
12. Open the direct preview URL in a new browser tab.
13. Refresh the preview and confirm it still serves the generated portfolio.

The product intentionally does not auto-chain these stages. A caller must
start each later stage explicitly.

## D. Preview acceptance

- [ ] The preview URL uses `https://preview.<DOMAIN>/preview`.
- [ ] The preview HTML loads without an application login cookie.
- [ ] CSS, JavaScript, images, and fonts load from the preview object.
- [ ] The preview works in the application's iframe.
- [ ] The direct preview URL works in a new tab.
- [ ] A failed replacement generation does not remove the last promoted
  preview.
- [ ] The preview gateway remains healthy after the worker restarts.

The preview is public/unlisted by design. Anyone who receives its opaque URL
can open it. This deployment does not add a separate publishing product.

## E. Two-user check

- [ ] User A can create and view their own portfolio.
- [ ] User B can create and view their own portfolio.
- [ ] Refreshing either browser preserves the active session.
- [ ] The application does not require a second worker or a second VM.
- [ ] A single worker processes jobs serially without losing state.

The current application has server-side ownership and entitlement rules even
though this deployment is not being treated as a security-sensitive public
service. Do not bypass those rules in the browser while testing.

## F. Failure diagnosis

| Symptom | First check |
| --- | --- |
| App does not load | `./scripts/azure-deploy.sh status`, DNS, ports `80`/`443`, `app` and `caddy` logs |
| Auth callback fails | Supabase callback URL and exact production origin |
| App is ready but jobs do not move | `worker` logs, worker heartbeat, `/health/ready`, database connectivity |
| Build Preparation fails | R2 credentials, resource-provider keys, worker logs |
| Code Generator stops before preview | Active model profile credential, provider quota, worker memory, Code Generator logs |
| Preview promotion fails | R2 bucket/prefix, preview public URL, preview gateway logs |
| Preview opens but is blank | Preview gateway logs, generated `dist` contents, browser console, R2 object listing |
| VM becomes slow or kills the worker | VM memory, Docker stats, worker concurrency, active generation count |

Useful commands:

```bash
./scripts/azure-deploy.sh status
./scripts/azure-deploy.sh logs app worker caddy
./scripts/azure-deploy.sh verify
docker stats
```

## G. Restart and recovery checks

Perform these after the first successful generation:

- [ ] Restart the worker and confirm the application remains available.
- [ ] Restart the preview gateway and reopen the existing preview URL.
- [ ] Restart the app and confirm the database-backed session remains.
- [ ] Reboot the VM and confirm Docker services return through
  `restart: unless-stopped`.
- [ ] Confirm the PostgreSQL named volume remains present.
- [ ] Confirm preview objects remain available in R2.

For a normal restart or a code fix, use `./scripts/azure-deploy.sh deploy`.
Never use `docker compose down -v` for ordinary maintenance.

## H. Minimal backup routine

The demo can use a simple manual backup rather than a full backup platform.
Run a PostgreSQL dump before repository or migration changes:

```bash
./scripts/azure-deploy.sh backup
```

Keep the dump outside the repository and periodically copy one known-good dump
off the VM. R2 remains the source for generated preview objects; do not delete
the active preview prefix while diagnosing an application issue.

## I. Cost and lifecycle checks

Once per week while using the demo:

- [ ] Check remaining Azure student credit and VM status.
- [ ] Check that the Azure spending limit remains enabled.
- [ ] Check R2 usage and budget alerts.
- [ ] Remove temporary artifacts according to the configured lifecycle.
- [ ] Open the app periodically so the Supabase Free project does not become
  inactive.
- [ ] Record the domain renewal date.

Model-provider usage must be checked separately from Azure, Supabase, and R2.

<!-- END SOURCE: 03-acceptance-and-operations.md -->

<!-- BEGIN SOURCE: 05-chrome-browser-agent-azure-setup-prompt.md -->
<a id="source-05-chrome-browser-agent-azure-setup-prompt"></a>

# Chrome browser agent handoff: start Azure deployment from zero

This document is a copy-paste handoff for the ChatGPT Chrome/browser-control
assistant that will operate the Azure Portal with the human user. It is not a
replacement for the repository deployment runbook; it is the browser-agent
procedure for creating the first Azure VM.

## How to use this handoff

Paste the **Browser-agent mission** section into the ChatGPT sidebar/extension
after opening Azure Portal. The browser assistant must work interactively,
describe the current page, make only the requested change, and pause at the
pause points below.

The human user is the final authority for any action that creates a billable
resource. The browser assistant must never guess a changed region, VM size,
subscription, or security rule.

## Fresh-session truth

The previous browser session was lost because the PC was accidentally turned
off. Start from the Azure Portal home page with the user already logged in.

Do not assume the previous wizard state survived. Do not assume the VM exists.
The cloud resource group may have survived because it was created before the
browser session ended, so verify it in Azure before creating anything.

At the beginning of this session, the confirmed human facts are:

| Fact | Value |
| --- | --- |
| Subscription | `Azure for Students` |
| Credit | `$100 out of $100` |
| Remaining duration | `365 days` |
| Expiration shown | `05/09/2027` |
| Current Azure cost | `$0.00` |
| Intended region | `(Asia Pacific) Central India` |
| Deployment type | Small two-user OryxenAI demo |
| Current browser state | Azure Portal home page; logged in |

The browser assistant must first verify the subscription and whether
`oryxenai-demo-rg` already exists. It must not create a second resource group.

## Browser-agent mission — copy/paste this section

```text
You are the interactive Azure Portal setup assistant for the OryxenAI demo.
Use browser control to guide and fill the Azure Portal one screen at a time.

Mission:
Create exactly one Azure Linux VM for OryxenAI. The VM will later run the
existing Docker Compose stack containing PostgreSQL, migrations, FastAPI, the
durable worker, the shared preview gateway, Code Generator tooling, and Caddy.

Interaction rules:
1. Start at the Azure Portal home page. Do not assume an old wizard state.
2. Before changing anything, verify the selected subscription is Azure for
   Students and inspect whether resource group oryxenai-demo-rg already exists.
3. If oryxenai-demo-rg exists, reuse it. Do not create another resource group.
4. If a requested portal field is named differently, inspect the current UI
   and report the exact label before choosing the closest equivalent.
5. Do not silently change Central India, the VM size, x64 architecture, or the
   subscription. Ask the human before using a fallback.
6. Do not select Pay-As-You-Go, add a payment method, remove the spending
   limit, or add paid Azure services.
7. Do not create Azure Database for PostgreSQL, App Service, AKS, Load
   Balancer, Application Gateway, Front Door, or a second VM.
8. Do not ask the human to paste a password, private SSH key, model key,
   Supabase secret, R2 secret, or other production secret into chat.
9. If Azure generates an SSH private key, download it directly to the human's
   computer. Never upload, display, copy, or paste the private key into chat.
10. Pause at every pause point in this document and wait for the human to
    confirm before proceeding.
11. At the end, report the created resource names and the VM public IPv4, but
    never report or request the private SSH key contents.

Azure resource target:
- Subscription: Azure for Students
- Existing/reusable resource group: oryxenai-demo-rg
- Resource group region: Central India
- VM name: oryxenai-demo-vm
- VNet: oryxenai-demo-vnet
- VNet address space: 10.0.0.0/16
- Subnet: oryxenai-demo-subnet
- Subnet address range: 10.0.0.0/24
- NIC: oryxenai-demo-nic, if the wizard exposes the name
- Public IP resource: oryxenai-demo-ip
- Public IP: IPv4, Standard SKU, Static allocation
- NSG: oryxenai-demo-nsg

VM target:
- Region: (Asia Pacific) Central India
- Availability: No infrastructure redundancy required
- Security type: Trusted launch virtual machines
- Image: Ubuntu Server 24.04 LTS, x64 Gen2
- Architecture: x64; never Arm64
- Azure Spot: Off
- VM size: Standard_B2as_v2, 2 vCPUs, 8 GiB RAM
- Fallback only with human approval: Standard_B2als_v2, approximately 4 GiB
- Hibernation: Off
- Authentication: SSH public key
- Linux username: oryxenaiadmin
- SSH key format: Ed25519
- Generated key-pair name: oryxenai-demo-key
- Basics public inbound ports: None

Disk target:
- OS disk size: 64 GiB (E6), if the portal offers this exact choice
- OS disk type: Standard SSD (LRS)
- Encryption: Platform-managed key
- Encryption at host: Off if unavailable/not registered
- Delete OS disk with VM: On
- Ultra Disk compatibility: Off
- Additional data disks: None

Networking target:
- Public inbound rules must be exactly:
  - Priority 100, Allow-SSH-MyIP, TCP 22, source current public IPv4/32
  - Priority 110, Allow-HTTP, TCP 80, source Any
  - Priority 120, Allow-HTTPS, TCP 443, source Any
- Do not create public rules for TCP 5432, 5544, 8000, or 4174.
- Load balancing: None
- Private IP: Dynamic/default
- Delete public IP with VM: On where offered
- Delete NIC with VM: On where offered

When the VM is successfully created, stop and report:
- VM provisioning state
- VM name
- resource group
- region
- VM size
- public IPv4
- public IP resource name
- NIC resource name
- VNet/subnet names
- NSG name
- whether the three intended NSG rules exist

Do not proceed to SSH, Docker, DNS, Caddy, Supabase, R2, or application
deployment until the human explicitly starts the next phase.
```

## Detailed browser sequence

The following is the expected sequence if the browser assistant needs a
deterministic checklist.

### Pause 0 — Azure account and existing resources

From Azure Portal home:

1. Open the subscription selector or Subscriptions page.
2. Confirm the active subscription is `Azure for Students`.
3. Confirm the displayed credit is still `$100 out of $100` or record the
   changed value.
4. Confirm the spending limit/protection remains enabled.
5. Open Resource groups.
6. Search for `oryxenai-demo-rg`.
7. If it exists, open it and confirm it is in Central India.
8. If it does not exist, create exactly `oryxenai-demo-rg` in Central India.

**Pause:** report whether the resource group existed or was newly created.
Wait for confirmation before opening the VM wizard.

### 1 — Open Create a virtual machine

Open **Virtual machines → Create → Azure virtual machine**.

On the Basics tab, enter:

| Portal field | Value |
| --- | --- |
| Subscription | `Azure for Students` |
| Resource group | `oryxenai-demo-rg` |
| Virtual machine name | `oryxenai-demo-vm` |
| Region | `(Asia Pacific) Central India` |
| Availability options | No infrastructure redundancy required |
| Security type | Trusted launch virtual machines |
| Image | Ubuntu Server 24.04 LTS — x64 Gen2 |
| VM architecture | x64 |
| Run with Azure Spot discount | Off |

Do not use Windows, Arm64, Spot, or a different region without asking.

### 2 — Choose the VM size

Open the size selector and select:

```text
Standard_B2as_v2
2 vCPUs
8 GiB RAM
```

Confirm the portal estimate and show it to the human. The previously observed
estimate was approximately `$35.92`, but the current portal estimate is the
one that matters.

Do not choose the free B1s size merely because it appears in the Student Hub.
The OryxenAI generator needs more memory for Docker, Node/npm, Chromium, and
build verification.

**Pause:** confirm the size, RAM, region, subscription, and estimate before
continuing.

### 3 — Administrator account

Set:

| Portal field | Value |
| --- | --- |
| Authentication type | SSH public key |
| Username | `oryxenaiadmin` |
| SSH public key source | Generate new key pair |
| Key pair name | `oryxenai-demo-key` |
| Key type/format | Ed25519 |

If Azure offers a download button, save the private key to the human's local
Downloads folder or another private local folder. Do not open it in chat or
upload it to the browser assistant.

Set **Public inbound ports** to **None** on Basics. We will use the explicit
NSG rules on Networking instead of Azure's default global SSH rule.

### 4 — Disks tab

Set:

| Portal field | Value |
| --- | --- |
| OS disk type | Standard SSD (LRS) |
| OS disk size | 64 GiB / E6, if available |
| Key management | Platform-managed key |
| Encryption at host | Off or unavailable |
| Delete with VM | On |
| Ultra Disk compatibility | Off |
| Data disks | None |

Do not create or attach a data disk for the first demo. Generated portfolio
objects will later use R2.

### 5 — Networking tab

Set or create:

| Portal field | Value |
| --- | --- |
| Virtual network | `oryxenai-demo-vnet` |
| Address space | `10.0.0.0/16` |
| Subnet | `oryxenai-demo-subnet` |
| Subnet range | `10.0.0.0/24` |
| Public IP | `oryxenai-demo-ip` |
| IP version | IPv4 |
| Public IP SKU | Standard |
| Allocation | Static |
| NIC name | `oryxenai-demo-nic`, if exposed |
| NSG | `oryxenai-demo-nsg` |
| Load balancing | None |
| Private IP | Dynamic/default |

If Azure reports that any of these resources already exist, inspect them and
reuse them only if the names and ranges match. Do not create duplicates.

Create the NSG rules:

#### SSH rule

```text
Priority: 100
Name: Allow-SSH-MyIP
Protocol: TCP
Destination port: 22
Source: current public IPv4 address with /32
Action: Allow
```

Use Azure's **My IP** selector if available. Otherwise open a temporary new
browser tab to a plain public-IP service such as `https://api.ipify.org`, read
the IPv4 address, and enter it as `ACTUAL_IP/32`. Do not use the documentation
example `203.0.113.10/32`.

#### HTTP rule

```text
Priority: 110
Name: Allow-HTTP
Protocol: TCP
Destination port: 80
Source: Any
Action: Allow
```

#### HTTPS rule

```text
Priority: 120
Name: Allow-HTTPS
Protocol: TCP
Destination port: 443
Source: Any
Action: Allow
```

Do not add any rule for 5432, 5544, 8000, or 4174. Do not add a load
balancer, Application Gateway, or Front Door.

**Pause:** show the completed Networking summary and wait for the human to
confirm that the VNet, subnet, public IP, NSG, source IP, and three priorities
are correct.

### 6 — Management tab

Use the simplest settings:

- Monitoring/boot diagnostics: enable basic boot diagnostics if Azure offers
  it without adding a paid monitoring service.
- System-assigned managed identity: Off/not required for the first deployment.
- Auto-shutdown: Off during initial setup and acceptance testing. We will use
  Azure **Stop/Deallocate** manually when the demo is not needed.
- Backup: Off for the first two-user demo unless Azure presents a clearly free
  option and the human explicitly approves it.
- Host-based encryption: Off if shown here as well.

Do not add Azure Monitor, Defender, Backup, or other paid add-ons silently.

### 7 — Monitoring tab

Do not enable paid monitoring or Application Insights for the first setup.
Keep only the basic VM/boot diagnostics that Azure enables without a separate
service charge.

If the portal shows a cost or a new service, pause and report it instead of
accepting it.

### 8 — Advanced tab

Keep defaults unless they conflict with the target:

- Extensions: none.
- Custom data/cloud-init: none.
- Proximity placement group: none.
- Capacity reservation: none.
- Dedicated host/host group: none.
- Host encryption: off.
- No additional startup script yet.

The application setup happens after SSH access is verified; do not install
Docker through an unreviewed custom script in the VM wizard.

### 9 — Tags tab

If tags are available, add only these non-secret tags:

```text
project     = oryxenai
environment = demo
owner       = student
```

Do not put emails, passwords, API keys, SSH material, or domain credentials in
tags.

### 10 — Review + create

Open Review + create, but do not submit immediately. Check every item:

- Subscription is `Azure for Students`.
- Resource group is `oryxenai-demo-rg`.
- Region is Central India.
- VM is `oryxenai-demo-vm`.
- Image is Ubuntu 24.04 LTS x64 Gen2.
- Size is `Standard_B2as_v2`, 2 vCPU, 8 GiB.
- Trusted Launch is selected.
- Spot and hibernation are off.
- Authentication is SSH public key.
- Username is `oryxenaiadmin`.
- The key pair name is `oryxenai-demo-key`.
- OS disk is 64 GiB Standard SSD LRS.
- Delete OS disk with VM is on.
- VNet and subnet names/ranges match.
- Public IP is Standard, Static, IPv4.
- NSG has only the three intended public rules.
- No public 5432, 5544, 8000, or 4174.
- No load balancer or other paid service appears.
- The estimate is acceptable within the `$100` credit.

**Mandatory pause before Create:** show the final summary and ask the human
for explicit confirmation to create the VM. Creating the VM is the first real
Azure resource deployment and starts credit usage.

### 11 — After the human confirms Create

Click Create and wait for the deployment to finish. Do not navigate away until
Azure reports success or a clear error.

Then open the VM Overview and record:

```text
VM name
Resource group
Provisioning state
Power state
Region
VM size
Public IPv4 address
Public IP resource name
NIC name
VNet name
Subnet name
NSG name
```

Check that:

- the VM is running;
- the public IPv4 exists;
- the NSG is attached to the VM NIC;
- the three intended inbound rules are present;
- no unwanted public application/database ports are open.

**Pause:** stop here. Do not SSH, install Docker, configure DNS, configure
Supabase, configure R2, or start application deployment until the human gives
the next instruction.

## What the browser agent must not request in chat

Never request these values in the ChatGPT conversation:

```text
Azure account password
private SSH key contents
POSTGRES_PASSWORD
SUPABASE_SECRET_KEY
R2_SECRET_ACCESS_KEY
model-provider API keys
image-provider API keys
Google OAuth client secret
```

The later deployment phase will enter application secrets directly into the
VM's `.env` file. Azure resource names, subscription IDs, public IPv4, domain
names, and Git commit SHAs are non-secret operational identifiers.

## Later phases — not part of this Azure wizard session

After the VM is created and the human explicitly starts the next phase, use
the existing runbook to:

1. SSH into the VM using the downloaded private key.
2. Configure Supabase Google OAuth, the exact HTTPS callback, Cloudflare R2,
   and DNS for `app.<DOMAIN>` and `preview.<DOMAIN>`.
3. Clone the current deployment branch and make the deployment script
   executable.
4. Run `./scripts/azure-deploy.sh setup`; it installs Docker and Docker
   Compose, creates the VM-local `.env`, and renders the production TOML
   overlay.
5. Run `./scripts/azure-deploy.sh deploy`; Compose starts Caddy, PostgreSQL,
   migrations, API, worker, and preview gateway together.
6. Run `./scripts/azure-deploy.sh verify` and the complete agent-to-preview
   acceptance flow.

Caddy is Compose-managed; do not install or configure a second native Caddy
service on the VM.

The current Azure task ends after successful VM creation and public-IP
recording. Do not mix application deployment into the VM wizard unless the
human explicitly asks to continue.

<!-- END SOURCE: 05-chrome-browser-agent-azure-setup-prompt.md -->

<!-- BEGIN SOURCE: 07-ai-assisted-operations.md -->
<a id="source-07-ai-assisted-operations"></a>

# AI-assisted OryxenAI operations

The deployment is deliberately arranged so an AI coding assistant can do most
of the diagnosis and code work while you perform only the account, credential,
and final release actions.

The expanded preparation audit and open-source comparison is in the
[deployment strategy pack](<../../doc/deployment strategy/README.md>), especially
its readiness matrix, GitHub/CI plan, and AI research. Claude Code, Codex, and
OpenCode are developer/operator tools; the production application uses its
configured provider adapters and does not require a CLI session on Azure.

The safe boundary is simple:

```text
AI assistant: inspect code, edit code, run checks, explain failures
You:         provide credentials privately, approve/push the release,
             run the one deploy command, and perform browser acceptance
```

Never give an AI assistant the contents of `.env`, a private SSH key, a
Supabase secret key, an R2 secret key, or a provider API key. It can work from
`.env.example`, configuration names, redacted logs, and commit IDs.

## The repeatable release loop

Use this same loop for a bug fix, a UI change, or a future engine:

1. Ask Codex or Claude to inspect the repository and implement the change.
2. Ask it to run the smallest relevant checks, then the full project checks if
   the change is broad.
3. Review the diff and commit the change on the development branch.
4. Push the branch to GitHub.
5. SSH to the VM and run:

   ```bash
   cd ~/oryxenai
   ./scripts/azure-deploy.sh deploy <commit-sha>
   ./scripts/azure-deploy.sh status
   ./scripts/azure-deploy.sh verify
   ```

6. If the release fails, collect only redacted output with
   `./scripts/azure-deploy.sh logs app worker preview-gateway`, give that
   output to the assistant, fix the cause, and deploy the next commit.

The exact commit argument makes it clear which AI-produced change is running.
The script records the last two successful release SHAs, so
`./scripts/azure-deploy.sh rollback` is the short recovery path.

## What to ask Codex to do

Codex is useful for work inside the repository: implementation, tests,
configuration changes, code review, and release diagnosis. Start a task from
the repository root and tell it to read `AGENTS.md`, `DECISIONS.md`, and the
relevant source files before editing.

Useful prompts:

```text
Read AGENTS.md and DECISIONS.md first. Inspect the current branch and implement
<change>. Preserve unrelated worktree changes. Run the smallest relevant tests,
review the diff, and report the exact files and commit SHA. Do not read or
print .env or any secret files.
```

```text
This is an Azure VM deployment failure. Read the redacted logs below and the
deployment script/Compose files. Diagnose the smallest root cause, propose a
fix, implement it if it is in the repository, and run the relevant checks.
Do not ask for or inspect credentials.

<paste redacted output here>
```

Codex can also review a proposed release before you push it:

```text
Review this deployment diff against AGENTS.md. Check Compose service startup,
healthchecks, migrations, the worker, Caddy routing, rollback behavior, and
future engine additions. Flag only concrete release blockers and suggest the
smallest fixes.
```

## What to ask Claude Code to do

Claude Code is useful for the same repository tasks, especially a second-pass
review of a large diff or a focused diagnosis from logs. From the repository
root, ask it to preserve the same project rules:

```text
Read AGENTS.md and DECISIONS.md before making changes. Review the current
deployment diff for a one-VM Docker Compose release. Do not read .env or print
secrets. Check the exact files named below, run relevant tests, and report
concrete problems only.
```

For a non-interactive review, Claude Code can receive a prompt through its
print/non-interactive mode. Keep the prompt and log input free of secrets. Use
its normal permission controls for edits; do not grant it access to the VM's
private key or production `.env`.

Official references:

- [Codex documentation](https://learn.chatgpt.com/docs)
- [Codex use cases](https://learn.chatgpt.com/use-cases)
- [Claude Code CLI usage](https://code.claude.com/docs/en/cli-usage)
- [Claude Code getting started](https://code.claude.com/docs/en/getting-started)

## Human-only actions

Keep these actions with you:

- Azure portal changes and billing/spending-limit decisions;
- GitHub access setup on the VM;
- entering values into the VM-local `.env` during `setup` or `configure`;
- approving and pushing a commit to the deployment branch;
- running `deploy` against the intended commit; and
- the final Google sign-in and generated-preview acceptance.

Everything else should be expressible as repository code, Compose
configuration, a test, or a redacted command output that an AI assistant can
inspect and improve.

<!-- END SOURCE: 07-ai-assisted-operations.md -->
