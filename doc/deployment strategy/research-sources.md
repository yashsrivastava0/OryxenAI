# Deployment research sources

Research recorded: 2026-09-15 20:26:26 +05:30 (Asia/Kolkata).

Five workstreams were searched with Exa during this preparation pass:
GitHub automation, open-source deployment platforms, AI-assisted operations,
Azure/container/authentication/storage, and infrastructure-as-code alternatives.
The review covered 76 search-result slots; the links below are the selected
first-party sources. Recheck provider pages before execution because prices,
student offers, product limits, and dashboards can change.

## Azure

- [Azure for Students](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students)
  describes the student credit and eligibility period. The guide must not
  hardcode a future balance or renewal assumption.
- [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)
  explains that exhausting included credit can disable services and stop or
  deallocate virtual machines. Keep the limit enabled unless the owner makes
  an explicit billing decision.
- [VM states and billing](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)
  distinguishes running, stopped, and deallocated states; disks and some
  networking resources can still incur charges after deallocation.
- [Connect to a Linux VM](https://learn.microsoft.com/en-us/azure/virtual-machines/linux-vm-connect)
  confirms the prerequisites used by this runbook: running VM, public IP,
  SSH key, and a narrowly scoped port-22 rule.

## Docker and HTTPS

- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
  recommends the official Docker apt repository and warns about firewall
  interactions when publishing container ports.
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
  documents `service_healthy` and `service_completed_successfully`, matching
  the database and migration dependencies in this repository.
- [`docker compose up --wait`](https://docs.docker.com/reference/cli/docker/compose/up/)
  documents waiting for services to be running or healthy.
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
  confirms that public DNS, ports 80/443, and persistent writable certificate
  storage are required for automatic certificates and renewals.

## Authentication and storage

- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
  covers Google Cloud consent setup, web origins, and the Supabase provider
  callback.
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
  explains Site URL and exact production redirect allowlists.
- [Cloudflare R2 S3 compatibility](https://developers.cloudflare.com/r2/get-started/s3/)
  confirms the endpoint shape, `auto` region, and S3 SDK integration used by
  the application.
- [R2 API tokens](https://developers.cloudflare.com/r2/api/tokens/)
  recommends bucket-scoped Object Read & Write credentials and notes that the
  secret key cannot be viewed again after creation.
- [R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
  explains prefix-based expiration and the need for a storage-write
  permission when managing lifecycle rules.
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
  is the current place to check storage, operation, retrieval, and egress
  policy rather than copying a stale price into project documentation.

## GitHub and the selected domain path

- [GitHub Student Developer Pack](https://education.github.com/pack) is the
  current offer catalogue. The `.me` domain offer and partner may change, so
  the owner should claim the available offer at the time of activation.
- [Student Developer Pack terms](https://docs.github.com/en/education/about-github-education/github-education-for-students/github-terms-and-conditions-for-the-student-developer-pack)
  notes that partner offers have separate terms and can change.
- [GitHub deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
  explains repository-scoped server access and why a read-only key is the
  appropriate default for a simple pull-based deployment.
- [GitHub deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
  documents environment protection rules, required reviewers, branch
  restrictions, and environment secrets. Its current plan note says required
  reviewers and wait timers on Free, Pro, and Team are limited to public
  repositories.
- [Controlling deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)
  documents push, pull-request, and manual workflow triggers, environment
  gates, and the use of concurrency for deployment control.
- [Workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
  explains how one concurrency group prevents overlapping releases.
- [Using GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
  explains repository/environment secret storage and access boundaries.
- [Available repository rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
  lists pull-request, status-check, linear-history, signed-commit, and
  force-push/deletion controls for a release branch.

## AI-assisted operations

- [Claude Code headless/programmatic mode](https://docs.anthropic.com/en/docs/claude-code/headless)
  documents non-interactive runs, `--bare`, exit codes, output formats, and
  restricting tools for scripts and CI.
- [Claude Code CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-reference)
  documents permission modes and tool allow/deny controls.
- [Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks-guide)
  documents pre-tool-call hooks that can enforce additional guardrails.
- [Claude Code GitHub Actions](https://docs.anthropic.com/en/docs/claude-code/github-actions)
  documents PR/issue automation and the credentials it requires; it is treated
  here as an optional review assistant, not as a production deploy authority.
- [GitHub Copilot cloud-agent risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/risks-and-mitigations)
  describes the human review and workflow-approval boundaries for agent output.

## Open-source deployment platforms and automation

- [Coolify overview](https://coolify.io/docs/core/what-is-coolify) describes a
  self-hosted PaaS/control plane that manages Docker resources, servers,
  domains, HTTPS, health checks, and deployments.
- [Coolify Docker Compose](https://coolify.io/docs/applications/builds/docker-compose)
  confirms Git-based Compose support, service/domain configuration, and
  branch/webhook automation.
- [Coolify Git-provider CI/CD](https://coolify.io/docs/applications/ci-cd)
  describes automatic redeployments and private-repository access methods.
- [Dokku installation and model](https://dokku.com/docs/getting-started/installation/)
  describes a single-server open-source PaaS centered on `git push`,
  Dockerfile/buildpack builds, web processes, and routing.
- [Kamal deploy](https://kamal-deploy.org/docs/commands/deploy/) describes its
  registry push/pull, SSH, proxy cutover, and release-version flow.
- [Watchtower introduction](https://containrrr.dev/watchtower/introduction/)
  describes registry polling and automatic container restarts when an image
  changes.
- [Ansible playbooks](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html)
  describes repeatable configuration management and multi-machine
  orchestration.
- [Ansible Docker Compose v2 module](https://docs.ansible.com/projects/ansible/latest/collections/community/docker/docker_compose_v2_module.html)
  confirms that Ansible can orchestrate an existing Compose project through the
  Docker Compose CLI plugin.
- [Terraform introduction](https://developer.hashicorp.com/terraform/intro)
  describes declarative infrastructure, plans, applies, providers, and state.

## Repository conclusions

The implementation-specific conclusions come from the checked-in
`compose.production.yaml`, `Caddyfile`, `config/app.production.toml`,
`config/models.toml`, `.env.example`, `scripts/azure-deploy.sh`, health routes,
storage adapters, authentication settings, and the existing
`docs/deployment` runbook. The production path is implemented but not proven
until the live VM, domain, provider integrations, and browser acceptance all
pass.

The research conclusion is to keep the existing Compose/script path, use a
protected deployment release pointer, and defer automatic GitHub-to-VM
deployment until the first manual release and the GitHub plan/network
constraints are understood.

For the reasoning and operator policy, see
[ai-and-open-source-research.md](ai-and-open-source-research.md) and
[github-and-ci.md](github-and-ci.md).
