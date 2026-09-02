import type { DiscoveryViewModel } from "../../data/adapters/discovery";
import { ConversationSurface, type AnsweredTurn } from "../../components/ConversationSurface";
import { ArtifactSurface } from "../../components/ArtifactSurface";
import { HandoffPanel } from "../../components/HandoffPanel";
import { AttentionPanel } from "../../components/AttentionPanel";

export interface DiscoveryStageProps {
  view: DiscoveryViewModel | null;
  history: AnsweredTurn[];
  canMutate: boolean;
  onStartDiscovery: (notes: string) => Promise<void>;
  onSubmitAnswer: (questionId: string, mode: string, value: unknown, isComplete: boolean) => Promise<void>;
  onGenerateBriefNow: () => Promise<void>;
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
  onApproveBrief,
  onReviseBrief,
  onContinueToContent,
}: DiscoveryStageProps) {
  if (!view || view.state === "available") {
    return (
      <div className="stage-available-panel">
        <p className="eyebrow">Stage 01 / Discovery</p>
        <h2>Ready to explore your story</h2>
        <p className="stage-desc">
          Discovery asks focused questions to uncover what makes your background unique before shaping the portfolio brief.
        </p>
        <button
          type="button"
          className="btn-primary"
          disabled={!canMutate}
          onClick={() => onStartDiscovery("Let's begin my portfolio.")}
        >
          Begin discovery
        </button>
      </div>
    );
  }

  // Attention / Error
  if (view.state === "attention") {
    return (
      <AttentionPanel
        title="Discovery needs attention"
        summary={view.safeError?.summary || "An issue occurred while processing your discovery answers."}
        preservedWorkNote="All your answered questions and input notes are preserved."
        retryLabel="Retry Discovery"
        onRetry={onGenerateBriefNow}
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
            summary="Your portfolio brief is locked and ready. Content Architect will turn this brief into route architecture and verified page content."
            nextDescription="Content Architect structures the site routes, positioning statement, and verified section-by-section copy."
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
      workingLabel={view.statusText}
      disabled={!canMutate}
      onSubmitAnswer={onSubmitAnswer}
      onGenerateBriefNow={onGenerateBriefNow}
    />
  );
}
