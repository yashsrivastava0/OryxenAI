# Azure issue: SSH connectivity and first deployment attempt

**Date:** 2026-09-21  
**Scope:** `oryxenai-demo-vm` SSH access and the first Azure deployment attempt.  
**Current status:** The VM guest SSH service is healthy, but external TCP 22 connectivity from the operator machine is still failing. No deployment is currently running.

## Azure coordinates

- Subscription: `Azure for Students`
- Resource group: `oryxenai-demo-rg`
- VM: `oryxenai-demo-vm`
- Public IP: `20.235.74.81` (static)
- OS: Ubuntu 24.04 LTS, x64
- Size: `Standard_B2as_v2`, 2 vCPU, approximately 8 GiB RAM
- Disk: 64 GiB Standard SSD LRS
- SSH user: `oryxenaiadmin`
- Local private-key path: `C:\Users\Yash Srivastava\Desktop\01_Projects\KEY-SECURE-AZURE\oryxenai-demo-key.pem`

## Azure networking state

- TCP 22 rule name: `Allow-SSH-MyIP`
- Current saved source: `152.58.120.139/32`
- Protocol/port: TCP/22
- Priority: 100
- Action: Allow
- TCP 80 and 443 rules were not changed.
- Ports 5432, 5544, 8000, and 4174 have no public allow rules.
- The SSH rule previously used `182.156.19.94/32`; the operator's public IP later changed.
- The operator's current public IP was confirmed with `api.ipify.org` as `152.58.120.139`.
- The local Wi-Fi address shown by PowerShell was `172.20.10.2`; this is not the address to place in the Azure NSG.

## Guest-side SSH verification

Azure Portal **VM → Run command → RunShellScript** was used without changing configuration. It reported:

- SSH service: `active`
- SSH state: `active (running)`; PID `2186`
- Listening sockets: `0.0.0.0:22` and `[::]:22`
- SSH journal for the preceding two hours: `-- No entries --`
- UFW: `Status: inactive`
- Prior successful SSH sessions were shown from `182.156.19.94`.

No SSH restart, VM restart, firewall change, or deployment command was run through Run Command.

## Local SSH and TCP results

The normal Windows SSH command is:

```powershell
ssh -i "C:\Users\Yash Srivastava\Desktop\01_Projects\KEY-SECURE-AZURE\oryxenai-demo-key.pem" oryxenaiadmin@20.235.74.81
```

The command has returned:

```text
ssh: connect to host 20.235.74.81 port 22: Connection refused
```

PowerShell TCP testing returned:

```text
RemotePort       : 22
SourceAddress    : 172.20.10.2
TcpTestSucceeded : False
PingSucceeded    : False
```

ICMP ping failure is not itself diagnostic because ping may be blocked. The TCP 22 failure is the relevant result. A read-only SSH test from the deployment workstation also timed out before authentication; the private key was not reached.

After Azure confirmed and saved `152.58.120.139/32`, a fresh TCP 22 test still failed. Therefore the remaining issue is the effective public ingress path, not the SSH key or the guest `sshd` process.

## First deployment attempt

1. An SSH session to the VM previously succeeded.
2. The VM was updated with `apt-get update` and the small bootstrap package set (`ca-certificates`, `curl`, `git`, and `openssl`).
3. The `deployment` branch was cloned into `~/oryxenai` and `scripts/azure-deploy.sh` was made executable.
4. An initial `./scripts/azure-deploy.sh setup` input attempt was cancelled after an incorrect value was entered at the persistent-data-root prompt. The VM `.env` file was removed afterward.
5. `./scripts/azure-deploy.sh setup` was rerun. It initialized `/srv/oryxenai`, pulled the pinned PostgreSQL image, validated merged production Compose configuration, and reported that Docker, storage, and doctor checks passed.
6. The first release deployment then targeted the old application SHA:

```text
91f0d187d6de67a6d6db158b70d235cd773b11c4
```

The deployment record identifies this as the `deploy` path, equivalent to:

