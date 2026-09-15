# CODE GENERATOR PORTFOLIO PREVIEW — FRONTEND RESEARCH & REDESIGN BRIEF

## Purpose

Redesign the frontend experience used to **review a portfolio produced by the Code Generator**.

Treat this as a frontend/product-design task first.

Do not assume this document knows the current component tree, route structure, API contracts, preview infrastructure, state model, framework details, or implementation boundaries. Before changing anything, inspect the existing application and understand how generation state and portfolio preview are currently exposed.

Preserve working application behavior. Adapt these recommendations intelligently to the existing architecture instead of blindly rebuilding systems that already work.

The user-facing objective is simple:

**The generated portfolio should become the dominant object on screen, remain safely contained inside the application, be easy to inspect at different viewport sizes, and make it obvious what is generating, what is ready to review, and what the user can do next.**

---

# 1. Research conclusions from current AI builders

The relevant products increasingly converge on the same mental model.

| Product    | Current preview pattern                                                                                                                                                                                                           | Useful lesson                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Lovable    | Desktop places chat/progress on the left and a live interactive preview on the right. The sidebar can collapse so preview gets the full window. Mobile switches between chat and preview rather than squeezing both side-by-side. | Make preview dominant and allow secondary UI to disappear.                                 |
| Lovable    | Preview has Desktop / Tablet / Mobile switching, page/path selection, refresh and open-in-new-tab. It also supports direct preview feedback/editing.                                                                              | Keep preview controls close to the preview rather than mixing them into global navigation. |
| Lovable    | Can use live preview or a steadier completed-version preview.                                                                                                                                                                     | Do not require users to stare at unstable intermediate renders.                            |
| Rocket.new | Calls Preview a browser built into Rocket. Supports screen selection, fullscreen, refresh, Desktop/Laptop/Tablet/Mobile modes, screenshots and visual edits.                                                                      | Treat preview as a contained browser surface.                                              |
| Replit     | Agent work and Preview coexist; after generation the right pane becomes the running application. Canvas can surround the preview with annotations and feedback.                                                                   | Review should happen against the actual artifact, not against logs or screenshots.         |
| v0         | Generated applications run as real previews. The current product emphasizes a live right-pane preview, sandboxed execution, full-screen viewing, history and direct Design Mode refinement.                                       | Real application preview is the primary artifact; generation mechanics stay secondary.     |
| Emergent   | Explicitly separates temporary Preview from Deployment/production.                                                                                                                                                                | The user must understand that reviewing something does not mean it is public.              |
| Bolt       | Generates a working app users can immediately see and refine in-browser; recent Visual Edits move feedback directly onto the rendered application.                                                                                | Reduce the distance between “I see a problem” and “request this change.”                   |

Do not literally clone any one interface.

The best direction is a synthesis:

**Lovable's clarity + Rocket's preview controls + Replit's review context + v0's artifact-first approach + Emergent's preview/publish distinction.**

---

# 2. Core product principle

The screen should not feel like:

> an IDE showing some generated website.

It should feel like:

> a portfolio review studio containing a real browser canvas.

The hierarchy should always be:

**1. Portfolio**

**2. Current state / generation status**

**3. Review and change actions**

**4. Secondary controls**

**5. Developer internals only when genuinely needed**

Do not make files, source code, terminal output, package installation, raw worker logs or technical IDs visually compete with the portfolio.

---

# 3. Recommended desktop composition

Start conceptually with:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Application navigation / project context / current stage                  │
├──────────────────────┬──────────────────────────────────────────────────────┤
│                      │ Preview toolbar                                      │
│ GENERATION / REVIEW  ├──────────────────────────────────────────────────────┤
│ CONTEXT              │                                                      │
│                      │                                                      │
│ Current state        │               GENERATED PORTFOLIO                    │
│ Semantic progress    │                                                      │
│ Important message    │               actual interactive preview             │
│                      │                                                      │
│ Change request       │                                                      │
│                      │                                                      │
├──────────────────────┴──────────────────────────────────────────────────────┤
│ review / continue actions, only where appropriate                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

Do not hardcode those proportions.

As a design starting point, the preview should normally receive roughly two-thirds to three-quarters of the usable desktop area.

The secondary panel must be collapsible.

When the portfolio is ready, give the user an obvious way to enter a **clean preview / focus / fullscreen mode** where the portfolio becomes almost the entire application viewport.

Rocket specifically recommends fullscreen when preview becomes cramped beside chat, while Lovable lets users collapse the entire sidebar for this reason.

