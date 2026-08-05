# Code Generator Agent

## Current purpose

Generates portfolio site source files from content and design direction. In
the scaffold phase this is a **deterministic mock** returning a checked-in
sample — no real code generation, no model call.

## Input

A `CodeGeneratorRequest` with:
- `content` — content outline from the Content Architect agent.
- `design` — visual direction from the Visual Design Director agent.

## Output

A `CodeGeneratorResponse` with:
- `files` — list of generated files (path, content, language).
- `metadata` — generation metadata (file count, generator).

## Current mock status

Returns `samples/output.json` validated against `CodeGeneratorResponse`.
Input is validated but does not influence the output.

## Future responsibilities

Generate HTML/CSS/JS files, component markup, and a deployable static site
from content and design artifacts.

## Non-responsibilities

- Does NOT perform discovery or content planning.
- Does NOT create visual designs.
- Does NOT call an LLM in this phase.
- Does NOT chain to other agents.
- Does NOT deploy or publish the generated site in this phase.