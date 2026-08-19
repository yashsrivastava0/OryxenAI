import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { publicSectionUrl } from "../../app/ResourceUrl";

export type RouteShellProps = {
  routeId: string;
  routePath: string;
  children: ReactNode;
  navigation?: ReactNode;
  footer?: ReactNode;
};

export function RouteShell({
  routeId,
  routePath,
  children,
  navigation,
  footer,
}: RouteShellProps) {
  return (
    <div data-route-shell={routeId}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {navigation}
      <main id="main-content" data-route-id={routeId} data-route-path={routePath}>
        {children}
      </main>
      {footer}
    </div>
  );
}

export function SectionAnchor({
  routePath,
  sectionId,
  children,
}: {
  routePath: string;
  sectionId: string;
  children: ReactNode;
}) {
  return <a href={publicSectionUrl(routePath, sectionId)}>{children}</a>;
}

export function useDisclosure(initialOpen = false) {
  const [open, setOpen] = useState(initialOpen);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const close = () => {
    setOpen(false);
    requestAnimationFrame(() => triggerRef.current?.focus());
  };
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);
  return {
    open,
    panelId,
    triggerRef,
    toggle: () => setOpen((value) => !value),
    close,
  };
}

export function Disclosure({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const disclosure = useDisclosure();
  return (
    <div data-disclosure>
      <button
        ref={disclosure.triggerRef}
        type="button"
        aria-expanded={disclosure.open}
        aria-controls={disclosure.panelId}
        onClick={disclosure.toggle}
      >
        {label}
      </button>
      <div id={disclosure.panelId} hidden={!disclosure.open}>
        {children}
      </div>
    </div>
  );
}
