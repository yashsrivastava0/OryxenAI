type FinalOutputStage =
  | "discovery"
  | "content_architect"
  | "visual_design_director"
  | "build_preparation";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function pickFields(
  source: Record<string, unknown>,
  fields: readonly string[],
): Record<string, unknown> {
  return Object.fromEntries(
    fields.filter((field) => field in source).map((field) => [field, source[field]]),
  );
}

const CONTENT_FIELDS = [
  "user_summary",
  "site_story_strategy",
  "decision_basis",
  "route_plan",
  "claim_grounding",
  "page_content_packs",
  "public_content_manifest",
  "omissions",
  "unresolved_issues",
  "privacy_and_confidentiality",
  "media_status",
  "visual_director_handoff",
  "warnings",
  "stages_run",
] as const;

const DESIGN_FIELDS = [
  "user_summary",
  "meta",
  "source_refs",
  "visual_language",
  "shared_visual_systems",
  "navigation_direction",
  "motion_system",
  "interaction_system",
  "pages",
  "asset_briefs",
  "resource_candidates",
  "accessibility_and_performance",
  "must_preserve",
  "must_not_fabricate",
  "conflicts",
  "warnings",
  "compiler_handoff",
  "resource_policy",
  "stages_run",
] as const;

const BUILD_FIELDS = [
  "scope_hash",
  "routes",
  "resource_needs",
  "resource_index",
  "component_index",
  "content_brief_markdown",
  "visual_brief_markdown",
  "target_contract",
  "recommended_dependencies",
  "warnings",
  "model_calls",
  "provider_calls",
] as const;

/** Return only the persisted final agent artifact, never intake/auth/job state. */
export function finalAgentOutput(
  stage: FinalOutputStage,
  rawState: unknown,
): Record<string, unknown> | null {
  if (!isRecord(rawState)) return null;

  if (stage === "discovery") {
    const brief = rawState.brief;
    if (!isRecord(brief) || typeof brief.markdown !== "string" || !brief.markdown.trim()) {
      return null;
    }
    return {
      operation: "build_or_revise_brief",
      mode: "BRIEF_READY",
      brief_title: typeof brief.title === "string" ? brief.title : "",
      brief_markdown: brief.markdown,
      user_summary: typeof brief.user_summary === "string" ? brief.user_summary : "",
      profile: isRecord(brief.profile) ? brief.profile : {},
      open_items: Array.isArray(brief.open_items) ? brief.open_items : [],
    };
  }

  const fields = stage === "content_architect"
    ? CONTENT_FIELDS
    : stage === "visual_design_director"
      ? DESIGN_FIELDS
      : BUILD_FIELDS;
  const output = pickFields(rawState, fields);
  return Object.keys(output).length > 0 ? output : null;
}
