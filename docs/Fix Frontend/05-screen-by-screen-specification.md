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

Primary: isolated preview theater with Desktop, Tablet, Mobile, Fit, route selection, focus mode, and open-in-new-window action.

Secondary: non-blocking warnings and explicit regeneration action only when server policy permits it. Clearly label verified versus candidate/unverified previews.

If the prior preparation approval succeeded but Generation start did not, show the approved preparation context and a separate `Start generation` action. Never replace this partial-success state with `Stage Locked`.

## Tablet and mobile

Tablet uses one column with a compact stage selector, in-flow context strip, route tabs, and reserved actions. Mobile uses a single readable stream, full-width controls, no permanent rails, and a full-screen/slide-over inspector. No content may require horizontal page scrolling.

## Administrator screen

The administrator screen is a separate `/admin` page, not another creator stage. Its detailed contract, server boundary, button matrix, confirmation flow, and responsive requirements live in [10-admin-console-specification.md](10-admin-console-specification.md). The creator screens only expose a quiet `Administration` link to accounts authorized by the server.
