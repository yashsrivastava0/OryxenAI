import { useState } from "preact/hooks";
import type { PageContentPackVM, RoutePlanVM } from "../data/adapters/content";
import { SiteMap } from "./SiteMap";
import { PeekCard } from "./PeekCard";

export interface ContentPackExplorerProps {
  routePlan: RoutePlanVM[];
  pageContentPacks: PageContentPackVM[];
}

/**
 * Route-scoped reading experience for the Content Architect artifact.
 *
 * The whole-site orientation (SiteMap) stays visible at the top as the entry
 * point, then a route-selector scopes the page-content-pack view to ONE
 * route's sections at a time — instead of flattening every route's every
 * section into one continuous scroll. Default selection is the first route.
 *
 * This is a separate component (not inlined into ContentStage) precisely so
 * its `useState` runs only under a real render pass. ContentStage stays a
 * hook-free function whose returned vnode tree can be inspected directly in
 * the Node-environment unit tests.
 */
export function ContentPackExplorer({ routePlan, pageContentPacks }: ContentPackExplorerProps) {
  // Only routes that actually have a content pack are selectable targets;
  // fall back to the route plan order so the tabs mirror the SiteMap order.
  const selectableRoutes = routePlan.filter((route) =>
    pageContentPacks.some((pack) => pack.routeId === route.routeId),
  );
  const orderedRoutes = selectableRoutes.length > 0 ? selectableRoutes : routePlan;
  const firstRouteId = orderedRoutes[0]?.routeId ?? pageContentPacks[0]?.routeId ?? "";

  const [selectedRouteId, setSelectedRouteId] = useState(firstRouteId);

  // Defensive: if the selected route is no longer present (data refreshed),
  // fall back to the first available route rather than showing nothing.
  const activeRouteId = orderedRoutes.some((r) => r.routeId === selectedRouteId)
    ? selectedRouteId
    : firstRouteId;

  const activePack = pageContentPacks.find((pack) => pack.routeId === activeRouteId) ?? null;
  const activeRoute = routePlan.find((route) => route.routeId === activeRouteId) ?? null;

  return (
    <div className="content-pack-explorer">
      {/* Whole-site orientation stays first. Selecting a node here also
          scopes the reading view below, so the map doubles as navigation. */}
      {routePlan.length > 0 && (
        <SiteMap routes={routePlan} onSelectRoute={(routeId) => setSelectedRouteId(routeId)} />
      )}

      {orderedRoutes.length > 0 && (
        <div className="content-route-selector" role="tablist" aria-label="Page routes">
          {orderedRoutes.map((route) => {
            const isActive = route.routeId === activeRouteId;
            const pack = pageContentPacks.find((p) => p.routeId === route.routeId);
            const sectionCount = pack?.sections.length ?? 0;
            return (
              <button
                key={route.routeId}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={`content-route-tab${isActive ? " is-active" : ""}`}
                onClick={() => setSelectedRouteId(route.routeId)}
              >
                <span className="content-route-tab-path">{route.path || route.routeId}</span>
                <span className="content-route-tab-count">{sectionCount} sections</span>
              </button>
            );
          })}
        </div>
      )}

      {activePack && (
        <div className="content-section-deck" role="tabpanel" aria-label="Selected route content">
          <p className="eyebrow">
            {activeRoute?.path || activeRouteId} · {activePack.sections.length} sections
          </p>
          {activeRoute?.audienceTakeaway && (
            <p className="content-route-takeaway">{activeRoute.audienceTakeaway}</p>
          )}
          {activePack.sections.length === 0 && (
            <p className="content-route-empty">This route has no detailed section copy yet.</p>
          )}
          {activePack.sections.map((sec) => {
            const headline = (sec.content.headline as string) || (sec.content.title as string) || sec.purpose;
            const subhead = (sec.content.subheadline as string) || (sec.content.body as string) || "";
            const otherKeys = Object.keys(sec.content).filter(
              (key) => !["headline", "title", "subheadline", "body"].includes(key),
            );
            return (
              <PeekCard
                key={sec.sectionId}
                eyebrow={sec.sectionId}
                title={headline || sec.purpose}
                badge={sec.priority || undefined}
                summary={subhead || sec.purpose}
              >
                <p className="peek-card-purpose">{sec.purpose}</p>
                {subhead && <p>{subhead}</p>}
                {otherKeys.length > 0 && (
                  <dl className="content-section-extra-fields">
                    {otherKeys.map((key) => {
                      const value = sec.content[key];
                      const rendered = Array.isArray(value)
                        ? value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join(", ")
                        : typeof value === "string"
                          ? value
                          : JSON.stringify(value);
                      return (
                        <div key={key}>
                          <dt>{key.replace(/_/g, " ")}</dt>
                          <dd>{rendered}</dd>
                        </div>
                      );
                    })}
                  </dl>
                )}
              </PeekCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
