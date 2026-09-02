// GenerationStage component (docs/Frontend/05 §4.6, §6.5, §8.8).
// Presents the Code Generator phase: locked, available, working, complete, or attention.

import type { GenerationViewModel } from "../../data/adapters/generation";
import { ProgressSurface } from "../../components/ProgressSurface";
import { AttentionPanel } from "../../components/AttentionPanel";

export interface GenerationStageProps {
  view: GenerationViewModel | null;
  canMutate: boolean;
  readOnly: boolean;
  onStart: () => Promise<void> | void;
  onRetry: () => Promise<void> | void;
  onOpenPreview: () => void;
  inFlight?: boolean;
}

export function GenerationStage({
  view,
  canMutate,
  readOnly,
  onStart,
  onRetry,
  onOpenPreview,
  inFlight = false,
}: GenerationStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 05 / Generate</p>
        <h2>Code Generation is Locked</h2>
        <p className="stage-desc">
          Code Generation requires a completed, verified Build Preparation handoff before planning can begin.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 05 / Generate</p>
        <h2>Generate Verified Portfolio</h2>
        <p className="stage-desc">
          Builds and tests your responsive portfolio site from the verified handoff package.
          Plans architecture, resolves resources, compiles routes, runs verified build checks, and prepares an isolated Preview.
        </p>
        <div className="stage-actions">
          <button
            type="button"
            className="btn-primary"
            disabled={!canMutate || inFlight || readOnly}
            onClick={onStart}
          >
            {inFlight ? "Starting generation..." : "Generate portfolio"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 05 / Generate"
        title="Generating Your Portfolio"
        currentMilestone={view.currentMilestone}
        milestones={view.milestones}
        elapsedSeconds={view.elapsedSeconds}
        secondarySummary={
          view.hasUsablePreview ? (
            <p className="progress-summary-item">
              An existing verified Preview is still available while this new build completes.
            </p>
          ) : undefined
        }
      />
    );
  }

  if (view.state === "complete") {
    return (
      <div className="generation-stage-view">
        <div className="generation-complete-summary">
          <p className="eyebrow">Stage 05 / Generate</p>
          <h2>Portfolio Generation Complete</h2>
          <p className="stage-desc">
            Your portfolio has been compiled, checked against geometry and runtime requirements, and promoted to verified Preview.
          </p>
          {view.activePreview?.promotedAt && (
            <p className="generation-promoted-meta">
              Promoted at {new Date(view.activePreview.promotedAt).toLocaleTimeString()}
            </p>
          )}
          <div className="stage-actions">
            <button
              type="button"
              className="btn-primary"
              onClick={onOpenPreview}
            >
              Open Preview
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (view.state === "attention") {
    return (
      <div className="generation-stage-view">
        <AttentionPanel
          title="Generation Needs Attention"
          summary={view.safeError?.summary ?? view.statusText}
          preservedWorkNote={
            view.hasUsablePreview
              ? "Your previously verified Preview remains active and viewable."
              : "Your approved build handoff and specifications remain safely preserved."
          }
          retryLabel="Retry generation"
          onRetry={view.retryEligible && canMutate ? onRetry : undefined}
          technicalDetails={view.safeError?.technicalDetails ?? (view.supportReference ? `Trace ID: ${view.supportReference}` : null)}
          inFlight={inFlight}
        />
      </div>
    );
  }

  return (
    <div className="stage-unsupported-panel">
      <p className="eyebrow">Stage 05 / Generate</p>
      <h2>Unrecognized Generation State</h2>
      <p className="stage-desc">
        This stage returned a state that is not recognized. Please refresh your browser or reconnect to continue.
      </p>
    </div>
  );
}
