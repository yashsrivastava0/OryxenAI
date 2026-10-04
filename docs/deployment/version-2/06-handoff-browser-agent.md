# 06 — Handoff to the browser-control agent

**Written:** 2026-10-04, at the end of the planning session. **Reader:** an AI
agent that will drive a browser (Chrome extension / browser-control tool) while
the owner watches, to configure Supabase, Google Cloud, Render, Namecheap and
UptimeRobot for OryxenAI. This file is self-contained; read it fully, then read
the files it points to. If anything here conflicts with what you see on screen,
**stop and ask the owner** — do not improvise.

---

## 1. Who you work for and what they want

The owner (they/them) is moving the OryxenAI app off an Azure VM, which will be
reused for other projects. Requirements, in their words condensed:

- **$0 hosting.** Everything on free tiers. The model-API bill is separate.
- 2–5 users at most; the live link is mainly opened from a resume.
- It must work exactly like local: frontend → backend → database → Google
  sign-in (via Supabase) → file upload → the three agent stages → Studio preview.
- Custom domain on Namecheap. Previously live at `https://app.oryxenai.me`.
- Easy, AI-assisted setup. The owner has never deployed on a PaaS and wants
  exact steps and exact values.
- No real data to migrate (development only). Only Google login identities
  matter; they live in Supabase and are kept.
- The owner said security/privacy is not a concern for this pilot. That does
  **not** relax the secret-handling rules below, which exist to avoid
  accidental leaks, not to meet a compliance bar.

## 2. What was decided (and why you should not reopen it)

**Render Free (one Docker web service) + the existing Supabase project (Google
Auth *and* Postgres) + UptimeRobot keep-alive.** Rejected after checking vendor
docs on 2026-10-04: Hugging Face Spaces (Docker Spaces need a paid plan),
Koyeb (no free web tier), Fly.io (no free tier), Railway ($5/mo, paid
fallback), Vercel (no persistent worker), Oracle free VM (a VM again).
Full reasoning with links: `01-research-and-decision.md`. Architecture:
`README.md`.

Known differences from local on the free host: lightweight PDF reader instead
of Docling/PyTorch; no server-side Chromium check; sleeps after 15 idle minutes
unless the pinger runs. These are accepted by design; do not try to "fix" them
in a dashboard.

## 3. What has been done so far

| Item | State |
| --- | --- |
| Research and decision | Done. |
| Documentation set `docs/deployment/version-2/` (README, 01–05, this file) | Written and committed locally as `fd8b3c0` on branch `NEW`. Not pushed. |
| Any code or config change | **Not done.** |
| `render.yaml`, light PDF engine, proxy-headers fix, CI change | **Not done** (tasks C1–C8 in `02-code-and-config-changes.md`, for a *coding* agent in another session). |
| Supabase / Google / Render / Namecheap / UptimeRobot settings | **Not touched.** You have not been given any access yet. |
| Azure VM | **Not touched.** Last known state in the repo (2026-09-30): stopped (deallocated), auto-start Logic App disabled. Not verified live. |

Repository state: `C:\Users\Yash Srivastava\Desktop\01_Projects\OryxenAI`, branch
`NEW`, with many uncommitted changes from other work and one pre-existing staged
rename (`editorial_forest` template). These are not yours; never stage, commit
or revert them. You normally will not touch the repository at all.

## 4. The most important sequencing fact

The Render service **cannot start correctly until the coding tasks are merged**
to the branch Render deploys: at minimum C1 (proxy headers), C2/C3 (light PDF
engine, so the app fits 512 MB), C5 (`render.yaml`), C7 (overlay setting). Also
`staging` currently lacks the Studio preview code, so the product must be
brought to `staging` first (P0 in doc 02).

Therefore split your work into two phases and **ask the owner which phase is
unlocked**:

| Phase | Can be done now (no code needed) | Needs the code merged first |
| --- | --- | --- |
| A | Read-only inspection of all dashboards; Supabase URL Configuration; Google OAuth origins and Test users; collect (not copy) the values you will later need; UptimeRobot account; Namecheap record inventory | — |
| B | — | Render service creation, env vars, first deploy, custom domain, Namecheap CNAME swap, UptimeRobot monitor, acceptance test |

Do phase A first. Changing Supabase/Google settings early is harmless: the
added production URLs only matter once the app is live, and localhost entries
are kept so local development keeps working.

## 5. Hard rules

1. **Never ask for, accept, type or store a password, 2FA code, recovery code or
   API secret.** The owner signs in to every site themselves. If a login screen
   appears, stop and tell the owner to sign in, then continue.
