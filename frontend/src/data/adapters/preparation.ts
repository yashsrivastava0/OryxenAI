// Build Preparation stage adapter (docs/Frontend/05 §6.4).
// Normalizes BuildPreparationState into PreparationViewModel.
// Follows defensive fail-closed parsing and grouping of evolving internal substages.

import type { StageState, StageViewModel } from "./types";

export interface PreparationMilestoneVM {
  id: string;
  label: string;
  state: "complete" | "current" | "quiet";
}

export interface PreparationViewModel extends StageViewModel {
  currentMilestone: string;
  milestones: PreparationMilestoneVM[];
  routeCount: number | null;
  warnings: string[];
  stale: boolean;
  staleReasons: string[];
  handoffEligible: boolean;
  safeError: { summary: string; technicalDetails?: string } | null;
  elapsedSeconds: number | null;
}

const CANONICAL_MILESTONES = [
  { id: "check_plan", label: "Checking approved plan" },
  { id: "resolve_materials", label: "Resolving portfolio materials" },
  { id: "compile_context", label: "Compiling build context" },
  { id: "package_verify", label: "Packaging and verifying handoff" },
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function resolveMilestoneIndex(substage: string): number {
  if (substage === "stage_0") return 0;
  if (substage === "stage_1" || substage === "stage_2") return 1;
  if (substage === "stage_3" || substage === "stage_4" || substage === "phase_2") return 2;
  if (
    substage === "materialize" ||
    substage === "stage_5" ||
    substage === "package" ||
    substage === "artifact_storage" ||
    substage === "phase_3"
  ) {
    return 3;
  }
  return 0; // fallback default
}

function resolveMilestoneLabel(substage: string): string {
  if (substage === "stage_0") return "Checking the approved plan";
  if (substage === "stage_1" || substage === "stage_2") return "Resolving portfolio materials";
  if (substage === "stage_3" || substage === "stage_4" || substage === "phase_2") return "Compiling the build context";
  if (
    substage === "materialize" ||
    substage === "stage_5" ||
    substage === "package" ||
    substage === "artifact_storage" ||
    substage === "phase_3"
  ) {
    return "Packaging and verifying the handoff";
  }
  return "Preparing the build package";
}

export function adaptBuildPreparation(
  raw: unknown,
  isUpstreamApproved: boolean = false,
): PreparationViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string") {
    return {
      state: "unsupported",
      statusText: "Build Preparation returned an unrecognized response",
      currentMilestone: "Preparing the build package",
      milestones: CANONICAL_MILESTONES.map((m) => ({ ...m, state: "quiet" })),
      routeCount: null,
      warnings: [],
      stale: false,
      staleReasons: [],
      handoffEligible: false,
      safeError: null,
      elapsedSeconds: null,
      raw,
    };
  }

  const status = raw.status;
  const currentSubstage = typeof raw.current_stage === "string" ? raw.current_stage : "";
  const isStale = Boolean(raw.stale);
  const staleReasons = Array.isArray(raw.stale_reasons)
    ? raw.stale_reasons.filter((r): r is string => typeof r === "string")
    : [];

  const handoffReport = isRecord(raw.handoff_report) ? raw.handoff_report : null;
  const packageResult = isRecord(raw.package) ? raw.package : null;
  const isHandoffEligible =
    Boolean(handoffReport?.handoff_eligible) &&
    packageResult !== null &&
    !isStale;

  const warnings = Array.isArray(raw.warnings)
    ? raw.warnings.filter((w): w is string => typeof w === "string")
    : [];

  const routeCount = Array.isArray(raw.routes) ? raw.routes.length : null;
  const elapsedSeconds = typeof raw.elapsed_seconds === "number" ? raw.elapsed_seconds : null;

  let safeError: { summary: string; technicalDetails?: string } | null = null;
  if (isRecord(raw.latest_error)) {
    const msg =
      typeof raw.latest_error.message === "string"
        ? raw.latest_error.message
        : "An issue occurred during build preparation.";
    const code = typeof raw.latest_error.code === "string" ? raw.latest_error.code : undefined;
    safeError = {
      summary: msg,
      technicalDetails: code ? `Error reference: ${code}` : undefined,
    };
  }

  // Derive Normalized State
  let state: StageState;
  let statusText: string;
  let currentMilestone = resolveMilestoneLabel(currentSubstage);

  if (status === "not_started") {
    state = isUpstreamApproved ? "available" : "locked";
    statusText = isUpstreamApproved
      ? "Ready to prepare the portfolio build handoff"
      : "Requires approved Content Plan and Visual Direction";
    currentMilestone = "Awaiting build preparation";
  } else if (status === "running") {
    state = "working";
    statusText = currentMilestone;
  } else if (status === "ready") {
    if (isStale) {
      state = "attention";
      statusText = "Upstream inputs changed. Regenerate preparation to continue.";
    } else if (!isHandoffEligible && handoffReport) {
      state = "attention";
      statusText = "Build preparation completed with unresolved issues. Regenerate to continue.";
    } else {
      state = "complete";
      statusText = "Build handoff package verified and ready for generation";
      currentMilestone = "Verified build handoff complete";
    }
  } else if (status === "needs_attention") {
    state = "attention";
    statusText = safeError?.summary ?? "Build preparation needs attention";
  } else {
    state = "unsupported";
    statusText = "Build Preparation returned an unrecognized status";
  }

  // Compute milestones list states
  const activeIdx = resolveMilestoneIndex(currentSubstage);
  const milestones: PreparationMilestoneVM[] = CANONICAL_MILESTONES.map((m, idx) => {
    if (state === "complete") {
      return { ...m, state: "complete" };
    }
    if (state === "working") {
      if (idx < activeIdx) return { ...m, state: "complete" };
      if (idx === activeIdx) return { ...m, state: "current" };
      return { ...m, state: "quiet" };
    }
    if (state === "attention" && status === "ready" && isStale) {
      // Prior build succeeded but now stale
      return { ...m, state: "complete" };
    }
    return { ...m, state: "quiet" };
  });

  return {
    state,
    statusText,
    currentMilestone,
    milestones,
    routeCount,
    warnings,
    stale: isStale,
    staleReasons,
    handoffEligible: isHandoffEligible,
    safeError,
    elapsedSeconds,
    raw,
  };
}
