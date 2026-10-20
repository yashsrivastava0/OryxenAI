import {
  Children,
  cloneElement,
  createContext,
  createElement,
  isValidElement,
  useContext,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type HTMLAttributes,
  type ReactElement,
  type ReactNode,
} from "react";

export const MotionContext = createContext({ enabled: false, claret: false });
const textOf = (children: ReactNode): string =>
  Children.toArray(children)
    .map((child) =>
      isValidElement<{ children?: ReactNode }>(child)
        ? textOf(child.props.children)
        : String(child ?? ""),
    )
    .join("");

function words(
  children: ReactNode,
  claret: boolean,
  index: { value: number },
): ReactNode {
  return Children.map(children, (child) => {
    if (isValidElement<{ children?: ReactNode }>(child))
      return cloneElement(
        child,
        {},
        words(child.props.children, claret, index),
      );
    if (typeof child !== "string" && typeof child !== "number") return child;
    return String(child)
      .split(/(\s+)/)
      .map((part, key) =>
        /^\s*$/.test(part) ? (
          part
        ) : claret ? (
          <span
            key={key}
            className="w"
            style={{ "--wi": index.value++ } as CSSProperties}
          >
            {part}
          </span>
        ) : (
          <span key={key} className="sw" aria-hidden="true">
            <span
              className="sw-i"
              style={{ "--w": Math.min(index.value++, 14) } as CSSProperties}
            >
              {part}
            </span>
          </span>
        ),
      );
  });
}

function duplicate(children: ReactNode, top = false): ReactNode {
  return Children.map(children, (child) =>
    isValidElement<Record<string, unknown>>(child)
      ? cloneElement(
          child,
          {
            id: undefined,
            "data-field": undefined,
            ...(top ? { "aria-hidden": true, inert: true } : {}),
          },
          duplicate(child.props.children as ReactNode),
        )
      : child,
  );
}

function replaceNumber(
  children: ReactNode,
  value: string,
  done = { value: false },
): ReactNode {
  return Children.map(children, (child) => {
    if (isValidElement<{ children?: ReactNode }>(child))
      return cloneElement(
        child,
        {},
        replaceNumber(child.props.children, value, done),
      );
    if (
      !done.value &&
      (typeof child === "string" || typeof child === "number") &&
      /\d/.test(String(child))
    ) {
      done.value = true;
      return String(child).replace(/\d[\d,]*(?:\.\d+)?/, value);
    }
    return child;
  });
}

/** React owns reveal classes, split words, counters and repeated ticker items. */
export function ThemeElement({
  as,
  children,
  className = "",
  style,
  ...props
}: HTMLAttributes<HTMLElement> & {
  as: string;
  children?: ReactNode;
  [key: `data-${string}`]: unknown;
}) {
  const motion = useContext(MotionContext);
  const element = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  const [count, setCount] = useState<string | null>(null);
  const text = textOf(children);
  const split =
    motion.enabled &&
    (motion.claret
      ? className.includes("thesis-statement")
      : ["h1", "h2"].includes(as) && text.trim().split(/\s+/).length <= 16);
  const reveal =
    motion.enabled &&
    (split ||
      className.includes("atlas-appear") ||
      (motion.claret &&
        /\b(section-title|figure|pillar|ledger-row|group|case-step|facts|lede|thesis-intro|credits-intro|work-empty)\b/.test(
          className,
        )));
  const counter = motion.enabled && as === "strong" && /\d/.test(text);
  const ticker = motion.enabled && /\b(marquee|ticker-track)\b/.test(className);
  const marker = motion.claret
    ? as === "h1" || as === "h2"
      ? "rf"
      : "rv"
    : "";
  const ref = element;
  useEffect(() => {
    const node = ref.current;
    if (!node || !(reveal || counter)) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: counter ? 0.6 : 0.08, rootMargin: "0px 0px -6% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [counter, ref, reveal]);
  useEffect(() => {
    if (!counter || !visible) {
      setCount(null);
      return;
    }
    const match = text.match(/\d[\d,]*(?:\.\d+)?/);
    if (!match) return;
    const value = Number(match[0].replaceAll(",", ""));
    if (!Number.isFinite(value)) return;
    const decimals = (match[0].split(".")[1] ?? "").length;
    let frame = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / 1400);
      setCount(
        progress === 1
          ? null
          : (value * (1 - (1 - progress) ** 4)).toLocaleString("en-US", {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
              useGrouping: match[0].includes(","),
            }),
      );
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [counter, text, visible]);
  const additions: Record<string, unknown> = {};
  let content = children;
  if (split) {
    const index = { value: 0 };
    content = words(children, motion.claret, index);
    if (motion.claret) additions["data-lit"] = index.value;
    else {
      additions["data-split"] = "";
      additions["aria-label"] = text.replace(/\s+/g, " ").trim();
    }
  }
  if (ticker) {
    content = (
      <>
        {children}
        {duplicate(children, true)}
      </>
    );
    additions["data-ready"] = "";
  }
  if (count !== null) content = replaceNumber(children, count);
  const classes = [
    className,
    reveal && marker,
    visible && (motion.claret ? "is-in" : "is-in-view"),
  ]
    .filter(Boolean)
    .join(" ");
  const length = text.length;
  if (!motion.claret && ["h1", "h2"].includes(as) && length > 32)
    additions["data-len"] = length > 90 ? "xl" : length > 55 ? "l" : "m";
  return createElement(
    as,
    {
      ...props,
      ...additions,
      ref,
      className: classes || undefined,
      style: {
        ...style,
        ...(as === "strong" ? { "--n": Math.max(2, text.length) } : {}),
      },
    },
    content,
  );
}

export function Dust() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { enabled } = useContext(MotionContext);
  useEffect(() => {
    const node = canvas.current;
    const parent = node?.parentElement;
    const context = node?.getContext("2d");
    if (!enabled || !node || !parent || !context) return;
    let width = 1,
      height = 1,
      frame = 0,
      visible = true;
    const points = Array.from({ length: 80 }, (_, i) => ({
      x: ((i * 73) % 101) / 101,
      y: ((i * 37) % 97) / 97,
      speed: 0.2 + (i % 9) / 10,
    }));
    const resize = new ResizeObserver(() => {
      const rect = parent.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      const scale = Math.min(devicePixelRatio, 1.5);
      node.width = width * scale;
      node.height = height * scale;
      context.setTransform(scale, 0, 0, scale, 0, 0);
    });
    const observer = new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting);
    });
    observer.observe(parent);
    resize.observe(parent);
    let previous = performance.now();
    const draw = (now: number) => {
      const delta = Math.min(0.05, (now - previous) / 1000);
      previous = now;
      if (visible && !document.hidden) {
        context.clearRect(0, 0, width, height);
        for (const point of points) {
          point.y = (point.y - delta * 0.02 * point.speed + 1) % 1;
          context.fillStyle = `rgba(255,176,74,${0.15 + 0.3 * point.speed})`;
          context.beginPath();
          context.arc(
            point.x * width,
            point.y * height,
            point.speed * 1.6,
            0,
            Math.PI * 2,
          );
          context.fill();
        }
      }
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      observer.disconnect();
    };
  }, [enabled]);
  return enabled ? (
    <canvas ref={canvas} className="dust" aria-hidden="true" />
  ) : null;
}
