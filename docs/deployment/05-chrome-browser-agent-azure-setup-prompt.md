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
2. Install Docker, Docker Compose, and Caddy.
3. Clone one exact committed OryxenAI release SHA.
4. Create the VM-local `.env` with secrets entered privately.
5. Create the production TOML overlay.
6. Create the production Compose override.
7. Configure Supabase Google OAuth and the exact HTTPS callback.
8. Create the Cloudflare R2 bucket and configure artifact/preview storage.
9. Configure DNS for `app.<DOMAIN>` and `preview.<DOMAIN>`.
10. Start PostgreSQL, migrations, API, worker, and preview gateway.
11. Run the complete agent-to-preview acceptance flow.

The current Azure task ends after successful VM creation and public-IP
recording. Do not mix application deployment into the VM wizard unless the
human explicitly asks to continue.
