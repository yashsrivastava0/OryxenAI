# 08 — Render & Supabase Free Tier Edge Cases, Developer Traps, and Proven Solutions

**Status:** Reference & Engineering Guide · **Last Updated:** 2026-10-05  
**Audience:** Human developers, system operators, and AI coding agents (Claude Code, OpenAI Codex, Antigravity, Cursor).  
**Context:** Deployment of OryxenAI as a single supervised Docker container on Render Free Web Service (Singapore) with Supabase Free PostgreSQL and Supabase Auth.

---

## 1. Executive Summary & Ground Truth

Running a multi-agent AI web application with background queues on a **strict $0 free tier** is entirely viable, but free PaaS environments enforce strict technical ceilings:
* **Render Free:** 512 MB RAM hard limit, 0.1 shared vCPU, 15-minute idle sleep, 100-second HTTP request timeout, ephemeral container disk, 750 free instance-hours/month.
* **Supabase Free:** 500 MB database storage, 50,000 monthly active users, 7-day inactivity project pause, connection limits (60 direct, 200 pooled).

This document captures **real-world failure modes, developer community lessons (Reddit, Render Forums, GitHub), and proven engineering solutions** across the entire OryxenAI stack. AI coding agents modifying or maintaining this codebase must adhere to these findings.

---

## 2. Infrastructure Traps & Proven Mitigations

### Trap 1: The 512 MB RAM Ceiling & CPython Memory Hoarding (OOM SIGKILL 137)

#### The Problem
Render enforces a hard memory cgroup limit at 512 MB. When a container exceeds 512 MB by even 1 MB, the Linux kernel immediately terminates the process with `SIGKILL` (exit code `137`). There is no graceful exception handling or warning.
In Python (CPython 3.13), calling `del obj` or `gc.collect()` cleans up internal object references, but **the underlying C library allocator (`glibc`) hoards freed virtual memory pages** for future allocations rather than returning them to the operating system. To Render's cgroup monitor, memory usage never drops and gradually creeps up until the service crashes.

#### Community Solutions & Recommended Fixes
1. **Disable Heavy Runtime Packages:**
   * Never import Docling, PyTorch, torchvision, or transformers at the module top level. Use `pdf_engine = "light"` (pypdfium2).
   * Disable headless Chromium on the server (`browser = "off"` in `config/app.render-free.toml`). Studio previews render natively in the client's browser.
2. **Explicit System Memory Trimming:**
   After running memory-intensive operations (such as PDF text extraction or image OCR), invoke `malloc_trim(0)` from `libc.so.6` to force `glibc` to release freed memory back to the OS:
   ```python
   import ctypes
   import gc


   def bound_system_memory() -> None:
       gc.collect()
       with contextlib.suppress(Exception):
           ctypes.CDLL("libc.so.6").malloc_trim(0)
   ```
3. **Allocator Tuning via Environment Variable:**
   Configure `glibc` memory allocation behavior in Dockerfile or deployment environment:
   ```dockerfile
   ENV MALLOC_MMAP_THRESHOLD_=65536
   ```
   This forces allocations larger than 64 KB to use direct OS `mmap` calls, which are immediately unmapped upon deletion rather than retained in the process heap.

---

### Trap 2: 0.1 Shared CPU Contention & Worker Starvation

#### The Problem
Render Free grants 0.1 shared vCPU (burstable). If the background worker runs heavy computation (e.g. OCR on a multi-page scanned PDF or CPU-heavy JSON normalization), the worker can monopolize the CPU, causing FastAPI health checks (`/health/live` and `/health/ready`) to miss Render's 5-second health-probe deadline, resulting in premature container restarts.

#### Community Solutions & Recommended Fixes
1. **Asynchronous Yielding in Worker Loops:**
   In long-running worker loops, introduce periodic `await asyncio.sleep(0.05)` checkpoints between pipeline stages and pages. This yields control back to the event loop so FastAPI can respond to health checks and API traffic without latency spikes.
2. **Worker Concurrency Limit:**
   Keep `concurrency = 1` and `claim_batch_size = 1` in `config/app.render-free.toml`. Process background jobs sequentially to prevent multiple heavy jobs from saturating the 0.1 CPU core.
