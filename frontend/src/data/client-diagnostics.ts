import { safeSessionStorage } from "./safe-storage";

// This trace is intentionally metadata-only. It is designed to accompany a
// user report, not to become a second copy of the resume or auth payload.
const STORAGE_KEY = "oryxenai.client-diagnostics.v1";
const MAX_EVENTS = 160;
const MAX_PENDING = 40;
type DiagnosticScalar = string | number | boolean | null;
export type DiagnosticMeta = Record<string, DiagnosticScalar | DiagnosticScalar[]>;

export interface ClientDiagnosticEventInput {
  kind: string;
  route?: string;
  method?: string;
  status?: number;
  duration_ms?: number;
  code?: string;
  stage?: string;
  state?: string;
  action?: string;
  input_characters?: number;
  message?: string;
  meta?: Record<string, unknown>;
}

export interface ClientDiagnosticEvent extends ClientDiagnosticEventInput {
  at: string;
  meta?: DiagnosticMeta;
}

interface StoredTrace {
  trace_id: string;
  events: ClientDiagnosticEvent[];
}

let flushTimer: number | null = null;
let flushInFlight = false;
let pendingEvents: ClientDiagnosticEvent[] = [];
let diagnosticsEndpointUnavailable = false;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function newTraceId(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi?.randomUUID) return cryptoApi.randomUUID();
  return `trace-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function readTrace(): StoredTrace {
  const raw = safeSessionStorage.getItem(STORAGE_KEY);
  if (raw) {
    try {
      const parsed: unknown = JSON.parse(raw);
      if (
        isRecord(parsed) &&
        typeof parsed.trace_id === "string" &&
        Array.isArray(parsed.events)
      ) {
        return {
          trace_id: parsed.trace_id,
          events: parsed.events.filter(isRecord).slice(-MAX_EVENTS) as unknown as ClientDiagnosticEvent[],
        };
      }
    } catch {
      // Corrupt or unavailable storage should never block the product.
    }
  }
  return { trace_id: newTraceId(), events: [] };
}

let trace = readTrace();

function persistTrace(): void {
  try {
    safeSessionStorage.setItem(STORAGE_KEY, JSON.stringify(trace));
  } catch {
    // Diagnostics are best-effort and must not affect the workflow.
  }
}

function isLocalBrowser(): boolean {
  if (typeof window === "undefined") return false;
  return ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname);
}

function safeRoute(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    return new URL(value, typeof window === "undefined" ? "http://localhost" : window.location.origin).pathname.slice(0, 200);
  } catch {
    return value.split(/[?#]/, 1)[0]?.slice(0, 200);
  }
}

function safeEvent(input: ClientDiagnosticEventInput): ClientDiagnosticEvent {
  const event: ClientDiagnosticEvent = {
    at: new Date().toISOString(),
    kind: input.kind.slice(0, 64),
  };
  const route = safeRoute(input.route);
  if (route) event.route = route;
  if (input.method) event.method = input.method.slice(0, 10).toUpperCase();
  if (typeof input.status === "number" && Number.isFinite(input.status)) {
    event.status = Math.max(0, Math.min(599, Math.round(input.status)));
  }
  if (typeof input.duration_ms === "number" && Number.isFinite(input.duration_ms)) {
    event.duration_ms = Math.max(0, Math.min(600000, Math.round(input.duration_ms)));
  }
  for (const key of ["code", "stage", "state", "action"] as const) {
    const value = input[key];
    if (value) event[key] = value.slice(0, 80);
  }
  if (input.message) event.message = input.message.slice(0, 200);
  if (typeof input.input_characters === "number" && Number.isFinite(input.input_characters)) {
    event.input_characters = Math.max(0, Math.min(300000, Math.round(input.input_characters)));
  }
  if (input.meta && isRecord(input.meta)) {
    const meta: DiagnosticMeta = {};
    for (const [key, value] of Object.entries(input.meta).slice(0, 32)) {
      const safeKey = key.slice(0, 80);
      if (typeof value === "string" && value.length <= 200) meta[safeKey] = value;
      else if (typeof value === "number" && Number.isFinite(value)) meta[safeKey] = value;
      else if (typeof value === "boolean" || value === null) meta[safeKey] = value;
      else if (Array.isArray(value)) {
        const values = value
          .filter(
            (item): item is DiagnosticScalar =>
              item === null || typeof item === "string" || typeof item === "number" || typeof item === "boolean",
          )
          .slice(0, 8);
        if (values.length) meta[safeKey] = values;
      }
    }
    if (Object.keys(meta).length) event.meta = meta;
  }
  return event;
}

function scheduleFlush(): void {
  if (!isLocalBrowser() || diagnosticsEndpointUnavailable || flushTimer !== null) return;
  flushTimer = window.setTimeout(() => {
    flushTimer = null;
    void flushPendingEvents();
  }, 350);
}

async function flushPendingEvents(): Promise<void> {
  if (!isLocalBrowser() || diagnosticsEndpointUnavailable || flushInFlight || pendingEvents.length === 0) return;
  flushInFlight = true;
  const batch = pendingEvents.splice(0, MAX_PENDING);
  try {
    const response = await window.fetch("/api/v1/client-diagnostics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_run_id: trace.trace_id, events: batch }),
      keepalive: true,
    });
    if (response.status === 404 || response.status === 405) {
      // Older local API processes may not have the optional diagnostics route.
      // Keep the local packet downloadable, but never create a 404 request loop.
      diagnosticsEndpointUnavailable = true;
      pendingEvents = [];
    } else if (!response.ok) {
      throw new Error(`client diagnostics returned ${response.status}`);
    }
  } catch {
    // Keep a bounded retry queue. A missing endpoint or offline browser is
    // expected in production and must not create an error loop.
    pendingEvents = [...batch, ...pendingEvents].slice(-MAX_PENDING);
  } finally {
    flushInFlight = false;
    if (pendingEvents.length > 0) scheduleFlush();
  }
}

export function getClientTraceId(): string {
  return trace.trace_id;
}

export function recordClientEvent(input: ClientDiagnosticEventInput): void {
  const event = safeEvent(input);
  trace.events = [...trace.events, event].slice(-MAX_EVENTS);
  pendingEvents = [...pendingEvents, event].slice(-MAX_PENDING);
  persistTrace();
  scheduleFlush();
}

export function downloadClientDiagnostics(): void {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  const blob = new Blob(
    [JSON.stringify(buildClientDiagnosticsPacket(), null, 2)],
    { type: "application/json" },
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `oryxenai-client-trace-${trace.trace_id.slice(0, 8)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function buildClientDiagnosticsPacket(): Record<string, unknown> {
  return {
    schema_version: 2,
    trace_id: trace.trace_id,
    exported_at: new Date().toISOString(),
    page: typeof window === "undefined" ? null : window.location.pathname,
    user_agent: typeof navigator === "undefined" ? null : navigator.userAgent.slice(0, 240),
    events: trace.events,
  };
}

export async function copyClientDiagnostics(): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.clipboard) return false;
  try {
    await navigator.clipboard.writeText(JSON.stringify(buildClientDiagnosticsPacket(), null, 2));
    return true;
  } catch {
    return false;
  }
}

function installRuntimeDiagnostics(): void {
  if (typeof window === "undefined") return;
  window.addEventListener("error", (event) => {
    recordClientEvent({ kind: "runtime_error", message: event.message || "window error" });
  });
  window.addEventListener("unhandledrejection", () => {
    recordClientEvent({ kind: "runtime_error", message: "unhandled promise rejection" });
  });
}

installRuntimeDiagnostics();
