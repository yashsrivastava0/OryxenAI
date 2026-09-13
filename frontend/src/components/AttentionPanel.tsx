import { useState } from "preact/hooks";
import type { SafeStageError } from "../data/adapters/types";

export interface AttentionPanelProps {
  title?: string;
  summary: string;
  preservedWorkNote?: string;
  retryLabel?: string;
  onRetry?: () => void | Promise<void>;
  retryAvailable?: boolean;
  technicalDetails?: string | null;
  errorDetails?: Pick<SafeStageError, "providerLabel" | "operationLabel" | "retryAfterSeconds" | "supportReference">;
  inFlight?: boolean;
}

export function AttentionPanel({
  title = "This stage needs attention",
  summary,
  preservedWorkNote = "Your previous approved work and inputs are safely preserved.",
  retryLabel = "Try again",
  onRetry,
  retryAvailable = true,
  technicalDetails = null,
  errorDetails,
  inFlight = false,
}: AttentionPanelProps) {
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const handleRetry = async () => {
    if (!onRetry || retrying || inFlight) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (reason) {
      setRetryError(reason instanceof Error ? reason.message : "Retry could not be started. Please try again.");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="attention-panel" role="alert">
      <div className="attention-header">
        <span className="attention-icon" aria-hidden="true">!</span>
        <h3 className="attention-title">{title}</h3>
      </div>

      <p className="attention-summary">{summary}</p>
      {preservedWorkNote && <p className="attention-preserved">{preservedWorkNote}</p>}
      {errorDetails?.providerLabel || errorDetails?.operationLabel ? (
        <p className="attention-attribution">
          {errorDetails.providerLabel ? `Provider: ${errorDetails.providerLabel}` : null}
          {errorDetails.providerLabel && errorDetails.operationLabel ? " · " : null}
          {errorDetails.operationLabel ? `Operation: ${errorDetails.operationLabel}` : null}
        </p>
      ) : null}
      {errorDetails?.retryAfterSeconds !== undefined ? (
        <p className="attention-retry-after" role="status">
          Retry after approximately {Math.max(1, Math.ceil(errorDetails.retryAfterSeconds))} seconds.
        </p>
      ) : null}
      {errorDetails?.supportReference ? (
        <p className="attention-reference">Reference: {errorDetails.supportReference}</p>
      ) : null}
      {retryError ? <p className="attention-retry-error" role="alert">{retryError}</p> : null}

      {onRetry && retryAvailable ? (
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
      ) : (
        <p className="attention-refresh-note">Refresh to check the latest state, or contact support if this continues.</p>
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
