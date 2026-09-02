export interface Archetype {
  id: string;
  code: string;
  title: string;
  tagline: string;
  draftText: string;
}

export const ARCHETYPES: Archetype[] = [
  {
    id: "systems-architect",
    code: "SYS-01",
    title: "Systems Architect",
    tagline: "High-scale distributed systems, low-latency infrastructure & resilience engineering.",
    draftText: `I am a Senior Systems Architect with 7+ years designing distributed backends, streaming pipelines, and fault-tolerant infrastructure.

Key highlights & milestones:
- Designed an event-driven telemetry ingest engine processing 250k events/sec on Rust and Kafka with sub-20ms p99 latency.
- Migrated an enterprise monolith to decoupled Go microservices, reducing incident MTTR by 65%.
- Authored open-source storage indexing engines and zero-allocation networking libraries.

Target portfolio direction: High-rigor, technical, editorial precision with system architecture deep-dives and verifiable performance metrics.`,
  },
  {
    id: "creative-technologist",
    code: "CRT-02",
    title: "Creative Technologist",
    tagline: "Kinetic UI, WebGL shaders, tactile design systems & experimental interaction.",
    draftText: `I am a Creative Technologist & Interaction Designer bridging software engineering and visual aesthetics.

Key highlights & milestones:
- Created bespoke WebGL & Three.js interactive graphics recognized across design and web communities.
- Architected fluid component systems with custom physics curves, fluid micro-interactions, and 60fps rendering.
- Researched kinetic typography and physical simulation engines compiled to WebAssembly.

Target portfolio direction: Visually commanding, tactile, Swiss editorial typography with dark mode nuances and interactive case studies.`,
  },
  {
    id: "product-lead",
    code: "PRD-03",
    title: "Founding Product Lead",
    tagline: "0-to-1 product strategy, technical execution, and user momentum.",
    draftText: `I am a Founding Product Engineer & Technical Lead taking ambitious software from zero to 1.

Key highlights & milestones:
- Shipped the core platform for a seed-stage developer startup, growing to 40,000 active developers in under 12 months.
- Led end-to-end delivery: React/TypeScript frontend, resilient async job queues, and multi-tenant PostgreSQL.
- Drove user research, customer discovery, and weekly release velocity.

Target portfolio direction: Narrative-driven, founder-level clarity focusing on product architecture, UX decisions, and quantifiable outcomes.`,
  },
  {
    id: "research-scientist",
    code: "RES-04",
    title: "Research Engineer",
    tagline: "Machine learning foundations, agentic architectures & algorithmic rigor.",
    draftText: `I am an Applied AI Researcher and ML Engineer working on generative models, agentic workflows, and inference optimization.

Key highlights & milestones:
- Published papers at top tier conferences on sparse attention and speculative decoding algorithms.
- Optimized production LLM serving stacks with custom CUDA kernels and quantization, reducing latency by 4x.
- Built rigorous evaluation suites and reproducibility harnesses for multi-agent reasoning benchmarks.

Target portfolio direction: Clean, academic-grade clarity with research abstracts, interactive benchmarks, and live code artifacts.`,
  },
];

export const QUICK_STARTERS = [
  "Senior Full-Stack Engineer (React, TypeScript, Python FastAPI)",
  "Staff Design Engineer focusing on accessible design systems",
  "DevOps / SRE Architect with Kubernetes & Terraform experience",
  "Data Engineer building modern real-time streaming warehouses",
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
    <div className="archetype-section">
      <div className="archetype-section-header">
        <span className="technical-badge">SELECT ARCHETYPE</span>
        <span className="archetype-hint">Choose a starting persona to pre-populate authentic narrative notes:</span>
      </div>

      <div className="archetype-grid" role="radiogroup" aria-label="Portfolio archetypes">
        {ARCHETYPES.map((arch) => {
          const isSelected = selectedId === arch.id;
          return (
            <button
              key={arch.id}
              type="button"
              className={`archetype-card ${isSelected ? "archetype-card-active" : ""}`}
              onClick={() => onSelectArchetype(arch)}
              disabled={disabled}
              role="radio"
              aria-checked={isSelected}
            >
              <div className="archetype-card-top">
                <span className="archetype-code">{arch.code}</span>
                {isSelected && <span className="archetype-active-indicator" aria-hidden="true">SELECTED</span>}
              </div>
              <h3 className="archetype-title">{arch.title}</h3>
              <p className="archetype-tagline">{arch.tagline}</p>
            </button>
          );
        })}
      </div>

      <div className="quick-starters-tray">
        <span className="quick-starters-label">Quick prompts:</span>
        <div className="quick-starters-list">
          {QUICK_STARTERS.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              className="quick-starter-pill"
              onClick={() => onSelectQuickStarter(prompt)}
              disabled={disabled}
            >
              + {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
