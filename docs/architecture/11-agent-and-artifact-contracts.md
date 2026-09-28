# Proposed agent and artifact contracts

> **Status:** proposed contracts for research and user review; not implemented API schemas. [Start here](README.md) · [System overview](10-proposed-resume-portfolio-system.md) · [Generation and operations](12-generation-preview-revisions-and-operations.md) · [Detailed agent playbook](13-agent-operation-playbook.md).

## 1. Contract rules shared by all stages

1. Every persisted output has a `contract_version`, stable artifact ID, portfolio/session ID, desired revision, parent IDs/hashes, operation/attempt ID, created time, and content hash. Model-produced artifacts also record prompt/configuration versions. The host computes hashes from canonical serialization. A consumer rejects unknown major versions or mismatched parents; it does not silently coerce a new payload into an old shape.
2. IDs for facts, projects, roles, sections, links, assets, and versions are stable across targeted revisions. New records get new IDs. Deleted records remain visible in version history but disappear from the new active artifact.
3. A model response is parsed into a strict type, then checked for cross-reference and semantic completeness. JSON-schema conformance does not establish that a claim is true, that a project is well explained, or that a page looks good ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)).
4. Public copy and internal metadata are separate. The renderer can read public copy, section order, link targets, and asset slots. It cannot accidentally render source excerpts, open questions, or model reasoning.
5. User edits are events against an exact desired revision and visible site version. An accepted edit while work is running carries forward earlier accepted edits and supersedes the old candidate. A request from a stale tab receives a conflict to review; it never silently overwrites newer intent.
6. The model-backed stages are Discovery, Content Architect, and Coding Engine, including their scoped interpretation/audit/repair operations. Each resolves a profile through `ModelClient` and `config/models.toml`. The orchestrator, parser, HTML serializer, storage, and mechanical verification are ordinary software.

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

**Inputs:** pasted text or readable PDF/DOCX/TXT, optional goal, source role, and links. Identify format beyond the declared MIME, bound size/decompression/parser time and memory, preserve the original, and extract text with stable locations. Retain original spelling separately from normalized working text. Image-only, encrypted, corrupted, or unreliable documents return a readable paste/replacement request. **OCR is deferred from the first release.** PDF extraction can lose reading order and cannot recover text from images by itself ([pypdf extraction documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)).

`IntakeIntent/v1` separately records the person's stated goal, audience, preferred display name/pronouns if volunteered, portfolio language, supplied link IDs/URLs, contact action, chosen theme, and which fields are explicit versus defaults. A missing preference is not converted into a fabricated personal preference. The intake form can stay short; Discovery asks only for consequential missing details.

The server creates a `SourceDocument` for **each** input and marks its role (`professional_details`, `job_description`, `writing_reference`, `visual_reference`, `instruction`, `correction`). An optional primary/resume relationship describes intentional replacement; it is not permission to discard other sources. Multiple resumes can contribute compatible facts. Ask about consequential contradictions, without requiring a primary-selection question for every upload. Every answer/addition/correction is an immutable source event. A job description is target context and cannot support a personal achievement.

