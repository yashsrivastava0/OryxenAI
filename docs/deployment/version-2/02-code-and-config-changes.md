# 02 — Code and configuration changes (agent work list)

**Audience:** an AI coding agent in a fresh session, and the human supervising
it. **Read first:** `AGENTS.md`, `DECISIONS.md`, then `README.md` in this
folder. **Status:** none of this is done yet. Line numbers were checked on
2026-10-04 against branch `NEW`; re-grep before editing because the tree moves.

## Ground rules

- Follow `AGENTS.md` §9: stage only files owned by each task (never
  `git add .`), conventional commits, log commit-sized work in `CHANGES.md`,
  record the architectural decision in `DECISIONS.md`.
- Never read, print, edit or commit `.env`. Never put a secret in a file in this
  repository. Secrets are entered in the Render dashboard only.
- Never open a PR to or merge into `deployment` without the owner's explicit
  instruction in that session.
- Local development must keep working exactly as it does now. Every change below
  is additive or selected by configuration; the default (`config/app.toml`)
  keeps today's behaviour.
- No live model calls in tests.

## P0 — Get a clean, complete base branch (blocking)

Facts verified 2026-10-04:

- Current branch is `NEW`, with many uncommitted modifications (see
  `git status`). Those belong to other work; do not sweep them into deployment
  commits.
- `staging` (`2635aba`) does **not** contain
  `src/oryxenai/agents/code_generator/serving.py` (Studio previews), nor
  `src/oryxenai/deployment/render_web.py`, nor `config/app.render-free.toml`.
  `deployment` is at `0b0cac0`. Both are behind the product.
- `render_web.py`, `app.render-free.toml` and the old v2 docs are tracked on
  `NEW` only.

Do:

1. Ask the owner which commits of `NEW` are releasable. Do not guess.
2. Bring the releasable product to `staging` through the normal review path.
   Confirm with `git ls-tree -r staging --name-only | grep code_generator/serving.py`.
3. Create the working branch for tasks C1–C8 from that `staging` tip, e.g.
   `deploy/render-free`. All commits below go there, then are merged to
   `staging`. Promotion to `deployment` is a later, owner-approved step.

Done when: the branch builds the Studio end-to-end locally and `uv run pytest`
is green on it.

---

## Code changes

### C1 — Trust the platform's proxy headers

**Why.** `RateLimitMiddleware` (`src/oryxenai/main.py:96-146`) keys on
`request.client.host`. Uvicorn only trusts forwarded headers from 127.0.0.1 by
default; behind Render every user then appears as the proxy and all users share
one bucket (`/auth/` 30 per minute, `/api/` 120 per minute). Azure avoided this
with `--proxy-headers --forwarded-allow-ips=*` in `compose.production.yaml:77`.
Neither `render_web.py` nor the Dockerfile `CMD` passes it.

**Change.**
- `src/oryxenai/deployment/render_web.py` (the `uvicorn` argument list,
  currently lines 61–74): append `"--proxy-headers"` and
  `"--forwarded-allow-ips=*"`. Add a one-line comment that `*` is safe only
  because the container's port is reachable only through the platform proxy.
- `Dockerfile:126` `CMD`: add the same two flags so the Railway/other-PaaS
  fallback behaves the same.

**Verify.** Add a unit test for the command construction if it is factored into
a helper, or assert the flags in a small test of `render_web`. Manually: two
requests with different `X-Forwarded-For` values hit different rate-limit keys.

### C2 — Lightweight PDF engine (the main code task)

**Why.** `src/oryxenai/agents/discovery/document_extract.py:10-21` imports
`docling` (and therefore PyTorch) at module import time. The API imports it via
`api/routes/discovery.py:12`, so the 512 MB free instance pays the memory cost
before any PDF is processed, and Docling's layout model will not fit anyway.

**Design.** Keep one public function, `extract_document(...)`, with the same
signature plus the new selector, the same return tuple
`(name, text, page_count, warnings)`, and the same `DocumentExtractionError`
messages. All validation in `_extract_pdf` before conversion (header check,
`pypdf` encryption/page-count checks, size, char limits) stays and runs for
both engines.

