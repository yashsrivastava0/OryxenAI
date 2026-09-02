import { LivingDraftMark } from "./LivingDraftMark";

export interface HandoffPanelProps {
  completedStageName: string;
  nextStageName: string;
  summary: string;
  nextDescription: string;
  actionLabel: string;
  onContinue: () => void | Promise<void>;
  inFlight?: boolean;
  disabled?: boolean;
}

export function HandoffPanel({
  completedStageName,
  nextStageName,
  summary,
  nextDescription,
  actionLabel,
  onContinue,
  inFlight = false,
  disabled = false,
}: HandoffPanelProps) {
  return (
    <div className="handoff-panel" role="region" aria-label={`Continue to ${nextStageName}`}>
      <div className="handoff-badge">
        <LivingDraftMark active={false} />
        <span className="handoff-badge-label">{completedStageName} Approved</span>
      </div>

      <h3 className="handoff-title">Ready for {nextStageName}</h3>
      <p className="handoff-summary">{summary}</p>

      <div className="handoff-next-card">
        <p className="handoff-next-label">Next step: {nextStageName}</p>
        <p className="handoff-next-desc">{nextDescription}</p>
      </div>

      <div className="handoff-actions">
        <button
          type="button"
          className="btn-primary handoff-button"
          disabled={inFlight || disabled}
          onClick={() => onContinue()}
        >
          {inFlight ? "Continuing..." : actionLabel}
        </button>
      </div>

      <p className="handoff-note">
        <small>Stages advance only when you click to proceed. Work never begins automatically.</small>
      </p>
    </div>
  );
}
