// Multi-tab state invalidation via BroadcastChannel. Messages carry only an
// opaque session ID and timestamp — never portfolio content or bearer
// tokens. See docs/Frontend/05 §11.3. Falls back to a no-op when
// BroadcastChannel is unavailable; normal focus/visibility polling
// (polling.ts) remains the complete fallback in that case.

const CHANNEL_NAME = "oryxenai.state-invalidated";

export interface InvalidationMessage {
  type: "state-invalidated";
  sessionId: string;
  at: number;
}

function isInvalidationMessage(value: unknown): value is InvalidationMessage {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as InvalidationMessage).type === "state-invalidated" &&
    typeof (value as InvalidationMessage).sessionId === "string" &&
    typeof (value as InvalidationMessage).at === "number"
  );
}

export interface InvalidationChannel {
  broadcast(sessionId: string): void;
  close(): void;
}

export function createInvalidationChannel(
  onInvalidate: (message: InvalidationMessage) => void,
  BroadcastChannelCtor: typeof BroadcastChannel | undefined = typeof BroadcastChannel !== "undefined" ? BroadcastChannel : undefined,
): InvalidationChannel {
  if (!BroadcastChannelCtor) {
    return { broadcast: () => {}, close: () => {} };
  }
  const channel = new BroadcastChannelCtor(CHANNEL_NAME);
  channel.onmessage = (event: MessageEvent) => {
    if (isInvalidationMessage(event.data)) onInvalidate(event.data);
  };
  return {
    broadcast(sessionId: string) {
      const message: InvalidationMessage = { type: "state-invalidated", sessionId, at: Date.now() };
      channel.postMessage(message);
    },
    close() {
      channel.close();
    },
  };
}
