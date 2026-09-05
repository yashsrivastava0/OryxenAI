Implement only the assigned route-section batch against the frozen shared
signatures. Turn the approved content and route-level visual direction into an
authored reading sequence, not interchangeable boxes. The
`<generation-contract>` block is the normative checklist for this unit.

Return `result: "accepted"` only when the context supplied to you explicitly
shows this exact unit's own files already generated and accepted in a prior
attempt, with nothing left to change. If no such existing accepted content
for this unit appears in your context, there is nothing yet to accept:
return `result: "changes"` with the complete new file set instead.
`result: "accepted"` with no qualifying prior content is a contract
violation, not a valid outcome.

Authority and anchor requirements:

- Copy every admitted route id, section id, fact id, criterion id, content
  string, source marker, interaction id, and approved destination exactly.
- Each concrete owned `.tsx` file is the independent owner of exactly one
  assigned section. That file must contain the route-scoped section id as the
  exact `data-content-id="<section_id>"` literal and must separately implement
  the exact `section_selector` listed for it in the generation contract. For a
  selector such as `#hero`, use `id="hero"`; do not turn it into
  `id="home:hero"`. Keep the route-scoped content identity and DOM selector as
  two distinct contract values when they differ. Include every approved
  content value for that section. Do not put two assigned section anchors in
  one file, create a route-level aggregator, or leave an owned section file as
  a helper with no section anchor.
- The first owned file is only the deterministic validation starting point; it
  is not an aggregator and does not own the other section files. Re-read every
  owned section file top to bottom and string-check the contract before
  returning. A copied-from-memory sentence, marker paraphrase, or one-character
  interaction-id change is a failed result.
- Follow the generation contract's canonical page-heading ownership exactly.
  The batch containing the named `h1_owner` section renders one visible `<h1>`
  in that section file; every other section and every batch that does not own
  it renders no `<h1>`. Do not demote the owner heading to `<h2>` or leave the
  composer to invent route copy it does not own.

Import paths are resolved from the repository root, not from the prompt's
logical `src/...` labels. Use the `@/` alias when possible. If using relative
imports, the exact paths from a section file at
`src/routes/<route-storage-key>/sections/<section-file>.tsx` are:

- `src/content/generated-content.ts` → `../../../content/generated-content`
- `src/components/generated/SharedSystems.tsx` → `../../../components/generated/SharedSystems`
- `src/app/ResourceUrl.ts` → `../../../app/ResourceUrl`
- another file in the same `sections/` directory → `./<section-file>`

Do not use four `..` segments from a section file; that leaves `src/` and
cannot resolve the trusted modules. Before returning, resolve every local
import against the actual owned source paths.

Each owned section file is an independent default-exported component. Preserve
an authoritative route-scoped ID such as `home:hero` exactly in
`data-content-id`, while implementing the blueprint's independent DOM selector
exactly (for example, `#hero` becomes `id="hero"`). Do not turn one section
file into an aggregator, import a component from itself, or re-export a named
component from a sibling unless that sibling visibly exports that exact name.
A named import or re-export is valid only when the target module contains that
named export; prefer a direct default import of each section file when
composing the batch.

Ownership and shell boundary:

- A route batch owns section fragments only. It must not create or modify a
  route shell, `<main>`, skip link, site navigation, footer, route registry,
  generated manifest, content module, or same-site URL policy.
- The route composer owns the shell and receives only frozen batch signatures
  plus approved interaction assignments. Import only the exact trusted exports
  listed in `shared_source`.
- Stay strictly inside `owned_paths`; use `create` only for absent files and
  `replace` only for existing files.

Visual and implementation contract:

- Use the exact token names and values emitted from the validated blueprint.
  Every emitted CSS custom property carries its group prefix: a color token
  named `cobalt` compiles to `--color-cobalt`, a spacing token named `5`
  compiles to `--space-5`, a size token to `--size-<name>`, a radius token to
  `--radius-<name>`, a border to `--border-<name>`, a shadow to
  `--shadow-<name>`. Always include that prefix, even when it looks redundant
  with the token's own name (a spacing token already named `space-5` still
  compiles to `--space-5`, not `--space-space-5`). Do not
  assume or recreate a default palette, `.card`, `.surface`, `.grid`, or
  other generic scaffold primitive not named in the motion pattern
  catalogue or already exported by SharedSystems.tsx. Do not add a
  second token system, arbitrary gradients, glass panels, floating blobs,
  dashboard card repetition, decorative pill overload, or uniform centering.
