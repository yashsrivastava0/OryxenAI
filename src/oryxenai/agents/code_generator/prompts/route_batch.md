Implement only the assigned route-section batch against the frozen shared
signatures. Turn the approved content and route-level visual direction into an
authored reading sequence, not interchangeable boxes. The
`<generation-contract>` block is the normative checklist for this unit.

Authority and anchor requirements:

- Copy every admitted route id, section id, fact id, criterion id, content
  string, source marker, interaction id, and approved destination exactly.
- The assigned anchor file must contain the route id, every section id as
  literal text, `id="<section_id>"`, and `data-content-id="<section_id>"`, every approved content
  string for those sections, every assigned source marker, and one exact
  `data-interaction-id` per assigned interaction. Subcomponents do not replace
  these anchor literals.
- Re-read the anchor file top to bottom and string-check the contract before
  returning. A copied-from-memory sentence, marker paraphrase, or one-character
  interaction-id change is a failed result.

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

- Use the exact token names and values emitted from the v3 blueprint. Do not
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
- All visible copy comes verbatim from `site_contract.public_content`.
  Connective labels and aria text must be approved content or at most three
  words. Never invent claims, metrics, clients, testimonials, credentials,
  project details, image subjects, or capabilities.

Return complete files for only the owned paths, honest coverage, and the
strict JSON transport object. If a required local input is unavailable, return
a bounded cannot-complete result instead of fabricating a substitute.