2. **Secrets never travel through you.** Secrets are: Supabase database
   password and the full `DATABASE_URL`, `SUPABASE_SECRET_KEY`, the model
   `EXPLABS_API_KEY`, `PREVIEW_GRANT_SECRET`, the Google OAuth client secret.
   When one must be entered into Render, ask the owner to paste it themselves
   into the field, or (only if the owner explicitly says so for that one value)
   use a copy-paste that never appears in your output, notes or screenshots.
   Do not read secrets aloud, summarise them, put them in a screenshot, or write
   them to a file. If a secret ever appears on screen in a captured image or in
   your output, tell the owner immediately so they can rotate it.
3. **Read before write.** Before every change, record the current value of any
   non-secret setting (a short text note in your report) so it can be restored.
4. **Change only what this file lists.** No Delete, Pause, Reset, Rotate,
   Regenerate, Remove or Disable on anything not named here. No new projects, no
   billing or upgrade clicks, no adding a payment method (the owner wants a
   strict $0; a free Render service without a card is suspended rather than
   billed when a quota runs out).
5. **Do not touch the Azure VM, Azure Portal resources, GitHub branch
   protection, or the `deployment` branch.** Doc 04 (VM cleanup) is a separate,
   later, owner-supervised task, and `AGENTS.md` forbids merging to
   `deployment` without the owner's explicit instruction in that session.
6. **Never use "Add from .env"** or upload a `.env` file anywhere. Do not open or
   read the repository's `.env`.
7. **No browser dialogs.** Avoid actions that trigger `alert`/`confirm` popups;
   if one appears and blocks you, tell the owner to dismiss it.
8. **If a screen differs from this description** (menu renamed, option missing,
   unexpected prompt, error) stop, describe exactly what you see, and ask. Do not
   guess around it. Do not retry the same failing action more than twice.
9. **Do not sign in to Google as the owner to "test" for them.** The first
   sign-in test is done by the owner in their own browser window.

## 6. Values you will need

| Name | Value | Source of truth |
| --- | --- | --- |
| App origin | `https://app.oryxenai.me` | Repo history (`docs/deployment/deployment-status-and-history.md`). The owner's message said "apporigin.me"; **confirm the domain with the owner before Phase A** and substitute throughout if it differs. |
| Supabase project | name `oxygen-ai-development`, ref `diiestlnmpaarhhexwhi` | `docs/Auth/09-confirmed-setup.md`; verify in the dashboard header. If the name/ref differs, stop. |
| Supabase URL | `https://diiestlnmpaarhhexwhi.supabase.co` | derived |
| Google Cloud project / OAuth client | `Oxygen.ai` / `Oxygen.ai Development` (web client) | same doc; verify |
| Google "authorized redirect URI" (must stay exactly this) | `https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback` | Supabase Google provider page |
| Render service name / region / plan | `oryxenai` / Singapore / Free | doc 02 C5 |
| Health path | `/health/ready` | `src/oryxenai/api/routes/health.py` |
| Start command | `python -m oryxenai.deployment.render_web` | `render_web.py` |
| Overlay | `config/app.render-free.toml` (env `OryxenAI_CONFIG_OVERLAY`, exact case) | repo |
| DNS host / registrar | Namecheap, BasicDNS, domain `oryxenai.me` | repo history |
| Old DNS targets to remove | `app` and `preview` A records → `20.235.74.81` (verify; may have changed) | repo history |

## 7. Phase A — tasks (do in this order)

Full click-paths are in `03-manual-setup-checklist.md`; below is the contract.

### A1. Confirm with the owner
- Domain is `oryxenai.me` and the hostname is `app.oryxenai.me`.
- Which Google accounts will sign in: **exactly two admin emails** and the
  normal-user emails (the app requires exactly two admins, up to 15 normal
  users). You need these only as a list for the Google "Test users" step; you
  do not need passwords.
- Whether the code work (doc 02) has been merged, to decide whether Phase B is
  unlocked.

### A2. Supabase (owner signs in)
Dashboard: `https://supabase.com/dashboard/project/diiestlnmpaarhhexwhi`

1. Read and report: project name/ref; Google provider enabled (do **not** open
   or reveal the client secret); current **Site URL**; current **Redirect URLs**.
2. **Authentication → URL Configuration** set:
   - Site URL: `https://app.oryxenai.me`
   - Redirect URLs, exactly three, no wildcards:
     `https://app.oryxenai.me/auth/callback`,
     `http://localhost:8000/auth/callback`,
     `http://127.0.0.1:8000/auth/callback`
