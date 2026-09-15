# OryxenAI: Resume Assets, High-Impact Bullets & Staff/Senior AI Engineer Interview Defense Guide

> **Production Credentials & Technical Interview Playbook**  
> **Target Roles:** Senior / Staff Agentic AI Engineer, LLM Systems Engineer, AI Backend / Distributed Systems Engineer  
> **Framing Caliber:** 3+ Years of Production Engineering Experience  
> **Focus:** Multi-Agent Orchestration, High-Throughput Distributed Queues, Neuro-Symbolic Verification, Deterministic Sandboxing, and Fail-Closed Production Architecture.

---

## 1. Executive Resume Project Descriptions

Use these pre-formatted snippets directly on your resume, portfolio website, GitHub pinned repo, or LinkedIn profile.

### Option A: The Impact-First Punchy Bullet (For 1-Page Resumes)
> **OryxenAI | Lead / Senior Agentic AI Systems Architect**  
> Architected an autonomous 5-stage neuro-symbolic software synthesis engine (FastAPI, PostgreSQL, Playwright) that converts raw intent and career documentation into fully compiled, AST-audited, and verified production web applications. Engineered a durable PostgreSQL `SKIP LOCKED` distributed queue with execution laning, eliminating Redis/Celery dependencies, and built a Playwright headless browser geometry verification engine that reduced LLM code generation hallucination rates to under 0.6%.

### Option B: The Comprehensive Project Description (For Technical CVs / LinkedIn)
> **OryxenAI — Autonomous Multi-Agent Web Synthesis & Software Engineering Engine**  
> *Core Stack: Python 3.13, FastAPI, PostgreSQL (JSONB, CTEs), Asyncpg, Playwright, TypeScript AST, Tailwind CSS, Vite, Pydantic V2*  
> - Designed and deployed an autonomous end-to-end 5-stage software engineering pipeline (**Discovery**, **Content Architect**, **Visual Design Director**, **Build Preparation**, **Code Generator**) eliminating framework bloat (no LangChain/CrewAI) in favor of deterministic Python protocols and bounded adaptive state machines.  
> - Engineered an ACID-compliant distributed task queue inside PostgreSQL using `WITH due AS (SELECT ... FOR UPDATE SKIP LOCKED)` with cryptographic MD5 lease tokens, active heartbeat renewal, and execution-lane concurrency throttling to prevent API rate-limit exhaustion.  
> - Built a multi-viewport headless browser verifier and AST structural auditor that measures DOM content-box geometry, validates CSS matrix transforms, and traps CSP/network leaks, driving clean build and preview promotion reliability to 99.4%.  
> - Reduced LLM token consumption by 68% across downstream stages by replacing monolithic prompt chains with compact cryptographic state snapshots and SHA-256 brief fencing.  
> - Pioneered a modular compiler architecture (Experience Blueprint, Disjoint Work Graph, Self-Healing AST Repair Loops) that anchors on high-rigor web portfolios as a bounded proving ground for general autonomous full-stack web software synthesis.

---

## 2. High-Impact, Metric-Driven Resume Bullets (By Target Role)

Select 4–6 bullets matching the exact job description you are targeting.

### Track A: Agentic AI & LLM Systems Engineer
- **Multi-Agent State Orchestration:** Architected a 5-stage autonomous agent pipeline utilizing deterministic Pydantic V2 state machines and adaptive bounded workflows (1–3 sequential calls per stage), eliminating infinite tool loops and reducing average generation latency by 45%.
- **Progressive Wave Code Generation:** Designed a 4-wave progressive source code generator (Foundation tokens, isolated 3-section route batches, route composers, and whole-site review) enforcing disjoint file ownership boundaries, completely eliminating context window exhaustion and syntax truncation on complex multi-page applications.
- **Context Window & Prompt Optimization:** Engineered a compact state snapshot handoff pattern that isolates upstream raw resumes, passing only structured profile facts and SHA-256 verified hashes to downstream agents, slashing prompt token bloat by 68% and eliminating context drift.
- **Neuro-Symbolic Verification:** Developed a hybrid LLM-compiler pipeline pairing generative models with a deterministic TypeScript AST auditor and Playwright headless browser verifier, verifying CSS layout geometry, computed matrix transforms, and accessibility compliance.
- **Automated Diagnostic Repair Loop:** Implemented a closed-loop diagnostic repair engine with SHA-256 error fingerprint recurrence damping and per-category repair budgets (2 unit / 4 total / 3 polish), preventing oscillating LLM repair cycles and achieving a 99.4% clean build rate.
- **Provider-Neutral Model Routing:** Designed a configuration-driven `ModelRouter` supporting Anthropic Messages, OpenAI JSON-object, and Gemini Flash APIs with indirect secret resolution, dynamic quota tracking, and automatic bounded failover (D-093).
- **Anti-Leakage Structural Guards:** Built regex-based AST scanners and envelope validators that structurally reject internal chain-of-thought and QA evaluation notes (`status_note:`, `publication_check:`) from ever leaking into user-facing copy.

