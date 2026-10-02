# OryxenAI: Proposed Architecture, Git Workflow, Agent Generation Pipeline, and Live Preview

> **Document Type:** Visual Architecture, Workflow Specification & Mermaid Reference Guide  
> **Target Audience:** Developers, System Architects, and Operators  
> **Status:** Architecture Reference & Visual Blueprint for Resume-to-Portfolio Generation  
> **Companion Documents:** [Architecture Overview](10-proposed-resume-portfolio-system.md) · [Agent & Artifact Contracts](11-agent-and-artifact-contracts.md) · [Generation & Operations Design](12-generation-preview-revisions-and-operations.md)

---

## 1. Executive Summary & Architecture Map

OryxenAI transforms an uploaded resume into a verified, publication-grade portfolio website through an orchestrated sequence of **specialized AI agents** and **deterministic software services**.

The system is strictly divided into clear boundaries:
1. **Git Branch & CI/CD Layer:** A two-tier branch model (`staging` for development, protected `deployment` for production) with an Azure VM self-hosted runner and automated quality checks.
2. **Infrastructure Layer:** A lightweight, single-VM Docker Compose stack featuring Caddy (edge reverse proxy and automatic HTTPS), FastAPI (API & product shell), a durable background worker, PostgreSQL 16, and VM-local persistent storage.
3. **Agent Generation Pipeline:**
   - **Intake Service (Deterministic):** Extracts text, preserves layout hierarchy, and creates source spans.
   - **Discovery Agent (AI):** Parses career facts, identifies ambiguities, and conducts a 1–3 question interview only when necessary.
   - **Content Architect Agent (AI):** Shapes the editorial narrative, selects sections, and writes every sentence of public copy (linked to verified facts).
   - **Coding Engine (Hybrid AI + Deterministic):** Selects component variants from a prebuilt theme catalogue (`RenderPlan/v1`) and compiles pristine semantic `index.html` referencing pre-verified `styles.css`.
4. **Verification & Live Preview Layer:** Automated headless Chromium checks validate DOM and mobile responsiveness before atomically serving the portfolio in a split-screen, sandboxed iframe.

---

## 2. Git Branching, Release Gate & CI/CD Architecture

The release workflow guarantees that code deployed to the Azure VM is clean, reviewed, and fully verified. Direct pushes to the production branch are prohibited by GitHub repository rulesets.

### 2.1 Branch Topology & Promotion Flow

```mermaid
gitGraph
    commit id: "init-repo"
    branch staging
    checkout staging
    commit id: "feat-discovery-agent"
    commit id: "fix-content-architect"
    commit id: "test-quality-gate"
    checkout main
    merge staging id: "pr-staging-merge"
    branch deployment
    checkout deployment
    merge staging id: "PR-to-deployment" tag: "v1.0-release-sha"
    checkout staging
    commit id: "feat-theme-enhancement"
```

### 2.2 End-to-End CI/CD Pipeline to the Azure VM

The Azure VM runs a GitHub Actions self-hosted runner as a `systemd` daemon. It polls GitHub via **outbound HTTPS**, which eliminates the need to expose inbound SSH ports to the public internet or GitHub IP ranges.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / Operator
    participant GH as GitHub Repository & CI
    participant Runner as Azure VM Self-Hosted Runner
    participant Script as scripts/azure-deploy.sh
    participant Compose as Docker Compose Engine
    participant AppWorker as Containers (App, Worker, Caddy)

    Dev->>GH: Push commit to feature branch & open PR to `staging`
    GH->>GH: Execute Quality Gate (Ruff, Mypy, Pytest, Docker Smoke)
    Dev->>GH: Merge into `staging` after checks pass

    Note over Dev,GH: Human Operator explicitly initiates production release
    Dev->>GH: Open PR from `staging` to `deployment`
    GH->>GH: Run `deployment-ci-gate` ruleset & tests
    Dev->>GH: Merge PR via `gh pr merge --merge` (Never squash/rebase)

    GH->>Runner: Notify new commit on `refs/heads/deployment` (Outbound poll)
    Runner->>Script: Execute ./scripts/azure-deploy.sh deploy <RELEASE_SHA>
    Script->>Script: Fetch clean commit & render production overlay
    Script->>Compose: docker compose -f compose.production.yaml up -d --build
    Compose->>Compose: Run one-shot `migrate` (alembic upgrade head)
    Compose->>AppWorker: Gracefully restart `app` & `worker`
    Compose->>AppWorker: Reload `caddy` configuration
    Script->>Script: Execute ./scripts/azure-deploy.sh verify (Health probes)
    Script-->>Runner: Deployment Succeeded (or trigger rollback on failure)
