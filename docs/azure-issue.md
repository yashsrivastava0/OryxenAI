# Azure issue: SSH connectivity and first deployment attempt

**Date:** 2026-09-21  
**Scope:** `oryxenai-demo-vm` SSH access and the first Azure deployment attempt.  
**Current status:** The VM guest SSH service is healthy and the NSG is
confirmed correctly configured (see "Rule-value history" below for the
current live source IP), but external TCP 22 connectivity from the
operator's current network still fails. Extensive same-session diagnostics
narrowed this to a client-side network-path issue (see "Conclusion" near
the bottom) rather than anything wrong with the VM, NSG, or repository. The
operator is pausing for the night and will retry from the office network
tomorrow morning. No deployment is currently running on the VM.

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

- NSG name: `oryxenai-demo-nsg`.
- TCP 22 rule name: `Allow-SSH-MyIP`, protocol TCP, port 22, priority 100, action Allow.
- TCP 80 and 443 rules were not changed at any point in this document.
- Ports 5432, 5544, 8000, and 4174 have no public allow rules.
- **CURRENT LIVE SOURCE as of the end of the 2026-09-21 evening session:
  `104.28.192.188/32`** (a Cloudflare WARP/Cloudflare One exit IP — see
  "Revert reference" below before assuming this is still correct in a future
  session).
- A PowerShell `Test-NetConnection` at one point showed `SourceAddress:
  172.20.10.2` — this is the phone hotspot's local/private tunnel address on
  the Windows Wi-Fi interface, **not** a public IP; it must never be placed
  in the Azure NSG. The actual public IP must always come from an external
  service (`api.ipify.org`, `checkip.amazonaws.com`, etc.), never from a
  local `ipconfig`/`Test-NetConnection` `SourceAddress` field.

### Rule-value history (for revert reference)

| Order | Source value | When / context | Confirmed via |
|---|---|---|---|
| 1 (oldest known) | `106.192.207.210/32` | Original Azure infra setup, per `deployment-status-and-history.md` | Azure infra checkpoint doc |
| 2 (last known-good, pre-tonight) | `182.156.19.94/32` | Earlier 2026-09-21, office Wi-Fi session — this is the value that was in place during the **successful** SSH session and first deployment attempt documented below | Portal save + reload, per `deployment-status-and-history.md` |
| 3 | `152.58.120.139/32` | 2026-09-21 evening, operator on Jio mobile hotspot at home; set and re-verified twice (~8:56pm and again ~8:58–8:59pm) after an initial `Test-NetConnection` failure | Portal save + reload; Network Watcher IP Flow Verify at ~8:31–8:32pm → `Access: Allow` |
| 4 (current live value) | `104.28.192.188/32` | 2026-09-21 evening, ~9:23–9:25pm, after enabling Cloudflare WARP/Cloudflare One on the operator's laptop to test whether rerouting off the Jio path would help | Portal save + reload; Network Watcher IP Flow Verify at ~9:30–9:32pm → `Access: Allow` |

**If reverting is ever needed:** value 2 (`182.156.19.94/32`) is the last
value confirmed to actually work end-to-end (successful SSH + start of a
real deployment attempt). Values 3 and 4 were both confirmed `Allow` by
Network Watcher but SSH still did not succeed through either — see
"Conclusion" below. Reverting to value 2 only makes sense if the operator is
back on the same office network that had that IP; otherwise get the current
public IP fresh (`(Invoke-RestMethod -Uri "https://api.ipify.org").Trim()`
in PowerShell) and set that instead of guessing from this table.

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

After Azure confirmed and saved `152.58.120.139/32`, a fresh TCP 22 test still failed. Therefore the remaining issue is the effective public ingress path, not the SSH key or the guest `sshd` process. (This turned out to be the first of two source IPs tried that evening — see the "Follow-up session" timeline below for the full picture, including the second IP and the eventual conclusion.)

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

## Office-network retest — 2026-09-22

The operator returned to the office Wi-Fi and ran a fresh read-only test from
the Windows workstation. The current public IP was:

```text
182.156.19.94
```

TCP 22 test result:

```text
TCP22_REACHABLE=False
```

