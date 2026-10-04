# Deployment v2 — leave the Azure VM, run free on Render + Supabase

**Research date:** 2026-10-04 · **Status:** plan and runbooks only. No cloud
service, DNS record, dashboard setting, branch or code was changed by writing
these documents. Everything in `02-code-and-config-changes.md` is still to be
done in a later session.

## The decision in one paragraph

Run OryxenAI as **one Docker web service on Render's Free plan**, with the
**existing Supabase project** providing both Google sign-in and the PostgreSQL
database, reached at **`https://app.oryxenai.me`** through a free external
uptime pinger that keeps the service awake. Hosting cost is $0. The model API
(Experiential Labs) is billed separately and is unchanged.

This is a deliberate trade: a free host has 512 MB of RAM and 0.1 CPU, which
cannot hold the Docling/PyTorch PDF engine or a headless Chromium. Two things
therefore differ from your local machine (see "What is different from local").

## Architecture

```text
Visitor / you
   │  https://app.oryxenai.me  (Namecheap CNAME → Render, free TLS)
   ▼
┌──────────────── Render Free Web Service (Docker, Singapore) ───────────────┐
│ python -m oryxenai.deployment.render_web                                   │
│   1. alembic upgrade head                                                  │
│   2. uvicorn  oryxenai.main:app   (API + Preact UI + /preview/g/...)       │
│   3. python -m oryxenai.jobs.worker  (durable PostgreSQL job queue)        │
└───────────────┬───────────────────────────────┬────────────────────────────┘
                │ DATABASE_URL                  │ HTTPS
                │ (Session pooler, :5432)       ▼
                ▼                         Experiential Labs model API
   ┌────────── Supabase project ───────────┐
   │ Postgres (app tables, jobs, versions) │◄── Browser signs in with Google
   │ Auth (Google provider, JWKS)          │    through supabase-js (PKCE)
   └───────────────────────────────────────┘

UptimeRobot (free) ──GET /health/ready every 5 min──► keeps Render awake and
                                                      keeps Supabase active
```

Why this is enough: the frontend is built into the Docker image and served by
FastAPI; Studio previews are stored in Postgres and served from the same
origin; sign-in is client-side Supabase (no cookies, no CORS); there is no
Redis, Celery, object store, preview host or Caddy to run.

## What is different from local (read this)

| Area | Local | Free deployment | Effect |
| --- | --- | --- | --- |
| PDF reading | Docling layout + OCR (PyTorch) | Lightweight engine (`pdf_engine = "light"`) | Text PDFs work. Heading/table structure is simpler. Scanned PDFs are best-effort OCR and must be measured on the real instance. |
| Server-side Chromium check of generated pages | optional | off (`browser = "off"`) | Your browser still renders the Studio preview; no headless-browser receipt is produced. |
| Cold start | none | ~1 min if the pinger stops | The pinger removes this in normal use. |
| Backups | your disk | Supabase Free has none | Weekly manual `pg_dump` (see 05). |

Everything else — Discovery, Content Architect, Studio, chat edits, versions,
signed previews, allowlist admission, admin page — runs the same code.

**Escalation if free is not good enough** (one setting each, no re-architecture):
Render Standard (2 GB) with `PDF_ENGINE=full` restores Docling; Railway
(`deployment-strategy.md`) is the other paid option; an Oracle Cloud Always
Free VM is free but is a VM again.

## Reading order

| # | File | For | What it contains |
| --- | --- | --- | --- |
| 1 | `01-research-and-decision.md` | you | Why Render, what was rejected, sources |
| 2 | `02-code-and-config-changes.md` | an AI coding agent | Exact code and config work list, in order, with acceptance checks |
| 3 | `03-manual-setup-checklist.md` | you or a browser-control AI | Supabase, Google Cloud, Render, Namecheap, UptimeRobot click-paths and exact values |
| 4 | `05-acceptance-and-troubleshooting.md` | you / agent | End-to-end test script, failure table, weekly care |
| 5 | `04-azure-vm-cleanup.md` | you | Freeing the VM — only after step 4 passes |

`deployment-strategy.md` (Railway, paid) is kept only as the paid fallback.
`free-tier-migration-guide.md` is now a pointer to this folder.

## Who does what

| Task | Owner |
| --- | --- |
| Code and repo config changes (doc 02) | AI coding agent, in a separate session |
| Dashboard work (doc 03) | You, or a browser-control AI you supervise. Do the Google sign-in yourself; never give an AI your Google password. |
| Secrets (API keys, DB password) | Paste directly from the provider screen into Render's field. Never into chat, git, docs or logs. |
| Production promotion | You. AGENTS.md: no merge to `deployment` without your explicit approval in the session. |

## Open items to confirm

1. **Domain.** Your message wrote "apporigin.me"; the repository's deployment
   history shows `oryxenai.me` on Namecheap with `app.oryxenai.me` as the live
   hostname. These documents use `app.oryxenai.me`. If the domain differs,
   replace it everywhere (search for `oryxenai.me`).
2. **Live dashboards were not inspected.** The repo only records the Supabase
   Auth setup as localhost-only (`docs/Auth/09-confirmed-setup.md`). Doc 03
   starts every section with "read the current value first".
3. **Azure VM state** (running or deallocated, anything on it you still want)
   is unknown from the repo and is checked in doc 04.
