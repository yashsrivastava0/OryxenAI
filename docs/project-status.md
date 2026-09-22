# OryxenAI — current implementation and deployment status

**Snapshot date:** 2026-09-21 (Asia/Kolkata)

**Purpose:** This is the short, current handoff for the human owner and any
AI coding/deployment assistant. It answers three questions: what exists,
what is still pending, and what must happen next.

This page describes the committed repository and live preparation state at the
latest checkpoint. The Azure application is not deployed or accepted yet.
Re-run `git status --short --branch` and use the exact verified application
release SHA before deploying.

The latest deployment-preparation audit is the
[deployment strategy pack](<../doc/deployment strategy/README.md>). It records
the current GitHub, Azure, VM-storage, authentication, model-runtime, domain, and
release gates without claiming that live deployment has been performed.

## Executive status

| Area | Status | Meaning |
| --- | --- | --- |
| Agent pipeline | Implemented locally | Discovery, Content Architect, Visual Design Director, Build Preparation, and the explicit Code Generator stage are present in the repository. |
| Durable execution | Implemented locally | PostgreSQL-backed jobs, worker heartbeats, retries, leases, idempotency, and stale-result fencing are part of the runtime. |
| Authentication and ownership | Implemented locally | Supabase Google authentication, admission, onboarding, ownership, entitlement rules, and the administrator lifecycle are implemented as bounded local foundations. |
| Product frontend | Implemented locally | The authenticated studio shell, explicit stage handoffs, generation control room, preview theater, traceability drawer, public sample previews, and admin console are present in the committed branch. |
| Azure infrastructure | Provisioned | The single Azure VM, network, public IP, and NSG exist; SSH was verified. |
| Deployment tooling | Implemented, not executed | Docker Compose production files, Caddy routing, production TOML template, and `scripts/azure-deploy.sh` are checked in. |
| Application on Azure | Not deployed | Docker has not been installed on the VM, the repository has not been cloned there, and no container or database migration has run there. |
| Production auth/domain | DNS ready; auth pending | Namecheap records for `app.oryxenai.me` and `preview.oryxenai.me` resolve to the static VM IP. Supabase/Google production redirects and HTTPS certificate/browser proof remain pending. |
| Production artifact storage | VM-local storage configured, runtime gate pending | Production Compose now bind-mounts the configurable VM data root, selects local Code Generator artifact/preview providers, initializes non-root ownership, and provides disk/backup/readback checks. Docker runtime, restart/reboot persistence, and Azure acceptance remain unproven. |
| Release candidate | Selected locally; publication pending | SHA `91f0d187d6de67a6d6db158b70d235cd773b11c4` passed the local release gate but is now superseded — it is the exact commit that failed the first VM deployment attempt on the npm-toolchain bug fixed in `d60d40b`. Do not deploy `91f0d18`; re-run the full local release gate and use `git log -1 --oneline` on `deployment` for the current verified SHA before deploying. |
| End-to-end acceptance | Pending | No real Azure run has yet proven Google login → agents → generated artifact → embedded preview → direct preview URL. |

## What has been implemented

### Runtime and data flow

- FastAPI application factory, settings, structured logging, and lifecycle
  management.
- PostgreSQL persistence through SQLAlchemy/asyncpg and Alembic migrations.
- A durable PostgreSQL job queue. The API enqueues work, the separate worker
  claims jobs with row locking, heartbeats while running, retries failures,
  and recovers stale leases.
- JSONB session state and agent-run snapshots with optimistic-concurrency
  checks. Agents do not receive HTTP or database-session objects.
- One shared application image used by separate Compose services for the API,
  worker, migration job, and preview gateway.

### Agent pipeline

The stages are intentionally explicit. Approval of one stage does not
automatically start the next stage.

1. **Discovery** — adaptive intake/questions, brief revision, explicit brief
   approval, envelope validation, idempotency, and revision-aware persistence.
