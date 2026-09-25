# Deployment-readiness matrix

Audit recorded: 2026-09-15 20:26:26 +05:30 (Asia/Kolkata)

Scope: preparation only. This audit did not start the Azure VM, install Docker
on the VM, deploy a release, write to VM-local artifact/preview storage, change Supabase or Google settings,
register the domain, create a GitHub branch, or push anything.

The evidence rule is deliberate:

- Checked-in code and local tests prove repository readiness only.
- A historical Azure or browser report proves what happened at that time only.
- Live VM-storage, model, authentication, preview, and two-user checks are required
  before calling the hosted application accepted.

## Executive verdict

The deployment design is ready to execute, but the release is not yet ready
to deploy or to call working in production. The remaining work is mostly
verification and owner-controlled setup, not a new hosting architecture.

The correct next milestone is:

```text
clean release SHA
  -> deployment branch
  -> VM-local production configuration
  -> Compose deploy and internal health
  -> later deploy.me DNS/auth/HTTPS
  -> live VM-storage/model/browser acceptance
```

Do not collapse those milestones into one claim.

## Repository-safe validation completed

- The merged production Compose configuration passed
  `docker compose --env-file .env.example -f compose.production.yaml config --quiet`.
- Local Markdown links in this strategy folder resolve.
- Bash syntax validation was attempted through both the Windows Bash launcher
  and Git Bash, but the host returned an access-denied process/mapping error.
  No shell syntax failure was observed; the existing Linux CI workflow still
  runs the authoritative `bash -n scripts/azure-deploy.sh` check.
- The environment verification script completed successfully after pointing
  `uv` at a temporary writable audit cache. It reported the expected local
  configuration and did not print secret values. This validates the local
  settings loader only, not the production environment.
- The full test suite was not used as a release verdict against the dirty
  multi-agent worktree. Run the complete release checks after contributors
  reconcile the tree and before selecting the deployment SHA.

## Evidence matrix

| Area | Evidence available now | Status | Gate before production acceptance |
| --- | --- | --- | --- |
| Durable jobs | PostgreSQL-backed jobs, worker heartbeats, retries, leases, idempotency, and stale-result fencing are implemented. | Repository-ready | Prove that the worker claims and completes a real job on Azure after migration. |
| Production topology | `compose.yaml` plus `compose.production.yaml` define PostgreSQL, one-shot migrations, API, worker, preview gateway, and Compose-managed Caddy with persistent volumes. | Ready to execute | Run merged Compose validation, build the image on the VM, and inspect all services. |
| Deployment command | `scripts/azure-deploy.sh` provides setup, configuration, doctor checks, exact-SHA deploy, status, logs, verification, backup, and rollback. | Ready with an operator caveat | Use an explicit exact SHA. Do not rely on its historical no-argument branch default until the release branch is actually recorded in VM state. |
| Azure VM | The repository's live checkpoint records an existing Ubuntu VM, static public IP, 2 vCPUs, about 8 GiB RAM, SSH access, and restricted SSH/HTTP/HTTPS rules. | Historical infrastructure evidence | Re-check power state, current public IP, disk, spending limit, and the current laptop's SSH access immediately before setup. Docker and the application were not proven installed there. |
| Network boundary | Only Caddy should publish ports 80/443. PostgreSQL, API, and preview ports are bound to VM loopback in Compose; SSH is intended to be one trusted `/32`. | Designed | Verify the Azure NSG and VM firewall have not drifted. Never open PostgreSQL, API, preview, or SSH to the Internet. |
| PostgreSQL and migrations | A dedicated `migrate` service waits for a healthy Postgres service and must complete before app/worker startup. | Repository-ready, Azure-unproven | Run the migration service on Azure and retain a backup before later schema-changing releases. |
| VM-local artifact and preview storage | The selected first-release boundary is persistent VM-backed Docker storage shared by the worker and preview gateway where required. The current production overlay still needs its local-filesystem provider values and storage-root checks. | Decision made, implementation follow-up | Configure volume/bind ownership, disk thresholds, retention, backup/restore, restart survival, and artifact/preview readback. |
| Local `.env` | The local file has model, Supabase, and provider-looking values, but it is not a production input. The audit found duplicate allowlist/admin declarations, a malformed token-like line, missing production coordinates, and an empty deferred Firebase value. | Not safe to copy | Create a fresh VM `.env` from `.env.example`; inspect and rotate the local token-like value if it is real. Never paste or commit the file. |
| Supabase auth | Authentication phases 1-4, JWT/JWKS verification, Google-only admission, onboarding, ownership, entitlements, admin lifecycle, and worker fencing exist locally. | Code/config ready, production-unproven | Configure the exact HTTPS origin and callback after the domain is available, then test Google login, onboarding, admin access, and two-user isolation. |
| `oryxenai.me` | The owner reports that the domain is registered through the GitHub Student Developer Pack and expires/renews on `2027-09-21`. The production hostnames are `app.oryxenai.me` and `preview.oryxenai.me`. | Domain controlled; public activation pending | Add both A records to the VM's current static IP, configure Supabase/Google redirects, wait for DNS, and run public HTTPS checks. |
| Model runtime | Agents use the provider-neutral `ModelClient` and `ModelRuntime`; profiles, fallbacks, capacity sources, and credential environment names are read from `config/models.toml`. | Code/config ready, provider calls unproven | At release time, inspect the current TOML and run the privacy-free provider preflight for every route used by the release. Never infer a model from prose. |
| Claude/Codex/OpenCode tools | `claude`, `codex`, and `opencode` are available on the development machine. They are developer/operator tools, not Compose services and not runtime dependencies. | Local tooling ready | Do not install a CLI or its personal session on the production VM. Use a bounded, read-only AI review and let a human approve secrets and deploy commands. |
| GitHub release | CI exists in `.github/workflows/ci.yml` and validates code, migrations, Compose, a container smoke path, and secret scanning. No deployment workflow exists. The `deployment` branch is not yet a release branch. | Release gate pending | Reconcile the dirty multi-agent worktree, choose one clean SHA, create/protect `deployment`, and push only that reviewed release. |
| Backups and observability | The script can produce a PostgreSQL dump and show Compose logs. Azure Backup, monitoring, and external log retention are not configured. | Minimal operational coverage | Download important dumps off the VM, test restore separately, and treat `status` plus redacted logs as the first incident evidence. |

