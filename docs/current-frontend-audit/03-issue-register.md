# 03 — Issue Register

This register catalogs every distinct frontend defect and friction point discovered during the forensic audit of OryxenAI.

---

### Issue Summary Table

| ID | Stage | Category | Severity | Confidence | Reproducibility | Short Summary |
|---|---|---|---|---|---|---|
| **FE-001** | Generation | Runtime / State | **Critical** | CONFIRMED | Always | Backend job failure silently swallowed; UI stuck indefinitely on "Generating" |
| **FE-002** | Content | Visual / Layout | **High** | CONFIRMED | Always | Stat badge directly overlaps and collides with H1 title "Architecture" |
| **FE-003** | Design | Visual / Layout | **High** | CONFIRMED | Always | Stat badge directly overlaps and collides with H1 title "Architecture" |
| **FE-004** | Content | Scroll / Density | **High** | CONFIRMED | Always | 8,026px page height; primary decision CTA is 11.5 viewport heights below fold |
| **FE-005** | Discovery | Scroll / Density | **High** | CONFIRMED | Always | 3,032px page height; primary "Approve" CTA is 4.1 viewport heights below fold |
| **FE-006** | Design | Scroll / Density | **Medium** | CONFIRMED | Always | 3,539px page height; primary CTA is 4.67 viewport heights below fold |
| **FE-007** | Content | Layout / Structure | **High** | CONFIRMED | Always | Content column squished to ~160px; headings wrap 1 word per line over 12 lines while 400px sits empty |
| **FE-008** | Prepare | Data / Rendering | **High** | CONFIRMED | Always | Discovered photography renders broken image icons with 20+ comma-separated keyword alt strings |
| **FE-009** | Global | IA / Hierarchy | **High** | CONFIRMED | Always | Developer "HANDOFF UTILITY" with raw JSON editor occupies right column during normal user workflow |
| **FE-010** | Generation | State / Copy | **High** | CONFIRMED | Always | Stage 05 initially displays "Stage Locked" with zero explanation or buttons despite completed handoff |
| **FE-011** | Content | Data / Copy | **Medium** | CONFIRMED | Always | Section headings and body paragraphs are 100% duplicate identical strings rendered twice |
| **FE-012** | Discovery | Visual / Typography | **Medium** | CONFIRMED | Always | H1 title font size causes 6-line awkward wrapping across 60% of viewport height |
| **FE-013** | Discovery | Action / Layout | **Medium** | CONFIRMED | Always | Primary CTA button text wraps onto 4 lines inside a narrow pill with clipped arrow icon |
| **FE-014** | Design | Action / Layout | **Medium** | CONFIRMED | Always | Primary CTA button text wraps onto 4 lines inside a narrow pill with clipped arrow icon |
| **FE-015** | Design | UX / Architecture | **Medium** | CONFIRMED | Always | Visual scenes and layout candidates are hidden inside collapsed accordions by default |
| **FE-016** | Prepare | Data / Hierarchy | **Medium** | CONFIRMED | Always | Metric counts (routes, assets, components) duplicated between left rail and central banner |
| **FE-017** | Global | Layout / Scroll | **Low** | CONFIRMED | Always | Vertical scrollbar present on initial empty intake screen (808px height on 695px viewport) |
| **FE-018** | Discovery | Visual / Copy | **Low** | CONFIRMED | Always | Stepper navigation is washed out and obscured behind question card during Discovery Q&A |
| **FE-019** | Generation | Copy / Typography | **Low** | CONFIRMED | Always | Unstyled lowercase label `plan` and missing whitespace `✓Queuing` in generation progress checklist |
| **FE-020** | Global | State / Synchronization | **Medium** | CONFIRMED | Always | Right rail Handoff Utility remains stuck on Stage 01 Discovery JSON output across all subsequent stages |

---

## Detailed Issue Specifications

