Implement only the assigned route or contiguous route-section batch against
the frozen shared signatures. Turn the approved content and route-level visual
direction into an authored reading sequence, not a sequence of interchangeable
boxes.

Wiring is already trusted and immutable: `src/generated/route-registry.ts`
maps this route to `src/routes/<storage_key>/index.tsx` (your `owned_paths`
use that exact storage key — see `shared_source` for the registry). Create
`index.tsx` there exporting the route component; scene/section components
and route-scoped CSS live beside it under the same directory. NEVER modify
the registry, `src/app/*`, `src/generated/*`, `src/content/*`, or scaffold
config — they are outside every unit's ownership by design.

`index.tsx` is the verification anchor and MUST itself contain, verbatim:
the route's `route_id` string, every assigned `section_id` string, every
approved content string for those sections (embed the copy — do not merely
import it), the exact `source_marker` string of each acceptance-coverage
entry assigned to this route, and one `data-interaction-id="<interaction_id>"`
attribute per planned interaction. Sub-components may exist beside it, but
`index.tsx` carries the copy and all markers.

Compose with the scaffold's system: spacing strictly through the `--space-*`,
`--element-gap`, `--content-gap`, and `--section-gap` tokens (consistent
cadence, deliberate pauses — never arbitrary margins), type through the fluid
`--text-*` scale with real hierarchy jumps, surfaces through `.card` /
`.frame` / `.surface` variants, and layout through `.stack`, `.cluster`,
`.grid`, `.grid--sidebar`. This target has no utility-class framework: write
route-scoped CSS against the tokens; vendored component source must be
rewritten into this idiom, never copied with foreign utility classes. The
context's `shared_source` holds the frozen foundation files — import ONLY
from those exact paths and exports, and read `site_contract.public_content`
for the approved copy you are rendering.

Choreograph the entrance: sections and key elements use `.reveal` variants
with `.stagger` so the route composes itself in sequence — sparingly, in
service of the thesis, with the reduced-motion equivalent being fully visible
static content (the scaffold guarantees this under the media query). Each
route must commit to its planned layout strategy so two routes never read as
the same template with different text.

For every assigned section, preserve its exact content identifier, facts,
criterion IDs, resource placement, responsive outcome, reduced-motion
equivalent, and keyboard-accessible interaction outcome. All visible copy
comes verbatim from `site_contract.public_content` — connective micro-labels
(buttons, aria-labels, alt text) must be copied from approved content or kept
under three words; never author new sentences of visible text. Express the planned
composition with concrete DOM hierarchy and CSS. Use asymmetry, editorial
spacing, data/evidence treatment, contrast, and controlled visual pauses only
when the admitted direction supports them. Avoid generic gradients,
glassmorphism, dashboard-like card repetition, and decorative animation.

Mark each implemented content/criterion/interaction/resource binding in the
source using the supplied marker convention. Own no paths outside the input.

Admission rules that reject the whole response on a single violation:

- Network references are banned with exactly one exception: approved
  external links rendered as `href="https://..."` attributes whose URL
  appears verbatim in `site_contract.public_content` (render those approved
  links faithfully). Everything else — remote `@import url(...)`, remote
  fonts/images/scripts, protocol-relative `//...`, `fetch(`, `WebSocket`,
  `XMLHttpRequest`, `EventSource`, and any URL in comments or metadata — is
  forbidden.
- Mark a file `replace` ONLY when it already exists in the candidate tree;
  every new file must be `create`. The context's `existing_files` list is the
  authoritative current tree — check it before choosing the operation.

Return complete files plus honest coverage, or a bounded request/cannot-complete
result when a required local input is genuinely unavailable.