3. **Decouple CPU-Intensive Tasks from HTTP Cycle:**
   HTTP handlers must never execute long-running pipelines synchronously. All heavy stages (Discovery brief synthesis, Content Architect planning, Studio code generation) are queued in PostgreSQL and return `202 Accepted` within 50 ms.

---

### Trap 3: Supabase Connection Pooling & `asyncpg` Prepared Statement Incompatibility

#### The Problem
Supabase provides two connection pooler ports via Supavisor:
* **Port 5432 (Session Mode):** Keeps the physical connection assigned to the client for the duration of the session. Supports PostgreSQL prepared statements.
* **Port 6543 (Transaction Mode):** Swaps physical connections between individual queries.

By default, SQLAlchemy's `asyncpg` driver caches prepared statements (`__asyncpg_stmt_X__`). If connected to Port 6543, queries will intermittently fail with:
`prepared statement "__asyncpg_stmt_1__" does not exist` or `already exists`. Furthermore, PostgreSQL advisory locks used in OryxenAI for model quota gating (`pg_advisory_xact_lock`) fail unpredictably in transaction mode.

#### Community Solutions & Recommended Fixes
1. **Primary Solution (Session Pooler):**
   In Render's `DATABASE_URL`, use the **Session pooler on port 5432**:
   `postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require`
2. **Minimal Local Pool Allocation:**
   Because Session mode reserves server connections, keep the local application pool strictly bounded in `config/app.render-free.toml`:
   ```toml
   [database.pool]
   pool_size = 1
   max_overflow = 1
   pool_timeout = 20
   pool_recycle = 1800
   ```
3. **Fallback Solution (If Port 6543 must be used):**
   If transaction pooling is ever required, disable prepared statement caching in `src/oryxenai/db/session.py`:
   ```python
   create_async_engine(
       url,
       connect_args={
           "statement_cache_size": 0,
           "prepared_statement_cache_size": 0,
       },
   )
   ```

---

### Trap 4: 15-Minute Inactivity Sleep & 7-Day Supabase Project Pausing

#### The Problem
* Render Free services automatically spin down after 15 minutes of inbound HTTP inactivity. The next visitor experiences a 50–70 second cold start while the container reboots. More critically, when the container is asleep, the background worker stops polling PostgreSQL.
* Free Supabase projects are automatically paused after 7 days of inactivity. Once paused, all database connections fail with connection refused or 503 until manually resumed in the dashboard.

#### Community Solutions & Recommended Fixes
1. **The Dual-Purpose Keep-Alive Monitor:**
   Configure a free monitor on UptimeRobot (or similar HTTP pinger) to issue a `GET` request every **5 minutes** to:
   `https://app.oryxenai.me/health/ready`
2. **Why `/health/ready` (not `/health/live`):**
   `src/oryxenai/api/routes/health.py` calls `check_database_ready()`, which executes an active SQL query (`SELECT to_regclass(...)`).
   * This inbound HTTP request prevents Render from sleeping (runs ~744 out of 750 free monthly hours).
   * The executed SQL query counts as active database traffic, preventing Supabase from ever pausing the database.

---

### Trap 5: Reverse Proxy Headers & Rate Limiting IP Collapse

#### The Problem
FastAPI's rate limiter (`src/oryxenai/main.py:RateLimitMiddleware`) tracks clients by `request.client.host`. Behind Render's load balancer, Uvicorn only trusts proxy headers from `127.0.0.1` by default. As a result, every visitor shares the single IP address of the Render proxy, causing all users to share one rate limit bucket (e.g., 30 requests/min for auth). A few clicks trigger HTTP 429 for all users.

#### Community Solutions & Recommended Fixes
Pass proxy forwarding flags to Uvicorn inside [`render_web.py`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/deployment/render_web.py):
```python
[
    sys.executable,
    "-m",
    "uvicorn",
    "oryxenai.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    port,
    "--proxy-headers",
    "--forwarded-allow-ips=*",
]
```
*Note:* Forwarding from `*` is secure here because Render does not expose the container's private port directly to the internet; all external traffic arrives strictly through Render's managed reverse proxy.

