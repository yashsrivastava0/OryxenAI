# Proposed agent and artifact contracts

> **Status:** target contracts for implementation, not current API schemas. [Start here](README.md) · [System overview](10-proposed-resume-portfolio-system.md) · [Generation and operations](12-generation-preview-revisions-and-operations.md).

## 1. Contract rules shared by all stages

1. Every persisted output has a `contract_version`, stable artifact ID, parent/source version IDs, created time, and content hash. A consumer rejects unknown major versions and stale parents; it does not silently coerce a new payload into an old shape.
2. IDs for facts, projects, roles, sections, links, assets, and versions are stable across targeted revisions. New records get new IDs. Deleted records remain visible in version history but disappear from the new active artifact.
3. A model response is parsed into a strict type, then checked for cross-reference and semantic completeness. JSON-schema conformance does not establish that a claim is true, that a project is well explained, or that a page looks good ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)).
4. Public copy and internal metadata are separate. The renderer can read public copy, section order, link targets, and asset slots. It cannot accidentally render source excerpts, open questions, or model reasoning.
5. User edits are events against an exact desired revision and visible site version. An accepted edit while work is running carries forward earlier accepted edits and supersedes the old candidate. A request from a stale tab receives a conflict to review; it never silently overwrites newer intent.
6. The only model-backed stages are Discovery, Content Architect, and Coding Engine. Each uses the configured OpenAI `gpt-6-luna` profile. The orchestrator, parser, HTML serializer, storage, and verification are ordinary software.

**Source precedence:** a later explicit user correction wins over an earlier answer, which wins over resume text for the same fact. A correction does not erase the old record; it supersedes it by ID. A supplied job description, sample portfolio, theme example, or model suggestion may shape presentation but cannot become a fact about the user. Conflicting resume sources do not get an automatic winner: Discovery records the conflict and asks or uses wording that avoids the disputed value. A user instruction to omit a fact affects public content selection, not the historical dossier. This precedence must be implemented in artifact merging and validators, not just in prompts.

### Artifact chain

```text
SourceDocument/v1 + IntakeIntent/v1
    -> DiscoveryDossier/v1
    -> PortfolioContent/v1
    -> RenderPlan/v1 + ThemeManifest/v1 + AssetManifest/v1
    -> SiteVersion/v1 (index.html, styles.css, assets, verification receipt)
```

The chain is directional. Coding Engine may request an upstream correction, but it may not change facts in its output. The content package is the one canonical source for person-specific visible words; `index.html` is a derived artifact.

Examples below omit some envelope fields for readability. Persisted records still carry the IDs, hashes, timestamps, and parent references required by rule 1.

## 2. Intake and document extraction

**Owner:** deterministic intake service, before Discovery.

**Inputs:** pasted text or uploaded PDF/DOCX/TXT, optional goal, links, theme choice, and later optional photo. The service identifies MIME and file size, extracts text, normalizes whitespace while retaining useful headings/bullets, and records source offsets/page numbers. Tables and two-column resumes require a reading-order check. OCR is a separate fallback for image-only PDFs; if unavailable or low quality, show a readable-text request instead of sending garbage to Discovery. The original file remains an immutable source object.

`IntakeIntent/v1` separately records the person's stated goal, audience, preferred display name/pronouns if volunteered, portfolio language, supplied link IDs/URLs, contact action, chosen theme, and which fields are explicit versus defaults. A missing preference is not converted into a fabricated personal preference. The intake form can stay short; Discovery asks only for consequential missing details.

The server creates a `SourceDocument` for **each** input and marks its role (`resume_candidate`, `primary_resume`, `secondary_resume`, `job_description`, `user_note`, `reference_portfolio`). Two resume candidates stay unselected until the user chooses a primary source or answers that question. Pasted text is a source with an immutable text snapshot even when there is no binary upload. Extraction preserves paragraph order, bullets, page/section positions, and original spelling in source spans. It may normalize a separate working text copy for the model. If a PDF's reading order is suspect, the UI should expose a short text preview for correction; a model must not silently infer a chronology from scrambled columns. OCR can improve a scanned PDF, but the output remains marked as OCR-derived and needs the same readable-text gate.

