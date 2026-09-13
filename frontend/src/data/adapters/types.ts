// Shared adapter vocabulary — every stage adapter (discovery.ts now; content,
// design, preparation, generation in their owning phases) outputs this same
// shape. See docs/Frontend/05 §2.2 and §6.1 "Adapter rules shared by all
// stages": accept unknown, validate the minimal required envelope, never
// normalize an unrecognized required status to "complete" or "available".

import type { StageJobViewModel } from "./job";

export type StageState =
  | "locked"
  | "available"
  | "working"
  | "input"
  | "review"
  | "attention"
  | "complete"
  | "unsupported";

export interface StageViewModel {
  state: StageState;
  statusText: string;
  raw: unknown;
  job: StageJobViewModel | null;
  /** Complete persisted agent-owned output, never reconstructed from cards. */
  agentOutput: unknown | null;
  /** Server-authorized manual retry capability, when the stage exposes one. */
  retryAvailable?: boolean;
}

/**
 * Safe provider diagnostics emitted by the API's operation-failure envelope.
 * Provider aliases, response bodies, endpoints, and credential material are
 * intentionally not part of this client-side type.
 */
export interface SafeStageError {
  summary: string;
  providerLabel?: string;
  operationLabel?: string;
  retryAfterSeconds?: number;
  supportReference?: string;
  retryable?: boolean;
}

const SAFE_PROVIDER_LABELS = new Set([
  "Experiential Labs",
  "Google Gemini",
  "Configured model provider",
]);

function safeBoundedString(value: unknown, maximum = 160): string | undefined {
  return typeof value === "string" && value.trim() && value.length <= maximum
    ? value.trim()
    : undefined;
}

/** Read only the reviewed public error fields from a stage payload. */
export function readSafeStageError(raw: unknown, summary: string): SafeStageError {
  const value = typeof raw === "object" && raw !== null ? raw as Record<string, unknown> : {};
  const providerLabel = safeBoundedString(value.provider_label);
  const retryAfter = value.retry_after_seconds;
  const retryAfterSeconds =
    typeof retryAfter === "number" && Number.isFinite(retryAfter) && retryAfter >= 0 && retryAfter <= 86400
      ? retryAfter
      : undefined;
  const supportReference = safeBoundedString(value.support_reference, 64);
  const result: SafeStageError = { summary };
  if (providerLabel && SAFE_PROVIDER_LABELS.has(providerLabel)) result.providerLabel = providerLabel;
  const operationLabel = safeBoundedString(value.operation_label ?? value.operation);
  if (operationLabel) result.operationLabel = operationLabel;
  if (retryAfterSeconds !== undefined) result.retryAfterSeconds = retryAfterSeconds;
  if (supportReference && /^model-[a-f0-9]{12}$/i.test(supportReference)) {
    result.supportReference = supportReference;
  }
  if (value.retryable === true) result.retryable = true;
  return result;
}

export function readAgentOutput(raw: unknown): unknown | null {
  if (typeof raw !== "object" || raw === null || !("agent_output" in raw)) return null;
  const output = (raw as { agent_output?: unknown }).agent_output;
  return output === undefined ? null : output;
}
