# OryxenAI live Azure deployment session log

**Session log date:** 2026-09-14 (Asia/Kolkata)

**Purpose:** Preserve the deployment conversation as an append-only operational
record. This file deliberately distinguishes confirmed observations, user or
assistant reports, unconfirmed commands, corrections, and repository work that
exists for future deployment. It is not a release manifest and it is not proof
that the application is deployed.

**Secret policy:** No private key contents, passwords, API keys, tokens, or
production `.env` values are recorded here. The Azure public IP is a deployment
coordinate, not a credential. The private SSH key remains on the operator's
secure device.

## Evidence labels

- **Portal report:** a value was reported from the Azure Portal wizard or the
  final Review + create page.
- **Terminal report:** a value was copied from the live SSH terminal.
- **Repository evidence:** a file, script, commit, or status document exists in
  the local repository.
- **Unconfirmed:** a command or claim was suggested, but its successful result
  was not shown in this conversation.
- **Historical or superseded:** an earlier state was replaced later. It remains
  in the log so a future operator does not mistake it for the final state.

## Executive summary

The Azure infrastructure was created for the small OryxenAI demo. The VM is
`oryxenai-demo-vm` in the existing `oryxenai-demo-rg` resource group in Central
India. The public IPv4 reported after creation is `20.235.74.81`. SSH access
was successfully tested from the Mac using the generated Ed25519 private key.
The VM reported Ubuntu 24.04.4 LTS, `x86_64`, approximately 8 GiB of memory,
and approximately 61 GiB of usable root disk.

The VM has received the small operating-system bootstrap package set. Git and
curl were verified. The Docker installation command was subsequently provided
but its output was not recorded in this conversation, so Docker, Compose, the
repository, PostgreSQL, migrations, the API, the worker, Caddy, DNS, Supabase
production settings, R2 VM configuration, and end-to-end acceptance remain
unconfirmed or pending.

The repository already contains substantial future-facing implementation and
deployment work: the explicit multi-agent pipeline, durable PostgreSQL jobs,
Supabase-based authentication and ownership foundations, the authenticated
product shell, the Generate/Preview experience, the Code Generator workflow,
production Compose/Caddy configuration, and the guided Azure deployment
script. Those repository capabilities must not be confused with a successful
live Azure application deployment.

## Chronological session record

### 1. Deployment strategy and documentation work

The deployment strategy was researched for a first-time deployer with a
maximum of two active normal users and a limited Azure for Students credit.
The selected shape was intentionally small:

- one Azure Linux VM;
- Docker Compose on that VM;
- PostgreSQL on the VM for application state and durable jobs;
- a separate FastAPI application container;
- a separate durable worker container;
- a preview gateway container;
- Caddy for the public application and preview routes;
- Supabase Google authentication;
- Cloudflare R2 for generated artifacts and preview objects; and
- one domain with `app.<DOMAIN>` and `preview.<DOMAIN>` hostnames.

The following deployment documents were created or maintained during the
deployment-planning work:

- `docs/deployment/01-deployment-options-research.md`
- `docs/deployment/02-azure-vm-runbook.md`
- `docs/deployment/03-acceptance-and-operations.md`
- `docs/deployment/04-current-azure-deployment-status.md`
- `docs/deployment/05-chrome-browser-agent-azure-setup-prompt.md`
- `docs/deployment/06-live-azure-vm-status.md`
- `docs/deployment/07-ai-assisted-operations.md`
- this file, `docs/deployment/08-live-azure-deployment-session-log-2026-09-14.md`

The earlier VM-wizard attempt was lost when the computer was accidentally
turned off. The VM wizard was then restarted from Azure Portal home instead of
assuming that the old unsaved wizard still existed.

### 2. Azure subscription and resource group

**Portal report:**

- Subscription: `Azure for Students`
- Starting credit reported: `$100 out of $100`
- Current cost before VM creation: `$0.00`
- Displayed remaining duration: 365 days
- Displayed expiration: `05/09/2027`
- Resource group: `oryxenai-demo-rg`
- Resource group region: Central India

The existing resource group was reused. No duplicate resource group was
created.

The Azure spending-limit/protection policy was intended to remain enabled, and
the deployment plan explicitly rejected upgrading to Pay-As-You-Go.

### 3. Azure VM wizard: Basics

The final reported Basics configuration was:

