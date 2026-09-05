# Live Azure VM deployment status

**Checkpoint purpose:** This is the current cross-tool handoff after Azure VM
provisioning and first SSH access. Read this file before the next deployment
operation and update it after each meaningful server or external-service step.

**Last confirmed:** 2026-09-05, from the human operator's Azure Portal and
SSH reports.

## Current phase

The Azure VM has been created successfully and is reachable over SSH. The
current Windows laptop is now the primary deployment machine. The Mac laptop
was used for the initial SSH connection and early package setup, but it is no
longer required for the deployment workflow.

The current stopping point is **before Docker installation**. The application
has not been cloned or started on the VM.

Successful SSH from the current Windows laptop confirms that:

- the downloaded Ed25519 private key matches the Azure VM's public key;
- the Azure public IP is reachable;
- the SSH NSG rule is working for the operator's source address; and
- the Azure administrator username is correct.

## Azure subscription and VM

| Field | Confirmed value |
| --- | --- |
| Subscription | `Azure for Students` |
| Initial credit reported | `$100 out of $100` |
| Resource group | `oryxenai-demo-rg` |
| Region | `Central India` |
| VM name | `oryxenai-demo-vm` |
| Current public IPv4 | `20.235.74.81` |
| Current VM private IPv4 | `10.0.0.4` |
| Operating system | Ubuntu Server 24.04 LTS, x64 Gen2 |
| Reported OS/kernel banner | Ubuntu 24.04.4 LTS, `6.17.0-1022-azure` |
| Architecture verified over SSH | `x86_64` |
| VM size | `Standard_B2as_v2` |
| VM capacity | 2 vCPUs, approximately 8 GiB RAM |
| Portal estimate at creation | `0.0492 USD/hr`, approximately `$35.92/month` |
| Azure Spot | Off |
| Hibernation | Off |
| Security type | Trusted launch virtual machines |
| Secure Boot | Yes |
| vTPM | Yes |
| Integrity monitoring | No |
| Authentication | SSH public key |
| Linux administrator | `oryxenaiadmin` |
| SSH format | Ed25519 |
| Azure key-pair name | `oryxenai-demo-key` |
| Basics public inbound ports | None |

The Azure deployment was reported complete, and the successful SSH session
confirms the VM is running and reachable. The portal's separate provisioning
state screenshot was not captured in this checkpoint.

## Disk configuration

| Field | Confirmed value |
| --- | --- |
| OS disk size | 64 GiB (E6) |
| OS disk type | Standard SSD, `StandardSSD_LRS` |
| Managed disk | Yes |
| Encryption | Platform-managed key |
| Encryption at host | Off/unavailable |
| Delete OS disk with VM | Yes |
| Ephemeral OS disk | None |
| Ultra Disk compatibility | Off/unavailable |
| Additional data disks | None |

## Networking configuration

| Resource/field | Confirmed value |
| --- | --- |
| VNet | `oryxenai-demo-vnet` |
| VNet address space | `10.0.0.0/16` |
| Subnet | `oryxenai-demo-subnet` |
| Subnet address range | `10.0.0.0/24` |
| Public IP resource | `oryxenai-demo-ip` |
| Public IP | IPv4, Standard SKU, Static |
| NSG | Advanced/custom, `oryxenai-demo-nsg` |
| NIC name | Azure-generated; the wizard exposed no editable NIC field |
| Accelerated networking | Off |
| Load balancing | None |
| Delete public IP with VM | Enabled |
| Delete NIC with VM | Enabled |
| Private IP allocation | Dynamic/default |

The intentional custom inbound rules are:

| Priority | Name | Source | Protocol/port | Action |
| ---: | --- | --- | --- | --- |
| 100 | `Allow-SSH-MyIP` | `106.192.207.210/32` | TCP/22 | Allow |
| 110 | `Allow-HTTP` | Any | TCP/80 | Allow |
| 120 | `Allow-HTTPS` | Any | TCP/443 | Allow |

No public allow rules were added for ports `5432`, `5544`, `8000`, or `4174`.
The application, PostgreSQL, and preview gateway are therefore expected to
remain private behind the future Caddy reverse proxy.

