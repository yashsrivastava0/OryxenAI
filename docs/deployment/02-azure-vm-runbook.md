# Azure VM deployment runbook

This runbook deploys the current repository to one Ubuntu Linux VM. It is
written for a first deployment and deliberately uses a small number of
services.

Replace these placeholders before running commands:

```text
<DOMAIN>        the registered domain, for example oryxenai.me
<APP_HOST>      app.<DOMAIN>
<PREVIEW_HOST>  preview.<DOMAIN>
<RELEASE_SHA>   the Git commit to deploy
```

Do not put real secrets in this document, GitHub, or chat messages.

## 1. Create the external accounts first

### Azure

1. Activate Azure for Students from the GitHub Student Pack or the Azure
   student portal.
2. Keep the subscription spending limit enabled.
3. Create one Linux VM in a region where a suitable SKU is available:
   - Ubuntu LTS;
   - 2 vCPUs;
   - at least 4 GiB RAM, preferably 8 GiB;
   - SSH public-key authentication;
   - a static public IP;
   - a persistent OS disk.
4. Configure the VM network security group with only:
   - TCP `22` for SSH;
   - TCP `80` for HTTP certificate issuance/redirect;
   - TCP `443` for the application and preview.

Do not add public rules for PostgreSQL `5432`, host port `5544`, API port
`8000`, or preview port `4174`. Caddy will proxy those services locally.

The VM creation workflow is documented in Microsoft's [Linux VM quickstart](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli).

### Supabase

Create a separate production project and enable Google as the only sign-in
provider. In the Supabase URL configuration, set:

```text
Site URL:     https://<APP_HOST>
Redirect URL: https://<APP_HOST>/auth/callback
```

The deployed application origin must be exact. Do not use localhost values in
the production configuration.

### Cloudflare R2

Create one private bucket for OryxenAI artifacts and previews. Record:

- the account ID and S3-compatible endpoint;
- bucket name;
- access key ID; and
- secret access key.

Use a token/key scoped to this bucket. The endpoint has the shape:
`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.

### Domain

If using the GitHub Student Pack domain offer, create DNS records:

```text
A  app.<DOMAIN>      <VM_STATIC_PUBLIC_IP>
A  preview.<DOMAIN>  <VM_STATIC_PUBLIC_IP>
```

DNS must resolve before Caddy can obtain certificates.

## 2. Prepare the VM

SSH into the VM:

```bash
ssh <vm-user>@<VM_STATIC_PUBLIC_IP>
```

Install Git, Docker, and Caddy. Use the current vendor instructions if the
Ubuntu image has moved to a newer release:

- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Caddy on Debian/Ubuntu](https://caddyserver.com/docs/install#debian-ubuntu-raspbian)

Then verify:

```bash
docker --version
docker compose version
caddy version
```

Add the deployment user to the Docker group and start a new SSH session:

```bash
sudo usermod -aG docker "$USER"
exit
```

## 3. Check out one release

Clone the repository with GitHub SSH or another non-interactive GitHub
credential method:

```bash
git clone <REPOSITORY_URL> ~/oryxenai
cd ~/oryxenai
git fetch --tags --prune
git checkout --detach <RELEASE_SHA>
```

Record the SHA in the deployment notes. Deploying a pinned commit makes a
rollback unambiguous.

## 4. Create the production environment

Start from the repository template:

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Fill only real values. Required values include:

```text
POSTGRES_PASSWORD
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
ORYXENAI_ADMIN_BOOTSTRAP_EMAILS
ORYXENAI_ALLOWED_USER_EMAILS
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
```

Put exactly the two bootstrap administrator emails in
`ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`. Put the normal-user emails that should be
able to use the demo in `ORYXENAI_ALLOWED_USER_EMAILS`. The current auth
implementation requires two bootstrap administrators even when the practical
demo has only two normal users.

Add the model and image-provider keys required by the profiles you intend to
run. Read the profile's `api_key_env` in [`config/models.toml`](../../config/models.toml);
do not guess a model name or provider key name.

## 5. Create the production TOML overlay

The checked-in `config/app.docker.toml` is Docker-shaped but still contains
localhost preview values and disables final Code Generator verification. Create
an uncommitted VM-local file at `config/app.production.toml` with this content,
replacing the domain and R2 values:

```toml
[app]
env = "production"
host = "0.0.0.0"
enable_dev_ui = false
enable_product_preact_shell = true

[auth]
required = true
pipeline_mode = "attached"
development_harness_mode = "attached"
admission_mode = "allowlist"
primary_origin = "https://<APP_HOST>"
allowed_origins = ["https://<APP_HOST>"]

[worker]
concurrency = 1

