"""Strict, dependency-free parser and selector for generated HTML bodies.

Generated markup is machine-written and has a known theme contract, so this
parser accepts a deliberately **strict subset** of HTML: every non-void element
needs an explicit, correctly nested end tag. A browser would silently repair
anything else, which is exactly how structure drifts without anyone noticing,
so malformed input is reported precisely (code, line, column) instead.

The selector engine implements the small subset the theme contracts need:
type, ``#id``, ``.class``, ``[attr]``, ``[attr=v]``, ``[attr^=v]``,
``:first-child``, ``:last-child``, ``:nth-child(n)`` and the descendant and
child (``>``) combinators.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from oryxenai.themes.issues import Issue

VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    }
)

_WS = re.compile(r"[ \t\n\r\f]+")


# A no-break space is content, but the ordinary spaces beside it are not: models
# routinely add or drop them, and the rendered difference is invisible.
_NBSP_FLANK = re.compile(" ?" + chr(0xA0) + " ?")


def normalize_text(value: str) -> str:
    """NFC-normalize and collapse ASCII whitespace.

    A no-break space itself is kept (it must still appear), but the ordinary
    whitespace directly around it is not significant.
    """
    collapsed = _WS.sub(" ", unicodedata.normalize("NFC", value)).strip()
    return _NBSP_FLANK.sub(chr(0xA0), collapsed)


@dataclass(eq=False)
class Text:
    value: str
    parent: Element | None = None
    line: int = 0
    column: int = 0


@dataclass(eq=False)
class Element:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    parent: Element | None = None
    children: list[Element | Text] = field(default_factory=list)
    line: int = 0
    column: int = 0

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def get(self, name: str) -> str | None:
        return self.attrs.get(name)

    def has(self, name: str) -> bool:
        return name in self.attrs

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def elements(self) -> list[Element]:
        return [child for child in self.children if isinstance(child, Element)]

    def iter_descendants(self) -> Iterator[Element]:
        stack: list[Element] = list(reversed(self.elements()))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.elements()))

    def iter_text_nodes(self) -> Iterator[Text]:
        stack: list[Element | Text] = list(reversed(self.children))
        while stack:
            node = stack.pop()
            if isinstance(node, Text):
                yield node
            else:
                stack.extend(reversed(node.children))

    def _collect(self, parts: list[str], *, skip_aria_hidden: bool) -> None:
        for child in self.children:
            if isinstance(child, Text):
                parts.append(child.value)
            elif not (skip_aria_hidden and child.get("aria-hidden") == "true"):
                child._collect(parts, skip_aria_hidden=skip_aria_hidden)

    def text(self, *, skip_aria_hidden: bool = False) -> str:
        """Normalized text content (like ``textContent``, never ``innerText``)."""
        parts: list[str] = []
        self._collect(parts, skip_aria_hidden=skip_aria_hidden)
        return normalize_text("".join(parts))

    def location(self) -> str:
        return f"<{self.tag}> at line {self.line}, column {self.column}"


@dataclass(slots=True)
class ParsedFragment:
    root: Element
    issues: list[Issue]
    comments: list[tuple[str, int, int]]

    @property
    def ok(self) -> bool:
        return not any(issue.is_error for issue in self.issues)


class _Abort(Exception):
    """Stop parsing after the first structural error (the tree is unreliable)."""


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("#fragment")
        self.issues: list[Issue] = []
        self.comments: list[tuple[str, int, int]] = []
        self._stack: list[Element] = [self.root]

    def _where(self) -> tuple[int, int]:
        line, offset = self.getpos()
        return line, offset + 1

    def _fail(
        self, code: str, message: str, *, expected: str | None = None, found: str | None = None
    ) -> None:
        line, column = self._where()
        self.issues.append(
            Issue(code, "error", message, expected=expected, found=found, line=line, column=column)
        )
        raise _Abort

    def _open(self, tag: str, attrs: list[tuple[str, str | None]]) -> Element:
        line, column = self._where()
        values: dict[str, str] = {}
        for name, value in attrs:
            if name in values:
                self._fail(
                    "HTML_DUPLICATE_ATTRIBUTE",
                    f"<{tag}> repeats the attribute '{name}'.",
                    found=name,
                )
            values[name] = "" if value is None else value
        element = Element(tag, values, self._stack[-1], [], line, column)
        self._stack[-1].children.append(element)
        return element

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = self._open(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self._stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self._fail(
                "HTML_SELF_CLOSING_NON_VOID",
                f"<{tag}/> is not a void element; write <{tag}></{tag}>.",
                found=f"<{tag}/>",
            )

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            self._fail(
                "HTML_END_TAG_FOR_VOID",
                f"</{tag}> must not appear; <{tag}> has no end tag.",
                found=f"</{tag}>",
            )
        top = self._stack[-1]
        if len(self._stack) == 1:
            self._fail(
                "HTML_UNEXPECTED_END_TAG",
                f"</{tag}> has no matching start tag.",
                found=f"</{tag}>",
            )
        if top.tag != tag:
            self._fail(
                "HTML_MISMATCHED_END_TAG",
                f"</{tag}> closes <{top.tag}> (opened at line {top.line}, column {top.column}).",
                expected=f"</{top.tag}>",
                found=f"</{tag}>",
            )
        self._stack.pop()

    def handle_data(self, data: str) -> None:
        parent = self._stack[-1]
        if parent.children and isinstance(parent.children[-1], Text):
            parent.children[-1].value += data
            return
        line, column = self._where()
        parent.children.append(Text(data, parent, line, column))

    def handle_comment(self, data: str) -> None:
        line, column = self._where()
        self.comments.append((data, line, column))

    def handle_decl(self, decl: str) -> None:
        self._fail(
            "HTML_DECLARATION_NOT_ALLOWED",
            "A <!...> declaration is not allowed in the page body.",
            found=f"<!{decl[:40]}>",
        )

    def handle_pi(self, data: str) -> None:
        self._fail(
            "HTML_DECLARATION_NOT_ALLOWED",
            "A processing instruction is not allowed in the page body.",
            found=f"<?{data[:40]}>",
        )

    def unknown_decl(self, data: str) -> None:
        self._fail(
            "HTML_DECLARATION_NOT_ALLOWED",
            "A CDATA or marked section is not allowed in the page body.",
            found=f"<![{data[:40]}]>",
        )

    def finish(self) -> None:
        self.close()
        if len(self._stack) > 1:
            open_element = self._stack[-1]
            self.issues.append(
                Issue(
                    "HTML_UNCLOSED_ELEMENT",
                    "error",
                    f"<{open_element.tag}> was never closed (opened at line {open_element.line}, "
                    f"column {open_element.column}).",
                    expected=f"</{open_element.tag}>",
                    found="end of input",
                    line=open_element.line,
                    column=open_element.column,
                )
            )


def parse_fragment(source: str) -> ParsedFragment:
    """Parse a body fragment; structural errors stop parsing and are reported."""
    builder = _TreeBuilder()
    try:
        builder.feed(source)
        builder.finish()
    except _Abort:
        pass
    return ParsedFragment(builder.root, builder.issues, builder.comments)


# ── selectors ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class _Predicate:
    kind: str
    name: str = ""
    value: str = ""


@dataclass(slots=True)
class _Compound:
    tag: str
    predicates: list[_Predicate]


_TOKEN = re.compile(r"\s*>\s*|\s+|[^\s>]+")
_COMPOUND = re.compile(r"^(?P<tag>[A-Za-z][\w-]*|\*)?(?P<rest>.*)$")
_PREDICATE = re.compile(
    r"#(?P<id>[\w-]+)"
    r"|\.(?P<cls>[\w-]+)"
    r"|\[(?P<attr>[\w-]+)(?:(?P<op>\^=|=)(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<bare>[^\]]*)))?\]"
    r"|:(?P<pseudo>first-child|last-child)"
    r"|:nth-child\((?P<nth>\d+)\)"
)

_CACHE: dict[str, list[tuple[str, _Compound]]] = {}


def _parse_compound(token: str) -> _Compound:
    head = _COMPOUND.match(token)
    if head is None:  # pragma: no cover - the pattern matches any string
        raise ValueError(f"Bad selector: {token!r}")
    rest = head.group("rest")
    predicates: list[_Predicate] = []
    position = 0
    while position < len(rest):
        match = _PREDICATE.match(rest, position)
        if match is None:
            raise ValueError(f"Unsupported selector syntax near {rest[position:]!r} in {token!r}")
        position = match.end()
        if match.group("id"):
            predicates.append(_Predicate("id", value=match.group("id")))
        elif match.group("cls"):
            predicates.append(_Predicate("class", value=match.group("cls")))
        elif match.group("attr"):
            value = match.group("dq") or match.group("sq") or match.group("bare") or ""
            predicates.append(_Predicate(match.group("op") or "has", match.group("attr"), value))
        elif match.group("pseudo"):
            predicates.append(_Predicate(match.group("pseudo")))
        else:
            predicates.append(_Predicate("nth", value=match.group("nth")))
    return _Compound(head.group("tag") or "*", predicates)


def _parse_selector(selector: str) -> list[tuple[str, _Compound]]:
    cached = _CACHE.get(selector)
    if cached is not None:
        return cached
    chain: list[tuple[str, _Compound]] = []
    combinator = ""
    for match in _TOKEN.finditer(selector.strip()):
        token = match.group(0)
        if token.strip() == ">":
            combinator = ">"
        elif not token.strip():
            combinator = combinator or " "
        else:
            chain.append((combinator, _parse_compound(token)))
            combinator = " "
    if not chain:
        raise ValueError(f"Empty selector: {selector!r}")
    _CACHE[selector] = chain
    return chain


def _compound_matches(element: Element, compound: _Compound) -> bool:
    if compound.tag != "*" and element.tag != compound.tag:
        return False
    for predicate in compound.predicates:
        kind = predicate.kind
        if kind == "id":
            if element.get("id") != predicate.value:
                return False
        elif kind == "class":
            if not element.has_class(predicate.value):
                return False
        elif kind == "has":
            if not element.has(predicate.name):
                return False
        elif kind == "=":
            if element.get(predicate.name) != predicate.value:
                return False
        elif kind == "^=":
            value = element.get(predicate.name)
            if value is None or not value.startswith(predicate.value):
                return False
        else:
            siblings = element.parent.elements() if element.parent is not None else [element]
            index = siblings.index(element) + 1
            if kind == "first-child" and index != 1:
                return False
            if kind == "last-child" and index != len(siblings):
                return False
            if kind == "nth" and index != int(predicate.value):
                return False
    return True


def _chain_matches(element: Element, chain: list[tuple[str, _Compound]], index: int) -> bool:
    combinator, compound = chain[index]
    if not _compound_matches(element, compound):
        return False
    if index == 0:
        return True
    ancestor = element.parent
    if combinator == ">":
        return (
            ancestor is not None
            and ancestor.tag != "#fragment"
            and _chain_matches(ancestor, chain, index - 1)
        )
    while ancestor is not None and ancestor.tag != "#fragment":
        if _chain_matches(ancestor, chain, index - 1):
            return True
        ancestor = ancestor.parent
    return False


def select(root: Element, selector: str) -> list[Element]:
    """All descendants of ``root`` matching ``selector``, in document order."""
    chain = _parse_selector(selector)
    last = len(chain) - 1
    return [node for node in root.iter_descendants() if _chain_matches(node, chain, last)]


def select_one(root: Element, selector: str) -> Element | None:
    found = select(root, selector)
    return found[0] if found else None
