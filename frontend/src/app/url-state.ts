// Small URL codec for the authenticated five-stage product. Generate &
// Preview is a merged final stage (D-081 supersedes D-063's "ends at Build
// Preparation" boundary); there is no separate "preview" stage id.

export type JourneyStageId = "discover" | "content" | "design" | "prepare" | "generate";
export type ViewId = "start" | "work" | "artifact" | "progress";

export interface AppUrlState {
  stage: JourneyStageId | null;
  view: ViewId | null;
}

const STAGE_VALUES: readonly JourneyStageId[] = ["discover", "content", "design", "prepare", "generate"];
const VIEW_VALUES: readonly ViewId[] = ["start", "work", "artifact", "progress"];

function includesValue<T extends string>(values: readonly T[], candidate: string | null): candidate is T {
  return candidate !== null && (values as readonly string[]).includes(candidate);
}

export function parseAppUrlState(search: string): AppUrlState {
  const params = new URLSearchParams(search);
  const stageRaw = params.get("stage");
  const viewRaw = params.get("view");
  return {
    stage: includesValue(STAGE_VALUES, stageRaw) ? stageRaw : null,
    view: includesValue(VIEW_VALUES, viewRaw) ? viewRaw : null,
  };
}

export function serializeAppUrlState(state: Partial<AppUrlState>): string {
  const params = new URLSearchParams();
  if (state.stage) params.set("stage", state.stage);
  if (state.view) params.set("view", state.view);
  const query = params.toString();
  return query ? `?${query}` : "";
}
