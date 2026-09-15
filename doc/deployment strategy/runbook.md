# Beginner deployment runbook

Follow the phases in order. A phase is not complete because containers merely
start; use its stated checks.

## 0. Release gate on the development machine

The current worktree is dirty. Treat its existing tracked Code Generator and
frontend changes, migrations, tests, and untracked tool directories as another
contributor's work. Do not stage them while preparing deployment.

First reconcile those changes with their contributor and select one release
commit. Then run the project checks appropriate to the release:

```powershell
git status --short --branch
git diff --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Run the frontend checks/build and the merged production Compose validation as
well. On Linux or CI, syntax-check `scripts/azure-deploy.sh`; the Windows
shell cannot replace that validation.

After the tree is clean and the SHA has passed review, create and publish the
release branch:

```powershell
git switch -c deployment <CLEAN_SHA>
git push -u origin deployment
```

Do not use `git add .` or include `.env`, caches, `node_modules`, build output,
`.kiro`, `.playwright-mcp`, or another contributor's unreviewed work.

## 1. Check Azure and connect

1. Open the Azure portal and confirm the existing VM is not deleted. If it is
   paused, start it and record the current public IP from the portal.
2. Confirm the SSH network rule allows port 22 only from the current trusted
   public IP. Keep ports 5432, 5544, 8000, and 4174 private.
3. Confirm the Azure for Students balance and expiration date. Keep the
   spending limit enabled unless the owner knowingly accepts pay-as-you-go
   billing.
4. From PowerShell, connect with the private key:

   ```powershell
   ssh -i "<path-to-private-key>" oryxenaiadmin@<current-vm-ip>
   ```

## 2. Install the repository and Docker

On the VM, clone the private repository using the approved read-only access
method, check out `deployment`, and enter the repository:

```bash
git clone <repository-ssh-or-https-url>
cd <repository-directory>
git switch deployment
chmod +x scripts/azure-deploy.sh
```

Run the guided setup. It installs Docker Engine and Compose from Docker's
official Ubuntu repository, creates the VM-local `.env`, and renders the
ignored production configuration:

```bash
./scripts/azure-deploy.sh setup
```

When prompted, enter `app.deploy.me` and `preview.deploy.me` even though DNS
will be configured later. Enter all other values from the owner checklist
privately. The script generates the PostgreSQL password and discovers active
model keys from `config/models.toml`.

If `.env` already exists, stop and inspect it privately. Do not overwrite it
blindly and do not copy the developer machine's `.env`.

## 3. Run the deployment preflight

```bash
./scripts/azure-deploy.sh doctor
```

Resolve every error before continuing. DNS warnings are expected during Phase
A because the domain has intentionally not been activated. Check that the
production overlay contains concrete hostnames and R2 coordinates and that the
VM-local `.env` has restrictive permissions.

## 4. Deploy the server before the domain

Deploy the exact release SHA selected in Step 0:

```bash
./scripts/azure-deploy.sh deploy <CLEAN_SHA>
./scripts/azure-deploy.sh status
```

The script builds the pinned application image on the VM, warms the offline
npm cache, starts PostgreSQL, applies Alembic migrations, starts the API,
worker, preview gateway, and Caddy, and waits on their health checks.

Before DNS is configured, validate the private VM-local endpoints:

```bash
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:4174/health/live
```

Also inspect the worker and service state:

```bash
./scripts/azure-deploy.sh status
./scripts/azure-deploy.sh logs worker
```

This is an infrastructure milestone, not public acceptance. Google login,
public HTTPS, and external preview URLs remain pending.

## 5. Activate `deploy.me` later

After Phase A is healthy:

1. Register or claim `deploy.me` through the current GitHub Student Developer
   Pack offer or the chosen registrar.
2. Add `app.deploy.me` and `preview.deploy.me` A records to the VM's static
   public IP.
3. Configure Supabase Site URL and the exact application callback.
4. Configure the Google OAuth web origin and the exact Supabase provider
   callback URL.
5. Wait for DNS propagation and Caddy's automatic HTTPS certificates.
6. Run:

   ```bash
   ./scripts/azure-deploy.sh verify
   ```

If Caddy reports certificate errors, check DNS, port 80/443 NSG rules, the
public IP, and Caddy logs before changing application code.

## 6. Public acceptance

Use a clean browser session and verify:

- Google sign-in, provider admission, username onboarding, and admin access.
- A normal user can use the intended portfolio flow.
- Discovery approval explicitly hands off to Content Architect, Visual Design
  Director, Build Preparation, and Code Generator.
- Code Generator creates a verified preview and R2 readback succeeds.
- The preview works embedded and at its direct URL after refresh.
- A second account cannot see or mutate the first account's portfolio.
- Post-success read-only behavior, worker retries, and diagnostics are honest.

Record failures with redacted logs and the exact release SHA. Do not paste the
VM `.env` or an entire environment dump into an issue or chat.