Originals, extracted text, and spans remain private. A span carries document/version, text offsets, page/paragraph where available, and extraction diagnostics. Partial extraction requires an explicit user choice to continue with the readable subset or provide a replacement; record the excluded pages/spans. Do not silently accept a partially parsed file as complete. Restrict accepted files and parsing resources as described in [OWASP upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html). Embedded instructions in resumes/reference documents remain untrusted source text, following the separation described by [OWASP prompt injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

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

**Admission rules:** supported format, bounded resources, readability diagnostics, and an explicit path for large documents. Text length alone does not prove quality or meaningful evidence. Every accepted source must have a terminal extraction disposition. Never silently trim the source to the model context limit.

## 3. Discovery Agent

### Single responsibility

Create the most useful **fact and intent handoff** for Content Architect. Discovery understands the person's career history and asks for missing context that would change the resulting page. It does not decide final positioning, section order, CTA wording, CSS theme, or public paragraphs.

### Reads

- Original source document IDs and extracted text/spans; initial goal and user-supplied links.
- Prior questions and answers; previous dossier version for a factual revision.
- An explicit selected theme preference, if the user has chosen one. Discovery records it; it does not analyze CSS.

### Question policy

Ask one to three high-value questions per turn, chosen from the material rather than a fixed list. Useful topics are portfolio goal/audience, personal versus team role, project problem, meaningful decision, measurable or qualitative result, work examples to feature, contact action, and ambiguous dates. A question must have a stated reason linked to an open item and must be skippable. Avoid asking for metrics a person does not have or asking the same question again after a skip. If enough material exists, go directly to the dossier. If the resume is sparse, a small interview may be necessary; a configured total-question budget prevents an endless loop, and after the user chooses to continue, finish with what is available.

Proposed defaults are **up to three questions per turn and two rounds**, configured centrally; zero questions is valid. If the user chooses “continue,” stop the interview. A disputed optional claim is omitted or phrased without the disputed value. If available material cannot support a meaningful page, return `needs_input` with one concrete request and retain every skip; do not restart a questionnaire.

A question is worthwhile when its answer could change a featured story, factual wording, section selection, or visitor action. It is not worthwhile merely because a field in a template is empty.

The Discovery operation returns `questions`, `dossier`, or `needs_input`. A question includes question-set ID, gap ID, reason, affected facts/entities, and answer/skip status. A complete first-call dossier can advance immediately after validation. Persist answer/skip events before continuation; load the current dossier draft, unresolved gaps, relevant original spans, and new events. The host enforces rounds/limits. Draft chunk outputs never masquerade as a complete dossier.

For example, “improved processing time by 25%” could prompt: “Which part did you handle, and was the result yours or the team's?” A skip leaves ownership unknown. Use wording that does not assign the result to either an individual or a team, or omit it when even project attribution is unclear. Never convert unknown ownership into assumed team ownership.

### Writes: `DiscoveryDossier/v1`

| Field | Meaning |
| --- | --- |
| `intent` | Goal, likely audience, desired visitor action, explicit emphasis and tone preferences; distinguish stated preferences from defaults |
| `subject` | Name/title/location and supplied links with stable IDs |
| `facts[]` | Atomic values/statements, original wording, evidence refs, qualifiers, ownership, and status (`source_asserted`, `user_confirmed`, `conflicting`, `superseded`) |
| `roles[]` | Organization, role, dates as supplied, responsibilities, linked project/fact IDs |
| `projects[]` | Context/problem, personal role, team role, approach/decisions, tools, result/metric and its scope, proof/link, linked fact IDs |
| `other_evidence[]` | Education, research, publications, awards, credentials, skills, talks, open source and other supplied material |
| `open_items[]` | Missing/contradictory facts, importance, question status, and safe wording constraint |
| `user_choices` | Feature/omit requests, exact terms to retain or change, selected theme preference |
| `source_refs` | Document/answer IDs and offsets needed to trace the dossier |
| `restrictions[]` | Fact/entity/field scope, omit/generalize/private instruction, source event, and public-use rule |
| `source_coverage[]` | Every substantive span mapped to facts, context/reference, instruction, duplicate, or excluded material with a reason |
| `lineage` | Exact source versions/hashes, dossier version, schema, producing operation, and host-computed payload hash |

`source_asserted` means the source says it; `user_confirmed` means a direct answer or correction supports it. Neither means independently verified. A correction supersedes an earlier fact revision while keeping its history. Stable logical fact IDs can have immutable revisions; references must identify the exact dossier/fact revision. Missing information is a gap, not an invented fact. Numeric outcomes retain units, baseline/timeframe when supplied, and attribution. Resume keywords alone do not justify a case study.

For each factual record, keep `source_refs`, `subject_id`, `ownership`, a `supersedes_ref` to the exact earlier fact revision when corrected, and a normalized value where useful (for example date text and parsed date separately). Parsing a date must never add a missing month/day. For a result, retain exact value/unit, attribution, and measurement period only when supplied. The dossier includes factual strengths and gaps, not finished public headlines or unsupported positioning.

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
      "status": "source_asserted"
    },
    {
      "id": "fact-2",
      "statement": "Ajay's current title is Backend Engineer",
      "source_refs": ["resume-1:page-1:span-2"],
      "status": "source_asserted"
    },
    {
      "id": "fact-17",
      "statement": "The billing rollout reduced processing time by 25%",
      "source_refs": ["resume-1:page-1:span-8", "answer-3"],
      "status": "user_confirmed",
      "ownership": "team"
    },
    {
      "id": "fact-18",
      "statement": "Ajay redesigned the queue consumer for the rollout",
      "source_refs": ["answer-3"],
      "status": "user_confirmed",
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

The excerpt is fictional and partial, not a complete dossier or a claim about the user. In this example `answer-3` confirms both the individual contribution and team attribution. Full records also include original wording, restrictions, complete span coverage, lineage, and the referenced source/answer bodies.

### Discovery acceptance

Require a usable identity or explicit anonymous choice, a stated/default goal with its basis, resolving evidence refs, unique IDs, all source-span dispositions, and retained restrictions/conflicts/skips. Preserve every role/project internally; display quotas never truncate the inventory. A sparse dossier can pass. Coverage catches unaccounted extracted spans, but cannot prove extraction or interpretation is perfect. Render readable Markdown and the compact frontend summary from this same dossier; neither replaces it downstream.

## 4. Content Architect Agent

### Single responsibility

Transform the dossier into a **complete, detailed, publishable single-page content package**. Select/order sections, establish emphasis, and write every personalized public field, including metadata and accessible labels. Bind every factual public field to supporting dossier facts. Static theme labels may supply generic chrome, never biography. Do not invent achievements, rewrite facts to satisfy a template, emit HTML/CSS, or directly interview the user; route factual questions through Discovery and the host.

### Reads

- One complete immutable Discovery dossier, including all restrictions, supersessions, gaps, and coverage. Supporting source excerpts for ambiguous or sensitive claims; no dependence on an earlier summary.
- The pinned theme's semantic capabilities: required/optional fields, density, supported interactions, and limitations. **Do not routinely send raw `styles.css`**; selectors alone do not explain the editorial contract.
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
| `narrative` / `evidence_list` | Introduction or other professional evidence using supported paragraphs/items | Use for unusual material or a project lacking required story fields |

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
| `theme_capability_version` | Exact semantic vocabulary and constraints used while writing |
| `claim_bindings[]` | Typed public field paths, supporting current fact IDs/revisions, relevant qualifiers and attribution |
| `coverage_ledger[]` | Every relevant fact/entity: used, condensed, retained internally, excluded by restriction/editorial choice, or unresolved; destination IDs and reasons |
| `review` | Missing evidence, restrictions applied, support/consistency findings, and compatibility issues; never rendered publicly |

The `document.sections[]` array is the only source of section order and nav labels. A section's copy is typed by block type: for example `project_story` can contain `context`, `contribution`, `approach`, and `outcome`, with required fields defined by its chosen short or long variant. Only supported block types enter a renderable package. If a theme does not support one, Content Architect selects a supported generic narrative block or returns a capability gap; it never silently drops the project.

Each factual sentence or field also has a `claim_bindings[]` entry containing its **typed field path** and supporting dossier fact IDs. A section-wide `fact_refs` list is a host-derived index of these bindings, not a substitute for them. The validator checks that every cited fact exists, is current, and permits the proposed ownership/metric wording. Purely editorial transitions need no fact binding. Static labels such as “Selected work” are theme or content vocabulary, not biographical claims. Automated checking catches missing references and changed numbers; nuanced overclaiming still needs task-specific review examples.

**Typed public-copy fields for the first theme family:**

| Block | Required when selected | Optional, only when supported | Normal omission behavior |
| --- | --- | --- | --- |
| `hero` | `name` (or chosen anonymous display identity), `eyebrow`, `headline`, `introduction`, `primary_action_label`, `primary_action_link_id` | location, second action, decorative visual slot | Image-free hero; a chosen anonymous display label is valid |
| `project_story` | title and supported contribution | context/problem, approach, outcome, proof link, tools | Compact variant when context/decisions/results are unknown; generic evidence item when contribution is unknown |
| `experience` | role or organization, at least one scope/work line | date text, progression, linked project | Narrative variant when dates are missing or inconsistent |
| `capability_groups` | one or more named groups with supported examples | secondary tool inventory | Do not invent mastery levels or fill an arbitrary quota |
| `credentials` | at least one sourced item | date, issuer, link | Omit section entirely when empty |
| `contact` | heading and usable internal or supplied external action | supplied contact links, closing note | Internal action when no external contact route is provided |
| `narrative` / `evidence_list` | heading and at least one sourced paragraph/item | links, dates, captions | Preserve unusual professional material without fabricating a project or credential |

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
          {"field_path": "copy.headline", "fact_ids": ["fact-2", "fact-18"]},
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
          "outcome": "The team's billing rollout reduced processing time by 25%."
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
  "claim_bindings": [
    {"field_path": "metadata.title", "fact_ids": ["fact-1", "fact-2"]},
    {"field_path": "metadata.description", "fact_ids": ["fact-1", "fact-2", "fact-18"]}
  ],
  "coverage_ledger": [
    {"fact_id": "fact-1", "disposition": "used", "section_ids": ["hero"], "other_paths": ["metadata.title", "metadata.description"]},
    {"fact_id": "fact-2", "disposition": "used", "section_ids": ["hero"], "other_paths": ["metadata.title", "metadata.description"]},
    {"fact_id": "fact-17", "disposition": "used", "section_ids": ["billing-work"]},
    {"fact_id": "fact-18", "disposition": "used", "section_ids": ["hero", "billing-work"]}
  ],
  "links": [{"id": "link-selected-work", "label": "Explore selected work", "url": "#billing-work"}],
  "asset_slots": [{"id": "hero-visual", "kind": "theme_illustration", "optional": true}],
  "editorial_notes": ["Do not attribute the team-wide 25% result solely to Ajay.", "The measurement period and design decisions were not supplied; omit those details from public copy."]
}
```

The example deliberately omits unsupported design rationale and measurement period. It shows field-level bindings and a partial coverage ledger; a complete package also carries all entity dispositions, the closing action, lineage, restrictions applied, and compatibility/audit results. Section-local paths resolve relative to that section; root paths resolve from the package. This is a shape example, not a complete publishable fixture or public-writing quality benchmark.

### Content acceptance

- One hero, substantive evidence when available, and a coherent closing action. No mandatory projects for someone who has none. A minimal introduction with a meaningful destination can carry a `limited_content` review flag; if neither evidence nor a usable destination exists, return `needs_input` with one concrete request.
- Every factual public field, including metadata/alt text, binds to current permitted facts; metrics retain units and attribution. Resolve references and audit semantic support, since valid fact IDs can still accompany an unsupported paraphrase. Review notes and private facts never reach public copy.
- Section IDs and link IDs are unique; navigation is derived from sections present; every selected block is theme-compatible.
- A dense package remains readable. When excessive text cannot fit a supported design, shorten lower-priority repetitions or select a long-form component; never silently truncate a fact or paragraph.
- If an indispensable clarification is needed, emit a `clarification_request` for the host/Discovery to evaluate against the shared question budget and skip history. A skipped optional gap stays omitted; Content Architect cannot restart the interview. If essential material remains unavailable, return `needs_input` with a concrete reason.

Content Architect performs three logical operations: **plan sections and coverage; write complete copy; audit support, consistency, completeness, and theme compatibility**. Small inputs may combine planning/writing. Large inputs use bounded named-section batches with direct factual inputs and persisted completion records. The audit compares planned sections to finished copy, resolves links/assets, checks all coverage dispositions, and rejects placeholders or incomplete output. A detailed internal artifact can still yield a concise public page. See [the playbook](13-agent-operation-playbook.md) for the operation packets and project-writing rules.

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

A `SiteVersion/v1` records parent dossier/content/plan IDs, theme/hash, HTML hash, stylesheet hash, asset manifest, screenshot references, and verification receipt. The model emits only allowed variants and bindings. Initial generation uses one composition operation with at most one targeted correction before the tested default mapping. Mechanical edits may reuse the previous compatible plan. Expiring preview grants are issued separately; never persist them in public metadata or model input.

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

Each theme specifies semantic block types, variants, field slots, templates/classes, CSS hash, assets, responsive expectations, and HTML/JS capability version. Pin one shared theme for the first release. Future theme switching requires compatibility checks; arbitrary style edits are outside the current contract.

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
    "contact": ["connect-layout"],
    "narrative": ["narrative-flow"],
    "evidence_list": ["evidence-list"]
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

Every public field appears in its declared slot with the multiplicity specified by the template. A name can intentionally appear in both hero and footer; this must be declared rather than rejected as a duplicate. No public section/field is silently dropped. Require semantic structure, resolving anchors, allowed paths/classes, escaped text/attributes, supported URL schemes, no scripts/event handlers/forms/inline styles, and no review-only data. Browser verification gates promotion separately.

## 6. Context and model-call policy

- **Discovery:** one understanding call when the source is ready; question rounds only while material gaps remain. It can return the dossier in the first call. Otherwise use one dossier-finalization call after the last answer/skip. Persist answers after every user action. No repeated full extraction for a simple correction.
- **Content Architect:** planning, writing, and audit with bounded section batches when needed. Ordinary cases can combine planning/writing. Each writing/repair call receives relevant facts directly. Do not impose a small fixed call count that makes complete output impossible; configure per-operation/revision budgets and stop explicitly when they are exhausted.
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
3. Use the configured adapter's tokenizer or counting facility when available; otherwise use a conservative estimate and larger margin. Character counts are not exact token counts. Record estimation method and actual response usage. This policy does not mandate a particular provider API.
4. If Discovery source material does not fit, split it on section/page boundaries, carry the heading and source IDs into each chunk, extract facts per chunk, deduplicate repeated facts by source identity, and merge contradictions before a final dossier call. Never drop trailing pages. If a Content package does not fit, first remove repeated source excerpts and irrelevant history; if output itself is too large, use a bounded continuation over named sections and an integration check. Coding Engine gets only the compact manifest, never the whole stylesheet.
5. A refusal, truncated/incomplete output, schema failure, or semantic validation failure is a classified result. Do not parse a partial JSON body into a publishable artifact. Retry only the same immutable operation within its configured attempt limit or request the precise upstream correction. Changing the input shape, schema, or prompt creates a new operation fingerprint.

Structured Outputs improves shape reliability but still requires application validation for cross-references, factual grounding, and page completeness ([OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)). No hidden provider transcript is replayed wholesale across stages. Persist enough bounded call metadata to reproduce the packet from immutable artifact versions; the portfolio's user-facing edit history is separate from the model's prompt history.

Limits are configuration values, chosen from measured latency and failure data, not magic numbers in prompts. Transient provider failures can retry the same immutable operation within a small budget; semantic defects return a specific failure. The application records each attempt and never duplicates an uncertain successful write. Evaluation cases should be stage-specific and calibrated with human review, consistent with [OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

### Configured model capability gate

Use `config/models.toml` as the authority for provider, model, routing, and fallback policy. During future implementation, check that each selected profile supports its request parameters, output schema, context allowance, and timeout policy. Handle refusal, truncation, invalid output, authentication errors, and rate limits explicitly. A disabled optional transport does not mean the configured workflow requires migration to that transport. Fallbacks must be configured and recorded in the operation lineage; never silently change the factual or validation contract to accommodate a provider failure. No credential setup or live model run is part of this documentation task.

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
