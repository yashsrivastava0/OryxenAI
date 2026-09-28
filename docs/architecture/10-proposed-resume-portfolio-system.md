# Proposed resume-to-portfolio architecture: product and system

> **Status:** research proposal, revised 2026-09-29; awaiting user review before implementation. This describes the target product. The current system is documented in `01-...` through `03-...` in this directory. No deployment or application change is implied by this document.
>
> **Start with:** [Architecture README](README.md). **Read next:** [Agent and artifact contracts](11-agent-and-artifact-contracts.md) and [Generation, preview, revisions, and operations](12-generation-preview-revisions-and-operations.md).

## 1. Decision in one paragraph

A user uploads or pastes professional details and states a goal. Intake preserves originals and extracts text. Discovery builds a detailed, source-linked dossier and asks only useful questions. Content Architect plans a single-page story and writes all personalized public copy into a complete structured package. Coding Engine selects supported components in a render plan; trusted application code produces `index.html`. Shared `styles.css`, templates, and assets come from a pinned theme package. Verification gates activation. User changes update canonical artifacts and create a new version. Every model call uses `ModelClient` and `config/models.toml`; provider selection is independent of these responsibilities.

## 2. Scope and honest limits

| Now, in the target first release | Later, without replacing the content pipeline |
| --- | --- |
| One HTML page per portfolio, `index.html` | Multiple HTML pages if a new document contract is explicitly introduced |
| One shared, prebuilt `styles.css`, pinned per version | Additional themes and per-portfolio style artifacts; never overwrite global CSS |
| HTML and CSS only, with local fonts/images where needed | Optional JavaScript behavior under a versioned capability contract |
| Optional sections and layout variants supported by the theme | New components added to the shared theme library |
| User review happens on a generated preview; questions interrupt only when useful | More granular direct manipulation in the editor |
| Readable PDF, DOCX, TXT, and pasted text | OCR, photo upload/cropping, other media, export, and public publishing |

The result can look excellent within a designed visual family. A fixed stylesheet cannot provide unlimited bespoke designs. “No errors” means a version cannot be labelled **ready** while a required check fails. Source references cannot prove that every statement was interpreted correctly; layout checks cannot prove beauty. Preserve originals, make omissions explicit, calibrate checks against representative examples, and let the user correct the finished portfolio.

The old full Code Generator is a source of lessons and archived code, not a subsystem to revive. This proposal does not add Visual Design Director, Build Preparation, independent per-route source generation, package installation, or a React/Vite build to each user portfolio.

## 3. User journey

```mermaid
flowchart LR
    U[Resume, goal, optional links] --> X[Extract readable source]
    X --> D[Discovery: facts and focused questions]
    D --> C[Content Architect: full page copy]
    C --> G[Coding Engine: compose index.html]
    T[Versioned CSS theme and assets] --> G
    G --> Q[Browser and contract checks]
    Q --> P[Active preview]
    P --> E[User change request]
    E --> D
    E --> C
    E --> G
```

### Screen sequence

1. **Portfolio start page:** resume upload or paste; short goal prompt; optional links and source-role selection. A user can start with only a readable resume. The page reports extraction progress and any document-read problem.
2. **Discovery conversation:** a small number of targeted questions appear in the left panel. The user may answer or skip. A clear “continue with what I gave you” action always exists. The agent never forces a generic questionnaire.
3. **Generation progress:** the UI presents understandable stages (“Understanding your work,” “Writing your portfolio,” “Building and checking your page”). Stage state comes from the server, survives refresh, and shows an actionable error when needed.
4. **Preview workspace:** the left side accepts change requests and shows a compact history; the right side displays the exact generated artifact at desktop/mobile widths. The current successful version remains visible while another is built.
5. **Review:** the user opens the same version standalone, interacts with native links/disclosures, and requests changes. Public publishing and downloadable export are separate future capabilities.

There are no mandatory intermediate approval screens. Saved dossier/content versions provide an audit and edit base; the user judges the generated portfolio in the preview. If a question is genuinely necessary to avoid a wrong central claim, the pipeline enters `waiting_for_answer` and resumes when answered or skipped.

The frontend distinguishes **no current page**, **last verified page with a new revision running**, and **new revision failed while the last verified page remains**. After a skip, proceed with available evidence. If that cannot support a meaningful page, return `needs_input` with one concrete request. Pin the shared theme before Content Architect receives its semantic capabilities. New themes and arbitrary styling are future capabilities.

Stage summaries are small projections of validated artifacts: received sources, understood direction, planned sections, and build/check status. Expandable details expose the full dossier/content package to the owner without inserting internal notes into the public page. Desktop preview uses an actual 1280 CSS-pixel frame scaled to fit the pane; mobile mode changes the frame viewport, not the generated files.

## 4. Stage ownership

