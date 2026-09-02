// Phase 1 visual/contract spike (docs/Frontend/05 §19 Phase 1). Phase 3
// replaces this with the real ProgressSurface (05 §8.8) reading Build
// Preparation's user-facing milestones (01 §6.9).
interface SpecimenItem {
  label: string;
  state: "complete" | "current" | "quiet";
}

const ITEMS: SpecimenItem[] = [
  { label: "Checking approved content and design", state: "complete" },
  { label: "Resolving required portfolio materials", state: "current" },
  { label: "Packaging build instructions", state: "quiet" },
  { label: "Verifying the handoff", state: "quiet" },
];

export function ProgressSpecimen() {
  return (
    <div className="specimen-progress" aria-label="Progress specimen">
      {ITEMS.map((item) => (
        <div key={item.label} className="specimen-progress-item" data-state={item.state}>
          {item.label}
        </div>
      ))}
    </div>
  );
}
