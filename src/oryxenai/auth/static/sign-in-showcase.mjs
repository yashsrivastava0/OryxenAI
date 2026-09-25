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
  const statusPillText = showcase.querySelector(".live-status-text");
  const stageNodes = [...document.querySelectorAll(".stage-rail-node")];
  const railActiveLine = document.getElementById("rail-active-segment");
  const railTravelingHighlight = document.getElementById("rail-traveling-highlight");
  const googleBtn = document.getElementById("google-sign-in");

  if (!cards.length) return;

  let currentIndex = 1; // Default to Portfolio Brief (hero centerpiece)
  let isPaused = false;
  let isHovered = false;
  let isFocused = false;
  let autoplayTimer = null;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Map each showcase card to the active two-stage workflow rail.
  const cardToStageIndex = [0, 1, 1];

  function updateCards(index) {
    currentIndex = index;
    const total = cards.length;

    cards.forEach((card, i) => {
      card.classList.remove("card-active", "card-prev", "card-next", "card-back");
      card.removeAttribute("aria-current");

      const diff = (i - currentIndex + total) % total;

      if (diff === 0) {
        card.classList.add("card-active");
        card.setAttribute("aria-current", "true");
        card.setAttribute("tabindex", "0");
      } else if (diff === 1) {
        card.classList.add("card-next");
        card.setAttribute("tabindex", "-1");
      } else if (diff === total - 1) {
        card.classList.add("card-prev");
        card.setAttribute("tabindex", "-1");
      } else {
        card.classList.add("card-back");
        card.setAttribute("tabindex", "-1");
      }
    });

    // Update pagination dots
    dots.forEach((dot, i) => {
      const active = i === currentIndex;
      dot.classList.toggle("active", active);
      dot.setAttribute("aria-selected", active ? "true" : "false");
    });

    // Update stage rail nodes
    const activeStageIdx = cardToStageIndex[currentIndex] ?? 0;
    stageNodes.forEach((node, i) => {
      const isPastOrCurrent = i <= activeStageIdx;
      const isExact = i === activeStageIdx;
      node.classList.toggle("active", isExact);
      node.classList.toggle("completed", isPastOrCurrent && !isExact);
    });

    // Update stage rail active segment line width
    if (railActiveLine && stageNodes.length > 1) {
      const percent = (activeStageIdx / (stageNodes.length - 1)) * 100;
      railActiveLine.style.width = `calc(${percent}% + 4px)`;
    }
  }

  function nextSlide() {
    updateCards((currentIndex + 1) % cards.length);
  }

  function prevSlide() {
    updateCards((currentIndex - 1 + cards.length) % cards.length);
  }

  function startAutoplay() {
    stopAutoplay();
    if (prefersReducedMotion || isPaused || isHovered || isFocused || document.hidden) return;
    autoplayTimer = window.setInterval(() => {
      nextSlide();
    }, 3800);
  }

  function stopAutoplay() {
    if (autoplayTimer) {
      clearInterval(autoplayTimer);
      autoplayTimer = null;
    }
  }

  // Navigation button listeners
  prevBtn?.addEventListener("click", () => {
    prevSlide();
    startAutoplay();
  });

  nextBtn?.addEventListener("click", () => {
    nextSlide();
    startAutoplay();
  });

  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => {
      updateCards(i);
      startAutoplay();
    });
  });

  // Pause / Resume toggle button
  pauseBtn?.addEventListener("click", () => {
    isPaused = !isPaused;
    pauseBtn.classList.toggle("is-paused", isPaused);
    pauseBtn.setAttribute("aria-label", isPaused ? "Play slideshow" : "Pause slideshow");
    pauseBtn.setAttribute("title", isPaused ? "Play slideshow" : "Pause slideshow");
    const pauseIcon = pauseBtn.querySelector(".icon-pause");
    const playIcon = pauseBtn.querySelector(".icon-play");
    if (pauseIcon && playIcon) {
      pauseIcon.hidden = isPaused;
      playIcon.hidden = !isPaused;
    }
    if (isPaused) {
      stopAutoplay();
    } else {
      startAutoplay();
    }
  });

  // Hover & Focus auto-pause
  showcase.addEventListener("mouseenter", () => {
    isHovered = true;
    stopAutoplay();
  });

  showcase.addEventListener("mouseleave", () => {
    isHovered = false;
    startAutoplay();
  });

  showcase.addEventListener("focusin", () => {
    isFocused = true;
    stopAutoplay();
  });

  showcase.addEventListener("focusout", (e) => {
    if (!showcase.contains(e.relatedTarget)) {
      isFocused = false;
      startAutoplay();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopAutoplay();
    } else {
      resetGoogleCta();
      startAutoplay();
    }
  });

  // Keyboard navigation for dots
  showcase.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      prevSlide();
      startAutoplay();
    } else if (e.key === "ArrowRight") {
      nextSlide();
      startAutoplay();
    }
  });

  // Live status chip cross-fading text
  const statusMessages = [
    "Discovery questions forming…",
    "Structuring the brief…",
    "Ready for your review",
  ];
  let statusMessageIdx = 0;

  if (statusPillText && !prefersReducedMotion) {
    window.setInterval(() => {
      statusPillText.style.opacity = "0";
      setTimeout(() => {
        statusMessageIdx = (statusMessageIdx + 1) % statusMessages.length;
        statusPillText.textContent = statusMessages[statusMessageIdx];
        statusPillText.style.opacity = "1";
      }, 250);
    }, 3600);
  }

  // Desktop Pointer Parallax Effect (subtle tilt & shift)
  let rafId = null;
  let targetRotX = 0;
  let targetRotY = 0;
  let currentRotX = 0;
  let currentRotY = 0;

  function updateParallax() {
    currentRotX += (targetRotX - currentRotX) * 0.1;
    currentRotY += (targetRotY - currentRotY) * 0.1;

    const activeCard = showcase.querySelector(".showcase-card.card-active");
    if (activeCard) {
      activeCard.style.setProperty("--tilt-x", `${currentRotX.toFixed(2)}deg`);
      activeCard.style.setProperty("--tilt-y", `${currentRotY.toFixed(2)}deg`);
    }

    if (Math.abs(targetRotX - currentRotX) > 0.01 || Math.abs(targetRotY - currentRotY) > 0.01) {
      rafId = requestAnimationFrame(updateParallax);
    } else {
      rafId = null;
    }
  }

  if (!prefersReducedMotion && window.matchMedia("(pointer: fine)").matches) {
    showcase.addEventListener("pointermove", (e) => {
      const rect = showcase.getBoundingClientRect();
      const xNorm = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2);
      const yNorm = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2);

      // Max ~1.2 deg rotation
      targetRotY = Math.max(-1.2, Math.min(1.2, xNorm * 1.2));
      targetRotX = Math.max(-1.2, Math.min(1.2, -yNorm * 1.2));

      if (!rafId) {
        rafId = requestAnimationFrame(updateParallax);
      }
    });

    showcase.addEventListener("pointerleave", () => {
      targetRotX = 0;
      targetRotY = 0;
      if (!rafId) {
        rafId = requestAnimationFrame(updateParallax);
      }
    });
  }

  // Ensure initial CTA state is clean
  resetGoogleCta();

  // Google CTA instant feedback
  if (googleBtn) {
    googleBtn.addEventListener("click", () => {
      const label = googleBtn.querySelector(".cta-label");
      if (label) {
        label.textContent = "Opening Google…";
      }
      googleBtn.classList.add("cta-submitting");
      // Safety fallback in case navigation is canceled or delayed
      window.setTimeout(resetGoogleCta, 8000);
    });
  }

  // Restore button state and autoplay on back-navigation (BFCache pageshow) or refocus
  window.addEventListener("pageshow", () => {
    resetGoogleCta();
    startAutoplay();
  });

  window.addEventListener("focus", () => {
    resetGoogleCta();
  });

  // Initial render
  updateCards(1);
  startAutoplay();
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

export function resetGoogleCta() {
  const googleBtn = document.getElementById("google-sign-in");
  if (!googleBtn) return;
  googleBtn.disabled = false;
  googleBtn.classList.remove("cta-submitting");
  const label = googleBtn.querySelector(".cta-label");
  if (label) {
    label.textContent = "Continue with Google";
  }
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
