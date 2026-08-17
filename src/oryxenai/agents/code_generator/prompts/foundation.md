Build the shared visual foundation for the admitted portfolio using only the
owned paths in the input. Treat the SitePlan as an implementation contract;
the `<generation-contract>` block is the mechanical checklist.

The scaffold provides a token-backed design baseline under `src/design`:
color, type, space, radius, shadow, and motion custom properties in
`tokens.css`; font variables in `fonts.css`; and reduced-motion-safe reveal
recipes in `motion.css`. The global utility entrypoint `src/design/global.css`
and the runtime shell are trusted and immutable. Override token values and
extend route-agnostic primitives in `src/components/shared/**`, but do not
create a parallel styles tree or re-derive a second scale.

Establish a clear creative thesis in token values, type hierarchy, rhythm,
surface treatment, responsive behavior, and meaningful interaction states.
Use the admitted typography recipe for `--font-display`, `--font-body`, and
`--font-mono`; use the fluid `--text-*` scale rather than fixed heading/body
sizes. Rewrite any vendored component source into this scaffold's token/CSS
idiom; never copy foreign utility classes or assume unadmitted frameworks.

The trusted shell already owns route loading, accessible navigation, the
unknown-path fallback, generated manifests, and the global CSS import. Do not
build route-specific content, duplicate route sections, modify package files,
or touch `src/generated/**`, `src/content/**`, `src/app/**`, `src/main.tsx`, or
`src/design/global.css`.

Use local resources only. Required media must be rendered from its admitted
`/resources/pack/...` URL; required component source must be imported and
rendered from `src/generated/resources/pack/...`. A comment, slot ID, filename
in a manifest, or prose mention is not resource usage. Package icons must use
their admitted package/export. Provide static reduced-motion equivalents.

Admission rules reject the complete response on any violation:

- No remote imports, fonts, images, scripts, runtime network calls, or
  unapproved URLs. Approved links may appear only as faithful content hrefs.
- `create` is only for a missing file; `replace` is only for an existing file.
- Stay strictly inside the owned paths and use only admitted bare imports.
- Fill `self_check` honestly after rereading the generated files.
