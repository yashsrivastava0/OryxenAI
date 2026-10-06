/**
 * Interactive showcase and motion controller for OryxenAI Screen 1 (/sign-in).
 * Pure vanilla ESM — zero external dependencies.
 */

export function initSignInShowcase() {
  const showcase = document.querySelector(".sign-in-showcase");
  if (!showcase) return;

  const cards = [...showcase.querySelectorAll(".showcase-card")];
  const dots = [...showcase.querySelectorAll(".showcase-dot")];
  const prevBtn = showcase.querySelector(".showcase-nav-prev");
  const nextBtn = showcase.querySelector(".showcase-nav-next");
  const pauseBtn = showcase.querySelector(".showcase-pause-btn");
  const stageNodes = [...document.querySelectorAll(".stage-rail-node")];
  const railActiveLine = document.getElementById("rail-active-segment");
  if (!cards.length) return;

  let currentIndex = 1;
  let isPaused = false;
  let isHovered = false;
  let isFocused = false;
  let isInView = true;
  let autoplayTimer = null;
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  const cardToStageIndex = [0, 0, 1, 2];

  function updateCards(index) {
    currentIndex = (index + cards.length) % cards.length;
    cards.forEach((card, i) => {
      const active = i === currentIndex;
      card.classList.toggle("card-active", active);
      card.setAttribute("aria-hidden", String(!active));
      card.toggleAttribute("inert", !active);
      card.setAttribute("tabindex", active ? "0" : "-1");
      if (active) card.setAttribute("aria-current", "true");
      else card.removeAttribute("aria-current");
    });
    dots.forEach((dot, i) => {
      const active = i === currentIndex;
      dot.classList.toggle("active", active);
      dot.setAttribute("aria-selected", String(active));
      dot.setAttribute("tabindex", active ? "0" : "-1");
      dot.setAttribute("aria-controls", cards[i].id);
    });
    const activeStageIdx = cardToStageIndex[currentIndex] ?? 0;
    stageNodes.forEach((node, i) => {
      node.classList.toggle("active", i === activeStageIdx);
      node.classList.toggle("completed", i < activeStageIdx);
    });
    if (railActiveLine && stageNodes.length > 1) {
      const percent = (activeStageIdx / (stageNodes.length - 1)) * 100;
      railActiveLine.style.width = `${percent}%`;
    }
  }

  function stopAutoplay() {
    if (autoplayTimer !== null) window.clearInterval(autoplayTimer);
    autoplayTimer = null;
  }

  function startAutoplay() {
    stopAutoplay();
    if (motionPreference.matches || isPaused || isHovered || isFocused || !isInView || document.hidden) return;
    autoplayTimer = window.setInterval(() => updateCards(currentIndex + 1), 6000);
  }

  prevBtn?.addEventListener("click", () => {
    updateCards(currentIndex - 1);
    startAutoplay();
  });
  nextBtn?.addEventListener("click", () => {
    updateCards(currentIndex + 1);
    startAutoplay();
  });
  dots.forEach((dot, i) => dot.addEventListener("click", () => {
    updateCards(i);
    startAutoplay();
  }));

  pauseBtn?.addEventListener("click", () => {
    isPaused = !isPaused;
    pauseBtn.setAttribute("aria-pressed", String(isPaused));
    const label = isPaused ? "Play slideshow" : "Pause slideshow";
    pauseBtn.setAttribute("aria-label", label);
    pauseBtn.setAttribute("title", label);
    pauseBtn.querySelector(".icon-pause")?.toggleAttribute("hidden", isPaused);
    pauseBtn.querySelector(".icon-play")?.toggleAttribute("hidden", !isPaused);
    startAutoplay();
  });

  showcase.addEventListener("mouseenter", () => { isHovered = true; stopAutoplay(); });
  showcase.addEventListener("mouseleave", () => { isHovered = false; startAutoplay(); });
  showcase.addEventListener("focusin", () => { isFocused = true; stopAutoplay(); });
  showcase.addEventListener("focusout", (event) => {
    if (!showcase.contains(event.relatedTarget)) { isFocused = false; startAutoplay(); }
  });
  showcase.addEventListener("keydown", (event) => {
    if (!dots.includes(event.target)) return;
    let index = currentIndex;
    if (event.key === "ArrowLeft") index -= 1;
    else if (event.key === "ArrowRight") index += 1;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = cards.length - 1;
    else return;
    event.preventDefault();
    updateCards(index);
    dots[currentIndex].focus();
  });

  function updateMotionPreference() {
    if (pauseBtn) pauseBtn.hidden = motionPreference.matches;
    startAutoplay();
  }
  motionPreference.addEventListener("change", updateMotionPreference);
  document.addEventListener("visibilitychange", startAutoplay);
  window.addEventListener("pagehide", stopAutoplay);
  window.addEventListener("pageshow", startAutoplay);
  if (typeof IntersectionObserver === "function") {
    const observer = new IntersectionObserver(([entry]) => {
      isInView = entry.isIntersecting;
      startAutoplay();
    });
    observer.observe(showcase);
  }

  updateCards(1);
  pauseBtn?.setAttribute("aria-pressed", "false");
  updateMotionPreference();
}

