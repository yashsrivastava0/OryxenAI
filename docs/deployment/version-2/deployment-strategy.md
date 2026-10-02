# Deployment strategy v2: Railway + Supabase

**Research snapshot:** 2026-10-03

**Recommendation:** Railway Hobby for the application, worker, and PostgreSQL;
retain the existing Supabase project for authentication.

**Status:** This is a deployment plan only. No cloud service, DNS record, or
production data was changed; no production branch was promoted or deployed.

## Decision

Moving off the Azure VM is a sound simplification for this application. The
current code already builds as a container and needs a web process, a
continuously running PostgreSQL queue worker, and PostgreSQL. Railway can host
all three in one project. The existing Supabase project continues to handle
Google sign-in. The Preact frontend stays bundled and served by FastAPI, and
the Studio preview stays on that same app origin.

Use a paid Railway Hobby workspace for production. Railway Free is useful for
a short experiment, not reliable always-on hosting: its monthly credit is
small, and a compute hard limit stops workloads. Hobby is $5/month and
includes $5 of resource usage; extra use is billed. A continuously running
worker and database use resources even when the app is idle, so this is not a
free stack.

**Blunt cost assessment:** Railway is the simpler hosting choice, but it is
not guaranteed to cost less than Azure. The repository's September 2026 Azure
snapshot showed an Azure for Students credit and a daily auto-shutdown
schedule. That snapshot is historical. If the student credit still covers the
VM, switching may increase cash spend while reducing maintenance. Compare one
representative Railway billing cycle with the live Azure bill before retiring
the VM.

### Production components

| Component | Host | Responsibility |
| --- | --- | --- |
| App / web | Railway service from root Dockerfile | FastAPI API, auth pages, and built Preact application |
| Worker | Railway service from the same Dockerfile | Long-running PostgreSQL queue consumer; command: **python -m oryxenai.jobs.worker** |
| PostgreSQL | Railway PostgreSQL service in the same project | Sessions, durable jobs, generated page bundles, and app state |
| Authentication | Existing Supabase project | Google sign-in and identity verification; user identities stay there |
| Model calls | Configured model provider | Discovery, Content Architect, and Studio operations; billed separately |

~~~mermaid
flowchart LR
    Browser -->|HTTPS: app.oryxenai.me| App["Railway app service<br/>FastAPI + bundled Preact"]
    App -->|private DATABASE_URL| DB[("Railway PostgreSQL")]
    Worker["Railway worker service"] -->|private DATABASE_URL| DB
    App <-->|Google sign-in / token verification| Supabase["Existing Supabase Auth"]
    Worker -->|configured model calls| Model["Configured model provider"]
    App -->|same-origin signed preview route| Browser
~~~

Do not add Vercel, Redis, Celery, an object store, Caddy, a separate preview
gateway, or a public portfolio-hosting service for this deployment.

## Why this fits the current code

- The root Dockerfile builds the frontend and Python application into one
  image. Its default command serves FastAPI on the platform-injected PORT.
- The separate worker runs the PostgreSQL-backed durable queue. It must stay
  running; a serverless function or sleeping worker can leave jobs queued.
- The app accepts a managed DATABASE_URL and converts PostgreSQL URLs to the
  SQLAlchemy asyncpg driver. The app and worker must use the same database.
- The Studio's sealed page bundle is stored in PostgreSQL. FastAPI serves its
  signed preview on the app origin; no object storage or second preview
  hostname is needed.
- The Docker build downloads Docling OCR assets into the image at
  /opt/docling-models. They must not be downloaded at runtime or depend on an
  ephemeral container filesystem.
- config/app.production.toml already selects required Supabase auth and local
  filesystem compatibility settings. Browser verification is currently off.
  The preview can still load, but the worker will not run optional
  server-side Chromium checks until the configuration change in this guide.
- The workflow ends with the owner's verified, sandboxed Studio preview.
  Public publishing or hosting of generated portfolios is not implemented.

Request flow:

1. The browser loads the Preact shell and calls FastAPI on app.oryxenai.me.
2. FastAPI validates Supabase identity and owner access, persists application
   state in PostgreSQL, and enqueues an explicitly user-started job.
3. The worker claims that job, calls the configured model provider, and
   commits its result.
4. The browser reads the updated stage. The owner reviews and explicitly
   approves each stage; the API does not silently chain stages.
