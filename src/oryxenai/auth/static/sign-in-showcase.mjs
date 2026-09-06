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

  // Mapping card index to stage rail index
  // 0: Discover (0), 1: Brief (0 or 1), 2: Content (1), 3: Design (2), 4: Preview (5)
  const cardToStageIndex = [0, 1, 1, 2, 5];

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
    }, 5400);
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

  // Google CTA instant feedback
  if (googleBtn) {
    googleBtn.addEventListener("click", () => {
      const label = googleBtn.querySelector(".cta-label");
      if (label) {
        label.textContent = "Opening Google…";
      }
      googleBtn.classList.add("cta-submitting");
    });
  }

  // Initial render
  updateCards(1);
  startAutoplay();
}

// Auto-run if loaded in browser
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSignInShowcase);
  } else {
    initSignInShowcase();
  }
}