1. **Setting.** In `src/oryxenai/core/settings.py` next to `max_pdf_pages` /
   `ocr_artifacts_path` (lines 478–480, the discovery limits model) add:
   - `pdf_engine: Literal["docling", "light"] = "docling"` (default keeps local
     behaviour)
   - `light_ocr: bool = True` (OCR pages that have no extractable text)
   Mirror them in `config/app.toml` `[discovery]` (near lines 134–136) with
   comments.
2. **Lazy imports.** Move every `docling*` import (lines 10–21) inside
   `_get_pdf_converter` (keep its `lru_cache`). The module must import cleanly
   with Docling not installed. When `pdf_engine = "docling"` and the import
   fails, raise `DocumentExtractionError("PDF reading is not ready on this
   server. Please try again later.")` and log the import error server-side.
3. **Light path** `_extract_pdf_light(data, max_pdf_pages, timeout, light_ocr)`:
   - Open with `pypdfium2` (already a Docling dependency; make it a direct one).
     For each page up to `max_pdf_pages`: get text with
     `page.get_textpage().get_text_range()`. Normalise only trailing
     whitespace; keep paragraph breaks. Join pages with the same
     `"\n\n--- Page break ---\n\n"` marker Docling output uses.
   - If a page has fewer than ~20 non-space characters and `light_ocr` is on,
     render it at scale ≈ 1.5–2 (`page.render(scale=...).to_pil()`), run RapidOCR
     (onnxruntime backend) and use the recognised lines in reading order.
     Process **one page at a time**, close/`del` page objects and call
     `gc.collect()` after each page to bound memory.
   - Enforce `pdf_timeout_seconds` with a monotonic deadline checked between
     pages; on expiry raise the existing "took too long" error.
   - Add a warning string "Layout and tables are simplified on this server;
     review the text." so the editable preview tells the user what changed.
   - Which OCR package? Use the one Docling's `rapidocr` extra currently
     resolves to in `uv.lock` (check `uv tree | grep -i rapidocr`), so no new
     vendor is introduced. If it needs model files, ship them in the wheel or
     download them in the Docker build stage — never at runtime.
4. **Plumbing.** `api/routes/discovery.py:55-62`: pass
   `engine=limits.pdf_engine` and `light_ocr=limits.light_ocr` into
   `extract_document`. Skip the `Path(artifacts_path).is_dir()` check
   (`document_extract.py:144`) when engine is `light`.
5. **Tests** (`tests/unit/agents/discovery/test_document_extract.py`): keep
   existing Docling tests (they use deterministic doubles); add tests for the
   light engine using small generated PDFs (the file already has a `_pdf()`
   helper): text PDF → expected text; page-limit and encrypted PDFs → same
   errors; blank-text page with `light_ocr=False` → "No readable text" error;
   monkeypatch the OCR callable for an OCR-path test. Import-time test: with
   `sys.modules["docling"] = None`, importing `document_extract` still works.

**Acceptance.** `uv run pytest tests/unit/agents/discovery -q` passes; the app
starts with Docling uninstalled; a text-PDF upload returns a transcript.

### C3 — Make the heavy dependencies optional and slim the image

**Why.** `pyproject.toml:32-34` hard-requires `docling[rapidocr]`, `torch` and
`torchvision`, which dominate image size, build time (Render free has 500 build
minutes per month) and memory.

**Change.**
1. `pyproject.toml`: move `docling[rapidocr]`, `torch`, `torchvision` to
   `[project.optional-dependencies] pdf-full = [...]`. Keep the
   `[tool.uv.sources]` CPU-wheel pins (lines ~55–66) working for that extra.
   Add the light set as normal dependencies: `pypdfium2`, the RapidOCR package
   and `onnxruntime`, and an OpenCV **headless** build (RapidOCR's OpenCV
   dependency must be `opencv-python-headless`; check `uv tree` for which
   OpenCV Docling currently drags in). Regenerate `uv.lock`
   (`uv lock`), commit both.
