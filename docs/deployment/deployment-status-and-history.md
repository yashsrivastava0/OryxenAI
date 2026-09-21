# OryxenAI deployment status and history (combined)

This canonical record preserves the original Azure status checkpoints and live deployment session log in one place.

## Current operator checkpoint — 2026-09-21

This is an operator-reported browser-verification checkpoint. It records
external configuration that was confirmed outside the repository; it does not
claim that the application has been deployed or accepted in production.

### Follow-up Azure recheck — 2026-09-21

- Subscription, resource group, VM identity, Ubuntu 24.04 LTS x64 image,
  `Standard_B2as_v2` size, static public IP `20.235.74.81`, and the attached
  64 GiB Standard SSD LRS disk were reverified.
- The VM was still running. Azure Portal did not expose guest free-space
  information in this recheck; the VM-side `disk-check` remains pending.
- The resource inventory contained eight expected resources: VM, NIC, disk,
  VNet, NSG, public IP, SSH key, and Azure Network Watcher. No database,
  App Service, AKS, load balancer, or second VM was present.
- Azure outbound TCP/443 diagnostics reported reachability to GitHub, Docker
  Hub, Supabase, Google, OpenAI, and Anthropic with 316 probes and no failures.
- The current operator public IP was reported as `182.156.19.94`, while the
  TCP 22 rule still allows only `106.192.207.210/32`. No NSG change was made.
  Before SSH, obtain confirmation and replace only the TCP 22 source with the
  current trusted `/32`; keep TCP 80/443 and all internal-port rules unchanged.
- The Azure Sponsorship page reported no active Sponsorship. Portal cost was
  reported as ₹438.29 with a forecast of ₹709.66; the remaining-credit and
  spending-limit figures remain unverified.

### Azure browser configuration finalized — 2026-09-21

- The current operator IP was rechecked as `182.156.19.94`.
- The NSG rule was saved and verified after reload: `Allow-SSH-MyIP`, TCP 22,
  source `182.156.19.94/32`, priority 100, Allow.
- TCP 80/443 and all other NSG rules remained unchanged.
- Azure browser-side infrastructure configuration is complete. Guest disk
  free space, SSH connectivity, Docker setup, application deployment, and
  runtime acceptance remain deployment-side checks.

### SSH connectivity and guest disk verification — 2026-09-21

- Read-only SSH connectivity succeeded to `20.235.74.81` using the
  operator-supplied Ed25519 key; the VM identified itself as
  `oryxenai-demo-vm`.
- The authenticated Linux user was `oryxenaiadmin`.
- Guest root storage reported 61 GiB total, 2.0 GiB used, 60 GiB available,
  and 4% usage on `/`; this satisfies the configured storage thresholds.
- Docker was not installed yet. VM repository setup, Docker installation,
  production configuration, deployment, and acceptance remain pending.
- No private-key contents or credential values were recorded.

### Namecheap DNS — completed

- Registrar/DNS host: Namecheap BasicDNS; Namecheap is authoritative for
  `oryxenai.me`.
- Saved and rechecked after reload:
  - `A app -> 20.235.74.81` (TTL Automatic)
  - `A preview -> 20.235.74.81` (TTL Automatic)
- Existing `@` and `www` records were left unchanged.
- No duplicate, MX, AAAA, wildcard, or nameserver changes were made.
- DNS work for the current `app.oryxenai.me` and `preview.oryxenai.me` hosts is
  complete. The bare domain and `www` are not part of the current Caddy host
  configuration.

### Azure infrastructure verification — completed

- Subscription: `Azure for Students` (active).
- Resource group: `oryxenai-demo-rg`.
- VM: `oryxenai-demo-vm`.
- VM state at checkpoint: running.
- Public IPv4: `20.235.74.81`.
- Public IP allocation: static.
- Inbound network rules confirmed:
  - TCP 22 from `106.192.207.210/32` only.
  - TCP 80 from Any.
  - TCP 443 from Any.
  - No public allow rules for TCP 5432, 5544, 8000, or 4174.
