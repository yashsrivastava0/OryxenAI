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
