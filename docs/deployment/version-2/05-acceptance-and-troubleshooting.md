# 05 — Acceptance test, troubleshooting and weekly care

Run this against `https://app.oryxenai.me` after doc 02 (code) and doc 03
(dashboards). A green health check alone proves nothing about agents or
previews. Use a test owner and disposable sessions. Live model calls bill the
model provider.

## A. Acceptance script

Tick each item; stop at the first failure and use section B.

### Platform and database

- [ ] `https://app.oryxenai.me/health/live` returns 200 and
      `/health/ready` returns 200 with `database: up`.
- [ ] Render logs for the latest deploy show Alembic reaching head, uvicorn
      listening, and the worker starting; no Python traceback.
- [ ] Browser: `/sign-in` loads over HTTPS with a valid certificate.
- [ ] In Supabase SQL Editor: `select count(*) from public.app_users;` works and
      `select status, count(*) from public.background_jobs group by 1;` returns
      rows or an empty set without error.

### Authentication and admission

- [ ] An allowlisted **admin** signs in with Google, lands on onboarding and
      then `/app`; `/admin` opens.
- [ ] An allowlisted **normal user** (separate browser profile) signs in and
      reaches `/app`; `/admin` is refused.
- [ ] A Google account that is not allowlisted is refused by the app (and, while
      the consent screen is in Testing, by Google if it is not a test user).
- [ ] Signing out and reloading shows the sign-in page; an expired/invalid token
      is rejected (do not bypass auth to test).

### The three stages

- [ ] Create a session, refresh the browser: the session is still there.
- [ ] Upload a small **text PDF** (and a `.md`/`.txt`): the editable transcript
      preview appears; the warning about simplified layout is shown for PDFs.
- [ ] Upload a small **scanned PDF**: the Free overlay reports that it has no
      selectable text and asks for a text-based PDF or pasted text. The service
      remains ready.
- [ ] Negative uploads: password-protected PDF, empty file, more than the page
      limit, wrong extension → each shows a visible safe error.
- [ ] Start **Discovery** explicitly; the durable job completes; a brief appears;
      approve it.
- [ ] Start **Content Architect** explicitly; review and approve the plan.
- [ ] Start **Studio** build (or "Approve & generate my portfolio"). A version
      is created, the page renders in the Studio iframe with its theme styling,
      and a signed preview opens from the same origin. A failed build must not
      replace the live page.
- [ ] Send a content change in the Studio chat; a new version appears; refresh
      and confirm the page persists; restore an earlier version.
- [ ] Note: with `browser = "off"` there is no headless-browser receipt on the
      version. That is expected on the free deployment.

### Sleep, restart and queue durability

- [ ] Stop touching the app for 20 minutes with the UptimeRobot monitor running:
      the service is still up (no cold start) in Render's metrics.
- [ ] Pause the monitor, wait 20+ minutes, load the app: it wakes (about a
      minute) and the earlier session is intact. Re-enable the monitor.
- [ ] Redeploy once from the Render dashboard while a job is queued: the job is
      still processed after restart (queue is in PostgreSQL).
- [ ] Open the app from a different network/phone to confirm the public URL.

### Cost and quotas

- [ ] Render → Billing → included usage: instance hours near 744 per month, no
      payment method attached (if you want a strict $0).
- [ ] Supabase → Reports/Database: size well under 500 MB.

## B. Troubleshooting

