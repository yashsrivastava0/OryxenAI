/* Claret Marquee v1 — content-independent behaviour.
   Reads structure only ([data-view], [data-scene], [data-chapter], headings, optional classes);
   no person text and no hard-coded routes. Progressive: the page is complete without it.
   No libraries, no network; styles are written only through the CSSOM (style.setProperty). */
(() => {
  "use strict";
  if (window.PortfolioTheme) return;

  const doc = document;
  const root = doc.documentElement;
  const VERSION = "1.0.0";
  const TAU = Math.PI * 2;

  const $ = (selector, scope = doc) => scope.querySelector(selector);
  const $$ = (selector, scope = doc) => Array.from(scope.querySelectorAll(selector));
  const mq = (query) => window.matchMedia(query);
  const params = new URLSearchParams(window.location.search);
  const debug = params.has("cm-debug");
  const reduced = mq("(prefers-reduced-motion: reduce)");
  const darkScheme = mq("(prefers-color-scheme: dark)");
  const hasIO = "IntersectionObserver" in window;
  // Automated visitors (screenshots, host verification) get the finished page: no veil, no
  // hidden-until-revealed content. Opt back in with ?motion=1 when testing motion itself.
  const automated = navigator.webdriver === true && !params.has("motion");
  const nativeTimeline = !!(window.CSS && CSS.supports && CSS.supports("animation-timeline: view()"));

  const warn = (...args) => { if (debug) console.warn("[marquee]", ...args); };
  const guard = (name, fn) => {
    try { return fn(); } catch (error) { warn(`${name} failed`, error); return undefined; }
  };
  const el = (tag, className, attrs) => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (attrs) for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const text = (node) => (node ? node.textContent.replace(/\s+/g, " ").trim() : "");
  const decode = (value) => { try { return decodeURIComponent(value); } catch { return ""; } };

  /* ---- Storage that survives opaque-origin sandboxes (localStorage throws there) ---- */
  const store = (() => {
    const memory = new Map();
    const probe = (kind) => {
      try { const area = window[kind]; area.setItem("__cm", "1"); area.removeItem("__cm"); return area; } catch { return null; }
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

  /* ---- Flags (set synchronously, before anything is measured) ---- */
  root.classList.add("js");
  const forced = params.get("driver");
  const driver = forced === "js" || (forced !== "native" && !nativeTimeline) ? "js" : "native";
  const motionState = () => (reduced.matches ? "reduced" : automated ? "off" : "full");
  const motionOn = () => root.dataset.motion === "full";
  root.dataset.motion = motionState();
  root.dataset.driver = driver === "native" && !nativeTimeline ? "js" : driver;
  if (reduced.addEventListener) reduced.addEventListener("change", () => { root.dataset.motion = motionState(); measureAll(); });

  /* ---- State ---- */
  let views = [];
  let viewById = new Map();
  let homeView = null;
  let activeView = null;
  let announcer = null;
  let themeButton = null;
  let pauseButton = null;
  let scrub = null;
  let linkNav = false;
  let origin = null;
  let clickedLink = null;
  let navKey = "";
  const scrollMemory = new Map();
  const scenes = [];
  const parallax = [];
  const lights = [];
  const tones = { claret: [] };
  let chapters = [];
  let ticker = null;
  let revealObserver = null;
  let countObserver = null;
  let lastScrollY = window.scrollY;
  let skew = 0;
  let timecodeShown = "";
  let heroProgress = 0;
  let readyResolve = () => {};
  const readyPromise = new Promise((resolve) => { readyResolve = resolve; });

  /* ---- Theme (light / dark) ---- */
  const savedTheme = store.get("cm-theme");
  if (savedTheme === "light" || savedTheme === "dark") root.dataset.theme = savedTheme;
  const currentScheme = () => root.dataset.theme || (darkScheme.matches ? "dark" : "light");
  function syncThemeUi() {
    if (themeButton) themeButton.setAttribute("aria-pressed", String(currentScheme() === "dark"));
  }
  // A same-document View Transition used purely as decoration: every promise is caught, it is
  // skipped when hidden or when motion is off, and the state change itself never waits for it.
  function transition(apply, className, from) {
    if (!motionOn() || doc.hidden || typeof doc.startViewTransition !== "function") { apply(); return Promise.resolve(); }
    const point = from || { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    root.style.setProperty("--vx", `${Math.round(point.x)}px`);
    root.style.setProperty("--vy", `${Math.round(point.y)}px`);
    root.classList.add(className);
    const run = doc.startViewTransition(apply);
    run.ready.catch(() => {});
    run.updateCallbackDone.catch(() => {});
    return run.finished.catch(() => {}).then(() => root.classList.remove(className));
  }
  function setTheme(next, from) {
    if (next !== "light" && next !== "dark") return;
    transition(() => { root.dataset.theme = next; store.set("cm-theme", next); syncThemeUi(); }, "is-vt-iris", from);
  }

  /* ---- Router: one article.route-view per route; hidden toggled synchronously ---- */
  function resolveRoute() {
    const id = decode(window.location.hash.slice(1).replace(/^\/+/, ""));
    if (!id) return { id: "", view: homeView, target: null };
    const asView = viewById.get(id);
    if (asView) return { id, view: asView, target: null };
    const node = doc.getElementById(id);
    const owner = node && node.closest("[data-view]");
    if (owner) return { id, view: owner, target: node };
    if (node && activeView) return { id: activeView.id, view: activeView, target: node, outside: true };
    return { id, view: homeView, target: null, missing: true };
  }

  function placeScroll(route, restore) {
    if (route.target) route.target.scrollIntoView({ block: "start", behavior: "instant" });
    else if (restore && scrollMemory.has(route.view.id)) window.scrollTo({ top: scrollMemory.get(route.view.id), behavior: "instant" });
    else window.scrollTo({ top: 0, behavior: "instant" });
  }

  function afterRoute(route, initial) {
    if (!initial) {
      const heading = route.outside ? route.target : route.target ? ($("h1,h2,h3", route.target) || route.target) : $("h1", route.view);
      if (heading) {
        if (!heading.hasAttribute("tabindex")) heading.setAttribute("tabindex", "-1");
        heading.focus({ preventScroll: true });
      }
      if (announcer) { announcer.textContent = ""; announcer.textContent = doc.title; }
    }
    measureAll();
    observeReveals(route.view);
  }

  function activate(initial, instant) {
    if (!views.length) return;
    const route = resolveRoute();
    const previous = activeView;
    const changed = previous !== route.view;
    const viaLink = linkNav;
    linkNav = false;
    if (previous) scrollMemory.set(previous.id, window.scrollY);
    const restore = !viaLink && !initial && changed;
    const commit = () => {
      for (const view of views) view.hidden = view !== route.view;
      doc.body.dataset.router = "ready";
      activeView = route.view;
      doc.title = route.view.dataset.title || doc.title;
      // Same-view anchors are scrolled (smoothly) by the browser; only a view change or a
      // programmatic go() needs an explicit jump.
      if (changed || initial) placeScroll(route, restore);
      else if (instant && route.target) route.target.scrollIntoView({ block: "start", behavior: "instant" });
      navKey = "";
      updateNav(route);
    };
    if (changed && !initial && !instant && viaLink) {
      // A project card and its case page share one poster: let it travel. Everything else
      // uses the iris cut from the click point.
      const pair = pairArt(previous, route.view, clickedLink);
      if (pair) pair.from.style.setProperty("view-transition-name", "cm-art");
      const apply = () => {
        if (pair) {
          pair.from.style.setProperty("view-transition-name", "none");
          pair.to.style.setProperty("view-transition-name", "cm-art");
        }
        commit();
      };
      transition(apply, pair ? "is-vt-art" : "is-vt-iris", origin).then(() => {
        if (pair) {
          pair.from.style.removeProperty("view-transition-name");
          pair.to.style.removeProperty("view-transition-name");
        }
        afterRoute(route, initial);
      });
    } else {
      commit();
      afterRoute(route, initial);
    }
  }

  function pairArt(fromView, toView, link) {
    if (!fromView || !toView || typeof doc.startViewTransition !== "function") return null;
    let from = null;
    let to = null;
    if (toView.id.startsWith("case-")) {
      const card = (link && link.closest(".project")) || $(`.project[href="#${CSS.escape(toView.id)}"]`, fromView);
      from = card && $(".poster", card);
      to = $(".case-art .poster", toView);
    } else if (fromView.id.startsWith("case-")) {
      const card = $(`.project[href="#${CSS.escape(fromView.id)}"]`, toView);
      from = $(".case-art .poster", fromView);
      to = card && $(".poster", card);
    }
    return from && to ? { from, to } : null;
  }

  function go(id) {
    const target = String(id || "").replace(/^#/, "");
    if (!target) return false;
    if (window.location.hash.slice(1) !== target) window.location.hash = target;
    activate(false, true);
    return true;
  }

  function updateNav(route) {
    const current = (route && route.view && route.view.id) || "";
    const section = chapters.length ? (chapters.find((c) => c.current) || {}).id || "" : "";
    const key = `${current}|${section}`;
    if (key === navKey) return;
    navKey = key;
    for (const link of $$(".topnav a[href^='#']")) {
      const id = decode(link.getAttribute("href").slice(1));
      const on = id === section || (id === "about" && current === "about") || (id === "work" && current.startsWith("case-"));
      if (on) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
    }
  }

  function setupRouter() {
    views = $$("[data-view]");
    if (!views.length) return;
    viewById = new Map(views.map((view) => [view.id, view]));
    homeView = viewById.get("home") || views[0];
    announcer = $("#route-announcer");
    if (!announcer) { announcer = el("span", "sr-only", { id: "route-announcer", role: "status", "aria-live": "polite" }); doc.body.append(announcer); }
    window.addEventListener("hashchange", () => activate(false, false));
    doc.addEventListener("click", (event) => {
      const link = event.target instanceof Element ? event.target.closest("a[href^='#']") : null;
      if (!link) return;
      if (link.getAttribute("href") === "#main") {
        // Skip link: move focus, but do not add a history entry that Back would land on.
        event.preventDefault();
        const main = $("#main");
        if (main) { main.setAttribute("tabindex", "-1"); main.focus(); main.scrollIntoView({ block: "start", behavior: "instant" }); }
        return;
      }
      linkNav = true;
      clickedLink = link;
      const box = link.getBoundingClientRect();
      origin = event.clientX || event.clientY ? { x: event.clientX, y: event.clientY } : { x: box.left + box.width / 2, y: box.top + box.height / 2 };
    }, true);
    activate(true, true);
  }

  /* ---- Measuring (cached document positions: nothing is read per frame) ---- */
  const docTop = (node) => node.getBoundingClientRect().top + window.scrollY;

  function measureAll() {
    guard("measure", () => {
      const vh = window.innerHeight;
      scenes.length = 0;
      parallax.length = 0;
      lights.length = 0;
      tones.claret = [];
      if (!activeView) return;
      for (const node of $$("[data-scene]", activeView)) {
        // A hero whose copy would not fit the pinned stage flows instead of being clipped.
        const stage = $(".hero-stage", node);
        if (stage) {
          node.removeAttribute("data-flow");
          if (motionOn() && stage.scrollHeight > stage.clientHeight + 2) node.setAttribute("data-flow", "");
        }
        const top = docTop(node);
        scenes.push({ node, top, span: Math.max(1, node.offsetHeight - vh), p: -1 });
      }
      for (const node of $$(".poster", activeView)) {
        const box = node.getBoundingClientRect();
        parallax.push({ node, mid: box.top + window.scrollY + box.height / 2, py: 99 });
      }
      for (const node of $$(".thesis-statement[data-lit]", activeView)) {
        const box = node.getBoundingClientRect();
        lights.push({ node, top: box.top + window.scrollY, height: box.height, count: Number(node.dataset.lit), lit: -1 });
      }
      const heroNode = $(".hero", activeView);
      for (const node of [heroNode, $(".credits", activeView), $(".site-footer")]) {
        if (!node || node.offsetParent === null && node !== node.ownerDocument.body) continue;
        const top = docTop(node);
        tones.claret.push({ top, bottom: top + node.offsetHeight });
      }
      chapters = $$("[data-chapter]", activeView).map((node) => {
        const top = docTop(node);
        const label = text($(".eyebrow,.kicker,h1,h2", node)).slice(0, 28);
        return { id: node.id || "", node, top, bottom: top + node.offsetHeight, label, current: false };
      });
      buildScrubTicks();
      measureTicker();
      requestFrame();
    });
  }

  /* ---- Frame loop: scroll-driven writes (scenes, light, parallax, scrubber, tones) ---- */
  let ticking = false;
  function requestFrame() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(frame);
  }

  function frame() {
    ticking = false;
    const y = window.scrollY;
    const vh = window.innerHeight;
    const max = Math.max(1, doc.documentElement.scrollHeight - vh);
    const progress = clamp(y / max, 0, 1);
    root.style.setProperty("--sp", progress.toFixed(4));
    for (const scene of scenes) {
      const p = clamp((y - scene.top) / scene.span, 0, 1);
      if (scene.node.classList.contains("hero")) heroProgress = p;
      if (root.dataset.driver === "js" && motionOn() && Math.abs(p - scene.p) > 0.0004) {
        scene.node.style.setProperty("--p", p.toFixed(4));
        scene.p = p;
      }
    }
    if (motionOn()) {
      for (const item of parallax) {
        const py = clamp((item.mid - y - vh / 2) / vh, -1, 1);
        if (Math.abs(py - item.py) > 0.002) { item.node.style.setProperty("--py", py.toFixed(3)); item.py = py; }
      }
      for (const item of lights) {
        const lit = clamp((vh * 0.88 - (item.top - y)) / (vh * 0.62 + item.height * 0.5), 0, 1) * (item.count + 3);
        if (Math.abs(lit - item.lit) > 0.02) { item.node.style.setProperty("--lit", lit.toFixed(2)); item.lit = lit; }
      }
    }
    const inClaret = (at) => tones.claret.some((range) => at >= range.top && at <= range.bottom);
    const top = inClaret(y + 34) ? "claret" : "paper";
    const bottom = inClaret(y + vh - 20) ? "claret" : "paper";
    if (root.dataset.top !== top) root.dataset.top = top;
    if (root.dataset.bottom !== bottom) root.dataset.bottom = bottom;
    const scrolled = y > 24;
    if (root.hasAttribute("data-scrolled") !== scrolled) root.toggleAttribute("data-scrolled", scrolled);
    let current = null;
    for (const chapter of chapters) { chapter.current = false; if (y + vh * 0.35 >= chapter.top) current = chapter; }
    if (current) current.current = true;
    updateNav({ view: activeView });
    updateScrub(progress, current);
    const delta = y - lastScrollY;
    lastScrollY = y;
    if (ticker && motionOn()) {
      skew += (clamp(-delta * 0.12, -7, 7) - skew) * 0.2;
      ticker.style.setProperty("--skew", `${skew.toFixed(2)}deg`);
      if (Math.abs(skew) > 0.02) requestFrame(); else if (skew !== 0) { skew = 0; ticker.style.setProperty("--skew", "0deg"); }
    }
  }

  /* ---- Scrubber nav (decor + shortcuts), timecode, tools ---- */
  function buildScrub() {
    if (scrub || !motionOn()) return;
    scrub = el("div", "scrub", { "aria-hidden": "true" });
    const label = el("span", "scrub-label");
    const track = el("div", "scrub-track");
    track.append(el("span", "scrub-fill"), el("span", "scrub-head"));
    const time = el("span", "scrub-time");
    time.textContent = "00:00";
    scrub.append(label, track, time);
    doc.body.append(scrub);
  }
  function buildScrubTicks() {
    if (!scrub) return;
    const track = $(".scrub-track", scrub);
    $$(".scrub-tick", track).forEach((node) => node.remove());
    const max = Math.max(1, doc.documentElement.scrollHeight - window.innerHeight);
    track.style.setProperty("--tw", `${track.clientWidth}px`);
    for (const chapter of chapters) {
      const tick = el("button", "scrub-tick", { type: "button", tabindex: "-1" });
      tick.style.setProperty("left", `${(clamp(chapter.top / max, 0, 1) * 100).toFixed(2)}%`);
      tick.addEventListener("click", () => chapter.node.scrollIntoView({ block: "start", behavior: "smooth" }));
      track.append(tick);
    }
  }
  function updateScrub(progress, current) {
    if (!scrub) return;
    const label = $(".scrub-label", scrub);
    const next = current ? current.label : "";
    if (label.textContent !== next) label.textContent = next;
    const seconds = Math.round(progress * 240);
    const code = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
    if (code !== timecodeShown) { $(".scrub-time", scrub).textContent = code; timecodeShown = code; }
  }
  function buildTools() {
    const bar = $(".topbar");
    if (!bar || $(".tools", bar)) return;
    const tools = el("div", "tools");
    themeButton = el("button", "tool tool-theme", { type: "button", "aria-label": "Dark mode", "aria-pressed": "false" });
    themeButton.addEventListener("click", (event) => {
      const box = themeButton.getBoundingClientRect();
      const from = event.clientX || event.clientY ? { x: event.clientX, y: event.clientY } : { x: box.left + box.width / 2, y: box.top + box.height / 2 };
      setTheme(currentScheme() === "dark" ? "light" : "dark", from);
    });
    tools.append(themeButton);
    if (motionOn()) {
      pauseButton = el("button", "tool tool-pause", { type: "button", "aria-label": "Pause motion", "aria-pressed": "false" });
      pauseButton.addEventListener("click", () => {
        const next = !root.hasAttribute("data-paused");
        root.toggleAttribute("data-paused", next);
        pauseButton.setAttribute("aria-pressed", String(next));
      });
      tools.append(pauseButton);
    }
    bar.append(tools);
    syncThemeUi();
  }

  /* ---- Reveals, rack-focus, word highlight, counters ---- */
  function setupReveals() {
    if (!motionOn() || !hasIO) return;
    const groups = new Map();
    const mark = (selector, className) => {
      for (const node of $$(selector)) {
        if (node.classList.contains("rv") || node.classList.contains("rf")) continue;
        const parent = node.parentElement;
        const index = groups.get(parent) || 0;
        groups.set(parent, index + 1);
        node.style.setProperty("--i", String(Math.min(index, 6)));
        node.classList.add(className);
      }
    };
    mark(".section-title,.about-teaser-copy h2,.credits h2,.page-head h1,.case-head h1", "rf");
    mark(".proof-head,.figure,.orgs,.pillar,.project,.work-empty,.about-teaser .portrait,.about-teaser-text,.credits-intro,.destinations li,.ledger-row,.group,.case-step,.facts,.lede,.pull blockquote,.thesis-intro", "rv");
    revealObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in");
        revealObserver.unobserve(entry.target);
      }
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    countObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        countUp(entry.target);
        countObserver.unobserve(entry.target);
      }
    }, { threshold: 0.6 });
  }
  function observeReveals(view) {
    if (!revealObserver) return;
    $$(".rv:not(.is-in),.rf:not(.is-in)", view).forEach((node) => revealObserver.observe(node));
    $$(".figure-value:not([data-counted])", view).forEach((node) => countObserver.observe(node));
  }
  function countUp(node) {
    node.dataset.counted = "1";
    const original = node.textContent;
    const match = original.match(/(\d[\d,]*\.?\d*)/);
    if (!match || reduced.matches) return;
    const final = parseFloat(match[1].replace(/,/g, ""));
    if (!Number.isFinite(final)) return;
    const decimals = (match[1].split(".")[1] || "").length;
    const commas = match[1].includes(",");
    const format = (value) => value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: commas });
    const started = performance.now();
    const duration = 1400;
    const step = (now) => {
      const t = clamp((now - started) / duration, 0, 1);
      const eased = 1 - Math.pow(1 - t, 4);
      node.textContent = original.replace(match[1], format(final * eased));
      if (t < 1) requestAnimationFrame(step); else node.textContent = original;
    };
    requestAnimationFrame(step);
  }
  // Word-level split only (never letters): whitespace text nodes stay in place.
  function splitStatements() {
    if (!motionOn()) return;
    for (const node of $$(".thesis-statement")) {
      if (node.dataset.lit) continue;
      const original = node.textContent;
      const parts = original.split(/(\s+)/);
      node.textContent = "";
      let count = 0;
      for (const part of parts) {
        if (!part) continue;
        if (/^\s+$/.test(part)) { node.append(doc.createTextNode(part)); continue; }
        const word = el("span", "w");
        word.textContent = part;
        word.style.setProperty("--wi", String(count));
        node.append(word);
        count += 1;
      }
      node.dataset.lit = String(count);
    }
  }

  /* ---- Ticker (duplicate once for a seamless loop; duplicates are aria-hidden) ---- */
  function setupTicker() {
    const node = $(".ticker-track");
    if (!node || !motionOn() || node.dataset.ready) return;
    ticker = node;
    node.dataset.ready = "1";
    for (const item of Array.from(node.children)) {
      const copy = item.cloneNode(true);
      copy.removeAttribute("data-field");
      copy.setAttribute("aria-hidden", "true");
      node.append(copy);
    }
  }
  function measureTicker() {
    if (!ticker) return;
    const width = ticker.scrollWidth / 2;
    ticker.style.setProperty("--ticker-dur", `${clamp(width / 55, 24, 140).toFixed(0)}s`);
  }

  /* ---- Dust: one small canvas of drifting motes in the hero beam (auto-degrades) ---- */
  function setupDust() {
    const art = $(".hero-art");
    if (!art || !motionOn() || (navigator.deviceMemory && navigator.deviceMemory <= 2) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2)) return;
    const canvas = el("canvas", "dust", { "aria-hidden": "true" });
    art.append(canvas);
    const ctx = canvas.getContext("2d");
    if (!ctx) { canvas.remove(); return; }
    const motes = Array.from({ length: 110 }, () => ({ x: Math.random(), y: Math.random(), z: 0.25 + Math.random() * 0.75, r: 0.6 + Math.random() * 1.7, s: 0.4 + Math.random() * 1.4, ph: Math.random() * TAU }));
    let width = 0;
    let height = 0;
    let visible = true;
    let slow = 0;
    let frames = 0;
    let last = performance.now();
    const size = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const box = art.getBoundingClientRect();
      width = Math.max(1, Math.round(box.width));
      height = Math.max(1, Math.round(box.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (now) => {
      requestAnimationFrame(draw);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!visible || doc.hidden || root.hasAttribute("data-paused") || !motionOn()) return;
      frames += 1;
      if (frames > 30 && frames <= 150 && dt > 0.034) slow += 1;
      if (frames === 150 && slow > 60) { canvas.remove(); return; }
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      const zoom = 1 + heroProgress * 0.9;
      const cx = width * 0.72;
      const cy = height * 0.44;
      for (const m of motes) {
        m.y -= 0.02 * m.z * m.s * dt;
        m.x -= 0.006 * m.z * dt;
        if (m.y < -0.02) { m.y = 1.02; m.x = Math.random(); }
        if (m.x < -0.02) m.x = 1.02;
        const px = cx + (m.x * width - cx) * zoom * (0.6 + m.z * 0.4);
        const py = cy + (m.y * height - cy) * zoom * (0.6 + m.z * 0.4);
        const beam = clamp((m.x - 0.3) * 1.6, 0.15, 1);
        const alpha = (0.14 + 0.5 * (0.5 + 0.5 * Math.sin(now / 900 * m.s + m.ph))) * m.z * beam * (1 - heroProgress * 0.7);
        ctx.fillStyle = `rgba(255,176,74,${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(px, py, m.r * m.z * (1 + heroProgress), 0, TAU);
        ctx.fill();
      }
    };
    size();
    if (hasIO) new IntersectionObserver((entries) => { visible = entries.some((entry) => entry.isIntersecting); }).observe(art);
    window.addEventListener("resize", size);
    requestAnimationFrame(draw);
  }

  /* ---- Veil: a bounded, skippable iris-open on first load (never blocks no-JS) ---- */
  function boot() {
    const deepLink = window.location.hash && window.location.hash !== "#home";
    const mode = params.get("intro") === "1" ? "on" : "auto";
    if (!motionOn() || params.get("intro") === "off" || deepLink || (mode !== "on" && store.get("cm-intro", "session"))) {
      root.dataset.boot = "done";
      return Promise.resolve();
    }
    store.set("cm-intro", "1", "session");
    root.dataset.boot = "run";
    const veil = el("div", "veil", { "aria-hidden": "true" });
    veil.textContent = text($(".brand-mark")) || "";
    doc.body.append(veil);
    const fonts = doc.fonts && doc.fonts.ready ? doc.fonts.ready : Promise.resolve();
    const loaded = new Promise((resolve) => { if (doc.readyState === "complete") resolve(); else window.addEventListener("load", resolve, { once: true }); });
    return Promise.race([Promise.all([loaded, fonts, sleep(650)]), sleep(2600)]).then(() => {
      const finish = () => { veil.remove(); root.dataset.boot = "done"; };
      if (typeof veil.animate !== "function") { finish(); return undefined; }
      const run = veil.animate({ clipPath: ["circle(150% at 50% 50%)", "circle(0% at 50% 50%)"] }, { duration: 950, easing: "cubic-bezier(.65,0,.35,1)", fill: "forwards" });
      run.finished.then(finish, finish);
      return undefined;
    });
  }

  /* ---- Posters: a soft light follows the pointer over a project card (fine pointers only) ---- */
  function setupSpots() {
    if (!motionOn() || !mq("(hover: hover) and (pointer: fine)").matches) return;
    for (const card of $$("a.project")) {
      const poster = $(".poster", card);
      if (!poster || $(".spot", poster)) continue;
      const spot = el("i", "spot", { "aria-hidden": "true" });
      poster.append(spot);
      card.addEventListener("pointermove", (event) => {
        const box = poster.getBoundingClientRect();
        spot.style.setProperty("--mx", `${(((event.clientX - box.left) / box.width) * 100).toFixed(1)}%`);
        spot.style.setProperty("--my", `${(((event.clientY - box.top) / box.height) * 100).toFixed(1)}%`);
      }, { passive: true });
    }
  }

  /* ---- Optional photos (future): a broken or missing image falls back to the monogram ---- */
  function setupPortraits() {
    for (const image of $$("figure.portrait img")) {
      image.decoding = "async";
      image.addEventListener("error", () => { image.hidden = true; });
    }
  }

  /* ---- Audit (used by tests) ---- */
  function audit() {
    const issues = [];
    if (!views.length) issues.push("no routes");
    for (const view of views) if ($$("h1", view).length !== 1) issues.push(`${view.id}: expected one h1`);
    const ids = new Set();
    for (const node of $$("[id]")) { if (ids.has(node.id)) issues.push(`duplicate id ${node.id}`); ids.add(node.id); }
    for (const link of $$("a[href^='#']")) { const id = decode(link.getAttribute("href").slice(1)); if (id && !doc.getElementById(id)) issues.push(`unresolved #${id}`); }
    return issues;
  }

  /* ---- Boot ---- */
  guard("router", setupRouter);
  guard("tools", buildTools);
  guard("scrub", buildScrub);
  guard("portraits", setupPortraits);
  guard("spots", setupSpots);
  guard("reveals", setupReveals);
  guard("statements", splitStatements);
  guard("ticker", setupTicker);
  guard("measure", measureAll);
  if (activeView) observeReveals(activeView);
  let resizeTimer = 0;
  window.addEventListener("scroll", requestFrame, { passive: true });
  window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(measureAll, 120); });
  window.addEventListener("load", () => { measureAll(); });
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => measureAll()).catch(() => {});
  guard("dust", setupDust);
  const booted = guard("boot", boot) || Promise.resolve();
  booted.then(() => readyResolve(true));

  window.PortfolioTheme = Object.freeze({
    version: VERSION,
    ready: readyPromise,
    go,
    setTheme: (value) => setTheme(value),
    audit
  });
})();
