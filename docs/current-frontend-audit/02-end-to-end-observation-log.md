# 02 — End-to-End Observation Log

Chronological, unvarnished forensic execution log of the real OryxenAI session (`5822e80f-83d8-4606-b25d-05e09e92d8b8`) conducted on 2026-09-12.

---

### 16:05:05 — Session Initialization & Git Check
- Confirmed running native services:
  - FastAPI server (`127.0.0.1:8000`)
  - Worker daemon (`oryxenai.jobs.worker`)
  - PostgreSQL (`127.0.0.1:5432`)
- Preserved `.env` and all existing uncommitted files intact.

---

### 16:08:12 — Authentication Verification
- Browser subagent navigated to `http://localhost:8000/app`.
- Session restore triggered Supabase OAuth redirect to Google Accounts sign-in (`https://accounts.google.com/v3/signin/...`).
- Captured evidence: `google_signin_page_1789209492223.png` (`evidence/screenshots/auth/auth-01-google-signin.png`).
- Observed strict boundary: Stopped and requested user takeover to authenticate without asking for credentials in chat.

---

### 16:11:35 — User Logged In & Workspace Restored
- User completed Google sign-in as `yashxbbdtest` (`yashxbbd@gmail.com`).
- Browser refreshed/restored session at `http://localhost:8000/app`.
- Observed initial Discovery intake screen:
  - Stepper active on `01 Discover`.
  - H1: "Bring your work into focus."
  - Textarea placeholder: "Paste your resume, work history..."
  - Counter: `0 words · 0 characters`.
- Measured layout metrics before text input:
  - `window.innerWidth`: 1536px, `window.innerHeight`: 695px, `scrollHeight`: 808px (ratio: 1.16x).
  - Vertical scrollbar present even with an empty screen.
- Captured screenshot: `discovery-01-empty.png`.

---

### 16:16:41 — Resume Ingestion
- Ingested Dr. Aditya Vikram Joshi's resume (`Input-Output-Of-Engine/resume.md`).
- Word count updated dynamically: `Draft active` | `514 words · 4495 characters`.
- "Start Discovery →" button became enabled with primary blue background.
- Captured screenshot: `discovery-02-resume-entered.png`.

---

### 16:17:56 — Discovery Question Phase
- Clicked "Start Discovery →".
- Backend enqueued durable job `discovery.understand_and_question`.
- UI transitioned to `QUESTION 01 OF 03` ("Please paste the rest of your professional experience...").
- Observed layout anomalies:
  - Stepper at the top became obscured / washed out behind the question card.
  - "HANDOFF UTILITY" taking up the entire right column with developer raw JSON toggle and "Copy JSON" links.
  - Red `ADMIN Reset Pipeline` button visible in the top navigation bar for normal product user.
- Captured screenshot: `discovery-03-question-active.png`.
- Handled question sequence:
  - Question 1: Clicked "Skip question".
  - Question 2: Selected option "Principal or Staff AI Systems Architecture".
  - Question 3: Selected option "Technical editorial: architecture-led, precise, and research-informed".

---

### 16:21:15 — Discovery Brief Generated
- Background job `discovery.build_or_revise_brief` finished successfully.
- UI transitioned to brief review (`view=artifact`).
- Observed visual flaws:
  - H1 title "Portfolio Discovery Brief — Dr. Aditya Vikram Joshi" wraps into 6 vertical lines, taking over 60% of vertical screen space.
  - Right rail displays full JSON response editor in raw monospace code box.
  - Scroll height measured at 3,032px (4.36x viewport height).
- Captured screenshot: `discovery-04-brief-top.png`.
- Scrolled 2,850px down to reach the primary decision action:
  - Button text wraps into 4 lines: "Approve &\ncontinue to\nContent\nArchitect".
  - Arrow icon cut off on the right edge.
- Captured screenshot: `discovery-05-approval-bottom.png`.

---

### 16:24:29 — Discovery Approval & Content Architect Start
- Clicked "Approve & continue to Content Architect".
- Transition state showed:
  - Completely empty white canvas with faint unstyled text in top-left: "2. Structuring your portfolio content", "You can safely navigate away...".
  - Unstyled text link: "Stop Content Architect".
  - Right rail still showed old Discovery Agent response.
- Captured screenshot: `discovery-06-approved.png`.

---

### 16:26:02 — Content Architect Review
- Background job `content_architect.build` completed (`status='succeeded'`).
- UI loaded Content Strategy & Route Architecture.
- Observed extreme structural and visual defects:
  - **Collision:** The stat box `PLANNED ROUTES: 1 | STATUS: Under Review` directly overlaps the H1 word "Architecture".
  - **Sprawl:** `scrollHeight` measured at 8,026px (11.55x viewport height).
  - **Squishing:** Content text squished into a narrow ~160px column while 400px of width sits empty. Headings wrap 1 word per line over 12 lines.
  - **Duplicate copy:** Heading string is duplicated word-for-word in the subtitle directly underneath.
- Captured screenshots: `content-01-result-top.png`, `content-02-result-mid.png`.
  - Button text wrapped onto 4 lines.
- Captured screenshot: `content-03-actions.png`.

---
