# Cobalt Atlas — Maya Kapoor portfolio prototype

Open [index.html](./index.html) directly in a browser. No build command or server is required.

This test-folder prototype uses three files:

- `index.html` holds all portfolio content, including identity, links, project descriptions, and sample outcomes.
- `style.css` owns all visual styling, responsive layouts, CSS artwork, and motion rules.
- `theme.js` provides content-independent hash routing, navigation state, accessible route announcements, and progressive scroll reveals.

The routes are `#home`, `#about`, `#case-oneaccount`, `#case-seller`, and `#case-atlas`. `#work` and `#contact` scroll to sections on the home view. Browser Back and Forward use normal hash history. Without JavaScript, every view remains in the document and anchor links still work. Reduced-motion preferences remove animated transitions.

To adapt the portfolio for another person, replace content and links in `index.html`. Keep each `data-view` ID aligned with its links. The script contains no person-specific text. The project visuals are abstract CSS concepts rather than screenshots or claims about real products.

The resume and all outcomes used here are fictional demonstration data. The sample email address is a placeholder. The Google Fonts import is optional; system-font fallbacks work offline.

This is a standalone front-end prototype in the test folder. Integrating it into OryxenAI Studio would require a separately pinned theme package, generated HTML contract, validator rules for scripts and routes, sandbox policy, and browser verification.
