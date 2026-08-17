export const PREVIEW_BRIDGE_VERSION = "preview-bridge-v1";

let trustedParentOrigin = "";

function currentPath(): string {
  const configured = document
    .querySelector('meta[name="oryxenai-preview-base"]')
    ?.getAttribute("content")
    ?.trim();
  const pathname = window.location.pathname || "/";
  if (!configured || configured === "/") return pathname;
  const base = `/${configured.replace(/^\/+|\/+$/g, "")}/`;
  return pathname.startsWith(base) ? pathname.slice(base.length - 1) || "/" : pathname;
}

export function installPreviewBridge(): void {
  if (window.parent === window) return;
  window.addEventListener("message", (event) => {
    if (event.source !== window.parent) return;
    const message = event.data as { type?: string; version?: string } | null;
    if (!message || message.version !== PREVIEW_BRIDGE_VERSION || message.type !== "preview:init") return;
    trustedParentOrigin = event.origin;
    window.parent.postMessage(
      { type: "preview:ready", version: PREVIEW_BRIDGE_VERSION, path: currentPath() },
      trustedParentOrigin,
    );
  });
  window.parent.postMessage(
    { type: "preview:ready", version: PREVIEW_BRIDGE_VERSION, path: currentPath() },
    "*",
  );
}

export function notifyPreviewRoute(path: string): void {
  if (!trustedParentOrigin || window.parent === window) return;
  window.parent.postMessage(
    { type: "preview:route", version: PREVIEW_BRIDGE_VERSION, path },
    trustedParentOrigin,
  );
}
