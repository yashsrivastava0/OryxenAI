// Code Generator stage adapter (docs/Frontend/05 §6.5).
// Normalizes CodeGeneratorSessionState into GenerationViewModel.
// Guards against premature success claims and safely preserves previous active previews.

import type { StageState, StageViewModel } from "./types";

export interface GenerationMilestoneVM {
  id: string;
  label: string;
  state: "complete" | "current" | "quiet";
}

export interface ActivePreviewInfo {
  origin?: string;
  baseUrl?: string;
  path: string;
  routePaths: string[];
  promotedAt?: string;
}

export interface GenerationIssueVM {
  code: string;
  message: string;
  blocking: boolean;
}

export interface GenerationViewModel extends StageViewModel {
  currentMilestone: string;
  milestones: GenerationMilestoneVM[];
  activePreview: ActivePreviewInfo | null;
  hasUsablePreview: boolean;
  safeError: { summary: string; technicalDetails?: string } | null;
  stale: boolean;
  retryEligible: boolean;
  elapsedSeconds: number | null;
  supportReference: string | null;
  issues: GenerationIssueVM[];
}

const CANONICAL_GENERATION_MILESTONES = [
  { id: "queue", label: "Waiting for generation lane" },
  { id: "plan", label: "Planning portfolio structure" },
  { id: "acquire", label: "Gathering approved materials" },
  { id: "generate", label: "Building portfolio routes" },
  { id: "verify", label: "Checking build and responsiveness" },
  { id: "promote", label: "Finalizing verified Preview" },
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function resolveGenerationMilestoneIndex(status: string): number {
  switch (status) {
    case "queued":
      return 0;
    case "planning":
      return 1;
    case "acquiring":
      return 2;
    case "generating":
      return 3;
    case "verifying":
      return 4;
    case "preview_pending":
      return 5;
    default:
      return 0;
  }
}

function resolveGenerationMilestoneLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Waiting for the generation lane";
    case "planning":
      return "Planning the portfolio build";
    case "acquiring":
      return "Preparing approved resources";
    case "generating":
      return "Building portfolio routes";
    case "verifying":
      return "Checking build and responsive behavior";
    case "preview_pending":
      return "Finalizing the verified Preview";
    default:
      return "Building the portfolio";
  }
}

