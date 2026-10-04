import { getClientTraceId } from "./client-diagnostics";
import { ApiError } from "./errors";

export interface DiagnosticIssue {
  code: string;
  sourceId?: string;
  path?: string;
}

export interface FailureDiagnosticInput {
  stage: string;
  action: string;
  summary: string;
  occurredAt?: string | null;
  code?: string | null;
  status?: number | null;
  requestId?: string | null;
  jobId?: string | null;
  operation?: string | null;
  suboperation?: string | null;
  supportReference?: string | null;
  issueCount?: number | null;
  issues?: DiagnosticIssue[];
}

/** Capture the time and reviewed API metadata while the failure is handled. */
export function captureFailure(
  error: unknown,
  stage: string,
  action: string,
  fallback: string,
): FailureDiagnosticInput {
  const summary = error instanceof ApiError ? error.message : fallback;
  const base: FailureDiagnosticInput = {
    stage,
    action,
    summary,
    occurredAt: new Date().toISOString(),
  };
  if (error instanceof ApiError) {
    base.code = error.code;
    base.status = error.status;
    base.requestId = error.requestId;
    base.operation = error.operationLabel;
    base.supportReference = error.supportReference;
  }
  return base;
}

function pageLocation(): string | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const safe = new URLSearchParams();
  for (const key of ["stage", "view"]) {
    const value = params.get(key);
    if (value && /^[a-z_-]{1,40}$/i.test(value)) safe.set(key, value);
  }
  const search = safe.toString();
  return `${window.location.pathname}${search ? `?${search}` : ""}`;
}

/** One small, user-initiated report. Never includes input, output or auth data. */
export function formatFailureDiagnostics(input: FailureDiagnosticInput): string {
  const occurredAt = input.occurredAt && !Number.isNaN(Date.parse(input.occurredAt))
    ? input.occurredAt
    : new Date().toISOString();
  const issues = (input.issues ?? []).slice(0, 12).filter((issue) =>
    /^[A-Za-z0-9_]{1,80}$/.test(issue.code) &&
    (!issue.path || /^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*$/.test(issue.path)) &&
    (!issue.sourceId || /^(fact|role|project|evidence)\/[A-Za-z0-9:_-]{1,64}$/.test(issue.sourceId))
  );
  return JSON.stringify(
    {
      schema_version: 1,
      occurred_at: occurredAt,
      copied_at: new Date().toISOString(),
      page: pageLocation(),
      stage: input.stage,
      action: input.action,
      code: input.code ?? null,
      summary: input.summary,
      http_status: input.status ?? null,
      request_id: input.requestId ?? null,
      job_id: input.jobId ?? null,
      operation: input.operation ?? null,
      suboperation: input.suboperation ?? null,
      reference: input.supportReference ?? null,
      issue_count: input.issueCount ?? null,
      issues,
      client_trace_id: getClientTraceId(),
    },
    null,
    2,
  );
}
