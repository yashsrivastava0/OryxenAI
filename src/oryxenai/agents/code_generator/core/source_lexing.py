"""Small lexical helpers shared by generated-source contract checks."""

from __future__ import annotations

import re

# Characters after which a top-level "/" is division/regex-end, not a new
# regex literal's opening slash: identifier/number tails, closers, and quote
# ends. Anything else (operators, punctuation, start-of-file) is a position
# where JavaScript itself would also parse "/" as starting a regex literal.
# "<" is included even though a bare less-than operator would make a
# following "/" a valid regex start in real JS: in this JSX/TSX source, "<"
# immediately followed by "/" is overwhelmingly a closing tag ("</Foo>"),
# never a regex literal, and misreading it as one can swallow an adjacent
# real "//" comment.
_REGEX_DIVISION_CONTEXT = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$)]\"'`<"
)


def _scan_regex_literal(value: str, start: int, length: int) -> int | None:
    """Return the end index of a JS regex literal starting at ``start``, or None.

    ``value[start]`` must be "/". Returns None (not a regex literal) for an
    empty body (the invalid ``//``/``/*`` cases, left to comment handling),
    an unterminated literal, or one that reaches a raw newline before closing
    — JS regex literals cannot contain a literal line break.
    """

    index = start + 1
    if index >= length or value[index] in ("/", "*"):
        return None
    in_class = False
    while index < length:
        character = value[index]
        if character == "\\" and index + 1 < length:
            index += 2
            continue
        if character in "\r\n":
            return None
        if character == "[":
            in_class = True
        elif character == "]":
            in_class = False
        elif character == "/" and not in_class:
            index += 1
            while index < length and value[index].isalpha():
                index += 1
            return index
        index += 1
    return None


def strip_source_comments(value: str) -> str:
    """Remove real source comments without truncating quoted URL strings or regex literals.

    The Code Generator intentionally keeps its trusted source audits
    dependency-free.  A regular expression cannot distinguish ``//`` in a
    comment from ``//`` in a JavaScript string such as an HTTPS URL, so use a
    small quote-aware scanner instead.  A JS regex literal (e.g.
    ``/^\\/api\\//`` or ``.replace(/\\/+$/, "")``) can itself contain a bare
    ``//`` outside any quote once its own backslash-escapes are consumed, so
    regex literals are recognized and passed through verbatim using the same
    start-of-expression heuristic real JS lexers use. Removed characters
    become spaces and line endings are preserved, which keeps later
    line/ordering diagnostics stable.
    """

    result: list[str] = []
    index = 0
    quote = ""
    length = len(value)
    last_significant = ""
    while index < length:
        character = value[index]
        if quote:
            result.append(character)
            if character == "\\" and index + 1 < length:
                index += 1
                result.append(value[index])
            elif character == quote:
                quote = ""
            last_significant = character
            index += 1
            continue

        if character in {'"', "'", "`"}:
            quote = character
            result.append(character)
            last_significant = character
            index += 1
            continue

        if value.startswith("<!--", index):
            end = value.find("-->", index + 4)
            end = length if end < 0 else end + 3
            result.extend(
                "\n" if item == "\n" else "\r" if item == "\r" else " " for item in value[index:end]
            )
            index = end
            continue

        if character == "/" and last_significant not in _REGEX_DIVISION_CONTEXT:
            regex_end = _scan_regex_literal(value, index, length)
            if regex_end is not None:
                result.append(value[index:regex_end])
                last_significant = value[regex_end - 1]
                index = regex_end
                continue

        if value.startswith("/*", index):
            end = value.find("*/", index + 2)
            end = length if end < 0 else end + 2
            result.extend(
                "\n" if item == "\n" else "\r" if item == "\r" else " " for item in value[index:end]
            )
            index = end
            continue

        if value.startswith("//", index) and (index == 0 or value[index - 1] != ":"):
            end = index + 2
            while end < length and value[end] not in "\r\n":
                end += 1
            result.extend(" " for _ in value[index:end])
            index = end
            continue

        result.append(character)
        if not character.isspace():
            last_significant = character
        index += 1
    return "".join(result)


def _inside_jsx_opening_tag(value: str, position: int) -> bool:
    """Return whether ``position`` is top-level inside a static JSX opening tag.

    Work backward through possible ``<Tag`` starts, then scan each candidate
    forward while respecting quoted attribute values, comments, and JSX
    expression braces. This deliberately does not treat selector text inside
    ``querySelector('[data-x="y"]')`` as JSX attribute evidence.
    """

    search_before = position
    while search_before > 0:
        tag_start = value.rfind("<", 0, search_before)
        if tag_start < 0:
            return False
        search_before = tag_start
        tag = re.match(r"[A-Za-z_$][\w$.:~-]*", value[tag_start + 1 :])
        if tag is None:
            continue
        tag_name_end = tag_start + 1 + tag.end()
        if tag_name_end < len(value) and not (
            value[tag_name_end].isspace() or value[tag_name_end] in {"/", ">"}
        ):
            continue

        index = tag_name_end
        brace_depth = 0
        quote = ""
        line_comment = False
        block_comment = False
        closed = False
        while index < position:
            character = value[index]
            if line_comment:
                if character in "\r\n":
                    line_comment = False
                index += 1
                continue
            if block_comment:
                if value.startswith("*/", index):
                    block_comment = False
                    index += 2
                else:
                    index += 1
                continue
            if quote:
                if character == "\\" and index + 1 < position:
                    index += 2
                    continue
                if character == quote:
                    quote = ""
                index += 1
                continue
            if value.startswith("//", index):
                line_comment = True
                index += 2
                continue
            if value.startswith("/*", index):
                block_comment = True
                index += 2
                continue
            if character in {'"', "'", "`"}:
                quote = character
            elif character == "{":
                brace_depth += 1
            elif character == "}" and brace_depth:
                brace_depth -= 1
            elif character == ">" and brace_depth == 0:
                closed = True
                break
            index += 1
        if not closed and not quote and not line_comment and not block_comment and brace_depth == 0:
            return True
    return False


def static_jsx_attribute_values(value: str, attribute_name: str) -> list[tuple[int, str]]:
    """Return positions and values for literal attributes on JSX opening tags."""

    attribute = re.escape(attribute_name)
    pattern = re.compile(
        rf"(?<![\w:.-]){attribute}\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        re.DOTALL,
    )
    return [
        (match.start(), match.group("value"))
        for match in pattern.finditer(value)
        if _inside_jsx_opening_tag(value, match.start())
    ]
