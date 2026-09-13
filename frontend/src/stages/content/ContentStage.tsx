import type { ContentViewModel } from "../../data/adapters/content";
import { finalAgentOutput } from "../../data/final-agent-output";
import { formatActivityStatus } from "../../data/activity-copy";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { WorkspaceCanvas } from "../../components/WorkspaceCanvas";
import { AttentionPanel } from "../../components/AttentionPanel";
import { ProgressSurface } from "../../components/ProgressSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { AsyncActionButton } from "../../components/AsyncActionButton";
import { PeekCard } from "../../components/PeekCard";
import { ContentPackExplorer } from "../../components/ContentPackExplorer";

export interface ContentStageProps {
  view: ContentViewModel | null;
  canMutate: boolean;
  onStart: () => Promise<void>;
  /** Starts Visual Design Director after approval has already been persisted. */
  onApproveAndContinue: () => Promise<void>;
  onStartNextStage?: () => Promise<void>;
  onRevise: (revisionRequest: string) => Promise<void>;
  onStop?: () => Promise<void>;
  inFlight?: boolean;
}

export function ContentStage({
  view,
  canMutate,
  onStart,
  onApproveAndContinue,
  onStartNextStage,
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

  // Derive the live activity line from the stage's real durable status via
  // the shared pure formatter — no hardcoded stage copy inside the generic
  // WorkspaceCanvas shell, composed here where the stage is known.
  const rawStatus =
    view.raw && typeof view.raw === "object" && "status" in view.raw
      ? String((view.raw as { status?: unknown }).status ?? "")
      : "";
  const activity = formatActivityStatus("content_architect", rawStatus, {
    stale: false,
  });
  const routeCount = view.routePlan.length;
  const sectionCount = view.pageContentPacks.reduce((sum, pack) => sum + pack.sections.length, 0);

  const rail = (
    <div className="content-activity-rail">
      <p className="eyebrow">Journey · Stage 02 of 05</p>
      <p className="workspace-journey-position">Content Architect</p>
      <p
        className={`oxa-activity-line${activity.working ? " is-active" : ""}`}
        role="status"
        aria-live="polite"
      >
        {activity.text}
      </p>
      <dl className="content-activity-facts">
        <div>
          <dt>Planned routes</dt>
          <dd>{routeCount}</dd>
        </div>
        <div>
          <dt>Content sections</dt>
          <dd>{sectionCount}</dd>
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
      nextStageName="Visual Design Director"
      onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
      onStartNextStage={isApproved ? onStartNextStage : undefined}
      nextStageInFlight={inFlight}
      onRevise={isApproved ? undefined : onRevise}
    >
      {(view.positioning || view.userSummary) && (
        <section className="content-strategy-card">
          <p className="eyebrow">Core positioning & strategy</p>
          {view.positioning && <p className="content-positioning">{view.positioning}</p>}
          {view.userSummary && <p className="content-summary">{view.userSummary}</p>}
        </section>
      )}

      {(view.routePlan.length > 0 || view.pageContentPacks.length > 0) && (
        <ContentPackExplorer routePlan={view.routePlan} pageContentPacks={view.pageContentPacks} />
      )}

      {view.decisionBasis.length > 0 && (
        <section className="content-decisions-panel" aria-label="Strategy decisions">
          <p className="eyebrow">Strategy decisions · {view.decisionBasis.length}</p>
          <ul className="content-decisions-list">
            {view.decisionBasis.map((d, idx) => (
              <PeekCard
                key={idx}
                eyebrow={d.basis.replace(/_/g, " ")}
                title={d.decision.replace(/_/g, " ")}
                summary={d.value}
              >
                {d.value && <p className="content-decision-value">{d.value}</p>}
                {d.rationale && <p className="content-decision-rationale">{d.rationale}</p>}
              </PeekCard>
            ))}
          </ul>
        </section>
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
  );

  return (
    <div className="content-stage-view">
      <WorkspaceCanvas
        railLabel="Stage 02 / Content Architect"
        ariaLabel="Content Architect workspace"
        rail={rail}
        artifact={artifact}
      />
    </div>
  );
}