5. Studio loads a signed preview from the same FastAPI service. Preview
   content remains sandboxed and is not published as a public portfolio.

## Platform comparison

| Option | Fit | Cost / trade-off | Decision |
| --- | --- | --- | --- |
| Railway Hobby | One project supports the Docker web service, always-on worker, and PostgreSQL. Existing same-origin UI and preview remain unchanged. Singapore is available and is the closest listed region for an India-based deployment. | $5/month subscription with $5 included usage; additional RAM, CPU, volume, and egress are metered. Railway-hosted PostgreSQL templates still leave backup, recovery, upgrades, and maintenance to the operator. | **Selected** for a simple one-project container migration, with explicit backup and cost checks. |
| Render | Supports Docker web services, workers, and PostgreSQL and can run the app correctly. | Free web services sleep after inactivity, free PostgreSQL expires after 30 days, and a free always-on worker is not available. A comparison floor using a 2 CPU / 4 GB web service, smallest paid worker, and smallest paid PostgreSQL is about $98/month before storage or bandwidth; OCR may require more. | Viable paid alternative; not selected for cost/complexity. |
| Vercel | Could host a separately adapted frontend or request handlers. | The product is a FastAPI app plus a persistent worker. Splitting adds routing, auth-origin, and preview-origin work; functions have execution and memory limits rather than a persistent worker process. | Rejected for this topology. |
| Azure VM | Runs the current Compose design and gives direct control of OS and containers. | Requires VM, Linux, Compose, Caddy, storage, power automation, SSH, runner, and host maintenance. Student credit may still make it cheaper in cash now. | Keep for rollback through cutover; retire only after acceptance and separate human sign-off. |

The free tier is not the success criterion. Durable jobs, PostgreSQL
persistence, OCR, live model calls, authentication, and preview must all work.
Railway's Free plan currently grants $1 of monthly credits (and a new trial
includes a one-time $5 credit); that is for learning the dashboard, not
production uptime or backup.

## Version 1 evidence and migration assumptions

Deployment history in the repository conflicts:

- docs/deployment/README.md has a 2026-09-14 note saying the app had not been
  deployed.
- docs/deployment/deployment-issues.md was updated 2026-09-30 and records a
  last-deployed SHA of 07132fe823cd0a2279c8ae3dddab9b90277771f6; the app was
  unreachable while the VM was deallocated and its auto-start workflow was
  disabled. It also describes an older application state.
- Source and decision records dated 2026-10-02 show later local workflow and
  Studio changes than that September deployment record.

Do not assume the current Azure runtime matches this checkout or contains no
user data. Before migration, confirm live VM status, exact deployed Git SHA,
PostgreSQL major version, schema revision, user data, and persistent files in
Azure Portal and on the VM. The September issue ledger is the last dated repo
evidence, not a live status check.

## Before provisioning

1. Start from a reviewed, clean release commit. The current local branch is
   not a production release identifier.
2. Check that the selected rehearsal branch actually contains the full
   product version. At this 2026-10-03 checkout, local staging ref 2635aba
   lacks src/oryxenai/agents/code_generator/serving.py, which is present in
   the current work branch. Reconcile/review the branch history before using
   staging for the full DB-to-Studio rehearsal.
3. Confirm whether Azure is running or stopped, whether automation can start
   it, the current DNS records, and the exact SHA reported by the live app.
4. Inventory PostgreSQL data and persistent directories from the Azure
   storage runbook. Current Studio bundles are in PostgreSQL, but an older
   deployed revision may still reference files on VM volumes.
5. Record the PostgreSQL version and Alembic revision. Production Compose
   pins PostgreSQL 16.4. Match its major version in Railway for the initial
   import if available; otherwise rehearse restore into a disposable Railway
   database first.
6. Take a database dump and VM/disk snapshot or copy of referenced files.
   Keep a copy outside the repository. Verify the dump can be listed or
   restored before treating it as a backup.
7. Do not change DNS, delete the VM, disable Azure auto-start, or promote a
   commit to protected deployment during this documentation step.

## Railway dashboard setup

Create production only after the staged deployment and acceptance run. For
the initial rehearsal, use a temporary Railway environment with its own test
database, then remove it after acceptance. A duplicate environment adds
temporary resource cost.

### 1. Project and PostgreSQL

1. Create a Railway project. Choose Singapore for the app, worker, and
   PostgreSQL services and keep them in the same region.