---

# 4. Preview container is a hard boundary

This is one of the most important requirements.

A generated portfolio must never be capable of visually “exploding” the surrounding frontend.

Examples include generated content containing:

```text
width: 1600px
min-width: 1200px
100vw / 100vh
position: fixed
position: sticky
z-index: 99999999
large SVGs
oversized images
full-screen overlays
portals/modals
very long pages
horizontal marquees
WebGL/canvas scenes
```

Whatever appears inside the generated portfolio must remain inside the preview boundary.

The host layout must therefore have a **strict containment contract**.

At the host-layout level, verify equivalents of:

```text
min-width: 0
min-height: 0
bounded width/height
overflow control
stable flex/grid sizing
```

particularly on every ancestor between the main workspace and the preview.

A common cause of “the preview made the whole UI wider” is a flex/grid child that lacks `min-width: 0`.

A common cause of “the whole application became 15,000px tall” is allowing the embedded document height to determine the workspace height.

The preview should instead have a bounded viewport and let the generated portfolio perform its own scrolling.

---

# 5. Do not directly trust generated DOM

If the existing architecture already uses an isolated browsing context such as an iframe, preserve that boundary unless there is a strong reason not to.

If it does not, investigate the existing preview mechanism before choosing a replacement.

For generated or otherwise untrusted application code, a browser isolation boundary is far safer than injecting generated HTML/JS/CSS directly into the parent application.

MDN and OWASP recommend iframe sandboxing for untrusted embedded content. MDN additionally warns that a same-origin iframe using both `allow-scripts` and `allow-same-origin` can effectively defeat the protection of sandboxing; serving potentially hostile content from another origin is safer.

This redesign does **not** need to redesign backend sandbox infrastructure unless the current frontend cannot satisfy the preview contract.

The coding agent should first inspect what already exists.

---

# 6. Preview viewport model

Do not treat the remaining width of the Studio as the generated website's only viewport.

A portfolio might be designed for a desktop viewport around 1440px wide while only 850–1000px of visible space remains beside application controls.

If the preview simply becomes 850px wide, the generated site may unexpectedly enter a tablet breakpoint.

Instead consider a proper **virtual viewport** model.

Conceptually:

```text
Selected viewport
1440 × 900

        ↓

rendered portfolio viewport

        ↓

scaled to fit available preview canvas
```

Recommended user-facing modes:

| Mode               | Purpose                                                       |
| ------------------ | ------------------------------------------------------------- |
| Desktop            | Inspect normal large-screen design                            |
| Laptop             | Verify common smaller desktop screens                         |
| Tablet             | Verify medium breakpoint                                      |
| Mobile             | Verify primary phone layout                                   |
| Fit                | Fit currently selected viewport into available preview canvas |
| Fullscreen / Focus | Give maximum screen area to the portfolio                     |

Do not expose twenty devices unless the product genuinely benefits from it.

Rocket supports Desktop, Laptop, Tablet and Mobile classes plus specific phone models. Lovable keeps the simpler Desktop/Tablet/Mobile model.

For this product, simplicity is preferable.

The important thing is testing breakpoint classes, not pretending to be a hardware laboratory.

---

# 7. Fit behaviour

“Fit” deserves explicit engineering attention.

The generated application should not be rewritten or have its breakpoint logic changed just because the preview canvas is smaller than the selected viewport.

Possible implementation approaches depend on the existing frontend.

If visual scaling is used, correctly account for:

* transform origin,
* wrapper dimensions,
* pointer coordinates,
* scrolling,
* focus outlines,
* browser zoom,
* high-DPI rendering.

CSS `transform: scale()` changes visual coordinates without causing surrounding layout to recalculate. Overflow therefore still needs to be handled by the preview wrapper.

Do not attempt to solve iframe sizing with `object-fit`; MDN explicitly notes that `object-fit` has no effect on iframes.

---

# 8. Preview toolbar

Keep the toolbar compact.

It should feel like browser chrome, not another application dashboard.

A sensible hierarchy is:

```text
[status]  [page / route]

                 [desktop/tablet/mobile]
                 [fit / scale]
                 [refresh]
                 [open separately]
                 [fullscreen]
```

Do not show labels for every action when icons plus tooltips are sufficient.

Make the most frequently used actions visible.

Put secondary actions behind overflow.

The toolbar should never take more visual attention than the portfolio.

---

# 9. Page / route navigation

Multi-page portfolios need a clear route/page control.

Research references:

Lovable has a page selector that can list pages, search them or accept a path.

Rocket has a “Currently viewing” screen selector.

For a portfolio product, prefer human-friendly page names:

```text
Home
About
Projects
Experience
Contact
```

rather than exposing internal route IDs.

If there are many generated routes, make the selector searchable.

Selecting a page should behave like real application navigation as much as possible.

The preview should still support normal links inside the generated portfolio.

Parent route control and child navigation must remain synchronized if the existing preview architecture supports this.

---

# 10. History behaviour

When the user navigates inside the preview:

* browser-like Back/Forward behaviour should not become confusing;
* selecting a page from the host toolbar should update the preview predictably;
* clicking internal portfolio links should update current route state where technically supported;
* refreshing a nested route should still load the correct page;
* unknown routes should produce the portfolio's intended 404/not-found behaviour, not break the Studio shell.

Do not unnecessarily rebuild the preview when only route state changed.

---

# 11. Refresh behaviour

Provide ordinary refresh.

Also account for the case where ordinary refresh does not fix a stale or broken environment.

Lovable explicitly provides a stronger restart behaviour when regular refresh is insufficient.

The UX can therefore distinguish conceptually between:

```text
Refresh preview
```

and, only when necessary:

```text
Restart preview
```

Do not present Restart permanently if it is rarely needed.

It can appear after repeated load failure or live under an overflow menu.

---

# 12. Generation → preview transition

Do not continuously flash half-built UI unless the current product intentionally supports live generation and it is reliable.

For a portfolio review product, the preferable progression is:

```text
Generation starts
↓
meaningful semantic progress
↓
portfolio becomes renderable
↓
verification / preparation
↓
healthy preview becomes available
↓
preview is promoted into primary view
```

While a new generation/revision is running, if there is already a healthy portfolio available, **keep displaying that healthy portfolio**.

Show something like:

```text
Updating your portfolio…
Current preview remains available.
```

Then replace it only when the new output is ready.

This is a much calmer UX than:

```text
good portfolio
→ blank screen
→ broken HTML
→ reload
→ another blank screen
→ completed portfolio
```

Lovable explicitly supports a mode where the preview displays the most recent completed version and only updates when work finishes.

---

# 13. Progress presentation

Do not expose chain-of-thought or noisy implementation logs.

Do not invent percentages unless the backend provides a real measurable progress model.

Avoid:

```text
Generating 63%
Thinking…
Running npm…
Editing 47 files…
```

Prefer semantic states such as:

```text
Preparing portfolio
Building pages
Applying visual direction
Connecting portfolio content
Checking interactions
Checking responsive layouts
Preparing preview
Ready for review
```

If actual application state provides more accurate terminology, use that terminology instead.

Do not fake work.

---

# 14. Loading states

Handle every major preview condition explicitly.

### Nothing generated yet

The preview canvas should not look broken.

Show a calm empty state explaining that the portfolio will appear here once generation completes.

### Generation underway

Display semantic progress and a reserved preview canvas.

### Starting preview

Use a subtle loading surface inside the preview container.

Do not allow the entire surrounding layout to shift.

### Preview ready

Crossfade or replace the loading surface quickly.

### Refreshing

Keep existing preview visible when possible; use a subtle activity indicator in the toolbar.

### New revision generating

Keep the last healthy preview visible.

### Preview unavailable

Show a contained recovery surface instead of a blank white iframe.

### Generation failed

The failure should appear in the surrounding application, not as an incomprehensible browser error page.

### Preview paused / sleeping

If the current infrastructure can pause preview execution, explain that clearly and provide Resume.

Lovable currently surfaces this exact concept for temporary preview environments.

---

# 15. Blank-preview detection

Do not assume iframe `load` means the application loaded successfully.

MDN documents that browsers fire an iframe's `load` event even when loading fails and do not provide a normal iframe `error` event for this purpose.

If the current preview implementation has a child/parent bridge or readiness handshake, use it.

Otherwise inspect the current mechanism and introduce the smallest reliable readiness signal appropriate to the architecture.

Conceptually:

```text
iframe/document loaded
        ≠
portfolio application ready
```

Possible UI states:

```text
Starting preview…
Preview did not respond.
Retry
Open separately
```

Do not leave an eternal spinner.

---

# 16. Timeout handling

Define different concepts:

**Loading** — expected.

**Slow** — taking longer than normal.

**Unavailable** — readiness could not be established.

Do not immediately label slow loading as failure.

Likewise, do not retry indefinitely.

