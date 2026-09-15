# Agent-by-Agent Deep Dive and Flaw Analysis

> **Target Audience:** AI Coding Agents, LLM Prompt Engineers, and Product Architects.
> **Purpose:** Detailed, factual, and critical comparison between what each backend agent produces (domain output, data density, structures, emitted events) and what the current frontend actually displays. Highlights exact structural flaws, missing capabilities, trapped data, and aesthetic regressions—specifically documenting why Build Preparation, Visual Design Director, and Content Architect currently appear uncurated or broken in the UI.

---

## 1. Stage 1: Discovery Agent (`discovery`)

### 1.1 What the Backend Produces
The Discovery Agent executes two distinct operations:
1. **Operation A (`understand_and_question`):**
   - Evaluates raw user intake (resumes, LinkedIn exports, unstructured text).
   - Produces 1 to 4 targeted questions (`DiscoveryQuestion`) with options and skip rules.
   - Produces an internal `memory_update` with `persona`, `open_items`, `privacy_notes`, `source_summary`, and `confirmed_details`.
   - Produces an `assistant_message` providing conversational context for why these questions are asked.
2. **Operation B (`build_or_revise_brief`):**
   - Synthesizes user answers and intake into a comprehensive `BriefOutput`.
   - Produces `brief_title`, `brief_markdown`, and `user_summary`.
   - Produces a **`StructuredProfile`** containing categorized facts:
     - `links`: Array of `{ label, url }`.
     - `skills`: Exhaustive array of verified competencies (e.g. 30+ specific technical domains).
     - `experience`: Array of `{ organization, role, dates, highlights[] }`.
     - `education`: Array of `{ institution, credential, dates }`.
     - `projects`: Array of `{ name, summary, contribution, tech[], link }`.
     - `spoken_languages`: Array of languages.
     - `private_omitted`: Information deliberately redacted for privacy.
   - Produces `brief_hash` (SHA-256) upon user approval, locking the discovery snapshot for downstream agents.

### 1.2 What the Current Frontend Displays
- **Question Phase (`ConversationSurface.tsx`):**
  - Isolates strictly `questions[0]`.
  - Renders question text, help text, up to 3 preset options, a free-text input, and a Skip button.
  - Keeps an accordion list of previously answered turns (`history`).
- **Review Phase (`DiscoveryStage.tsx` -> `ArtifactSurface.tsx`):**
  - Renders `brief.title` and `brief.markdown` (or `user_summary`) inside `ArtifactSurface`.

### 1.3 Identified Flaws & Gaps
1. **Trapped Structured Profile:** The entire `StructuredProfile` (skills, projects, work history, education) extracted by the model is **never rendered as structured UI elements** in the chat or brief view. The user spent time providing an extensive resume, and the model parsed it into clean JSON facts, but the UI only displays a plain prose markdown summary. The facts remain invisible unless the user opens the raw JSON copy drawer.
2. **Hidden Context & Memory:** The model’s `assistant_message` explaining *why* questions are being asked, along with `open_items` and `privacy_notes`, are discarded by `DiscoveryStage.tsx` after initial submission.
3. **No Turn Sequence Indicator:** The user cannot see how many questions remain in the interview sequence (e.g. "Question 2 of 3").
4. **No Side-by-Side Fact Validation:** The user cannot verify that their skills and projects were extracted accurately before generating the brief.

---

## 2. Stage 2: Content Architect Agent (`content_architect`)

### 2.1 What the Backend Produces
The Content Architect consumes only the approved Discovery structured facts and produces an exhaustive, machine-addressable editorial package (`ContentArchitectOutput`):
1. **`site_story_strategy`:** Core narrative positioning, value proposition, central narrative thesis, primary audience, secondary audience, main visitor action, tone, and editorial principles.
2. **`decision_basis`:** Provenance records for major strategic decisions (`decision`, `value`, `basis`, `confidence`, `rationale`).
3. **`route_plan`:** Array of `RoutePlanEntry` defining site topology (`route_id`, `path`, `title`, `purpose`, `audience_takeaway`, `priority`, `content_density`, `section_sequence`, `publication_status`).
4. **`page_content_packs`:** Normalized sections for every route (`PageContentPack`). Each section (`ContentSection`) contains:
   - `section_id` (e.g. `"home:hero"`, `"home:selected-work"`).
   - `purpose` (e.g. `"Establish senior engineering leadership"`).
   - `content`: Rich dictionary containing headlines, subheadlines, narrative paragraphs, structured item arrays, quotes, metrics, or tags.
   - `priority`, `optional`, `mobile_condensation`.
