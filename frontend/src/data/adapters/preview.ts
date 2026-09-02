// Preview adapter (docs/Frontend/05 §6.6).
// Validates active preview receipts, isolates origins, derives promoted routes,
// and enforces container/route security invariants.

export type PreviewState = "absent" | "opening" | "ready" | "stale" | "unavailable";
export type PreviewViewport = "fit" | "mobile" | "tablet" | "desktop";

export interface PreviewRoute {
  id: string;
  path: string;
  label: string;
}

export interface PreviewVM {
  state: PreviewState;
  stableOrigin?: string;
  stableBaseUrl?: string;
  currentUrl?: string;
  routes: PreviewRoute[];
  selectedPath?: string;
  promotedAt?: string;
  isPreviousVerifiedResult: boolean;
  loadErrorMessage?: string;
  raw?: unknown;
}

export interface PreviewAdaptOptions {
  selectedPath?: string;
  isStale?: boolean;
  loadStatus?: "idle" | "opening" | "ready" | "failed" | "timed_out";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function formatRouteLabel(path: string): string {
  const clean = path.replace(/^\/+|\/+$/g, "");
  if (!clean) return "Home";
  return clean
    .split(/[-_/]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function normalizeRoutePath(rawPath: string): string | null {
  if (typeof rawPath !== "string") return null;
  const trimmed = rawPath.trim();
  if (!trimmed) return null;
  // Security check: reject path traversal and backslashes
  if (trimmed.includes("..") || trimmed.includes("\\") || trimmed.includes("\0")) return null;
  const parts = trimmed.split(/[?#]/);
  const pathOnly = parts[0] || "";
  if (!pathOnly) return null;
  const normalized = pathOnly.startsWith("/") ? pathOnly : `/${pathOnly}`;
  return normalized;
}

function validateAndParseReceipt(activePreview: Record<string, unknown>): {
  origin: string;
  baseUrl: string;
  routePaths: string[];
  promotedAt?: string;
} | null {
  let rawUrl = typeof activePreview.url === "string" ? activePreview.url.trim() : "";
  let rawOrigin = typeof activePreview.origin === "string" ? activePreview.origin.trim() : "";
  let rawBaseUrl =
    typeof activePreview.base_url === "string"
      ? activePreview.base_url.trim()
      : typeof activePreview.baseUrl === "string"
        ? (activePreview.baseUrl as string).trim()
        : "";
  let rawPath = typeof activePreview.path === "string" ? activePreview.path.trim() : "";

  // Reject path traversal in raw inputs
  if (
    rawUrl.includes("..") ||
    rawPath.includes("..") ||
    rawBaseUrl.includes("..") ||
    rawUrl.includes("\\") ||
    rawPath.includes("\\") ||
    rawBaseUrl.includes("\\")
  ) {
    return null;
  }

  // If url is provided, parse it
  let urlObj: URL | null = null;
  if (rawUrl) {
    try {
      urlObj = new URL(rawUrl);
    } catch {
      return null;
    }
  } else if (rawOrigin) {
    try {
      const combined = rawBaseUrl || (rawPath ? new URL(rawPath, rawOrigin).toString() : rawOrigin);
      urlObj = new URL(combined);
    } catch {
      return null;
    }
  }

  if (!urlObj) return null;

  // 1. Strict scheme check: http: or https: only. Reject javascript:, data:, etc.
  if (urlObj.protocol !== "http:" && urlObj.protocol !== "https:") {
    return null;
  }

  // 2. Strict host check: must have a valid hostname
  if (!urlObj.hostname || urlObj.hostname.includes(" ") || urlObj.hostname.includes("\0")) {
    return null;
  }

  // 3. Strict pathname check: no directory traversal
  if (urlObj.pathname.includes("..") || urlObj.pathname.includes("\\")) {
    return null;
  }

  const origin = urlObj.origin;
  const baseUrl = urlObj.toString();

  // Extract declared route paths (supports route_paths, routePaths, and routes array)
  const rawRoutePaths = Array.isArray(activePreview.route_paths)
    ? activePreview.route_paths
    : Array.isArray(activePreview.routePaths)
      ? activePreview.routePaths
      : Array.isArray(activePreview.routes)
        ? (activePreview.routes as unknown[]).map((r) =>
            isRecord(r) && typeof r.path === "string" ? r.path : "",
          )
        : [];

  const routePaths: string[] = [];
  for (const rp of rawRoutePaths) {
    const norm = normalizeRoutePath(String(rp));
    if (norm && !routePaths.includes(norm)) {
      routePaths.push(norm);
    }
  }

  // If no routes declared or root route missing, ensure root route exists
  if (!routePaths.includes("/")) {
    routePaths.unshift("/");
  }

  const promotedAt =
    typeof activePreview.promoted_at === "string"
      ? activePreview.promoted_at
      : typeof activePreview.promotedAt === "string"
        ? (activePreview.promotedAt as string)
        : undefined;

  return { origin, baseUrl, routePaths, promotedAt };
}

/**
 * Pure adapter converting Code Generator state or raw session active_preview into a validated PreviewVM.
 */
export function adaptPreview(
  rawInput: unknown,
  options?: PreviewAdaptOptions,
): PreviewVM {
  if (!isRecord(rawInput)) {
    return {
      state: "absent",
      routes: [],
      isPreviousVerifiedResult: false,
      raw: rawInput,
    };
  }

  // Extract active_preview record either from raw server payload or GenerationViewModel
  let activePreviewRecord: Record<string, unknown> | null = null;
  let isPreviousVerified = false;
  let isStale = Boolean(options?.isStale || rawInput.stale);

  if (isRecord(rawInput.active_preview)) {
    activePreviewRecord = rawInput.active_preview;
  } else if (isRecord(rawInput.activePreview)) {
    activePreviewRecord = rawInput.activePreview as Record<string, unknown>;
  }

  // Determine if this is a previous verified result retained during active work or failure
  const status = typeof rawInput.status === "string" ? rawInput.status : "";
  const stageState = typeof rawInput.state === "string" ? rawInput.state : "";
  if (
    activePreviewRecord &&
    (status === "queued" ||
      status === "planning" ||
      status === "acquiring" ||
      status === "generating" ||
      status === "verifying" ||
      status === "preview_pending" ||
      status === "needs_attention" ||
      stageState === "working" ||
      stageState === "attention")
  ) {
    isPreviousVerified = true;
  }

  if (!activePreviewRecord) {
    return {
      state: "absent",
      routes: [],
      isPreviousVerifiedResult: false,
      raw: rawInput,
    };
  }

  // Validate active preview receipt
  const receipt = validateAndParseReceipt(activePreviewRecord);
  if (!receipt) {
    return {
      state: "unavailable",
      routes: [],
      isPreviousVerifiedResult: false,
      loadErrorMessage: "Invalid preview receipt data.",
      raw: rawInput,
    };
  }

  // Map route objects preserving declared order
  const routes: PreviewRoute[] = receipt.routePaths.map((path) => ({
    id: path,
    path,
    label: formatRouteLabel(path),
  }));

  // Resolve selected path
  let selectedPath = options?.selectedPath ? normalizeRoutePath(options.selectedPath) : null;
  if (!selectedPath || !routes.some((r) => r.path === selectedPath)) {
    selectedPath = routes[0]?.path ?? "/";
  }

  // Build current URL: clean concatenation without appending private session tokens
  let currentUrl = receipt.baseUrl;
  try {
    const baseWithTrailing = receipt.baseUrl.endsWith("/") ? receipt.baseUrl : `${receipt.baseUrl}/`;
    const relPath = selectedPath.replace(/^\/+/, "");
    currentUrl = relPath ? new URL(relPath, baseWithTrailing).toString() : receipt.baseUrl;
  } catch {
    currentUrl = receipt.baseUrl;
  }

  // Determine stage state
  let state: PreviewState = "ready";
  if (isStale) {
    state = "stale";
  } else if (options?.loadStatus === "failed" || options?.loadStatus === "timed_out") {
    state = "unavailable";
  } else if (options?.loadStatus === "opening") {
    state = "opening";
  }

  return {
    state,
    stableOrigin: receipt.origin,
    stableBaseUrl: receipt.baseUrl,
    currentUrl,
    routes,
    selectedPath,
    promotedAt: receipt.promotedAt,
    isPreviousVerifiedResult: isPreviousVerified,
    loadErrorMessage:
      options?.loadStatus === "failed"
        ? "Preview frame could not load. Use Open in new tab to inspect the verified output."
        : options?.loadStatus === "timed_out"
          ? "Preview gateway connection timed out. Service may be sleeping or unreachable."
          : undefined,
    raw: rawInput,
  };
}