2. Add a Railway PostgreSQL service. Match the Azure PostgreSQL major version
   for the first data import where possible.
3. Use Railway's variable-reference picker to provide PostgreSQL's private
   DATABASE_URL to both app and worker. Do not enable public database access
   for normal app use.
4. Open the database Backups settings and explicitly enable daily backups.
   Railway documents daily volume backups with six days of retention. Also
   keep periodic logical exports outside Railway; a same-provider volume
   backup is not a complete disaster recovery plan.
5. Do not point the production app at the source database during setup. Use
   an isolated test database for the staging environment.

### 2. App / web service

1. Add a service from the GitHub repository. Keep its root directory at the
   repository root so Railway detects the root Dockerfile.
2. Leave the Dockerfile default start command in place. It reads Railway's
   injected PORT; do not replace it with a fixed port.
3. Set the deployment pre-deploy command to:

   ~~~text
   alembic upgrade head
   ~~~

   It runs before the new app is activated and must exit successfully. Set
   this on the app service only; do not run concurrent migrations from both
   app and worker.
4. Set the Railway healthcheck path to /health/ready. It checks application
   and database/schema readiness. Railway calls this during deployment but
   does not keep monitoring it afterward.
5. Assign the temporary Railway domain for rehearsal. Add the production
   domain only during controlled cutover.
6. Keep one app replica initially. Add capacity only after observing memory
   and latency under OCR and Studio workloads.

### 3. Worker service

1. Add another service from the same repository and root Dockerfile.
2. Set its start command to:

   ~~~text
   python -m oryxenai.jobs.worker
   ~~~

3. Do not assign a public domain or HTTP healthcheck. It is a background
   process and does not listen on PORT.
4. Keep it always running; turn off Railway Serverless/sleep for this service.
   Verify logs and the worker heartbeat after startup.
5. Use the same database, model, Supabase, and admission settings as the app.
   The worker reauthorizes jobs and calls configured model profiles.
6. Start with one worker replica. The production overlay sets worker
   concurrency to four. Validate PDF/OCR and multiple-job memory use before
   raising resource caps or adding replicas.

### 4. Enable server-side browser verification for Version 2

The signed Studio preview route works in the normal container. The production
overlay currently turns the browser check off, so enable Chromium on the
worker to keep the verified-page workflow available in Version 2:

1. Set the non-secret build variable INSTALL_CHROMIUM=true on the worker
   service. The root Dockerfile already has the corresponding build argument
   and optional browser layer. The API service does not need Chromium.
2. In a reviewed source change, set
   [code_generator.verification] browser = "best_effort" in the production
   overlay used by Railway.
3. Rebuild the worker from the same commit as the app. The worker executes
   page verification; the app serves the preview.
4. Start with best_effort. It records browser availability/errors while
   allowing a valid page to proceed. required makes missing Chromium a build
   failure and should be chosen only after the checks are reliable on the
   selected resources.

This configuration change has not been made by this documentation update.
If the browser cannot start on Railway, best_effort records the limitation
and still allows a valid page to proceed. Test the Studio iframe and signed
same-origin preview in a real browser before cutover.

## Environment variables

Set variables in Railway's environment store, not in source control. Apply
shared application settings to both app and worker unless noted. Use
Railway's service reference for DATABASE_URL instead of copying its
credential into two text fields.

| Variable | App | Worker | Purpose |
| --- | --- | --- | --- |
| OryxenAI_CONFIG_OVERLAY | Required | Required | Set to config/app.production.toml. |
| DATABASE_URL | Required | Required | Railway PostgreSQL private connection. Both processes use the same database. |
| SUPABASE_URL | Required | Required | Existing Supabase project URL. |
| SUPABASE_PUBLISHABLE_KEY | Required | Required | Supabase browser/public key; it is not a server secret. |
| SUPABASE_SECRET_KEY | Required | Required | Server-only Supabase key. Never expose it to frontend, browser, or logs. |
| ORYXENAI_AUTH_PRIMARY_ORIGIN | Required | Required | Exact public origin, for example https://app.oryxenai.me. No path or trailing slash. |
| ORYXENAI_AUTH_ALLOWED_ORIGINS | Required | Required | Comma-separated exact origins. Include temporary origin in rehearsal; production needs the app origin. |
| ORYXENAI_ADMIN_BOOTSTRAP_EMAILS | Required | Required | Approved administrator allowlist values required by production auth. |
| ORYXENAI_ALLOWED_USER_EMAILS | Required | Required | Normal-user allowlist because production config uses allowlist admission. |
| EXPLABS_BASE_URL | Required for live model calls | Required for live model calls | Active model endpoint; current .env.example value is https://api.experientiallabs.ai/v1. Recheck the approved provider configuration before deployment. |
| EXPLABS_API_KEY | Live calls | Live calls | Credential for the current active model profile in config/models.toml. |
| PREVIEW_GRANT_SECRET | Recommended | Not needed | Stable random secret of at least 32 characters so signed links survive app restarts and work across app replicas. |
| INSTALL_CHROMIUM | Not needed | Recommended for Version 2 | Non-secret Docker build variable; set true on the worker with the overlay change above. |
| PORT | Platform-managed | Not used | Railway injects this for the web app. Do not pin it. |

