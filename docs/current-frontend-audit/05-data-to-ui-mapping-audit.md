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

## 3. Visual Design Director Stage Mapping

```text
Backend Schema (VisualDesignOutput)
  ├── creative_thesis: "Treat the portfolio as a readable systems map..."
  ├── visual_language: { color_palette: [...], typography: [...], motion_system: [...] }
  ├── page_experiences: [
  │     {
  │       route_id: "home",
  │       scenes: [
  │         { scene_id: "hero", layout_intent: "...", narrative_goal: "..." },
  │         { scene_id: "systems-grid", layout_intent: "...", narrative_goal: "..." }
  │       ]
  │     }
  │   ]
  └── adapted_resources: [...]
```

### Observed Mappings & Flaws:
1. **Visual Direction Rendered as Prose Walls Instead of Visual Elements:**
   - The backend output defines a complete visual language (colors, fonts, layout intents).
   - However, the UI renders ZERO color swatches, ZERO font sample cards, and ZERO visual storyboard previews.
   - The entire visual direction is presented as prose paragraphs, bullet points, and collapsed code disclosures.
2. **Scene Details Buried Behind Accordions (FE-015):**
   - Rather than rendering a visual storyboard where the user can scan the 4 scenes of the page, the scenes are hidden behind `<details><summary>Page direction detail · 1 routes</summary></details>`.
   - If not expanded, the visual design review communicates virtually nothing about what the site will actually look like.
3. **Stat Badge Title Collision (FE-003):**
   - Identical to Content Architect: the badge `STYLED ROUTES: 1 | SCENES: 4 | STATUS: Under Review` is placed directly on top of the word `Architecture`.

---

## 4. Build Preparation Stage Mapping

```text
Backend Schema (BuildPreparationOutput)
  ├── readiness_summary: { routes_bound: 1, resources_found: 8, missing: 0 }
  ├── resource_index: {
  │     images: [
  │       { id: "img-1", query: "home office, person, work, web design...", url: "..." },
  │       { id: "img-2", query: "artist, studio, art, sculpture...", url: "..." }
  │     ],
  │     components: [...]
  │   }
  └── briefs: { narrative_brief: "...", visual_brief: "..." }
```

### Observed Mappings & Flaws:
1. **Broken Image Thumbnails with 20+ Comma-Separated Keyword Alt Text (FE-008):**
   - The backend researched photography candidates based on image query strings.
   - The frontend renders `<img>` tags pointing to external candidate URLs without error handlers or proxy fallbacks.
   - When the URLs fail (or are blocked by CSP/network), the browser falls back to the `alt` attribute.
   - The `alt` attribute was populated with the raw backend search query (`home office, person, work, web design, business, workplace, monitor, computer, keyboard, screen, laptop, office work, independent, freelancer, success, graphic designer, designer, digital, nomad`).
   - This results in huge 300px grey boxes filled with 20+ comma-separated search terms.
2. **Redundant Duplicate Metrics (FE-016):**
   - Left Rail: `Routes bound: 1`, `Resources found: 8 found · 0 missing`, `Component suggestions: 1`.
   - Center Banner: `ROUTES: 1`, `RESOURCE NEEDS: 11`, `DISCOVERED ASSETS: 8`, `COMPONENT INTENTS: 1`.
   - The same 4 numbers are displayed in two separate cards 200px apart with slightly different labels (`Resources found` vs `DISCOVERED ASSETS`).

---

## 5. Code Generation Stage Mapping

```text
Backend Schema & State
  ├── job_kind: "code_generator.v5.plan"
  ├── status: "failed"
  ├── error_payload: { code: "HANDLER_ERROR", message: "The background job handler failed." }
```

### Observed Mappings & Flaws:
1. **Failure State Swallowed Entirely (FE-001):**
   - Backend database explicitly records `status='failed'`, `finished_at='2026-09-12 11:09:41'`.
   - Frontend API polling endpoint `/api/v1/sessions/...` only exposes top-level session state (`current_stage: "generate"`, `session_status: "active"`).
   - The frontend adapter does not correlate the background job failure with the UI view model.
   - UI stays permanently frozen on `Generating your portfolio` with a static 5-step checklist.
2. **Typography & Polish (FE-019):**
   - Ordered list item rendered as: `1. ✓Queuing the portfolio generation...` (missing whitespace between checkmark and text).
   - Progress subtitle is literally an unstyled lowercase word: `<p>plan</p>`.
