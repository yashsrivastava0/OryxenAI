// Session-scoped idempotency key manager (docs/Frontend/05 §7.3).
// Persists unresolved keys in sessionStorage under a scoped key name.
// Cleans up on confirmed reconciliation or when explicitly reset. Never stores payloads.

function generateUUID(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function storageKey(sessionId: string, action: string): string {
  return `oryxen:idempotency:${sessionId}:${action}`;
}

export function getOrCreateIdempotencyKey(sessionId: string, action: string): string {
  if (typeof window === "undefined" || !window.sessionStorage) {
    return generateUUID();
  }
  const key = storageKey(sessionId, action);
  const existing = window.sessionStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const fresh = generateUUID();
  try {
    window.sessionStorage.setItem(key, fresh);
  } catch {
    // Graceful fallback if storage is restricted
  }
  return fresh;
}

export function clearIdempotencyKey(sessionId: string, action: string): void {
  if (typeof window === "undefined" || !window.sessionStorage) return;
  try {
    window.sessionStorage.removeItem(storageKey(sessionId, action));
  } catch {
    // Ignore storage errors
  }
}
