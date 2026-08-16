# Recreate this site as a single HTML file: Baseline — Tennis Club & Academy

You are an expert creative front-end developer. Produce a single self-contained `index.html` that reproduces the project below exactly — same layout, sections, visuals, motion, and interaction. Pure HTML/CSS/JS in one file: no build step, no framework, no bundler. Use ES modules with a CDN importmap for the one library used (Lenis, for smooth scroll). Hardcode every value given here as a fixed constant. Reproduce all spring/text animation with plain JS (a tiny rAF spring helper) and CSS — same feel, no React, no @react-spring, no spring-text-engine.

## What it is

A single-screen-then-scroll marketing landing page for **"Baseline" — a members' tennis club & academy** ("Baseline Tennis Club & Academy"). The look is editorial and confident: a deep-navy full-bleed hero with a parallax on-court photo, an oversized uppercase headline that reveals word-by-word from behind a clipping mask, then a stack of light/dark sections (a "trusted by" coach carousel with giant ghost words, a numbered programs list, two tilted court photo cards, a 4-up stats band on navy, a 3-up testimonials grid, and a navy footer). It opens with a **navy intro loader** (wordmark + a filling progress bar) that slides up to reveal the hero, at which point the hero's text and cards animate in. Smooth scrolling is driven by **Lenis**. Motion everywhere is spring-based: scroll-triggered reveals (clip-mask slide-ups, fade-and-rise), hover micro-interactions (arrows nudge, cards lift/scale, icons rotate/scale), parallax tied to scroll progress, and two auto/manual carousels.

The whole layout is **rem-based and adaptively scaled**: the root `font-size` is recomputed from the viewport width so the design stays proportional at every size (scales down below 1920px via `vw` media queries, scales up above 1920px via JS). Treat almost every dimension as `rem`.

## Page shell & libraries

