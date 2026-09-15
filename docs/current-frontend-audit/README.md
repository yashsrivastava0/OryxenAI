# OryxenAI — Complete Frontend Forensic Audit Report
**Master Evaluation & Evidence Dossier**

---

## 1. Executive Summary & Forensic Mandate

This document serves as the master forensic UX, frontend, layout, and runtime audit of the live OryxenAI application (`http://localhost:8000/app`). 

This audit was conducted in strict adherence to an **EVIDENCE COLLECTION ONLY** mandate:
- **Zero source code modifications:** No Preact components, CSS stylesheets, TypeScript interfaces, backend API routes, database schemas, or automated tests were modified.
- **Zero cosmetic tweaks:** No styles or layouts were "improved" or patched during the audit.
- **Pure product observation:** Findings are derived strictly from running the real application in the browser, interacting with it as a first-time user, inspecting live DOM geometry, measuring layout metrics, analyzing backend database states, and logging network/console traffic.

The audit was executed end-to-end using an authentic, high-complexity professional profile:
[Input-Output-Of-Engine/resume.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/Input-Output-Of-Engine/resume.md) — Dr. Aditya Vikram Joshi (Principal Agentic AI Systems Architect with 11+ years of experience across Blinkit, MakeMyTrip, and IBM Research).

---

## 2. Environment & Runtime Context

- **Audit Date & Time:** 2026-09-12T16:05:00+05:30 to 2026-09-12T17:30:00+05:30
- **Git Branch:** `codex/code-generator-control-room`
- **Git Commit SHA:** `362f88c28bbbd184402d48a602048337328dd746`
- **Application Workspace URL:** `http://localhost:8000/app`
- **Dedicated Test Portfolio Session ID:** `5822e80f-83d8-4606-b25d-05e09e92d8b8`
- **Authenticated Identity:** `yashxbbdtest` (`yashxbbd@gmail.com`, UUID: `6a630f57-0f19-4480-8425-8b66a60eb2a8`)
- **Identity Provider:** Supabase Google OAuth (`https://diiestlnmpaarhhexwhi.supabase.co`)
- **Primary Tested Viewport:** 1536 × 695 (Standard desktop test class, evaluating 1440 × 900 baseline)
- **Responsive Viewport Checks:** 1366 × 768 (Short laptop), 768 × 1024 (Tablet), 390 × 844 (Mobile)
- **Active Backend Services:**
  - FastAPI Application Server: `uvicorn oryxenai.main:app --host 127.0.0.1 --port 8000 --reload` (PID: 24320)
  - Background Worker Daemon: `python -m oryxenai.jobs.worker` (PIDs: 22872, 18404)
  - Preview Gateway Daemon: `python -m oryxenai.preview.gateway` (PIDs: 19728, 16304)
  - PostgreSQL Database: `127.0.0.1:5432` (PID: 7620)

---

## 3. Journey Reached & Operational Status

The audit successfully progressed through the complete pipeline up to the terminal execution of Stage 05:

```text
[Google Sign-In] 
   └── Verified OAuth Boundary & Multi-Step Session Restore
        └── [Stage 01: Discovery]
             ├── Empty Intake Card (0 words / 0 chars)
             ├── 20KB Resume Ingestion & Dynamic Validation
             ├── 3-Question Adaptive Questionnaire Sequence
             ├── Brief Generation (Durable Job: discovery.build_or_revise_brief)
             └── Explicit Approval & Hash-Stamped Transition
                  └── [Stage 02: Content Architect]
                       ├── Content Strategy & Route Architecture (Durable Job: content_architect.build)
                       ├── 8,026px Full Review Pass
                       └── Explicit Approval Transition
                            └── [Stage 03: Visual Design Director]
                                 ├── Visual Direction & Scene Storyboard (Durable Job: visual_design_director.build)
                                 ├── 3,539px Full Review Pass
                                 └── Explicit Approval Transition
                                      └── [Stage 04: Build Preparation]
                                           ├── Handoff Brief Assembly (Durable Job: build_preparation.prepare)
                                           ├── Discovered Asset & Component Intent Review
                                           └── Transition to Generation
                                                └── [Stage 05: Code Generation & Preview]
                                                     ├── Initial "Stage Locked" Screen
                                                     ├── Plan Progress View (Durable Job: code_generator.v5.plan)
                                                     └── Terminal State: Background worker failed (HANDLER_ERROR); 
                                                         Frontend silently swallowed error in infinite polling freeze.
```

