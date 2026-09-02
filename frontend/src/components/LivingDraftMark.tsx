// Preact wrapper around the ONE canonical mark markup shared with the auth
// pages — see src/oryxenai/auth/static/living-draft-mark.mjs for why this is
// a cross-boundary relative import rather than a duplicated component.
import { livingDraftMarkMarkup } from "../../../src/oryxenai/auth/static/living-draft-mark.mjs";

interface LivingDraftMarkProps {
  active?: boolean;
}

export function LivingDraftMark({ active = false }: LivingDraftMarkProps) {
  return <span dangerouslySetInnerHTML={{ __html: livingDraftMarkMarkup({ active }) }} />;
}