2. **Content Architect** — consumes only the approved Discovery snapshot and
   creates an approved route/content scope through a bounded durable job.
3. **Visual Design Director** — consumes only approved Content Architect
   output, uses the checked-in deterministic resource catalogue, and produces
   an approved visual direction.
4. **Build Preparation** — explicitly compiles the approved content and visual
   scope into the immutable Markdown brief pair:
   `content-and-narrative-brief.md` and `visual-and-build-brief.md`.
5. **Code Generator** — explicitly admits the hash-bound brief pair, plans,
   acquires pinned resources, progressively generates source, runs bounded
   review/repair, builds, performs browser/geometry checks, and promotes a
   stable preview atomically.

The Code Generator also has a standalone development harness. The production
session path and the harness share the core workflow, but the harness is not
the production deployment path.

### Authentication, ownership, and administration

The committed local foundation includes:

- Supabase Google-only session restoration through the self-hosted pinned
  browser client.
- JWT/JWKS verification and verified-provider admission.
- Allow-list admission, one-time username onboarding, and the `/api/v1/me`
  identity boundary.
- Owner-scoped portfolio/session APIs and administrator cross-session access.
- The normal-user portfolio/generation/success entitlement and worker
  reauthorization/fencing rules.
- Audited administrator lifecycle operations, resumable cleanup, entitlement
  reset, bounded role transitions, and the authenticated `/admin` console.

Production OAuth configuration and owner-completed browser acceptance remain
deployment gates; local implementation is not the same as production proof.

### Frontend and preview experience

The committed branch contains:

- The authenticated product/studio shell and the explicit Discovery → Content
  → Design → Preparation → Generate flow.
- Real backend-milestone-driven generation progress, a preview theater, an
  attention/retry surface, and a traceability drawer with copyable diagnostic
  data.
- Three fictional, unauthenticated sample portfolio previews on the sign-in
  surface, with responsive layouts and reduced-motion behavior.
- The administrator control plane with Users, Projects, Legacy, Deleted,
  Operations, and Audit views.
- Recent accessibility, responsive-shell, public-preview, and preview-motion
  improvements recorded in `CHANGES.md`.

These are product capabilities in the repository. They have not yet been
validated through the real Azure deployment acceptance path.

### Verification evidence and remaining proof gap

- The repository has unit, API, integration, worker, frontend, and browser
  checks. Use `uv run pytest`, `uv run ruff check .`, `uv run ruff format
  --check .`, and `uv run mypy src` as appropriate for the selected release.
- The documented Code Generator reliability campaign consumed its authorized
  five full-pipeline attempts without producing an accepted `ready` result.
  Several deterministic fixes landed afterward, and the latest committed
  work also classifies a Windows Vite `spawn EPERM` failure as infrastructure
  with a recovery path. This is useful engineering progress, not proof of a
  successful Azure/Linux generation.
- A fresh, release-SHA-bound generation on the target Azure VM remains
  required before claiming that the deployed Code Generator and preview path
  work end to end. The campaign ledger is
  [`docs/code-generator-live-campaign.md`](code-generator-live-campaign.md).

### Deployment implementation in the repository

The deployment path is now implemented as a single-VM Compose release:

- `compose.yaml` remains the local development stack with loopback host ports
  and optional validation/cache-warm profiles.
- `compose.production.yaml` is a self-contained production stack containing
  PostgreSQL, the one-shot migration service, FastAPI, the durable worker, the
  preview gateway, and Compose-managed Caddy. Only Caddy publishes ports 80
  and 443; the application services remain on the internal backend network.
- `config/app.production.toml` is a non-secret template for production
  origins, VM-local storage, worker, and Code Generator verification settings.
- `Caddyfile` routes the app and preview hostnames and terminates HTTPS.
- `scripts/azure-deploy.sh` provides `setup`, `configure`, `doctor`, `deploy`,
  `status`, `logs`, `verify`, `backup`, and `rollback`.
