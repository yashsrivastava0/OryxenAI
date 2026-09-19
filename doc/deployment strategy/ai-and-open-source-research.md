# AI-assisted and open-source deployment research

Research recorded: 2026-09-15 20:26:26 +05:30 (Asia/Kolkata)

Method: five research workstreams were searched with Exa: GitHub automation,
open-source deployment platforms, AI-assisted operations, Azure/container/
authentication/storage, and infrastructure-as-code alternatives. The search
review covered 76 result slots. High-signal first-party documentation was
filtered and linked below. Product limits, pricing, and plan features must be
checked again at execution time.

This research is preparation, not evidence that Azure, R2, Supabase, or the
model providers are currently reachable.

## Short answer

AI assistance is useful for this project as a bounded operator and review
layer. An additional open-source deployment platform is not useful enough to
justify its control-plane and maintenance cost.

The recommended stack remains:

```text
GitHub + existing CI
  -> protected deployment branch
  -> exact-SHA manual release
  -> scripts/azure-deploy.sh over restricted SSH
  -> Docker Compose on the existing Azure VM
  -> Caddy, Supabase Auth, and Cloudflare R2
```

This is simpler than adding a PaaS dashboard, registry, auto-updater, second
orchestrator, or infrastructure-as-code state system.

## Terminology: what “Claude CLI / array” means here

There are three different things that should not be mixed together:

1. **Claude Code CLI** is a developer workstation tool. It can inspect a
   repository, review a diff, run a bounded command, and explain a failure.
   It is not required by the OryxenAI application.
2. **AnthropicAdapter** is an application provider adapter. The source uses
   `httpx` against the configured provider API through the provider-neutral
   `ModelClient` boundary. The production container does not invoke the Claude
   CLI.
3. **The model routing configuration** is the profile/fallback/capacity
   structure in `config/models.toml`. It is probably what “array” refers to:
   the application selects profiles and fallback profiles from configuration.
   It is not a separate service that must be installed on Azure.

At the time of this audit, the local machine had `claude`, `codex`, and
`opencode` commands available. Tool versions and model names are intentionally
not treated as deployment constants. The production readiness check is a
provider preflight through the application runtime, not a CLI version check.

## What AI should do

AI is a good fit for:

- reading the repository and comparing Compose, TOML, migrations, auth, and
  storage contracts;
- checking a pull request for missing health checks, unsafe ports, accidental
  secret exposure, and migration risk;
- preparing the exact owner checklist and copy/paste command sequence;
- interpreting redacted `doctor`, Compose, Caddy, worker, and browser logs;
- generating a release note that names the exact SHA and checks performed;
- preparing a rollback explanation and a post-deploy acceptance checklist.

AI should not be allowed to:

- read or print `.env`, production secret stores, cookies, OAuth client
  secrets, bearer tokens, SSH private keys, R2 secret keys, or provider keys;
- make Azure billing, domain, Google OAuth, Supabase, or R2 dashboard changes
  without the owner;
- create or push the `deployment` branch while the release tree is dirty;
- run `deploy`, `rollback`, destructive database commands, or volume deletion
  autonomously;
- claim that a model key, auth provider, R2 bucket, or VM works merely because
  a variable is present or a container is running.

## Safe AI operating loop

Use this sequence:

1. Human selects the scope and keeps secrets private.
2. AI inspects source and proposes a minimal change or command sequence.
3. CI runs tests, type checks, Compose validation, smoke checks, and secret
   scanning.
4. Human reviews the complete diff and migration impact.
5. Human chooses the exact release SHA and approves the branch push.
6. Human or a trusted operator runs the exact-SHA deploy command over SSH.
7. AI receives only redacted output and helps diagnose failures.
8. Human performs Google login, R2/preview, and two-user acceptance.

A useful incident handoff is:

```text
Release SHA: <sha>
Command: <command without secrets>
Service: <app|worker|preview-gateway|caddy|postgres>
Expected: <expected result>
Observed: <redacted error and timestamp>
Recent change: <short description>
```

## Claude Code research findings

Anthropic's current Claude Code documentation supports a non-interactive
`claude -p` mode for scripts and CI. It documents `--bare` as a way to skip
automatic discovery of hooks, skills, plugins, MCP servers, memory, and
project context, which makes a scripted review more deterministic. It also
documents restricting automatically approved tools.

For this repository, a safe use is a read-only review in a disposable checkout
with an explicit prompt and narrowly allowed read/search tools. Do not give
the review an SSH agent, Azure credentials, production `.env`, or Docker
socket. If a review needs Bash, use a separate human-approved step and inspect
the command before it runs.

Claude Code hooks can block or inspect tool calls, but hooks are themselves
code that must be reviewed. A repository's non-bare configuration can load
hooks, MCP servers, skills, or commands; that is another reason to prefer
`--bare` for scripted audits and to review the exact working directory.

Claude Code also has a GitHub Actions integration that can respond to
mentions, review pull requests, or prepare changes. That is appropriate as an
optional PR assistant, not as the production deploy authority. Any generated
commit remains subject to CI, branch protection, human review, and the exact
SHA release gate.

## Open-source deployment options evaluated