Check config/models.toml before deployment. Add the credential named by each
active profile if routing changes; do not copy every unused key from
.env.example. The active model profile reads both its endpoint and key from
EXPLABS_BASE_URL and EXPLABS_API_KEY.

Do not copy POSTGRES_PASSWORD, DB_HOST_OVERRIDE, DB_PORT_OVERRIDE, or APP_HOST
from the Azure .env template into the app/worker services; Railway supplies
the database URL and domain separately.

Reuse the approved administrator and user email settings from the current
deployment; do not put real allowlists in this public runbook. Since production
auth is required, missing Supabase or admission configuration is a release
blocker, not a reason to disable auth.

## Supabase authentication changes

Keep the existing Supabase project and Google provider configuration. User
identities and Supabase subject IDs remain in that project, so user accounts
do not need migration.

1. In Supabase Authentication → URL Configuration, set/keep the Site URL at
   https://app.oryxenai.me.
2. Add this exact URL under Redirect URLs:
   https://app.oryxenai.me/auth/callback
3. For isolated Railway rehearsal, add the exact temporary Railway callback
   URL as an additional redirect and include its origin in
   ORYXENAI_AUTH_ALLOWED_ORIGINS. Remove it after the test.
   Add that temporary origin to the Google OAuth client's Authorized
   JavaScript origins while testing if it is not already listed; remove it
   when staging ends. This does not replace the Google redirect URI below.
4. The Google OAuth provider's authorized callback remains the Supabase Auth
   callback:
   https://<SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback
   That differs from the app callback above. Do not replace the Google
   provider callback with a Railway hostname.
5. If the app hostname stays app.oryxenai.me, production Google OAuth
   settings normally need no change. Retest sign-in after DNS cutover.
6. Keep SUPABASE_SECRET_KEY server-side. The app may deliver the publishable
   key to the browser as designed.

Supabase recommends an exact production redirect path; broad wildcards are
for controlled local or preview use, not the production callback.

## Domain and HTTPS cutover

1. Exercise the app using the temporary Railway domain. Test Supabase callback
   and signed preview on that exact hostname.
2. Add app.oryxenai.me as a custom domain on the Railway app service. Copy the
   DNS record Railway shows into the existing DNS provider; do not guess a
   CNAME target from an old deployment.
3. Wait for Railway to report the domain and HTTPS certificate active.
4. Keep API, login callback, static assets, and preview on the same
   https://app.oryxenai.me origin.
5. Do not point preview.oryxenai.me at a new service. Current source serves
   Studio previews under the app origin. Retain the old preview DNS/VM route
   until rollback and old-link behavior have been checked.
6. Confirm public origin variables match the final HTTPS hostname before
   asking users to sign in.

## Migration and release order

### Stage A — Rehearse without production data

1. Deploy a temporary Railway environment from a reviewed staging commit
   only after confirming that staging contains the complete version under
   test, including Studio and preview.
2. Create an isolated PostgreSQL database; never point it at Azure production.
3. Configure the production-style overlay, required environment values, a
   test Supabase user, and the active model provider key.
4. Run the acceptance checks below, including a live model call and PDF/OCR
   test. Model provider calls can incur separate charges.
5. Record API/worker memory, OCR duration, model duration, and Railway usage.
   Adjust service resource limits only after measuring.
6. If GitHub CI is present, enable Railway Wait for CI. This requires a
   suitable GitHub Actions workflow. The checkout inspected for this guide
   has no .github workflow directory, so confirm the actual GitHub repository
   before relying on this gate.

