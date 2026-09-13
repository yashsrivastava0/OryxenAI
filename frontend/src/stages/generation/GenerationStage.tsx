import { useState } from "preact/hooks";
import type { GenerationViewModel } from "../../data/adapters/generation";
import { copyJson } from "../../data/clipboard";

export interface GenerationStageProps {
  view: GenerationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  sessionId?: string | null;
  onStart: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRegenerate: () => Promise<void>;
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
}: GenerationStageProps) {
  const [instructionText, setInstructionText] = useState("");
  const [showTraceabilityDrawer, setShowTraceabilityDrawer] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [zoomFit, setZoomFit] = useState(true);

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

  let activeIndex = 0;
  if (coordStage) {
    const idx = stageKeys.indexOf(coordStage);
    if (idx >= 0) activeIndex = idx;
  }

  // In attention state, the failed stage is activeIndex (defaults to verify if unknown)
  const failedIndex = isAttention ? (activeIndex >= 0 ? activeIndex : 3) : -1;

  // Active preview URL
  const previewUrl = view.preview?.url || view.candidatePreview?.url || "";
  const hasVerifiedPreview = Boolean(view.preview?.url);

  // Headline and subtitle for left panel
  const projectTitle = isAvailable
    ? "From idea to launch."
    : isWorking
      ? "Building your site"
      : view.projectTitle || "Personal Portfolio";

  const projectSubtitle = isAvailable
    ? "OryxenAI turns your ideas into working software, step by step. Follow the plan, refine as you go, and preview in real time."
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
      `- Attempt: ${view.currentAttempt || 1} of 2`,
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
                timeText = idx === 0 ? "1m ago" : "1m ago";
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
                timeText = `${idx + 2}m`;
                descText = milestone.completeDesc;
              } else if (idx === failedIndex) {
                stepStatus = "attention";
                timeText = "1m";
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

                  {/* Progress Bar on Active Build step matching image 14 */}
                  {stepStatus === "active" && milestone.id === "build" && (
                    <div className="step-progress-row">
                      <div className="step-progress-bar">
                        <div className="step-progress-fill" style={{ width: "62%" }} />
                      </div>
                      <span className="step-progress-percent">62%</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Instruction Composer Section matching images 13, 14, 15 */}
        <div className="codegen-composer-area">
          <label htmlFor="codegen-instruction-input" className="composer-eyebrow">
            {isAvailable && "TELL ORYXENAI WHAT TO DO NEXT"}
            {isWorking && "Add a follow-up instruction"}
            {isAttention && "Next step"}
            {isComplete && "Refine your portfolio"}
          </label>

          {isAttention && (
            <p className="composer-subprompt">
              Tell the agent what to fix, or retry with a new instruction.
            </p>
          )}

          <div className="composer-box">
            <textarea
              id="codegen-instruction-input"
              className="composer-textarea"
              rows={3}
              placeholder={
                isAvailable
                  ? "Describe the next change..."
                  : isWorking
                    ? "Describe a change or ask about this build..."
                    : isAttention
                      ? "Tell the agent what to fix..."
                      : "Describe a change to make to your portfolio..."
              }
              value={instructionText}
              onInput={(e) => setInstructionText((e.target as HTMLTextAreaElement).value)}
              disabled={inFlight}
            />

            {isAttention && (
              <div className="composer-char-count">{instructionText.length}/500</div>
            )}
          </div>

          <div className="composer-actions-row">
            {isAvailable && (
              <>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => setInstructionText("Focus on projects, leadership, and clean visual typography.")}
                >
                  + Add context
                </button>
                <button
                  type="button"
                  className="btn-primary btn-cobalt"
                  onClick={onStart}
                  disabled={!canMutate || inFlight}
                >
                  {inFlight ? "Starting…" : "Generate Portfolio →"}
                </button>
              </>
            )}

            {isWorking && (
              <>
                <span className="composer-quiet-hint">You can keep working while we build.</span>
                <button
                  type="button"
                  className="btn-secondary"
                  disabled={!instructionText.trim()}
                  onClick={() => setInstructionText("")}
                >
                  Send
                </button>
              </>
            )}

            {isAttention && (
              <>
                <button
                  type="button"
                  className="btn-primary btn-cobalt"
                  onClick={onRetry}
                  disabled={!canMutate || inFlight}
                >
                  {inFlight ? "Sending fix…" : "Send →"}
                </button>
              </>
            )}

            {isComplete && (
              <>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={onRegenerate}
                  disabled={!canMutate || inFlight}
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  className="btn-primary btn-cobalt"
                  disabled={!instructionText.trim() || inFlight}
                  onClick={onRegenerate}
                >
                  Send →
                </button>
              </>
            )}
          </div>

          {isAvailable && (
            <p className="composer-footnote">
              Be specific. You can mention sections, content, or style changes.
            </p>
          )}

          {isWorking && (
            <div className="composer-stop-row">
              <button
                type="button"
                className="btn-secondary btn-stop"
                onClick={() => {}}
                title="Stop current generation"
              >
                ■ Stop generation
              </button>
            </div>
          )}

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
                <button
                  type="button"
                  className="btn-primary btn-cobalt attention-retry-btn"
                  onClick={onRetry}
                  disabled={!canMutate || inFlight}
                >
                  <span className="retry-symbol">↻</span>
                  {inFlight ? "Retrying generation…" : "Retry generation"}
                </button>
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
                  <strong>Retry available</strong>
                </div>
                <p>You can retry generation with the same settings.</p>
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
                  onClick={() => {
                    const iframe = document.querySelector(".preview-iframe") as HTMLIFrameElement;
                    if (iframe && previewUrl) iframe.src = previewUrl;
                  }}
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
                {!isAttention && view.candidatePreview && !view.preview && (
                  <span className="address-badge badge-candidate">
                    <span>⚠️ Candidate preview (unverified)</span>
                  </span>
                )}
                <span className="address-url">
                  {previewUrl ? previewUrl.replace(/^https?:\/\//, "") : "preview.oryxenai.local/"}
                </span>
              </div>
            </div>

            {/* Inner iframe or blueprint surface */}
            <div className="browser-content-viewport">
              {previewUrl ? (
                <iframe
                  src={previewUrl}
                  title="Generated portfolio preview"
                  className="preview-iframe"
                  sandbox="allow-scripts allow-same-origin allow-forms"
                />
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
                  <span className="pulse-dot" /> Preview updating as pages are verified
                </span>
                <span className="theater-subfooter-right">Last update moments ago</span>
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
                    <strong>Open preview</strong>
                    <span>View in a new tab</span>
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

              {isWorking && (
                <button type="button" className="btn-disabled-lock" disabled>
                  <span className="lock-icon">🔒</span>
                  <span>Publish unavailable until verification completes</span>
                </button>
              )}

              {isAttention && (
                <div className="publish-attention-lock">
                  <button type="button" className="btn-disabled-lock" disabled>
                    <span className="upload-icon">⬆</span>
                    <span>Publish after verification</span>
                  </button>
                  <span
                    className="info-bubble"
                    title="Publishing requires complete and verified portfolio checks."
                  >
                    ⓘ
                  </span>
                </div>
              )}

              {isComplete && (
                <button
                  type="button"
                  className="btn-primary btn-cobalt btn-lg"
                  onClick={() => {
                    if (previewUrl) window.open(previewUrl, "_blank");
                  }}
                >
                  <span className="publish-icon">🚀</span>
                  <div className="publish-text">
                    <strong>Publish when ready</strong>
                    <span>Deploy your project</span>
                  </div>
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
                    <strong className="metric-value">{view.currentAttempt || 1} of 2</strong>
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
              {isAttention && view.retryAvailable && (
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
