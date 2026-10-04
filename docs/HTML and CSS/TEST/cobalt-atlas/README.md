# Cobalt Atlas v2 — person-agnostic portfolio theme (test prototype)

Open [index.html](./index.html) directly in a browser. No build step.

The app regenerates the HTML for each person and reuses the theme unchanged. **The theme is exactly two files:**

| File | Owns |
| --- | --- |
| `style.css` | Every visual decision: tokens, layout, components, generative artwork, motion, print. Fonts are imported from Google Fonts by one `@import` line at the top. |
| `theme.js` | Behaviour only: routing, loading states, reveals, navigation chrome, command palette. No person text, no hard-coded routes. |

Everything else in this folder is not part of the theme: `index.html` and `profile-*.html` are **content fixtures** (the HTML the app would generate), `verify/verify.py` is the test harness, and this README and `RESEARCH.md` are notes.

## The fixtures

Every fixture is **fictional**. Their job is to prove the theme does not depend on who the portfolio is for. Their small images are inline `data:` URIs so they work offline; `<img src>` can be any URL.

| Fixture | Stresses |
| --- | --- |
| `index.html` (Maya, product designer) | 3 case studies, About route, **no photo** (initials avatar on About). |
| `profile-engineer.html` | 4 projects (bento layout), hero without a visual, skills marquee, 4 stats incl. a negative number. |
| `profile-chef.html` | Non-tech vocabulary, one project, **photo** in the hero and on About, no stats, no timeline. |
| `profile-stress.html` | One view only, 60-character name, 150-character headline, unbreakable strings, emoji/CJK/RTL, **a broken portrait** and a broken card image, empty sections, 8 externally linked projects. |

## Markup contract

Only two things are required. Everything else is optional and degrades quietly.

**Required**

- One `<article class="route-view" id="…" data-view data-title="…">` per page/route. The view with `id="home"` (or else the first one) is the default.
- Navigation links are ordinary `<a href="#id">` inside `.site-nav`. `id` may be a view **or any section inside a view**; the router shows the owning view and scrolls to the section. No route names live in JavaScript.
- Exactly one `<h1>` per view.

**Components** (all optional; unknown or missing ones never break layout)

`.site-header` (`.wordmark`, `.site-nav`, `.header-cta`) · `.hero` (`.hero-copy`, `.eyebrow`, `.hero-lede`, `.hero-actions`, `.hero-foot`, optional `.hero-visual` with `.hero-core`, `.hero-float-top/-bottom`, `figure.portrait`, `.visual-caption`) · `.marquee > ul.marquee-track` · `.intro-band` · `.work-section` + `.project-list > a.project-card` (`.project-art`, `.project-info`) · `.impact-section` + `.impact-grid > div > strong + p` · `.approach-section` · `.contact-section` · `.page-hero`, `.about-quote`, `.timeline > .timeline-row`, `.capabilities`, `.capability-grid`, `.education`, `.chip-list` · case pages: `.case-hero` (`.back-link`, `.case-intro dl`), `.case-art-frame`, `.case-body` (`.case-text`, `.case-result`), `.page-next` · `.site-footer` · `.atlas-appear` on anything that should reveal on scroll.

**Artwork.** Artwork is generated in CSS and carries no person-specific content. Put `data-art="orbit|grid|waves|stack|bars|dots"` and `data-tone="1-4"` on `.project-art` / `.case-art-frame`, or omit them and `theme.js` assigns a rotation. Text inside the art (`.art-corner`, `.art-bottom`, `.art-pop`) is plain content. An `<img>` inside the slot replaces the generated art, shows a skeleton while loading, and falls back to the art if it fails.

**Profile picture (optional).** Add `<figure class="portrait"><img src="…" alt="Name"></figure>` (`src` can be any URL) in the hero's `.hero-visual` (a full-bleed photo with the theme's chips layered over it) and/or in the About hero's right-hand column (a round avatar). It always looks finished, in three states:

| State | Markup | Result |
| --- | --- | --- |
| Photo | `<figure class="portrait"><img …></figure>` | The photo, cropped to the slot (`object-position` favours faces), with a skeleton while it loads. |
| No photo | `<figure class="portrait"></figure>` (or leave the figure out) | A generated avatar: gradient, rings and the person's **initials**, derived from the wordmark (or set `data-initials="MK"` yourself). Without a figure the hero keeps its orbit artwork. |
| Photo fails | the `<img>` 404s or is blocked | Switches to the initials avatar automatically; the page never shows a broken-image icon. |

**Opt-outs.** `data-no-split` on a heading skips the word-reveal. `data-intro="off"` on `<body>` disables the intro loader; `data-intro="on"` forces it.

## What the theme does