### Stage B — Prepare the production target

1. Confirm the exact reviewed source SHA. Follow the repo rule: normal work
   on staging, reviewed production promotion through protected deployment.
2. Connect production Railway services to deployment only when the release
   is ready, but keep their automatic deploy triggers off until after the
   database restore. Staging pushes must not trigger production.
3. Ensure the same release cannot trigger the old Azure runner. Confirm
   Railway and Azure branch triggers in their dashboards before any
   production push.
4. Set production variables and prepare the app domain, but do not deploy the
   app against an empty database. The Alembic pre-deploy migration runs after
   the Azure dump has been restored in Stage C.
5. Enable the daily database backup schedule now. Take the manual Railway
   snapshot and independent logical export after restoring production data.

### Stage C — Freeze, export, restore, and switch

1. Start a maintenance window. If Azure is deallocated, confirm the existing
   VM can be started and its database is readable. Stop new Azure writes and
   stop its worker after active jobs finish or are safely left for recovery.
   Do not let Azure and Railway workers process production jobs against
   different DB copies.
2. Take the final Azure database dump after writes stop. Copy it off the VM
   and preserve the original Azure data.
   If Azure cannot be started, choose the latest verified backup and record
   its timestamp; reconcile or explicitly accept the data-loss window before
   pointing production DNS to Railway.
3. Restore into the empty Railway PostgreSQL service. Use pg_dump/pg_restore
   with --no-owner --no-acl. Prefer a Railway CLI tunnel for the external
   restore; otherwise enable a temporary PostgreSQL TCP proxy only during
   the restore and disable it immediately. Never put DATABASE_URL in source
   control or paste it into chat/logs.
4. Verify the restored database and take a pre-migration backup. This gives
   you a restore point if the new schema migration fails.
5. Inventory any legacy file-backed records the release still uses. Do not
   copy old filesystem directories just because they exist; verify current
   code has a reader for them. Current Studio bundles are database rows.
6. Manually deploy the Railway app from the reviewed SHA. Its pre-deploy command
   applies Alembic migrations to the restored database; wait for
   /health/ready. Then start/redeploy the worker from that same SHA and
   confirm it polls the restored database.
7. Update app.oryxenai.me DNS to the Railway-assigned target. Keep Azure
   available but unable to resume processing jobs against its old database.
8. Confirm DNS and HTTPS first, then test Supabase login, API, worker, a
   disposable generation, and Studio preview from a clean browser session.
   Record Railway deployment SHA and final backup location.

Example PostgreSQL client operations only. Run from a protected temporary
directory after setting connection strings in the local shell/environment
store. These are not commands to run against production before the maintenance
window.

~~~powershell
pg_dump --format=custom --no-owner --no-acl --dbname $env:SOURCE_DATABASE_URL --file .\oryxenai-azure.dump
pg_restore --no-owner --no-acl --dbname $env:RAILWAY_DATABASE_URL .\oryxenai-azure.dump
~~~

For Railway's private database, link the Railway CLI to the target project
and PostgreSQL service, then open a tunnel in a separate terminal:

~~~powershell
railway link
railway connect postgres --tunnel-only
~~~

Point RAILWAY_DATABASE_URL to the local tunnel connection details printed by
Railway. The shell variables are placeholders; never put actual values in
this file.

### Stage D — Observe, roll back, retire Azure

1. Keep Azure deallocated or otherwise unable to write during the observation
   window. Preserve its disk and verified backup.
2. Watch Railway deploy/app logs, worker heartbeat and job status, database
   usage, memory, and acceptance results for at least one normal usage cycle.
3. Roll back the app image only while its schema is compatible with the
   database. After schema changes or new production writes, rollback needs
   planned data recovery/reconciliation; simply moving DNS to Azure would
   lose Railway-side writes.
4. After acceptance, backup/restore checks, and explicit operator retirement
   approval, disable Azure auto-start and its self-hosted runner path, remove
   obsolete DNS, then retire VM/disk/IP resources. VM deallocation does not
   stop all disk or IP billing.

## Branch and deployment strategy

| Branch / environment | Purpose | Railway action |
| --- | --- | --- |
| Feature branches | Local and review work | No production service attached |
| staging | Normal development/rehearsal | Railway staging environment only |
| deployment | Protected reviewed production release | Railway production app/worker after explicit operator approval |

