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
| Desktop body measure | Main prose region is at least 36rem at desktop and never collapses to a one/two-word column |
| CTA rendering | Desktop labels do not wrap into four lines and arrow/icon is not clipped |
| Empty intake | No permanent scrollbar is created by shell decoration/padding alone |

## Representation and data

| Check | Expected result |
|---|---|
| Content | Route map and route selection appear before long copy; only selected route is expanded |
| Duplicate copy | Identical section title/body values are rendered once with the correct semantic role |
| Output inspector | Raw JSON is absent from normal product mode and available only in developer mode after explicit opening |
| Inspector freshness | Selecting a later stage cannot leave Discovery output selected by fallback |

## Async behavior

| Check | Expected result |
|---|---|
| Active job identity | Adapter uses `active_job_id`, not `current_run_id`, to select a job |
| Terminal failure | Failed/cancelled active job maps to `attention` even if run status is stale |
| Polling stop | Poll coordinator unsubscribes after `attention`, `review`, `complete`, `locked`, or `unsupported` |
| Retry validity | Retry button is shown only when `retry_available` is true and the endpoint accepts it |
| Explicit stage boundary | Discovery approval permits a separate Content Architect start; Content Architect approval is terminal |
| Input composer | Intake, answer, and revision fields have labels, inline validation, preserved values on failure, and visible submit actions |
| Destination copy | The start action after Discovery approval names Content Architect; no bare `Next` advances a stage |
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
- `Next question` and `Approve brief` are not interchangeable labels; Content Architect starts through its own explicit action after Discovery approval.

## Browser test coverage

Add fixture-backed browser tests that mount each normalized stage state and measure real layout in a browser. Keep existing adapter, API, worker, and security tests. Add one live authenticated smoke run covering:

```text
Discovery intake → questions → brief review → approval
→ Content review → approval
→ terminal approved state
```

Record screenshots and geometry results for the four target viewport classes on every remediation pass.

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
