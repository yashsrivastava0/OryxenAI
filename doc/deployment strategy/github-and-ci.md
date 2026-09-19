# GitHub, release branch, and CI/CD strategy

Audit recorded: 2026-09-15 20:26:26 +05:30 (Asia/Kolkata)

This is the repository and release-control plan for a very small installation.
It is intentionally conservative because the application contains database
migrations, a durable worker, model credentials, and persistent preview data.

## Recommendation

Keep the existing GitHub Actions quality workflow, create a protected
`deployment` branch only from one clean reviewed release SHA, and initially
deploy that SHA manually over the already restricted SSH path. Do not make a
push to `deployment` automatically restart production yet.

That gives the owner a simple, understandable release loop:

```text
development branch
  -> pull request and CI
  -> protected deployment branch
  -> exact SHA selected by the owner
  -> SSH to VM
  -> scripts/azure-deploy.sh deploy <SHA>
  -> status and acceptance checks
```

The domain is independent of GitHub. `deploy.me` can be connected after the
server is healthy; it does not need to be registered before the branch or
Compose release process is prepared.

## What exists in GitHub today

- The repository remote points to `yashsrivastava0/OryxenAI`.
- The current checked-out branch is a development/reliability branch, not a
  production release pointer.
- The worktree contains tracked and untracked work from other contributors.
  It must not be pushed as a deployment release until ownership is reconciled.
- A branch named `deployment` was not present at the time of this audit.
  Re-run `git branch -a` before creating it.
- `.github/workflows/ci.yml` already runs on pushes and pull requests. It
  performs Python quality checks, type checks, migrations/tests, Compose
  validation, a Docker smoke path, and secret scanning.
- There is no deployment workflow. No GitHub secret currently needs to contain
  an Azure private key, R2 key, Supabase secret, model key, or production
  `.env`.

These are audit observations, not permanent status claims. Check the current
remote and workflow files again at the release gate.

## Branch layout

Use these roles:

| Ref | Role | Rule |
| --- | --- | --- |
| Development branches | Feature, bug-fix, reliability, and documentation work | May move quickly; must pass CI before release consideration. |
| `deployment` | Human-readable production release pointer | Only clean, reviewed, tested commits; no unreviewed direct pushes. |
| Exact commit SHA | Actual deployed version | Record it in the release note and VM deployment state. |

Do not use `deployment` as a long-lived scratch branch. A future change is
made on a normal development branch, reviewed, and then merged into
`deployment`. The VM deploys the resulting SHA, not an unpinned branch tip.

The current repository has multiple historical branches with different
states. Do not assume that `main`, `working`, or the current branch is the
correct release source without reviewing the graph and the contributor-owned
changes.

## How the branch should be created later

Do not run this while the worktree is dirty. After the release gate has
selected a clean SHA:

```powershell
git status --short --branch
git switch -c deployment <CLEAN_SHA>
git log -1 --oneline
git push -u origin deployment
```

If the branch already exists, inspect it and compare its tip to the intended
release before pushing. Never use `git add .` for this step. Never include
`.env`, `.workspace`, caches, `node_modules`, build output, `.kiro`,
`.playwright-mcp`, or another contributor's unreviewed files.

The push is an external repository change. It should happen only after the
owner has approved the clean release and the complete staged diff has been
reviewed.

## GitHub protection to configure

In the repository Settings, create a branch ruleset targeting `deployment`
after the branch exists:

1. Require a pull request before merging.
2. Require the `quality` check from `.github/workflows/ci.yml` to pass.
   Select the exact check name shown in the Actions/branch-rule UI if it
   differs from the job identifier.
3. Block force pushes and branch deletion.
4. Prefer a linear history or squash merge so the release pointer is easy to
   audit.
5. Restrict direct updates to the owner or a deliberately chosen bypass actor.
6. Do not require a successful production deployment before merging while
   production deployment is still a manual operator action.

GitHub's ruleset documentation supports pull-request, status-check, linear
history, signed-commit, and update/deletion controls. Use the least set that
protects this branch without preventing the owner from recovering the demo.

### Important plan limitation

GitHub's current documentation says required reviewers and wait timers for
environments on Free, Pro, and Team plans are available only for public
repositories. If this repository is private on a personal account, check the
current GitHub plan before depending on a `production` environment approval
gate or environment-only secrets.

For the initial setup, branch protection plus a human-approved exact-SHA SSH
deployment is more predictable than assuming a plan feature is available.

## The simple release loop

For each future application change:

1. Make the change on a development branch.
2. Run the relevant local checks and open a pull request.
3. Let the existing CI workflow finish successfully.
4. Review the complete diff, migration impact, configuration impact, and
   generated frontend bundle impact.
5. Merge the reviewed change into `deployment`.
6. Record the resulting SHA.
7. SSH to the VM and run:

   ```bash
   cd ~/oryxenai
   ./scripts/azure-deploy.sh doctor
   ./scripts/azure-deploy.sh deploy <EXACT_SHA>
   ./scripts/azure-deploy.sh status
   ```

8. Run internal health checks, then the relevant browser/R2/preview smoke
   checks. Run public HTTPS verification only after `deploy.me` is active.

This is CI plus controlled release automation. It is enough for two or three
users and keeps migration failures, model-provider changes, and preview
promotion visible to the person responsible for the service.

## Private repository access from the VM

The VM needs to fetch the selected Git ref. For a private repository, use a
repository-scoped, read-only GitHub deploy key stored on the VM. This key is
different from the Azure SSH private key used to log in to the VM.

The setup sequence is documented in
[`docs/deployment/02-azure-vm-runbook.md`](../../docs/deployment/02-azure-vm-runbook.md):

- generate the VM-specific key on the VM;
- add only the public key to the GitHub repository as read-only;
- verify `ssh -T git@github.com`;
- pin/verify GitHub's host key;
- keep the private key outside the repository and never paste it into an AI
  conversation.

GitHub documents deploy keys as repository-scoped server credentials and
describes agent forwarding as a quick but less automation-friendly option.
The dedicated read-only key is the repeatable choice here.

## Why not automatic deploy-on-push now?

The repository's current Azure VM has an SSH rule restricted to one operator
IP address. GitHub-hosted runner source addresses are not that one stable
operator address, so making Actions SSH directly to the VM would require
changing the NSG or adding another access path.

An Actions job would also need a deployment credential in GitHub. A long-lived
VM SSH private key in repository secrets is a larger blast radius than the
current VM-local read-only GitHub key, and it would make a branch push capable
of changing production without an explicit human step.

The application deploy is not a single stateless container replacement:

- migrations must run before app/worker startup;
- the worker and preview gateway must remain aligned with the app image;
- the VM owns persistent PostgreSQL and generated-workspace volumes;
- rollback does not downgrade database migrations;
- R2 and model-provider failures need operator-visible diagnosis.

For those reasons, automatic push deployment is not the first-release
recommendation.

## Optional future one-click workflow

If manual SSH becomes inconvenient later, the smallest safe evolution is a
manual `workflow_dispatch` workflow that:

- can run only for the protected `deployment` branch;
- references a `production` environment;
- uses a required reviewer when the repository plan supports it;
- uses a single `production` concurrency group so two releases cannot run at
  once;
- passes the immutable workflow commit SHA to the VM deployment command;
- runs `doctor`, deploy, internal health, and a bounded post-deploy check;
- never reads or uploads the production `.env`.

The transport still needs a deliberate choice. A self-hosted runner on the VM
or an Azure-native command path with narrowly scoped identity is safer than
opening SSH to all GitHub-hosted runner IPs. Either choice adds operational
setup and should be introduced only after the first manual release works.

GitHub documents environments for protection rules and secrets, and
concurrency groups for ensuring that only one deployment runs at a time. Those
features are useful later; they are not a reason to add a deployment workflow
before the current VM, plan, and network constraints are verified.

## AI in the GitHub workflow

AI may review a pull request, explain a failed CI job, or prepare a release
checklist. It must not receive `.env`, provider keys, OAuth secrets, R2 secret
keys, cookies, bearer tokens, or the Azure private key. AI-generated changes
still require the same CI, human diff review, and branch protection.

Claude Code's GitHub integration and GitHub Copilot agents can be considered
for read-only review or issue-to-PR assistance later. They are optional
developer workflow tools, not a production deployment controller.

## Domain timing

The branch and CI/CD plan does not depend on `deploy.me`. After the VM-local
stack is healthy, activate the domain in a separate change:

1. obtain/control `deploy.me`;
2. point `app.deploy.me` and `preview.deploy.me` to the current static IP;
3. configure Supabase Site URL and the exact auth callback;
4. configure Google OAuth's production origin/callback;
5. allow Caddy to obtain certificates;
6. run public HTTPS and browser acceptance.

See [`runbook.md`](runbook.md) for the complete order.

## References

- [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Controlling deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
- [Workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [Using GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Available repository rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Managing deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