```bash
./scripts/azure-deploy.sh deploy 91f0d187d6de67a6d6db158b70d235cd773b11c4
```

The literal invocation line was not captured in the terminal transcript, but the target SHA is recorded. There is no separate `build` subcommand; image building is part of `deploy`.

## Deployment failure details

- The application image built successfully in approximately 197.5 seconds.
- Failure occurred afterward during the temporary offline npm-cache warm-up worker.
- Error:

```text
Error: Cannot find module '../lib/cli.js'
Require stack:
- /usr/local/bin/npm
Node.js v22.23.2
[azure] ERROR: command failed at line 60 (exit 1)
```

- Root cause: the runtime image copied the Node image's `npm` and `npx` symlink launchers as regular files, breaking npm's relative module resolution.
- The corrected Dockerfile copies the npm package, recreates the `npm` and `npx` symlinks, and checks `npm --version` and `npx --version` during the image build.
- The old SHA must not be retried. A newly verified release SHA is required after the correction is published.

## Containers and process state at failure

- `docker compose build` completed.
- A one-off `worker-run-...` container was created for npm-cache warm-up and started its entrypoint.
- The Compose network `oryxenai_backend` was created.
- The failure happened before the script's later `docker compose up` for PostgreSQL and migrations.
- No long-running app, worker, preview gateway, Caddy, migration, or PostgreSQL runtime was started by this attempt.
- The `--rm` one-off run was intended to remove its temporary container; cached image layers and network state may remain.
- The deployment script exited after the error. No background deployment process, terminal multiplexer, lock file, or SSH session was intentionally left running. The SSH session was later closed with `exit`.

## VM resource observations before the failure

- RAM: approximately 7.7 GiB total and 7.2 GiB available.
- Swap: 0 B.
- Root disk: approximately 61 GiB total, 60 GiB available, and 2 GiB used at the SSH check.
- Later doctor output reported approximately 58 GiB free.
- No disk-exhaustion message, OOM-killer message, or memory failure was observed.

## Accidental shell input

These Dockerfile instructions were later typed at the Bash prompt:

```text
COPY --from=frontend-builder /usr/local/bin/npm /usr/local/bin/npm
COPY --from=frontend-builder /usr/local/bin/npx /usr/local/bin/npx
COPY --from=frontend-builder /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
```

They produced `COPY: command not found`. They were manually pasted as Dockerfile repair text into the SSH shell; the deployment script did not leak Dockerfile content into shell input.

## Current unresolved point

The guest confirms that `sshd` is listening, but external TCP 22 remains unsuccessful even after the NSG rule was saved for the current public IP. The next Azure-side evidence needed is:

- effective security rules for the VM NIC/subnet;
- Network Watcher IP Flow Verify for inbound TCP/22 from `152.58.120.139` to the VM's private IP;
- confirmation that `20.235.74.81` is still attached to this VM's active NIC.

No deployment retry should occur until external SSH connectivity is restored and the effective Azure path is understood.

## Follow-up session — 2026-09-21 (evening): suspected carrier-path filtering

**Context change:** the earlier successful SSH session and first deployment
attempt (documented above) happened over the operator's office Wi-Fi. This
follow-up session started with the operator at home on a Jio mobile hotspot
(iPhone 12 Personal Hotspot, tethered to the Windows laptop) — a different
network path than everything documented above.

- Fresh SSH attempts from the Jio-hotspot IP (`152.58.120.139`, confirmed via
  `api.ipify.org`/`checkip.amazonaws.com`) failed, first as an immediate
  `Connection refused`, later as a silent `Connection timed out`.
- Azure Network Watcher **IP Flow Verify** was run for this IP and returned
  `Access: Allow` via rule `Allow-SSH-MyIP` (NSG `oryxenai-demo-nsg`,
  VM private IP `10.0.0.4`, TCP/22 inbound) — confirming the NSG is not the
  blocker for this IP either.
- Raw TCP tests from the same machine/network showed port 22 and 443 to
  `github.com` succeeding normally, while port 22/80/443 to the VM's own IP
  (`20.235.74.81`) failed — i.e. general outbound connectivity on these ports
  works, but specifically the path to this VM does not.
