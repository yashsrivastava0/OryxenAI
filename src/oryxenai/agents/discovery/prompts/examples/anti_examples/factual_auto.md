# Anti-example: factual Auto decision

BAD:
"auto_decisions": [
  {
    "category": "project_selection",
    "selected_value": "Project A is the best",
    "explanation": "Auto-chosen because it is the most impressive."
  }
]

REASON:
Project selection is a factual/positioning decision, not a presentation
decision. It requires user input or supported evidence, and choosing the
"most impressive" alternative without evidence silently favors an
unsupported claim.

GOOD:
Project selection is either omitted, asked about, or chosen with explicit
basis fact IDs and user involvement. Auto decisions are limited to tone,
theme, motion, project ordering, section emphasis, CTA phrasing, and
visual intensity.
