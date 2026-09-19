export const PREVIEW_BRIDGE_VERSION = "preview-bridge-v1";

export type PreviewEmbedState = "idle" | "loading" | "ready" | "degraded" | "error";

export function getPreviewOrigin(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    return parsed.origin;
  } catch {
    return null;
  }
}

export function withPreviewReloadToken(url: string, token = Date.now()): string {
  const parsed = new URL(url);
  parsed.searchParams.set("_preview_reload", String(token));
  return parsed.toString();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isPreviewReadyMessage(
  event: Pick<MessageEvent, "source" | "origin" | "data">,
  frameWindow: Window | null,
  expectedOrigin: string,
): boolean {
  if (event.source !== frameWindow || event.origin !== expectedOrigin || !isRecord(event.data)) {
    return false;
  }
  return event.data.type === "preview:ready" && event.data.version === PREVIEW_BRIDGE_VERSION;
}

export function isPreviewRouteMessage(
  event: Pick<MessageEvent, "source" | "origin" | "data">,
  frameWindow: Window | null,
  expectedOrigin: string,
): boolean {
  if (event.source !== frameWindow || event.origin !== expectedOrigin || !isRecord(event.data)) {
    return false;
  }
  return (
    (event.data.type === "preview:route" || event.data.type === "preview:navigation") &&
    event.data.version === PREVIEW_BRIDGE_VERSION
  );
}

export function previewRouteFromMessage(data: unknown): string | null {
  if (!isRecord(data)) return null;
  const value = typeof data.path === "string" ? data.path : data.route;
  return typeof value === "string" && value.trim() ? value : null;
}
