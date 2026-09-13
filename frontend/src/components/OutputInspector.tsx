import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { copyJson, formatJson, type CopyJsonResult } from "../data/clipboard";
import type { StageState } from "../data/adapters/types";

export interface OutputInspectorEntry {
  id: string;
  label: string;
  state: StageState;
  agentOutput: unknown | null;
  available?: boolean;
  stale?: boolean;
}

interface OutputInspectorProps {
  entries: OutputInspectorEntry[];
  activeStage: string;
  enabled: boolean;
}

function hasOutput(value: unknown): boolean {
  return typeof value === "object" && value !== null;
}

function isAvailable(entry: OutputInspectorEntry): boolean {
  return entry.available ?? hasOutput(entry.agentOutput);
}

function copyLabel(result: CopyJsonResult | null): string {
  if (result === "copied" || result === "fallback") return "Copied to clipboard!";
  if (result === "unavailable") return "Select text below";
  return "Copy output";
}

/**
 * Developer-only read-only slide-over output inspector drawer matching 11-output-inspector.png.
 * Fresh stage selections never silently fall back to an older stage's output.
 */
export function OutputInspector({ entries, activeStage, enabled }: OutputInspectorProps) {
  const [open, setOpen] = useState(false);
  const [copyState, setCopyState] = useState<{ id: string; result: CopyJsonResult } | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLElement | null>(null);
  const entry = entries.find((candidate) => candidate.id === activeStage) ?? null;
  const available = Boolean(entry && isAvailable(entry));
  const json = useMemo(() => (available && entry ? formatJson(entry.agentOutput) : ""), [available, entry]);

  useEffect(() => {
    setOpen(false);
    setCopyState(null);
  }, [activeStage]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (event.key !== "Tab" || !drawerRef.current) return;
      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
        "button:not(:disabled), textarea, [href], select",
      );
      if (!focusable.length) return;
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    window.setTimeout(() => drawerRef.current?.querySelector<HTMLElement>("button, textarea")?.focus(), 0);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [open]);

  if (!enabled) return null;

  const copy = async () => {
    if (!entry || !available) return;
    const result = await copyJson(json);
    setCopyState({ id: entry.id, result });
  };

  return (
    <>
      {/* Visual floating / edge trigger button matching 01-shell-overview.png */}
      <button
        ref={triggerRef}
        type="button"
        className={`output-inspector-edge-trigger ${open ? "is-open" : ""}`}
        aria-expanded={open}
        aria-controls="output-inspector-drawer"
        aria-label="Inspector toggle"
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="inspector-trigger-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="4" y1="21" x2="4" y2="14" />
            <line x1="4" y1="10" x2="4" y2="3" />
            <line x1="12" y1="21" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12" y2="3" />
            <line x1="20" y1="21" x2="20" y2="16" />
            <line x1="20" y1="12" x2="20" y2="3" />
            <line x1="1" y1="14" x2="7" y2="14" />
            <line x1="9" y1="8" x2="15" y2="8" />
            <line x1="17" y1="16" x2="23" y2="16" />
          </svg>
        </span>
        <span className="inspector-trigger-label">
          {open ? "INSPECTOR OPEN" : "INSPECTOR CLOSED"}
        </span>
      </button>

      {open ? (
        <div
          className="output-inspector-backdrop"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setOpen(false);
              triggerRef.current?.focus();
            }
          }}
        >
          <aside
            id="output-inspector-drawer"
            ref={drawerRef}
            className="output-inspector-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="output-inspector-title"
          >
            <header className="output-inspector-header">
              <div className="inspector-title-row">
                <h2 id="output-inspector-title">Output Inspector</h2>
                <span className="inspector-badge">Developer only</span>
              </div>
              <button
                type="button"
                className="btn-quiet inspector-close-btn"
                aria-label="Close Output Inspector"
                onClick={() => {
                  setOpen(false);
                  triggerRef.current?.focus();
                }}
              >
                ✕
              </button>
            </header>

            <p className="output-inspector-intro">
              Inspect the selected stage output. Read-only.
            </p>

            {entry ? (
              <section className="output-inspector-section">
                <span className="inspector-section-label">Selected stage</span>
                <strong className="inspector-stage-name">{entry.label}</strong>
                <p className="inspector-stage-desc">
                  Generates the portfolio artifact for this session.
                </p>

                <div className="inspector-status-block">
                  <span className="inspector-section-label">Status</span>
                  <div className="inspector-status-pill">
                    <span className="status-dot status-dot--complete" aria-hidden="true">●</span>
                    <span>{entry.stale ? "Previous result" : entry.state.toUpperCase()}</span>
                  </div>
                </div>
              </section>
            ) : null}

            {json ? (
              <div className="inspector-code-section">
                <div className="inspector-code-header">
                  <span className="inspector-section-label">Output (JSON)</span>
                  <span className="code-format-tag">JSON</span>
                </div>
                <div className="inspector-code-wrapper">
                  <textarea
                    className="agent-output-json-field"
                    readOnly
                    spellcheck={false}
                    value={json}
                    aria-label="Selected stage JSON"
                    onFocus={(event) => event.currentTarget.select()}
                  />
                </div>
                <button
                  type="button"
                  className="btn-primary btn-cobalt inspector-copy-btn"
                  onClick={() => void copy()}
                >
                  <span aria-hidden="true">📋</span>
                  <span>{copyState && copyState.id === entry?.id ? copyLabel(copyState.result) : "Copy output"}</span>
                </button>
              </div>
            ) : (
              <div className="output-inspector-empty">
                <p>The selected stage has no completed output yet.</p>
              </div>
            )}
          </aside>
        </div>
      ) : null}
    </>
  );
}
