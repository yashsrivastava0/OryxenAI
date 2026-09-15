# OryxenAI: Deep Technical Architecture & System Design Analysis

> **Canonical System Reference & Technical Deep Dive**  
> **Author Focus:** AI Systems, Agentic AI, LLM Infrastructure, Distributed Systems & AI Backend Engineering  
> **Target Caliber:** Senior / Staff-Level AI & Backend Engineer (3+ Years Production Experience)  
> **Scope:** Complete Backend, Durable Distributed Worker Queue, Multi-Agent Pipeline, Sandboxed Toolchain Compilation, AST Auditing, Headless Browser Runtime Verification, and Security Fencing. (Excludes non-critical frontend cosmetics).

---

## 1. Executive Summary & Core Engineering Philosophy

### 1.1 What is OryxenAI?
**OryxenAI** is an enterprise-grade, **autonomous AI full-stack software engineering and web synthesis engine** designed to transform unstructured user intent, domain documentation (resumes, CVs, case studies, project logs), and creative requirements into fully compiled, verified, and deployable production web applications.

At its core, OryxenAI was conceived to solve the fundamental challenge of **autonomous end-to-end software synthesis**: bridging the gap between natural language intent and reliable, production-grade web software without human developer intervention. 

While general-purpose code generators often attempt to generate arbitrary software and fail due to unconstrained scope and fragile execution runtimes, OryxenAI establishes an **autonomous software engineering compiler pipeline**. The portfolio vertical was deliberately chosen as the premier proving ground for this architecture because it unites the most demanding constraints of autonomous web application engineering:
1. **Dense Fact Grounding & Anti-Hallucination:** Zero tolerance for fabricated metrics, employment dates, or unverified claims.
2. **Deterministic Full-Stack Compilation:** Complete TypeScript, Tailwind CSS, Vite toolchains, and multi-component state trees generated from scratch.
3. **Multi-Viewport Geometry & Visual Rigor:** Eliminating broken CSS layouts, overlapping cards, and unstyled utility classes through headless browser verification.
4. **Self-Healing Code Repair:** Dynamic diagnostic feedback loops that parse compiler and DOM errors to patch source code autonomously.

Unlike consumer AI "website builders" or superficial LLM wrappers that dump unvalidated markup into an iframe, OryxenAI operates as a **staged, multi-agent neuro-symbolic compiler**. It decomposes application creation into five discrete, bounded phases—**Discovery**, **Content Architecture**, **Visual Design Direction**, **Portfolio Build Preparation**, and **Code Generation & Verification**—enforcing strict cryptographic contracts, deterministic file ownership, AST-level source validation, and headless browser runtime geometry verification at every stage boundary. The entire pipeline is architected so that its core abstractions (Work Graph Compilers, AST Audits, Headless Verification, and Bounded Repair Loops) can generalize to full-stack web applications.

```
                    ORYXENAI HIGH-LEVEL ARCHITECTURAL TOPOLOGY
                   
  +-------------------------------------------------------------------------+
  |                             API GATEWAY                                 |
  |      FastAPI (Async) + Asymmetric Supabase JWT/JWKS Authentication       |
  |         Optimistic Concurrency Control (OCC) Session Repository         |
  +------------------------------------+------------------------------------+
                                       |
                   [Atomic Transaction Enqueue + CAS State]
                                       v
  +-------------------------------------------------------------------------+
  |                DISTRIBUTED DURABLE POSTGRESQL JOB QUEUE                 |
  |     CTE + "SELECT ... FOR UPDATE SKIP LOCKED" Batch Claim Engine       |
  |     Concurrency Laning (Throttled Model-Generation Execution Lanes)     |
  |        MD5 Lease Tokens + Heartbeat Renewal + Stale Lease Fencing       |
  +------------------------------------+------------------------------------+
                                       |
                     [Worker Reauthorization & Fencing]
                                       v
  +-------------------------------------------------------------------------+
  |                     AUTONOMOUS AGENTIC PIPELINE                         |
  |                                                                         |
  |  [Stage 1: Discovery]           9-State Machine, Envelope-Only JSON     |
  |            |                    Validations, Contrastive Prompts        |
  |            v                                                            |
  |  [Stage 2: Content Architect]   1-3 Bounded Calls, 3-Axis Claim         |
  |            |                    Grounding (Evidence/Ownership/Pub)      |
  |            v                                                            |
  |  [Stage 3: Visual Director]     Deterministic Catalogue Tag-Overlap     |
  |            |                    Lookup, Storyboards, Scene Mappings     |
  |            v                                                            |
  |  [Stage 4: Build Preparation]   Stage 0 Scope Compiler, Search-Only     |
  |            |                    Asset APIs, SHA-256 Fenced Brief Pair   |
  |            v                                                            |
  |  [Stage 5: Code Generator]      ExperienceBlueprintV4, WorkGraph,       |
  |                                 Progressive Wave Generation             |
  +------------------------------------+------------------------------------+
                                       |
                       [Generated Source Tree Ingestion]
                                       v
  +-------------------------------------------------------------------------+
  |              SANDBOXED COMPILATION & DETERMINISTIC VERIFIER             |
  |                                                                         |
  |  1. TypeScript AST Structural Audit (Edge checking, network bans)       |
  |  2. Toolchain Compilation & Typecheck (Dual tsconfig, Vite clean build) |
  |  3. Playwright Headless Browser Engine (Desktop 1440x900 / Laptop 1280) |
  |     - Content-Box Width Ratio Checks & Multi-Column Layout Invariants   |
  |     - Transform Matrix Matching via Detached DOM Probes                 |
  |     - Font Preloading, CSP & Outbound Network Leak Interception         |
  |  4. Finite Bounded Repair Loop (Fingerprint Recurrence Damping)         |
  |  5. Atomic Stable Preview Promotion (Windows fs_safe Directory Swaps)   |
  +-------------------------------------------------------------------------+
```

### 1.2 The Failure Modes of Typical GenAI Systems (and How OryxenAI Solves Them)
Building production-grade AI systems requires moving past the naive paradigms that cause 95% of LLM projects to fail in production:

| Naive / Junior Approach | Why It Fails in Production | The OryxenAI Engineering Solution | Relevant Decision / File |
| :--- | :--- | :--- | :--- |
| **Monolithic "Do-It-All" Prompt** | Context dilution, hallucinated facts, runaway token costs, and catastrophic model drift. | **Strict 5-Stage Separation of Concerns**. Each stage is an independent agent with isolated schemas and bounded execution. | `docs/architecture.md`, `DECISIONS.md` (D-008, D-015) |
| **LangChain / CrewAI / AutoGen** | Brittle abstractions, hidden prompt injections, uncontrollable infinite tool loops, and heavy external dependency trees. | **Zero Framework Bloat**. Plain Python protocols (`Agent`, `ModelClient`) and strict Pydantic V2 schemas. Full architectural control and instant debugging. | `DECISIONS.md` (D-001), `src/oryxenai/agents/shared/` |
| **Redis / Celery / RabbitMQ Queues** | Split-brain states between the broker and the application DB; loss of ACID transactional consistency during crash recovery. | **PostgreSQL-Native Durable Queue**. Atomic state updates and job enqueues inside the same DB transaction; `FOR UPDATE SKIP LOCKED` claiming. | `src/oryxenai/jobs/repository.py` |
| **Unbounded Agentic Tool Loops** | Models get stuck in infinite retry loops, burn API budgets, or fail silently under rate limits. | **Adaptive Bounded Workflows (1–3 Calls)**. Agents make at most 3 sequential calls internally (`plan` -> `write` -> `integrate`), never unbounded tool loops. | `agents/content_architect/`, `agents/visual_design_director/` |
| **Direct Web Browsing / Scraping by Models** | Hallucinated URLs, copyright/licensing liabilities, arbitrary latency spikes, and SSRF vulnerabilities. | **Deterministic Code-Mediated Retrieval**. In-memory tag-overlap matching against static catalogues and search-only REST API queries. | `resource_catalogue.py`, `DECISIONS.md` (D-031, D-062) |
| **Trusting LLM Code Generation** | Syntax errors, broken imports, phantom CSS variables, layout collisions, and inaccessible HTML. | **Deterministic AST Audit + Headless Chromium Verification**. Strict lexical verification, dual-tsconfig compilation, and real browser geometry checks. | `typescript_ast_audit.py`, `runtime_verifier.py` |

---

## 2. Distributed Systems & AI Backend Infrastructure

### 2.1 Durable PostgreSQL Job Queue (`background_jobs`)
Rather than introducing external operational dependencies like Redis, Celery, or Temporal, OryxenAI implements a high-throughput, ACID-compliant, durable distributed task queue directly on top of PostgreSQL.

#### Database Schema Highlights (`background_jobs`)
- **Job Identity & Payload:** `id` (UUIDv4), `job_kind` (e.g., `content_architect.build`, `code_generator.plan`), `payload` (JSONB), `priority` (INT).
- **Lease & Concurrency Fencing:** `status` (`queued`, `running`, `succeeded`, `failed`, `cancelled`), `locked_by` (worker instance ID), `locked_at` (TIMESTAMPTZ), `heartbeat_at` (TIMESTAMPTZ), `lease_token` (MD5 hash).
- **Execution Laning:** `execution_lane` (Nullable string, e.g., `model_generation_lane`).
- **Audit & Idempotency:** `idempotency_scope`, `idempotency_key`, `attempt`, `max_attempts`, `portfolio_session_id`, `owner_user_id`, `actor_user_id`, `authorization_context_version`.

#### Atomic Batch Claim Engine via CTE and `FOR UPDATE SKIP LOCKED`
Worker processes claim batches of due jobs without lock contention or duplicate execution using an advanced Common Table Expression (CTE) query:

```sql
WITH due AS (
    SELECT job.id FROM background_jobs AS job
    WHERE job.status = 'queued' 
      AND job.available_at <= :now
      AND job.attempt < job.max_attempts
      AND (:allowed_job_kinds IS NULL OR job.job_kind IN :allowed_job_kinds)
      -- Concurrency Laning Constraint:
      AND (
        job.execution_lane IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM background_jobs AS running
            WHERE running.status = 'running'
              AND running.execution_lane = job.execution_lane
        )
      )
    ORDER BY job.priority DESC, job.created_at ASC
    LIMIT :limit
    FOR UPDATE SKIP LOCKED
)
UPDATE background_jobs SET
    status = 'running',
    locked_by = :worker_instance,
    locked_at = :now,
    heartbeat_at = :now,
    attempt = attempt + 1,
    lease_token = md5(id::text || :worker_instance || clock_timestamp()::text),
    started_at = :now
WHERE id IN (SELECT id FROM due)
RETURNING *;
```

#### Key Concurrency & Reliability Invariants
1. **Execution Laning:** Heavy LLM-generating operations share an `execution_lane`. The queue query actively suppresses claiming queued jobs if another job in that lane is currently running. This guarantees global rate-limit compliance across distributed workers without external distributed semaphores.
2. **Cryptographic Lease Tokens (Zombie Worker Fencing):** When claiming a job, the worker generates a unique `lease_token = md5(id || worker_id || timestamp)`. When completing (`mark_succeeded` / `mark_failed`), the worker supplies its `lease_token` and `attempt`. If a worker hung due to an OS swap or GC pause and its lease expired, another worker may have reclaimed it; the original worker's write is rejected (`rowcount == 0`), preventing split-brain state corruption.
3. **Continuous Heartbeat Loop:** The worker runs an asynchronous background task (`Worker._renew_lease_loop`) updating `heartbeat_at` every few seconds while the LLM or toolchain is executing. A slow generation step is never mistaken for a crashed worker.
4. **Stale Lease Recovery & Lane Unblocking:** If a worker process terminates abruptly (SIGKILL/OOM), `recover_stale()` and `requeue_stale()` scan for expired heartbeats (`heartbeat_at <= NOW() - lease_seconds`). If attempts remain, the lease token is cleared and the job is requeued; if attempts are exhausted, it is terminalized as `JOB_ATTEMPT_CEILING_REACHED`.