| Option | What it adds | Fit for OryxenAI | Decision |
| --- | --- | --- | --- |
| Existing Docker Compose plus `azure-deploy.sh` | A versioned multi-service topology, migration ordering, health checks, backups, logs, and exact-SHA releases | Matches the current application and the single VM; no new control plane | Use |
| Coolify | A self-hosted PaaS/control plane, dashboard/API, Git integration, proxy, domains, HTTPS, health checks, and automatic deploys | Can ingest a Git Compose project, but adds another service, another secrets surface, and proxy/volume conventions to learn. The current script already handles the small deployment. | Do not add now |
| Dokku | A single-server PaaS built around `git push`, buildpacks/Dockerfile, web processes, and routing | The application is a coordinated Compose project with a migration job, worker, preview gateway, Caddy, persistent volumes, and offline npm cache. Adapting that topology to Dokku would be more work than using Compose. | Do not add |
| Kamal | SSH orchestration, registry image push/pull, proxy cutover, and release versioning | It assumes a registry-centered image flow and introduces another deployment configuration/proxy. The current VM builds the pinned image locally and must run migrations first. | Do not add |
| Watchtower | Registry image polling and automatic container restarts when an image changes | It cannot safely express this application's migration and release-review boundary. Automatic restarts could apply an image without a reviewed SHA or migration plan. | Do not add |
| Ansible + Docker Compose module | Repeatable remote configuration and Compose orchestration | Valid if there are many hosts or repeated fleet operations. For one already-created VM, it duplicates the guided Bash script and adds an inventory, collection, and controller setup. | Revisit only if the topology grows |
| Terraform | Declarative cloud resources, plans, applies, and state | Valuable when infrastructure is being created and managed as code. Here the VM already exists and the immediate problem is application release, not resource provisioning. Adding state and Azure credentials would increase the beginner burden. | Do not add for first release |

### Coolify in more detail

Coolify is the strongest open-source alternative considered because it can
connect to a server over SSH, manage Docker Compose applications, configure
domains/HTTPS/health checks, and react to repository changes. It is a real
option if the owner later wants a dashboard and automatic redeployments.

It still means operating Coolify itself, understanding its proxy and resource
model, deciding how it stores secrets, and reconciling its deployment behavior
with the application's one-shot migration service, persistent volumes,
loopback-only ports, R2 storage, and exact-SHA rollback policy. For a maximum
of two or three users, that is an unnecessary layer.

### Why the existing script is an open-source solution

The selected path is not proprietary deployment magic. It uses Git, Bash,
Docker Engine, Docker Compose, PostgreSQL, and Caddy, all with inspectable
configuration. The repository already expresses the required dependency order
and health boundaries. A small script is easier for an AI assistant to read
and for a beginner to recover than a second platform hiding Compose behavior
behind a dashboard.

## AI-assisted deployment recommendation

Use AI-assisted deployment in two bounded modes:

### Mode A: preparation and review

- Codex/Claude Code/OpenCode may read the source, write documentation, and
  prepare a release checklist.
- CI remains the automatic quality gate.
- A human decides whether a branch is ready and whether a migration is safe.

### Mode B: guided operation

- The human opens the SSH session and keeps secrets in the terminal.
- The assistant provides one command at a time and waits for the redacted
  result.
- The deterministic deployment script performs setup, migration, Compose
  startup, health checks, and release-state recording.
- The assistant diagnoses failures but does not invent success.

Do not use a general-purpose AI agent as an unattended production operator.
The useful automation is already in the script; AI supplies context and
explanation around it.

## Future GitHub AI/CI shape

The simple future shape is:

```text
pull request
  -> CI quality workflow
  -> human review
  -> protected deployment branch
  -> optional manual workflow dispatch
  -> exact SHA deploy
```

If a future one-click workflow is added, protect it with a production
environment approval and a single concurrency group where the GitHub plan
supports those features. Keep the workflow limited to the deployment branch
and an exact SHA. Do not put the production `.env` or long-lived broad cloud
credentials in a workflow merely to save one SSH step.

## Research conclusions

1. The current Compose/script path is the smallest reliable fit.
2. Coolify is viable but adds a control plane that this demo does not need.
3. Dokku, Kamal, and Watchtower solve different deployment shapes and would
   complicate migrations, persistent volumes, or release pinning here.
4. Ansible and Terraform are valuable when the number of hosts or cloud
   resources grows; they are not prerequisites for this single existing VM.
5. Claude Code, Codex, and OpenCode should remain development/operator tools.
   The production image must continue to rely on the configured provider
   adapters and `ModelClient`, not a personal CLI session.
6. Human approval remains necessary for secrets, billing, domain/auth
   settings, release pushes, deploys, and live browser acceptance.

## First-party sources reviewed

### AI assistance

- [Claude Code headless/programmatic mode](https://docs.anthropic.com/en/docs/claude-code/headless)
- [Claude Code CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-reference)
- [Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks-guide)
- [Claude Code GitHub Actions](https://docs.anthropic.com/en/docs/claude-code/github-actions)
- [GitHub Copilot cloud-agent risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)

### Open-source deployment

- [Coolify overview](https://coolify.io/docs/core/what-is-coolify)
- [Coolify Docker Compose applications](https://coolify.io/docs/applications/builds/docker-compose)
- [Coolify Git-provider CI/CD](https://coolify.io/docs/applications/ci-cd)
- [Dokku installation and model](https://dokku.com/docs/getting-started/installation/)
- [Kamal deploy flow](https://kamal-deploy.org/docs/commands/deploy/)
- [Watchtower image-update model](https://containrrr.dev/watchtower/introduction/)
- [Ansible playbooks](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html)
- [Ansible Docker Compose v2 module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_compose_v2_module.html)
- [Terraform infrastructure as code](https://developer.hashicorp.com/terraform/intro)