5. **`claim_grounding`:** Complete evidence ledger (`claim_id`, `statement`, `source_reference`, `evidence_status`, `ownership`, `publication_status`).
6. **`omissions` & `unresolved_issues`:** Specific claims excluded due to confidentiality or lack of verification.
7. **`visual_director_handoff`:** Structural hints for typography, density, and layout.
8. **`content_hash`:** SHA-256 hash stamped upon explicit approval, anchoring downstream visual design.

### 2.2 What the Current Frontend Displays
In `ContentStage.tsx`, the component synthesizes markdown strings in client memory and passes them into `ArtifactSurface.tsx`:
```typescript
// Route plan flattened to markdown:
const routeMarkdown = view.routePlan.map(r =>
  `### \`${r.path}\` — ${r.title}\n* **Purpose:** ${r.purpose}\n* **Status:** \`${r.publicationStatus}\`\n* **Audience takeaway:** ${r.audienceTakeaway}\n* **Sections:** ${r.sectionSequence.map(s => `\`${s}\``).join(", ")}`
).join("\n\n---\n\n");

// Sections flattened to markdown:
const packsMarkdown = view.pageContentPacks.map(pack => {
  const sectionsText = pack.sections.map(sec => {
    const headline = (sec.content.headline as string) || (sec.content.title as string) || sec.purpose;
    const subhead = (sec.content.subheadline as string) || (sec.content.body as string) || "";
    return `#### Section: \`${sec.sectionId}\` (${sec.priority || "standard"})\n*Purpose: ${sec.purpose}*\n\n${headline ? `**${headline}**\n\n` : ""}${subhead}`;
  }).join("\n\n");
  return `### Route: \`${pack.routeId}\`\n\n${sectionsText}`;
}).join("\n\n---\n\n");
```

### 2.3 Identified Flaws & Gaps
1. **Degrading Structured Data into Pseudo-Markdown:** Content Architect produces richly structured data (nested sections, priorities, publication statuses). Instead of rendering clean visual cards, route trees, and editorial wireframes, `ContentStage.tsx` flattens everything into raw Markdown with markdown hashes (`###`), asterisks (`*`), and backticks (`` ` ``).
2. **Missing Section Data:** Section content dictionaries can contain complex structures (e.g. project lists, technology tags, metric callouts). `ContentStage.tsx` only inspects `headline` and `subhead/body`, throwing away all other structured content fields from the screen.
3. **No Visual Sitemap:** Routes are listed as bullet points. There is no hierarchical sitemap visualization or route-to-section tree.
4. **Completely Hidden Claim Grounding:** The `claim_grounding` ledger (which documents evidence status and publication status) is completely dropped from the view.
5. **No Route Switching:** The user cannot click on individual routes to isolate and review their specific sections.

---

## 3. Stage 3: Visual Design Director Agent (`visual_design_director`)

### 3.1 What the Backend Produces
The Visual Design Director produces a comprehensive design and experience specification (`VisualDesignDirectorOutput`):
1. **`visual_language`:**
   - `creative_thesis`: Core creative and aesthetic direction statement.
   - `design_keywords`: Curated aesthetic keywords (e.g. `["editorial", "architectural", "tactile"]`).
   - `color_intent`: Palette philosophy, contrast ratios, and semantic roles.
   - `typography_intent`: Typeface roles, hierarchy, and optical balance.
   - `motion_intent`: Motion philosophy, duration character, and physics curves.
   - `palette_tokens`: Concrete hex/HSL values for primary, secondary, surface, background, and accent.
2. **`shared_visual_systems`:** Background treatments, grid geometry, elevation models, spacing scales.
3. **`pages` (`PageVisualDirection[]`):** Route-by-route visual and layout direction.
4. **`scenes` (`SceneDirection[]`):** Scene-by-scene composition choreography:
   - `layout_intent`: Asymmetric offsets, visual hierarchy, whitespace allocation.
   - `layer_stack`: Explicit z-index and depth layering order.
   - `relative_proportions`: Compositional ratios (e.g. "2/3 text, 1/3 abstract diagram").
   - `alignment_relationships`: Shared reading rails, alignment anchors.
   - `motion_intent`: Entry triggers, reveal behaviors, duration character.
   - `interaction_states`: Touch behavior, focus rings, hover depth.
   - `responsive_behavior` & `reduced_motion_behavior`.
   - `acceptance_criteria`: Visual quality assertions.
5. **`resource_candidates`:** Adapted layout and component patterns from the deterministic catalogue (`catalogue.json`).
6. **`visual_direction_hash`:** SHA-256 hash stamped upon explicit approval, anchoring Build Preparation.