| Field | Final reported value |
| --- | --- |
| Subscription | `Azure for Students` |
| Resource group | `oryxenai-demo-rg` |
| VM name | `oryxenai-demo-vm` |
| Region | `(Asia Pacific) Central India` |
| Availability | No infrastructure redundancy required |
| Security type | Trusted launch virtual machines |
| Image | Ubuntu Server 24.04 LTS, x64 Gen2 |
| Architecture | x64 |
| Azure Spot | Off |
| Hibernation | Off or unavailable |
| VM size | `Standard_B2as_v2` |
| vCPUs | 2 |
| Memory | 8 GiB |
| Earlier portal estimate | Approximately `$35.92/month` |
| Later displayed hourly price | `0.0492 USD/hr` |
| Authentication | SSH public key |
| Linux username | `oryxenaiadmin` |
| SSH format | Ed25519 |
| Key pair name | `oryxenai-demo-key` |
| Basics public inbound ports | None |

The hourly and monthly estimates are consistent with each other. The VM is
chargeable against the Azure student credit while it is running; it was not a
permanently free VM.

The private key was not placed in the repository or any AI conversation. The
portal's generated-key workflow required the operator to click Create before
the `Download private key and create resource` action appeared. The operator
downloaded the key after that prompt appeared.

### 4. Azure VM wizard: Disks

The final reported disk configuration was:

- OS disk size: 64 GiB (E6)
- OS disk type: Standard SSD, `StandardSSD_LRS`
- Managed disks: Yes
- Encryption: Platform-managed key
- Encryption at host: Off or unavailable
- Delete OS disk with VM: On
- Ultra Disk compatibility: Off or unavailable
- Additional data disks: None
- Ephemeral OS disk: None

The disk was intentionally changed from the initial Premium SSD/image-default
configuration to Standard SSD to reduce student-credit consumption for the
two-user demo.

### 5. Azure VM wizard: Networking

The initial Azure networking defaults were different from the planned values:

- default VNet: `vnet-centralindia-1`
- default subnet: `snet-centralindia-1`
- default subnet range: `172.16.0.0/24`
- default public IP resource name: `oryxenai-demo-vm-ip`
- default NSG mode: Basic
- cleanup switches initially off

Those defaults were corrected before VM creation.

The final reported networking configuration was:

| Resource or field | Final reported value |
| --- | --- |
| VNet | `oryxenai-demo-vnet` |
| VNet address space | `10.0.0.0/16` |
| Subnet | `oryxenai-demo-subnet` |
| Subnet address range | `10.0.0.0/24` |
| Public IP resource | `oryxenai-demo-ip` |
| Public IP version | IPv4 |
| Public IP SKU | Standard |
| Public IP allocation | Static |
| NSG mode | Advanced/custom |
| NSG resource | `oryxenai-demo-nsg` |
| NIC name | No editable field; Azure-generated name accepted |
| Load balancing | None |
| Accelerated networking | Off |
| Private IP allocation | Dynamic/default |
| Delete public IP with VM | On |
| Delete NIC with VM | On |

The intentional custom inbound rules were:

| Priority | Name | Source | Protocol and port | Action |
| ---: | --- | --- | --- | --- |
| 100 | `Allow-SSH-MyIP` | `106.192.207.210/32` | TCP/22 | Allow |
| 110 | `Allow-HTTP` | Any | TCP/80 | Allow |
| 120 | `Allow-HTTPS` | Any | TCP/443 | Allow |

No public allow rules were added for ports `5432`, `5544`, `8000`, or
`4174`.

The SSH source address was the public IP detected by Azure during wizard
configuration. It may become stale if the operator changes networks. If SSH
later times out, the next diagnostic is to compare the operator's current
public IP with the NSG `/32` rule. Port 22 must not be opened to Any.

### 6. Azure VM wizard: Management, Monitoring, Advanced, and Tags

The final reported Management settings were:

- System-assigned managed identity: Off
- Microsoft Entra ID login: Off
- User-assigned identity: None or unavailable
- Azure Backup: Off
- Recovery Services vault: None
- Site Recovery: Off
- Periodic assessment: Off
- Hotpatch: Off
- Patch orchestration: Image default
- Auto-shutdown: Off
- Hibernation: Off or unavailable
- No paid backup, identity, security, or management add-on

The final reported Monitoring settings were:

- Alerts: Off
- Boot diagnostics: Off
- OS guest diagnostics: Off
- Application health monitoring: Off
- No VM Insights
- No Application Insights
- No Log Analytics workspace
- No Defender add-on
- No monitoring agent
- No custom storage account

The final reported Advanced settings were:

- Extensions: None
- VM applications: None
- Custom data: Blank
- Cloud-init: No
- User data: Unavailable or not exposed
- Scripts/post-deployment commands: None or unavailable
- Capacity reservation group: None
- NVMe: Disabled or unavailable for this VM size
- Disk controller: SCSI
- No dedicated host, host group, or proximity placement group

