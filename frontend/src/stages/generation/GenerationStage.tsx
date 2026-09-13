import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import type { GenerationPreviewVM, GenerationViewModel } from "../../data/adapters/generation";
import { friendlyRouteLabel } from "../../data/adapters/generation";
import { formatActivityStatus } from "../../data/activity-copy";
import { AttentionPanel } from "../../components/AttentionPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";

export interface GenerationStageProps {
  view: GenerationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  onStart: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRegenerate: () => Promise<void>;
}

// Real device classes, not a hardware laboratory (preview.md §6) — the
// three breakpoint classes this product's generated portfolios actually
// target (see D-088: desktop 1440x900 and laptop 1280x800 are the release
// gate; tablet/mobile are the two additional classes worth eyeballing).
const DEVICES = [
  { id: "mobile", label: "Mobile", width: 390, height: 844 },
  { id: "tablet", label: "Tablet", width: 768, height: 1024 },
  { id: "desktop", label: "Desktop", width: 1440, height: 900 },
] as const;
type DeviceId = (typeof DEVICES)[number]["id"];

const PREVIEW_BRIDGE_VERSION = "preview-bridge-v1";
// Bounded readiness thresholds (preview.md §15-16): distinguish "loading"
// (expected) from "slow" (longer than normal) from "timeout" (readiness
// could not be established) — never an eternal spinner, never an
// aggressive auto-reload loop.
const SLOW_AFTER_MS = 6000;
const TIMEOUT_AFTER_MS = 20000;

function resolveRouteUrl(preview: GenerationPreviewVM, routePath: string): string {
  const trimmed = routePath.replace(/^\/+/, "");
  try {
    return trimmed ? new URL(trimmed, preview.url).toString() : preview.url;
  } catch {
    return preview.url;
  }
}

function originOf(url: string): string | null {
  try {
    return new URL(url, window.location.href).origin;
  } catch {
    return null;
  }
}

// Milestone labels are static descriptions of real backend phases, not the
// live status line. formatActivityStatus() owns the single canonical,
// specific phrasing for each real code_generator status
// (queued/planning/acquiring/generating/verifying/preview_pending); reusing
// it here keeps the milestone wording specific and consistent with the live
// activity copy instead of a second, generic hardcoded string. The trailing
// ellipsis belongs to the live pulse line, not a static list item, so it is
// trimmed. This never invents a milestone: every status passed in already
// corresponds to a milestone the backend actually reports, and an
// unrecognised status falls back to the caller-supplied generic label.
function milestoneLabel(status: string, fallback: string): string {
  const copy = formatActivityStatus("code_generator", status);
  if (!copy.working) return fallback;
  return copy.text.replace(/…+$/u, "").trim() || fallback;
}

/** Measures the available canvas width so the selected device viewport can
 * be scaled to fit (preview.md §6-7: a virtual viewport, not just "make the
 * iframe narrower"). transform: scale() does not affect layout, so the
 * wrapper's own box is sized to the POST-scale footprint manually. */
function useCanvasWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

