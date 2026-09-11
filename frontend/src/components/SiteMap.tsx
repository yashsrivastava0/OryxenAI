import type { RoutePlanVM } from "../data/adapters/content";

export interface SiteMapProps {
  routes: RoutePlanVM[];
  onSelectRoute?: (routeId: string) => void;
}

/**
 * Visual route architecture map: a connected row of route nodes (path,
 * title, publication status, section count) replacing the old flattened
 * "### `/path` — Title" markdown bullets. This is the "real sitemap tree"
 * the Content Architect stage was missing — the site's shape should be
 * seen, not read as prose.
 */
export function SiteMap({ routes, onSelectRoute }: SiteMapProps) {
  if (routes.length === 0) return null;

  return (
    <nav className="site-map oxa-stagger" aria-label="Site architecture">
      <ol className="site-map-rail">
        {routes.map((route, index) => (
          <li key={route.routeId} className="site-map-node" data-priority={route.publicationStatus}>
            {index > 0 && <span className="site-map-connector" aria-hidden="true" />}
            <button
              type="button"
              className="site-map-node-button"
              onClick={() => onSelectRoute?.(route.routeId)}
            >
              <span className="site-map-path">{route.path || "/"}</span>
              <span className="site-map-title">{route.title || route.routeId}</span>
              <span className="site-map-sections">{route.sectionSequence.length} sections</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
