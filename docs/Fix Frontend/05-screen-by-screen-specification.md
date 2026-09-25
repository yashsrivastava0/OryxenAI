# Screen-by-screen specification

The screen specifications below are authoritative for hierarchy and behavior. The visual references in `visuals/` show composition only.

## Control language used across screens

Inputs and actions are part of the specification, not decorative annotations. Every control must have a visible label, a keyboard name, a loading state, and a safe failure state.

- Discovery intake and answers use a labeled multiline input/composer. The input is for user-provided intent or an answer to the current question; it is not a raw model prompt editor.
- The intake CTA is `Start Discovery`.
- The question CTA is `Submit answer` or `Next question` depending on whether the next question has already been returned. It must not claim to advance an agent stage.
- A `Revise` action reveals a short revision composer with a label such as `What should change?`, preserves the current artifact, and submits through the existing revision endpoint.
- A disabled or loading button keeps its label and exposes progress through adjacent status text; it must never collapse to an unlabeled icon.

## Discovery: intake

Primary: one focused intake field with a clear purpose sentence and a single Start Discovery action.

Secondary: optional prompt examples below the field; no developer output, raw JSON, or oversized empty rail.

Behavior:

- fit the primary field, validation message, and CTA within the short desktop viewport;
- show bounded character/word feedback without creating a second panel;
- preserve input locally only through the existing safe session behavior;
- show clear validation for empty or oversized input;
- when starting, move to working with an honest milestone message.

Input contract:

- label: `What should this portfolio make clear?`;
- multiline field with a concise example placeholder, not a raw JSON or prompt field;
- submit: `Start Discovery`;
- validation: empty, over-limit, and unavailable-session states are shown inline next to the field;
- after submit, preserve the input through the existing session state and replace the composer with the working surface.

## Discovery: questioning

Primary: one question at a time with its answer control.

Secondary: compact progress “Question 1 of N”, answered-turn summary, and stop/retry control when applicable.

Do not place the step navigator behind the question card. Do not expose raw agent envelopes. Use a single transition-based status announcement when a new question arrives.

Answer contract:

- show one labeled answer field, `Your answer`;
- keep `Submit answer` visible without scrolling past the question;
- show `Next question` only after the server has returned the next question and the user is moving through an already-saved answer;
- on failed save, retain the typed answer and show `We couldn't save that answer. Try again.` with a retry action.

## Discovery: brief review

Primary: brief summary and profile facts that let the user judge whether the narrative is accurate.

Secondary: full Markdown brief in a collapsed reader/drawer; revision composer.

The title is compact and readable. The approval dock is visible immediately and remains available while the full brief is inspected. The user can approve, revise, or leave without losing the durable state.

The revision composer is initially compact or closed. When opened, it must contain one labeled multiline field (`What should change?`), a `Send revision` action, and a `Cancel` action. Approval remains visible in the reserved action dock while the composer is open.

## Discovery: question experience addendum

This section is authoritative for the Discovery question composer and supersedes older wording that submits a single-select option immediately.

Shared question layout:

- keep the stage navigator unobscured above the question canvas;
- show a compact `Question {current} of {total}` indicator and, when present, a collapsed `Earlier answers` disclosure;
- show one question prompt as the primary heading;
- place `helpText` immediately below the prompt as a short reason or answering hint;
- render the answer control in a readable single column;
- reserve the action area so the primary action is visible without a long scroll.

MCQ/multi-select:

- use native checkbox inputs for `multi_select`, one per server-provided option;
- wrap each input and label in a full-row selectable tile; do not render options inline;
- selection is local until the user presses `Next question`;
- allow selection changes before submission and support one or more selected values;
- use `Select all that apply` only as a hint when it accurately describes the server-provided question;
- keep `Skip question` separate and visible when `allowSkip` is true.

Single-select and boolean:

- use native radio inputs for `single_select` and the same tile geometry as multi-select;
- show `Select one` when the question needs that instruction;
- do not auto-submit when a radio is selected;
- submit the selected value only from the explicit `Next question` action.

Free-text:

- use the existing `text` kind and a visible `Your answer` label above a multiline textarea;
- use `helpText` or a short example placeholder as supplemental guidance, never as the label;
- preserve the existing safe draft behavior;
- do not show a numeric character count unless a real limit is returned by the product contract;
- use `Next question` when another question is already available and `Submit answer` only when the current server state requires final submission.

Save failure:

- retain the typed text or selected values;
- show a safe inline error associated with the field/group;
- keep a retry-capable action and never imply that the next question was reached;
- announce the transition once through the small status region, not by making the whole card live.

See [12-discovery-question-experience-research.md](12-discovery-question-experience-research.md) and the separate visual references [16](visuals/16-discovery-mcq-question.png) and [17](visuals/17-discovery-text-question.png).

## Content Architect: review

Primary order:

1. site narrative thesis and value proposition;
2. route map showing every planned route;
3. route tabs or selector;
4. selected route's section cards with title, role, and actual copy;
5. unresolved issues or decision basis only when non-empty.

Only the selected route is expanded. Other routes remain compact but selectable. Title and body fields must not duplicate identical text. The action dock remains visible for approval and revision.

Content Architect approval is the terminal state of the active workflow.

## Tablet and mobile

Tablet uses one responsive column with a compact stage selector, in-flow context strip, contained route controls, and reserved actions. Mobile uses a single readable stream, full-width controls, no permanent rails, and a full-screen/slide-over inspector. No content may require horizontal page scrolling.

## Administrator screen

The administrator screen is a separate `/admin` page, not another creator stage. Its detailed contract, server boundary, button matrix, confirmation flow, and responsive requirements live in [10-admin-console-specification.md](10-admin-console-specification.md). The creator screens only expose a quiet `Administration` link to accounts authorized by the server.
