# Cobalt Atlas — standalone stylesheet concept

Open [`index.html`](./index.html) to preview the portfolio. The first project links to [`project.html`](./project.html), and the navigation opens [`about.html`](./about.html). All three pages use [`atlas-portfolio.css`](./atlas-portfolio.css). The demo needs no build step, JavaScript, remote fonts, or image files.

This is the second new prebuilt stylesheet concept alongside Obsidian Signal. It is intentionally separate from the active Editorial Forest theme. Cobalt Atlas uses a fixed cobalt side spine, open light masthead, horizontal snap gallery, connected process line, circular portrait, and radial pill-button interaction. A soft morphing liquid shape, scroll linked gallery artwork, progress bar, and same-origin page transitions extend that language. Its `atlas-*` components and `--atlas-*` tokens are independent of the other two stylesheets.

The CSS artwork fills project and portrait spaces when no image is provided. To use an image, place an `<img>` inside `.atlas-art` or `.atlas-profile__portrait`; the image covers the built-in artwork. Use meaningful `alt` text and remove the placeholder's `role="img"` when doing so.

The stylesheet is ready for optional future scripts: `.atlas-page[data-motion="on"]` plus `.atlas-appear.is-in-view` for reveal motion, `data-scrolled="true"` for the header, and `--atlas-drift-x` / `--atlas-drift-y` for the hero drawing. The page remains readable without any script and honors reduced-motion settings.

The current Studio still accepts its original fixed one-page markup contract. Adopting this concept there later requires a new pinned theme package, content mapping, exemplar, and validator rules. The mock's project navigation is a regular static HTML link, not CSS routing.