**Output:** `SourceDocument/v1` contains document ID, original object key/hash, format, extraction status (`readable`, `needs_text`, `partial`), extracted-text object key/hash, page count when known, and source spans. A span has ID, page/section or character range, and a short exact excerpt. The extractor does not declare that a resume statement has been externally verified.

**Illustrative extraction excerpt:**

```json
{
  "contract_version": "SourceDocument/v1",
  "id": "resume-1",
  "format": "pdf",
  "original_object_key": "sources/resume-1/original.pdf",
  "original_sha256": "<computed-content-hash>",
  "extraction_status": "readable",
  "extracted_text_object_key": "sources/resume-1/text.txt",
  "extracted_text_sha256": "<computed-text-hash>",
  "page_count": 2,
  "spans": [
    {"id": "resume-1:page-1:span-1", "page": 1, "excerpt": "Ajay Mehta"},
    {"id": "resume-1:page-1:span-8", "page": 1, "excerpt": "Reduced billing processing time by 25%"}
  ]
}
```

Hashes above are schematic fields populated by the service; no model supplies them. A production record also stores extraction diagnostics and text ranges so a fact can be traced beyond a short excerpt.

**Admission rules:** a meaningful text threshold, supported format, extraction diagnostics, and an explicit path for very large documents. A partial extraction is labelled partial. Multiple uploaded resumes remain separate sources; the user selects the primary one or Discovery asks which to use. A job description or sample portfolio is labelled reference material and is never merged into the person's biographical facts.

## 3. Discovery Agent

### Single responsibility

Create the most useful **fact and intent handoff** for Content Architect. Discovery understands the person's career history and asks for missing context that would change the resulting page. It does not decide final positioning, section order, CTA wording, CSS theme, or public paragraphs.

### Reads

- Original source document IDs and extracted text/spans; initial goal and user-supplied links.
- Prior questions and answers; previous dossier version for a factual revision.
- An explicit selected theme preference, if the user has chosen one. Discovery records it; it does not analyze CSS.

### Question policy

Ask one to three high-value questions per turn, chosen from the material rather than a fixed list. Useful topics are portfolio goal/audience, personal versus team role, project problem, meaningful decision, measurable or qualitative result, work examples to feature, contact action, and ambiguous dates. A question must have a stated reason linked to an open item and must be skippable. Avoid asking for metrics a person does not have or asking the same question again after a skip. If enough material exists, go directly to the dossier. If the resume is sparse, a small interview may be necessary; a configured total-question budget prevents an endless loop, and after the user chooses to continue, finish with what is available.

An initial product default can be **at most two question rounds and five questions total**, with one to three in any one round; keep these values in configuration so observed completion rates can change them. If the user explicitly chooses “continue,” stop asking immediately. An indispensable unresolved conflict may still block a specific claim; it does not block a shorter portfolio built from the remaining evidence.

A question is worthwhile when its answer could change a featured story, factual wording, section selection, or visitor action. It is not worthwhile merely because a field in a template is empty.

The Discovery operation has a **tagged result**: `questions` (one to three question records with gap ID, reason, and affected fact/project IDs) or `dossier` (complete `DiscoveryDossier/v1`). The first understanding call may return a complete dossier directly when it has enough material; there is no compulsory second call. Answers and skips are persisted before continuation. A resumed call receives the current dossier draft or fact candidates, unanswered high-value gaps, the new answer events, and only cited source spans needed to resolve them. It must not reopen already skipped questions merely because a field remains blank. The orchestrator, not the agent, enforces the configured question and round limits.

For example, a billing resume that says only “improved processing time by 25%” could prompt: “Which part of this rollout did you personally work on, and was the 25% result for your part or the wider team?” The question record cites the ambiguous source span, explains that attribution affects portfolio wording, and accepts either an answer or a skip. A skipped question leaves an explicit gap and leads to neutral team wording.

### Writes: `DiscoveryDossier/v1`

| Field | Meaning |
| --- | --- |
| `intent` | Goal, likely audience, desired visitor action, explicit emphasis and tone preferences; distinguish stated preferences from defaults |
| `subject` | Name/title/location and supplied links with stable IDs |
| `facts[]` | Atomic statements with fact ID, normalized wording, source span or answer ID, status (`supplied`, `user_clarified`, `unclear`, `conflicting`), and ownership when applicable |
| `roles[]` | Organization, role, dates as supplied, responsibilities, linked project/fact IDs |
| `projects[]` | Context/problem, personal role, team role, approach/decisions, tools, result/metric and its scope, proof/link, linked fact IDs |
| `other_evidence[]` | Education, research, publications, awards, credentials, skills, talks, open source and other supplied material |
| `open_items[]` | Missing/contradictory facts, importance, question status, and safe wording constraint |
| `user_choices` | Feature/omit requests, exact terms to retain or change, selected theme preference |
| `source_refs` | Document/answer IDs and offsets needed to trace the dossier |

