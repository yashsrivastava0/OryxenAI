# Proposed agent operation playbook

> **Status:** research and review only, 2026-09-29. These are proposed responsibilities and contracts, not implemented code. Review this design before starting implementation. [Architecture index](README.md) · [Artifact schemas](11-agent-and-artifact-contracts.md) · [Runtime and repair](12-generation-preview-revisions-and-operations.md).

## 1. The three agents and the software around them

| Owner | The question it answers | Authoritative output | What completes the stage |
| --- | --- | --- | --- |
| Intake service | What exactly did the user submit, and what could be read? | Immutable sources, extraction spans, intent/answer events | Every accepted input has an explicit extraction disposition |
| Discovery | What do we know about this person, what do they want, and what remains uncertain? | Complete `DiscoveryDossier` | Facts, evidence, restrictions, conflicts, skips, and source coverage pass their checks |
| Content Architect | What should this portfolio say, in what order, for this audience? | Complete `PortfolioContent` | Every selected section has finished public copy, evidence bindings, and coverage dispositions |
| Code Generator / Coding Engine | Which supported composition fits that exact copy? | Constrained `RenderPlan` | All sections/fields bind to compatible variants/assets; no copy changes |
| Trusted renderer | What are the exact HTML bytes for this plan and theme? | `index.html` and sealed bundle manifest | Escaping, links, structure, theme, and asset checks pass |
| Verifier and orchestrator | May these exact bytes become the current preview? | Receipt and fenced activation | Required checks pass and the revision/worker/authorization still match |

“Agent” describes ownership of reasoning and structured output. It does not mean an autonomous process that can call other agents, write database transactions, browse arbitrary links, install packages, or publish content. Host application code supplies the inputs and validates the results.

```mermaid
flowchart LR
    S[Sources and answers] --> D[Discovery dossier]
    D --> C[Complete content package]
    C --> G[Supported render plan]
    G --> H[Trusted HTML renderer]
    T[Pinned theme] --> C
    T --> G
    T --> H
```

Text equivalent: source evidence → factual dossier → finished public content → supported composition → generated HTML. Content Architect receives semantic theme capabilities; composition receives variant/slot capabilities; the renderer receives actual templates and CSS/assets.

### Common operation envelope

The host assembles an immutable packet containing:

- Session/portfolio ID, pipeline version, desired revision, operation ID, and authorized attempt.
- Parent artifact IDs and hashes, schema/prompt/configuration versions, and theme capability version where relevant.
- The operation's direct factual/content inputs, including exact relevant source spans.
- User intent, privacy restrictions, accepted correction events, and the allowed change scope.
- Required output contract, remaining budgets, and structured issues when repairing.

The output is one tagged result: completed artifact, questions/clarification, `needs_input`, or a classified failure. Internal validated batches are explicitly partial. They cannot be consumed as a completed stage. The host owns timestamps, IDs/hashes, storage, validation receipts, job scheduling, and compact UI projections.

## 2. Intake: establish trustworthy boundaries

### Work sequence

1. Authorize the existing portfolio session and record the request/idempotency key.
2. Store the original file or pasted text immutably. Keep source role separate from the extracted words.
3. Parse within configured file/decompression/time/memory limits. Keep useful paragraph/page locations and an unchanged text snapshot alongside normalized working text.
4. Record extraction diagnostics. Multiple columns, repeated headers, tables, blank pages, and image-only pages need explicit accounting.
5. Accept readable text, ask for replacement/paste, or let the user explicitly continue with a known readable subset. Keep excluded/uncertain portions visible in the source record.
6. Commit source references and schedule Discovery only for admitted material. A failed upload does not become an empty resume.

