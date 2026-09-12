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

Rules: preserve cross-origin isolation; label candidate versus verified; keep existing preview when a later run fails; respect reduced motion.

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
