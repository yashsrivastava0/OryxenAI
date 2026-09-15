# Generation ready/preview and responsive layout research

This document is the focused handoff for the final Code Generator surface: the
state in which a verified preview is available for review, plus the responsive
behavior required when the same surface is rendered at tablet widths. It is a
documentation and reference-image deliverable. It does not change frontend
source code, backend contracts, or the existing visual set.

The authoritative new reference is
[`visuals/20-generation-ready-preview.png`](visuals/20-generation-ready-preview.png).
There is intentionally no tablet image. Tablet is a responsive implementation
requirement, not a second product composition or a new preview-device promise.

## 1. Scope and decision summary

### In scope

- The `complete`/ready Code Generator view when a verified preview URL exists.
- The distinction between a verified preview and a candidate/unverified
  preview.
- The review actions that are safe for the current product contract.
- Reflow of the host workspace at 768–1199 CSS pixels.
- Browser-level checks at 1536×695, 1366×768, 768×1024, and 390×844.
- A new desktop reference image that an implementing AI can compare against.

### Deliberately out of scope

- A dedicated tablet mockup or tablet-specific visual asset.
- Adding a new backend field, publishing API, share-link system, or device
  emulation API.
- Changing the preview gateway or weakening the self-only CSP.
- Re-generating or overwriting `visuals/01`–`visuals/19`.
- Administrator screens. The separate admin work may continue independently;
  the creator ready state must not open the admin menu or expose its reset
  control.

### Product decision

The ready surface is a review theater, not a deployment console. The primary
user question is “Can I inspect the verified result and decide what to do
next?” The surface therefore prioritizes the preview, its verification status,
route navigation, and a clear open/review action. A `Publish`, `Deploy`, or
similar action must not be shown unless a server-authoritative publishing
contract exists; the current repository explicitly keeps public publishing out
of scope.

## 2. Codebase-grounded forensic findings

This section describes the current implementation, not the target. Paths are
relative to the repository root.

### 2.1 Current stage rendering

`frontend/src/stages/generation/GenerationStage.tsx` currently has explicit
branches for `attention`, `working`, `available`, and `complete`. In the ready
branch it:

1. derives `previewUrl` from `view.preview?.url` or
   `view.candidatePreview?.url`;
2. marks the preview as verified with `hasVerifiedPreview` only when
   `view.preview?.url` is present;
3. renders the five-milestone stepper (`Plan`, `Acquire`, `Build`, `Verify`,
   `Preview`);
4. renders a browser-framed iframe when a preview URL exists;
5. shows `Open preview`/`View in a new tab` beneath the theater; and
6. currently renders a ready-state control labelled `Publish when ready` with
   the secondary line `Deploy your project`.

The last item is the important contract mismatch. The current callback opens
the existing preview URL; it does not publish a portfolio. The implementation
handoff must rename that action to a truthful preview action, or remove it in
favor of the existing open-preview link. Do not make the browser imply a
server-side deployment that did not happen.

The component also has a no-view/locked branch with `Stage Locked`. That branch
is valid only when preparation is genuinely not approved. It must not appear
after a successful preparation approval when the separate generation-start
request failed; that partial-success case belongs to the available/start-next
contract in `03-runtime-state-and-api-contract.md`.

### 2.2 Current adapter and view-model contract

`frontend/src/data/adapters/generation.ts` already exposes the fields needed by
the target surface:

```text
status, stale, staleReasons, currentMilestone, coordinatorStage,
currentAttempt, traceId, activeJobId, activeJobKind, issues, latestError,
projectTitle, projectSummary, preview, candidatePreview, warnings,
safeError, retryAvailable
```

The adapter already maps:

- `ready` to `complete` when the view is not stale;
- `ready` to `attention` when the view is stale;
- a terminal failed/cancelled active job to `attention`;
- `not_started` to `available` only after preparation approval;
- `active_job_id`/`active_job_kind` to the active job, without comparing
  `current_run_id` to a job ID;
- `preview` and `candidatePreview` independently, so a prior preview can be
  preserved during attention recovery; and
- `retryAvailable` only when the server projection permits retry.

That adapter behavior is the source of truth. The ready screen must not infer
verification from a URL alone, invent a route, or turn a candidate preview into
a verified preview. The UI should display the safe projection and keep raw
agent output in the closed developer inspector.

### 2.3 Current layout and CSS risks

`frontend/src/styles/shell.css` currently defines:

- `.codegen-workspace` as a two-column grid with a 340–380px left panel;
- a breakpoint at `max-width: 1024px` that changes the grid to one column;
- `.browser-content-viewport` with `aspect-ratio: 16 / 10`,
  `min-height: 480px`, and `max-height: calc(100vh - 14rem)`;
- a `.device-selector-pills` region that currently contains only a Desktop
  control; and
- separate mobile rules that stack general stage grids but do not yet define
  the ready-state preview ordering, minimum available height, or action-dock
  relationship.

The single-column tablet breakpoint is not sufficient by itself. At
768×1024, leaving the left activity/composer column before the preview creates
an unnecessarily long path to the artifact the user is trying to review. At
the same time, keeping a fixed `min-height: 480px` inside a small tablet
viewport can make the theater and action area compete for vertical space.
The implementing AI must reflow the surface, not merely let the desktop grid
wrap.

### 2.4 Audit evidence

The current audit screenshots are forensic references:

- [`generation-01-start.png`](../current-frontend-audit/evidence/screenshots/generation/generation-01-start.png)
  shows the old locked arrival, a large unused canvas, and a permanently
  visible handoff utility rail.
- [`generation-02-progress.png`](../current-frontend-audit/evidence/screenshots/generation/generation-02-progress.png)
  shows plain progress copy, a raw JSON rail, and no primary preview theater.

Those images explain the origin of FE-001, FE-010, FE-019, and FE-020. They are
not visual targets. The new reference removes browser chrome, taskbars, admin
menus, raw JSON, and the permanent utility rail.

## 3. External research and design implications

The following sources are guidance, not a replacement for the OryxenAI API
contract.

### 3.1 Responsive layout is content-driven

web.dev describes responsive design as a combination of fluid layout, fluid
media, and media queries, and recommends choosing breakpoints where the
content needs them rather than treating device names as fixed layout classes.
The implication here is that “tablet” is a behavior range for the host shell:
the two-column arrangement stops being useful when the preview and its
controls can no longer remain readable. The implementation should use CSS
constraints and measured geometry, not a separate tablet product screen.
[1][2]

### 3.2 Reflow must remove two-dimensional page scrolling

WCAG reflow guidance requires content to remain usable at a 320 CSS-pixel
viewport without two-dimensional scrolling, except for content whose nature
requires two dimensions. The preview itself is inherently a bounded embedded
surface; the surrounding application must still reflow and must not create a
page-level horizontal scrollbar. Route controls and any compact tab strip may
scroll within their own contained region, never by widening the document.
[3][4]

### 3.3 Focus and status are part of the ready state

WCAG 2.2 treats focus not being obscured as a real interaction requirement.
A sticky action dock, a drawer, or a responsive preview reordering must not
cover the focused control. Status messages can communicate a preview
promotion or verification transition without moving focus; continuous polling
should not re-announce the entire theater.
[5][6]

### 3.4 The iframe is a contained artifact, not the application shell

The current preview uses an iframe with `allow-scripts allow-same-origin
allow-forms`. MDN documents the importance of understanding sandbox tokens and
the risk of combining scripts and same-origin content when the embedded page
is served from the same origin. Keep the existing preview isolation boundary
and let the preview gateway remain responsible for preview content. The host
surface should size the frame with a responsive aspect-ratio container; it
should not rely on `object-fit`, which does not control iframe layout.
[7][8]

### 3.5 Browser validation should use real viewport emulation

Playwright's device and viewport emulation can validate layout at realistic
screen sizes, touch capability, and viewport dimensions. Use fixture-backed
view models for deterministic state coverage, then add one authenticated smoke
journey. The screenshot generated for this handoff is a visual reference; it
does not replace DOM geometry assertions.
[9]

## 4. Target ready/preview experience

### 4.1 User goal

When `GenerationViewModel.state === "complete"` and
`view.preview?.url` is present, the page should answer four questions at a
glance:

1. Is the result verified or only a candidate?
2. What artifact am I looking at?
3. How do I inspect another route or open the preview independently?
4. What can I safely do next?

The preview is the dominant visual surface. The milestone history and
instruction composer remain available but subordinate. A developer inspector
is opt-in and closed by default.

### 4.2 Desktop composition

At 1536×695 and 1366×768:

- Use the compact OryxenAI topbar and five-stage navigator without an account
  popover or destructive admin control.
- Keep a short `Generate & Preview` context strip in normal flow.
- Use a centered, bounded workspace. The left context column may contain the
  project title, a concise approved-handoff summary, and the completed
  milestone list. It must not become a second prose document.