- `config/models.toml` remains the source of truth for model profiles and the
  environment-variable names used for their credentials.
- `.env.example` documents required names. Real values belong only in the
  VM-local ignored `.env`.

The deployment script is designed so the VM pulls one exact Git commit,
builds the image from that commit, warms the offline npm cache, runs migrations,
starts the services, and performs internal health checks. Public HTTPS and
browser acceptance are separate checks.

## Azure state

Azure infrastructure was created and SSH access was verified. The detailed
portal and SSH record is [`docs/deployment/06-live-azure-vm-status.md`](deployment/06-live-azure-vm-status.md).
The lossless chronological deployment record, including corrected and
unconfirmed steps, is [`docs/deployment/08-live-azure-deployment-session-log-2026-09-14.md`](deployment/08-live-azure-deployment-session-log-2026-09-14.md).

| Resource/setting | Confirmed value |
| --- | --- |
| Subscription | `Azure for Students` |
| Resource group | `oryxenai-demo-rg` |
| Region | `Central India` |
| VM | `oryxenai-demo-vm` |
| Public IPv4 | `20.235.74.81` |
| Private IPv4 observed over SSH | `10.0.0.4` |
| OS | Ubuntu Server 24.04 LTS, x64 Gen2 |
| VM size | `Standard_B2as_v2`, 2 vCPU, approximately 8 GiB RAM |
| Portal estimate at creation | `0.0492 USD/hr`, approximately `$35.92/month` |
| VNet/subnet | `oryxenai-demo-vnet` / `oryxenai-demo-subnet` |
| NSG | `oryxenai-demo-nsg` |
| Public ports | TCP 22 from the recorded operator `/32`, TCP 80, TCP 443 |
| Internal ports | 5432, 5544, 8000, and 4174 are not publicly allowed |

The user connected successfully with the generated Ed25519 key as
`oryxenaiadmin`. The VM was prepared with `apt update`, the small bootstrap
tool set, and `apt upgrade`; Git and curl were verified. Docker, Compose,
Caddy, the repository, PostgreSQL, and the application were not installed or
started during that checkpoint.

The VM may have been stopped/deallocated while idle. Its current power state
and current Azure credit must be checked in the Azure Portal immediately
before the next server operation; this documentation refresh did not perform
a new portal or SSH verification.

## External prerequisite state

### Supabase

The owner reports that the Supabase project work is ready. The final production
domain is now recorded below; the following deployment-specific values still
need to be verified and applied:

- `SUPABASE_URL`;
- the publishable/browser key;
- the server-only secret key, entered only on the VM;
- Google provider enabled; and
- exact Site URL and redirect URL for the final `app.oryxenai.me` origin.

The production values are:

```text
Site URL:      https://app.oryxenai.me
Redirect URL:  https://app.oryxenai.me/auth/callback
```

### VM-local artifact and preview storage

The first Azure release will store generated artifacts and preview objects on
the VM's persistent disk through Docker-backed local-filesystem storage. The
worker and shared preview gateway must use the same persistent preview root;
Code Generator artifacts, workspaces, checkpoints, caches, and Caddy state
must remain on explicitly owned persistent volumes as appropriate.

No external object-storage endpoint, bucket, access key, secret key, or
lifecycle policy is required for this path. The production overlay and release
script now select the available local-filesystem providers, create/check the
VM storage roots, enforce non-root ownership, and provide backup, restore
dry-run, restart, artifact readback, and preview readback checks. Existing
cloud-compatible code is not the selected production path.

The legacy generic `artifact_storage` boundary still has no local-filesystem
implementation: `src/oryxenai/storage/artifacts.py` supports memory and
S3-compatible stores only. The active Markdown brief handoff does not use that
boundary, but a legacy session containing a generic `ArtifactReference` is a
release blocker until a reviewed local implementation exists. Docker build,
startup, migration, health, and persistence checks must still be run with a
live daemon; no Azure deployment is claimed here.

