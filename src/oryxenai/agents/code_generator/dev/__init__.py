"""Development and test utilities for the Code Generator.

Nothing in here may be imported by runtime code (a unit test enforces that).
The reference renderer is a test oracle and the source of the prompt exemplar,
not a fallback path: a model failure is reported, never papered over.
"""
