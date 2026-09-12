# Acceptance matrix

The implementation is complete only when the following checks pass against the audit fixture data and the live authenticated journey.

## Geometry and hierarchy

| Check | Expected result |
|---|---|
| Horizontal overflow | `document.documentElement.scrollWidth <= document.documentElement.clientWidth` at 1536×695, 1366×768, 768×1024, and 390×844 |
| Header collision | Stage title, status, metadata, and context strip have no intersecting bounding boxes |
| Review action | Primary review action is visible on first render and remains reachable without returning to document end |
| Discovery review height | Audit fixture is no more than 2.5 viewport heights in the default summary-first state |
| Content review height | Audit fixture is no more than 4 viewport heights with one route expanded |
| Design review height | Audit fixture is no more than 3.5 viewport heights with the storyboard visible |
| Preparation review height | Audit fixture is no more than 2.5 viewport heights |
| Desktop body measure | Main prose region is at least 36rem at desktop and never collapses to a one/two-word column |
| CTA rendering | Desktop labels do not wrap into four lines and arrow/icon is not clipped |
| Empty intake | No permanent scrollbar is created by shell decoration/padding alone |

## Representation and data

| Check | Expected result |
|---|---|
| Content | Route map and route selection appear before long copy; only selected route is expanded |
| Duplicate copy | Identical section title/body values are rendered once with the correct semantic role |
| Design | Thesis, intent cards, and scenes are visible without opening one catch-all disclosure |
| Design token policy | No fabricated hex colors, palette tokens, font names, or specimens are introduced |
| Preparation media | No cross-origin `<img>` is rendered under the self-only CSP; no raw keyword alt text appears |
| Output inspector | Raw JSON is absent from normal product mode and available only in developer mode after explicit opening |
| Inspector freshness | Selecting a later stage cannot leave Discovery output selected by fallback |

## Async behavior

| Check | Expected result |
|---|---|
| Active job identity | Adapter uses `active_job_id`, not `current_run_id`, to select a job |
| Terminal failure | Failed/cancelled active job maps to `attention` even if run status is stale |
| Failure convergence | Code Generator failure becomes visible within one successful poll |
| Polling stop | Poll coordinator unsubscribes after `attention`, `review`, `complete`, `locked`, or `unsupported` |
| Retry validity | Retry button is shown only when `retry_available` is true and the endpoint accepts it |
| Preview preservation | Existing verified/candidate preview remains visible after attention |
| Generation entry | Approved Build Preparation shows an actionable Generate state, not a dead-end lock |
| Partial approval | Approval success and next-stage start failure are represented separately |

## Accessibility and interaction

- Keyboard traversal reaches every navigation, tab, drawer, and action control.
- Focus rings are visible.
- Drawer Escape returns focus to the opening control.
- Route tabs expose selected state.
- Status announcements occur only on meaningful transitions.
- Reduced-motion mode removes nonessential transitions.
- Error summaries are understandable without developer terminology.

## Browser test coverage

Add fixture-backed browser tests that mount each normalized stage state and measure real layout in a browser. Keep existing adapter, API, worker, and security tests. Add one live authenticated smoke run covering:

```text
Discovery intake → questions → brief review → approval
→ Content review → approval
→ Design review → approval
→ Preparation ready → generation
→ success or attention recovery
```

Record screenshots and geometry results for the four target viewport classes on every remediation pass.