3. Save. Re-open the page and confirm the saved values.
4. **Connect → Session pooler (port 5432):** *look* at it to confirm that the
   option exists and the port is 5432, but do not copy or record the password
   or full URI. The owner will paste it into Render themselves in Phase B. Never
   use the Transaction pooler (6543).
5. **SQL Editor (read-only):** run
   `select tablename from pg_tables where schemaname='public' order by 1;`
   and `select pg_size_pretty(pg_database_size(current_database()));`.
   Report whether OryxenAI tables already exist and the DB size. Run no write
   statements.

### A3. Google Cloud (owner signs in)
Console: `https://console.cloud.google.com/auth/clients` → project `Oxygen.ai`
→ web client `Oxygen.ai Development`.

1. Record the current **Authorized JavaScript origins** and **Authorized
   redirect URIs**.
2. Add JavaScript origin `https://app.oryxenai.me` (scheme + host only; no
   path; no trailing slash). Keep the existing localhost origins.
3. Confirm the redirect URI list contains
   `https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback`. Do not add the
   app URL there. Do not reveal the client secret.
4. Save. (Google may take minutes to apply it.)
5. Audience / consent screen: leave **External** + **Testing**. Under **Test
   users** add each login email from A1 (admins and normal users). Do not
   publish the app.

### A4. Namecheap inventory (owner signs in; read-only in phase A)
`Domain List → oryxenai.me → Manage → Advanced DNS`. Confirm the nameservers are
Namecheap BasicDNS. Record every existing host record verbatim (especially
`app` and `preview`). Change nothing yet.

### A5. UptimeRobot account (optional now)
Owner creates a free account at `https://uptimerobot.com/`. Do not add the
monitor until the service is live.

**Report after Phase A:** the before/after table for Supabase and Google, the
Namecheap record list, DB state, and any surprise.

## 8. Phase B — tasks (only after the owner says the code is merged)

### B1. Render account and service
Dashboard `https://dashboard.render.com/`; owner signs in with GitHub.
Keep the workspace on the free **Hobby** plan; **add no payment method**.

Create the service either from the Blueprint (`New → Blueprint`, repository,
the branch the owner names — doc 02 expects `deployment`; read `render.yaml`)
or manually: `New → Web Service → Docker`; repo root; Dockerfile `./Dockerfile`;
Docker command `python -m oryxenai.deployment.render_web`; Region
**Singapore**; Instance type **Free**; Health check path `/health/ready`;
Auto-deploy **Off**.

Environment variables (12 keys; exact names):

| Key | Value | Who enters it |
| --- | --- | --- |
| `OryxenAI_CONFIG_OVERLAY` | `config/app.render-free.toml` | you |
| `ORYXENAI_AUTH_PRIMARY_ORIGIN` | `https://app.oryxenai.me` | you |
| `ORYXENAI_AUTH_ALLOWED_ORIGINS` | `https://app.oryxenai.me` | you |
| `SUPABASE_URL` | `https://diiestlnmpaarhhexwhi.supabase.co` | you |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase → Project Settings → API Keys (publishable) | owner pastes |
| `SUPABASE_SECRET_KEY` | same page (secret) | owner pastes |
| `DATABASE_URL` | Session-pooler URI (port 5432) with the password URL-encoded and `?sslmode=require` | owner pastes |
| `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` | exactly two admin emails, comma-separated | owner confirms/types |
| `ORYXENAI_ALLOWED_USER_EMAILS` | normal-user emails, comma-separated, at least one | owner confirms/types |
| `EXPLABS_BASE_URL` | model endpoint from `.env.example` (confirm with owner) | you / owner |
| `EXPLABS_API_KEY` | model provider key | owner pastes |
| `PREVIEW_GRANT_SECRET` | auto-generated by the Blueprint, or owner-generated 32+ chars | Render / owner |

**Never set** `PORT`, `POSTGRES_PASSWORD`, `DB_HOST_OVERRIDE`,
`DB_PORT_OVERRIDE`, `APP_HOST`, `R2_*`, `VITE_*`, or unused provider keys.

Watch **Logs** during the first build/deploy. Success = Alembic upgrades to head,
uvicorn listens, the worker starts, no Python traceback. Then verify
`https://<service>.onrender.com/health/ready` → HTTP 200 and
`{"status":"ready","database":"up"}`. Sign-in is *not expected* to work on the
`onrender.com` hostname (the app only accepts the `app.oryxenai.me` origin).

