Build the shared foundation for the admitted portfolio, using only the owned
paths in the input. Treat the SitePlan as an implementation contract, not a
suggestion.

The scaffold already provides a token-backed design baseline under
`src/design/`: color/type/space/radius/shadow/motion custom properties in
`tokens.css`, layout and surface utilities in `global.css` (`.container`,
`.section`, `.stack`, `.cluster`, `.grid`, `.grid--sidebar`, `.frame`,
`.card`, `.lift`, `.eyebrow`, `.lead`, `.label`, `.action`), an entrance
reveal system in `motion.css` (`.reveal`, `.reveal--fade`, `.reveal--scale`,
`.reveal--left`, `.stagger`), and font variables in `fonts.css`. Build on
these instead of re-deriving scales: override token VALUES to express the
plan's thesis, keep token and utility names stable, and extend with
route-agnostic primitives only.

Establish the reusable shell, tokens, global typography, route loading,
accessible navigation, shared primitives, and the visual baseline that every
route can inherit. Make the creative thesis observable in source: it should
affect layout rhythm, type hierarchy, color restraint, and interaction
behavior rather than survive only as comments. Map the admitted typography
recipe onto `--font-display`, `--font-body`, and `--font-mono` and use the
fluid `--text-*` scale — never fixed pixel sizes for headings or body.

Any vendored component source under `src/components/vendor/` is reference
material in a foreign idiom (it may assume utility-class frameworks this
target does not have): rewrite it into this scaffold's token/CSS idiom,
preserving structure, licensing header, and behavior — never copy foreign
utility classes or assume frameworks that are not admitted dependencies.

Use explicit semantic/source markers for the shell and any planned shared
system so verification can correlate the implementation with the SitePlan.
Provide a reduced-motion baseline before adding optional motion. Do not build
route-specific content here, duplicate route sections, modify package files,
or assume a resource that is not locally bound.

Admission rules that reject the whole response on a single violation:

- Network references are banned with exactly one exception: approved
  external links rendered as `href="https://..."` attributes whose URL
  appears verbatim in the approved public content. Everything else — remote
  `@import url(...)`, remote fonts/images/scripts, protocol-relative `//...`,
  `fetch(`, `WebSocket`, `XMLHttpRequest`, `EventSource`, and any URL in
  comments, CSS, or metadata — is forbidden. Fonts come from the local
  recipes/files or system stacks; images only from local
  `public/resources/...` paths present in the context.
- Mark a file `replace` ONLY when it already exists in the candidate tree;
  every new file must be `create`. The context's `existing_files` list is the
  authoritative current tree — check it before choosing the operation.
- Stay strictly inside the owned paths listed for this unit.

If a concrete missing resource prevents the assigned foundation, return a
receipt-bound request. Otherwise return complete replacement/create files and
coverage for exactly the assigned outcomes.
