// PreviewSurface (docs/Frontend/05 §8.10).
// Implements the verified preview iframe surface with:
// - Route / viewport / refresh / new-tab toolbar
// - Container-sizing hardening (zero-CLS reserved box + visual scale letterbox)
// - Exact-origin postMessage handshake & frame lifecycle controller
// - Cold-start message adaptation and preview-specific failure recovery
// - Previous verified preview preservation

import { useEffect, useMemo, useRef, useState, useCallback } from "preact/hooks";
import type { PreviewVM, PreviewViewport } from "../../data/adapters/preview";
import type { JourneyStageId } from "../../app/url-state";

export const PREVIEW_BRIDGE_VERSION = "preview-bridge-v1";

interface ProfileDimensions {
  width: number;
  height: number;
}

export const VIEWPORT_PROFILES: Record<"mobile" | "tablet" | "desktop", ProfileDimensions> = {
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1440, height: 900 },
};

export interface PreviewSurfaceProps {
  view: PreviewVM | null;
  readOnly?: boolean;
  viewport?: PreviewViewport;
  selectedRoute?: string;
  scale?: number;
  loadStatus?: "opening" | "ready" | "failed" | "timed_out";
  coldStartAcknowledged?: boolean;
  onViewportChange?: (viewport: PreviewViewport) => void;
  onRouteChange?: (routePath: string) => void;
  onRefresh?: () => void;
  onNavigateStage?: (stage: JourneyStageId) => void;
  iframeRef?: any;
  containerRef?: any;
  onIframeLoad?: () => void;
  onIframeError?: () => void;
}

export interface UsePreviewControllerOptions {
  initialViewport?: PreviewViewport;
  initialRoute?: string;
  onRouteSelected?: (routePath: string) => void;
  onViewportChanged?: (viewport: PreviewViewport) => void;
}

/**
 * Hook managing the browser runtime lifecycle, exact-origin postMessage handshake,
 * ResizeObserver box-sizing, and timeout timers for the preview frame.
 */