- Preserve the repo's staging → review → deployment flow. Attach Railway
  autodeploy only to the intended branch for each environment.
- Branch names alone do not guarantee branch contents. The local staging ref
  inspected on 2026-10-03 lacks the Studio serving module present in this
  worktree. Reconcile and review branch history before pointing Railway
  staging at it; do not treat a stale staging branch as full-flow acceptance.
- Never merge, push, or promote to deployment just to test settings. AGENTS.md
  requires real-time operator sign-off for production promotion.
- Railway Wait for CI requires a GitHub Actions workflow. This checkout has
  no workflow files visible; verify GitHub's actual configuration before
  relying on this gate.
- Run schema migrations in the app pre-deploy step only, not concurrently
  from both app and worker.
- Deploy app and worker from the same reviewed SHA. For schema changes, make
  sure an old worker cannot consume jobs against an incompatible schema.
- Keep ordinary schema releases backward-compatible while app and worker
  deploy independently. For an incompatible schema change, pause the worker,
  disable production autodeploys, deploy the app/migration, verify readiness,
  deploy the worker from the same SHA, then resume job processing.
- Prevent a production release from triggering both Azure and Railway deploy
  paths. This task did not push, open a PR, alter branch protection, or change
  either platform's settings.
- Enable Railway production autodeploy only after the first import is
  accepted. Keep Wait for CI enabled when the real GitHub workflow supports
  it; use a manual deployment of the reviewed SHA if that gate is unavailable.

## End-to-end acceptance checklist

Run this against the isolated Railway environment first and repeat critical
checks after production DNS changes. A green HTTP healthcheck alone does not
prove the workflow works.

### Database and app

- [ ] PostgreSQL is online and private; app and worker use the same URL.
- [ ] Alembic reaches the repository head without a failed pre-deploy command.
- [ ] /health/ready returns 2xx.
- [ ] Static assets and API routes load from the same public HTTPS origin.
- [ ] Create a session, refresh the browser, and confirm state persists.

### Authentication and ownership

- [ ] Google sign-in through existing Supabase returns to /auth/callback on
  the Railway hostname.
- [ ] The allowlisted test owner can create and reopen an owned session.
- [ ] A non-allowlisted test identity is rejected according to the current
  admission policy.
- [ ] Invalid/expired Supabase tokens fail as expected; auth was not bypassed.

### Worker and agent stages

- [ ] Worker logs show it started and connects to the app's PostgreSQL.
- [ ] Explicitly start Discovery; see the durable job leave the queue and
  persist a reviewable result.
- [ ] Upload selectable and scanned PDFs; confirm extraction/OCR finishes
  and the transcript reaches the intended session.
- [ ] Confirm malformed, encrypted, empty, and over-limit documents produce
  a visible error without creating an invalid source record.
- [ ] Approve Discovery, explicitly start Content Architect, review its plan,
  and approve it.
- [ ] Explicitly start Studio generation. Confirm the worker completes and
  the page version is persisted.
- [ ] Restart/redeploy the worker after enqueueing a test job; confirm the
  durable job remains and is processed when the worker returns.
- [ ] Confirm an invalid input or model failure is shown to the owner and a
  failed page does not replace the current live version.

### Studio preview

- [ ] Open the Studio iframe and confirm the generated page and theme assets
  render.
- [ ] Open the short-lived signed preview URL on the app origin and confirm
  grant/expiry behavior.
- [ ] Confirm sandbox/CSP behavior remains intact and preview is not public
  portfolio hosting.
- [ ] Refresh Studio and verify the current page still loads from PostgreSQL.
- [ ] If browser verification is enabled, inspect the version receipt and
  confirm Chromium completed or recorded a visible best_effort limitation.

### Operations and backup

- [ ] Daily Railway backup is enabled and a manual backup succeeds.
- [ ] Restore a logical dump to a disposable database before deleting Azure
  data or ending rollback availability.
- [ ] Observe a representative period of app, worker, and DB usage and record
  the real cost before deciding to retire Azure.
- [ ] Account for Railway healthchecks being deployment-only; review service
  status/logs during operation.

Use a test owner and disposable sessions. Live model calls are opt-in in the
repository test suite but required for real deployment acceptance; the model
provider bills them separately.

## Costs and operating assumptions

