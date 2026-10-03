/* Cobalt Atlas: content-independent navigation and motion.
   To reuse the theme, change text and links in index.html; keep data-view IDs
   and matching hash links in sync. The page remains readable without JS. */
(() => {
  "use strict";

  const views = [...document.querySelectorAll("[data-view]")];
  const viewById = new Map(views.map((view) => [view.id, view]));
  const navigation = [...document.querySelectorAll("[data-nav]")];
  const announcer = document.getElementById("route-announcer");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const aliases = new Map([["work", "home"], ["contact", "home"]]);
  let activeView = null;
  let revealObserver = null;

  if (!views.length) return;

  if ("IntersectionObserver" in window && !reducedMotion.matches) {
    revealObserver = new IntersectionObserver(
      (entries, observer) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add("is-in-view");
          observer.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -7% 0px", threshold: 0.08 }
    );
    document.querySelectorAll(".atlas-appear").forEach((element) => {
      revealObserver.observe(element);
    });
    document.body.dataset.motion = "on";
  }

  function currentRoute() {
    let fragment = window.location.hash.slice(1);
    try {
      fragment = decodeURIComponent(fragment);
    } catch {
      fragment = "";
    }
    const targetId = fragment || "home";
    const viewId = aliases.get(targetId) || targetId;
    return {
      targetId,
      view: viewById.get(viewId) || viewById.get("home") || views[0]
    };
  }

  function updateNavigation(targetId, view) {
    for (const link of navigation) {
      const name = link.dataset.nav;
      const active = name === targetId ||
        (name === "work" && (targetId === "home" || view.id.startsWith("case-")));
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
  }

  function scrollAndFocus(route, initial) {
    const target = route.targetId === "work" || route.targetId === "contact"
      ? document.getElementById(route.targetId)
      : null;
    requestAnimationFrame(() => {
      if (target) target.scrollIntoView({ block: "start", behavior: "instant" });
      else window.scrollTo({ top: 0, behavior: "instant" });
      if (!initial) {
        const heading = target?.querySelector("h2") || route.view.querySelector("h1");
        if (heading) {
          heading.setAttribute("tabindex", "-1");
          heading.focus({ preventScroll: true });
        }
      }
      if (revealObserver) {
        route.view.querySelectorAll(".atlas-appear:not(.is-in-view)").forEach((element) => {
          revealObserver.observe(element);
        });
      }
    });
  }

  function activateRoute(initial = false) {
    const route = currentRoute();
    const changed = activeView !== route.view;
    const commit = () => {
      for (const view of views) view.hidden = view !== route.view;
      document.body.dataset.router = "ready";
      activeView = route.view;
      document.title = route.view.dataset.title || document.title;
      updateNavigation(route.targetId, route.view);
      if (announcer && !initial) announcer.textContent = document.title;
    };

    if (changed && !initial && !reducedMotion.matches &&
        typeof document.startViewTransition === "function") {
      const transition = document.startViewTransition(commit);
      transition.finished.then(
        () => scrollAndFocus(route, initial),
        () => scrollAndFocus(route, initial)
      );
    } else {
      commit();
      scrollAndFocus(route, initial);
    }
  }

  window.addEventListener("hashchange", () => activateRoute());
  activateRoute(true);
  // On a direct hash load, the browser may perform native anchor scrolling
  // after the script's first frame. Restore the route's intended position.
  window.addEventListener("load", () => {
    setTimeout(() => scrollAndFocus(currentRoute(), true), 0);
  }, { once: true });
})();
