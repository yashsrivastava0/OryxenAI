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
    discipline: "Narrative Extraction",
    outcome: "Interactive dialogue uncovering your authentic voice, core projects, and technical thesis.",
    badge: "Interactive Chat",
  },
  {
    number: "02",
    name: "Content Architect",
    discipline: "Information Architecture",
    outcome: "Synthesizes multi-page route blueprints, strategic copy, and project case study frameworks.",
    badge: "Adaptive Multi-Call",
  },
  {
    number: "03",
    name: "Visual Design Director",
    discipline: "Aesthetic Direction",
    outcome: "Establishes custom typography roles, motion tokens, color palette, and component systems.",
    badge: "Catalogue Synthesis",
  },
  {
    number: "04",
    name: "Build Preparation",
    discipline: "Compiler Packaging",
    outcome: "Validates public scope, packages verified resources, and creates an immutable deterministic ZIP.",
    badge: "Immutable Handoff",
  },
  {
    number: "05",
    name: "Code Generator & Preview",
    discipline: "Full-Stack Synthesis",
    outcome: "Emits verified React + Vite source code with live multi-viewport sandboxed preview.",
    badge: "Sandboxed Gateway",
  },
];

export function PipelineStagePreview() {
  return (
    <section className="pipeline-showcase-section" aria-labelledby="pipeline-heading">
      <div className="pipeline-showcase-header">
        <div>
          <span className="technical-badge">DELIBERATE TRANSFORMATION</span>
          <h2 id="pipeline-heading" className="pipeline-showcase-title">
            Five specialized stages. Zero automated slop.
          </h2>
        </div>
        <p className="pipeline-showcase-subtitle">
          Every stage produces an explicit artifact for your review and approval before the next stage begins.
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
