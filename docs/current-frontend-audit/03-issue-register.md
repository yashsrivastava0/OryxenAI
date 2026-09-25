# 03 — Issue Register

This register catalogs every distinct frontend defect and friction point discovered during the forensic audit of OryxenAI.

---

### Issue Summary Table

| ID | Stage | Category | Severity | Confidence | Reproducibility | Short Summary |
|---|---|---|---|---|---|---|
| **FE-002** | Content | Visual / Layout | **High** | CONFIRMED | Always | Stat badge directly overlaps and collides with H1 title "Architecture" |
| **FE-004** | Content | Scroll / Density | **High** | CONFIRMED | Always | 8,026px page height; primary decision CTA is 11.5 viewport heights below fold |
| **FE-005** | Discovery | Scroll / Density | **High** | CONFIRMED | Always | 3,032px page height; primary "Approve" CTA is 4.1 viewport heights below fold |
| **FE-007** | Content | Layout / Structure | **High** | CONFIRMED | Always | Content column squished to ~160px; headings wrap 1 word per line over 12 lines while 400px sits empty |
| **FE-009** | Global | IA / Hierarchy | **High** | CONFIRMED | Always | Developer "HANDOFF UTILITY" with raw JSON editor occupies right column during normal user workflow |
| **FE-011** | Content | Data / Copy | **Medium** | CONFIRMED | Always | Section headings and body paragraphs are 100% duplicate identical strings rendered twice |
| **FE-012** | Discovery | Visual / Typography | **Medium** | CONFIRMED | Always | H1 title font size causes 6-line awkward wrapping across 60% of viewport height |
| **FE-013** | Discovery | Action / Layout | **Medium** | CONFIRMED | Always | Primary CTA button text wraps onto 4 lines inside a narrow pill with clipped arrow icon |
| **FE-017** | Global | Layout / Scroll | **Low** | CONFIRMED | Always | Vertical scrollbar present on initial empty intake screen (808px height on 695px viewport) |
| **FE-018** | Discovery | Visual / Copy | **Low** | CONFIRMED | Always | Stepper navigation is washed out and obscured behind question card during Discovery Q&A |
| **FE-020** | Content Architect | State / Synchronization | **Medium** | CONFIRMED | Always | Right rail Handoff Utility remains stuck on Discovery JSON output during Content Architect review |

---

## Detailed Issue Specifications

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

### FE-004: Excessive Vertical Sprawl — Primary CTA 11.5 Viewport Heights Down (Content Stage)
- **Stage:** Content Architect (Stage 02)
- **Category:** Scroll / Density / Action Placement
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Expected Behavior:** High-level strategic review and primary handoff actions should be visible in the initial 1-2 viewports, or accompanied by a sticky action bar, rather than requiring 8,000 pixels of scrolling.
- **User Impact:** Users frequently miss or lose track of the review decision after scrolling through the long artifact.
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

### FE-009: Developer "HANDOFF UTILITY" Dominates Primary Right Column
- **Stage:** Global (Discovery and Content Architect)
- **Category:** Information Architecture / Visual Hierarchy
- **Severity:** **High**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Viewport:** 1536 × 695 (Desktop)
- **Actual Behavior:** A 360px-wide right column titled "HANDOFF UTILITY - Agent output" with "Copy JSON" links and a black monospace raw JSON editor box is persistently displayed during everyday user tasks (answering questions, reviewing narrative, selecting options).
- **Expected Behavior:** Developer tools and raw JSON dumps should be housed in a collapsed drawer, modal, or dedicated `/dev` panel rather than occupying primary desktop real estate.
- **User Impact:** Clutters screen, distracts non-technical users, squishes the actual content into a narrow central strip.
- **Evidence:** Discovery and Content Architect screenshots.

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

### FE-013: Discovery Approval CTA Text Wraps Across 4 Lines with Clipped Arrow
- **Category:** Action / Layout
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** CTA button text wraps onto 4 lines ("Approve &\ncontinue to\nContent\nArchitect") inside a narrow fixed-width pill; the arrow icon is clipped on the right border.
- **Expected Behavior:** Button width should be `auto` or `min-content` with `white-space: nowrap` or balanced 2-line wrap.
- **Evidence:** `evidence/screenshots/discovery/discovery-05-approval-bottom.png`.

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

### FE-020: Handoff Utility Shows Stale Discovery Output During Content Architect Review
- **Stage:** Content Architect
- **Category:** State / Synchronization
- **Severity:** **Medium**
- **Confidence:** **CONFIRMED**
- **Reproducibility:** Always
- **Actual Behavior:** During Content Architect review, the right rail JSON viewer still displays the Discovery Agent's `understand_and_question` output instead of the selected stage output.
- **Expected Behavior:** The inspector follows the selected active stage and shows its corresponding safe output.
- **Source Correlation:** `frontend/src/components/WorkspaceCanvas.tsx`.