- Outbound Internet access was reported working, including DNS/HTTPS
  connectivity to Supabase, Google, and Docker Hub.
- Storage reported: 64 GiB disk with approximately 59 GiB free on `/`.
- `/srv/oryxenai` and `/srv/oryxenai-backups` do not exist yet; the production
  setup/storage-init command must create them with the service ownership and
  permissions required by Compose.
- The SSH rule was not independently checked against the current operator
  public IP. Recheck the actual egress IP immediately before SSH; if it is not
  `106.192.207.210`, replace the rule with the current trusted `/32` and do
  not broaden SSH to Any.
- The VM was intentionally left running because deployment timing was not
  specified. Deallocate it when pausing work to limit Azure credit usage.

The follow-up recheck confirms the VM/network shape but does not authorize an
SSH rule change, deployment, or a billing-plan change.

### Repository/release state at this checkpoint

- Local worktree was clean when inspected.
- Branch: `deployment` (13 commits ahead of `origin/deployment`).
- Current HEAD: `1bf6edb4ac10a4b5442de3c60416ab075e6db34d`.
- The earlier release-check run covered `aede6f0c7dc8bca142a33b1471bee16a8ba10dce`,
  not the newer documentation HEAD. That run passed Compose validation but
  failed Ruff, formatting, Mypy, and one integration test; therefore no SHA is
  currently approved for deployment.
- No Azure Docker image build, repository checkout, production `.env`,
  migration, Caddy certificate issuance, application deployment, or live
  end-to-end acceptance has been recorded.

The latest local repository inspection after this checkpoint found a clean
`deployment` branch, 14 commits ahead of `origin/deployment`, at
`52dcd6544705243c591fafb644939dcfd318b212`. That SHA is documentation-clean
but is not release-approved until the complete release gate passes.

### Next checkpoint

1. Reconcile the release branch and run the complete release gate against the
   exact SHA intended for deployment.
2. Recheck the current SSH egress IP and connect to the running VM.
3. Clone/checkout the exact release SHA and run
   `./scripts/azure-deploy.sh setup` privately on the VM.
4. Run `doctor`, `disk-check`, and storage/read-back checks.
5. Deploy the exact verified SHA, then configure/verify Supabase and Google
   OAuth production URLs and complete HTTPS/browser acceptance.


## Included source documents