export function adaptCodeGenerator(
  raw: unknown,
  isPreparationReady: boolean = false,
  readOnly: boolean = false,
): GenerationViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string") {
    return {
      state: "unsupported",
      statusText: "Code Generator returned an unrecognized response",
      currentMilestone: "Building the portfolio",
      milestones: CANONICAL_GENERATION_MILESTONES.map((m) => ({ ...m, state: "quiet" })),
      activePreview: null,
      hasUsablePreview: false,
      safeError: null,
      stale: false,
      retryEligible: false,
      elapsedSeconds: null,
      supportReference: null,
      issues: [],
      raw,
    };
  }

  const status = raw.status;
  const isStale = Boolean(raw.stale);
  const supportReference =
    typeof raw.trace_id === "string" && raw.trace_id
      ? raw.trace_id
      : typeof raw.current_run_id === "string" && raw.current_run_id
        ? raw.current_run_id
        : null;

  // Active Preview validation
  let activePreview: ActivePreviewInfo | null = null;
  let hasUsablePreview = false;
  if (isRecord(raw.active_preview)) {
    let origin = typeof raw.active_preview.origin === "string" ? raw.active_preview.origin : undefined;
    let baseUrl = typeof raw.active_preview.base_url === "string" ? raw.active_preview.base_url : undefined;
    let path = typeof raw.active_preview.path === "string" ? raw.active_preview.path : "";
    if (typeof raw.active_preview.url === "string" && raw.active_preview.url) {
      try {
        const parsed = new URL(raw.active_preview.url);
        origin = origin ?? parsed.origin;
        baseUrl = baseUrl ?? raw.active_preview.url;
        path = path || parsed.pathname;
      } catch {
        // Handled safely
      }
    }
    const routePaths = Array.isArray(raw.active_preview.route_paths)
      ? raw.active_preview.route_paths.filter((p): p is string => typeof p === "string")
      : [];
    const promotedAt =
      typeof raw.active_preview.promoted_at === "string" ? raw.active_preview.promoted_at : undefined;

    if (origin && path) {
      activePreview = { origin, baseUrl, path, routePaths, promotedAt };
      hasUsablePreview = true;
    }
  }

  // Safe issues extraction
  const issues: GenerationIssueVM[] = [];
  if (Array.isArray(raw.issues)) {
    for (const item of raw.issues) {
      if (isRecord(item) && typeof item.message === "string") {
        issues.push({
          code: typeof item.code === "string" ? item.code : "ISSUE",
          message: item.message,
          blocking: Boolean(item.blocking),
        });
      }
    }
  }

  // Safe error extraction
  let safeError: { summary: string; technicalDetails?: string } | null = null;
  if (isRecord(raw.latest_error)) {
    const msg =
      typeof raw.latest_error.message === "string"
        ? raw.latest_error.message
        : "An issue occurred during portfolio generation.";
    const code = typeof raw.latest_error.code === "string" ? raw.latest_error.code : undefined;
    safeError = {
      summary: msg,
      technicalDetails: code || supportReference ? `Reference: ${code ?? supportReference}` : undefined,
    };
  }

  const elapsedSeconds = typeof raw.elapsed_seconds === "number" ? raw.elapsed_seconds : null;

  // Retry eligibility: read-only users cannot retry; retry_status must not be explicitly "ineligible"
  const retryEligible =
    !readOnly &&
    status === "needs_attention" &&
    raw.retry_status !== "ineligible";

  // Derive Normalized State
  let state: StageState;
  let statusText: string;
  let currentMilestone = resolveGenerationMilestoneLabel(status);

  if (status === "not_started") {
    state = isPreparationReady && !readOnly ? "available" : "locked";
    statusText = isPreparationReady
      ? "Ready to generate your portfolio"
      : "Requires completed Build Preparation handoff";
    currentMilestone = "Awaiting generation start";
  } else if (
    status === "queued" ||
    status === "planning" ||
    status === "acquiring" ||
    status === "generating" ||
    status === "verifying" ||
    status === "preview_pending"
  ) {
    state = "working";
    statusText = currentMilestone;
  } else if (status === "ready") {
    if (hasUsablePreview) {
      state = "complete";
      statusText = "Portfolio generated and verified";
      currentMilestone = "Verified Preview ready";
    } else {
      // ready without usable active Preview is an attention state per §6.5
      state = "attention";
      statusText = "Preview is currently unavailable. Reconnect or refetch to confirm state.";
      currentMilestone = "Preview unavailable";
    }
  } else if (status === "needs_attention") {
    state = "attention";
    statusText = safeError?.summary ?? "Generation stopped and needs attention";
  } else {
    state = "unsupported";
    statusText = "Code Generator returned an unrecognized status";
  }

  // Compute milestones states
  const activeIdx = resolveGenerationMilestoneIndex(status);
  const milestones: GenerationMilestoneVM[] = CANONICAL_GENERATION_MILESTONES.map((m, idx) => {
    if (state === "complete") {
      return { ...m, state: "complete" };
    }
    if (state === "working") {
      if (idx < activeIdx) return { ...m, state: "complete" };
      if (idx === activeIdx) return { ...m, state: "current" };
      return { ...m, state: "quiet" };
    }
    if (state === "attention" && hasUsablePreview) {
      // Prior build was verified
      return { ...m, state: "complete" };
    }
    return { ...m, state: "quiet" };
  });

  return {
    state,
    statusText,
    currentMilestone,
    milestones,
    activePreview,
    hasUsablePreview,
    safeError,
    stale: isStale,
    retryEligible,
    elapsedSeconds,
    supportReference,
    issues,
    raw,
  };
}
