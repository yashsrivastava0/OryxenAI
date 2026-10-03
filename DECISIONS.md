## D-129 — Discovery palette selects an immutable Studio theme

- **Date & Time:** 2026-10-03 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** The owner supplied three distinct pre-built portfolio designs and asked for one visual choice during Discovery to determine which stylesheet the Code Generator uses. The existing flow had one pinned theme and a complete, approved single-page content tree.
- **Decision:** Append one required, server-authored palette question after up to three contextual Discovery questions. Its three swatch choices map deterministically to Editorial Forest Motion, Cobalt Atlas, or Obsidian Signal; an optional mood note is saved for the interview UI but does not change selection or factual copy. Persist the chosen immutable theme id in Discovery and Content Architect state, include it in their approval hashes, and pin it to the Code Generator run and version. Give each design its own CSS, markup contract, manifest, and reference renderer while keeping the existing `page_content` schema. Sessions approved before this change use the configured legacy default theme.
- **Rejected alternatives:** Model-selected themes, mapping from free-text mood notes, runtime stylesheet modes, CSS mutations per owner, and changing the content schema for this visual choice.
- **Consequence:** The owner sees palette descriptions and swatches, never theme filenames in the choice UI. The same selected package is used for first build, content edits, restore, and signed preview. The three designs remain independent immutable packages, and no publishing or deployment behavior changes.

## D-128 — Proposed interactive Studio theme using pre-built JavaScript

- **Date & Time:** 2026-10-03 — Codex (OpenAI)
- **Status:** proposed-research-only; not approved or implemented
- **Context:** The owner wants more advanced portfolio interaction while keeping `index.html` generated per person and pairing it with pre-built CSS and JavaScript. The current v1 theme already has CSS motion, but its preview CSP and iframe sandbox block scripts; saved versions record a full asset manifest while serve/restore check only the CSS hash.
- **Proposal:** Create a new immutable theme version with reviewed `styles.css` and `theme.js`; keep the model output to visible `body_html` and let the host insert the script in the head. Extend exact markup/hook validation, full-bundle integrity checks, theme-specific preview CSP/iframe flags without `allow-same-origin`, and browser verification of behavior. Retain v1 for existing versions. Treat visual layout variants and new portfolio content shapes as separate versioned contract work.
- **Rejected paths for this proposal:** Model-generated or inline JavaScript, per-user stylesheet/script files, editing released v1 assets, unbounded hook/data attributes, a second queue or runtime bundler, and claiming that JavaScript alone creates distinct layouts.
- **Trade-off:** Script execution enlarges the preview trust boundary. Strict CSP/sandbox, audited fixed code, resource hashes, keyboard/reduced-motion behavior, and a realistic Chromium policy are release gates. The D-127 Render Free pilot currently disables browser verification, so interactive per-build verification would need a measured hosting/policy choice. D-126 remains the paid always-on path.
- **Consequence:** Research and exact implementation map are in `docs/research/studio-interactive-theme-architecture.md`. No code, schema, theme package, config, remote service, or production branch is changed by this proposal. An implementation decision and separate task are still required.

## D-127 — Render Free pilot with existing Supabase Auth and PostgreSQL

- **Date & Time:** 2026-10-03 — Codex (OpenAI)
- **Status:** decided-not-provisioned
- **Context:** The operator clarified a hard free-tier constraint, only two or three expected users, and a preference for the fewest beginner-friendly services. The app needs a PostgreSQL-backed API/worker, document intake, agent stages, and a same-origin Studio preview. D-126's Railway Hobby plan is paid and therefore does not satisfy that constraint.
- **Decision:** Select one Render Free Docker Web Service for the combined FastAPI/Preact app and existing durable worker, plus the existing Supabase project for Google Auth and application PostgreSQL. Use the Supabase Session pooler, one Render instance, a low-concurrency Render-specific overlay, startup Alembic migrations, and bounded 30-day retention for replaceable model cache, superseded Studio versions, and retired Code Generator runs. Add a managed-host supervisor because Render Free has no background-worker service. This is a limited pilot only.
- **Rejected alternatives:** Railway Free's $1/month usage allowance as a dependable always-running app/worker/database; Vercel Functions for the persistent worker and 600–900 second job timeouts; Render Free PostgreSQL because it expires after 30 days; a separate frontend/preview host, Redis, or object storage.
- **Trade-off:** Render Free sleeps after 15 minutes without inbound traffic, may restart, and has 512 MB RAM / 0.1 CPU. Long jobs need the service awake; OCR may exceed memory; the overlay does not run headless Chromium verification. Supabase Free is limited to a recommended 500 MB database and can pause for low activity. This is not production-grade availability. If a complete DB-to-Studio acceptance run fails, use the paid Railway Hobby path in D-126 rather than representing the free service as reliable.
- **Consequence:** The strict-free pilot guide is `docs/deployment/version-2/free-tier-migration-guide.md`. D-126 remains the paid always-on alternative. The Azure `deployment` branch and VM are not modified or retired by this decision. The Render pilot has not been provisioned and no cloud database, OAuth, DNS, or Azure state was changed; local verification used only `oryxenai_test`.

