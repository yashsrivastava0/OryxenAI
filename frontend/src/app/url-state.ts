// Small URL codec for the authenticated three-stage product. Later-stage
// developer harnesses have their own routes and never enter this state.

export type JourneyStageId = "discover" | "content" | "design";
export type ViewId = "start" | "work" | "artifact" | "progress";

export interface AppUrlState {
  stage: JourneyStageId | null;
  view: ViewId | null;
}

const STAGE_VALUES: readonly JourneyStageId[] = ["discover", "content", "design"];
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
