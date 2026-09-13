// Visual Design Director stage adapter (docs/Frontend/05 §6.3).
// Normalizes VisualDesignDirectorState into DesignViewModel.
// Follows the same fail-closed, defensive pattern established by discovery.ts and content.ts.
//
// The backend schema (src/oryxenai/agents/visual_design_director/schemas.py)
// produces ZERO literal colors, hex codes, font names, or CSS values. The
// `visual_language`/`shared_visual_systems`/`motion_system` blocks are
// free-form PROSE dicts (read here as thesis/intent strings). The genuinely
// structured, ID-bearing payload is `pages[].scenes[]` (the per-scroll-moment
// storyboard), the top-level `asset_briefs[]`, and `resource_candidates[]` —
// those are the fields this adapter surfaces so the stage can visualize what
// actually happens as a visitor scrolls, instead of flattening rich structure
// into prose.

import { selectStageJob } from "./job";
import {
  readAgentOutput,
  readSafeStageError,
  type SafeStageError,
  type StageState,
  type StageViewModel,
} from "./types";

export interface VisualLanguageVM {
  creativeThesis: string;
  designKeywords: string[];
  colorIntent: string;
  typographyIntent: string;
  motionIntent: string;
}

/**
 * One deliberate scroll/interaction moment within a route — the structured,
 * ID-bearing storyboard beat from SceneDirection. `motionIntent` is the real
 * free-dict on the backend, flattened here to a compact readable line so the
 * UI never has to render raw JSON.
 */
export interface SceneDirectionVM {
  sceneId: string;
  routeId: string;
  narrativeGoal: string;
  viewportRole: string;
  contentRefs: string[];
  layoutIntent: string;
  alignmentRelationships: string;
  relativeProportions: string;
  layerStack: string;
  backgroundIntent: string;
  assetRequirements: string[];
  resourceCandidates: string[];
  /** Compact human line derived from the motion_intent dict (may be empty). */
  motionIntent: string;
  /** Compact human line derived from the interaction_states dict (may be empty). */
  interactionStates: string;
  transitionIn: string;
  transitionOut: string;
  responsiveBehavior: string;
  accessibilityIntent: string;
  reducedMotionBehavior: string;
  performanceRisk: string;
  failureSafeStaticState: string;
  acceptanceCriteria: string[];
}

/**
 * Intent for one meaningful image/visual requirement (AssetBrief). Never a
 * concrete file — Build Preparation resolves the real asset. The adapter keeps
 * the fields that make the treatment understandable at review time.
 */
export interface AssetBriefVM {
  assetId: string;
  purpose: string;
  contentRef: string;
  assetType: string;
  sourceStatus: string;
  sourcePolicy: string;
  importance: string;
  compositionRole: string;
  desktopTreatment: string;
  mobileTreatment: string;
  visualTreatment: string;
  fallbackStrategy: string;
  decorativeVsInformative: string;
  subject: string;
  mood: string;
}

export interface PageVisualDirectionVM {
  routeId: string;
  title: string;
  path: string;
  purpose: string;
  mood: string;
  visitorTakeaway: string;
  firstImpression: string;
  storyboard: string;
  sectionRhythm: string;
  primaryEmphasis: string;
  secondaryEmphasis: string;
  responsiveSummary: string;
  layoutIntent: string;
  desktopTreatment: string;
  mobileTreatment: string;
  scenes: SceneDirectionVM[];
  /** IDs referencing the top-level asset_briefs[]. */
  assetBriefIds: string[];
  resourceCandidateIds: string[];
}

export interface ResourceCandidateVM {
  resourceId: string;
  category: string;
  whyItMatches: string;
  whereItMayHelp: string;
  priority: string;
  possibleUse: string;
  adaptationNotes: string;
  confidence: string;
}