## D-126 — Railway Hobby as the recommended Version 2 hosting target

- **Date & Time:** 2026-10-03 — Codex (OpenAI)
- **Status:** decided-not-provisioned
- **Context:** The app now runs as a containerized FastAPI/Preact service with a PostgreSQL-backed durable worker, Supabase authentication, and same-origin signed Studio previews. The earlier Azure VM deployment requires host, Compose, TLS, storage, and power automation. The operator asked for a simpler, beginner-friendly replacement that preserves the full DB-to-preview workflow.
- **Decision:** Recommend one Railway Hobby project with three services: app/web from the root Dockerfile, one always-on worker from the same image, and PostgreSQL. Retain the existing Supabase project for Google Auth; keep the bundled frontend and same-origin preview on FastAPI; keep the PostgreSQL queue and page bundles in PostgreSQL. Use Singapore for Railway services, configure a database backup and external logical exports, and validate the complete workflow before cutover.
- **Rejected alternatives:** Vercel frontend/API split (adds origin/routing/preview complexity and has no persistent worker); free-only deployment (not a dependable always-on DB/worker plan); adding Redis, object storage, a preview host, or a separate frontend host.
- **Trade-off:** Railway Hobby is paid and usage-metered; it is simpler operationally but is not guaranteed to undercut Azure, especially while student credits remain. Railway's PostgreSQL service still requires operator-owned backups, restore drills, upgrades, and monitoring.
- **Consequence:** Documented in `docs/deployment/version-2/deployment-strategy.md`. This records a hosting recommendation only: no service was provisioned, no data or DNS was changed, and no commit was deployed or promoted. Confirm live Azure state and measure Railway use before retiring the VM.

## D-122 — Studio: a one-shot, verified page build with sealed versions and a sandboxed same-origin preview