### FE-001: Backend Job Failure Silently Swallowed — UI Frozen Indefinitely
- **Stage:** Generate & Preview (Stage 05)
- **Category:** Runtime / State / Error Handling
- **Severity:** **Critical**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** When background worker job `code_generator.v5.plan` failed with `HANDLER_ERROR`, the frontend polling loop received 200 OK responses with `session_status='active'` and remained permanently stuck on "Generating your portfolio". No error banner, toast, boundary, or retry button was shown.
- **Expected Behavior:** The frontend should detect failure state from the session or run projection, stop polling, display an informative error banner with failure details, and provide a clear "Retry Generation" action.
- **User Impact:** The user is left waiting indefinitely thinking the system is working, with no path forward except hard page reloads or abandoning the app.
- **Evidence:** `evidence/screenshots/generation/generation-02-progress.png`, `evidence/console/console_logs.txt`, DB query row `5db62977-0bed-41ef-84ec-3f8e14491f6e`.
- **Source Correlation:** `frontend/src/stages/generation/GenerationStage.tsx`, `src/oryxenai/api/routes/sessions.py`.

---

### FE-002: Stat Badge Overlaps and Collides with H1 Title "Architecture" (Content Stage)
- **Stage:** Content Architect (Stage 02)
- **Category:** Visual / Layout / CSS
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** The stat pill container (`PLANNED ROUTES: 1 | STATUS: Under Review`) is positioned with CSS that causes it to collide horizontally and vertically directly over the letters of "Architecture" in the H1 title.
- **Expected Behavior:** Header metadata/status pills should sit either above the title, in a dedicated flex/grid header row, or right-aligned without absolute overlapping.
- **User Impact:** Extreme unpolished appearance; text illegibility.
- **Evidence:** `evidence/screenshots/content/content-01-result-top.png`.
- **Source Correlation:** `frontend/src/stages/content/ContentStage.tsx`, `frontend/src/styles/shell.css`.

---

### FE-003: Stat Badge Overlaps and Collides with H1 Title "Architecture" (Design Stage)
- **Stage:** Visual Design Director (Stage 03)
- **Category:** Visual / Layout / CSS
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** The stat pill (`STYLED ROUTES: 1 | SCENES: 4 | STATUS: Under Review`) collides directly with the word "Architecture" in `Visual Direction & Experience Architecture`.
- **Expected Behavior:** Metadata badges must be placed cleanly outside the title bounding box.
- **User Impact:** Severe visual defect on a key review screen.
- **Evidence:** `evidence/screenshots/design/design-02-result-top.png`.
- **Source Correlation:** `frontend/src/stages/design/DesignStage.tsx`, `frontend/src/styles/shell.css`.

---

### FE-004: Excessive Vertical Sprawl — Primary CTA 11.5 Viewport Heights Down (Content Stage)
- **Stage:** Content Architect (Stage 02)
- **Category:** Scroll / Density / Action Placement
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** Document height expands to 8,026px (11.55x viewport height). The primary "Approve & continue to Visual Design Director" CTA is located at y=7,994px.
- **Expected Behavior:** High-level strategic review and primary handoff actions should be visible in the initial 1-2 viewports, or accompanied by a sticky action bar, rather than requiring 8,000 pixels of scrolling.
- **User Impact:** Extreme fatigue; users frequently miss or get lost trying to find how to proceed to the next stage.
- **Measurements:** `scrollHeight`: 8,026px, `innerHeight`: 695px, CTA distance: 7,994px (11.50 vh).
- **Evidence:** `evidence/screenshots/content/content-03-actions.png`, `evidence/measurements/scroll_and_layout_metrics.json`.

---

### FE-005: Excessive Vertical Sprawl — Primary CTA 4.1 Viewport Heights Down (Discovery Stage)
- **Stage:** Discovery (Stage 01)
- **Category:** Scroll / Density / Action Placement
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** Document scroll height is 3,032px. The "Approve & continue to Content Architect" button sits at y=2,850px.
- **Expected Behavior:** Key brief summary and approval controls should be immediately accessible above or near the fold.
- **Measurements:** `scrollHeight`: 3,032px, `innerHeight`: 695px, CTA distance: 2,850px (4.10 vh).
- **Evidence:** `evidence/screenshots/discovery/discovery-05-approval-bottom.png`.

---

