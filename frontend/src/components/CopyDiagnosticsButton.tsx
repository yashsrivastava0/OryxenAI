import { useState } from "preact/hooks";
import { copyJson, type CopyJsonResult } from "../data/clipboard";
import {
  formatFailureDiagnostics,
  type FailureDiagnosticInput,
} from "../data/failure-diagnostics";

export function CopyDiagnosticsButton({
  failure,
  className = "btn-secondary diagnostic-copy-button",
}: {
  failure: FailureDiagnosticInput;
  className?: string;
}) {
  const [copyState, setCopyState] = useState<"idle" | CopyJsonResult>("idle");
  const [displayedAt] = useState(() => new Date().toISOString());

  const copy = async () => {
    const result = await copyJson(
      formatFailureDiagnostics({ ...failure, occurredAt: failure.occurredAt ?? displayedAt }),
    );
    setCopyState(result);
    window.setTimeout(() => setCopyState("idle"), 1800);
  };

  return (
    <>
      <button type="button" className={className} onClick={() => void copy()}>
        {copyState === "copied" || copyState === "fallback" ? "Diagnostics copied" : "Copy diagnostics"}
      </button>
      {copyState === "unavailable" ? <span role="status">Clipboard unavailable.</span> : null}
    </>
  );
}
