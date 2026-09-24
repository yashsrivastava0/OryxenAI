import type { JourneyStageId } from "../app/url-state";
import type { StageState } from "../data/adapters/types";

export type FullStageId = JourneyStageId;

export interface JourneyStageVM {
  id: FullStageId;
  ordinal: number;
  label: string;
  sublabel?: string;
  state: StageState;
  isSelectable: boolean;
}

export interface JourneyRailProps {
  journey: JourneyStageVM[];
  selectedStageId: JourneyStageId;
  onSelect: (stage: JourneyStageId) => void;
}

type RailState = "locked" | "current" | "complete" | "attention" | "default";

function railState(state: StageState): RailState {
  if (state === "locked") return "locked";
  if (state === "complete") return "complete";
  if (state === "attention" || state === "unsupported") return "attention";
  if (state === "working" || state === "input" || state === "review" || state === "available") return "current";
  return "default";
}

export function JourneyRail({ journey, selectedStageId, onSelect }: JourneyRailProps) {
  const allStages = journey;

  const currentStageIndex = allStages.findIndex((s) => s.id === selectedStageId);

  return (
    <nav className="journey-nav" aria-label="Portfolio journey">
      {/* Mobile compact selector matching 10-mobile-review.png */}
      <div className="journey-mobile-summary">
        <div className="journey-mobile-header">
          <span className="journey-mobile-kicker">CURRENT STAGE</span>
          <div className="journey-mobile-breadcrumbs" aria-hidden="true">
            <span>DISCOVER</span>
            <span className="breadcrumb-arrow">›</span>
            <span className="breadcrumb-active">CONTENT</span>
            <span className="breadcrumb-arrow">›</span>
            <span>APPROVE</span>
          </div>
        </div>

        <div className="journey-mobile-select-wrapper">
          <label className="visually-hidden" htmlFor="journey-stage-select">Current portfolio stage</label>
          <select
            id="journey-stage-select"
            value={String(selectedStageId)}
            aria-label="Current portfolio stage"
            onChange={(event) => {
              const next = (event.target as HTMLSelectElement).value as JourneyStageId;
              const stage = allStages.find((item) => item.id === next);
              if (stage?.isSelectable) onSelect(next);
            }}
          >
            {allStages.map((stage) => (
              <option key={stage.id} value={stage.id} disabled={!stage.isSelectable}>
                {stage.ordinal}. {stage.label}{stage.isSelectable ? "" : " (locked)"}
              </option>
            ))}
          </select>
          <span className="journey-mobile-chevron" aria-hidden="true">▾</span>
        </div>

        <div className="journey-mobile-track">
          <div
            className="journey-mobile-fill"
            style={{ width: `${((currentStageIndex + 1) / allStages.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Desktop horizontal stepper for the active journey. */}
      <ol className="journey-rail">
        {allStages.map((stage, index) => {
          const state = railState(stage.state);
          const isSelected = stage.id === selectedStageId;
          const isComplete = state === "complete";
          const isCurrent = isSelected || state === "current";

          return (
            <li
              key={stage.id}
              data-state={state}
              data-selected={isSelected ? "true" : "false"}
              className={`journey-step ${isSelected ? "selected" : ""} ${isCurrent ? "current" : ""} ${isComplete ? "complete" : ""}`}
            >
              {/* Connector line segment between steps */}
              {index > 0 && (
                <div
                  className={`journey-connector ${allStages[index - 1]?.state === "complete" ? "connector-complete" : ""} ${isSelected ? "connector-active" : ""}`}
                  aria-hidden="true"
                >
                  <span className="journey-connector-line" />
                </div>
              )}

              {stage.isSelectable ? (
                <button
                  type="button"
                  className={`journey-button ${isSelected ? "active" : ""}`}
                  aria-current={isSelected ? "step" : undefined}
                  onClick={() => onSelect(stage.id as JourneyStageId)}
                >
                  <span className="journey-node">
                    <span className="journey-ordinal">
                      {isComplete && !isSelected ? "✓" : stage.ordinal}
                    </span>
                  </span>
                  <span className="journey-meta">
                    <strong className="journey-label">{stage.label}</strong>
                  </span>
                </button>
              ) : (
                <div className="journey-locked-label">
                  <span className="journey-node">
                    <span className="journey-ordinal">{stage.ordinal}</span>
                  </span>
                  <span className="journey-meta">
                    <strong className="journey-label">{stage.label}</strong>
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// StageNavigator alias for cleaner semantic imports
export const StageNavigator = JourneyRail;