`supplied` means the user-provided material says it; it does **not** mean independently verified. A user correction creates a newer fact version and marks the former value superseded. Numeric outcomes keep units, baseline/timeframe if supplied, and individual/team attribution; unknown parts stay unknown. Resume keywords alone do not justify an invented case study.

For each factual record, keep `source_refs`, `subject_id`, `ownership`, `supersedes_fact_id` when corrected, and a normalized value where relevant (for example date text and parsed date separately). Parsing a date into a machine value must never silently add a missing month or day. For a result, store the exact value/unit, whose result it was, and the measurement period only if supplied. The dossier can include factual strengths and open gaps; it does not include public-facing headlines or unsupported career positioning.

**Illustrative compact excerpt; the real dossier can contain many records:**

```json
{
  "contract_version": "DiscoveryDossier/v1",
  "id": "dossier-2",
  "source_document_ids": ["resume-1"],
  "intent": {
    "goal": "Find backend engineering roles",
    "audience": "Hiring teams",
    "visitor_action": "Read selected work",
    "basis": "user_answer"
  },
  "subject": {"name": "Ajay Mehta", "current_title": "Backend Engineer"},
  "facts": [
    {
      "id": "fact-1",
      "statement": "Ajay Mehta is the displayed name",
      "source_refs": ["resume-1:page-1:span-1"],
      "status": "supplied"
    },
    {
      "id": "fact-2",
      "statement": "Ajay's current title is Backend Engineer",
      "source_refs": ["resume-1:page-1:span-2"],
      "status": "supplied"
    },
    {
      "id": "fact-17",
      "statement": "The billing rollout reduced processing time by 25%",
      "source_refs": ["resume-1:page-1:span-8"],
      "status": "supplied",
      "ownership": "team"
    },
    {
      "id": "fact-18",
      "statement": "Ajay redesigned the queue consumer for the rollout",
      "source_refs": ["answer-3"],
      "status": "user_clarified",
      "ownership": "individual"
    }
  ],
  "projects": [
    {
      "id": "project-billing",
      "name": "Billing rollout",
      "problem": "Processing throughput during rollout",
      "personal_contribution_fact_ids": ["fact-18"],
      "result_fact_ids": ["fact-17"]
    }
  ],
  "open_items": [
    {"id": "gap-4", "detail": "Metric baseline and measurement period are unknown", "importance": "wording"}
  ]
}
```

The excerpt is fictional and illustrates data shape, not a claim about the supplied sample portfolio.

### Discovery acceptance

Require at least a usable identity or an explicit anonymous-display choice, a meaningful goal/default goal, source references for substantive facts, stable unique IDs, and no unresolved contradiction used as a confident fact. A dossier may be sparse and still valid. It should be sufficient for Content Architect to distinguish personal contribution from team outcome. A human-readable review summary can be generated from the dossier but is not the downstream source of truth.

## 4. Content Architect Agent

### Single responsibility

Transform the dossier into a **complete, detailed, one-page editorial package** for the coding stage. It selects and orders sections, chooses the leading story, writes every person-specific visible sentence, and ties important factual claims to dossier fact IDs. Fixed theme chrome may supply generic labels, but it never supplies biography. Content Architect does not browse the resume afresh, re-interview the user, decide CSS class names, or generate HTML.

### Reads

- One immutable Discovery dossier version and any targeted source excerpt needed to resolve a referenced ambiguity. The raw resume is not sent by default.
- Common semantic component vocabulary supported by the selected theme(s).
- User's change request and prior content package for an editorial revision.

### Content depth and structure

A hero gives the professional identity and a clear reason to continue. Selected projects use context/problem, personal role, approach/decisions, outcome, and proof when the dossier supplies them. Experience explains progression and scope rather than merely repeating the resume. Skills are grouped around evidenced capability; a flat inventory can be secondary. Education, research, publications, awards, or testimonials appear only if supported by actual material. Core substance stays visible on the page, including on mobile.

