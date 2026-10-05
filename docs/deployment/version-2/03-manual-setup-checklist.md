# 03 — Manual setup checklist (dashboards)

**Audience:** you, or a browser-control AI you supervise. **Do this after** the
code work in `02-code-and-config-changes.md` is merged to the branch Render will
deploy (at minimum tasks C1, C2, C3, C5, C7), because the service will not
start correctly without them.

## Rules for any AI helping with the browser

- Open each dashboard yourself and sign in yourself. The AI must never be given
  a Google, Supabase, Render, Namecheap or GitHub password, a 2FA code or a
  recovery code.
- Secret values (database password, Supabase secret key, model API key,
  preview secret) are copied straight from the provider's screen into Render's
  value field. They must not be pasted into chat, a file, a screenshot, a
  commit or a log. If a secret appears in a screenshot, rotate it.
- Before changing any setting, read the current value and write it down
  (non-secret ones) so it can be restored.
- Change only what is listed. If a screen differs from this description, stop
  and ask; vendors rename menus.
- Do not click Delete, Pause, Reset password, Rotate or Remove on anything not
  named below.

## Values used below

| Name | Value |
| --- | --- |
| App origin | `https://app.oryxenai.me` (see the domain note in `README.md`) |
| Supabase project | `oxygen-ai-development`, ref `diiestlnmpaarhhexwhi` (confirm in the dashboard) |
| Google Cloud project / client | `OryxenAI` / `Oxygen.ai Development` (confirm) |
| Render service name | `oryxenai` |
| Region | Singapore |

---

## Step 1 — Supabase

Dashboard: <https://supabase.com/dashboard/project/diiestlnmpaarhhexwhi>

1. Confirm the project name/ref in the header. If it differs, stop.
2. **Authentication → Sign In / Providers → Google**: confirm it is enabled and
   a Client ID/Secret are saved. Do not change them.
3. **Authentication → URL Configuration**
   - Note the current Site URL and Redirect URLs.
   - **Site URL:** `https://app.oryxenai.me`
   - **Redirect URLs:** make the list exactly these three
     (add the first, keep the two localhost ones for local development):
     - `https://app.oryxenai.me/auth/callback`
     - `http://localhost:8000/auth/callback`
     - `http://127.0.0.1:8000/auth/callback`
   - No wildcards. Save.
4. **Project Settings → API Keys:** note where the *publishable* key and the
   *secret* key are. You will copy them in Step 4.
5. Click **Connect** (top bar) → choose **Session pooler** (port **5432**).
   Keep this screen for Step 4. Do **not** use "Transaction pooler" (6543):
   it breaks prepared statements and the worker's advisory lock.
   Replace `[YOUR-PASSWORD]` with the database password, URL-encoding any
   special characters (`a@b` becomes `a%40b`), and keep `sslmode=require`.
   The complete URI has only one literal `@`, between credentials and host.
   If you do not know the password, resetting it is a decision for you, not
   the AI: it affects every other user of that database password.
6. **SQL Editor (read-only check):**
   ```sql
   select pg_size_pretty(pg_database_size(current_database()));
   select tablename from pg_tables where schemaname = 'public' order by 1;
   ```
   Expect no OryxenAI tables (fresh start). If OryxenAI tables already exist
   from earlier trials, tell the AI/agent before first deploy: Alembic will
   upgrade them in place and old rows will remain.

## Step 2 — Google Cloud

Console: <https://console.cloud.google.com/auth/clients> (project `OryxenAI`).

1. Open web client **Oxygen.ai Development**.
2. **Authorized JavaScript origins:** keep the two localhost entries, add
   `https://app.oryxenai.me`. Scheme and host only — no path, no trailing slash.
3. **Authorized redirect URIs:** must contain exactly
   `https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback`. Do not add the
   app URL here.
4. Save (Google can take several minutes to apply changes).
5. **Audience / OAuth consent screen:** leave *External* + *Testing*. Under
   **Test users** add every Google account that will sign in: the two admins and
   each normal user. While in Testing, a Google account that is not listed
   cannot sign in even if it is on the app allowlist.

## Step 3 — Render: create the service

Dashboard: <https://dashboard.render.com/>

1. Sign up / sign in with GitHub. Keep the workspace on the **Hobby** (free)
   plan and **do not add a payment method** if you want a hard $0 (a service
   that exhausts a free quota is then suspended instead of billed).
