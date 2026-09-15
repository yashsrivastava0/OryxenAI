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
| Ready preview height | Verified preview, status, and primary open/review action are reachable without a hidden or covering action area |
| Tablet preview order | At 768×1024 the preview theater appears before long activity/composer content, with no page-level horizontal scroll |
| Preview frame bounds | The iframe remains inside the theater bounds at 1536×695, 1366×768, 768×1024, and 390×844 |

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
| Ready verification | `preview.url` is visibly labelled verified; a candidate URL is never presented as verified |
| Preview action truthfulness | Ready state contains an open/review action, not a publish/deploy claim unsupported by the server contract |
| Candidate/verified split | `preview` and `candidatePreview` remain distinct in the rendered view model and in the theater |
| Generation entry | Approved Build Preparation shows an actionable Generate state, not a dead-end lock |
| Partial approval | Approval success and next-stage start failure are represented separately |
| Input composer | Intake, answer, and revision fields have labels, inline validation, preserved values on failure, and visible submit actions |
| Destination copy | Review handoff buttons name the destination agent; no bare `Next` advances a stage |
| Admin boundary | Creator topbar contains no destructive admin reset; authorized accounts can reach `/admin` from the account menu |
| Admin controls | `/admin` renders summary, Users/Projects/Legacy/Deleted/Operations/Audit tabs, row actions, refresh, pagination, live status, and typed-target confirmation |
| Admin safety | Unauthorized `/admin` access is rejected server-side; destructive mutations include idempotency and confirmation data; self/last-admin protections remain visible as safe errors |

## Accessibility and interaction

- Keyboard traversal reaches every navigation, tab, drawer, and action control.
- Focus rings are visible.
- Drawer Escape returns focus to the opening control.
- Route tabs expose selected state.
- Status announcements occur only on meaningful transitions.
- Reduced-motion mode removes nonessential transitions.
- Error summaries are understandable without developer terminology.
- Intake, answer, revision, and admin confirmation controls have visible focus and inline validation.
- `Next question` and `Approve & continue to {destination}` are not interchangeable labels.

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

For Generation ready/preview, use the fixture-backed `ready` view with a
verified preview URL, a candidate-only view, a stale-ready view, and an
attention view with a preserved preview. Compare hierarchy to
[20-generation-ready-preview.png](visuals/20-generation-ready-preview.png),
but treat the view model and server response as authoritative. Tablet has no
separate image: record the 768×1024 geometry and focus results as the
responsive acceptance evidence.

For the separate administrator pass, record `/admin` at desktop and mobile widths, including the Users tab, a project/operations tab, and one confirmation dialog. Use [12-admin-control-center.png](visuals/12-admin-control-center.png) as composition reference only; use live API data and safe masked values in validation.

## Discovery question browser matrix

| Scenario | Fixture/input | Pass condition |
|---|---|---|
| Single-select idle | `single_select` with three options | Native radio group renders with a visible group name and no request occurs on option selection |
| Single-select submit | one option selected | `Next question` submits the existing answer payload once and enters the server-returned state |
| Multi-select | `multi_select` with three options | Native checkbox group renders as vertical selectable tiles; multiple values can be selected and deselected locally |
| Multi-select submit | one or more options selected | `Next question` submits selected IDs once; empty selection cannot submit unless the server contract permits it |
| Text question | `text` question | `Your answer` is a visible associated label; textarea and action are visible without long scrolling |
| Draft retention | text typed, save request rejected | typed value remains, safe inline error is visible, and retry is available |
| Choice retention | options selected, save request rejected | selected values remain checked and no false next-question transition is announced |
| Skip | `allowSkip: true` | `Skip question` is separate, submits the existing skip payload, and never fabricates an answer string |
| Transition announcement | successful save returns a new question | exactly one meaningful status transition is announced; the entire question body is not repeatedly read |
| Keyboard | radios, checkboxes, textarea, actions | Tab/Shift+Tab, arrows, Space, Enter, and visible focus follow the native/group contract |
| Responsive geometry | 1536×695, 1366×768, 768×1024, 390×844 | no page overflow, clipped controls, title/status overlap, or action obstruction |
| Product boundary | creator question screen | no raw JSON, permanent output rail, open admin popover, or destructive reset control is present |