- **Date & Time:** 2026-10-02 09:43 +05:30 — Claude Code (Anthropic)
- **Status:** decided-implemented-locally
- **Context:** Content Architect approval ended the product, while D-116, D-118 and D-121 require an AI-written `index.html` over the pinned stylesheet, a verified preview, and a chat that changes the page. The operator ruled out retry and repair loops for now, asked for exact failure reporting instead, and required a simple, debuggable pipeline that deploys on any container host (not only Azure).
- **Decision:** One durable job per build with a single attempt: admission (no model call), one model call that returns only `lang` and the visible body markup, strict validation on a stdlib parser (closed-world visible text, approved copy bound to its placement, forbidden constructs; never auto-fixed), a host-owned `<head>`, a sealed bundle (the page in PostgreSQL, the theme's files from the image, both by hash), real-browser verification (`best_effort` by default), and one promote transaction fenced by the job lease and the session lock. Every failure is one envelope (code, stage, summary, cause, where, expected and found, owner, action, reference) stored on the version, mirrored in session state and shown in the Studio; a failed attempt never replaces the live page; a job that dies silently is reconciled on the next read. The theme is an immutable package (byte-pinned CSS, local fonts and art, manifest, executable markup contract); the model sees the contract and an exemplar, never the CSS. Versions and chat live in their own cascade tables; a chat message runs `interpret_change` (typed edits to a whitelist of content paths, or a reply) and then the same pipeline, restore copies a verified row, and privacy-sensitive removals restrict older versions that showed the text. The preview is `/preview/g/<hmac-grant>/...` served same-origin outside `/api`, with a CSP `sandbox` and an iframe sandbox that allow neither scripts nor `allow-same-origin`, and grants redacted from logs. The product's primary action on the content review is one explicit click, "Approve & generate my portfolio": approve, then start, then open the Studio.
- **Rejected alternatives:** A model-written full document including `<head>`; giving the model the stylesheet; an HTML parsing dependency (bs4/html5lib); auto-fixing near-miss markup; a retry loop, repair call or labelled fallback renderer now; an object store for bundles; a dedicated preview origin (kept as a code seam); serverless hosting of the worker; an API that starts the build as a side effect of approval.
- **Trade-off:** Strict validation and no repair mean a rare miss costs the owner a click on "Try again"; the live campaign measured first-pass success on every content shape rather than assuming it. Chromium is optional, so verification can be recorded as unavailable on a minimal host.
- **Consequence:** Deviates from AGENTS.md "no automatic stage chaining" only in the UI sense (one explicit user click; no endpoint chains stages) and from docs/architecture/12 section 5 by applying chat edits to the site's content version instead of rewriting approved Discovery or Content Architect artifacts (Content Architect approval stays terminal). Narrows D-121's "Code Generator unbuilt" and the Content Architect-only product boundary. A single retry loop, a single repair call and a degraded render are seams in `pipeline.py`; scripts, extra stylesheets and more themes can join a bundle's manifest later. Publishing or hosting a public page remains unbuilt.

## D-123 — Shared model layer generalised for a third engine

- **Date & Time:** 2026-10-02 09:43 +05:30 — Claude Code (Anthropic)
- **Status:** decided-implemented-locally
- **Context:** Engine routing, the per-run call allowance and preflight were written for exactly two engines, and an engine with no configuration silently fell back to an unrelated route.
- **Decision:** `AgentKey.CODE_GENERATOR` joins the pipeline engines; the per-run budget takes the largest `normal_calls` and `recovery_allowance` across the engine's configured operation routes (identical values for Discovery and Content Architect); preflight and the durable job timeout check cover the new engine; the Code Generator is configured explicitly in `config/models.toml` with no fallback profile and `recovery_allowance = 0`. The provider's JSON parser tolerates raw control characters inside strings (`strict=False`) before its brace-scan fallback, which markup in a JSON string needs.
- **Rejected alternatives:** A second budget mechanism for the new engine; relying on the default route; a separate non-JSON transport for markup.
- **Consequence:** A new engine must be configured, or its calls are refused instead of rerouted. Existing engines behave as before; the shared-layer tests pin their budgets.

## D-121 — Preview belongs to the Code Generator, not Content Architect

- **Date & Time:** 2026-10-01 21:55 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** D-118 added a client-side, unverified "Live preview" tab to the Content Architect review, filling the pinned template with page copy in the browser. The operator directed that previewing happens only in the Code Generator.
- **Decision:** The Content Architect review shows the structured copy and the evidence and coverage inspector only. The preview component, its template-substitution helper, and the tab were removed. The pinned `index.html` and `styles.css` fixture moved from the served frontend `public/` folder to `docs/pinned-theme/` as reference input for the Code Generator and is no longer served by the app. Previewing returns with the Code Generator, which previews the verified bundle (D-116).
- **Rejected alternatives:** Keep the quick preview as a labelled draft; add a deterministic preview inside Content Architect.
- **Trade-off:** Until the Code Generator exists, reviewers judge the copy as structured fields rather than as a rendered page.
- **Consequence:** Narrows the last sentence of D-118. Content Architect's output contract is unchanged. The Code Generator, verified preview, and deployment remain unbuilt.

## D-120 — Compact Discovery draft with bounded same-route recovery

- **Date & Time:** 2026-10-01 16:25 +05:30 — Codex (OpenAI)
- **Status:** decided-implemented-locally
- **Context:** Discovery brief generation was slow and frequently failed because the model had to emit a large span-linked dossier and every missing link rejected the whole response. One global running model lane also queued unrelated users.
- **Decision:** The model emits a compact, lenient draft; the server builds the stored `DiscoveryDossier/v1`, repairs IDs and links, and derives the compatibility profile. New dossiers retain source-document hashes but leave span coverage empty and identify provenance as `brief_derived`. Only absent usable Markdown or a non-object output is a hard contract failure. Discovery uses the configured route with one same-profile recovery attempt, streamed responses where supported, and configurable model-lane concurrency. `READY_FOR_BRIEF` queues the brief within Discovery in the worker transaction; approval remains explicit before Content Architect.
- **Rejected alternatives:** Keep strict span-by-span model output and use more retries; add another provider; split the brief into parallel calls before measuring the compact version.
- **Consequence:** Supersedes D-116's span-linked Discovery dossier mechanics, D-117's no-retry trade-off for Discovery, and D-119's assumption that Discovery stays on its previous model. Existing dossiers and approval hashes remain readable. New briefs have less excerpt-level provenance, while Content Architect still receives IDs and complete structured context. The gateway route and lane size remain configuration choices; deployment is separate.

## D-119 — Content Architect routes through GPT-6 Luna

- **Date & Time:** 2026-10-01 14:30 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** The operator asked for Content Architect to use the EXP Labs GPT-6 Luna model while Discovery keeps its current model.
- **Decision:** `config/models.toml` gains an `experiential_luna_6` profile (same gateway and credential variable), and only the Content Architect engine route and its three operation routes select it. Policy version moved to `active_agent_routes_v3`. D-117's single-provider rule is unchanged.
- **Trade-off:** Roughly twice the latency of the previous profile on the same input. Profile pricing is a placeholder copied from the existing profile.
- **Consequence:** Implemented locally in `f5e5d14`; no deployment or external promotion was performed.

## D-118 — Typed single-page content tree for the pinned template

- **Date & Time:** 2026-10-01 13:05 +05:30 — Claude Code (Anthropic)
- **Status:** decided-and-implemented-locally
- **Context:** Content Architect still modeled a generic multi-route site that the code already forced to one page, and its prompts asked for project, experience, and education content the one pinned template (`docs/HTML and CSS/`) has no slot for.
- **Decision:** Content Architect returns a typed `page_content` tree matching the template region for region, including exactly four systems-practice pillars and name-only organizations. Claims and the six-way coverage ledger (`used`, `condensed`, `retained_internally`, `excluded_by_restriction`, `excluded_editorially`, `unresolved`) bind to field paths. Template rules live in the shared system prompt and one rule module; completeness is repaired by the existing single bounded integration call rather than rejected per model call. Organizations, links, and marquee keywords may be empty rather than invented. The review stage adds a client-side, unverified preview of the pinned HTML and CSS.
- **Rejected alternatives:** A generic theme-agnostic block model, which adds a translation layer with no second theme to justify it; sending raw CSS to the model; hard-failing a run on a wrong pillar count before the repair call.
- **Trade-off:** Sessions saved with the route-based shape load with an empty page and must be re-run, and `CONTENT_ARCHITECT_NO_PUBLISHABLE_ROUTES` became `CONTENT_ARCHITECT_PAGE_NOT_PUBLISHABLE`. Supporting a second stylesheet later needs a new content contract.
- **Consequence:** Implemented locally in `2bdc7f8`, narrowing D-116's Content Architect handoff to this shape. The Code Generator, verified preview, and deployment remain unbuilt.

## D-117 — Single-provider routing for active agent operations

- **Date & Time:** 2026-10-01 10:40 +05:30 — Codex (OpenAI)
- **Status:** decided-and-implemented-locally
- **Context:** The active agent routes had one configured primary and cross-provider fallbacks. A transient primary failure caused a fallback attempt, leaving the UI to name the alternate provider in the final error. The operator directed that both active stages use one gateway only.
- **Decision:** Discovery and Content Architect use only the primary profile configured in `config/models.toml` for every active operation. Alternate-provider fallbacks, their capacity observations, and optional profile selection are disabled. A new explicit retry or revision receives the current policy snapshot while already queued jobs retain their immutable snapshot.
- **Trade-off:** A temporary gateway failure now surfaces directly and requires a user retry; saved source material and answers remain intact. The provider, model, endpoint, and credential variable stay in configuration.
- **Consequence:** Implemented locally in `4e20499`; no deployment or external promotion was performed.

## D-116 — Complete agent handoffs with two approvals and AI-written HTML

- **Date & Time:** 2026-09-29 16:13 +05:30 — Codex (OpenAI)
- **Status:** decided-not-yet-implemented
- **Context:** The operator wants Discovery and Content Architect to preserve and develop complete user context for a later Code Generator, with text entry first, explicit report/copy review, and HTML integrated with a preset stylesheet.
- **Decision:** The target first intake is one freeform text box; PDF/DOCX attachments are later adapters. Discovery preserves every substantive source detail in a linked dossier and asks zero or a contextual group of one to three questions when useful; its report requires explicit user approval. Content Architect receives the complete approved dossier, records a disposition for every item, writes all person-specific single-page copy, and requires explicit approval. The AI Code Generator writes `index.html` using only that approved copy as person-specific input plus the pinned theme markup contract; a coordinator attaches unchanged `styles.css`, verifies, and previews the exact bundle. Provider/model routing remains configuration-driven.
- **Rejected alternatives:** A small fixed interview, lossy profile-only handoff, automatic progression past either review gate, first-slice file parsing, a plan-only Code Generator with host-authored HTML, or per-user stylesheet changes.
- **Consequence:** Supersedes D-115's automatic progression and trusted-renderer choices in the target proposal; D-113 still describes the active product. The revised design is documented in `docs/architecture/10-...` through `14-...`. Application code, schema, theme assets, and deployment remain future implementation work.

## D-115 — Research-only refinement of the portfolio proposal

- **Date & Time:** 2026-09-29 01:22 +05:30 — Codex (OpenAI)
- **Status:** open
- **Context:** The operator clarified that this task is architecture research in Markdown and that implementation follows their review. Earlier D-114 prose also coupled the proposal to a particular model and hosting migration.
- **Decision:** Submit the refined design in `docs/architecture/10-...` through `13-...` for review: complete evidence/coverage contracts, detailed Content Architect writing and audit, constrained composition with trusted HTML rendering, one shared pinned stylesheet, isolated verified preview, ordered edits, and bounded repair. Provider/model settings remain in `config/models.toml`; reuse storage/job boundaries without selecting a hosting migration. No implementation is authorized by this documentation task.
- **Rejected alternatives:** Treating earlier "implement" messages as permission to change runtime after the clarification; treating short agent summaries as complete handoffs; silently fixing failures by dropping evidence or editing shared CSS per user.
- **Consequence:** This is a refinement of D-114 pending user review, not a change to the active D-113 workflow. Code, schema, theme assets, model configuration, and deployment require a later implementation task. Current deployment decisions retain their meaning.
## D-124 — Owner reset and text-first Discovery file intake

- **Date & Time:** 2026-10-02 18:05 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** Owners need to restart the full portfolio journey from any stage and submit a resume file at the first Discovery screen, including when they have no typed notes.
- **Decision:** Expose the existing fenced pipeline cleanup through the owner-scoped session route while keeping the same entitlement-bound session ID. Place one reset action in the sticky workspace header; require explicit confirmation and reload empty Discovery after cleanup. Extract selectable text from one bounded PDF, UTF-8 Markdown, or plain text file through an authenticated intake adapter and submit it through Discovery's existing `document_text` field. Do not retain the uploaded binary. Leave DOCX, OCR, and photographs for later intake work.
- **Consequence:** A reset removes Discovery and Content state, jobs and runs, generated page versions, chat history, and external artifacts. Active workers are fenced by the session status and revision. File-only Discovery starts use the same model and provenance flow as pasted material.

## D-125 — Structure-preserving PDF intake with bundled OCR

- **Date & Time:** 2026-10-02 20:35 +05:30 — Codex (OpenAI)
- **Status:** implemented-locally
- **Context:** D-124 added text-first PDF intake but left OCR out. Full-page OCR of the supplied searchable resume replaced accurate embedded wording with recognition errors, while extraction without local layout support could not handle scanned resumes or retain useful section structure. Managed containers also have ephemeral filesystems and separate web/worker processes.
- **Decision:** Convert PDFs with Docling's PDFium backend and normal OCR mode so selectable text remains authoritative while image regions and scanned pages use local RapidOCR. Export detected hierarchy, reading order, furniture, and page breaks to editable Markdown; return the whole transcript, page count, and partial-conversion warning. Keep UTF-8 Markdown/text exact, stream uploads under configured byte/page/time/character limits, and pass the reviewed transcript plus filename through Discovery's existing source snapshot and question packet. Download model artifacts at image build time and ship them at `/opt/docling-models`; runtime OCR runs offline. Accept provider `DATABASE_URL` values and runtime auth origins for managed-host PostgreSQL and hostnames.
- **Rejected alternatives:** Full-page OCR as the only path; a runtime Hugging Face dependency; storing original uploaded files; making a scanned-document OCR service a required external dependency; adding DOCX and photos to this release.
- **Trade-off:** Container images are larger and PDF extraction uses CPU and memory; OCR on low-quality scans can still misrecognize text, so the full transcript is editable before submission. Begin with 2 vCPU and 4 GiB RAM per API instance and tune from measured latency and memory.
- **Consequence:** Supersedes D-124's decision to defer scanned-PDF OCR. DOCX, photos, and multiple attachments remain unsupported. Render/Railway deployments use the same image with separate API and durable worker services, one PostgreSQL database, and a migration step; this records compatibility guidance and does not authorize a remote deployment.
