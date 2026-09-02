import type { JourneyStageId } from "../app/url-state";
import type { StageState } from "../data/adapters/types";

export interface JourneyStageVM {
  id: JourneyStageId;
  ordinal: number;
  label: string;
  state: StageState;
  isSelectable: boolean;
}

interface JourneyRailProps {
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

// Completed and current stages are selectable; a locked future stage is
// descriptive, never a fake disabled button (docs/Frontend/01 §5, 05 §8.2).
export function JourneyRail({ journey, selectedStageId, onSelect }: JourneyRailProps) {
  return (
    <nav className="journey-nav" aria-label="Portfolio journey">
      <ol className="journey-rail">
        {journey.map((stage) => {
          const state = railState(stage.state);
          const isSelected = stage.id === selectedStageId;
          const ordinal = String(stage.ordinal).padStart(2, "0");
          return (
            <li
              key={stage.id}
              data-state={state}
              data-selected={isSelected ? "true" : "false"}
              className={`journey-step ${isSelected ? "selected" : ""}`}
            >
              {stage.isSelectable ? (
                <button
                  type="button"
                  className={`journey-button ${isSelected ? "active" : ""}`}
                  aria-current={isSelected ? "step" : undefined}
                  onClick={() => onSelect(stage.id)}
                >
                  <span className="journey-ordinal">{ordinal}</span>
                  <span className="journey-label">{stage.label}</span>
                  {state === "complete" && <span className="journey-check" aria-hidden="true">✓</span>}
                </button>
              ) : (
                <span className="journey-locked-label">
                  <span className="journey-ordinal">{ordinal}</span>
                  <span className="journey-label">{stage.label}</span>
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