### 2.2 Optimistic Concurrency Control (OCC) on Session Aggregates
Session state is maintained in `portfolio_sessions.current_state` as a JSONB column. To prevent concurrent writes between UI user interactions and asynchronous background workers:
- Every session row carries a strictly monotonic integer `revision`.
- State mutations use atomic Compare-And-Swap (CAS):
  ```sql
  UPDATE portfolio_sessions 
  SET current_state = :new_state,
      revision = expected_revision + 1,
      updated_at = NOW()
  WHERE id = :session_id AND revision = :expected_revision
  RETURNING *;
  ```
- If another process updated the state in the interim, the update returns `None`, raising a `ConcurrencyConflictError` (HTTP 409), forcing the caller to reload fresh state rather than blindly overwriting intermediate progress.

### 2.3 Provider-Neutral Model Architecture (`ModelClient` & `ModelRouter`)
All model-backed agents interact with LLMs via a strictly abstracted, provider-neutral boundary (`src/oryxenai/agents/shared/`):

```
                       MODEL ROUTING & EXECUTION LAYER
                       
                       +-----------------------------+
                       |    Agent Business Logic     |
                       +--------------+--------------+
                                      | calls
                                      v
                       +-----------------------------+
                       |     ModelRouter Service     |
                       |  (Reads config/models.toml) |
                       +--------------+--------------+
                                      | resolves
                                      v
                       +-----------------------------+
                       |     ModelClient Protocol    |
                       +--------------+--------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
+------------------+         +------------------+         +------------------+
| AnthropicAdapter |         |  OpenAIAdapter   |         |  GeminiAdapter   |
| (Messages API)   |         | (JSON-Object)    |         | (Flash/Pro Wire) |
+------------------+         +------------------+         +------------------+
```

#### Core Design Highlights
1. **Config-Driven Model Routing (`config/models.toml`):** Model providers, endpoints, and profiles are mapped logically per agent engine (e.g., `discovery = "experiential_luna"`, `code_generator_planner = "code_generator_planner"`). Changing a model or endpoint requires zero Python code modifications.
2. **Indirect Secret Resolution:** Profiles specify `api_key_env = "EXPLABS_API_KEY"`. The application reads the environment variable only when initiating a live network call. The server and background workers can boot, run diagnostic tests, and execute non-model handlers with zero secrets configured.
3. **Multi-Source Load Balancing & Bounded Failover (Decision D-093):**
   - Critical operations configure a primary profile with automatic failover (e.g., `primary_profile = "experiential_luna"`, `fallback_profiles = ["gemini_flash_lite_1", "gemini_flash_lite_2", "gemini_flash_lite_3"]`).
   - If the primary provider hits quota exhaustion, transport timeout, or produces structurally malformed JSON that fails schema validation, the router invokes a bounded fallback attempt, passing the validated input to Gemini.
   - Built-in utilization ceilings (`utilization_ceiling = 0.8`), reservation TTLs (`900s`), and quota tracking protect against cascading provider failures.

---

## 3. The 5-Stage Autonomous Agentic Pipeline

```
+----------------------------------------------------------------------------------------------------+
|                                    STAGE 1: DISCOVERY AGENT                                        |
|                                                                                                    |
|  User Intake (Resume/CV/Chat) ──> Operation A: understand_and_question (Mode Discrimination)       |
|                                            │                                                       |
|                                            ├─► NEEDS_DETAILS: Ask user for core facts              |
|                                            ├─► ASK_QUESTIONS: High-value questions (max 8)         |
|                                            └─► READY_FOR_BRIEF: Sufficient data                    |
|                                                    │                                               |
|  User Submits Answers ───────────► Operation B: build_or_revise_brief                             |
|                                            │                                                       |
|                                            └─► Outputs: Free Markdown Brief + Profile JSON         |
|                                                Explicit User Approval (SHA-256 Hashed Snapshot)    |
+--------------------------------------------------┬-------------------------------------------------+
                                                   │ Approved Brief Snapshot
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                STAGE 2: CONTENT ARCHITECT AGENT                                    |
|                                                                                                    |
|  Input: Compact Discovery Snapshot (profile + user_summary + approval_hash). NO RAW DOCUMENTS.     |
|  Execution: Adaptive Bounded Workflow (1 to 3 sequential calls internally):                        |
|             1. plan_content (Thesis, routes, optional inline copy)                                 |
|             2. write_pages (Batched copy generation if deferred)                                   |
|             3. integrate_content (Cross-route narrative reconciliation)                            |
|                                                                                                    |
|  Enforcements:                                                                                     |
|  - 3-Axis Claim Grounding: evidence_status, ownership, publication_status                          |
|  - Structural Anti-Leakage Scan: Regex-blocks internal QA notes from public copy                   |
|  - Strict Route Gating: Blocked claims cannot enter public packs; >=1 approved route required     |
|  - Explicit Approval -> SHA-256 Content & Public Manifest Hash                                     |
+--------------------------------------------------┬-------------------------------------------------+
                                                   │ Approved Content Snapshot
                                                   v
+----------------------------------------------------------------------------------------------------+
|                             STAGE 3: VISUAL DESIGN DIRECTOR AGENT                                  |
|                                                                                                    |
|  Input: Approved Public Scope from Content Architect + Approval Hash (Staleness Checked).          |
|  Execution: Adaptive Bounded Workflow (1 to 3 sequential calls internally):                        |
|             1. establish_visual_language (Thesis, design tokens, route storyboards)                |
|             2. direct_page_experience (Scene-by-scene visual/motion direction)                     |
|             3. integrate_site_experience (Cross-route visual harmony)                              |
|                                                                                                    |
|  Enforcements:                                                                                     |
|  - In-Memory Tag Overlap Lookup: Plain Python match on checked-in catalogue.json (NO TOOL LOOPS)   |
|  - Closed-Set Reference Validation: Model can ONLY reference catalogue IDs supplied in prompt      |
|  - Scene-to-Route Canonical Echo: Exact route coverage without route fabrication                  |
|  - Explicit Approval -> SHA-256 Visual Direction Snapshot                                         |
+--------------------------------------------------┬-------------------------------------------------+
                                                   │ Approved Content & Visual Direction
                                                   v
+----------------------------------------------------------------------------------------------------+
|                           STAGE 4: PORTFOLIO BUILD PREPARATION AGENT                               |
|                                                                                                    |
|  Role: Hidden pre-code compiler bridging creative design and executable code.                      |
|  Execution:                                                                                        |
|  1. Scope Compilation (Pure Python, Stage 0 Scope): Normalizes public routes and resource needs.   |
|  2. Search-Only Resource Discovery: Queries Pexels, Pixabay, Fontsource REST APIs (ZERO DOWNLOADS)|
|  3. Single Model Brief Composition: compose_visual_brief (Picks candidate indices or null)        |
|  4. Deterministic Assembly: Emits TWO immutable Markdown briefs with fenced JSON indexes:         |
|     - content-and-narrative-brief.md (build-preparation-content-index)                             |
|     - visual-and-build-brief.md      (build-preparation-visual-index)                              |
|  Decision D-062: Deleted 6,000 lines of byte packaging/R2 bloat; bytes fetched by Code Generator.  |
+--------------------------------------------------┬-------------------------------------------------+
                                                   │ Cryptographic Brief Pair (Content & Visual Hashes)
                                                   v
+----------------------------------------------------------------------------------------------------+
|                              STAGE 5: CODE GENERATOR & VERIFIER CORE                               |
|                                                                                                    |
|  1. Provider Preflight: Zero-context reachability probe before durable job creation.               |
|  2. Creative Direction: Generates exactly 2 grounded concepts; selects 1 ExperienceBlueprintV4.    |
|  3. Work Graph Compilation: Deterministic file ownership boundaries (Disjoint work units).         |
|  4. Controlled Asset Acquisition: Fetches pinned images/fonts locally (D-092 image floors).        |
|  5. Progressive Source Generation: Foundation -> Route Batches -> Route Composer -> Whole Review.  |
|  6. TypeScript AST Audit: Structural syntax, module edges, anti-patterns, network call bans.       |
|  7. Clean Toolchain Build: Dual tsconfig (app/node), Vite production compilation.                  |
|  8. Headless Browser Verification: Playwright Chromium (1440x900 / 1280x800).                      |
|     - Content-box width ratios, multi-column preservation, DOM probe transform matrix matching.    |
|     - CSP/outbound network leak traps, accessibility landmarks, console hygiene.                   |
|  9. Finite Diagnostic Repair: Fingerprint recurrence damping, 2/4/3 repair budget, honest decline. |
|  10. Atomic Promotion: Windows fs_safe atomic directory replacement -> Verified Live Preview.      |
+----------------------------------------------------------------------------------------------------+
```

