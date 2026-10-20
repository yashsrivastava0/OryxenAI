# Theme Authoring Guide — structuring a new portfolio design

How to add a new look to OryxenAI without touching the agents' behaviour. It is
theme-neutral: it describes structure, responsibilities and integration points,
not any particular palette, font or layout. Check `DECISIONS.md` before changing
any rule below, and record material choices there.

## 1. The core idea

A design is an **immutable, pinned theme package**. Everything that is *wording*
comes from the approved `page_content`; everything that is *look and behaviour*
comes from the theme. The agents never negotiate between the two:

```text
Explorer (Discovery)  -> picks a palette card -> deterministic pinned theme id
Content Architect     -> writes theme-agnostic page_content (never reads a theme)
Studio (Code Gen)     -> theme.render_body(page_content) -> validate -> seal -> verify -> preview
```

Design consequences:

* A new theme must not require prompt, agent or schema changes in the normal case.
* The theme id travels with the session through build, versions, chat edits,
  restore and preview. Never infer the theme from content.
* A released theme version never changes. A design change after release is a new
  version (`v2`), because the manifest pins bytes.

## 2. Package structure

One folder per family and version: `src/oryxenai/themes/<family>/v<N>/`.

| File | Role |
| :--- | :--- |
| `manifest.json` | Theme id, display name, contract version, stylesheet/script names, capabilities (`javascript`, `generated_css`), optional `runtime.global`, and a SHA-256 + byte pin for every shipped file. Verified on load; any drift raises. |
| `contract.py` | The markup contract: allowed tags/attributes, host-owned chrome strings, derivation of host-computed hints, closed-world validation, `<head>` rendering, exemplar. |
| `body.html.j2` | Pure template: body HTML as a function of `page_content` plus derived values. |
| `contract_rules.md` | Human-readable rules (used when a model-written body is the fallback). |
| `style.css`, `theme.js` (optional) | All look and behaviour. Fonts self-hosted under `assets/`, with their licences. |

Register the module in the theme registry (`src/oryxenai/themes/__init__.py`).
Nothing enrols themes automatically, including tests.

## 3. The contract (what makes it safe)

* **Host-rendered body.** Implement `render_body` so the page is deterministic,
  needs no model call and cannot miscopy approved wording. A theme without it
  falls back to one model call; avoid that for new designs.
* **Closed-world validation.** The rendered body is checked strictly and never
  auto-repaired:
  * every visible text node and `aria-label` must equal an approved string
    (content strings plus the contract's small, enumerated chrome list);
  * tags and attributes come from allow-lists; no inline `style`, `on*`,
    `srcset`, `title`, or similar;
  * every class used must exist in `style.css`;
  * `data-field` bound text must equal its source value; every `#anchor` must
    resolve; HTML must parse strictly (no self-closing non-void tags).
  Consequences: do not split text into per-word or per-letter markup on the
  server (split at runtime in JS, word level only); use CSS counters for
  numerals; keep chrome strings few and language-neutral.
* **Derive, don't ask.** Anything computable from content (initials, size
  classes for long names, which illustration variant a project gets, sample
  flags) is computed by the contract so it cannot drift from the content.
* **Host-owned `<head>`.** Title, description, colour-scheme, direction for
  right-to-left languages, an inert icon (so no 404 is counted as a failure),
  the stylesheet link and the pinned script. The model or owner never writes it.
* **Routes.** If the theme is multi-view, use fragment routes that match the
  verifier contract (one home view plus others, only one visible at a time,
  focus moved to the heading, a live-region announcer). Create a route only
  when its content is genuinely specific; do not render empty pages.
* **Labels for non-real material.** Sample or illustrative content must carry a
  visible label, enforced by `validate_body`.

## 4. Look and behaviour rules

* **No photo required.** Every section must look finished without an image;
  design CSS art, monograms and typography as the default and make image slots
  progressive (an image replaces the fallback; a load error restores it). Add
  `img` to the contract only when the asset pipeline exists.
* **Progressive enhancement.** Layer 0 is complete HTML/CSS and readable with
  scripting off. Layer 1 is CSS motion gated by `prefers-reduced-motion`.
  Layer 2 is `theme.js`. Automation (`navigator.webdriver`), reduced motion and
  no-script all get a finished, static page; provide an explicit opt-in to see
  full motion in tests.
* **Motion that degrades.** If using scroll-driven animation, keep one
  keyframes definition with two drivers (native timelines where supported, a
  JS scrubber elsewhere) and test both. Only animate transform/opacity-class
  properties, provide a pause control for continuous motion, keep native
  scrolling (no scroll hijacking), and never let a visual effect hide content
  from assistive technology.
* **Accessibility and i18n.** One `h1` per view, skip link, landmarks, visible
  focus, adequate contrast in every colour scheme, `forced-colors` and print
  rules, logical CSS properties, and tolerance for very long, short, empty and
  right-to-left content.
* **Performance.** Self-host fonts with metric-matched fallbacks, avoid layout
  shift, no libraries or network, and stay inside the size budgets enforced by
  the theme tests.

## 5. Preview sandbox constraints

