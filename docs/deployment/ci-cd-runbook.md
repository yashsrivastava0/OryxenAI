# CI/CD runbook: automatic deploy via a self-hosted GitHub Actions runner

Read this before touching deployment automation, on any device, with any AI
tool. It exists so a fresh session — Claude Code, Codex CLI, or a human —
can operate and troubleshoot the pipeline without re-deriving any of this
from scratch. See D-107 and D-110 in `DECISIONS.md` for the decision record;
this file is the operational how-to and issue log that sits underneath it.

## `gh` CLI is now available (set up 2026-09-22)

Installed via `winget install --id GitHub.cli` on the primary dev machine
and authenticated as `yashsrivastava0` (`gh auth login --web`, scopes:
`gist`, `read:org`, `repo`, `workflow`). It lives at
`C:\Program Files\GitHub CLI\gh.exe` — winget's PATH update did not
propagate to already-open or freshly-spawned tool shells in this
environment, so call it by full path (or check whether a truly new
interactive terminal now resolves `gh` directly before assuming it doesn't).

This unlocks direct log/PR access that previously required relaying through
the operator:

```bash
gh run list --repo yashsrivastava0/OryxenAI --branch <branch>
gh run view <run-id> --repo yashsrivastava0/OryxenAI --log-failed
gh pr view <number-or-branch> --repo yashsrivastava0/OryxenAI --json mergeable,statusCheckRollup
gh pr merge <number> --repo yashsrivastava0/OryxenAI --merge   # never --squash/--rebase (see below)
```

Plain GitHub REST API calls (e.g. via WebFetch) work unauthenticated for
run/job **status** on this public repo, but the log-content endpoints
return 403 without a token — `gh` is the only zero-friction way to read
actual failure text.

## What exists today

- A GitHub Actions self-hosted runner runs as a systemd service directly on
  the Azure VM (not on GitHub's cloud infrastructure).
  - Service name: `actions.runner.yashsrivastava0-OryxenAI.oryxenai-azure-vm.service`
  - Runs as: `oryxenaiadmin` (the same user that owns the deploy checkout)
  - Install directory: `/home/oryxenaiadmin/actions-runner`
  - Label: `azure-oryxenai`
  - Enabled at boot (`systemctl enable`d by the runner's own `svc.sh install`)
- `.github/workflows/ci.yml` has a `deploy` job:
  - `needs: quality` — only runs after lint/type/test/build/audit/Docker
    checks pass.
  - Triggers only on `push` or manual `workflow_dispatch` to the
    `deployment` branch (`if: github.ref == 'refs/heads/deployment' && ...`).
  - `runs-on: [self-hosted, azure-oryxenai]` — targets the runner above.
  - No `environment:` gate — **fully automatic**, no approval click, per an
    explicit operator instruction ("temporarily"). See "Re-adding an
    approval gate" below to change that.
  - **Currently force-disabled**: the `if:` condition has a leading
    `false &&` (added 2026-09-22) so a bulk catch-up push to GitHub couldn't
    accidentally trigger the very first live deploy before the operator was
    ready. Delete that `false &&` clause (in its own PR, per the branch
    protection below) to re-enable before the real first deployment trial.
  - No `actions/checkout` step: it runs `./scripts/azure-deploy.sh deploy
    ${{ github.sha }}` then `./scripts/azure-deploy.sh verify` with
    `working-directory: /home/oryxenaiadmin/oryxenai` — the script does its
    own `git fetch origin` + `git checkout --detach <sha>` in place, exactly
    like a human running it by hand.
  - On failure, dumps `status` and `logs` into the Action's own output so a
    human doesn't have to SSH in just to see what broke. No auto-rollback —
    a human (or an agent acting on explicit instruction) decides the next
    step and runs `./scripts/azure-deploy.sh rollback` if needed.

**Why a self-hosted runner instead of GitHub SSHing into the VM:** this VM's
NSG allows inbound SSH from exactly one hand-picked IP at a time (see
`docs/azure-issue.md` for the full multi-session saga — Jio hotspot,
Cloudflare WARP, and office Wi-Fi each produced a different IP and each
needed a manual NSG edit). GitHub-hosted runners connect from large, rotating
Microsoft/GitHub IP ranges, so an SSH-from-GitHub design would need the NSG
opened broadly to work reliably. A self-hosted runner polls GitHub over
**outbound** HTTPS instead — no inbound port, no SSH key stored in GitHub,
no NSG change, ever. The `Allow-SSH-MyIP` rule is completely unaffected by
this pipeline and remains only for interactive human debugging.

## Branch protection: `deployment` requires a PR — direct pushes never work

A GitHub repository ruleset (`deployment-ci-gate`, set up during the earlier
security audit) blocks **any** direct push to `refs/heads/deployment` —
including from the repo owner, from the command line, with a valid
credential, no exceptions. It also requires the `quality` job ("Lint,
type-check, test, audit") to pass as a required status check. Discovered the
hard way on 2026-09-22: a plain `git push origin deployment` was rejected
with `GH013: Repository rule violations ... Changes must be made through a
pull request.`

This means "push to deployment" never actually means a raw push in
practice. The real mechanic is:

```text
commit -> push to a side/feature branch (never `deployment` directly)
  -> open a PR into `deployment`
  -> GitHub runs `quality` on the PR automatically
  -> once green, merge the PR (regular merge commit, not squash/rebase --
     squash/rebase rewrites commit SHAs, breaking any doc that references
     an exact short-SHA, e.g. CHANGES.md/DECISIONS.md entries)
  -> the merge itself is a push event on `deployment`
  -> if the deploy job's trigger is enabled, it fires immediately on the
     VM's own runner: azure-deploy.sh deploy <sha> then verify
  -> pass/fail visible in the repo's Actions tab; failure includes
     status+logs inline
```

Nothing about the deploy step depends on which laptop/device does the
pushing/merging — the runner lives on the VM, not on any operator's
machine. But *reaching* `deployment` at all always requires this branch ->
PR -> merge path, from anyone, on any device.

### A freshly-opened PR may show a false "conflicts" banner

GitHub sometimes reports "This branch has conflicts that must be resolved"
right after a branch is pushed, even when there is no real conflict — its
mergeability check can be stale for a minute or two. Before trusting that
banner (and before doing any manual conflict-resolution work), verify
locally:

```bash
git fetch origin
git merge-tree "$(git merge-base HEAD origin/deployment)" HEAD origin/deployment
```

Empty output means a clean merge — the banner was stale; just wait and
refresh the PR page. Only investigate further if this actually prints
conflict markers.

## The real SSH key (do not confuse with other keys on this machine)

The VM's actual authorized private key is **`oryxenai-demo-key.pem`**,
normally found in the operator's `Downloads/Personal & Financial/` folder on
Windows. A different key once present at `~/.ssh/termius_windows` (labeled
"Termius iPhone" — apparently generated by the Termius mobile app for an
unrelated purpose) was **not** a valid credential for this VM and was
deleted from the operator's machine on 2026-09-22 after confirming it always
failed with `Permission denied (publickey)`. If a future session finds a
`~/.ssh/*` key that isn't `oryxenai-demo-key.pem`, do not assume it works —
verify with a harmless read-only command first (`uname -m && whoami`) before
relying on it for anything.

### Known issue: Windows OpenSSH rejects `.pem` files with loose ACLs

Symptom:

```text
Bad permissions. Try removing permissions for user: <domain>\<user> on file <path>.
Load key "<path>": bad permissions
Permission denied (publickey)
```

This is not a wrong key — Windows OpenSSH refuses to use a private key file
whose NTFS ACLs allow more than the current user to read it (the same
principle as `chmod 600` on Linux/macOS). A `.pem` downloaded via a browser
usually inherits broad permissions. Fix in PowerShell:

```powershell
icacls "<full path to the .pem file>" /inheritance:r
icacls "<full path to the .pem file>" /grant:r "$($env:USERNAME):(R)"
```

Then retry the `ssh -i "<path>" oryxenaiadmin@<vm-ip> ...` command.

## Setting up the runner from scratch (new VM, or this one needs re-registering)

1. In the GitHub repo → **Settings → Actions → Runners → New self-hosted
   runner**. **The page defaults to the Windows tab even when the intended
   target is a Linux VM — explicitly switch the OS selector to Linux, x64**
   before copying anything, or you'll get `config.cmd`/`.zip`/PowerShell
   commands that don't run on this VM at all.
2. The page shows a Download block and a Configure block. The Configure
   block contains a registration token
   (`./config.sh --url ... --token ...`) that is **short-lived (about one
   hour) and single-use** — get it, use it promptly, don't paste it anywhere
   persistent (not `.env`, not a committed file — it has no lasting value
   once the runner is registered).
3. On the VM (needs passwordless `sudo` for the service-install step —
   already confirmed available for `oryxenaiadmin`; check with `sudo -n
   true` if unsure):
   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   curl -o actions-runner-linux-x64-<version>.tar.gz -L <download-url-from-the-page>
   echo "<sha256-from-the-page>  actions-runner-linux-x64-<version>.tar.gz" | shasum -a 256 -c
   tar xzf ./actions-runner-linux-x64-<version>.tar.gz
   ./config.sh --url https://github.com/yashsrivastava0/OryxenAI --token <TOKEN> \
     --unattended --name oryxenai-azure-vm --labels azure-oryxenai --work _work
   sudo ./svc.sh install oryxenaiadmin
   sudo ./svc.sh start
   sudo ./svc.sh status
   ```
4. Confirm in GitHub → Settings → Actions → Runners that it shows **Idle**
   (green). That confirms registration and the systemd service are both
   healthy without needing a real deploy yet.

## Checking runner health

```bash
sudo systemctl status 'actions.runner.*'
```

or check the Actions → Runners page in the GitHub UI (shows Idle/Active/
Offline). If it shows Offline, SSH in and check `sudo systemctl status
actions.runner.yashsrivastava0-OryxenAI.oryxenai-azure-vm.service` — restart
with `sudo systemctl restart <service-name>` if it crashed; re-register from
scratch (above) only if the service itself is gone or corrupted.

## Re-adding an approval gate

The workflow file has a comment directly above the `deploy` job's
`concurrency:` block showing exactly what to add back:

```yaml
environment: production
```

Then create that environment once in GitHub → **Settings → Environments →
New environment** → name it exactly `production` → check **Required
reviewers** → add whoever should approve. Every future deploy will then
pause for one click in the GitHub UI before touching the VM. No workflow
logic changes beyond that one line.

## If the runner is offline and a deploy is needed anyway

The manual path still works exactly as documented in
`docs/deployment/deployment-guide.md` sections 6-7 — SSH in with
`oryxenai-demo-key.pem` and run `./scripts/azure-deploy.sh deploy <sha>` /
`verify` / `rollback` / `status` / `logs` by hand from
`/home/oryxenaiadmin/oryxenai`. The automated pipeline and the manual
commands are the same underlying script; automation just removes the need
to type it yourself.

## Cross-references

- `DECISIONS.md` D-107 (superseded) and D-110 (current design and why).
- `docs/azure-issue.md` — the full SSH/NSG connectivity investigation this
  design was built to route around.
- `docs/deployment/deployment-issues.md` — the timestamped log of every
  CI/Compose bug found and fixed (or still open) while getting the
  required `quality` check green. Check its "Currently open issues"
  section before assuming CI is broken for a new reason.
- `CHANGES.md` — `bf6c6ff` (production Docker network egress fix, D-109),
  `7cb4102` (this CD pipeline, D-110).
