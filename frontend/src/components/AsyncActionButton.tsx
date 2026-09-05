import { useState } from "preact/hooks";

export interface AsyncActionButtonProps {
  label: string;
  busyLabel: string;
  onAction: () => Promise<void>;
  disabled?: boolean;
  inFlight?: boolean;
}

/**
 * Event handlers do not automatically surface rejected promises in Preact.
 * Keep stage-start failures in the stage surface so a user can retry without
 * losing the durable state or being left with an unhandled rejection.
 */
export function AsyncActionButton({
  label,
  busyLabel,
  onAction,
  disabled = false,
  inFlight = false,
}: AsyncActionButtonProps) {
  const [localInFlight, setLocalInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = inFlight || localInFlight;

  const handleClick = async () => {
    if (disabled || busy) return;
    setLocalInFlight(true);
    setError(null);
    try {
      await onAction();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The stage could not be started. Try again.");
    } finally {
      setLocalInFlight(false);
    }
  };

  return (
    <div className="async-action-group">
      <button
        type="button"
        className="btn-primary"
        disabled={disabled || busy}
        onClick={() => void handleClick()}
      >
        {busy ? busyLabel : label}
      </button>
      {error ? <p className="start-error" role="alert">{error}</p> : null}
    </div>
  );
}
