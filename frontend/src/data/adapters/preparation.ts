// Build Preparation adapter.  The backend state is authoritative; this
// adapter only translates durable status and safe handoff facts into the
// shared product vocabulary.

import { selectStageJob } from "./job";
import {
  readAgentOutput,
  readSafeStageError,
  type SafeStageError,
  type StageState,
  type StageViewModel,
} from "./types";

export interface PreparationRouteVM {
  routeId: string;
  path: string;
  title: string;
  purpose: string;
}

export interface PreparationEventVM {
  eventId: string;
  stage: string;
  level: "info" | "warning" | "error";
  message: string;
  timestamp: string;
}

export interface BuildPreparationViewModel extends StageViewModel {
  status: string;
  stale: boolean;
  staleReasons: string[];
  currentStage: string;
  elapsedSeconds: number | null;
  completedAt: string | null;
  routes: PreparationRouteVM[];
  resourceNeedsCount: number;
  resourceIndexCount: number;
  componentIndexCount: number;
  contentBriefMarkdown: string;
  visualBriefMarkdown: string;
  targetContract: string;
  recommendedDependencies: string[];
  warnings: string[];
  events: PreparationEventVM[];
  safeError: (SafeStageError & { retryable: boolean }) | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to prepare the build handoff",
  running: "Preparing the build handoff",
  ready: "Build handoff ready for generation",
  needs_attention: "Build Preparation needs attention",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function adaptRoute(value: unknown): PreparationRouteVM | null {
  if (!isRecord(value) || typeof value.route_id !== "string") return null;
  return {
    routeId: value.route_id,
    path: typeof value.path === "string" ? value.path : "",
    title: typeof value.title === "string" ? value.title : "",
    purpose: typeof value.purpose === "string" ? value.purpose : "",
  };
}

function adaptEvent(value: unknown): PreparationEventVM | null {
  if (!isRecord(value) || typeof value.event_id !== "string" || typeof value.message !== "string") {
    return null;
  }
  const level = value.level === "warning" || value.level === "error" ? value.level : "info";
  return {
    eventId: value.event_id,
    stage: typeof value.stage === "string" ? value.stage : "",
    level,
    message: value.message,
    timestamp: typeof value.timestamp === "string" ? value.timestamp : "",
  };
}

function safeError(raw: Record<string, unknown>, failedJob: boolean): BuildPreparationViewModel["safeError"] {
  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  if (!latestError && !failedJob) return null;
  return {
    ...readSafeStageError(
      latestError,
      typeof latestError?.message === "string"
        ? latestError.message
        : typeof latestError?.summary === "string"
          ? latestError.summary
          : "Build Preparation could not complete.",
    ),
    retryable: latestError?.retryable === true,
  };
}

export function adaptBuildPreparation(
  raw: unknown,
  contentApproved = false,
  designApproved = false,
  jobs: unknown[] = [],
): BuildPreparationViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATUS_TEXT)) {
    return {
      state: "unsupported",
      statusText: "Build Preparation returned an unrecognised state. Refresh to continue.",
      raw,
      job: selectStageJob(jobs),
      agentOutput: null,
      status: "unsupported",
      stale: false,
      staleReasons: [],
      currentStage: "",
      elapsedSeconds: null,
      completedAt: null,
      routes: [],
      resourceNeedsCount: 0,
      resourceIndexCount: 0,
      componentIndexCount: 0,
      contentBriefMarkdown: "",
      visualBriefMarkdown: "",
      targetContract: "",
      recommendedDependencies: [],
      warnings: [],
      events: [],
      safeError: null,
    };
  }

  const status = raw.status;
  const job = selectStageJob(jobs, typeof raw.job_id === "string" ? raw.job_id : null);
  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  const stale = raw.stale === true;
  let state: StageState =
    status === "running"
      ? "working"
      : status === "ready"
        ? stale
          ? "attention"
          : "complete"
        : status === "needs_attention" || failedJob
          ? "attention"
          : status === "not_started"
            ? contentApproved && designApproved
              ? "available"
              : "locked"
            : "unsupported";

  const staleReasons = strings(raw.stale_reasons);
  const routes = Array.isArray(raw.routes)
    ? raw.routes.map(adaptRoute).filter((route): route is PreparationRouteVM => route !== null)
    : [];
  const events = Array.isArray(raw.events)
    ? raw.events.map(adaptEvent).filter((event): event is PreparationEventVM => event !== null)
    : [];
  const latestError = safeError(raw, failedJob);
  const statusText = stale
    ? "This handoff is out of date and needs to be prepared again"
    : status === "not_started" && state === "locked"
      ? "Locked until Content and Design are approved"
      : STATUS_TEXT[status] ?? "Preparing the build handoff";

  if (failedJob) state = "attention";

  return {
    state,
    statusText,
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    status,
    stale,
    staleReasons,
    currentStage: typeof raw.current_stage === "string" ? raw.current_stage : "",
    elapsedSeconds: typeof raw.elapsed_seconds === "number" ? raw.elapsed_seconds : null,
    completedAt: typeof raw.completed_at === "string" ? raw.completed_at : null,
    routes,
    resourceNeedsCount: Array.isArray(raw.resource_needs) ? raw.resource_needs.length : 0,
    resourceIndexCount: Array.isArray(raw.resource_index) ? raw.resource_index.length : 0,
    componentIndexCount: Array.isArray(raw.component_index) ? raw.component_index.length : 0,
    contentBriefMarkdown: typeof raw.content_brief_markdown === "string" ? raw.content_brief_markdown : "",
    visualBriefMarkdown: typeof raw.visual_brief_markdown === "string" ? raw.visual_brief_markdown : "",
    targetContract: typeof raw.target_contract === "string" ? raw.target_contract : "",
    recommendedDependencies: strings(raw.recommended_dependencies),
    warnings: strings(raw.warnings),
    events,
    safeError: latestError,
  };
}
