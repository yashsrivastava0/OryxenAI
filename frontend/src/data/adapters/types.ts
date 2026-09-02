// Shared adapter vocabulary — every stage adapter (discovery.ts now; content,
// design, preparation, generation in their owning phases) outputs this same
// shape. See docs/Frontend/05 §2.2 and §6.1 "Adapter rules shared by all
// stages": accept unknown, validate the minimal required envelope, never
// normalize an unrecognized required status to "complete" or "available".

export type StageState =
  | "locked"
  | "available"
  | "working"
  | "input"
  | "review"
  | "attention"
  | "complete"
  | "unsupported";

export interface StageViewModel {
  state: StageState;
  statusText: string;
  raw: unknown;
}
