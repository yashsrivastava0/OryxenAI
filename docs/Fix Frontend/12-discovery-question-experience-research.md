# Discovery Question Experience Research

This document is the focused handoff for the Discovery interview surface. It combines the supplied runtime screenshots, repository inspection, official form/accessibility guidance, and the visual direction required for the two new reference images.

The target is a guided editorial interview: one question, one clear answer mode, one honest reason for the question, and one obvious next action. It should feel considered and specific to the portfolio-building job without exposing prompts, JSON, worker details, or a developer rail.

## 1. Evidence boundary

The supplied screenshots are current-state evidence, not design references:

- [discovery-question-current-01.png](evidence/discovery-question-current-01.png)
- [discovery-question-current-02.png](evidence/discovery-question-current-02.png)

They show browser chrome, the Windows taskbar, an open administrator account menu, and a live Discovery question. The browser chrome/taskbar are outside the product. The open administrator menu is an interaction state that must not obstruct a creator question. It is retained only to document the safety/IA finding; the administrator experience remains a separate `/admin` surface.

The canonical audit remains the source of issue IDs and runtime measurements:

- [Discovery question audit image](../current-frontend-audit/evidence/screenshots/discovery/discovery-03-question-active.png)
- [scroll and layout metrics](../current-frontend-audit/evidence/measurements/scroll_and_layout_metrics.json)
- [issue register](../current-frontend-audit/03-issue-register.md)
- [accessibility findings](../current-frontend-audit/09-accessibility-interaction-findings.md)

The evidence images are deliberately copied without annotation or cropping. Generated visuals are implementation references only and must not be treated as production assets.

### Evidence copy integrity

The evidence files below are byte-for-byte copies of the supplied screenshots. SHA-256 is recorded so a later implementation pass can verify that the forensic baseline was not altered:

| Supplied screenshot | Pack copy | SHA-256 |
|---|---|---|
| `Screenshot 2026-09-13 181739.png` | [discovery-question-current-01.png](evidence/discovery-question-current-01.png) | `78B2C04301330828D644997F34EC0D181D84B21A31A94FE5260346D722366241` |
| `Screenshot 2026-09-13 191627.png` | [discovery-question-current-02.png](evidence/discovery-question-current-02.png) | `B0669343497A0011733CF1618309F786D9E25BF84D49FD896D66BEA76A1B493E` |

The generated references are intentionally normalized to the requested `1536×695` application viewport in their prompts; the image generator exported them at `1862×845` and `1864×844` respectively. Do not resize them as part of product implementation or treat their illustrative copy as API data.

## 2. Forensic findings

### 2.1 What the screenshots show

The current question view presents a long, model-shaped prompt in a wide empty canvas, then places three inline checkboxes on one line and a small blue button below them. The controls do not read as one answer group. The previous-answer disclosure, question ordinal, draft status, and source-material hint run together rather than forming a clear scan order.

The global stage navigator is visually weak while the question is active. The open account menu covers the upper-right content and makes the creator surface look like it is competing with an administrator surface. The large unused lower portion of the viewport makes the experience feel unfinished instead of intentionally calm.

### 2.2 What the source confirms

The current implementation is in [`ConversationSurface.tsx`](../../frontend/src/components/ConversationSurface.tsx):

| Finding | Source evidence | Consequence |
|---|---|---|
| Single-select choices are buttons | `single_select` maps each option to `.btn-choice` | No radio-group semantics; selection immediately submits in `handleSingleSelect` |
| Multi-select is inline | `multi_select` maps labels to `.checkbox-row` in `.checkbox-list` | Options lack a deliberate tile/list treatment and clear grouping hint |
| Text questions use a textarea | `text` renders `.composer-textarea` with the label `Your answer` | The semantic control exists, but the question surface does not provide strong hierarchy |
| Actions are local to the question body | `.question-actions` appears below the controls | Action placement and label vary by branch and are not reserved consistently |
| Prior answers use native details | `.prior-answers-accordion` wraps `<details>` | Useful secondary content, but its summary must stay compact and readable |
| The active card is broadly live | `.active-question-card` has `aria-live="polite"` | Polling or DOM changes can announce too much content; announcements should be transition-only |
| Question-specific styling is absent from the current CSS search | No matching selectors were found for `.question-prompt`, `.btn-choice`, `.checkbox-row`, `.question-actions`, or `.conversation-surface` under `frontend/src` styles | Native browser controls can show through, which explains the generic/basic appearance |

