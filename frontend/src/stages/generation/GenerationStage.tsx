import { useEffect, useRef, useState } from "preact/hooks";
import type { GenerationViewModel } from "../../data/adapters/generation";
import { copyJson } from "../../data/clipboard";
import {
  getPreviewOrigin,
  isPreviewReadyMessage,
  isPreviewRouteMessage,
  PREVIEW_BRIDGE_VERSION,
  previewRouteFromMessage,
  type PreviewEmbedState,
  withPreviewReloadToken,
} from "../../data/preview-bridge";

export interface GenerationStageProps {
  view: GenerationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  sessionId?: string | null;
  onStart: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onRefresh?: () => Promise<void>;
}

interface MilestoneDef {
  id: string;
  label: string;
  stageKey: string;
  defaultDesc: string;
  workingDesc: string;
  completeDesc: string;
  stoppedDesc: string;
}

/** Converts a millisecond duration into a small, human-readable "remaining"
 * string for the active milestone (e.g. "About 6 minutes remaining"). Pure
 * formatting only — the value itself always comes from
 * `view.estimatedRemainingMs`, which traces back to backend-computed,
 * non-fabricated sources (see adaptStageEstimate in data/adapters/generation.ts). */
function formatEstimatedTimeRemaining(ms: number): string {
  if (ms < 60_000) return "Less than a minute remaining";
  const totalMinutes = Math.round(ms / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours < 1) return `About ${totalMinutes} minute${totalMinutes === 1 ? "" : "s"} remaining`;
  if (minutes === 0) return `About ${hours} hour${hours === 1 ? "" : "s"} remaining`;
  return `About ${hours} hour${hours === 1 ? "" : "s"} ${minutes} minute${minutes === 1 ? "" : "s"} remaining`;
}

const MILESTONES: MilestoneDef[] = [
  {
    id: "plan",
    label: "Plan",
    stageKey: "plan",
    defaultDesc: "Turn your idea into a clear plan.",
    workingDesc: "Analyzing your request and planning the structure...",
    completeDesc: "Analyzed your request and planned the structure.",
    stoppedDesc: "Planning stopped.",
  },
  {
    id: "acquire",
    label: "Acquire",
    stageKey: "acquire",
    defaultDesc: "Gather assets, set up structure.",
    workingDesc: "Collecting assets and setting up dependencies...",
    completeDesc: "Collected assets, set up dependencies.",
    stoppedDesc: "Acquisition stopped.",
  },
  {
    id: "build",
    label: "Build",
    stageKey: "generate",
    defaultDesc: "Generate pages, components, and content.",
    workingDesc: "Building pages...",
    completeDesc: "Generated site files and components.",
    stoppedDesc: "Build stopped.",
  },
  {
    id: "verify",
    label: "Verify",
    stageKey: "verify",
    defaultDesc: "Run checks and refine.",
    workingDesc: "Running checks and validating the site...",
    completeDesc: "Validated site quality and viewports.",
    stoppedDesc: "Verification stopped.",
  },
  {
    id: "preview",
    label: "Preview",
    stageKey: "preview",
    defaultDesc: "Review and prepare for launch.",
    workingDesc: "Preparing the live preview...",
    completeDesc: "Portfolio ready to review.",
    stoppedDesc: "Waiting for verification to complete.",
  },
];

