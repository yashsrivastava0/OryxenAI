// Studio (Code Generator) stage adapter.
// Normalizes the /code-generator envelope into StudioViewModel. Fail-closed like
// the other adapters: an unrecognized status is "unsupported", never "ready".
//
// The server owns what is live (active_version_id) and whether a build is in
// flight; the browser only ever renders that.

import { selectStageJob } from "./job";
import type { StageState, StageViewModel } from "./types";

export type StudioStatus = "not_started" | "build_running" | "ready" | "needs_attention";
export type StudioBuildStage =
  | "queued"
  | "starting"
  | "planning"
  | "generating"
  | "validating"
  | "verifying";
export type StudioOrigin = "initial" | "retry" | "change" | "restore";

export interface StudioFailureLocationVM {
  kind: string;
  ref: string;
  detail: string;
}

export interface StudioIssueVM {
  code: string;
  severity: string;
  message: string;
  path: string;
  selector: string;
  expected: string;
  found: string;
}

/** One exact failure: what failed, where, why, and what to do next. */
export interface StudioFailureVM {
  code: string;
  stage: string;
  summary: string;
  cause: string;
  where: StudioFailureLocationVM[];
  expected: string;
  found: string;
  owner: string;
  retryable: boolean;
  action: string;
  issueCount: number;
  reference: string;
  issues: StudioIssueVM[];
}

export interface StudioVersionVM {
  id: string;
  seq: number;
  versionNumber: number | null;
  origin: StudioOrigin;
  status: string;
  instruction: string;
  restricted: boolean;
  createdAt: string | null;
  completedAt: string | null;
  failure: StudioFailureVM | null;
  warningCount: number;
  browser: string | null;
}

export interface StudioChatVM {
  id: string;
  seq: number;
  role: "user" | "assistant" | "system";
  kind: "message" | "build" | "notice";
  body: string;
  versionId: string | null;
  createdAt: string | null;
}

export interface StudioInFlightVM {
  stage: StudioBuildStage;
  origin: "initial" | "retry" | "change";
  instruction: string;
  elapsedSeconds: number | null;
  versionId: string;
}

export interface StudioViewModel extends StageViewModel {
  status: StudioStatus | "unknown";
  activeVersionId: string | null;
  activeVersionNumber: number;
  inFlight: StudioInFlightVM | null;
  /** True while any build (first or chat-driven) is queued or running. */
  building: boolean;
  lastError: StudioFailureVM | null;
  versions: StudioVersionVM[];
  chat: StudioChatVM[];
  sessionRevision: number | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to generate your portfolio",
  build_running: "Building your portfolio",
  ready: "Your portfolio is live in the preview",
  needs_attention: "The build needs attention",
};