The SSH source address was the public IP detected during VM creation. If the
operator changes networks and SSH later times out, check the current public IP
and update only the SSH `/32` rule; do not open port 22 to Any.

## Management, monitoring, advanced settings, and tags

### Management

- System-assigned managed identity: Off.
- Microsoft Entra ID login: Off.
- Azure Backup: Off; no Recovery Services vault.
- Site Recovery: Off.
- Periodic assessment: Off.
- Hotpatch: Off.
- Patch orchestration: Image default.
- Auto-shutdown: Off.
- Hibernation: Off/unavailable.
- No paid backup, identity, security, or management add-on.

### Monitoring

- Alerts: Off.
- Boot diagnostics: Off.
- OS guest diagnostics: Off.
- Application health monitoring: Off.
- No VM Insights, Application Insights, Log Analytics workspace, Defender
  add-on, monitoring agent, or custom storage account.

### Advanced

- Extensions: None.
- VM applications: None.
- Custom data: Blank.
- Cloud-init: No.
- Capacity reservation group: None.
- NVMe: Disabled/unavailable for this VM size.
- Disk controller: SCSI.
- No scripts, user data, dedicated host, host group, or placement group.

### Tags

- `project = oryxenai`
- `environment = demo`
- `owner = student`

Azure's review page displayed these tags against generic possible resource
types, including Storage Account, Recovery Services vault, SQL VM, schedules,
and extensions. Those lines were propagation targets, not evidence that those
optional resources were created. No such optional resource was selected.

## Local operator and SSH handoff

The private key was securely copied from the Mac to the current Windows
laptop. It is stored outside the OryxenAI repository in the operator's local
secure folder. The key contents must never be put in this repository, an AI
conversation, GitHub, `.env`, or another shared location.

The current Windows SSH command is:

```powershell
ssh -i "<LOCAL_SECURE_KEY_PATH>\oryxenai-demo-key.pem" oryxenaiadmin@20.235.74.81
```

The actual local key path is intentionally not treated as deployment
configuration. The user must substitute the local path on the machine that is
running SSH.

The first SSH host-key fingerprint accepted by both machines was:

```text
SHA256:5I3/jSo9HvOfx0CFPHq2uvJrHoBM4+OCJ19zRzOD0zI
```

The Windows copy initially had an inherited/unknown ACL, so Windows OpenSSH
reported `UNPROTECTED PRIVATE KEY FILE`. The operator removed inheritance,
removed the stale SID entry where present, granted the current Windows user
read access, and then connected successfully. The key itself was not edited.

## Server preparation already completed

The following operations have completed on the VM:

```text
sudo apt update
sudo apt install -y git ca-certificates curl gnupg lsb-release
sudo apt upgrade -y
```

Observed verification:

| Check | Result |
| --- | --- |
| `whoami` | `oryxenaiadmin` |
| `hostname` | `oryxenai-demo-vm` |
| `uname -m` | `x86_64` |
| `git --version` | `2.43.0` |
| `curl --version` | `8.5.0` |
| Memory | 7.7 GiB visible, about 7.2 GiB available at idle |
| Root disk | 61 GiB visible, about 60 GiB available after setup |
| Kernel/update state | Running kernel reported up to date |
| Reboot requirement | No reboot was requested by the completed upgrade |

The package upgrade restarted the services it could restart and deferred a
few normal service restarts. No container existed yet, and no application
service was running. This is not an application failure.

## Local environment audit (not production-ready)

On 2026-09-05, the local repository's `.env` was audited without displaying
any secret values.

- `.env` exists and is correctly ignored by Git.
- The expected names from `.env.example` are present.
- The active model configuration references the provider-key names
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `OPENCODE_GO_API_KEY`; the local
  file contains those names with non-empty values.
- Supabase URL, publishable key, and server-only key names are present with
  non-empty values, but presence alone does not prove that the credentials or
  Google OAuth dashboard settings are valid.
- R2 access-key names are present with non-empty values, but their values must
  never be copied into chat or committed.
