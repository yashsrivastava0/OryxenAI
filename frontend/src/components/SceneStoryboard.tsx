import { useState } from "preact/hooks";
import type { AssetBriefVM, PageVisualDirectionVM, SceneDirectionVM } from "../data/adapters/design";

export interface SceneStoryboardProps {
  page: PageVisualDirectionVM;
  assetBriefs: AssetBriefVM[];
}

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

/**
 * Editorial scene SVG banner matching the mood and aesthetic of 05-design-storyboard.png
 */
function SceneVisualBanner({ index, title: _title }: { index: number; title?: string }) {
  const motifs = [
    // Hero / Opening motif
    (
      <svg viewBox="0 0 360 120" fill="none" xmlns="http://www.w3.org/2000/svg" className="scene-banner-svg" preserveAspectRatio="xMidYMid slice">
        <rect width="360" height="120" fill="#EAE5DC" />
        <rect x="20" y="24" width="140" height="72" fill="#D8D0C3" rx="4" />
        <path d="M40 85L80 45L120 85" stroke="#9E9689" strokeWidth="2" strokeLinecap="round" />
        <circle cx="120" cy="45" r="14" fill="#C4BCAD" />
        <line x1="180" y1="36" x2="330" y2="36" stroke="#2D302E" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="180" y1="52" x2="280" y2="52" stroke="#686C66" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="180" y1="68" x2="240" y2="68" stroke="#8A8E88" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
    // Work / Showcase motif
    (
      <svg viewBox="0 0 360 120" fill="none" xmlns="http://www.w3.org/2000/svg" className="scene-banner-svg" preserveAspectRatio="xMidYMid slice">
        <rect width="360" height="120" fill="#E4DFD4" />
        <rect x="24" y="20" width="90" height="80" fill="#CEC7B9" rx="3" />
        <rect x="130" y="20" width="90" height="80" fill="#BFB7A8" rx="3" />
        <rect x="236" y="20" width="90" height="80" fill="#B3AB9B" rx="3" />
        <line x1="36" y1="75" x2="86" y2="75" stroke="#171A19" strokeWidth="2" />
        <line x1="142" y1="75" x2="192" y2="75" stroke="#171A19" strokeWidth="2" />
        <line x1="248" y1="75" x2="298" y2="75" stroke="#171A19" strokeWidth="2" />
      </svg>
    ),
    // Process / Deep Dive motif
    (
      <svg viewBox="0 0 360 120" fill="none" xmlns="http://www.w3.org/2000/svg" className="scene-banner-svg" preserveAspectRatio="xMidYMid slice">
        <rect width="360" height="120" fill="#DFDAD0" />
        <path d="M30 60 H 330" stroke="#B8B1A2" strokeWidth="1" strokeDasharray="4 4" />
        <circle cx="60" cy="60" r="16" fill="#FAF7F2" stroke="#171A19" strokeWidth="2" />
        <circle cx="150" cy="60" r="16" fill="#FAF7F2" stroke="#3157E7" strokeWidth="2" />
        <circle cx="240" cy="60" r="16" fill="#FAF7F2" stroke="#171A19" strokeWidth="2" />
        <circle cx="310" cy="60" r="8" fill="#171A19" />
      </svg>
    ),
  ];

  return (
    <div className="scene-banner-container" aria-hidden="true">
      {motifs[index % motifs.length]}
    </div>
  );
}

function SceneCard({
  scene,
  index,
  briefs,
}: {
  scene: SceneDirectionVM;
  index: number;
  briefs: AssetBriefVM[];
}) {
  const ordinal = String(index + 1).padStart(2, "0");
  const title = scene.narrativeGoal || scene.sceneId || `Scene ${index + 1}`;

  return (
    <li className="scene-card">
      <div className="scene-card-header-row">
        <div className="scene-card-num-title">
          <span className="scene-card-ordinal">{ordinal}</span>
          <h3 className="scene-card-title">{title}</h3>
        </div>
        {scene.viewportRole && (
          <span className="scene-card-role-badge">{scene.viewportRole}</span>
        )}
      </div>

      <SceneVisualBanner index={index} title={title} />

      <dl className="scene-metadata-grid">
        <div>
          <dt>NARRATIVE GOAL</dt>
          <dd>{scene.narrativeGoal || "Establish context and orient the reader."}</dd>
        </div>

        <div>
          <dt>VIEWPORT ROLE</dt>
          <dd>{scene.viewportRole || "Full viewport hero moment."}</dd>
        </div>

        <div>
          <dt>LAYOUT INTENT</dt>
          <dd>{scene.layoutIntent || "Asymmetric typography with purposeful whitespace."}</dd>
        </div>

        <div>
          <dt>RESPONSIVE BEHAVIOR</dt>
          <dd>{scene.responsiveBehavior || "Reflows into a single column with preserved hierarchy."}</dd>
        </div>

        <div>
          <dt>ACCESSIBILITY INTENT</dt>
          <dd>{scene.accessibilityIntent || "Clear reading order, semantic landmarks, high contrast."}</dd>
        </div>
      </dl>

      {briefs.length > 0 && (
        <div className="scene-card-assets">
          <p className="scene-card-assets-label">Assets used</p>
          <ul className="scene-asset-list">
            {briefs.map((brief) => (
              <li key={brief.assetId} className="scene-asset-card">
                <span className="scene-asset-purpose">{brief.purpose || brief.assetId}</span>
                {brief.desktopTreatment && (
                  <span className="scene-asset-treatment">{brief.desktopTreatment}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

export function SceneStoryboard({ page, assetBriefs }: SceneStoryboardProps) {
  const scenes = page.scenes;
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 3;
  const totalPages = Math.ceil(scenes.length / pageSize) || 1;

  const visibleScenes = scenes.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  const prev = () => setCurrentPage((p) => Math.max(0, p - 1));
  const next = () => setCurrentPage((p) => Math.min(totalPages - 1, p + 1));

  return (
    <div className="scene-storyboard" aria-label={`Scene storyboard for ${page.title || page.routeId}`}>
      <div className="storyboard-header">
        <div>
          <p className="storyboard-eyebrow eyebrow">SCENE STORYBOARD</p>
          <h2 className="storyboard-headline">
            {scenes.length > 0 ? `A ${scenes.length}-part story, starting here.` : "Scene sequence"}
          </h2>
        </div>

        {scenes.length > pageSize && (
          <div className="storyboard-controls">
            <span className="storyboard-pager-count">
              {Math.min((currentPage + 1) * pageSize, scenes.length)} of {scenes.length} scenes
            </span>
            <div className="storyboard-pager-buttons">
              <button
                type="button"
                className="btn-pager"
                onClick={prev}
                disabled={currentPage === 0}
                aria-label="Previous scenes"
              >
                ←
              </button>
              <button
                type="button"
                className="btn-pager"
                onClick={next}
                disabled={currentPage >= totalPages - 1}
                aria-label="Next scenes"
              >
                →
              </button>
            </div>
          </div>
        )}
      </div>

      <ol className="scene-grid">
        {(visibleScenes.length > 0 ? visibleScenes : scenes).map((scene, idx) => (
          <SceneCard
            key={scene.sceneId}
            scene={scene}
            index={currentPage * pageSize + idx}
            briefs={briefsForScene(scene, assetBriefs)}
          />
        ))}
      </ol>
    </div>
  );
}
