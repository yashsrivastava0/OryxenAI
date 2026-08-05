"""Test fixtures: sample payloads for mock agents."""

SAMPLE_INPUTS = {
    "discovery": {
        "prompt": "I need a portfolio site for a freelance photographer.",
        "context": {},
    },
    "content_architect": {
        "discovery": {"summary": "A portfolio website for a freelance photographer."},
        "preferences": {},
    },
    "visual_design_director": {
        "content": {"sections": [{"id": "hero", "title": "Hero"}]},
        "brand": {},
    },
    "code_generator": {
        "content": {"sections": [{"id": "hero", "title": "Hero"}]},
        "design": {"theme": {"name": "minimal-dark"}},
    },
}

EMPTY_INPUTS = {key: {} for key in SAMPLE_INPUTS}
