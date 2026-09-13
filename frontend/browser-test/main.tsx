import { render, type ComponentChildren } from "preact";
import { JourneyRail, type JourneyStageVM } from "../src/components/JourneyRail";
import { OutputInspector } from "../src/components/OutputInspector";
import { StartSurface } from "../src/components/StartSurface";
import { DiscoveryStage } from "../src/stages/discovery/DiscoveryStage";
import { ContentStage } from "../src/stages/content/ContentStage";
import { DesignStage } from "../src/stages/design/DesignStage";
import { BuildPreparationStage } from "../src/stages/preparation/BuildPreparationStage";
import { GenerationStage } from "../src/stages/generation/GenerationStage";
import { adaptDiscovery } from "../src/data/adapters/discovery";
import { briefReview, questionsMcqReady, questionsReady, questionsTextReady } from "../src/data/adapters/discovery.fixtures";
import { adaptContentArchitect } from "../src/data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../src/data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../src/data/adapters/design";
import { designFixtureReview } from "../src/data/adapters/design.fixtures";
import { adaptBuildPreparation } from "../src/data/adapters/preparation";
import { preparationReady } from "../src/data/adapters/preparation.fixtures";
import { adaptCodeGenerator } from "../src/data/adapters/generation";
import { generationNeedsAttentionWithPreview, generationWorking } from "../src/data/adapters/generation.fixtures";
import { StageContextStrip } from "../src/components/StageContextStrip";
import "../src/styles/shell.css";

const noop = async () => {};

function getJourney(isDiscover: boolean): JourneyStageVM[] {
  return [
    { id: "discover", ordinal: 1, label: "Discover", sublabel: "UNDERSTAND YOUR STORY", state: isDiscover ? "current" : "complete", isSelectable: true },
    { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: isDiscover ? "locked" : "review", isSelectable: !isDiscover },
    { id: "design", ordinal: 3, label: "Design", sublabel: "CRAFT PRESENTATION", state: "locked", isSelectable: false },
    { id: "prepare", ordinal: 4, label: "Prepare", sublabel: "FINALIZE DETAILS", state: "locked", isSelectable: false },
    { id: "generate", ordinal: 5, label: "Generate & Preview", sublabel: "BUILD PORTFOLIO", state: "locked", isSelectable: false },
  ];
}

function FixtureFrame({ children }: { children: ComponentChildren }) {
  const fixture = new URLSearchParams(window.location.search).get("fixture") ?? "discovery-input";
  const isDiscover = fixture.startsWith("discovery-");
  const journey = getJourney(isDiscover);

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <a className="app-brand" href="#" aria-label="OryxenAI workspace">
          <span className="brand-wordmark">OryxenAI</span>
          <span className="header-pipe" aria-hidden="true">|</span>
          <span className="header-descriptor">IDEAS TO IMPACT</span>
        </a>
        <JourneyRail journey={journey} selectedStageId={isDiscover ? "discover" : "content"} onSelect={() => {}} />
        <div className="app-topbar-actions">
          <span className="topbar-motto">A MORE THOUGHTFUL CREATIVE FUTURE</span>
          <span className="topbar-dot" aria-hidden="true">•</span>
          <div className="account-menu">
            <span className="account-monogram">Y</span>
          </div>
        </div>
      </header>

      {isDiscover ? (
        <StageContextStrip
          stageName="Discover"
          stagePurpose="Capture your goal, audience, key message and any reference material."
          tagline="A STRONG START LEADS FURTHER"
        />
      ) : (
        <StageContextStrip
          stageName="Content"
          stagePurpose="Shape the narrative structure and page outlines."
          tagline="A STRONG START LEADS FURTHER"
        />
      )}

      <main className="app-work-surface">
        <div className="app-stage-layout">
          <section id="workspace-stage" className="stage-frame" tabIndex={-1}>
            {children}
          </section>
          <OutputInspector
            entries={[{ id: "content", label: "Content Architect", state: "review", agentOutput: null }]}
            activeStage="content"
            enabled={new URLSearchParams(window.location.search).get("inspector") === "1"}
          />
        </div>
      </main>
    </div>
  );
}

function StageFixture() {
  const fixture = new URLSearchParams(window.location.search).get("fixture") ?? "discovery-input";
  if (fixture === "discovery-input") {
    return <StartSurface onStart={noop} />;
  }
  if (fixture === "discovery-question-mcq") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(questionsMcqReady)}
        history={[
          {
            questionId: "q_prior",
            questionText: "What was your most recent principal engineering impact?",
            answerText: "Designed and rolled out a zero-downtime ledger engine handling $4B daily volume.",
          },
        ]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={noop as never}
        onGenerateBriefNow={noop}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-question-text") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(questionsTextReady)}
        history={[
          { questionId: "q_prior_1", questionText: "What was your most recent title?", answerText: "Principal Systems Architect" },
          { questionId: "q_prior_2", questionText: "What primary domain is this portfolio for?", answerText: "Fintech & low-latency execution" },
        ]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={noop as never}
        onGenerateBriefNow={noop}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-question-single") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(questionsReady)}
        history={[]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={noop as never}
        onGenerateBriefNow={noop}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-review") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(briefReview)}
        history={[]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={noop as never}
        onGenerateBriefNow={noop}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "content-review") {
    return <ContentStage view={adaptContentArchitect(contentFixtureReview, true)} canMutate onStart={noop} onApproveAndContinue={noop} onRevise={noop} />;
  }
  if (fixture === "content-approved") {
    return <ContentStage view={adaptContentArchitect(contentFixtureApproved, true)} canMutate onStart={noop} onApproveAndContinue={noop} onStartNextStage={noop} onRevise={noop} />;
  }
  if (fixture === "design-storyboard") {
    return <DesignStage view={adaptVisualDesignDirector(designFixtureReview, true)} canMutate onStart={noop} onApproveAndContinue={noop} onRevise={noop} />;
  }
  if (fixture === "preparation-ready") {
    return <BuildPreparationStage view={adaptBuildPreparation(preparationReady, true, true)} canMutate onStart={noop} onRegenerate={noop} />;
  }
  if (fixture === "generation-working") {
    return <GenerationStage view={adaptCodeGenerator(generationWorking, true, [])} canMutate onStart={noop} onRetry={noop} onRegenerate={noop} />;
  }
  if (fixture === "generation-attention") {
    const jobs = [{ id: "job-verify-failed", kind: "code_generator.verify_and_preview", status: "failed", attempt: 1, max_attempts: 3 }];
    return <GenerationStage view={adaptCodeGenerator(generationNeedsAttentionWithPreview, true, jobs)} canMutate onStart={noop} onRetry={noop} onRegenerate={noop} />;
  }
  return <p>Unknown fixture</p>;
}

render(<FixtureFrame><StageFixture /></FixtureFrame>, document.getElementById("app")!);