2. **Local developers** now run `uv sync --extra pdf-full` to keep Docling.
   Update `AGENTS.md` §7 commands, `scripts/bootstrap.ps1` and
   `scripts/bootstrap.sh` accordingly, and mention it in `README.md`.
3. `Dockerfile`:
   - Add `ARG PDF_ENGINE=light` in the builder stage.
   - `uv sync --frozen --no-dev --no-install-project` → add
     `$( [ "$PDF_ENGINE" = "full" ] && echo --extra pdf-full )` (use an `if`
     block rather than command substitution if clearer); same for the second
     `uv sync` (line 56).
   - Run `scripts/download_docling_models.py` (lines 47–50) **only when**
     `PDF_ENGINE=full`. Copy `/opt/docling-models` into the runtime stage only
     in that case (use a stage that creates an empty directory otherwise, so
     the `COPY` does not fail).
   - Keep `INSTALL_CHROMIUM=false` (default) and `HF_HUB_OFFLINE=1`.
   - Re-check the OpenCV runtime libraries installed at lines 36–39 and 62–65;
     headless OpenCV needs far fewer — remove `libgl1`, `libxcb1`, `libsm6`,
     `libxext6`, `libxrender1` only if the image still runs.
4. `.dockerignore`: confirm `.workspace/`, `node_modules/`, `.venv/`, `output/`,
   `docs/` are excluded so the Render build context is small.

**Measurement gate (do not skip, record the numbers in `CHANGES.md`):**

```bash
docker build -t oryxenai:light --build-arg PDF_ENGINE=light .
docker image ls oryxenai:light            # record size; expect well under 1 GB
docker run --rm --memory=512m --cpus=0.5 \
  -e OryxenAI_CONFIG_OVERLAY=config/app.render-free.toml  ...   # test env, test DB
# in another shell:  docker stats   (idle RSS of API + worker)
# upload (a) a 3-page text PDF, (b) a 3-page scanned PDF; record peak memory
```

Decision rule: idle RSS (API + worker) should stay under ~350 MB. If the scanned
PDF is OOM-killed or exceeds the 120 s timeout, set `light_ocr = false` in the
overlay and make the empty-text error say "This PDF has no selectable text.
Export it as a text-based PDF or paste the text." Report the result to the
owner; do not silently drop scanned-PDF support.

### C4 — Start-up cost on a 0.1 CPU instance

`render_web.py:46` runs `alembic upgrade head` on every start, including every
wake-up. That is fine functionally. Add a log line with elapsed time around it
and around uvicorn readiness. Only if boot exceeds Render's health-check window
(measure first), skip the migration when `alembic_version` already equals head
(`alembic.script.ScriptDirectory` + a one-row query) — keep the migration
mandatory on first start and after deploys.

### C5 — `render.yaml` Blueprint (repeatable, AI-friendly setup)

Create `render.yaml` at the repository root. Keys verified against Render's
Blueprint spec on 2026-10-04:

```yaml
services:
  - type: web
    name: oryxenai
    runtime: docker
    plan: free
    region: singapore
    branch: deployment            # see C6; use the deploy branch the owner approves
    dockerfilePath: ./Dockerfile
    dockerContext: .
    dockerCommand: python -m oryxenai.deployment.render_web
    healthCheckPath: /health/ready
    autoDeployTrigger: "off"      # first release is manual; later "checksPass"
    envVars:
      - key: OryxenAI_CONFIG_OVERLAY
        value: config/app.render-free.toml
      - key: ORYXENAI_AUTH_PRIMARY_ORIGIN
        value: https://app.oryxenai.me
      - key: ORYXENAI_AUTH_ALLOWED_ORIGINS
        value: https://app.oryxenai.me
      - key: PREVIEW_GRANT_SECRET
        generateValue: true       # Render generates a stable random secret
      - key: DATABASE_URL
        sync: false
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_PUBLISHABLE_KEY
        sync: false
      - key: SUPABASE_SECRET_KEY
        sync: false
      - key: ORYXENAI_ADMIN_BOOTSTRAP_EMAILS
        sync: false
      - key: ORYXENAI_ALLOWED_USER_EMAILS
        sync: false
      - key: EXPLABS_BASE_URL
        sync: false
      - key: EXPLABS_API_KEY
        sync: false
```