A retry loop that reloads the preview every two seconds can prevent a slow application from ever finishing startup.

Use bounded retries.

---

# 17. Preview errors

A generated portfolio can fail in many ways:

```text
JavaScript exception
missing bundle
404 asset
font failure
bad image
route failure
runtime crash
infinite render
network dependency timeout
CSS parse problem
CSP restriction
unsupported browser API
```

The frontend must distinguish:

**Host application failure**

from:

**Generated portfolio failure**

A problem inside the portfolio must never destroy the host Studio.

The normal user should see:

```text
Preview needs attention.

The portfolio could not be displayed correctly.

Retry preview
```

If technical diagnostics are useful, put them behind a secondary details surface.

Do not dump stack traces into the primary UX.

---

# 18. Portfolio overflow cases

Test intentionally generated pathological layouts.

### Fixed-width layout

Portfolio:

```text
width: 1800px
```

Expected:

The preview may horizontally scroll or scale depending on preview mode.

The host application must not widen.

### Huge minimum width

```text
min-width: 1400px
```

Expected:

Contained inside preview.

### 100vw

Expected:

100vw belongs to the generated application's viewport, not the host Studio.

### 100vh

Expected:

It fills the generated viewport, not the whole OryxenAI page.

### position: fixed

Expected:

Fixed to the embedded preview viewport.

### enormous z-index

Expected:

Cannot cover preview toolbar or application navigation.

### full-screen modal

Expected:

Covers only the generated portfolio viewport.

### portal element

Expected:

Still contained by the generated application's browsing context.

### extremely tall page

Expected:

Generated portfolio scrolls internally.

The host page does not become 20,000px tall.

---

# 19. Scrolling model

Desktop should ideally have clearly separated scroll ownership.

Conceptually:

```text
Application shell
    fixed workspace

Generation/review panel
    own scroll if necessary

Portfolio preview
    own scroll

Global page
    ideally not moving during focused preview work
```

Avoid nested scroll areas unless each has an obvious job.

Do not create three adjacent panes that all scroll vertically.

---

# 20. Scroll chaining

When the user reaches the bottom of the portfolio, avoid accidental scrolling of the entire Studio if possible.

Evaluate appropriate `overscroll-behavior` or equivalent existing design patterns.

This is particularly important on trackpads and mobile touch devices.

---

# 21. Preview focus mode

Provide a high-priority focus/fullscreen experience.

In focus mode:

* collapse secondary generation context;
* retain a very small escape/header surface;
* keep device and route controls available;
* maximize preview size;
* do not hide the action required to return to normal mode.

Rocket explicitly hides the chat panel in fullscreen preview, and Lovable lets users collapse the entire chat sidebar.

---

# 22. Mobile Studio behaviour

Never shrink desktop split-view UI onto a phone.

Lovable's current mobile pattern is more appropriate: users swipe between chat and preview instead of seeing both simultaneously.

For this product, options include:

```text
[Progress] [Preview]
```

or a preview-first surface with generation/review information in a bottom sheet.

The exact solution should match the existing navigation patterns.

The important rule:

**The generated portfolio gets the usable mobile width.**

Do not render:

```text
140px progress column + 240px preview
```

on a 390px phone.

---

# 23. Tablet behaviour

Tablet is not just a large phone.

At medium widths, consider:

* collapsible progress rail;
* temporary overlay panel;
* preview-first layout;
* reduced toolbar labels;
* overflow menu for secondary actions.

Do not make the toolbar horizontally scroll unless absolutely necessary.

---

# 24. Short laptop screens

Test height, not only width.

Critical sizes include roughly:

```text
1366 × 768
1280 × 720
```

The preview toolbar, primary preview and next-step action must remain usable.

Do not create giant headings or large vertical status cards above the actual portfolio.

A preview product that looks excellent at 1440×1000 but forces the actual portfolio below the fold at 1280×720 has failed.

---

# 25. Window resizing

Resize continuously while testing.

Check:

* split panel resize;
* browser resize;
* sidebar expansion;
* sidebar collapse;
* toolbar wrapping;
* viewport scaling;
* preview centering;
* mobile breakpoint changes;
* iframe reload behaviour.

Changing the host size should not unnecessarily restart the generated application.

---

# 26. Browser zoom and OS scaling

Test at:

```text
80%
100%
125%
150%
```

where practical.

Also consider Windows display scaling.

Controls must not overlap merely because effective CSS viewport dimensions change.

Avoid pixel-perfect positioning that assumes one DPI.

---

# 27. External links

