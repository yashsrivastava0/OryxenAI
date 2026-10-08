import { render, type ComponentChildren } from "preact";
import { useRef, useState } from "preact/hooks";
import { JourneyRail, type JourneyStageVM } from "../src/components/JourneyRail";
import { OutputInspector } from "../src/components/OutputInspector";
import { StartSurface } from "../src/components/StartSurface";
import { StageContextStrip } from "../src/components/StageContextStrip";
import { DiscoveryStage } from "../src/stages/discovery/DiscoveryStage";
import { ContentStage } from "../src/stages/content/ContentStage";
import { StudioStage } from "../src/stages/studio/StudioStage";
import { adaptStudio } from "../src/data/adapters/studio";
import { studioFixtures } from "./studio-fixtures";
import { adaptDiscovery } from "../src/data/adapters/discovery";
import { approved, briefReview, questionsMcqReady, questionsReady, questionsTextReady } from "../src/data/adapters/discovery.fixtures";
import { AppShell } from "../src/app/AppShell";
import { adaptContentArchitect } from "../src/data/adapters/content";
import { contentFixtureApproved, contentFixtureReview } from "../src/data/adapters/content.fixtures";
// The product template loads these shared files before shell.css. Keep the
// browser fixture honest so its local preview uses the same design tokens.
import "../../src/oryxenai/auth/static/tokens.css";
import "../../src/oryxenai/auth/static/motion.css";
import "../src/styles/shell.css";
// @ts-expect-error test-only virtual module exposes the actual server-owned catalog.
import themeCatalog from "virtual:theme-catalog";

const noop = async () => {};

type FixtureStage = "discover" | "content" | "studio";

function stageOf(fixture: string): FixtureStage {
  if (fixture.startsWith("discovery-")) return "discover";
  if (fixture.startsWith("studio-")) return "studio";
  return "content";
}

function getJourney(stage: FixtureStage): JourneyStageVM[] {
  return [
    { id: "discover", ordinal: 1, label: "Explore", sublabel: "UNDERSTAND YOUR STORY", state: stage === "discover" ? "current" : "complete", isSelectable: true },
    { id: "content", ordinal: 2, label: "Content", sublabel: "SHAPE NARRATIVE", state: stage === "discover" ? "locked" : stage === "studio" ? "complete" : "review", isSelectable: stage !== "discover" },
    { id: "studio", ordinal: 3, label: "Studio", sublabel: "BUILD YOUR PAGE", state: stage === "studio" ? "complete" : "locked", isSelectable: stage === "studio" },
  ];
}

