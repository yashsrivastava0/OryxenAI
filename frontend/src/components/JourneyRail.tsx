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
export function JourneyRail({ journey, onSelect }: JourneyRailProps) {
  return (
    <ol className="journey-rail" aria-label="Portfolio journey">
      {journey.map((stage) => {
        const state = railState(stage.state);
        const ordinal = String(stage.ordinal).padStart(2, "0");
        return (
          <li key={stage.id} data-state={state}>
            {stage.isSelectable ? (
              <button type="button" onClick={() => onSelect(stage.id)}>
                <span className="journey-ordinal">{ordinal}</span> {stage.label}
              </button>
            ) : (
              <span>
                <span className="journey-ordinal">{ordinal}</span> {stage.label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