Notes for the agent: `PORT` is injected by Render, never set it; `PDF_ENGINE`
defaults to `light` in the Dockerfile, so the free service needs no build
setting (to build the full image later, check Render's Docker docs for how
service environment variables reach `ARG`s at build time before relying on it).
Validate the file with the Render CLI/dashboard Blueprint
preview before the owner applies it. If the owner prefers the dashboard form,
doc 03 gives the same values; keep the two consistent.

### C6 — Cut the Azure deployment out of CI; define production = Render

Facts: on `staging`/`deployment`, `.github/workflows/ci.yml` has a `deploy` job
(line ~203) that runs `./scripts/azure-deploy.sh deploy ${{ github.sha }}` on a
self-hosted runner labelled `azure-oryxenai` when the ref is
`refs/heads/deployment`, plus Azure-only steps (`bash -n scripts/azure-deploy.sh`,
production Compose validation). `main` has a smaller CI file. The `NEW` branch
has no `.github/` directory, so do this on the base branch from P0.

**Change.**
1. Remove the `deploy` job and the Azure-script/Compose validation steps. Keep
   lint, mypy, pytest (Postgres 16 service), frontend typecheck/build and the
   container smoke test. Keep `workflow_dispatch`.
2. Add a Docker build step for the **light** image so CI proves the Render image
   builds (`docker build --build-arg PDF_ENGINE=light .`).
3. In Render, `autoDeployTrigger: checksPass` on the `deployment` branch then
   deploys only after CI passes. The existing GitHub ruleset on `deployment`
   (PR required, `quality` check required) stays.
4. Update `AGENTS.md` §8, `docs/deployment/ci-cd-runbook.md` (also fix its stale
   "deploy job disabled" statement) and add a `DECISIONS.md` entry: production
   host = Render Free + Supabase; Azure retired; branch rules unchanged;
   no automatic deploy without owner approval. **Get the owner's OK before
   editing `AGENTS.md`.**

### C7 — Overlay and environment documentation

- `config/app.render-free.toml`: add
  ```toml
  [discovery]
  pdf_engine = "light"
  light_ocr = true      # set false if the C3 measurement gate fails
  ```
  and delete the `ocr_artifacts_path = "/opt/docling-models"` line (it only
  matters for `docling`). Keep everything else: `app.env="production"`,
  `[database.pool] pool_size=1, max_overflow=1`, `[worker] concurrency=1`,
  `[code_generator.verification] browser="off"`, `[retention]` on,
  `local_fs` storage. Leave the placeholder origins; the env vars override them
  (`core/settings.py:854-861`).
- Update the comment at the top of the file: it is the *free-host* overlay, not
  Render-only.
- `.env.example`: add a short "Render/Supabase" block listing the variable names
  in the table below with empty values, and mark the Azure-only variables
  (`APP_HOST`, `ORYXENAI_DATA_ROOT`, `ORYXENAI_BACKUP_DIR`, …) as VM-only.

### C8 — Cleanup commit (only after acceptance in doc 05 passes)

Separate commit, so rollback to Azure stays possible until then:
delete `compose.production.yaml`, `Caddyfile`, `scripts/azure-deploy.sh`,
`config/app.production.toml` (or keep it as the paid-host overlay — ask the
owner), archive the Azure-specific files under `docs/deployment/` into
`docs/deployment/archive/`, and fix `docs/deployment/README.md` to point at this
folder. Do not delete `config/app.docker.toml` / `compose.yaml` (local Docker).

---

## Configuration reference

### Render environment variables

