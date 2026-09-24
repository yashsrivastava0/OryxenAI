import { render, type ComponentChildren } from "preact";
import { JourneyRail, type JourneyStageVM } from "../src/components/JourneyRail";
import { OutputInspector } from "../src/components/OutputInspector";
import { StartSurface } from "../src/components/StartSurface";
import { StageContextStrip } from "../src/components/StageContextStrip";
import { DiscoveryStage } from "../src/stages/discovery/DiscoveryStage";
import { ContentStage } from "../src/stages/content/ContentStage";
import { adaptDiscovery } from "../src/data/adapters/discovery";
import { briefReview, questionsMcqReady, questionsReady, questionsTextReady } from "../src/data/adapters/discovery.fixtures";
import { adaptContentArchitect } from "../src/data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../src/data/adapters/content.fixtures";
// The product template loads these shared files before shell.css. Keep the
// browser fixture honest so its local preview uses the same design tokens.
import "../../src/oryxenai/auth/static/tokens.css";
import "../../src/oryxenai/auth/static/motion.css";
import "../src/styles/shell.css";

const noop = async () => {};

function getJourney(isDiscover: boolean): JourneyStageVM[] {
  return [
    { id: "discover", ordinal: 1, label: "Discover", sublabel: "UNDERSTAND YOUR STORY", state: isDiscover ? "current" : "complete", isSelectable: true },
    { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: isDiscover ? "locked" : "review", isSelectable: !isDiscover },
  ];
}

function FixtureFrame({ children }: { children: ComponentChildren }) {
  const fixture = new URLSearchParams(window.location.search).get("fixture") ?? "discovery-input";
  const isDiscover = fixture.startsWith("discovery-");

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <a className="app-brand" href="#" aria-label="OryxenAI workspace">
          <span className="brand-wordmark">OryxenAI</span>
          <span className="header-pipe" aria-hidden="true">|</span>
          <span className="header-descriptor">IDEAS TO IMPACT</span>
        </a>
        <JourneyRail journey={getJourney(isDiscover)} selectedStageId={isDiscover ? "discover" : "content"} onSelect={() => {}} />
        <div className="app-topbar-actions">
          <span className="topbar-motto">A MORE THOUGHTFUL CREATIVE FUTURE</span>
          <span className="topbar-dot" aria-hidden="true">•</span>
          <div className="account-menu">
            <span className="account-monogram">Y</span>
          </div>
        </div>
      </header>

      <StageContextStrip
        stageName={isDiscover ? "Discover" : "Content"}
        stagePurpose={isDiscover
          ? "Capture your goal, audience, key message and any reference material."
          : "Shape the narrative structure and page outlines."}
        tagline="A STRONG START LEADS FURTHER"
      />

      <main className="app-work-surface">
        <div className="app-stage-layout">
          <section id="workspace-stage" className="stage-frame" data-stage={isDiscover ? "discover" : "content"} tabIndex={-1}>
            <div className="stage-transition-layer">{children}</div>
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
  if (fixture === "discovery-input") return <StartSurface onStart={noop} />;

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
    return <ContentStage view={adaptContentArchitect(contentFixtureApproved, true)} canMutate onStart={noop} onApproveAndContinue={noop} onRevise={noop} />;
  }
  return <p>Unknown fixture</p>;
}

render(<FixtureFrame><StageFixture /></FixtureFrame>, document.getElementById("app")!);