The adapter already recognizes the authoritative question kinds in [`discovery.ts`](../../frontend/src/data/adapters/discovery.ts): `text`, `single_select`, `multi_select`, and `boolean`. It exposes only option `id` and `label`; this pack does not invent option descriptions, question limits, or new backend fields.

The older behavior description says a single option submits immediately in [`docs/frontend-behavior-spec.md`](../frontend-behavior-spec.md). For this remediation, the explicit product decision is to keep a selection local until the user activates `Next question`. The implementing AI must follow this pack for the Discovery question surface and must not silently change the server answer payload.

### 2.3 Previous state to target state

| Current state | Target state |
|---|---|
| Long paragraph-like question and inline native controls | One concise prompt, one short contextual hint, one grouped answer surface |
| Single-select option click submits immediately | Native radio selection is reviewable; explicit `Next question` submits |
| Multi-select checkboxes run together on one line | Vertically stacked, full-row clickable checkbox tiles with selected state |
| Text input is visually generic | Labeled editorial composer with clear field boundary and preserved draft |
| Full question card in a live region | Small status region announces only a new question, save result, or failure |
| Stage navigator competes with the question | Navigator stays above and unobscured; question canvas owns the primary focus |
| Administrator menu can cover creator content | Creator menu stays quiet; administration is reached through the separate authorized surface |
| Blank lower viewport with no intentional dock | Reserved action dock creates a clear finish to the interaction without covering content |

## 3. Research findings and applied rules

The following external guidance is used as design input, not copied as a visual theme.

### 3.1 Question shape and copy

GOV.UK recommends asking one question per question page, making clear why the question is being asked, and allowing an “I do not know” or “I’m not sure” answer where valid.[^1] The OryxenAI application of that rule is one Discovery question at a time, with `helpText` used as a short reason or hint rather than a second paragraph of explanation.

Closed questions and a series of simple questions are generally easier to understand than a single complex open question.[^2] The agent may still ask a free-text question when the missing detail is genuinely narrative, but the question should request a bounded kind of answer and provide an example cue.

### 3.2 Choice controls

Use radios when exactly one option may be selected and checkboxes when one or more options may be selected.[^3] The visual treatment can be a larger clickable tile, but the implementation should keep native `<input>` and `<label>` semantics. The group should have a visible `legend`/heading and a concise hint such as `Select one` or `Select all that apply`.

Do not preselect an answer unless the product has a strong evidence-based reason. If a valid escape response exists, provide it as a real option such as `I’m not sure`, not as hidden behavior.[^3] The OryxenAI adapter remains responsible for the server-provided option set; the UI must not fabricate an escape option that was not returned by the agent.

### 3.3 Free-text answers

A textarea must have a visible label; placeholder copy is not a substitute because it disappears when the field receives focus.[^4] The label should be short and direct, while the hint can explain the kind of evidence that is useful. Do not render a numeric character count unless the server/product contract provides a real limit and there is a demonstrated reason to expose it.[^5]

### 3.4 Validation and recovery

Errors belong immediately after the question/hint and should be visually connected to the field or group. Existing values should remain in place so the person can edit rather than re-enter an answer.[^6] For a failed Discovery save, preserve the local text or selections, show a specific safe message, and keep a retry path. A service failure must not be presented as if the user entered invalid content.

### 3.5 Keyboard and status behavior

