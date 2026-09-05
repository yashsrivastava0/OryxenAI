// ProgressSurface component (docs/Frontend/05 §8.8).
// Presents semantic milestones with clear completed/active/quiet markers,
// neutral elapsed context, and honest leave/return reassurance.
// Strictly avoids percentages, ETAs, token streams, or fake spinners.

import type { ComponentChildren } from "preact";
import { useState } from "preact/hooks";

export interface ProgressMilestoneItem {
  id: string;
  label: string;
  state: "complete" | "current" | "quiet";
}

export interface ProgressSurfaceProps {
  stageLabel: string;
  title: string;
  currentMilestone: string;
  milestones: ProgressMilestoneItem[];
  elapsedSeconds?: number | null;
  leaveNote?: string;
  secondarySummary?: ComponentChildren;
  onStop?: () => Promise<void>;
  stopLabel?: string;
}

interface ProgressStopActionProps {
  onStop: () => Promise<void>;
  stopLabel: string;
}

function ProgressStopAction({ onStop, stopLabel }: ProgressStopActionProps) {
  const [stopping, setStopping] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);

  const handleStop = async () => {
    if (stopping) return;
    setStopping(true);
    setStopError(null);
    try {
      await onStop();
    } catch (error) {
      setStopError(error instanceof Error ? error.message : "Could not stop this process.");
    } finally {
      setStopping(false);
    }
  };

  return (
    <>
      <div className="question-actions">
        <button type="button" className="btn-quiet stop-action" onClick={() => void handleStop()} disabled={stopping}>
          {stopping ? "Stopping..." : stopLabel}
        </button>
      </div>
      {stopError && <p className="error-copy" role="alert">{stopError}</p>}
    </>
  );
}

export function ProgressSurface({
  stageLabel,
  title,
  currentMilestone,
  milestones,
  elapsedSeconds = null,
  leaveNote = "You can safely navigate away or close this tab; work continues on the server.",
  secondarySummary,
  onStop,
  stopLabel = "Stop process",
}: ProgressSurfaceProps) {
  const formattedElapsed =
    elapsedSeconds !== null && elapsedSeconds > 0
      ? elapsedSeconds < 60
        ? `${Math.floor(elapsedSeconds)}s elapsed`
        : `${Math.floor(elapsedSeconds / 60)}m ${Math.floor(elapsedSeconds % 60)}s elapsed`
      : null;

  return (
    <section className="progress-surface" aria-label={`${stageLabel} progress`}>
      <header className="progress-header">
        <p className="eyebrow">{stageLabel}</p>
        <h2 className="progress-title">{title}</h2>
        <div className="progress-active-marker">
          <span className="pulse-indicator" aria-hidden="true" />
          <span className="current-milestone-text">{currentMilestone}</span>
        </div>
      </header>

      <div className="progress-body" aria-busy="true">
        <ol className="progress-milestones" role="list">
          {milestones.map((item) => (
            <li
              key={item.id}
              className="progress-milestone-item"
              data-state={item.state}
            >
              <span className="progress-milestone-indicator" aria-hidden="true">
                {item.state === "complete" ? (
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
                  </svg>
                ) : item.state === "current" ? (
                  <span className="current-dot" />
                ) : (
                  <span className="quiet-dot" />
                )}
              </span>
              <span className="progress-milestone-label">{item.label}</span>
            </li>
          ))}
        </ol>

        {formattedElapsed && (
          <p className="progress-elapsed">
            <span className="elapsed-label">Elapsed:</span>{" "}
            <span className="elapsed-value">{formattedElapsed}</span>
          </p>
        )}

        {leaveNote && <p className="progress-leave-note">{leaveNote}</p>}

        {onStop && (
          <ProgressStopAction onStop={onStop} stopLabel={stopLabel} />
        )}
      </div>

      {secondarySummary && (
        <aside className="progress-secondary-summary" aria-label="Summary details">
          {secondarySummary}
        </aside>
      )}
    </section>
  );
}
