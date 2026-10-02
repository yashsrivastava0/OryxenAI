# Obsidian Signal — standalone stylesheet concept

Open [`index.html`](./index.html) in a browser to preview the landing page. Its featured project links to [`case-study.html`](./case-study.html), which previews a second static page. Both use only [`signal-portfolio.css`](./signal-portfolio.css). No build step, package, remote font, image download, or JavaScript is required.

This folder is a design prototype. It is not registered as a Studio theme and does not change the current pinned theme. The current Code Generator validates a fixed one-page markup contract, so adopting this stylesheet in the product later would also require a new theme package, exemplar, validator contract, and content mapping. The case-study link demonstrates ordinary HTML navigation; CSS itself does not provide routing.

## Composition

The theme uses a near-black canvas, electric chartreuse signal color, sharp geometry, oversized sans display type, fine guide lines, and a single deliberate motion language. It includes a hero, project feature, project grid, about/portrait area, process steps, quote band, contact section, footer, and project-detail layouts. Breakpoints cover desktop, tablet, and small phones.

Artwork is optional. A `.sg-media` element has a complete CSS background on its own. Add `.sg-media__art` for a typographic placeholder, or add an `<img>` inside `.sg-media` to cover the placeholder with a real image. The portrait follows the same pattern. Give image elements meaningful `alt` text and omit the placeholder `role="img"` when a real image is present.

## Future extension points

The stylesheet works without scripts. Later, JavaScript may set `data-motion="enabled"` on `.sg-page` and add `.is-visible` to `.sg-reveal` elements after they enter the viewport. It may update `--sg-parallax-x`, `--sg-parallax-y`, and `--sg-scroll-progress`; or set `data-header-scrolled="true"`. For a scripted mobile menu, add a real menu button, set `data-nav-enhanced="true"` only after the button works, and toggle `data-nav-open="true"` with an updated `aria-expanded` value. The `sg-progress` bar also supports CSS scroll timelines when `data-css-progress` is present. Keep the reduced-motion path when adding any new effect.

For additional pages, reuse the nav/footer and use `.sg-page-hero`, `.sg-case`, `.sg-case__split`, `.sg-case__visual`, and `.sg-next`. Link static HTML documents as the mock does, or let a future router handle those URLs. None of these pages are generated or served by the current Studio pipeline.