The W3C radio pattern places focus into the checked radio, or the first radio when none is selected; arrow keys move within the radio group, Space selects, and Tab leaves the group.[^7] A checkbox changes state with Space and must have an accessible label and group description when presented as a logical set.[^8] Prefer native controls so these behaviors are inherited and testable.

The question card itself should not be a constantly changing live region. W3C keyboard guidance treats Tab as movement between components and arrow keys as movement within composite widgets.[^9] WCAG 2.2 requires status messages to be programmatically determinable without forcing focus to the message, and the focus-not-obscured requirement makes the reserved action dock and sticky navigator important layout constraints.[^10]

## 4. Product interaction contract

### Shared question header

Every question state uses the same order:

1. compact stage context: `Discovery` and a short purpose;
2. progress: `Question {current} of {total}`;
3. optional compact earlier-answer disclosure;
4. one question prompt;
5. one `helpText`/reason line when provided;
6. the answer control;
7. reserved actions: primary answer submission and optional `Skip question`.

The question prompt is the heading for the answer group. Avoid repeating the same prompt as both a heading and a field legend where that would cause duplicate screen-reader output. The visible group label can be the prompt heading, and the fieldset legend can use the same accessible name only when the markup is structured to avoid double announcement.

### MCQ / multi-select

The supplied screenshot is a multi-select scenario. Its target representation is:

- a semantic `<fieldset>`/group;
- a visible prompt and a short `Select all that apply` hint;
- one vertically stacked option tile per server-provided option;
- native checkbox input inside each tile, visually aligned at the leading edge;
- a selected tile state with cobalt border/fill contrast and a non-color indicator;
- no inline run-on options and no custom checkbox role;
- selection changes local state only;
- primary action remains disabled until a valid selection exists, unless the server contract explicitly allows an empty answer;
- `Next question` submits the selected option IDs through the existing answer command;
- `Skip question` remains a separate secondary action when `allowSkip` is true.

For `single_select`, use the same tile geometry with native radio inputs and a `Select one` hint. The visual reference should show the multi-select case because it directly addresses the attached screenshot, while the documentation and tests cover both modes. Boolean questions use the single-select treatment with the server-provided Yes/No values.

### Free-text

The target representation is:

- a short conversational prompt;
- `helpText` as one or two lines of guidance;
- visible label `Your answer` above the textarea;
- an appropriately sized multiline field, not a raw prompt editor;
- an example placeholder that disappears without losing the label;
- existing safe draft persistence while typing;
- optional subtle saved-draft status, never a fake progress percentage;
- `Next question` when another server-returned question is available, otherwise `Submit answer`;
- `Skip question` as a separate secondary action when allowed.

The CTA label describes the answer operation. It must not claim to start the next agent or advance a production stage.

## 5. State matrix for implementation

| State | Visible treatment | Interaction |
|---|---|---|
| `input` / unanswered | prompt, hint, answer control, action dock | answer is editable; choices are local until Next |
| selected | selected tile/radio state; primary action enabled | user may change selection before submission |
| saving | preserve answer; stable button name such as `Next question`; adjacent `Saving answer…` status | disable duplicate submission; do not blank the field |
| save error | inline safe error, retained answer, retry-capable action | focus error or answer control according to browser test; no data loss |
| skipped | transition status and next server state | submit the existing skip payload; never send literal fake answer text |
| working | semantic Discovery worker surface | keep question controls out of the DOM if no question is available; stop/retry only when supported |
| stale/offline | last known question remains visible with connection notice | bounded retry/refresh; preserve local draft |
| unsupported | safe explanation and refresh path | fail closed; never guess that a question is complete |

## 6. Visual references

Because assets `13`, `14`, and `15` already exist in the dirty workspace as another contributor’s Code Generator references, the new Discovery images use the next unused indices:

