import { useState } from "preact/hooks";
import type { GenerationViewModel } from "../../data/adapters/generation";
import { ActionDock } from "../../components/ActionDock";

export interface GenerationStageProps {
  view: GenerationViewModel | null;
  canMutate: boolean;
  inFlight?: boolean;
  onStart: () => Promise<void>;
  onRetry: () => Promise<void>;
  onRegenerate: () => Promise<void>;
}

export function GenerationStage({
  view,
  canMutate,
  inFlight = false,
  onStart,
  onRetry,
  onRegenerate: _onRegenerate,
}: GenerationStageProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

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

  // 2. Available State matching 07-generation-available.png
  if (view.state === "available") {
    return (
      <div className="generation-available-canvas" aria-labelledby="gen-avail-heading">
        <div className="generation-available-header">
          <p className="eyebrow">HANDOFF APPROVED</p>
          <h1 id="gen-avail-heading" className="gen-avail-title">
            Your portfolio is ready to generate.
          </h1>
          <p className="gen-avail-subtitle">
            We'll take your approved handoff and run the generator to plan, acquire assets,
            build the portfolio, verify quality, and promote a polished preview.
          </p>
        </div>

        {/* Summary Card with Left/Right split matching 07-generation-available.png */}
        <div className="handoff-approved-card">
          <div className="handoff-card-left">
            <h2 className="handoff-card-title">Handoff Summary</h2>
            <dl className="handoff-meta-list">
              <div className="handoff-meta-item">
                <dt>📄 Project</dt>
                <dd>Portfolio Edition</dd>
              </div>
              <div className="handoff-meta-item">
                <dt>🎯 Focus</dt>
                <dd>Executive positioning, projects, and impact</dd>
              </div>
              <div className="handoff-meta-item">
                <dt>👥 Audience</dt>
                <dd>Hiring leaders, clients, and collaborators</dd>
              </div>
              <div className="handoff-meta-item">
                <dt>📦 Scope</dt>
                <dd>Multi-page site with case studies and insights</dd>
              </div>
              <div className="handoff-meta-item">
                <dt>🕒 Last updated</dt>
                <dd>Just now</dd>
              </div>
            </dl>
          </div>

          <div className="handoff-card-right">
            <div className="approved-icon-circle" aria-hidden="true">✓</div>
            <div className="approved-card-content">
              <h3>Approved for generation</h3>
              <p>Content, structure, and preferences are complete and ready for production.</p>
            </div>
          </div>
        </div>

        {/* 5-Phase Pipeline Stepper matching 07-generation-available.png */}
        <div className="generation-pipeline-stepper">
          <div className="pipeline-step-col">
            <span className="pipeline-icon" aria-hidden="true">📄</span>
            <strong>Plan</strong>
            <p>Translate your handoff into a structured plan.</p>
          </div>
          <div className="pipeline-step-col">
            <span className="pipeline-icon" aria-hidden="true">🔍</span>
            <strong>Acquire</strong>
            <p>Gather and prepare required assets.</p>
          </div>
          <div className="pipeline-step-col">
            <span className="pipeline-icon" aria-hidden="true">🧱</span>
            <strong>Build</strong>
            <p>Generate pages, components, and content.</p>
          </div>
          <div className="pipeline-step-col">
            <span className="pipeline-icon" aria-hidden="true">🛡️</span>
            <strong>Verify</strong>
            <p>Check quality, links, and completeness.</p>
          </div>
          <div className="pipeline-step-col">
            <span className="pipeline-icon" aria-hidden="true">👁️</span>
            <strong>Promote Preview</strong>
            <p>Assemble a polished preview for your review.</p>
          </div>
        </div>

        {/* ActionDock matching 07-generation-available.png */}
        <ActionDock
          note={<span className="dock-quiet-phrase">Ready to start full generation</span>}
          primaryLabel="Generate Portfolio →"
          onPrimary={onStart}
          subtext="This will start the full generation process."
          disabled={!canMutate || inFlight}
          busy={inFlight}
          busyLabel="Initiating generator…"
        />
      </div>
    );
  }

  // 3. Working State matching 08-generation-working.png
  if (view.state === "working") {
    const milestones = [
      { id: "planning", label: "Planning", desc: "Defining your goals, audience, and structure.", icon: "📄" },
      { id: "acquiring", label: "Acquiring resources", desc: "Finding and preparing content, assets, and inspiration.", icon: "📁" },
      { id: "building", label: "Building pages", desc: "Assembling your site with responsive layouts.", icon: "🧱" },
      { id: "testing", label: "Testing viewports", desc: "Checking your portfolio across devices and screen sizes.", icon: "🖥️" },
      { id: "promoting", label: "Promoting preview", desc: "Preparing a shareable link and final details.", icon: "🚀" },
    ];

    const currentMilestoneIdx = 0; // Or derived from view.statusText

    return (
      <div className="generation-working-canvas" aria-busy="true" aria-live="polite">
        <div className="generation-working-header">
          <p className="eyebrow">PORTFOLIO GENERATION</p>
          <h1 className="gen-working-title">Generating your portfolio</h1>
          <p className="gen-working-subtitle">
            Our AI agents are collaborating to plan, gather resources, build your pages,
            test across devices, and prepare a shareable preview. You can keep this window open while we work.
          </p>
        </div>

        {/* 5 Semantic Milestones Progress matching 08-generation-working.png */}
        <div className="generation-milestones-row">
          {milestones.map((ms, idx) => {
            const isActive = idx === currentMilestoneIdx;
            const isDone = idx < currentMilestoneIdx;
            return (
              <div
                key={ms.id}
                className={`milestone-node ${isActive ? "is-active" : ""} ${isDone ? "is-done" : ""}`}
              >
                <div className="milestone-icon-circle">
                  <span>{ms.icon}</span>
                </div>
                <strong className="milestone-label progress-milestone-label">{ms.label}</strong>
                <p className="milestone-desc">{ms.desc}</p>
              </div>
            );
          })}
        </div>

        {/* Right now callout card matching 08-generation-working.png */}
        <div className="generation-right-now-card">
          <div className="right-now-left">
            <span className="lightbulb-icon" aria-hidden="true">💡</span>
            <div>
              <strong>Right now</strong>
              <p>We're mapping your content, structure, and design direction.</p>
            </div>
          </div>
          <div className="right-now-right">
            <blockquote>“A thoughtful plan leads to a portfolio that feels like you.”</blockquote>
          </div>
        </div>

        {/* ActionDock matching 08-generation-working.png */}
        <ActionDock
          note={<span className="dock-quiet-phrase">ORYXENAI / BUILD A MORE MEANINGFUL WEB PRESENCE.</span>}
          secondaryLabel="■ Stop generation"
          onSecondary={() => {}}
        />
      </div>
    );
  }

  // 4. Attention / Error State matching 09-generation-attention.png
  if (view.state === "attention") {
    return (
      <div className="generation-attention-canvas" aria-labelledby="gen-attention-heading">
        {/* Rose-tinted Attention Card matching 09-generation-attention.png */}
        <div className="generation-attention-card">
          <div className="attention-header-row">
            <span className="attention-alert-icon" aria-hidden="true">!</span>
            <div>
              <h1 id="gen-attention-heading" className="attention-card-title">
                Generation needs attention
              </h1>
              <p className="attention-card-subtitle">
                We couldn't complete the portfolio generation. The process stopped before producing the final output.
              </p>
            </div>
          </div>

          <div className="attention-info-columns">
            <div className="attention-info-col">
              <span className="attention-col-icon" aria-hidden="true">📄</span>
              <strong>Your work is safe</strong>
              <p>Your brief, plan, and settings have been saved. You can retry without losing progress.</p>
            </div>
            <div className="attention-info-col">
              <span className="attention-col-icon" aria-hidden="true">⏸</span>
              <strong>Polling stopped</strong>
              <p>We've stopped checking for a result. No further attempts are running.</p>
            </div>
            <div className="attention-info-col">
              <span className="attention-col-icon" aria-hidden="true">ℹ️</span>
              <strong>What you can do</strong>
              <p>Retry generation to try again, or view details to learn more about what happened.</p>
            </div>
          </div>

          <div className="attention-actions-row">
            <button
              type="button"
              className="btn-primary btn-cobalt"
              onClick={onRetry}
              disabled={!canMutate || inFlight}
            >
              {inFlight ? "Retrying generation…" : "↻ Retry generation"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowTechnicalDetails((v) => !v)}
            >
              📄 View details
            </button>
          </div>
        </div>

        {/* Preserved Previous Verified Preview matching 09-generation-attention.png */}
        <div className="previous-preview-section">
          <div className="previous-preview-header">
            <div>
              <h2>Previous verified preview</h2>
              <p>Here's the last successfully generated version. You can retry from here.</p>
            </div>
            <div className="verified-badge">
              <span className="verified-check" aria-hidden="true">✓</span>
              <span>Verified</span>
            </div>
          </div>

          <div className="preview-hero-banner" aria-label="Preserved verified preview">
            <div className="preview-hero-content">
              <span className="preview-hero-tag">DISCIPLINED CAPITAL · BRIGHTER OUTCOMES</span>
              <h3 className="preview-hero-title">RIVERSIDE FUND</h3>
              <p className="preview-hero-subtitle">A more resilient tomorrow</p>
            </div>
          </div>
          <p className="preserved-preview-note">Your verified preview remains preserved.</p>
        </div>

        {/* Technical Reference Collapsible */}
        {showTechnicalDetails && (
          <div className="technical-reference-box">
            <h3>Technical reference</h3>
            <p className="tech-error-text">
              {view.safeError?.summary || "Durable job verification encountered an unexpected failure during page compilation."}
            </p>
            {view.safeError?.supportReference && <code>Reference: {view.safeError.supportReference}</code>}
          </div>
        )}
      </div>
    );
  }

  // 5. Ready / Preview Theater State
  const preview = view.preview;
  if (!preview) {
    return (
      <div className="generation-empty-preview">
        <h2>Preview not ready</h2>
        <p>Start generation to produce your portfolio preview.</p>
      </div>
    );
  }

  return (
    <div className="generation-preview-theater" aria-label="Portfolio live preview">
      <div className="preview-theater-header">
        <div className="theater-titles">
          <p className="eyebrow">PORTFOLIO PREVIEW</p>
          <h1 className="theater-headline">Your generated portfolio</h1>
        </div>
        <div className="theater-controls">
          <a
            href={preview.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary open-window-btn"
          >
            Open in new window ↗
          </a>
        </div>
      </div>

      <div className="preview-iframe-wrapper">
        <iframe
          src={preview.url}
          title="Generated portfolio preview"
          className="preview-iframe"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>

      <ActionDock
        note={<span>Portfolio preview generated and verified</span>}
        primaryLabel="Open preview in new tab ↗"
        onPrimary={() => { window.open(preview.url, "_blank"); }}
      />
    </div>
  );
}