- Working hypothesis (not confirmed with carrier-side evidence): Jio's mobile
  network applies destination-specific (ASN/datacenter-range) filtering or
  throttling to this Azure India datacenter's IP range for tethered/hotspot
  traffic, distinct from a blanket port-22 block. This is consistent with all
  observations above but has not been independently verified against Jio's
  own documentation or support.
- **Test performed:** Cloudflare WARP (the `1.1.1.1` app) was enabled on the
  Windows laptop to reroute traffic off the Jio path. Confirmed egress IP
  changed from `152.58.120.139` to `104.28.192.188`.
- The NSG rule `Allow-SSH-MyIP` was updated (via Azure Portal, by a separate
  AI session with browser access) from `152.58.120.139/32` to
  `104.28.192.188/32`, same priority (100), same protocol/port (TCP/22), no
  other rule touched. Result pending confirmation/reload at the time of this
  entry.

**This is an explicitly temporary workaround, not a fix:** Cloudflare WARP
does not guarantee a stable exit IP across reconnects — a future WARP
session could get a different IP, requiring the NSG rule to be updated again.
No durable solution (e.g. Azure Bastion, which needs no public inbound SSH
rule at all, or a VPN/static-IP arrangement) has been chosen yet; this
remains an open follow-up decision, not something resolved by this
workaround.

**Whoever reads this next:** if SSH to `20.235.74.81` fails again, first
check the operator's current network (office Wi-Fi vs. mobile hotspot vs.
VPN state) and current egress IP before assuming a new Azure-side problem —
this session's evidence strongly suggests network path, not VM or NSG
misconfiguration, is the recurring cause on non-office networks.

### Conclusion for this session — exhausted Azure-side diagnostics

All Azure-side and VM-side evidence checks out clean:

- Network Watcher IP Flow Verify returned `Access: Allow` for **both**
  tested source IPs (`152.86.120.139/32` Jio, then `104.28.192.188/32`
  Cloudflare WARP/One), matching rule `Allow-SSH-MyIP` both times.
- Azure Portal Run Command (`RunShellScript`) confirmed, live, during this
  session: `sshd` active and listening on `0.0.0.0:22`/`[::]:22`, `ufw`
  inactive, iptables `INPUT` chain policy `ACCEPT` with **zero rules**, no
  `fail2ban` installed, and `journalctl -u ssh` showed **zero entries** for
  the exact window covering a timestamped SSH attempt from
  `104.28.192.188`. The packet never reached the VM's kernel/sshd at all.
- The same `ssh` command was run three ways with an identical
  `Connection timed out` result: through the AI's Bash tool, through the
  AI's PowerShell tool, and by the operator directly in their own fresh
  PowerShell window — ruling out anything specific to how either AI tool
  executes commands.
- A `tracert -d -w 1000` attempt to confirm the network path had a typo
  (traced `20.235.74.8`, not the real VM IP `20.235.74.81`) and is not
  conclusive either way; ICMP traceroutes routinely die after hop 1 on
  Indian mobile carrier networks regardless of whether the underlying TCP
  path works, so this was not repeated.

**Working conclusion:** this is very likely a network-path issue specific
to tonight's connection (Jio mobile hotspot, and separately Jio-through-
Cloudflare-One), not a repository, Azure resource, or NSG misconfiguration.
The one prior successful session today was over office Wi-Fi. No further
Azure-side changes are indicated — the next productive step is simply
retrying from a network path already known to work (office Wi-Fi) or a
different network/VPN not yet tried, rather than more Azure-side
diagnostics.

**Follow-up worth deciding later (not decided in this session):** a durable
fix so this doesn't recur regardless of network — e.g. Azure Bastion (no
public inbound SSH port needed at all) — versus continuing to re-pin the
NSG rule to whatever IP is current each session.

## Credential handling

No private-key contents, passwords, API keys, tokens, or production `.env` values are recorded in this file.