---

### Trap 6: Namecheap DNS, Conflicting Records & SSL Hangs

#### The Problem
When binding a custom domain (`app.oryxenai.me`) on Render with Namecheap DNS:
* Old A records pointing to previous hosts (e.g. the historical Azure VM IP `20.235.74.81`) take precedence over CNAME records, causing Render domain verification to fail or hang on "Certificate Pending" indefinitely.
* Namecheap URL Redirects or extraneous IPv6 AAAA records conflict with Render's IPv4 routing.

#### Community Solutions & Recommended Fixes
1. In Namecheap Advanced DNS for `oryxenai.me`:
   * **Delete** any existing A or CNAME records for the host `app`.
   * **Delete** any AAAA (IPv6) records for `app`.
   * **Add CNAME Record:** Host `app`, Value `<service-name>.onrender.com`, TTL `Automatic` (or 1 minute for fast propagation).
2. Wait for Render dashboard to display "Verified", then confirm TLS certificate issuance before directing user traffic.

---

### Trap 7: Ephemeral File Storage Wipes

#### The Problem
Render containers have ephemeral local disk storage. Any files saved to local disk during execution are permanently lost when the service restarts, scales, or redeploys.

#### Community Solutions & Recommended Fixes
* **Zero Disk Dependency:** OryxenAI stores all state in PostgreSQL:
  * Intake & Discovery dossiers: `portfolio_sessions.discovery_dossier` (JSONB)
  * Content plans: `portfolio_sessions.content_blueprint` (JSONB)
  * Generated site code: `portfolio_site_versions.index_html` and `manifest` (TEXT / JSONB)
* Static theme files (fonts, base CSS) are pre-packaged into the immutable Docker image at build time.

---

## 3. Agent-Specific Edge Cases & Failure Recovery

### Discovery Agent & Document Intake
* **Failure Mode:** User uploads a multi-page high-resolution scanned PDF.
* **Risk:** Memory explosion and timeout during OCR.
* **Mitigation:**
  1. Limit file size (`max_bytes = 10 * 1024 * 1024`) and pages (`max_pdf_pages = 10`).
  2. With `pdf_engine = "light"`, extract text directly with `pypdfium2`.
  3. If no text exists and `light_ocr = true`, render pages sequentially at scale 1.5, run RapidOCR, delete the PIL image immediately, and trigger `gc.collect()` before moving to the next page.
  4. Enforce `pdf_timeout_seconds = 120`.

### Content Architect Agent
* **Failure Mode:** Model provider returns truncated or invalid JSON during the sequential planning pipeline (`plan_content` -> `write_pages` -> `integrate_content`).
* **Mitigation:**
  1. Structured envelope validation via Pydantic schemas.
  2. If the provider model returns an error or malformed payload, convert to `stable_provider_failure` with retryable flag.
  3. Job handler does not crash the process; it sets the job status to `failed` and logs an exact `what / where / why` diagnostic envelope in session state so the user can retry via UI.

### Studio (Code Generator) & Live Preview
* **Failure Mode 1 (Grant Expiry):** User leaves the Studio open for >30 minutes and preview iframe errors with `GrantExpired`.
  * *Resolution:* The frontend automatically catches the expired grant and requests a fresh grant via `/api/code-generator/preview-grant` using the active session token.
* **Failure Mode 2 (Ephemeral Grant Secret):** If `PREVIEW_GRANT_SECRET` is generated randomly at boot, every container redeploy breaks all currently loaded iframes.
  * *Resolution:* `PREVIEW_GRANT_SECRET` must be set as a permanent environment variable in Render dashboard.
* **Failure Mode 3 (Sandbox Escapes & CSP):** Serving untrusted user HTML on the primary domain.
  * *Resolution:* Studio previews are served via `/preview/g/<grant>/...` with a strict `Content-Security-Policy: sandbox allow-scripts allow-popups; frame-ancestors 'self'`. The iframe has no `allow-same-origin`, preventing the preview from reading parent local storage or auth cookies.