```

---

## 3. High-Level System Infrastructure & Container Topology

All application components run inside a single Azure Ubuntu VM orchestrated via Docker Compose. No external managed database, Redis, or Kubernetes is required.

```mermaid
graph TB
    subgraph PublicInternet ["Public Internet"]
        ClientBrowser["User Browser"]
        GoogleOAuth["Google OAuth 2.0"]
        OpenAIEndpoint["OpenAI Model API (gpt-6-luna)"]
    end

    subgraph AzureHost ["Azure Linux VM (Host Environment)"]
        RunnerService["GitHub Actions Self-Hosted Runner (systemd)"]
        
        subgraph HostStorage ["VM Persistent Storage (/srv/oryxenai/)"]
            PGData[("Postgres Data: /postgres")]
            PreviewData[("Site Previews: /preview")]
            ArtifactsData[("Agent Artifacts: /artifacts")]
            CaddyData[("Caddy Certificates: /caddy")]
            BackupStore[("Backups: /srv/oryxenai-backups")]
        end

        subgraph DockerComposeStack ["Docker Compose Network: compose.production.yaml"]
            CaddyContainer["Caddy v2 Edge Proxy<br/>Ports: 80 & 443<br/>UID: 1001"]

            subgraph BackendBridge ["Internal Bridge Network: backend"]
                FastAPIApp["FastAPI Web App (Uvicorn)<br/>Port: 8000 (Internal Only)<br/>UID: 1001"]
                DurableWorker["Durable Python Worker<br/>(Background Job Executor)<br/>UID: 1001"]
                MigrationJob["Alembic Migration<br/>(One-shot on startup)"]
                PostgresDB[("PostgreSQL 16.4 Alpine<br/>Port: 5432 (Internal Only)")]
            end
        end
    end

    subgraph ExternalAuth ["SaaS Services"]
        SupabaseAuth["Supabase Authentication"]
    end

    %% Network Connections
    ClientBrowser -->|HTTPS 443| CaddyContainer
    CaddyContainer -->|Reverse Proxy| FastAPIApp
    ClientBrowser <-->|OAuth Flow| GoogleOAuth
    GoogleOAuth <--> SupabaseAuth
    FastAPIApp <-->|Verify JWT / Session| SupabaseAuth

    %% Database & Worker Connections
    MigrationJob -.->|1. Apply schema changes| PostgresDB
    FastAPIApp -->|2. Store session & enqueue jobs| PostgresDB
    DurableWorker -->|3. Claim jobs via SKIP LOCKED| PostgresDB
    DurableWorker -->|4. Prompt Model via ModelClient| OpenAIEndpoint

    %% Storage Mounts
    PostgresDB --- PGData
    FastAPIApp --- PreviewData
    DurableWorker --- PreviewData
    DurableWorker --- ArtifactsData
    CaddyContainer --- CaddyData
    BackupStore -.->|pg_dump & tar backups| HostStorage
```

---

## 4. End-to-End Agent Generation Pipeline

When a user submits their resume, the orchestrator advances through a sequential pipeline of deterministic extractors and AI agents.

```mermaid
flowchart TD
    Start([User Uploads Resume + Goal]) --> Intake[Intake Service: Text Extraction & Normalization]
    Intake --> SourceDoc[(SourceDocument/v1)]
    
    SourceDoc --> Discovery[Discovery Agent: AI Fact & Intent Extraction]
    
    Discovery --> CheckGaps{Are there critical<br/>factual gaps?}
    CheckGaps -- Yes --> AskQuestions[Present 1-3 Targeted Questions to User]
    AskQuestions --> UserResponse[User Answers or Skips]
    UserResponse --> FinalizeDossier[Discovery Finalization]
    CheckGaps -- No --> FinalizeDossier
    
    FinalizeDossier --> DossierDoc[(DiscoveryDossier/v1)]
    
    DossierDoc --> ContentArch[Content Architect Agent: AI Story & Copywriting]
    ThemeManifest[Prebuilt Theme Manifest & Semantic Vocabulary] --> ContentArch
    
    ContentArch --> ContentPkg[(PortfolioContent/v1)]
    
    ContentPkg --> CodingEngine[Coding Engine: AI Variant Selection & Plan]
    CodingEngine --> RenderPlan[(RenderPlan/v1)]
    
    RenderPlan --> HostRenderer[Deterministic Host Renderer]
    PrebuiltCSS[Prebuilt Theme Stylesheet: styles.css] --> HostRenderer
    HostRenderer --> SiteCandidate[(Candidate SiteVersion/v1: index.html)]
    
    SiteCandidate --> HeadlessQA[Automated Headless Chromium QA Gate]
    HeadlessQA --> QAPass{Checks Passed?<br/>DOM, Mobile, Links}
    
    QAPass -- Yes --> Promotion[Atomic Promotion to Active Version]
    QAPass -- No --> RepairLog[Log Findings & Trigger Recovery]
    
    Promotion --> LivePreview([Live Interactive Preview in Split-Screen Workspace])