export function GenerationStage({
  view,
  canMutate,
  inFlight = false,
  sessionId,
  onStart,
  onRetry,
  onRegenerate,
  onRefresh,
}: GenerationStageProps) {
  const [showTraceabilityDrawer, setShowTraceabilityDrawer] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [zoomFit, setZoomFit] = useState(true);
  const [previewEmbedState, setPreviewEmbedState] = useState<PreviewEmbedState>("idle");
  const [previewEmbedMessage, setPreviewEmbedMessage] = useState("");
  const [previewRoute, setPreviewRoute] = useState<string | null>(null);
  const previewFrameRef = useRef<HTMLIFrameElement>(null);
  const previewUrl = view?.preview?.url || view?.candidatePreview?.url || "";
  const [previewSrc, setPreviewSrc] = useState(previewUrl);

  useEffect(() => {
    setPreviewSrc(previewUrl);
    setPreviewEmbedState(previewUrl ? "loading" : "idle");
    setPreviewEmbedMessage("");
    setPreviewRoute(null);
    if (!previewUrl) return;

    const expectedOrigin = getPreviewOrigin(previewUrl);
    if (!expectedOrigin) {
      setPreviewEmbedState("error");
      setPreviewEmbedMessage("The preview URL is invalid.");
      return;
    }

    const onMessage = (event: MessageEvent) => {
      const frame = previewFrameRef.current;
      if (isPreviewReadyMessage(event, frame?.contentWindow ?? null, expectedOrigin)) {
        setPreviewEmbedState("ready");
        setPreviewEmbedMessage("");
        return;
      }
      if (isPreviewRouteMessage(event, frame?.contentWindow ?? null, expectedOrigin)) {
        setPreviewRoute(previewRouteFromMessage(event.data));
      }
    };

    window.addEventListener("message", onMessage);
    const timer = window.setTimeout(() => {
      setPreviewEmbedState((current) => {
        if (current === "ready" || current === "degraded") return current;
        setPreviewEmbedMessage("The preview did not finish loading. Open it in a new tab to inspect the diagnostic response.");
        return "error";
      });
    }, 8000);

    return () => {
      window.removeEventListener("message", onMessage);
      window.clearTimeout(timer);
    };
  }, [previewUrl]);

  const sendPreviewInit = () => {
    if (!previewUrl) return;
    const origin = getPreviewOrigin(previewUrl);
    if (!origin) {
      setPreviewEmbedState("error");
      setPreviewEmbedMessage("The preview URL is invalid.");
      return;
    }
    setPreviewEmbedState((current) => current === "ready" ? current : "degraded");
    previewFrameRef.current?.contentWindow?.postMessage(
      { type: "preview:init", version: PREVIEW_BRIDGE_VERSION },
      origin,
    );
  };

  const reloadPreview = () => {
    if (!previewUrl) return;
    try {
      setPreviewEmbedState("loading");
      setPreviewEmbedMessage("");
      setPreviewSrc(withPreviewReloadToken(previewUrl));
    } catch {
      setPreviewEmbedState("error");
      setPreviewEmbedMessage("The preview URL is invalid.");
    }
  };

  // 1. Locked State
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel" role="region" aria-label="Code Generator locked">
        <p className="eyebrow">Stage 05 / Generate & Preview</p>
        <h2 className="locked-title">Stage Locked</h2>
        <p className="locked-desc">
          Generation requires an approved Build Preparation handoff before code synthesis can begin.
        </p>
      </div>
    );
  }

  // Determine stage active index and failed index
  const stageKeys = ["plan", "acquire", "generate", "verify", "preview"];
  const isAttention = view.state === "attention";
  const isWorking = view.state === "working";
  const isAvailable = view.state === "available";
  const isComplete = view.state === "complete";
  // Any non-stale attention state is recoverable through the same-run retry
  // action. The server still validates ownership, freshness, and entitlement
  // before it queues the next durable stage attempt.
  const retryEnabled = isAttention && !view.stale;

  const coordStage = view.coordinatorStage || (
    view.status === "planning" ? "plan" :
    view.status === "acquiring" ? "acquire" :
    view.status === "generating" ? "generate" :
    view.status === "verifying" ? "verify" :
    view.status === "preview_pending" || view.status === "ready" ? "preview" :
    isAttention ? (
      view.activeJobKind?.includes("verify") ? "verify" :
      view.activeJobKind?.includes("generate") ? "generate" :
      view.activeJobKind?.includes("acquire") ? "acquire" :
      view.activeJobKind?.includes("plan") ? "plan" :
      (typeof view.latestError?.message === "string" && view.latestError.message.toLowerCase().includes("verif") ? "verify" : "verify")
    ) : ""
  );

  let activeIndex = -1;
  if (coordStage) {
    const idx = stageKeys.indexOf(coordStage);
    if (idx >= 0) activeIndex = idx;
  }

  // In attention state, the failed stage is activeIndex (defaults to verify if unknown)
  const failedIndex = isAttention ? (activeIndex >= 0 ? activeIndex : 3) : -1;

  // Active preview URL
  const hasVerifiedPreview = Boolean(view.preview?.url);

  // Headline and subtitle for left panel
  const projectTitle = isAvailable
    ? "Ready to build your portfolio."
    : isWorking
      ? "Building your site"
      : view.projectTitle || "Personal Portfolio";

  const projectSubtitle = isAvailable
    ? "Your approved briefs are ready. Start generation when you are ready to create a reviewable preview."
    : isWorking
      ? "Turning your idea into a working, production-ready site."
      : view.projectSummary || "A clean, modern portfolio site for a product designer with case studies and a blog.";

  const eyebrow = isAvailable
    ? "BUILD WORKSPACE"
    : isWorking
      ? "Code Generator"
      : "Project";

  const issues = (view.issues && view.issues.length > 0) ? view.issues : (view.warnings || []);
  const failedStageName = failedIndex >= 0 ? MILESTONES[failedIndex]?.label : "Verification";

  const errorCode =
    (typeof view.latestError?.code === "string" && view.latestError.code) ||
    (typeof view.job?.error?.code === "string" && view.job.error.code) ||
    "GENERATION_ATTENTION";

  // Copy diagnostic report handler for traceability drawer
  const handleCopyReport = async () => {
    const report = [
      `### OryxenAI Code Generator Traceability Report`,
      `- Timestamp: ${new Date().toISOString()}`,
      `- Session ID: ${sessionId || "current-session"}`,
      `- Trace ID: ${view.traceId || "local-dev-trace"}`,
      `- Active Job ID: ${view.activeJobId || view.job?.id || "N/A"}`,
      `- Coordinator Stage: ${coordStage || "verify"}`,
      `- Status: ${view.status}`,
      `- Attempt: ${view.currentAttempt || 1}${view.job?.maxAttempts ? ` of ${view.job.maxAttempts}` : ""}`,
      ``,
      `#### Error Summary`,
      `- Code: ${errorCode}`,
      `- Summary: ${view.safeError?.summary || "Generation stopped during build execution"}`,
      ``,
      `#### Identified Issues (${issues.length})`,
      ...(issues.length > 0 ? issues.map((iss, i) => `${i + 1}. ${iss}`) : ["None reported"]),
      ``,
      `#### Technical Context`,
      "```json",
      JSON.stringify(
        {
          status: view.status,
          coordinatorStage: coordStage,
          safeError: view.safeError,
          latestError: view.latestError,
          staleReasons: view.staleReasons,
        },
        null,
        2,
      ),
      "```",
    ].join("\n");

    await copyJson(report);
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 3000);
  };

  return (
    <div className="codegen-workspace" aria-labelledby="codegen-heading">
      {/* ===================================================================
          LEFT COLUMN: Activity, 5-Milestone Stepper & Instruction Composer
          =================================================================== */}
      <aside className="codegen-left-panel">
        <div className="codegen-panel-header">
          <p className="eyebrow">{eyebrow}</p>
          <h1 id="codegen-heading" className="codegen-main-title">{projectTitle}</h1>
          <p className="codegen-subtitle">{projectSubtitle}</p>
        </div>

        {/* Vertical 5-Milestone Stepper matching images 13, 14, 15 */}
        <div className="codegen-stepper" role="list" aria-label="Build progress milestones">
          {MILESTONES.map((milestone, idx) => {
            let stepStatus: "complete" | "active" | "attention" | "pending" = "pending";
            let timeText = "—";
            let descText = milestone.defaultDesc;

            if (isComplete) {
              stepStatus = "complete";
              timeText = "Complete";
              descText = milestone.completeDesc;
            } else if (isAvailable) {
              stepStatus = idx === 0 ? "pending" : "pending";
              timeText = idx === 0 ? "Ready" : "—";
              descText = milestone.defaultDesc;
            } else if (isWorking) {
              if (idx < activeIndex) {
                stepStatus = "complete";
                timeText = "Complete";
                descText = milestone.completeDesc;
              } else if (idx === activeIndex) {
                stepStatus = "active";
                timeText = "In progress";
                descText = milestone.workingDesc;
              } else {
                stepStatus = "pending";
                timeText = "Pending";
                descText = milestone.defaultDesc;
              }
            } else if (isAttention) {
              if (idx < failedIndex) {
                stepStatus = "complete";
                timeText = "Complete";
                descText = milestone.completeDesc;
              } else if (idx === failedIndex) {
                stepStatus = "attention";
                timeText = "Needs attention";
                descText = milestone.stoppedDesc;
              } else {
                stepStatus = "pending";
                timeText = "—";
                descText = milestone.defaultDesc;
              }
            }

            return (
              <div
                key={milestone.id}
                className={`codegen-step-item is-${stepStatus}`}
                role="listitem"
              >
                <div className="step-track-col" aria-hidden="true">
                  <div className={`step-node step-node--${stepStatus}`}>
                    {stepStatus === "complete" && <span className="check-mark">✓</span>}
                    {stepStatus === "attention" && <span className="alert-mark">!</span>}
                    {stepStatus === "active" && <span className="active-dot" />}
                    {stepStatus === "pending" && <span className="pending-num">{idx + 1}</span>}
                  </div>
                  {idx < MILESTONES.length - 1 && <div className="step-track-line" />}
                </div>

                <div className="step-content-col">
                  <div className="step-content-header">
                    <strong className="step-label">{milestone.label}</strong>
                    <span className={`step-tag tag--${stepStatus}`}>{timeText}</span>
                  </div>
                  <p className="step-desc">{descText}</p>
                  {isWorking && idx === activeIndex && typeof view.estimatedRemainingMs === "number" && (
                    <p className="step-estimate">{formatEstimatedTimeRemaining(view.estimatedRemainingMs)}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Instruction Composer Section matching images 13, 14, 15 */}
        <div className="codegen-composer-area">
          <p className="composer-eyebrow">
            {isAvailable && "APPROVED BUILD HANDOFF"}
            {isWorking && "GENERATION IN PROGRESS"}
            {isAttention && "RECOVERY ACTION"}
            {isComplete && "PREVIEW CONTROLS"}
          </p>

          <p className="composer-subprompt">
            {isAvailable && "The approved Build Preparation briefs are the complete input for this generation."}
            {isWorking && "The worker is progressing through planning, acquisition, build, verification, and preview promotion."}
            {isAttention && retryEnabled
              ? "Retry the durable generation with the same approved handoff, or open the diagnostic record."
              : isAttention
                ? "This run is preserved for diagnosis. Refresh the state or open the diagnostic record."
                : ""}
            {isComplete && "The promoted preview is ready. Regenerating creates a new verified candidate."}
          </p>

          <div className="composer-actions-row">
            {isAvailable && (
              <button type="button" className="btn-primary btn-cobalt" onClick={onStart} disabled={!canMutate || inFlight}>
                {inFlight ? "Starting..." : "Generate Portfolio →"}
              </button>
            )}

            {isWorking && (
              <span className="composer-quiet-hint">Generation is running from the approved handoff.</span>
            )}

            {isAttention && retryEnabled && (
              <button type="button" className="btn-primary btn-cobalt" onClick={onRetry} disabled={!canMutate || inFlight}>
                {inFlight ? "Retrying..." : "Retry"}
              </button>
            )}

            {isComplete && (
              <button type="button" className="btn-secondary" onClick={onRegenerate} disabled={!canMutate || inFlight}>
                Regenerate
              </button>
            )}
          </div>

          {isAvailable && <p className="composer-footnote">The generator consumes the immutable brief pair; no extra prompt is required.</p>}
          {isWorking && <p className="composer-footnote">This screen updates from durable job state. It will remain available if you refresh.</p>}

          {isAttention && (
            <div className="composer-details-link-row">
              <button
                type="button"
                className="technical-details-btn"
                onClick={() => setShowTraceabilityDrawer(true)}
              >
                ≡ View technical details
              </button>
            </div>
          )}
        </div>

      </aside>

      {/* ===================================================================
          RIGHT COLUMN: Live Preview Theater (+ Attention Card in Attention)
          =================================================================== */}
      <section className="codegen-theater-column" aria-label="Portfolio live preview theater">
        {/* Rose/Red-tinted Attention Card matching Image 15 */}
        {isAttention && (
          <div className="codegen-attention-card" role="alert" aria-live="assertive">
            <div className="attention-header-group">
              <div className="attention-icon-badge" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div className="attention-headline-group">
                <h2 className="attention-title">Generation needs attention</h2>
                <p className="attention-desc">
                  {view.safeError?.summary || "The build stopped during verification. Your saved work is safe."}
                </p>
              </div>

              <div className="attention-cta-group">
                {retryEnabled && <button
                  type="button"
                  className="btn-primary btn-cobalt attention-retry-btn"
                  onClick={onRetry}
                  disabled={!canMutate || inFlight}
                >
                  <span className="retry-symbol">↻</span>
                  {inFlight ? "Retrying generation…" : "Retry generation"}
                </button>}
                {!retryEnabled && (
                  <button
                    type="button"
                    className="btn-secondary attention-refresh-btn"
                    onClick={onRefresh}
                    disabled={!onRefresh || inFlight}
                  >
                    Refresh state
                  </button>
                )}
                <button
                  type="button"
                  className="btn-secondary attention-open-details-btn"
                  onClick={() => setShowTraceabilityDrawer(true)}
                >
                  Open details
                </button>
              </div>
            </div>

            {/* 3 Information Pillars matching Image 15 */}
            <div className="attention-pillars-row">
              <div className="attention-pillar">
                <div className="pillar-header">
                  <span className="pillar-icon" aria-hidden="true">📄</span>
                  <strong>Preview preserved</strong>
                </div>
                <p>
                  {hasVerifiedPreview
                    ? "Your last verified preview is still available."
                    : "Your brief, plan, and settings have been saved."}
                </p>
              </div>
              <div className="attention-pillar">
                <div className="pillar-header">
                  <span className="pillar-icon" aria-hidden="true">⏸</span>
                  <strong>Polling stopped</strong>
                </div>
                <p>We've stopped checking for new results.</p>
              </div>
              <div className="attention-pillar">
                <div className="pillar-header">
                  <span className="pillar-icon" aria-hidden="true">↻</span>
                  <strong>{retryEnabled ? "Retry available" : "Manual retry unavailable"}</strong>
                </div>
                <p>{retryEnabled ? "You can retry generation with the same settings." : "This diagnostic state must be reviewed before another run can be queued."}</p>
              </div>
            </div>
          </div>
        )}

        {/* Live Preview Theater Chrome matching Images 13, 14, 15 */}
        <div className="codegen-preview-theater">
          <div className="theater-toolbar">
            <div className="theater-toolbar-left">
              <span className="theater-eyebrow">LIVE PREVIEW</span>
              <span className={`theater-status-dot dot--${isComplete ? "live" : isWorking ? "updating" : isAttention ? "attention" : "ready"}`}>
                ● {isComplete ? "Live" : isWorking ? "Updating in real time" : isAttention ? "Attention required" : "Ready"}
              </span>
            </div>

            {/* Viewport Control: Dedicated Desktop ONLY per explicit user requirement */}
            <div className="theater-toolbar-controls">
              <div className="device-selector-pills" role="radiogroup" aria-label="Preview viewport">
                <button
                  type="button"
                  className="device-pill is-active"
                  aria-checked="true"
                  role="radio"
                  title="Desktop viewport (exclusive generation target)"
                >
                  <span className="device-icon">🖥️</span>
                  <span>Desktop</span>
                </button>
              </div>

              <div className="zoom-controls">
                <button
                  type="button"
                  className={`zoom-btn ${zoomFit ? "is-active" : ""}`}
                  onClick={() => setZoomFit(!zoomFit)}
                  title="Fit preview to view"
                >
                  ⛶ Fit to view
                </button>
              </div>
            </div>
          </div>

          {/* Browser Window Frame with macOS Chrome */}
          <div className={`codegen-browser-frame ${zoomFit ? "is-fitted" : ""}`}>
            <div className="browser-chrome">
              <div className="window-dots" aria-hidden="true">
                <span className="dot dot-close" />
                <span className="dot dot-minimize" />
                <span className="dot dot-zoom" />
              </div>

              <div className="browser-nav-arrows" aria-hidden="true">
                <button type="button" className="nav-arrow" disabled>←</button>
                <button type="button" className="nav-arrow" disabled>→</button>
                <button
                  type="button"
                  className="nav-arrow"
                  onClick={reloadPreview}
                  title="Reload preview"
                >
                  ⟳
                </button>
              </div>

              {/* Address bar with verified / candidate badge matching Image 15 */}
              <div className="browser-address-bar">
                {isAttention && hasVerifiedPreview && (
                  <span className="address-badge badge-verified">
                    <span className="shield-icon" aria-hidden="true">🛡️</span>
                    <span>Previous verified preview</span>
                  </span>
                )}
                {!hasVerifiedPreview && view.candidatePreview && (
                  <span className="address-badge badge-candidate">
                    <span>⚠️ Candidate preview (unverified)</span>
                  </span>
                )}
                <span className="address-url">
                  {previewUrl
                    ? previewUrl.replace(/^https?:\/\//, "")
                    : isAttention
                      ? "No preview promoted yet"
                      : "preview.oryxenai.local/"}
                </span>
              </div>
            </div>

            {/* Inner iframe or blueprint surface */}
            <div className="browser-content-viewport">
              {previewUrl ? (
                <>
                  <iframe
                    ref={previewFrameRef}
                    src={previewSrc}
                    title="Generated portfolio preview"
                    className="preview-iframe"
                    sandbox="allow-scripts allow-same-origin allow-forms"
                    onLoad={sendPreviewInit}
                    onError={() => {
                      setPreviewEmbedState("error");
                      setPreviewEmbedMessage("The generated preview could not be loaded.");
                    }}
                  />
                  {previewEmbedState === "degraded" && (
                    <p className="preview-embed-status" role="status">
                      {previewEmbedMessage || "Preview loaded. Waiting for an optional readiness signal."}
                    </p>
                  )}
                  {previewEmbedState === "error" && (
                    <p className="preview-embed-error" role="alert">
                      {previewEmbedMessage || "The generated preview is unavailable."} Open it in a new tab to inspect the diagnostic response.
                    </p>
                  )}
                </>
              ) : isWorking ? (
                <div className="preview-placeholder preview-placeholder--working">
                  <div className="wireframe-skeleton">
                    <div className="skeleton-hero">
                      <div className="skeleton-bar bar-title" />
                      <div className="skeleton-bar bar-sub" />
                      <div className="skeleton-image-box" />
                    </div>
                    <div className="skeleton-grid">
                      <div className="skeleton-card" />
                      <div className="skeleton-card" />
                    </div>
                  </div>
                  <p className="preview-loading-label">
                    <span className="loading-spinner" />
                    Assembling pages and running responsive checks…
                  </p>
                </div>
              ) : (
                <div className="preview-placeholder preview-placeholder--available">
                  <div className="blueprint-card">
                    <span className="blueprint-tag">READY FOR SYNTHESIS</span>
                    <h3 className="blueprint-title">Executive Portfolio</h3>
                    <p className="blueprint-desc">
                      Your handoff has been compiled into immutable briefs. Click Generate Portfolio to build the desktop site and promote the live preview.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Sub-footer update line matching Image 14 */}
            {isWorking && (
              <div className="theater-subfooter">
                <span className="theater-subfooter-left">
                  Preview updates after each verified backend milestone
                </span>
                <span className="theater-subfooter-right">{previewRoute ? `Route ${previewRoute}` : `Current attempt ${view.currentAttempt || 1}`}</span>
              </div>
            )}
          </div>

          {/* Action Bar matching Images 13, 14, 15 */}
          <div className="theater-action-bar">
            <div className="theater-action-left">
              {previewUrl ? (
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-open-preview"
                >
                  <span className="open-icon">↗</span>
                  <div className="open-text">
                    <strong>{hasVerifiedPreview ? "Open verified preview" : "Open candidate preview"}</strong>
                    <span>{hasVerifiedPreview ? "View in a new tab" : "Unverified — review in a new tab"}</span>
                  </div>
                </a>
              ) : (
                <span className="preview-unready-note">Preview ready after generation</span>
              )}
            </div>

            <div className="theater-action-right">
              {isAvailable && (
                <button
                  type="button"
                  className="btn-primary btn-cobalt btn-lg"
                  onClick={onStart}
                  disabled={!canMutate || inFlight}
                >
                  {inFlight ? "Generating…" : "Generate Portfolio →"}
                </button>
              )}

              {isWorking && <span className="preview-unready-note">Verification is in progress</span>}

              {isAttention && (
                <span className="preview-unready-note">
                  {retryEnabled ? "Use the recovery action above to continue." : "No manual retry is available for this run."}
                </span>
              )}

              {isComplete && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={onRegenerate}
                  disabled={!canMutate || inFlight}
                >
                  Regenerate portfolio
                </button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ===================================================================
          RIGHT-SIDE TRACEABILITY POP-UP DRAWER (USER'S EXPLICIT REQUIREMENT)
          =================================================================== */}
      {showTraceabilityDrawer && (
        <div
          className="codegen-drawer-backdrop"
          onClick={() => setShowTraceabilityDrawer(false)}
        >
          <aside
            className="codegen-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="codegen-drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-badge">DIAGNOSTICS & TRACEABILITY</span>
                <h2 id="drawer-title">Generation Issue Details</h2>
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                aria-label="Close details"
                onClick={() => setShowTraceabilityDrawer(false)}
              >
                ✕
              </button>
            </div>

            <div className="codegen-drawer-body">
              {/* Copy Diagnostic Report Action Banner */}
              <div className="drawer-copy-banner">
                <p>Copy full diagnostic report to clipboard for traceability and developer debugging.</p>
                <button
                  type="button"
                  className="btn-primary btn-cobalt drawer-copy-btn"
                  onClick={handleCopyReport}
                >
                  {copyFeedback ? "✓ Copied to clipboard!" : "📋 Copy diagnostic report"}
                </button>
              </div>

              {/* Failure Overview Card */}
              <div className="drawer-section">
                <h3 className="drawer-section-title">Failure Overview</h3>
                <div className="drawer-metric-grid">
                  <div className="drawer-metric">
                    <span className="metric-label">Failed Stage</span>
                    <strong className="metric-value font-mono">{failedStageName}</strong>
                  </div>
                  <div className="drawer-metric">
                    <span className="metric-label">Attempt</span>
                    <strong className="metric-value">{view.currentAttempt || 1}{view.job?.maxAttempts ? ` of ${view.job.maxAttempts}` : ""}</strong>
                  </div>
                  <div className="drawer-metric">
                    <span className="metric-label">Status</span>
                    <strong className="metric-value status-tag">{view.status}</strong>
                  </div>
                </div>

                {view.safeError?.summary && (
                  <div className="drawer-summary-box">
                    <strong>Safe Summary:</strong>
                    <p>{view.safeError.summary}</p>
                  </div>
                )}
              </div>

              {/* Traceability Identifiers */}
              <div className="drawer-section">
                <h3 className="drawer-section-title">Traceability Identifiers</h3>
                <dl className="drawer-id-list">
                  <div className="id-row">
                    <dt>Trace ID</dt>
                    <dd><code>{view.traceId || "local-dev-trace"}</code></dd>
                  </div>
                  <div className="id-row">
                    <dt>Active Job ID</dt>
                    <dd><code>{view.activeJobId || view.job?.id || "N/A"}</code></dd>
                  </div>
                  <div className="id-row">
                    <dt>Session ID</dt>
                    <dd><code>{sessionId || "current-session"}</code></dd>
                  </div>
                  <div className="id-row">
                    <dt>Error Code</dt>
                    <dd><code>{errorCode}</code></dd>
                  </div>
                </dl>
              </div>

              {/* Specific Issues List */}
              {issues.length > 0 && (
                <div className="drawer-section">
                  <h3 className="drawer-section-title">Specific Issues ({issues.length})</h3>
                  <ul className="drawer-issues-list">
                    {issues.map((issue, idx) => (
                      <li key={idx} className="drawer-issue-item">
                        <span className="issue-bullet" aria-hidden="true">⚠️</span>
                        <span className="issue-text">{issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Collapsible Raw Technical JSON */}
              <details className="drawer-tech-disclosure">
                <summary>View raw technical JSON</summary>
                <pre className="drawer-code-block">
                  {JSON.stringify(
                    {
                      status: view.status,
                      coordinatorStage: coordStage,
                      traceId: view.traceId,
                      activeJobId: view.activeJobId,
                      safeError: view.safeError,
                      latestError: view.latestError,
                      issues: view.issues,
                      staleReasons: view.staleReasons,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </div>

            <div className="codegen-drawer-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowTraceabilityDrawer(false)}
              >
                Close
              </button>
              {isAttention && retryEnabled && (
                <button
                  type="button"
                  className="btn-primary btn-cobalt"
                  onClick={async () => {
                    setShowTraceabilityDrawer(false);
                    await onRetry();
                  }}
                  disabled={!canMutate || inFlight}
                >
                  {inFlight ? "Retrying…" : "↻ Retry generation"}
                </button>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