- **One library:** [Lenis](https://github.com/darkroomengineering/lenis) for smooth scroll, via ES-module importmap:
  ```html
  <script type="importmap">
  { "imports": { "lenis": "https://cdn.jsdelivr.net/npm/lenis@1.1.18/+esm" } }
  </script>
  ```
  Init: `const lenis = new Lenis({ smoothWheel: true })` and drive it with a `requestAnimationFrame` loop (`function raf(t){ lenis.raf(t); requestAnimationFrame(raf) } requestAnimationFrame(raf)`). Expose `lenis.start()` / `lenis.stop()` to lock scroll for the loader / open menu / open modal (also toggle native scroll by setting `html { position:relative; overflow:hidden; height:100% }` while locked, and removing those props when unlocked). On first load call `window.scrollTo(0,0)`.
- **Font:** Google Font **Onest** (`display=swap`, latin), all weights used are 400 (default) and 500 (`font-medium`). Load via `<link>` to `https://fonts.googleapis.com/css2?family=Onest:wght@400;500&display=swap`. Set `font-family: "Onest", system-ui, sans-serif` on `body`.
- **CSS reset:** box-sizing border-box on everything; zero default margins; images `display:block; max-width:100%`; `body { min-height:100vh; background: var(--background); color: var(--foreground); }`. Buttons get `cursor:pointer`. Use `:focus-visible { outline: 2px solid var(--brand-light); outline-offset: 2px; }` as a focus fallback.
- **Background / page frame:** `<body>` background is white (`#ffffff`). The whole page content lives in a `<main>` with **padding `0.5rem` (mobile) / `0.75rem` (≥640px)** around it (`p-2` / `sm:p-3`) — this inset is what gives the hero and dark sections their rounded "card" framing against the white page. `<main>` is `width:100%; overflow-x:clip`.
- **Adaptive rem grid (critical — bake this in exactly):**
  - `FONT_BASE = 16`. Design base width = 1920.
  - Base rule: `html { font-size: 16px }`.
  - Scale-DOWN media queries (each = `16 * 100 / baseWidth` vw):
    ```css
    @media (max-width: 1920px) { html { font-size: 0.833333vw; } } /* base 1920 */
    @media (max-width: 1440px) { html { font-size: 1.111111vw; } } /* base 1440 */
    @media (max-width: 1024px) { html { font-size: 1.5625vw;  } }  /* base 1024 */
    @media (max-width: 640px)  { html { font-size: 4.444444vw; } } /* base 360  */
    ```
  - Scale-UP (viewport wider than 1920): in JS, on load + resize, set `html.style.fontSize`:
    ```js
    const FONT_BASE = 16, BASE_W = 1920, COEF = 0.6666;
    const reduction = ((BASE_W - innerWidth) / BASE_W) * 100 * COEF;
    const size = FONT_BASE - (FONT_BASE * reduction) / 100;
    if (size > FONT_BASE) html.style.fontSize = size + "px"; else html.style.removeProperty("font-size");
    ```
    (Above 1920 `reduction` is negative so `size > 16` and it scales up; at/below 1920 it clears the inline size and the media queries drive.)
  - Because of this, **all spacing/typography below is in `rem`** (1rem = 16px at design width). Where the source used Tailwind tokens I give you the resolved rem/px values.

### Tailwind token → value map (the source was Tailwind v4; resolve these)
Spacing scale: `1` = 0.25rem, `1.5`=0.375rem, `2`=0.5rem, `3`=0.75rem, `4`=1rem, `5`=1.25rem, `6`=1.5rem, `7`=1.75rem, `8`=2rem, `10`=2.5rem, `11`=2.75rem, `12`=3rem, `14`=3.5rem, `16`=4rem, `20`=5rem, `24`=6rem. Sizes (`size-N`,`w-N`,`h-N`) use the same scale. `text-xs`=0.75rem, `text-sm`=0.875rem, `text-base`=1rem, `text-lg`=1.125rem, `text-xl`=1.25rem, `text-2xl`=1.5rem, `text-3xl`=1.875rem, `text-4xl`=2.25rem, `text-5xl`=3rem, `text-6xl`=3.75rem, `text-7xl`=4.5rem. Radii: `rounded-xl`=0.75rem. Breakpoints: `sm`=640px, `md`=768px, `lg`=1024px. `svh` = small viewport height unit (`100svh`).

### Palette (CSS variables on `:root`)
```css
--background:#ffffff;  --foreground:#0a0a0a;
--brand:#2563c9;       /* primary royal blue */
--brand-deep:#0f2f63;  /* deep navy — hero/stats/footer base */
--brand-light:#5790e6; /* light blue accent / focus ring */
--accent-teal:#0b6e97; /* blue court caption tint */
--surface:#f4f4f4;     /* off-white section bg */
--surface-card:#ffffff;
--ink:#0a0a0a;         /* near-black headings */
--ink-soft:#717784;    /* muted body */
--ghost:#d7dae1;       /* oversized ghost text */
--hairline:#e6e8ec;    /* subtle borders */
--on-brand:#ffffff;    /* text on navy */
/* radii */
--radius-card:1.5rem; --radius-card-lg:2rem; --radius-pill:62.5rem;
```
`text-on-brand/70` etc. mean white at that opacity (use `rgba` or `color-mix`/opacity). `bg-on-brand/15` = white @ 15%, `border-on-brand/15` = white @ 15%, `bg-brand-deep/40` = navy @ 40%, etc. Reproduce these alpha tints faithfully.

### Tiny spring helper (use for all JS-driven motion)
Implement a minimal critically-tunable spring per animated property, integrated in the rAF loop, matching react-spring's `{ tension, friction }` model:
```js
// step a value toward target: v += (-tension*(x-target) - friction*v) * dt; x += v*dt;
```
Drive transforms/opacity from these. For entrance reveals you may instead use CSS transitions with the easings below — match the *feel* (clip-mask slide-up, fade+rise). For scroll-progress parallax, map the element's viewport position (top=bottom → 0, bottom=top → 1) to the `from`→`to` value and apply each frame.

### Easings (named, used by the text/loader reveals)
- `easeOutExpo` — for word/line clip-mask reveals (hero title, stacked lines, ghost words).
- `easeOutQuart` — facilities body word fade.
- `easeInOutCubic` — loader progress fill + loader curtain slide-up.
Durations are given per block below (in ms). Where a spring `config` is given as `{tension, friction}`, use the spring helper; where given as `{duration, easing}`, use a timed CSS/JS tween.

### Reveal primitives (replicate these three behaviors)
1. **Clip-mask word/line reveal ("TextEngine" / "StackedLines"):** wrap each word or line in an `overflow:hidden` box; the inner span starts at `translateY(115%)` (lines) / `translateY(115%)` words with `opacity:0` and animates to `translateY(0) opacity:1`. Add `padding-bottom:0.14em` (lines) / line padding `0.12em` (ghost words) on the clip box so descenders aren't cut. Words/lines **stagger**. Re-fire when content changes (carousels) by re-running the reveal on the new text.
2. **In-view reveal ("Inview"):** element starts at the `from` state (e.g. `{opacity:0, y:28}`) and springs to `to` (`{opacity:1, y:0}`) the first time it enters the viewport (play **once**), after an optional `delayIn`. Use an IntersectionObserver to trigger.
3. **Hover spring ("Hover"):** on pointer-enter animate to `to`, on leave back to `from`, using the given `{tension,friction}`. **Disabled on mobile** (viewport ≤ 768px) — no hover effects there.

---

## Layout & sections (in order)

Page order inside `<main>` (each top-level section is a rounded card / band separated by the `0.5–0.75rem` page inset and small `mt-3` (0.75rem) gaps where noted): **Hero → Trust → Programs → Facilities → Stats → Testimonials → Footer**, plus a portaled **Contact modal** and a **fullscreen menu overlay** triggered from the header.

### 1) Site header (inside the hero, transparent over the photo)
DOM: a `<header>` flex row, `padding: 1.5rem 1.5rem 0` (mobile) / `2rem 2.5rem 0` (≥640px), `text-xs` (0.75rem), white text.
- **Left nav** (hidden below `lg`/1024px), `flex-1`, gap `2rem`: links `Programs & Coaches` (`#programs`), `Club & Events` (`#facilities`). White @ 90% opacity, →100% on hover; smooth-scroll to anchor on click.
- **Center brand** (`flex-1`, centered on ≥lg): a tennis-ball SVG mark + the word **Baseline**. `text-base` (1rem), `font-medium` (500), `uppercase`, `letter-spacing:0.2em`, gap `0.5rem`. Mark = `size-5` (1.25rem). The mark SVG (`viewBox 0 0 24 24`, stroke `currentColor`, `stroke-width:1.8`, round caps, fill none):
  ```svg
  <circle cx="12" cy="12" r="9"/>
  <path d="M4.8 5.6A9 9 0 0 0 4.8 18.4"/>
  <path d="M19.2 5.6a9 9 0 0 1 0 12.8"/>
  ```
- **Right** (`flex-1`, justify-end, gap `1rem`/`1.25rem`): a text button **"Book a Visit"** (hidden below `sm`, uppercase, tracking-wide, underline on hover) that opens the **Contact modal**; and a **burger button** — `size-10` (2.5rem) grid, `rounded-pill`, `background: white @15%`, `backdrop-blur`, hover white @25%; contains two stacked 1px-tall, `width:1rem` white bars with `5px` gap. Clicking it opens the **fullscreen menu overlay**.

### 2) Hero section
`<section>` deep-navy (`--brand-deep`), white text, `position:relative; isolate; overflow:hidden`, `border-radius: var(--radius-card-lg)` (2rem). Height: `calc(100svh - 1rem)` (mobile) / `calc(100svh - 1.5rem)` (≥640px), `min-height:36rem`. Flex column.
- **Parallax background plate** (`absolute inset-0; z-index:-10`): an inner layer sized `position:absolute; left/right:0; top:-16%; height:132%; width:100%` holding the hero image **`hero/hero-court.webp`** (`object-fit:cover`, full size), alt "Player lunging for a shot on a hard court". The inner layer is **scroll-parallaxed** from `translateY(0%)` → `translateY(12%)` across the section's scroll progress (oversized + shifted up so the shift never exposes an edge). Over the image, a top-to-bottom gradient overlay: `linear-gradient(to bottom, rgba(15,47,99,0.65), rgba(15,47,99,0.35), rgba(15,47,99,0.75))`.
- Header (above) sits at the top.
- **Giant title** block: `padding: 1rem 1.5rem 0` (mobile) / left/right `2.5rem` (≥640px). One `<h1 id="hero-title">` with text **"Own The Court"** (the source joins `titleLines` with a space). Style: `font-size:12.5vw`, `font-medium` (500), `uppercase`, `line-height:0.85`, `letter-spacing:-0.02em` (tight), `white-space:nowrap`. **Reveal:** word-by-word clip-mask slide-up (`wordOut {y:115%,opacity:0}` → `wordIn {y:0,opacity:1}`), **wordStagger 140ms**, per-word **duration 1100ms, easing easeOutExpo**. **Gated by the loader:** it stays hidden until the loader flips `ready=true`, then plays in.
- **Bottom row** (`margin-top:auto`, `padding: 0 1.5rem 2rem` mobile / `0 2.5rem 2.5rem` ≥640px): a flex that is column on mobile, row space-between & items-end on ≥sm, gap `1.5rem`.
  - **Tagline**: a `<p>` of two stacked clip-mask lines **"Show Up,"** / **"Level Up"**. Style: `font-size:2.4rem`, `font-medium`, `uppercase`, `line-height:0.95`, tight tracking, color white @85%. Reveal = stacked-lines (clip-mask slide-up), **baseDelay 350ms, stagger 110ms, duration 900ms, easeOutExpo**, gated by loader.
  - **Right cluster** (flex, items-end, gap `1rem`):
    - **Collection slider** (hidden below `md`/768px, `width:16rem` column, gap `0.75rem`): an auto-advancing card carousel over 3 collections. The card: flex row, gap `0.75rem`, `rounded-card`(1.5rem), `border: 1px white@15%`, `background: white@10%`, `padding:0.75rem`, `box-shadow` navy@20%, `backdrop-blur`. Left: a `3.5rem` square (`rounded-xl`) image; right: brand (`0.7rem`, medium, uppercase, tracking-wide), title (`0.7rem`, uppercase, opacity 80%), and a small underlined CTA link `"{cta} →"` (`0.65rem`). The three slides (image, brand, title, cta):
      1. `2.webp` — brand **"Baseline Pro"**, title **"Featured Gear"**, cta **"Shop the kit"**, alt "Player driving a backhand on a hard court".
      2. `3.webp` — **"Court Series"**, **"Summer Drop"**, **"View the line"**, alt "Player stretching for a forehand on clay".
      3. `5.webp` — **"Academy Kit"**, **"Junior Range"**, **"Browse juniors"**, alt "Player set in a ready stance on clay".
      Autoplay **interval 3800ms**, wrap-around, **gated on loader ready**. Each advance **cross-fades** old→new card (cache outgoing, fade out `{opacity:0,y:16,scale:0.96}` → fade in `{opacity:1,y:0,scale:1}`, config `{tension:210,friction:24}`). Below the card, **carousel dots** (see component) tone="light", 3 dots. The whole slider also does an Inview rise-in on first reveal: `from {opacity:0,y:28}`→`to {…,y:0}`, **delayIn 650ms**, config `{tension:200,friction:26}`.
    - **Membership card** (Inview rise-in, **delayIn 780ms**, same config): `<article>`, `width:100%` max `20rem` (mobile) / `15rem` (≥sm), same glassy style (border white@15%, bg white@10%, p `0.75rem`, rounded-card, shadow, blur), flex row gap `0.75rem`, items-stretch. Left column space-between: big value **"9K+"** (`text-3xl`/1.875rem, medium, line-none); a row of four overlapping `1.25rem` circles (`-space-x-2`, each `rounded-pill`, `1px` border navy@40%) with backgrounds **`#5790e6`, `#c2e029`, `#0b6e97`, `#ffffff`**; caption **"Members on court"** (`0.65rem`, opacity 80%). Right: a `4rem`-wide `aspect-[3/4]` `rounded-xl` image **`1.webp`**, alt "Player waiting to return on a clay court".

### 3) Trust section ("Trusted by serious players")
`<section>` white background (`--background`), `position:relative; isolate; overflow:hidden`, `padding: 4rem 1.5rem` (mobile) / `5rem 2.5rem` (≥640px). It's a **coach carousel** over 3 slides; switching the slide re-fires the ghost-word reveals and cross-fades the coach photo.
- **Top badges row** (`z-20`, column→row, space-between on ≥sm):
  - A **percentage badge**: `size-28`(7rem)/`size-32`(8rem ≥sm) circle (`rounded-pill`), `background: --surface`, centered text: **"100%"** (`text-2xl`, medium) over caption **"Coaching built around your game"** (`0.6rem`, `--ink-soft`, max-width `7em`). Inview reveal `from {opacity:0,scale:0.9}`→`{…,scale:1}`, config `{tension:220,friction:22}`.
  - A **badge card** `<article>` (max-width `28rem`, gap `1rem`/`1.25rem`, `rounded-card`, bg `--surface`, padding `1.25rem`/`1.5rem`): a square index chip **"#01"** (`rounded-xl`, bg `--background`, padding `0.5rem 1rem`, `text-xl`, medium) + a title **"Trusted by serious players"** (`text-lg`, medium) and body **"From first-timers to nationally ranked juniors, players train here because the progress shows up on the scoreboard."** (`text-xs`, `--ink-soft`, relaxed leading). Inview reveal `from {opacity:0,y:24}`→`{…,y:0}`, **delayIn 120ms**, config `{tension:200,friction:26}`.
- **Oversized ghost heading** (`<h2 id="trust-title">`, `pointer-events:none; z-0; user-select:none`, max-width `88rem`, margin-top `3rem`, centered): `font-size:8.2vw`, medium, uppercase, `line-height:1.02`, tight tracking. Two rows, each a flex `justify-between` of two **ghost words**. Words come from the active slide's `headline` (4 words, 2 rows of 2). Word 3 (bottom-left) is **ink-colored** (`--ink`); the other three are **ghost-colored** (`--ghost`). Each word does the clip-mask slide-up reveal (**duration 700ms, easeOutExpo**) and **re-fires when the slide changes**. Each word also gets a small opposing **scroll parallax** on X: top-left `x:-3%→3%`, top-right `x:3%→-3%`, bottom-left `x:-2%→4%`, bottom-right `x:4%→-3%` (mapped across section scroll).
  - Slide headlines: **slide 1** `["Expert","Result-","Driven","Coaching"]`, **slide 2** `["Sharper","Faster","Stronger","Player"]`, **slide 3** `["Future","Champions","Start","Here"]`. (Layout order per row: `[w1 w2]` / `[w3 w4]`; w3 = ink.)
- **Center coach card** (`z-10`, centered; on ≥sm absolutely centered at the section's middle via `left/top:50%` + translate; `width:13rem`/`16rem` ≥sm): a `<figure>` with a **static `6deg` rotation**, `aspect-[3/4]`, `rounded-card`, `bg --brand`, `overflow:hidden`, holding the coach image (`object-cover`) and a glass caption (`absolute inset-x-3 bottom-3`, `rounded-xl`, `bg navy@40%`, white text, `backdrop-blur`, padding `0.5rem 0.75rem`): name (`text-sm`, medium) + role (`0.65rem`, opacity 80%). Inview reveal `from {opacity:0,y:60,scale:0.92}`→`{…,y:0,scale:1}`, config `{tension:170,friction:26}`. On slide change, **cross-fade the photo** (`{opacity:0}`→`{opacity:1}`, config `{tension:260,friction:26}`).
  - Slides (image, name, role, alt): **1** `5.webp`, "Marco Vidal", "Head Coach", "Head coach set in a ready stance on clay"; **2** `4.webp`, "Elena Sokolova", "Performance Coach", "Performance coach following through on a serve"; **3** `1.webp`, "James Okoro", "Juniors Lead", "Juniors lead waiting to return on clay".
- **Carousel controls row** (`z-20`, margin-top `3rem`/`6rem` ≥sm, space-between): a **prev arrow button** (variant outline), **carousel dots** (3, dark tone, active index), a **next arrow button** (variant solid). Prev/next cycle the slide (wrap-around), dots jump to index. Each control change re-fires the ghost-word reveals + photo cross-fade.

### 4) Programs section
`<section id="programs">` background `--surface`, `padding: 6rem 1.5rem` (mobile) / left/right `2.5rem` (≥640px), `py-24`(6rem).
- Header: an **Eyebrow** (component) reading **"Training programs"** (dark tone), then an `<h2 id="programs-title">` stacked-lines **"Built for"** / **"every level"** (`text-5xl`/3rem, medium, line-height 0.95, tight, margin-top `1rem`).
- A `<ul>` (`margin-top:3.5rem`) of **4 program rows**, each an `<a>` (`href` given) with a top border `1px --hairline` (last row also bottom border), focus bg `--background`. Inside each: an Inview rise-in `from {opacity:0,y:26}`→`{…,y:0}`, **delayIn = rowIndex × 90ms**, config `{tension:190,friction:26}`, laid out as a flex row gap `1.5rem`, `padding: 1.75rem 0`, items-center:
  - index number (`width:2.5rem`, `text-sm`, medium, `--ink-soft`),
  - name (`text-2xl`→`text-3xl` ≥sm, medium, tight) + description (`text-sm`, `--ink-soft`),
  - a trailing `size-11`(2.75rem) circle (`rounded-pill`, `1px --hairline` border) holding a right-arrow SVG. On **row hover**, the arrow group springs `from {x:0,opacity:0.55}`→`to {x:8,opacity:1}`, config `{tension:300,friction:20}`.
  - Rows (index, name, description, href):
    1. `01` **Junior Development** — "Fundamentals, footwork, and match play for ages 6–14." (`#junior`)
    2. `02` **Performance Squad** — "High-volume training for competitive and ranked players." (`#performance`)
    3. `03` **Adult Clinics** — "Small-group sessions to sharpen technique and fitness." (`#adult`)
    4. `04` **Private Coaching** — "One-to-one sessions tailored to your goals and schedule." (`#private`)
  - Arrow SVG (`viewBox 0 0 24 24`, fill none, stroke currentColor, `stroke-width:1.8`, round): `<path d="M5 12h14M13 6l6 6-6 6"/>`.

### 5) Facilities section
`<section id="facilities">` background `--background`, `border-radius:var(--radius-card-lg)`, **`margin-top:-2.5rem`** (`-mt-10`, so it overlaps up onto the programs surface, creating a rounded reveal), `padding: 4rem 1.5rem 5rem` (mobile) / left/right `2.5rem` (≥640px) (`pt-16 pb-20`).
- A grid, 1 col → 2 cols on ≥md, `items-end`, gap `2.5rem`.
  - **Intro column** (max-width `24rem`): an Inview-revealed `size-16`(4rem) `rounded-card` image **`3.webp`** (alt "Player stretching for a forehand on clay"; reveal `from {opacity:0,scale:0.85}`→`{…,scale:1}`, config `{tension:240,friction:20}`); then an `<h2 id="facilities-title">` stacked-lines **"Tour Our"** / **"World-Class"** / **"Courts"** (`text-5xl`, medium, line 0.95, tight, **stagger 120ms**, margin-top `1.5rem`); then a `<p>` body **"Reserve a court for focused practice, squad drills, or private sessions — and train in the same conditions you'll compete in."** (`text-sm`, `--ink-soft`, max-width `20rem`, margin-top `1.5rem`) revealed word-by-word fade+rise (`wordOut {y:18,opacity:0}`→`wordIn {y:0,opacity:1}`, **wordStagger 28ms, delayIn 250ms, duration 700ms, easeOutQuart**).
  - **Court cards** (flex, items-end, gap `1.25rem`): two `<figure>` tiles, each `flex-1`, Inview rise-in `from {opacity:0,y:48}`→`{…,y:0}`, **delayIn = index × 140ms**, config `{tension:180,friction:26}`. The **second tile** gets `margin-bottom:2rem` (staggered baseline). Each tile is an `aspect-[3/4]`, `rounded-card`, `overflow:hidden`, `bg --surface` image with a **hover scale spring** `from {scale:1}`→`to {scale:1.03}`, config `{tension:300,friction:22}`. Glass caption (`absolute inset-x-3 bottom-3`, `rounded-xl`, `backdrop-blur`, white text, padding `0.75rem 1rem`): name (`text-sm`, medium) + description (`0.65rem`, opacity 85%). Caption tint depends on `tone`: blue → `bg accent-teal@55%`, clay → `bg navy@40%`.
    - Tile 1 (tone **clay**): `1.webp`, **"Redline Clay"** — "A fast outdoor clay court tuned for long, physical rallies." (alt "Player on the baseline of an outdoor clay court").
    - Tile 2 (tone **blue**): `4.webp`, **"Harbor Court"** — "A sheltered hard court built for precision and night play." (alt "Player following through on a blue hard court").

### 6) Stats section
`<section>` deep-navy (`--brand-deep`), white text, `border-radius:var(--radius-card-lg)`, **`margin-top:0.75rem`** (`mt-3`), `padding: 5rem 1.5rem` (mobile) / left/right `2.5rem` (≥640px) (`py-20`).
- Header: **Eyebrow** light-tone **"By the numbers"**, then `<h2 id="stats-title">` stacked-lines **"A club that"** / **"keeps score"** (`text-5xl`, medium, margin-top `1rem`).
- A `<dl>` grid 2-col → 4-col on ≥lg, `gap-x 2rem`, `gap-y 3rem`, margin-top `4rem`. Four **stat cells**, each Inview rise-in `from {opacity:0,y:30}`→`{…,y:0}`, **delayIn = index × 110ms**, config `{tension:180,friction:24}`, with a top border `1px white@20%`, `padding-top:1.25rem`: a big value (`text-6xl`→`text-7xl` ≥sm, medium, tight) + a label (`text-sm`, white@65%, margin-top `0.75rem`). (Mark the label `sr-only` in a `<dt>` for semantics; show value/label in `<dd>`.)
  - **24** Certified coaches · **12** Championship courts · **9K+** Members training · **15** Years on the baseline.

### 7) Testimonials section
`<section id="testimonials">` background `--background`, `padding: 5rem 1.5rem` (mobile) / `6rem 2.5rem` (≥640px) (`py-20 sm:py-24`).
- Header: **Eyebrow** **"What players say"**, then `<h2 id="testimonials-title">` stacked-lines **"Loved by"** / **"the locker room"** (`text-5xl`, medium, margin-top `1rem`).
- A `<ul>` grid 1-col → 3-col on ≥md, gap `1.25rem`, margin-top `3.5rem`. Three **testimonial cards**, each Inview rise-in `from {opacity:0,y:40}`→`{…,y:0}`, **delayIn = index × 120ms**, config `{tension:180,friction:26}`, and a **hover lift** `from {y:0}`→`to {y:-8}`, config `{tension:300,friction:22}`. Card: `flex; flex-col; justify-between; h-full; rounded-card; bg --surface; padding:1.75rem`. Contents: a large opening quote glyph **"** (`text-4xl`, `--brand`, line-none), a `<blockquote>` (`text-lg`, relaxed, `--ink`, margin-top `1rem`), a `<figcaption>` with top border `1px --hairline`, `padding-top:1rem`, margin-top `1.5rem`: name (medium) + role (`text-sm`, `--ink-soft`).
  - 1. "I added a level to my serve in one season. The coaching is detailed and it actually sticks." — **Priya Anand**, *Performance Squad*.
  - 2. "Best courts in the city and a team that treats every member like a competitor." — **Lukas Brenner**, *Adult Clinics*.
  - 3. "My daughter went from shy beginner to club champion. Worth every minute." — **Dana Okafor**, *Parent, Junior Development*.

### 8) Footer
`<footer id="contact">` deep-navy, white text, `border-radius:var(--radius-card-lg)`, **`margin-top:0.75rem`**, `padding: 3.5rem 1.5rem` (mobile) / `4rem 2.5rem` (≥640px) (`py-14 sm:py-16`).
- **CTA band** (border-bottom `1px white@15%`, padding-bottom `3.5rem`, column→row space-between items-end on ≥sm): left = **Eyebrow** light **"Get started"** + stacked-lines `<p>` **"Ready to"** / **"play?"** (`text-6xl`, medium, line 0.92, tight, margin-top `1rem`); right = a **light pill button** **"Book a Visit"** (Inview rise-in `from {opacity:0,y:20}`→`{…,y:0}`, **delayIn 150ms**, config `{tension:200,friction:24}`) that opens the **Contact modal**.
- **Columns grid** (`py-14`, `md` columns `1.4fr 1fr 1fr 1fr`, gap `2.5rem`):
  - Brand column (max-width `20rem`): mark + **Baseline** (`text-lg`, medium, uppercase, tracking 0.2em); blurb **"A members' tennis club and academy where focused coaching meets championship courts."** (`text-sm`, white@65%, margin-top `1rem`); an `<address>` (not-italic, margin-top `1.5rem`, white@80%, `text-sm`): email link **play@baseline.club** (`mailto:`), phone link **+1 (212) 555-0148** (`tel:+12125550148`), and a muted address line **120 Court Lane, New York** (white@55%).
  - Three link `<nav>` columns, each: an uppercase heading (`text-xs`, medium, tracking 0.2em, white@50%) + a `<ul>` (`text-sm`, white@80%, space-y `0.75rem`):
    - **Programs**: Junior Development (`#junior`), Performance Squad (`#performance`), Adult Clinics (`#adult`), Private Coaching (`#private`).
    - **Club**: Membership (`#membership`), Facilities (`#facilities`), Events (`#club`), Pro Shop (`#shop`).
    - **Company**: About (`#about`), Coaches (`#programs`), Careers (`#careers`), Contact (`#contact`).
- **Bottom bar** (border-top `1px white@15%`, padding-top `2rem`, `text-sm`, white@60%, column→row space-between items-center on ≥sm): copyright **"© 2026 Baseline Tennis Club. All rights reserved."**; a Social nav (Instagram `#instagram`, X `#x`, YouTube `#youtube`, LinkedIn `#linkedin`); a Legal nav (Privacy `#privacy`, Terms `#terms`). Gaps `1.25rem`.

### Shared UI components
- **Eyebrow**: inline-flex, items-center, gap `0.5rem`, `text-xs`, medium, uppercase, `letter-spacing:0.22em`. A leading `0.375rem` dot (`rounded-pill`). Dark tone: text `--ink-soft`, dot `--brand`. Light tone: text white@70%, dot `--brand-light`.
- **Pill button**: inline-flex, items-center, gap `0.5rem`, `rounded-pill`, `padding:0.875rem 1.75rem`, `text-sm`, medium, uppercase, tracking-wide, focus ring `--brand-light`. Trailing arrow SVG (`M5 12h14M13 6l6 6-6 6`, `size-4`) that **springs `x:0→5`** on hover (config `{tension:320,friction:20}`). Variants: `light` = bg white, text navy, hover bg `--brand-light`/text white; `solid` = bg `--ink`, text white, hover bg `--brand-deep`; `outline` = border current, text `--ink`, hover bg ink/text white.
- **Arrow button** (carousel): `size-12`/`size-14` ≥sm grid circle (`rounded-pill`, border). `outline` = border `--hairline`, transparent, text `--ink`, hover border `--ink`. `solid` = bg `--ink`, border `--ink`, text white, hover bg `--brand-deep`. Inner arrow SVG (`M5 12h14M13 6l6 6-6 6`, `size-5`) **scales `1→1.15` on hover** (config `{tension:320,friction:18}`); the **prev** arrow is the same path flipped `scaleX(-1)`.
- **Carousel dots**: a flex row, gap `0.5rem`. Each dot a button (`padding:0.375rem`) wrapping a `0.375rem`-tall pill: active = `width:1.25rem` filled (`--ink` dark / white light), idle = `width:0.375rem` (idle color `--ghost` dark / white@40% light). `aria-current` on active.

### Contact modal (portaled, scroll-locked)
Trigger: header "Book a Visit", menu "Book a Visit", footer CTA pill. Render at `document.body` level, `position:fixed; inset:0; z-index:90`, flex end/center: items-end on mobile, items-center on ≥sm, padding `0.75rem`/`1.5rem`. When closed it's `pointer-events:none`.
- **Backdrop**: `absolute inset-0; bg navy@40%; backdrop-blur`; opacity springs `0→1` (config `{tension:240,friction:30}`); click closes.
- **Panel** (`role=dialog aria-modal`): springs in `from {opacity:0,y:28,scale:0.96}`→`to {opacity:1,y:0,scale:1}`, config `{tension:240,friction:26}`. Style: `max-height:92svh; overflow-y:auto; rounded-card-lg; bg --surface-card; padding:1.5rem`/`2rem` ≥sm; max-width `32rem` ≥sm; `text --ink`; big navy shadow.
  - Header: **Eyebrow "Book a visit"** + stacked-lines `<h2>` **"Come see"** / **"the courts"** (`text-4xl`→`text-5xl` ≥sm, medium, **stagger 90ms, duration 800ms**, margin-top `0.75rem`); a close button (`size-10` circle, bg `--surface`, hover `--hairline`) with an **X icon that rotates `0→90deg` on hover** (config `{tension:300,friction:18}`); X path `M6 6l12 12M18 6L6 18`, `stroke-width:1.8`.
  - Form (`margin-top:1.75rem`, flex col gap `1rem`, `noValidate`): three labeled fields — **"Full name"** (text, placeholder "Alex Rivera"), **"Email"** (email, placeholder "you@email.com"), **"What would you like to play?"** (textarea rows 3, placeholder "I'd love to try a private lesson on the clay courts…"). Field label = `text-xs`, medium, uppercase, tracking 0.18em, `--ink-soft`. Input = `w-full; rounded-xl; border 1px --hairline; bg --background; padding:0.75rem 1rem; text-sm`; focus border/ring `--brand-light`. Submit button: `rounded-pill; bg --ink; text white; padding:0.875rem 1.75rem; text-sm; medium; uppercase; tracking-wide`; hover bg `--brand-deep`; label **"Request a visit"** (→ **"Sending…"** while submitting; disabled+dimmed then).
  - **Submit is a no-op stub** (no real API): on submit, `preventDefault`, briefly show "Sending…", then show the **success panel** (do NOT call any server). Success panel (`margin-top:2rem; rounded-card; bg --surface; padding:1.5rem; text-center`): a `size-12` brand-blue circle with a white check SVG (`M5 13l4 4L19 7`); **"Request received"** (`text-lg`, medium); subtext **"Thanks, {firstName or 'there'} — our team will be in touch to lock in your visit."**; a **"Done"** pill button (bg `--ink`, hover `--brand-deep`) that closes.
- Behaviors: **Esc closes**; opening **stops Lenis** (scroll lock) and focuses the name field after ~120ms; closing **restarts Lenis** and resets the form ~350ms later.

### Fullscreen menu overlay (from the burger)
Portaled at body level, `position:fixed; inset:0; z-index:70`, flex column. Closed = `pointer-events:none`.
- A navy backdrop (`absolute inset-0; bg --brand-deep`) that **fades `opacity 0→1`** (config `{tension:260,friction:30}`), click closes.
- A panel that springs `from {opacity:0,y:-24}`→`{…,y:0}` (config `{tension:220,friction:28}`), full height, padding mirrors the page inset (`0.5rem`/`0.75rem`) then inner `1.5rem 1.5rem` / `2.5rem` ≥sm so the close button lands exactly where the burger was.
  - Top row: brand mark + **Baseline** (uppercase, tracking 0.2em) and a close button (`size-10` circle, white@15%, hover white@25%) with the **X-rotate-on-hover** icon (as above).
  - Center nav (flex col, justify-center, gap `0.5rem`): four big links, each spring rise-in `from {opacity:0,y:28}`→`{…,y:0}`, **delayIn = 120 + i×70 ms**, config `{tension:200,friction:26}`; link = block `text-5xl`→`text-7xl` ≥sm, medium, tight, hover color `--brand-light`. Links: **Programs** (`#programs`), **Facilities** (`#facilities`), **Reviews** (`#testimonials`), **Contact** (`#contact`). Clicking a link smooth-scrolls to the anchor and closes the menu.
  - Bottom row (border-top white@15%, padding-top `2rem`, col→row): a **light pill "Book a Visit"** (closes menu, opens Contact modal) + a social nav (Instagram, X, YouTube, LinkedIn, white@70%, hover white).
- Esc closes; opening stops Lenis, closing restarts it.

## The loader / reveal

This is the opening moment in the preview. On first paint a **navy curtain** covers the whole viewport (`position:fixed; inset:0; z-index:200; bg --brand-deep; white text`), centered column, gap `2rem`:
- A wordmark: tennis-ball mark (`size-7`/1.75rem) + **Baseline** (`text-2xl`, medium, uppercase, tracking 0.2em), which springs in `from {opacity:0,y:16}`→`{…,y:0}` (config `{tension:200,friction:22}`).
- A progress track: a `width:10rem`, `height:1px`, `rounded-pill`, `bg white@20%`, `overflow:hidden`, containing a white fill that **scales X `0→1`** from `transform-origin:left`, with **delayIn 120ms**, **duration `MIN_VISIBLE_MS - 120` (= 1280ms)**, easing **easeInOutCubic**.

Timing & reveal logic (bake in): `MIN_VISIBLE_MS = 1400`, `MAX_VISIBLE_MS = 2600`, `EXIT_MS = 850`.
- On mount: **stop Lenis** (scroll locked).
- Once `window` `load` fires (or immediately if already complete), start a countdown of `MIN_VISIBLE_MS` (1400ms). If `load` never fires, force-start after `MAX_VISIBLE_MS` (2600ms).
- When the countdown ends: set **`ready = true`** (which triggers the hero title, tagline, collection slider, and membership card to animate in — they were gated on this), **start Lenis**, and **slide the curtain up**: `translateY(0%)`→`translateY(-105%)`, **duration `EXIT_MS` (850ms), easing easeInOutCubic**. Remove the curtain from the DOM after `EXIT_MS`.
- Respect `prefers-reduced-motion: reduce`: shorten min-visible to ~200ms and make the exit instant.

## Fixed parameters (bake these in)

- **Colors:** `--background #ffffff`, `--foreground/#ink #0a0a0a`, `--brand #2563c9`, `--brand-deep #0f2f63`, `--brand-light #5790e6`, `--accent-teal #0b6e97`, `--surface #f4f4f4`, `--surface-card #ffffff`, `--ink-soft #717784`, `--ghost #d7dae1`, `--hairline #e6e8ec`, `--on-brand #ffffff`. Membership avatar dots: `#5790e6 #c2e029 #0b6e97 #ffffff`.
- **Radii:** card `1.5rem`, card-lg `2rem`, pill `62.5rem`, `rounded-xl 0.75rem`.
- **Font:** Onest (Google), weights 400/500. Body family `"Onest", system-ui, sans-serif`.
- **Page inset:** `0.5rem` (<640) / `0.75rem` (≥640). Section gaps: `mt-3` = `0.75rem` (stats, footer); facilities `margin-top:-2.5rem`.
- **Adaptive grid:** `FONT_BASE 16`, base width 1920, scale-up `COEF 0.6666`; media-query vw values `0.833333 / 1.111111 / 1.5625 / 4.444444` at maxwidths `1920 / 1440 / 1024 / 640`.
- **Breakpoints:** sm 640, md 768, lg 1024. **Hover disabled ≤768px.**
- **Loader:** MIN_VISIBLE 1400ms, MAX_VISIBLE 2600ms, EXIT 850ms; progress fill delay 120ms, duration 1280ms (easeInOutCubic); curtain `0%→-105%`.
- **Hero reveal:** title wordStagger 140ms / per-word duration 1100ms easeOutExpo, wordOut y 115%; tagline baseDelay 350 / stagger 110 / duration 900 easeOutExpo; collection slider Inview delayIn 650 + autoplay 3800ms + card crossfade `{tension:210,friction:24}`; membership Inview delayIn 780. Both Inview configs `{tension:200,friction:26}`. Hero height `calc(100svh - 1rem)` / `-1.5rem` ≥sm, min `36rem`. Title `font-size:12.5vw`, tagline `2.4rem`, ghost heading `8.2vw`.
- **StackedLines defaults:** stagger 120ms, baseDelay 0, duration 950ms, easeOutExpo, lineOut y 115%, line clip padding-bottom `0.14em`.
- **Trust:** ghost word reveal duration 700ms easeOutExpo; ghost X parallax pairs `±3% / ±3% / -2%→4% / 4%→-3%`; coach card rotate `6deg`, Inview `{tension:170,friction:26}`, photo crossfade `{tension:260,friction:26}`; percent badge `{tension:220,friction:22}`; badge card delayIn 120 `{tension:200,friction:26}`.
- **Programs:** row Inview delayIn `i×90`, `{tension:190,friction:26}`; arrow hover `x:0→8, opacity .55→1` `{tension:300,friction:20}`.
- **Facilities:** icon `{tension:240,friction:20}`; title stacked stagger 120; body word fade wordStagger 28 / delayIn 250 / duration 700 easeOutQuart, wordOut y 18; card Inview delayIn `i×140` `{tension:180,friction:26}`, 2nd card `mb 2rem`; card hover scale `1→1.03` `{tension:300,friction:22}`.
- **Stats:** cell Inview delayIn `i×110` `{tension:180,friction:24}`.
- **Testimonials:** card Inview delayIn `i×120` `{tension:180,friction:26}`; hover lift `y:0→-8` `{tension:300,friction:22}`.
- **Footer CTA pill:** Inview delayIn 150 `{tension:200,friction:24}`.
- **Modal:** backdrop fade `{tension:240,friction:30}`, panel `{tension:240,friction:26}` from `{opacity:0,y:28,scale:0.96}`, title stacked stagger 90 / duration 800, X-rotate hover `{tension:300,friction:18}`, focus name after 120ms, reset form after 350ms. **Submit is a stub — never hit a network.**
- **Menu overlay:** backdrop fade `{tension:260,friction:30}`, panel `{opacity:0,y:-24}` `{tension:220,friction:28}`, links delayIn `120 + i×70` `{tension:200,friction:26}`.
- **Pill/arrow/dots/eyebrow:** as specified in "Shared UI components".
- **Copyright year:** 2026. Contact: play@baseline.club, +1 (212) 555-0148, 120 Court Lane, New York.

## Assets

Base URL: `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000`

| Code path | Full URL | Used by |
|---|---|---|
| `/assets/hero/hero-court.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/hero/hero-court.webp` | Hero parallax background plate |
| `/assets/1.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/1.webp` | Hero **membership card** image · Trust **slide 3** (James Okoro) · Facilities **Redline Clay** card |
| `/assets/2.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/2.webp` | Hero collection slide 1 (**Baseline Pro / Featured Gear**) |
| `/assets/3.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/3.webp` | Hero collection slide 2 (**Court Series / Summer Drop**) · Facilities **intro icon** |
| `/assets/4.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/4.webp` | Trust **slide 2** (Elena Sokolova) · Facilities **Harbor Court** card |
| `/assets/5.webp` | `https://api.getlayers.ai/storage/v1/object/public/public/assets/baseline-88535e4000/5.webp` | Hero collection slide 3 (**Academy Kit / Junior Range**) · Trust **slide 1** (Marco Vidal) |

All `<img>` / `background-image` must point at these full URLs. Set `loading`/`fetchpriority` sensibly (hero plate eager, the rest lazy).