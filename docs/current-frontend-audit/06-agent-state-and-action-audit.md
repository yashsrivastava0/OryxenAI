# 06 — Agent State & Action Audit

This document examines how agent states and user actions are represented, positioned, and synchronized across the portfolio generation pipeline.

---

## 1. Agent State Synchronization Matrix

| Pipeline Stage | Backend Job State | Frontend Visible State | Stepper Badge | Synchronization Accuracy | Notes / Defects |
|---|---|---|---|---|---|
| **Discovery (Intake)** | None | `Ready to structure your brief` | `01 Discover` (Active) | **Accurate** | Clear initial state. Counter updates smoothly as text is entered. |
| **Discovery (Questions)** | `succeeded` (job: `discovery.understand_and_question`) | `QUESTION 01 OF 03` | Washed out / Hidden | **Partially Degraded** | Stepper is visually hidden behind the active question card. |
| **Discovery (Review)** | `succeeded` (job: `discovery.build_or_revise_brief`) | `Ready for review` | `01 Discover` (Active) | **Accurate** | Brief correctly loaded upon job completion. |
| **Discovery (Approved)** | Session transitioned | Brief approved (`✓ Discover`) | `01 Discover` -> `02 Content` | **Accurate** | Transition is crisp; checkmark appears on completed stage. |
| **Content Architect** | `succeeded` (job: `content_architect.build`) | `Under review` | `02 Content` (Active) | **Accurate** | Correct status pill, but stat pill visually collides with H1 title (FE-002). |
| **Visual Design Director** | `succeeded` (job: `visual_design_director.build`) | `Under review` | `03 Design` (Active) | **Accurate** | Correct status pill; exact same visual collision bug as Content Architect (FE-003). |
| **Build Preparation** | `succeeded` (job: `build_preparation.prepare`) | `BUILD PREPARATION / HANDOFF READY` | `04 Prepare` (Active) | **Accurate** | Correct state communication. |
| **Generate & Preview (Initial)** | Ready for run | `Stage Locked` | `05 Generate & Preview` (Active) | **INCORRECT** | Erroneously displays "Stage Locked" upon arrival despite having just approved Stage 04 (FE-010). |
| **Generate & Preview (Active)** | `failed` (job: `code_generator.v5.plan`) | `Generating your portfolio` | `05 Generate & Preview` (Active) | **CRITICAL FAILURE** | Job failed in worker, but frontend remains stuck permanently on "Generating your portfolio" (FE-001). |

---

## 2. Action Placement & Ergonomics Audit

### A. Primary Call-to-Action (CTA) Accessibility
Across the pipeline, three primary CTAs control progression:
1. `Approve & continue to Content Architect` (Stage 01)
2. `Approve & continue to Visual Design Director` (Stage 02)
3. `Approve & continue to Build Preparation` (Stage 03)
4. `Continue to Generate & Preview →` (Stage 04)

#### Key Findings:
- **Severe Inconsistency in CTA Placement:**
  - In Stages 01, 02, and 03, the primary approval action is placed at the **absolute bottom of the page** (at y=2,850px, y=7,994px, and y=3,244px respectively). The user cannot see how to advance without scrolling past all content.
  - In Stage 04, the primary action is suddenly placed **right at the top** (at y=741px). While much more usable, this radical shift in action placement creates spatial disorientation.
- **Button Sizing and Text Wrapping (FE-013, FE-014):**
  - The CTA buttons in Stages 01, 02, and 03 have a fixed or constrained width with `overflow: hidden`. As a result:
    - Text wraps across **4 lines**:
      ```text
      Approve &
      continue to
      Content
      Architect
      ```
    - The trailing arrow icon (`→`) is clipped against the right border of the button.
  - Buttons should have `white-space: nowrap` or flexible inline padding to accommodate editorial stage names comfortably.

---

## 3. Secondary Actions & Escape Hatches

### A. "Chat & Revise" Action
- In Stages 01, 02, and 03, a secondary white button labeled `Chat & revise` sits directly beneath the primary CTA.
- **Observation:** Clicking `Chat & revise` scrolls or transitions into a revision composer. However, placing it below the primary CTA gives it lower priority than "Approve", even though reviewing and revising is the explicit purpose of an editorial stage.

### B. "Reset Pipeline" Dangerous Action (Top Navigation Bar)
- Throughout Stages 01 to 05, an `ADMIN Reset Pipeline` button with a red badge is persistently displayed in the top right header navigation bar next to the user menu.
- **Risk Assessment:**
  - This is a destructive administrative action that wipes the session's pipeline state.
  - Exposing this prominently in the top header during normal user portfolio generation creates significant risk of accidental data destruction.
  - Administrative reset should be restricted to `/admin` or nested behind a multi-step confirmation dialog.

---

## 4. State Recovery & Polling Behavior

1. **Client Polling Cadence:**
   - The frontend polls `GET /api/v1/sessions/:id` every ~2,000ms during active jobs (`content_architect.build`, `visual_design_director.build`, `code_generator.v5.plan`).
   - There is no exponential backoff or jitter implemented in the client polling loop.
2. **Failure Detection Gap:**
   - When a durable job fails with `status='failed'`, the worker writes the error payload to `background_jobs`.
   - However, the `portfolio_sessions` row is not updated with a failure status or error message.
   - Consequently, the polling loop receives `200 OK` indefinitely with `current_stage='generate'`, leaving the client unable to break out of the working state.