```

---

## 5. Agent Responsibilities, Contracts & Execution Details

| Stage | Type | Primary Responsibility | Input Contract | Output Contract | Model / Engine |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Intake** | Deterministic | Extracts plain text from PDF/DOCX/TXT; preserves headings, bullets, and line numbers; indexes source spans. | Binary file or pasted text + user goal | `SourceDocument/v1` | Python `pypdf` / `docx` |
| **2. Discovery** | AI Agent | Extracts verified career facts, roles, projects, metrics, and individual vs. team ownership. Asks 1–3 focused, skippable questions if key context is ambiguous. | `SourceDocument/v1` + user intent | `DiscoveryDossier/v1` | OpenAI `gpt-6-luna` via `ModelClient` |
| **3. Content Architect** | AI Agent | Directs editorial positioning; decides section sequence; writes 100% of visible public copy (no placeholders or "TODOs"); binds each statement to dossier fact IDs. | `DiscoveryDossier/v1` + Theme vocabulary | `PortfolioContent/v1` | OpenAI `gpt-6-luna` via `ModelClient` |
| **4. Coding Engine** | Hybrid (AI + Host) | **AI:** Selects supported theme component variants and asset slots (`RenderPlan/v1`).<br/>**Host:** Compiles semantic `index.html` referencing prebuilt `styles.css`. | `PortfolioContent/v1` + `ThemeManifest/v1` | `RenderPlan/v1` & `SiteVersion/v1` | AI Plan + Deterministic HTML Serializer |
| **5. Verification Gate** | Deterministic | Headless Chromium renders page at 320px, 768px, and 1200px viewports; checks for console errors, text overflow, and dead links. | `SiteVersion/v1` files | `VerificationReceipt/v1` | Headless Chromium (Playwright/Puppeteer) |

---

## 6. How the Live Preview is Displayed (UI & Workspace Architecture)

The frontend features a **split-screen desktop layout** separating interactive controls from the live preview frame.

### 6.1 Frontend Screen Structure

```mermaid
graph TD
    subgraph ProductWindow ["OryxenAI Workspace Window"]
        TopNav["Top Navigation Bar: Portfolio Title | Theme Selector | Export ZIP Button | User Profile"]

        subgraph SplitPane ["Horizontal Split Workspace"]
            subgraph LeftConsole ["Left Panel: Interactive Control & Revision Studio (40% width)"]
                IntakeCard["1. Intake & Source Details<br/>• Uploaded: Resume.pdf<br/>• Goal: Staff Backend Engineer"]
                StepperCard["2. Pipeline Progress Stepper<br/>✓ Resume Extracted<br/>✓ Career Facts Dossier Ready<br/>✓ Editorial Copy Written<br/>● Live Preview Ready"]
                QuestionCard["3. Active Questions / Clarifications<br/>(Displays when Discovery needs context; skippable)"]
                RevisionCard["4. Revision Console<br/>[ Text input: 'Shorten headline and emphasize AWS...' ]<br/>[ Version Switcher: v1 (Active) | v2 (Building...) ]"]
            end

            subgraph RightPreview ["Right Panel: Live Sandboxed Iframe (60% width)"]
                ViewportToggle["Device Toggle Bar: [ Desktop (1200px) ] | [ Tablet (768px) ] | [ Mobile (375px) ]"]
                PreviewFrame["Sandboxed Iframe:<br/>src='/p/{portfolio_id}/{version_id}/index.html'<br/>• Renders pure index.html + styles.css<br/>• Zero app runtime scripts inside preview<br/>• Fully scrollable, clickable, and responsive"]
            end
        end
    end

    TopNav --- SplitPane