### Domain and GitHub

- The owner reports that `oryxenai.me` is registered through the GitHub Student
  Developer Pack and expires/renews on `2027-09-21`.
- The production hostnames are `app.oryxenai.me` and `preview.oryxenai.me`.
- DNS A records must point both hostnames to the VM's current static public IP
  before public HTTPS verification. The last documented IP was `20.235.74.81`;
  re-check the Azure Portal before creating records.
- GitHub is the source repository, not a second application runtime. The VM
  still needs read access to the selected branch. For a private repository,
  configure a VM-specific GitHub deploy key or another approved read-only
  checkout method. The Azure SSH private key is not used for GitHub access.
- A self-hosted GitHub Actions runner is installed and running on the VM,
  and a `deploy` job in `ci.yml` will deploy automatically once a change
  reaches `deployment` (D-110; no approval-click gate currently, per an
  explicit "fully automatic" instruction). See
  `docs/deployment/ci-cd-runbook.md` for the full mechanics, the real SSH
  key, and known setup gotchas. Manually SSHing in and running the
  deployment script by hand still works and remains the path for ad hoc
  operations (`status`, `logs`, `rollback`, `restore-dry-run`, etc.).
- **`deployment` is protected by a `deployment-ci-gate` repository ruleset:
  no direct push ever works, from anyone, including the owner.** Every
  change must go through a side branch, a PR, a passing `quality` check,
  and a merge commit (never squash/rebase). The `gh` CLI is installed and
  authenticated on the primary dev machine
  (`C:\Program Files\GitHub CLI\gh.exe`, not yet on PATH in tool shells) —
  use it to read run/job logs (`gh run view <id> --log-failed`) instead of
  relaying them through the operator.
- **As of 2026-09-22, the `deploy` job's trigger is deliberately forced off**
  (a leading `false &&` in its `if:` condition) and a PR
  (github.com/yashsrivastava0/OryxenAI/pull/1) is open and blocked: the
  required `quality` check is failing on 3 tests, one of which
  (`tests/integration/test_code_generator_verification_worker.py::test_verification_builds_and_promotes_a_clean_candidate`
  and the related `test_dependency_manager.py` failure) is a **real,
  deployment-relevant bug** — the Code Generator's npm invocation resolves
  to the Windows-only `npm.cmd` on Linux CI, and would fail identically on
  the real (Linux) Azure VM. Not yet fixed. A third failure
  (`tests/browser/test_frontend_remediation.py::test_developer_inspector_is_opt_in_and_drawer_is_accessible`)
  may overlap with `PLAN.MD`'s active Code Generator frontend work — check
  before fixing it. Do not remove the `false &&` disable or merge that PR
  without the operator's fresh, explicit go-ahead.

## What is pending

### Release and repository gate

No release SHA has passed the live Azure deployment and acceptance gates.
Therefore:

1. Do not deploy from an unreviewed or dirty checkout.
2. Inspect `git status --short --branch` and the relevant diffs.
3. Run the relevant tests/checks for the exact intended release.
4. Select and record one exact clean commit SHA.
5. Push that release branch/commit if the owner approves publishing it.

The deployment VM must fetch that exact release, not a moving or dirty local
working tree.

### VM and production setup

The following have not yet happened on Azure:

- Start the VM if it is deallocated.
- Confirm Windows SSH access from the primary deployment laptop.
- Clone the selected GitHub repository/branch.
- Install Docker Engine and the Docker Compose plugin.
- Create the VM-local `.env` and rendered
  `config/app.production.local.toml`.
- Enter the final domain, Supabase, allow-list, PostgreSQL, VM-storage,
  model-provider, and image-provider configuration.
- Run the deployment script's doctor checks.
- Build the exact image, warm npm dependencies, migrate PostgreSQL, and start
  the app, worker, preview gateway, and Caddy.

### Public integration and acceptance