export function usePreviewController(
  view: PreviewVM | null,
  options?: UsePreviewControllerOptions,
) {
  const [viewport, setViewport] = useState<PreviewViewport>(() => {
    if (options?.initialViewport) return options.initialViewport;
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      return "fit";
    }
    return "desktop";
  });

  const [selectedRoute, setSelectedRoute] = useState<string>(() => {
    if (options?.initialRoute && view?.routes.some((r) => r.path === options.initialRoute)) {
      return options.initialRoute;
    }
    return view?.selectedPath || view?.routes[0]?.path || "/";
  });

  const [loadStatus, setLoadStatus] = useState<"opening" | "ready" | "failed" | "timed_out">("opening");
  const [coldStartAcknowledged, setColdStartAcknowledged] = useState(false);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [containerWidth, setContainerWidth] = useState<number>(1080);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const openingTimerRef = useRef<number | null>(null);
  const timeoutTimerRef = useRef<number | null>(null);

  // Sync selectedRoute if view routes change
  useEffect(() => {
    if (view?.routes.length) {
      if (!view.routes.some((r) => r.path === selectedRoute)) {
        const fallback = view.selectedPath || view.routes[0]?.path || "/";
        setSelectedRoute(fallback);
      }
    }
  }, [view?.routes, view?.selectedPath, selectedRoute]);

  // Measure container width for container-sizing hardening
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const w = el.clientWidth;
      if (w > 0) setContainerWidth(w);
    };

    measure();

    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const w = entry.contentRect.width;
          if (w > 0) setContainerWidth(w);
        }
      });
      observer.observe(el);
      return () => observer.disconnect();
    } else {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }
  }, []);

  const clearTimers = useCallback(() => {
    if (openingTimerRef.current !== null) {
      window.clearTimeout(openingTimerRef.current);
      openingTimerRef.current = null;
    }
    if (timeoutTimerRef.current !== null) {
      window.clearTimeout(timeoutTimerRef.current);
      timeoutTimerRef.current = null;
    }
  }, []);

  // PostMessage protocol: send preview:init to iframe on load
  const sendPreviewInit = useCallback(() => {
    if (!iframeRef.current?.contentWindow || !view?.stableOrigin) return;
    try {
      iframeRef.current.contentWindow.postMessage(
        { type: "preview:init", version: PREVIEW_BRIDGE_VERSION },
        view.stableOrigin,
      );
    } catch {
      // Cross-origin safety
    }
  }, [view?.stableOrigin]);

  const onIframeLoad = () => {
    sendPreviewInit();
    timeoutTimerRef.current = window.setTimeout(() => {
      setLoadStatus((prev) => (prev === "opening" ? "timed_out" : prev));
    }, 8000);
  };

  const onIframeError = () => {
    clearTimers();
    setLoadStatus("failed");
  };

  // Exact-origin postMessage listener
  useEffect(() => {
    const targetOrigin = view?.stableOrigin;
    if (!targetOrigin) return;

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== targetOrigin) return;
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data = event.data as { type?: string; version?: string; path?: string } | null;
      if (!data || data.version !== PREVIEW_BRIDGE_VERSION) return;

      if (data.type === "preview:ready") {
        clearTimers();
        setLoadStatus("ready");
        if (data.path && view?.routes.some((r) => r.path === data.path)) {
          setSelectedRoute(data.path);
          options?.onRouteSelected?.(data.path);
        }
      } else if (data.type === "preview:route" && typeof data.path === "string") {
        if (view?.routes.some((r) => r.path === data.path)) {
          setSelectedRoute(data.path);
          options?.onRouteSelected?.(data.path);
        }
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [view?.stableOrigin, view?.routes, clearTimers, options]);

  // Reset loading cycle when route or refreshNonce changes
  useEffect(() => {
    if (!view?.stableOrigin || view.state === "absent" || view.state === "unavailable") return;

    clearTimers();
    setLoadStatus("opening");
    setColdStartAcknowledged(false);

    openingTimerRef.current = window.setTimeout(() => {
      setColdStartAcknowledged(true);
    }, 2000);

    return () => clearTimers();
  }, [selectedRoute, refreshNonce, view?.stableOrigin, view?.state, clearTimers]);

  // Calculate scale factor
  const scale = useMemo(() => {
    if (viewport === "fit") return 1;
    const profile = VIEWPORT_PROFILES[viewport];
    const availableW = containerWidth > 0 ? containerWidth : profile.width;
    return availableW < profile.width ? availableW / profile.width : 1;
  }, [viewport, containerWidth]);

  const onViewportChange = (v: PreviewViewport) => {
    setViewport(v);
    options?.onViewportChanged?.(v);
  };

  const onRouteChange = (path: string) => {
    setSelectedRoute(path);
    options?.onRouteSelected?.(path);
  };

  const onRefresh = () => {
    setRefreshNonce((n) => n + 1);
  };

  return {
    viewport,
    selectedRoute,
    scale,
    loadStatus,
    coldStartAcknowledged,
    onViewportChange,
    onRouteChange,
    onRefresh,
    onIframeLoad,
    onIframeError,
    containerRef,
    iframeRef,
  };
}

function computeFrameUrl(stableBaseUrl: string | undefined, activeRoute: string): string {
  if (!stableBaseUrl) return "";
  try {
    const baseWithSlash = stableBaseUrl.endsWith("/") ? stableBaseUrl : `${stableBaseUrl}/`;
    const rel = activeRoute.replace(/^\/+/, "");
    return rel ? new URL(rel, baseWithSlash).toString() : stableBaseUrl;
  } catch {
    return stableBaseUrl;
  }
}