```

### 6.2 Atomic Version Promotion & Zero-Flicker Revisions

When the user requests an edit in the left console:
1. The currently approved portfolio (`v1`) **remains visible and interactive** in the iframe.
2. The server spins up a background worker job to build `v2` (routing the edit to Discovery, Content Architect, or Coding Engine as required).
3. The new candidate `v2` undergoes automated headless browser verification in isolation.
4. Only upon passing all checks does the server update `active_site_version_id` in PostgreSQL.
5. The frontend receives the revision event via polling and updates the iframe source to `v2` without screen flash or broken intermediary states.

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant UI as Left Control Panel
    participant Frame as Right Iframe Preview
    participant API as FastAPI Backend
    participant Worker as Background Worker
    participant DB as PostgreSQL

    Note over User,Frame: User is viewing verified SiteVersion v1 in Iframe
    User->>UI: Enter revision: "Make the billing project title punchier"
    UI->>API: POST /api/portfolio/{id}/revisions (edit_event)
    API->>DB: Enqueue build job for candidate v2
    API-->>UI: Revision accepted (status: 'composing')
    UI->>UI: Show subtle background progress indicator

    Note over Frame: Iframe continues showing v1 without disruption
    Worker->>DB: Claim build job
    Worker->>Worker: Content Architect rewrites section & Engine compiles v2 HTML
    Worker->>Worker: Run Headless Chromium verification on v2
    Worker->>DB: Mark v2 as 'verified' & promote active_site_version_id = v2

    loop Polling Status
        UI->>API: GET /api/portfolio/{id}/state
        API-->>UI: active_version = v2, status = 'ready'
    end

    UI->>Frame: Update iframe src to /p/{portfolio_id}/v2/index.html
    Frame-->>User: Smoothly displays updated portfolio v2
```

---

## 7. Artifact Contract Chain & Data Traceability

Every piece of text displayed on the final portfolio traces directly back through immutable artifacts to the original uploaded resume.

```mermaid
classDiagram
    class SourceDocument {
        +String contract_version = "SourceDocument/v1"
        +String document_id
        +String original_sha256
        +String extracted_text
        +List source_spans
    }

    class DiscoveryDossier {
        +String contract_version = "DiscoveryDossier/v1"
        +String dossier_id
        +String source_document_id
        +SubjectProfile subject
        +List facts
        +List roles
        +List projects
        +List open_gaps
    }

    class PortfolioContent {
        +String contract_version = "PortfolioContent/v1"
        +String content_id
        +String dossier_id
        +EditorialStory story
        +List sections
        +List claim_bindings
        +Metadata metadata
    }

    class RenderPlan {
        +String contract_version = "RenderPlan/v1"
        +String plan_id
        +String content_id
        +String theme_id = "editorial-forest/v1"
        +List placements
    }

    class SiteVersion {
        +String contract_version = "SiteVersion/v1"
        +String site_version_id
        +String render_plan_id
        +String index_html_hash
        +String styles_css_hash
        +String preview_url
        +String verification_status
    }

    SourceDocument --> DiscoveryDossier : Parsed by Discovery Agent
    DiscoveryDossier --> PortfolioContent : Structured by Content Architect
    PortfolioContent --> RenderPlan : Layout mapped by Coding Engine
    RenderPlan --> SiteVersion : Serialized & Verified into Final Site
```

### Claim Binding Guarantee:
In `PortfolioContent/v1`, every factual claim carries a direct reference to a verified fact ID:
```json
{
  "field_path": "sections[billing-work].copy.outcome",
  "text": "The team achieved a 25% reduction in billing queue latency.",
  "fact_ids": ["fact-17"]
}
```
This guarantees that the AI cannot invent metrics, hallucinate credentials, or misattribute team achievements to an individual.

---

## 8. Summary of Architectural Decisions

1. **AI Where Judgment is Required:** Discovery and Content Architect are full AI agents utilizing `gpt-6-luna` for reading comprehension, factual deduction, and editorial writing.
2. **Determinism Where Safety is Required:** Code generation does **not** rely on raw LLM CSS creation. Instead, the AI selects component placements from a prebuilt, responsive theme catalogue (`editorial-forest/v1`), and a deterministic host compiler writes the HTML.
3. **No Downtime / Zero-Flicker Preview:** The preview is sandboxed in an iframe. Generating or revising a portfolio never destroys or blanks the current active version until the new revision passes headless browser checks.
4. **Single-VM Production Simplicity:** The system avoids unnecessary infrastructure bloat (no Kubernetes, Redis, or managed database clusters), operating reliably on a single Azure Linux VM managed via Docker Compose and an automated self-hosted GitHub Actions runner.
