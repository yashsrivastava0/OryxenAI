// Shared adapter vocabulary — each active stage adapter outputs this same
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
  code?: string;
  providerLabel?: string;
  operationLabel?: string;
  suboperation?: string;
  occurredAt?: string;
  issueCount?: number;
  issues?: Array<{ code: string; sourceId?: string; path?: string }>;
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
  const code = safeBoundedString(value.code, 80);
  if (code) result.code = code;
  if (providerLabel && SAFE_PROVIDER_LABELS.has(providerLabel)) result.providerLabel = providerLabel;
  const operationLabel = safeBoundedString(value.operation_label ?? value.operation);
  if (operationLabel) result.operationLabel = operationLabel;
  const suboperation = safeBoundedString(value.suboperation, 80);
  if (suboperation && ["plan_content", "write_pages", "integrate_content", "approval_readiness"].includes(suboperation)) {
    result.suboperation = suboperation;
  }
  const occurredAt = safeBoundedString(value.occurred_at, 40);
  if (occurredAt && !Number.isNaN(Date.parse(occurredAt))) result.occurredAt = occurredAt;
  if (typeof value.issue_count === "number" && Number.isInteger(value.issue_count) && value.issue_count >= 0) {
    result.issueCount = value.issue_count;
  }
  if (Array.isArray(value.issues)) {
    result.issues = value.issues.slice(0, 12).flatMap((entry) => {
      if (typeof entry !== "object" || entry === null) return [];
      const issue = entry as Record<string, unknown>;
      if (issue.code !== "coverage_path_unpopulated" && issue.code !== "invalid_output_field") return [];
      const sourceId = safeBoundedString(issue.source_id, 80);
      const path = safeBoundedString(issue.path, 160);
      if (!path || !/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*$/.test(path)) return [];
      if (issue.code === "coverage_path_unpopulated" && (!sourceId || !/^(fact|role|project|evidence)\/[A-Za-z0-9:_-]{1,64}$/.test(sourceId))) return [];
      return [{ code: issue.code, sourceId, path }];
    });
  }
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
