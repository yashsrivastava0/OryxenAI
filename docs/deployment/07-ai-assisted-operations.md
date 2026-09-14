# AI-assisted OryxenAI operations

The deployment is deliberately arranged so an AI coding assistant can do most
of the diagnosis and code work while you perform only the account, credential,
and final release actions.

The safe boundary is simple:

```text
AI assistant: inspect code, edit code, run checks, explain failures
You:         provide credentials privately, approve/push the release,
             run the one deploy command, and perform browser acceptance
```

Never give an AI assistant the contents of `.env`, a private SSH key, a
Supabase secret key, an R2 secret key, or a provider API key. It can work from
`.env.example`, configuration names, redacted logs, and commit IDs.

## The repeatable release loop

Use this same loop for a bug fix, a UI change, or a future engine:

1. Ask Codex or Claude to inspect the repository and implement the change.
2. Ask it to run the smallest relevant checks, then the full project checks if
   the change is broad.
3. Review the diff and commit the change on the development branch.
4. Push the branch to GitHub.
5. SSH to the VM and run:

   ```bash
   cd ~/oryxenai
   ./scripts/azure-deploy.sh deploy <commit-sha>
   ./scripts/azure-deploy.sh status
   ./scripts/azure-deploy.sh verify
   ```

6. If the release fails, collect only redacted output with
   `./scripts/azure-deploy.sh logs app worker preview-gateway`, give that
   output to the assistant, fix the cause, and deploy the next commit.

The exact commit argument makes it clear which AI-produced change is running.
The script records the last two successful release SHAs, so
`./scripts/azure-deploy.sh rollback` is the short recovery path.

## What to ask Codex to do

Codex is useful for work inside the repository: implementation, tests,
configuration changes, code review, and release diagnosis. Start a task from
the repository root and tell it to read `AGENTS.md`, `DECISIONS.md`, and the
relevant source files before editing.

Useful prompts:

```text
Read AGENTS.md and DECISIONS.md first. Inspect the current branch and implement
<change>. Preserve unrelated worktree changes. Run the smallest relevant tests,
review the diff, and report the exact files and commit SHA. Do not read or
print .env or any secret files.
```

```text
This is an Azure VM deployment failure. Read the redacted logs below and the
deployment script/Compose files. Diagnose the smallest root cause, propose a
fix, implement it if it is in the repository, and run the relevant checks.
Do not ask for or inspect credentials.

<paste redacted output here>
```

Codex can also review a proposed release before you push it:

```text
Review this deployment diff against AGENTS.md. Check Compose service startup,
healthchecks, migrations, the worker, Caddy routing, rollback behavior, and
future engine additions. Flag only concrete release blockers and suggest the
smallest fixes.
```

## What to ask Claude Code to do

Claude Code is useful for the same repository tasks, especially a second-pass
review of a large diff or a focused diagnosis from logs. From the repository
root, ask it to preserve the same project rules:

```text
Read AGENTS.md and DECISIONS.md before making changes. Review the current
deployment diff for a one-VM Docker Compose release. Do not read .env or print
secrets. Check the exact files named below, run relevant tests, and report
concrete problems only.
```

For a non-interactive review, Claude Code can receive a prompt through its
print/non-interactive mode. Keep the prompt and log input free of secrets. Use
its normal permission controls for edits; do not grant it access to the VM's
private key or production `.env`.

Official references:

- [Codex documentation](https://learn.chatgpt.com/docs)
- [Codex use cases](https://learn.chatgpt.com/use-cases)
- [Claude Code CLI usage](https://code.claude.com/docs/en/cli-usage)
- [Claude Code getting started](https://code.claude.com/docs/en/getting-started)

## Human-only actions

Keep these actions with you:

- Azure portal changes and billing/spending-limit decisions;
- GitHub access setup on the VM;
- entering values into the VM-local `.env` during `setup` or `configure`;
- approving and pushing a commit to the deployment branch;
- running `deploy` against the intended commit; and
- the final Google sign-in and generated-preview acceptance.

Everything else should be expressible as repository code, Compose
configuration, a test, or a redacted command output that an AI assistant can
inspect and improve.
