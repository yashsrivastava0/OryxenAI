# Operation: build the shared visual foundation

Build the owned visual foundation from the selected ExperienceBlueprintV2 and
the normative `<generation-contract>` block. Do not create route content.

The scaffold already owns `src/design/global.css`, its baseline token files,
the runtime shell, and generated manifests. Create exactly the compiler-owned
foundation surfaces:

- `src/design/generated-tokens.css`: deliberate `:root` overrides for the
  blueprint's semantic colors, spacing cadence, containers, type scale,
  surfaces, focus treatment, and motion timing; plus local `@font-face` rules.
- `src/components/generated/SharedSystems.tsx`: import
  `../../design/generated-tokens.css`, export `SharedSystems`, and implement
  only route-agnostic systems the plan actually needs. Route units render this
  export, which is how the generated token layer enters the application.

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
`src/main.tsx`, the baseline design files, or any path outside `owned_paths`.

Admission rejects the complete response for remote assets/network calls,
unapproved URLs, unadmitted bare imports, incorrect create/replace operations,
or dishonest self-checks. Return only complete owned files or a bounded
cannot-complete result.
