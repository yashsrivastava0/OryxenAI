export interface PipelineStageInfo {
  number: string;
  code: string;
  name: string;
  discipline: string;
  outcome: string;
  badge: string;
  kind: "dialogue" | "structure" | "aesthetic" | "compiler" | "synthesis";
}

export const PIPELINE_STAGES: PipelineStageInfo[] = [
  {
    number: "01",
    code: "STG-01",
    name: "Discovery Studio",
    discipline: "Narrative & Evidence",
    outcome: "Interactive dialogue extracting career milestones, technical depth, and authentic personal voice.",
    badge: "Interactive Turn",
    kind: "dialogue",
  },
  {
    number: "02",
    code: "STG-02",
    name: "Content Architect",
    discipline: "Information Architecture",
    outcome: "Transforms the approved brief into site route blueprints, positioning statements, and deep case studies.",
    badge: "Structured Plan",
    kind: "structure",
  },
  {
    number: "03",
    code: "STG-03",
    name: "Visual Design Director",
    discipline: "Aesthetic Systems",
    outcome: "Establishes bespoke typography scales, tactile motion tokens, and calibrated component palettes.",
    badge: "Visual System",
    kind: "aesthetic",
  },
  {
    number: "04",
    code: "STG-04",
    name: "Build Preparation",
    discipline: "Deterministic Compiler",
    outcome: "Validates public scope, acquires pinned resources, and creates an immutable cryptographic pack.",
    badge: "Immutable Pack",
    kind: "compiler",
  },
  {
    number: "05",
    code: "STG-05",
    name: "Code Generator & Runtime",
    discipline: "Production Synthesis",
    outcome: "Emits verified React + Vite production source with sandboxed, multi-device viewport runtime verification.",
    badge: "Verified Runtime",
    kind: "synthesis",
  },
];

function StageDisciplineIcon({ kind }: { kind: PipelineStageInfo["kind"] }) {
  switch (kind) {
    case "dialogue":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M2.5 3.5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H6.414L3.707 13.207A.5.5 0 0 1 3 12.854V10.5h-.5a1 1 0 0 1-1-1v-6Z" />
        </svg>
      );
    case "structure":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M1 2.75C1 1.784 1.784 1 2.75 1h10.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0 1 13.25 15H2.75A1.75 1.75 0 0 1 1 13.25V2.75Zm1.75-.25a.25.25 0 0 0-.25.25v3.5h11v-3.5a.25.25 0 0 0-.25-.25H2.75ZM13.5 7.75h-5v5.75h4.75a.25.25 0 0 0 .25-.25V7.75Zm-6.5 5.75V7.75h-4.5v5.5c0 .138.112.25.25.25H7Z" />
        </svg>
      );
    case "aesthetic":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm0 1.5a5.5 5.5 0 0 1 5.5 5.5h-11A5.5 5.5 0 0 1 8 2.5Z" />
        </svg>
      );
    case "compiler":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M8.5.5a.75.75 0 0 0-1 0l-6 5.5a.75.75 0 0 0-.25.55v7.5c0 .414.336.75.75.75h12a.75.75 0 0 0 .75-.75v-7.5a.75.75 0 0 0-.25-.55l-6-5.5ZM7.75 7.5v-3.2l4.5 4.125V13h-4.5V7.5Zm-1.5 5.5H2.75V8.425L7.25 4.3V13h-1Z" />
        </svg>
      );
    case "synthesis":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="m9.653 1.696.005-.003a.75.75 0 0 0-.85-.145L2.3 4.802A.75.75 0 0 0 2 5.46v5.08a.75.75 0 0 0 .3.601l6.508 3.254a.75.75 0 0 0 .684 0l6.508-3.254a.75.75 0 0 0 .3-.601V5.46a.75.75 0 0 0-.3-.601L9.653 1.696ZM8 3.208l4.984 2.492L8 8.192 3.016 5.7 8 3.208ZM3.5 7.152l3.75 1.875v4.54L3.5 11.693V7.152Zm5.25 6.415v-4.54l3.75-1.875v4.541l-3.75 1.874Z" />
        </svg>
      );
  }
}

export function PipelineStagePreview() {
  return (
    <section className="pipeline-showcase-section" aria-labelledby="pipeline-heading">
      <header className="pipeline-showcase-header">
        <div className="pipeline-header-badge">
          <span className="pipeline-badge-pip" aria-hidden="true" />
          <span>VERIFIED PIPELINE ARCHITECTURE</span>
        </div>
        <h2 id="pipeline-heading" className="pipeline-showcase-title">
          Five specialized stages. Reviewed by you at every step.
        </h2>
        <p className="pipeline-showcase-subtitle">
          Each stage generates an explicit, reviewable artifact before the next stage unlocks. No blind generation.
        </p>
      </header>

      <div className="pipeline-bento-grid">
        {PIPELINE_STAGES.map((stage) => (
          <article
            key={stage.number}
            className={`pipeline-bento-card bento-${stage.number}`}
            data-kind={stage.kind}
          >
            <div className="bento-card-header">
              <div className="bento-stage-ident">
                <span className="bento-stage-code">{stage.code}</span>
                <span className="bento-discipline-tag">
                  <StageDisciplineIcon kind={stage.kind} />
                  {stage.discipline}
                </span>
              </div>
              <span className="bento-number-watermark" aria-hidden="true">
                {stage.number}
              </span>
            </div>

            <h3 className="bento-stage-name">{stage.name}</h3>
            <p className="bento-stage-outcome">{stage.outcome}</p>

            <div className="bento-card-footer">
              <span className="bento-stage-pill">
                {stage.kind === "dialogue" && <span className="bento-pip-pulse" aria-hidden="true" />}
                {stage.kind === "synthesis" && <span className="bento-pip-active" aria-hidden="true" />}
                {stage.badge}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
