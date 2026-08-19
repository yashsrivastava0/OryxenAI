# Operation: audit the shared visual foundation

The host deterministically compiles the owned token and content modules from
the validated ExperienceBlueprintV3 before this operation runs. Review the
result against the normative `<generation-contract>` block; do not invent a
second token system and do not retype approved copy.

The scaffold already owns `src/design/global.css`, its baseline token files,
the runtime shell, `src/components/generated/SharedSystems.tsx`, and generated
manifests. The host owns the deterministic foundation files:

- `src/design/generated-tokens.css`: deterministic `:root` values for every
  typed blueprint token group, plus only approved local font bindings.
- `src/content/generated-content.ts`: a typed, receipt-bound module containing
  the approved public content when the contract requests it.

Do not modify either host-owned file or the trusted `SharedSystems` module.
The trusted shell provides skip-link behavior, one main landmark, disclosure
keyboard handling, focus return, and portable same-site URL helpers. Route
units consume those interfaces; they do not recreate them.

Use the admitted font binding and weights exactly. Pack fonts are copied under
`src/generated/resources/pack/fonts/...`; reference their exact relative paths
from `generated-tokens.css` so Vite fingerprints them and the result works at
nested preview bases. Never use a remote font, root-relative provider URL, or
unbound family name.

Make the visual thesis observable in hierarchy and rhythm. Preserve readable
line height and measure, visible focus, strong contrast, responsive spacing,
and a restrained motion vocabulary. Any reveal or transition primitive must
be fully visible and usable under `prefers-reduced-motion: reduce`. Avoid a
second token system, utility-framework syntax, generic gradient/glass effects,
and interchangeable card primitives.

The trusted shell already owns route loading and unknown-path behavior. Never
modify package files, `src/generated/**`, `src/content/**`, `src/app/**`,
`src/main.tsx`, the baseline design files, the trusted shared systems, or any
path outside `owned_paths`.

Admission rejects the complete response for remote assets/network calls,
unapproved URLs, unadmitted bare imports, incorrect create/replace operations,
or dishonest self-checks. Return only complete owned files or a bounded
cannot-complete result.