2. In the existing `OryxenAI` Hobby workspace and `Origin AI` project, choose
   **New → Blueprint**, pick repository `yashsrivastava0/OryxenAI`, branch
   `deployment`, and let it read `render.yaml`. Alternative
   without the Blueprint: **New → Web Service → Docker**, Region **Singapore**,
   Instance type **Free**, Dockerfile `./Dockerfile`, Docker command
   `python -m oryxenai.deployment.render_web`, Health check path
   `/health/ready`, Auto-deploy **After CI Checks Pass**.
3. When the Blueprint asks for the `sync: false` values, or in **Environment**
   after creation, enter every variable from the table in doc 02
   ("Render environment variables"). Sources:
   - `DATABASE_URL`: the Session pooler URI from Step 1.5 (secret).
   - `SUPABASE_URL`: `https://diiestlnmpaarhhexwhi.supabase.co`.
   - `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`: Supabase → Project
     Settings → API Keys.
   - `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS`: exactly two emails, comma-separated.
   - `ORYXENAI_ALLOWED_USER_EMAILS`: the other emails allowed to sign up.
   - `EXPLABS_BASE_URL` / `EXPLABS_API_KEY`: from your model provider.
   - `PREVIEW_GRANT_SECRET`: generated by the Blueprint, or create one locally
     with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   - Do **not** use "Add from .env" and do **not** add `PORT`.
4. Create the service and watch **Logs**. A successful start shows, in order:
   Alembic upgrading to head, uvicorn listening, the worker starting. The first
   build takes several minutes.
5. Open `https://<service>.onrender.com/health/ready`. Expect HTTP 200 and
   `{"status":"ready","database":"up"}`. (Sign-in is *not* expected to work on
   this hostname yet: the app only accepts the `app.oryxenai.me` origin.)

## Step 4 — Domain and DNS

1. Render → the service → **Settings → Custom Domains → Add**
   `app.oryxenai.me`. Render shows the target hostname (a `*.onrender.com` name).
2. Namecheap → **Domain List → oryxenai.me → Manage → Advanced DNS** (DNS must be
   Namecheap BasicDNS/Namecheap nameservers):
   - Replace only the old `app` A record (to the Azure VM IP). Write down its
     value first. Leave the apex and mail records alone.
   - Add **CNAME Record**: Host `app`, Value = the Render target, TTL Automatic.
3. Back in Render, click **Verify**. Wait until the domain shows verified and
   the certificate is issued (minutes, occasionally longer while DNS
   propagates). Render redirects HTTP to HTTPS by itself.
4. Check `https://app.oryxenai.me/health/ready` returns 200.

## Step 5 — Keep it awake (UptimeRobot)

A free Render service stops after 15 idle minutes, which also stops the worker.

1. Create a free account at <https://uptimerobot.com/>.
2. **Add New Monitor:** type *HTTP(s)*, URL
   `https://app.oryxenai.me/health/ready`, interval **5 minutes** (the free
   plan minimum; confirm in their UI), alert contact = your email.
3. Using `/health/ready` (not `/health/live`) is intentional: it queries the
   database, which also counts as activity so Supabase Free does not pause the
   project after a week of low use.
4. Alternative if you prefer not to use a third party: a scheduled GitHub
   Actions workflow with `curl` every 5 minutes works but is not guaranteed to
   run on time; UptimeRobot is more dependable.

## Step 6 — First sign-in (you, not the AI)

1. Open `https://app.oryxenai.me/sign-in` in a normal browser window.
2. Sign in with an **admin** Google account from the allowlist.
3. Complete onboarding, reach `/app`, open `/admin` (admins only).
4. Sign in with a normal-user account in another browser profile.
5. Continue with `05-acceptance-and-troubleshooting.md`.

## Step 7 — Confirm automatic releases

Render → service → **Settings → Build & Deploy → Auto-Deploy** must show
**After CI Checks Pass**, branch `deployment`. A later fast-forward push of a
CI-passing `staging` SHA to `deployment` is the release action; no PR review or
dashboard deploy click is needed. See `../ci-cd-runbook.md`.

## Quick verification table

| Check | Where | Expected |
| --- | --- | --- |
| Supabase Site URL | Auth → URL Configuration | `https://app.oryxenai.me` |
| Supabase redirect list | same | 3 entries, exact |
| Google JS origins | OAuth client | localhost ×2 + `https://app.oryxenai.me` |
| Google redirect URI | OAuth client | only the Supabase `/auth/v1/callback` |
| Google test users | Audience | all login emails |
| Render env | Environment | 12 keys from doc 02, no `PORT` |
| Render health | `/health/ready` | 200, `database: up` |
| DNS | Namecheap | `CNAME app → onrender`, no A records for `app`/`preview` |
| Pinger | UptimeRobot | monitor up, 5-minute interval |