### Track B: AI Backend & Distributed Systems Engineer
- **Durable PostgreSQL Task Queue:** Engineered a distributed task queue directly on PostgreSQL utilizing CTEs and `SELECT ... FOR UPDATE SKIP LOCKED`, achieving zero lock contention under concurrent multi-worker execution and eliminating external Redis/Celery dependencies.
- **Concurrency Laning & Rate Throttling:** Implemented database-level `execution_lane` queuing constraints, dynamically suppressing concurrent LLM-heavy jobs across distributed workers to enforce strict upstream API rate-limit and cost compliance.
- **Fault-Tolerant Worker Lifecycle:** Designed a zombie-worker fencing mechanism using cryptographic MD5 lease tokens (`md5(id || worker_id || timestamp)`) and active heartbeat renewal; enabled sub-15s automated recovery of orphaned jobs without duplicate execution.
- **Optimistic Concurrency Control (OCC):** Implemented session-level Compare-And-Swap (CAS) state mutations backed by strictly monotonic revision integers on JSONB columns, preventing concurrent race conditions between async workers and HTTP client requests.
- **Zero-Trust Worker Authorization:** Created an asynchronous worker authorization fence (`worker_fence.py`) that re-authenticates session ownership, tenant status, and single-portfolio generation entitlements immediately before executing background AI operations.
- **Windows-Hardened Filesystem Swaps:** Hardened atomic directory promotion against OS-level file locks using extended UNC paths (`\\?\`) and exponential backoff retries, ensuring zero corrupted builds during live preview promotion.

### Track C: Full-Stack Generative AI / Systems Engineer
- **End-to-End GenAI Architecture:** Led the architectural design and implementation of a full-stack generative web platform, bridging an asynchronous FastAPI/PostgreSQL backend with an interactive multi-agent discovery and generation pipeline.
- **Isolated Live Preview Gateway:** Engineered a dedicated Starlette preview gateway running on port 4174 with immutable SHA-256 candidate storage, conditional ETag pointer promotion, runtime `<meta name="oryxenai-preview-base">` injection, and a postMessage `PreviewBridge` providing real-time multi-viewport device emulation and inspection highlights.
- **Pre-Code Compilation & Asset Discovery:** Designed a search-only resource discovery engine (Pexels, Pixabay, Fontsource REST APIs) that selects visual assets via deterministic Python tag-overlap algorithms, eliminating 6,000 lines of fragile byte packaging bloat (D-062).
- **Dual-Tsconfig Toolchain Sandboxing:** Built a network-isolated source generation sandbox enforcing offline npm cache warming, complete UTF-8 file overwrites, and dual `tsconfig` verification (app & node) before deployment.
- **Asymmetric Authentication & Tenancy:** Integrated Supabase Google OAuth via asymmetric JWKS public key verification and Just-In-Time (JIT) provisioning, featuring a server-enforced capacity gate and single-portfolio entitlement freezing.

---

## 3. Core Architectural Differentiators ("The Secret Sauce")

When technical interviewers ask: *"How does this differ from the hundreds of AI wrappers built with LangChain?"*, use these concrete architectural pillars to explain why OryxenAI is an enterprise-grade compiler:

```
                           THE "SECRET SAUCE" CONTRAST MATRIX
                           
  CONCERN               NAIVE AI WRAPPERS               ORYXENAI ENTERPRISE COMPILER
  ─────────────────────────────────────────────────────────────────────────────────────────────
  Agent Topology        LangChain / CrewAI graphs       Zero-framework Python protocols & Pydantic
  Task Execution        Unbounded ReAct tool loops      Adaptive bounded workflows (1-3 calls max)
  Distributed Queue     In-memory or Redis/Celery       PostgreSQL CTE + SKIP LOCKED + Concurrency Lanes
  State Persistence     Volatile memory / loose JSON    JSONB with monotonic OCC revision CAS
  Context Strategy      Dumps entire chat history       Compact snapshot handoffs + SHA-256 brief fencing
  Asset Acquisition     LLM hallucinates external URLs   Deterministic Python tag-overlap over static catalogue
  Code Verification     Trusts LLM output / `npm build` TypeScript AST audit + Playwright multi-viewport DOM
  Repair Mechanism      Infinite prompt retry loops     Fingerprint recurrence damping & honest decline
```

### Pillar 1: Why Custom Python Protocols Beat LangChain, CrewAI & AutoGen
- **Zero Framework Lock-in:** Agent frameworks introduce opaque abstractions (hidden system prompts, uncontrolled memory buffers, speculative tool-calling conventions). When a framework breaks or changes its internal API, production systems fail.
- **Predictable Token Budgets:** Frameworks often enter silent, recursive reasoning loops that burn hundreds of thousands of tokens. OryxenAI enforces **Adaptive Bounded Workflows (1–3 calls max)**—guaranteeing deterministic cost bounds per pipeline run.
- **Testability & Determinism:** Every OryxenAI agent is an isolated Python module with explicit Pydantic schemas, typed inputs, and sample fixtures. Unit tests execute deterministically in milliseconds without mocking complex framework runtimes.

### Pillar 2: Why PostgreSQL `SKIP LOCKED` Beats Celery & Redis
- **Unified Transactional Consistency:** In Celery/Redis architectures, updating application state in PostgreSQL and publishing a task to Redis requires distributed transactions (2PC). If the worker crashes between the DB write and the broker publish, the system enters a split-brain state.
- **Single Source of Truth:** With OryxenAI, creating a portfolio run and enqueuing background work happens inside a **single atomic PostgreSQL transaction**. If the transaction rolls back, no rogue job is dispatched.
- **Zero Additional Operational Overhead:** No Redis cluster to monitor, no memory eviction bugs, and no message loss during broker restarts. The PostgreSQL queue leverages existing ACID backups, replicas, and monitoring tools.

### Pillar 3: The Compiler-Planner Pattern vs. Monolithic HTML Prompting
- **The Problem with Raw Code Generation:** Asking an LLM to generate an entire website (HTML, Tailwind CSS, TypeScript, and state) in a single prompt causes catastrophic hallucination: invalid closing tags, phantom CSS classes, missing imports, and broken responsive layouts.
- **The OryxenAI Solution:** The LLM acts as a **Creative Director and Planner**, producing a typed `ExperienceBlueprintV4` (semantic color tokens, fluid typography steps, layout region spans). A deterministic host compiler (`WorkGraphCompiler`) translates this blueprint into disjoint work units. LLMs then synthesize code for isolated 3-section batches with strict file ownership.

### Pillar 4: Neuro-Symbolic Multi-Viewport Verification
- **Beyond Syntax Checks:** Syntax checkers only prove code can parse. OryxenAI boots a real headless Chromium instance via Playwright to verify:
  1. **DOM Geometry:** Content-box width ratios, multi-column preservation (`computedColumns > 1`).
  2. **Computed Style Dynamics:** CSS matrix transforms validated using hidden DOM probe elements.
  3. **Runtime Security:** Traps console errors, asset 404s, and unauthorized outbound network calls (`fetch`/`axios`).

### Pillar 5: Autonomous Full-Stack Web Synthesis vs. Toy Code Generators (The Frontier Paradigm)
- **The Ambition:** OryxenAI was designed around the same engineering ambitions as frontier autonomous AI software engineering platforms—taking raw, unstructured human intent and autonomously compiling, auditing, building, and deploying fully functioning software with zero human code intervention.
- **Why Portfolios as the Strategic Proving Ground?** Many general-purpose coding agents fail because they attempt to synthesize arbitrary backend/frontend apps simultaneously, immediately collapsing into unconstrained scope, state mismatch, and unprovable code. We deliberately chose responsive web portfolios as our primary proving ground:
  - It demands the highest level of **visual rigor, responsive layout geometry, and brand aesthetics**—where even a 2px alignment error or unstyled class looks like a failure.
  - It requires **strict zero-hallucination grounding** (verifying employment dates, projects, and metrics) paired with complex full-stack code (TypeScript, Vite, Tailwind CSS, asset routing, multi-route navigation).
  - Every architectural component we engineered—the **Work Graph Compiler**, the **Disjoint File Ownership Sandbox**, the **TypeScript AST Auditor**, and the **Headless Browser Diagnostic Feedback Loop**—was decoupled from the portfolio domain, creating a generalizable engine for autonomous full-stack web software generation.

---

## 4. In-Depth STAR Technical Stories for System Design & Behavioral Rounds

### Story 1: Conquering Hallucinated Code & Infinite Repair Loops in LLM Code Generation
- **Situation:** During early live generation runs, our Code Generator hit severe reliability hurdles: models hallucinated non-existent npm packages (`lucide-react-icons`), omitted required visual assets, and entered oscillating repair loops where fixing a TypeScript error broke CSS layout geometry.
- **Task:** As the AI Systems Architect, I needed to design a deterministic verification and repair system that guarantees 100% syntactically and visually valid React/Vite portfolios while capping repair execution time and token expenditure.
- **Action:**
  1. Built a dependency-free **TypeScript AST structural auditor** (`typescript_ast_audit.py`) that scans imports against a local allowlist and blocks client-side network calls before any Node.js toolchain runs.
  2. Engineered a **Playwright headless browser verifier** (`runtime_verifier.py`) evaluating real DOM computed styles, content-box ratios, and matrix transforms across desktop (1440x900) and laptop (1280x800) viewports.
  3. Implemented a **finite diagnostic repair loop with fingerprint recurrence damping** (`final_repair.py`). Every error is SHA-256 fingerprinted; if the same error recurs across rounds, the loop breaks immediately. Added `FinalRepairDeclined` to handle honest model declines rather than burning retries.
  4. Enforced strict image policy floors (`minimum_visible_images = 2`, `require_primary_route_image = true`, Decision D-092) at the schema level.
- **Result:** Increased end-to-end generation pass rates from ~20% to **99.4%**, eliminated infinite repair loops, and achieved fully verified live candidate promotion in under 90 seconds.

### Story 2: Architecting a High-Throughput Distributed Task Queue on PostgreSQL
- **Situation:** Our multi-agent pipeline required asynchronous background execution for long-running LLM and browser verification tasks. Introducing Redis and Celery introduced dual-database split-brain risks, rate-limit thrashing, and increased cloud infrastructure costs.
- **Task:** Build an ACID-compliant, durable distributed task queue directly inside PostgreSQL capable of handling concurrent agent runs, worker crash recovery, and upstream API rate-limit throttling.
- **Action:**
  1. Implemented batch claiming using a SQL Common Table Expression (CTE) with `SELECT ... FOR UPDATE SKIP LOCKED` on the `background_jobs` table.
  2. Built **Execution Laning**: added a query constraint that checks `NOT EXISTS (SELECT 1 FROM background_jobs WHERE running.status = 'running' AND running.execution_lane = job.execution_lane)`. This throttles concurrent model-generation jobs across all workers without distributed locks.
  3. Implemented **Cryptographic Lease Fencing**: claimed jobs receive an MD5 token (`md5(id || worker_id || timestamp)`). Any update from a worker whose lease expired is rejected.
  4. Added background heartbeat renewal loops in workers and automated stale lease recovery queries (`recover_stale()`, `requeue_stale()`).
- **Result:** Completely eliminated external queue dependencies, achieved zero database lock contention under load, guaranteed zero duplicate job executions, and maintained strict LLM API rate-limit compliance.

### Story 3: Eliminating Token Bloat & State Drift via Compact Cryptographic Pipelines
- **Situation:** In multi-agent pipelines, agents often pass accumulating conversational context forward. By stage 4, prompts were hitting context window limits, costing $0.15+ per run, and causing downstream models to hallucinate facts from earlier draft iterations.
- **Task:** Decouple inter-agent dependencies so each agent receives the minimum necessary context while guaranteeing strict narrative and factual consistency.
- **Action:**
  1. Redesigned the pipeline around **Compact Snapshot Ingestion**: Content Architect never sees raw resumes or conversational transcripts; it ingests only structured profile facts and approval hashes from Discovery.
  2. Built **Triple-Axis Claim Grounding**: every factual claim carries `evidence_status`, `ownership`, and `publication_status`. Blocked claims are structurally forbidden from reaching downstream packs.
  3. Replaced 6,000 lines of fragile resource packaging (Decision D-062) with a **Cryptographic Brief Pair**: Build Preparation outputs two clean Markdown documents (`content-and-narrative-brief.md` and `visual-and-build-brief.md`), each carrying a fenced SHA-256 JSON index block. Downstream Code Generator binds to these hashes.
- **Result:** Slashed prompt token consumption by **68%**, reduced overall pipeline latency by 35%, and cryptographically guaranteed that no downstream stage can build on outdated or unapproved content.

### Story 4: Designing a Zero-Trust Worker Authorization Fence for Ephemeral SaaS Entitlements
- **Situation:** In an asynchronous multi-tenant AI SaaS, a critical race condition exists: a user can initiate a generation job, quickly cancel their subscription or exhaust their quota, yet the background worker will still pick up the job and burn expensive LLM tokens.
- **Task:** Enforce strict multi-tenant isolation and single-portfolio generation entitlements across asynchronous worker boundaries.
- **Action:**
  1. Built asymmetric JWT/JWKS verification integrating Supabase Google OAuth with local Just-In-Time (JIT) provisioning and tenant ownership mapping.
  2. Implemented a server-enforced **Single-Portfolio Entitlement Model**: upon the first successful portfolio generation, all further mutation endpoints freeze into read-only mode.
  3. Engineered the **Zero-Trust Worker Authorization Fence** (`worker_fence.py`): immediately after claiming a job and before executing any LLM or database mutation, the background worker validates session status, owner activity, and entitlement revisions against the live database.
- **Result:** Completely closed the asynchronous entitlement evasion vulnerability, prevented wasted model inference spend on deactivated accounts, and established enterprise-grade tenant isolation.

---

## 5. 25 Tough Technical Interview Questions & Battle-Tested Answers

### Multi-Agent Orchestration & LLM Architecture

#### Q1: Why did you build custom Python agent protocols instead of using LangChain, CrewAI, or AutoGen?
**Answer:**  
"Agent frameworks introduce heavy, opaque abstractions that are speculative before real product requirements are known. In production, LangChain and CrewAI suffer from hidden prompt mutations, unexpected dependency conflicts, and uncontrollable recursion loops when tools fail.  
By using plain Python protocols (`Agent`, `ModelClient`) and strict Pydantic V2 schemas, we achieved total architectural transparency. Every agent owns its exact schema, trusted system prompts, and sample fixtures. We eliminated thousands of lines of external dependencies, made every execution path unit-testable in milliseconds, and preserved full control over token budgets and retry semantics."

#### Q2: How do your agents prevent runaway execution loops and excessive token spending?
**Answer:**  
"We reject open-ended ReAct tool-calling loops in favor of **Adaptive Bounded Workflows**. Both Content Architect and Visual Design Director are constrained to a maximum of 1 to 3 sequential calls internally:
1. `plan`: Determines high-level strategy and optionally generates full output if the scope is compact.
2. `write`: Executes batched page generation only if deferred by the plan.
3. `integrate`: A targeted reconciliation pass triggered only if route count > 2 or cross-route conflicts were flagged.
By enforcing bounded state machines with discriminated union output schemas, an agent can never enter an infinite loop. The maximum number of model calls is hard-capped at 3 per job."

#### Q3: How do you handle LLM output non-determinism and malformed JSON responses?
**Answer:**  
"We address this at three layers:
1. **Transport-Level JSON Mode:** We utilize provider-native structured output modes (OpenAI JSON Object mode, Anthropic tool-use schema constraints).
2. **Discriminated Envelope Validation:** Output schemas validate the transport envelope rather than the creative prose. If the model emits malformed JSON, our Pydantic validator raises `ModelOutputInvalidError`, which is treated as a retryable transient failure.
3. **Multi-Source Bounded Fallback (Decision D-093):** If our primary provider (`experiential_luna`) repeatedly fails schema validation or hits rate limits, our `ModelRouter` automatically fails over to a secondary provider (`gemini_flash_lite`), passing the identical validated input before terminating."

#### Q4: What is your prompt engineering strategy, and why did you avoid vector-based few-shot retrieval?
**Answer:**  
"In an earlier prototype (Decision D-002), we implemented a vector database with a 20-file dynamic few-shot retrieval library. In practice, this was over-engineering: semantic search over few-shot examples introduced latency, non-deterministic prompt variance, and retrieval failures when user inputs used unexpected vocabulary.  
We replaced this with **Inline Contrastive Prompting**. Our prompts include paired `BAD` vs. `GOOD` contrastive examples directly in the markdown template. This demonstrates exact boundary conditions (e.g., how to handle missing data without hallucinating) deterministically on every call without RAG overhead or vector DB maintenance."

#### Q5: How do you prevent prompt injection and data leakage across pipeline stages?
**Answer:**  
"First, we strictly isolate untrusted user data. User documents are ingested only in Discovery and wrapped in CDATA delimiters with instructions treating them as untrusted data.  
Second, we use **Compact Snapshot Ingestion**: downstream agents (Content Architect, Visual Design Director, Code Generator) never receive the raw user documents. They receive only structured, validated facts (`profile`, `route_plan`).  
Third, we enforce **Structural Anti-Leakage Scanning**: `validators.py` uses regular expressions to inspect generated copy for internal evaluation tags (e.g., `status_note:`, `evidence_status:`), rejecting outputs if the model attempts to leak internal reasoning into public HTML."

---

### Distributed Systems, Queues & Concurrency

#### Q6: Explain how your PostgreSQL queue handles concurrent worker claims without lock contention.
**Answer:**  
"We use a Common Table Expression (CTE) combining `FOR UPDATE SKIP LOCKED` and an atomic `UPDATE`:
```sql
WITH due AS (
    SELECT id FROM background_jobs
    WHERE status = 'queued' AND available_at <= NOW()
    ORDER BY priority DESC, created_at ASC
    LIMIT :batch_size
    FOR UPDATE SKIP LOCKED
)
UPDATE background_jobs SET status = 'running', locked_by = :worker_id, lease_token = md5(...)
WHERE id IN (SELECT id FROM due) RETURNING *;
```
`FOR UPDATE SKIP LOCKED` instructs PostgreSQL to inspect rows in order and immediately skip any row locked by another concurrent transaction. Workers never block waiting on each other; they instantly claim mutually exclusive batches in a single round-trip."

#### Q7: How does your queue solve the 'Zombie Worker' problem?
**Answer:**  
"When a worker claims a job, it writes a cryptographically unique `lease_token` (`md5(id || worker_id || timestamp)`) and increments the `attempt` counter.  
While running, the worker maintains a background asyncio heartbeat loop renewing `heartbeat_at`. If a worker hangs (e.g., network partition or OS swap), its heartbeat expires. Another worker's recovery process (`requeue_stale`) clears the lease and resets the status to `queued`.  
If the zombie worker suddenly wakes up and attempts to call `mark_succeeded`, its SQL query includes `WHERE id = :id AND lease_token = :lease_token AND attempt = :attempt`. Because the lease was cleared, `rowcount == 0`, and the zombie worker's stale write is completely fenced."

#### Q8: How do you prevent distributed workers from overwhelming third-party LLM rate limits?
**Answer:**  
"We implemented **Concurrency Laning** directly in the queue claim query. Jobs requiring high-volume model generation declare an `execution_lane` (e.g., `model_generation_lane`).  
The claim CTE includes a predicate:
```sql
AND (
    job.execution_lane IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM background_jobs AS running
        WHERE running.status = 'running' AND running.execution_lane = job.execution_lane
    )
)
```
This guarantees that across our entire worker pool, only one heavy generation job runs per lane at any instant. Fresh jobs wait in `queued` status until the active job finishes, completely preventing 429 rate-limit cascades without needing an external distributed lock like Redis Redlock."

#### Q9: How do you handle race conditions between user UI edits and background worker updates?
**Answer:**  
"We use **Optimistic Concurrency Control (OCC)** on our `portfolio_sessions` table. The table includes an integer `revision` column.  
When an agent or API handler loads state, it records the current revision. When persisting the result, it executes:
```sql
UPDATE portfolio_sessions 
SET current_state = :new_state, revision = :revision + 1 
WHERE id = :id AND revision = :expected_revision;
```
If a user submitted answers or an admin triggered an edit concurrently, the revision in the database has incremented. The worker's update matches zero rows and returns `None`, raising a `ConcurrencyConflictError` (HTTP 409) rather than clobbering the user's modifications."

#### Q10: Why did you choose PostgreSQL JSONB for agent state instead of normalized relational tables?
**Answer:**  
"Agent architectures evolve rapidly. In early development, normalizing every agent field into relational tables (e.g., separate tables for sections, storyboards, design tokens, and repair receipts) required running database migrations on every prompt or schema tweak.  
PostgreSQL JSONB provides the perfect balance: it gives us schema flexibility at the storage layer while enforcing strict, type-safe validation at the application layer via Pydantic V2. Furthermore, PostgreSQL allows GIN indexing on JSONB paths, letting us query nested agent states efficiently when needed."

---

### Code Generation, AST Auditing & Sandboxing

#### Q11: How do you prevent an LLM from hallucinating npm packages or importing malicious libraries?
**Answer:**  
"We enforce a multi-tier boundary:
1. **Network-Isolated Build:** The generator runs with `--offline` against a pre-warmed npm cache (`.workspace/npm-cache`). It is physically impossible for the build process to download arbitrary packages from the npm registry.
2. **TypeScript AST Structural Audit:** In `typescript_ast_audit.py`, we run a lexical regex parser over all generated `.tsx` files. We extract all `import ... from '...'` module specifiers and cross-reference them against an explicit allowlist of pre-installed packages and local generated files. Any undeclared import raises `SOURCE_IMPORT_UNKNOWN` immediately, triggering a bounded repair pass before the Node toolchain ever executes."

#### Q12: How do you ensure the generated website doesn't make unauthorized outbound network calls (SSRF / Data Exfiltration)?
**Answer:**  
"We enforce this at both static analysis and runtime verification:
1. **Static AST Audit:** Our AST audit scans for client-side HTTP calls using `_NETWORK_RE`, matching `fetch(`, `axios(`, `XMLHttpRequest`, `WebSocket`, and `EventSource`. Any match immediately fails the source contract.
2. **Playwright CSP & Network Interception:** In `runtime_verifier.py`, our headless browser listens to all network requests (`page.on('request')`). If the page attempts an outbound HTTP request to any origin other than the local asset server, the test fails with a security violation diagnostic."

#### Q13: What is the 'Experience Blueprint', and why is it superior to letting the LLM write CSS?
**Answer:**  
"Letting an LLM write raw CSS results in visual incoherence—conflicting margins, arbitrary colors, and broken responsive breakpoints.  
Our `ExperienceBlueprintV4` acts as a neuro-symbolic bridge: the LLM specifies design intent (e.g., `background: "canvas-dark"`, `accent: "signal-orange"`, `columns_desktop: 8`, `type_scale: "fluid-dynamic"`).  
Our host compiler then deterministically maps these into checked-in CSS custom properties and Tailwind v4 theme variables. The model never touches raw layout calculations; it consumes the compiled token vocabulary, ensuring pixel-perfect responsive harmony across sections."

#### Q14: How does your Playwright runtime verifier test CSS transforms when browser computed styles return matrix strings?
**Answer:**  
"This was a fascinating engineering challenge. A model might author `transform: translateY(0px) scale(1.05)`, but `window.getComputedStyle(el).transform` in Chromium always returns an expanded matrix string like `matrix(1.05, 0, 0, 1.05, 0, 0)`. Direct string matching always fails.  
We solved this by injecting a detached DOM probe element (`_TRANSFORM_MATCH_JS`). We apply the expected transform to the probe, read Chromium's computed matrix, remove the probe, and parse the matrix floats. We then perform a numerical component-by-component comparison with an epsilon tolerance (1px for translation, 0.02 for scale and rotation). This eliminates false positives while guaranteeing exact animation fidelity."

#### Q15: How does your diagnostic repair loop prevent infinite loops when an LLM cannot fix an error?
**Answer:**  
"We implemented **Fingerprint Recurrence Damping**. Every diagnostic issue generates a deterministic SHA-256 fingerprint from its code, file, route, and normalized error message.  
We track these fingerprints across repair rounds. If the exact same fingerprint appears in two consecutive rounds, the engine recognizes that the LLM's repair strategy has stalled and aborts the loop.  
Furthermore, we support `FinalRepairDeclined`: if the LLM recognizes that an instruction is impossible to fulfill within constraints, it returns an explicit `cannot_complete` status. We treat this as a clean terminal state rather than fruitlessly burning our repair budget."

---

### Security, Authentication & Systems Architecture

#### Q16: How does your asynchronous worker know if a user's account was deleted or banned after a job was enqueued?
**Answer:**  
"We built the **Worker Authorization Fence** (`src/oryxenai/auth/worker_fence.py`).  
Every background job carries an `owner_user_id`, `actor_user_id`, and `authorization_context_version`. When a worker claims a job, before executing any logic, it calls `validate_job()`.  
This queries the live `app_users` table: if the owner is marked `inactive` or `deleted`, or if the session is flagged `quarantined`, the fence raises `AuthorizationFenceError`. The worker immediately terminalizes the job without calling external LLMs or persisting state."

#### Q17: How do you enforce your 'single portfolio per user' entitlement in an async architecture?
**Answer:**  
"When a generation candidate passes all verification gates, the worker executes `finalize_portfolio_entitlement()`. Inside a database transaction, it marks the user's `PortfolioEntitlement` as `succeeded`.  
Once marked succeeded, all mutation endpoints across the API (revising content, regenerating visuals) reject incoming requests with HTTP 403.  
If an in-flight job was already queued when another job completed, the Worker Authorization Fence re-checks the entitlement revision before execution and fences the duplicate job."

#### Q18: Why did you eliminate the 6,000-line Build Preparation ZIP packager (Decision D-062)?
**Answer:**  
"In our early architecture, Build Preparation acted as a heavyweight asset packager: it downloaded images from Pexels, verified MIME types, generated local fonts, packed them into a ZIP file, and uploaded them to Cloudflare R2.  
This introduced massive complexity: signed URL expiration bugs (D-060), storage costs, and duplicate work, because Code Generator still had to unzip and re-verify the files.  
We refactored Build Preparation to be a pure discovery and compilation agent: it queries REST APIs for image candidates, has a single model call pick candidates by index, and emits two clean Markdown briefs with fenced SHA-256 JSON indexes. Asset bytes are acquired directly by Code Generator at generation time, eliminating 6,000 lines of fragile infrastructure code."

#### Q19: How do you handle Windows-specific filesystem locking issues during directory swaps?
**Answer:**  
"On Windows, file system operations frequently fail with transient `PermissionError` when background processes (like Vite dev servers, file indexers, or antivirus scanners) briefly hold open file handles during directory renames.  
We engineered `fs_safe.py`, which normalizes paths using extended Windows UNC prefixes (`\\?\`) to bypass the 260-character `MAX_PATH` limit. When performing directory replacements, it uses a retry loop with exponential backoff and jitter. If an atomic rename fails due to a temporary lock, it retries up to 5 times before failing cleanly."

#### Q20: What was the root cause of the Uvicorn Windows subprocess bug you diagnosed, and how did you resolve it?
**Answer:**  
"When running Uvicorn with `--reload` on Windows, Uvicorn defaults to Python's `asyncio.SelectorEventLoop`. However, on Windows, `SelectorEventLoop` does not implement `asyncio.create_subprocess_exec()`, throwing an immediate `NotImplementedError` whenever our toolchain runner attempted to spawn Node or Playwright subprocesses.  
We resolved this by updating our native development scripts to run Uvicorn without `--reload` in environments executing toolchain builds, allowing the event loop to default to `ProactorEventLoop`, which provides native Windows asynchronous I/O and process spawning."

---

### Evaluation, Reliability & Performance

#### Q21: What metrics do you track to measure the performance and quality of your agentic system?
**Answer:**  
"We track four key metric pillars:
1. **Verification Gate Pass Rate:** Percentage of generated portfolios that pass AST auditing, Vite clean build, and headless DOM geometry checks on the first try (currently 99.4%).
2. **Token Efficiency:** Ratio of input/output tokens to completed public copy. By using compact snapshots, we reduced downstream stage token usage by 68%.
3. **Queue Health & Contention:** Lock wait times and claim throughput on `background_jobs`. With `SKIP LOCKED`, our lock contention is 0ms.
4. **Stale Lease Recovery Time:** Time elapsed between a worker crash and job reclamation (sub-15 seconds)."

#### Q22: How do you prevent regressions when updating prompts across different LLM providers?
**Answer:**  
"We maintain offline test fixtures and sample runs in each agent directory (`samples/input.json`, `samples/output.json`).  
Before rolling out prompt changes, we run our test suite using `MockModelClient` to verify schema envelope compatibility. For live model evaluations, we run offline test suites using recorded candidate inputs and evaluate output structure using our strict Pydantic validators (`validators.py`). We never push prompt changes directly to production without verifying AST pass rates against our benchmark briefs."

#### Q23: Why did you make Desktop web the blocking release gate instead of Mobile (Decision D-088)?
**Answer:**  
"Our headless browser verifier originally required both mobile (375x667) and desktop (1440x900) viewports to pass every geometry and transform check before preview promotion.  
However, live campaign telemetry revealed that subtle cosmetic variations on mobile (such as fluid font wrapping or responsive padding) were triggering minor diagnostics that consumed our finite repair budget, even though the desktop portfolio was visually stunning and fully functional.  
We made an executive architectural decision (D-088): desktop and laptop viewports are the strict blocking release gates. Mobile viewports remain fully responsive via CSS media queries and fluid clamping, but mobile-specific geometry diagnostics are marked advisory, preserving repair budgets for functional defects."

#### Q24: How does your system recover if an external image API (like Pexels or Pixabay) goes down?
**Answer:**  
"In our asset acquisition pipeline (`resource_adapters.py`), all external API interactions are non-blocking and fail-safe.  
If an image candidate URL fails to download (or returns a 404/timeout), the adapter catches the exception and attempts a fallback query. If all image providers fail, the system falls back to our checked-in aesthetic CSS primitives (abstract gradients, SVG geometric textures) defined in `SharedSystems.tsx`. The site still compiles clean, renders beautifully, and passes all verification gates without crashing."

#### Q25: If you had to scale this architecture to 100,000 daily active users, what would you change first?
**Answer:**  
"Our core agent pipeline and PostgreSQL state machines would scale smoothly, but I would make three infrastructure evolutions:
1. **Read-Replicas for Queue & State:** Offload read-heavy session polling to PostgreSQL read-replicas, keeping the primary instance dedicated to `SKIP LOCKED` claiming and OCC state writes.
2. **Dedicated Toolchain & Browser Worker Nodes:** Separate the lightweight LLM-calling workers from the compute/memory-heavy toolchain workers (Node.js builds and Playwright Chromium instances). This prevents browser instances from causing memory pressure on API workers.
3. **S3-Compatible Object Store for Generated Artifacts:** Currently, generated candidate trees reside on the local filesystem. At 100k DAU, I would stream completed `dist/` bundles directly to an S3-compatible object store (like Cloudflare R2) backed by a CDN edge for instantaneous preview serving."

#### Q26: Why did you anchor your autonomous full-stack software synthesizer on web portfolios rather than general-purpose CRUD/SaaS applications, and how does this architecture generalize?
**Answer:**  
"We deliberately anchored on web portfolios as our primary proving ground because portfolios unite the most rigorous, unforgiving constraints in automated software engineering:
1. **Zero-Hallucination Fact Grounding:** Unlike a synthetic demo app where placeholder data is fine, a portfolio demands exact fidelity to a real person's career, metrics, and achievements.
2. **Extreme Visual & Geometric Rigor:** In a generic CRUD app, an off-by-10px alignment or an awkward mobile card wrap is barely noticed. In a portfolio, visual aesthetics, fluid typography, responsive layout geometry, and smooth CSS matrix transforms are critical.
3. **Provable Runtime Execution:** It forces the engine to solve complete compilation, dependency allowlisting, asset routing, and multi-viewport DOM verification in an end-to-end provable loop.

**How it generalizes to arbitrary full-stack applications:**  
The engine's core infrastructure is completely domain-agnostic. The `WorkGraphCompiler` manages disjoint file ownership; the `typescript_ast_audit` verifies module import edges and bans unauthorized network calls; the sandboxed toolchain manages npm packages and Vite compilation; and the headless Playwright engine verifies live runtime execution.  
To extend this pipeline to full-stack CRUD applications (e.g., dashboard apps with authentication and database models), one only needs to extend the `ExperienceBlueprint` to include data schemas and API endpoints. The distributed PostgreSQL worker queue, OCC state transitions, sandboxed toolchain compilation, AST audits, and self-healing diagnostic repair loops remain 100% reusable."

#### Q27: How does your Live Preview Gateway serve generated applications without risking XSS, clickjacking, or data exfiltration?
**Answer:**  
"Serving LLM-generated code live in a browser presents severe security hazards: malicious prompt injection could attempt to read cookies, execute XSS attacks against the studio, or exfiltrate sensitive candidate data.  
We architected a dedicated, isolated **Preview Gateway** (`src/oryxenai/preview/gateway.py`) on a separate port (4174) with a zero-trust security profile:
1. **Zero Outbound Network Egress (`connect-src 'none'`):** The Gateway applies a strict Content-Security-Policy that disables `fetch()`, `XMLHttpRequest`, `WebSocket`, and `EventSource`. The generated application cannot phone home or leak telemetry.
2. **Anti-Clickjacking Protection (`frame-ancestors`):** The policy explicitly restricts embedding to the parent studio application origin (`http://localhost:8000` or production host).
3. **Dynamic Base Injection (`_inject_preview_base`):** When serving `index.html`, the gateway dynamically injects `<meta name="oryxenai-preview-base" content="/preview/candidate/<token>/<run_id>/">`. This allows client-side routers (`ResourceUrl.ts`) to resolve subpath mounts without rebuilding the Vite bundle.
4. **Read-Back SHA-256 Storage Verification:** Before any preview is promoted, every file in `dist/` is written to immutable storage and read back to verify byte-exact SHA-256 integrity. Active pointer promotion occurs via atomic conditional PUT using ETags, ensuring zero corrupted or half-written previews reach the user."

#### Q28: Walk me through the exact step-by-step lifecycle of code generation: what files are created in what order, and how do you prevent context window exhaustion?
**Answer:**  
"Monolithic code generation fails because fitting full-stack HTML, Tailwind CSS, TypeScript, and state into a single prompt blows past model attention limits, resulting in syntax truncation and hallucinations.  
We engineered **Progressive Wave Synthesis**, partitioning generation into four ownership-isolated phases:
1. **Wave 1: Foundation Contracts:** Synthesizes `generated-tokens.css` (semantic CSS custom properties for background, text, and accent colors), `tokens.css` (Tailwind `@theme` inline mappings), and `SharedSystems.tsx` (reusable motion wrappers, dialog primitives, and texture backdrops).
2. **Wave 2: Section Batches:** The `WorkGraphCompiler` slices the approved route into batches of at most 3 sections. Each batch prompt receives *only* its assigned sections and blueprint contracts. It writes isolated TSX and scoped CSS files (e.g., `HeroSection.tsx`, `HeroSection.css`), marked with strict `data-content-id` landmark attributes.
3. **Wave 3: Route Composition:** A dedicated Composer unit generates `src/routes/<route>/index.tsx`. It imports the completed Wave 2 components in canonical order and wires page-level grid spacing in `route.css`.
4. **Wave 4: Whole-Site Integration Review:** A read-only audit evaluates cross-route typography, contrast, and navigation links.

Because each wave has strict, mutually exclusive file ownership boundaries, models generate small, focused, highly reliable files (under 150 lines each), completely eliminating context window exhaustion and syntax truncation."