- [16-discovery-mcq-question.png](visuals/16-discovery-mcq-question.png)
- [17-discovery-text-question.png](visuals/17-discovery-text-question.png)
- [exact prompts](visuals/prompts.md#16-discovery-mcq-questionpng)

Both images are horizontal UI references at an intended `1536×695` application viewport. They must show the product viewport only: no browser toolbar, taskbar, open account popover, administrator reset, raw JSON, external asset URLs, gradients, stock imagery, or invented backend fields.

### 16 — MCQ reference

Show a polished multi-select question with a compact unobscured stage navigator, Discovery context strip, `Question 02 of 04`, a short reason for asking, three readable vertical checkbox tiles, one or two selected states, a visible `Next question` action, and a quiet `Skip question` action. The lower action area must be reserved rather than floating over content.

### 17 — free-text reference

Show the same shell with a shorter question, `Your answer` above a spacious textarea, example placeholder, subtle draft status, visible `Next question`, and `Skip question`. Keep the field and actions above the fold at the intended desktop viewport.

These are reference images, not pixel-perfect requirements. Exact behavior, semantics, backend data, and responsive rules in this document and the parent pack take precedence.

## 7. Implementation routing

The implementing AI should inspect and, where appropriate, refactor:

- [`ConversationSurface.tsx`](../../frontend/src/components/ConversationSurface.tsx) for local selection, submit timing, focus, and status boundaries;
- [`DiscoveryStage.tsx`](../../frontend/src/stages/discovery/DiscoveryStage.tsx) for stage-level callbacks and error propagation;
- [`discovery.ts`](../../frontend/src/data/adapters/discovery.ts) for the pure server-to-VM boundary;
- [`shell.css`](../../frontend/src/styles/shell.css) for explicit question selectors and viewport-safe geometry;
- existing [`ActionDock.tsx`](../../frontend/src/components/ActionDock.tsx), [`AsyncActionButton.tsx`](../../frontend/src/components/AsyncActionButton.tsx), and [`ProgressSurface.tsx`](../../frontend/src/components/ProgressSurface.tsx) before adding duplicate abstractions.

No backend route or response field is required for this visual remediation. The existing answer endpoint, session revision, idempotency, ownership, and server-authoritative state remain unchanged.

## 8. Acceptance checklist for this surface

- A single-select click does not send a request before `Next question`.
- A multi-select user can select, deselect, review, and submit multiple option IDs.
- Radio and checkbox controls retain native label/group semantics.
- Text answers retain their value after a failed save.
- `Your answer` is a visible label, not only placeholder text.
- `Next question`, `Submit answer`, and `Skip question` are distinct accessible names.
- A new question produces one meaningful status announcement; polling does not reread the entire card.
- Focus is not hidden behind the sticky dock or stage navigator.
- The question action is reachable without a long scroll at desktop, tablet, and mobile target sizes.
- No page-level horizontal overflow occurs at `1536×695`, `1366×768`, `768×1024`, or `390×844`.
- The creator question surface contains no raw JSON or permanent administrator controls.
- Existing visual hashes remain unchanged; only the two new Discovery image files are added.

## Sources

[^1]: GOV.UK Design System, [Question pages](https://design-system.service.gov.uk/patterns/question-pages/).
[^2]: GOV.UK Service Manual, [Designing good questions](https://www.gov.uk/service-manual/design/designing-good-questions).
[^3]: GOV.UK Design System, [Radios](https://design-system.service.gov.uk/components/radios/) and [Checkboxes](https://design-system.service.gov.uk/components/checkboxes/).
[^4]: GOV.UK Design System, [Textarea](https://design-system.service.gov.uk/components/textarea/).
[^5]: GOV.UK Design System, [Character count](https://design-system.service.gov.uk/components/character-count/).
[^6]: GOV.UK Design System, [Error message](https://design-system.service.gov.uk/components/error-message/).
[^7]: W3C WAI-ARIA Authoring Practices Guide, [Radio Group Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/radio/).
[^8]: W3C WAI-ARIA Authoring Practices Guide, [Checkbox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/).
[^9]: W3C WAI-ARIA Authoring Practices Guide, [Developing a Keyboard Interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/).
[^10]: W3C, [Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/) and [Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum).
