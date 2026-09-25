# Research notes and design rationale

## Product posture

OryxenAI is an agentic portfolio-production studio, not a conversational wrapper around a form and not a generic analytics dashboard. Its interface has to make two different activities legible:

1. an agent is working autonomously through a bounded workflow; and
2. a human is reviewing an artifact and deciding whether to explicitly start the next retained stage.

The UI therefore needs a deliberate handoff rhythm:

```text
User supplies intent
  → agent works asynchronously
  → server persists a durable state
  → UI explains the current milestone
  → user reviews a decision-grade artifact
  → explicit approval or revision
  → after Discovery approval, the user may explicitly start Content Architect
  → Content Architect approval ends the active workflow
```

The current frontend obscures this rhythm by rendering internal outputs, repeating metadata, forcing both active stages through the same nested grid, and treating a long document as the primary interaction model. The remediation should make the workflow feel calm and operational: the agent can work for a while, but the user can always tell what is happening, what has been produced, and what requires judgment.

## External research

Anthropic describes agents as self-directed systems that plan, act, observe, adjust, and return for human input when needed. That maps directly to OryxenAI's durable worker and explicit approval boundary: progress should be visible, but internal process should not become the product surface. See [Trustworthy agents in practice](https://www.anthropic.com/research/trustworthy-agents?aff=Z8BZe).

Anthropic's agent guidance also distinguishes predefined workflows from dynamic agents and recommends simple, composable patterns. OryxenAI already has the right bounded workflow shape; the frontend should expose the workflow's checkpoints rather than inventing a chat metaphor for every stage. See [Building effective AI agents](https://www.anthropic.com/engineering/building-effective-agents?via=aitoolhunt).

OpenAI's Codex app positions a long-running agent workspace around focused task review, progress, and inspectable work. The equivalent OryxenAI pattern is one focused stage canvas with a compact pipeline navigator and an optional inspection surface, not several simultaneous utility rails. See [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/).

WCAG 2.2 requires status information to be programmatically determinable and available without forcing focus changes. The frontend should use a small, transition-based status announcer instead of putting large, frequently changing stage regions inside live regions. See [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Design direction

Keep the existing editorial Swiss foundation:

- warm paper surface;
- deep ink text;
- one restrained cobalt action color;
- serif display voice paired with crisp sans-serif utility text;
- hairline rules and deliberate asymmetry.

Change the application posture:

- stage headings become compact statements rather than poster-scale banners;
- body copy gets a stable readable measure;
- decoration becomes background atmosphere, not navigation or content;
- status is a text label with a clear semantic state, not a floating badge;
- data is represented according to the active job: the brief, routes, and planned sections;
- actions stay visible as decisions, not as the last paragraph of a long document.

## What the visual references are for

The generated images in `visuals/` are implementation references. They communicate relative hierarchy, density, whitespace, panel placement, action placement, and responsive collapse. They are not a source of truth for exact text or backend fields. Exact behavior remains in the Markdown specifications and the existing backend/API contracts.

The references must not introduce:

- purple AI gradients;
- fake percentage dials;
- external image URLs;
- invented model names, provider names, or internal IDs;
- raw JSON as the primary product surface.
