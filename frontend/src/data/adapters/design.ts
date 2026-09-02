// Visual Design Director stage adapter (docs/Frontend/05 §6.3).
// Normalizes VisualDesignDirectorState into DesignViewModel.
// Follows the same fail-closed, defensive pattern established by discovery.ts and content.ts.

import type { StageState, StageViewModel } from "./types";

export interface VisualLanguageVM {
  creativeThesis: string;
  designKeywords: string[];
  colorIntent: string;
  typographyIntent: string;
  motionIntent: string;
}

export interface PageVisualDirectionVM {
  routeId: string;
  title: string;
  purpose: string;
  mood: string;
  layoutIntent: string;
  desktopTreatment: string;
  mobileTreatment: string;
}

export interface ResourceCandidateVM {
  resourceId: string;
  category: string;
  whyItMatches: string;
  adaptationNotes: string;
}

export interface DesignViewModel extends StageViewModel {
  userSummary: string;
  creativeThesis: string;
  visualLanguage: VisualLanguageVM;
  pages: PageVisualDirectionVM[];
  resources: ResourceCandidateVM[];
  conflicts: string[];
  warnings: string[];
  safeError: { summary: string } | null;
}

const STATUS_TEXT: Record<string, string> = {
  not_started: "Ready to direct visual experience",
  build_running: "Developing the visual direction",
  design_review: "Your visual direction is ready to review",
  approved: "Visual direction approved",
  needs_attention: "Visual Design Director needs attention",
};

const STATE_MAP: Record<string, StageState> = {
  not_started: "available",
  build_running: "working",
  design_review: "review",
  approved: "complete",
  needs_attention: "attention",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function adaptPageVisualDirection(raw: unknown): PageVisualDirectionVM | null {
  if (!isRecord(raw) || typeof raw.route_id !== "string") return null;
  return {
    routeId: raw.route_id,
    title: typeof raw.title === "string" ? raw.title : "",
    purpose: typeof raw.purpose === "string" ? raw.purpose : "",
    mood: typeof raw.mood === "string" ? raw.mood : "",
    layoutIntent: typeof raw.layout_intent === "string" ? raw.layout_intent : "",
    desktopTreatment: typeof raw.desktop_treatment === "string" ? raw.desktop_treatment : "",
    mobileTreatment: typeof raw.mobile_treatment === "string" ? raw.mobile_treatment : "",
  };
}

function adaptResourceCandidate(raw: unknown): ResourceCandidateVM | null {
  if (!isRecord(raw) || typeof raw.resource_id !== "string") return null;
  return {
    resourceId: raw.resource_id,
    category: typeof raw.category === "string" ? raw.category : "",
    whyItMatches: typeof raw.why_it_matches === "string" ? raw.why_it_matches : "",
    adaptationNotes: typeof raw.adaptation_notes === "string" ? raw.adaptation_notes : "",
  };
}

/**
 * Accepts the raw `visual_design_director` dict from VisualDesignDirectorStateResponse
 * and whether Content Architect has been approved.
 */
export function adaptVisualDesignDirector(raw: unknown, contentApproved = false): DesignViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATE_MAP)) {
    return {
      state: "unsupported",
      statusText: "Visual Design Director returned an unrecognised state. Refresh to continue.",
      raw,
      userSummary: "",
      creativeThesis: "",
      visualLanguage: {
        creativeThesis: "",
        designKeywords: [],
        colorIntent: "",
        typographyIntent: "",
        motionIntent: "",
      },
      pages: [],
      resources: [],
      conflicts: [],
      warnings: [],
      safeError: null,
    };
  }

  const status = raw.status;
  let state: StageState = STATE_MAP[status] ?? "unsupported";

  // Upstream gating: if not started and Content is not yet approved, this stage is locked.
  if (status === "not_started" && !contentApproved) {
    state = "locked";
  }

  const userSummary = typeof raw.user_summary === "string" ? raw.user_summary : "";
  const lang = isRecord(raw.visual_language) ? raw.visual_language : {};
  const creativeThesis = typeof lang.creative_thesis === "string" ? lang.creative_thesis : "";
  const designKeywords = Array.isArray(lang.design_keywords)
    ? lang.design_keywords.filter((k): k is string => typeof k === "string")
    : [];

  const visualLanguage: VisualLanguageVM = {
    creativeThesis,
    designKeywords,
    colorIntent: typeof lang.color_intent === "string" ? lang.color_intent : "",
    typographyIntent: typeof lang.typography_intent === "string" ? lang.typography_intent : "",
    motionIntent: typeof lang.motion_intent === "string" ? lang.motion_intent : "",
  };

  const pages = Array.isArray(raw.pages)
    ? raw.pages.map(adaptPageVisualDirection).filter((p): p is PageVisualDirectionVM => p !== null)
    : [];

  const resources = Array.isArray(raw.resource_candidates)
    ? raw.resource_candidates.map(adaptResourceCandidate).filter((r): r is ResourceCandidateVM => r !== null)
    : [];

  const conflicts = Array.isArray(raw.conflicts)
    ? raw.conflicts.filter((c): c is string => typeof c === "string")
    : [];

  const warnings = Array.isArray(raw.warnings)
    ? raw.warnings.filter((w): w is string => typeof w === "string")
    : [];

  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const safeError =
    status === "needs_attention" && latestError
      ? { summary: typeof latestError.message === "string" ? latestError.message : "Visual Design Director needs attention." }
      : null;

  return {
    state,
    statusText: status === "not_started" && !contentApproved
      ? "Locked until Content is approved"
      : STATUS_TEXT[status] ?? "Working on Design",
    raw,
    userSummary,
    creativeThesis,
    visualLanguage,
    pages,
    resources,
    conflicts,
    warnings,
    safeError,
  };
}
