import type { DesignViewModel } from "../../data/adapters/design";
import { finalAgentOutput } from "../../data/final-agent-output";
import { formatActivityStatus } from "../../data/activity-copy";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { WorkspaceCanvas } from "../../components/WorkspaceCanvas";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { PeekCard } from "../../components/PeekCard";
import { SceneStoryboard } from "../../components/SceneStoryboard";

export interface DesignStageProps {
  view: DesignViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  /** Starts Build Preparation after approval has already been persisted. */
  onApproveAndContinue: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function DesignStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onStartNextStage,
  onRevise,
  onStop,
  inFlight = false,
}: DesignStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Visual Design Director requires an approved site content plan before establishing the aesthetic systems, visual language, and page layouts.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 03 / Visual Design Director</p>
        <h2>Ready to direct visual experience</h2>
        <p className="stage-desc">
          Visual Design Director will consume your approved content plan to derive the creative thesis, the per-page visual language, and a scene-by-scene storyboard of what a visitor experiences while scrolling each page.
        </p>
        <AsyncActionButton
          label="Start Visual Design Director"
          busyLabel="Starting Visual Design Director..."
          onAction={onStart}
          disabled={!canMutate}
          inFlight={inFlight}
        />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Visual Design Director" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 03 / Visual Design Director"
        title="Directing the visual proof"
        currentMilestone={view.statusText || "Visual Design Director is working from the approved content plan"}
        milestones={[
          { id: "content", label: "Approved content plan received", state: "complete" },
          { id: "current", label: view.statusText || "Visual Design Director is working", state: "current" },
        ]}
        onStop={onStop}
        stopLabel="Stop Visual Design Director"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Visual Design Director needs attention"
        summary={view.safeError?.summary || "Design direction synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Content Plan remains safe."
        retryLabel="Retry Visual Design Director"
        onRetry={onStart}
        errorDetails={view.safeError ?? undefined}
      />
    );
  }

  // review or complete
  const isApproved = view.state === "complete";
  const lang = view.visualLanguage;

  // Derive the live activity line from the stage's real durable status via the
  // shared pure formatter — same precedent as ContentStage. No hardcoded stage
  // copy inside the generic WorkspaceCanvas shell; composed here.
  const rawStatus =
    view.raw && typeof view.raw === "object" && "status" in view.raw
      ? String((view.raw as { status?: unknown }).status ?? "")
      : "";
  const activity = formatActivityStatus("visual_design_director", rawStatus, { stale: false });

  const sceneCount = view.pages.reduce((sum, page) => sum + page.scenes.length, 0);

  const rail = (
    <div className="content-activity-rail">
      <p className="eyebrow">Journey · Stage 03 of 05</p>
      <p className="workspace-journey-position">Visual Design Director</p>
      <p
        className={`oxa-activity-line${activity.working ? " is-active" : ""}`}
        role="status"
        aria-live="polite"
      >
        {activity.text}
      </p>
      {lang.creativeThesis && <p className="design-rail-thesis">{lang.creativeThesis}</p>}
      <dl className="content-activity-facts">
        <div>
          <dt>Styled routes</dt>
          <dd>{view.pages.length}</dd>
        </div>
        <div>
          <dt>Scenes</dt>
          <dd>{sceneCount}</dd>
        </div>
        <div>
          <dt>Asset briefs</dt>
          <dd>{view.assetBriefs.length}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{isApproved ? "Locked & approved" : "Under review"}</dd>
        </div>
      </dl>
    </div>
  );

  const artifact = (
    <ArtifactSurface
      title="Visual Direction & Experience Architecture"
      artifactTypeName="visual direction"
      statusBadge={isApproved ? "Approved" : "Ready for review"}
      isApproved={isApproved}
      canMutate={canMutate}
      finalJsonOutput={finalAgentOutput("visual_design_director", view.raw)}
      warnings={view.warnings}
      metadata={[
        { label: "Styled Routes", value: String(view.pages.length) },
        { label: "Scenes", value: String(sceneCount) },
        { label: "Status", value: isApproved ? "Locked & Approved" : "Under Review" },
      ]}
      nextStageName="Build Preparation"
      onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
      onStartNextStage={isApproved ? onStartNextStage : undefined}
      nextStageInFlight={inFlight}
      onRevise={isApproved ? undefined : onRevise}
    >
      {lang.creativeThesis && (
        <section className="design-thesis-card">
          <p className="eyebrow">Creative thesis</p>
          <p className="design-thesis-quote">{lang.creativeThesis}</p>
          {lang.designKeywords.length > 0 && (
            <ul className="design-keyword-chips oxa-stagger">
              {lang.designKeywords.map((keyword) => (
                <li key={keyword} className="design-keyword-chip">{keyword}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {(lang.colorIntent || lang.typographyIntent || lang.motionIntent) && (
        <div className="design-intent-grid oxa-stagger">
          {lang.colorIntent && (
            <div className="design-intent-card">
              <p className="design-intent-label">Color intent</p>
              <p>{lang.colorIntent}</p>
            </div>
          )}
          {lang.typographyIntent && (
            <div className="design-intent-card">
              <p className="design-intent-label">Typography intent</p>
              <p>{lang.typographyIntent}</p>
            </div>
          )}
          {lang.motionIntent && (
            <div className="design-intent-card">
              <p className="design-intent-label">Motion intent</p>
              <p>{lang.motionIntent}</p>
            </div>
          )}
        </div>
      )}

      {/* PRIMARY artifact: the scene-by-scene storyboard of what happens as a
          visitor scrolls each page. Only rendered when the run actually carried
          pages/scenes (VISUAL_LANGUAGE_AND_PAGES and later modes). */}
      {!view.visualLanguageOnly && sceneCount > 0 && (
        <div className="design-storyboard-deck">
          <p className="eyebrow">Scroll journey · {sceneCount} scenes across {view.pages.length} routes</p>
          {view.pages
            .filter((page) => page.scenes.length > 0)
            .map((page) => (
              <SceneStoryboard key={page.routeId} page={page} assetBriefs={view.assetBriefs} />
            ))}
        </div>
      )}

      {/* VISUAL_LANGUAGE_ONLY: no pages/scenes yet. Make the language-only
          state explicit rather than rendering an empty storyboard. */}
      {view.visualLanguageOnly && (
        <div className="design-language-only-note" role="note">
          <p>
            This is the visual language foundation — the creative thesis and the color, typography, and motion intent above. Page-by-page scene direction is produced in the next pass and will appear here as a scroll-journey storyboard.
          </p>
        </div>
      )}

      {/* SECONDARY / supporting detail: the per-page direction deck. Demoted
          into a collapsible drawer — it still carries real value
          (desktop/mobile treatment prose) but is no longer the headline. */}
      {view.pages.length > 0 && (
        <details className="design-page-deck-drawer">
          <summary>Page direction detail · {view.pages.length} routes</summary>
          <div className="design-page-deck">
            {view.pages.map((page) => (
              <PeekCard
                key={page.routeId}
                eyebrow={page.path || page.routeId}
                title={page.title || page.routeId}
                badge={page.mood || undefined}
                summary={page.firstImpression || page.layoutIntent || page.purpose}
              >
                {page.purpose && <p>{page.purpose}</p>}
                <dl className="design-page-detail-fields">
                  {page.storyboard && (<div><dt>Storyboard</dt><dd>{page.storyboard}</dd></div>)}
                  {page.primaryEmphasis && (<div><dt>Primary emphasis</dt><dd>{page.primaryEmphasis}</dd></div>)}
                  {page.secondaryEmphasis && (<div><dt>Secondary emphasis</dt><dd>{page.secondaryEmphasis}</dd></div>)}
                  {page.layoutIntent && (<div><dt>Layout intent</dt><dd>{page.layoutIntent}</dd></div>)}
                  {page.desktopTreatment && (<div><dt>Desktop</dt><dd>{page.desktopTreatment}</dd></div>)}
                  {page.mobileTreatment && (<div><dt>Mobile</dt><dd>{page.mobileTreatment}</dd></div>)}
                  {page.responsiveSummary && (<div><dt>Responsive</dt><dd>{page.responsiveSummary}</dd></div>)}
                </dl>
              </PeekCard>
            ))}
          </div>
        </details>
      )}

      {view.resources.length > 0 && (
        <details className="design-resources-drawer">
          <summary>Adapted layout candidates · {view.resources.length}</summary>
          <ul>
            {view.resources.map((r) => (
              <li key={r.resourceId}>
                <strong>{r.resourceId}</strong>
                {r.category && <span className="design-resource-category"> ({r.category})</span>}
                {r.priority && <span className="design-resource-category"> · {r.priority}</span>}
                <p>{r.whyItMatches}</p>
                {r.possibleUse && <p className="design-resource-adaptation">Use: {r.possibleUse}</p>}
                {r.adaptationNotes && <p className="design-resource-adaptation">Adaptation: {r.adaptationNotes}</p>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {view.conflicts.length > 0 && (
        <div className="content-unresolved-banner" role="note">
          <p className="warnings-title">Conflicts to resolve</p>
          <ul>
            {view.conflicts.map((conflict, idx) => (
              <li key={idx}>{conflict}</li>
            ))}
          </ul>
        </div>
      )}
    </ArtifactSurface>
  );

  return (
    <div className="design-stage-view">
      <WorkspaceCanvas
        railLabel="Stage 03 / Visual Design Director"
        ariaLabel="Visual Design Director workspace"
        rail={rail}
        artifact={artifact}
      />
    </div>
  );
}
