import { createPortal } from "react-dom";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import type { Portfolio } from "../template-values";
import { RouteContext } from "./routing";
import "./react.css";
import { MotionContext } from "./motion";
import { Intro } from "./Intro";

const decodeHash = () => {
  try {
    return decodeURIComponent(location.hash.slice(1).replace(/^\/+/, ""));
  } catch {
    return "";
  }
};
const clamp = (x: number, min = 0, max = 1) => Math.min(max, Math.max(min, x));

export function InteractiveTheme({
  portfolio,
  host,
  children,
}: {
  portfolio: Portfolio;
  host: RefObject<HTMLDivElement | null>;
  children: ReactNode;
}) {
  const claret = portfolio.theme_id === "claret-marquee/v1";
  const [hash, setHash] = useState(decodeHash);
  const [menu, setMenu] = useState(false);
  const [palette, setPalette] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [dark, setDark] = useState(() => {
    try {
      const stored = localStorage.getItem("oryxen-react-theme");
      if (stored) return stored === "dark";
    } catch {
      /* opaque host */
    }
    return matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [paused, setPaused] = useState(false);
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [scroll, setScroll] = useState(0);
  const [topVisible, setTopVisible] = useState(false);
  const scrollMemory = useRef(new Map<string, number>());
  const previous = useRef({ hash: "", view: "home", initial: true });
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [header, setHeader] = useState<Element | null>(null);
  const projects = portfolio.c.atlas.projects as Array<Record<string, any>>;
  const views = [
    "home",
    "about",
    ...projects.flatMap((p, i) =>
      p.problem && p.approach ? [`case-${i + 1}`] : [],
    ),
  ];
  const view = views.includes(hash)
    ? hash
    : hash.startsWith("case-")
      ? (views.find((v) => hash.startsWith(v + "-")) ?? "home")
      : "home";
  const navigate = useCallback((next: string) => {
    if (location.hash !== "#" + next) {
      const target = new URL(location.href);
      target.hash = encodeURIComponent(next);
      history.pushState(null, "", target.href);
    }
    setHash(next);
    setMenu(false);
    setPalette(false);
  }, []);
  const destinations = [
    { id: "home", label: "Home" },
    { id: "work", label: "Work" },
    { id: "about", label: "About" },
    { id: "contact", label: "Contact" },
    ...projects.flatMap((p, i) =>
      p.problem && p.approach
        ? [{ id: `case-${i + 1}`, label: p.title as string }]
        : [],
    ),
  ];
  const results = destinations.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  );
  const motionAvailable =
    !reduced &&
    (!navigator.webdriver ||
      new URLSearchParams(location.search).has(
        claret ? "motion" : "atlas-motion",
      ));
  const fullMotion = motionAvailable && !paused;
  useEffect(() => {
    setHeader(
      host.current?.querySelector(claret ? ".topbar" : ".site-header") ?? null,
    );
  }, [claret, host]);

  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(media.matches);
    const hashChange = () => {
      setHash(decodeHash());
      setMenu(false);
      setPalette(false);
    };
    const keys = (event: KeyboardEvent) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        !claret
      ) {
        event.preventDefault();
        setPalette((open) => !open);
      }
      if (event.key === "Escape") {
        setPalette(false);
        setMenu(false);
      }
    };
    media.addEventListener("change", sync);
    window.addEventListener("hashchange", hashChange);
    window.addEventListener("popstate", hashChange);
    window.addEventListener("keydown", keys);
    return () => {
      media.removeEventListener("change", sync);
      window.removeEventListener("hashchange", hashChange);
      window.removeEventListener("popstate", hashChange);
      window.removeEventListener("keydown", keys);
    };
  }, [claret]);

  useLayoutEffect(() => {
    const root = document.documentElement;
    const names = [
      "data-theme",
      "data-motion",
      "data-driver",
      "data-atlas",
      "data-boot",
      "data-header",
      "data-top",
      "data-bottom",
      "data-scrolled",
      "data-paused",
    ];
    const saved = names.map((name) => root.getAttribute(name));
    const wasJs = root.classList.contains("js");
    const wasMenu = root.classList.contains("menu-open");
    const router = document.body.getAttribute("data-router");
    root.classList.add("js");
    root.classList.toggle("menu-open", menu);
    root.dataset.theme = dark ? "dark" : "light";
    root.dataset.motion = claret
      ? fullMotion
        ? "full"
        : reduced
          ? "reduced"
          : "off"
      : fullMotion
        ? "on"
        : "off";
    root.dataset.driver = "js";
    root.dataset.atlas = "ready";
    root.dataset.boot = claret ? "done" : "";
    root.toggleAttribute("data-paused", paused);
    document.body.dataset.router = "ready";
    try {
      localStorage.setItem("oryxen-react-theme", dark ? "dark" : "light");
    } catch {
      /* opaque host */
    }
    return () => {
      names.forEach((name, i) =>
        saved[i] === null
          ? root.removeAttribute(name)
          : root.setAttribute(name, saved[i]!),
      );
      root.classList.toggle("js", wasJs);
      root.classList.toggle("menu-open", wasMenu);
      if (router === null) document.body.removeAttribute("data-router");
      else document.body.setAttribute("data-router", router);
    };
  }, [claret, dark, fullMotion, menu, paused, reduced]);

  useLayoutEffect(() => {
    const parent = host.current;
    if (!parent) return;
    const old = previous.current;
    if (old.view !== view) scrollMemory.current.set(old.view, window.scrollY);
    const target = parent.querySelector<HTMLElement>(
      `#${CSS.escape(hash || view)}`,
    );
    const article = parent.querySelector<HTMLElement>(
      `[data-view][id="${view}"]`,
    );
    const heading =
      target?.querySelector<HTMLElement>("h1,h2,h3") ??
      article?.querySelector<HTMLElement>("h1");
    document.title = article?.dataset.title ?? portfolio.c.metadata.title;
    if (hash && target)
      target.scrollIntoView({
        block: "start",
        behavior: reduced || old.initial ? "instant" : "smooth",
      });
    else
      window.scrollTo({
        top: old.initial ? 0 : (scrollMemory.current.get(view) ?? 0),
        behavior: "instant",
      });
    if (!old.initial && heading) {
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    }
    previous.current = { hash, view, initial: false };
  }, [hash, host, portfolio, reduced, view]);

  useEffect(() => {
    if (!dialog.current) return;
    if (palette) {
      dialog.current.showModal();
      input.current?.focus();
    } else if (dialog.current.open) dialog.current.close();
    return () => {
      if (dialog.current?.open) dialog.current.close();
    };
  }, [palette]);

  // Measurements and animation variables only: React owns all structure/state.
  useEffect(() => {
    const parent = host.current;
    if (!parent) return;
    let frame = 0;
    let disposed = false;
    const paint = () => {
      frame = 0;
      if (disposed) return;
      const max = Math.max(
        1,
        document.documentElement.scrollHeight - innerHeight,
      );
      const fraction = clamp(scrollY / max);
      document.documentElement.toggleAttribute("data-scrolled", scrollY > 24);
      setScroll(fraction);
      setTopVisible(scrollY > innerHeight * 1.2);
      document.documentElement.style.setProperty(
        claret ? "--sp" : "--scroll",
        String(fraction),
      );
      parent.querySelectorAll<HTMLElement>("[data-scene]").forEach((node) => {
        const rect = node.getBoundingClientRect();
        node.style.setProperty(
          "--p",
          String(clamp(-rect.top / Math.max(1, rect.height - innerHeight))),
        );
        const stage = node.querySelector<HTMLElement>(".hero-stage");
        if (stage)
          node.toggleAttribute(
            "data-flow",
            stage.scrollHeight > stage.clientHeight + 2,
          );
      });
      parent.querySelectorAll<HTMLElement>(".poster").forEach((node) => {
        const rect = node.getBoundingClientRect();
        node.style.setProperty(
          "--py",
          String(
            clamp(
              (rect.top + rect.height / 2 - innerHeight / 2) / innerHeight,
              -1,
              1,
            ),
          ),
        );
      });
      parent.querySelectorAll<HTMLElement>("[data-lit]").forEach((node) => {
        const rect = node.getBoundingClientRect();
        node.style.setProperty(
          "--lit",
          String(
            clamp(
              (innerHeight * 0.88 - rect.top) /
                (innerHeight * 0.62 + rect.height * 0.5),
            ) *
              (Number(node.dataset.lit) + 3),
          ),
        );
      });
      if (claret) {
        const tones = Array.from(
          parent.querySelectorAll<HTMLElement>(".hero,.credits,.site-footer"),
        ).filter((node) => !node.closest("[hidden]"));
        const within = (point: number) =>
          tones.some((node) => {
            const rect = node.getBoundingClientRect();
            return point >= rect.top && point <= rect.bottom;
          });
        document.documentElement.dataset.top = within(34) ? "claret" : "paper";
        document.documentElement.dataset.bottom = within(innerHeight - 20)
          ? "claret"
          : "paper";
      }
      const nav = parent.querySelector<HTMLElement>(".site-nav");
      const active = nav?.querySelector<HTMLElement>("[aria-current]");
      if (nav && active) {
        nav.style.setProperty("--nx", `${active.offsetLeft}px`);
        nav.style.setProperty("--nw", `${active.offsetWidth}px`);
        nav.style.setProperty("--no", "1");
      }
      parent.querySelectorAll<HTMLElement>(".timeline").forEach((node) => {
        const rect = node.getBoundingClientRect();
        node.style.setProperty(
          "--tl",
          String(
            clamp((innerHeight * 0.62 - rect.top) / Math.max(1, rect.height)),
          ),
        );
      });
    };
    const request = () => {
      if (!frame) frame = requestAnimationFrame(paint);
    };
    const resize = new ResizeObserver(request);
    resize.observe(parent);
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    document.fonts.ready.then(() => {
      if (!disposed) request();
    });
    request();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      resize.disconnect();
      window.removeEventListener("scroll", request);
      window.removeEventListener("resize", request);
      document.documentElement.style.removeProperty("--sp");
      document.documentElement.style.removeProperty("--scroll");
    };
  }, [claret, hash, host]);

  const tools = (
    <div className={claret ? "tools" : "header-tools"}>
      <button
        type="button"
        className={claret ? "tool tool-theme" : "tool-btn theme-toggle"}
        aria-label="Toggle color theme"
        aria-pressed={dark}
        onClick={() => setDark(!dark)}
      >
        {claret ? null : "◐"}
      </button>
      {claret ? (
        motionAvailable && (
          <button
            type="button"
            className="tool tool-pause"
            aria-label="Pause motion"
            aria-pressed={paused}
            onClick={() => setPaused(!paused)}
          />
        )
      ) : (
        <>
          <button
            type="button"
            className="tool-btn palette-btn"
            aria-label="Quick navigation"
            onClick={() => {
              setQuery("");
              setSelected(0);
              setPalette(true);
            }}
          >
            ⌘<kbd>K</kbd>
          </button>
          <button
            type="button"
            className="tool-btn menu-toggle"
            aria-label="Toggle navigation"
            aria-expanded={menu}
            aria-controls="react-site-nav"
            onClick={() => setMenu(!menu)}
          >
            ☰
          </button>
        </>
      )}
    </div>
  );
  return (
    <RouteContext.Provider value={{ hash, view, menu, navigate }}>
      <MotionContext.Provider value={{ enabled: fullMotion, claret }}>
        {children}
      </MotionContext.Provider>
      {header ? createPortal(tools, header) : tools}
      <Intro
        enabled={motionAvailable}
        claret={claret}
        name={portfolio.c.hero.name}
        monogram={portfolio.d.monogram}
      />
      <span
        id="react-route-announcer"
        className="sr-only"
        role="status"
        aria-live="polite"
      >
        {document.title}
      </span>
      {!claret && (
        <button
          type="button"
          className={`to-top${topVisible ? " is-visible" : ""}`}
          aria-label="Back to top"
          onClick={() => {
            window.scrollTo({
              top: 0,
              behavior: reduced ? "instant" : "smooth",
            });
          }}
        >
          ↑
        </button>
      )}
      {!claret && (
        <dialog
          ref={dialog}
          className="palette"
          aria-label="Quick navigation"
          onCancel={() => setPalette(false)}
          onClick={(event) => {
            if (event.target === event.currentTarget) setPalette(false);
          }}
        >
          <div className="palette-box">
            <input
              ref={input}
              className="palette-input"
              aria-label="Search pages"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setSelected(0);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  setSelected((i) =>
                    Math.max(
                      0,
                      Math.min(
                        results.length - 1,
                        i + (event.key === "ArrowDown" ? 1 : -1),
                      ),
                    ),
                  );
                }
                if (event.key === "Enter" && results[selected])
                  navigate(results[selected].id);
              }}
            />
            <ul className="palette-list" aria-label="Pages">
              {results.map((item, i) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={selected === i ? "is-selected" : ""}
                    onClick={() => navigate(item.id)}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
            <button type="button" onClick={() => setPalette(false)}>
              Close
            </button>
          </div>
        </dialog>
      )}
      {claret && motionAvailable && (
        <div className="scrub" aria-hidden="true">
          <span className="scrub-label">{view}</span>
          <div className="scrub-track">
            <span
              className="scrub-fill"
              style={{ transform: `scaleX(${scroll})` }}
            />
            <span className="scrub-head" style={{ left: `${scroll * 100}%` }} />
          </div>
          <span className="scrub-time">{Math.round(scroll * 100)}%</span>
        </div>
      )}
    </RouteContext.Provider>
  );
}
