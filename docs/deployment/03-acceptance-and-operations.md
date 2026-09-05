# Deployment acceptance and operations

The deployment is successful only when a real user can sign in, move through
the explicit agent stages, and open the generated portfolio preview. A green
container list alone is not acceptance.

## A. Infrastructure smoke test

- [ ] DNS resolves `app.<DOMAIN>` and `preview.<DOMAIN>` to the VM.
- [ ] HTTPS certificates are valid.
- [ ] `https://app.<DOMAIN>/health/live` returns successfully.
- [ ] `https://app.<DOMAIN>/health/ready` reports the database ready.
- [ ] `https://preview.<DOMAIN>/health/live` returns successfully.
- [ ] PostgreSQL, app, worker, and preview gateway are all running in Compose.
- [ ] The migration service completed successfully.
- [ ] The worker logs show a heartbeat after startup.

## B. Authentication smoke test

Use a clean browser session:

- [ ] Open `https://app.<DOMAIN>`.
- [ ] Sign in with Google.
- [ ] The callback returns to `https://app.<DOMAIN>/auth/callback`.
- [ ] The first account reaches onboarding when required.
- [ ] The account reaches `/app` after onboarding.
- [ ] A configured second user can sign in independently.
- [ ] The two bootstrap administrators can reach `/admin` if admin checks are
  being tested.

If the callback fails, check the exact Supabase Site URL, Redirect URL,
`primary_origin`, and `allowed_origins`. All four must describe the same HTTPS
application origin.

## C. Full generation acceptance

Perform this with a small, privacy-safe portfolio input first:

1. Start Discovery and wait for the worker to process it.
2. Answer the questions and approve the brief.
3. Explicitly start Content Architect and wait for its result.
4. Approve the content result.
5. Explicitly start Visual Design Director and wait for its result.
6. Approve the visual direction.
7. Explicitly start Build Preparation and confirm both Markdown briefs exist.
8. Explicitly start Code Generator.
9. Confirm the worker claims the Code Generator jobs and continues renewing
   heartbeats.
10. Wait for source generation, dependency acquisition, build checks, browser
    verification, and preview promotion to finish.
11. Open the generated preview inside the application.
12. Open the direct preview URL in a new browser tab.
13. Refresh the preview and confirm it still serves the generated portfolio.

The product intentionally does not auto-chain these stages. A caller must
start each later stage explicitly.

## D. Preview acceptance

- [ ] The preview URL uses `https://preview.<DOMAIN>/preview`.
- [ ] The preview HTML loads without an application login cookie.
- [ ] CSS, JavaScript, images, and fonts load from the preview object.
- [ ] The preview works in the application's iframe.
- [ ] The direct preview URL works in a new tab.
- [ ] A failed replacement generation does not remove the last promoted
  preview.
- [ ] The preview gateway remains healthy after the worker restarts.

The preview is public/unlisted by design. Anyone who receives its opaque URL
can open it. This deployment does not add a separate publishing product.

## E. Two-user check

- [ ] User A can create and view their own portfolio.
- [ ] User B can create and view their own portfolio.
- [ ] Refreshing either browser preserves the active session.
- [ ] The application does not require a second worker or a second VM.
- [ ] A single worker processes jobs serially without losing state.

The current application has server-side ownership and entitlement rules even
though this deployment is not being treated as a security-sensitive public
service. Do not bypass those rules in the browser while testing.

## F. Failure diagnosis

| Symptom | First check |
| --- | --- |
| App does not load | Caddy status, DNS, ports `80`/`443`, `app` logs |
| Auth callback fails | Supabase callback URL and exact production origin |
| App is ready but jobs do not move | `worker` logs, worker heartbeat, `/health/ready`, database connectivity |
| Build Preparation fails | R2 credentials, resource-provider keys, worker logs |
| Code Generator stops before preview | Active model profile credential, provider quota, worker memory, Code Generator logs |
| Preview promotion fails | R2 bucket/prefix, preview public URL, preview gateway logs |
| Preview opens but is blank | Preview gateway logs, generated `dist` contents, browser console, R2 object listing |
| VM becomes slow or kills the worker | VM memory, Docker stats, worker concurrency, active generation count |

Useful commands:

```bash
docker stats
docker compose -f compose.yaml -f compose.production.yaml logs --tail 250 worker
docker compose -f compose.yaml -f compose.production.yaml logs --tail 250 app
docker compose -f compose.yaml -f compose.production.yaml logs --tail 250 preview-gateway
```

## G. Restart and recovery checks

Perform these after the first successful generation:

- [ ] Restart the worker and confirm the application remains available.
- [ ] Restart the preview gateway and reopen the existing preview URL.
- [ ] Restart the app and confirm the database-backed session remains.
- [ ] Reboot the VM and confirm Docker services return through
  `restart: unless-stopped`.
- [ ] Confirm the PostgreSQL named volume remains present.
- [ ] Confirm preview objects remain available in R2.

Never use `docker compose down -v` for ordinary maintenance.

## H. Minimal backup routine

The demo can use a simple manual backup rather than a full backup platform.
Run a PostgreSQL dump before repository or migration changes:

```bash
mkdir -p ~/oryxenai-backups
docker compose -f compose.yaml -f compose.production.yaml \
  exec -T postgres pg_dump -U oryxen -d oryxenai \
  | gzip > ~/oryxenai-backups/oryxenai-$(date +%Y%m%d-%H%M%S).sql.gz
```

Keep the dump outside the repository and periodically copy one known-good dump
off the VM. R2 remains the source for generated preview objects; do not delete
the active preview prefix while diagnosing an application issue.

## I. Cost and lifecycle checks

Once per week while using the demo:

- [ ] Check remaining Azure student credit and VM status.
- [ ] Check that the Azure spending limit remains enabled.
- [ ] Check R2 usage and budget alerts.
- [ ] Remove temporary artifacts according to the configured lifecycle.
- [ ] Open the app periodically so the Supabase Free project does not become
  inactive.
- [ ] Record the domain renewal date.

Model-provider usage must be checked separately from Azure, Supabase, and R2.