Generated portfolio links may point to:

```text
GitHub
LinkedIn
email
resume
external project
company website
```

Define deliberate behaviour.

Internal portfolio navigation stays in the preview.

External web links should normally open safely outside the preview after user interaction.

Generated content must not unexpectedly navigate the top-level Studio application.

Iframe sandboxing can restrict top-level navigation unless those capabilities are explicitly granted.

---

# 28. target="_blank" and popups

Do not blindly grant popup permissions.

Some generated portfolios may use:

```text
window.open()
target="_blank"
```

Decide which user-initiated external navigation is supported.

Ensure new tabs cannot maintain unsafe opener relationships where that matters.

Do not allow generated content to spam windows.

---

# 29. Downloads

Portfolio content may include:

```text
Download résumé
Download CV
Download case study
```

If downloads are supported, test them deliberately.

If the preview sandbox restricts them, expose the correct capability intentionally rather than broadly loosening preview restrictions.

---

# 30. Forms

Generated portfolios may contain:

```text
contact forms
newsletter fields
demo forms
```

Decide whether preview form submissions should actually execute.

A review environment may intentionally suppress real submissions.

If they are suppressed, communicate this clearly.

Do not silently allow a test form to send real emails or create real production records unless that behaviour is explicitly part of the product.

---

# 31. Authentication inside a preview

Embedded authentication can fail because of:

* third-party cookie rules,
* popup restrictions,
* redirect URI assumptions,
* frame restrictions,
* cross-origin storage policies.

Do not destroy preview isolation just to accommodate an unusual authentication flow.

If a flow genuinely requires a top-level context, provide:

```text
Open preview in new tab
```

Lovable and Rocket both explicitly provide a separate-browser preview path for fuller testing.

---

# 32. Browser permissions

Generated portfolio code should not automatically inherit access to things such as:

```text
camera
microphone
geolocation
payment APIs
clipboard
fullscreen
screen capture
```

Permissions should follow the existing platform/security design and be granted minimally.

The browser supports iframe-level Permissions Policy restrictions for exactly this kind of capability control.

---

# 33. Parent ↔ preview communication

If the current system needs the parent UI and generated portfolio to coordinate, use a narrow, explicit bridge rather than parent DOM manipulation.

Potential message categories:

```text
preview ready
current route changed
runtime failure
request external navigation
visibility changed
refresh
navigate to route
```

Do not invent these messages if the current architecture already defines its own protocol.

Inspect first.

If cross-origin messaging is used, validate:

```text
event.origin
event.source
message shape
message version/type
```

Do not accept arbitrary `postMessage` payloads.

MDN recommends cross-origin communication through `postMessage` when normal DOM access is blocked by same-origin policy.

---

# 34. Preview visibility

When preview is hidden because the user switches panels or the browser tab becomes inactive, heavy generated pages might continue running:

```text
videos
canvas loops
WebGL
particle systems
requestAnimationFrame
timers
```

If the existing preview bridge supports lifecycle information, consider notifying the portfolio that preview became hidden.

This can reduce unnecessary CPU/GPU usage.

Do not add a complicated protocol solely for this unless heavy previews justify it.

---

# 35. Media-heavy portfolios

Test portfolios containing:

* autoplay video;
* multiple videos;
* very large images;
* SVG animation;
* canvas;
* WebGL;
* large background videos.

Preview controls should remain responsive.

The host shell should not become sluggish because the generated site is visually complex.

Avoid expensive host-side blur/backdrop effects surrounding a heavy preview.

---

# 36. Font loading

The generated site may initially render fallback fonts and then shift.

Preview UI must not resize because the embedded site's typography changes.

The browser canvas stays fixed.

The generated application can experience its own internal layout shift without changing the host shell.

---

# 37. Missing assets

Missing image/font/icon resources should not produce a broken host screen.

The generated application may look incomplete.

The surrounding review UI stays functional.

If verification/advisory information is available through the product, surface it calmly rather than replacing the portfolio with a giant error.

---

# 38. Stale assets and cache

Users will often say:

> I asked it to change something but I still see the old version.

Provide predictable recovery:

```text
normal refresh
strong/restart refresh where supported
```

Do not aggressively disable all caching in production just to solve development-style issues.

Follow the existing preview system's asset/version strategy.

---

# 39. Service workers

If generated portfolios can register service workers, they can complicate preview refresh and stale-build behaviour.

Inspect whether the current generator permits them.

Do not introduce service-worker support casually into a generated preview environment.

