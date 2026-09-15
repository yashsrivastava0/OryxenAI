# 04 — Layout, Scroll & Density Audit

## Overview & Core Findings
Scrolling is one of the most severe usability failure modes in the current OryxenAI application. Across multiple stages, review screens expand to **4x to 11.5x the viewport height**, burying critical decision actions (Approve, Revise, Continue) thousands of pixels below the fold.

Furthermore, this vertical expansion is not driven by rich multimedia or dense analytics — it is driven by:
1. **Severely squished content columns (150–200px wide)** that force sentences to wrap word-by-word into dozens of vertical lines while hundreds of pixels of horizontal canvas sit completely empty.
2. **Gigantic font sizes** on H1 titles that wrap across 4 to 6 lines, consuming up to 60% of the initial viewport height.
3. **Absence of sticky action bars or floating decision docks**, forcing users to blindly scroll to the very bottom of long text walls to approve a stage.
4. **Persistent vertical scrollbar on empty intake screens**, caused by unbudgeted margins and min-height rules.

---

## Precise Scroll & Layout Metrics

| Screen / State | Viewport Width | Viewport Height | Total Page Height | Height Ratio (`scrollHeight / vh`) | Primary Action Y Position | Distance to Action (Viewport Heights) | Status / Problem |
|---|---:|---:|---:|---:|---:|---:|---|
| **Discovery: Empty Intake** | 1536 px | 695 px | 808 px | **1.16x** | 680 px | 0.98 vh | Unnecessary scrollbar (+113px excess) |
| **Discovery: Question 01** | 1536 px | 695 px | 808 px | **1.16x** | 680 px | 0.98 vh | Minor vertical scrollbar |
| **Discovery: Brief Review** | 1536 px | 695 px | 3,032 px | **4.36x** | 2,850 px | **4.10 vh** | Approve CTA lost 2,850px below top |
| **Content Architect: Review** | 1536 px | 695 px | 8,026 px | **11.55x** | 7,994 px | **11.50 vh** | **Extreme sprawl.** 8,000px scroll for 1 route! |
| **Visual Design: Review** | 1536 px | 695 px | 3,539 px | **5.09x** | 3,244 px | **4.67 vh** | CTA lost 3,244px below top |
| **Build Preparation: Review** | 1536 px | 695 px | 2,180 px | **3.14x** | 741 px | **1.06 vh** | CTA placed near top (good contrast) |
| **Generation: In Progress** | 1536 px | 695 px | 950 px | **1.37x** | N/A | N/A | Stuck in infinite progress state |

---

## Detailed Stage-by-Stage Scroll Analysis

### 1. Stage 01: Discovery Brief Review (3,032 px / 4.36 Viewports)
- **The Culprit:**
  - H1 title `Portfolio Discovery Brief — Dr. Aditya Vikram Joshi` wraps into 6 lines because font size is set to a fixed massive scale (~2.5rem serif with narrow column constraint).
  - Every extracted section (Summary, Structured Profile, Experience, Skills) is stacked in a single vertical column.
  - Skills chips and experience items are rendered linearly without responsive multi-column wrapping.
- **Action Loss:** The primary button "Approve & continue to Content Architect" is at pixel 2,850. A user on a standard laptop (1366x768 / 1440x900) must perform 5 to 7 mouse wheel sweeps through the entire brief before discovering how to approve it.

---

### 2. Stage 02: Content Architect Review (8,026 px / 11.55 Viewports)
- **The Culprit:**
  - **Severe column squishing:** The main text column is constrained to ~160px width. Headings like `Translate the broad profile into a clear narrative about the connected systems practice` wrap into **12 vertical lines** of 1 to 2 words per line.
  - To the right of this 160px text strip, approximately **400px of width sits completely vacant**.
  - Section titles and section bodies duplicate the exact same text string, doubling the vertical footprint.
  - No route switcher or tabbed pagination exists in the rendered view; all 5 content sections of the page are dumped sequentially in one gigantic vertical scroll container.
- **Action Loss:** The primary button is 7,994px down — 11.5 full screen heights away. This is an unacceptable usability barrier.

---

### 3. Stage 03: Visual Design Director Review (3,539 px / 5.09 Viewports)
- **The Culprit:**
  - Similar column squishing as Content Architect.
  - Although the actual scene storyboards and layout candidates are collapsed behind disclosure carets (`▶ Page direction detail`, `▶ Adapted layout candidates`), the page still stretches to 3,539px due to generous vertical paddings and margins on empty layout containers.
  - If a user actually expands the scene disclosures, the page height explodes beyond 10,000px!

---

### 4. Stage 04: Build Preparation (2,180 px / 3.14 Viewports)
- **Positive Counter-Example in Action Placement:**
  - Unlike Stages 01-03, Build Preparation positions the primary action `Continue to Generate & Preview →` near the top of the canvas at `y = 741 px` (1.06 viewports). The user sees the decision immediately upon page load without scrolling!
- **Density Flaw:**
  - Below the action, two large grey broken image containers take up ~600px of vertical space displaying broken image icons and raw comma-separated alt keywords.

---

## Structural Density & Wasted Screen Real Estate

Across all stages at 1536x695 (and standard 1440x900 desktop):
- **Left Rail:** 240px to 260px fixed width (often displaying 3-4 small text metrics).
- **Right Rail (Handoff Utility):** 360px fixed width (displaying developer JSON).
- **Remaining Center Canvas:** ~900px total width.
  - However, the inner content container inside this canvas is artificially capped or padded down to only 160px–320px in multiple sub-components!
  - As a result, **more than 40% of the horizontal center canvas is empty grid lines**, while the readable content is suffocated in a vertical sliver.
