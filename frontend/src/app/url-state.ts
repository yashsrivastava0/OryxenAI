// /app URL query codec — no client router (docs/Frontend/README.md decision
// 1; docs/Frontend/05 §3.2). Pure parse/serialize so it's unit-testable
// without a DOM; AppShell.tsx owns calling history.pushState/replaceState
// with the result.

export type JourneyStageId = "discover" | "content" | "design" | "prepare" | "generate" | "preview";
export type ViewId = "start" | "work" | "artifact" | "progress" | "preview";
export type PreviewViewport = "fit" | "mobile" | "tablet" | "desktop";

export interface AppUrlState {
  stage: JourneyStageId | null;
  view: ViewId | null;
  route: string | null;
  viewport: PreviewViewport | null;
}

const STAGE_VALUES: readonly JourneyStageId[] = ["discover", "content", "design", "prepare", "generate", "preview"];
const VIEW_VALUES: readonly ViewId[] = ["start", "work", "artifact", "progress", "preview"];
const VIEWPORT_VALUES: readonly PreviewViewport[] = ["fit", "mobile", "tablet", "desktop"];

function includesValue<T extends string>(values: readonly T[], candidate: string | null): candidate is T {
  return candidate !== null && (values as readonly string[]).includes(candidate);
}

/**
 * Parses `location.search`. Unknown/invalid values are dropped, not kept —
 * the caller should normalize the address bar with `replaceState` after
 * calling this (docs/Frontend/05 §3.2 rule 2).
 */
export function parseAppUrlState(search: string): AppUrlState {
  const params = new URLSearchParams(search);
  const stageRaw = params.get("stage");
  const viewRaw = params.get("view");
  const routeRaw = params.get("route");
  const viewportRaw = params.get("viewport");

  let stage = includesValue(STAGE_VALUES, stageRaw) ? stageRaw : null;
  let view = includesValue(VIEW_VALUES, viewRaw) ? viewRaw : null;

  // If view is preview, stage is normalized to preview
  if (view === "preview" || stage === "preview") {
    stage = "preview";
    view = "preview";
  }

  const viewport = includesValue(VIEWPORT_VALUES, viewportRaw) ? viewportRaw : null;
  // Structural safety only here — whether `route` actually matches a
  // promoted route belongs to the Preview adapter.
  const route =
    routeRaw && routeRaw.startsWith("/") && !routeRaw.includes("..") && !routeRaw.includes("\\")
      ? routeRaw
      : null;

  return { stage, view, route, viewport };
}

export function serializeAppUrlState(state: Partial<AppUrlState>): string {
  const params = new URLSearchParams();
  if (state.stage) {
    params.set("stage", state.stage);
  }
  if (state.view) {
    params.set("view", state.view);
  }
  if (state.route) {
    params.set("route", state.route);
  }
  if (state.viewport) {
    params.set("viewport", state.viewport);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