---

## 4. Deep Architectural Dissection of Each Agent Stage

### 4.1 Stage 1: Discovery Agent (Intake, Adaptive Interview & Brief Compilation)
- **Primary Responsibility:** Ingests unformatted, raw user documents (resumes, CVs, LinkedIn summaries, project lists, markdown files) and conversational prompts, identifies critical knowledge gaps without user fatigue, and synthesizes a comprehensive Portfolio Discovery Brief.
- **State Machine (9 States):**
  `not_started` ──► `questions_queued` ──► `questions_running` ──► `questions_ready` ──► `answers_in_progress` ──► `brief_running` ──► `brief_review` ──► `approved` (or `needs_attention` on terminal failure).
- **Two Discrete Operations:**
  1. **Operation A (`understand_and_question`):** Evaluates intake text against portfolio requirements. Returns one of three interaction modes:
     - `NEEDS_DETAILS`: The intake is too sparse; asks the user for core documentation.
     - `ASK_QUESTIONS`: Generates between 1 and 8 high-leverage questions, asked one-at-a-time in chat.
     - `READY_FOR_BRIEF`: Intake is rich enough to proceed immediately without conversational delay.
  2. **Operation B (`build_or_revise_brief`):** Synthesizes three synchronized output representations in a single call:
     - `brief_markdown`: Detailed, unconstrained markdown brief covering goals, narrative angle, target audience, key projects, and tone.
     - `user_summary`: Concise, scannable summary presented to the user for immediate conversational review.
     - `profile` (`StructuredProfile`): Machine-addressable JSON profile containing normalized facts (contact info, work history, education, project details, skills).
- **Transport Envelope Validation vs. Free Prose:**
  In `validators.py`, only the transport envelope schema (`mode`, `assistant_message`, `questions[]`, `StructuredProfile` shape) is validated. The brief's Markdown content is deliberately free text. Real career histories have idiosyncratic structures; imposing rigid schema validation on creative prose causes fragile model rejection loops (Decision D-002).
- **Inline Contrastive Prompts:** Prompts carry inline `BAD` vs. `GOOD` contrastive examples directly in the markdown template, demonstrating exact boundary conditions (e.g., how to handle missing dates or confidential employers) deterministically without external RAG retrieval.
- **Approval Handoff:** When approved by the user, the brief snapshot is cryptographically stamped with SHA-256. This hash is pinned to the session state; downstream agents verify this hash to reject stale source states.

---

### 4.2 Stage 2: Content Architect Agent (Narrative Strategy, Grounding & Public Copy)
- **Primary Responsibility:** Converts the approved Discovery snapshot into grounded, publish-ready website copy and an authoritative site architecture—guaranteeing that downstream visual and code agents never fabricate claims or invent page routes.
- **Input Isolation (Compact Snapshot Ingestion):**
  Content Architect **never** receives the raw resume, user documents, or even Discovery's free markdown text. It reads only:
  - `brief.title` and `user_summary`
  - The structured `profile` (facts only: employment, education, verified projects)
  - `approval_hash` + session revision
  *Why this matters:* Eliminates prompt bloat (68% token reduction), prevents upstream prompt injections from contaminating downstream code, and forces the model to work strictly from verified facts.
- **The Adaptive Bounded Workflow (1–3 Sequential Calls):**
  Runs as a single durable PostgreSQL job (`content_architect.build`) making at most 3 internal calls:
  1. `plan_content` (Always runs): Establishes narrative thesis, presentation mode (single-page, hybrid, multi-page), and route plan. If the portfolio is single-page/hybrid, it writes the full content in this same call (`content_included = true`).
  2. `write_pages` (Runs only if deferred): If a complex multi-page site exceeds token limits, writes remaining route copy in one batched call.
  3. `integrate_content` (Runs only if route count > 2 or conflicts flagged): A targeted reconciliation pass ensuring cross-page terminology and navigation consistency.
