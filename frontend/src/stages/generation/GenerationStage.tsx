import { useEffect, useRef, useState } from "preact/hooks";
import type { GenerationPreviewVM, GenerationViewModel } from "../../data/adapters/generation";
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

const VIEWPORTS = [
  { id: "mobile", label: "Mobile", width: "390px", height: "844px" },
  { id: "tablet", label: "Tablet", width: "768px", height: "1024px" },
  { id: "desktop", label: "Desktop", width: "1440px", height: "900px" },
  { id: "fit", label: "Fit", width: "100%", height: "42rem" },
] as const;

const PREVIEW_BRIDGE_VERSION = "preview-bridge-v1";

function resolveRouteUrl(preview: GenerationPreviewVM, routePath: string): string {
  const trimmed = routePath.replace(/^\/+/, "");
  try {
    return trimmed ? new URL(trimmed, preview.url).toString() : preview.url;
  } catch {
    return preview.url;
  }
}

function PreviewPanel({ preview, unverified }: { preview: GenerationPreviewVM; unverified: boolean }) {
  const routeOptions = preview.routePaths.length > 0 ? preview.routePaths : ["/"];
  const [routePath, setRoutePath] = useState(routeOptions[0] ?? "/");
  const [viewport, setViewport] = useState<(typeof VIEWPORTS)[number]["id"]>("desktop");
  const [bridgeStatus, setBridgeStatus] = useState("Loading the embedded preview...");
  const [refreshNonce, setRefreshNonce] = useState(0);
  const frameRef = useRef<HTMLIFrameElement | null>(null);

  const frameSrc = resolveRouteUrl(preview, routePath);
  const activeViewport = VIEWPORTS.find((item) => item.id === viewport) ?? VIEWPORTS[2];

  const sendPreviewInit = () => {
    const frame = frameRef.current;
    if (!frame || !frame.src || !frame.contentWindow) return;
    let origin: string;
    try {
      origin = new URL(frame.src, window.location.href).origin;
    } catch {
      return;
    }
    frame.contentWindow.postMessage({ type: "preview:init", version: PREVIEW_BRIDGE_VERSION }, origin);
  };

  useEffect(() => {
    setBridgeStatus("Loading the embedded preview...");
    const handleMessage = (event: MessageEvent) => {
      const frame = frameRef.current;
      if (!frame || event.source !== frame.contentWindow || !frame.src) return;
      let origin: string;
      try {
        origin = new URL(frame.src, window.location.href).origin;
      } catch {
        return;
      }
      if (event.origin !== origin) return;
      const data = event.data as { type?: unknown; version?: unknown } | null;
      if (data?.type === "preview:ready" && data.version === PREVIEW_BRIDGE_VERSION) {
        setBridgeStatus("Embedded preview connected.");
        sendPreviewInit();
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameSrc]);

  return (
    <section
      className="generation-preview-panel"
      aria-label={unverified ? "Unverified candidate preview" : "Verified portfolio preview"}
    >
      <div className="generation-preview-toolbar">
        <label className="generation-preview-route">
          <span className="metadata-label">Route</span>
          <select value={routePath} onChange={(event) => setRoutePath((event.target as HTMLSelectElement).value)}>
            {routeOptions.map((path) => (
              <option key={path} value={path}>{path || "/"}</option>
            ))}
          </select>
        </label>
        <div className="generation-preview-viewports" role="group" aria-label="Preview viewport">
          {VIEWPORTS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="btn-quiet"
              aria-pressed={item.id === viewport}
              onClick={() => setViewport(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="generation-preview-actions">
          <button
            type="button"
            className="btn-quiet"
            onClick={() => setRefreshNonce((value) => value + 1)}
          >
            Refresh
          </button>
          <a className="btn-quiet" href={frameSrc} target="_blank" rel="noopener noreferrer">
            Open in new tab
          </a>
        </div>
      </div>

      <p className="generation-preview-status" role="status">
        {unverified ? "Unverified candidate — not promoted. " : ""}
        {bridgeStatus}
      </p>

      <div className="generation-preview-frame-shell" data-viewport={activeViewport.id}>
        <iframe
          key={`${frameSrc}:${refreshNonce}`}
          ref={frameRef}
          className="generation-preview-frame"
          title="Generated portfolio preview"
          src={frameSrc}
          sandbox="allow-scripts allow-same-origin"
          style={{ width: activeViewport.width, height: activeViewport.height }}
          onLoad={sendPreviewInit}
        />
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
        currentMilestone={view.currentMilestone || view.statusText}
        milestones={[
          { id: "queued", label: "Queued for generation", state: "complete" },
          { id: "plan", label: "Planning the site", state: view.status === "planning" ? "current" : view.status === "queued" ? "quiet" : "complete" },
          { id: "acquire", label: "Acquiring resources", state: view.status === "acquiring" ? "current" : ["queued", "planning"].includes(view.status) ? "quiet" : "complete" },
          { id: "generate", label: "Generating the portfolio", state: view.status === "generating" ? "current" : ["queued", "planning", "acquiring"].includes(view.status) ? "quiet" : "complete" },
          { id: "verify", label: "Verifying the build", state: view.status === "verifying" || view.status === "preview_pending" ? "current" : "quiet" },
        ]}
      />
    );
  }

  if (view.state === "attention") {
    return (
      <>
        <AttentionPanel
          title={view.stale ? "This portfolio is out of date" : "Generation needs attention"}
          summary={
            view.safeError?.summary ||
            (view.stale
              ? "An approved build handoff changed since this portfolio was generated. Regenerate to bring it up to date."
              : "The generated portfolio could not pass final verification. Your last verified preview, if any, is preserved below.")
          }
          preservedWorkNote="Your approved build handoff and any previously verified preview remain unchanged."
          retryLabel={view.stale ? "Regenerate portfolio" : "Retry generation"}
          onRetry={view.stale ? onRegenerate : onRetry}
          inFlight={inFlight}
          errorDetails={view.safeError ?? undefined}
          technicalDetails={view.staleReasons.length > 0 ? view.staleReasons.join("\n") : null}
        />
        {view.candidatePreview ? (
          <PreviewPanel preview={view.candidatePreview} unverified />
        ) : null}
        {view.preview ? <PreviewPanel preview={view.preview} unverified={false} /> : null}
      </>
    );
  }

  return (
    <article className="generation-stage-view" aria-labelledby="generation-title">
      <header className="generation-header">
        <p className="eyebrow">GENERATE &amp; PREVIEW / PORTFOLIO READY</p>
        <h1 id="generation-title">Your portfolio is generated and verified.</h1>
        <p>This is the live, verified build. Regenerating replaces it only after a new run succeeds.</p>
      </header>

      {view.preview ? <PreviewPanel preview={view.preview} unverified={false} /> : null}

      {(view.warnings ?? []).length > 0 ? (
        <aside className="generation-warnings" aria-label="Generation warnings">
          <p className="metadata-label">Non-blocking notes</p>
          <ul>
            {(view.warnings ?? []).map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </aside>
      ) : null}

      {canMutate && (
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