- Configure DNS and wait for both hostnames to resolve.
- Confirm Supabase Google OAuth uses the exact HTTPS app origin.
- Confirm VM-local artifact write/readback and preview readback after restart.
- Confirm Caddy obtains certificates and both health endpoints work.
- Test the complete explicit agent sequence with a small privacy-safe input.
- Test both embedded and direct generated-preview URLs.
- Test a second allowed user and owner isolation.
- Test restart/recovery and a PostgreSQL backup.

## Next exact sequence

Use this order when the owner is ready to deploy:

1. **Release gate on the development laptop.** Reconcile the dirty worktree,
   run the appropriate checks, select one exact SHA, and record it.
2. **Azure check.** In the Portal, confirm the VM exists, review its power
   state and remaining student credit, and start it if deallocated.
3. **Repository access.** Confirm the GitHub repository URL and release branch;
   configure VM read access if the repository is private.
4. **Domain/auth/storage coordinates.** Confirm the final domain, both DNS A
   records, the Supabase project and callback settings, and the VM storage
   root, capacity, ownership, backup, and retention policy. Keep all secret
   values off chat and Git.
5. **One-time VM setup.** SSH to the VM, clone the repository, and run:

   ```bash
   chmod +x scripts/azure-deploy.sh
   ./scripts/azure-deploy.sh setup
   ```

   Enter the prompted production values directly in the terminal. The script
   installs Docker and writes the ignored VM-local configuration.

6. **Preflight and release.** Fix every real `doctor` error, then run:

   ```bash
   ./scripts/azure-deploy.sh doctor
   ./scripts/azure-deploy.sh deploy <EXACT_RELEASE_SHA>
   ./scripts/azure-deploy.sh status
   ./scripts/azure-deploy.sh verify
   ```

7. **Browser acceptance.** Sign in with Google, complete the explicit stages,
   generate a portfolio, confirm VM-local artifact/preview readback, open the in-app preview,
   open its direct URL, and repeat the ownership check with the second user.
8. **Idle operation.** When the demo is not needed, use Azure Stop/
   Deallocate. Check Azure disk usage, Supabase, domain, and model-provider
   usage separately.

## Acceptance definition

The deployment is not complete when the VM is merely online or when the
containers are running. It is complete only when all of these are true:

- the app and preview hostnames resolve over HTTPS;
- Google login, callback, and onboarding work;
- the database is migrated and ready;
- the worker claims and completes durable jobs;
- Discovery, Content Architect, Visual Design Director, and Build Preparation
  complete in their explicit order;
- Code Generator completes source generation, build, verification, and stable
  preview promotion;
- the generated portfolio appears inside the application;
- the direct preview URL works after refresh; and
- a second allowed user can use the application without seeing the first
  user's portfolio data.

## Source-of-truth documents

- [`AGENTS.md`](../AGENTS.md) — canonical cross-tool project context and
  collaboration rules.
- [`README.md`](../README.md) — quick developer setup and architecture summary.
- [`docs/architecture.md`](architecture.md) — architectural rationale.
- [`docs/deployment/README.md`](deployment/README.md) — deployment index.
- [`docs/deployment/02-azure-vm-runbook.md`](deployment/02-azure-vm-runbook.md)
  — command-level first deployment.
- [`docs/deployment/06-live-azure-vm-status.md`](deployment/06-live-azure-vm-status.md)
  — Azure resource and SSH checkpoint.
- [`docs/deployment/03-acceptance-and-operations.md`](deployment/03-acceptance-and-operations.md)
  — acceptance, diagnosis, backup, and cost operations.
- [`docs/code-generator-live-campaign.md`](code-generator-live-campaign.md)
  — historical Code Generator reliability evidence; it does not claim an
  Azure-ready successful campaign.
- [`CHANGES.md`](../CHANGES.md) — append-only implementation history.
- [`DECISIONS.md`](../DECISIONS.md) — architectural decisions and rejected
  alternatives.
