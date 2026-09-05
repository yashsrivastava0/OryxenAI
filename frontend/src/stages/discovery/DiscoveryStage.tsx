import type { DiscoveryViewModel } from "../../data/adapters/discovery";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { HandoffPanel } from "../../components/HandoffPanel";
import { AttentionPanel } from "../../components/AttentionPanel";
import { StartSurface } from "../../components/StartSurface";
import { UnsupportedPanel } from "../../components/UnsupportedPanel";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (questionId: string, mode: string, value: unknown, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow: () => Promise<void>;
  onRetryDiscovery: () => Promise<void>;
  onStopDiscovery?: () => Promise<void>;
  onApproveBrief: () => Promise<void>;
  onReviseBrief: (revisionRequest: string) => Promise<void>;
  onContinueToContent: () => void;
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
  onApproveBrief,
  onReviseBrief,
  onContinueToContent,
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
      />
    );
  }

  // Brief Review or Complete
  if (view.state === "review" || view.state === "complete") {
    const rawBrief = (view.raw as Record<string, unknown>)?.brief as Record<string, unknown> | undefined;
    const briefTitle = (rawBrief?.title as string) || "Portfolio Discovery Brief";
    const briefMarkdown = (rawBrief?.markdown as string) || (rawBrief?.user_summary as string) || "";
    const isApproved = view.state === "complete";

    return (
      <div className="discovery-brief-view">
        <ArtifactSurface
          title={briefTitle}
          artifactTypeName="brief"
          statusBadge={isApproved ? "Approved" : "Ready for review"}
          isApproved={isApproved}
          canMutate={canMutate}
          markdownContent={briefMarkdown}
          onApprove={onApproveBrief}
          onRevise={onReviseBrief}
        />

        {isApproved && (
          <HandoffPanel
            completedStageName="Discovery Brief"
            nextStageName="Content Architect"
            summary="Your approved brief is now the only input Content Architect receives. Your raw source notes stay behind the Discovery boundary."
            nextDescription="Content Architect defines the routes, positioning, and section-by-section portfolio copy."
            actionLabel="Continue to Content"
            onContinue={onContinueToContent}
          />
        )}
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
