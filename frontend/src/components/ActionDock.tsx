import type { ComponentChildren } from "preact";

export interface ActionDockProps {
  primaryLabel?: string;
  onPrimary?: () => void | Promise<void>;
  secondaryLabel?: string;
  onSecondary?: () => void | Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  note?: ComponentChildren;
  subtext?: ComponentChildren;
  tone?: "default" | "attention";
  children?: ComponentChildren;
  className?: string;
}

/**
 * The reserved ActionDock surface keeps review decisions visible without
 * duplicating buttons inside each artifact's body.
 * Fixed/sticky at the viewport bottom with glassmorphism backdrop.
 */
export function ActionDock({
  primaryLabel,
  onPrimary,
  secondaryLabel,
  onSecondary,
  disabled = false,
  busy = false,
  busyLabel = "Saving…",
  note,
  subtext,
  tone = "default",
  children,
  className = "",
}: ActionDockProps) {
  return (
    <div
      className={`action-dock action-dock--${tone} ${className}`}
      role="region"
      aria-label="Stage actions"
      aria-busy={busy}
    >
      <div className="action-dock-content">
        <div className="action-dock-left">
          {note ? (
            <div className="action-dock-note">{note}</div>
          ) : (
            <div className="action-dock-brand-note">
              <span className="dock-brand-name">OryxenAI</span>
              <span className="dock-brand-sep" aria-hidden="true">|</span>
              <span className="dock-brand-motto">CREATIVE WORKFLOWS FOR REAL PROGRESS</span>
            </div>
          )}
        </div>

        <div className="action-dock-right">
          <div className="action-dock-buttons">
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

            {children}

            {primaryLabel && onPrimary ? (
              <div className="dock-primary-wrapper">
                <button
                  type="button"
                  className="btn-primary btn-cobalt action-dock-primary"
                  disabled={disabled || busy}
                  onClick={() => void onPrimary()}
                >
                  <span>{busy ? busyLabel : primaryLabel}</span>
                  {!busy && <span className="dock-arrow" aria-hidden="true">→</span>}
                </button>
                {subtext && <span className="dock-subtext">{subtext}</span>}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
