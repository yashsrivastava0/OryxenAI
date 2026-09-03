export interface PipelineStageInfo {
  number: string;
  name: string;
  discipline: string;
  outcome: string;
  badge: string;
}

export const PIPELINE_STAGES: PipelineStageInfo[] = [
  {
    number: "01",
    name: "Discovery Studio",
    discipline: "Narrative & Intent",
    outcome: "Interactive dialogue that uncovers your authentic background, core projects, and technical strengths.",
    badge: "Interactive Chat",
  },
  {
    number: "02",
    name: "Content Architect",
    discipline: "Information Architecture",
    outcome: "Transforms your brief into multi-page route blueprints, strategic copy, and project case study frameworks.",
    badge: "Structured Plan",
  },
  {
    number: "03",
    name: "Visual Design Director",
    discipline: "Creative & Aesthetic",
    outcome: "Establishes custom typography, motion tokens, color palette, and component systems tailored to your profile.",
    badge: "Visual System",
  },
  {
    number: "04",
    name: "Build Preparation",
    discipline: "Deterministic Compiler",
    outcome: "Validates public scope, packages verified resources, and creates an immutable build bundle.",
    badge: "Immutable ZIP",
  },
  {
    number: "05",
    name: "Code Generator & Preview",
    discipline: "Production Synthesis",
    outcome: "Emits verified React + Vite source code with a sandboxed, live multi-viewport preview.",
    badge: "Verified Preview",
  },
];

export function PipelineStagePreview() {
  return (
    <section className="pipeline-showcase-section" aria-labelledby="pipeline-heading">
      <div className="pipeline-showcase-header">
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
      </div>

      <div className="pipeline-showcase-grid">
        {PIPELINE_STAGES.map((stage) => (
          <article key={stage.number} className="pipeline-showcase-card">
            <div className="pipeline-card-top">
              <span className="pipeline-stage-number">{stage.number}</span>
              <span className="pipeline-stage-discipline">{stage.discipline}</span>
            </div>
            <h3 className="pipeline-stage-name">{stage.name}</h3>
            <p className="pipeline-stage-outcome">{stage.outcome}</p>
            <div className="pipeline-card-bottom">
              <span className="pipeline-stage-badge">{stage.badge}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
