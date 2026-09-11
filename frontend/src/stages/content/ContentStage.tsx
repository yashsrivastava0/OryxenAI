import type { ContentViewModel } from "../../data/adapters/content";
import { finalAgentOutput } from "../../data/final-agent-output";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { SiteMap } from "../../components/SiteMap";
import { PeekCard } from "../../components/PeekCard";

export interface ContentStageProps {
  view: ContentViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  /** Approves the content plan and starts Visual Design Director in one action. */
  onApproveAndContinue: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function ContentStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onRevise,
  onStop,
  inFlight = false,
}: ContentStageProps) {
  if (!view || view.state === "locked") {
    return (
      <div className="stage-locked-panel">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2>Stage Locked</h2>
        <p className="stage-desc">
          Content Architect requires an approved portfolio brief from Discovery before building your site architecture and page copy.
        </p>
      </div>
    );
  }

  if (view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 02 / Content Architect</p>
        <h2>Ready to structure portfolio content</h2>
        <p className="stage-desc">
          Content Architect will consume your approved brief to define the site's route structure, positioning statements, and detailed section copy.
        </p>
        <AsyncActionButton
          label="Start Content Architect"
          busyLabel="Starting Content Architect..."
          onAction={onStart}
          disabled={!canMutate}
          inFlight={inFlight}
        />
      </div>
    );
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Content Architect" statusText={view.statusText} />;
  }

  if (view.state === "working") {
    return (
      <ProgressSurface
        stageLabel="Stage 02 / Content Architect"
        title="Structuring the content proof"
        currentMilestone={view.statusText || "Content Architect is working from the approved brief"}
        milestones={[
          { id: "brief", label: "Approved Discovery brief received", state: "complete" },
          { id: "current", label: view.statusText || "Content Architect is working", state: "current" },
        ]}
        onStop={onStop}
        stopLabel="Stop Content Architect"
      />
    );
  }

  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Content Architect needs attention"
        summary={view.safeError?.summary || "Content synthesis encountered an issue and can be restarted."}
        preservedWorkNote="Your approved Discovery brief remains intact."
        retryLabel="Retry Content Architect"
        onRetry={onStart}
        errorDetails={view.safeError ?? undefined}
      />
    );
  }

  // review or complete
  const isApproved = view.state === "complete";

  return (
    <div className="content-stage-view">
      <ArtifactSurface
        title="Content Strategy & Route Architecture"
        artifactTypeName="content plan"
        statusBadge={isApproved ? "Approved" : "Ready for review"}
        isApproved={isApproved}
        canMutate={canMutate}
        finalJsonOutput={finalAgentOutput("content_architect", view.raw)}
        warnings={view.warnings}
        metadata={[
          { label: "Planned Routes", value: String(view.routePlan.length) },
          { label: "Status", value: isApproved ? "Locked & Approved" : "Under Review" },
        ]}
        nextStageName={isApproved ? undefined : "Visual Design Director"}
        onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
        onRevise={isApproved ? undefined : onRevise}
      >
        {(view.positioning || view.userSummary) && (
          <section className="content-strategy-card">
            <p className="eyebrow">Core positioning & strategy</p>
            {view.positioning && <p className="content-positioning">{view.positioning}</p>}
            {view.userSummary && <p className="content-summary">{view.userSummary}</p>}
          </section>
        )}

        {view.routePlan.length > 0 && <SiteMap routes={view.routePlan} />}

        {view.pageContentPacks.length > 0 && (
          <div className="content-section-deck">
            <p className="eyebrow">Page content · {view.pageContentPacks.reduce((sum, pack) => sum + pack.sections.length, 0)} sections</p>
            {view.pageContentPacks.map((pack) => {
              const route = view.routePlan.find((r) => r.routeId === pack.routeId);
              return (
                <div key={pack.routeId} className="content-section-deck-route">
                  <p className="content-section-deck-route-label">{route?.path || pack.routeId}</p>
                  {pack.sections.map((sec) => {
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
              );
            })}
          </div>
        )}

        {view.decisionBasis.length > 0 && (
          <details className="content-decisions-drawer">
            <summary>Strategy decisions · {view.decisionBasis.length}</summary>
            <ul>
              {view.decisionBasis.map((d, idx) => (
                <li key={idx}>
                  <strong>{d.decision.replace(/_/g, " ")}:</strong> {d.value}
                  <span className="content-decision-basis"> ({d.basis.replace(/_/g, " ")})</span>
                  {d.rationale && <p className="content-decision-rationale">{d.rationale}</p>}
                </li>
              ))}
            </ul>
          </details>
        )}

        {view.unresolvedIssues.length > 0 && (
          <div className="content-unresolved-banner" role="note">
            <p className="warnings-title">Unresolved items</p>
            <ul>
              {view.unresolvedIssues.map((issue, idx) => (
                <li key={idx}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </ArtifactSurface>
    </div>
  );
}