There is no fixed project count or word minimum. A rich dossier can support multiple detailed stories; a sparse one cannot. Each paragraph should add information, not repeat adjectives. The final package must include finished nav labels, headings, project copy, CTA/link labels, metadata title and description, and any image captions/alt text that the renderer needs. No “TODO”, “fill later”, or silent placeholder is publishable copy.

| Supported semantic block | Content Architect supplies when evidence exists | When material is missing |
| --- | --- | --- |
| `hero` | Display identity, role, positioning line, introduction, primary action/link ID | Use a precise role or goal; avoid an unsupported specialty claim |
| `project_story` | Title, problem/context, personal contribution, decisions/approach, outcome with attribution and proof/link when supplied | Choose a short variant with only supported fields; never fill an unknown result |
| `experience` | Role, organization, dates as supplied, scope, work/evidence lines | Omit missing dates or scope rather than inventing a timeline |
| `capability_groups` | Evidence-led groups, brief explanation, skills/tools with linked supporting work | Use a modest inventory; no artificial mastery labels |
| `credentials` | Education, research, publications, awards, or certifications and supplied dates/links | Omit the block entirely if unsupported |
| `contact` | User-supplied contact/link action, short closing copy, visible label | If no contact route is supplied, use a real internal evidence section as the action; if neither exists, request more material |

Every selected block carries its full public copy in the package. The table is a semantic vocabulary for all first-release themes, not a requirement that every person have every block.

### Writes: `PortfolioContent/v1`

| Field | Meaning |
| --- | --- |
| `dossier_id` and `dossier_hash` | Exact source version |
| `story` | Positioning, lead evidence, audience takeaway, primary visitor action |
| `document` | Single ordered section array; each section has stable ID, semantic `block_type`, nav label, purpose, public copy, fact refs, link refs, asset slot refs |
| `metadata` | Browser title/description and sharing summary text |
| `links` | Stable ID, label, URL and where it is used |
| `asset_slots` | Optional portrait, visual, or logo need; an absent slot has a defined fallback |
| `editorial_notes` | Review-only omissions, unresolved detail, and explanation of user-confirmed versus inferred choices |

The `document.sections[]` array is the only source of section order and nav labels. A section's copy is typed by block type: for example `project_story` can contain `context`, `contribution`, `approach`, and `outcome`, with required fields defined by its chosen short or long variant. Only supported block types enter a renderable package. If a theme does not support one, Content Architect selects a supported generic narrative block or returns a capability gap; it never silently drops the project.

Each factual sentence or field also has a `claim_bindings[]` entry containing its **typed field path** and supporting dossier fact IDs. A section-wide `fact_refs` list is a host-derived index of these bindings, not a substitute for them. The validator checks that every cited fact exists, is current, and permits the proposed ownership/metric wording. Purely editorial transitions need no fact binding. Static labels such as “Selected work” are theme or content vocabulary, not biographical claims. Automated checking catches missing references and changed numbers; nuanced overclaiming still needs task-specific review examples.

**Typed public-copy fields for the first theme family:**

| Block | Required when selected | Optional, only when supported | Normal omission behavior |
| --- | --- | --- | --- |
| `hero` | `name` (or chosen anonymous display identity), `eyebrow`, `headline`, `introduction`, `primary_action_label`, `primary_action_link_id` | location, second action, decorative visual slot | Image-free hero; a chosen anonymous display label is valid |
| `project_story` | title, context, contribution | approach, result, proof link, tools | Short variant when decisions/results are unknown; no invented metric |
| `experience` | role or organization, at least one scope/work line | date text, progression, linked project | Narrative variant when dates are missing or inconsistent |
| `capability_groups` | one or more named groups with supported examples | secondary tool inventory | Do not invent mastery levels or fill an arbitrary quota |
| `credentials` | at least one sourced item | date, issuer, link | Omit section entirely when empty |
| `contact` | heading and usable internal or supplied external action | supplied contact links, closing note | Internal action when no external contact route is provided |

This table defines minimum renderable fields. Long-form variants may need more copy, but they cannot force Content Architect to fabricate an outcome. The selected theme's manifest supplies item-count and soft text-length bands; those guide variant selection and browser checks rather than hard truncation.

