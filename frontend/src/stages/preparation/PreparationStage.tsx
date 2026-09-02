// PreparationStage component (docs/Frontend/05 §4.5, §6.4, §8.8).
// Presents the Build Preparation phase: locked, available, working, complete, or attention.

import type { PreparationViewModel } from "../../data/adapters/preparation";
import { ProgressSurface } from "../../components/ProgressSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { HandoffPanel } from "../../components/HandoffPanel";

export interface PreparationStageProps {
  view: PreparationViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void> | void;
  onRegenerate: () => Promise<void> | void;
  onContinueToGeneration: () => void;
  inFlight?: boolean;
}

export function PreparationStage({
  view,
  canMutate,
  onStart,
  onRegenerate,
  onContinueToGeneration,
  inFlight = false,
}: PreparationStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 04 / Prepare</p>
        <h2>Build Preparation is Locked</h2>
        <p className="stage-desc">
          Build Preparation requires approved Content Plan and Visual Direction before compilation can begin.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 04 / Prepare</p>
        <h2>Prepare Portfolio Build Hand-off</h2>
        <p className="stage-desc">
          Validates your approved content and design direction, resolves required portfolio materials,
          and compiles a verified build package ready for code generation.
        </p>
        <div className="stage-actions">
          <button
            type="button"
            className="btn-primary"
            disabled={!canMutate || inFlight}
            onClick={onStart}
          >
            {inFlight ? "Starting preparation..." : "Prepare build"}
          </button>
        </div>
      </div>
    );
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 04 / Prepare"
        title="Preparing Your Portfolio Build"
        currentMilestone={view.currentMilestone}
        milestones={view.milestones}
        elapsedSeconds={view.elapsedSeconds}
        secondarySummary={
          view.routeCount ? (
            <p className="progress-summary-item">
              Compiling context for <strong>{view.routeCount}</strong> approved routes.
            </p>
          ) : undefined
        }
      />
    );
  }

  if (view.state === "complete") {
    return (
      <div className="preparation-stage-view">
        <div className="preparation-complete-summary">
          <p className="eyebrow">Stage 04 / Prepare</p>
          <h2>Build Hand-off Verified</h2>
          <p className="stage-desc">
            Your portfolio build context, route specifications, and verified assets have been packaged and confirmed.
          </p>
          {view.warnings.length > 0 && (
            <div className="stage-warnings-box">
              <span className="warning-label">Advisories:</span>
              <ul>
                {view.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <HandoffPanel
          completedStageName="Build Preparation"
          nextStageName="Code Generation"
          summary="Your verified build handoff package is assembled and ready."
          nextDescription="Plans, generates, and verifies your responsive portfolio site code on a dedicated generation lane."
          actionLabel="Continue to Generation"
          onContinue={onContinueToGeneration}
          disabled={!canMutate}
        />
      </div>
    );
  }

  if (view.state === "attention") {
    return (
      <div className="preparation-stage-view">
        <AttentionPanel
          title="Build Preparation Needs Attention"
          summary={
            view.safeError?.summary ??
            (view.stale
              ? "Approved inputs changed after preparation was completed. Regenerate to produce an up-to-date build handoff."
              : "Build preparation stopped before the verified package could be completed.")
          }
          preservedWorkNote="Your approved Content Plan and Visual Direction remain safely saved."
          retryLabel={view.stale ? "Regenerate preparation" : "Try again"}
          onRetry={canMutate ? onRegenerate : undefined}
          technicalDetails={
            view.safeError?.technicalDetails ??
            (view.staleReasons.length ? `Stale reasons: ${view.staleReasons.join(", ")}` : null)
          }
          inFlight={inFlight}
        />
      </div>
    );
  }

  return (
    <div className="stage-unsupported-panel">
      <p className="eyebrow">Stage 04 / Prepare</p>
      <h2>Unrecognized Stage State</h2>
      <p className="stage-desc">
        This stage returned a state that is not recognized. Please refresh your browser or reconnect to continue.
      </p>
    </div>
  );
}