| Owner | Receives | Produces | Decision boundary |
| --- | --- | --- | --- |
| Intake service | Upload/paste, goal, optional links | Extracted text with source spans and asset records | Parses documents; does not write biographical claims |
| Discovery | Extracted source, goal, answers, prior dossier on revision | `DiscoveryDossier/v1` | Facts, personal contribution, user intent, open points; no final public copy |
| Content Architect | Complete dossier, semantic component catalogue, current package on revision | `PortfolioContent/v1` | Positioning, section selection/order, complete person-specific publishable copy; no HTML/CSS |
| Coding Engine model | Complete content package, theme manifest, approved asset IDs, previous render plan | `RenderPlan/v1` | Supported variants and bindings; no prose, arbitrary classes, HTML, or CSS |
| Trusted renderer and verifier | Validated plan/content and exact theme/templates/assets | `index.html`, bundle manifest, verification receipt | Escape, assemble, check, and attest exact candidate bytes |
| Application orchestrator | Stage artifacts, jobs, edit requests | Version pointers, progress, preview admission | Runs handoffs, retries, supersession, and promotion; not an AI agent |

Parsing, storage, rendering, structural validation, and browser measurements are host work. Semantic audits belong to the agent that owns the artifact and may use a configured model. A valid schema alone does not establish factual support or visual quality. See the [agent operation playbook](13-agent-operation-playbook.md) for detailed responsibilities and acceptance criteria.

## 5. Logical system and data movement

```mermaid
flowchart TB
    Browser[Product browser] --> Web[Web/API service]
    Web --> DB[(PostgreSQL)]
    Web --> Store[(Durable artifact storage)]
    Worker[Durable worker and Chromium] <--> DB
    Worker <--> Store
    Worker --> Model[Configured ModelClient]
    Browser --> Preview[Versioned preview endpoint]
    Preview --> DB
    Preview --> Store
```

- **PostgreSQL** owns portfolio identity, current version pointer, revision requests, job state, structured dossiers/content packages, theme/version references, and the immutable run ledger. Each handoff is committed before the next job is enqueued in the same database transaction.
- **The storage abstraction** owns original resumes, large extracted text, generated HTML, theme CSS, fonts/images, and diagnostic screenshots. Durable shared files or object storage may implement it; ephemeral worker files cannot be the only copy. Each artifact has an immutable key/hash. Source documents remain private and outside the public bundle.
- **The worker** claims durable jobs, makes model calls, renders/validates candidates, and writes artifacts. At-least-once delivery is expected; idempotency keys, leases, and compare-and-swap promotion prevent duplicate or stale results from replacing the current page.
- **The preview endpoint** serves a specific manifest version's exact bytes on an isolated origin. Owner-issued, expiring access covers HTML and relative assets. The iframe and standalone page load the same bundle. A version pointer changes only after readback, verification, and revision/worker fencing.
- **No vector database is needed for a single resume.** Source IDs, structured records, and selective context assembly are sufficient. If the user later supplies many external documents, retrieval can be added behind the same dossier boundary.

### Context loading

The full extracted resume is supplied to Discovery for its initial fact extraction when it fits the configured context allowance. A longer readable source is split by document sections into source-linked chunks and merged before the dossier is finalized; an unreadable source gets a visible correction path. Discovery follow-ups load the dossier plus only relevant source spans and prior answers. Content Architect loads the dossier, goal, explicit preferences, and component vocabulary. Coding Engine loads the content package, theme/component manifest, and assets; it does not need the full resume. Revisions load the selected old version and the requested change. Every model call records its input artifact IDs, schema version, prompt version, model profile, output ID, and result status. Conversation history is retained as events but is not replayed wholesale into every call.

### Minimum execution path and ownership

The logical path is extraction → Discovery understanding/clarification → dossier validation → content planning/writing/audit → composition → rendering → verification. Small inputs may combine planning and writing. Large dossiers use bounded named-section batches, each with its own facts. No call-count optimization may truncate the factual inventory or final package. The application controls handoffs from persisted state; agents do not call each other or own database transactions. Persist a completed artifact and enqueue the next job in one transaction.

The most important handoff gate is `PortfolioContent/v1`: it must contain the **finished public page**, including the sections that will actually be rendered. A beautiful theme cannot recover missing project context or fabricated claims. The most important render gate is theme compatibility: a valid content package may still be unrenderable if the theme has no template for its chosen block or its text exceeds every supported layout. Such a mismatch is returned to the owning theme/content stage with a precise section and field, rather than retried as generic HTML generation.

## 6. Design system and the supplied stylesheet

The supplied stylesheet is the visual seed for theme `editorial-forest/v1` (working identifier). Source on this machine: `C:\Users\Yash Srivastava\Desktop\01_Projects\trash\test\NOT-TOUCH-AI\styles.css`; SHA-256 `3A643EEEE0D2A8254F811A44D98E241E8E82B521429E4B53B312C169584925CE`. The companion `index.html` shows the intended level of art direction. These source files were read only; they were not copied or modified by this proposal. At implementation, copy the reviewed CSS into a versioned theme package in this repository so the build is reproducible on another machine.