For v1, support readable PDF/DOCX/TXT and pasted text. OCR is deferred. Do not promise perfect document structure recovery; [pypdf explains the limitations](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

### Source roles and trust

| Role | May support personal claims? | Use |
| --- | --- | --- |
| Professional details/resume | Yes, as `source_asserted` | Facts about work, education, projects, links |
| Direct answer/correction | Yes, as `user_confirmed` when unambiguous | Clarify or supersede an earlier value |
| Job description | No | Audience/positioning goals and relevant emphasis |
| Writing/visual reference | No | Tone or presentation preferences |
| Explicit restriction | Controls publication | Omit/generalize selected facts, contacts, organizations, or projects |
| Embedded instruction inside a resume | No operational authority | Preserve as source text; never override agent/system contracts |

Do not fetch a supplied project URL just to make generation work. A link can be syntactically valid without being externally verified. If URL import becomes a feature, it produces a separate source artifact before Discovery.

## 3. Discovery: complete factual understanding

### 3.1 Inventory before interview

Discovery first accounts for the supplied material. Extract identities, roles, organizations, dates, responsibilities, projects, technologies, outcomes, education, publications, awards, volunteering, and unusual professional evidence. There is no maximum project count in the canonical inventory.

Separate a sentence containing several claims into atomic facts when that helps verification. For “Built the queue consumer for a rollout that reduced processing time by 25%,” contribution, rollout membership, measured result, units, and ownership are distinct concerns. Preserve original wording and qualifiers. Do not turn a year into a full date, a team result into individual credit, a skill mention into mastery, or “helped” into “led.”

Attach a disposition to every substantive extracted span: fact(s), intent, restriction, reference context, duplicate, or excluded with reason. Duplicate sources retain their references. A coverage ledger with no missing IDs detects one class of omission; it does not prove that every fact was interpreted correctly. Representative human-reviewed cases remain necessary.

### 3.2 Decide which questions materially help

Question selection follows impact, not a fixed form. Prioritize contradictions affecting identity/dates, personal ownership, portfolio purpose, featured evidence, and visitor action. Ask up to three concise questions in a turn and at most two rounds by the proposed defaults. Ask none when evidence is sufficient.

| Trigger in the actual material | Example question | If skipped |
| --- | --- | --- |
| Audience changes which work leads | “Should this mainly attract employers, clients, or research collaborators?” | Use a conservative stated default and record its basis |
| Project contribution is unclear | “Which parts did you personally handle?” | Describe supported participation without invented ownership |
| Outcome may belong to a team | “Was this result for your contribution or the wider team?” | Preserve unknown attribution; omit the result if safe wording is impossible |
| Sources give different dates | “These sources show different end dates. Which should I use?” | Omit the disputed precision; keep conflict recorded |
| Strong project has no context | “What problem did this project solve, and who used it?” | Use only supplied project context; allow a compact treatment |
| Several equally strong directions | “Which of these projects should visitors notice first?” | Choose an evidence-based ordering and mark it as an editorial default |
| No useful visitor action | “What should an interested visitor do next?” | Use a real supplied destination or an existing evidence anchor |

Questions cite gap/entity/source IDs internally and include a short user-readable reason. A question-set ID binds answers to the exact draft. Persist answers and skips before continuation; stale answer submissions receive a conflict. “Continue with available details” closes the interview rather than generating another differently worded request for the same missing metric.

If a skipped gap blocks only one claim, omit that claim. If nothing meaningful can be produced, return `needs_input` with one concrete request. Do not invent a professional identity or fictional contact destination to produce a nominal success.

### 3.3 Reconcile and finalize

Use explicit corrections to supersede earlier fact versions. Conflicting resumes do not get an automatic newest-file winner. Keep unresolved conflicts as conflicts and restrictions attached to the exact facts/entities they cover. Never promote an inferred audience preference into a user-confirmed fact.

The final dossier must include all groups in the [contract](11-agent-and-artifact-contracts.md): lineage, identity, intent/basis, complete experience/projects, other evidence, atomic facts, restrictions, gaps/conflicts/skips, and source coverage. Its readable Markdown view can be extensive. Its frontend card may show a short direction summary, source count, unresolved questions, and an expandable details action. Both views are projections of the same validated dossier.

### 3.4 Large dossiers and factual revisions

For long inputs, extract bounded source chunks with stable span IDs, persist validated chunk outputs, then merge facts and check conflicts globally. A chunk has an explicit range and completion marker. Finalization requires all admitted chunks accounted for; the last page is never discarded to make a request fit.

For a name/date/contribution correction, load the relevant fact revisions and evidence plus current global restrictions. Reconcile the change into a new complete dossier version. Unaffected facts retain IDs and provenance. Downstream consumers receive that exact new dossier, never a short “name changed” message as their only factual base.

## 4. Content Architect: full editorial planning and writing

### 4.1 What it receives

Content Architect receives the complete dossier as its logical input, the user's goal/preferences, and the pinned theme's semantic capability contract. The contract describes hero, introduction, project, experience, capabilities, credentials, generic narrative/list, and contact blocks; required/optional fields; density options; native interactions; and limitations.

Do not routinely send raw `styles.css`. CSS is useful to the renderer/theme engineer; it does not tell the writer which fields are required or which claims are allowed. Source excerpts are attached when an ambiguous/sensitive statement needs checking. On revision, include the current content package, ordered edit events, affected targets, and all still-applicable restrictions/corrections.

“Complete input” does not require one enormous model call. The host retains the full dossier and supplies a complete section-specific subset to each writing call, with global intent/restrictions and cross-section entity references. Coverage planning must account for the entire inventory; no lossy summary substitutes for the facts used to write a section.

### 4.2 Operation A: plan story and evidence coverage

Produce a section plan with stable IDs, semantic types, purpose, order, navigation intent, supporting entities/facts, and a brief decision reason. Define the audience, professional positioning, strongest supported evidence, desired visitor action, and tone. Decision reasons should be concise editorial explanations, not hidden reasoning transcripts.

Map every relevant fact/entity to a planned use or explicit disposition:

| Disposition | Required record |
| --- | --- |
| Used | Section/field destinations and supporting fact revision |
| Condensed | Destination and how qualifications/meaning are preserved |
| Retained internally | Reason it is not necessary for this public page |
| Excluded by restriction | Exact applicable restriction/event |
| Excluded editorially | Concrete relevance/redundancy reason; entity remains recoverable |
| Unresolved | Gap/conflict ID and affected claim omitted or constrained |

A new graduate may lead with coursework/projects; an experienced operator with responsibilities and results; a researcher with publications. No fixed quota requires all profiles to invent three projects, metrics, employers, awards, or testimonials. A generic narrative/list block preserves unusual material when a specialized block would distort it.

### 4.3 Operation B: write complete sections

Each writing packet contains the section plan, exact current facts with original qualifiers, relevant evidence excerpts, link/asset records, supported block fields, global restrictions, and required output paths. The writer must not rely on an earlier strategy paragraph to remember the factual record.

For ordinary portfolios, planning/writing can be combined. For long portfolios, persist validated named-section batches. Maintain a completion map of expected versus completed section IDs. An interrupted or truncated batch remains incomplete; retry only the missing/invalid work within budget, then audit the integrated package.

#### Project narrative contract

| Public field | Writing rule |
| --- | --- |
| Title | Supplied name or conservative descriptive title; no invented product brand |
| Context/problem | Explain what the source supports about purpose/users/problem |
| Contribution | Preserve individual/team role and degree of ownership |
| Approach/decisions | Describe supplied actions/reasons; do not invent why a technology was chosen |
| Outcome | Use supported qualitative/quantitative result, exact scope/units, and attribution; optional when absent |
| Technologies | Use supplied tools in their correct relationship to the project |
| Proof links | Refer only to existing validated canonical links |
| Missing/omitted fields | Internal reason and gap/fact IDs; no “not provided” filler on the public page |

“Detailed” means complete useful supported copy with clear evidence relationships. It does not mean stretching one bullet into an invented case study. If only title, contribution, and tools exist, use a compact project treatment. If contribution is also unknown, use a supported generic evidence item instead of filling a required project field with a guess.

Experience preserves role/employer/date precision, supported scope, and achievements. Capability groups use supported skills/examples without mastery ratings. Metadata, navigation labels, captions, alt text, CTA labels, and contact copy are part of the finished package; Code Generator must never invent them later.

### 4.4 Operation C: audit the integrated content

Run mechanical checks first, then a scoped semantic support audit where needed:

1. **Completion:** every selected section and required field has finished copy; no outline-only sections or placeholder prose.
2. **Lineage:** the package references the exact current dossier/theme-capability version.
3. **References:** all claims, links, assets, sections, and navigation targets resolve.
4. **Support:** each factual public field is supported by the cited facts, including subject, ownership, modality, scope, chronology, metrics, and qualifications. A valid fact ID with an exaggerated sentence fails.
5. **Restrictions:** check body copy, metadata, accessible text, link destinations, and asset labels. User-requested omission overrides an editorial preference to feature impressive evidence.
6. **Coverage:** every relevant fact/entity has a disposition; no source project disappeared because a writing call got only the first few items.
7. **Consistency:** names, pronouns if supplied, terminology, dates, and corrections agree across sections/metadata.
8. **Compatibility:** every field can be rendered using the pinned semantic capabilities without forced truncation.

Unsupported claims return precise fields and evidence to the writer. Incorrect facts return to Discovery. A shared component gap is a capability failure, not permission to delete the section. The host integrates validated copy into one `PortfolioContent`; the reader-facing summary might show emphasis, ordered sections, and a short excerpt, while the complete artifact remains expandable.

### 4.5 What the next stage must be able to assume

The content package has finished personalized words, unambiguous section IDs/order, current canonical links/assets, complete factual bindings, coverage, and internal review findings. The coding stage should be able to render it without asking “What should this person's biography or result say?” That question belongs here and must be resolved before handoff.

## 5. Code Generator: composition, then trusted serialization

### Model-owned composition

Load the exact content package and a compact manifest of compatible variants/slots and approved assets. Select variants based on content shape: long names, amount of project detail, timeline availability, number of items, and whether a visual exists. Return only theme/section/variant/asset IDs and allowed bindings.

The plan must cover every public field and section. It cannot add or rewrite words, omit sections, invent an image/link, generate classes, or add CSS/JavaScript. Editorial order remains Content Architect's responsibility. Reordering a section is a content-structure revision, not a hidden layout decision.

If the plan is invalid, provide exact enum/slot/compatibility failures for one bounded correction. Then use the theme's tested default mapping when it preserves the whole package. An incompatible theme fails explicitly. A factual typo edit can reuse its old compatible plan without another model call.

### Host-owned rendering

The renderer loads pinned trusted templates, escapes text/attributes, validates URLs, derives unique anchors/navigation, serializes metadata/landmarks/sections, and links exact shared CSS/assets. It produces one complete `index.html`. There is no user-specific package installation, framework build, generated server, or stylesheet generation.

The bundle contains only public HTML, shared CSS, and approved referenced assets. Internal facts, source resumes, prompts, summaries, review notes, and repair transcripts are not copied into HTML comments, JSON data attributes, or metadata. A field-to-DOM map used by verification is a private diagnostic artifact unless a specific public attribute is explicitly designed and safe.

Fixed CSS works only when the theme includes responsive templates for sparse and dense content. Build missing project, experience, credentials, and generic blocks once, with image-free fallbacks and locally packaged fonts. A shared defect requires a new reviewed theme version. A model must not patch a private stylesheet to hide it.

## 6. Handoffs, compact UI, and repair ownership

| Handoff | Consumer receives | Gate before it proceeds | Compact UI |
| --- | --- | --- | --- |
| Intake → Discovery | All admitted source/version refs, spans, roles, intent/events | Extraction accounted for; no silent truncation | Received files and actionable read problems |
| Discovery → Content | Complete dossier, restrictions, conflicts/skips, theme capabilities | Provenance/coverage/identity/current revision | Understood direction and useful questions |
| Content → Composition | Complete public copy plus semantic types/order and approved refs | Support, coverage, completeness, compatibility | Emphasis, section outline, short excerpt |
| Composition → Renderer | Valid plan, exact content/theme/assets | Supported variants and complete field binding | Building page |
| Renderer → Verifier | Sealed bundle and private expected-binding map | Hashes/readback/HTML constraints | Checking page |
| Verifier → Promotion | Receipt bound to exact bytes and versions | Passing required checks, current authorized attempt/revision | Ready preview or actionable failure |

UI projections use bounded excerpts and counts from validated artifacts, not a separate model-written factual story. Full-detail panels paginate/collapse by source/entity/section as needed; a frontend list limit never limits the stored dossier. Users review the actual finished portfolio first and use details when useful.

```mermaid
flowchart TD
    V[Validate artifact or candidate] --> R{Required checks pass?}
    R -->|Yes| N[Next stage or fenced activation]
    R -->|No| O[Classify failure and owner]
    O --> B{Repair budget and valid scope?}
    B -->|Yes| F[Targeted repair or infrastructure retry]
    F --> V
    B -->|No| E[Actionable state; keep active preview]
```

Text equivalent: check → pass to next stage, or classify → scoped repair within budget → check again. Stop on exhausted/no-progress/shared engineering defects. A changed content artifact invalidates downstream checks. A browser process retry against unchanged bytes reuses the content and bundle. Detailed budgets and failure classes live in the [runtime repair policy](12-generation-preview-revisions-and-operations.md#repair-policy).

## 7. Worked example: initial generation and corrections

This is fictional illustrative material, not information about the user.

### Initial source

The resume says “Ajay Mehta, Backend Engineer,” mentions a billing rollout with a 25% processing-time reduction, and lists a queue consumer contribution. A job description also mentions Kubernetes; the resume does not.

1. Intake preserves the resume and job description as different source roles.
2. Discovery records the name/title, contribution, and rollout result with source refs. It does not add Kubernetes to the person's skills. It asks about result ownership because the wording is ambiguous.
3. The answer says, “I redesigned the queue consumer; the reduction was for the team's rollout.” This becomes an immutable answer event. Contribution is individual; result attribution is team; baseline and measurement period remain unknown.
4. Content Architect may write “I redesigned the queue consumer for the billing rollout. The team's rollout reduced processing time by 25%.” Each factual field binds to the relevant facts. It omits an invented baseline or technology-choice rationale and records the gaps internally.
5. Composition selects a compact supported project variant. The host renders HTML, checks assets/layout/navigation, seals and verifies the candidate, then activates it under the current revision.

### “My name is Akash, and make the introduction less formal”

Persist one request with factual and editorial sub-actions. Discovery creates a corrected name fact revision; the earlier name is superseded, not erased from history. Content Architect updates every mapped personalized name field, metadata, and affected prose, then changes the introduction tone using the corrected dossier. Audit checks all identity-bearing fields. Reuse the compatible composition, rebuild HTML, verify, and activate. Shared CSS bytes remain identical.

### A second request arrives before completion

The user says “Hide the billing result.” If the expected revision matches the latest accepted intent, append the new instruction and supersede the in-flight candidate for promotion. The next candidate applies the name correction, tone change, and hiding instruction in order. If the message came from a stale tab, return a conflict and current intent summary instead of silently accepting an ambiguous base.

```mermaid
sequenceDiagram
    actor User
    participant API
    participant Ledger
    participant Worker
    User->>API: Correct name and tone, expected revision
    API->>Ledger: Append accepted event and enqueue
    User->>API: Hide result, latest expected revision
    API->>Ledger: Append event; supersede older candidate
    Worker->>Ledger: Load stable base and all unapplied events
    Worker->>Worker: Reconcile, write, render, verify
    Worker->>Ledger: Activate only at current event watermark
```

The old working preview stays available until a valid current candidate passes. If verification fails, report the failure beside it. A later rewrite reads the corrected dossier and restrictions, so the old name/result cannot return merely because the original resume still contains them.

## 8. Acceptance scenarios for future implementation

These are proposed acceptance criteria, not tests implemented or run by this documentation change.

| Scenario | Required result |
| --- | --- |
| Important fact near the end of a long resume | Preserved in dossier and accounted for in content coverage |
| Many roles/projects | Complete internal inventory; public selection recorded explicitly |
| Missing metric/outcome | Omit unsupported outcome; no invented number or success claim |
| Team result and individual contribution | Preserve separate ownership and scope |
| Resume plus target job description | Target requirements never become personal achievements |
| Private employer/contact/result | Absent from public copy, metadata, labels, and bundle |
| Scanned/encrypted/corrupt/partial document | Preserve original; explain paste/replacement or explicit readable-subset choice |
| Long international name/title and dense project copy | Full text remains readable in supported mobile/tablet/desktop layouts |
| Valid JSON with unsupported claim | Content support audit routes exact field/evidence for repair |
| Truncated model output | Incomplete state; resume named missing work or fail within budget |
| Name correction followed by tone rewrite | Corrected identity survives every affected field and metadata |
| Two accepted edits during a build | Ordered events preserved; candidate applies both |
| Late stale worker or recovered lease | Cannot commit as current or promote |
| Crash after stage completion | Persisted artifact and queued handoff resume idempotently |
| CSS/font/image missing or wrong hash | Candidate never marked ready |
| Browser process crash | Bounded verification retry using the same sealed bytes |
| Repair budget exhausted | Actionable failure; accepted request and last verified version retained |
| Iframe and standalone preview | Same version, correct headers, working relative asset authorization |
| Preview grant expires | Owner refresh/reload path; no content regeneration |
| Restore older version and edit | Selected dossier/content/plan become the base; current privacy restrictions still apply |
| Arbitrary styling request | Explain deferred capability; preserve shared CSS |
| User cancels while model call runs | Late response cannot activate; current working preview remains |

Future deterministic fixtures should cover these mechanics. Factual fidelity, editorial quality, and visual acceptance also need representative human-reviewed portfolios. Live model evaluations require explicit authorization. The architecture makes failures traceable and bounded; it does not establish a guarantee that all possible errors have been eliminated.

## 9. Review decisions and next step

The proposed defaults are automatic progression after useful clarification, review primarily after generation, one shared versioned theme, complete internal artifacts with compact UI projections, native single-page interactions, and content edits that rebuild only personalized HTML. Models and resource limits remain configuration-driven. Publishing, OCR, per-user style generation, custom JavaScript, and multi-page output are future capabilities.

The next step is the user's architecture review. After a separate implementation request, follow the [implementation slices](README.md#recommended-implementation-slices), beginning with the reusable theme and canonical artifact contracts. This proposal itself creates no agents, APIs, migrations, tests, or deployment changes.