- Use route-scoped CSS and approved responsive composition. Layout must remain
  readable at mobile, tablet, and desktop widths. Use spacing and typography
  from the blueprint instead of arbitrary margins or a utility framework. CSS
  lengths are numeric or tokenized (`50ch`, not `fiftych`); never join a
  spelled-out number to a CSS unit.
- Use only custom properties that exist in the compiler-emitted token groups
  or that the owning JSX defines literally as runtime style state. Never emit
  `@font-face` in route CSS; local font faces and URLs are already emitted by
  the trusted token compiler.
- Implement only motion beats assigned to this batch. Every animated state
  must use the exact marker, selectors, before/after values, trigger, duration,
  and easing listed under `EXECUTABLE MOTION BEATS`, with a static, fully
  visible `prefers-reduced-motion` equivalent. A `viewport` trigger requires
  actual IntersectionObserver-driven state or a CSS view timeline; a
  stylesheet-load animation is not a viewport trigger. Essential content is
  visible in the unguarded CSS baseline. If a viewport beat starts at opacity
  0, guard that before-state with `[data-motion-ready="true"]` and set the
  attribute only after confirming IntersectionObserver support. When a beat's
  instruction names a trusted motion pattern (it reads "Apply trusted motion
  pattern ... exactly"), use the named `SharedSystems.tsx` component or class
  exactly as instructed instead of hand-authoring new CSS/JS for that beat —
  wrap the section's content in it rather than reimplementing the same
  before/after values, trigger, and easing yourself. `Reveal`/`StaggerGroup`
  set `data-motion-ready` on their own wrapper element, not on `children` —
  if a CSS selector must combine `data-motion-ready` with another marker
  (a resource or interaction marker) on one element, pass that marker as a
  literal attribute directly to `Reveal`/`StaggerGroup` itself (for example
  `<Reveal data-resource-marker="...">`), which forwards it onto the same
  wrapper. Putting the marker on `children` instead puts it on a different
  DOM node than `data-motion-ready`, and a compound selector requiring both
  will never match either one.
- Every visible link, button, and disclosure has a keyboard name, focus state,
  and at least a 36px inline and block hit area.
- Put every assigned interaction on the actual target element identified by
  its `target_selector`. That same JSX opening tag must carry both the exact
  `data-interaction-id` attribute and the blueprint `literal_marker`. An
  outcome in another section is a destination, not a reason to move ownership
  to the route composer or mark a duplicate navigation control.

Resource and content contract:

- Render only admitted local resources. Planned images use the trusted
  `LocalImage` component with the exact short `resourceId` and presentation
  props from `PLANNED LOCAL IMAGE BINDINGS`. Omit the `sources` prop: the
  component resolves exact responsive paths, hashes, dimensions, and formats
  from the immutable generated manifest. Never transcribe a rendition path or
  substitute an acquisition-ledger path containing a run id. Same-site links
  use `publicRouteUrl`; approved external URLs must exactly match the contract.
- A required component binding is used by importing its materialized local
  module and rendering it. A slot id, filename comment, or manifest mention is
  not usage. Never use remote imports, fetch, network URLs, or package changes.
- Call `contentValue("<literal-approved-content-id>")` directly for every
  approved content key. Do not hide the key behind a generic alias or generated
  lookup; the source audit must be able to prove the executable literal.
- This includes approved metadata keys such as CTA/link `kind` values. Bind
  those values through a direct `contentValue("<literal-approved-content-id>")`
  call to a meaningful `data-*` attribute instead of dropping them as
  non-visible copy.
- Implement every assigned interaction's exact navigation, state attribute,
  state value, transition, keyboard behavior, and focus behavior from the
  generation contract. A matching href alone is insufficient when the
  contract requires activated state or target focus.
- Copy the complete ordered `unit.resource_slot_ids` list exactly into the
  returned `resource_slot_ids` coverage array. Include optional package,
  recipe, and component slots even when the assigned section source does not
  render them directly; this array records the work-unit assignment, not only
  the image slots you chose to use.
- All visible copy comes verbatim from `site_contract.public_content`.
  Connective labels and aria text must be approved content or at most three
  words. Never invent claims, metrics, clients, testimonials, credentials,
  project details, image subjects, or capabilities.

A resource placement whose `required` field is false and has no admitted
`local_paths` is working as designed, not a defect: render a tasteful,
non-personal decorative or generated composition for that placement instead
(no `LocalImage`, no invented photograph). This is normal, expected input,
never grounds for `cannot_complete` — that authority is reserved for
resources actually marked `required`.

Return complete files for only the owned paths, honest coverage, and the
strict JSON transport object. If a required local input is unavailable, return
a bounded cannot-complete result instead of fabricating a substitute.
