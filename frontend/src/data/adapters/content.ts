// Content Architect stage adapter (docs/Frontend/05 §6.3).
// Normalizes ContentArchitectState into ContentViewModel.
// Follows the same fail-closed, defensive pattern established by discovery.ts.

import type { StageState, StageViewModel } from "./types";

export interface RoutePlanVM {
  routeId: string;
  path: string;
  title: string;
  purpose: string;
  publicationStatus: string;
  audienceTakeaway: string;
  sectionSequence: string[];
}

export interface ContentSectionVM {
  sectionId: string;
  purpose: string;
  content: Record<string, unknown>;
  priority: string;
  optional: boolean;
}

export interface PageContentPackVM {
  routeId: string;
  sections: ContentSectionVM[];
}

export interface DecisionRecordVM {
  decision: string;
  value: string;
  basis: string;
  rationale: string;
}

export interface ContentViewModel extends StageViewModel {
  userSummary: string;
  positioning: string;
  routePlan: RoutePlanVM[];
  pageContentPacks: PageContentPackVM[];
  decisionBasis: DecisionRecordVM[];
  unresolvedIssues: string[];
  warnings: string[];
  safeError: { summary: string } | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to structure portfolio content",
  build_running: "Structuring your portfolio content",
  content_review: "Your content plan is ready to review",
  approved: "Content plan approved",
  needs_attention: "Content Architect needs attention",
};

const STATE_MAP: Record<string, StageState> = {
  not_started: "available",
  build_running: "working",
  content_review: "review",
  approved: "complete",
  needs_attention: "attention",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function adaptRoutePlanEntry(raw: unknown): RoutePlanVM | null {
  if (!isRecord(raw) || typeof raw.route_id !== "string") return null;
  return {
    routeId: raw.route_id,
    path: typeof raw.path === "string" ? raw.path : "",
    title: typeof raw.title === "string" ? raw.title : "",
    purpose: typeof raw.purpose === "string" ? raw.purpose : "",
    publicationStatus: typeof raw.publication_status === "string" ? raw.publication_status : "approved",
    audienceTakeaway: typeof raw.audience_takeaway === "string" ? raw.audience_takeaway : "",
    sectionSequence: Array.isArray(raw.section_sequence)
      ? raw.section_sequence.filter((s): s is string => typeof s === "string")
      : [],
  };
}

function adaptSection(raw: unknown): ContentSectionVM | null {
  if (!isRecord(raw) || typeof raw.section_id !== "string") return null;
  return {
    sectionId: raw.section_id,
    purpose: typeof raw.purpose === "string" ? raw.purpose : "",
    content: isRecord(raw.content) ? raw.content : {},
    priority: typeof raw.priority === "string" ? raw.priority : "",
    optional: Boolean(raw.optional),
  };
}

function adaptPagePack(raw: unknown): PageContentPackVM | null {
  if (!isRecord(raw) || typeof raw.route_id !== "string") return null;
  const sections = Array.isArray(raw.sections)
    ? raw.sections.map(adaptSection).filter((s): s is ContentSectionVM => s !== null)
    : [];
  return {
    routeId: raw.route_id,
    sections,
  };
}

function adaptDecision(raw: unknown): DecisionRecordVM | null {
  if (!isRecord(raw) || typeof raw.decision !== "string") return null;
  return {
    decision: raw.decision,
    value: typeof raw.value === "string" ? raw.value : "",
    basis: typeof raw.basis === "string" ? raw.basis : "safe_default",
    rationale: typeof raw.rationale === "string" ? raw.rationale : "",
  };
}

/**
 * Accepts the raw `content_architect` dict from ContentArchitectStateResponse
 * and whether Discovery has been approved.
 */
export function adaptContentArchitect(raw: unknown, discoveryApproved = false): ContentViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATE_MAP)) {
    return {
      state: "unsupported",
      statusText: "Content Architect returned an unrecognised state. Refresh to continue.",
      raw,
      userSummary: "",
      positioning: "",
      routePlan: [],
      pageContentPacks: [],
      decisionBasis: [],
      unresolvedIssues: [],
      warnings: [],
      safeError: null,
    };
  }

  const status = raw.status;
  let state: StageState = STATE_MAP[status] ?? "unsupported";

  // Upstream gating: if not started and Discovery is not yet approved, this stage is locked.
  if (status === "not_started" && !discoveryApproved) {
    state = "locked";
  }

  const userSummary = typeof raw.user_summary === "string" ? raw.user_summary : "";
  const strategy = isRecord(raw.site_story_strategy) ? raw.site_story_strategy : {};
  const positioning = typeof strategy.positioning === "string" ? strategy.positioning : "";

  const routePlan = Array.isArray(raw.route_plan)
    ? raw.route_plan.map(adaptRoutePlanEntry).filter((r): r is RoutePlanVM => r !== null)
    : [];

  const pageContentPacks = Array.isArray(raw.page_content_packs)
    ? raw.page_content_packs.map(adaptPagePack).filter((p): p is PageContentPackVM => p !== null)
    : [];

  const decisionBasis = Array.isArray(raw.decision_basis)
    ? raw.decision_basis.map(adaptDecision).filter((d): d is DecisionRecordVM => d !== null)
    : [];

  const unresolvedIssues = Array.isArray(raw.unresolved_issues)
    ? raw.unresolved_issues.filter((i): i is string => typeof i === "string")
    : [];

  const warnings = Array.isArray(raw.warnings)
    ? raw.warnings.filter((w): w is string => typeof w === "string")
    : [];

  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const safeError =
    status === "needs_attention" && latestError
      ? {
          summary:
            typeof latestError.message === "string"
              ? latestError.message
              : typeof latestError.summary === "string"
                ? latestError.summary
                : "Content Architect needs attention.",
        }
      : null;

  return {
    state,
    statusText: status === "not_started" && !discoveryApproved
      ? "Locked until Discovery is approved"
      : STATUS_TEXT[status] ?? "Working on Content",
    raw,
    userSummary,
    positioning,
    routePlan,
    pageContentPacks,
    decisionBasis,
    unresolvedIssues,
    warnings,
    safeError,
  };
}