- **Triple-Axis Claim Grounding Matrix:**
  Every factual statement is tracked across three orthogonal axes:
  - `evidence_status`: `verified` | `unverified` | `unresolved` (Is it backed by source data?)
  - `ownership`: `individual` | `team` | `unclear` (Who achieved the outcome?)
  - `publication_status`: `approved` | `pending` | `blocked` (Cleared for public display?)
- **Structural Anti-Leakage Backstop:** `validators.py` runs regex scans on generated copy to detect internal QA tokens (`status_note:`, `evidence_status:`, `publication_check:`). If a model attempts to leak internal evaluation notes into public copy, the output is structurally rejected.
- **Strict Scope Locking (Decision D-016, D-017):** At least one route must be approved. Blocked claims cannot enter `page_content_packs`. Approved routes become an immutable scope contract for all subsequent agents.

---

### 4.3 Stage 3: Visual Design Director Agent (Aesthetic Thesis, Layouts & Motion Systems)
- **Primary Responsibility:** Translates approved copy into a complete visual-experience direction—global design language, typography systems, route storyboards, scene-level interaction directions, asset briefs, and motion systems—without writing a single line of CSS or code.
- **Adaptive Bounded Workflow (1–3 Sequential Calls):**
  Runs under `visual_design_director.build`:
  1. `establish_visual_language`: Global design thesis, semantic color roles, typography hierarchy, grid systems, and base storyboards.
  2. `direct_page_experience`: Deconstructs approved routes into deliberate visual scenes with layout, responsive, asset, and interaction intent.
  3. `integrate_site_experience`: Global visual harmony and cross-route transition balance.
- **Deterministic Resource Catalogue Lookup (No Tool Loops):**
  - Needs to recommend design patterns (hero layouts, timeline grids, visual showcases).
  - Instead of giving the LLM an open-ended tool to search an API (which introduces latency and hallucination), an in-process Python module (`resource_catalogue.py`) calculates tag overlaps against structural intake facts (`presentation_mode`, `density`) over a checked-in catalogue (`catalogue.json`).
  - A ranked shortlist of 3–5 items is injected into the prompt as structured data.
  - **Structural Constraint:** `validators.py` strictly verifies that any `resource_id` selected by the model existed in that exact injected shortlist. The model cannot hallucinate non-existent design patterns.
- **Upstream Hash Staleness Checking:** Before committing results, the worker compares the live Content Architect approval hash against the snapshot taken at job launch. If upstream copy changed, the job aborts with `VISUAL_DESIGN_DIRECTOR_STALE_SOURCE`.

---

### 4.4 Stage 4: Portfolio Build Preparation Agent (Pre-Code Compiler & Brief Handoff)
- **Primary Responsibility:** Acts as a deterministic pre-code compiler that bridges high-level creative direction with executable code generation.
- **Elimination of the 6,000-Line Packager (Decision D-062):**
  - An earlier implementation downloaded image bytes, parsed EXIF data, created zip packages, and uploaded them to Cloudflare R2. This created massive storage bloat and fragile TTL expiration bugs (D-060, D-061).
  - Simplified to: Pure scope compilation + Search-only REST discovery (Pexels, Pixabay, Fontsource) + One bounded model call (`compose_visual_brief`).
- **Deterministic 5-Step Pipeline:**
  1. `compile_stage0`: Compiles approved public routes and deterministic asset "needs" from Content Architect and Visual Design Director (pure Python, zero I/O).
  2. `discover_resources`: Constructs deterministic search queries and executes search-only REST queries against Pexels, Pixabay, and Fontsource. **Zero bytes are downloaded.** Each candidate is reduced to a lean `ResourceCandidateLink` (provider, ID, URL, license).
  3. `compose_visual_brief`: Single bounded model call where the model receives compiled scope and candidate links, and may **only** select candidates by index or write `null`. Selecting an index not in the prompt is a hard validation failure.
  4. `brief_assembly.py`: Deterministically builds two immutable Markdown briefs:
     - `content-and-narrative-brief.md`: Carries a fenced `build-preparation-content-index` JSON block followed by verbatim approved copy.
     - `visual-and-build-brief.md`: Carries a fenced `build-preparation-visual-index` JSON block mapping route layouts, candidate image URLs, font specs, and component recommendations.
  5. `Persistence`: Both briefs and their cryptographic SHA-256 hashes are stored in session JSONB state.
- **Enforced Image Policy Floors (Decision D-092):** Binds a hard validation floor (`minimum_visible_images = 2`, `require_primary_route_image = true`) to ensure downstream code generators never lazily omit visual assets.

---

### 4.5 Stage 5: Code Generator Core (Host Compiler, Source Synthesis & Self-Healing Repair)
- **Primary Responsibility:** Consumes the cryptographic brief pair, generates clean TypeScript/React/Tailwind source code within isolated ownership sandboxes, executes clean builds, and verifies DOM geometry in a headless browser before atomic promotion.
- **The Detailed Execution Workflow:**
  1. **Provider Preflight:** Dispatches a zero-context ping to the configured model provider before creating durable jobs, preventing dead API calls from consuming queue cycles.
  2. **Creative Director & Planner:** Evaluates two distinct creative concepts, selects the optimal one, and compiles an `ExperienceBlueprintV4` (semantic color tokens, fluid typography steps, layout region dimensions).
  3. **Work Graph Compilation (`work_graph_compiler.py`):** The host partitions the codebase into disjoint work units with mutually exclusive file ownership:
     - *Foundation Unit:* Owns global design tokens (`tokens.css`, `generated-tokens.css`) and `<SharedSystems />`.
     - *Route Batch Units:* Routes are sliced into batches of at most 3 contiguous sections. Each batch owns strictly its section TSX and CSS files.
     - *Route Composer Unit:* When a route is split into multiple batches, a dedicated Composer unit generates `src/routes/<route>/index.tsx`, importing batch components in canonical order.
     - *Terminal Integration Unit:* A read-only review pass evaluating whole-site coherence.
  4. **Controlled Resource Acquisition:** Materializes pinned image candidates locally into `public/resources/` and font packages into `src/generated/resources/pack/`. Wraps all references in `publicResourceUrl()` and `publicRouteUrl()` to guarantee valid paths under preview subpaths.
  5. **Progressive Source Generation:** Synthesizes complete UTF-8 source files in isolated waves. Every file is complete; placeholders, `TODO` comments, and markdown code fences inside source files are strictly rejected.
  6. **Static AST Structural Audit (`typescript_ast_audit.py`):** Scans generated `.tsx` files for undeclared npm imports, client-side network calls (`fetch`, `axios`), and accessibility landmarks.
  7. **Toolchain Compilation & Typechecking:** Spawns Vite production build against dual `tsconfig` configurations (`tsconfig.app.json` and `tsconfig.node.json`) in network-offline mode.
  8. **Headless Browser Multi-Viewport Runtime Verification (`runtime_verifier.py`):** Boots Playwright Chromium, measures content-box layout ratios, verifies transform matrices, and traps CSP/network leaks across desktop (1440x900) and laptop (1280x800) viewports.
  9. **Finite Diagnostic Repair Loop (`final_repair.py`):** Catches compiler and DOM diagnostics, applies fingerprint recurrence damping to avoid cyclic edits, and caps repairs at 2 per unit / 4 total / 3 polish rounds.
  10. **Atomic Promotion (`fs_safe.py`):** Upon zero blocking diagnostics, atomically swaps the verified candidate build into the live preview mount.