const BUILD_STAGES: readonly StudioBuildStage[] = [
  "queued",
  "starting",
  "planning",
  "generating",
  "validating",
  "verifying",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function str(value: unknown, limit = 4000): string {
  return typeof value === "string" ? value.slice(0, limit) : "";
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function records(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

export function adaptStudioFailure(raw: unknown): StudioFailureVM | null {
  if (!isRecord(raw) || typeof raw.code !== "string") return null;
  return {
    code: str(raw.code, 80),
    stage: str(raw.stage, 40),
    summary: str(raw.summary, 600) || "The build did not finish.",
    cause: str(raw.cause, 800),
    where: records(raw.where)
      .slice(0, 8)
      .map((item) => ({
        kind: str(item.kind, 20),
        ref: str(item.ref, 200),
        detail: str(item.detail, 300),
      })),
    expected: str(raw.expected, 400),
    found: str(raw.found, 400),
    owner: str(raw.owner, 40),
    retryable: raw.retryable !== false,
    action: str(raw.action, 400),
    issueCount: num(raw.issue_count) ?? 0,
    reference: str(raw.reference, 40),
    issues: records(raw.issues)
      .slice(0, 20)
      .map((item) => ({
        code: str(item.code, 60),
        severity: str(item.severity, 12),
        message: str(item.message, 400),
        path: str(item.path, 200),
        selector: str(item.selector, 200),
        expected: str(item.expected, 300),
        found: str(item.found, 300),
      })),
  };
}

function adaptVersion(raw: Record<string, unknown>): StudioVersionVM | null {
  if (typeof raw.id !== "string") return null;
  const origin = raw.origin;
  const summary = isRecord(raw.summary) ? raw.summary : {};
  return {
    id: raw.id,
    seq: num(raw.seq) ?? 0,
    versionNumber: num(raw.version_number),
    origin: origin === "change" || origin === "retry" || origin === "restore" ? origin : "initial",
    status: str(raw.status, 20),
    instruction: str(raw.instruction, 1600),
    restricted: raw.restricted === true,
    createdAt: typeof raw.created_at === "string" ? raw.created_at : null,
    completedAt: typeof raw.completed_at === "string" ? raw.completed_at : null,
    failure: adaptStudioFailure(raw.error),
    warningCount: num(summary.warning_count) ?? 0,
    browser: typeof summary.browser === "string" ? summary.browser : null,
  };
}

function adaptChat(raw: Record<string, unknown>): StudioChatVM | null {
  if (typeof raw.id !== "string") return null;
  const role = raw.role === "user" || raw.role === "assistant" ? raw.role : "system";
  const kind = raw.kind === "build" || raw.kind === "notice" ? raw.kind : "message";
  return {
    id: raw.id,
    seq: num(raw.seq) ?? 0,
    role,
    kind,
    body: str(raw.body, 2000),
    versionId: typeof raw.version_id === "string" ? raw.version_id : null,
    createdAt: typeof raw.created_at === "string" ? raw.created_at : null,
  };
}

function adaptInFlight(raw: unknown): StudioInFlightVM | null {
  if (!isRecord(raw) || typeof raw.version_id !== "string") return null;
  const stage = BUILD_STAGES.find((item) => item === raw.stage) ?? "queued";
  const origin = raw.origin === "change" || raw.origin === "retry" ? raw.origin : "initial";
  return {
    stage,
    origin,
    instruction: str(raw.instruction, 1600),
    elapsedSeconds: num(raw.elapsed_seconds),
    versionId: raw.version_id,
  };
}

export function adaptStudio(envelope: unknown, contentApproved: boolean): StudioViewModel {
  const root = isRecord(envelope) ? envelope : {};
  const generator = isRecord(root.code_generator) ? root.code_generator : {};
  const statusRaw = typeof generator.status === "string" ? generator.status : "";
  const known = statusRaw in STATUS_TEXT;
  const status: StudioViewModel["status"] = known ? (statusRaw as StudioStatus) : "unknown";
  const activeVersionId =
    typeof generator.active_version_id === "string" && generator.active_version_id
      ? generator.active_version_id
      : null;
  const inFlight = adaptInFlight(generator.in_flight);
  const jobId = isRecord(generator.in_flight) ? str(generator.in_flight.job_id, 80) : "";
  const building = status === "build_running";

  let state: StageState;
  if (!contentApproved) state = "locked";
  else if (!known) state = "unsupported";
  else if (status === "not_started") state = "available";
  else if (status === "build_running") state = activeVersionId ? "complete" : "working";
  else if (status === "ready") state = activeVersionId ? "complete" : "available";
  else state = activeVersionId ? "complete" : "attention";

  return {
    state,
    statusText: known ? (STATUS_TEXT[statusRaw] ?? "") : "Studio status is not recognized",
    raw: envelope,
    job: selectStageJob(root.jobs, jobId || null, "code_generator.build"),
    agentOutput: null,
    status,
    activeVersionId,
    activeVersionNumber: num(generator.active_version_number) ?? 0,
    inFlight,
    building,
    lastError: adaptStudioFailure(generator.last_error),
    versions: records(root.versions)
      .map(adaptVersion)
      .filter((item): item is StudioVersionVM => item !== null),
    chat: records(root.chat)
      .map(adaptChat)
      .filter((item): item is StudioChatVM => item !== null),
    sessionRevision: num(root.session_revision),
  };
}

export interface StudioMilestone {
  id: string;
  label: string;
  state: "complete" | "current" | "quiet";
}

/** Plain-language progress for the first build, from the server's stage. */
export function studioMilestones(stage: StudioBuildStage): StudioMilestone[] {
  const order: Array<[string, string, StudioBuildStage[]]> = [
    ["received", "Approved content received", []],
    ["writing", "Writing your page", ["queued", "starting", "planning", "generating"]],
    ["checking", "Checking every word, link and section", ["validating"]],
    ["browser", "Testing the page in a browser", ["verifying"]],
    ["ready", "Opening your preview", []],
  ];
  const currentIndex = Math.max(
    1,
    order.findIndex(([, , stages]) => stages.includes(stage)),
  );
  return order.map(([id, label], index) => ({
    id,
    label,
    state: index < currentIndex ? "complete" : index === currentIndex ? "current" : "quiet",
  }));
}

export function studioStageLabel(stage: StudioBuildStage, origin: StudioInFlightVM["origin"]): string {
  switch (stage) {
    case "queued":
      return "Waiting for a free builder";
    case "starting":
    case "planning":
      return origin === "change" ? "Understanding your request" : "Getting started";
    case "generating":
      return origin === "change" ? "Rewriting the page" : "Writing your page";
    case "validating":
      return "Checking every word, link and section";
    case "verifying":
      return "Testing the page in a browser";
    default:
      return "Working";
  }
}

/** Newest-first ready versions that can be restored or shown as history. */
export function readyVersions(versions: StudioVersionVM[]): StudioVersionVM[] {
  return versions
    .filter((item) => item.status === "ready" && item.versionNumber !== null)
    .sort((left, right) => (right.versionNumber ?? 0) - (left.versionNumber ?? 0));
}

export function failureDiagnostics(failure: StudioFailureVM): string {
  return JSON.stringify(
    {
      code: failure.code,
      stage: failure.stage,
      summary: failure.summary,
      cause: failure.cause,
      owner: failure.owner,
      where: failure.where,
      expected: failure.expected || undefined,
      found: failure.found || undefined,
      reference: failure.reference,
      issue_count: failure.issueCount,
      issues: failure.issues,
    },
    null,
    2,
  );
}
