"""The executable markup contract every portfolio theme provides.

A theme is more than a stylesheet: its selectors, legal markup, derived values
and empty-field rules are versioned together. The Code Generator is generic; it
asks the theme's contract to derive host values, compose the technical
``<head>``, describe the structure to the model, and validate the model's body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from oryxenai.themes.htmltree import Element
from oryxenai.themes.issues import Issue


class ThemeContract(Protocol):
    theme_id: str
    default_language: str
    allowed_tags: frozenset[str]
    # Attribute allow-list per tag; the "*" key applies to every tag.
    allowed_attributes: Mapping[str, frozenset[str]]
    # Static, theme-owned strings that may appear in markup (not biographical).
    chrome_strings: frozenset[str]

    def class_vocabulary(self) -> frozenset[str]:
        """Every class name the stylesheet defines plus declared hook classes."""

    def valid_language(self, lang: str) -> bool:
        """Whether ``lang`` is a well-formed BCP-47 tag this theme accepts."""

    def asset_paths(self) -> frozenset[str]:
        """Bundle-relative asset URLs markup may reference (``./assets/...``)."""

    def derive(self, page_content: Mapping[str, Any]) -> dict[str, Any]:
        """Host-computed values the model must use verbatim."""

    def approved_text(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> set[str]:
        """Closed set of normalized strings visible text may consist of."""

    def approved_urls(self, page_content: Mapping[str, Any]) -> set[str]:
        """Exact external/mailto URLs links may use."""

    def render_head(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any], lang: str
    ) -> str:
        """Everything before the page body: doctype, ``<head>`` and ``<body>`` open tag."""

    def render_tail(self) -> str:
        """Everything after the page body."""

    def validate_body(
        self, root: Element, page_content: Mapping[str, Any], derived: Mapping[str, Any]
    ) -> list[Issue]:
        """Theme-specific structure and copy-binding checks on the parsed body."""

    def prompt_contract(self) -> str:
        """Markup contract text for the model: structure example plus rules."""


@runtime_checkable
class HostRenderedContract(Protocol):
    """A contract that can write its own page body from approved content.

    Implementing ``render_body`` is all a new theme needs to be built by the host:
    the body is a pure function of ``page_content``, so no model call is made for the
    build and the result is validated, sealed and browser-verified like any other page.
    A theme without it falls back to the model-written path.
    """

    def render_body(
        self, page_content: Mapping[str, Any], derived: Mapping[str, Any] | None = None
    ) -> str:
        """The complete page body markup for ``page_content``."""