- Give the preview theater the larger share of the available width.
- Place a small theater toolbar above the frame with a truthful verification
  state, route selection if route paths are available, `Fit to view`, and an
  explicit open-preview action.
- Render the verified iframe inside a bounded browser frame with no overflow
  escape. The generated page may scroll within the iframe; the host document
  must not expand to the generated page height.
- Reserve a bottom action area. Prefer `Open verified preview` or `Review
  preview`; offer `Regenerate` only if the server and entitlement allow it.
- Do not show `Publish when ready`, `Deploy your project`, a fake percentage,
  a public URL, raw JSON, model/provider names, or technical trace data in the
  normal surface.

### 4.3 Copy and status rules

Use status copy that describes the server projection:

| Projection | User-facing status | Preview treatment | Action treatment |
|---|---|---|---|
| `complete` + verified preview | `Portfolio ready to review` or the adapter's ready text | Badge `Verified preview` | Open/review preview; optional policy-backed regenerate |
| `complete` + candidate only | `Preview ready for review` | Badge `Candidate preview — not yet verified` | Review candidate; never call it verified |
| `attention` + preserved preview | `Generation needs attention` | Keep the previous preview and label it | Retry only when `retryAvailable`; otherwise refresh/support |
| `working` + preview | `Preview updating` | Keep preview visible with update status | Stop/cancel only if the existing server contract permits |
| `available` | `Ready to generate` | No generated preview; show approved handoff | `Generate portfolio` |
| `locked` | Explain the exact missing prerequisite | No preview | Link back to the prerequisite stage |

The adapter's `statusText`, `safeError`, `warnings`, `preview`, and
`candidatePreview` remain authoritative. Illustrative image text must not be
copied into the application without a corresponding field.

### 4.4 Preview theater contract

The shared `PreviewTheater` should accept:

```text
preview: GenerationPreviewVM | null
candidatePreview: GenerationPreviewVM | null
verificationStatus: verified | unverified | absent
routePaths: string[]
activeRoute: string | null
fitToView: boolean
onOpenPreview(): void
onRouteChange(routePath): void
onToggleFit(): void
```

Required behavior:

- Use `preview.url` only for the verified badge.
- Use `candidatePreview.url` only with an explicit candidate label.
- Preserve the last usable preview when a later job enters `attention`.
- Keep the browser frame and iframe inside a `min-width: 0` grid item.
- Use an aspect-ratio wrapper, but allow a sensible `min-height: 0` at tablet
  and mobile widths so the frame does not force the page beyond the viewport.
- Make route navigation a contained control. If there are no route paths, do
  not render an empty selector.
- Opening the preview in a new tab must use the existing verified/candidate
  URL selected by the view model; do not build a URL in the browser.
- Keep technical traceability in the closed `OutputInspector` or attention
  details drawer. It must not be part of the theater's normal reading order.

## 5. Tablet behavior: responsive rules, no dedicated tablet screen

The user-facing visual pack intentionally has no tablet PNG. Implement and
test the following behavior instead.

### 5.1 Tablet landscape and portrait: 768–1199px

At the tablet range:

1. Switch from the desktop two-column workspace to a single logical flow.
2. Put the context/status strip first, the preview theater next, and the
   milestone/composer details after it or inside a disclosure. The user should
   reach the primary artifact before scrolling through activity history.
3. Replace the full five-step navigator with the existing compact stage
   selector pattern. Keep the current stage and progress text available; do
   not hide the stage identity in color alone.
4. Let the theater use the available width. Remove the desktop `min-height:
   480px` pressure when it would cause action obstruction; preserve the frame's
   aspect ratio and a readable minimum that is measured in the browser.
5. Keep the action dock in normal flow or sticky only when its reserved height
   is measured. It must never overlay the iframe, the route selector, or a
   focused control.
6. Collapse the instruction composer by default when it is not needed. If
   open, it appears after the preview or in an accessible sheet; the user must
   not lose typed text when the layout changes.
7. Keep route selectors within a horizontally scrollable local strip. The
   document itself must remain at one-dimensional width.
8. Keep Output Inspector closed. If opened, it becomes a dismissible
   full-width sheet or drawer that returns focus to its trigger.

This is a responsive reflow, not a separate tablet device preview. The
embedded generated site remains whatever preview the server supplied. Do not
invent a tablet URL, tablet screenshot, tablet-specific metadata, or a new
backend viewport field.

### 5.2 Mobile cross-check: 390×844