**What it already provides:** navigation, strong hero with visual, marquee, four-card pillars, collapsible capability groups, organization context, contact list, footer, motion, responsive breakpoints, and reduced-motion handling.

**What must be done once to make it reusable:**

1. Add designed `project_story`, `experience_timeline` or `experience_narrative`, `education_credentials`, and generic narrative/list components. The example currently lacks detailed case studies.
2. Make nav labels/section count, pillar count, skill count, and content lengths variable. The sample HTML assumes four nav links, four pillars, and a very large fixed skills inventory. Test long names, short labels, empty optional fields, and mobile widths.
3. Provide a first-party image-free hero variant and local visual fallback. The sample uses a remote Unsplash image; that must not be required for a complete page.
4. Bundle the font assets referenced by `@font-face` or remove those references and use intentional fallbacks. The two supplied files do not include the referenced font files.
5. Keep substantial project and experience copy visible in normal page flow. Reserve `<details>` for secondary inventories; the portfolio's main story must be visible without opening controls.
6. Define the theme's supported component IDs, HTML structure/class names, optional slots, variants, and responsive constraints in one versioned manifest. Build every theme against this same semantic vocabulary, or declare a compatibility matrix and select theme before Content Architect runs.

The example's decorative marquee repeats capability terms and the reading-progress bar uses CSS scroll-timeline support. Both are optional presentation pieces. They must be omitted or replaced when there is no suitable evidence or browser support; neither may carry essential resume content. The first release does not need page JavaScript for navigation, `<details>`, or the preview. The CSS has a `20rem` minimum body width, so the theme's responsive acceptance range begins at that supported width; narrower embedding containers must be handled by the product preview frame rather than by assuming the page can shrink indefinitely.

A portfolio version pins the CSS/theme hash and resolves the exact CSS through its bundle manifest. Reusing a stylesheet does not mean serving a mutable “latest.css” path to old versions.

## 7. Deployment boundary, deferred until the system works

The target requires a responsive API, a durable worker with a pinned browser environment, PostgreSQL, and durable artifact storage available to the serving and worker processes. Reuse the repository's existing boundaries. This research selects no hosting migration. Capacity and concurrency limits should be measured during future implementation; deployment changes require their own authorized task and operational review.

## 8. Proposed transition from today's repository

| Existing area | Target change |
| --- | --- |
| `src/oryxenai/agents/discovery/` | Replace the 16-section Markdown-brief-as-primary handoff with a versioned, source-linked dossier and adaptive interview. A readable summary may be derived from it. |
| `src/oryxenai/agents/content_architect/` | Remove multi-route planning from the first release. Produce one complete single-page content package with typed component sections and finished copy. |
| `src/oryxenai/agents/shared/` and `config/models.toml` | Reuse the provider-neutral boundary and configured profiles; pin operation/prompt/schema versions. Check required transport capabilities without assuming a provider migration. |
| `src/oryxenai/jobs/`, `src/oryxenai/db/` | Reuse durable jobs, leases, and revision checks; add immutable dossier/content/site version records and transactional handoffs. |
| `src/oryxenai/storage/` | Extend the storage abstraction for immutable sources, bundles, manifests, and readback; retain compatible configured backends. |
| `frontend/` and `src/oryxenai/api/routes/` | Replace stage-by-stage approval UI with intake, focused questions, progress, generated preview, version history, and a change composer. |
| Old downstream generator | Do not resurrect its React/source-repair/route-batch pipeline. Build a small theme-bound HTML composer and browser verifier. |
| Deployment files | Keep operational work separate; the target architecture does not depend on moving providers. |

The planned design conflicts with D-113's **currently implemented** endpoint boundary; D-113 remains the truth about the active application until the new API, worker, and UI are deployed together. Existing approved user records require a deliberate migration/read compatibility plan; the new product must not infer a new dossier from a lossy old summary without user review.

### Implementation order and gates

1. **Theme foundation:** import the supplied CSS; build the component manifest and missing project/experience components; capture visual reference screenshots and responsive acceptance cases.
2. **Contracts and persistence:** implement extractor, dossier/content/render schemas, immutable version references, and migration paths. Prove stale jobs cannot promote.
3. **Discovery and Content Architect:** replace prompts and outputs; exercise sparse, detailed, ambiguous, and career-switching resumes. A complete package must be renderable without biography writing by Coding Engine.
4. **Coding Engine and preview:** render from supported components, bundle theme assets, verify real browser output, and expose the exact bundle in the frontend.
5. **Revision and repair loop:** factual, editorial, structural, and supported variant changes; ordered intent, bounded retries, cancellation, restore, and last-working-version behavior.
6. **Operational release:** compatible API/worker versions, storage readback, database migrations/backups, and measured capacity checks. Release only in a separately authorized task.
7. **Future capabilities:** optional photo upload, new theme versions, style editing, then JavaScript after a separately defined behavior contract.

See the next two documents for the exact artifacts, revision semantics, gates, and failure handling.
