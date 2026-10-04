# 04 — Freeing the Azure VM for other projects

**Do this only after** `05-acceptance-and-troubleshooting.md` has passed on
`https://app.oryxenai.me`. Until then the VM is the rollback path. Resource
names below come from the repository's earlier Azure notes (2026-09) and may
have changed: read each value in the portal or on the VM before acting.

Known names from the repo (verify): resource group `oryxenai-demo-rg`, VM
`oryxenai-demo-vm`, Logic App `oryxenai-vm-autostart` (daily 07:00 IST start;
VM auto-shutdown 01:00 IST), VM user `oryxenaiadmin`, deploy checkout
`/home/oryxenaiadmin/oryxenai`, Compose project `oryxenai`, data under
`/srv/oryxenai` and backups under `/srv/oryxenai-backups` (defaults), GitHub
runner service `actions.runner.yashsrivastava0-OryxenAI.oryxenai-azure-vm.service`
in `/home/oryxenaiadmin/actions-runner`, Namecheap DNS records
`app` and `preview` → the VM public IP.

The repo's last dated evidence (2026-09-30) is that the VM was *Stopped
(deallocated)* and the Logic App *Disabled*; this is not a current status.

## Order of operations

### 1. Decide what to keep (5 minutes)

There is no production data (development only). If you still want a safety
copy, start the VM, then on it:

```bash
cd /home/oryxenaiadmin/oryxenai
./scripts/azure-deploy.sh backup          # writes SQL + storage archives under /srv/oryxenai-backups
ls -l /srv/oryxenai-backups               # verify the .sha256 files exist
```

Copy the archives to your own machine with `scp` (use the VM's real IP/user from
the Azure portal). Skip this if you accept losing the old test sessions.

### 2. Stop the application, do not destroy the machine

On the VM, from the deploy checkout:

```bash
docker compose -f compose.production.yaml ps          # note the real service names
docker compose -f compose.production.yaml stop        # app, worker, caddy, postgres
```

Never run `docker compose down -v` or delete `/srv/oryxenai` yet: `-v` removes
volumes. `stop` keeps everything restartable for one more observation window
(suggest a week).

### 3. Stop anything that can resurrect or redeploy it

| What | Action | Why |
| --- | --- | --- |
| GitHub self-hosted runner | On the VM: `sudo systemctl stop 'actions.runner.*'` then `sudo systemctl disable 'actions.runner.*'`; in GitHub → repo Settings → Actions → Runners, remove the runner. | A push to `deployment` would otherwise try to deploy to the VM (until doc 02 task C6 removes that CI job). |
| CI deploy job | Doc 02 task C6 (code change). | Removes the Azure deploy path from the workflow. |
| Logic App `oryxenai-vm-autostart` | Azure portal → Logic App → **Disable** (delete later). | Stops the daily 07:00 start. |
| VM auto-shutdown | Leave or remove according to what the *next* project needs. | |
| Namecheap A records `app`, `preview` | Already replaced in doc 03 Step 4. | The domain must not point at a machine you are about to reuse. |

### 4. Remove only OryxenAI's footprint from the VM

After the observation window, with the next project's needs in mind:

```bash
cd /home/oryxenaiadmin/oryxenai
docker compose -f compose.production.yaml down        # no -v yet
docker images | grep -i oryxenai                      # review
docker image rm <oryxenai image ids>                  # only these
docker volume ls                                      # review before any prune
```

Then delete, after confirming the paths are not shared: `/srv/oryxenai`,
`/srv/oryxenai-backups` (only after your off-VM copy is verified),
`/home/oryxenaiadmin/oryxenai`, `/home/oryxenaiadmin/actions-runner`.
Do not run `docker system prune -a --volumes` on a VM that will host other
projects' containers.

### 5. Azure networking and billing

- **NSG:** remove the inbound rules for ports 80 and 443 added for OryxenAI and
  the single-IP SSH rule if the next project does not need them. Port 22 should
  stay restricted.
- **Public IP:** the DNS records no longer reference it. If the next project
  keeps the VM, keep the IP; if you delete the VM, also delete the IP, NIC and
  disk — a deallocated VM still bills for its disk and static IP.
- **Cost check:** Cost Management → resource group `oryxenai-demo-rg`, confirm
  the daily cost matches what you expect for the new use.

### 6. Repository cleanup

Doc 02 task C8 (delete `compose.production.yaml`, `Caddyfile`,
`scripts/azure-deploy.sh`; archive the Azure docs) — separate commit, after this
document is complete.

## Rollback (if the Render deployment fails acceptance)

Until step 4 is done: start the VM, `docker compose -f compose.production.yaml up -d`,
re-add the Namecheap A records (`app` and `preview` → the VM IP, recorded in
doc 03 Step 4), and re-enable the runner if you want CI deploys again. Supabase
URL settings can stay: `https://app.oryxenai.me` is the same origin either way.
