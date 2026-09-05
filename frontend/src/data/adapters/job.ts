// Safe, deliberately small job projection used to explain queued/running
// states in the browser. It never carries job payloads or worker lock data.

export interface StageJobViewModel {
  id: string;
  kind: string;
  status: string;
  attempt: number;
  maxAttempts: number;
  createdAt: string | null;
  startedAt: string | null;
  heartbeatAt: string | null;
  finishedAt: string | null;
  error: { code: string; message: string } | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function safeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function safeString(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function adaptJob(raw: unknown): StageJobViewModel | null {
  if (!isRecord(raw) || typeof raw.id !== "string" || typeof raw.status !== "string") return null;
  const rawError = isRecord(raw.error) ? raw.error : null;
  return {
    id: raw.id,
    kind: typeof raw.kind === "string" ? raw.kind : "",
    status: raw.status,
    attempt: safeNumber(raw.attempt),
    maxAttempts: safeNumber(raw.max_attempts),
    createdAt: safeString(raw.created_at),
    startedAt: safeString(raw.started_at),
    heartbeatAt: safeString(raw.heartbeat_at),
    finishedAt: safeString(raw.finished_at),
    error:
      rawError && typeof rawError.code === "string" && typeof rawError.message === "string"
        ? { code: rawError.code, message: rawError.message }
        : null,
  };
}

export function selectStageJob(rawJobs: unknown, jobId?: string | null): StageJobViewModel | null {
  const jobs = Array.isArray(rawJobs)
    ? rawJobs.map(adaptJob).filter((job): job is StageJobViewModel => job !== null)
    : [];
  if (jobId) return jobs.find((job) => job.id === jobId) ?? null;
  return jobs.at(-1) ?? null;
}
