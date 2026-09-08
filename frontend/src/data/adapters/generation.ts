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
}

export interface GenerationViewModel extends StageViewModel {
  status: string;
  stale: boolean;
  staleReasons: string[];
  currentMilestone: string;
  preview: GenerationPreviewVM | null;
  safeError: (SafeStageError & { retryable: boolean }) | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to generate the portfolio",
  queued: "Queued for generation",
  planning: "Planning the site",
  acquiring: "Acquiring resources",
  generating: "Generating the portfolio",
  verifying: "Verifying the build",
  ready: "Portfolio generated and verified",
  preview_pending: "Finishing the preview",
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
  };
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
      safeError: null,
    };
  }

  const status = raw.status;
  const job = selectStageJob(jobs, typeof raw.current_run_id === "string" ? raw.current_run_id : null);
  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  const stale = raw.stale === true;
  const preview = adaptPreview(raw.active_preview);

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
    currentMilestone: isRecord(raw.progress) && typeof raw.progress.coordinator_stage === "string"
      ? raw.progress.coordinator_stage
      : statusText,
    preview,
    safeError: safeError(raw, failedJob),
  };
}
