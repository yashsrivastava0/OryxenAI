/* Cobalt Atlas v2 — content-independent behaviour (see README.md).
   Reads structure only ([data-view], header links, headings, optional classes);
   no person text, no hard-coded routes. Progressive: the page works without JS.
   No libraries; styles are applied through the CSSOM (element.style.setProperty). */
(() => {
  "use strict";
  if (window.AtlasTheme) return;

  const doc = document;
  const root = doc.documentElement;
  const VERSION = "2.0.0";

  const $ = (selector, scope = doc) => scope.querySelector(selector);
  const $$ = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));
  const mq = (query) => window.matchMedia(query);
  const params = new URLSearchParams(window.location.search);
  const debug = params.has("atlas-debug");
  const reduced = mq("(prefers-reduced-motion: reduce)");
  const finePointer = mq("(hover: hover) and (pointer: fine)");
  const darkScheme = mq("(prefers-color-scheme: dark)");
  const hasIO = "IntersectionObserver" in window;
  // Automated visitors (screenshots, link checks, host verification) get the
  // finished page: no intro, no hidden-until-revealed content. Opt back in
  // with ?atlas-motion=1 when testing the motion layer itself.
  const automated = navigator.webdriver === true && !params.has("atlas-motion");
  const motionOn = () => !reduced.matches && !automated;
  const nativeScrollTimeline = !!(window.CSS && CSS.supports && CSS.supports("animation-timeline: scroll()"));

  const warn = (...args) => { if (debug) console.warn("[atlas]", ...args); };
  const guard = (name, fn) => {
    try { return fn(); } catch (error) { warn(`${name} failed`, error); return undefined; }
  };
  const el = (tag, className, attrs) => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (attrs) for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const decode = (value) => {
    try { return decodeURIComponent(value); } catch { return ""; }
  };
  const text = (node) => (node ? node.textContent.replace(/\s+/g, " ").trim() : "");

  /* ---- Storage that survives opaque-origin sandboxes ---- */
  const store = (() => {
    const memory = new Map();
    const probe = (kind) => {
      try {
        const area = window[kind];
        area.setItem("__atlas", "1");
        area.removeItem("__atlas");
        return area;
      } catch { return null; }
    };
    const areas = { local: probe("localStorage"), session: probe("sessionStorage") };
    return {
      get(key, scope = "local") {
        try { if (areas[scope]) return areas[scope].getItem(key); } catch { /* fall through */ }
        return memory.get(scope + key) ?? null;
      },
      set(key, value, scope = "local") {
        try { if (areas[scope]) { areas[scope].setItem(key, value); return; } } catch { /* fall through */ }
        memory.set(scope + key, value);
      }
    };
  })();

  root.classList.add("js");

  /* ---- Theme (light / dark) ---- */
  const storedTheme = store.get("atlas-theme");
  if (storedTheme === "light" || storedTheme === "dark") root.dataset.theme = storedTheme;
  const currentScheme = () => root.dataset.theme || (darkScheme.matches ? "dark" : "light");

  let themeButton = null;
  function syncThemeUi() {
    const dark = currentScheme() === "dark";
    if (themeButton) themeButton.setAttribute("aria-pressed", String(dark));
    const meta = $('meta[name="theme-color"]');
    if (meta) {
      const bg = getComputedStyle(doc.body || root).backgroundColor;
      if (bg) meta.setAttribute("content", bg);
    }
  }
  function setTheme(next, origin) {
    if (next !== "light" && next !== "dark") return;
    const apply = () => {
      root.dataset.theme = next;
      store.set("atlas-theme", next);
      syncThemeUi();
    };
    if (origin && motionOn() && typeof doc.startViewTransition === "function") {
      root.classList.add("is-theme-vt");
      const transition = doc.startViewTransition(apply);
      transition.ready.then(() => {
        const radius = Math.hypot(Math.max(origin.x, innerWidth - origin.x), Math.max(origin.y, innerHeight - origin.y));
        root.animate(
          { clipPath: [`circle(0px at ${origin.x}px ${origin.y}px)`, `circle(${radius}px at ${origin.x}px ${origin.y}px)`] },
          { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)", pseudoElement: "::view-transition-new(root)" }
        );
      }).catch(() => {});
      transition.finished.finally(() => root.classList.remove("is-theme-vt"));
    } else {
      root.classList.add("theme-anim");
      apply();
      setTimeout(() => root.classList.remove("theme-anim"), 500);
    }
  }

  /* ---- State shared by modules ---- */
  let views = [];
  let viewById = new Map();
  let homeView = null;
  let activeView = null;
  let linkNav = false;
  let clickedCard = null;
  let userScrolled = false;
  let introDone = false;
  let menuOpen = false;
  const scrollMemory = new Map();
  const spy = { targets: [], id: null };
  let announcer = null;
  let routeBar = null;
  let revealObserver = null;
  let countObserver = null;
  let liveObserver = null;
  let openPalette = () => {};
  let readyResolve = () => {};
  const readyPromise = new Promise((resolve) => { readyResolve = resolve; });

  /* ---- Chrome that must exist even if the generator omitted it ---- */
  function ensureChrome() {
    if (!$(".scroll-progress")) {
      doc.body.prepend(el("div", "scroll-progress", { "aria-hidden": "true" }));
    }
    routeBar = el("div", "atlas-route-bar", { "aria-hidden": "true" });
    doc.body.append(routeBar);
    announcer = $("#route-announcer");
    if (!announcer) {
      announcer = el("span", "sr-only", { id: "route-announcer", role: "status", "aria-live": "polite" });
      doc.body.append(announcer);
    }
    if (!$(".skip-link") && $("#main")) {
      const skip = el("a", "skip-link", { href: "#main" });
      skip.textContent = "Skip to content";
      doc.body.prepend(skip);
    }
  }

  /* ---- Intro loader (bounded, skippable, never blocks no-JS) ---- */
  function startLoader() {
    const mode = params.get("intro") === "1" ? "on" : (doc.body.dataset.intro || root.dataset.intro || "auto");
    if (mode === "off" || reduced.matches) return Promise.resolve();
    if (mode !== "on" && (!motionOn() || store.get("atlas-intro", "session"))) return Promise.resolve();
    store.set("atlas-intro", "1", "session");

    root.classList.add("is-loading");
    const name = text($(".wordmark-name")) || doc.title.split(/\s[—–|-]\s/)[0].trim();
    const markText = text($(".wordmark-mark")) || name.charAt(0);
    const node = el("div", "atlas-loader", { "aria-hidden": "true" });
    const mark = el("div", "loader-mark");
    if (markText.length > 1 && /[.·•]$/.test(markText)) {
      mark.append(markText.slice(0, -1));
      const dot = el("span");
      dot.textContent = markText.slice(-1);
      mark.append(dot);
    } else mark.textContent = markText;
    const label = el("div", "loader-name");
    label.textContent = name;
    const bar = el("div", "loader-bar");
    const fill = el("i");
    bar.append(fill);
    const count = el("div", "loader-count");
    count.textContent = "0";
    node.append(mark, label, bar, count);
    doc.body.prepend(node);

    const started = performance.now();
    const MIN = 700;
    const CAP = 2600;
    let finished = false;
    let shown = 0;
    const paint = (value) => {
      node.style.setProperty("--lp", value.toFixed(3));
      count.textContent = String(Math.round(value * 100));
    };
    const loop = () => {
      const elapsed = performance.now() - started;
      const target = finished ? 1 : Math.min(0.9, 1 - Math.exp(-elapsed / 650));
      shown += (target - shown) * 0.22;
      paint(shown);
      if (!(finished && shown > 0.995)) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);

    const loaded = new Promise((resolve) => {
      if (doc.readyState === "complete") resolve();
      else window.addEventListener("load", resolve, { once: true });
    });
    const fonts = doc.fonts && doc.fonts.ready ? doc.fonts.ready : Promise.resolve();
    const ready = Promise.all([loaded, fonts]).then(() => sleep(Math.max(0, MIN - (performance.now() - started))));
    return Promise.race([ready, sleep(CAP)]).then(async () => {
      finished = true;
      paint(1);
      await sleep(220);
      node.classList.add("is-done");
      root.classList.remove("is-loading");
      setTimeout(() => node.remove(), 1200);
    });
  }

  /* ---- Router ---- */
  function resolveRoute() {
    const hash = window.location.hash.slice(1).replace(/^\/+/, "");
    const id = decode(hash);
    if (!id) return { id: "", view: homeView, target: null };
    const asView = viewById.get(id);
    if (asView) return { id, view: asView, target: null };
    const node = doc.getElementById(id);
    const owner = node && node.closest("[data-view]");
    if (owner) return { id, view: owner, target: node };
    // A real element outside every view (e.g. the skip link's #main): stay put.
    if (node && activeView) return { id: activeView.id, view: activeView, target: node, outside: true };
    return { id, view: homeView, target: null, missing: true };
  }

  function viewLabel(view) {
    for (const link of $$(".site-nav a[href^='#']")) {
      if (decode(link.getAttribute("href").slice(1)) === view.id) return text(link);
    }
    const title = view.dataset.title || text($("h1", view));
    return title.split(/\s[—–-]\s/)[0].trim() || view.id;
  }

  function navLinks() {
    const links = new Set($$(".site-nav a[href^='#'], [data-nav]"));
    return Array.from(links).filter((link) => (link.getAttribute("href") || "").startsWith("#"));
  }

  function updateNav(route) {
    if (!route || !route.view) return;
    const back = route.view.querySelector(".back-link[href^='#']");
    const backId = back ? decode(back.getAttribute("href").slice(1)) : "";
    const currentId = spy.id || route.id || route.view.id;
    for (const link of navLinks()) {
      const id = decode(link.getAttribute("href").slice(1));
      const isCurrent = id === currentId || (!spy.id && id === route.view.id) || (!!backId && id === backId && !spy.id);
      if (isCurrent) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    placeIndicator();
  }

  function placeIndicator() {
    const nav = $(".site-nav");
    if (!nav) return;
    const current = $("a[aria-current='page']", nav);
    if (!current || !nav.offsetParent || getComputedStyle(nav).position === "absolute") {
      nav.style.setProperty("--no", "0");
      return;
    }
    const navRect = nav.getBoundingClientRect();
    const rect = current.getBoundingClientRect();
    nav.style.setProperty("--nx", `${(rect.left - navRect.left + nav.scrollLeft).toFixed(1)}px`);
    nav.style.setProperty("--nw", `${rect.width.toFixed(1)}px`);
    nav.style.setProperty("--no", "1");
    nav.setAttribute("data-ready", "");
  }

  function collectSpyTargets(view) {
    const targets = [];
    const seen = new Set();
    const add = (node) => {
      if (!node || !node.id || seen.has(node.id) || node === view) return;
      seen.add(node.id);
      targets.push({ id: node.id, el: node });
    };
    for (const link of navLinks()) {
      const id = decode(link.getAttribute("href").slice(1));
      const node = id && doc.getElementById(id);
      if (node && node !== view && view.contains(node)) add(node);
    }
    $$(".case-toc a", view).forEach((link) => add(doc.getElementById(decode(link.getAttribute("href").slice(1)))));
    targets.sort((a, b) => (a.el.compareDocumentPosition(b.el) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
    spy.targets = targets;
    spy.id = null;
  }

  function pairArt(fromView, toView, sourceCard) {
    if (!fromView || !toView || !("startViewTransition" in doc)) return null;
    let from = null;
    let to = null;
    const toFrame = $(".case-art-frame", toView);
    const fromFrame = $(".case-art-frame", fromView);
    if (toFrame) {
      const card = sourceCard && fromView.contains(sourceCard) ? sourceCard : $(`a.project-card[href="#${CSS.escape(toView.id)}"]`, fromView);
      from = card && $(".project-art", card);
      to = toFrame;
    } else if (fromFrame) {
      from = fromFrame;
      const card = $(`a.project-card[href="#${CSS.escape(fromView.id)}"]`, toView);
      to = card && $(".project-art", card);
    }
    return from && to ? { from, to } : null;
  }

  function placeScroll(route, initial, restore) {
    if (route.target) route.target.scrollIntoView({ block: "start", behavior: "instant" });
    else if (restore && scrollMemory.has(route.view.id)) window.scrollTo({ top: scrollMemory.get(route.view.id), behavior: "instant" });
    else window.scrollTo({ top: 0, behavior: "instant" });
  }

  function afterRoute(route, initial, changed) {
    if (!initial) {
      const heading = route.outside ? route.target
        : route.target ? ($("h1,h2,h3", route.target) || route.target)
        : $("h1", route.view);
      if (heading) {
        if (!heading.hasAttribute("tabindex")) heading.setAttribute("tabindex", "-1");
        heading.focus({ preventScroll: true });
      }
      if (announcer) { announcer.textContent = ""; announcer.textContent = doc.title; }
      if (routeBar && (changed || route.target) && motionOn()) {
        routeBar.classList.remove("is-active");
        void routeBar.offsetWidth;
        routeBar.classList.add("is-active");
      }
    }
    $$(".marquee[data-ready]", route.view).forEach(measureMarquee);
    root.dataset.header = "";
    if (revealObserver && introDone) observeReveals(route.view);
  }

  function activateRoute(initial = false) {
    if (!views.length) return;
    const route = resolveRoute();
    const previous = activeView;
    const changed = previous !== route.view;
    const viaLink = linkNav;
    const sourceCard = clickedCard;
    linkNav = false;
    clickedCard = null;
    if (previous) scrollMemory.set(previous.id, window.scrollY);
    const restore = !viaLink && !initial && changed;

    const pair = changed && !initial && motionOn() ? pairArt(previous, route.view, sourceCard) : null;
    const commit = () => {
      if (pair) {
        pair.from.style.setProperty("view-transition-name", "none");
        pair.to.style.setProperty("view-transition-name", "atlas-art");
      }
      for (const view of views) view.hidden = view !== route.view;
      doc.body.dataset.router = "ready";
      activeView = route.view;
      doc.title = route.view.dataset.title || doc.title;
      collectSpyTargets(route.view);
      updateNav(route);
      if (changed || initial || route.target) {
        if (changed || initial) placeScroll(route, initial, restore);
        else route.target.scrollIntoView({ block: "start", behavior: reduced.matches ? "instant" : "smooth" });
      }
      closeMenu();
    };
    const finish = () => {
      if (pair) {
        pair.from.style.removeProperty("view-transition-name");
        pair.to.style.removeProperty("view-transition-name");
      }
      afterRoute(route, initial, changed);
    };

    // A skipped transition (rapid navigation) rejects ready/updateCallbackDone;
    // swallow those so quick clicking never logs uncaught errors.
    const run = () => {
      const transition = doc.startViewTransition(commit);
      transition.ready.catch(() => {});
      transition.updateCallbackDone.catch(() => {});
      transition.finished.then(finish, finish);
    };
    if (pair) {
      pair.from.style.setProperty("view-transition-name", "atlas-art");
      run();
    } else if (changed && !initial && motionOn() && typeof doc.startViewTransition === "function") {
      run();
    } else {
      commit();
      finish();
    }
  }

  /* ---- Reveals, split headings, counters ---- */
  function observeReveals(scope) {
    if (!revealObserver) return;
    $$(".atlas-appear:not(.is-in-view), [data-split]:not(.is-in-view)", scope).forEach((node) => revealObserver.observe(node));
    $$(".count:not([data-counted])", scope).forEach((node) => countObserver && countObserver.observe(node));
  }

  function setupReveals() {
    if (!motionOn() || !hasIO) return;
    root.dataset.motion = "on";
    const groups = new Map();
    $$(".atlas-appear").forEach((node) => {
      const parent = node.parentElement;
      const index = groups.get(parent) || 0;
      groups.set(parent, index + 1);
      node.style.setProperty("--i", String(Math.min(index, 6)));
    });
    revealObserver = new IntersectionObserver((entries, observer) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in-view");
        observer.unobserve(entry.target);
      }
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.08 });
    countObserver = new IntersectionObserver((entries, observer) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        countUp(entry.target);
      }
    }, { threshold: 0.6 });
    // Every hidden-until-revealed rule is keyed on data-motion, so dropping it shows everything.
    reduced.addEventListener("change", () => { if (reduced.matches) root.removeAttribute("data-motion"); });
  }

  function fitHeadings() {
    for (const heading of $$("h1, h2")) {
      const length = text(heading).length;
      const tier = length > 90 ? "xl" : length > 55 ? "l" : length > 32 ? "m" : "";
      if (tier) heading.dataset.len = tier;
    }
  }

  function word(content, index) {
    const outer = el("span", "sw", { "aria-hidden": "true" });
    const inner = el("span", "sw-i");
    inner.style.setProperty("--w", String(Math.min(index, 14)));
    if (content) inner.textContent = content;
    outer.append(inner);
    return outer;
  }
  function splitInto(parent, state) {
    for (const node of Array.from(parent.childNodes)) {
      if (node.nodeType === Node.TEXT_NODE) {
        const fragment = doc.createDocumentFragment();
        for (const part of node.data.split(/(\s+)/)) {
          if (!part) continue;
          if (/^\s+$/.test(part)) { fragment.append(" "); state.last = null; }
          else if (state.last) state.last.firstChild.append(part);
          else { state.last = word(part, state.n++); fragment.append(state.last); }
        }
        node.replaceWith(fragment);
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.tagName === "BR") { state.last = null; continue; }
        if (/\s/.test(node.textContent.trim())) {
          state.last = null;
          splitInto(node, state);
        } else if (state.last) {
          state.last.firstChild.append(node);
        } else {
          const holder = word("", state.n++);
          node.replaceWith(holder);
          holder.firstChild.append(node);
          state.last = holder;
        }
      }
    }
  }
  function splitHeadings() {
    if (!motionOn() || !hasIO) return;
    const candidates = $$("h1, h2, .intro-statement, .about-quote blockquote, .case-intro > p");
    for (const heading of candidates) {
      if (heading.closest("[data-no-split]") || heading.hasAttribute("data-no-split") || heading.dataset.split) continue;
      const words = text(heading).split(" ").length;
      if (words > 16 || words < 1) continue;
      const original = heading.innerHTML;
      try {
        const label = Array.from(heading.childNodes).map((n) => (n.nodeName === "BR" ? " " : n.textContent)).join("").replace(/\s+/g, " ").trim();
        splitInto(heading, { last: null, n: 0 });
        heading.setAttribute("aria-label", label);
        heading.setAttribute("data-split", "");
      } catch (error) {
        heading.innerHTML = original;
        warn("split failed", error);
      }
    }
  }

  // Stat numerals size themselves from their character count (see style.css).
  function tagNumerals() {
    for (const node of $$(".impact-grid strong, .case-result strong, .art-pop strong, .hero-float strong")) {
      node.style.setProperty("--n", String(Math.max(2, text(node).length)));
    }
  }

  const NUMBER = /^(\s*[+\-≈~<>]?\s*)(\d[\d,]*(?:\.\d+)?)/;
  function setupCounters() {
    if (!motionOn() || !hasIO) return;
    const selector = ".impact-grid strong, .case-result strong, .art-pop strong, .hero-float strong, [data-count]";
    for (const target of $$(selector)) {
      const walker = doc.createTreeWalker(target, NodeFilter.SHOW_TEXT);
      const first = walker.nextNode();
      if (!first) continue;
      const match = NUMBER.exec(first.nodeValue);
      if (!match) continue;
      // <data>, not <span>: unit-suffix rules like ".impact-grid strong span" must not match the number.
      const span = el("data", "count", { value: match[2].replace(/,/g, "") });
      span.textContent = match[2];
      span.dataset.final = match[2];
      const rest = first.nodeValue.slice(match[0].length);
      first.nodeValue = match[1];
      first.after(span);
      if (rest) span.after(doc.createTextNode(rest));
    }
  }
  function countUp(span) {
    span.setAttribute("data-counted", "");
    const final = span.dataset.final || span.textContent;
    const target = parseFloat(final.replace(/,/g, ""));
    if (!Number.isFinite(target) || reduced.matches) return;
    const decimals = (final.split(".")[1] || "").length;
    const grouped = final.includes(",");
    span.style.setProperty("min-inline-size", `${span.getBoundingClientRect().width}px`);
    const format = (value) => (grouped
      ? value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
      : value.toFixed(decimals));
    const started = performance.now();
    const duration = 1300;
    const tick = (now) => {
      const progress = clamp((now - started) / duration, 0, 1);
      span.textContent = progress < 1 ? format(target * (1 - Math.pow(1 - progress, 3))) : final;
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  /* ---- Art, images, marquee, live loops ---- */
  function assignArt() {
    const kinds = ["orbit", "grid", "waves", "stack", "bars", "dots"];
    $$(".project-card").forEach((card, index) => {
      const art = $(".project-art", card);
      if (!art) return;
      if (!art.dataset.art) art.dataset.art = kinds[index % kinds.length];
      if (!art.dataset.tone) art.dataset.tone = String((index % 4) + 1);
    });
    $$(".case-art-frame").forEach((frame) => {
      const view = frame.closest("[data-view]");
      const art = view && $(`a.project-card[href="#${CSS.escape(view.id)}"] .project-art`);
      if (art) {
        if (!frame.dataset.art) frame.dataset.art = art.dataset.art;
        if (!frame.dataset.tone) frame.dataset.tone = art.dataset.tone;
      } else if (!frame.dataset.art) frame.dataset.art = "orbit";
    });
  }

  // Initials for the photo-less avatar: first + last name, ignoring suffixes (Jr, III...).
  function initialsOf(name) {
    const words = name.replace(/[^\p{L}\p{N}\s'-]/gu, "").split(/\s+/).filter((w) => w && !/^(jr|sr|ii|iii|iv|phd|md)$/i.test(w));
    if (!words.length) return "";
    const first = (w) => Array.from(w)[0];
    return (words.length > 1 ? first(words[0]) + first(words[words.length - 1]) : Array.from(words[0]).slice(0, 2).join("")).toUpperCase();
  }
  function setupPortraits() {
    const name = text($(".wordmark-name")) || doc.title.split(/\s[—–|-]\s/)[0].trim();
    for (const portrait of $$(".portrait")) {
      if (!portrait.dataset.initials) portrait.dataset.initials = initialsOf(name);
      if (!$("img", portrait)) portrait.setAttribute("aria-hidden", "true");
    }
  }

  function setupImages() {
    for (const img of $$("img")) {
      if (!img.hasAttribute("decoding")) img.decoding = "async";
      if (!img.hasAttribute("loading") && !img.closest(".hero")) img.loading = "lazy";
      const wrap = img.closest("[data-art], .project-art, .case-art-frame, .portrait, .hero-visual");
      const fail = () => { if (wrap) { wrap.classList.remove("is-loading"); wrap.classList.add("is-error"); } };
      if (img.complete) { if (img.naturalWidth === 0 && img.getAttribute("src")) fail(); continue; }
      if (wrap) wrap.classList.add("is-loading");
      img.addEventListener("load", () => wrap && wrap.classList.remove("is-loading"), { once: true });
      img.addEventListener("error", fail, { once: true });
    }
  }

  function measureMarquee(marquee) {
    const track = $(".marquee-track", marquee);
    if (!track || !track.scrollWidth) return;
    marquee.style.setProperty("--marquee-dur", `${clamp(track.scrollWidth / 60, 20, 90).toFixed(1)}s`);
  }
  function setupMarquee() {
    if (!motionOn()) return;
    for (const marquee of $$(".marquee")) {
      const track = $(".marquee-track", marquee) || marquee.firstElementChild;
      if (!track) continue;
      track.classList.add("marquee-track");
      const clone = track.cloneNode(true);
      clone.setAttribute("aria-hidden", "true");
      clone.inert = true;
      $$("[id]", clone).forEach((node) => node.removeAttribute("id"));
      marquee.append(clone);
      marquee.setAttribute("data-ready", "");
      measureMarquee(marquee);
    }
  }

  function setupLiveLoops() {
    if (!hasIO || !motionOn()) return;
    const nodes = $$(".hero, .contact-section, .page-next, .hero-visual");
    nodes.forEach((node) => node.setAttribute("data-live", ""));
    liveObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) entry.target.removeAttribute("data-paused");
        else entry.target.setAttribute("data-paused", "");
      }
    });
    nodes.forEach((node) => liveObserver.observe(node));
  }

  /* ---- Case-study table of contents ---- */
  function buildToc() {
    for (const view of views) {
      const sections = $$(".case-text, .case-result", view);
      if (sections.length < 2 || $(".case-toc", view)) continue;
      const nav = el("nav", "case-toc", { "aria-label": "On this page" });
      sections.forEach((section, index) => {
        if (!section.id) section.id = `${view.id || "view"}--s${index + 1}`;
        const label = text($(":scope > span", section)) || text($("h2", section)) || section.id;
        const link = el("a", "", { href: `#${section.id}` });
        link.textContent = label.replace(/^\d+\s*\/\s*/, "");
        nav.append(link);
      });
      const body = $(".case-body", view) || sections[0];
      body.before(nav);
    }
  }

  /* ---- Header tools: theme, palette, menu ---- */
  const ICONS = {
    sun: '<svg class="icon-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg><svg class="icon-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h16M4 16h16"/></svg>',
    close: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    up: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>'
  };
  let menuButton = null;
  function closeMenu() {
    const nav = $(".site-nav");
    if (!nav || !menuOpen) return;
    menuOpen = false;
    nav.removeAttribute("data-open");
    if (menuButton) { menuButton.setAttribute("aria-expanded", "false"); menuButton.innerHTML = ICONS.menu; }
  }
  function setupHeaderTools() {
    const header = $(".site-header");
    const nav = $(".site-nav");
    const up = el("button", "to-top", { type: "button", "aria-label": "Back to top" });
    up.innerHTML = ICONS.up;
    up.addEventListener("click", () => window.scrollTo({ top: 0, behavior: reduced.matches ? "instant" : "smooth" }));
    doc.body.append(up);
    if (!header) return;
    const tools = el("div", "header-tools");

    themeButton = el("button", "tool-btn theme-toggle", { type: "button", "aria-label": "Dark mode", title: "Toggle light / dark" });
    themeButton.innerHTML = ICONS.sun;
    themeButton.addEventListener("click", (event) => {
      const rect = themeButton.getBoundingClientRect();
      const origin = event.detail === 0 ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : { x: event.clientX, y: event.clientY };
      setTheme(currentScheme() === "dark" ? "light" : "dark", origin);
    });
    tools.append(themeButton);

    if (typeof HTMLDialogElement === "function") {
      const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
      const paletteButton = el("button", "tool-btn palette-btn", { type: "button", "aria-label": "Quick navigation", title: "Quick navigation" });
      paletteButton.innerHTML = ICONS.search;
      const hint = el("kbd");
      hint.textContent = mac ? "⌘K" : "Ctrl K";
      paletteButton.append(hint);
      paletteButton.addEventListener("click", () => openPalette());
      tools.append(paletteButton);
    }

    if (nav) {
      if (!nav.id) nav.id = "atlas-site-nav";
      menuButton = el("button", "tool-btn menu-toggle", { type: "button", "aria-label": "Menu", "aria-expanded": "false", "aria-controls": nav.id });
      menuButton.innerHTML = ICONS.menu;
      menuButton.addEventListener("click", () => {
        menuOpen = !menuOpen;
        nav.toggleAttribute("data-open", menuOpen);
        menuButton.setAttribute("aria-expanded", String(menuOpen));
        menuButton.innerHTML = menuOpen ? ICONS.close : ICONS.menu;
        if (menuOpen) root.dataset.header = "";
      });
      tools.append(menuButton);
      // composedPath(): swapping the button icon detaches event.target mid-click.
      doc.addEventListener("click", (event) => {
        if (menuOpen && !event.composedPath().includes(header)) closeMenu();
      });
      doc.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menuOpen) { closeMenu(); menuButton.focus(); }
      });
      nav.addEventListener("click", (event) => { if (event.target.closest("a")) closeMenu(); });
      mq("(min-width: 52.01rem)").addEventListener("change", closeMenu);
      if ("ResizeObserver" in window) new ResizeObserver(placeIndicator).observe(nav);
    }
    header.append(tools);
    syncThemeUi();
    darkScheme.addEventListener("change", syncThemeUi);
  }

  /* ---- Command palette ---- */
  function setupPalette() {
    if (typeof HTMLDialogElement !== "function") return;
    const dialog = el("dialog", "palette", { "aria-label": "Quick navigation" });
    const box = el("div", "palette-box");
    const input = el("input", "palette-input", {
      type: "text", placeholder: "Jump to a page or section…", role: "combobox", "aria-expanded": "true",
      "aria-controls": "atlas-palette-list", "aria-autocomplete": "list", autocomplete: "off", spellcheck: "false", "aria-label": "Search pages and sections"
    });
    const list = el("ul", "palette-list", { id: "atlas-palette-list", role: "listbox", "aria-label": "Results" });
    const foot = el("div", "palette-foot");
    foot.innerHTML = "<span>↑↓ move</span><span>↵ open</span><span>esc close</span>";
    box.append(input, list, foot);
    dialog.append(box);
    doc.body.append(dialog);

    let items = [];
    let shown = [];
    let selected = 0;

    const collect = () => {
      const found = [];
      const used = new Set();
      views.forEach((view) => {
        const label = viewLabel(view);
        found.push({ label, hint: "Page", go: view.id });
        used.add(view.id);
      });
      views.forEach((view) => {
        $$("section[id]", view).forEach((section) => {
          if (used.has(section.id) || /--s\d+$/.test(section.id)) return;
          const heading = $("h1, h2, h3", section);
          const label = text(heading) || section.id;
          found.push({ label, hint: text($(".section-kicker", section)) ? "Section" : "Section", go: section.id });
          used.add(section.id);
        });
      });
      const mail = $("a[href^='mailto:']");
      if (mail) found.push({ label: `Email ${mail.getAttribute("href").replace(/^mailto:/, "").split("?")[0]}`, hint: "Contact", href: mail.getAttribute("href") });
      found.push({ label: "Toggle light / dark", hint: "Theme", action: () => setTheme(currentScheme() === "dark" ? "light" : "dark") });
      return found;
    };
    const render = () => {
      const tokens = input.value.toLowerCase().split(/\s+/).filter(Boolean);
      shown = items.filter((item) => tokens.every((token) => item.label.toLowerCase().includes(token)));
      selected = clamp(selected, 0, Math.max(0, shown.length - 1));
      list.replaceChildren();
      if (!shown.length) {
        const empty = el("li", "palette-empty", { role: "presentation" });
        empty.textContent = "Nothing matches that.";
        list.append(empty);
        input.removeAttribute("aria-activedescendant");
        return;
      }
      shown.forEach((item, index) => {
        const row = el("li", "", { role: "option", id: `atlas-opt-${index}`, "aria-selected": String(index === selected) });
        const label = el("span");
        label.textContent = item.label;
        const hint = el("span", "pi-hint");
        hint.textContent = item.hint;
        row.append(label, hint);
        row.addEventListener("pointermove", () => { if (selected !== index) { selected = index; mark(); } });
        row.addEventListener("click", () => choose(item));
        list.append(row);
      });
      input.setAttribute("aria-activedescendant", `atlas-opt-${selected}`);
    };
    const mark = () => {
      $$("li[role='option']", list).forEach((row, index) => {
        row.setAttribute("aria-selected", String(index === selected));
        if (index === selected) { row.scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", row.id); }
      });
    };
    const choose = (item) => {
      dialog.close();
      if (item.go) window.location.hash = item.go;
      else if (item.href) window.location.href = item.href;
      else if (item.action) item.action();
    };
    openPalette = () => {
      if (dialog.open) return;
      items = collect();
      input.value = "";
      selected = 0;
      render();
      dialog.showModal();
      input.focus();
    };
    input.addEventListener("input", () => { selected = 0; render(); });
    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") { event.preventDefault(); selected = (selected + 1) % Math.max(1, shown.length); mark(); }
      else if (event.key === "ArrowUp") { event.preventDefault(); selected = (selected - 1 + shown.length) % Math.max(1, shown.length); mark(); }
      else if (event.key === "Enter" && shown[selected]) { event.preventDefault(); choose(shown[selected]); }
    });
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    doc.addEventListener("keydown", (event) => {
      const typing = event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable='true']");
      if ((event.key === "k" || event.key === "K") && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        if (dialog.open) dialog.close(); else openPalette();
      } else if (event.key === "/" && !typing && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        openPalette();
      }
    });
  }

  /* ---- Pointer effects (fine pointers only) ---- */
  function setupPointerEffects() {
    if (!finePointer.matches || !motionOn()) return;
    const spotSelector = ".project-art, .capability-grid > div, .impact-grid > div, .case-result, .approach-list > div, [data-spot]";
    const magnetSelector = ".button, .header-cta, .back-link";
    let frame = 0;
    let event = null;
    let tiltCard = null;
    let magnet = null;
    const reset = () => {
      if (tiltCard) {
        const art = $(".project-art", tiltCard);
        if (art) { art.style.setProperty("--rx", "0deg"); art.style.setProperty("--ry", "0deg"); }
        tiltCard = null;
      }
      if (magnet) { magnet.style.setProperty("--tx", "0px"); magnet.style.setProperty("--ty", "0px"); magnet = null; }
    };
    const handle = () => {
      frame = 0;
      const target = event && event.target instanceof Element ? event.target : null;
      if (!target) return;
      const spot = target.closest(spotSelector);
      if (spot) {
        const rect = spot.getBoundingClientRect();
        spot.style.setProperty("--mx", `${(event.clientX - rect.left).toFixed(0)}px`);
        spot.style.setProperty("--my", `${(event.clientY - rect.top).toFixed(0)}px`);
      }
      const card = target.closest(".project-card");
      if (tiltCard && tiltCard !== card) reset();
      if (card) {
        const art = $(".project-art", card);
        if (art) {
          const rect = art.getBoundingClientRect();
          const px = clamp((event.clientX - rect.left) / rect.width - 0.5, -0.5, 0.5);
          const py = clamp((event.clientY - rect.top) / rect.height - 0.5, -0.5, 0.5);
          art.style.setProperty("--rx", `${(px * 5).toFixed(2)}deg`);
          art.style.setProperty("--ry", `${(-py * 4).toFixed(2)}deg`);
          tiltCard = card;
        }
      }
      const button = target.closest(magnetSelector);
      if (magnet && magnet !== button) { magnet.style.setProperty("--tx", "0px"); magnet.style.setProperty("--ty", "0px"); magnet = null; }
      if (button) {
        const rect = button.getBoundingClientRect();
        button.style.setProperty("--tx", `${clamp((event.clientX - (rect.left + rect.width / 2)) * 0.18, -9, 9).toFixed(1)}px`);
        button.style.setProperty("--ty", `${clamp((event.clientY - (rect.top + rect.height / 2)) * 0.28, -7, 7).toFixed(1)}px`);
        magnet = button;
      }
    };
    doc.addEventListener("pointermove", (moveEvent) => {
      if (moveEvent.pointerType !== "mouse") return;
      event = moveEvent;
      if (!frame) frame = requestAnimationFrame(handle);
    }, { passive: true });
    doc.addEventListener("pointerleave", reset);
    window.addEventListener("blur", reset);
  }

  /* ---- Scroll: progress, header, spy, timeline, back-to-top ---- */
  function setupScroll() {
    let lastY = window.scrollY;
    let ticking = false;
    const toTop = $(".to-top");
    const frame = () => {
      ticking = false;
      const y = window.scrollY;
      if (!nativeScrollTimeline) {
        const max = Math.max(1, root.scrollHeight - innerHeight);
        root.style.setProperty("--scroll", clamp(y / max, 0, 1).toFixed(4));
      }
      const delta = y - lastY;
      if (Math.abs(delta) > 6) {
        root.dataset.header = delta > 0 && y > 180 && !menuOpen ? "hidden" : "";
        lastY = y;
      }
      if (y < 80) root.dataset.header = "";
      if (toTop) toTop.classList.toggle("is-visible", y > innerHeight * 1.2);

      if (spy.targets.length) {
        const line = innerHeight * 0.4;
        let current = null;
        for (const target of spy.targets) {
          const rect = target.el.getBoundingClientRect();
          if (rect.top <= line && rect.bottom > line) current = target.id;
        }
        if (current !== spy.id) {
          spy.id = current;
          if (activeView) updateNav({ id: resolveRoute().id, view: activeView });
          $$(".case-toc a", activeView || doc).forEach((link) => {
            if (decode(link.getAttribute("href").slice(1)) === current) link.setAttribute("aria-current", "true");
            else link.removeAttribute("aria-current");
          });
        }
      }
      if (activeView) {
        for (const timeline of $$(".timeline", activeView)) {
          const rect = timeline.getBoundingClientRect();
          if (rect.bottom < 0 || rect.top > innerHeight) continue;
          timeline.style.setProperty("--tl", clamp((innerHeight * 0.62 - rect.top) / Math.max(1, rect.height), 0, 1).toFixed(3));
        }
      }
    };
    const schedule = () => { if (!ticking) { ticking = true; requestAnimationFrame(frame); } };
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", () => { placeIndicator(); schedule(); }, { passive: true });
    frame();
  }

  /* ---- Contract self-check (silent unless asked) ---- */
  function audit() {
    const errors = [];
    const warnings = [];
    if (!views.length) errors.push("No [data-view] elements found.");
    const seen = new Map();
    $$("[id]").forEach((node) => seen.set(node.id, (seen.get(node.id) || 0) + 1));
    seen.forEach((count, id) => { if (count > 1) errors.push(`Duplicate id "${id}" (${count}x).`); });
    views.forEach((view) => {
      if (!view.id) errors.push("A [data-view] element has no id.");
      const h1s = $$("h1", view);
      if (h1s.length !== 1) warnings.push(`View #${view.id} has ${h1s.length} <h1> elements (expected 1).`);
      if (!view.dataset.title) warnings.push(`View #${view.id} has no data-title.`);
      let last = 0;
      $$("h1,h2,h3,h4,h5", view).forEach((heading) => {
        const level = Number(heading.tagName[1]);
        if (last && level > last + 1) warnings.push(`View #${view.id}: heading level jumps from h${last} to h${level} ("${text(heading).slice(0, 40)}").`);
        last = level;
      });
    });
    $$("a[href^='#']").forEach((link) => {
      const id = decode(link.getAttribute("href").slice(1));
      if (id && !doc.getElementById(id)) errors.push(`Link "#${id}" has no target.`);
    });
    $$("img").forEach((img) => { if (!img.hasAttribute("alt")) errors.push(`Image without alt: ${img.getAttribute("src")}`); });
    if (!$(".site-nav")) warnings.push("No .site-nav found.");
    return { ok: errors.length === 0, errors, warnings, views: views.map((view) => view.id) };
  }

  /* ---- Boot ---- */
  // style.css holds the first paint until data-boot is set (see "Boot veil").
  // Lift it once the fonts in use have arrived (bounded), so the web-font swap
  // happens while the page is still hidden and never shifts visible content.
  function init() {
    let lifted = false;
    const lift = () => { if (!lifted) { lifted = true; root.dataset.boot = ""; } };
    try { boot(); } catch (error) { lift(); throw error; }
    void root.offsetHeight; // force layout so the fonts this page uses are requested
    const pending = doc.fonts && doc.fonts.status === "loading" ? Promise.race([doc.fonts.ready, sleep(800)]) : null;
    if (pending) pending.then(lift, lift); else lift();
  }

  function boot() {
    views = $$("[data-view]");
    viewById = new Map(views.map((view) => [view.id, view]));
    homeView = viewById.get("home") || views[0] || null;

    guard("chrome", ensureChrome);
    const intro = guard("loader", startLoader) || Promise.resolve();

    guard("art", assignArt);
    guard("portraits", setupPortraits);
    guard("images", setupImages);
    guard("fit", fitHeadings);
    guard("numerals", tagNumerals);
    guard("toc", buildToc);
    guard("marquee", setupMarquee);
    guard("split", splitHeadings);
    guard("counters", setupCounters);
    guard("reveals", setupReveals);
    guard("live", setupLiveLoops);
    guard("header", setupHeaderTools);
    guard("palette", setupPalette);
    guard("pointer", setupPointerEffects);

    doc.addEventListener("click", (event) => {
      const link = event.target instanceof Element ? event.target.closest("a[href^='#']") : null;
      if (link && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey) {
        linkNav = true;
        clickedCard = link.closest(".project-card");
      }
    }, true);
    ["wheel", "touchstart", "keydown", "pointerdown"].forEach((name) => {
      window.addEventListener(name, () => { userScrolled = true; }, { once: true, passive: true });
    });
    window.addEventListener("hashchange", () => guard("route", () => activateRoute()));
    guard("route", () => activateRoute(true));
    guard("scroll", setupScroll);
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(placeIndicator);

    // A direct hash load can be re-scrolled natively after our first frame.
    window.addEventListener("load", () => {
      setTimeout(() => {
        if (userScrolled || !activeView) return;
        const route = resolveRoute();
        if (route.target) route.target.scrollIntoView({ block: "start", behavior: "instant" });
        else if (window.scrollY < 4) window.scrollTo({ top: 0, behavior: "instant" });
        placeIndicator();
      }, 0);
    }, { once: true });

    // Never leave content hidden if something upstream stalls.
    const failsafe = setTimeout(() => root.removeAttribute("data-motion"), 8000);
    intro.then(() => {
      clearTimeout(failsafe);
      introDone = true;
      guard("observe", () => observeReveals(doc));
      root.dataset.atlas = "ready";
      readyResolve(true);
      if (debug) console.info("[atlas] audit", audit());
    });
  }

  window.AtlasTheme = Object.freeze({
    version: VERSION,
    audit,
    ready: readyPromise,
    go: (id) => { window.location.hash = id; },
    setTheme: (mode) => setTheme(mode),
    openPalette: () => openPalette()
  });

  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