[artifact_storage]
provider = "r2_s3"
endpoint_url = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"
bucket = "<R2_BUCKET>"
region = "auto"
prefix = "temporary"
require_lifecycle = true

[build_preparation]
fixture_enabled = false
debug_mirror_enabled = false

[code_generator_development]
enabled = false

[code_generator_verification]
enabled = true
preview_base_url = "https://<PREVIEW_HOST>/preview"
preview_health_url = "http://preview-gateway:4174/health/live"
preview_host = "0.0.0.0"
preview_port = 4174
preview_parent_origin = "https://<APP_HOST>"
preview_embed_origins = ["https://<APP_HOST>"]
preview_storage_provider = "artifact_storage"
preview_storage_prefix = "preview"
preview_public_readback_required = true
```

This file is deployment configuration, not a secret store. Keep real
credentials in `.env`; do not commit this VM-local file if it contains
account-specific values.

## 6. Make Compose use the production overlay

Create an uncommitted `compose.production.yaml` on the VM:

```yaml
services:
  migrate:
    environment:
      OryxenAI_CONFIG_OVERLAY: config/app.production.toml
  app:
    environment:
      OryxenAI_CONFIG_OVERLAY: config/app.production.toml
  worker:
    environment:
      OryxenAI_CONFIG_OVERLAY: config/app.production.toml
  preview-gateway:
    environment:
      OryxenAI_CONFIG_OVERLAY: config/app.production.toml
```

The existing Compose file still runs the required topology. Its host ports
remain available to the VM, but only ports `80`, `443`, and restricted SSH
should be allowed through the Azure network security group.

## 7. Build and start the stack

From the repository root:

```bash
docker compose -f compose.yaml -f compose.production.yaml \
  build migrate app worker preview-gateway

docker compose -f compose.yaml -f compose.production.yaml \
  up -d migrate app worker preview-gateway

docker compose -f compose.yaml -f compose.production.yaml ps
```

Expected state:

- `postgres` is healthy;
- `migrate` exits successfully;
- `app` is running and healthy;
- `worker` is running;
- `preview-gateway` is running and healthy.

Check the internal service logs:

```bash
docker compose -f compose.yaml -f compose.production.yaml \
  logs --tail 200 migrate app worker preview-gateway
```

## 8. Configure Caddy

Edit `/etc/caddy/Caddyfile`:

```caddyfile
app.<DOMAIN> {
    reverse_proxy 127.0.0.1:8000
}

preview.<DOMAIN> {
    reverse_proxy 127.0.0.1:4174
}
```

Validate and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Caddy obtains and renews HTTPS certificates after DNS and ports `80`/`443`
are working.

## 9. Verify the service before signing in

From any machine with internet access:

```bash
curl -fsS https://<APP_HOST>/health/live
curl -fsS https://<APP_HOST>/health/ready
curl -I https://<APP_HOST>/
curl -I https://<PREVIEW_HOST>/health/live
```

PowerShell equivalent:

```powershell
Invoke-RestMethod https://<APP_HOST>/health/live
Invoke-RestMethod https://<APP_HOST>/health/ready
Invoke-WebRequest -UseBasicParsing https://<APP_HOST>/
Invoke-WebRequest -UseBasicParsing https://<PREVIEW_HOST>/health/live
```

If `/health/ready` fails, inspect the app and migration logs before trying the
browser flow.

## 10. Deploy updates

Use a pinned commit and rebuild the image:

```bash
cd ~/oryxenai
git fetch --tags --prune
git checkout --detach <NEW_RELEASE_SHA>

docker compose -f compose.yaml -f compose.production.yaml \
  build migrate app worker preview-gateway
docker compose -f compose.yaml -f compose.production.yaml \
  up -d migrate app worker preview-gateway
```

Do not run `docker compose down -v`. The `-v` option removes the PostgreSQL
volume and can erase sessions and durable jobs.

For a rollback, check out the previous known-good SHA, rebuild, and run the
same commands. Do not roll back across an irreversible database migration
without first checking the migration history.

## 11. Basic recovery commands

```bash
# Show service state.
docker compose -f compose.yaml -f compose.production.yaml ps

# Restart only the application processes.
docker compose -f compose.yaml -f compose.production.yaml restart app worker preview-gateway

# Follow worker activity.
docker compose -f compose.yaml -f compose.production.yaml logs -f worker

# Stop the application without removing data.
docker compose -f compose.yaml -f compose.production.yaml stop app worker preview-gateway
```

If the VM runs out of memory during generation, stop the worker, confirm the
VM size, and retry with the worker still configured at concurrency `1`. Do not
create another worker: the application already has a global model-generation
lane.