---

## 4. Master Layout, Scroll & Density Metrics Table

A primary finding of this audit is that **excessive scrolling and vertical expansion severely cripple user decision-making**. The table below documents the empirical DOM geometry measured directly in the browser across every screen state:

| Screen / Pipeline State | Viewport (W×H) | Document `scrollHeight` | Scroll Ratio (`scrollHeight / vh`) | Primary Decision Action | Action Y-Coordinate | Action Distance (Viewport Heights) | Observed Ergonomic Flaw |
|---|---:|---:|---:|---|---:|---:|---|
| **Discovery: Empty Intake** | 1536 × 695 | 808 px | **1.16x** | `Start Discovery →` | 680 px | 0.98 vh | Permanent scrollbar (+113px overflow) before any user input. |
| **Discovery: Question 01** | 1536 × 695 | 808 px | **1.16x** | `Save and continue` | 680 px | 0.98 vh | Stepper navigation is washed out behind the active question card. |
| **Discovery: Brief Review** | 1536 × 695 | 3,032 px | **4.36x** | `Approve & continue to Content Architect` | 2,850 px | **4.10 vh** | User must scroll 4+ viewports through linear text to approve. Button text wrapped across 4 lines. |
| **Content Architect: Review** | 1536 × 695 | 8,026 px | **11.55x** | `Approve & continue to Visual Design Director` | 7,994 px | **11.50 vh** | **Catastrophic sprawl.** Primary CTA is 8,000px down. Headings wrap 1 word per line in 160px column. Status pill collides with H1. |
| **Visual Design: Review** | 1536 × 695 | 3,539 px | **5.09x** | `Approve & continue to Build Preparation` | 3,244 px | **4.67 vh** | Primary CTA is 4.67 viewports down. All scenes hidden in collapsed disclosures. Status pill collides with H1. |
| **Build Preparation: Review** | 1536 × 695 | 2,180 px | **3.14x** | `Continue to Generate & Preview →` | 741 px | **1.06 vh** | CTA placed near top (good placement), but 2 large broken images display 20+ keyword alt strings. |
| **Generation: In Progress** | 1536 × 695 | 950 px | **1.37x** | N/A (Automated) | N/A | N/A | Permanent polling freeze on failed job; unstyled lowercase `plan` label; no recovery CTA. |

*Exact JSON measurements archived in [evidence/measurements/scroll_and_layout_metrics.json](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json).*

---

## 5. Stage-by-Stage Forensic Breakdown

### Stage 01: Discovery Agent (Intake, Questions & Brief)
- **Visual & Layout Inspection:**
  - On the empty intake screen, the vertical scrollbar is permanently visible (`scrollHeight: 808px` vs `innerHeight: 695px`), breaking the clean single-screen landing impression ([discovery-01-empty.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-01-empty.png)).
  - During the adaptive questioning sequence (`QUESTION 01 OF 03`), the top stage stepper becomes washed out and obscured behind the main card ([discovery-03-question-active.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png)).
  - The right 360px column is monopolized by the developer `HANDOFF UTILITY`, presenting raw JSON editor boxes (`understand_and_question` envelope) to non-technical users.
- **Brief Presentation Defect:**
  - The main title `Portfolio Discovery Brief — Dr. Aditya Vikram Joshi` wraps into **6 vertical lines** ("Portfolio \n Discovery \n Brief — \n Dr. Aditya \n Vikram \n Joshi"), taking up over 400px of height ([discovery-04-brief-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-04-brief-top.png)).
- **Action Loss:**
  - The primary decision button `Approve & continue to Content Architect` is buried at `y = 2,850px` (4.1 viewports down).
  - The button is constrained to a narrow pill, forcing its text to wrap across 4 lines with the trailing arrow icon clipped against the border ([discovery-05-approval-bottom.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-05-approval-bottom.png)).

---

### Stage 02: Content Architect (Content Strategy & Route Architecture)
- **Severe Layout Collision (FE-002):**
  - The status badge pill (`PLANNED ROUTES: 1 | STATUS: Under Review`) is positioned with CSS coordinates that cause it to collide directly over the letters of the word "Architecture" in the H1 title ([content-01-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-01-result-top.png)).
