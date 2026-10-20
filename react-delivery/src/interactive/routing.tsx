import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type AnchorHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { MotionContext } from "./motion";

export type Routes = {
  hash: string;
  view: string;
  menu: boolean;
  navigate: (hash: string) => void;
};
export const RouteContext = createContext<Routes | null>(null);

export function PortfolioNav(props: HTMLAttributes<HTMLElement>) {
  const route = useContext(RouteContext);
  return (
    <nav
      {...props}
      id={props.id ?? "react-site-nav"}
      data-open={route?.menu ? "" : undefined}
    />
  );
}

export function RouteView(
  props: HTMLAttributes<HTMLElement> & { children?: ReactNode },
) {
  const route = useContext(RouteContext);
  return (
    <article {...props} hidden={route ? props.id !== route.view : false} />
  );
}

export function CaseContents({
  index,
  outcome,
}: {
  index: number;
  outcome: boolean;
}) {
  const route = useContext(RouteContext);
  if (!route) return null;
  const labels = [
    "The opportunity",
    "The approach",
    ...(outcome ? ["Outcome"] : []),
  ];
  return (
    <nav className="case-toc" aria-label="On this page">
      {labels.map((label, section) => (
        <PortfolioLink key={label} href={`#case-${index}--s${section + 1}`}>
          {label}
        </PortfolioLink>
      ))}
    </nav>
  );
}

export function PortfolioLink({
  href,
  onClick,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const route = useContext(RouteContext);
  const motion = useContext(MotionContext);
  const element = useRef<HTMLAnchorElement>(null);
  const [visible, setVisible] = useState(false);
  const reveal =
    motion.enabled && /\batlas-appear\b/.test(props.className ?? "");
  useEffect(() => {
    if (!reveal || !element.current) return;
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
      { threshold: 0.08 },
    );
    observer.observe(element.current);
    return () => observer.disconnect();
  }, [reveal]);
  const current =
    route &&
    href?.startsWith("#") &&
    (href.slice(1) === route.hash || (!route.hash && href === "#home"));
  return (
    <a
      {...props}
      ref={element}
      className={
        [props.className, reveal && visible && "is-in-view"]
          .filter(Boolean)
          .join(" ") || undefined
      }
      href={href}
      aria-current={current ? "page" : undefined}
      onClick={(event) => {
        onClick?.(event);
        if (
          route &&
          href?.startsWith("#") &&
          !event.defaultPrevented &&
          !event.metaKey &&
          !event.ctrlKey
        ) {
          event.preventDefault();
          route.navigate(href.slice(1));
        }
      }}
    />
  );
}
