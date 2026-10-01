"""Code Generator: writes the page markup for an approved portfolio.

The model writes the visible ``<body>`` markup for ONE pinned theme from the
approved Content Architect ``page_content``; the host owns the technical
``<head>``, attaches the theme's unchanged ``styles.css``, validates the exact
bytes, and previews them. See ``README.md`` for the pipeline and its contracts.
"""