| Symptom | Check in this order |
| --- | --- |
| Build fails | Render build log; Dockerfile path; `uv.lock` committed and matching `pyproject.toml`; build minutes left; the light image builds in CI first. |
| Service restarts in a loop / "Out of memory" | Render metrics. Confirm `pdf_engine = "light"`, `browser = "off"`, pool 1+1, worker concurrency 1. Re-run the C3 memory measurement. Set `light_ocr = false` if OCR is the trigger. |
| Start-up crash at import | Log line from `validate_auth_configuration`: missing Supabase key, not exactly two admin emails, empty allowlist, more than one origin, or a localhost origin in production. |
| `/health/ready` 503 | `DATABASE_URL`: Session pooler (5432), password URL-encoded, `sslmode=require`; Supabase project not paused (resume it in the dashboard); Alembic error earlier in the log. |
| `prepared statement … already exists` or worker lock errors | You used the Transaction pooler (6543). Switch to the Session pooler or the direct connection. |
| Sign-in loops or "redirect" error | Supabase Site URL and redirect list contain `https://app.oryxenai.me/auth/callback` exactly; Google JS origin added; env origins have no trailing slash. A redirect not in the list silently falls back to the Site URL. |
| Sign-in returns 403 `ORIGIN_NOT_ALLOWED` on POST | The page origin differs from `ORYXENAI_AUTH_ALLOWED_ORIGINS` (for example you are on the `onrender.com` hostname). Use `app.oryxenai.me`. |
| Google "access blocked" | Account missing from Test users, or the consent screen is not in Testing. |
| Signed in but "not allowed" | Email missing from `ORYXENAI_ALLOWED_USER_EMAILS` / admin list; admission mode is `allowlist` in the overlay. |
| Everyone gets 429 | Check the Render overlay's `trusted_client_ip_header` and confirm Render supplies distinct valid `CF-Connecting-IP` values. The middleware ignores a caller-supplied `X-Forwarded-For` prefix. |
| Jobs stay queued | The service was asleep (pinger down) or the worker child exited; check logs for the worker line and `service_heartbeats`. Same database for API and worker (they share one container, so check `DATABASE_URL`). |
| Studio preview blank / "grant expired" | `PREVIEW_GRANT_SECRET` set and stable; grant lifetime is 30 minutes — reopen from Studio; browser console for CSP errors; the version row exists in `portfolio_site_versions`. |
| PDF returns "not ready on this server" | Engine is `docling` but Docling is not installed (overlay not applied: check `OryxenAI_CONFIG_OVERLAY`). |
| Domain shows certificate error | Render domain not verified yet; CNAME value copied wrongly; leftover A record for `app`. |
| Supabase paused | Resume in the dashboard; check the pinger hits `/health/ready`, not `/health/live`. |

## C. Weekly care (10 minutes)

1. Render → Billing: instance hours and any suspension notice.
2. UptimeRobot: any downtime in the last week.
3. Supabase: database size, project active.
4. **Backup** (Supabase Free has none). From your machine with PostgreSQL client
   tools, using the Session pooler URI in a *local* environment variable (never
   committed):
   ```powershell
   pg_dump --format=custom --no-owner --no-acl --schema=public `
     --dbname="$env:SUPABASE_SESSION_POOLER_URL" `
     --file="$env:LOCALAPPDATA\OryxenAI\backups\oryxenai-$(Get-Date -Format yyyyMMdd).dump"
   pg_restore --list "$env:LOCALAPPDATA\OryxenAI\backups\oryxenai-$(Get-Date -Format yyyyMMdd).dump" | Select-Object -First 5
   ```
   Dump only `public`; never dump or restore Supabase's `auth` schema.
5. Model provider balance (separate from hosting).

## D. If free is not enough

| Symptom | Smallest upgrade |
| --- | --- |
| OOM even with `light_ocr = false`, or you want Docling quality and Chromium verification | Render Standard (2 GB RAM, 1 CPU): change plan, build with `PDF_ENGINE=full`, set `pdf_engine = "docling"` and `browser = "best_effort"` (needs the Chromium image build argument as documented in the Dockerfile). Cost is monthly; see Render pricing. |
| You want always-on without a pinger and a separate worker | Railway Hobby (`deployment-strategy.md`). |
| You want everything identical to local and still free | Oracle Cloud Always Free VM (2 OCPU / 12 GB): runs the original Docker image, but it is a VM again. |
