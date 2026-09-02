import type { ConnectionState } from "../app/store";

interface ConnectionBannerProps {
  state: ConnectionState;
}

// Persistent, non-modal — never a toast per poll (docs/Frontend/02 §4).
const COPY: Record<Exclude<ConnectionState, "confirmed">, string> = {
  checking: "Checking for updates…",
  stale: "Offline. Showing the last confirmed state.",
  offline: "Reconnect to confirm the latest state.",
};

export function ConnectionBanner({ state }: ConnectionBannerProps) {
  if (state === "confirmed") return null;
  return (
    <div className="connection-banner" role="status">
      {COPY[state]}
    </div>
  );
}
