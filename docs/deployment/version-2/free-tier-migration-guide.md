# Version 2 — free-tier pilot migration runbook

**Research checked:** 2026-10-03

**Status:** source/configuration work is local; no Render service, Supabase setting,
Google OAuth setting, DNS record, cloud database, or Azure resource was changed.
Local verification used only the dedicated `oryxenai_test` database.

**Target:** one Render Free web service + the existing Supabase project (Google
Auth and PostgreSQL). This is a low-traffic pilot, not an always-on production
service.

## Decision, plainly

Use **Render Free for one Docker Web Service**, and keep the existing Supabase
project for **both Google Auth and the application PostgreSQL database**. The
service serves the compiled Preact app and FastAPI API, runs the durable worker
beside the API in the same container, and serves signed Studio previews on the
same origin. The one service and one Supabase project are the fewest practical
services for the current architecture.

This is the best fit if the hard limit is **free compute** and the expected
usage is two or three people. It is not an honest promise of a $0 bill or an
always-on service. Render's free compute has included workspace bandwidth and
build minutes, but a linked payment method can be billed for overages.
Without a payment method, Render suspends services or new builds when an
included quota is exhausted. Check **Billing → Monthly Included Usage** before
and after each build. [Render Free limits](https://render.com/docs/free),
[outbound bandwidth](https://render.com/docs/outbound-bandwidth), and
[build pipeline](https://render.com/docs/build-pipeline)

Render labels Free for hobby/testing, provides only 0.1 CPU and 512 MB RAM,
may restart the instance, and spins it down after 15 minutes without inbound
traffic. A sleeping app cannot run its worker. Keep the Studio tab open while a
long job is running; jobs remain durable in Supabase and can resume after the
service wakes. Render's Free web plan has no separate background-worker
service, so this guide co-hosts the worker with the web process. [Render Free
limits](https://render.com/docs/free), [Render compute plans](https://render.com/docs/compute-plans)

The app contains Docling/PyTorch PDF processing. A large or scanned PDF may
exceed 512 MB or take too long on 0.1 CPU. Server-side Chromium verification is
turned off in this free overlay; the owner's browser still renders the signed
Studio preview. The app's validation and stored page version still run, but a
headless-browser receipt is not produced. If the actual PDF/OCR and complete
Studio acceptance run fails because of memory, CPU, or sleep, the blunt answer
is that this product cannot meet that requirement on a free instance. Move the
same Docker app to a paid always-on service (the prior [Railway Hobby strategy](./deployment-strategy.md)
remains the simpler paid option) rather than claiming a free deploy is reliable.

Do not use Render's Free PostgreSQL for this app: it expires 30 days after
creation and has no backups. Supabase is already in the stack, so using its
PostgreSQL avoids a third service. Supabase Free is also a pilot tier: Nano has
a recommended maximum database size of 500 MB, and inactive projects may pause
after a week of low database activity. The 500 MB database quota can put a Free
project into read-only mode (even though its underlying included disk is 1 GB).
Free projects have no downloadable automatic daily backups; keep logical
exports outside Supabase. [Supabase compute/disk
limits](https://supabase.com/docs/guides/platform/compute-and-disk),
[database size limits](https://supabase.com/docs/guides/platform/database-size),
[Supabase project pausing](https://supabase.com/docs/guides/platform/free-project-pausing),
[Supabase backups](https://supabase.com/docs/guides/platform/backups)

### What I ruled out

| Option | Why it is not the free-tier pick |
| --- | --- |
| Railway Free | $1/month usage credit and 512 MB RAM per service; an app, worker, and database running together are unlikely to fit that allowance reliably. Railway Hobby starts at $5/month plus usage above its included $5. [Railway plans](https://docs.railway.com/pricing/plans) |
| Vercel Hobby | Good for static/front-end or request functions, but this app needs a durable PostgreSQL worker and has configured agent jobs up to 600–900 seconds. Hobby functions cap execution at 300 seconds. Splitting it would add another host/origin and would not supply the persistent worker. [Vercel function limits](https://vercel.com/docs/functions/limitations) |
| Render Free Postgres | Expires after 30 days and has no backup support. Supabase already supplies the database and Auth. [Render Free limits](https://render.com/docs/free) |
| Separate frontend host, Redis, object storage, preview host | Not needed: the Dockerfile builds the frontend; PostgreSQL is already the durable queue and Studio page store; previews are same-origin. |

## Diagram: where each piece goes

```text
                         Google account
                              │
                              ▼
Browser ── sign-in ──► Supabase Auth ── callback ──► /auth/callback
  │                                                     │
  │ HTTPS: app, API, static assets, signed preview      │
  ▼                                                     ▼
┌──────────────────────── Render Free Web Service ─────────────────────────┐
│ Root Dockerfile builds Preact + FastAPI + offline Docling model assets    │
│                                                                           │
│  FastAPI process                         Worker process                   │
│  • Auth and owner checks                  • polls durable queue            │
│  • app API                                • Discovery / PDF extraction     │
│  • serves Preact files                    • Content Architect              │
│  • serves signed /preview/...              • Studio page generation         │
└─────────────┬────────────────────────────────┬────────────────────────────┘
              │                                │
              └── DATABASE_URL (TLS, session pooler) ──┐
                                                        ▼
                     ┌──────── Existing Supabase project ──────────┐
                     │ Google Auth + PostgreSQL                     │
                     │ public schema: app sessions, jobs, versions  │
                     │ Auth schema: stable Supabase user identities │
                     └──────────────────────────────────────────────┘

Worker ── configured EXPLABS model calls ──► Experiential Labs API
Browser ◄── same-origin sandboxed preview ── FastAPI + version in Postgres
```

`/app`, `/api/...`, assets, `/auth/callback`, and `/preview/g/...` all use the
same Render HTTPS origin. There is no Vercel frontend, second API origin,
separate worker service, Redis, Render database, or public hosting for generated
portfolios.

## Verified repository facts and assumptions

These facts were checked in the repository on 2026-10-03. Dashboard values must
still be confirmed in the live services before changing them.

- The app is Python 3.13/FastAPI, SQLAlchemy async, Alembic, and PostgreSQL; the
  frontend is Preact/TypeScript/Vite. The root [`Dockerfile`](../../../Dockerfile)
  builds the frontend and includes offline Docling assets under
  `/opt/docling-models`.
- `main.py` starts the API only. Render Free cannot create a Free background
  worker, so this change adds
  [`render_web.py`](../../../src/oryxenai/deployment/render_web.py): it applies
  Alembic migrations, starts Uvicorn and the current PostgreSQL worker, forwards
  shutdown signals, and stops the service if either child process exits.
- The Render overlay is
  [`app.render-free.toml`](../../../config/app.render-free.toml). It turns on
  required Supabase auth and the allowlist, limits concurrency/pools to one,
  keeps the product Preact shell, stores no durable data on Render's ephemeral
  disk, and turns off server-side Chromium to conserve memory.
- The application uses Supabase as the identity provider but accesses app data
  through SQLAlchemy/PostgreSQL, not Supabase REST/Data API. The app's tables
  are in `public`; Supabase Auth's users stay in the project's `auth` schema.
- Studio bundles are stored in `portfolio_site_versions` in PostgreSQL and
  served through same-origin signed preview URLs. The fixed theme is in the
  image. A separate preview host or object store is not required.
- The retired pre-Studio Code Generator tables can remain in a restored
  database. Current Studio does not read those legacy runs; the 30-day worker
  cleanup removes old run rows and their database-cascaded stage/event rows.
  Azure VM-local artifact files are not imported into Render and remain only in
  the off-VM backup until the migration is accepted.
- The active model routes in `config/models.toml` use `EXPLABS_API_KEY` and
  `EXPLABS_BASE_URL`. Hosting credits do not pay the model provider.
- The confirmed Auth setup document records Supabase project
  `oxygen-ai-development`, ref `diiestlnmpaarhhexwhi`, region Mumbai
  (`ap-south-1`), with Google enabled and the OAuth app in Testing. It records
  Google project `Oxygen.ai` and client `Oxygen.ai Development`; the Client ID
  and secret are intentionally private. This is a development project, so
  reusing it means pilot app data shares that project with development Auth.
  There is no separate production Supabase project in the checked-in setup.
  See [`09-confirmed-setup.md`](../../Auth/09-confirmed-setup.md).
- Last checked-in Azure issue evidence says the VM was deallocated and the
  public app unreachable on 2026-09-30. This is historical evidence, not a
  current Azure query. A deployed-SHA note points to an older build than this
  checkout. Do not assume Azure is empty or matches current code.
- The current checkout is on local branch `NEW`, ahead of `origin/NEW`. The
  checked local `staging` ref lacks `src/oryxenai/agents/code_generator/serving.py`;
  it is not safe as the complete Studio rehearsal source until reconciled. No
  GitHub Actions workflow files were present in the checked checkout. The old
  `deployment` branch is wired to Azure; do not select it for Render. Before
  creating a release branch, inspect `git status` and exclude all unrelated
  local or staged work from this migration.

## Before opening dashboards

### 1. Release the code to a Render-only branch

1. Review and merge this task's code/documentation commit into `staging` through
   the repository's normal review path. First reconcile the missing Studio
   `serving.py` on `staging`; the branch must contain the full current app,
   `0028_private_supabase_app_schema`, the Render launcher, retention code, and
   overlay.
2. Create a branch named **`render-pilot`** from that reviewed `staging` commit.
   Do not use `deployment`: it can still trigger Azure deployment.
3. Connect Render to `render-pilot`. Keep Render **Manual Deploy** selected for
   the first rollout. There is no checked-in CI gate to rely on.
4. Do not merge or push to `deployment`, disable branch protection, or turn off
   Azure automation during this code-review step.

The worktree may contain unrelated local or staged changes. Inspect
`git status` before creating a release commit and exclude anything outside this
migration.

### 2. Choose whether to migrate old Azure app data

The two paths below are different; choose one before first Render startup.

**Recommended for the cleanest pilot if old sessions can be retired:** keep the
existing Supabase Auth project, do not import the Azure PostgreSQL database,
and let the first Render start run Alembic on the project's empty OryxenAI app
schema. Existing Google identities remain in Supabase Auth and are provisioned
into the new app tables on first sign-in. Previous portfolio sessions, approved
briefs, job history, and Studio versions will not appear in the new database.
This is a real data reset; it is not a backup.

**If the current portfolio/session records must survive:** take and verify an
Azure PostgreSQL backup and restore only the Azure `public` schema into the
existing Supabase Postgres database **before** creating/starting the Render
service. Reuse the exact same Supabase project so `app_users.supabase_user_id`
continues to refer to the existing Auth UUIDs. Never dump/restore Supabase's
`auth`, `storage`, or other Supabase-managed schemas. The next Render startup
runs Alembic to the current head; migration `0028` re-applies server-only table
permissions and RLS to app tables, including a restored database whose older
Alembic history would otherwise skip the original Supabase-specific ACL step.

If the target project's `public` schema already contains OryxenAI tables, or
the source dump lists objects that collide with existing Supabase objects, stop
before restore. Do not use `pg_restore --clean`, drop schemas, or delete
sessions to make it fit. Rehearse against a disposable project first. This is
the only migration step that needs access to the old Azure VM, and only if
preserving Azure data is required.

## Step 1 — check Supabase and Google settings

Open the existing project directly:

**Supabase Dashboard:** <https://supabase.com/dashboard/project/diiestlnmpaarhhexwhi>

**Google Auth clients:** <https://console.cloud.google.com/auth/clients>

In Supabase, verify the selected project name/ref shown in the dashboard is
`oxygen-ai-development` / `diiestlnmpaarhhexwhi`. If it is a different project,
stop and use that project's own callback/key values instead; do not substitute
another project ref into this guide.

### 1A. Check the target DB before creating app tables

Open **SQL Editor → New query** in the project and run these read-only checks:

```sql
select current_database() as database_name,
       pg_size_pretty(pg_database_size(current_database())) as database_size;

select schemaname,
       relname as table_name,
       pg_size_pretty(pg_total_relation_size(relid)) as total_size
from pg_catalog.pg_statio_user_tables
where schemaname = 'public'
order by pg_total_relation_size(relid) desc
limit 25;

select schemaname, tablename
from pg_catalog.pg_tables
where schemaname = 'public'
order by tablename;
```

The checked-in Auth setup says there were no manually created app tables when
it was recorded; verify the live project. Keep the total below 400 MB before
importing old Azure data. **400 MB is a conservative migration target, not a
published Supabase limit.** Supabase lists 500 MB as the Free Nano recommended
maximum. If the database is already close to 500 MB, do not import; first
identify and safely remove unused app data or choose a paid database plan.
Deleting rows does not always make PostgreSQL's on-disk size shrink
immediately; ordinary vacuuming reuses space. Do not run `VACUUM FULL` as a
quick fix.

### 1B. Google OAuth provider settings

The app's sign-in uses the existing Supabase Google provider. Keep its current
Google Client ID and Client Secret; the app does not need a new Google OAuth
client just because the host changes.

1. In Supabase, open **Authentication → Sign In / Providers → Google**.
2. Keep **Google enabled**.
3. Keep the saved **Client ID** and **Client Secret** unchanged. Do not paste
   these values into the Render app; Supabase owns them.
4. Leave **Skip nonce checks** off and **Allow users without an email** off,
   matching the recorded setup.
5. Keep the scopes `openid`, `userinfo.email`, and `userinfo.profile`.
6. On the Google Auth clients page, select Google project **Oxygen.ai** and
   open web client **Oxygen.ai Development**. Do not create another client.
7. After Render has generated its service hostname, add the following one
   value to **Authorized JavaScript origins**:

   ```text
   https://<EXACT_RENDER_HOSTNAME>
   ```

   The origin contains only scheme and host: no `/auth/callback`, no path, no
   trailing slash. Keep both existing local origins:

   ```text
   http://localhost:8000
   http://127.0.0.1:8000
   ```

8. In **Authorized redirect URIs**, keep exactly the Supabase callback already
   recorded for this project:

   ```text
   https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback
   ```

   Do **not** replace this URI with the Render callback. Google's redirect is
   to Supabase; Supabase then redirects to the app. [Supabase Google OAuth
   setup](https://supabase.com/docs/guides/auth/social-login/auth-google)

9. Leave Google's audience **External** and publishing status **Testing** for
   this small private pilot. Under **Test users**, add each exact account that
   will log in, including the existing two admins and the new normal user.
   Each additional person must be added to Test users while Testing remains
   enabled; they will not be able to sign in just because their app email is
   allowlisted. For a private 2–3 person pilot, publishing the consent screen
   is not required.

The Google client ID and secret remain in Supabase. The Render service only
needs the Supabase project URL and Supabase API keys in its runtime variables.

### 1C. Supabase URL Configuration

After the Render service hostname exists, open **Authentication → URL
Configuration** and set:

| Supabase field | Exact value |
| --- | --- |
| Site URL | `https://<EXACT_RENDER_HOSTNAME>` |
| Redirect URL 1 | `https://<EXACT_RENDER_HOSTNAME>/auth/callback` |
| Redirect URL 2 | `http://localhost:8000/auth/callback` |
| Redirect URL 3 | `http://127.0.0.1:8000/auth/callback` |

Replace `<EXACT_RENDER_HOSTNAME>` with the full host shown by Render, without
`https://` inside the placeholder. For example, if Render shows
`oryxenai-free-pilot.onrender.com`, the Site URL is
`https://oryxenai-free-pilot.onrender.com` and the callback is
`https://oryxenai-free-pilot.onrender.com/auth/callback`. Use the dashboard's
actual hostname if it differs. Do not add a wildcard or `preview.oryxenai.me`.
Supabase requires the app callback to be in its redirect allowlist; this is a
different URL from Google's Supabase callback. [Supabase redirect URL
configuration](https://supabase.com/docs/guides/auth/redirect-urls)

### 1D. Supabase app keys and PostgreSQL connection string

1. Under **Project Settings → API Keys**, copy the current **Publishable key**
   and **Secret key** for this project. These are not the Google OAuth
   Client ID/Secret. Use the values expected by the current app environment
   names below. Never put the secret key in frontend/Vite variables.
2. Open **Connect** at the top of the project dashboard.
3. Select **Session pooler** and copy its PostgreSQL URI. Use the
   **Session** mode on port **5432**, not Transaction mode on `6543`; this app
   uses a long-running backend and normal SQLAlchemy sessions/prepared
   statements. Supabase documents session mode for IPv4-only clients. Do not
   invent the pooler host or username; copy them from this dashboard.
4. Replace the displayed `[YOUR-PASSWORD]` placeholder with this Supabase
   project's database password. URL-encode reserved characters in that
   password. Keep all query parameters Supabase includes, especially
   `sslmode=require`.

The shape will be similar to the following; the username/password/host must be
the exact dashboard-generated values:

```text
postgresql://postgres.diiestlnmpaarhhexwhi:<URL-ENCODED_DATABASE_PASSWORD>@<COPIED_SESSION_POOLER_HOST>:5432/postgres?sslmode=require
```

The code converts the `postgresql://` scheme to `postgresql+asyncpg://` and
converts `sslmode=require` for asyncpg. [Supabase Postgres connection
methods](https://supabase.com/docs/guides/database/connecting-to-postgres)

## Step 2 — optional Azure data export and import

Skip this section only if the decision in **Before opening dashboards → 2.
Choose whether to migrate old Azure app data** was to start with an empty
OryxenAI application database. The app schema will then be created by Alembic
on Render's first boot, and old portfolio sessions will not be available.

### 2A. Read-only Azure check and backup

This is necessary only when retaining Azure data. The repository's current
status note says the VM was deallocated on 2026-09-30, but status may have
changed. In Azure Portal, inspect the VM and its storage read-only first. Do
not delete it or change its network/OS disk; it is being repurposed.

If the VM is stopped and the old database must be copied, start it temporarily
only for backup/export, then stop OryxenAI writes and worker jobs. From the
deployed repository root on the VM, run its existing backup command:

```bash
./scripts/azure-deploy.sh backup
```

This creates compressed SQL and a separate archive of OryxenAI's VM storage in
the configured backup directory (default `/srv/oryxenai-backups`). Verify the
`.sha256` files and copy both archives off the VM before removing anything.

For the Supabase import, also make a PostgreSQL custom-format dump of the
source `public` schema. Run this from the production Compose project root on
the VM, using the actual configured backup directory if it differs from the
default:

```bash
docker compose -f compose.production.yaml exec -T postgres \
  pg_dump -U oryxen -d oryxenai --format=custom --schema=public \
  --no-owner --no-acl \
  > /srv/oryxenai-backups/oryxenai-public.dump

sha256sum /srv/oryxenai-backups/oryxenai-public.dump \
  | tee /srv/oryxenai-backups/oryxenai-public.dump.sha256
sha256sum -c /srv/oryxenai-backups/oryxenai-public.dump.sha256
pg_restore --list /srv/oryxenai-backups/oryxenai-public.dump | head -40
```

Keep this dump private and outside Git. Copy it to the operator's machine with
`scp` using the VM's actual SSH host/user from Azure; do not use a guessed
address. The browser extension cannot perform or validate this binary database
transfer.

Before restore, re-run the Step 1A table list on Supabase and confirm no
OryxenAI app tables already exist. Set a temporary `TARGET_DATABASE_URL` in a
local PowerShell session using the session-pooler URI. To avoid putting the URI
in command history, use a secure prompt:

```powershell
$secureDbUrl = Read-Host -AsSecureString "Paste the Supabase Session pooler URI"
$dbUrlPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureDbUrl)
try {
    $env:TARGET_DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($dbUrlPointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($dbUrlPointer)
}
```

Remove the temporary environment variable when restore is finished:

```powershell
Remove-Item Env:\TARGET_DATABASE_URL
```

### 2B. Restore without dropping Supabase's existing `public` schema

Use a PostgreSQL client version compatible with the source dump. First make a
restore list, excluding only the source `public` schema-creation record (the
Supabase database already has a `public` schema):

```powershell
pg_restore --list .\oryxenai-public.dump |
    Where-Object { $_ -notmatch ' SCHEMA - public ' } |
    Set-Content -Encoding ascii .\oryxenai-public.restore-list
```

Review `oryxenai-public.restore-list` before using it. It must still contain
the app tables and the `alembic_version` table. If it contains an unexpected
object that collides with Supabase, stop and rehearse a filtered restore
instead of dropping anything.

Restore only with the reviewed list. `--single-transaction` makes a failed
restore roll back as a unit. Do not include `--clean`:

```powershell
pg_restore --use-list .\oryxenai-public.restore-list `
    --no-owner --no-acl --single-transaction `
    --dbname="$env:TARGET_DATABASE_URL" `
    .\oryxenai-public.dump
```

Only the Azure `public` schema is imported. Supabase's `auth` schema, Google
OAuth client, Supabase Auth user UUIDs, Storage schema, and provider config are
not imported or replaced. The next Render service start runs:

```text
python -m alembic upgrade head
```

Migration `0028_private_supabase_app_schema` applies RLS and revokes direct
Supabase Data API privileges from app tables after the restore. If the restore
list does not show `alembic_version`, or migration logs report an unknown
revision, stop and restore into a disposable project for diagnosis before
allowing the pilot app to write.

After the app passes acceptance, save the verified source dump off the VM.
Do not run a generic SQL `DELETE` against `portfolio_sessions` or
`portfolio_site_versions` to reduce size: the relationship to the active
page and approved workflow data must be preserved.

## Step 3 — create one Render Web Service

Open **Render Dashboard:** <https://dashboard.render.com/>. Create this service
from the reviewed `render-pilot` branch only after the Supabase settings and,
if applicable, DB restore are complete.

1. Select **New → Web Service**.
2. Connect GitHub if prompted, select repository
   `https://github.com/yashsrivastava0/OryxenAI`, then click **Connect**.
3. Fill the create form as follows:

| Render field | Exact input |
| --- | --- |
| Name | `oryxenai-free-pilot` |
| Region | `Singapore` |
| Branch | `render-pilot` |
| Language / Runtime | `Docker` |
| Root Directory | leave blank (repository root) |
| Dockerfile Path | `./Dockerfile` |
| Docker Context Directory | `.` / repository root, if shown |
| Build Command | leave blank; Dockerfile builds the frontend and Python image |
| Docker Command | `python -m oryxenai.deployment.render_web` |
| Instance Type | `Free` |
| Health Check Path | `/health/ready` |
| Persistent Disk | none |
| Auto-Deploy | `Manual Deploy` for first release |
| Custom Domain | none for the pilot; use the generated `onrender.com` host |

Render supports building from a repository Dockerfile and lets a Docker
Command override the Dockerfile `CMD`. The root Dockerfile is required here;
do not choose the native Python runtime or a Render Static Site. [Render Docker
deploys](https://render.com/docs/docker), [Render Web Services](https://render.com/docs/web-services)

4. In the create form's **Environment Variables** area, add the exact variables
   in Step 4 before creating the service. For the two origin variables, enter
   the expected value `https://oryxenai-free-pilot.onrender.com` if available;
   after creation, compare it with the exact host Render shows and correct
   both variables if Render assigned a different hostname.
5. Create the Web Service. Copy the hostname from the service's **Settings →
   Domains** page. Use the dashboard's exact value in all origin and OAuth
   settings. The likely hostname is
   `oryxenai-free-pilot.onrender.com`; it is not authoritative until shown by
   Render.
6. If environment variables were added after service creation, use **Save,
   rebuild, and deploy**. Check **Events/Logs** until the build and deployment
   succeed.
7. Confirm Render's HTTPS service URL responds to
   `https://<EXACT_RENDER_HOSTNAME>/health/ready` with HTTP 200 and JSON
   `{"status":"ready","database":"up"}`.

Do not create another Render worker, Render PostgreSQL database, Render Key
Value store, or Static Site. The supervisor starts the app and worker in this
one service. Render Free has no SSH/Shell access, no persistent disk, and no
one-off job service; migrations run in `render_web.py` on service startup.

## Step 4 — set Render environment variables

Open the service → **Environment** → **Environment Variables**. Add each row
individually. Do not bulk-upload the repository `.env`: it also contains
Azure/local settings and unused provider keys. Render exposes environment
variables at runtime; keep credentials in this dashboard only. [Render
environment variables](https://render.com/docs/configure-environment-variables)

| Key (type exactly) | Value to enter | Keep secret? |
| --- | --- | --- |
| `OryxenAI_CONFIG_OVERLAY` | `config/app.render-free.toml` | No |
| `DATABASE_URL` | Full Supabase Session pooler URI from Step 1D, with password URL-encoded and `sslmode=require` | **Yes** |
| `SUPABASE_URL` | `https://diiestlnmpaarhhexwhi.supabase.co` | No |
| `SUPABASE_PUBLISHABLE_KEY` | Copy the project's current Supabase Publishable key | No (browser-safe, but set only in the service config) |
| `SUPABASE_SECRET_KEY` | Copy the project's current Supabase Secret key | **Yes** |
| `ORYXENAI_AUTH_PRIMARY_ORIGIN` | `https://<EXACT_RENDER_HOSTNAME>`; no trailing slash | No |
| `ORYXENAI_AUTH_ALLOWED_ORIGINS` | `https://<EXACT_RENDER_HOSTNAME>`; one exact origin, no wildcard | No |
| `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` | The two existing admin Google emails, comma-separated, copied privately from the current approved settings | Private configuration |
| `ORYXENAI_ALLOWED_USER_EMAILS` | The exact normal-user Google email(s) admitted to the pilot, comma-separated | Private configuration |
| `EXPLABS_BASE_URL` | `https://api.experientiallabs.ai/v1` | No |
| `EXPLABS_API_KEY` | Copy the currently active Experiential Labs key from its private key store | **Yes** |
| `PREVIEW_GRANT_SECRET` | Generate locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`; paste its output once and keep it stable | **Yes** |

For initial service creation, if Render has not assigned the final hostname yet,
use the placeholder origin already in `app.render-free.toml`, then replace it
with the exact Render origin immediately after service creation and redeploy.
Auth is not accepted as configured until the exact host is in Render, Supabase
URL Configuration, Google Authorized JavaScript origins, and both origin
environment variables.

Do not add `PORT`; Render supplies it and `render_web.py` binds to it. Do not
add `VITE_*` keys; FastAPI injects the Supabase browser settings at runtime. Do
not add `POSTGRES_PASSWORD`, `DB_HOST_OVERRIDE`, `DB_PORT_OVERRIDE`, `APP_HOST`,
`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, or inactive OpenAI/Anthropic/Gemini
keys. The existing project does not need them for this configuration.

The keys `SUPABASE_SECRET_KEY`, `EXPLABS_API_KEY`, `DATABASE_URL`, and
`PREVIEW_GRANT_SECRET` must never be committed, pasted into documentation,
included in an AI prompt, or placed in the browser bundle. To populate them,
copy directly from their provider's secret screen into Render's value field.
Never use Render's **Add from .env** with the complete repository `.env`.

## Step 5 — finish the exact OAuth URL edits

Now that Render's actual host exists:

1. Set the Supabase **Site URL** and three **Redirect URLs** exactly as in Step
   1C using the actual host.
2. In Google Auth Platform → `Oxygen.ai` → `Oxygen.ai Development`, add the
   actual HTTPS origin to **Authorized JavaScript origins**. Do not add a path.
3. Confirm Google's **Authorized redirect URI** is still:

   ```text
   https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback
   ```

4. In Google **Test users**, ensure all three pilot accounts are listed: the
   two admin accounts and the one normal user (or the exact 2–3 total intended
   users, if the two admins are among those people).
5. In Render Environment, set both origin variables to the exact Render host
   and select **Save, rebuild, and deploy**.
6. Wait for the new deployment to finish and `/health/ready` to return 200.

The current app configuration hard-requires exactly **two bootstrap admin
emails** and its validator fixes the database normal-user capacity at **15**.
Do not set a made-up `normal_user_limit=3`; startup rejects it. In restricted
mode the exact allowlist controls who may join. A minimal pilot with one normal
user plus two admins is three distinct identities. If “two or three users” is
intended to mean two or three *normal* users in addition to two administrators,
then the total account count is four or five; put those normal identities in
both Google's Test users and `ORYXENAI_ALLOWED_USER_EMAILS`.

## Step 6 — first deployment and first login

1. In Render → service → **Manual Deploy**, deploy the latest reviewed commit
   from `render-pilot`.
2. In deployment logs, confirm:
   - `alembic upgrade head` exits successfully before the child processes
     start;
   - Uvicorn starts on Render's injected port;
   - worker logs show it started and connected to the same Supabase database;
   - no startup error reports missing Supabase keys, database connectivity,
     auth-origin validation, or provider configuration.
3. Open `https://<EXACT_RENDER_HOSTNAME>/health/ready`. Require HTTP 200 and
   `database: up`.
4. Open `https://<EXACT_RENDER_HOSTNAME>/sign-in` in a normal browser tab.
5. Sign in with the allowlisted normal Google test account. Do not enter or
   share anyone's Google password with the browser-control agent. Google
   returns to the Supabase callback, then to
   `https://<EXACT_RENDER_HOSTNAME>/auth/callback`.
6. Complete onboarding with a test name/username. Confirm the user reaches
   `/app` and can create a session.
7. Sign in separately with each admin identity and confirm the admin page is
   available only to those bootstrap admins.
8. Try one Google account that is not in the Google test-user list or app
   allowlist only if you have an approved test account for that check. It must
   not gain app access.

## Step 7 — verify DB → agents → generated page → preview

Keep the browser tab visible during the first run. The frontend checks for job
updates while it is visible; Render Free can stop the worker after inactivity.
The durable job row remains in Postgres, but it cannot execute while the Render
container is stopped.

1. In the new user's `/app` workspace, create a test session and refresh the
   page. The same session should still be present, proving the app uses
   PostgreSQL rather than Render's ephemeral filesystem.
2. Use a small plain-text intake first. Explicitly start Discovery. Wait for
   the job to finish and confirm a reviewable brief appears; do not close the
   tab during the job.
3. Approve the brief, explicitly start Content Architect, review its plan, and
   approve it.
4. Explicitly start Studio generation. Wait for the job to finish. Confirm the
   version is saved, the Studio iframe displays the page, and its theme assets
   load.
5. Open the short-lived signed preview from the same Render host. Confirm it
   loads without a login leak or cross-origin preview host. The grant lasts 30
   minutes by current config; it can be reissued from Studio after expiry.
6. Send a supported content-change request in Studio chat, wait for the new
   version, and refresh. Confirm the live page remains after refresh.
7. In Supabase SQL Editor, inspect counts/statuses without opening sensitive
   payloads:

   ```sql
   select status, count(*)
   from public.background_jobs
   group by status
   order by status;

   select count(*) as app_users from public.app_users;
   select count(*) as sessions from public.portfolio_sessions;
   select count(*) as page_versions from public.portfolio_site_versions;
   ```

8. Repeat with one small selectable-text PDF. Only after that passes, try one
   small scanned PDF and watch Render's memory/restart/log view during OCR.
   Stop if it repeatedly restarts or fails; do not increase complexity by
   adding services to hide a Free-plan memory limit.
9. Confirm Render's health endpoint remains ready and the worker heartbeat
   updates. A green HTTP health check alone does not prove agents or preview
   work.

With `browser = "off"`, application-side Chromium checking is intentionally
absent. A successful Studio preview means the generated page rendered in the
owner's browser; it does not mean a headless server browser verified it.
Enablement of that verification requires a Chromium-enabled image and more
memory, so it is a paid-tier acceptance item if required.

## Step 8 — backups, quotas, and ongoing care

- Check Render's **Billing → Monthly Included Usage** at least weekly. One
  continuously running Free web service can use most of the 750 workspace
  instance hours/month. The Hobby workspace currently includes 5 GB of outbound
  bandwidth and 500 build pipeline minutes. If a payment method is linked,
  overages can be charged; without one, quota exhaustion suspends the service or
  disables builds until reset. Keep the service on the Free compute plan and
  check the live billing page; watch for suspension or restarts. [Render Free
  limits](https://render.com/docs/free), [outbound bandwidth
  limits](https://render.com/docs/outbound-bandwidth), [build pipeline
  limits](https://render.com/docs/build-pipeline)
- Check Supabase's project health and database size at least weekly. Use the
  same Supabase project periodically so a low-activity Free project is less
  likely to pause. If it pauses, resume from the Supabase Dashboard. Supabase
  says a few user queries per day during the prior week typically avoids
  inactivity pausing, but this is not an uptime guarantee.
- Supabase Free does not provide downloadable scheduled daily backups. Once a
  week, create a custom PostgreSQL dump outside the repository using a local
  PostgreSQL client and the same private Session pooler URI:

  ```powershell
  $backupDir = Join-Path $env:LOCALAPPDATA "OryxenAI\backups"
  New-Item -ItemType Directory -Force $backupDir | Out-Null
  $backupFile = Join-Path $backupDir ("oryxenai-supabase-{0}.dump" -f (Get-Date -Format "yyyyMMdd"))
  pg_dump --format=custom --no-owner --no-acl --schema=public `
      --dbname="$env:TARGET_DATABASE_URL" --file="$backupFile"
  pg_restore --list "$backupFile" | Select-Object -First 20
  ```

  Set `TARGET_DATABASE_URL` only in the local shell/session as shown in Step
  2A; never commit it. Keep one additional backup copy outside the computer.
  Periodically rehearse a restore into a disposable database/project before
  treating the dump as a recovery plan. [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups)
- Model API calls are billed/quota-limited separately by Experiential Labs.
  Hosting's Free quota does not provide free model tokens. Start with a small
  controlled test prompt and check the provider's current balance/limits.
- The container's filesystem is ephemeral. Uploaded input is processed by the
  app; durable sessions, jobs, model cache, and version HTML belong in
  Supabase PostgreSQL. Do not add persistent user data to local files.

## Implemented 30-day data retention

This change adds a worker maintenance loop and the Render-only configuration:

- The worker runs an immediate, bounded cleanup sweep at startup and then
  about once every 24 hours while the service is awake.
- It deletes expired or 30-day-idle structured model-cache rows.
- It deletes terminal Studio versions older than 30 days only if they are not
  the active version and not the newest ready version for that session. It
  also keeps `max_versions_per_session = 10`, which prunes older versions when
  a new generation is completed.
- It removes pre-Studio `code_generator_runs` last updated more than 30 days
  ago. Their stage-attempt and event rows cascade from the run deletion. This
  retired pipeline is not used by current Studio; the latest active page and
  the whole portfolio session are retained.
- Each sweep is bounded to 100 rows per category; the app configuration can
  tune this batch size. Superseded versions' chat-message foreign keys are set
  null by the existing database relation; the user's overall session, intake,
  approved Discovery/Content Architect artifacts, and latest active page are
  not deleted.
- This is a real scheduled cleanup policy, but Render sleep means the daily
  clock pauses while the service is stopped. The sweep runs again when the
  worker starts.
- It does not delete whole accounts or sessions, unexpired/in-progress jobs,
  current output, or legacy Azure files. Old Azure storage is removed only
  during the final Oryxen-only host cleanup after its backup has been checked.
- PostgreSQL may reuse deleted space without immediately reducing the reported
  database file size. Monitor Supabase's reported usage; do not use a blocking
  `VACUUM FULL` as an automated retention action.

## Step 9 — minimal Azure cleanup after acceptance

Do this only after all acceptance checks pass, a Supabase dump is saved and
listed successfully, and any Azure data required for migration has been
restored and checked.

1. From the deployed OryxenAI checkout on the VM, inspect the actual service
   names with `docker compose -f compose.production.yaml ps`. After the final
   database backup, stop the OryxenAI `app`, `worker`, `caddy`, and `postgres`
   services shown by the current Compose file. If the older deployed checkout
   still has a separate `preview-gateway`, stop that OryxenAI service too.
   Preserve the VM itself, its OS disk, shared network resources, and anything
   needed by the next project. Do not run `docker compose down -v`.
2. Disable only the OryxenAI Azure self-hosted runner/deploy trigger so a later
   push cannot redeploy to this repurposed machine. Confirm the runner is not
   shared by the next project first.
3. Keep the verified database and file backups off the VM. After the rollback
   window is over, remove only OryxenAI containers/images, its checkout, and
   its dedicated data directories (documented defaults are `/srv/oryxenai`
   and `/srv/oryxenai-backups`; verify actual paths before removing). Do not
   delete the VM, disk, IP, VNet, or any shared resource.
4. Leave DNS alone for the free pilot because it uses Render's generated
   `onrender.com` URL. Do not point `app.oryxenai.me` at Render unless you
   separately decide to attach that custom domain and update its DNS.

## Troubleshooting map

| Symptom | Check in this order |
| --- | --- |
| Build fails | Render Build Logs; root context is repo root; Docker runtime selected; `Dockerfile` and `uv.lock` present; build minutes remaining. |
| Service exits before API starts | Render runtime logs; `OryxenAI_CONFIG_OVERLAY` exact case/path; Supabase env vars set; copied `DATABASE_URL` is Session pooler port 5432; startup Alembic migration result. |
| `/health/ready` returns 503 | Supabase project is active; `DATABASE_URL` is exact and includes SSL; Session pooler host/username copied, password percent-encoded; Alembic reached head. |
| Google returns redirect error | Supabase Site URL and exact app callback; Google Authorized JavaScript origin contains only the Render origin; Google Authorized redirect URI is still the Supabase callback; update both origin vars. |
| Google signs in but app denies user | Account is in Google's Test users and `ORYXENAI_ALLOWED_USER_EMAILS`; bootstrap admins are in `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`; keep admission mode `allowlist`. |
| Jobs stay queued | Render service is awake; worker startup is in the same service logs; worker and API use the same DB URL; inspect `background_jobs.status`. |
| PDF/OCR restarts service | 512 MB Free memory limit; try plain text/small selectable PDF. Repeated scan/OCR failure means Free is too small for this workload. |
| Studio page is blank | `portfolio_site_versions` row and active version; same-origin `/preview/g/...`; static theme assets included in current Docker image; preview grant secret stable. |
| Supabase project paused | Resume the project in Supabase Dashboard, then load the app and verify `/health/ready`; free-tier inactivity pause is separate from Render sleep. |
| Database usage stays high after TTL | Check table sizes and live rows. PostgreSQL may not shrink its files after deletion; do not drop active sessions or run `VACUUM FULL` without a planned maintenance window. |

## Official references

- [Render Free instances and their limits](https://render.com/docs/free)
- [Render compute plans](https://render.com/docs/compute-plans)
- [Render Docker services](https://render.com/docs/docker)
- [Render environment variables](https://render.com/docs/configure-environment-variables)
- [Render service regions](https://render.com/docs/regions)
- [Supabase Google OAuth](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
- [Supabase Postgres connection methods](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase compute and disk limits](https://supabase.com/docs/guides/platform/compute-and-disk)
- [Supabase Free project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
- [Supabase database backups](https://supabase.com/docs/guides/platform/backups)
- [Railway plans and usage pricing](https://docs.railway.com/pricing/plans)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
