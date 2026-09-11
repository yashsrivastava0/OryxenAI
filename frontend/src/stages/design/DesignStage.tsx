import type { DesignViewModel } from "../../data/adapters/design";
import { finalAgentOutput } from "../../data/final-agent-output";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { PeekCard } from "../../components/PeekCard";

export interface DesignStageProps {
  view: DesignViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  /** Approves the visual direction and starts Build Preparation in one action. */
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function DesignStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
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
          Visual Design Director will consume your approved content plan to derive the creative thesis, typography hierarchy, color intention, and page-by-page visual language.
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

  return (
    <div className="design-stage-view">
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
          { label: "Status", value: isApproved ? "Locked & Approved" : "Under Review" },
        ]}
        nextStageName={isApproved ? undefined : "Build Preparation"}
        onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
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
                <p className="design-intent-label">Color</p>
                <p>{lang.colorIntent}</p>
              </div>
            )}
            {lang.typographyIntent && (
              <div className="design-intent-card">
                <p className="design-intent-label">Typography</p>
                <p>{lang.typographyIntent}</p>
              </div>
            )}
            {lang.motionIntent && (
              <div className="design-intent-card">
                <p className="design-intent-label">Motion</p>
                <p>{lang.motionIntent}</p>
              </div>
            )}
          </div>
        )}

        {view.pages.length > 0 && (
          <div className="design-page-deck">
            <p className="eyebrow">Page direction · {view.pages.length}</p>
            {view.pages.map((page) => (
              <PeekCard
                key={page.routeId}
                eyebrow={page.routeId}
                title={page.title || page.routeId}
                badge={page.mood || undefined}
                summary={page.layoutIntent || page.purpose}
              >
                {page.purpose && <p>{page.purpose}</p>}
                <dl className="design-page-detail-fields">
                  {page.layoutIntent && (<div><dt>Layout intent</dt><dd>{page.layoutIntent}</dd></div>)}
                  {page.desktopTreatment && (<div><dt>Desktop</dt><dd>{page.desktopTreatment}</dd></div>)}
                  {page.mobileTreatment && (<div><dt>Mobile</dt><dd>{page.mobileTreatment}</dd></div>)}
                </dl>
              </PeekCard>
            ))}
          </div>
        )}

        {view.resources.length > 0 && (
          <details className="design-resources-drawer">
            <summary>Adapted layout candidates · {view.resources.length}</summary>
            <ul>
              {view.resources.map((r) => (
                <li key={r.resourceId}>
                  <strong>{r.resourceId}</strong> <span className="design-resource-category">({r.category})</span>
                  <p>{r.whyItMatches}</p>
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
    </div>
  );
}
