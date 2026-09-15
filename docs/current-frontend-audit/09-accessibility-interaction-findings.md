# 09 — Accessibility & Interaction Findings

This document evaluates the accessibility (a11y), keyboard operability, ARIA semantics, and interactive states of the running application.

---

## 1. Keyboard Navigation & Focus Order

### A. Focus Rings & Visibility:
- **Observed Behavior:**
  - Interactive elements generally display a visible focus outline when navigated via `Tab`.
  - However, in the intake card's prompt chips (`+ The work I want to be known for`, etc.), focus styles are faint and lack sufficient contrast against the grid background.
  - The "HANDOFF UTILITY" right rail captures tab focus across 5 "Copy JSON" buttons before the user can tab down to the main content or primary stage action, creating a focus trap/detour for keyboard-only users.

### B. Logical Tab Order:
- **Top Bar:** Focus moves logically: Skip link -> Logo -> Stepper items -> Reset Pipeline -> User profile dropdown.
- **Review Stages (Stages 01–03):**
  - Focus order: Top Bar -> Left Rail items -> Main Title -> Accordions -> Right Rail "Copy JSON" buttons -> Primary Action Button.
  - Users navigating by keyboard must press `Tab` over 30 times through collapsed disclosures and right rail buttons to reach the "Approve & continue" action.

---

## 2. ARIA Semantics & Landmarks

### A. Landmarks:
- `<main>` landmark exists.
- `<header>` / `.app-topbar` is present.
- `<nav class="journey-nav">` properly identifies the stage progress bar.

### B. Issues Observed:
1. **Live Region Noise during Polling:**
   - `#product-root` is marked with `aria-live="polite"`.
   - While intended to announce stage updates, every 2-second polling fetch that updates minor DOM attributes triggers screen reader announcements, causing verbose chatter.
2. **Missing Accessible Names on Broken Images (FE-008):**
   - In Build Preparation, the broken photography images have raw comma-separated alt strings with 25+ keywords.
   - Screen reader users hear: *"image, home office comma person comma work comma web design comma business comma workplace comma monitor comma computer comma keyboard..."* for 45 seconds per image.
3. **Disclosure Elements:**
   - Standard HTML `<details>` and `<summary>` are used for accordions (`Final JSON output`, `Page direction detail`), which have native keyboard accessibility (Enter/Space to toggle).

---

## 3. Contrast, Readability & Typography

1. **Heading Line Lengths & Sizing:**
   - As documented in FE-007, heading lines squished to 160px width force rapid vertical eye tracking that severely hampers readability.
2. **Decorative Background Watermarks:**
   - Text strings like `PRIVATE BY DESIGN.`, `FROM EXPERIENCE TO OPPORTUNITY.`, `NOTHING ADVANCES WITHOUT APPROVAL` are rendered in low-contrast grey (`var(--graphite-dim)`) directly onto the grid.
   - While decorative, they occasionally collide with container borders or sit directly behind text cards, causing visual noise.
3. **Contrast Ratios:**
   - Body ink (`var(--ink)`) on cream paper (`var(--paper)` / `#f8f6f0`) exceeds WCAG AAA standards (> 7:1 contrast).
   - Primary blue button (`.btn-primary`) with white text achieves > 4.5:1 contrast.
