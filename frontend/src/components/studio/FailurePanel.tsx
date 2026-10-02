import { useState } from "preact/hooks";
import { copyJson, type CopyJsonResult } from "../../data/clipboard";
import { failureDiagnostics, type StudioFailureVM } from "../../data/adapters/studio";

const STAGE_LABEL: Record<string, string> = {
  start: "Starting the build",
  interpret: "Understanding your request",
  generate: "Writing the page",
  validate: "Checking the page",
  bundle: "Packaging the page",
  verify: "Testing in a browser",
  promote: "Publishing the preview",
};

const OWNER_LABEL: Record<string, string> = {
  model_output: "The writing model's output",
  validation: "The page checks",
  content: "Your approved content",
  theme: "The page theme",
  browser: "The browser test",
  infrastructure: "The service",
  configuration: "Service configuration",
  user_input: "Your action",
};

const WHERE_LABEL: Record<string, string> = {
  field: "Content field",
  selector: "Page element",
  source: "Markup position",
  viewport: "Screen size",
  request: "Request",
  file: "File",
};

export interface FailurePanelProps {
  failure: StudioFailureVM;
  title?: string;
  /** Reassurance about what was kept (for example the last live page). */
  preservedNote?: string;
  retryLabel?: string;
  onRetry?: () => void | Promise<void>;
  inFlight?: boolean;
  /** A smaller version for the chat column. */
  compact?: boolean;
}

/**
 * One exact failure: what happened, where, why, and what to do next. The same
 * facts the server stored, so a support request can quote the reference.
 */
export function FailurePanel({
  failure,
  title = "The build did not finish",
  preservedNote,
  retryLabel = "Try again",
  onRetry,
  inFlight = false,
  compact = false,
}: FailurePanelProps) {
  const [copyState, setCopyState] = useState<"idle" | CopyJsonResult>("idle");
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const copy = async () => {
    const result = await copyJson(failureDiagnostics(failure));
    setCopyState(result);
    window.setTimeout(() => setCopyState("idle"), 1800);
  };

  const retry = async () => {
    if (!onRetry || retrying || inFlight) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (error) {
      setRetryError(error instanceof Error ? error.message : "Could not start again. Please try again.");
    } finally {
      setRetrying(false);
    }
  };

  const stage = STAGE_LABEL[failure.stage] ?? failure.stage;
  const owner = OWNER_LABEL[failure.owner] ?? failure.owner;

  return (
    <section
      className={`studio-failure${compact ? " studio-failure--compact" : ""}`}
      role="alert"
      aria-label="Build failure details"
    >
      <header className="studio-failure-head">
        <span className="studio-failure-icon" aria-hidden="true">!</span>
        <h3>{title}</h3>
      </header>

      <dl className="studio-failure-list">
        <div>
          <dt>What happened</dt>
          <dd>{failure.summary}</dd>
        </div>
        {failure.where.length > 0 ? (
          <div>
            <dt>Where</dt>
            <dd>
              <ul className="studio-failure-where">
                {failure.where.map((item, index) => (
                  <li key={`${item.kind}-${item.ref}-${index}`}>
                    <span className="studio-failure-kind">{WHERE_LABEL[item.kind] ?? item.kind}</span>
                    <code>{item.ref}</code>
                    {item.detail ? <span className="studio-failure-detail">{item.detail}</span> : null}
                  </li>
                ))}
              </ul>
              {failure.issueCount > failure.where.length ? (
                <span className="studio-failure-more">
                  and {failure.issueCount - failure.where.length} more in the diagnostics
                </span>
              ) : null}
            </dd>
          </div>
        ) : null}
        {failure.cause ? (
          <div>
            <dt>Why</dt>
            <dd>{failure.cause}</dd>
          </div>
        ) : null}
        {failure.expected || failure.found ? (
          <div className="studio-failure-compare">
            {failure.expected ? (
              <div>
                <dt>Expected</dt>
                <dd><code>{failure.expected}</code></dd>
              </div>
            ) : null}
            {failure.found ? (
              <div>
                <dt>Found</dt>
                <dd><code>{failure.found}</code></dd>
              </div>
            ) : null}
          </div>
        ) : null}
        {failure.action ? (
          <div>
            <dt>What you can do</dt>
            <dd>{failure.action}</dd>
          </div>
        ) : null}
      </dl>

      {preservedNote ? <p className="studio-failure-preserved">{preservedNote}</p> : null}
      <p className="studio-failure-meta">
        {stage} · {owner}
        {failure.reference ? <> · Reference <code>{failure.reference}</code></> : null}
      </p>
      {retryError ? <p className="studio-inline-error" role="alert">{retryError}</p> : null}

      <div className="studio-failure-actions">
        {onRetry && failure.retryable ? (
          <button
            type="button"
            className="btn-primary"
            disabled={retrying || inFlight}
            onClick={() => void retry()}
          >
            {retrying || inFlight ? "Starting…" : retryLabel}
          </button>
        ) : null}
        <button type="button" className="btn-secondary" onClick={() => void copy()}>
          {copyState === "copied" || copyState === "fallback" ? "Diagnostics copied" : "Copy diagnostics"}
        </button>
        {copyState === "unavailable" ? (
          <span role="status" className="studio-failure-detail">Clipboard unavailable.</span>
        ) : null}
      </div>
    </section>
  );
}
