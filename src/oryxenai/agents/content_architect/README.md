# Content Architect Agent

## Current purpose

Structures the content outline and sections for a portfolio site from
discovery output. In the scaffold phase this is a **deterministic mock**
returning a checked-in sample — no real reasoning, no model call.

## Input

A `ContentArchitectRequest` with:
- `discovery` — structured discovery output from the Discovery agent.
- `preferences` — optional user preferences.

## Output

A `ContentArchitectResponse` with:
- `sections` — ordered list of page sections.
- `outline` — high-level site outline.

## Current mock status

Returns `samples/output.json` validated against `ContentArchitectResponse`.
Input is validated but does not influence the output.

## Future responsibilities

Plan information architecture, section types, copy placeholders, and content
hierarchy based on discovery artifacts.

## Non-responsibilities

- Does NOT generate visual designs.
- Does NOT generate code.
- Does NOT call an LLM in this phase.
- Does NOT chain to other agents.