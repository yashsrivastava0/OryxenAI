Implement only the assigned route or contiguous route-section batch against
the frozen shared signatures. Turn the approved content and route-level visual
direction into an authored reading sequence, not a sequence of interchangeable
boxes. The `<generation-contract>` block in your instructions lists, for THIS
unit, the exact anchor file, every section_id, every verbatim copy string,
every marker token, and every interaction attribute your output is admitted
and finally verified against — treat it as the checklist, not the site
contract prose.

Wiring is already trusted and immutable: `src/generated/route-registry.ts`
maps this route to `src/routes/<storage_key>/index.tsx` (your `owned_paths`
use that exact storage key — see `shared_source` for the registry). Create
`index.tsx` there exporting the route component; scene/section components
and route-scoped CSS live beside it under the same directory. NEVER modify
the registry, `src/app/*`, `src/generated/*`, `src/content/*`, or scaffold
config — they are outside every unit's ownership by design.

The `generation_contract.routes[*].anchor_file` is this unit's verification
anchor and MUST itself contain, verbatim:
the route's `route_id` string, every assigned `section_id` string — both as
literal text and as a `data-content-id="<section_id>"` attribute on each
section's wrapper element (runtime journeys wait on those attributes) — every
approved content string for those sections (embed the copy — do not merely
import it), the exact `source_marker` string of each acceptance-coverage
entry assigned to this route, and one `data-interaction-id="<interaction_id>"`
attribute per planned interaction. Sub-components may exist beside it, but
`index.tsx` carries the copy and all markers. Concretely, the anchor looks
like this shape (illustrative fragment, your composition is your own):

```tsx
{/* marker:criterion:home:0 — embedded verbatim per the plan */}
<section id="home-hero" data-content-id="home:hero">
  <h1>{content.hero.headline}</h1>
  <p>{content.hero.body}</p>
  <a
    href="#featured-projects"
    data-interaction-id="interaction:home:explore-projects"
  >
    {content.hero.primary_cta.label}
  </a>
</section>
```

BAD (rejected): copying the headline from memory with different wording;
putting the copy only in a data file the anchor imports; a marker sentence
instead of the short token; a `data-interaction-id` whose id differs from the
plan's interaction id by one character. GOOD: the literal strings from the
contract block, byte-for-byte, inside the anchor file.

Compose with the scaffold's system: spacing strictly through the `--space-*`,
`--element-gap`, `--content-gap`, and `--section-gap` tokens (consistent
cadence, deliberate pauses — never arbitrary margins), type through the fluid
`--text-*` scale with real hierarchy jumps, surfaces through `.card` /
`.frame` / `.surface` variants, and layout through `.stack`, `.cluster`,
`.grid`, `.grid--sidebar`. This target has no utility-class framework: write
route-scoped CSS against the tokens; vendored component source must be
rewritten into this idiom, never copied with foreign utility classes. The
context's `shared_source` holds the frozen foundation files — import ONLY
from those exact paths and exports (relative imports must resolve; every
bare import must be an admitted package), and read
`site_contract.public_content` for the approved copy you are rendering.

Bind the resources you use to their admitted local paths: acquired images
live under `public/resources/acquired/...` and pack media under
`public/resources/pack/...` (exact paths in the resource ledger and contract).
Import `publicResourceUrl` from the trusted `src/app/ResourceUrl.ts` helper and
pass it the manifest's prefix-free reference (`resources/pack/...`). Never use
root-relative `/resources/...` literals: they break nested preview mounts.
Use that module's `publicRouteUrl` for every same-site route `href`; literal
root-relative route links are not portable across nested preview mounts.
Required local component source is copied to
`src/generated/resources/pack/...`; import its module and render the imported
component in this route. A comment, slot ID, or manifest mention is not usage.

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
under three words; never author new sentences of visible text. Express the
planned composition with concrete DOM hierarchy and CSS. Use asymmetry,
editorial spacing, data/evidence treatment, contrast, and controlled visual
pauses only when the admitted direction supports them. Avoid generic
gradients, glassmorphism, dashboard-like card repetition, and decorative
animation.

Admission rules that reject the whole response on a single violation:

- Network references are banned with exactly one exception: approved
  external links rendered as `href="https://..."` attributes whose URL is in
  the contract's approved-URL list (render those approved links faithfully).
  Everything else — remote `@import url(...)`, remote fonts/images/scripts,
  protocol-relative `//...`, `fetch(`, `WebSocket`, `XMLHttpRequest`,
  `EventSource`, and any URL in comments or metadata — is forbidden.
- Mark a file `replace` ONLY when it already exists in the candidate tree;
  every new file must be `create`. The context's `existing_files` list is the
  authoritative current tree — check it before choosing the operation.
- Stay strictly inside the owned paths listed for this unit.

Before returning, re-read the assigned anchor file top to bottom and verify every
literal in the contract block is present by exact string match; fix any miss,
then fill `self_check` honestly. Return complete files plus honest coverage,
or a bounded request/cannot-complete result when a required local input is
genuinely unavailable.
