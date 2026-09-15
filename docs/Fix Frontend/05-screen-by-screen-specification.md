# Screen-by-screen specification

The screen specifications below are authoritative for hierarchy and behavior. The visual references in `visuals/` show composition only.

## Control language used across screens

Inputs and actions are part of the specification, not decorative annotations. Every control must have a visible label, a keyboard name, a loading state, and a safe failure state.

- Discovery intake and answers use a labeled multiline input/composer. The input is for user-provided intent or an answer to the current question; it is not a raw model prompt editor.
- The intake CTA is `Start Discovery`.
- The question CTA is `Submit answer` or `Next question` depending on whether the next question has already been returned. It must not claim to advance an agent stage.
- Review CTAs name the destination agent: `Approve & continue to Content Architect`, `Approve & continue to Visual Design Director`, and `Approve & continue to Build Preparation`.
- Build Preparation uses `Continue to Generate`, which reveals the explicit Generation entry action; it does not silently auto-start Code Generator.
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

## Visual Design Director: review

Primary order:

1. creative thesis;
2. design-intent summary for color behavior, typography behavior, grid, motion, and interaction;
3. route selector;
4. visible scene storyboard for the selected page;
5. asset-brief treatment cards and adapted resource candidates.

Scenes are not hidden behind a single collapsed disclosure. Page-level detail, candidate rationale, and final JSON are secondary. Never fabricate color swatches, hex values, font names, or literal CSS tokens.

## Build Preparation: working

Primary: a four-step semantic progress surface: validating, researching, assembling, verifying.

Secondary: current milestone, elapsed/last-updated information, and stop/retry behavior when supported.

Do not show raw API requests, storage paths, or incomplete resource payloads.

## Build Preparation: ready

Primary: readiness summary with one status and compact counts for routes, sections, resources, and components.

Secondary: metadata-only evidence cards and two separate brief readers.

Evidence cards show title, purpose, provider/source, license, dimensions/aspect, and source link. They do not render external preview URLs as images under the self-only CSP. A neutral intent tile is used when there is no same-origin image.

The explicit Continue to Generate action is available in the action dock and/or the readiness summary without requiring a long scroll.

## Generation: available

When Build Preparation is approved, show a clear Generate Portfolio action. Do not show an unexplained Stage Locked dead end. If the user arrived early, show the exact prerequisite and a direct link back to Prepare.

## Generation: working

Primary: semantic milestones with the current milestone emphasized:

```text
Planning → Acquiring resources → Building pages → Testing viewports → Promoting preview
```

Use human-readable labels, not raw lowercase coordinator values. Show current activity, safe attempt information, last update, and Stop when supported. Do not invent percentages or ETAs.

## Generation: attention

Primary: concise failure summary and direct next action.

Secondary: preserved verified/candidate preview, safe technical reference disclosure, and refresh/support guidance when retry is unavailable.

The UI must stop polling, retain existing preview artifacts, and never display an endless working checklist after a terminal job failure.

## Generation: ready/preview

Primary: an isolated verified-preview theater with a truthful verification label, route selection only when route data exists, Fit to view, focus mode when supported, and an open-in-new-window action. The preview is the dominant artifact; the milestone history and instruction composer remain secondary.

Secondary: non-blocking warnings and explicit regeneration only when server policy permits it. Clearly label verified versus candidate/unverified previews. Do not render `Publish` or `Deploy` copy without a server-authoritative publishing contract; the current generation callback opens the preview and does not publish it.

The current implementation source is `frontend/src/stages/generation/GenerationStage.tsx`, and its data authority is `frontend/src/data/adapters/generation.ts`. Use [17-generation-ready-preview-research.md](17-generation-ready-preview-research.md) and [20-generation-ready-preview.png](visuals/20-generation-ready-preview.png) for the ready-state hierarchy.

If the prior preparation approval succeeded but Generation start did not, show the approved preparation context and a separate `Start generation` action. Never replace this partial-success state with `Stage Locked`.

## Tablet and mobile

Tablet uses one responsive column with a compact stage selector, in-flow context strip, preview theater before long activity/composer content, contained route controls, and reserved actions. This is a host-shell reflow requirement, not a dedicated tablet visual or a new preview-device API. Mobile uses a single readable stream, full-width controls, no permanent rails, and a full-screen/slide-over inspector. No content may require horizontal page scrolling.

## Administrator screen

The administrator screen is a separate `/admin` page, not another creator stage. Its detailed contract, server boundary, button matrix, confirmation flow, and responsive requirements live in [10-admin-console-specification.md](10-admin-console-specification.md). The creator screens only expose a quiet `Administration` link to accounts authorized by the server.
