# Operations and AI-assisted maintenance

Preparation audit recorded: 2026-09-15 20:26:26 +05:30 (Asia/Kolkata).

The normal operating model is: make a reviewed change, merge it to
`deployment`, deploy its exact SHA, verify, and keep the previous good SHA
available for rollback.

## Routine commands on the VM

Run these from the repository directory:

| Need | Command |
| --- | --- |
| Inspect containers and last releases | `./scripts/azure-deploy.sh status` |
| Recheck configuration | `./scripts/azure-deploy.sh doctor` |
| Deploy a release | `./scripts/azure-deploy.sh deploy <commit-sha>` |
| View all recent logs | `./scripts/azure-deploy.sh logs` |
| View one service | `./scripts/azure-deploy.sh logs app` |
| Check internal and public health | `./scripts/azure-deploy.sh verify` |
| Edit VM-local configuration | `./scripts/azure-deploy.sh configure` |
| Create a database dump | `./scripts/azure-deploy.sh backup` |
| Return to the previous recorded release | `./scripts/azure-deploy.sh rollback` |

Run `verify` only after the public DNS and domain phase is active. During the
domain-free phase, use the VM-local curl checks in the runbook.

## Updating the application

1. Make the change on a development branch.
2. Run backend, frontend, lint, type, and relevant integration checks.
3. Commit it locally and review the complete diff.
4. Merge or fast-forward the reviewed result into `deployment` and push it.
5. SSH to the VM, fetch the branch, and deploy the exact new SHA.
6. Run `status`, health checks, and the relevant browser smoke test.

Do not rely on an unpinned branch tip during a production incident. Record the
SHA used for every deployment.

## Backups and recovery

The built-in backup command writes a PostgreSQL dump under the VM user's
`~/oryxenai-backups` directory. After important releases and before schema
migrations, download a copy to secure owner-controlled storage. A backup left
only on the VM is lost if the VM or disk is lost.

Do not use `docker compose down -v`; it deletes persistent database and service
volumes. The deployment script's rollback restores application code and images,
not database migrations. Take a backup before deploying a migration change and
restore it in a disposable environment when a recovery test is needed.

## Cost and availability

- Keep the Azure spending limit enabled while learning the system.
- Check the Azure for Students balance and expiry regularly.
- When the site is not needed, use Azure's Stop/Deallocate action rather than
  only shutting down Ubuntu. Compute billing stops after deallocation, while
  disks and networking may still have charges.
- Keep R2 private and configure the required lifecycle rules for temporary
  objects. Do not apply cleanup rules to live preview objects without checking
  the configured prefixes.
- Model and image-provider charges are separate from Azure, Supabase, and R2.

## AI-assisted troubleshooting

AI may inspect code, deployment configuration, command output, and redacted
logs. The safe incident format is:

```text
Release SHA: <sha>
Command: <command without secrets>
Service: <app|worker|preview-gateway|caddy|postgres>
Expected: <expected result>
Observed: <redacted error and timestamp>
Recent change: <short description>
```

Before sharing output, remove API keys, bearer tokens, cookies, private URLs,
OAuth secrets, database passwords, SSH material, and complete environment
files. AI must not invent a successful deployment from local tests or a green
container status.

## Tooling boundary

Claude Code, Codex, and OpenCode are optional development/operator tools. The
production image does not install or invoke a CLI session. OryxenAI routes
model calls through the configured provider adapters and the ModelClient
boundary; the active profile and fallback list must be read from
config/models.toml at release time.

For the safe AI workflow, GitHub branch controls, and open-source platform
comparison, see [github-and-ci.md](github-and-ci.md) and
[ai-and-open-source-research.md](ai-and-open-source-research.md).

The owner remains responsible for Azure billing decisions, secret entry,
domain registration, Google/Supabase/R2 dashboard changes, and final
multi-account browser acceptance.