function FixtureFrame({ children }: { children: ComponentChildren }) {
  const fixture = new URLSearchParams(window.location.search).get("fixture") ?? "discovery-input";
  const stage = stageOf(fixture);
  const isDiscover = stage === "discover";

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <a className="app-brand" href="#" aria-label="OryxenAI workspace">
          <span className="brand-wordmark">OryxenAI</span>
          <span className="header-pipe" aria-hidden="true">|</span>
          <span className="header-descriptor">IDEAS TO IMPACT</span>
        </a>
        <JourneyRail journey={getJourney(stage)} selectedStageId={stage} onSelect={() => {}} />
        <div className="app-topbar-actions">
          <span className="topbar-motto">A MORE THOUGHTFUL CREATIVE FUTURE</span>
          <span className="topbar-dot" aria-hidden="true">•</span>
          <div className="account-menu">
            <span className="account-monogram">Y</span>
          </div>
        </div>
      </header>

      <StageContextStrip
        stageName={isDiscover ? "Explore" : stage === "studio" ? "Studio" : "Content"}
        stagePurpose={isDiscover
          ? "Capture your goal, audience, key message and any reference material."
          : stage === "studio"
            ? "Review your live page and ask for changes to its words."
            : "Shape the narrative structure and page outlines."}
        tagline="A STRONG START LEADS FURTHER"
      />

      <main className="app-work-surface">
        <div className="app-stage-layout">
          <section id="workspace-stage" className="stage-frame" data-stage={stage} tabIndex={-1}>
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
  if (fixture === "discovery-input") {
    return (
      <StartSurface
        onStart={noop}
        onExtractDocument={async () => ({
          name: "resume.md",
          text: "# My resume",
          characters: 11,
          page_count: null,
          warnings: [],
        })}
      />
    );
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
        onSubmitAnswer={async (answer) => {
          (window as unknown as { __capturedDiscoveryAnswer?: unknown }).__capturedDiscoveryAnswer = answer;
        }}
        onGenerateBriefNow={noop}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-question-queued") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(questionsMcqReady)}
        history={[]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={async () => { await new Promise((resolve) => window.setTimeout(resolve, 1200)); }}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-questions-working" || fixture === "discovery-brief-working") {
    const jobs = [{ id: "timing-job", kind: "discovery.build", status: "running", created_at: new Date(Date.now() - 18000).toISOString(), started_at: new Date(Date.now() - 17000).toISOString(), heartbeat_at: new Date().toISOString() }];
    return <DiscoveryStage view={adaptDiscovery({ ...questionsMcqReady, status: fixture === "discovery-questions-working" ? "questions_running" : "brief_running" }, jobs)} history={[]} canMutate onStartDiscovery={noop} onSubmitAnswer={noop as never} onRetryDiscovery={noop} onApproveAndContinue={noop} onReviseBrief={noop} />;
  }
  if (fixture === "discovery-question-save-fails") {
    return (
      <DiscoveryStage
        view={adaptDiscovery(questionsMcqReady)}
        history={[]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={async () => {
          await new Promise((resolve) => window.setTimeout(resolve, 150));
          throw new Error("Save failed");
        }}
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
  if (fixture === "discovery-question-palette" || fixture === "discovery-question-palette-many") {
    return (
      <DiscoveryStage
        view={adaptDiscovery({
          status: "questions_ready",
          operation_a: {
            items: [{ ...themeCatalog, options: fixture.endsWith("-many")
              ? Array.from({ length: 24 }, (_, index) => ({ ...themeCatalog.options[index % themeCatalog.options.length], id: `future_${index}`, label: `Portfolio look ${index + 1}` }))
              : themeCatalog.options }],
          },
          answers: { items: {} },
        })}
        history={[]}
        canMutate
        onStartDiscovery={noop}
        onSubmitAnswer={noop as never}
        onRetryDiscovery={noop}
        onApproveAndContinue={noop}
        onReviseBrief={noop}
      />
    );
  }
  if (fixture === "discovery-attention") {
    return (
      <DiscoveryStage
        view={adaptDiscovery({
          status: "needs_attention",
          latest_error: {
            code: "MODEL_OUTPUT_INVALID",
            message: "The model returned output that did not satisfy the required structure.",
            provider_label: "Experiential Labs",
            operation_label: "build_or_revise_brief",
            support_reference: "model-a3d7ea9e7071",
            retryable: false,
          },
        })}
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
  if (fixture === "content-working") {
    return <ContentStage view={adaptContentArchitect({ ...contentFixtureReview, status: "build_running", elapsed_seconds: 22 }, true)} canMutate onStart={noop} onApproveAndContinue={noop} onRevise={noop} />;
  }
  if (fixture === "content-approved") {
    return <ContentStage view={adaptContentArchitect(contentFixtureApproved, true)} canMutate onStart={noop} onApproveAndContinue={noop} onRevise={noop} />;
  }
  if (fixture.startsWith("studio-")) return <StudioFixture name={fixture} />;
  return <p>Unknown fixture</p>;
}

const samplePreview = async (versionId: string) => ({
  url: `/studio-sample/index.html?v=${encodeURIComponent(versionId)}`,
  expires_at: "2099-01-01T00:00:00+00:00",
  expires_in_seconds: 1800,
  version_id: versionId,
  version_number: null,
});

// A stateful stand-in for the API so the whole chat -> build -> new version
// flow can be exercised in a real browser without a backend.
function InteractiveStudio({ initial }: { initial: unknown }) {
  const [view, setView] = useState(() => adaptStudio(initial, true));
  const counter = useRef(2);
  const send = async (message: string) => {
    const next = counter.current;
    counter.current += 1;
    const base = view;
    setView(adaptStudio(studioFixtures.building(initial, message, next, "planning"), true));
    window.setTimeout(() => setView(adaptStudio(studioFixtures.building(initial, message, next, "generating"), true)), 700);
    window.setTimeout(() => setView(adaptStudio(studioFixtures.afterChange(initial, message, next, base), true)), 1600);
  };
  return (
    <StudioStage
      view={view}
      contentApproved
      canMutate
      inFlight={false}
      loadPreview={samplePreview}
      onStart={noop}
      onStop={async () => setView(adaptStudio(initial, true))}
      onSend={send}
      onRestore={noop}
    />
  );
}

function StudioFixture({ name }: { name: string }) {
  const envelope = studioFixtures.byName(name);
  if (name === "studio-interactive") return <InteractiveStudio initial={envelope} />;
  return (
    <StudioStage
      view={adaptStudio(envelope, true)}
      contentApproved
      canMutate
      inFlight={false}
      loadPreview={samplePreview}
      onStart={noop}
      onStop={noop}
      onSend={noop}
      onRestore={noop}
    />
  );
}

// Raw API payloads for the Python-side fake backend (tests/browser).
(window as unknown as { __fixtures: unknown }).__fixtures = {
  discoveryApproved: approved,
  contentReview: contentFixtureReview,
  contentApproved: contentFixtureApproved,
};

// authorizedFetch in production throws on a non-2xx response; mirror that so the
// real AppShell/API-client error paths run against a fake backend.
async function fixtureFetch(url: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let body: { error?: { code?: string; message?: string; details?: unknown } } | null = null;
    try {
      body = await response.clone().json();
    } catch {
      body = null;
    }
    throw {
      code: body?.error?.code ?? "REQUEST_FAILED",
      status: response.status,
      message: body?.error?.message ?? "The request could not be completed.",
      details: body?.error?.details,
    };
  }
  return response;
}

if (new URLSearchParams(window.location.search).get("app") === "1") {
  render(
    <AppShell
      authorizedFetch={fixtureFetch}
      me={{
        id: "user-e2e",
        username: "yash",
        role: "user",
        status: "active",
        onboarding_required: false,
        admin_available: false,
        can_create_portfolio: true,
        portfolio_session_id: "session-e2e",
      }}
      serverSessionId="session-e2e"
    />,
    document.getElementById("app")!,
  );
} else {
  render(<FixtureFrame><StageFixture /></FixtureFrame>, document.getElementById("app")!);
}