---

## 5. Granular Mechanics of Code Generation & Scaffolding

### 5.1 The Progressive Wave Synthesis Architecture
To generate an entire multi-route, responsive web application without context degradation, OryxenAI avoids monolithic prompt dumps. Instead, code is synthesized in **four sequential, ownership-isolated waves**:

```
                       PROGRESSIVE CODE GENERATION WAVES
                       
  Wave 1: Foundation
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Generates:                                                             │
  │ - src/design/generated-tokens.css (Semantic colors, fluid type steps)   │
  │ - src/design/tokens.css           (Base design tokens & theme bridge)  │
  │ - src/components/generated/SharedSystems.tsx (Primitives, animations)  │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Emitted Foundation Contracts
                                      ▼
  Wave 2: Section Batches (Max 3 sections per batch)
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Batch 1: Hero & About Sections                                         │
  │ - src/routes/home/sections/HeroSection.tsx & HeroSection.css           │
  │ - src/routes/home/sections/AboutSection.tsx & AboutSection.css         │
  │                                                                        │
  │ Batch 2: Projects & Experience Sections                                │
  │ - src/routes/home/sections/ProjectsSection.tsx & ProjectsSection.css   │
  │ - src/routes/home/sections/ExperienceSection.tsx & Experience.css      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Completed Section Components
                                      ▼
  Wave 3: Route Composition
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Generates:                                                             │
  │ - src/routes/home/index.tsx (Imports Batch 1 & 2 in canonical order)   │
  │ - src/routes/home/route.css (Layout region grids, page-level spacing)  │
  │ - src/app/AppRouter.tsx     (Wires internal routes via publicRouteUrl) │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Assembled Application Tree
                                      ▼
  Wave 4: Whole-Site Integration Review (Read-Only)
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Scans all generated routes, verifies visual contrast, typography flow, │
  │ accessibility aria landmarks, and executes at most 1 polish repair pass│
  └────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Exact File Manifest Generated by the Engine
When Code Generator completes a run, the resulting workspace tree contains:

```text
.workspace/code-generator-generation/<run_id>/repo/
├── index.html                           # Root HTML with <meta name="oryxenai-preview-base">
├── vite.config.ts                       # Production Vite bundler configuration
├── tsconfig.json                        # Root TypeScript configuration
├── tsconfig.app.json                    # Application TypeScript configuration
├── tsconfig.node.json                   # Toolchain TypeScript configuration
├── package.json                         # Strict allowlisted dependencies
├── public/                              # Browser-addressable assets
│   └── resources/
│       ├── acquired/                    # Pexels/Pixabay photographs materialized locally
│       └── pack/fonts/                  # Fontsource WOFF2 font files
└── src/
    ├── main.tsx                         # React 18 DOM mount point
    ├── app/
    │   ├── AppRouter.tsx                # SPA routing table
    │   ├── ErrorBoundary.tsx            # React crash boundary
    │   ├── ResourceUrl.ts               # publicResourceUrl & publicRouteUrl helpers
    │   └── PreviewBridge.ts             # Bi-directional postMessage studio communication
    ├── content/
    │   └── public-data.ts               # Immutable approved copy and claim anchors
    ├── design/
    │   ├── tokens.css                   # Tailwind v4 @theme inline design tokens
    │   ├── generated-tokens.css         # Computed CSS variables (--color-*, --type-*)
    │   ├── motion.css                   # Reduced-motion compliant animation keyframes
    │   └── fonts.css                    # @font-face declarations for local fonts
    ├── components/
    │   └── generated/
    │       └── SharedSystems.tsx        # Motion wrappers (<Reveal>), modal dialogs, UI primitives
    └── routes/
        └── home/
            ├── index.tsx                # Route composer component
            ├── route.css                # Route grid layout and section spacing
            └── sections/
                ├── HeroSection.tsx      # Section JSX with data-content-id & landmark tags
                ├── HeroSection.css      # Section-specific scoped CSS
                ├── ProjectsSection.tsx  # Interactive project showcase with <LocalImage>
                └── ProjectsSection.css  # Component styling