The final tags were:

- `project = oryxenai`
- `environment = demo`
- `owner = student`

The empty trailing tag row was left empty.

### 7. Review gate and corrections

The Review + create page initially showed Boot diagnostics enabled with
managed storage. The portal displayed a nominal storage charge. Because the
deployment goal was the cheapest working demo and Boot diagnostics is not
required by the application, the setting was changed to Off.

The corrected Review + create page reported:

- validation completed without a validation error;
- price `0.0492 USD/hr`;
- Boot diagnostics Off;
- no custom storage account;
- no unexpected monitoring resource;
- no quota issue;
- no identity requirement;
- no duplicate resource;
- VM still uncreated until the human operator clicked Create.

The Review + create page showed tag propagation targets for resource types
such as an availability set, storage account, Recovery Services vault,
schedules, SQL virtual machine, extensions, and SSH key. These were generic
target rows, not evidence that those optional resources had been selected.

### 8. VM creation and SSH

The human operator performed the final Azure Create action after the review
was approved. The deployment was reported complete.

The public IPv4 reported after creation was:

    20.235.74.81

The private IPv4 observed inside Ubuntu was:

    10.0.0.4

The private address is internal to the Azure VNet and is not the address used
from the operator's laptop.

The generated private key was first used from a Mac at the reported local
path:

    /Users/yash/Downloads/oryxenai-demo-key.pem

The operator ran `chmod 400` on the file. The command was run twice; the
second run was harmless.

The SSH command used was:

    ssh -i "/Users/yash/Downloads/oryxenai-demo-key.pem" oryxenaiadmin@20.235.74.81

On the first connection, the operator accepted the host authenticity prompt
with `yes`. The host key fingerprint recorded by the terminal was:

    SHA256:5I3/jSo9HvOfx0CFPHq2uvJrHoBM4+OCJ19zRzOD0zI

The terminal then reported a successful login:

    Welcome to Ubuntu 24.04.4 LTS (GNU/Linux 6.17.0-1022-azure x86_64)
    oryxenaiadmin@oryxenai-demo-vm:~$

The operator later asked whether the private key should be pasted into this
conversation. The answer was no. The key must remain on the device that runs
SSH, or be transferred securely to the device that will run SSH. It must not
be placed in the repository, `.env`, GitHub, or an AI chat.

### 9. Live VM verification

At the SSH prompt, the following commands were run:

    whoami
    hostname
    uname -m
    free -h
    df -h /

The terminal reported:

| Check | Observed value |
| --- | --- |
| User | `oryxenaiadmin` |
| Hostname | `oryxenai-demo-vm` |
| Architecture | `x86_64` |
| Memory total | `7.7Gi` |
| Memory available at check | `7.2Gi` |
| Root filesystem size | `61G` |
| Root filesystem available | `60G` |
| Root filesystem used | `3%` |
| Swap | `0B` |

This verified the VM's basic CPU architecture, memory, disk, account, and SSH
identity. It did not verify Docker or the application.

### 10. VM bootstrap packages

The operator ran the following bootstrap commands in the SSH session:

    sudo apt update
    sudo apt install -y git ca-certificates curl gnupg lsb-release

The terminal reported successful package processing and no required service
restart. It verified:

    git version 2.43.0
    curl 8.5.0

The SSH banner said the running kernel was up to date and that the available
package list was more than a week old before `apt update` was run.

A separate existing deployment-status document records `sudo apt upgrade -y`
as completed during a broader checkpoint. That command's output is not present
in the current conversation transcript. Treat the upgrade as repository
reported but not independently reverified in this log.

### 11. Docker installation command status

After Git and curl were verified, the official Docker Ubuntu repository
installation command was provided for execution. It included:

- the Docker signing key;
- the Docker Ubuntu apt source;
- Docker Engine;
- the Docker CLI;
- containerd;
- Buildx; and
- the Docker Compose plugin.

The command also included enabling the Docker service, checking Docker and
Compose versions, and running the `hello-world` image.

The output of that Docker command was not included before this log request.
Therefore the current evidence classification is:

- Docker Engine: **unconfirmed**
- Docker Compose plugin: **unconfirmed**
- Docker service enabled/running: **unconfirmed**
- `hello-world` check: **unconfirmed**
- application repository cloned: **not done**
- application containers started: **not done**

Do not assume Docker is installed merely because the command was provided.
The next operator must run and record:

    docker --version
    docker compose version
    sudo systemctl is-active docker

If the repository's current `scripts/azure-deploy.sh setup` is used instead,
inspect its current behavior first so Docker is not installed twice through
conflicting methods.

## Repository implementation and future work preserved by this log

