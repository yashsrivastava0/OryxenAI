import { useState } from "preact/hooks";
import { copyClientDiagnostics, downloadClientDiagnostics } from "../data/client-diagnostics";

interface ClientTraceNoticeProps {
  traceId: string;
}

/** Local-only handoff for reproducing frontend issues without sharing input. */
export function ClientTraceNotice({ traceId }: ClientTraceNoticeProps) {
  const [copied, setCopied] = useState(false);

  const copyTrace = async () => {
    const didCopy = await copyClientDiagnostics();
    setCopied(didCopy);
    if (didCopy) window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <aside className="client-trace-notice" data-client-trace-id={traceId} aria-label="Local test trace">
      <span><strong>Test trace</strong> <code>{traceId.slice(0, 8)}</code> · safe request, job, and error timeline</span>
      <div className="client-trace-actions">
        <button type="button" className="btn-quiet" onClick={() => void copyTrace()}>
          {copied ? "Copied" : "Copy trace"}
        </button>
        <button type="button" className="btn-quiet" onClick={downloadClientDiagnostics}>Download trace</button>
      </div>
    </aside>
  );
}
