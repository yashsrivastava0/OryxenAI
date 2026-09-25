# 01 — Screen & State Inventory

This document provides the canonical map of screens, stages, and states observed during the live forensic audit of OryxenAI (`http://localhost:8000/app`), based on actual browser execution and screenshots.

---

## 1. Authentication Shell (`/sign-in`, `/auth/callback`)
- **Route:** `http://localhost:8000/` / `http://localhost:8000/app` -> redirected to Supabase Google OAuth
- **Components Observed:**
  - Full-screen brand intro ("Make the work legible before making it public.")
  - Editorial tagline and active-stage navigation
  - Google OAuth sign-in boundary
  - Account state handling (pending admission, workspace paused, username onboarding)
- **Primary Actions:** "Continue with Google"
- **Evidence:** `evidence/screenshots/auth/auth-01-google-signin.png`
- **Anomalies / Observations:**
  - Automated browser instances without existing cookies redirect straight to Google sign-in.
  - Clear multi-step status explanation during restore ("1. Restoring your session -> 2. Completing Google sign-in -> 3. Verifying OryxenAI access -> 4. Preparing your workspace").

---

## 2. Stage 01: Discovery — Intake & Questioning
- **Route:** `http://localhost:8000/app?stage=discovery`
- **State A: Empty Intake**
  - **Status:** `Ready to structure your brief` | `0 words · 0 characters`
  - **Components:**
    - Top header: App branding ("OryxenAI | portfolio editorial room"), User menu (`yashxbbdtest ▼`)
    - Stepper: two active stages (01 Discovery, 02 Content Architect)
    - Hero title: "Bring your work into focus."
    - Intake card (`#intake-notes` textarea) with 4 prompt chips (`+ The work I want to be known for`, `+ Two projects worth examining`, `+ The audience this portfolio should reach`, `+ Constraints, gaps, or claims to avoid`)
    - Footer bar: Security badge ("🔒 Private workspace · Nothing moves forward without your approval") + CTA `Start Discovery →`
  - **Evidence:** `evidence/screenshots/discovery/discovery-01-empty.png`, `discovery-02-resume-entered.png`
  - **Scroll Metrics:** `window.innerHeight`: 695px, `scrollHeight`: 808px (Ratio: 1.16x). Vertical scrollbar present even when empty!
- **State B: Interactive Questioning**
  - **Status:** `Private draft` | `QUESTION 01 OF 03`
  - **Components:**
    - Left/Center: Question prompt card, lede context, answer textarea (`#answer-notes`), action buttons (`Save and continue`, `Skip question`)
    - Right Rail: "HANDOFF UTILITY - Agent output" with stage list (`Discovery Agent NOT READY`, `Content Architect LOCKED`, etc.) and black monospace raw JSON box.
    - Top Bar: Injected red `ADMIN Reset Pipeline` button.
  - **Evidence:** `evidence/screenshots/discovery/discovery-03-question-active.png`
  - **Anomalies:**
    - The top stepper is washed out / hidden behind the question card.
    - Developer "HANDOFF UTILITY" with raw JSON box is prominently rendered in the right column while a normal user is answering basic discovery questions.

---

## 3. Stage 01: Discovery — Brief Review & Approval
- **Route:** `http://localhost:8000/app?stage=discovery&view=artifact`
- **Status:** `Ready for review` | `BRIEF`
- **Components:**
  - Left Rail: `Stage 01 / Discovery`, `Journey · Discovery`, extracted candidate facts (`Dr. Aditya Vikram Joshi`, `Experience entries: 3`, `Skills: 112`)
  - Center Canvas:
    - Giant wrapping serif H1 title: `Portfolio Discovery Brief — Dr. Aditya Vikram Joshi` (wraps into 6 lines!)
    - Brief sections: Summary, Structured Profile, Extracted Experience, Skills
    - Collapsed disclosures: `Complete portfolio brief (22k characters)`, `▶ Final JSON output`
    - Action buttons: `Approve & continue to Content Architect` (blue button), `Chat & revise` (white button)
  - Right Rail: `HANDOFF UTILITY` with `Discovery Agent AVAILABLE`, `Copy JSON` link, and full JSON response editor.
- **Evidence:** `evidence/screenshots/discovery/discovery-04-brief-top.png`, `discovery-05-approval-bottom.png`
- **Scroll Metrics:** `window.innerHeight`: 695px, `scrollHeight`: 3,032px (Ratio: 4.36x). Primary CTA is 2,850px below top (4.1 viewport heights).
- **Anomalies:**
  - Gigantic font size on title causes 6-line wrapping.
  - CTA button text wraps onto 4 lines inside a narrow pill ("Approve &\ncontinue to\nContent\nArchitect").
  - Primary decision action is lost at the very bottom of a 3,000px page.

---

## 4. Stage 02: Content Architect — Strategy & Route Architecture
- **Route:** `http://localhost:8000/app?stage=content&view=artifact`
- **Status:** `Under review` | `CONTENT PLAN` | `Ready for review`
- **Components:**
  - Left Rail: `Stage 02 / Content Architect`, `Planned routes: 1`, `Content sections: 5`, `Status: Under review`
  - Center Canvas:
    - H1 Title: `Content Strategy & Route Architecture`
    - Stat pill: `PLANNED ROUTES: 1 | STATUS: Under Review` (Overlaps directly onto the title word "Architecture"!)
    - Notes & Exclusions callout box (creamy background)
    - Section blocks (`HOME : SYSTEMS-PRACTICE`, `HOME : TECHNICAL-CAPABILITIES`, etc.)
    - Disclosure: `▶ Final JSON output`
  - Right Rail: `HANDOFF UTILITY` showing `Content Architect AVAILABLE` and JSON response.
- **Evidence:** `evidence/screenshots/content/content-01-result-top.png`, `content-02-result-mid.png`, `content-03-actions.png`
- **Scroll Metrics:** `window.innerHeight`: 695px, `scrollHeight`: 8,026px (Ratio: 11.55x). Primary CTA distance: 7,994px (11.5 viewport heights).
- **Anomalies:**
  - **Severe visual collision:** Stat box overlaps directly on top of the word "Architecture".
  - **Severe vertical sprawl:** 8,026px page height.
  - **Severe column squishing:** Heading words wrap 1-2 words per line in a narrow 160px column while 400px of whitespace sits empty to the right.
  - **Duplicate text:** Section title and section body are identical strings rendered twice.

---