### 3.2 What the Current Frontend Displays
In `DesignStage.tsx`, the component flattens the visual direction into raw markdown text strings:
```typescript
const thesisMarkdown = [
  lang.creativeThesis ? `### Creative Thesis\n${lang.creativeThesis}` : "",
  lang.designKeywords.length > 0 ? `\n\n**Keywords:** ${lang.designKeywords.join(", ")}` : "",
  lang.colorIntent ? `\n\n**Color Intention:** ${lang.colorIntent}` : "",
  lang.typographyIntent ? `\n\n**Typography Intention:** ${lang.typographyIntent}` : "",
  lang.motionIntent ? `\n\n**Motion Rules:** ${lang.motionIntent}` : "",
].join("");
```

### 3.3 Identified Flaws & Gaps
1. **A Visual Design Stage with Zero Visual Elements:** The user is asked to review and approve the visual design direction of their site, yet the screen consists solely of black-and-white markdown bullet points.
2. **No Palette Swatches:** Even though `color_intent` and palette tokens exist, there are no color swatches or contrast tokens rendered.
3. **No Typography Specimens:** Typography scales and font choices are described in prose rather than demonstrated with visual type specimens.
4. **Scene Layout Choreography is Buried:** The rich scene choreography (`relative_proportions`, `layer_stack`, `motion_intent`, `interaction_states`) is reduced to flat text bullet points.
5. **Catalogue Candidates are Invisible as Components:** Catalogue recommendations are rendered as plain text strings (`* hero_asymmetric_text_dominant: ...`) instead of visual pattern cards.
6. **No Spatial Scene Cards:** Scenes should be displayed as visual wireframes showing their layer stack and alignment relationships.

---

## 4. Stage 4: Build Preparation Agent (`build_preparation`) — The Core Flaw Area

### 4.1 What the Backend Produces
Build Preparation compiles approved Content and Visual Design models into two production briefs:
1. **`content-and-narrative-brief.md`:** Contains all approved route content and copy, prefixed with a machine-readable ````json build-preparation-content-index ```` block.
2. **`visual-and-build-brief.md`:** Contains all visual directions, typography systems, researched image candidate URLs, and component intents, prefixed with a machine-readable ````json build-preparation-visual-index ```` block.
3. **Structured State Metadata (`BuildPreparationState`):**
   - `routes`: Array of `RouteScope` objects with associated `section_ids`, `scene_ids`, `asset_ids`, and `resource_ids`.
   - `resource_needs`: Array of 40 specific asset/resource requirements.
   - `resource_index`: Array of 23 discovered candidate links (Unsplash/Wikimedia photos, fonts, icons) with real preview URLs, provider IDs, and licenses.
   - `component_index`: Array of 13 component suggestions (e.g. Framer Motion patterns, accessible disclosure widgets) with item URLs and providers.
   - `events`: Ordered audit log of compiler events:
     - `scope_compiled`: Detail breakdown of routes, assumptions, target image count, and resource needs.
     - `resource_research:<hash>`: Provider call count and discovered candidate counts.
     - `compose_visual_brief:<hash>`: Visual model call execution and prose composition.

### 4.2 What the Current Frontend Displays (`BuildPreparationStage.tsx`)

Lines 140–166 of `BuildPreparationStage.tsx`:
```tsx
<div className="preparation-brief-grid">
  <section className="preparation-brief-card" aria-labelledby="content-brief-title">
    <p className="eyebrow">CONTENT BRIEF</p>
    <h2 id="content-brief-title">Content and narrative</h2>
    {view.contentBriefMarkdown ? (
      <SafeMarkdown content={view.contentBriefMarkdown} />
    ) : (
      <p className="preparation-empty">The content brief is not available yet.</p>
    )}
  </section>
  <section className="preparation-brief-card" aria-labelledby="visual-brief-title">
    <p className="eyebrow">VISUAL BRIEF</p>
    <h2 id="visual-brief-title">Visual and build direction</h2>
    {view.visualBriefMarkdown ? (
      <SafeMarkdown content={view.visualBriefMarkdown} />
    ) : (
      <p className="preparation-empty">The visual brief is not available yet.</p>
    )}
  </section>
