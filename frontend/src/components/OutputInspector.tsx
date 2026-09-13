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
  if (result === "copied" || result === "fallback") return "Copied";
  if (result === "unavailable") return "Select JSON below";
  return "Copy JSON";
}

/** Developer-only read-only output drawer. Fresh stage selections never
 * silently fall back to an older stage's output. */
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
      <button
        ref={triggerRef}
        type="button"
        className="output-inspector-trigger"
        aria-expanded={open}
        aria-controls="output-inspector-drawer"
        onClick={() => setOpen(true)}
      >
        <span aria-hidden="true">☷</span>
        <span>Inspector</span>
        <small>Developer only</small>
      </button>
      {open ? (
        <div className="output-inspector-backdrop" onClick={(event) => {
          if (event.target === event.currentTarget) {
            setOpen(false);
            triggerRef.current?.focus();
          }
        }}>
          <aside
            id="output-inspector-drawer"
            ref={drawerRef}
            className="output-inspector-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="output-inspector-title"
          >
            <header className="output-inspector-header">
              <div>
                <p className="eyebrow">DEVELOPER ONLY</p>
                <h2 id="output-inspector-title">Output Inspector</h2>
              </div>
              <button type="button" className="btn-quiet" aria-label="Close Output Inspector" onClick={() => {
                setOpen(false);
                triggerRef.current?.focus();
              }}>×</button>
            </header>
            <p className="output-inspector-intro">Read-only persisted output for the selected stage.</p>
            {entry ? (
              <section className="output-inspector-selection">
                <span className="metadata-label">Selected stage</span>
                <strong>{entry.label}</strong>
                <span className="output-inspector-state">{entry.stale ? "Previous result" : entry.state}</span>
              </section>
            ) : null}
            {json ? (
              <>
                <textarea className="agent-output-json-field" readOnly spellcheck={false} value={json} aria-label="Selected stage JSON" onFocus={(event) => event.currentTarget.select()} />
                <button type="button" className="btn-primary" onClick={() => void copy()}>
                  {copyState && copyState.id === entry?.id ? copyLabel(copyState.result) : "Copy output"}
                </button>
              </>
            ) : (
              <p className="output-inspector-empty">The selected stage has no completed output yet.</p>
            )}
          </aside>
        </div>
      ) : null}
    </>
  );
}