/**
 * Opens the three fictional outcome examples in one native modal dialog.
 * The preview content is already in the trusted template; this controller
 * only toggles visibility and restores focus to the card that opened it.
 */
export function initOutcomeShowcase() {
  const section = document.querySelector(".outcome-showcase");
  const dialog = document.querySelector("#outcome-preview-dialog");
  const closeButton = dialog?.querySelector("[data-outcome-close]");
  if (!section || !(dialog instanceof HTMLDialogElement) || !(closeButton instanceof HTMLElement)) return;

  const cards = [...section.querySelectorAll("[data-outcome-id]")];
  const previews = [...dialog.querySelectorAll("[data-outcome-preview]")];
  const routeLinks = [...dialog.querySelectorAll("[data-preview-route]")];
  const screens = [...dialog.querySelectorAll("[data-preview-screen]")];
  const sheet = dialog.querySelector(".outcome-dialog-sheet");
  const authLink = section.querySelector("[data-focus-auth]");
  let returnTrigger = null;

  function setRouteState(preview, route) {
    routeLinks.forEach((link) => {
      if (link.closest("[data-outcome-preview]") !== preview) return;
      if (link.getAttribute("data-preview-route") === route) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    const routeStatus = preview.querySelector("[data-preview-route-status]");
    if (routeStatus instanceof HTMLElement) {
      routeStatus.textContent = `/${route.slice(route.lastIndexOf("-") + 1)}`;
    }
  }

  previews.forEach((preview) => {
    preview.addEventListener("pointermove", (event) => {
      const bounds = preview.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      preview.style.setProperty("--pointer-x", `${((event.clientX - bounds.left) / bounds.width) * 100}%`);
      preview.style.setProperty("--pointer-y", `${((event.clientY - bounds.top) / bounds.height) * 100}%`);
    });
    preview.addEventListener("pointerleave", () => {
      preview.style.setProperty("--pointer-x", "50%");
      preview.style.setProperty("--pointer-y", "22%");
    });
  });

  if (sheet instanceof HTMLElement && typeof IntersectionObserver === "function") {
    const screenObserver = new IntersectionObserver((entries) => {
      const visibleEntry = entries
        .filter((entry) => entry.isIntersecting)
        .sort((first, second) => first.boundingClientRect.top - second.boundingClientRect.top)[0];
      if (!visibleEntry) return;
      const preview = visibleEntry.target.closest("[data-outcome-preview]");
      const route = visibleEntry.target.getAttribute("data-preview-screen");
      if (preview instanceof HTMLElement && !preview.hidden && route) setRouteState(preview, route);
      visibleEntry.target.classList.add("is-in-view");
    }, { root: sheet, threshold: 0.55 });
    screens.forEach((screen) => screenObserver.observe(screen));
  }

  function resetCardState() {
    cards.forEach((card) => card.setAttribute("aria-expanded", "false"));
  }

  function restoreFocus() {
    resetCardState();
    if (returnTrigger instanceof HTMLElement) returnTrigger.focus();
    returnTrigger = null;
  }

  function closePreview() {
    if (dialog.open) {
      resetCardState();
      dialog.close();
    } else {
      restoreFocus();
    }
  }

  cards.forEach((card) => {
    card.addEventListener("click", () => {
      const id = card.getAttribute("data-outcome-id");
      if (!id) return;
      const selected = previews.find((preview) => preview.getAttribute("data-outcome-preview") === id);
      if (!selected) return;
      previews.forEach((preview) => { preview.hidden = preview !== selected; });
      setRouteState(selected, `${id}-home`);
      returnTrigger = card;
      cards.forEach((candidate) => candidate.setAttribute("aria-expanded", String(candidate === card)));
      if (sheet instanceof HTMLElement) sheet.scrollTop = 0;
      dialog.showModal();
      window.requestAnimationFrame(() => closeButton.focus());
    });
  });

  routeLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const preview = link.closest("[data-outcome-preview]");
      const route = link.getAttribute("data-preview-route");
      if (!(preview instanceof HTMLElement) || preview.hidden || !route) return;
      const target = preview.querySelector(`[data-preview-screen="${route}"]`);
      if (!target) return;
      event.preventDefault();
      setRouteState(preview, route);
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  closeButton.addEventListener("click", closePreview);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closePreview();
  });
  dialog.addEventListener("cancel", restoreFocus);
  dialog.addEventListener("close", restoreFocus);

  authLink?.addEventListener("click", () => {
    window.requestAnimationFrame(() => document.getElementById("google-sign-in")?.focus());
  });
}

// Auto-run if loaded in browser
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initSignInShowcase();
      initOutcomeShowcase();
    });
  } else {
    initSignInShowcase();
    initOutcomeShowcase();
  }
}