**Illustrative excerpt:**

```json
{
  "contract_version": "PortfolioContent/v1",
  "id": "content-4",
  "dossier_id": "dossier-2",
  "story": {
    "positioning": "Backend engineer with billing rollout experience",
    "reader_takeaway": "Ajay contributed to a billing rollout through a queue-consumer redesign",
    "primary_action_link_id": "link-selected-work"
  },
  "document": {
    "mode": "single_document",
    "sections": [
      {
        "id": "hero",
        "block_type": "hero",
        "nav_label": null,
        "copy": {
          "name": "Ajay Mehta",
          "eyebrow": "Backend Engineer",
          "headline": "Backend engineering through practical system changes.",
          "introduction": "I work on backend systems, including a billing rollout where I redesigned the queue consumer.",
          "primary_action_label": "Explore selected work",
          "primary_action_link_id": "link-selected-work"
        },
        "fact_refs": ["fact-1", "fact-2", "fact-18"],
        "claim_bindings": [
          {"field_path": "copy.name", "fact_ids": ["fact-1"]},
          {"field_path": "copy.eyebrow", "fact_ids": ["fact-2"]},
          {"field_path": "copy.introduction", "fact_ids": ["fact-2", "fact-18"]}
        ],
        "asset_slots": ["hero-visual"]
      },
      {
        "id": "billing-work",
        "block_type": "project_story",
        "nav_label": "Selected work",
        "copy": {
          "title": "Making a billing rollout process work more efficiently",
          "context": "The team worked on a billing rollout.",
          "contribution": "I redesigned the queue consumer for that rollout.",
          "outcome": "The team reported a 25% reduction in processing time during the rollout."
        },
        "fact_refs": ["fact-17", "fact-18"],
        "claim_bindings": [
          {"field_path": "copy.title", "fact_ids": ["fact-17"]},
          {"field_path": "copy.context", "fact_ids": ["fact-17"]},
          {"field_path": "copy.contribution", "fact_ids": ["fact-18"]},
          {"field_path": "copy.outcome", "fact_ids": ["fact-17"]}
        ]
      }
    ]
  },
  "metadata": {
    "title": "Ajay Mehta | Backend Engineer",
    "description": "Selected backend engineering work by Ajay Mehta."
  },
  "links": [{"id": "link-selected-work", "label": "Explore selected work", "url": "#billing-work"}],
  "asset_slots": [{"id": "hero-visual", "kind": "theme_illustration", "optional": true}],
  "editorial_notes": ["Do not attribute the team-wide 25% result solely to Ajay.", "The measurement period and design decisions were not supplied; omit those details from public copy."]
}
```

The example deliberately shows an editorial limitation: the missing design decision is absent from public copy and recorded only in review metadata. A supported shorter project variant is selected for this content. The sample is schematic, not a quality benchmark for public wording.

### Content acceptance

- One hero, a substantive evidence section when any work/education/skills material supports one, and a coherent closing/contact action. No mandatory projects for a user who has none. If a source contains no substantive evidence and the user skips every request for more, produce a minimal truthful introduction only when a usable destination/link still makes a page meaningful, with an explicit `limited_content` review flag. If there is neither evidence nor a usable destination, return `needs_material` with one concrete request instead of manufacturing a case study or a self-link.
- Each factual section cites existing dossier facts; measurable results have matching wording, units, and attribution. Draft review notes never appear in public copy.
- Section IDs and link IDs are unique; navigation is derived from sections present; every selected block is theme-compatible.
- A dense package remains readable. When excessive text cannot fit a supported design, shorten lower-priority repetitions or select a long-form component; never silently truncate a fact or paragraph.
- If a single indispensable clarification is needed, emit a bounded `clarification_request` targeting the precise dossier gap. Otherwise produce the best supported package.

The Content Architect's completion check compares the section plan to the actual typed copy: every planned section has copy, every copy field required by its block variant is filled, every link ID resolves, and a section selected for the navigation has a label. A package can deliberately omit unsupported optional sections, but it records that choice in `editorial_notes`. It cannot hand the Coding Engine an outline and expect the renderer to invent paragraphs.

## 5. Coding Engine Agent and controlled renderer

### Single responsibility