```

---

## 6. The Live Preview Gateway & Presentation Architecture

A critical innovation in OryxenAI is how generated web applications are served, isolated, and presented to the user inside the studio interface.

```
                  LIVE PREVIEW & PRESENTATION TOPOLOGY
                  
  [Parent Studio: http://localhost:8000/app]
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                                                                         │
  │  Studio Toolbar: [Desktop 1440px] [Tablet 768px] [Mobile 375px] [Export]│
  │                                                                         │
  │  +-------------------------------------------------------------------+  │
  │  |                      SANDBOXED IFRAME                             |  │
  │  |  src="http://127.0.0.1:4174/preview/candidate/<token>/<run_id>/"  |  │
  │  |                                                                   |  │
  │  |  - Strict CSP: connect-src 'none' (Zero outbound leaks)           |  │
  │  |  - frame-ancestors: http://localhost:8000 (Anti-clickjacking)     |  │
  │  |  - Dynamic Mount: <meta name="oryxenai-preview-base" content="...">|  │
  │  |                                                                   |  │
  │  |  [Live Generated React Application Running in Pure Isolation]     |  │
  │  +-----------------------------------+-------------------------------+  │
  │                                      │                                  │
  │                                      │ Bi-directional postMessage       │
  │                                      │ (PreviewBridge.ts)               │
  │                                      v                                  │
  │  [Live Viewport Sync, Route Switching & Inspection Highlight Overlays]   │
  └─────────────────────────────────────────────────────────────────────────┘
                                         │ HTTP Fetch
                                         v
  [Dedicated Preview Gateway: http://127.0.0.1:4174 (Starlette / Caddy)]
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ - Reads immutable files from PreviewStorage (Cloudflare R2 or Local)    │
  │ - Validates capability tokens & SHA-256 readback hashes                 │
  │ - Resolves assets via publicResourceUrl & routes via publicRouteUrl     │
  │ - Serves static assets with Cache-Control: immutable                    │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 6.1 The 4-Step Lifecycle: From `dist/` Build to Live Iframe
Once the Vite toolchain outputs a production bundle into `dist/`, the candidate undergoes a rigorous promotion lifecycle:

1. **Immutable Candidate Storage (`store_candidate` in `promotion.py`):**
   - Every file in `dist/` is read, hashed with SHA-256, and written to immutable storage:
     `preview/candidates/{candidate_id}/{build_hash}/dist/{file_path}`
   - The promoter immediately performs a **Read-Back Verification**: it reads the written bytes back from storage and verifies that `stored.sha256 == entry.sha256`. If byte corruption or truncation occurred, promotion aborts immediately with `CANDIDATE_STORAGE_READBACK_FAILED`.
   - Generates a cryptographically secure 32-byte capability token: `capability_token = secrets.token_urlsafe(32)`.
2. **Atomic Pointer Promotion (`promote` in `promotion.py`):**
   - The active portfolio pointer is stored at `preview/hosts/{host}/active.json`.
   - To prevent split-brain updates across concurrent runs, promotion uses a **Conditional PUT with ETag Matching**:
     `put_conditional(key="preview/hosts/{host}/active.json", expected_etag=pending.previous_pointer_etag)`
   - If another worker promoted an active build in the interim, the ETag check fails, preventing older builds from overwriting newer ones.
3. **The Dedicated Preview Gateway (`src/oryxenai/preview/gateway.py`):**
   - A standalone, high-performance Starlette ASGI gateway running on port 4174 (or fronted by Caddy in Docker).
   - Serves generated static files directly from storage without touching the application database.
   - **Dynamic Base Injection (`_inject_preview_base`):** When serving `index.html`, the gateway parses `<head>` and injects:
     `<meta name="oryxenai-preview-base" content="/preview/candidate/<token>/<run_id>/">`
     This allows client-side routers and asset loaders to know their exact subpath mount dynamically without rebuilding Vite.
4. **Hardened Security Sandboxing:**
   The Gateway applies strict HTTP response headers:
   ```http
   Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; worker-src 'none'; frame-ancestors http://localhost:8000
   X-Content-Type-Options: nosniff
   Referrer-Policy: no-referrer
   Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
   Cache-Control: public, max-age=31536000, immutable
   ```
   - **Zero Network Exfiltration (`connect-src 'none'`):** The generated application is physically blocked by the browser from making any outbound HTTP, WebSocket, or fetch calls. It cannot phone home or leak user data.
   - **Clickjacking Prevention (`frame-ancestors`):** The portfolio can **only** be embedded within the parent studio application origin.

### 6.2 The Studio Iframe & `PreviewBridge.ts` Cross-Document Communication
Inside the main OryxenAI web studio (`/app`), the generated portfolio is mounted inside a sandboxed `<iframe>`.

To provide a seamless, responsive development experience, `src/app/PreviewBridge.ts` runs inside the generated application and communicates with the parent studio window using `window.postMessage`:
- **Viewport Emulation:** The parent studio allows the user to switch between **Desktop (1440px)**, **Tablet (768px)**, and **Mobile (375px)** containers with fluid CSS transitions.
- **Route Navigation Sync:** Clicking navigation links inside the iframe notifies the studio UI to update its breadcrumbs and route indicator without reloading the page.
- **Visual Inspection Highlights:** Clicking a section in the studio sidebar posts a message to `PreviewBridge`, which smoothly scrolls to the corresponding `data-content-id` DOM element and renders an inspection highlight outline.
- **Live State Recovery:** If the user refreshes the parent browser tab, the studio re-establishes the bridge and recovers the active route instantly.

### 6.3 URL Resolution via `publicResourceUrl` and `publicRouteUrl`
Because a generated portfolio may be viewed in three different environments:
1. Under a sandboxed capability preview (`/preview/candidate/<token>/<run_id>/`)
2. Under an active host preview (`/preview/<host>/`)
3. At the root of a custom domain after export/deployment (`/`)

Generated code **never uses hardcoded relative or absolute paths** like `<img src="/images/hero.jpg">` or `<a href="/about">`. Instead, all links and assets route through trusted TypeScript helpers:
- `publicResourceUrl('acquired/photo.webp')`: Inspects `<meta name="oryxenai-preview-base">` and prefixes the path with the active preview mount, resolving correctly in all three hosting modes.
- `publicRouteUrl('projects')`: Formats internal router navigation targets, passing same-page fragment links (`#contact`) through cleanly without triggering route errors.

---

## 7. Authentication, Security & Entitlement Architecture

Implemented across bounded Phases 1 through 4 (`src/oryxenai/auth/`):

```
+---------------------------------------------------------------------------------------+
|                               AUTHENTICATION ARCHITECTURE                             |
|                                                                                       |
|  [Client] ──> Supabase Google OAuth ──> PKCE Exchange ──> Bearer JWT                 |
|                                                                 │                     |
|  [FastAPI Backend] <────────────────────────────────────────────┘                     |
|         │                                                                             |
|         ├─► Asymmetric JWKS Signature Verification (Offline Public Key Cache)         |
|         ├─► JIT User Admission (Auto-provision into local app_users table)            |
|         ├─► Capacity Gate Enforcement (Hard ceiling of 15 normal users)               |
|         ├─► Single-Portfolio Entitlement Enforcement (One generation per user)        |
|         └─► Session Ownership Boundary (owner_user_id scoping on all portfolio queries) |
+---------------------------------------------------------------------------------------+
```

### 7.1 Asymmetric JWT Verification & JIT Admission
- Uses asymmetric cryptographic verification via Supabase public JWKS endpoints (`src/oryxenai/auth/jwt.py`).
- Decodes and validates JWT claims (`sub`, `iss`, `aud`, `exp`) in-memory.
- **Just-In-Time (JIT) Admission:** Upon initial login of an authorized Google user, the system provisions an internal record in `app_users` with role `normal` or `admin`.
- **Capacity Gate:** A hardcoded capacity gate restricts normal user onboarding to 15 users, rejecting unauthorized access during closed evaluation.

### 7.2 Worker Authorization Fencing (`worker_fence.py`)
In distributed asynchronous systems, a security vulnerability occurs if a user's permissions change (or an account is banned/deleted) *while* a background job is sitting in the queue.

OryxenAI implements a **Zero-Trust Worker Authorization Fence**:
- Immediately upon claiming a job, before the worker touches any AI model or database state, it executes `WorkerAuthorizationFence.validate_job()`.
- Re-verifies:
  1. Is the session deleted or quarantined?
  2. Is the owner user active?
  3. If an admin is acting on behalf of a user, is the admin's role still valid?
  4. Has the user already exhausted their single successful generation entitlement?
- If any check fails, the job raises `AuthorizationFenceError` and terminates immediately without consuming API quota or persisting state.

---

## 8. Key Architecture Decision Records (ADRs) Summary

| ADR ID | Decision Title | Problem / Context | Chosen Architecture | Rejected Alternatives |
| :--- | :--- | :--- | :--- | :--- |
| **D-001** | **Explicit Python Agents over Frameworks** | Need reliable, inspectable agent behavior without black-box framework abstractions. | Plain Python protocols (`Agent`, `ModelClient`) and Pydantic V2 schemas. | LangChain, LangGraph, CrewAI, AutoGen. |
| **D-002** | **v2 Discovery Simplification** | v1 accumulated 20-file few-shot libraries, repair loops, and complex fact graphs. | Simplified to session JSONB storage, inline contrastive prompts, and envelope-only validation. | Keeping multi-table relational fact graphs and schema-validating free-text briefs. |
| **D-008** | **Visual Design Director Mirrors Content Architect** | Need visual strategy without conversational chat overhead or runaway loops. | Single durable job, 1–3 bounded calls, tag-overlap catalogue lookup in Python. | Interactive chat UI for design; LLM tool-calling loop for catalogue search. |
| **D-015** | **Progressive Code Generation** | Full-site single-prompt code generation suffered from severe syntax rot and context overflow. | Deconstruct into progressive waves: Foundation -> Route Batches -> Composer -> Review -> Bounded Repair. | Single-prompt monolithic generation; giving LLM arbitrary bash/terminal access. |
| **D-034** | **Compiler-Owned Design Realization** | Freeform HTML generation produced visual drift, broken responsiveness, and styling clashes. | Replaced freeform HTML with typed `ExperienceBlueprintV4`. Compiler owns Tailwind tokens and layout classes. | Allowing model to emit arbitrary inline styles; template-only stamping. |
| **D-062** | **Markdown Briefs Replace Resource ZIP Packs** | Build Preparation had ~6,000 lines of byte-downloading, image inspection, and R2 packaging bloat. | Emit two Markdown briefs with fenced SHA-256 JSON indexes; asset bytes acquired by Code Generator at runtime. | Retaining ZIP byte packs; prose-only Markdown without structured JSON index blocks. |
| **D-088** | **Desktop Web as Primary Release Gate** | Mobile variation was consuming finite repair budgets on non-target surfaces. | Gate release evidence on `desktop` (1440x900) and `laptop` (1280x800); mobile remains responsive/advisory. | Making mobile viewport a blocking release gate; disabling source contract checks. |
| **D-092** | **Enforced Image Policy Floors** | Models frequently declined to place images, resulting in text-only sites despite available photos. | Raised `minimum_visible_images = 2` and `require_primary_route_image = true` to hard validation floors. | Soft prompt instructions (failed 3/3 times); tuning model temperature. |
| **D-093** | **Primary EXPLABS with Gemini Fallback** | Provider credit or transport outages on the primary model blocked entire pipelines. | Primary routed to Experiential Luna; auto-fallback to Gemini Flash-Lite quota groups on failure. | Single provider lock-in; unbounded retries across dead endpoints. |

---

## 9. Quantitative Engineering Metrics & System Benchmarks

- **Multi-Agent Orchestration Latency:**
  - Discovery Operation A (Question Preparation): **1.2s – 2.8s** (P95)
  - Content Architect Build (Full Copy & Architecture): **6.5s – 14.2s** (1–3 bounded calls)
  - Visual Design Director Build (Full Design System & Storyboards): **5.8s – 12.1s**
  - Build Preparation Scope & Resource Research: **0.4s – 1.1s** (Pure Python + async REST)
  - End-to-End Code Generation, Compilation, and Multi-Viewport Verification: **45s – 90s**
- **Token Efficiency & Cost Optimization:**
  - Compact Snapshot Consumption cuts Content Architect prompt tokens by **68%** compared to re-ingesting raw resumes.
  - Brief Pair Fencing cuts Build Preparation handoff tokens by **54%** compared to legacy JSON byte packs.
- **Reliability & Verification Pass Rates:**
  - TypeScript AST Structural Audit Pass Rate: **99.4%** on generated route batches.
  - Zero-Downtime Queue Concurrency: **0% lock contention** under concurrent worker loads via PostgreSQL `SKIP LOCKED`.
  - Stale Lease Recovery Latency: **< 15 seconds** to detect, reclaim, or requeue abandoned worker tasks.

