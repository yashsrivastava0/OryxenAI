import type { ComponentChildren } from "preact";

export function HelpDisclosure({ label, children }: { label: string; children: ComponentChildren }) {
  return (
    <details className="help-disclosure">
      <summary aria-label={`About ${label}`} title={`About ${label}`}><span aria-hidden="true">i</span></summary>
      <div className="help-disclosure__content">{children}</div>
    </details>
  );
}