- [Current Azure deployment status](#source-04-current-azure-deployment-status)
- [Live Azure VM deployment status](#source-06-live-azure-vm-status)
- [Live Azure deployment session log](#source-08-live-azure-deployment-session-log-2026-09-14)

<!-- BEGIN SOURCE: 04-current-azure-deployment-status.md -->
<a id="source-04-current-azure-deployment-status"></a>

# Current Azure deployment status

> **Historical checkpoint:** The VM wizard was later completed successfully.
> This file records the pre-provisioning wizard state only. For the current
> post-creation state, read [`06-live-azure-vm-status.md`](./06-live-azure-vm-status.md).
> The current operational strategy supersedes the older manual/native-Caddy
> instructions in this historical file; use [`02-azure-vm-runbook.md`](./02-azure-vm-runbook.md)
> and `scripts/azure-deploy.sh` for deployment.

**Checkpoint purpose:** This file is the handoff state for the human user and
the next step-by-step deployment assistant. Read it before touching the Azure
VM wizard. Update it after each meaningful portal step.

> **Browser reset note:** This was the previous interrupted wizard checkpoint.
> The PC was powered off and the browser wizard state was lost. The target
> values below remain useful, but start the fresh session from Azure Portal
> home and follow [`05-chrome-browser-agent-azure-setup-prompt.md`](./05-chrome-browser-agent-azure-setup-prompt.md).

**Last reported state:** Azure Portal → **Create a virtual machine** →
**Networking** tab.

**Critical status:** The VM has **not** been created. Only the resource group
listed below is definitely provisioned. Docker, Ubuntu runtime access, SSH
access, PostgreSQL, DNS, Caddy, Supabase, Cloudflare R2, and application
deployment have not started.

## 1. Azure subscription

The user is deploying OryxenAI as a small two-user demo on Microsoft Azure.

| Field | Confirmed value |
| --- | --- |
| Subscription | `Azure for Students` |
| Starting credit | `$100` |
| Credit shown as available | `$100 out of $100` |
| Remaining duration | `365 days` |
| Expiration shown in Azure | `05/09/2027` |
| Azure cost before deployment | `$0.00` |
| Cost policy | Keep spending protection enabled |

Never upgrade this subscription to Pay-As-You-Go or add paid Azure services
without explicit approval. The selected VM currently shows approximately
`$35.92` in the Azure wizard; this is the portal's estimate at selection time,
not a permanent price guarantee.

## 2. Resource group — completed

This is the only Azure resource definitely created so far.

| Field | Value |
| --- | --- |
| Resource group | `oryxenai-demo-rg` |
| Region | `Central India` |
| Subscription | `Azure for Students` |

Do not create another resource group.

## 3. Current VM wizard

The VM wizard is still open. The user has completed Basics and Disks and has
just selected **Next: Networking**.

The VM creation request has not been submitted. Do not click **Review +
create** or **Create** until Networking, Management, Monitoring, Advanced,
Tags, and the final validation have been reviewed.

| Field | Intended value |
| --- | --- |
| VM name | `oryxenai-demo-vm` |
| Region | `(Asia Pacific) Central India` |
| Extended Zone | Off |
| Availability | No infrastructure redundancy required |
| Security type | Trusted launch virtual machines |
| Operating system | Ubuntu Server 24.04 LTS — x64 Gen2 |
| Architecture | x64; do not use Arm64 |
| Azure Spot | Off |
| Hibernation | Off |
| VM size | `Standard_B2as_v2` |
| vCPUs | 2 |
| RAM | 8 GiB |
| Portal estimate shown | `$35.92` |
| Authentication | SSH public key |
| Linux username | `oryxenaiadmin` |
| SSH key flow | Generate new key pair |
| SSH format | Ed25519 |
| SSH key pair name | `oryxenai-demo-key` |
| Basics public inbound ports | None |

### Why these VM choices are fixed

- Keep Trusted Launch. The portal presented it as the current Ubuntu Gen2
  default, and there is no reason to switch back to Standard.
- Keep x64. The stack includes Docker, Node/npm, Chromium, and build tooling;
  conventional x86-64 compatibility is preferred.
- Keep Azure Spot off. PostgreSQL and the worker should not be evicted as a
  normal part of the demo.
- Keep hibernation off. Azure indicated that it is incompatible with the
  selected Trusted Launch/Linux combination in this configuration.
- Keep `Standard_B2as_v2` for now. It is the preferred 8 GiB size for the
  combined PostgreSQL, API, worker, preview gateway, Caddy, Node/npm,
  Chromium, and Code Generator workload.
- `Standard_B2als_v2` is only a fallback if capacity or credit pressure later
  makes it necessary. It is not the current selection.

## 4. Disk configuration — completed in the wizard

The initial Azure defaults were changed to reduce the student-credit burn.

| Field | Current value |
| --- | --- |
| OS disk size | `64 GiB (E6)` |
| OS disk type | `Standard SSD (LRS)` |
| Disk encryption | Platform-managed key |
| Encryption at host | Off |
| Delete OS disk with VM | On |
| Ultra Disk compatibility | Off |
| Additional data disks | None |

Azure indicated that managed disks are encrypted at rest. Encryption at host
was not registered for the selected subscription, so it is not being enabled.
Do not create a customer-managed key or KMS configuration for this demo.

The demo will use the main OS disk for PostgreSQL, local working data,
generated artifacts, and previews. The first release does not use Cloudflare
R2; Docker-backed VM storage is the selected artifact/preview boundary.

Keep **Delete with VM** on to reduce the chance of leaving a billable managed
disk behind if the VM is intentionally deleted.

## 5. Administrator and SSH state

The wizard is configured for SSH public-key authentication only.

| Field | Value |
| --- | --- |
| Authentication type | SSH public key |
| Linux administrator | `oryxenaiadmin` |
| Key generation | Generate new key pair |
| Key format | Ed25519 |
| Key pair name | `oryxenai-demo-key` |

The downloaded private key must remain private on the user's machine. Never
paste it into ChatGPT, another AI conversation, GitHub, source control, `.env`,
Discord, or any other shared channel.

The eventual SSH command will resemble:

```bash
ssh oryxenaiadmin@<AZURE_PUBLIC_IPV4>
```

No public IPv4 exists yet because the VM and networking resources have not
been created.

## 6. Networking tab — exact target configuration

The Networking page is the current stopping point. The user has not yet
confirmed or applied these values in the portal.

### Virtual network

| Field | Target value |
| --- | --- |
| VNet name | `oryxenai-demo-vnet` |
| Address space | `10.0.0.0/16` |
| Subnet name | `oryxenai-demo-subnet` |
| Subnet range | `10.0.0.0/24` |

### Network resources

| Resource | Target name |
| --- | --- |
| Network interface | `oryxenai-demo-nic` |
| Public IP | `oryxenai-demo-ip` |
| Network security group | `oryxenai-demo-nsg` |

If the wizard does not expose the NIC name field, do not abort only for that
reason. Verify the automatically generated NIC before final creation if the
portal makes that possible.

### Public IP

The intended public IP properties are:

| Field | Target value |
| --- | --- |
| Resource name | `oryxenai-demo-ip` |
| IP version | IPv4 |
| SKU | Standard |
| Allocation | Static |
| Routing preference, if shown | Microsoft network |

`oryxenai-demo-ip` is the Azure resource name, not the numerical address. The
actual address will be allocated only after networking/VM creation.

### Network Security Group

Use an explicit or advanced NSG. The eventual public rules are exactly:

| Priority | Name | Protocol | Destination | Source | Action |
| ---: | --- | --- | ---: | --- | --- |
| 100 | `Allow-SSH-MyIP` | TCP | 22 | User's current public IPv4 `/32` | Allow |
| 110 | `Allow-HTTP` | TCP | 80 | Any | Allow |
| 120 | `Allow-HTTPS` | TCP | 443 | Any | Allow |

For SSH, use the user's actual current public IPv4 followed by `/32`. The
example address `203.0.113.10/32` is documentation-only and must not be used.
Do not require the user to disclose their address in chat if they prefer to
enter it directly in Azure.

Do **not** create public allow rules for:

```text
5432  PostgreSQL container port
5544  Docker host database port
8000  FastAPI host port
4174  Preview gateway host port
```

Those services remain private to the VM/Docker network. Caddy will eventually
expose the application through ports 80 and 443.

### Load balancing and private IP

| Field | Target value |
| --- | --- |
| Load balancing | None |
| Azure Load Balancer | Do not create |
| Application Gateway | Do not create |
| Azure Front Door | Do not create |
| Private IP allocation | Dynamic/default |

One VM is sufficient. A manually assigned static private IP is not required at
this stage.

### Cleanup behavior

Where the portal provides these options, prefer:

- Delete public IP with VM: On.
- Delete NIC with VM: On.
- Delete OS disk with VM: already On.

This reduces the chance of orphaned resources consuming the student credit.

## 7. Azure settings still to inspect

After Networking, the next assistant must inspect these wizard tabs before
creation:

1. Management
2. Monitoring
3. Advanced
4. Tags
5. Review + create

The VM must not be considered provisioned until Azure successfully completes
the creation operation and shows the VM resource with a public IPv4.

## 8. Eventual server architecture

After the VM exists, the intended application-side architecture is:

```text
Azure Linux VM
└── Ubuntu 24.04 LTS x64
    └── Docker Compose
        ├── PostgreSQL
        ├── database migration service
        ├── FastAPI application
        ├── durable worker
        ├── shared preview gateway
        ├── Code Generator
        │   ├── Node.js
        │   ├── npm
        │   ├── Chromium
        │   └── build tooling
        └── Caddy
            ├── HTTP :80
            └── HTTPS :443
```

External services remain:

```text
Supabase
└── Google authentication

Cloudflare R2
├── generated artifacts
└── generated previews
```

This plan intentionally does not use Azure Database for PostgreSQL, Azure App
Service, Azure Kubernetes Service, separate Azure worker services, or a second
Azure VM.

## 9. Future public hostnames

The eventual public hostnames will be:

```text
Application: https://app.<MY_DOMAIN>
Preview:     https://preview.<MY_DOMAIN>
```

Both will eventually have DNS A records pointing to the Azure static public
IPv4. Caddy will terminate HTTPS.

The domain has not yet been configured during the Azure wizard.

## 10. Supabase work — pending

Nothing in Supabase has been configured for this deployment yet.

Later, configure:

- a production Supabase project;
- Google OAuth;
- Supabase Site URL;
- Supabase callback URL;
- expected callback:
  `https://app.<MY_DOMAIN>/auth/callback`.

Do not perform this until the VM and domain situation are ready enough to use
the final HTTPS application origin.

## 11. Cloudflare R2 work — pending

Nothing in Cloudflare R2 has been configured during this deployment session.

Later, create/configure:

- R2 bucket;
- R2 access key ID;
- R2 secret access key;
- artifact storage configuration;
- preview storage configuration.

Never ask the user to paste R2 credentials into chat. Enter them directly on
the VM when creating `.env`.

## 12. Secrets policy

Never request or paste any of the following into an AI conversation:

```text
POSTGRES_PASSWORD
private SSH key
SUPABASE_SECRET_KEY
R2_SECRET_ACCESS_KEY
OpenAI/model-provider API keys
image-provider API keys
other production secrets
```

These values will eventually be entered directly into the VM's `.env` file.
Non-secret identifiers such as resource names, subscription IDs, resource
group names, hostnames, and commit SHAs may be discussed in chat.

Expected `.env` categories are:

```text
POSTGRES_PASSWORD

SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY

R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY

model-provider variables required by config/models.toml
image-provider variables required by the active configuration
```

## 13. Git and deployment safety

No application code has been deployed to Azure.

Before copying or cloning application code onto the VM:

1. Inspect `git status`.
2. Do not deploy uncommitted work.
3. Choose one exact Git commit SHA.
4. Record that SHA.
5. Deploy exactly that version.
6. Do not accidentally include unrelated Code Generator worktree changes.

## 14. Production configuration — pending

After Azure infrastructure exists, configure all of the following:

- production `.env`;
- production TOML configuration;
- the self-contained production Docker Compose stack;
- Caddy configuration;
- Supabase configuration;
- Cloudflare R2 configuration;
- DNS.

None of these has been completed yet.

## 15. Deployment acceptance criteria

Do not call the deployment complete just because the VM is online. Final
acceptance requires all of these to work:

- Google login;
- worker job processing;
- Discovery;
- Content Architect;
- Visual Design Director;
- Build Preparation;
- Code Generator;
- generated portfolio upload;
- preview inside the application;
- direct preview URL.

## 16. Azure cost management

The available Azure credit is `$100`, and the selected VM currently shows an
estimated `$35.92` in the portal. Cost efficiency matters.

When the server is not needed for an extended period, use Azure **Stop /
Deallocate** rather than only running `sudo shutdown` inside Ubuntu. Deallocate
stops compute billing; storage and static-IP charges may still remain, so check
Azure Cost Management.

Keep the Azure spending limit/protection enabled throughout the demo.

## 17. Exact next action

The next assistant must continue from the Azure Portal's open **Networking**
tab.

Do not click **Review + create** yet.

Inspect the actual Networking fields shown by Azure and guide the user
field-by-field toward:

```text
VNet:       oryxenai-demo-vnet       10.0.0.0/16
Subnet:     oryxenai-demo-subnet     10.0.0.0/24
Public IP:  oryxenai-demo-ip         IPv4 / Standard / Static
NSG:        oryxenai-demo-nsg

100  TCP 22  user's-current-IP/32
110  TCP 80  Any
120  TCP 443 Any

No public 5432, 5544, 8000, or 4174.
No load balancer.
```

After Networking, inspect Management, Monitoring, Advanced, Tags, and Review
+ create before provisioning.

## 18. Confirmed versus prescribed values

### Definitely confirmed from the portal/user report

- Azure for Students subscription;
- `$100` available;
- `$0.00` current cost;
- `365 days` remaining;
- expiration displayed as `05/09/2027`;
- resource group `oryxenai-demo-rg`;
- Central India;
- no infrastructure redundancy;
- Trusted Launch;
- Ubuntu Server 24.04 LTS x64 Gen2;
- x64 architecture;
- Azure Spot off;
- `Standard_B2as_v2`;
- 2 vCPUs;
- 8 GiB RAM;
- portal estimate `$35.92`;
- hibernation off;
- SSH public-key flow;
- Linux user `oryxenaiadmin`;
- generated Ed25519 key pair flow;
- key pair name `oryxenai-demo-key`;
- Basics public inbound ports set to None;
- 64 GiB E6 OS disk;
- Standard SSD LRS;
- platform-managed key;
- encryption at host off;
- delete OS disk with VM on;
- Ultra Disk off;
- no additional data disks;
- Networking tab currently open;
- VM not created.

### Prescribed working values to recheck in the UI if necessary

- VM name `oryxenai-demo-vm`;
- VNet `oryxenai-demo-vnet`;
- subnet `oryxenai-demo-subnet`;
- NIC `oryxenai-demo-nic`;
- public IP resource `oryxenai-demo-ip`;
- NSG `oryxenai-demo-nsg`;
- VNet CIDR `10.0.0.0/16`;
- subnet CIDR `10.0.0.0/24`;
- Standard static IPv4 public IP;
- SSH source restricted to the user's current public IPv4 `/32`;
- public TCP 80 and 443;
- no public TCP 5432, 5544, 8000, or 4174;
- no load balancer;
- dynamic/default private IP;
- cleanup of public IP and NIC with VM where offered.

<!-- END SOURCE: 04-current-azure-deployment-status.md -->

<!-- BEGIN SOURCE: 06-live-azure-vm-status.md -->
<a id="source-06-live-azure-vm-status"></a>

# Live Azure VM deployment status

**Checkpoint purpose:** This is the current cross-tool handoff after Azure VM
provisioning and first SSH access. Read this file before the next deployment
operation and update it after each meaningful server or external-service step.

**Last Azure/SSH confirmation:** 2026-09-05, from the human operator's Azure
Portal and SSH reports.

**Documentation refresh:** 2026-09-14. This refresh records repository and
deployment progress since the SSH checkpoint; it did not perform a new Azure
Portal or SSH check. Verify the VM power state, current public IP, and credit
balance live before the next server command.

## Current phase

The Azure VM has been created successfully and was reachable over SSH. The
current Windows laptop is now the primary deployment machine. The Mac laptop
was used for the initial SSH connection and early package setup, but it is no
longer required for the deployment workflow.

The current deployment stopping point remains **before Docker installation**.
The application has not been cloned or started on the VM. If the user stopped
or deallocated the VM while idle, start it and re-check SSH before continuing.

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
remain private behind the Compose-managed Caddy reverse proxy.

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

The user reports that the Supabase project is ready. The production VM still
needs the Supabase URL, publishable key, server-only key, and the final Google
OAuth Site URL/redirect configuration. The exact HTTPS origin must be settled
before applying those settings:

```text
Site URL:      https://app.<DOMAIN>
Redirect URL:  https://app.<DOMAIN>/auth/callback
```

The user reports that Cloudflare R2 artifact storage is already set up and
that an R2 API token, access key, and secret key are available. The values
were not displayed or recorded. This means the external account is reported
ready; it does **not** mean the VM production configuration has been created
or tested.

Before the VM is configured, confirm only the non-secret R2 identifiers:

- bucket name;
- Cloudflare account ID or S3-compatible endpoint;
- whether the bucket is private; and
- whether the required lifecycle policy is configured.

The runtime production configuration primarily needs the R2 S3-compatible
endpoint/account ID, bucket, access key ID, and secret access key. The API
token must not be substituted for the S3 secret key. Enter secret values
directly into the VM-local production `.env` when deployment begins.

## Repository implementation status at the 2026-09-14 refresh

Since the original Azure checkpoint, the committed branch has gained and
recorded the following implementation work:

- guided Azure VM Compose deployment with production Compose/Caddy/TOML
  overlays, release-SHA deployment, preflight/doctor checks, health checks,
  backup, status, logs, and rollback commands;
- the authenticated studio flow through explicit Generate/Preview;
- the Code Generator control room with real milestone progress, preview
  theater, attention/retry state, and traceability diagnostics;
- the administrator control plane;
- public fictional portfolio examples and art-directed preview motion; and
- Code Generator brief-ingestion, preview-first verification, retry/receipt,
  and Windows Vite-spawn diagnostics fixes.

These are repository capabilities, not evidence that the live Azure VM has
run them. The current shared worktree also contains uncommitted and untracked
work from another contributor. Use a clean, reviewed SHA for the first VM
release.

## Not done yet

None of the following has been performed on the VM:

- Docker Engine installation.
- Docker Compose plugin installation.
- Compose-managed Caddy configuration.
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

The fact that the Azure VM is online and SSH works is only an infrastructure
checkpoint. It is not a deployed application or an end-to-end acceptance
result.

Do not claim the application is deployed merely because the VM and SSH work.

## Next exact checkpoint

Continue from the current Windows laptop and active SSH session. Prepare the
external prerequisites, then follow the guided script in the runbook:

1. Reconcile the shared worktree, run the required checks, and choose one
   exact clean release SHA.
2. Confirm the repository URL and deployment branch/commit.
3. Confirm the production Supabase project, Google provider, and final domain
   origin.
4. Confirm the private Cloudflare R2 bucket and its non-secret identifiers;
   keep secret values out of chat.
5. Configure DNS for `app.<DOMAIN>` and `preview.<DOMAIN>` to
   `20.235.74.81`.
6. Start the VM if it is deallocated, then clone the selected release onto it.
7. Run `./scripts/azure-deploy.sh setup`; it installs Docker, creates the
   VM-local `.env`, and renders the production TOML overlay.
8. Run `./scripts/azure-deploy.sh doctor`, then
   `./scripts/azure-deploy.sh deploy <EXACT_RELEASE_SHA>`, followed by `verify`
   and the browser
   acceptance checks. Caddy is started by Compose; do not install it natively.
9. Run health, authentication, worker, generation, and
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

<!-- END SOURCE: 06-live-azure-vm-status.md -->

<!-- BEGIN SOURCE: 08-live-azure-deployment-session-log-2026-09-14.md -->
<a id="source-08-live-azure-deployment-session-log-2026-09-14"></a>

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

- `compose.yaml` for local development with loopback ports and optional
  validation profiles;
- `compose.production.yaml` for the self-contained production stack: PostgreSQL,
  migrations, API, worker, preview gateway, and Caddy;
- VM-local persistent storage for PostgreSQL, generated artifacts, previews,
  worker state, and Caddy data, subject to backup, retention, and disk checks;
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

<!-- END SOURCE: 08-live-azure-deployment-session-log-2026-09-14.md -->
