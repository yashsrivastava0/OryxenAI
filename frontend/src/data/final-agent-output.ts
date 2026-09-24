/**
 * Compatibility accessor for the complete persisted agent output.
 *
 * The API now includes `agent_output` on each stage projection. Keep this
 * small helper for existing artifact surfaces, but never rebuild an output
 * from fields currently rendered by the UI: unknown and nested agent fields
 * must remain copyable.
 */

type FinalOutputStage =
  | "discovery"
  | "content_architect";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function finalAgentOutput(
  _stage: FinalOutputStage,
  rawState: unknown,
): Record<string, unknown> | null {
  if (!isRecord(rawState) || !isRecord(rawState.agent_output)) return null;
  return rawState.agent_output;
}
