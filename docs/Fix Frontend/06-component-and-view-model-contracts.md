# Component and view-model contracts

The implementation should use the existing Preact/TypeScript/Vite stack and keep data translation in pure adapters. Shared components provide composition rules; stages remain responsible for their own representation.

## Shared components

### StageNavigator

Inputs: ordered stage IDs, labels, current stage, normalized stage state, and selection callback.

Rules: render five production stages; show active state independently of color; prevent selection of locked/unsupported stages; collapse to a selector on tablet/mobile; do not render stage-local raw output.

### StageContextStrip

Inputs: stage name, purpose, status text, up to four facts, freshness, and optional inspector action.

Rules: render facts once; never duplicate the same count or status in the artifact header and action dock.

### ArtifactReview

Inputs: eyebrow, title, purpose, status, children, secondary readers, warnings, and action configuration.

Rules: single-flow header; bounded title; no absolute status placement; readable body measure; no forced table-of-contents column; secondary content uses deliberate disclosure.

### ActionDock

Inputs: primary action, secondary action, disabled/loading state, status message, and optional stop/retry behavior.

Rules: sticky but reserved; never covers content; primary action has one clear verb; labels do not wrap on desktop; mobile actions stack full width.

Action semantics:

- accept an explicit `destinationStage` and `requiresApproval` flag;
- render destination-specific copy, never a bare `Next` for a stage handoff;
- expose `Approve & continue to {destination}` only when the current stage is reviewable;
- expose `Continue to Generate` for the approved preparation handoff and keep Code Generator start explicit;
- expose `Start next stage` when approval succeeded but the subsequent start request failed;
- expose `Retry generation` only when `retry_available` is true in the server projection;
- keep a sibling status region for `Saving`, `Approved`, `Start failed`, or `Retrying`.

### InputComposer

Inputs: field label, purpose/help text, value, validation state, word/character limit, submit label, disabled/loading state, and submit callback.

Rules: semantic `<label>` association; multiline field for intake, answers, and revisions; preserve typed value on failed requests; no raw prompts, JSON, provider names, or model reasoning; use full-width layout on mobile; submit through the existing API command and announce only the resulting transition.

### NextStageHandoff

Inputs: approved current stage, destination label, start status, approval callback, start callback, and partial-success message.

Rules: one explicit user gesture may request approval and navigation, but the view model records approval and start independently. The destination cannot become `working` until its start response is confirmed. Partial success is rendered as `Approved` plus `Start next stage`.

### OutputInspector

Inputs: active stage, stage outputs, safe state metadata, and copy handler.

Rules: developer mode only, closed by default, read-only JSON, active-stage selection, safe copy feedback, keyboard Escape close, no worker payloads or secrets.

### ProgressSurface

Inputs: semantic milestones, current milestone, elapsed/last updated, stop callback, and state.

Rules: no fake percentage or ETA; status text is human-readable; working state is `aria-busy`; only meaningful transitions are announced.

### AttentionPanel

Inputs: safe summary, preserved-work note, retry availability, retry callback, refresh/support guidance, and optional technical details.

Rules: no “Oops!” copy; never show a retry button that the backend will reject; preserve previews and approved inputs.

### PreviewTheater

Inputs: verified/candidate preview, route list, viewport controls, focus mode, and external-open action.

Rules: preserve cross-origin isolation; label candidate versus verified; keep existing preview when a later run fails; respect reduced motion. The ready state is a review theater, not a publishing console: do not render `Publish` or `Deploy` actions unless the server contract supplies them. Route controls are conditional on route data, and the iframe stays inside a bounded aspect-ratio wrapper with `min-width: 0`.

Ready-state contract:

- `preview.url` is the only source for a `Verified preview` label;
- `candidatePreview.url` is explicitly labelled candidate/unverified;
- `Open verified preview`/`Review preview` uses the existing server-supplied URL and does not construct a public URL;
- a previous preview remains visible during `attention` when the adapter supplies it;
- desktop may use the current two-column composition, while 768–1199px reflows to preview-first single flow; tablet is not a separate device mockup;
- at tablet/mobile widths the preview height is responsive and must not be forced by the desktop `min-height: 480px` when that would obscure actions;
- route selection, fit controls, and focus mode are rendered only when their data/callbacks exist; and
- diagnostics remain in the closed developer-only inspector.