Choose a polished composition from the **actual supported theme components** and turn the content package into a working site version. Coding Engine may decide between approved hero/project/experience variants and select an available visual asset. It cannot invent a new claim, change a metric, omit a required section, or write a per-user stylesheet in this release.

### Reads

- Exact `PortfolioContent` version; a compact `ThemeManifest` projection and component examples; asset IDs and verified storage keys; prior render plan and change request for a layout revision. The model normally does **not** read the prior full HTML, CSS, raw resume, or all prior chat.
- Browser findings from a failed candidate when a repair is warranted. It receives bounded diagnostics tied to section/component IDs, not an unbounded transcript.

### Writes: `RenderPlan/v1`

The model-backed composition operation returns a small typed plan: theme version, section ID to supported component variant, asset-slot binding, and optional layout notes constrained to the theme's vocabulary. A host renderer serializes the plan and the content package to semantic HTML. It owns `doctype`, `<head>`, section IDs, nav links, escaping, relative asset paths, and `styles.css` reference. This still creates a different `index.html` for each user, with AI-chosen composition, while eliminating free-form CSS/JS/path creation.

```json
{
  "contract_version": "RenderPlan/v1",
  "id": "plan-7",
  "content_id": "content-4",
  "theme_id": "editorial-forest/v1",
  "placements": [
    {"section_id": "hero", "variant": "hero-with-illustration", "asset_slot": "hero-visual"},
    {"section_id": "billing-work", "variant": "project-story-short", "asset_slot": null}
  ]
}
```

A `SiteVersion/v1` then records parent dossier/content IDs, theme ID/hash, `index.html` hash, stylesheet hash, asset manifest, screenshot keys, verification receipt, and preview URL. The AI proposes only allowed variant IDs and slots; the renderer performs all actual path and tag assembly. Initial generation makes one configured Luna composition call. A mechanical revision such as a corrected name may reuse its valid plan and re-render without another composition call; when the layout choice changes, Luna proposes the new plan.

```json
{
  "contract_version": "SiteVersion/v1",
  "id": "site-7",
  "content_id": "content-4",
  "render_plan_id": "plan-7",
  "theme_id": "editorial-forest/v1",
  "files": [
    {"path": "index.html", "sha256": "<computed-html-hash>"},
    {"path": "styles.css", "sha256": "<computed-css-hash>"}
  ],
  "asset_manifest_id": "assets-7",
  "verification": {"receipt_id": "verify-7", "status": "passed"},
  "preview_path": "/p/portfolio-1/site-7/index.html"
}
```

The model does not emit this site manifest. The host fills it after object readback and verification, then promotes the version if its requested revision is still current. Hash placeholders represent computed values, never literal production values.

### Theme manifest and component contract

Each theme specifies semantic block types, allowed variants, required/optional fields, HTML pattern version, class vocabulary, CSS hash, asset slots, font files, image dimensions/crops, responsive expectations, and HTML/JS capability version. Theme selection is either a user choice or a bounded default based on content shape. All themes should initially support the same block types so Content Architect can write once and theme switching only rerenders.

**Illustrative theme manifest excerpt:**

```json
{
  "contract_version": "ThemeManifest/v1",
  "theme_id": "editorial-forest/v1",
  "stylesheet": {"path": "styles.css", "sha256": "<computed-css-hash>"},
  "components": {
    "hero": ["hero-with-illustration", "hero-monogram"],
    "project_story": ["project-story-short", "project-story-long"],
    "experience": ["experience-narrative"],
    "capability_groups": ["capability-groups"],
    "credentials": ["credentials-list"],
    "contact": ["connect-layout"]
  },
  "asset_slots": ["hero-visual", "portrait"],
  "capabilities": {"html": "single-document/v1", "javascript": false}
}
```

The actual manifest also names each variant's required/optional copy fields, HTML template/class IDs, local asset files and hashes, and responsive fixture IDs. A theme is published into the catalogue only after those templates and its CSS are verified together.

The implementer should make `ThemeManifest/v1` an executable compatibility record, not a free-text description. For each variant it declares `block_type`, `variant_id`, `template_id`/template hash, required/optional copy paths, minimum/maximum item counts if the design truly has a structural limit, advisory text-length bands, emitted class/child structure, asset slots, and a fallback variant. The manifest also has a default variant per block. A build-time theme linter checks that all referenced templates, CSS selectors, fonts, and local images exist. The model sees only variant IDs, field availability, and short descriptions; the host renderer reads the full manifest and templates.