- `FIREBASE_ADMIN_CREDENTIAL_JSON` is empty; this is acceptable for the
  current Supabase Google-auth path unless a future configuration explicitly
  enables Firebase.
- `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` appears twice.
- `ORYXENAI_ALLOWED_USER_EMAILS` appears twice.
- One non-comment line at local `.env` line 42 is not parseable as a normal
  `NAME=value` entry.
- `SCALEMAX_API_KEY` and `SCALEMAX_BASE_URL` are extra local names not listed
  in the current `.env.example`; do not transfer them unless the selected
  runtime configuration explicitly requires them.

Before deployment, clean the local file so each environment variable appears
once and every non-comment line is a valid `NAME=value` assignment. Keep one
admin allow-list line and one normal-user allow-list line, using the
comma-separated format documented in `.env.example`. Do not copy this local
`.env` wholesale to the VM: create a separate production `.env` directly on
the VM and enter only the required values there.

## External prerequisite readiness reported

The user reports that Cloudflare R2 artifact storage is already set up and
that an R2 API token, access key, and secret key are available. The values
were not displayed or recorded.

Before the VM is configured, confirm only the non-secret R2 identifiers:

- bucket name;
- Cloudflare account ID or S3-compatible endpoint;
- whether the bucket is private; and
- whether the required lifecycle policy is configured.

The runtime production configuration primarily needs the R2 S3-compatible
endpoint, bucket, access key ID, and secret access key. The API token must not
be substituted for the S3 secret key and should not be copied to the VM unless
the selected deployment operation explicitly requires it. Enter secret values
directly into the VM-local production `.env` when deployment begins.

## Not done yet

None of the following has been performed on the VM:

- Docker Engine installation.
- Docker Compose plugin installation.
- Caddy installation or configuration.
- Repository clone or source-code transfer.
- Release SHA selection or deployment commit recording on the VM.
- Production `.env` creation.
- Production TOML overlay creation.
- Production Compose overlay creation.
- PostgreSQL container startup or migrations.
- FastAPI app startup.
- Durable worker startup.
- Preview gateway startup.
- Domain DNS records.
- Supabase production Google OAuth configuration.
- VM-side Cloudflare R2 configuration and validation.
- HTTPS certificate issuance.
- Application or portfolio generation acceptance testing.

Do not claim the application is deployed merely because the VM and SSH work.

## Next exact checkpoint

Continue from the current Windows laptop and active SSH session. Install Docker
Engine and the Docker Compose plugin using Docker's current official Ubuntu
repository instructions. Then add `oryxenaiadmin` to the Docker group, start a
new SSH session, and verify `docker --version` and `docker compose version`.

Do not clone or copy application code until the repository's local Git state
has been inspected and one exact release commit SHA has been selected. Do not
deploy uncommitted work or unrelated Code Generator worktree changes.

After Docker is verified, prepare the external prerequisites and production
configuration in this order:

1. Confirm the repository URL and exact release SHA.
2. Create/confirm the production Supabase project and final domain origin.
3. Create the private Cloudflare R2 bucket and collect its identifiers without
   placing secret values in chat.
4. Configure DNS for `app.<DOMAIN>` and `preview.<DOMAIN>` to
   `20.235.74.81`.
5. Clone the pinned source onto the VM.
6. Create the VM-local `.env`, production TOML overlay, and Compose overlay.
7. Install/configure Caddy after DNS and final hostnames are known.
8. Start Compose and run health, authentication, worker, generation, and
   preview acceptance tests.

Use [`02-azure-vm-runbook.md`](./02-azure-vm-runbook.md) for the command-level
deployment procedure and [`03-acceptance-and-operations.md`](./03-acceptance-and-operations.md)
for final acceptance and cost/lifecycle checks.

## Secret handling reminder

Secret values must be entered directly on the VM and must never be pasted into
an AI conversation or committed:

```text
POSTGRES_PASSWORD
SUPABASE_SECRET_KEY
R2_SECRET_ACCESS_KEY
model-provider API keys
image-provider API keys
private SSH key contents
```

Non-secret values such as the VM public IP, Azure resource names, hostnames,
and selected Git commit SHA may be recorded in deployment notes.