- **Catastrophic 8,026px Scroll Sprawl (FE-004):**
  - Content Architect exhibits the worst vertical inflation in the app, expanding to **8,026px (11.55x viewport height)** for a single 1-page route!
  - The primary approval CTA is 7,994px down ([content-03-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-03-actions.png)).
- **The 160px Column Squishing Flaw (FE-007):**
  - Content sections are constrained to a narrow ~160px column width while over 400px of adjacent canvas is completely vacant.
  - Headings wrap into 12 single-word vertical lines ("Translate / the / broad / profile / into a / clear / narrative..."), destroying readability ([content-02-result-mid.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-02-result-mid.png)).
- **Duplicate Copy Mapping (FE-011):**
  - The section heading and the body paragraph directly beneath it render the exact same text string twice in immediate succession.

---

### Stage 03: Visual Design Director (Visual Direction & Scene Storyboard)
- **Identical Status Pill Collision (FE-003):**
  - The status pill `STYLED ROUTES: 1 | SCENES: 4 | STATUS: Under Review` collides directly with "Architecture" in `Visual Direction & Experience Architecture` ([design-02-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-02-result-top.png)).
- **Representation Mismatch — Visual Stage is Not Visual (FE-015):**
  - The visual director outputs color palettes, font pairings, and motion intents. However, the UI renders **monochrome prose text and code boxes** with zero color swatches or typography specimens.
  - All 4 scenes are collapsed behind `<details><summary>Page direction detail · 1 routes</summary></details>`, leaving 70% of the screen as an empty grid ([design-03-scenes.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-03-scenes.png)).
- **Action Loss (FE-006, FE-014):**
  - Primary CTA is 3,244px down (4.67 viewports) with 4-line wrapped text inside a narrow button ([design-04-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-04-actions.png)).

---

### Stage 04: Build Preparation (Handoff Assembly & Discovered Assets)
- **Positive Ergonomic Contrast:**
  - Build Preparation correctly positions its primary action `Continue to Generate & Preview →` near the top at `y = 741px` (1.06 viewports) ([preparation-02-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-02-result-top.png)).
- **Broken Image Gallery with Raw Keyword Alt Strings (FE-008):**
  - Under "Discovered photography 15 candidates", 2 external photo candidates fail to load (blocked by strict CSP `img-src 'self'`).
  - The browser displays broken image icons with 25+ comma-separated search keywords (`home office, person, work, web design, business, workplace...`) rendered in huge grey boxes ([preparation-04-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-04-actions.png)).
- **Redundant Metric Duplication (FE-016):**
  - Left rail and center banner display duplicate counts (`Routes bound: 1`, `Discovered assets: 8`, etc.) 200px apart.

---

### Stage 05: Code Generation & Preview (Generation Failure & State Freeze)
- **Initial "Stage Locked" Dead End (FE-010):**
  - When the user transitions from approved Build Preparation, Stage 05 initially displays `Stage Locked` with zero buttons, progress bars, or explanations ([generation-01-start.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/generation/generation-01-start.png)).
- **Critical Silent Failure & Infinite Polling Hang (FE-001):**
  - The UI transitions to "Generating your portfolio" with a 5-step checklist and unstyled label `plan` ([generation-02-progress.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png)).
  - In the background, worker job `code_generator.v5.plan` (`5db62977-0bed-41ef-84ec-3f8e14491f6e`) **failed with `HANDLER_ERROR`**.
  - **The frontend completely failed to detect or display the failure.** It entered an infinite polling loop (`GET /api/v1/sessions/...` every 2s for 25+ minutes), displaying a frozen progress checklist with no error banner, toast, failure notice, or retry button!
- **State Desynchronization in Right Rail (FE-020):**
  - The right rail Handoff Utility remained stuck on Stage 01 Discovery JSON output, never updating to Code Generator.

---

## 6. Complete Issue Register (FE-001 to FE-020)

