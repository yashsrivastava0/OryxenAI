import {
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { publicResourceUrl, publicSectionUrl } from "../../app/ResourceUrl";
import { RESOURCE_MANIFEST } from "../../generated/resource-manifest";

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

export type LocalImageSource = {
  path: string;
  width: number;
  height: number;
  format?: string;
};

type ManifestImageAsset = {
  resource_id: string;
  sources: readonly LocalImageSource[];
};

export function LocalImage({
  resourceId,
  sources,
  alt,
  sizes = "100vw",
  loading = "lazy",
  fit = "cover",
  focalPosition = "center",
}: {
  resourceId: string;
  sources?: readonly LocalImageSource[];
  alt: string;
  sizes?: string;
  loading?: "lazy" | "eager";
  fit?: CSSProperties["objectFit"];
  focalPosition?: string;
}) {
  const manifestAssets = RESOURCE_MANIFEST.image_assets as readonly ManifestImageAsset[];
  const manifestAsset = manifestAssets.find((asset) => asset.resource_id === resourceId);
  const ordered = [...(sources ?? manifestAsset?.sources ?? [])]
    .filter((source) => source.path && source.width > 0 && source.height > 0)
    .sort((left, right) => left.width - right.width);
  const largest = ordered.at(-1);
  if (!largest) return null;
  const grouped = new Map<string, LocalImageSource[]>();
  for (const source of ordered) {
    const format = (source.format || "").toLowerCase();
    const entries = grouped.get(format) || [];
    entries.push(source);
    grouped.set(format, entries);
  }
  const fallbackFormat = grouped.has("jpeg")
    ? "jpeg"
    : grouped.has("jpg")
      ? "jpg"
      : grouped.keys().next().value || "";
  const fallbackSources = grouped.get(fallbackFormat) || [largest];
  const srcSet = (items: readonly LocalImageSource[]) =>
    items
      .map((source) => `${publicResourceUrl(source.path)} ${source.width}w`)
      .join(", ");
  return (
    <picture style={{ display: "block", inlineSize: "100%", blockSize: "100%" }}>
      {[...grouped.entries()]
        .filter(([format]) => format && format !== fallbackFormat)
        .map(([format, items]) => (
          <source
            key={format}
            type={`image/${format === "jpg" ? "jpeg" : format}`}
            srcSet={srcSet(items)}
            sizes={sizes}
          />
        ))}
      <img
        data-resource-id={resourceId}
        src={publicResourceUrl((fallbackSources.at(-1) || largest).path)}
        srcSet={srcSet(fallbackSources)}
        sizes={sizes}
        width={largest.width}
        height={largest.height}
        loading={loading}
        decoding="async"
        alt={alt}
        style={{
          display: "block",
          inlineSize: "100%",
          blockSize: "100%",
          objectFit: fit,
          objectPosition: focalPosition,
        }}
      />
    </picture>
  );
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
