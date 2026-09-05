# Current Azure deployment status

**Checkpoint purpose:** This file is the handoff state for the human user and
the next step-by-step deployment assistant. Read it before touching the Azure
VM wizard. Update it after each meaningful portal step.

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

The demo will use the main OS disk for PostgreSQL and local working data.
Generated artifacts and previews are intended to move to Cloudflare R2 later.

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
- production Docker Compose overlay;
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