**Compatibility rule:** Content Architect chooses semantic blocks from the intersection supported by the selected theme and the first-release common vocabulary. Coding Engine chooses only a variant declared for that exact block. The host rejects unknown classes or copied reference markup that the manifest has not registered. If a new CSS version changes a component's markup needs, publish a new theme version and template version together. Existing sites keep their pinned version. Content may be reused across themes only after a compatibility check; otherwise an editorial conversion is explicit and reviewable.

For the supplied CSS seed, `editorial-forest/v1` must be completed before general use: the original selectors support `hero`, `pillar-grid`, `capability-group`, `context-layout`, and `connect-layout`, while project stories and variable experience need new shared CSS/components. Those additions are theme development, not person-specific generation. The sample's font references and remote hero image must be resolved by the theme asset build.

### Coding acceptance

Every public section and required copy field from `PortfolioContent` appears in the HTML exactly once according to its component contract. The page has one main landmark, sensible heading order, live anchor targets, asset paths in the manifest, no unsupported class/variant, no script for the current capability version, and no review-only metadata. Browser verification is a separate, required step before promotion.

## 6. Context and model-call policy

- **Discovery:** one understanding call when the source is ready; question rounds only while material gaps remain. It can return the dossier in the first call. Otherwise use one dossier-finalization call after the last answer/skip. Persist answers after every user action. No repeated full extraction for a simple correction.
- **Content Architect:** one complete plan-and-write call for ordinary cases; one optional targeted continuation for a genuinely long package or a precisely failed consistency gate. Do not split into a model call per section by default.
- **Coding Engine:** one composition call for a new portfolio, then host rendering; a valid plan can be reused for a mechanical content revision. A bounded targeted repair call applies only when a correctable component mapping error survives deterministic normalization. No general “regenerate the whole site until it looks good” loop.

For an oversized source, split extracted text at document/section boundaries into bounded chunks with source span IDs, extract atomic facts from each, then merge and check contradictions before the dossier is finalized. Do not keep only the beginning of a resume or silently drop later pages. The chunking threshold and per-operation context allowance are configuration values; each chunk's provenance survives the merge. The fact graph and question/answer events are durable memory. Model context is assembled from those records for the current task, not from an ever-growing raw chat transcript.

### Exact model packets and memory

| Operation | Assemble these inputs | Exclude from the default packet | Persisted result |
| --- | --- | --- | --- |
| Discovery understanding | Stable instructions/schema, `IntakeIntent`, all readable source spans or one bounded source chunk, current correction events | Theme CSS, page HTML, unrelated chat turns | Tagged questions or dossier/fact candidates with source IDs |
| Discovery continuation | Latest dossier/fact candidates, new answers/skips, the cited spans for open gaps, explicit user preferences | Whole resume again when only one fact changed | New dossier or next bounded question set |
| Content writing | Exact dossier, requested goal/audience, selected theme's semantic block vocabulary, prior package and edit instruction only on revision | Raw PDF, full chat transcript, stylesheet text, prior HTML | Complete `PortfolioContent/v1` |
| Coding composition | Exact content package, compact theme manifest projection, available asset IDs, prior plan and targeted browser finding only when relevant | Resume, dossier source excerpts, full CSS, old HTML by default | `RenderPlan/v1` with only declared IDs/variants |

The database is the durable memory. Each request is assembled afresh from immutable artifacts and newer user events, with a deterministic ordering: stable system instructions and schema, versioned theme/component vocabulary when needed, then dynamic portfolio material. Model conversation state or provider compaction is not the canonical memory, because an opaque summary cannot replace source-linked facts. A prompt cache can speed repeated stable prefixes, but a cache hit is neither guaranteed nor a correctness condition ([OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)).

### Token admission and overflow behavior

