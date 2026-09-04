import { LivingDraftMark } from "./LivingDraftMark";

export function CompletionPanel() {
  return (
    <aside className="completion-panel" aria-labelledby="completion-title">
      <div className="completion-mark" aria-hidden="true"><LivingDraftMark active /></div>
      <p className="eyebrow">Creative handoff / saved</p>
      <h2 id="completion-title">Your direction is approved.</h2>
      <p>The brief, content architecture, and visual direction are preserved as the approved foundation for your portfolio.</p>
      <dl>
        <div><dt>Discovery</dt><dd>approved</dd></div>
        <div><dt>Content</dt><dd>approved</dd></div>
        <div><dt>Direction</dt><dd>approved</dd></div>
      </dl>
      <p className="completion-boundary">Build Preparation and code generation are not part of this authenticated release. No later stage has started.</p>
    </aside>
  );
}
