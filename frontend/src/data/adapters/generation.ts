// Code Generator adapter. The backend state is authoritative; this adapter
// only translates the durable session status and the promoted preview
// pointer into the shared product vocabulary. See
// src/oryxenai/agents/code_generator/session_schemas.py for the source
// contract (CodeGeneratorSessionStatus, CodeGeneratorSessionState).

import { selectStageJob } from "./job";
import {
  readAgentOutput,
  readSafeStageError,
  type SafeStageError,
  type StageState,
  type StageViewModel,
} from "./types";

export interface GenerationPreviewVM {
  url: string;
  routeIds: string[];
  routePaths: string[];
  verificationStatus?: "verified" | "unverified";
}

/** Human-friendly page names for the theater's route selector, derived by
 * pairing routeIds with routePaths positionally (both arrays are emitted
 * in the same route order by the backend — session_schemas.py's
 * ActivePreview). Falls back to the bare path when no id is available. */
export function friendlyRouteLabel(routeId: string, path: string): string {
  if (!routeId) return path || "/";
  if (routeId === "home") return "Home";
  return routeId
    .split(/[-_]/)
    .filter(Boolean)
    .map((word) => word[0]!.toUpperCase() + word.slice(1))
    .join(" ");
}

export interface GenerationViewModel extends StageViewModel {
  status: string;
  stale: boolean;
  staleReasons: string[];
  currentMilestone: string;
  preview: GenerationPreviewVM | null;
  candidatePreview?: GenerationPreviewVM | null;
  warnings?: string[];
  safeError: (SafeStageError & { retryable: boolean }) | null;
  retryAvailable?: boolean;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to generate the portfolio",
  queued: "Queued for generation",
  planning: "Planning the site",
  acquiring: "Acquiring resources",
  generating: "Building pages",
  verifying: "Testing viewports",
  ready: "Portfolio generated and verified",
  preview_pending: "Promoting preview",
  needs_attention: "Generation needs attention",
};

const WORKING_STATUSES = new Set([
  "queued",
  "planning",
  "acquiring",
  "generating",
  "verifying",
  "preview_pending",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function adaptPreview(value: unknown): GenerationPreviewVM | null {
  if (!isRecord(value) || typeof value.url !== "string" || !value.url) return null;
  return {
    url: value.url,
    routeIds: strings(value.route_ids),
    routePaths: strings(value.route_paths),
    verificationStatus: value.verification_status === "unverified" ? "unverified" : "verified",
  };
}

function warningMessages(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === "string") return [item];
    if (isRecord(item) && typeof item.message === "string") return [item.message];
    return [];
  });
}

function safeError(raw: Record<string, unknown>, failedJob: boolean): GenerationViewModel["safeError"] {
  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  if (!latestError && !failedJob) return null;
  return {
    ...readSafeStageError(
      latestError,
      typeof latestError?.message === "string"
        ? latestError.message
        : typeof latestError?.safe_user_summary === "string"
          ? latestError.safe_user_summary
          : "Code Generator could not complete.",
    ),
    retryable: latestError?.retryable === true,
  };
}

export function adaptCodeGenerator(
  raw: unknown,
  preparationApproved = false,
  jobs: unknown[] = [],
): GenerationViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATUS_TEXT)) {
    return {
      state: "unsupported",
      statusText: "Code Generator returned an unrecognised state. Refresh to continue.",
      raw,
      job: selectStageJob(jobs),
      agentOutput: null,
      status: "unsupported",
      stale: false,
      staleReasons: [],
      currentMilestone: "",
      preview: null,
      candidatePreview: null,
      warnings: [],
      safeError: null,
      retryAvailable: false,
    };
  }

  const status = raw.status;
  const hasActiveJobProjection = "active_job_id" in raw || "active_job_kind" in raw;
  const activeJobId = typeof raw.active_job_id === "string" ? raw.active_job_id : null;
  const activeJobKind = typeof raw.active_job_kind === "string" ? raw.active_job_kind : null;
  const coordinatorStage = isRecord(raw.progress) && typeof raw.progress.coordinator_stage === "string"
    ? raw.progress.coordinator_stage
    : "";
  const legacyJobKind = coordinatorStage ? `code_generator.${coordinatorStage}` : null;
  // `current_run_id` identifies the durable generation run, not a background
  // job. Prefer the additive active-job projection from the existing state
  // response so the UI never looks up a run UUID as if it were a job UUID.
  const job = hasActiveJobProjection
    ? activeJobId
      ? selectStageJob(jobs, activeJobId)
      : activeJobKind
        ? selectStageJob(jobs, null, activeJobKind)
        : null
    : selectStageJob(jobs, null, legacyJobKind);
  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  const stale = raw.stale === true;
  const preview = adaptPreview(raw.active_preview);
  const candidatePreview = adaptPreview(raw.candidate_preview);

  let state: StageState =
    WORKING_STATUSES.has(status)
      ? "working"
      : status === "ready"
        ? stale
          ? "attention"
          : "complete"
        : status === "needs_attention" || failedJob
          ? "attention"
          : status === "not_started"
            ? preparationApproved
              ? "available"
              : "locked"
            : "unsupported";

  if (failedJob) state = "attention";

  const statusText = stale
    ? "The build handoff changed since this portfolio was generated"
    : status === "not_started" && state === "locked"
      ? "Locked until Build Preparation is ready"
      : (STATUS_TEXT[status] ?? "Generating the portfolio");

  return {
    state,
    statusText,
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    status,
    stale,
    staleReasons: strings(raw.stale_reasons),
    currentMilestone: STATUS_TEXT[status] ?? statusText,
    preview,
    candidatePreview,
    warnings: warningMessages(raw.warnings ?? raw.advisories),
    safeError: safeError(raw, failedJob),
    retryAvailable: state === "attention" && !stale && raw.retry_available === true,
  };
}