| Key | Value | Secret | Notes |
| --- | --- | --- | --- |
| `OryxenAI_CONFIG_OVERLAY` | `config/app.render-free.toml` | no | Exact spelling and case. |
| `DATABASE_URL` | Supabase **Session pooler** URI (port **5432**) with the DB password URL-encoded and `?sslmode=require` | yes | Copy from Supabase **Connect**. Code rewrites it to `postgresql+asyncpg://` and converts `sslmode` (`settings.py:893-925`). |
| `SUPABASE_URL` | `https://diiestlnmpaarhhexwhi.supabase.co` | no | Confirm the project ref in the dashboard. |
| `SUPABASE_PUBLISHABLE_KEY` | project publishable key | no | Browser-safe; injected into pages at runtime. |
| `SUPABASE_SECRET_KEY` | project secret key | yes | Server-only (admin user endpoints). |
| `ORYXENAI_AUTH_PRIMARY_ORIGIN` | `https://app.oryxenai.me` | no | No trailing slash, no path. |
| `ORYXENAI_AUTH_ALLOWED_ORIGINS` | `https://app.oryxenai.me` | no | **Exactly one** HTTPS origin in production; localhost is rejected (`settings.py:452-457`). |
| `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` | two admin Google emails, comma-separated | private | **Exactly two** required (`settings.py:410-413`). |
| `ORYXENAI_ALLOWED_USER_EMAILS` | normal-user Google emails | private | Required non-empty when `admission_mode = "allowlist"`; max 15. |
| `EXPLABS_BASE_URL` | model provider base URL from `.env.example` | no | Re-check `config/models.toml` for the active profile. |
| `EXPLABS_API_KEY` | provider key | yes | Copy from the provider's key page. |
| `PREVIEW_GRANT_SECRET` | 32+ random characters | yes | Without it, previews break on every restart. |

**Do not set:** `PORT` (Render injects it), `POSTGRES_PASSWORD`,
`DB_HOST_OVERRIDE`, `DB_PORT_OVERRIDE`, `APP_HOST`, `R2_*`, any `VITE_*`, or the
unused Anthropic/Gemini/OpenAI keys.

### Origin and URL settings — one list, four places

The same origin string `https://app.oryxenai.me` must appear in all of:

1. Render env: `ORYXENAI_AUTH_PRIMARY_ORIGIN`, `ORYXENAI_AUTH_ALLOWED_ORIGINS`.
2. Supabase → Authentication → URL Configuration → **Site URL**.
3. Supabase → same page → **Redirect URLs**: `https://app.oryxenai.me/auth/callback`
   (keep `http://localhost:8000/auth/callback` and
   `http://127.0.0.1:8000/auth/callback` for local development; Supabase matches
   redirect URLs exactly and falls back to the Site URL otherwise).
4. Google Cloud → OAuth client → **Authorized JavaScript origins**:
   `https://app.oryxenai.me` (scheme + host only).

Google's **Authorized redirect URI** is *not* changed: it stays
`https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback`. The browser goes
Google → Supabase → `https://app.oryxenai.me/auth/callback`.

### DNS (Namecheap, BasicDNS)

Remove the old A records `app` and `preview` that point to the Azure VM IP, add
`CNAME  app  →  <render-service>.onrender.com`. `preview.oryxenai.me` is not
used any more (previews are same-origin at `/preview/g/...`).

### Branch and deploy mapping

| Branch | Purpose | Deploys to |
| --- | --- | --- |
| feature / `deploy/render-free` | work | nothing |
| `staging` | integration, CI | nothing (Render has no free staging; test locally with Docker) |
| `deployment` | protected production | Render, after CI, with owner approval |

## Definition of done for this work list

- Light Docker image builds in CI and meets the C3 numbers (recorded).
- All repository gates pass: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy src`, `uv run pytest`, `uv run alembic upgrade head` (against the
  test DB only), frontend build.
- `render.yaml` valid; no secret anywhere in the diff
  (`git diff --cached | grep -iE "key|secret|password"` reviewed by hand).
- `CHANGES.md` and `DECISIONS.md` updated; owner told exactly which commit to
  promote and which dashboard steps (doc 03) remain.