1. Compile the **actual** request for one operation, including instructions, structured-output schema, selected facts/sections, examples, and any tool definitions. Keep shared instructions before user-specific material to make the prefix stable.
2. Check `input_tokens + reserved_max_output_tokens + safety_margin <= configured_operation_context_limit`, with `configured_operation_context_limit` no greater than the selected model's published context window. The output reserve includes invisible reasoning/format tokens; the margin accounts for transport or schema changes. The model's large advertised window does not set the product's operational limit.
3. Use the Responses [input-token counting endpoint](https://developers.openai.com/api/docs/guides/token-counting) for an exact near-limit count of the same request shape. A local estimate may reject obviously excessive material early, but a character count is not an exact token count. Record estimated and actual counts and response usage by operation.
4. If Discovery source material does not fit, split it on section/page boundaries, carry the heading and source IDs into each chunk, extract facts per chunk, deduplicate repeated facts by source identity, and merge contradictions before a final dossier call. Never drop trailing pages. If a Content package does not fit, first remove repeated source excerpts and irrelevant history; if output itself is too large, use a bounded continuation over named sections and an integration check. Coding Engine gets only the compact manifest, never the whole stylesheet.
5. A refusal, truncated/incomplete output, schema failure, or semantic validation failure is a classified result. Do not parse a partial JSON body into a publishable artifact. Retry only the same immutable operation within its configured attempt limit or request the precise upstream correction. Changing the input shape, schema, or prompt creates a new operation fingerprint.

Structured Outputs improves shape reliability but still requires application validation for cross-references, factual grounding, and page completeness ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)). No hidden provider transcript is replayed wholesale across stages. Persist enough bounded call metadata to reproduce the packet from immutable artifact versions; the portfolio's user-facing edit history is separate from the model's prompt history.

Limits are configuration values, chosen from measured latency and failure data, not magic numbers in prompts. Transient provider failures can retry the same immutable operation within a small budget; semantic defects return a specific failure. The application records each attempt and never duplicates an uncertain successful write. Evaluation cases should be stage-specific and calibrated with human review, consistent with [OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

### Requested model integration gate

The requested target is OpenAI `gpt-6-luna` for every model-backed stage. Keep the existing `ModelClient` abstraction, but add or adapt a direct OpenAI profile that actually reaches this model. The present provider-compatible chat adapter and its fallback policy are not proof of compatibility. Prefer the Responses API for the new structured-output operations; set schema output through its supported response format, validate the result again in application code, and handle refusal, incomplete output, unsupported schema shape, timeout, and rate-limit responses. For non-`none` reasoning effort, omit unsupported sampling parameters such as `temperature` and `top_p`; pin reasoning effort per operation and evaluate the chosen settings on representative cases. The current provider-neutral call boundary may need an adapter change to express these parameters. Do not silently substitute another model if this requested model is unavailable; surface a stage-specific configuration or provider error. These are implementation checks, not a claim that account access has already been established. See [the model page](https://developers.openai.com/api/docs/models/gpt-6-luna), [GPT-6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model), and [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

**Concrete repository blocker:** `ModelRuntime._validate_profile()` in `src/oryxenai/agents/shared/model_runtime.py` explicitly raises for `provider == "openai_responses"`. Current active operation routing in `config/models.toml` also has fallback profiles inconsistent with the requested single-model target. Before changing agent prompts, implement and verify the Responses transport behind `ModelClient`, update its capability declaration and operation routes, and confirm a strict schema call through the configured profile. Do not remove the explicit rejection until the transport exists. This is a target implementation dependency; these architecture documents do not change runtime configuration.

## 7. Current-to-target contract differences

| Current implementation | Target |
| --- | --- |
| Discovery accepts `message/document_text/goal`, emits Markdown brief, summary, and a small fact-only profile | Intake extracts document with source spans; Discovery emits a richer canonical dossier with intent, ownership, project detail, answer references, and open gaps |
| Content Architect receives summary/profile/open items and omits the full brief | Receives the complete structured dossier; no strategic context is lost in a brief that was never passed downstream |
| Content Architect plans single/hybrid/multi routes and separate page packs/manifest | Produces one single-page package with one section array and one canonical public-copy source |
| Approvals are explicit stage gates | The orchestrator advances automatically after useful questions; the generated preview is the principal review surface |
| No active generator | A new theme-bound HTML Coding Engine and renderer are added; old complex generator contracts are not restored |
| The current state validates mostly response shape and some references | New artifacts also validate completeness, cross-stage traceability, supported components, and browser-rendered behavior |

Implementation must migrate or adapt old records intentionally. Old brief/profile snapshots lack the proposed source IDs and project context; an automated conversion should mark unknown provenance and ask the user to confirm material missing facts rather than inventing them.
