# 01 — Research and decision

**Checked:** 2026-10-04. Vendor pricing and limits change; re-open the linked
page before acting on any number. Earlier documents in `docs/deployment/` and
the previous contents of this folder were treated as claims to verify, not as
facts; everything below was re-derived from the repository and vendor pages.

## Requirements (from the owner)

- $0 hosting. Model API cost is separate and out of scope.
- 2–5 users; mainly someone opening the live link from a resume.
- Everything must work: UI → API → worker → database → Supabase Google
  sign-in → file upload → Studio preview.
- Custom domain on Namecheap; previously `app.oryxenai.me`.
- Easy, AI-assisted deployment; not another hand-managed VM.
- No data worth migrating (development only); Google identities live in
  Supabase and are kept.

## What the application needs from a host (verified in the repo)

| Need | Evidence |
| --- | --- |
| One web process on `$PORT`, health at `/health/ready` | `Dockerfile:126`, `src/oryxenai/api/routes/health.py` |
| A **continuously running** worker (PostgreSQL queue, `SKIP LOCKED`, jobs up to 600–900 s) | `src/oryxenai/jobs/worker.py`, `config/app.toml` `kind_timeouts` |
| Can share a container with the API | `src/oryxenai/deployment/render_web.py` (already written; runs alembic, uvicorn, worker) |
| PostgreSQL reachable through **session** pooling | prepared statements (asyncpg) and a session advisory lock in `src/oryxenai/agents/shared/model_quota.py:270,431` |
| Frontend served by FastAPI, no Node at runtime | `Dockerfile` stage 0; `src/oryxenai/web/routes.py` |
| Same-origin signed previews, bundles in Postgres | `src/oryxenai/agents/code_generator/serving.py`, `portfolio_site_versions` |
| Supabase Google sign-in, client-side PKCE, no cookies | `src/oryxenai/auth/static/auth-controller.mjs`, `src/oryxenai/auth/jwt.py` (JWKS, no JWT secret) |
| Exactly one HTTPS origin in production | `src/oryxenai/core/settings.py:452-457` |
| No Redis, object store, preview host | `[artifact_storage]`/`[archive_storage]` overridden to `local_fs` in the overlay |
| PDF extraction is the heavy part | `document_extract.py` imports Docling/PyTorch at module top; `docs/deployment/document-extraction.md` asks for 2 vCPU / 4 GiB |

## Options evaluated

| Option | $0? | Fits the app? | Verdict |
| --- | --- | --- | --- |
| **Render Free web service** | Yes | Docker, one service, free TLS, custom domain. 0.1 CPU, 512 MB, sleeps after 15 min idle, 750 instance-hours/month, no free background worker (so the worker runs inside the web service). | **Chosen.** |
| Hugging Face Spaces | Free CPU hardware is 2 vCPU / 16 GB, but *Docker Spaces require a paid plan to create*. | Would fit technically. | Rejected: not actually free. |
| Koyeb | The pricing page no longer lists a free web service. | — | Rejected. |
| Railway | Free plan has no included credit (a trial grants a one-time $5); Hobby is $5/month plus usage. | Fits well (web + worker + Postgres in one project). | Paid fallback; see `deployment-strategy.md`. |
| Fly.io | No free tier for new organisations. | Fits. | Rejected for $0. |
| Vercel | Free hobby plan. | Serverless functions; no persistent worker; function time limits below the app's 600–900 s jobs. | Rejected. |
| Google Cloud Run | Free monthly quota exists, but CPU is throttled between requests unless always-on billing is chosen. | A background worker cannot be relied on. Needs a billing account and card. | Rejected: not simple, not reliably free. |
| Oracle Cloud Always Free VM | Free; the Ampere allowance was cut to 2 OCPU / 12 GB in 2026; "out of host capacity" errors are common. | Full fidelity (Docling and Chromium fit). | **Fallback only**: it is a VM again. |
| Stay on Azure | Student credit may cover it. | Works today. | The VM is being repurposed. |

## Why Render Free works here, and what it costs you

- **One service is enough** because `render_web.py` supervises uvicorn and the
  worker in one container and applies migrations first.
- **Database = Supabase Free Postgres.** Render's free Postgres expires after
  30 days. Supabase is already in the stack for sign-in, so it adds no new
  vendor. Use the **Session pooler** (port 5432); the Transaction pooler
  (6543) does not support prepared statements.
- **Sleep:** a free Render service stops after 15 minutes without inbound
  requests, and a stopped service cannot run the worker. An external pinger
  every 5 minutes keeps it up. One always-on service uses about 744 of the
  750 free instance-hours in a 31-day month. The same pings are database
  activity, so the free Supabase project is not paused for inactivity.
- **Memory:** API + worker + Python libraries must fit in 512 MB, so the
  PyTorch-based PDF engine and Chromium are out. See doc 02, tasks C2–C3, for
  the replacement and the measurement gate that decides whether scanned-PDF OCR
  can stay.
- **No staging environment** for free; use the same service with manual deploy
  until acceptance passes.

## Cost summary

| Item | Cost |
| --- | --- |
| Render Free web service, TLS, custom domain | $0 |
| Supabase Free (Auth + Postgres, 500 MB) | $0 |
| UptimeRobot free monitor | $0 |
| Namecheap domain | already owned; renewals are separate |
| Model API | unchanged, billed by the provider |
| Overage risk | Render bills overages only if a payment method is attached. Keep none attached for a strict $0, accepting suspension if a quota runs out. |

## Sources

- Render free tier: <https://render.com/docs/free>
- Render compute plans: <https://render.com/docs/compute-plans>
- Render custom domains: <https://render.com/docs/custom-domains>
- Render Blueprint spec: <https://render.com/docs/blueprint-spec>
- Render deploys: <https://render.com/docs/deploys>
- Supabase connection methods: <https://supabase.com/docs/guides/database/connecting-to-postgres>
- Supabase redirect URLs: <https://supabase.com/docs/guides/auth/redirect-urls>
- Supabase free project pausing: <https://supabase.com/docs/guides/platform/free-project-pausing>
- Hugging Face Spaces overview: <https://huggingface.co/docs/hub/spaces-overview>
- Railway plans: <https://docs.railway.com/pricing/plans>
- Fly.io pricing: <https://fly.io/docs/about/pricing/>
- Koyeb pricing: <https://www.koyeb.com/pricing>