Scripted themes are served with a strict policy: scripts and styles from
`'self'` only, no inline style (use CSSOM `style.setProperty`), fonts and images
from `'self'`/`data:`, no network, an opaque origin (so `localStorage` and
similar throw: wrap in try/catch with an in-memory fallback), and no
same-origin privileges. Generated or user-written scripts are not allowed; only
the reviewed, pinned `theme.js` runs. Pitfalls:

* String-based waits in the browser driver (`wait_for_function("...")`) are
  blocked by this policy; poll with `evaluate` instead.
* The CSS class extractor treats a bare statement at-rule (such as
  `@layer a,b;`) placed directly before a style rule as swallowing that rule's
  classes. Start the stylesheet with `@font-face` blocks or use block form.
* Sticky scene stages must not sit inside `overflow: hidden|auto|scroll`
  ancestors (use `overflow: clip`).

## 6. Integration with each agent

### 6.1 Discovery (Explorer)

* The visual question is appended by the server after the model-authored
  questions. Palette choices map **deterministically** to a pinned theme id; the
  optional mood note never changes that mapping and never enters the factual
  dossier.
* Add one palette entry per look in `agents/discovery/palette.py`: stable id,
  label, short description, swatches, and target theme id. Expose it only once
  the theme loads and is sealed.
* Themes that use the extended content (see 6.2) enable one extra optional
  question for project details and explicit permission for a labelled
  illustrative concept. This is driven by the shared predicate, not by a
  theme-name check.
* The frontend picker (`frontend/src/data/adapters/discovery.ts`, the card
  component, `shell.css` demo styles, tests) must render the new card at every
  width without clipping; check the card cap, the grid, and any budget test.

### 6.2 Content Architect

* It writes the shared `page_content` tree and, for themes that declare it, the
  extended supplement (About, experience, education, statistics, projects).
  Its prompts **never read a theme package**; they stay theme-neutral.
* A theme opts into the extended supplement by being listed with the shared
  predicate in `src/oryxenai/themes/__init__.py` (`uses_atlas_content` over the
  registered ids). Every gate (admission, agent, service, prompt builder,
  Discovery) must call that predicate, never a literal theme id.
* If a design needs a field the tree lacks, change the shared schema, prompts
  and every theme deliberately, and record the decision. Do not smuggle
  theme-specific fields in. Hard length/count limits live in admission; design
  the layout to survive the maximum and the minimum of each field.
* Writing guidance (outcome-first, proof before adjectives) belongs in the
  shared prompts and affects every theme.

### 6.3 Code Generator (Studio)

Flow: admission (counts and lengths, no model call) -> produce body
(`render_body`) -> strict validation -> seal (host head + body, hashed) ->
browser verification (policy-controlled) -> promote (one transaction). One
durable job, no automatic retry or repair; a failure is reported exactly.

* The browser verifier drives a runtime object in the page. The manifest's
  `runtime.global` names it (default exists); expose a small frozen API with the
  navigation and readiness the verifier expects, set the router-ready flag
  synchronously, and toggle view visibility synchronously (transitions are
  cosmetic only).
* Verification counts console errors, page errors, failed or external requests
  and an unapplied stylesheet. Log only through debug-gated warnings.
* Chat edits change **content** through whitelisted typed operations; the theme
  is never rewritten per user.
* Production verification may be disabled in some deployments, so the theme's
  own CI browser tests are the real safety net. Never claim runtime
  verification you did not run.

## 7. Sealing and release

1. Develop with a dev seal: regenerate `manifest.json` file pins after every
   CSS/JS/font edit (`compute_manifest_files`). Pages built from older bytes
   stop serving, so do not point a long-lived dev database at an unfinished theme.
2. Do not add the Explorer card until the theme loads and passes its tests.
3. Visual review by the owner before release; after release, changes mean a new
   version.

## 8. Test checklist (add per theme)

* Unit: manifest drift, line endings, class vocabulary, exemplar vs
  placeholders, closed-world rejection of injected markup/scripts, routes,
  sample/illustrative labels, deterministic double render, size budgets, font
  magic bytes and licences, registry sanity.
* Fixtures: typical, sparse, and hostile content (very long names, right-to-left
  and CJK text, maximum rows, empty sections), all within admission limits.
* Browser (Chromium, served with the real preview headers): light and dark,
  phone/tablet/desktop widths, every route, both scroll drivers, no script,
  reduced motion, automation mode, keyboard navigation and history, contrast,
  layout shift, zero console/CSP/request errors, fonts actually loaded, phone
  header fits on one line. Optionally an accessibility engine run (test-only).
* Integration: picker shows the card and selection pins the theme id; the shared
  content gate is true for the theme; the real verifier path passes; API flows.
* Optional and opt-in: other browser engines; a live end-to-end run with real
  model calls (costs spend, ask first).

## 9. Do / don't summary

* Do keep wording in content and look in the theme; derive hints in the contract.
* Do make every state complete without images, scripts or motion.
* Do keep agents theme-neutral and route all gating through shared predicates.
* Don't hardcode theme ids, model names or counts in business logic or prose.
* Don't split text server-side, add inline styles, load external resources, or
  let a failed build replace the live page.
* Don't edit released theme bytes; version instead.
* Don't add automatic stage chaining, retries or repairs; those are deliberate,
  documented changes.