See [17-generation-ready-preview-research.md](17-generation-ready-preview-research.md) for the code-grounded rationale and [20-generation-ready-preview.png](visuals/20-generation-ready-preview.png) for hierarchy only.

## Stage-specific components

- `RouteMap`: complete route inventory with route ID, path, purpose, and active selection.
- `RouteTabs`: accessible tablist for selected route, with horizontal overflow contained inside the tab strip.
- `SectionCard`: section role, title, copy, evidence, and optional unresolved state; suppress exact title/body duplicates.
- `IntentCard`: prose visual intent with a stable label; no fabricated token values.
- `SceneStoryboard`: ordered scene cards with narrative goal, viewport role, layout, motion, responsive behavior, accessibility, and performance intent.
- `ResourceEvidenceCard`: title, purpose, provider/source, license, dimensions/aspect, source link, and neutral fallback tile; never direct external image preview.
- `BriefReader`: collapsed Markdown reader with safe rendering and no duplicate summary content.

## Normalized state contract

The shared stage state is:

```text
locked | available | working | input | review | attention | complete | unsupported
```

`input` is reserved for user-completable Discovery intake/answers. `review` means the artifact is ready for a human decision. `attention` means work stopped or needs a user-supported recovery. Unknown backend states map to `unsupported`.

Every view model includes:

```text
state
statusText
raw
job
agentOutput
```

Stage-specific models may add renderable fields but must retain the complete agent-owned output separately from derived cards.

## Adapter rules

- Accept `unknown` input.
- Validate only the minimal required envelope.
- Normalize only recognized statuses.
- Do not fabricate missing content.
- Deduplicate exact repeated display values where the backend field has been mapped to two visual roles.
- Preserve safe errors and previews.
- Keep backend IDs out of user-facing copy unless they are approved support references.

## Discovery question surface

The Discovery interview may be implemented as one component or a small family of components, but the following contracts must remain explicit:

### QuestionHeader

Inputs: stage label, current ordinal, total ordinal, question text, optional `helpText`, and optional earlier-answer disclosure.

Rules: one visible primary question; bounded line length; no duplicate prompt/body rendering; no admin controls or raw agent envelope; heading and answer group must not produce duplicate screen-reader announcements.

### ChoiceGroup

Inputs: question kind, server-provided option IDs/labels, selected IDs, disabled/loading state, and change callback.

Rules: `single_select` uses native radios, `multi_select` uses native checkboxes, and `boolean` uses the single-select treatment. Every control has an associated visible label. Full-row tiles are presentation only; do not replace native control semantics with an untested custom role. Selection does not call the API.

### AnswerComposer

Inputs: current question, local answer, draft state, validation error, submit label, skip availability, disabled/loading state, and callbacks.

Rules: text questions use a visible `Your answer` label and the existing safe session draft behavior. The composer retains its value after failure. `Next question` submits the existing answer payload and never claims to start another agent stage.

### QuestionActionBar

Inputs: primary submit action, optional skip action, loading state, save status, and error/retry action.

Rules: primary and secondary actions remain visible in the initial viewport; labels do not wrap on desktop; mobile actions stack full width; selection and answer changes remain local until the explicit primary action.

### Question state view model

The question presentation may derive local UI state from the existing `DiscoveryQuestionVM` without changing the backend schema:

```text
question: DiscoveryQuestionVM
selection: string[]
textDraft: string
submitLabel: "Next question" | "Submit answer"
saveState: "idle" | "saving" | "error"
statusMessage: string | null
```

`selection` and `textDraft` are client interaction state. The adapter remains pure and continues to accept `unknown`, preserve the raw response, and normalize only the existing question kinds. No option descriptions, question limits, model fields, or provider fields may be invented for this surface.
