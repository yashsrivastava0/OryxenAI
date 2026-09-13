import type { ComponentChildren } from "preact";

export interface ActionDockProps {
  primaryLabel: string;
  onPrimary?: () => void | Promise<void>;
  secondaryLabel?: string;
  onSecondary?: () => void | Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  note?: ComponentChildren;
  tone?: "default" | "attention";
}

/** The reserved action surface keeps review decisions visible without
 * duplicating buttons in each artifact's body. It does not own API policy. */
export function ActionDock({
  primaryLabel,
  onPrimary,
  secondaryLabel,
  onSecondary,
  disabled = false,
  busy = false,
  busyLabel = "Saving...",
  note,
  tone = "default",
}: ActionDockProps) {
  return (
    <div className={`action-dock action-dock--${tone}`} role="region" aria-label="Stage actions" aria-busy={busy}>
      <div className="action-dock-note">{note}</div>
      <div className="action-dock-actions">
        {secondaryLabel && onSecondary ? (
          <button
            type="button"
            className="btn-secondary action-dock-secondary"
            disabled={disabled || busy}
            onClick={() => void onSecondary()}
          >
            {secondaryLabel}
          </button>
        ) : null}
        {onPrimary ? (
          <button
            type="button"
            className="btn-primary action-dock-primary"
            disabled={disabled || busy}
            onClick={() => void onPrimary()}
          >
            {busy ? busyLabel : primaryLabel}
            {!busy && <span aria-hidden="true">→</span>}
          </button>
        ) : null}
      </div>
    </div>
  );
}
