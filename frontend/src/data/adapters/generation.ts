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
  coordinatorStage?: string;
  currentAttempt?: number;
  traceId?: string;
  activeJobId?: string | null;
  activeJobKind?: string | null;
  issues?: string[];
  latestError?: Record<string, unknown> | null;
  projectTitle?: string;
  projectSummary?: string;
  preview: GenerationPreviewVM | null;
  candidatePreview?: GenerationPreviewVM | null;
  warnings?: string[];
  safeError: (SafeStageError & { retryable: boolean }) | null;
  retryAvailable?: boolean;
  estimatedRemainingMs?: number;
  estimatedTotalMs?: number;
  estimateSource?: "configured_budget" | "observed_and_budget";
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

interface StageEstimateVM {
  estimatedRemainingMs?: number;
  estimatedTotalMs?: number;
  estimateSource?: "configured_budget" | "observed_and_budget";
}

const EMPTY_STAGE_ESTIMATE: StageEstimateVM = {
  estimatedRemainingMs: undefined,
  estimatedTotalMs: undefined,
  estimateSource: undefined,
};

function adaptStageEstimate(value: unknown): StageEstimateVM {
  if (!isRecord(value)) return EMPTY_STAGE_ESTIMATE;
  return {
    estimatedRemainingMs: typeof value.estimated_remaining_ms === "number" ? value.estimated_remaining_ms : undefined,
    estimatedTotalMs: typeof value.estimated_total_ms === "number" ? value.estimated_total_ms : undefined,
    estimateSource:
      value.source === "configured_budget" || value.source === "observed_and_budget" ? value.source : undefined,
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

function safeError(
  raw: Record<string, unknown>,
  failedJob: boolean,
  failedJobView: StageViewModel["job"],
): GenerationViewModel["safeError"] {
  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const jobError = failedJobView?.error
    ? {
        code: failedJobView.error.code,
        message: failedJobView.error.message,
      }
    : null;
  const sourceError = latestError ?? jobError;
  if (!sourceError && !failedJob) return null;
  const sourceRecord: Record<string, unknown> = isRecord(sourceError) ? sourceError : {};
  return {
    ...readSafeStageError(
      sourceRecord,
      typeof sourceRecord.message === "string"
        ? sourceRecord.message
        : typeof sourceRecord.safe_user_summary === "string"
          ? sourceRecord.safe_user_summary
          : "Code Generator could not complete.",
    ),
    retryable: sourceRecord.retryable === true,
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
      coordinatorStage: "",
      currentAttempt: 1,
      traceId: "",
      activeJobId: null,
      activeJobKind: null,
      issues: [],
      latestError: null,
      projectTitle: "Personal Portfolio",
      projectSummary: "A clean, modern portfolio site for a product designer with case studies and a blog.",
      preview: null,
      candidatePreview: null,
      warnings: [],
      safeError: null,
      retryAvailable: false,
      estimatedRemainingMs: undefined,
      estimatedTotalMs: undefined,
      estimateSource: undefined,
    };
  }

  const status = raw.status;
  const hasActiveJobProjection = "active_job_id" in raw || "active_job_kind" in raw;
  const activeJobId = typeof raw.active_job_id === "string" ? raw.active_job_id : null;
  const activeJobKind = typeof raw.active_job_kind === "string" ? raw.active_job_kind : null;
  const rawCoordStage = isRecord(raw.progress) && typeof raw.progress.coordinator_stage === "string"
    ? raw.progress.coordinator_stage
    : "";
  const coordinatorStage = rawCoordStage || (
    status === "planning" ? "plan" :
    status === "acquiring" ? "acquire" :
    status === "generating" ? "generate" :
    status === "verifying" ? "verify" :
    status === "preview_pending" || status === "ready" ? "preview" :
    activeJobKind?.includes("verify") ? "verify" :
    activeJobKind?.includes("generate") ? "generate" :
    activeJobKind?.includes("acquire") ? "acquire" :
    activeJobKind?.includes("plan") ? "plan" : ""
  );
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

  const creative = isRecord(raw.creative_direction) ? raw.creative_direction : null;
  const planSummary = isRecord(raw.progress) && isRecord(raw.progress.plan_summary)
    ? raw.progress.plan_summary
    : isRecord(raw.plan_summary) ? raw.plan_summary : null;

  let projectTitle = "Personal Portfolio";
  let projectSummary = "A clean, modern portfolio site for a product designer with case studies and a blog.";

  if (creative && typeof creative.headline === "string" && creative.headline) {
    projectTitle = creative.headline;
  } else if (planSummary && typeof planSummary.title === "string" && planSummary.title) {
    projectTitle = planSummary.title;
  }

  if (creative && typeof creative.positioning === "string" && creative.positioning) {
    projectSummary = creative.positioning;
  } else if (planSummary && typeof planSummary.summary === "string" && planSummary.summary) {
    projectSummary = planSummary.summary;
  }

  const issues: string[] = [];
  if (Array.isArray(raw.issues)) {
    for (const item of raw.issues) {
      if (typeof item === "string") issues.push(item);
      else if (isRecord(item)) {
        if (typeof item.message === "string") issues.push(item.message);
        else if (typeof item.code === "string") issues.push(item.code);
      }
    }
  }

  const currentAttempt = isRecord(raw.progress) && typeof raw.progress.current_attempt === "number"
    ? raw.progress.current_attempt
    : 1;

  const stageEstimate = adaptStageEstimate(
    isRecord(raw.progress) ? raw.progress.stage_estimate : undefined,
  );

  const traceId = typeof raw.trace_id === "string" ? raw.trace_id : "";
  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;

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
    coordinatorStage,
    currentAttempt,
    traceId,
    activeJobId,
    activeJobKind,
    issues,
    latestError,
    projectTitle,
    projectSummary,
    preview,
    candidatePreview,
    warnings: warningMessages(raw.warnings ?? raw.advisories),
    safeError: safeError(raw, failedJob, job),
    retryAvailable: state === "attention" && !stale && raw.retry_available === true,
    estimatedRemainingMs: stageEstimate.estimatedRemainingMs,
    estimatedTotalMs: stageEstimate.estimatedTotalMs,
    estimateSource: stageEstimate.estimateSource,
  };
}
