/** Public fictional demos; never owns authentication or starts generation. */
export function initOutcomeShowcase() {
  const showcase = document.querySelector(".sample-showcase");
  const dialog = document.getElementById("sample-dialog");
  if (!showcase || !(dialog instanceof HTMLDialogElement) || showcase.dataset.initialized) return;
  showcase.dataset.initialized = "true";
  const tabs = [...showcase.querySelectorAll("[data-sample]")];
  const poster = document.getElementById("sample-poster");
  const fallback = document.getElementById("sample-poster-fallback");
  const panel = document.getElementById("sample-panel");
  const title = document.getElementById("sample-browser-title");
  const openLink = document.getElementById("sample-open");
  const closeButton = document.getElementById("sample-close");
  const retry = document.getElementById("sample-retry");
  const slot = document.getElementById("sample-frame-slot");
  const placeholder = document.getElementById("sample-dialog-poster");
  const feedback = document.getElementById("sample-load-feedback");
  const status = document.getElementById("sample-load-status");
  const stage = dialog.querySelector(".sample-dialog-stage");
  const rotationButton = document.getElementById("sample-rotation");
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  let rotationTimer = null, paused = false, hovered = false, inView = true, leaving = false;
  let selected = tabs[0], frame = null, attempt = null, timers = [], returnFocus = null;
  let initialLinkPending = true;
  let closingHistory = false;
  let frameToken = null;
  let loadStarted = 0;
  const entry = id => tabs.find(tab => tab.dataset.sample === id);
  const label = tab => `${tab.dataset.name} / ${tab.dataset.profile}`;
  const asset = (tab, file) => `/showcase-samples/${tab.dataset.sample}/${file}`;
  const readSample = () => new URL(location.href).searchParams.get("sample");

  function scheduleRotation() {
    clearTimeout(rotationTimer); rotationTimer = null;
    if (paused || hovered || !inView || leaving || motion.matches || document.hidden || dialog.open || closingHistory || showcase.contains(document.activeElement)) return;
    rotationTimer = setTimeout(() => {
      select(tabs[(tabs.indexOf(selected) + 1) % tabs.length]);
      scheduleRotation();
    }, Number(showcase.dataset.rotationInterval));
  }
  function updateRotationControl() {
    rotationButton.disabled = motion.matches;
    rotationButton.setAttribute("aria-pressed", String(paused));
    rotationButton.textContent = motion.matches ? "Motion reduced" : paused ? "Play ▶" : "Pause Ⅱ";
    rotationButton.setAttribute("aria-label", motion.matches ? "Automatic switching disabled for reduced motion" : paused ? "Resume automatic sample switching" : "Pause automatic sample switching");
    scheduleRotation();
  }
  rotationButton.addEventListener("click", () => { paused = !paused; updateRotationControl(); });
  showcase.addEventListener("pointerenter", () => { hovered = true; scheduleRotation(); });
  showcase.addEventListener("pointerleave", () => { hovered = false; scheduleRotation(); });
  showcase.addEventListener("focusin", scheduleRotation);
  showcase.addEventListener("focusout", () => queueMicrotask(scheduleRotation));
  document.addEventListener("visibilitychange", scheduleRotation);
  motion.addEventListener("change", updateRotationControl);
  const observer = new IntersectionObserver(entries => { inView = entries[0].isIntersecting; scheduleRotation(); });
  observer.observe(showcase);

  function select(tab, focus = false) {
    if (!tab) return;
    selected = tab;
    tabs.forEach(candidate => {
      candidate.setAttribute("aria-selected", String(candidate === tab));
      candidate.tabIndex = candidate === tab ? 0 : -1;
    });
    panel.setAttribute("aria-labelledby", tab.id);
    title.textContent = label(tab);
    poster.alt = `${tab.dataset.name}: ${tab.dataset.profile}'s fictional portfolio, with profile and selected projects`;
    poster.hidden = false;
    fallback.hidden = true;
    poster.classList.remove("is-switching");
    poster.src = asset(tab, "poster.webp");
    openLink.href = asset(tab, "index.html");
    if (focus) tab.focus();
  }
  poster.addEventListener("load", () => poster.classList.add("is-switching"));
  poster.addEventListener("error", () => { poster.hidden = true; fallback.hidden = false; });
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => { select(tab); scheduleRotation(); });
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); select(tabs[next], true); scheduleRotation(); }
    });
    tab.querySelector("img")?.addEventListener("error", event => { event.target.hidden = true; });
  });
  function cancelLoad() {
    timers.forEach(clearTimeout); timers = []; attempt = null; frameToken = null;
    frame?.remove(); frame = null;
  }
  function load() {
    cancelLoad();
    loadStarted = performance.now();
    attempt = crypto.randomUUID();
    frameToken = attempt;
    const thisAttempt = attempt;
    placeholder.src = asset(selected, "poster.webp"); placeholder.hidden = false;
    feedback.hidden = true; retry.hidden = true; feedback.classList.remove("is-error"); status.textContent = "Opening sample…";
    stage.setAttribute("aria-busy", "true");
    frame = document.createElement("iframe");
    frame.title = `${label(selected)} — interactive fictional portfolio`;
    frame.setAttribute("sandbox", "allow-scripts allow-popups allow-popups-to-escape-sandbox");
    frame.referrerPolicy = "no-referrer";
    frame.src = `${asset(selected, "index.html")}?attempt=${encodeURIComponent(attempt)}`;
    slot.replaceChildren(frame);
    timers.push(setTimeout(() => { if (attempt === thisAttempt) feedback.hidden = false; }, Number(showcase.dataset.loadingDelay)));
    timers.push(setTimeout(() => {
      if (attempt !== thisAttempt) return;
      cancelLoad(); stage.setAttribute("aria-busy", "false");
      feedback.hidden = false; retry.hidden = false; feedback.classList.add("is-error"); status.textContent = "This sample couldn’t load.";
    }, Number(showcase.dataset.loadTimeout)));
  }
  window.addEventListener("message", event => {
    if (dialog.open && frame && event.source === frame.contentWindow && event.data?.attempt === frameToken && event.data?.type === "oryxenai-demo-close") {
      close(); return;
    }
    if (!dialog.open || !frame || event.source !== frame.contentWindow || !attempt) return;
    if (event.data?.type !== "oryxenai-demo-ready" || event.data.attempt !== attempt) return;
    const readyAttempt = attempt;
    timers.forEach(clearTimeout); timers = [];
    const remaining = Math.max(0, (motion.matches ? 0 : Number(showcase.dataset.minimumPreview)) - (performance.now() - loadStarted));
    const reveal = () => {
      if (!dialog.open || !frame || attempt !== readyAttempt) return;
      attempt = null;
      frame.classList.add("is-ready"); placeholder.hidden = true; feedback.hidden = true;
      stage.setAttribute("aria-busy", "false");
    };
    if (remaining) timers.push(setTimeout(reveal, remaining)); else reveal();
  });
  function show(tab) {
    if (!tab) return;
    select(tab);
    if (!dialog.open) returnFocus = document.activeElement instanceof HTMLElement && document.activeElement !== document.body ? document.activeElement : openLink;
    if (!dialog.open) dialog.showModal();
    document.body.classList.add("sample-modal-open");
    document.getElementById("sample-dialog-title").textContent = label(tab);
    load(); closeButton.focus(); scheduleRotation();
  }
  function dismiss() {
    cancelLoad(); if (dialog.open) dialog.close();
    document.body.classList.remove("sample-modal-open");
    returnFocus?.focus({ preventScroll: true }); returnFocus = null; scheduleRotation();
  }
  function close() {
    dismiss();
    const url = new URL(location.href);
    if (!url.searchParams.has("sample")) return;
    if (history.state?.oryxenaiSample) {
      closingHistory = true; openLink.setAttribute("aria-disabled", "true"); history.back();
    }
    else { url.searchParams.delete("sample"); history.replaceState(history.state, "", url); }
  }
  openLink.addEventListener("click", event => {
    event.preventDefault(); initialLinkPending = false;
    if (closingHistory || dialog.open) return;
    const url = new URL(location.href); url.searchParams.set("sample", selected.dataset.sample);
    history.pushState({ ...history.state, oryxenaiSample: true }, "", url); show(selected);
  });
  closeButton.addEventListener("click", close); retry.addEventListener("click", load);
  dialog.addEventListener("cancel", event => { event.preventDefault(); close(); });
  dialog.addEventListener("click", event => { if (event.target === dialog) close(); });
  dialog.addEventListener("close", () => {
    if (dialog.open) return; // A delayed close event may arrive after reopening.
    cancelLoad(); document.body.classList.remove("sample-modal-open");
  });
  window.addEventListener("popstate", () => {
    closingHistory = false; openLink.removeAttribute("aria-disabled");
    const tab = entry(readSample()); if (tab) show(tab); else dismiss(); scheduleRotation();
  });
  function resolveInitialLink() {
    if (!initialLinkPending || !document.body.dataset.authOutcome) return;
    initialLinkPending = false;
    if (["signed_out", "storage_error", "provider_unavailable"].includes(document.body.dataset.authOutcome)) {
      const tab = entry(readSample()); if (tab) show(tab);
    }
  }
  select(entry(readSample()) || selected); resolveInitialLink();
  updateRotationControl();
  window.addEventListener("oryxenai-auth-resolved", resolveInitialLink);
  window.addEventListener("pagehide", () => { leaving = true; clearTimeout(rotationTimer); cancelLoad(); });
  window.addEventListener("pageshow", event => { leaving = false; if (event.persisted && dialog.open) load(); scheduleRotation(); });
}
if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initOutcomeShowcase, { once: true });
  else initOutcomeShowcase();
}
