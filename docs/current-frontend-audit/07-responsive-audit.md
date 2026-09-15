# 07 — Responsive & Viewport Audit

This audit evaluates the layout, information density, and interactive usability across desktop, laptop, tablet, and mobile viewports.

---

## 1. Viewport Matrix Summary

| Viewport Category | Resolution Tested | Layout Mode | Primary Failure Modes Observed |
|---|---|---|---|
| **Primary Desktop** | 1536 × 695 / 1440 × 900 | 3-Column (Left Rail + Canvas + Right Rail) | Column squishing (160px text strip), wasted horizontal space, 6-line wrapped H1 headings. |
| **Short Laptop** | 1366 × 768 (Usable: ~650px) | 3-Column | Immediate vertical scrollbar on empty intake; primary CTAs pushed 4–11 viewports below fold. |
| **Tablet** | 768 × 1024 | Stacked Column (`workspace-canvas` 1fr) | Left and right rails collapse above/below canvas; content reading width expands, but vertical height exceeds 10,000px. |
| **Mobile** | 390 × 844 | Single Column Stack | Stepper switches to track bar; excessive vertical scroll; broken photography alt tags dominate screen. |

---

## 2. Short Laptop Viewport (1366 × 768 / Critical Vertical Test)
In `frontend/src/styles/shell.css`, special media queries exist for short viewports:
- `@media (max-height: 840px) and (min-width: 901px)`
- `@media (max-height: 740px) and (min-width: 901px)`

### Observed Behavior:
1. **Intake Screen (Empty State):**
   - The media query sets `.workbench-textarea { min-height: 6.5rem; }` and hides `.workbench-intro-desc`.
   - Despite this, `document.documentElement.scrollHeight` is **808px**, exceeding the 695px inner window by **113px**.
   - Result: An awkward vertical scrollbar is permanently rendered on what should be an elegant zero-scroll landing card.
2. **Review Screens:**
   - In 1366x768, standard browser UI chrome (tabs, URL bar, bookmarks) reduces vertical viewport to 620–680px.
   - At this height, the 8,026px Content Architect screen requires **12 to 13 mouse wheel rotations** to scroll from top to bottom.
   - The stat pills colliding with H1 titles ("Architecture") are completely unavoidable in this height range.

---

## 3. Tablet Viewport (768 × 1024)
At `max-width: 768px`, CSS rules trigger:
- `.workspace-canvas` switches to `grid-template-columns: 1fr`.
- `.workspace-canvas-rail` shifts from `position: sticky` to `position: static` with `flex-wrap: wrap`.

### Observed Behavior:
1. **Header & Stepper:**
   - The 5-stage stepper collapses into a compact strip.
   - Subtitles on the stepper ("UNDERSTAND YOUR STORY", "SHAPE NARRATIVE") hide cleanly.
2. **Information Reprioritization:**
   - While the rail collapses above the canvas, secondary metadata (`Experience entries: 3`, `Skills: 112`) still consumes 120px of vertical space before the main content begins.
   - The H1 titles in Discovery and Content Architect continue to wrap awkwardly.
3. **Right Rail Collapse:**
   - The "HANDOFF UTILITY" with the raw JSON textarea drops to the very bottom of the page beneath all content and buttons. While this frees up horizontal space, it adds another 400px of scrolling to an already massive page.

---

## 4. Mobile Viewport (390 × 844)
At `max-width: 640px`, mobile styles engage:
- Stepper is replaced by `.journey-mobile-summary` with a thin progress track (`.journey-mobile-track`).
- Brand subtitle and user account handle hide cleanly.
- Buttons stretch to full width (`width: 100%`).

### Observed Behavior:
1. **Broken Imagery on Mobile (Build Preparation):**
   - In Build Preparation, the broken photography cards expand to 100% width on mobile.
   - The 20+ comma-separated search keywords in the `alt` text wrap over 15 lines of text inside two gigantic grey rectangles, forcing users to scroll past two screenfuls of broken search terms before reaching generation details.
2. **Text Wrapping on Buttons:**
   - Because mobile buttons expand to `width: 100%`, the 4-line text wrapping bug seen on desktop (`Approve &\ncontinue to...`) resolves into 1 or 2 lines on mobile!
   - This proves that the desktop button text wrapping is an artificial layout defect caused by fixed desktop width constraints rather than text length.
3. **Stacking vs Reprioritization:**
   - Mobile simply stacks every card, callout, disclosure, and section vertically.
   - No content condensation (e.g. mobile summary cards or collapsible accordions for long text) is applied to the 8,000px Content Architect page.

---

## 5. Reduced Motion Accessibility
Inspected `@media (prefers-reduced-motion: reduce)` in `frontend/src/styles/shell.css`:
- `html { scroll-behavior: auto; }`
- Animations and transitions forced to `1ms !important`.
- Shimmer sweep animations (`.workbench-sweep`) disabled.
- **Verdict:** Reduced motion styles are properly implemented in the CSS foundation.