| ID | Stage | Category | Severity | Confidence | Reproducibility | Root Cause & User Impact Summary | Source Code Correlation |
|---|---|---|---|---|---|---|---|
| **FE-001** | Generation | Runtime / State | **Critical** | CONFIRMED | Always | **Silent Failure Hang:** Worker job failed with `HANDLER_ERROR`, but API session state stayed `active`. Frontend polled infinitely without error display or retry CTA. | [GenerationStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/generation/GenerationStage.tsx), [sessions.py](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/api/routes/sessions.py) |
| **FE-002** | Content | Visual / Layout | **High** | CONFIRMED | Always | **Title Badge Collision:** Stat pill (`PLANNED ROUTES: 1`) collides directly over the word "Architecture" in H1 heading due to absolute/float positioning. | [ContentStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/content/ContentStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L420-L480) |
| **FE-003** | Design | Visual / Layout | **High** | CONFIRMED | Always | **Title Badge Collision:** Stat pill collides directly over the word "Architecture" in `Visual Direction & Experience Architecture`. | [DesignStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/design/DesignStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L420-L480) |
| **FE-004** | Content | Scroll / Density | **High** | CONFIRMED | Always | **8,026px Vertical Sprawl:** Page height expands to 11.55x viewport height; primary decision CTA is buried 7,994px below the top. | [ContentStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/content/ContentStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L1200-L1260) |
| **FE-005** | Discovery | Scroll / Density | **High** | CONFIRMED | Always | **3,032px Vertical Sprawl:** Brief expands to 4.36x viewport height; primary "Approve" CTA is buried 2,850px below the top. | [DiscoveryStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/discovery/DiscoveryStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L900-L950) |
| **FE-006** | Design | Scroll / Density | **Medium** | CONFIRMED | Always | **3,539px Vertical Sprawl:** Visual direction expands to 5.09x viewport height; primary CTA is buried 3,244px below the top. | [DesignStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/design/DesignStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L1300-L1350) |
| **FE-007** | Content | Layout / Structure | **High** | CONFIRMED | Always | **160px Column Squishing:** Content constrained to 160px width forcing 12-line single-word wrapping while 400px sits empty. | [ContentStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/content/ContentStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L1220-L1280) |
| **FE-008** | Prepare | Data / Rendering | **High** | CONFIRMED | Always | **Broken Image Gallery:** External photography candidate images blocked by CSP (`img-src 'self'`), displaying 25+ raw keyword alt strings in grey boxes. | [BuildPreparationStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/preparation/BuildPreparationStage.tsx), [web.py](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/src/oryxenai/auth/web.py#L27-L47) |
| **FE-009** | Global | IA / Hierarchy | **High** | CONFIRMED | Always | **Developer Tooling Intrusion:** 360px `HANDOFF UTILITY` with raw JSON editor permanently visible in primary right column during normal user workflow. | [WorkspaceCanvas.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/components/WorkspaceCanvas.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L800-L860) |
| **FE-010** | Generation | State / UX | **High** | CONFIRMED | Always | **"Stage Locked" Dead End:** Initial arrival at Stage 05 displays "Stage Locked" with zero action buttons despite completed Stage 04 handoff. | [GenerationStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/generation/GenerationStage.tsx) |
| **FE-011** | Content | Data / Copy | **Medium** | CONFIRMED | Always | **100% Duplicate Copy:** Section H3 heading and descriptive paragraph render identical text string twice in succession. | [ContentStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/content/ContentStage.tsx) |
| **FE-012** | Discovery | Visual / Typography | **Medium** | CONFIRMED | Always | **6-Line Wrapped H1 Title:** Giant font size forces brief title to wrap into 6 lines across 400px of vertical space. | [DiscoveryStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/discovery/DiscoveryStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L910-L930) |
| **FE-013** | Discovery | Action / Layout | **Medium** | CONFIRMED | Always | **4-Line Button Text Wrapping:** Primary CTA button text wraps across 4 lines inside a narrow pill with arrow icon clipped. | [DiscoveryStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/discovery/DiscoveryStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L650-L680) |
| **FE-014** | Design | Action / Layout | **Medium** | CONFIRMED | Always | **4-Line Button Text Wrapping:** Design approval CTA wraps across 4 lines inside a narrow pill with clipped arrow. | [DesignStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/design/DesignStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L650-L680) |
| **FE-015** | Design | UX / Architecture | **Medium** | CONFIRMED | Always | **Visual Scenes Hidden in Disclosures:** Scenes and layout candidates are hidden behind collapsed `<details>` accordions by default. | [DesignStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/design/DesignStage.tsx), [SceneStoryboard.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/components/SceneStoryboard.tsx) |
| **FE-016** | Prepare | Data / Hierarchy | **Medium** | CONFIRMED | Always | **Duplicate Metric Counts:** Metric counts (routes, assets, components) duplicated between left rail and central banner. | [BuildPreparationStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/preparation/BuildPreparationStage.tsx) |
| **FE-017** | Global | Layout / Scroll | **Low** | CONFIRMED | Always | **Permanent Scrollbar on Empty Screen:** Scroll height is 808px on 695px viewport (+113px excess) before any user input. | [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L2050-L2078) |
| **FE-018** | Discovery | Visual / Hierarchy | **Low** | CONFIRMED | Always | **Stepper Occlusion:** Global progress stepper is washed out and obscured behind question card during Q&A. | [DiscoveryStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/discovery/DiscoveryStage.tsx), [shell.css](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/styles/shell.css#L300-L350) |
| **FE-019** | Generation | Copy / Polish | **Low** | CONFIRMED | Always | **Unstyled Label & Typo:** Lowercase unstyled `<p>plan</p>` label and missing whitespace in `1. ✓Queuing...`. | [GenerationStage.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/stages/generation/GenerationStage.tsx) |
| **FE-020** | Global | State / Synchronization | **Medium** | CONFIRMED | Always | **Stale Right Rail JSON Output:** Handoff utility JSON viewer fails to update to active stage, remaining frozen on Stage 01 Discovery output. | [WorkspaceCanvas.tsx](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/frontend/src/components/WorkspaceCanvas.tsx) |

*Full specifications with expanded reproduction notes in [03-issue-register.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/03-issue-register.md).*

---

## 7. Systemic Architectural & UX Problem Families

The 20 cataloged defects stem from six deep architectural and design system flaws:

### 1. The Result Representation Mismatch
The platform generates sophisticated creative artifacts (content strategy, design tokens, visual scenes, code generation). However, the frontend reduces nearly everything to **linear prose dumps or collapsed code blocks**. Visual Design Director does not show visual colors or fonts; Content Architect does not show an interactive sitemap; Build Preparation shows broken external image tags.

### 2. Catastrophic Vertical Sprawl & Action Loss
The application lacks a viewport height budget. Instead of leveraging multi-column cards, tabbed views, or sticky action docks, every piece of data is stacked vertically. In Content Architect, this creates an 8,026px page where the user must scroll through 11.5 screens of text before discovering the "Approve" button.

### 3. Rigid Grid Sizing & The 160px Column Paradox
The CSS layout uses fixed-width rails (260px left, 360px right) and restricts internal content containers to 160px–200px. This causes single-word wrapping and giant vertical page heights while hundreds of pixels of center canvas space sit completely empty.

### 4. Developer Tooling Intrusion in the User Workspace
The 360px `HANDOFF UTILITY` right rail was designed for platform debugging but was hard-mounted into the primary user experience. It clutters every stage, exposes raw JSON payloads, and consumes 25% of the screen.

### 5. Silent Error Concealment in Asynchronous State Loops
The frontend polling architecture decouples top-level session status from background worker job status. When a durable worker job fails, the API does not project the failure to the session, trapping the frontend in an infinite, silent polling freeze.

### 6. Content Security Policy (CSP) vs External Media Disconnect
The application enforces strict CSP (`img-src 'self'`), but the Build Preparation agent selects third-party external candidate photography URLs. When the frontend attempts to render these URLs, the browser blocks them, resulting in broken image boxes with raw search query alt text.

---

## 8. Complete Evidence & Document Directory Index

### Core Audit Reports:
- [00-audit-context.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/00-audit-context.md) — Exact runtime configuration, services, session IDs, and methodology.
- [01-screen-and-state-inventory.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/01-screen-and-state-inventory.md) — Comprehensive inventory of every screen, stage, status, and component.
- [02-end-to-end-observation-log.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/02-end-to-end-observation-log.md) — Chronological execution log from 16:05 to 17:20.
- [03-issue-register.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/03-issue-register.md) — Authoritative register of all 20 cataloged defects (FE-001 to FE-020).
- [04-layout-scroll-density-audit.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/04-layout-scroll-density-audit.md) — Layout geometry, scroll ratios, column squishing, and density analysis.
- [05-data-to-ui-mapping-audit.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/05-data-to-ui-mapping-audit.md) — Field-by-field schema vs view model vs rendered DOM comparison.
- [06-agent-state-and-action-audit.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/06-agent-state-and-action-audit.md) — Agent lifecycle synchronization, action ergonomics, and polling mechanics.
- [07-responsive-audit.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/07-responsive-audit.md) — Viewport analysis (Desktop 1536x695, Laptop 1366x768, Tablet 768x1024, Mobile 390x844).
- [08-console-network-runtime-findings.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/08-console-network-runtime-findings.md) — Network logs, polling traces, CSP blocking, and worker job failures.
- [09-accessibility-interaction-findings.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/09-accessibility-interaction-findings.md) — Keyboard navigation, focus order, ARIA live region noise, and contrast checks.
- [10-journey-and-information-architecture-findings.md](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/10-journey-and-information-architecture-findings.md) — Synthesis into root problem families and user journey evaluation.

### Raw Data & Log Artifacts:
- [evidence/measurements/scroll_and_layout_metrics.json](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json) — Exact pixel measurements and scroll ratios.
- [evidence/console/console_logs.txt](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/console/console_logs.txt) — Captured console output and polling logs.
- [evidence/network/network_findings.txt](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/network/network_findings.txt) — Captured network request sequence and status codes.

### Screenshot Evidence Archive (21 Screenshots):
- **Auth Shell:**
  - [evidence/screenshots/auth/auth-01-google-signin.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/auth/auth-01-google-signin.png) — Google OAuth sign-in boundary.
- **Global Shell:**
  - [evidence/screenshots/global/global-01-initial-shell.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/global/global-01-initial-shell.png) — Authenticated product shell.
- **Discovery Stage:**
  - [evidence/screenshots/discovery/discovery-01-empty.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-01-empty.png) — Empty intake card with vertical scrollbar.
  - [evidence/screenshots/discovery/discovery-02-resume-entered.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-02-resume-entered.png) — Ingested resume and character count validation.
  - [evidence/screenshots/discovery/discovery-03-question-active.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png) — Interactive Question 01 with obscured stepper and right rail JSON utility.
  - [evidence/screenshots/discovery/discovery-04-brief-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-04-brief-top.png) — 6-line wrapped H1 title and extracted profile rail.
  - [evidence/screenshots/discovery/discovery-05-approval-bottom.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-05-approval-bottom.png) — 4-line wrapped approval CTA buried 2,850px below top.
  - [evidence/screenshots/discovery/discovery-06-approved.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/discovery/discovery-06-approved.png) — Empty canvas transition state.
- **Content Architect Stage:**
  - [evidence/screenshots/content/content-01-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-01-result-top.png) — Direct collision between stat badge and H1 title "Architecture".
  - [evidence/screenshots/content/content-02-result-mid.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-02-result-mid.png) — 160px column squishing with 12-line single-word headings.
  - [evidence/screenshots/content/content-03-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/content/content-03-actions.png) — Primary approval CTA buried at y = 7,994px.
- **Visual Design Director Stage:**
  - [evidence/screenshots/design/design-01-working.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-01-working.png) — Working transition state.
  - [evidence/screenshots/design/design-02-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-02-result-top.png) — Direct collision between stat badge and H1 title "Architecture".
  - [evidence/screenshots/design/design-03-scenes.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-03-scenes.png) — Scenes hidden behind collapsed accordions.
  - [evidence/screenshots/design/design-04-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/design/design-04-actions.png) — Primary approval CTA buried at y = 3,244px.
- **Build Preparation Stage:**
  - [evidence/screenshots/preparation/preparation-01-working.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-01-working.png) — Working transition state.
  - [evidence/screenshots/preparation/preparation-02-result-top.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-02-result-top.png) — Handoff ready state with primary CTA placed at y = 741px.
  - [evidence/screenshots/preparation/preparation-03-briefs.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-03-briefs.png) — Notes for generator callout box.
  - [evidence/screenshots/preparation/preparation-04-actions.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/preparation/preparation-04-actions.png) — Broken image gallery with 20+ keyword alt strings.
- **Code Generation Stage:**
  - [evidence/screenshots/generation/generation-01-start.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/generation/generation-01-start.png) — "Stage Locked" dead end upon arrival.
  - [evidence/screenshots/generation/generation-02-progress.png](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png) — Permanent polling freeze on failed job with unstyled `plan` label.

---

## 9. Next Phase Declaration

> [!IMPORTANT]
> **Zero Implementation Performed:**  
> In strict conformance with instructions, no application code, styling, schemas, or tests were altered.  
> This complete forensic evidence package is archived under [`docs/current-frontend-audit/`](file:///c:/Users/Yash%20Srivastava/Desktop/01_Projects/OryxenAI/docs/current-frontend-audit/) and is ready to serve as the definitive factual baseline for the subsequent research and remediation phase.
