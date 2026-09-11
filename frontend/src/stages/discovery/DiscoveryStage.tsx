import type { DiscoveryViewModel } from "../../data/adapters/discovery";
import type { DiscoveryAnswerSubmission } from "../../data/discovery-answer";
import { finalAgentOutput } from "../../data/final-agent-output";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { AttentionPanel } from "../../components/AttentionPanel";
import { StartSurface } from "../../components/StartSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";
import { ExtractedProfileRail } from "../../components/ExtractedProfileRail";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow: () => Promise<void>;
  onRetryDiscovery: () => Promise<void>;
  onStopDiscovery?: () => Promise<void>;
  /** Approves the brief and starts Content Architect in one action. */
  onApproveAndContinue: () => Promise<void>;
  onReviseBrief: (revisionRequest: string) => Promise<void>;
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
  onApproveAndContinue,
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

  // Brief Review or Complete
  if (view.state === "review" || view.state === "complete") {
    const briefTitle = view.brief?.title || "Portfolio Discovery Brief";
    const briefMarkdown = view.brief?.markdown || view.brief?.userSummary || "";
    const isApproved = view.state === "complete";

    return (
      <div className="discovery-brief-view">
        <div className="discovery-review-layout">
          <ArtifactSurface
            title={briefTitle}
            artifactTypeName="brief"
            statusBadge={isApproved ? "Approved" : "Ready for review"}
            isApproved={isApproved}
            canMutate={canMutate}
            markdownContent={briefMarkdown}
            finalJsonOutput={finalAgentOutput("discovery", view.raw)}
            nextStageName={isApproved ? undefined : "Content Architect"}
            onApproveAndContinue={isApproved ? undefined : onApproveAndContinue}
            onRevise={isApproved ? undefined : onReviseBrief}
          />
          {view.brief && <ExtractedProfileRail profile={view.brief.profile} />}
        </div>
      </div>
    );
  }

  // Conversation flow (questions_ready, answers_in_progress, or working)
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
