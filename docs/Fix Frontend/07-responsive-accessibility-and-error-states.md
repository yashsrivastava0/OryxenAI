# Responsive, accessibility, and error-state rules

## Viewport behavior

### Desktop: 1200px and above

- one centered stage canvas;
- compact full stage navigator;
- context strip in normal flow;
- ActionDock visible and reserved;
- Output Inspector opens as a drawer without shrinking the canvas;
- main prose measure approximately 36–56rem;
- route/scene/evidence grids may use two columns only when the content relationship is meaningful.

### Tablet: 768px–1199px

- single-column stage canvas;
- compact horizontal stage selector;
- context facts wrap without creating a second rail;
- route tabs scroll inside their own strip, never the page;
- action dock remains visible and reserved;
- secondary readers remain collapsed by default.

### Mobile: 390px–767px

- compact topbar and current-stage selector;
- one-column artifact stream;
- full-width actions, stacked in priority order;
- inspect/debug output opens full-screen or as a slide-over;
- preview theater fits the viewport and exposes device controls without overflow;
- no decorative label or registration mark may create page overflow.

## Keyboard and focus

- The skip link targets the current stage.
- Stage navigation uses buttons/links with visible focus rings and `aria-current` for the selected stage.
- Route tabs use a real tablist pattern or an equivalent accessible navigation pattern; inactive route content is not duplicated in the DOM unnecessarily.
- Drawers close with Escape and return focus to the trigger.
- ActionDock controls remain keyboard reachable at every scroll position.
- Copy feedback is announced without moving focus.
- Focus must not jump to the top when polling updates a stage.

Inputs and handoffs:

- every intake, answer, and revision field has a programmatic label and an inline error target;
- submit buttons are reachable immediately after their field and expose a stable accessible name while loading;
- `Next question` and `Approve & continue to {destination}` are distinct in both visible copy and announcement text;
- approval announces the completed approval separately from a successful next-stage start;
- if start fails after approval, focus moves to the `Start next stage` recovery action.

## Live regions

- Use one small `role="status"` region for meaningful transitions such as “brief ready for review”, “generation failed”, or “preview promoted”.
- Do not put the entire changing stage, question card, progress list, or every polling update in an assertive live region.
- Keep error summaries in `role="alert"` only when the user needs immediate attention.
- Do not announce unchanged content repeatedly.

## Error states

| Condition | UI state | Required response |
|---|---|---|
| Offline/transient fetch error | stale connection | retain last state, show refresh/connection notice, continue bounded retry |
| Agent/provider failure | attention | safe summary, preserved inputs/artifacts, valid retry if server allows |
| Terminal Code Generator job failure | attention | stop polling, show active job error, retry/recovery action |
| Authorization fence failure | attention/support | explain that the session must refresh or needs support; no blind retry loop |
| Stale approved handoff | attention | identify stale source and require regenerate/new run |
| Approval succeeds, next start fails | approved + next available | show the approved state and a separate start-next action |
| Unknown backend status | unsupported | safe explanation and refresh, never guessed completion |
| Broken/external resource preview | evidence fallback | metadata tile and source link, no broken image or raw query alt text |
| Error boundary render failure | stage error boundary | preserve shell/navigation and offer reset/refetch |
| Input save fails | input | retain typed value, announce the save failure, expose retry |
| Administrator action fails | admin attention | retain the selected tab/row, show safe error text, keep the confirmation dialog usable |

## Motion and contrast

- Preserve the existing reduced-motion media behavior.
- Never require animation to understand status, scene order, or action availability.
- Keep visible focus indicators and sufficient text/control contrast.
- Use animation only for short state transitions and drawer movement; do not use looping ambient motion during agent work.

## Discovery question-specific rules

- Use a real `<fieldset>`/`<legend>` or an equivalent native grouping for radio and checkbox questions.
- Associate group hints and validation text with `aria-describedby`; every input has a visible label.
- Keep the option tile's focus indicator around the whole interactive row, not only the small control.
- For radios, Tab enters the checked radio or first radio, arrow keys move within the group, Space selects, and Tab exits the group. For checkboxes, Space toggles the focused control.
- Selecting an option must not move focus or submit before `Next question`.
- After a successful question transition, move focus to the new question heading/control only when needed to preserve orientation; do not reset focus on ordinary polling updates.
- On save failure, retain the answer and expose the error beside the question. Do not clear the field or selected values.
- A question save failure is an input-state error; a worker/provider failure is a separate attention state.
- Replace the broad `aria-live` on the whole question card with one small transition-only status region for events such as `Question ready`, `Answer saved`, or `We couldn't save that answer. Try again.`
- The action dock must reserve its own layout space so it cannot cover the focused control or the question's error.
- At 390px, tiles and textarea are full width, question copy stays within the viewport, and `Next question`/`Skip question` stack without horizontal scrolling.

## Administrator responsive rules

- the admin summary band changes from four columns to two and then one without hiding counts;
- the tablist wraps or becomes a contained horizontal strip; it must not widen the page;
- row action buttons wrap within the row and retain text labels;
- destructive confirmation dialogs fit the viewport, keep Cancel and Confirm reachable, and return focus to the originating action on cancel or completion.
