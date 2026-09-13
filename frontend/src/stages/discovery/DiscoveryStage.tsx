import { useState } from "preact/hooks";
import type { DiscoveryViewModel, StructuredProfileVM } from "../../data/adapters/discovery";
import type { DiscoveryAnswerSubmission } from "../../data/discovery-answer";
import { finalAgentOutput } from "../../data/final-agent-output";
import { formatActivityStatus } from "../../data/activity-copy";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { WorkspaceCanvas } from "../../components/WorkspaceCanvas";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { AttentionPanel } from "../../components/AttentionPanel";
import { StartSurface } from "../../components/StartSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow: () => Promise<void>;
  onRetryDiscovery: () => Promise<void>;
  onStopDiscovery?: () => Promise<void>;
  inFlight?: boolean;
  /** Starts Content Architect after approval has already been persisted. */
  onStartNextStage?: () => Promise<void>;
  onApproveAndContinue: () => Promise<void>;
  onReviseBrief: (revisionRequest: string) => Promise<void>;
}

/**
 * The full Markdown brief (`brief.markdown`) is the authoritative artifact,
 * but reading it is now opt-in: it sits behind an explicit "Read full brief"
 * toggle, collapsed by default, so the decision layer (userSummary + the
 * Approve/Revise actions) stays above the fold rather than being buried
 * under a wall of Markdown. This replicates the exact interaction pattern of
 * BuildPreparationStage's `BriefDrawer` (a local `useState(false)` toggle
 * with a `btn-quiet` show/hide button and a collapsed character-count hint).
 */
function BriefMarkdownDrawer({ markdown }: { markdown: string }) {
  const [open, setOpen] = useState(false);
  if (!markdown) return null;
  return (
    <section className="preparation-brief-card discovery-brief-drawer">
      <div className="preparation-brief-card-head">
        <div>
          <p className="eyebrow">FULL BRIEF</p>
          <h2>Complete portfolio brief</h2>
        </div>
        <button type="button" className="btn-quiet" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide full brief" : "Read full brief"}
        </button>
      </div>
      {open ? (
        <div className="preparation-brief-body">
          <SafeMarkdown content={markdown} />
        </div>
      ) : (
        <p className="preparation-brief-collapsed-hint">
          {Math.round(markdown.length / 1000)}k characters — the complete portfolio brief, collapsed by default.
        </p>
      )}
    </section>
  );
}

/**
 * A condensed version of the ExtractedProfileRail's structured facts: name,
 * current title, experience count, and skills count — every value read
 * directly from the real `brief.profile` fields, never invented. Rendered
 * only when at least one fact is present so an empty profile leaves no
 * hollow shell.
 */
function CondensedProfileFacts({ profile }: { profile: StructuredProfileVM }) {
  const hasIdentity = Boolean(profile.name || profile.currentTitle);
  const experienceCount = profile.experience.length;
  const skillsCount = profile.skills.length;
  if (!hasIdentity && experienceCount === 0 && skillsCount === 0) return null;

  return (
    <div className="discovery-profile-facts">
      <p className="eyebrow">Extracted from your material</p>
      {hasIdentity && (
        <div className="discovery-profile-identity">
          {profile.name && <strong>{profile.name}</strong>}
          {profile.currentTitle && <span>{profile.currentTitle}</span>}
        </div>
      )}
      <dl className="content-activity-facts">
        <div>
          <dt>Experience entries</dt>
          <dd>{experienceCount}</dd>
        </div>
        <div>
          <dt>Skills</dt>
          <dd>{skillsCount}</dd>
        </div>
      </dl>
    </div>
  );
}

