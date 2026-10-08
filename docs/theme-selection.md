# Explorer theme selection

`config/themes.toml` is the server-owned catalog for the Explorer visual decision.
The picker receives this metadata with the palette question; it does not keep
its own theme list, badges, color mappings or card count.

To expose a new theme:

1. Build and register its immutable package in `oryxenai.themes` using the
   existing theme contract and manifest rules.
2. If it renders the Atlas content supplement, include its pinned id in
   `ATLAS_CONTENT_THEME_IDS` as required by the content pipeline.
3. Add a catalog entry with a unique stable choice id, registered theme id,
   label, description, swatches and presentation. `presentation.colors` means
   background, text and accent; `presentation.style` chooses a reusable preview
   composition. Choose `interactive` for scripted themes and `classic` for
   CSS themes. Catalog order determines order within each collection.
4. Restart the application. The catalog is validated and cached per process.
   Run the theme, Explorer API, frontend and browser checks before releasing.

Keep choice ids stable. Approved sessions and generated versions continue to
pin their theme independently of the picker. To retire a choice later, keep
its catalog entry and immutable package but set `selectable = false`. Its
historical mapping remains resolvable; new selection is refused and unanswered
palette questions receive the current available catalog.

The gallery presents interactive looks first and retains classic looks.
Search and collection filters do not discard the selected look. The summary
identifies it even when filtered out; “Show selection” clears those filters.
There is no automatic selection. Native radio controls support keyboard use,
and a stale saved draft cannot enable Continue.

The test-only browser fixture imports the same catalog. Run it with
`node node_modules/vite/bin/vite.js --config vite.browser-test.config.ts`
from `frontend`, then open `/?fixture=discovery-question-palette`.
`/?fixture=discovery-question-palette-many` exercises a larger synthetic catalog.
These fixtures exercise selection without model calls or changing real sessions;
the authenticated application remains available through the native API launcher.