- **Routing.** Hash routes with Back/Forward, per-view scroll restoration, focus moved to the new heading, an `aria-live` announcement, a `document.title` per view, and the right nav item highlighted (a case page highlights the link its `.back-link` points to). Same-document View Transitions crossfade routes and morph a project card's artwork into the case-study artwork. Unknown hashes fall back to the home view.
- **Loading states.** A bounded intro loader (short, skipped on repeat visits and under reduced motion), a route progress bar, image skeletons with error fallbacks, and a boot veil that holds the first paint until headings are fitted and fonts are in so the page never visibly re-flows.
- **Motion.** Word-by-word headline reveals, staggered scroll reveals, count-up statistics (the final text is always preserved), spotlight/tilt/magnetic effects on fine pointers only, an animated mesh-gradient hero, a skills marquee, scroll-linked timeline and progress bar, scroll-driven parallax where supported.
- **Navigation chrome added by JS.** Floating glass header with a sliding active indicator, mobile menu, light/dark toggle (follows the OS; circular View-Transition reveal), back-to-top, case-study table of contents with scroll-spy, and a **command palette** (`Ctrl/⌘ + K` or `/`) listing every page and section.
- **Robust to content.** Headline size tiers from text length, `overflow-wrap`/`min-width: 0` everywhere, quantity-aware layouts (1 to many projects, 1 to many stats), container-query cards, numerals sized from tile width and character count, empty sections hidden.
- **Accessibility.** Skip link, visible focus, 24 px targets, reduced-motion support (everything visible, loops off), `prefers-contrast`, `forced-colors`, print styles.

## Fonts, images and other resources

Nothing is bundled. Fonts come from Google Fonts through the `@import` at the top of `style.css` (Geist, Geist Mono, Instrument Serif); images and anything else in the page can be loaded from any URL. If the network or Google Fonts is unreachable the page still works: metric-matched fallback faces (measured against the real fonts) take over, so layout does not move. Styles set by JavaScript go through `element.style.setProperty`, the script makes no network calls and uses no `eval`, and storage access is wrapped so the theme also works where `localStorage` throws.

The Studio's current preview policy is stricter than this (`font-src 'self'`, `style-src 'self'`, `img-src 'self'`), so a page using Google Fonts or remote images would be blocked there and fall back to the system faces. That is a separate integration decision; the theme itself does not depend on it.

**Automated visitors.** When `navigator.webdriver` is true (screenshots, link checkers, host verification) the theme skips the intro and never hides content waiting for a reveal, so they see the finished page. Add `?atlas-motion=1` to exercise the motion layer under automation, `?intro=1` to force the loader, and `?atlas-debug` to log `AtlasTheme.audit()`.

**No JavaScript.** Every view stays in the document in order, links work, and the nav is visible (`@media (scripting: none)`). With scripting enabled the first paint is held only until `theme.js` sets `html[data-boot]`; a CSS-only timer lifts the hold if the script never runs.

`window.AtlasTheme` exposes `audit()` (contract problems: duplicate ids, links with no target, views without one `h1`, images without `alt`, heading-level jumps), `go(id)`, `setTheme(mode)`, `openPalette()` and `ready` (a promise).

## Customising

Change tokens in the `tokens` layer at the top of `style.css`: neutrals, `--accent`, `--volt`, `--tone1…4-*` (artwork), radii, type scale, motion curves. Colours use `oklch()` with `light-dark()`, so a light and a dark value live side by side.

**Changing fonts** takes two edits: replace the Google Fonts `@import` at the top of `style.css` with any other (a premium host, Adobe Fonts, your own `@font-face`), and update the `--font-sans`, `--font-serif` and `--font-mono` tokens. The `size-adjust` fallback faces next to the import were measured against the current fonts, so re-measure them if you change typefaces (or delete them; the only cost is a small layout shift while a new font loads).

## Browser support

Baseline 2024 features are used directly (`@layer`, `light-dark()`, `:has()`, container queries, `@property`, `color-mix()`, `text-wrap`). Newer features are enhancements only and fall back to the same content without them: scroll-driven animation (Firefox stable lacks it, so JS drives the progress bar), same-document View Transitions (a plain route swap otherwise), `@starting-style`, `backdrop-filter`.

## Verification

```powershell
.workspace/venv/Scripts/python.exe "docs/HTML and CSS/TEST/cobalt-atlas/verify/verify.py" --axe path\to\axe.min.js --shots <dir>
```

The harness serves this folder over plain HTTP and drives Chromium with Playwright. It first checks the theme really is two files (pages reference only `style.css` and `theme.js`, no stray folders, no network calls in the script) and that the Google Fonts actually loaded (this needs a network connection). For every fixture × width × colour scheme × route it checks console errors, failed requests, horizontal overflow, one visible `h1`, layout shift and size budgets. It then runs the modes: no-JS, reduced motion, motion + intro loader, routing (deep links, odd hashes, history, skip link, TOC), keyboard (palette, tab order, mobile menu), an axe-core pass, and a pixel-based contrast audit that samples the real background behind every text node. `axe.min.js` is a test-only download and is not shipped. Use `--matrix` or `--modes <names>` to run a subset, and `--csp` to emulate the Studio's old strict policy and sandbox.

## Limits

- The artwork is abstract CSS, not product screenshots, and the fixtures are invented.
- Integrating this into OryxenAI Studio still requires the separate steps in [RESEARCH.md](./RESEARCH.md): a pinned theme package, a generated-HTML contract, validator rules for scripts and routes, and a decision on whether the preview policy allows external fonts and images. This folder does not change the Studio.
- UI strings added by `theme.js` (button labels, palette hints) are English.
