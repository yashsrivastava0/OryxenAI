# 10 — Journey & Information Architecture Findings

This document synthesizes the empirical evidence collected during the forensic audit into major systemic problem families that degrade the OryxenAI product experience.

---

## 1. Problem Family A: Result Representation Mismatch
An agent-based creation tool is only as good as its mental models. When an agent finishes its work, the UI must translate complex backend data into a representation natural to that domain.
Currently, this translation breaks down across multiple stages:

1. **Visual Design Director is Not Visual:**
   - Visual Design Director is meant to show the user the aesthetic thesis, color direction, typography, and page scene storyboard.
   - Instead, the UI renders **monochrome prose bullet points**, technical identifiers, and collapsed code disclosures. There are no color palettes, no font specimens, and no visual scene mockups.
2. **Content Architecture is Not Structured:**
   - Content Architect is meant to show the site sitemap and narrative flow across pages.
   - Instead of an interactive sitemap or route-scoped navigation, all sections of the site are dumped sequentially into an 8,000-pixel-tall document.
3. **Build Preparation Looks Like a Raw Package Dump:**
   - Rather than communicating generation readiness cleanly, Build Preparation exposes broken photography cards with raw keyword strings and duplicated metric tables.

---

## 2. Problem Family B: Excessive Vertical Expansion & Action Loss
The primary editorial invariant of OryxenAI is: *"Nothing moves forward without your approval."*
However, the user cannot easily approve what they cannot reach:

1. **Extreme Scroll Distances:**
   - Content Architect requires **7,994 pixels (11.5 viewport heights)** of continuous scrolling to find the "Approve" button.
   - Discovery requires **2,850 pixels (4.1 viewport heights)** of scrolling.
   - Visual Design requires **3,244 pixels (4.67 viewport heights)** of scrolling.
2. **Missing Sticky Controls:**
   - There is no persistent bottom action bar, floating dock, or header action area during review states.
   - If a user reads a section and decides to approve, they must scroll through thousands of pixels of remaining text just to trigger the transition.
3. **Inconsistent Positioning:**
   - In Stage 04, the primary button is suddenly located at the top (y=741px), breaking the mental model established across Stages 01–03.

---

## 3. Problem Family C: Column Squishing & Layout Collisions
The grid system in `shell.css` suffers from rigid layout constraints:

1. **The 160px Column Paradox:**
   - In Content Architect, section titles and text are squished into a narrow 160px column while 400px of adjacent canvas is completely blank.
   - This creates 12-line single-word headings that stretch the page vertically.
2. **Direct Visual Collisions (FE-002, FE-003):**
   - In both Content Architect and Visual Design Director, the status/metric badge (`PLANNED ROUTES: 1 | STATUS: Under Review`) has CSS coordinates that cause it to collide directly over the word "Architecture" in the H1 heading.
   - This demonstrates that layout styling was never visually tested against real multi-word titles.

---

## 4. Problem Family D: Developer Tooling Dominates User Workspace
1. **The "HANDOFF UTILITY" Right Rail (FE-009):**
   - A 360px-wide sidebar titled `HANDOFF UTILITY - Agent output` with raw JSON editor boxes and "Copy JSON" links is permanently visible on every screen.
   - For a portfolio creator (designer, engineer, executive), exposing raw backend JSON keys (`mode`, `operation`, `request_id`, `input_fingerprint`) during creative questioning and editorial review is confusing and intimidating.
   - It steals 25% of the total screen width from the creative workspace.
2. **Destructive Reset Pipeline in Header:**
   - An `ADMIN Reset Pipeline` button with a red badge is placed prominently in the global top header, risking accidental pipeline destruction during normal usage.

---

## 5. Problem Family E: Silent Error Concealment & State Freezes
The most severe technical finding of this audit is how the frontend handles failures (FE-001):

1. **Swallowed Job Failures:**
   - When the backend background worker experiences a job failure (as occurred in `code_generator.v5.plan`), the frontend polling loop continues unabated.
   - The UI provides zero feedback that an error occurred, remaining stuck on "Generating your portfolio" with a static checklist forever.
2. **Lack of Self-Healing / Retry Actions:**
   - Because failure is not acknowledged by the UI, the user is given no "Retry", "Inspect Diagnostics", or "Return to Build Prep" action.
   - The user's only recourse is closing the browser tab.

---

## Summary of Journey Answers
Evaluating the global journey against the standard questions:

| Question | User Clarity Level | Observed Reality |
|---|---|---|
| **Where am I?** | Moderate | Top stepper shows stage number, but stepper gets washed out during Q&A. |
| **What has already happened?** | Moderate | Prior stages show checkmarks in stepper (`✓ Discover`), but reviewing past stage results requires switching tabs. |
| **What is happening now?** | **Poor during jobs** | Loading screens are often stark empty voids or infinite progress checklists that never update upon failure. |
| **What did this agent produce?** | **Poor** | Results are rendered as raw text walls or collapsed code disclosures rather than visual portfolios or interactive sitemaps. |
| **What requires my judgment?** | **Poor** | Primary approval actions are buried at the bottom of 8,000px pages; review content is mixed with machine metadata. |
| **What happens next?** | Moderate | CTA buttons indicate destination (`Approve & continue to Visual Design Director`), but button text is squished into 4 lines. |
