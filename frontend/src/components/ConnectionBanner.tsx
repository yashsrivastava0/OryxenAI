import type { ConnectionState } from "../app/store";
import { CopyDiagnosticsButton } from "./CopyDiagnosticsButton";
import type { FailureDiagnosticInput } from "../data/failure-diagnostics";

interface ConnectionBannerProps {
  state: ConnectionState;
  failure?: FailureDiagnosticInput | null;
}

// Persistent, non-modal — never a toast per poll (docs/Frontend/02 §4).
const COPY: Record<Exclude<ConnectionState, "confirmed">, string> = {
  checking: "Checking for updates…",
  stale: "The latest check did not complete. Showing the last confirmed state.",
  offline: "Reconnect to confirm the latest state.",
};

export function ConnectionBanner({ state, failure = null }: ConnectionBannerProps) {
  if (state === "confirmed") return null;
  return (
    <div className="connection-banner" role="status">
      {COPY[state]}
      {state !== "checking" ? <CopyDiagnosticsButton key={`${state}-${failure?.occurredAt ?? ""}`} failure={failure ?? { stage: "workspace", action: "refresh state", summary: COPY[state], code: state === "offline" ? "CONNECTION_OFFLINE" : "CONNECTION_STALE" }} /> : null}
    </div>
  );
}