## Local configuration findings

The local `.env` was inspected structurally without printing values. The
important findings are:

- Model/provider, Supabase, image-provider, and PostgreSQL-looking entries
  are present, but presence is not proof that a credential is valid.
- `APP_HOST` and `PREVIEW_HOST` are not usable local production coordinates.
- The administrator and normal-user allowlist keys appear more than once.
  The deployment script's simple parser uses the last declaration, which is
  another reason to start the VM from a clean template.
- One non-comment line is malformed and token-like. If it is a live secret,
  revoke or rotate it before using the development machine further.
- `SCALEMAX_*` entries are extra relative to `.env.example`; do not delete
  them blindly, but confirm whether any current profile consumes them.
- `FIREBASE_ADMIN_CREDENTIAL_JSON` is empty and belongs to a deferred provider
  path; it is not part of the selected Google/Supabase deployment.
- The existing local file contains provider-looking values that must not be
  copied into the VM; production storage is VM-local and needs a fresh
  storage/backup configuration.

## What is ready versus what is not

### Ready to prepare

- One-VM Azure Compose is the appropriate scale for two or three users.
- Production Caddy, loopback service bindings, persistent volumes, migration
  ordering, health checks, and exact-SHA image tags are checked in.
- The owner-facing setup and maintenance flow is documented in
  [`runbook.md`](runbook.md) and [`operations.md`](operations.md).
- The future domain is kept in the configuration plan without blocking the
  server-only phase.
- GitHub CI can remain the quality gate while deployment stays explicit and
  reviewable.

### Not yet proven

- Current Azure state after the documented checkpoint.
- Docker/image build/migrations/containers on Azure.
- VM-local artifact/preview write/readback, disk monitoring, backup, and restore.
- Live model provider reachability and quota behavior.
- Production Supabase/Google redirects and browser login.
- The entire five-stage flow and the two-user ownership boundary on Azure.
- A clean release branch and a tested rollback from a real Azure release.

## Release-blocking conditions

Stop before deployment if any of these is true:

1. `git status --short --branch` shows unreviewed tracked changes or the
   release SHA cannot be identified.
2. The VM has no current SSH access, the public IP changed, or port 22 is open
   more broadly than the trusted operator address.
3. The VM `.env` would be copied from the developer machine or still contains
   placeholders, duplicates, or an unrecognized credential.
4. `doctor` reports missing active model keys, missing VM-storage/auth values,
   invalid merged Compose configuration, insufficient disk, or bad volume
   ownership.
5. VM-local artifacts/previews cannot survive a restart or a tested backup
   restore is unavailable.
6. The migration fails, an app/worker/preview health check fails, or the
   worker does not process a diagnostic job.
7. The latest reliability-session issues have not been re-tested against a
   healthy runtime.

## Source-of-truth order

When documents disagree, use this order:

1. The exact checked-out source and tests for behavior.
2. `config/models.toml` for model routing and credential names.
3. `config/app.production.toml` plus the VM-local rendered overlay for
   production behavior.
4. `compose.yaml`, `compose.production.yaml`, `Caddyfile`, and
   `scripts/azure-deploy.sh` for infrastructure operations.
5. [`docs/project-status.md`](../../docs/project-status.md) and
   [`docs/deployment/`](../../docs/deployment/) for historical checkpoints.
6. Older architecture or provider notes only for rationale.

Related documents:

- [`github-and-ci.md`](github-and-ci.md)
- [`ai-and-open-source-research.md`](ai-and-open-source-research.md)
- [`owner-checklist.md`](owner-checklist.md)
- [`runbook.md`](runbook.md)
- [`research-sources.md`](research-sources.md)
