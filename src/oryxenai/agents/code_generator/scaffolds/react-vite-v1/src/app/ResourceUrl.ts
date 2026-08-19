function runtimeBaseUrl(): URL {
  const configured = document
    .querySelector('meta[name="oryxenai-preview-base"]')
    ?.getAttribute("content")
    ?.trim();
  if (configured) {
    const path = `/${configured.replace(/^\/+|\/+$/g, "")}/`;
    return new URL(path, window.location.origin);
  }
  const moduleScript = Array.from(
    document.querySelectorAll<HTMLScriptElement>('script[type="module"][src]'),
  )
    .map((script) => script.src)
    .find(Boolean);
  return moduleScript ? new URL("../", moduleScript) : new URL("/", window.location.origin);
}

export function publicResourceUrl(path: string): string {
  const normalized = path.replace(/^public\//, "").replace(/^\/+/, "");
  if (!normalized || normalized.includes("..") || /^[a-z][a-z0-9+.-]*:/i.test(normalized)) {
    throw new Error("Unsafe local resource path");
  }
  return new URL(normalized, runtimeBaseUrl()).toString();
}

export function publicRouteUrl(path: string): string {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("..")) {
    throw new Error("Unsafe local route path");
  }
  const normalized = path.replace(/^\/+/, "");
  const url = new URL(normalized, runtimeBaseUrl());
  return `${url.pathname}${url.search}${url.hash}`;
}
