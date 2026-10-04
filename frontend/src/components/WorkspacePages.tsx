import type { JourneyStageId } from "../app/url-state";
import { ActionDock } from "./ActionDock";
import { HelpDisclosure } from "./HelpDisclosure";

interface WorkspacePagesProps {
  nextStage: JourneyStageId;
  hasSession: boolean;
  discoveryApproved: boolean;
  contentApproved: boolean;
  previewReady: boolean;
  working: boolean;
  onResume: () => void;
  onGuide: () => void;
}

const STEP_LABELS: Record<JourneyStageId, string> = {
  discover: "Discovery",
  content: "Content Architect",
  studio: "Studio",
};

export function WorkspaceHome({ nextStage, hasSession, discoveryApproved, contentApproved, previewReady, working, onResume, onGuide }: WorkspacePagesProps) {
  const headline = previewReady ? "Your portfolio is ready to review." : working ? "Your portfolio is taking shape." : hasSession ? "Pick up where you left off." : "Begin with your story.";
  const detail = previewReady
    ? "Open the private Studio preview, see how your page reads, and request changes to its words."
    : working
      ? "Your current step is in progress. You can return to it whenever you are ready."
      : "Your answers and approvals stay with this workspace. Each step starts when you choose to continue.";
  return (
    <div className="workspace-page workspace-home">
      <div className="workspace-page__hero">
        <p className="eyebrow">YOUR WORKSPACE / PORTFOLIO</p>
        <h1>{headline}</h1>
        <p>{detail}</p>
        <div className="workspace-home__meta"><span className="status-mark" /> {previewReady ? "Private preview available" : `Next: ${STEP_LABELS[nextStage]}`}</div>
      </div>
      <div className="workspace-home__steps" aria-label="Your progress">
        <div className="workspace-step" data-complete={discoveryApproved}><span>01</span><strong>Discover</strong><p>Tell us what matters, answer focused questions, and approve the brief.</p></div>
        <div className="workspace-step" data-complete={contentApproved}><span>02</span><strong>Shape the content</strong><p>Review the words and structure that will appear on your page.</p></div>
        <div className="workspace-step" data-complete={previewReady}><span>03</span><strong>See your page</strong><p>Open the verified private preview and refine its content.</p></div>
      </div>
      <button type="button" className="workspace-guide-link" onClick={onGuide}>How the process works <span aria-hidden="true">↗</span></button>
      <ActionDock primaryLabel={previewReady ? "Open Studio preview" : `Resume ${STEP_LABELS[nextStage]}`} onPrimary={onResume} note="Your work is saved in this private workspace." />
    </div>
  );
}

export function WorkspaceGuide({ nextStage, onResume }: Pick<WorkspacePagesProps, "nextStage" | "onResume">) {
  return (
    <div className="workspace-page workspace-guide">
      <header className="workspace-page__hero">
        <p className="eyebrow">GUIDE / THREE STEPS</p>
        <h1>From raw material to a page you can see.</h1>
        <p>Bring a résumé, notes, or a rough idea. You make the decisions at each review point.</p>
      </header>
      <div className="guide-steps">
        <section><span className="guide-number">01 / DISCOVERY</span><h2>Find the story</h2><p>Add your background and goals. We ask a few focused questions, then prepare a brief for your review.</p><HelpDisclosure label="Discovery">The brief is a working summary of your source material. You can revise it before approval.</HelpDisclosure></section>
        <section><span className="guide-number">02 / CONTENT</span><h2>Shape the words</h2><p>Review the proposed page copy and decide whether it represents you. Ask for revisions before you approve it.</p><HelpDisclosure label="Content Architect">This step prepares the page’s content and structure. It does not open a live preview yet.</HelpDisclosure></section>
        <section><span className="guide-number">03 / STUDIO</span><h2>See it come together</h2><p>We build and check your one-page portfolio, then show it in a private preview. You can request changes to the words beside the page.</p><HelpDisclosure label="private preview">Only the signed-in owner can open this preview. Public sharing and publishing are not part of the current workflow.</HelpDisclosure></section>
      </div>
      <ActionDock primaryLabel={`Go to ${STEP_LABELS[nextStage]}`} onPrimary={onResume} note="You control when each stage starts." />
    </div>
  );
}
