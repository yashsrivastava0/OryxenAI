/**
 * Development-harness projection for the product Generate & Preview screen.
 *
 * This adapter is intentionally not used by the authenticated product API.
 * It lets the browser fixture render a real standalone Code Generator run
 * through the same GenerationStage as production, without inventing a
 * production session or bypassing preview-origin checks.
 */

export interface DevelopmentRunProjectionLike {
  run_id?: unknown;
  status?: unknown;
  coordinator_stage?: unknown;
  pipeline_contract_version?: unknown;
  trace_id?: unknown;
  current_attempt?: unknown;
  job_id?: unknown;
  generation_job_id?: unknown;
  verification_job_id?: unknown;
  plan_summary?: unknown;
  source_summary?: unknown;
  creative_direction?: unknown;
  candidate_preview?: unknown;
  active_preview?: unknown;
  terminal_failure?: unknown;
  issues?: unknown;
  advisories?: unknown;
}

export interface DevelopmentPreviewProjectionLike {
  active_preview?: unknown;
  candidate_preview?: unknown;
}

export interface DevelopmentGenerationProjection {
  raw: Record<string, unknown>;
  jobs: Array<Record<string, unknown>>;
}

const WORKING_STATUSES = new Set([
  "created",
  "queued",
  "admitting",
  "planning",
  "planned",
  "acquiring",
  "acquired",
  "generating_foundation",
  "generating_routes",
  "integrating",
  "source_ready",
  "building",
  "smoke_testing",
  "repairing",
  "preview_pending",
]);

export function mapDevelopmentStatus(status: unknown): string {
  switch (status) {
    case "acquiring":
    case "acquired":
      return "acquiring";
    case "generating_foundation":
    case "generating_routes":
    case "integrating":
    case "source_ready":
      return "generating";
    case "building":
    case "smoke_testing":
    case "repairing":
      return "verifying";
    case "ready":
      return "ready";
    case "preview_pending":
      return "preview_pending";
    case "needs_attention":
      return "needs_attention";
    case "created":
    case "queued":
    case "admitting":
    case "planning":
    case "planned":
    default:
      return "planning";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function nonEmptyString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stageForDevelopmentRun(run: DevelopmentRunProjectionLike): string {
  const explicit = nonEmptyString(run.coordinator_stage);
  if (explicit) return explicit;
  const status = nonEmptyString(run.status);
  return mapDevelopmentStatus(status) === "acquiring"
    ? "acquire"
    : mapDevelopmentStatus(status) === "generating"
      ? "generate"
      : mapDevelopmentStatus(status) === "verifying"
        ? "verify"
        : "plan";
}

function activeJobIdForStage(run: DevelopmentRunProjectionLike, stage: string): string {
  if (stage === "plan") return nonEmptyString(run.job_id);
  if (stage === "generate") return nonEmptyString(run.generation_job_id);
  if (stage === "verify" || stage === "preview") return nonEmptyString(run.verification_job_id);
  return "";
}

function activeJobKindForStage(run: DevelopmentRunProjectionLike, stage: string): string {
  const pipeline = nonEmptyString(run.pipeline_contract_version);
  const prefix = pipeline.includes("v5") ? "code_generator.v5." : "code_generator.";
  if (stage === "acquire") return `${prefix}acquire`;
  if (stage === "generate") return `${prefix}generate`;
  if (stage === "verify" || stage === "preview") return `${prefix}verify_and_preview`;
  return `${prefix}plan`;
}

function terminalFailureError(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) return null;
  const code = nonEmptyString(value.terminal_code) || nonEmptyString(value.code);
  const message =
    nonEmptyString(value.safe_user_summary) ||
    nonEmptyString(value.message) ||
    "Code Generator could not complete.";
  return code || message ? { code, message, retryable: false } : null;
}

function syntheticJob(
  run: DevelopmentRunProjectionLike,
  status: string,
  activeJobId: string,
  activeJobKind: string,
): Record<string, unknown>[] {
  if (!activeJobId) return [];
  const terminal = status === "needs_attention";
  return [
    {
      id: activeJobId,
      kind: activeJobKind,
      status: terminal ? "failed" : status === "ready" ? "succeeded" : "running",
      attempt: numberOr(run.current_attempt, 1),
      max_attempts: 1,
      error: terminalFailureError(run.terminal_failure),
    },
  ];
}

export function adaptDevelopmentRun(
  runValue: unknown,
  previewValue: unknown = null,
): DevelopmentGenerationProjection {
  const run: DevelopmentRunProjectionLike = isRecord(runValue) ? runValue : {};
  const preview: DevelopmentPreviewProjectionLike = isRecord(previewValue) ? previewValue : {};
  const status = mapDevelopmentStatus(run.status);
  const stage = stageForDevelopmentRun(run);
  const activeJobId = activeJobIdForStage(run, stage);
  const activeJobKind = activeJobId ? activeJobKindForStage(run, stage) : "";
  const activePreview = preview.active_preview ?? run.active_preview ?? null;
  const candidatePreview = preview.candidate_preview ?? run.candidate_preview ?? null;

  const raw: Record<string, unknown> = {
    status,
    active_job_id: activeJobId || null,
    active_job_kind: activeJobKind || null,
    trace_id: nonEmptyString(run.trace_id),
    latest_error: run.terminal_failure ?? null,
    issues: Array.isArray(run.issues) ? run.issues : [],
    warnings: Array.isArray(run.advisories) ? run.advisories : [],
    creative_direction: isRecord(run.creative_direction) ? run.creative_direction : {},
    active_preview: activePreview,
    candidate_preview: candidatePreview,
    retry_available: false,
    progress: {
      coordinator_stage: stage,
      current_attempt: numberOr(run.current_attempt, 1),
      plan_summary: isRecord(run.plan_summary) ? run.plan_summary : {},
      source_summary: isRecord(run.source_summary) ? run.source_summary : {},
    },
  };

  const jobs = syntheticJob(run, status, activeJobId, activeJobKind);
  // Keep the helper's status vocabulary close to the source contract so a
  // future unsupported source status cannot silently look complete.
  if (!WORKING_STATUSES.has(nonEmptyString(run.status)) && status === "planning") {
    raw.status = "planning";
  }
  return { raw, jobs };
}