As checked on 2026-10-03, Railway Hobby is $5/month and includes $5 resource
usage. Published rates are $10 per GB-month of RAM, $20 per vCPU-month of CPU,
$0.15 per GB-month of volume, and $0.05 per GB of network egress. Usage above
the included $5 is billed. Prices and platform features change; recheck before
provisioning.

The web service, worker, and database consume memory around the clock. CPU and
OCR memory can spike during file intake. The Azure cost-automation document
quotes about $35.92/month for VM compute running 24/7 at the time it was
written, with scheduled shutdown reducing compute but leaving disk/network
resources billing. This is not a current invoice. Railway's live usage graph,
not a guessed package price, should be used for comparison.

Set a Railway soft usage alert before production. Choose a hard limit only
after observing representative usage. Hitting a compute hard limit can take
all services offline, a direct spend/availability trade-off. Model provider
usage, domain renewal, and Supabase charges are separate.

Railway's PostgreSQL template is an operator-managed database workload, not a
fully outsourced database operations team. The operator still owns backup
setup, restore drills, upgrades, and monitoring. If that level of database
operations is unacceptable, choose managed PostgreSQL elsewhere and accept
the extra provider and its cost.

## Troubleshooting

| Symptom | First checks |
| --- | --- |
| App does not start | Railway build/runtime logs; production overlay; injected PORT; required Supabase and allowlist values |
| /health/ready fails | DATABASE_URL reference, private networking, migration logs, current Alembic head |
| Login returns an error | Supabase Site URL and exact Redirect URL; app origin variables; Google callback; temporary hostname allowlist |
| Jobs stay queued | Worker is running and not sleeping; same DB URL; heartbeat and worker logs |
| Live agent call fails | Active route and api_key_env in config/models.toml; provider key/credits/quota; outbound call logs |
| PDF/OCR is slow or restarts | App memory/CPU chart, request logs, bundled Docling assets, per-process concurrency/resource settings |
| Generation completes but preview is blank | Bundle/version rows in PostgreSQL; same-origin serving; signed grant/expiry; browser console |
| Browser verification is unavailable | INSTALL_CHROMIUM build setting, production browser policy, image rebuild, Railway memory |

## AI-assisted operations prompt

~~~text
Read docs/deployment/version-2/deployment-strategy.md and the current source
configuration before making any deployment change. Work in Railway staging
first. Do not read, print, edit, or commit .env. Do not deploy, merge, or push
to the protected deployment branch unless I explicitly approve it in this
session. For a production cutover, report the exact source SHA, database
backup/restore status, Supabase callback status, worker status, and database-
to-Studio-preview acceptance results before changing DNS.
~~~

## Repository references

- [Root Dockerfile](../../../Dockerfile)
- [Production app overlay](../../../config/app.production.toml)
- [Model routes](../../../config/models.toml)
- [Environment template](../../../.env.example)
- [PDF extraction and managed-container notes](../document-extraction.md)
- [Azure issue ledger](../deployment-issues.md)
- [Azure VM-local storage runbook](../vm-local-storage-runbook.md)
- [Azure cost automation notes](../vm-cost-automation.md)
- [Studio preview implementation](../../../src/oryxenai/agents/code_generator/serving.py)
- [Health routes](../../../src/oryxenai/api/routes/health.py)

## Official platform references

Prices and features were checked for this research snapshot; recheck before
provisioning.

- [Railway plans and resource pricing](https://docs.railway.com/pricing/plans)
- [Railway cost controls and hard limits](https://docs.railway.com/pricing/cost-control)
- [Railway deployment regions](https://docs.railway.com/deployments/regions)
- [Railway PostgreSQL and private DATABASE_URL](https://docs.railway.com/databases/postgresql)
- [Railway pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command)
- [Railway healthchecks and injected PORT](https://docs.railway.com/deployments/healthchecks)
- [Railway GitHub autodeploys and Wait for CI](https://docs.railway.com/deployments/github-autodeploys)
- [Railway volume backup schedule](https://docs.railway.com/volumes/backups)
- [Railway PostgreSQL logical backup and restore](https://docs.railway.com/guides/postgres-backups-restores)
- [Render free services and database expiry](https://render.com/docs/free)
- [Render pricing](https://render.com/pricing)
- [Vercel function limitations](https://vercel.com/docs/functions/limitations)
- [Supabase Auth redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase Google OAuth setup and callback URI](https://supabase.com/docs/guides/auth/social-login/auth-google)
