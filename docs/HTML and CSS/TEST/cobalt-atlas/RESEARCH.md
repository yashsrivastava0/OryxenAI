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

The illustrations are CSS concepts, not real product screenshots. The provided resume and its metrics are fictional. The optional Google Fonts import in this test can fall back to local system fonts; production should self-host pinned fonts. This test does not modify the Studio backend or its security policy.