If it already exists, ensure a previous generation's service worker cannot keep controlling a new preview unexpectedly.

---

# 40. Version/revision UX

v0 prominently exposes History, while Lovable has project version history.

However, do **not** introduce user-visible version history merely because competitors have it.

First inspect the product's existing generation model.

If versions/revisions already exist as a supported user concept, the preview UI can eventually offer:

```text
Current
Previous
Restore
Compare
```

If they do not exist, do not invent a frontend-only history model.

The minimum UX requirement is simply:

**never destroy the last healthy preview while a replacement is being prepared.**

---

# 41. Requesting changes

Once the portfolio is ready, make revision feedback close to the preview.

Conceptually:

```text
Describe what you want changed…
```

with a clear action.

Do not force the user to navigate away from the portfolio and remember what looked wrong.

Future enhancement possibilities, if they fit product scope:

```text
select element
annotate region
capture screenshot
pin comment
```

Lovable, Rocket, Replit and Bolt are all moving toward visual feedback directly against the rendered artifact. Lovable supports element selection, inline text editing, annotations and comments; Rocket offers visual editing and screenshot capture; Replit Canvas lets annotations travel with the selected preview.

Do not necessarily implement all of those now.

Design the surface so they could be added later without redesigning the entire workspace.

---

# 42. Do not make preview editing interfere with normal interaction

If future visual-selection mode is introduced, distinguish clearly between:

```text
Interact
```

and:

```text
Select / annotate
```

Otherwise users will click a portfolio navigation link while trying to select it, or select an element while trying to test it.

Mode changes need visible state.

---

# 43. Review actions

The portfolio review moment needs clear outcome actions.

Examples:

```text
Request changes
Approve
Continue
```

Use whatever terminology matches the existing workflow.

Do not use developer-centric words like:

```text
Commit
Merge
Ship build
Promote artifact
```

for normal portfolio users unless those terms already exist in the product language.

---

# 44. Preview versus public/live state

Make the distinction obvious.

Emergent's Preview and Deployment are intentionally separate concepts, and Lovable describes preview as a private staging-like space while published visitors see a separate snapshot.

For this product, appropriate language could resemble:

```text
Private preview
Review before publishing
Not public yet
```

Use only if factually accurate for the existing application.

Do not claim privacy or publication behaviour that the backend does not actually provide.

---

# 45. Visual design

Do not copy the dark-IDE aesthetic of developer builders unless the surrounding product already uses it.

The portfolio itself is visually rich.

The host review UI should therefore be restrained.

Use:

* quiet canvas/background;
* precise separators;
* small controls;
* strong typography;
* clear active states;
* restrained shadows;
* minimal chrome;
* consistent existing product tokens.

Avoid:

* giant gradient panels;
* excessive cards;
* glowing “AI” decorations;
* oversized generation text;
* fake terminal windows;
* animation competing with portfolio motion.

The surrounding UI should disappear mentally when the user begins reviewing the portfolio.

---

# 46. Toolbar contrast

Generated portfolios may contain:

```text
pure white
pure black
bright yellow
photography
video
moving backgrounds
```

Do not place essential preview controls directly over generated content without a stable contrast strategy.

Prefer controls outside the preview canvas.

If future floating controls are placed over preview, they need adaptive or intentionally fixed high-contrast styling.

Lovable's floating preview toolbar can automatically adapt its appearance against content, illustrating the underlying problem.

---

# 47. Motion

Host animations should be subtle.

Good candidates:

```text
panel collapse
focus-mode transition
preview-ready crossfade
toolbar state transition
device viewport resize
status change
```

Do not animate the preview container continuously.

Do not add fake scanning/progress animations.

Respect `prefers-reduced-motion`.

The generated portfolio may already contain substantial motion; the Studio should not visually fight it.

---

# 48. Accessibility

The preview shell itself must have excellent accessibility even if generated portfolio quality varies.

Requirements include:

* visible keyboard focus;
* labelled icon buttons;
* sensible tooltip behaviour;
* meaningful iframe title;
* keyboard-accessible route selector;
* keyboard-accessible device controls;
* no control dependent solely on hover;
* minimum comfortable pointer targets;
* readable status messaging;
* reduced-motion support;
* sufficient contrast.

Do not announce constantly changing generation status to screen readers every second.

Use restrained live-region semantics only for meaningful state changes.

---

# 49. Keyboard focus and iframe boundary

Iframes create a distinct keyboard context.

Test:

```text
Tab into preview
Tab through portfolio
Shift+Tab back out
Esc from focus/fullscreen mode
keyboard activation of preview toolbar
route selector navigation
```

Users must not feel trapped inside the generated portfolio.

---

# 50. Mobile accessibility

Do not place 20 tiny toolbar icons across a phone.

Move secondary actions into an overflow sheet/menu.

Maintain touch targets around common accessibility guidance sizes.

Do not rely on hover-only tooltips.

---

# 51. Performance

The preview workspace needs to feel immediate even when the generated site is heavy.

Avoid reloading the portfolio when:

```text
collapsing sidebar
changing unrelated host UI
opening menus
changing generation panel tabs
```

Changing viewport dimensions should normally resize the preview, not reconstruct it.

Changing Fit scale should not reload.

Host effects should primarily use transform/opacity and inexpensive layout changes.

Do not keep expensive `will-change` hints permanently enabled everywhere.

---

# 52. Layout containment and CSS containment

CSS `contain` can help isolate layout/paint work in parts of the host UI, but do not treat it as a security boundary.

Use the correct browser isolation mechanism for generated application execution.

Use CSS containment for layout/performance only where it actually helps.

---

# 53. Network/offline state

Handle the Studio becoming offline.

The user should understand:

```text
Portfolio preview may be unavailable while offline.
```

Do not misrepresent network failure as generation failure.

If a previously rendered preview remains usable locally, leave it visible where appropriate.

---

# 54. Multiple tabs

A user may open the same portfolio in two tabs.

Avoid surprising behaviour such as:

```text
Tab A refreshes old preview
Tab B completes new generation
Tab A somehow replaces current state with stale data
```

Frontend should use the application's authoritative current state rather than making local assumptions about which generation is newest.

---

# 55. Race conditions

Be careful with asynchronous preview operations.

Example:

```text
user selects /projects
preview load A begins

user selects /about
preview load B begins

A completes after B
```

The toolbar should not jump back to `/projects`.

Use request identity/current-navigation checks where relevant.

The same principle applies to refresh, device changes and new preview URLs.

---

# 56. Rapid revision requests

If users can request multiple changes quickly:

* avoid launching conflicting frontend states;
* show queued/pending status if the backend provides it;
* keep the currently healthy preview available;
* don't optimistically pretend every change is already applied.

Lovable currently queues preview-toolbar change requests rather than forcing users to wait before describing the next modification.

Do not implement queuing yourself unless supported by the existing product.

---

# 57. Fullscreen browser APIs

Distinguish:

```text
Studio focus mode
```

from:

```text
browser Fullscreen API
```

A focus mode that simply expands the preview within the app is often easier and less disruptive.

Native browser fullscreen can be an optional enhancement.

Do not require permission-sensitive fullscreen behaviour just to provide a larger canvas.

---

# 58. Open in new tab

This is highly valuable and should be retained or added if technically appropriate.

Lovable and Rocket both expose it directly.

It solves:

* true browser width testing;
* embedded-auth limitations;
* complex keyboard flows;
* testing browser chrome interactions;
* copying a route URL;
* testing heavy visual content.

The opened preview should represent the same portfolio state as the embedded preview.

---

# 59. Screenshot/feedback future path

Rocket's screenshot-to-chat model is particularly relevant for design review: users can capture the whole preview or an area and use it as feedback context.

This does not need to be implemented immediately.

But avoid designing a preview shell that would make future screenshot annotation impossible.

---

# 60. What NOT to copy from developer-oriented tools

Do not automatically add:

```text
file explorer
terminal
source-code editor
Git branch selector
package manager
console
server logs
database explorer
deployment logs
raw build logs
```

Those tools make sense for Replit/v0/Bolt's developer workflows.

The primary user here is reviewing a generated portfolio.

Developer diagnostics may exist elsewhere, but they should not dominate this screen.

---

# 61. What NOT to do with the current codebase

Do not assume:

* a particular iframe implementation;
* a particular backend preview service;
* a specific state-machine name;
* a fixed generation API;
* a particular component library;
* a specific router;
* a particular storage strategy;
* version history exists;
* live intermediate builds exist;
* publishing behaviour works a certain way.

Inspect the repository first.

Map the existing implementation onto this experience.

Change only what is necessary for the frontend redesign and safe preview behaviour.

---

# 62. Suggested information hierarchy

When generation is in progress:

```text
Code Generator

Building your portfolio
Current meaningful step

[semantic activity]

Portfolio preview / existing healthy preview
```

When ready:

```text
Portfolio ready for review

[large preview]

Request changes                  Approve / Continue
```

If something fails:

```text
Portfolio generation needs attention

Previous healthy preview, if one exists

Retry / appropriate recovery
```

Keep wording concise.

---

# 63. Suggested preview toolbar hierarchy

Primary:

```text
Page
Desktop / Tablet / Mobile
Fit
Refresh
Focus
```

Secondary/overflow:

```text
Open in new tab
Restart preview
possibly capture
possibly additional viewport options
```

Only expose actions supported by the real application.

---

# 64. Suggested responsive philosophy

### Large desktop

Split review/progress and preview.

Preview dominates.

### Small laptop

Reduce secondary-panel width and collapse nonessential details.

### Tablet landscape

Preview first, secondary panel collapsible.

### Tablet portrait

Preview with overlay/drawer for generation context.

### Mobile

One major surface at a time.

Preview receives full width.

Generation/review context becomes tab, sheet or separate view.

---

# 65. Test matrix

Test the redesigned frontend against generated portfolios with:

| Case                                | What to verify                          |
| ----------------------------------- | --------------------------------------- |
| Normal portfolio                    | Standard happy path                     |
| 1-page portfolio                    | Empty route selector handling           |
| 10+ routes                          | Searchable route navigation             |
| Very long page                      | Internal scroll containment             |
| Fixed 1600px layout                 | No Studio horizontal expansion          |
| `100vw/100vh` hero                  | Correct embedded viewport               |
| Fixed header                        | Fixed only inside preview               |
| Giant z-index modal                 | Cannot cover Studio                     |
| Sticky sections                     | Correct internal scrolling              |
| Horizontal carousel                 | Does not move parent                    |
| Huge images                         | Container remains stable                |
| Missing image                       | Preview survives                        |
| Missing font                        | Preview survives                        |
| JS exception                        | Recovery UI appears                     |
| Slow startup                        | Slow state rather than infinite spinner |
| Blank render                        | Readiness timeout/recovery              |
| Nested route refresh                | Works correctly                         |
| Unknown route                       | Appropriate not-found behaviour         |
| External link                       | Safe expected behaviour                 |
| Download link                       | Explicit expected behaviour             |
| Contact form                        | Defined preview behaviour               |
| OAuth/login                         | Open-new-tab fallback where needed      |
| WebGL/video                         | Host remains responsive                 |
| Browser zoom 125–150%               | Controls remain usable                  |
| 1280×720                            | Preview remains primary                 |
| 390px phone                         | No desktop split-view compression       |
| Keyboard only                       | Full workflow possible                  |
| Reduced motion                      | No unnecessary motion                   |
| Network disconnect                  | Correct offline state                   |
| New generation while preview exists | Old healthy preview remains             |
| Rapid route changes                 | No stale async state                    |
| Multiple tabs                       | No obvious stale preview regression     |

---

# 66. Acceptance criteria

The redesign is successful when the user can arrive at the Code Generator review stage and immediately understand:

**What is happening?**

**Where is my portfolio?**

**Can I interact with it?**

**How does it look on desktop/tablet/mobile?**

**How do I make the preview larger?**

**How do I navigate its pages?**

**What do I do if it fails to load?**

**How do I ask for changes?**

**What do I do when I approve it?**

And technically:

The generated portfolio never expands the host layout.

Long portfolio pages scroll inside the preview.

Fixed/sticky/fullscreen generated UI stays confined to the preview.

Preview resizing does not constantly reload the application.

The secondary panel can get out of the way.

Short laptops remain usable.

Mobile uses one primary surface at a time.

Blank/error/slow states are explicit.

Previous healthy output is preserved while newer work is being prepared whenever the underlying product supports that behaviour.

Preview and published/live states are not accidentally conflated.

No unnecessary developer IDE is added.

Existing backend and Code Generator behaviour are preserved unless an actual frontend integration problem requires modification.

---

# 67. Research-backed design direction

The clearest 2026 pattern is not “show more AI activity.”

It is:

**make the generated artifact increasingly tangible and directly reviewable.**

Lovable puts the live app beside chat and lets chat disappear.

Rocket treats the generated app as an internal browser.

Replit lets users annotate the rendered result.

v0 centers the live running app and increasingly pushes design changes directly against it.

Bolt now lets people visually edit by clicking the rendered application.

Emergent keeps testing Preview separate from real Deployment.

The frontend should therefore be designed around:

> **Artifact first. Agent second. Review before release.**

Use this as the governing principle when making implementation decisions.