This live Azure session occurred after substantial repository implementation.
The following capabilities exist in the repository or are recorded by its
current status documents. They are future-facing deployment inputs, not proof
of live Azure acceptance.

### Runtime and database

- FastAPI application factory, settings, structured logging, and lifecycle.
- PostgreSQL persistence through SQLAlchemy/asyncpg and Alembic migrations.
- A durable PostgreSQL-backed job queue with row-lock claiming, heartbeats,
  retries, leases, stale-job recovery, idempotency, and optimistic concurrency.
- JSONB session state and agent-run snapshots.
- Separate Compose processes for migrations, API, worker, and preview gateway.
- No Redis, Celery, Kafka, or external queue.

### Explicit agent pipeline

- Discovery with adaptive intake, questions, brief revision, explicit approval,
  envelope validation, and durable persistence.
- Content Architect consuming only the approved Discovery snapshot.
- Visual Design Director consuming only approved Content Architect output and
  consulting the deterministic checked-in resource catalogue.
- Build Preparation compiling approved content and visual direction into the
  hash-checked Markdown brief pair.
- Code Generator admitting the immutable brief pair, planning, acquiring
  pinned resources, generating source, performing bounded review and repair,
  building, verifying, and promoting a stable preview.
- Explicit stage handoffs rather than automatic chaining.

### Authentication, ownership, and administration

- Supabase Google-only session restoration through the pinned browser client.
- JWT/JWKS verification and verified-provider admission.
- Allow-list admission, username onboarding, and `/api/v1/me`.
- Owner-scoped portfolio APIs and administrator cross-session access.
- User entitlement rules, worker reauthorization, and fencing.
- Audited administrator lifecycle operations, cleanup, reset, role transitions,
  and the authenticated admin console.

### Product frontend and preview experience

- Authenticated Preact/TypeScript/Vite product shell.
- Explicit Discovery, Content, Design, Preparation, and Generate/Preview flow.
- Real backend milestone progress for the Code Generator.
- Preview theater, attention/retry state, traceability diagnostics, and
  generated-preview iframe behavior.
- Public fictional sample portfolio previews on the sign-in surface.
- Administrator control plane.
- Responsive, accessibility, reduced-motion, and visual-reference work
  recorded in the repository's change history.

### Deployment implementation already in the repository

The current repository status documents report that these deployment pieces
are present:

- `compose.yaml` for PostgreSQL, migrations, API, worker, and preview gateway;
- `compose.production.yaml` for production service configuration and Caddy;
- `config/app.production.toml` for non-secret production settings;
- `Caddyfile` for application and preview host routing;
- `scripts/azure-deploy.sh` with setup, configure, doctor, deploy, status,
  logs, verify, backup, and rollback operations;
- `.env.example` with required variable names and no real credentials;
- `config/models.toml` as the source of truth for model profiles and the
  environment-variable names used for credentials; and
- deployment documentation and AI-assisted operations guidance.

### Compilation and verification context

The repository has undergone frontend, backend, agent, Code Generator, and
deployment-tooling implementation and verification work. The current change
history records local tests, type checks, frontend builds, browser fixtures,
Code Generator campaign runs, and follow-up fixes. Those records are useful
engineering evidence, but they are not a replacement for a fresh build and
acceptance run on the Azure VM from one selected clean release SHA.

The repository's current status specifically records that:

- production Compose/Caddy/TOML deployment tooling was implemented;
- the authenticated Generate/Preview stage was implemented;
- the Code Generator control room, preview theater, traceability, and
  preview-first acceptance work was implemented;
- Windows Vite process-spawn diagnostics and recovery were addressed; and
- a clean release SHA still has to be selected from the current dirty shared
  worktree before Azure deployment.

No Azure Docker image build, database migration, live container build, or live
portfolio generation has been confirmed by this session log.

## Mistakes, false starts, and corrected decisions

This section is intentionally retained so future operators know what happened
and do not repeat an earlier assumption.

1. **The first wizard session was lost.** The computer was accidentally turned
   off, so the Azure VM wizard state was not trusted. The resource group was
   reused and the VM wizard was completed again from Azure Portal home.

2. **Azure's initial networking defaults were not accepted.** The wizard first
   showed different VNet, subnet, public IP, and Basic NSG values. They were
   replaced with the named VNet, subnet, static Standard public IP, and custom
   NSG plan recorded above.

3. **The browser agent paused on the wrong tab once.** It reported that it
   would remain on Monitoring even though the intended next checkpoint was
   Advanced. A corrective instruction moved the review to Advanced, then Tags,
   and finally Review + create.

