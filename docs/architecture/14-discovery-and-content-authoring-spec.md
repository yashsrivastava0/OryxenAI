# Proposed Discovery and Content Architect operating specification

> **Status:** target architecture for review, not the behavior of the current API or product. This document defines the two agent handoffs in detail. Read it with the [artifact contracts](11-agent-and-artifact-contracts.md) and [generation mechanics](12-generation-preview-revisions-and-operations.md). It does not implement either agent.

## 1. Product path and ownership

The first planned intake is one freeform text box. A person may write a short request, paste a full resume, combine a goal with notes, or add professional details in any order. The application stores the exact text before interpreting it. A later attachment control may accept PDF and DOCX; those formats must be converted into the same source and span contract before Discovery runs. File upload, extraction, and OCR are not part of this first text-input slice.

```text
Freeform text and later answers
  -> complete DiscoveryDossier and readable report
  -> explicit Discovery approval
  -> complete PortfolioContent and readable copy review
  -> explicit Content Architect approval
  -> AI Code Generator writes index.html from approved copy and theme rules
  -> coordinator verifies the exact HTML + pinned styles.css bundle
  -> preview and revision
```

The application, not either agent, stores artifacts, checks revisions and approvals, and schedules the next job. Approval pins an exact artifact hash. A changed Discovery fact invalidates later content approval; changed content invalidates generated HTML. No stage consumes an unapproved draft as its authoritative parent.

The rule "do not miss a single user detail" applies to the **internal source and dossier**, including details that are redundant, unsuitable for a public page, or still disputed. Content Architect chooses what the public page says and records a disposition for every dossier item. This keeps a readable portfolio without losing the person's supplied history. A detailed report describes known facts, useful interpretation, and remaining gaps separately; lack of input never becomes permission to invent biography, metrics, contact details, or projects.

## 2. Discovery: build a complete understanding

### Intake interpretation and inventory

Discovery reads the original text, its stable source spans, the stated goal, later answers and skips, and accepted corrections. It first classifies text as information about the person, a desired target/job description, a writing or visual reference, an instruction or preference, a duplicate, or unclear material. A target employer's requirement is context for positioning, not evidence that the user has that skill. Template placeholders and pasted AI prose remain references until the user confirms a personal fact.

| Information to account for | Detail to preserve when supplied |
| --- | --- |
| Identity and direction | Display name, actual/current title, location, career transition, goal, target audience, desired visitor action, languages and preferred terms |
| Roles and chronology | Each organization and role, dates at the precision supplied, progression, responsibilities, scope, collaborators, tools, achievements and links to projects |
| Projects and work samples | Every item, problem and users, personal contribution, team contribution, decisions and reasons actually supplied, methods/tools, outputs, qualitative or measured outcome, attribution, proof and public link |
| Other evidence | Education, certifications, research, publications, talks, awards, open source, volunteering, leadership, client work, testimonials only when actually supplied, and unusual work evidence |
| Presentation choices | Requested emphasis, examples to feature or avoid, audience, tone, depth, ordering, preferred contact route, and exact wording to retain |
| Constraints and uncertainty | Explicit omit/generalize requests, contradictory values, unclear ownership, absent context, unsupported claims, skips, and details whose source role is uncertain |

Represent multi-claim sentences as separate facts when their support or ownership differs. Keep the exact original wording and all source occurrences, even if normalized records deduplicate a repeated fact. Do not add a month to a year-only date, change "helped" to "led," claim an organization-wide result as individual achievement, or infer expertise from a keyword. A source assertion and a direct user confirmation have different statuses; neither means external verification. Corrections supersede exact old fact revisions without erasing their history.

Every substantive span receives a traceable disposition: fact, intent/preference, restriction, reference context, duplicate, or excluded with a reason. There is no project or role quota in the canonical dossier. If a long paste exceeds a model packet, chunk at section boundaries, assign span IDs, merge all chunks, and require coverage of the final chunk before finalizing. Display limits and short summaries cannot truncate the stored inventory.

### Conversation policy

Ask only when an answer could materially change factual wording, the strongest story, the intended audience, what to feature, or the visitor action. Ask **zero** questions when the source already supports a useful report. Otherwise show a context sentence and **one, two, or three** related questions in a round, selected from actual gaps. Phrase them as a helpful conversation, with concise answer choices when the source suggests real alternatives, a free-text path, and a Skip action. Never force the person through a generic demographic form or ask them to restate what they pasted.

