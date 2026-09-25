# 05 — Data-to-UI Mapping Audit

This audit evaluates how backend API payloads and schema data are transformed through frontend adapters and rendered into UI components.

---

## 1. Discovery Stage Mapping

```text
Backend Schema (DiscoveryBrief)
  ├── candidate_name: "Dr. Aditya Vikram Joshi"
  ├── professional_title: "Principal Agentic AI Systems Architect..."
  ├── target_roles: ["Principal Agentic Systems Architect", ...]
  ├── extracted_facts: { experiences: [...], skills: [...] }
  └── brief_markdown: "..."
```

### Observed Mappings & Flaws:
1. **Title Rendering:**
   - Backend `candidate_name` and brief title are combined into `Portfolio Discovery Brief — Dr. Aditya Vikram Joshi`.
   - Instead of a structured profile header, it is fed as raw text into a single unconstrained serif H1 that wraps into 6 disjointed lines.
2. **Extracted Facts Summary:**
   - Left rail displays: `Experience entries: 3`, `Skills: 112`.
   - The user provided 11+ years of experience across 4 companies and 4 enterprise projects in `resume.md`. The backend captured 3 experience entries and 112 individual skills.
   - However, the UI does not allow the user to easily inspect or verify which 3 experiences were selected versus which were omitted; it only displays the aggregate integer `3`.
3. **Raw Code Leakage:**
   - The right rail renders the full `understand_and_question` and `build_or_revise_brief` raw JSON payloads directly into an interactive `<textarea class="json-code-box" readonly>`. Technical JSON keys (`mode`, `operation`, `questions`, `brief_markdown`) are exposed directly to the user.

---

## 2. Content Architect Stage Mapping

```text
Backend Schema (ContentArchitectureOutput)
  ├── strategic_positioning: { primary_narrative: "...", audience_targets: [...] }
  ├── routes: [
  │     {
  │       route_id: "home",
  │       title: "Home",
  │       sections: [
  │         {
  │           section_id: "systems-practice",
  │           role: "Translate the broad profile into a clear narrative...",
  │           narrative_intent: "Translate the broad profile into a clear narrative...",
  │           copy: "..."
  │         }
  │       ]
  │     }
  │   ]
  └── warnings: [...]
```

### Observed Mappings & Flaws:
1. **Duplicate Text in Section Cards (FE-011):**
   - The backend returned identical strings for `role` and `narrative_intent`.
   - The UI adapter mapped `role` to the section H3 heading and `narrative_intent` to the paragraph immediately below it.
   - Result in UI:
     - H3: `"Translate the broad profile into a clear narrative about the connected systems practice."`
     - P: `"Translate the broad profile into a clear narrative about the connected systems practice."`
     - The exact same sentence is rendered twice in immediate succession.
2. **Collision of Route Counter and Page Title (FE-02):**
   - Backend `routes.length` (= 1) and status (`Under Review`) are rendered into a metadata pill component `.artifact-status-badge`.
   - In CSS, this badge has absolute or float positioning that places it at coordinates overlapping the letters of the H1 title `Content Strategy & Route Architecture`.
3. **Route Navigation Missing:**
   - The backend schema supports multi-route portfolios (`routes: RoutePlan[]`).
   - In this run, 1 route (`home`) was planned. However, there is no route selector, tab, or breadcrumb that indicates which route the user is currently previewing; the section list simply starts dumping sections with the prefix `HOME : SYSTEMS-PRACTICE`.

---
