export interface Archetype {
  id: string;
  code: string;
  title: string;
  shortLabel: string;
  tagline: string;
  draftText: string;
}

export const ARCHETYPES: Archetype[] = [
  {
    id: "systems-architect",
    code: "SYS-01",
    title: "Systems Architect",
    shortLabel: "Systems",
    tagline: "High-scale distributed backends, low-latency streaming & infrastructure.",
    draftText: `Senior Systems Architect specializing in distributed backends, real-time data pipelines, and high-availability infrastructure.

Key highlights & milestones:
- Designed an event-driven telemetry ingest engine processing 250k events/sec on Rust and Kafka with sub-20ms p99 latency.
- Migrated an enterprise monolith to decoupled Go microservices, reducing incident MTTR by 65%.
- Authored open-source storage indexing engines and zero-allocation networking libraries.

Target portfolio direction: Technical depth with system architecture diagrams, failure-mode analyses, and verifiable performance metrics.`,
  },
  {
    id: "creative-technologist",
    code: "CRT-02",
    title: "Creative Technologist",
    shortLabel: "Creative",
    tagline: "Kinetic UI, WebGL shaders, tactile design systems & dynamic interaction.",
    draftText: `Creative Technologist and Interaction Designer bridging engineering precision with visual aesthetics.

Key highlights & milestones:
- Built WebGL & Three.js interactive graphics recognized across design and frontend developer communities.
- Architected fluid component systems with custom spring physics, tactile micro-interactions, and 60fps rendering.
- Researched kinetic typography and physical simulation engines compiled to WebAssembly.

Target portfolio direction: Visually commanding, tactile typography with dark mode nuances, fluid motion, and interactive case studies.`,
  },
  {
    id: "product-lead",
    code: "PRD-03",
    title: "Founding Product Engineer",
    shortLabel: "Product",
    tagline: "0-to-1 product strategy, full-stack delivery, and user growth.",
    draftText: `Founding Product Engineer and Technical Lead building products from concept to scale.

Key highlights & milestones:
- Shipped the core platform for a seed-stage developer startup, growing to 40,000 active developers in under 12 months.
- Led end-to-end delivery: React/TypeScript frontend, resilient async job queues, and multi-tenant PostgreSQL.
- Drove user research, customer discovery, and weekly release cadence.

Target portfolio direction: Product-focused clarity detailing architectural decisions, UX trade-offs, and measurable outcomes.`,
  },
  {
    id: "research-scientist",
    code: "RES-04",
    title: "Research Engineer",
    shortLabel: "AI / ML",
    tagline: "Generative models, agentic workflows & inference optimization.",
    draftText: `Applied AI Researcher and ML Engineer working on foundation models, agentic execution, and inference optimization.

Key highlights & milestones:
- Published papers at top conferences on sparse attention and speculative decoding algorithms.
- Optimized production LLM serving stacks with custom CUDA kernels and quantization, reducing latency by 4x.
- Built evaluation suites and reproducibility harnesses for multi-agent reasoning benchmarks.

Target portfolio direction: Clean, rigorous presentation with research abstracts, interactive benchmarks, and live code artifacts.`,
  },
];

export const QUICK_STARTERS = [
  "Full-Stack Engineer (React, TypeScript, Python FastAPI)",
  "Staff Design Engineer focusing on design systems",
  "DevOps / SRE Architect (Kubernetes & Terraform)",
  "Data Engineer building real-time warehouses",
];

export interface ArchetypeSelectorProps {
  selectedId: string | null;
  onSelectArchetype: (archetype: Archetype) => void;
  onSelectQuickStarter: (starterText: string) => void;
  disabled?: boolean;
}

export function ArchetypeSelector({
  selectedId,
  onSelectArchetype,
  onSelectQuickStarter,
  disabled = false,
}: ArchetypeSelectorProps) {
  return (
    <div className="archetype-control-bar" aria-label="Role archetypes">
      <div className="archetype-segmented-track" role="radiogroup" aria-label="Role template chips">
        <span className="archetype-lead-label">TEMPLATE:</span>
        {ARCHETYPES.map((arch) => {
          const isSelected = selectedId === arch.id;
          return (
            <button
              key={arch.id}
              type="button"
              className={`archetype-chip ${isSelected ? "archetype-chip-active" : ""}`}
              onClick={() => onSelectArchetype(arch)}
              disabled={disabled}
              role="radio"
              aria-checked={isSelected}
              title={`${arch.title} — ${arch.tagline}`}
            >
              <span className="archetype-chip-code">{arch.code}</span>
              <span className="archetype-chip-name">{arch.shortLabel}</span>
              {isSelected && <span className="archetype-chip-dot" aria-hidden="true" />}
            </button>
          );
        })}
      </div>

      <div className="quick-focus-strip" aria-label="Quick focus suggestions">
        <span className="quick-focus-label">FOCUS:</span>
        <div className="quick-focus-pills">
          {QUICK_STARTERS.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              className="quick-focus-pill"
              onClick={() => onSelectQuickStarter(prompt)}
              disabled={disabled}
            >
              + {prompt.split(" ")[0]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