export function DiscoveryStage({
  view,
  history,
  canMutate,
  onStartDiscovery,
  onSubmitAnswer,
  onGenerateBriefNow,
  onRetryDiscovery,
  onStopDiscovery,
  inFlight = false,
  onApproveAndContinue,
  onStartNextStage,
  onReviseBrief,
}: DiscoveryStageProps) {
  if (!view) {
    return (
      <div className="agent-working-proof" role="status" aria-live="polite" aria-busy="true">
        <p className="eyebrow">Discovery / restoring</p>
        <h2>Opening your last confirmed proof</h2>
        <div className="working-rule" aria-hidden="true"><span /></div>
        <p>Your saved answers and brief remain on the server.</p>
      </div>
    );
  }

  if (view.state === "available") {
    return <StartSurface onStart={onStartDiscovery} disabled={!canMutate} />;
  }

  if (view.state === "unsupported") {
    return <UnsupportedPanel stageName="Discovery" statusText={view.statusText} />;
  }

  // Attention / Error
  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Discovery needs attention"
        summary={view.safeError?.summary || "An issue occurred while processing your discovery answers."}
        preservedWorkNote="All your answered questions and input notes are preserved."
        retryLabel="Retry Discovery"
        onRetry={onRetryDiscovery}
        errorDetails={view.safeError ?? undefined}
      />
    );
  }

  // Brief Review or Complete — the validated-brief decision layer, migrated
  // into the shared two-zone WorkspaceCanvas.
  if (view.state === "review" || view.state === "complete") {
    const briefTitle = view.brief?.title || "Portfolio Discovery Brief";
    const briefMarkdown = view.brief?.markdown || "";
    const userSummary = view.brief?.userSummary || "";
    const isApproved = view.state === "complete";

    // Derive the live activity line from the stage's real durable status via
    // the shared pure formatter — composed here where the stage is known, not
    // inside the generic WorkspaceCanvas shell.
    const rawStatus =
      view.raw && typeof view.raw === "object" && "status" in view.raw
        ? String((view.raw as { status?: unknown }).status ?? "")
        : "";
    const activity = formatActivityStatus("discovery", rawStatus);

    const rail = (
      <div className="content-activity-rail">
        <p className="eyebrow">Journey · Stage 01 of 05</p>
        <p className="workspace-journey-position">Discovery</p>
        <p
          className={`oxa-activity-line${activity.working ? " is-active" : ""}`}
          role="status"
          aria-live="polite"
        >
          {activity.text}
        </p>
        {view.brief && <CondensedProfileFacts profile={view.brief.profile} />}
      </div>
    );

    const artifact = (
      <ArtifactSurface
        title={briefTitle}
        artifactTypeName="brief"
        statusBadge={isApproved ? "Approved" : "Ready for review"}
        isApproved={isApproved}
        canMutate={canMutate}
        finalJsonOutput={finalAgentOutput("discovery", view.raw)}
        nextStageName="Content Architect"
        onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
        onStartNextStage={isApproved ? onStartNextStage : undefined}
        nextStageInFlight={inFlight}
        onRevise={isApproved ? undefined : onReviseBrief}
      >
        {userSummary && (
          <section className="discovery-brief-summary">
            <p className="eyebrow">Summary</p>
            <p className="discovery-summary-text">{userSummary}</p>
          </section>
        )}
        {/* Full Markdown brief moved BEHIND a collapsed-by-default disclosure
            so the summary + Approve/Revise actions stay above the fold. */}
        <BriefMarkdownDrawer markdown={briefMarkdown} />
      </ArtifactSurface>
    );

    return (
      <div className="discovery-brief-view">
        <WorkspaceCanvas
          railLabel="Stage 01 / Discovery"
          ariaLabel="Discovery brief workspace"
          rail={rail}
          artifact={artifact}
        />
      </div>
    );
  }

  // Conversation flow (questions_ready, answers_in_progress, or working) —
  // interview mechanics intentionally unchanged.
  return (
    <ConversationSurface
      questions={view.currentQuestions}
      history={history}
      isWorking={view.state === "working"}
      job={view.job}
      workingLabel={view.statusText}
      disabled={!canMutate}
      onSubmitAnswer={onSubmitAnswer}
      onGenerateBriefNow={onGenerateBriefNow}
      onRetryStalled={onRetryDiscovery}
      onStop={onStopDiscovery}
    />
  );
}
