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
  assigned section. That file must contain the section id as literal text,
  `id="<section_id>"`, and `data-content-id="<section_id>"`, plus every
  approved content string for that section. Do not put two assigned section
  anchors in one file, create a route-level aggregator, or leave an owned
  section file as a helper with no section anchor.
- The first owned file is only the deterministic validation starting point; it
  is not an aggregator and does not own the other section files. Re-read every
  owned section file top to bottom and string-check the contract before
  returning. A copied-from-memory sentence, marker paraphrase, or one-character
  interaction-id change is a failed result.

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

Each owned section file is an independent default-exported component and must
carry the exact route-scoped `id="<section_id>"` and
`data-content-id="<section_id>"` literals for its one assigned section; do not
shorten authoritative IDs such as `home:hero` to `hero`. Do not turn one
section file into an aggregator, import a component from itself, or re-export
a named component from a sibling unless that sibling visibly exports that
exact name. A named import or re-export is valid only when the target module
contains that named export; prefer a direct default import of each section
file when composing the batch.

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
  assume or recreate a default palette, `.card`, `.surface`, `.grid`,
  `.reveal`, `.stagger`, or other generic scaffold primitive. Do not add a
  second token system, arbitrary gradients, glass panels, floating blobs,
  dashboard card repetition, decorative pill overload, or uniform centering.
- Use route-scoped CSS and approved responsive composition. Layout must remain
  readable at mobile, tablet, and desktop widths. Use spacing and typography
  from the blueprint instead of arbitrary margins or a utility framework.
- Implement only motion beats assigned to this batch. Every animated state
  must have a static, fully visible `prefers-reduced-motion` equivalent.
- Every visible link, button, and disclosure has a keyboard name, focus state,
  and at least a 36px inline and block hit area.

Resource and content contract:

- Render only admitted local resources. Images use the trusted
  `publicResourceUrl` helper with prefix-free local references; same-site links
  use `publicRouteUrl`; approved external URLs must exactly match the contract.
- A required component binding is used by importing its materialized local
  module and rendering it. A slot id, filename comment, or manifest mention is
  not usage. Never use remote imports, fetch, network URLs, or package changes.
- Call `contentValue("<literal-approved-content-id>")` directly for every
  approved content key. Do not hide the key behind a generic alias or generated
  lookup; the source audit must be able to prove the executable literal.
- Copy the complete ordered `unit.resource_slot_ids` list exactly into the
  returned `resource_slot_ids` coverage array. Include optional package,
  recipe, and component slots even when the assigned section source does not
  render them directly; this array records the work-unit assignment, not only
  the image slots you chose to use.
- All visible copy comes verbatim from `site_contract.public_content`.
  Connective labels and aria text must be approved content or at most three
  words. Never invent claims, metrics, clients, testimonials, credentials,
  project details, image subjects, or capabilities.

Return complete files for only the owned paths, honest coverage, and the
strict JSON transport object. If a required local input is unavailable, return
a bounded cannot-complete result instead of fabricating a substitute.
