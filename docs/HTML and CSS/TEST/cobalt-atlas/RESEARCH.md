# Cobalt Atlas: theme architecture findings

## Recommended production shape

Treat a portfolio version as **approved content + a pinned theme package + generated HTML**. The theme package owns the immutable `style.css`, `theme.js`, fonts, and any approved artwork. The code generator writes the visible HTML against a strict markup contract. The host adds the technical `<head>`, stylesheet, and script reference, seals the bundle, verifies it in the real preview environment, and promotes only a passing version. A chat edit rebuilds the HTML with the same pinned package.

This test prototype shows the rendering side of that model. Its five distinct views live in one `index.html` and use hash routes. This gives direct links and Back/Forward navigation on plain static hosting without server rewrite rules. `theme.js` only reads IDs and `data-view` attributes. All person-specific copy remains in HTML.

## Why these effects

- CSS handles composition, responsive behavior, hover states, and the conceptual product artwork. There is no runtime layout engine or animation dependency.
- [IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) starts reveals only as sections enter view. Reveals animate opacity and transforms, avoiding layout-changing properties.
- [`hashchange`](https://developer.mozilla.org/en-US/docs/Web/API/Window/hashchange_event) powers route changes and native browser history. [`startViewTransition`](https://developer.mozilla.org/en-US/docs/Web/API/Document/startViewTransition) is optional; the route still works without it.
- [Scroll-driven CSS animation](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations/Timelines) enhances the progress indicator where supported. Unsupported browsers simply omit the indicator.
- `prefers-reduced-motion` disables reveal and transition motion. With JavaScript disabled, every view stays readable in document order.

## Changes required before Studio integration

The current Studio contract deliberately forbids scripts and accepts a one-page HTML subset. Its preview CSP and iframe sandbox also omit `allow-scripts`. Therefore this prototype **cannot be copied into the active theme folder and work as-is**.

1. **New pinned theme version:** Put the reviewed `theme.js`, CSS, and local fonts in a new immutable package. Hash each asset in the manifest and keep the existing themes unchanged for existing sessions.
2. **Expanded content contract:** Add structured fields for About and each case study, with admission bounds and explicit placement rules. The model should supply content and allowed markup only. It must never supply JavaScript, inline handlers, arbitrary URLs, or CSS.
3. **Validator changes:** Allow the route IDs, navigation links, and theme classes needed by the new markup. Validate unique IDs, internal hash resolution, allowed text placement, and complete case-study content. Keep the closed-world content check.
4. **Sealing and preview:** Add the script tag in host-owned HTML only. Adjust CSP and iframe sandbox to permit the **trusted theme script** while preserving an opaque origin and owner-scoped preview grants. Test script loading through the actual signed preview route before changing production policy. Do not grant `allow-same-origin` merely to make effects run.
5. **Verification:** Exercise every route, direct deep link, Back/Forward, no-JS fallback, keyboard focus, reduced motion, console errors, request failures, and horizontal overflow at phone and desktop widths. A failed build must leave the previous live version intact.
6. **Deployable bundle:** Keep assets relative to `index.html` and avoid external font or animation services in the production package. Static hash routes work on a static host; the authenticated Studio preview still requires its existing backend and grant logic.

## Prototype limits

The illustrations are CSS concepts, not real product screenshots. The provided resume, the extra fixtures and all metrics are fictional. Fonts are imported from Google Fonts by `style.css` (the theme is exactly `style.css` + `theme.js`); the fixtures' small images are inline `data:` URIs and any image URL works. The earlier embedded-font experiment was dropped in favour of this simpler setup. This test does not modify the Studio backend or its security policy.

## 2026 research pass (theme v2)

Goal: find out how top-tier portfolio sites are built with HTML, CSS and JavaScript in 2026, and decide what a **content-independent** theme should adopt.

### What advanced sites actually run on

- Award-level portfolio sites are mostly framework apps (typically Next.js) with **GSAP + ScrollTrigger** for scroll and timeline choreography, **Lenis** for smooth scrolling kept in sync with GSAP on one animation frame loop, and **Three.js/WebGL** for 3D hero scenes. Page transitions come from GSAP timelines or the View Transitions API.
- GSAP became free (including SplitText, ScrollTrigger, Flip, MorphSVG) in 2025 after Webflow acquired it, but under a **proprietary "no charge" licence**, not an open-source one. Its terms restrict use in tools that compete with Webflow's visual animation building. A product that *generates* sites for other people is a grey area, and the file would also have to be vendored through the Studio's sealing and CSP. **Decision: do not depend on it.**
- Lenis is MIT and small, and it keeps native scrolling, but replacing scroll behaviour is a contested accessibility trade-off and adds a vendored file. **Decision: skip it; use native scrolling.**
- Three.js/WebGL gives the strongest wow but is heavy and fragile under a sandbox. **Decision: out of scope**; CSS gradients (with `@property`-animated coordinates) give a similar feel without a GPU dependency.

### What the platform now covers natively (and what the theme uses)

| Capability | Status found | Use in the theme |
| --- | --- | --- |
| Same-document View Transitions | Chrome 111, Safari 18, Firefox 144 | Route crossfade, shared-element art morph, circular theme reveal. Plain swap without support. |
| Cross-document View Transitions | Chrome 126, Safari 18.2 | Not used (single-document hash routing). |
| Scroll-driven animations (`animation-timeline`) | Chrome 115, Safari 26; Firefox stable still behind a flag | Progress bar and parallax under `@supports`; JS fills in for Firefox. |
| `light-dark()`, `oklch()`, `color-mix()`, `@property`, `:has()`, container queries, `@layer`, `text-wrap` | Baseline | Core of the token system and layout. |
| `@starting-style`, `linear()`, anchor positioning | Shipping in current engines | Palette/dialog entry. |
| `sibling-index()`, `scroll-state()` queries, `corner-shape`, `scroll-target-group`, `contrast-color()` | Chromium-only or very new | Deliberately **not** relied on. |

### Patterns adopted from current top-tier sites

Large type hierarchy with a serif-italic accent, bento/modular stat grids, kinetic (word-reveal) headlines, spotlight and magnetic micro-interactions on fine pointers only, animated mesh gradients, marquees, a command palette, dark mode with an OS default, shared-element transitions, and skeleton/bounded-intro loading states (skeletons mirror real layout, avoid full-page spinners, and show nothing for sub-100 ms waits).

### Constraint that shaped everything else

A generated portfolio must work for any profession and any volume of content, inside a sandbox with a strict CSP and an opaque origin. That ruled out libraries and external assets, forced every effect to be optional, and led to features that make the theme robust instead of just pretty: headline size tiers, container-query cards, character-count-aware numerals, a boot veil to prevent re-flow, metric-matched fallback fonts, and an automation mode that shows the finished page.

### Sources

Read in full: Chrome "What's new in web UI" (I/O 2026), web.dev "Interop 2026", LogRocket "CSS in 2026", MDN View Transition API, MDN Scroll-driven animations, the GSAP Standard License page and the Lenis repository README. Seen only as search-result summaries (not read in full, treat as indicative): Awwwards listings, the Codrops write-up of a GSAP + Three.js + Lenis site (the page returned HTTP 403), the 2026 web design trend roundups, UX Planet's recruiter-portfolio article, and skeleton-loading guidance from design-system docs.

- https://developer.chrome.com/blog/new-in-web-ui-io26
- https://web.dev/blog/interop-2026
- https://blog.logrocket.com/css-in-2026/
- https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations
- https://developer.chrome.com/docs/web-platform/view-transitions/cross-document
- https://gsap.com/standard-license/
- https://css-tricks.com/gsap-is-now-completely-free-even-for-commercial-use/
- https://github.com/darkroomengineering/lenis
- https://tympanus.net/codrops/2026/07/15/the-architecture-behind-trionn-coordinating-gsap-three-js-lenis-and-web-audio/
- https://uxplanet.org/how-recruiters-judge-ux-portfolios-2026-59f77143ce1e

Browser-support figures above come from those pages and the search summaries; re-check them against caniuse before relying on a specific version number.
