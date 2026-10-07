# 09 — Runtime Load Distribution, Resilience Strategy & AI Agent Implementation Rules

**Status:** Architecture Specification · **Last Updated:** 2026-10-05  
**Audience:** AI coding agents (Claude Code, OpenAI Codex, Antigravity, Cursor) and human engineering leads.  
**Context:** Guidelines for maintaining stability, distributing load, and implementing features safely within the Render Free + Supabase environment.

---

## 1. Core Architectural Invariants

Every agent or engineer making code modifications must preserve these core invariants:
1. **Zero Synchronous AI Execution in Web Handlers:** HTTP route handlers must return within 100 ms. All multi-turn AI reasoning, brief synthesis, and code generation must be dispatched to the durable PostgreSQL worker queue.
2. **Strict Memory Bounding (<= 512 MB):** No library or routine may assume unrestricted system memory. Heavy operations must process data incrementally and actively release memory pages.
3. **Storage Immutability:** Generated portfolios are stored as versioned bundles in PostgreSQL (`portfolio_site_versions`). The container filesystem must be treated as completely ephemeral and stateless.
4. **Idempotent Queue Handlers:** The queue operates on at-least-once execution semantics. If a container reboots mid-job, the re-claimed handler execution must not corrupt session state.

---

## 2. Load Distribution & Concurrency Architecture

### Asynchronous Request-Response Decoupling

```text
Browser Client                    FastAPI Web Service                   PostgreSQL Queue & Worker
      │                                    │                                        │
      ├─── 1. POST /api/discovery/start ──►│                                        │
      │                                    ├─── 2. Insert job (status: queued) ────►│
      │◄── 3. 202 Accepted {job_id} ───────┤                                        │
      │                                    │                                        ├─── 4. Worker claims job
      ├─── 5. GET /api/jobs/{job_id} ─────►│                                        │       (SELECT FOR UPDATE)
      │◄── 6. 200 OK {status: running} ────┤                                        │       Executes LLM pipeline
      │    (Client polls every 2-3s)       │                                        │
      │                                    │                                        ├─── 7. Commits result
      ├─── 8. GET /api/jobs/{job_id} ─────►│                                        │       (status: succeeded)
      │◄── 9. 200 OK {status: succeeded} ──┤                                        │
```

* **HTTP Layer:** Never blocks on model provider latency. HTTP requests return immediately with an HTTP 202 status.
* **Worker Layer:** Bounded to `concurrency = 1`. Jobs are prioritized via `foreground_job_kinds` so user-facing operations (chat edits, initial builds) execute ahead of background retention sweeps.
* **Database Contention:** Protected by `SELECT ... FOR UPDATE SKIP LOCKED`, preventing race conditions or worker deadlocks.

---

### Process Architecture: Subprocess Supervisor vs. In-Process Asyncio

The Render container is supervised by [`src/oryxenai/deployment/render_web.py`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/deployment/render_web.py).

| Model | Memory Impact | Fault Isolation | Verdict |
| :--- | :--- | :--- | :--- |
| **Current: Subprocess Supervisor** (`render_web.py`) | Spawns two Python processes (Uvicorn + Worker). Uses ~160–220 MB RAM combined. | **High:** If the worker crashes or runs out of memory, Uvicorn remains alive, allowing the web service to report diagnostic errors and keep health probes green. | **Maintained as current standard.** |
| **Alternative: In-Process Runner** (Worker inside FastAPI lifespan) | Single Python process. Uses ~110–140 MB RAM (saves ~50 MB). | **Lower:** An unhandled OOM in the worker terminates the entire web server simultaneously. | **Reserved as optimization** if memory margins ever tighten below 100 MB. |

---

## 3. Memory Bounding & Garbage Collection Playbook

When writing code that processes documents, strings, or model payloads:

### Rule A: The CPython + glibc Memory Release Pattern
Whenever a batch task or file extraction completes, do not rely on standard reference counting alone. Call this cleanup sequence:

```python
import contextlib
import ctypes
import gc


def release_runtime_memory() -> None:
    """Force Python garbage collection and trim glibc heap allocations back to OS."""
    gc.collect()
    with contextlib.suppress(Exception):
        # libc.so.6 is standard on Debian bookworm (Render Docker image)
        ctypes.CDLL("libc.so.6").malloc_trim(0)
```

### Rule B: PDF Extraction Memory Isolation
When extracting text from uploaded PDFs:
1. Always iterate page-by-page. Never hold all page render bitmaps in memory simultaneously.
2. Explicitly close and delete the `pypdfium2` page object before rendering the next page:
   ```python
   for page_index in range(min(page_count, max_pages)):
       page = pdf.get_page(page_index)
       try:
           text_page = page.get_textpage()
           text = text_page.get_text_range()
           # ... process text ...
       finally:
           page.close()
   release_runtime_memory()
   ```

### Rule C: Database Session Lifecycle
1. Never hold long-lived `AsyncSession` instances across network I/O or sleep calls.
2. Use short-lived context managers (`async with sessionmaker() as session:`).
3. The engine pool is configured with `pool_recycle = 1800` to refresh stale TCP connections and reclaim driver memory.

---

## 4. Resilience & Failure Recovery Rules

### Rule 1: The Outer Timeout Safety Hook
When a job handler times out via `asyncio.wait_for(...)`, the handler's internal `try/except` block is cancelled from the outside. 
Every handler registered in `src/oryxenai/jobs/registry.py` must implement the `on_timeout` protocol:
```python
async def on_timeout(self, payload: dict[str, Any], error: dict[str, Any]) -> None:
    """Invoked when outer job timeout fires to prevent stuck UI states."""
    envelope = FailureEnvelope(
        code="JOB_TIMEOUT",
        stage="execute",
        summary="Operation exceeded time limit and was stopped.",
        retryable=True,
    )
    await persist_terminal_failure(payload, envelope)
```
*Failure to implement `on_timeout` causes sessions to remain stuck in "running" status indefinitely.*

### Rule 2: Optimistic Revision Checking
When persisting stage outputs to `portfolio_sessions`, always increment and assert the `revision` column. If a concurrent modification was committed by the user while the worker was processing, the worker must abort and discard stale state rather than overwriting newer user changes.

---

## 5. Rules for AI Coding Agents Modifying This Repo

1. **Do Not Reintroduce Docling/PyTorch:**
   * Any change that imports `docling`, `torch`, or `transformers` unconditionally at the module level will instantly cause Render Free to OOM crash during container startup. Keep imports strictly deferred and guard them with configuration flags.
2. **Do Not Turn on Server-Side Chromium on Free Deployments:**
   * `[code_generator.verification] browser` must remain `"off"` in `config/app.render-free.toml`.
3. **Preserve Pinned Theme Contracts:**
   * Theme HTML and CSS bundles in `src/oryxenai/themes/` must remain deterministic and sealed. Do not introduce runtime network downloads of third-party CSS or JS assets.
4. **Follow the Conventional Commit & Ledger Protocol:**
   * Log units of work to `CHANGES.md`.
   * Record structural decisions in `DECISIONS.md`.
   * Never execute `git add .` or `git add -A`. Stage only files explicitly modified for the assigned task.
   * Never push or merge to `deployment` branch without real-time human authorization.
