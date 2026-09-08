import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { copyJson, formatJson, type CopyJsonResult } from "../data/clipboard";
import type { StageState } from "../data/adapters/types";

export interface AgentOutputRailEntry {
  id: string;
  label: string;
  state: StageState;
  agentOutput: unknown | null;
  /** Set when the stage has a successful final response, even if the output
   * happens to be an empty object.  Keeping this separate from the rendered
   * cards prevents an intermediate question envelope being offered as final. */
  available?: boolean;
  stale?: boolean;
}

interface AgentOutputRailProps {
  entries: AgentOutputRailEntry[];
  activeStage: string;
}

function hasOutput(value: unknown): boolean {
  return typeof value === "object" && value !== null;
}

function outputAvailable(entry: AgentOutputRailEntry): boolean {
  return entry.available ?? hasOutput(entry.agentOutput);
}

function copyLabel(result: CopyJsonResult | null): string {
  if (result === "copied" || result === "fallback") return "JSON copied";
  if (result === "unavailable") return "Select JSON below";
  return "Copy full JSON";
}

export function AgentOutputRail({ entries, activeStage }: AgentOutputRailProps) {
  const firstAvailable = entries.find(outputAvailable);
  const [selectedId, setSelectedId] = useState(activeStage);
  const [copyState, setCopyState] = useState<{ id: string; result: CopyJsonResult } | null>(null);
  const copyTimerRef = useRef<number | null>(null);
  const entryIds = entries.map((entry) => entry.id).join("|");

  useEffect(() => () => {
    if (copyTimerRef.current !== null) window.clearTimeout(copyTimerRef.current);
  }, []);

  useEffect(() => {
    if (entryIds.split("|").includes(activeStage)) setSelectedId(activeStage);
  }, [activeStage, entryIds]);

  const selectedCandidate = entries.find((entry) => entry.id === selectedId);
  const selected = selectedCandidate && outputAvailable(selectedCandidate)
    ? selectedCandidate
    : firstAvailable ?? selectedCandidate ?? entries[0];
  const selectedJson = useMemo(
    () => (selected && outputAvailable(selected) ? formatJson(selected.agentOutput) : ""),
    [selected],
  );

  useEffect(() => {
    setCopyState(null);
  }, [selected?.id, selectedJson]);

  const handleCopy = async (entry: AgentOutputRailEntry) => {
    if (!outputAvailable(entry)) return;
    setSelectedId(entry.id);
    const result = await copyJson(formatJson(entry.agentOutput));
    setCopyState({ id: entry.id, result });
    if (copyTimerRef.current !== null) window.clearTimeout(copyTimerRef.current);
    copyTimerRef.current = window.setTimeout(() => {
      setCopyState((current) => (current?.id === entry.id ? null : current));
    }, 1800);
  };

  return (
    <aside className="agent-output-rail" aria-label="Complete agent outputs">
      <details className="agent-output-details" open>
        <summary className="agent-output-summary">
          <span>
            <span className="eyebrow">HANDOFF UTILITY</span>
            <strong>Agent output</strong>
          </span>
          <span className="agent-output-summary-note">Full JSON</span>
        </summary>

        <p className="agent-output-intro">
          Copy the complete persisted response from any finished stage. This utility never changes the portfolio.
        </p>

        <div className="agent-output-list">
          {entries.map((entry) => {
            const available = outputAvailable(entry);
            const selectedEntry = entry.id === selected?.id;
            return (
              <div
                key={entry.id}
                className={`agent-output-row ${selectedEntry ? "selected" : ""}`}
                data-state={entry.state}
              >
                <button
                  type="button"
                  className="agent-output-select"
                  disabled={!available}
                  aria-pressed={selectedEntry}
                  onClick={() => setSelectedId(entry.id)}
                >
                  <span className="agent-output-row-label">{entry.label}</span>
                  <span className="agent-output-row-state">
                    {!available
                      ? entry.state === "locked"
                        ? "Locked"
                        : "Not ready"
                      : entry.stale || entry.state === "working"
                        ? "Previous result"
                        : "Available"}
                  </span>
                </button>
                <button
                  type="button"
                  className="btn-quiet agent-output-copy"
                  disabled={!available}
                  aria-label={`Copy full JSON for ${entry.label}`}
                  onClick={() => void handleCopy(entry)}
                >
                  {copyState?.id === entry.id ? copyLabel(copyState.result) : "Copy JSON"}
                </button>
              </div>
            );
          })}
        </div>

        {selectedJson ? (
          <div className="agent-output-preview">
            <div className="agent-output-preview-header">
              <span>{selected?.label} response</span>
              <span className="agent-output-preview-hint">Read-only</span>
            </div>
            <textarea
              className="agent-output-json-field"
              readOnly
              spellcheck={false}
              value={selectedJson}
              aria-label={`${selected?.label ?? "Agent"} complete JSON response`}
              onFocus={(event) => event.currentTarget.select()}
            />
            {copyState?.id === selected?.id && copyState?.result === "unavailable" ? (
              <p className="agent-output-copy-status" role="status">
                Clipboard unavailable. Select the read-only JSON field and copy it manually.
              </p>
            ) : null}
          </div>
        ) : (
          <p className="agent-output-empty">A completed agent response will appear here after its review pass.</p>
        )}
      </details>
    </aside>
  );
}
