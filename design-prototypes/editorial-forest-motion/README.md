# Editorial Forest Motion — standalone multi-page variant

Open [`index.html`](./index.html), [`work.html`](./work.html), and [`about.html`](./about.html) through the local preview server. They share [`forest-motion.css`](./forest-motion.css), a standalone copy of the pinned Editorial Forest stylesheet with additional motion and page layouts. The original package under `src/oryxenai/themes/editorial_forest/v1/` was not changed. The copied local font and SVG assets retain their included license.

This variant adds ambient ink movement, artwork parallax, linked page transitions, practice-area spreads, an About layout, and a clear multi-page navigation. The pinned theme already had entrance motion, a marquee, section reveals, and CSS scroll progress; those behaviors remain in this variant. The new pages use practice areas from the sample profile rather than inventing client projects or outcomes.

The three HTML pages are normal same-origin documents. Browsers that support `@view-transition` can animate navigation; other browsers simply load the destination. Scroll linked effects use `@supports` and reduced-motion rules. No JavaScript is required.

This is a preview concept. The current Studio still generates one page against its pinned markup contract. Integrating a new theme or multi-page output there would require a separate contract, content model, bundle, and preview design.
