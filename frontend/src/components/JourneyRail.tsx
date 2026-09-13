import type { JourneyStageId } from "../app/url-state";
import type { StageState } from "../data/adapters/types";

export type FullStageId = JourneyStageId | "prepare" | "generate" | "preview";

export interface JourneyStageVM {
  id: FullStageId;
  ordinal: number;
  label: string;
  sublabel?: string;
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

const DEFAULT_SUBLABELS: Record<string, string> = {
  discover: "UNDERSTAND YOUR STORY",
  content: "SHAPE NARRATIVE",
  design: "CRAFT PRESENTATION",
  prepare: "FINALIZE DETAILS",
  generate: "BUILD PORTFOLIO",
  preview: "REVIEW AND APPROVE",
};

export function JourneyRail({ journey, selectedStageId, onSelect }: JourneyRailProps) {
  // If the provided journey only has the 3 interactive stages (e.g. in existing unit tests),
  // extend it with the 3 descriptive locked pipeline stages for the complete 6-stage presentation.
  const allStages: JourneyStageVM[] = journey.length === 3
    ? [
        ...journey,
        { id: "prepare", ordinal: 4, label: "Prepare", sublabel: DEFAULT_SUBLABELS.prepare, state: "locked", isSelectable: false },
        { id: "generate", ordinal: 5, label: "Generate", sublabel: DEFAULT_SUBLABELS.generate, state: "locked", isSelectable: false },
        { id: "preview", ordinal: 6, label: "Preview", sublabel: DEFAULT_SUBLABELS.preview, state: "locked", isSelectable: false },
      ]
    : journey;

  const currentStageIndex = allStages.findIndex((s) => s.id === selectedStageId);
  const currentStage = allStages[currentStageIndex] ?? allStages[0];
  const activeOrdinal = String(currentStage ? currentStage.ordinal : 1).padStart(2, "0");
  const totalCount = String(allStages.length).padStart(2, "0");

  return (
    <nav className="journey-nav" aria-label="Portfolio journey">
      {/* Mobile compact progress bar */}
      <div className="journey-mobile-summary">
        <label className="journey-mobile-label" htmlFor="journey-stage-select">Current stage</label>
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
        <div className="journey-mobile-badge">
          <span className="journey-mobile-count">{activeOrdinal} / {totalCount}</span>
          <span className="journey-mobile-sep">·</span>
          <span className="journey-mobile-name">{currentStage?.label?.toUpperCase()}</span>
        </div>
        <div className="journey-mobile-track">
          <div
            className="journey-mobile-fill"
            style={{ width: `${((currentStageIndex + 1) / allStages.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Full 6-stage architectural rail */}
      <ol className="journey-rail">
        {allStages.map((stage, index) => {
          const state = railState(stage.state);
          const isSelected = stage.id === selectedStageId;
          const ordinal = String(stage.ordinal).padStart(2, "0");
          const sublabel = stage.sublabel ?? DEFAULT_SUBLABELS[stage.id] ?? "";
          const isComplete = state === "complete";
          const isCurrent = isSelected || state === "current";

          return (
            <li
              key={stage.id}
              data-state={state}
              data-selected={isSelected ? "true" : "false"}
              className={`journey-step ${isSelected ? "selected" : ""} ${isCurrent ? "current" : ""} ${isComplete ? "complete" : ""}`}
            >
              {/* Connector line segment */}
              {index > 0 && (
                <div className={`journey-connector ${allStages[index - 1]?.state === "complete" ? "connector-complete" : ""} ${isSelected ? "connector-active" : ""}`} aria-hidden="true">
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
                    <span className="journey-ordinal">{isComplete ? "✓" : ordinal}</span>
                  </span>
                  <span className="journey-meta">
                    <strong className="journey-label">{stage.label}</strong>
                    {sublabel && <small className="journey-sublabel">{sublabel}</small>}
                  </span>
                </button>
              ) : (
                <div className="journey-locked-label">
                  <span className="journey-node">
                    <span className="journey-ordinal">{ordinal}</span>
                  </span>
                  <span className="journey-meta">
                    <strong className="journey-label">{stage.label}</strong>
                    {sublabel && <small className="journey-sublabel">{sublabel}</small>}
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
