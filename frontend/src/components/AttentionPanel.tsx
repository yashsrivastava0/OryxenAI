import { useState } from "preact/hooks";

export interface AttentionPanelProps {
  title?: string;
  summary: string;
  preservedWorkNote?: string;
  retryLabel?: string;
  onRetry?: () => void | Promise<void>;
  technicalDetails?: string | null;
  inFlight?: boolean;
}

export function AttentionPanel({
  title = "This stage needs attention",
  summary,
  preservedWorkNote = "Your previous approved work and inputs are safely preserved.",
  retryLabel = "Try again",
  onRetry,
  technicalDetails = null,
  inFlight = false,
}: AttentionPanelProps) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    if (!onRetry || retrying || inFlight) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="attention-panel" role="alert">
      <div className="attention-header">
        <span className="attention-icon" aria-hidden="true">⚠</span>
        <h3 className="attention-title">{title}</h3>
      </div>

      <p className="attention-summary">{summary}</p>
      {preservedWorkNote && <p className="attention-preserved">{preservedWorkNote}</p>}

      {onRetry && (
        <div className="attention-actions">
          <button
            type="button"
            className="btn-primary attention-retry-btn"
            disabled={retrying || inFlight}
            onClick={handleRetry}
          >
            {retrying || inFlight ? "Retrying..." : retryLabel}
          </button>
        </div>
      )}

      {technicalDetails && (
        <details className="attention-technical">
          <summary>Technical reference</summary>
          <pre>{technicalDetails}</pre>
        </details>
      )}
    </div>
  );
}