### FE-006: Excessive Vertical Sprawl — Primary CTA 4.67 Viewport Heights Down (Design Stage)
- **Stage:** Visual Design Director (Stage 03)
- **Category:** Scroll / Density / Action Placement
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** Document height is 3,539px. Primary CTA is at y=3,244px.
- **Measurements:** `scrollHeight`: 3,539px, `innerHeight`: 695px, CTA distance: 3,244px (4.67 vh).
- **Evidence:** `evidence/screenshots/design/design-04-actions.png`.

---

### FE-007: Severe Column Squishing with Wasted Horizontal Space (Content Stage)
- **Stage:** Content Architect (Stage 02)
- **Category:** Layout / Structure
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** Content section titles and descriptions are constrained into a narrow ~160px column, forcing 12 lines of single-word wrapping ("Translate / the / broad / profile / into a / clear..."), while ~400px of width on the canvas sits completely blank.
- **Expected Behavior:** Grid columns should use responsive auto-fit/fr units so text has adequate line length (45-75 characters) rather than 1-2 words per line.
- **User Impact:** Painful reading experience; artificially inflates page height to 8,000px.
- **Evidence:** `evidence/screenshots/content/content-02-result-mid.png`.

---

### FE-008: Broken Image Gallery with 20+ Comma-Separated Keyword Alt Strings
- **Stage:** Build Preparation (Stage 04)
- **Category:** Data / Rendering / Visual Quality
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** Under "Discovered photography 15 candidates", 2 large grey boxes render broken image icons with huge walls of raw search keywords in alt text (`home office, person, work, web design, business, workplace, monitor, computer, keyboard, screen, laptop, office work...`).
- **Expected Behavior:** Images should load verified local or proxied thumbnails; if an image fails to load, show a clean fallback card or omit broken candidates.
- **User Impact:** Looks like a broken prototype or scraping failure.
- **Evidence:** `evidence/screenshots/preparation/preparation-04-actions.png`.

---

### FE-009: Developer "HANDOFF UTILITY" Dominates Primary Right Column
- **Stage:** Global (All Stages)
- **Category:** Information Architecture / Visual Hierarchy
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** A 360px-wide right column titled "HANDOFF UTILITY - Agent output" with "Copy JSON" links and a black monospace raw JSON editor box is persistently displayed during everyday user tasks (answering questions, reviewing narrative, selecting options).
- **Expected Behavior:** Developer tools and raw JSON dumps should be housed in a collapsed drawer, modal, or dedicated `/dev` panel rather than occupying primary desktop real estate.
- **User Impact:** Clutters screen, distracts non-technical users, squishes the actual content into a narrow central strip.
- **Evidence:** All stage screenshots (`discovery-03`, `discovery-04`, `content-01`, `design-02`, `preparation-02`).

---

### FE-010: Stage 05 Displays "Stage Locked" Dead End on Initial Arrival
- **Stage:** Generate & Preview (Stage 05)
- **Category:** State / Flow / UX
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** When navigating from Stage 04 to Stage 05, the screen initially says `Stage Locked` with zero buttons, progress indicators, or explanation, before asynchronously loading or requiring another action.
- **Expected Behavior:** If the user arrived from approved Stage 04, Stage 05 should immediately present the generation readiness summary and a prominent "Generate Portfolio" action.
- **User Impact:** High confusion; user thinks they broke the pipeline or lack permissions.
- **Evidence:** `evidence/screenshots/generation/generation-01-start.png`.

---

### FE-011: Section Headings and Body Text Are 100% Identical Duplicate Strings
- **Stage:** Content Architect (Stage 02)
- **Category:** Data Mapping / Copy
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** Under `HOME : SYSTEMS-PRACTICE`, the H3 heading is `"Translate the broad profile into a clear narrative about the connected systems practice."` and the paragraph immediately below it is the exact same string repeated.
- **Expected Behavior:** Heading should be the concise section title/role; body should be the actual section description or narrative excerpt.
- **User Impact:** Repetitive, robotic feel.
- **Evidence:** `evidence/screenshots/content/content-02-result-mid.png`.

---