The Azure NSG was last saved for the mobile-hotspot address
`152.58.120.139/32`. Therefore the office test is currently blocked by the
single-IP SSH allow rule. No SSH authentication attempt was made because TCP
22 was not reachable. The office address is the earlier address associated
with prior successful SSH sessions; the Azure rule needs to be verified or
switched back to `182.156.19.94/32` before retesting.

## Follow-up session — 2026-09-21 (evening): suspected carrier-path filtering

**Context change:** the earlier successful SSH session and first deployment
attempt (documented above) happened over the operator's office Wi-Fi
(NSG source `182.156.19.94/32` at the time). This follow-up session started
with the operator at home on a Jio mobile hotspot (iPhone 12 Personal
Hotspot, tethered to the Windows laptop) — a different network path than
everything documented above. Two AI sessions were involved throughout: this
one (reasoning/diagnosis/prompt-writing) and a separate session with actual
Azure Portal browser control (referred to below as "the browser controller").

### Timeline

Two AI sessions logged overlapping clock times independently (this session's
own record vs. the browser controller's own chat log), which could not be
fully reconciled to the minute — the order below is the logically consistent
sequence (each step's prerequisites happened before it), not a
minute-by-minute transcript. Where a specific time is well-attested by both
sources it's included; otherwise steps are given in sequence only.

- First local test: `ssh ... oryxenaiadmin@20.235.74.81` →
  `Connection refused`. `Test-NetConnection 20.235.74.81 -Port 22` showed
  `TcpTestSucceeded: False` and `SourceAddress: 172.20.10.2` (the phone
  hotspot's private tunnel address — a red herring, not a public IP; flagged
  as such at the time and never placed in the NSG).
- Public IP confirmed via
  `(Invoke-RestMethod -Uri "https://api.ipify.org").Trim()` →
  `152.58.120.139`.
- NSG rule `Allow-SSH-MyIP` source set to `152.58.120.139/32` by the browser
  controller. `Test-NetConnection` still showed `TcpTestSucceeded: False`
  immediately after.
- Rule was explicitly re-verified and re-saved (same value,
  `152.58.120.139/32`, protocol TCP, port 22, priority 100, action Allow) to
  rule out a save that silently hadn't taken effect (~8:57–8:59pm). Portal
  confirmed the value persisted after reload.
- Network Watcher **IP Flow Verify** for `152.58.120.139` → port 22 →
  `Access: Allow` via `Allow-SSH-MyIP`. Confirms the NSG itself was correct
  even though SSH still failed end-to-end.
- Azure Portal **Run Command → RunShellScript** (read-only, no config
  changes) confirmed guest-side health: `sshd` active (`systemctl is-active
  ssh` → active, PID 2186), listening on `0.0.0.0:22` and `[::]:22`, `ufw
  status` → inactive, and zero `journalctl -u ssh` entries in the preceding
  two hours. Prior successful sessions in that log were from `182.156.19.94`
  (the office-Wi-Fi IP).
- **~9:02pm** — This `docs/azure-issue.md` file was created to hand off
  findings between AI sessions.
- **~9:03pm** — The mobile-hotspot-vs-office-network theory was first raised
  (independently, by the browser controller) as the likely explanation.
- Fresh SSH attempts from the Jio-hotspot IP continued to fail: first as an
  immediate `Connection refused`, later (after a cooldown wait, to rule out
  a short-lived rate limit) as a silent `Connection timed out`.
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
- **Test performed (shortly before ~9:23pm):** Cloudflare WARP / Cloudflare One (the
  `1.1.1.1` app, "Traffic and DNS (UDP)" mode) was enabled on the Windows
  laptop to reroute traffic off the Jio path. Confirmed egress IP changed
  from `152.58.120.139` to `104.28.192.188` (verified via `curl
  https://api.ipify.org` from this AI session's own shell tool, which shares
  the operator's actual machine/network — not a separate cloud sandbox;
  confirmed by the operator independently running the identical `ssh`
  command themselves in a fresh PowerShell window with the same
  `Connection timed out` result).
- **~9:23–9:25pm** — NSG rule `Allow-SSH-MyIP` updated (via the browser
  controller) from `152.58.120.139/32` to `104.28.192.188/32`, same
  priority (100), same protocol/port (TCP/22), no other rule touched.
  Confirmed saved and persisted after reload.
- **~9:27–9:29pm** — A second Run Command diagnostic (read-only) ran
  immediately after a timestamped SSH attempt from `104.28.192.188`. Result:
  `sshd` still active/listening, `ufw` inactive, **iptables `INPUT` chain:
  policy `ACCEPT`, zero rules**, `fail2ban-client: command not found` (not
  installed), and `journalctl -u ssh` showed **zero entries** for the window
  covering the timestamped attempt — the packet never reached the VM's
  kernel/sshd at all, even with WARP active and the NSG confirmed correct.
- **~9:30–9:32pm** — A second Network Watcher IP Flow Verify, this time for
  `104.28.192.188` → port 22 → `Access: Allow` via `Allow-SSH-MyIP`. Same
  clean result as the first IP.
- A `tracert -d -w 1000` attempt to confirm the network path had a target
  typo (`20.235.74.8`, missing the final digit — not the real VM IP
  `20.235.74.81`) and is inconclusive either way; ICMP traceroutes routinely
  die after hop 1 on Indian mobile carrier networks regardless of whether
  the underlying TCP path works, so this was not repeated.

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

All Azure-side and VM-side evidence checks out clean (full detail in the
timeline above): NSG confirmed `Allow` for both tested IPs via Network
Watcher, guest `sshd` confirmed healthy and listening, iptables wide open
with zero rules, no fail2ban installed, and zero journal entries for any
attempt made — meaning every attempt was dropped before ever reaching the
VM's network stack. The same result was reproduced through this AI's Bash
tool, its PowerShell tool, and the operator's own independent terminal.

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

## Resolution — 2026-09-22 morning: confirmed as office-network-only

The operator returned on office Wi-Fi the next morning. Public IP was
`182.156.19.94` — exactly the "last known-good" value from the rule-value
history table above. The NSG rule `Allow-SSH-MyIP` was updated from
`104.28.192.188/32` back to `182.156.19.94/32` (via the browser controller,
same pattern as every prior update; TCP 80/443 untouched). SSH succeeded
immediately on the first attempt:

```text
SSH_OK
oryxenai-demo-vm
oryxenaiadmin
 04:19:40 up 21:19,  1 user,  load average: 0.00, 0.00, 0.00
/dev/root  61G  6.9G  55G  12% /
Mem: 7.7Gi total, 822Mi used, 3.2Gi free, 6.9Gi available
Swap: 0B
```

**This confirms the working conclusion above without further ambiguity:**
the entire prior evening's SSH failures were specific to the operator's
non-office network path (Jio hotspot, and separately Jio+Cloudflare One),
not the VM, NSG, or repository. No Azure-side configuration was changed
tonight beyond restoring the NSG source IP to the known-good value.

**CURRENT LIVE NSG SOURCE is now `182.156.19.94/32` (office Wi-Fi)** —
supersedes the `104.28.192.188/32` value recorded earlier in this file.

### VM state confirmed on reconnect

- Docker `29.8.1`, Compose `v5.5.1` — both already installed (from the
  earlier `setup` run, per the "First deployment attempt" section above).
- Repo at `~/oryxenai` was still a detached checkout at the old, stale SHA
  `91f0d18` (the pre-fix commit) — unchanged since last night's failed
  attempt.
- `/srv/oryxenai` and `/srv/oryxenai-backups` exist. Leftover artifacts from
  the failed attempt: a `oryxenai:local` Docker image (1.79 GB) and the
  `oryxenai_backend` Docker network. Not cleaned up before the new deploy;
  `docker compose build`/`up` is expected to reconcile or replace these.
- Production `.env` at `~/oryxenai/.env` already existed (rendered during
  the earlier `setup` run) and was left untouched.

### Code transfer method (important for future sessions)

The original plan was `git archive HEAD | ssh ... tar -x` to overlay the
corrected commit onto the VM's working tree without pushing to GitHub.
**This does not work with `scripts/azure-deploy.sh`**: `deploy`'s
`resolve_release()` function explicitly refuses to run if the VM's working
tree has any tracked-file changes (`git status --porcelain
--untracked-files=no`), which a raw tar overlay would immediately trigger.
It also does `git fetch origin` + `git rev-parse <sha>` — a SHA that only
exists locally and was never pushed to `origin` cannot resolve.

**Working method used instead:** push the exact local commit directly into
the VM's own repository as a new ref, over SSH, without touching `origin`
or the VM's checked-out branch:

```bash
git push "ssh://oryxenaiadmin@20.235.74.81/home/oryxenaiadmin/oryxenai" HEAD:refs/heads/incoming-deploy
```

This transfers the commit object (and any new history) into the VM's local
git object database as a new branch ref, leaves the working tree and
current detached HEAD completely untouched (verified via `git status
--porcelain` returning empty and `git log -1` still showing the old SHA
immediately after the push), and makes the exact SHA resolvable so
`./scripts/azure-deploy.sh deploy <sha>` can `git checkout --detach <sha>`
normally through its real, unmodified code path — no script changes needed.
The temporary `incoming-deploy` ref can be deleted after a successful
deploy (`git branch -D incoming-deploy` on the VM); it is not referenced by
the deploy script itself once checked out.

### Deploy result — partial success, new bug found

`./scripts/azure-deploy.sh deploy a19a7c57fae131e7f6bb9324737fa85d7da494af`
(the local `deployment` HEAD at the time, 8 commits ahead of
`origin/deployment`, not pushed — includes the npm/npx symlink fix plus the
CI/security fixes from the production-readiness audit) got substantially
further than the previous attempt:

- **All 4 Docker images built successfully.** `npm --version` and `npx
  --version` both resolved cleanly to `10.9.8` during the build, confirming
  the `d60d40b` npm/npx symlink fix works correctly in a real build — the
  original blocker from the first deployment attempt is resolved.
- **New failure during npm-cache warm-up** (`compose run --rm --no-deps
  worker bash /app/scripts/warm-npm-cache.sh`):

```text
npm error code EAI_AGAIN
npm error syscall getaddrinfo
npm error errno EAI_AGAIN
npm error request to https://registry.npmjs.org/@tailwindcss%2fvite failed, reason: getaddrinfo EAI_AGAIN registry.npmjs.org
[azure] ERROR: command failed at line 57 (exit 1)
```

`EAI_AGAIN` is a complete DNS-resolution failure — the container had zero
network route to the internet, not a registry/proxy/rate-limit problem.

### Root cause: `backend` network was Docker-`internal`

`compose.production.yaml`'s `backend` network was declared `internal: true`,
and `app`, `worker`, `migrate`, and `preview-gateway` (via the shared
`&application` anchor) were **only** attached to `backend`. Docker's
`internal: true` blocks *all* outbound routing for every container on that
network, not just inbound exposure — so this wasn't only an npm-cache-warmup
problem. As configured, `worker` (model provider calls, Supabase, npm

The `internal: true` comment's stated intent — "No service other than Caddy
is attached to the public-facing network" — was about preventing *inbound*
exposure. But none of `app`/`worker`/`migrate`/`preview-gateway`/`postgres`
publish a host `ports:` mapping anyway (only `caddy` does), so a normal,
non-internal bridge network already gives that same inbound isolation
without also killing egress. `internal: true` was an over-tightened
hardening step that broke real functionality; recorded as D-109 in
`DECISIONS.md`.

**Fix applied:** removed `internal: true` from the `backend` network
definition in `compose.production.yaml` and corrected the two comments that
called it "internal-only." No other file needed to change.

**Verified locally** (Docker Desktop, this workstation, against the local
`.env`): `docker compose -f compose.production.yaml config --quiet` parses;
a worker container on the fixed network resolves `registry.npmjs.org` via
DNS and completes a real `HTTP 200` HTTPS request; the exact failing command
(`bash /app/scripts/warm-npm-cache.sh`) now completes successfully. Full
local suite also re-run clean after the fix: `ruff check`, `ruff format
--check`, `mypy src`, `pytest` (1433 passed, 5 skipped), and in `frontend/`:
`typecheck`, `test` (144 passed), `build`.

**Not yet done:** the fix has not been re-deployed to the Azure VM. Per the
operator's explicit instruction, no further VM/SSH action (re-running
`deploy`, cleaning up the leftover `oryxenai:local` image, the
`oryxenai_backend` Docker network, or the stale `incoming-deploy` git ref on
the VM) happens without a fresh, explicit go-ahead.

## Credential handling

No private-key contents, passwords, API keys, tokens, or production `.env` values are recorded in this file.