Mobile is not the main visual deliverable in this task, but it is part of the
regression boundary:

- one-column artifact and full-width theater;
- context and progress condensed into a selector/summary;
- action controls stacked in priority order with reserved bottom space;
- route strip scrolls locally if needed;
- no permanent left panel, developer rail, raw JSON, or admin menu;
- preview frame does not force horizontal page scroll;
- user can reach `Open preview`, retry/recovery, or the next valid action
  without an obscuring fixed element.

## 6. Implementation sequence

The implementing AI should follow this order and keep each change small:

1. Read `03-runtime-state-and-api-contract.md` and verify that the server
   projection and adapter state are authoritative.
2. Keep `adaptCodeGenerator` pure; add or preserve fixture cases for verified
   ready, candidate-only ready, stale ready, preserved preview attention, and
   partial approval/start failure.
3. Refactor `GenerationStage.tsx` around `ProgressSurface`, `PreviewTheater`,
   `ActionDock`, and a compact ready-state context summary. Do not duplicate
   preview URL selection in JSX.
4. Replace the misleading `Publish when ready` copy with the truthful
   preview/review action supported by the current callback/API contract.
5. Make the verified/candidate label visible in the theater and expose route
   controls only when route data exists.
6. Update `shell.css` with a ready-state layout that has `min-width: 0`, a
   bounded responsive iframe wrapper, and an explicit tablet ordering. Do not
   solve tablet by only setting the desktop grid to one column.
7. Keep the instruction composer and diagnostics discoverable but subordinate;
   ensure a drawer/sheet has Escape handling and focus return.
8. Add fixture-backed browser checks for all four viewports. Use real DOM
   measurements for document overflow, theater bounds, action visibility,
   title/status intersections, and focus obstruction.
9. Run the authenticated smoke journey through preparation approval, generation
   start, ready/preview, and attention recovery. Preserve the existing auth,
   revision, idempotency, entitlement, and preview-isolation assertions.
10. Compare the implementation to
    [`visuals/20-generation-ready-preview.png`](visuals/20-generation-ready-preview.png)
    for hierarchy only. When the image and backend state disagree, the
    Markdown/API contract wins.

## 7. Acceptance checks for this surface

| Check | Expected result |
|---|---|
| Ready state | A verified preview is the dominant artifact and is labelled verified |
| Candidate state | Candidate preview is visibly unverified and never described as live/verified |
| Preview containment | Iframe remains inside the theater; generated page height does not expand the host document |
| Truthful action | No publish/deploy claim appears without a server-backed contract |
| Route control | Route selector appears only with route data and scrolls within its own region |
| Tablet ordering | At 768×1024 the preview is reachable before long activity/composer content |
| Tablet geometry | No horizontal overflow, clipped toolbar, or action-dock obstruction at 768×1024 |
| Desktop geometry | No title/status overlap and no clipped controls at 1536×695 or 1366×768 |
| Mobile geometry | No horizontal overflow and actions remain reachable at 390×844 |
| Preview failure | Terminal failure maps to attention within one successful poll, stops polling, and preserves any existing preview |
| Recovery | Retry appears only when `retry_available` is true; authorization-fence failures offer refresh/support instead |
| Focus | Opening/closing inspector returns focus correctly; sticky actions do not obscure focus |
| Status | Preview promotion and failure are announced once through a small status region; polling does not re-read the theater |
| Product boundary | No raw JSON, open admin menu, creator reset action, secret, model/provider detail, or external media URL in the normal surface |

## 8. Source list

The numbered references in this document are the primary guidance used for the
responsive and embedded-preview conclusions.

1. [web.dev — Responsive web design basics](https://web.dev/articles/responsive-web-design-basics)
2. [web.dev — Introduction to responsive design](https://web.dev/learn/design/intro)
3. [W3C — Reflow, WCAG 2.1 Understanding](https://www.w3.org/WAI/WCAG21/Understanding/reflow)
4. [W3C — Technique G225: target content remains within 320 CSS pixels](https://www.w3.org/WAI/WCAG22/Techniques/general/G225)
5. [W3C — Focus Not Obscured (Minimum), WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum)
6. [W3C — Status Messages, WCAG 2.1 Understanding](https://www.w3.org/WAI/WCAG21/Understanding/status-messages.html)
7. [MDN — `<iframe>` element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe)
8. [MDN — General embedding technologies](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content/General_embedding_technologies)
9. [Playwright — Emulation](https://playwright.dev/docs/emulation)

