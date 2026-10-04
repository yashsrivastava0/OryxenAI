import { useState } from "preact/hooks";
import type { SafeStageError } from "../data/adapters/types";
import type { StageJobViewModel } from "../data/adapters/job";
import { captureFailure, type FailureDiagnosticInput } from "../data/failure-diagnostics";
import { CopyDiagnosticsButton } from "./CopyDiagnosticsButton";

export interface AttentionPanelProps {
  stage: string;
  title?: string;
  summary: string;
  preservedWorkNote?: string;
  retryLabel?: string;
  onRetry?: () => void | Promise<void>;
  retryAvailable?: boolean;
  technicalDetails?: string | null;
  errorDetails?: SafeStageError;
  job?: StageJobViewModel | null;
  inFlight?: boolean;
}

const OPERATION_NAMES: Record<string, string> = {
  understand_and_question: "Preparing your questions",
  prepare_questions: "Preparing your questions",
  build_or_revise_brief: "Writing your brief",
  build_brief: "Writing your brief",
  "content_architect.build": "Writing your page content",
  plan_content: "Planning your page content",
  write_pages: "Writing your page content",
  integrate_content: "Completing your page content",
};

function friendlyOperation(label?: string): string | undefined {
  if (!label) return undefined;
  return (
    OPERATION_NAMES[label] ??
    label.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
}

export function AttentionPanel({
  stage,
  title = "This stage needs attention",
  summary,
  preservedWorkNote = "Your previous approved work and inputs are safely preserved.",
  retryLabel = "Try again",
  onRetry,
  retryAvailable = true,
  technicalDetails = null,
  errorDetails,
  job,
  inFlight = false,
}: AttentionPanelProps) {
  const operationName = friendlyOperation(errorDetails?.operationLabel);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<FailureDiagnosticInput | null>(null);
  const diagnostic: FailureDiagnosticInput = {
    stage,
    action: "background job",
    summary,
    occurredAt: errorDetails?.occurredAt ?? job?.finishedAt,
    code: errorDetails?.code ?? job?.error?.code,
    jobId: job?.id,
    operation: errorDetails?.operationLabel,
    suboperation: errorDetails?.suboperation,
    supportReference: errorDetails?.supportReference,
    issueCount: errorDetails?.issueCount,
    issues: errorDetails?.issues,
  };

  const handleRetry = async () => {
    if (!onRetry || retrying || inFlight) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (reason) {
      setRetryError(captureFailure(reason, stage, "retry", "Retry could not be started. Please try again."));
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
          {operationName ? `Operation: ${operationName}` : null}
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
      {retryError ? <p className="attention-retry-error" role="alert">{retryError.summary} <CopyDiagnosticsButton failure={retryError} /></p> : null}

      <div className="attention-actions">
        {onRetry && retryAvailable ? (
          <button
            type="button"
            className="btn-primary attention-retry-btn"
            disabled={retrying || inFlight}
            onClick={handleRetry}
          >
            {retrying || inFlight ? "Retrying..." : retryLabel}
          </button>
        ) : (
          <p className="attention-refresh-note">Refresh to check the latest state, or contact support if this continues.</p>
        )}
        <CopyDiagnosticsButton failure={diagnostic} />
      </div>

      {technicalDetails && (
        <details className="attention-technical">
          <summary>Technical reference</summary>
          <pre>{technicalDetails}</pre>
        </details>
      )}
    </div>
  );
}