Each proposed question has a gap ID, affected fact/project IDs, a short reason, and an answerability check. Prioritize consequential identity or date conflicts, personal versus team contribution, a strong project's problem and approach, portfolio purpose/audience, proof of an important result, and a usable visitor action. Ask for a metric only when one was mentioned ambiguously or the user appears to have one; absence of a number by itself is not a gap that requires an interview.

| Context | Natural question | Why it helps |
| --- | --- | --- |
| Two roles point toward different audiences | "Your recent work covers both platform engineering and product features. Which should a visitor understand first?" | Changes the leading story |
| A project lists a team result | "For the billing rollout, which part did you handle, and was the 25% improvement measured for your piece or the wider team?" | Separates contribution from attribution |
| A work sample is promising but thin | "The dashboard looks worth showing. What problem was it meant to solve, and what did you decide to change?" | Supports a real case study |
| A nontechnical profile lists several kinds of work | "Your resume includes client relationships and campaign work. Which kind of opportunity should this portfolio help you attract?" | Uses the person's language, not engineering jargon |
| No contact route is supplied | "How would you like someone interested in your work to reach you? A link or email is fine, and you can skip this." | Gives the page an actionable ending |

Persist answers and skips before continuing. Ask once per distinct gap; do not rephrase a skipped question. A new answer can create a new material gap, so the conversation is adaptive rather than bound to two fixed rounds. A user can choose "continue with what I gave you" at any point. That closes optional questioning and preserves unresolved items. If the input is only "make me a portfolio" or otherwise lacks usable professional material, ask for one concrete starting source; after continued absence, return `needs_input` rather than inventing a person. If information is sufficient, acknowledge it briefly and move directly to the Discovery report for review, never past its approval gate.

### Authoritative output and review

`DiscoveryDossier/v1` contains source and answer lineage; identity; intent with the basis of each stated or defaulted choice; every role, project, skill and other evidence item; atomic facts with qualifiers, source refs, and individual/team/unknown ownership; explicit restrictions; question and skip history; contradictions and open items; user choices; and complete source coverage. Missing facts stay absent. A suggested editorial direction may be present as a clearly marked interpretation, never inside a factual field.

The readable Discovery report is a projection of the dossier, not a second competing source. It should cover: direction and success criteria; professional identity; complete experience and project inventory; individual contributions and team context; evidence and claim strength; skills and credentials; likely strongest stories; audience and visitor action; confirmed presentation preferences; conflicts, restrictions and unanswered gaps; and the precise choices the user is approving. It may be long when the source is rich. It does not pad sparse input with generic prose or final public copy. The UI can open with a short summary, but the full report and inventory remain inspectable and editable before approval.

Approval is allowed only when the accepted source is accounted for, the report and dossier agree, material conflicts are either resolved or explicitly constrained, and a meaningful Content Architect input remains. Approval stores the dossier/report version and hash. The Content Architect receives that **complete approved dossier**, not merely its summary or a capped project list.

## 3. Content Architect: write the complete public page

### Input and editorial decisions

Content Architect receives the exact approved dossier and its hash, global restrictions and open items, the user's stated goal/preferences, and the pinned theme's semantic component contract. It does not independently reinterpret a raw resume or interview the user. If a central fact is unsupported or contradictory, it requests one focused clarification through Discovery; an optional skipped gap stays a gap. The application checks that the dossier hash remains current before content is approved or sent downstream.

It decides the page's audience promise, professional positioning, evidence order, section selection, density, and primary visitor action. These are editorial decisions with short reasons and provenance: user confirmed, source derived, or safe default. A complete inventory does not imply an equally long public page. The content coverage ledger maps **every dossier fact and entity** to a public field, a faithful condensation, a retained internal item with a concrete relevance reason, an explicit restriction, or an unresolved gap. No item vanishes because a model call received only a summary or the first few projects.

### Finished copy contract

`PortfolioContent/v1` is one approved, single-page, renderable package. It includes ordered section IDs/types and navigation labels; all headings and person-specific words; hero introduction and CTA; grounded experience and project stories; capability and credential treatments when supported; closing/contact text; link and asset-slot IDs; document title and description; and captions or accessible labels needed by selected components. Internal editorial notes and coverage records are separate from public copy. Every factual public field binds to the exact current dossier fact revision, preserving ownership, date precision, units, qualifications, and restrictions.