### B2. Custom domain and DNS
1. Render → service → Settings → Custom Domains → add `app.oryxenai.me`; note
   the target hostname it shows.
2. Namecheap Advanced DNS: first record the old `app` / `preview` A records, then
   delete them, then add `CNAME  app  →  <render target>` (TTL Automatic). Do
   not touch MX, TXT or other records. `preview.oryxenai.me` is no longer used.
3. In Render, Verify; wait for the certificate to become active. Check
   `https://app.oryxenai.me/health/ready` → 200.

### B3. UptimeRobot
HTTP(s) monitor on `https://app.oryxenai.me/health/ready`, 5-minute interval,
alerts to the owner's email. Use `/health/ready` (database activity also stops
Supabase Free pausing), not `/health/live`.

### B4. First sign-in — owner does this
Owner opens `https://app.oryxenai.me/sign-in` and signs in with an admin Google
account, completes onboarding, reaches `/app` and `/admin`. You may observe
(read page state, console, network status codes) but do not enter credentials.

### B5. Acceptance
Follow `05-acceptance-and-troubleshooting.md` §A. You can read page states and
logs; the owner performs uploads and clicks that involve their identity or the
model API (which costs money). Record each item pass/fail with evidence
(status code, visible text) but never secrets.

### B6. Turn on auto-deploy — only on the owner's word
Render → Settings → Build & Deploy → Auto-Deploy → **After CI Checks Pass**, on
the branch the owner names. Do not do this automatically.

## 9. Things that look wrong but are expected

- Sign-in on `*.onrender.com` fails or POSTs return 403 `ORIGIN_NOT_ALLOWED`:
  expected; only `app.oryxenai.me` is allowed.
- Google's redirect URI is the **Supabase** URL, not the app URL. The flow is
  Google → Supabase → `https://app.oryxenai.me/auth/callback`.
- Supabase silently falls back to the Site URL if a redirect URL is not in the
  list — an "unexpected landing page" usually means a missing/typoed entry.
- A Google account not in **Test users** is blocked even if it is on the app
  allowlist.
- A freshly woken free Render service takes about a minute to respond.
- After deploy, the version receipt shows no headless-browser result:
  `browser = "off"` by design.
- Render free instance hours: one always-on service uses ~744 of 750 hours;
  that is why exactly one service is created.

## 10. If something fails

Use the symptom table in `05-acceptance-and-troubleshooting.md` §B. The most
likely first-day failures:

1. Out-of-memory restart loop → the code work (light PDF engine) is missing or
   the overlay was not applied (`OryxenAI_CONFIG_OVERLAY` spelling).
2. Start-up crash naming auth validation → admin email count is not exactly two,
   allowlist empty, more than one origin, or a localhost origin in production.
3. `/health/ready` 503 → wrong `DATABASE_URL` (must be Session pooler, port 5432,
   URL-encoded password, `sslmode=require`) or Supabase project paused.
4. Everyone rate-limited (HTTP 429) → proxy-headers fix (C1) missing.

## 11. Reporting format

At the end of each phase give the owner a short report:

- **Done:** each setting, `before → after`, with the page name.
- **Verified:** the check you ran and its observed result.
- **Not done / blocked:** and why.
- **Needs the owner:** anything requiring their login, a secret, or a decision.
- **Surprises:** anything that differed from this file.

No secrets, no full connection strings, no key fragments in the report.

## 12. Out of scope for you

Code changes (doc 02), Azure VM cleanup (doc 04), `AGENTS.md`/`DECISIONS.md`
edits, git commits/pushes, branch protection, spending money, and any change to
the model provider account.

## 13. Reference index

| File | Use |
| --- | --- |
| `README.md` | Decision, architecture, trade-offs |
| `01-research-and-decision.md` | Why this host, sources |
| `02-code-and-config-changes.md` | Coding agent's task list; env-var table and the four-places-for-the-origin list |
| `03-manual-setup-checklist.md` | Detailed click-path for every dashboard (your main manual) |
| `04-azure-vm-cleanup.md` | Later, owner-supervised |
| `05-acceptance-and-troubleshooting.md` | Test script, failure table, weekly backup |
| `deployment-strategy.md` | Paid Railway fallback only; not verified |
| `docs/Auth/09-confirmed-setup.md` | Recorded Supabase/Google setup (localhost-only as of recording) |
| `AGENTS.md` | Repo rules for coding agents (branches, no deploy without sign-off) |
