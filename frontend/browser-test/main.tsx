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
import { briefReview, questionsReady } from "../src/data/adapters/discovery.fixtures";
import { adaptContentArchitect } from "../src/data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../src/data/adapters/content.fixtures";
import { adaptVisualDesignDirector } from "../src/data/adapters/design";
import { designFixtureReview } from "../src/data/adapters/design.fixtures";
import { adaptBuildPreparation } from "../src/data/adapters/preparation";
import { preparationReady } from "../src/data/adapters/preparation.fixtures";
import { adaptCodeGenerator } from "../src/data/adapters/generation";
import { generationNeedsAttentionWithPreview, generationWorking } from "../src/data/adapters/generation.fixtures";
import "../src/styles/shell.css";

const noop = async () => {};
const journey: JourneyStageVM[] = [
  { id: "discover", ordinal: 1, label: "Discover", sublabel: "UNDERSTAND YOUR STORY", state: "complete", isSelectable: true },
  { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: "review", isSelectable: true },
  { id: "design", ordinal: 3, label: "Design", sublabel: "CRAFT PRESENTATION", state: "locked", isSelectable: false },
  { id: "prepare", ordinal: 4, label: "Prepare", sublabel: "FINALIZE DETAILS", state: "locked", isSelectable: false },
  { id: "generate", ordinal: 5, label: "Generate & Preview", sublabel: "BUILD PORTFOLIO", state: "locked", isSelectable: false },
];

function FixtureFrame({ children }: { children: ComponentChildren }) {
  return (
    <div className="app-shell">
      <header className="app-topbar">
        <a className="app-brand" href="#" aria-label="OryxenAI workspace">
          <span className="brand-wordmark">OryxenAI</span>
          <span className="header-pipe" aria-hidden="true">|</span>
          <span className="header-descriptor">portfolio editorial room</span>
        </a>
        <span className="account-name">Fixture</span>
      </header>
      <main className="app-work-surface">
        <JourneyRail journey={journey} selectedStageId="content" onSelect={() => {}} />
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
