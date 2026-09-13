import type { AssetBriefVM, PageVisualDirectionVM, SceneDirectionVM } from "../data/adapters/design";

export interface SceneStoryboardProps {
  page: PageVisualDirectionVM;
  /**
   * The full top-level asset-brief list. A scene references briefs by id
   * (via its asset_requirements / content_refs), so the storyboard resolves
   * those ids to the real brief objects to show compact treatment cards
   * beside the scene that uses them.
   */
  assetBriefs: AssetBriefVM[];
}

/**
 * Resolve the asset briefs a single scene actually uses. A scene points at
 * briefs two ways in the real backend output:
 *   - `asset_requirements` holds asset_id values directly, and
 *   - `content_refs` can also match an AssetBrief's `content_ref` or `asset_id`.
 * We union both, deduping by asset_id, and only surface briefs that exist in
 * the top-level list (no fabricated placeholders).
 */
function briefsForScene(scene: SceneDirectionVM, all: AssetBriefVM[]): AssetBriefVM[] {
  const wanted = new Set<string>([...scene.assetRequirements, ...scene.contentRefs]);
  if (wanted.size === 0) return [];
  const seen = new Set<string>();
  const matched: AssetBriefVM[] = [];
  for (const brief of all) {
    if (seen.has(brief.assetId)) continue;
    if (wanted.has(brief.assetId) || (brief.contentRef && wanted.has(brief.contentRef))) {
      matched.push(brief);
      seen.add(brief.assetId);
    }
  }
  return matched;
}

/** A single scene's motion/responsive/asset detail. */
function SceneCard({
  scene,
  index,
  briefs,
}: {
  scene: SceneDirectionVM;
  index: number;
  briefs: AssetBriefVM[];
}) {
  return (
    <li className="scene-card">
      <div className="scene-card-head">
        <span className="scene-card-step" aria-hidden="true">
          {index + 1}
        </span>
        <div className="scene-card-titles">
          <p className="scene-card-goal">{scene.narrativeGoal || scene.sceneId || `Scene ${index + 1}`}</p>
          {scene.viewportRole && <p className="scene-card-viewport">{scene.viewportRole}</p>}
        </div>
      </div>

      <dl className="scene-card-fields">
        {scene.layoutIntent && (
          <div>
            <dt>Layout</dt>
            <dd>{scene.layoutIntent}</dd>
          </div>
        )}
        {scene.motionIntent && (
          <div>
            <dt>Motion</dt>
            <dd>{scene.motionIntent}</dd>
          </div>
        )}
        {scene.responsiveBehavior && (
          <div>
            <dt>Responsive</dt>
            <dd>{scene.responsiveBehavior}</dd>
          </div>
        )}
        {scene.reducedMotionBehavior && (
          <div>
            <dt>Reduced motion</dt>
            <dd>{scene.reducedMotionBehavior}</dd>
          </div>
        )}
        {scene.accessibilityIntent && (
          <div>
            <dt>Accessibility</dt>
            <dd>{scene.accessibilityIntent}</dd>
          </div>
        )}
        {scene.performanceRisk && (
          <div>
            <dt>Performance</dt>
            <dd>{scene.performanceRisk}</dd>
          </div>
        )}
      </dl>

      {briefs.length > 0 && (
        <div className="scene-card-assets">
          <p className="scene-card-assets-label">Assets used</p>
          <ul className="scene-asset-list">
            {briefs.map((brief) => (
              <li key={brief.assetId} className="scene-asset-card">
                <p className="scene-asset-head">
                  <span className="scene-asset-purpose">{brief.purpose || brief.assetId}</span>
                  {brief.decorativeVsInformative && (
                    <span
                      className={`scene-asset-tag scene-asset-tag--${
                        brief.decorativeVsInformative === "informative" ? "informative" : "decorative"
                      }`}
                    >
                      {brief.decorativeVsInformative}
                    </span>
                  )}
                </p>
                <dl className="scene-asset-fields">
                  {brief.assetType && (
                    <div>
                      <dt>Type</dt>
                      <dd>{brief.assetType}</dd>
                    </div>
                  )}
                  {brief.desktopTreatment && (
                    <div>
                      <dt>Desktop</dt>
                      <dd>{brief.desktopTreatment}</dd>
                    </div>
                  )}
                  {brief.mobileTreatment && (
                    <div>
                      <dt>Mobile</dt>
                      <dd>{brief.mobileTreatment}</dd>
                    </div>
                  )}
                  {brief.fallbackStrategy && (
                    <div>
                      <dt>Fallback</dt>
                      <dd>{brief.fallbackStrategy}</dd>
                    </div>
                  )}
                </dl>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

/**
 * SceneStoryboard — renders one page's scene sequence as an ordered, vertical
 * storyboard: each numbered card is one deliberate moment as a visitor scrolls
 * the page (narrative goal, viewport role, layout, motion, responsive and
 * accessibility intent), with the asset briefs that scene references shown as
 * compact treatment cards beside it.
 *
 * This intentionally renders NO color swatches, hex codes, or font specimens —
 * the backend produces none. It visualizes the real structured scene/asset
 * intelligence instead.
 */
export function SceneStoryboard({ page, assetBriefs }: SceneStoryboardProps) {
  if (page.scenes.length === 0) return null;

  return (
    <section className="scene-storyboard" aria-label={`Scroll journey for ${page.title || page.routeId}`}>
      <header className="scene-storyboard-head">
        <p className="scene-storyboard-route">{page.path || page.routeId}</p>
        <p className="scene-storyboard-title">{page.title || page.routeId}</p>
        {page.visitorTakeaway && <p className="scene-storyboard-takeaway">{page.visitorTakeaway}</p>}
        {page.sectionRhythm && <p className="scene-storyboard-rhythm">Flow: {page.sectionRhythm}</p>}
      </header>
      <ol className="scene-storyboard-track oxa-stagger">
        {page.scenes.map((scene, index) => (
          <SceneCard
            key={scene.sceneId || `${page.routeId}-scene-${index}`}
            scene={scene}
            index={index}
            briefs={briefsForScene(scene, assetBriefs)}
          />
        ))}
      </ol>
    </section>
  );
}