</div>
```

### 4.3 Why It Looks Completely Wrong
1. **Direct Dumping of Massive Markdown with Fenced JSON:**
   The backend briefs each exceed 150KB to 200KB in size. Near the very top of each brief is a massive fenced JSON block (````json build-preparation-content-index ... ````). Because `BuildPreparationStage.tsx` simply dumps `view.contentBriefMarkdown` and `view.visualBriefMarkdown` into `<SafeMarkdown />`, the user is greeted with a giant wall of raw, unparsed JSON:
   ```json
   {
     "kind": "content_index",
     "run_id": "6b899b90-...",
     "content_architect_content_hash": "a1f9...",
     "navigation_contract": { ... },
     "routes": [ ... ]
   }
   ```
   This looks like a broken debugging dump or an unfinished development script rather than a refined studio product.
2. **Researched Visual Assets are Never Shown:**
   The backend queried external providers and found 23 real photography and asset candidates with real `preview_url` links. **None of these images are rendered.** They remain locked inside the unparsed JSON index inside the markdown text.
3. **Researched Components are Trapped in Text:**
   The 13 component suggestions with URLs and documentation are rendered as plain markdown tables or buried in code blocks.
4. **Compiler Events Stream is Ignored:**
   The `events` log contains precise, reassuring progress milestones (`scope_compiled`, `resource_research:e075a2ad`, `compose_visual_brief:e3bc7699`), yet the frontend ignores them entirely during execution.
5. **Infinite Vertical Scrolling:**
   Rendering two 200KB markdown documents in parallel cards causes the page to stretch thousands of pixels vertically, completely destroying the editorial layout.

---

## 5. Stage 5: Code Generator & Live Preview Sandbox (`code_generator`)

### 5.1 What the Backend Produces
1. **Execution Lifecycle:** Progresses through `queued` -> `planning` -> `acquiring` -> `generating` -> `verifying` -> `ready`.
2. **`active_preview`:**
   - `url`: Sandbox URL on the isolated preview gateway (e.g. `https://preview.oryxenai.local/p/abcd-1234/`).
   - `route_ids`: `["home", "work", "about"]`.
   - `route_paths`: `["/", "/work", "/about"]`.
   - `build_hash`: Verified bundle hash.
   - `candidate_identity_hash`: Unique cryptographic candidate stamp.
3. **`candidate_preview`:** An unverified candidate preview produced when non-blocking issues exist (e.g. minor visual score differences).
4. **`advisories` & `warnings`:** Verification findings, CSS geometry reports, and accessibility checks.
5. **Multi-Viewport Reports:** Headless browser validation results across Desktop (1440x900), Tablet (768x1024), and Mobile (375x812).

### 5.2 What the Current Frontend Displays (`GenerationStage.tsx`)
- Milestone progress via `ProgressSurface`.
- When ready, renders `PreviewPanel` containing an `<iframe>`:
  - Route selector `<select>`.
  - Viewport buttons (`Mobile`, `Tablet`, `Desktop`, `Fit`).
  - Refresh button.
  - Open in new tab link.

### 5.3 Identified Flaws & Gaps
1. **Cross-Origin Iframe Refresh Exception:**
   Line 110 in `GenerationStage.tsx`:
   ```typescript
   onClick={() => frameRef.current?.contentWindow?.location.reload()}
   ```
   Because the preview gateway runs on a different origin or subdomain, accessing `contentWindow.location.reload()` throws a browser `SecurityError: Blocked a frame with origin from accessing a cross-origin frame`. The refresh must be executed by resetting `iframe.src` or remounting the frame.
2. **Missing Fullscreen / Device Theater Mode:**
   The viewport switcher only adjusts CSS dimensions within a constrained container. There is no fullscreen toggle or responsive device frame bezel.
3. **Unverified Candidate Clarity:**
   When a candidate preview exists under `needs_attention`, it is presented with minimal context, leaving the user unsure which checks passed and which failed.
4. **No Route Bar Navigation Sync:**
   Clicking links inside the generated portfolio iframe changes the route within the iframe, but the studio shell toolbar route selector does not update to reflect the iframe’s current URL.
5. **Post-Success Read-Only Indication:**
   Once a portfolio achieves a verified preview, all mutation endpoints reject requests with `PORTFOLIO_READ_ONLY`, but the UI does not celebrate this milestone with a permanent completion seal or explain why editing is locked.

---

## 6. Synthesis: Exact Blueprint for the Frontend Revamp

| Stage | Current Implementation Flaw | Required Revamped Experience |
|---|---|---|
| **Discovery** | Structured profile facts (skills, projects, experience) are hidden. | Split-screen workspace: Focused chat interview on left; live-updating structured profile card on right. |
| **Content Architect** | Flattens structured routes and sections into raw markdown bullet points. | Visual route architecture map (sitemap tree), visual section wireframe cards, copy inspection drawer. |
| **Visual Design** | Zero visual elements; design system is rendered as text bullets. | Interactive design studio: Color palette swatches, typography scale specimen sheet, visual scene layout wireframes, component catalogue gallery. |
| **Build Preparation** | Dumps raw 300KB+ Markdown with huge fenced JSON blocks into cards. | Curated build command center: Summary metrics dashboard, visual image candidate gallery with thumbnails, component suggestions deck, clean brief drawer with syntax-highlighted code modal. |
| **Code Generator** | Cross-origin iframe reload error; constrained device view. | Device theater sandbox (Mobile, Tablet, Desktop, Fullscreen), safe iframe reloading via src reassignment, candidate vs verified status pills, postMessage navigation sync. |