### FE-012: H1 Title Font Size Causes 6-Line Awkward Wrapping (Discovery Brief)
- **Stage:** Discovery (Stage 01)
- **Category:** Visual / Typography
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** Title `Portfolio Discovery Brief — Dr. Aditya Vikram Joshi` wraps into 6 separate lines ("Portfolio \n Discovery \n Brief — \n Dr. Aditya \n Vikram \n Joshi"), occupying over 400px of vertical space.
- **Expected Behavior:** Font size should scale appropriately (e.g. `clamp(1.75rem, 3vw, 2.5rem)`) so titles wrap cleanly in 1-2 lines.
- **Evidence:** `evidence/screenshots/discovery/discovery-04-brief-top.png`.

---

### FE-013 / FE-014: Primary CTA Button Text Wraps Across 4 Lines with Clipped Arrow
- **Stage:** Discovery (Stage 01) & Visual Design Director (Stage 03)
- **Category:** Action / Layout
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** CTA button text wraps onto 4 lines ("Approve &\ncontinue to\nContent\nArchitect") inside a narrow fixed-width pill; the arrow icon is clipped on the right border.
- **Expected Behavior:** Button width should be `auto` or `min-content` with `white-space: nowrap` or balanced 2-line wrap.
- **Evidence:** `evidence/screenshots/discovery/discovery-05-approval-bottom.png`, `evidence/screenshots/design/design-04-actions.png`.

---

### FE-015: Visual Scenes and Layout Candidates Hidden in Collapsed Disclosures
- **Stage:** Visual Design Director (Stage 03)
- **Category:** UX / Information Architecture
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** All visual storyboard scenes and layout candidates are collapsed behind disclosure carets (`▶ Page direction detail`, `▶ Adapted layout candidates`). The default view is mostly empty whitespace.
- **Expected Behavior:** Visual design should be visual! Scenes should be rendered as an interactive horizontal storyboard or visible visual cards.
- **Evidence:** `evidence/screenshots/design/design-03-scenes.png`.

---

### FE-016: Redundant Metric Counts Duplicated Between Left Rail and Center Banner
- **Stage:** Build Preparation (Stage 04)
- **Category:** Data / Information Hierarchy
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** Left rail shows `Routes bound: 1`, `Resources found: 8 found · 0 missing`, `Component suggestions: 1`. 200px to the right, a giant banner shows `ROUTES: 1 | RESOURCE NEEDS: 11 | DISCOVERED ASSETS: 8 | COMPONENT INTENTS: 1`.
- **Expected Behavior:** Unify metadata display into a single authoritative location.
- **Evidence:** `evidence/screenshots/preparation/preparation-02-result-top.png`.

---

### FE-017: Vertical Scrollbar Present on Empty Intake Screen
- **Stage:** Global / Discovery
- **Category:** Layout / Scroll
- **Severity:** **Low**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** Document height is 808px on a 695px viewport, creating an unnecessary vertical scrollbar before any user input.
- **Expected Behavior:** Single-screen intake should fit 100vh without scrolling on standard desktop viewports (1440x900 / 1366x768).
- **Measurements:** `scrollHeight`: 808px vs `innerHeight`: 695px (+113px excess).
- **Evidence:** `evidence/measurements/scroll_and_layout_metrics.json`.

---

### FE-018: Stepper Navigation Obscured Behind Question Card
- **Stage:** Discovery Questions
- **Category:** Visual / Z-Index / Hierarchy
- **Severity:** **Low**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** The global stage progress stepper is washed out or overlapped by the question card backdrop.
- **Evidence:** `evidence/screenshots/discovery/discovery-03-question-active.png`.

---

### FE-019: Unstyled Progress Label `plan` and Typo in Generation Progress
- **Stage:** Generation (Stage 05)
- **Category:** Copy / Polish
- **Severity:** **Low**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** Progress list contains an unstyled lowercase label `plan` and missing whitespace in `1. ✓Queuing...`.
- **Evidence:** `evidence/screenshots/generation/generation-02-progress.png`.

---

### FE-020: Handoff Utility Rail Remains Stuck on Stage 01 Output
- **Stage:** Global / Stages 02-05
- **Category:** State / Synchronization
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** In Stage 05 (Generation), the right rail JSON viewer still displays the Discovery Agent's `understand_and_question` output from Stage 01 instead of the active stage.
- **Evidence:** `evidence/screenshots/generation/generation-02-progress.png`.