4. **Boot diagnostics was initially enabled.** The final review exposed a
   nominal managed-storage charge. It was disabled before VM creation to honor
   the low-cost demo requirement. The current final state is Boot diagnostics
   Off.

5. **The Review page did not display every networking detail.** The summary
   did not show the full custom NSG rule table, CIDRs, or every Public IP
   property. Those values came from the prior Networking report and should be
   checked in the created NSG if a future incident requires it.

6. **Private-key location changed across devices.** The initial SSH test used
   the Mac Downloads path. Later instructions discussed copying the key to a
   separate Windows device. The current path must always be checked on the
   device running SSH; the key is not a repository or server configuration
   file.

7. **The old and new deployment instructions are not perfectly aligned.** The
   older `02-azure-vm-runbook.md` contains native Caddy installation language,
   while the newer project status and `scripts/azure-deploy.sh` describe
   Compose-managed Caddy. Before the next live command, use the current script
   and current Compose files as the source of truth. Do not install native
   Caddy and Compose Caddy at the same time without reconciling the documents.

8. **An existing status document has broader historical claims.** In
   particular, it records an `apt upgrade` and a Windows SSH handoff whose
   output is not present in this raw conversation. Those claims are preserved
   as historical repository evidence, while this file marks them as not
   independently reverified here.

## Current known state after the recorded session

### Confirmed live infrastructure

- Azure VM exists: `oryxenai-demo-vm`.
- Resource group exists: `oryxenai-demo-rg`.
- Public IPv4 recorded: `20.235.74.81`.
- SSH login succeeded as `oryxenaiadmin`.
- Ubuntu 24.04.4 LTS and `x86_64` were observed.
- Git and curl were installed and verified.
- The root disk and memory were inspected successfully.

### Not yet proven on the live VM

- Docker Engine installation.
- Docker Compose plugin installation.
- Caddy runtime mode.
- Repository checkout.
- Exact release commit.
- Production `.env`.
- Production application TOML.
- PostgreSQL container.
- Alembic migration.
- FastAPI container.
- Durable worker.
- Preview gateway.
- R2 upload and readback.
- Supabase Google OAuth callback.
- DNS resolution.
- HTTPS certificate issuance.
- Generated portfolio output.
- Embedded preview.
- Direct preview URL.
- Two-user browser acceptance.

### Repository release gate

The working tree is dirty with unrelated tracked and untracked changes from
other contributors. Do not deploy a moving branch or copy the local working
tree to the VM. The next release operation must:

1. inspect `git status --short --branch`;
2. review relevant diffs and preserve unrelated work;
3. run the checks appropriate to the selected release;
4. choose one exact clean commit SHA;
5. record and push that SHA if approved; and
6. deploy that SHA to the VM.

## Next exact checkpoint

Before running more server commands:

1. Confirm the VM is running and the public IP is still current.
2. From the active SSH session, verify Docker with:

       docker --version
       docker compose version
       sudo systemctl is-active docker

3. Inspect the current `scripts/azure-deploy.sh` and Compose files before
   choosing between the guided setup path and the manually described older
   runbook path.
4. Reconcile the dirty repository and select an exact release SHA.
5. Confirm the final domain, Supabase coordinates, and non-secret R2
   coordinates.
6. Enter secret values directly on the VM only when the production setup
   command requests them.
7. Run the production setup and doctor checks.
8. Deploy the selected SHA, inspect service status and logs, and run health
   checks.
9. Configure DNS and HTTPS.
10. Complete the real Google-login, agent-pipeline, artifact, preview, and
    two-user acceptance gate.

Until those checkpoints pass, describe OryxenAI as **Azure VM provisioned and
SSH-tested, application deployment pending**.

## Source documents

- [`docs/project-status.md`](../project-status.md) — current implementation,
  release gate, and deployment status.
- [`docs/deployment/06-live-azure-vm-status.md`](./06-live-azure-vm-status.md)
  — structured live Azure checkpoint.
- [`docs/deployment/02-azure-vm-runbook.md`](./02-azure-vm-runbook.md) —
  command-level deployment runbook; reconcile its older Caddy wording with
  the current script before execution.
- [`docs/deployment/03-acceptance-and-operations.md`](./03-acceptance-and-operations.md)
  — health, authentication, generation, preview, restart, backup, and cost
  acceptance checklist.
- [`docs/deployment/07-ai-assisted-operations.md`](./07-ai-assisted-operations.md)
  — redacted-log and AI handoff rules.
- `AGENTS.md` — repository source of truth and collaboration rules.
- `CHANGES.md` — committed implementation and verification history.
- `DECISIONS.md` — architectural decisions and rejected alternatives.