export interface DesignViewModel extends StageViewModel {
  userSummary: string;
  creativeThesis: string;
  visualLanguage: VisualLanguageVM;
  /** True when this run carried only visual language (VISUAL_LANGUAGE_ONLY mode). */
  visualLanguageOnly: boolean;
  pages: PageVisualDirectionVM[];
  assetBriefs: AssetBriefVM[];
  resources: ResourceCandidateVM[];
  conflicts: string[];
  warnings: string[];
  safeError: SafeStageError | null;
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

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

/**
 * Flatten a free-form prose dict (motion_intent, interaction_states) into a
 * compact single line without inventing structure. The backend emits these as
 * loose string->string maps (e.g. {purpose, trigger, intensity}); we join the
 * string values in a stable, readable order. Non-string values are ignored so
 * we never leak raw JSON into the UI.
 */
function flattenProseDict(value: unknown): string {
  if (!isRecord(value)) return "";
  const parts: string[] = [];
  for (const key of Object.keys(value)) {
    const entry = value[key];
    if (typeof entry === "string" && entry.trim()) {
      parts.push(`${key.replace(/_/g, " ")}: ${entry.trim()}`);
    } else if (Array.isArray(entry)) {
      const joined = entry.filter((e): e is string => typeof e === "string").join(", ");
      if (joined) parts.push(`${key.replace(/_/g, " ")}: ${joined}`);
    }
  }
  return parts.join(" · ");
}

function adaptScene(raw: unknown): SceneDirectionVM | null {
  if (!isRecord(raw)) return null;
  return {
    sceneId: asString(raw.scene_id),
    routeId: asString(raw.route_id),
    narrativeGoal: asString(raw.narrative_goal),
    viewportRole: asString(raw.viewport_role),
    contentRefs: asStringList(raw.content_refs),
    layoutIntent: asString(raw.layout_intent),
    alignmentRelationships: asString(raw.alignment_relationships),
    relativeProportions: asString(raw.relative_proportions),
    layerStack: asString(raw.layer_stack),
    backgroundIntent: asString(raw.background_intent),
    assetRequirements: asStringList(raw.asset_requirements),
    resourceCandidates: asStringList(raw.resource_candidates),
    motionIntent: flattenProseDict(raw.motion_intent),
    interactionStates: flattenProseDict(raw.interaction_states),
    transitionIn: asString(raw.transition_in),
    transitionOut: asString(raw.transition_out),
    responsiveBehavior: asString(raw.responsive_behavior),
    accessibilityIntent: asString(raw.accessibility_intent),
    reducedMotionBehavior: asString(raw.reduced_motion_behavior),
    performanceRisk: asString(raw.performance_risk),
    failureSafeStaticState: asString(raw.failure_safe_static_state),
    acceptanceCriteria: asStringList(raw.acceptance_criteria),
  };
}

function adaptAssetBrief(raw: unknown): AssetBriefVM | null {
  if (!isRecord(raw) || typeof raw.asset_id !== "string") return null;
  return {
    assetId: raw.asset_id,
    purpose: asString(raw.purpose),
    contentRef: asString(raw.content_ref),
    assetType: asString(raw.asset_type),
    sourceStatus: asString(raw.source_status),
    sourcePolicy: asString(raw.source_policy),
    importance: asString(raw.importance),
    compositionRole: asString(raw.composition_role),
    desktopTreatment: asString(raw.desktop_treatment),
    mobileTreatment: asString(raw.mobile_treatment),
    visualTreatment: asString(raw.visual_treatment),
    fallbackStrategy: asString(raw.fallback_strategy),
    decorativeVsInformative: asString(raw.decorative_vs_informative),
    subject: asString(raw.subject),
    mood: asString(raw.mood),
  };
}

function adaptPageVisualDirection(raw: unknown): PageVisualDirectionVM | null {
  if (!isRecord(raw) || typeof raw.route_id !== "string") return null;
  const scenes = Array.isArray(raw.scenes)
    ? raw.scenes.map(adaptScene).filter((s): s is SceneDirectionVM => s !== null)
    : [];
  return {
    routeId: raw.route_id,
    title: asString(raw.title),
    path: asString(raw.path),
    purpose: asString(raw.purpose),
    mood: asString(raw.mood),
    visitorTakeaway: asString(raw.visitor_takeaway),
    firstImpression: asString(raw.first_impression),
    storyboard: asString(raw.storyboard),
    sectionRhythm: asString(raw.section_rhythm),
    primaryEmphasis: asString(raw.primary_emphasis),
    secondaryEmphasis: asString(raw.secondary_emphasis),
    responsiveSummary: asString(raw.responsive_summary),
    layoutIntent: asString(raw.layout_intent),
    desktopTreatment: asString(raw.desktop_treatment),
    mobileTreatment: asString(raw.mobile_treatment),
    scenes,
    assetBriefIds: asStringList(raw.asset_briefs),
    resourceCandidateIds: asStringList(raw.resource_candidates),
  };
}

function adaptResourceCandidate(raw: unknown): ResourceCandidateVM | null {
  if (!isRecord(raw) || typeof raw.resource_id !== "string") return null;
  return {
    resourceId: raw.resource_id,
    category: asString(raw.category),
    whyItMatches: asString(raw.why_it_matches),
    whereItMayHelp: asString(raw.where_it_may_help),
    priority: asString(raw.priority),
    possibleUse: asString(raw.possible_use),
    adaptationNotes: asString(raw.adaptation_notes),
    confidence: asString(raw.confidence),
  };
}

/**
 * Accepts the raw `visual_design_director` dict from VisualDesignDirectorStateResponse
 * and whether Content Architect has been approved.
 */
export function adaptVisualDesignDirector(
  raw: unknown,
  contentApproved = false,
  jobs: unknown[] = [],
): DesignViewModel {
  if (!isRecord(raw) || typeof raw.status !== "string" || !(raw.status in STATE_MAP)) {
    return {
      state: "unsupported",
      statusText: "Visual Design Director returned an unrecognised state. Refresh to continue.",
      raw,
      job: selectStageJob(jobs),
      agentOutput: null,
      userSummary: "",
      creativeThesis: "",
      visualLanguage: {
        creativeThesis: "",
        designKeywords: [],
        colorIntent: "",
        typographyIntent: "",
        motionIntent: "",
      },
      visualLanguageOnly: false,
      pages: [],
      assetBriefs: [],
      resources: [],
      conflicts: [],
      warnings: [],
      safeError: null,
    };
  }

  const status = raw.status;
  const job = selectStageJob(jobs, typeof raw.job_id === "string" ? raw.job_id : null);
  const failedJob = job?.status === "failed" || job?.status === "cancelled";
  let state: StageState = failedJob ? "attention" : STATE_MAP[status] ?? "unsupported";

  // Upstream gating: if not started and Content is not yet approved, this stage is locked.
  if (status === "not_started" && !contentApproved) {
    state = "locked";
  }

  const userSummary = asString(raw.user_summary);
  const lang = isRecord(raw.visual_language) ? raw.visual_language : {};
  const creativeThesis = asString(lang.creative_thesis);
  const designKeywords = asStringList(lang.design_keywords);

  const visualLanguage: VisualLanguageVM = {
    creativeThesis,
    designKeywords,
    // The backend never emits literal color/type/motion CSS; these are prose
    // "intent" strings. Read the primary field, falling back to adjacent prose
    // keys the model actually uses in real output (e.g. color_behavior,
    // typography, motion_character) so the UI shows real intent, not blanks.
    colorIntent: asString(lang.color_intent) || asString(lang.color_behavior),
    typographyIntent: asString(lang.typography_intent) || asString(lang.typography),
    motionIntent: asString(lang.motion_intent) || asString(lang.motion_character),
  };

  const pages = Array.isArray(raw.pages)
    ? raw.pages.map(adaptPageVisualDirection).filter((p): p is PageVisualDirectionVM => p !== null)
    : [];

  const assetBriefs = Array.isArray(raw.asset_briefs)
    ? raw.asset_briefs.map(adaptAssetBrief).filter((a): a is AssetBriefVM => a !== null)
    : [];

  const resources = Array.isArray(raw.resource_candidates)
    ? raw.resource_candidates.map(adaptResourceCandidate).filter((r): r is ResourceCandidateVM => r !== null)
    : [];

  // pages_included is the backend's own discriminator for VISUAL_LANGUAGE_ONLY
  // vs the later page-bearing modes. When false (or when no pages parsed), the
  // scene visualization has nothing to show and the UI renders language only.
  const pagesIncluded = raw.pages_included === true;
  const visualLanguageOnly = !pagesIncluded || pages.length === 0;

  const conflicts = asStringList(raw.conflicts);
  const warnings = asStringList(raw.warnings);

  const latestError = isRecord(raw.latest_error) ? raw.latest_error : null;
  const safeError =
    (status === "needs_attention" && latestError) || failedJob
      ? readSafeStageError(
          latestError,
          typeof latestError?.message === "string"
            ? latestError.message
            : typeof latestError?.summary === "string"
              ? latestError.summary
              : job?.error?.message ?? "Visual Design Director needs attention.",
        )
      : null;

  return {
    state,
    statusText: status === "not_started" && !contentApproved
      ? "Locked until Content is approved"
      : STATUS_TEXT[status] ?? "Working on Design",
    raw,
    job,
    agentOutput: readAgentOutput(raw),
    userSummary,
    creativeThesis,
    visualLanguage,
    visualLanguageOnly,
    pages,
    assetBriefs,
    resources,
    conflicts,
    warnings,
    safeError,
  };
}