function computeLayout(viewport: PreviewViewport, scale: number) {
  if (viewport === "fit") {
    return {
      wrapperStyle: {
        width: "100%",
        height: "680px",
        overflow: "hidden",
        position: "relative" as const,
      },
      iframeStyle: {
        width: "100%",
        height: "100%",
        border: "none",
        transform: "none",
      },
    };
  }

  const profile = VIEWPORT_PROFILES[viewport];
  const wrapperW = Math.round(profile.width * scale);
  const wrapperH = Math.round(profile.height * scale);

  return {
    wrapperStyle: {
      width: `${wrapperW}px`,
      height: `${wrapperH}px`,
      overflow: "hidden",
      position: "relative" as const,
      margin: "0 auto",
    },
    iframeStyle: {
      width: `${profile.width}px`,
      height: `${profile.height}px`,
      border: "none",
      transform: `scale(${scale})`,
      transformOrigin: "top left",
      position: "absolute" as const,
      top: 0,
      left: 0,
    },
  };
}

/**
 * Pure presentational PreviewSurface component (docs/Frontend/05 §8.10).
 * Renders toolbar, layout, iframe, overlay, and recovery cards given current view state.
 */
export function PreviewSurface({
  view,
  readOnly = false,
  viewport = "desktop",
  selectedRoute,
  scale = 1,
  loadStatus = "opening",
  coldStartAcknowledged = false,
  onViewportChange,
  onRouteChange,
  onRefresh,
  onNavigateStage,
  iframeRef,
  containerRef,
  onIframeLoad,
  onIframeError,
}: PreviewSurfaceProps) {
  // Current route fallback
  const activeRoute = selectedRoute || view?.selectedPath || view?.routes[0]?.path || "/";
  const currentFrameUrl = computeFrameUrl(view?.stableBaseUrl, activeRoute);
  const layout = computeLayout(viewport, scale);

  // 1. Absent State
  if (!view || view.state === "absent") {
    return (
      <div className="preview-surface preview-surface-absent" ref={containerRef}>
        <div className="preview-empty-card" role="region" aria-label="Preview not available">
          <div className="preview-empty-icon" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <h2 className="preview-empty-title">Preview will appear after verification</h2>
          <p className="preview-empty-desc">
            Your verified portfolio preview will be presented here once generation and Playwright DOM checks succeed.
          </p>
          {onNavigateStage && !readOnly ? (
            <button
              type="button"
              className="action-btn primary"
              onClick={() => onNavigateStage("discover")}
            >
              Start portfolio discovery
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  // 2. Invalid / Unavailable State
  if (view.state === "unavailable" && !view.stableOrigin) {
    return (
      <div className="preview-surface preview-surface-unavailable" ref={containerRef}>
        <div className="preview-empty-card preview-error-card" role="alert">
          <h2 className="preview-empty-title">Preview receipt unavailable</h2>
          <p className="preview-empty-desc">
            {view.loadErrorMessage || "The preview receipt could not be verified safely. Please retry generation."}
          </p>
          {onNavigateStage && !readOnly ? (
            <button
              type="button"
              className="action-btn secondary"
              onClick={() => onNavigateStage("generate")}
            >
              Back to generation
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  const showOverlay = loadStatus === "opening";
  const showFailureCard = loadStatus === "failed" || loadStatus === "timed_out";

  return (
    <div className="preview-surface" ref={containerRef}>
      {/* ── Preview Toolbar (§8.10) ─────────────────────────────────────────── */}
      <div className="preview-toolbar" role="toolbar" aria-label="Preview controls">
        {/* Route Selector */}
        <div className="preview-toolbar-group">
          <label htmlFor="preview-route-select" className="visually-hidden">
            Select route
          </label>
          <select
            id="preview-route-select"
            className="preview-route-select"
            value={activeRoute}
            onChange={(e) => onRouteChange?.((e.target as HTMLSelectElement).value)}
            aria-label="Preview route selector"
          >
            {view.routes.map((route) => (
              <option key={route.id} value={route.path}>
                {route.label} ({route.path})
              </option>
            ))}
          </select>
        </div>

        {/* Viewport Buttons */}
        <div className="preview-viewport-controls" role="group" aria-label="Preview viewport selection">
          {(["fit", "mobile", "tablet", "desktop"] as const).map((v) => (
            <button
              key={v}
              type="button"
              className="preview-viewport-btn"
              aria-pressed={viewport === v}
              onClick={() => onViewportChange?.(v)}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
          {scale < 0.999 && viewport !== "fit" ? (
            <span className="preview-scale-pill" title={`Visual scale: ${Math.round(scale * 100)}%`}>
              {Math.round(scale * 100)}%
            </span>
          ) : null}
        </div>

        {/* Actions */}
        <div className="preview-toolbar-actions">
          {view.isPreviousVerifiedResult ? (
            <span className="preview-retained-badge" title="Retained from previous verified generation">
              Previous verified Preview
            </span>
          ) : null}

          <button
            type="button"
            className="preview-refresh-btn"
            onClick={onRefresh}
            aria-label="Refresh preview frame"
            title="Reload preview frame"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span>Refresh</span>
          </button>

          <a
            href={currentFrameUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="preview-open-link"
            title="Open verified preview in a new browser tab"
          >
            <span>Open in new tab</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        </div>
      </div>

      {/* ── Frame Area with Box Reservation & Letterboxing ─────────────────── */}
      <div className="preview-frame-boundary">
        <div className="preview-frame-wrapper" style={layout.wrapperStyle}>
          {/* Loading Overlay inside frame boundary */}
          {showOverlay ? (
            <div className="preview-frame-overlay" role="status" aria-live="polite">
              <div className="preview-spinner" aria-hidden="true" />
              <p className="preview-overlay-text">
                {coldStartAcknowledged
                  ? "Opening verified Preview. Connecting to the preview gateway. This can take a little longer after inactivity."
                  : "Opening verified Preview..."}
              </p>
            </div>
          ) : null}

          {/* Failure / Timeout Recovery Overlay */}
          {showFailureCard ? (
            <div className="preview-frame-recovery" role="alert">
              <div className="preview-timeout-card">
                <h3>
                  {loadStatus === "timed_out"
                    ? "Preview gateway connection timed out"
                    : "Preview frame could not load"}
                </h3>
                <p>
                  {loadStatus === "timed_out"
                    ? "The preview gateway did not respond within 8 seconds. If the service was sleeping, it may take an extra moment to start."
                    : "The embedded frame was unable to display the verified site."}
                </p>
                <div className="preview-recovery-actions">
                  <button type="button" className="action-btn primary" onClick={onRefresh}>
                    Refresh frame
                  </button>
                  <a
                    href={currentFrameUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="action-btn secondary"
                  >
                    Open in new tab
                  </a>
                </div>
              </div>
            </div>
          ) : null}

          {/* Verified Preview IFrame with Strict Sandbox */}
          <iframe
            ref={iframeRef}
            src={currentFrameUrl}
            title="Promoted verified portfolio preview"
            sandbox="allow-scripts allow-same-origin"
            style={layout.iframeStyle}
            onLoad={onIframeLoad}
            onError={onIframeError}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Self-contained ConnectedPreviewSurface component that pairs usePreviewController
 * with PreviewSurface for full browser rendering.
 */
export function ConnectedPreviewSurface({
  view,
  readOnly = false,
  onNavigateStage,
  initialViewport,
  initialRoute,
  onRouteSelected,
  onViewportChanged,
}: {
  view: PreviewVM | null;
  readOnly?: boolean;
  onNavigateStage?: (stage: JourneyStageId) => void;
  initialViewport?: PreviewViewport;
  initialRoute?: string;
  onRouteSelected?: (routePath: string) => void;
  onViewportChanged?: (viewport: PreviewViewport) => void;
}) {
  const controller = usePreviewController(view, {
    initialViewport,
    initialRoute,
    onRouteSelected,
    onViewportChanged,
  });

  return (
    <PreviewSurface
      view={view}
      readOnly={readOnly}
      onNavigateStage={onNavigateStage}
      {...controller}
    />
  );
}
