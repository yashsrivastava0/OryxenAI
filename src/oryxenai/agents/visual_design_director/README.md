# Visual Design Director Agent

## Current purpose

Defines visual direction: theme, color palette, and typography for the
portfolio site. In the scaffold phase this is a **deterministic mock**
returning a checked-in sample — no real reasoning, no model call.

## Input

A `VisualDesignDirectorRequest` with:
- `content` — content outline from the Content Architect agent.
- `brand` — optional brand guidelines.

## Output

A `VisualDesignDirectorResponse` with:
- `theme` — theme name, mode, and design tokens.
- `palette` — list of color hex values.
- `typography` — heading/body fonts and modular scale.

## Current mock status

Returns `samples/output.json` validated against `VisualDesignDirectorResponse`.
Input is validated but does not influence the output.

## Future responsibilities

Produce design tokens, component styling direction, and accessibility-aware
theme decisions based on content and brand input.

## Non-responsibilities

- Does NOT generate code.
- Does NOT perform discovery or content planning.
- Does NOT call an LLM in this phase.
- Does NOT chain to other agents.