function PreviewPanel({
  preview,
  unverified,
  focusMode,
  onToggleFocusMode,
}: {
  preview: GenerationPreviewVM;
  unverified: boolean;
  focusMode: boolean;
  onToggleFocusMode: () => void;
}) {
  const routeOptions = preview.routePaths.length > 0 ? preview.routePaths : ["/"];
  const [routePath, setRoutePath] = useState(routeOptions[0] ?? "/");
  const [deviceId, setDeviceId] = useState<DeviceId>("desktop");
  const [fitToCanvas, setFitToCanvas] = useState(true);
  const [readiness, setReadiness] = useState<"loading" | "connected" | "slow" | "timeout">("loading");
  const [refreshNonce, setRefreshNonce] = useState(0);
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const { ref: canvasRef, width: canvasWidth } = useCanvasWidth<HTMLDivElement>();

  const frameSrc = resolveRouteUrl(preview, routePath);
  const device = DEVICES.find((item) => item.id === deviceId) ?? DEVICES[2];
  // Leave a little horizontal breathing room rather than scaling to the
  // exact pixel edge of the available canvas.
  const availableWidth = Math.max(canvasWidth - 24, 1);
  const scale = fitToCanvas ? Math.min(1, availableWidth / device.width) : 1;

  const sendPreviewInit = () => {
    const frame = frameRef.current;
    if (!frame || !frame.src || !frame.contentWindow) return;
    const origin = originOf(frame.src);
    if (!origin) return;
    frame.contentWindow.postMessage({ type: "preview:init", version: PREVIEW_BRIDGE_VERSION }, origin);
  };

  useEffect(() => {
    setReadiness("loading");
    const slowTimer = window.setTimeout(() => setReadiness((r) => (r === "loading" ? "slow" : r)), SLOW_AFTER_MS);
    const timeoutTimer = window.setTimeout(
      () => setReadiness((r) => (r === "loading" || r === "slow" ? "timeout" : r)),
      TIMEOUT_AFTER_MS,
    );

    const handleMessage = (event: MessageEvent) => {
      const frame = frameRef.current;
      if (!frame || event.source !== frame.contentWindow || !frame.src) return;
      const origin = originOf(frame.src);
      if (!origin || event.origin !== origin) return;
      const data = event.data as { type?: unknown; version?: unknown; path?: unknown } | null;
      if (data?.type === "preview:ready" && data.version === PREVIEW_BRIDGE_VERSION) {
        setReadiness("connected");
      } else if (data?.type === "preview:route" && data.version === PREVIEW_BRIDGE_VERSION && typeof data.path === "string") {
        // The generated portfolio navigated internally (a real link click);
        // keep the theater's own route selector in sync so it never
        // silently disagrees with what's actually on screen.
        const normalized = data.path || "/";
        if (routeOptions.includes(normalized)) setRoutePath(normalized);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => {
      window.clearTimeout(slowTimer);
      window.clearTimeout(timeoutTimer);
      window.removeEventListener("message", handleMessage);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameSrc]);

  const readinessLabel =
    readiness === "connected"
      ? "Embedded preview connected."
      : readiness === "slow"
        ? "Still starting — this is taking longer than usual."
        : readiness === "timeout"
          ? "Preview did not respond. Try refreshing."
          : "Starting preview…";

  return (
    <section
      className={`preview-theater ${focusMode ? "is-focused" : ""}`}
      aria-label={unverified ? "Unverified candidate preview" : "Verified portfolio preview"}
    >
      <div className="preview-theater-toolbar">
        <label className="preview-theater-route">
          <span className="metadata-label">Page</span>
          <select value={routePath} onChange={(event) => setRoutePath((event.target as HTMLSelectElement).value)}>
            {routeOptions.map((path, idx) => (
              <option key={path} value={path}>
                {friendlyRouteLabel(preview.routeIds[idx] ?? "", path)}
              </option>
            ))}
          </select>
        </label>
        <div className="preview-theater-devices" role="group" aria-label="Preview viewport">
          {DEVICES.map((item) => (
            <button
              key={item.id}
              type="button"
              className="btn-quiet"
              aria-pressed={item.id === deviceId}
              onClick={() => setDeviceId(item.id)}
            >
              {item.label}
            </button>
          ))}
          <button
            type="button"
            className="btn-quiet"
            aria-pressed={fitToCanvas}
            title={fitToCanvas ? "Showing scaled to fit — click for actual size" : "Showing actual size — click to fit"}
            onClick={() => setFitToCanvas((value) => !value)}
          >
            Fit
          </button>
        </div>
        <div className="preview-theater-actions">
          <button type="button" className="btn-quiet" onClick={() => setRefreshNonce((value) => value + 1)}>
            Refresh
          </button>
          <a className="btn-quiet" href={frameSrc} target="_blank" rel="noopener noreferrer">
            Open in new tab
          </a>
          <button type="button" className="btn-quiet" onClick={onToggleFocusMode} aria-pressed={focusMode}>
            {focusMode ? "Exit focus" : "Focus"}
          </button>
        </div>
      </div>

      <p className="preview-theater-status" role="status" data-readiness={readiness}>
        {unverified ? "Unverified candidate — not promoted. " : ""}
        {readinessLabel}
        {readiness === "timeout" && (
          <button type="button" className="btn-quiet preview-theater-status-retry" onClick={() => setRefreshNonce((v) => v + 1)}>
            Retry
          </button>
        )}
      </p>

      <div className="preview-theater-canvas" ref={canvasRef}>
        <div
          className="preview-theater-device-wrapper"
          data-device={device.id}
          style={{ width: `${device.width * scale}px`, height: `${device.height * scale}px` }}
        >
          <div
            className="preview-theater-device-scale"
            style={{ width: `${device.width}px`, height: `${device.height}px`, transform: `scale(${scale})` }}
          >
            {readiness === "loading" && <div className="preview-theater-loading-veil" aria-hidden="true" />}
            <iframe
              key={`${frameSrc}:${refreshNonce}`}
              ref={frameRef}
              className="preview-theater-frame"
              title="Generated portfolio preview"
              src={frameSrc}
              sandbox="allow-scripts allow-same-origin"
              onLoad={sendPreviewInit}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export function GenerationStage({
  view,
  canMutate,
  inFlight = false,
  onStart,
  onRetry,
  onRegenerate,
}: GenerationStageProps) {
  const [focusMode, setFocusMode] = useState(false);
  const toggleFocusMode = () => setFocusMode((value) => !value);

  // Users must never feel trapped in focus mode (preview.md §21, §49:
  // "Esc from focus/fullscreen mode" is an explicit required keyboard
  // test). The toolbar's own "Exit focus" button remains the primary,
  // discoverable affordance; this is the fast keyboard escape hatch.
  useEffect(() => {
    if (!focusMode) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFocusMode(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [focusMode]);

  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 05 / Generate &amp; Preview</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Generate turns the approved build handoff into a real portfolio and lets you preview it here once it is verified.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 05 / Generate &amp; Preview</p>
        <h2>Ready to generate your portfolio</h2>
        <p className="stage-desc">
          This explicit step builds a real, verified React/Vite portfolio from your approved build handoff and gives you a live preview here.
        </p>
        <AsyncActionButton
          label="Generate portfolio"
          busyLabel="Starting generation..."
          onAction={onStart}
          disabled={!canMutate}
          inFlight={inFlight}
        />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Generate & Preview" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 05 / Generate & Preview"
        title="Generating your portfolio"
        currentMilestone={view.currentMilestone || milestoneLabel(view.status, view.statusText)}
        milestones={[
          { id: "plan", label: "Planning", state: ["queued", "planning"].includes(view.status) ? "current" : "complete" },
          { id: "acquire", label: "Acquiring resources", state: view.status === "acquiring" ? "current" : ["queued", "planning"].includes(view.status) ? "quiet" : "complete" },
          { id: "generate", label: "Building pages", state: view.status === "generating" ? "current" : ["queued", "planning", "acquiring"].includes(view.status) ? "quiet" : "complete" },
          { id: "verify", label: "Testing viewports", state: view.status === "verifying" ? "current" : ["queued", "planning", "acquiring", "generating"].includes(view.status) ? "quiet" : "complete" },
          { id: "promote", label: "Promoting preview", state: view.status === "preview_pending" ? "current" : "quiet" },
        ]}
      />
    );
  }

  if (view.state === "attention") {
    return (
      <div className={`generation-theater-boundary ${focusMode ? "is-focused" : ""}`}>
        {!focusMode && (
          <AttentionPanel
            title={view.stale ? "This portfolio is out of date" : "Generation needs attention"}
            summary={
              view.safeError?.summary ||
              (view.stale
                ? "An approved build handoff changed since this portfolio was generated. Regenerate to bring it up to date."
                : "The generated portfolio could not pass final verification. Your last verified preview, if any, is preserved below.")
            }
            preservedWorkNote="Your verified preview remains preserved."
            retryLabel={view.stale ? "Regenerate portfolio" : "Retry generation"}
            onRetry={view.stale ? onRegenerate : onRetry}
            retryAvailable={view.stale || view.retryAvailable}
            inFlight={inFlight}
            errorDetails={view.safeError ?? undefined}
            technicalDetails={view.staleReasons.length > 0 ? view.staleReasons.join("\n") : null}
          />
        )}
        {view.candidatePreview ? (
          <PreviewPanel preview={view.candidatePreview} unverified focusMode={focusMode} onToggleFocusMode={toggleFocusMode} />
        ) : null}
        {view.preview ? (
          <PreviewPanel preview={view.preview} unverified={false} focusMode={focusMode} onToggleFocusMode={toggleFocusMode} />
        ) : null}
      </div>
    );
  }

  return (
    <article className={`generation-stage-view generation-theater-boundary ${focusMode ? "is-focused" : ""}`} aria-labelledby="generation-title">
      {!focusMode && (
        <header className="generation-header">
          <p className="eyebrow">GENERATE &amp; PREVIEW / PORTFOLIO READY</p>
          <h1 id="generation-title">Your portfolio is generated and verified.</h1>
          <p>This is the live, verified build. Regenerating replaces it only after a new run succeeds.</p>
        </header>
      )}

      {view.preview ? (
        <PreviewPanel preview={view.preview} unverified={false} focusMode={focusMode} onToggleFocusMode={toggleFocusMode} />
      ) : null}

      {!focusMode && (view.warnings ?? []).length > 0 ? (
        <aside className="generation-warnings" aria-label="Generation warnings">
          <p className="metadata-label">Non-blocking notes</p>
          <ul>
            {(view.warnings ?? []).map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </aside>
      ) : null}

      {!focusMode && canMutate && (
        <div className="generation-actions">
          <button type="button" className="btn-secondary" disabled={inFlight} onClick={() => void onRegenerate()}>
            Regenerate portfolio
          </button>
          <p>Regeneration is explicit and replaces this preview only after the new verified build succeeds.</p>
        </div>
      )}
    </article>
  );
}