| Source situation | Writing behavior |
| --- | --- |
| Rich project with context, contribution, approach and result | Write a full story with those distinct parts and the supported outcome attribution |
| Project has only name, tools and contribution | Use a concise honest project treatment; leave unknown problem, rationale and result out |
| Experience without a project | Tell a role or responsibility story from supplied scope and evidence rather than inventing a project |
| New graduate or career changer | Lead with supported academic, independent, volunteer or transferable work appropriate to the goal |
| No metric or proof link | Use specific qualitative facts if available; never fabricate a number or link |
| No public contact destination | Use a real internal action if meaningful; otherwise request a concrete destination rather than generating a fake one |

Plan coverage across the entire dossier before writing. Small cases may combine planning and writing; large ones use named section batches that each receive the exact relevant facts plus global choices/restrictions. Persist a completion map, then audit the integrated package for missing sections, wrong or exaggerated claims, stale revisions, broken references, duplicated filler, and theme incompatibility. No placeholder, outline, review note, or model instruction belongs in publishable copy. If the theme cannot express required approved content, return an exact component/field gap instead of dropping it.

The UI shows the complete proposed copy and its section order. The user can request a revision or edit it before explicit approval. Approval pins the exact package hash. Any subsequent Discovery correction invalidates this approval until the content is reconciled and approved again. The approved package is the Code Generator's sole **person-specific** input; the generator also receives system-owned theme rules and available assets.

## 4. Code Generator boundary and coordinator

The AI Code Generator writes a complete `index.html` using the approved `PortfolioContent`, the pinned theme manifest with permitted class names and markup examples, and available asset IDs. It may choose supported component variants and HTML structure. For a page too large for one model output, it may write named sections and a shell in bounded calls; the coordinator assembles those AI-written fragments in approved order and refuses an incomplete document. It must preserve approved wording, section order, links and factual meaning, and must not read the raw resume or Discovery dossier. The coordinator attaches the exact prebuilt `styles.css` and its assets; neither agent edits that stylesheet for an individual portfolio.

The Code Generator returns HTML plus a private map from approved section/field IDs to their intended DOM targets. The coordinator checks parseability, theme classes and required structure, exact approved field coverage after HTML decoding, allowed links and assets, unique IDs/navigation, missing or extra claims, and desktop/mobile browser behavior on the same versioned path the user will preview. A failed check names the owning field or component and permits bounded HTML repair against the same approved content. It cannot be "fixed" by deleting copy or silently changing CSS. Only a verified immutable bundle becomes the active preview.

Preview changes return to the earliest owner: factual corrections to Discovery, wording/emphasis/section changes to Content Architect, and supported layout changes to Code Generator. A new approval is required for any upstream artifact that changes. A late worker or stale candidate cannot replace a newer approved version.

## 5. Acceptance examples for the later implementation

| Scenario | Required result |
| --- | --- |
| A long pasted resume ends with an important project | The project and its source span remain in the dossier and content coverage ledger |
| The paste mixes resume text, a target job ad, and a sample portfolio | Discovery records their different roles; job requirements and sample claims do not become personal facts |
| Two dates or titles conflict | Ask once when consequential; otherwise preserve both and avoid disputed public precision |
| A user says "we increased revenue" | Preserve team attribution; ask what the user did before assigning personal credit |
| One, two, or three material gaps exist | Ask that many tailored questions together, each with a reason, free text and Skip |
| The input is already rich | Ask no questions, acknowledge sufficient context, and show the complete report for approval |
| A user skips or says to continue | Retain the gap and stop asking about it; write from known facts where possible |
| Input remains only a generic request | Return one concrete `needs_input` request; do not invent a career history |
| A project lacks an outcome or metric | Use supported contribution and context; no fabricated result or generic filler |
| Many roles, projects or duplicate mentions exist | Preserve every source detail and occurrence; deduplicate normalized facts without deleting references |
| A fact is excluded from the public page | Keep it in the dossier and record Content Architect's disposition and reason |
| The user edits a name after Discovery approval | Create a new dossier version; stale content and HTML approvals cannot be reused |
| Approved copy exceeds a supported visual component | Choose a compatible long variant or return a precise content/theme gap; never silently truncate |
| Generated HTML changes or drops approved copy | Reject the candidate and repair HTML against the same approved package |

These are contract and behavior examples for future implementation. This documentation task does not run the model workflow or change the active product.
